"""Eval workflow - runs tests with assertion checking.

Assertion Types:
    contains: Response contains substring (case-insensitive)
    not_contains: Response does NOT contain substring
    contains_any: Response contains at least one value
    equals: Exact match (trimmed)
    contains_function_call: Specific tool was called
    llm_rubric: LLM-based semantic evaluation using an LLM judge
"""
import time
import uuid
from pathlib import Path
from typing import Optional

import yaml
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.func import entrypoint, task
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.config import get_stream_writer

from .test_workflow import test_workflow, thread_config, checkpointer
from ..schemas.models import Turn, TurnEvent, EvalResult, EventType
from ..schemas.test_case import AssertionType


# Cache for loaded judge prompts
_judge_prompts_cache: Optional[dict] = None


def _load_judge_prompts() -> dict:
    """Load LLM judge prompts from YAML configuration.

    Returns:
        Dict with 'system_prompt' and 'eval_template' keys

    Raises:
        FileNotFoundError: If prompts/llm_judge.yaml doesn't exist
        yaml.YAMLError: If YAML parsing fails
    """
    global _judge_prompts_cache

    if _judge_prompts_cache is not None:
        return _judge_prompts_cache

    prompts_path = Path(__file__).parent.parent / "prompts" / "llm_judge.yaml"

    if not prompts_path.exists():
        raise FileNotFoundError(
            f"LLM judge prompts not found at {prompts_path}. "
            "Create prompts/llm_judge.yaml with 'system_prompt' and 'eval_template' keys."
        )

    with open(prompts_path, 'r') as f:
        prompts = yaml.safe_load(f)

    if 'system_prompt' not in prompts:
        raise ValueError("llm_judge.yaml must contain 'system_prompt' key")
    if 'eval_template' not in prompts:
        raise ValueError("llm_judge.yaml must contain 'eval_template' key")

    _judge_prompts_cache = prompts
    return prompts


async def evaluate_with_llm(
    user_input: str,
    agent_response: str,
    rubric: str,
    model: Optional[str] = None
) -> tuple[bool, str]:
    """Evaluate agent response against rubric using LLM judge.

    Args:
        user_input: The user's message
        agent_response: The agent's response to evaluate
        rubric: The evaluation criteria/rubric
        model: LLM model to use for evaluation (default: from config)

    Returns:
        Tuple of (passed: bool, reason: str)
    """
    import json
    from ..core.config import get_config

    prompts = _load_judge_prompts()

    # Use config default if model not specified (strict resolution)
    if model is None:
        config = get_config()
        model = config.resolve_model()

    llm = init_chat_model(model=model, model_provider="openai", temperature=0)

    eval_prompt = prompts['eval_template'].format(
        user_input=user_input,
        agent_response=agent_response,
        rubric=rubric
    )

    messages = [
        SystemMessage(content=prompts['system_prompt']),
        HumanMessage(content=eval_prompt),
    ]

    try:
        response = await llm.ainvoke(messages)
        content = response.content.strip()

        # Parse JSON response
        # Handle potential markdown code blocks
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        result = json.loads(content)
        return result.get("passed", False), result.get("reason", "No reason provided")

    except json.JSONDecodeError as e:
        return False, f"Failed to parse LLM response: {e}"
    except Exception as e:
        return False, f"LLM evaluation error: {e}"


@task
async def run_assertion(turn: Turn, assertion: dict) -> dict:
    """Run a single assertion against a turn.

    Args:
        turn: Turn object with agent_response and events
        assertion: Dict with 'type' and 'value' keys (type is already normalized by schema)

    Returns:
        Dict with assertion, passed, turn_number, message
    """
    raw_type = assertion.get("type", "")
    value = assertion.get("value", "")
    response = turn.agent_response.lower()

    passed = False
    message = None

    # Normalize assertion type using canonical enum
    # This handles any legacy hyphenated types that weren't pre-validated
    try:
        assertion_type = AssertionType.normalize(raw_type)
    except ValueError:
        return {
            "assertion": assertion,
            "passed": False,
            "turn_number": turn.turn_number,
            "message": f"Unknown assertion type: {raw_type}"
        }

    if assertion_type == AssertionType.CONTAINS_FUNCTION_CALL:
        # Check if any tool call matches the expected name
        passed = any(
            e.type == EventType.TOOL_CALL and e.content.get("name") == value
            for e in turn.events
        )
        if not passed:
            tool_names = [e.content.get("name") for e in turn.events if e.type == EventType.TOOL_CALL]
            message = f"Expected tool '{value}', found: {tool_names}"

    elif assertion_type == AssertionType.CONTAINS:
        if isinstance(value, list):
            passed = all(v.lower() in response for v in value)
        else:
            passed = value.lower() in response
        if not passed:
            message = f"Response does not contain '{value}'"

    elif assertion_type == AssertionType.NOT_CONTAINS:
        if isinstance(value, list):
            passed = not any(v.lower() in response for v in value)
            if not passed:
                found = [v for v in value if v.lower() in response]
                message = f"Response should not contain: {found}"
        else:
            passed = value.lower() not in response
            if not passed:
                message = f"Response should not contain '{value}'"

    elif assertion_type == AssertionType.CONTAINS_ANY:
        if isinstance(value, list):
            passed = any(v.lower() in response for v in value)
        else:
            passed = value.lower() in response
        if not passed:
            message = f"Response should contain at least one of: {value}"

    elif assertion_type == AssertionType.CONTAINS_ALL:
        if isinstance(value, list):
            passed = all(v.lower() in response for v in value)
        else:
            passed = value.lower() in response
        if not passed:
            message = f"Response should contain all of: {value}"

    elif assertion_type == AssertionType.EQUALS:
        passed = turn.agent_response.strip() == str(value).strip()
        if not passed:
            message = f"Expected exact match with '{value}'"

    elif assertion_type == AssertionType.MATCHES:
        import re
        try:
            passed = bool(re.search(value, turn.agent_response))
        except re.error as e:
            passed = False
            message = f"Invalid regex pattern: {e}"
        if not passed and message is None:
            message = f"Response does not match pattern '{value}'"

    elif assertion_type == AssertionType.LLM_RUBRIC:
        # LLM-based semantic evaluation
        rubric = assertion.get("value") or assertion.get("rubric", "")
        eval_model = assertion.get("model")  # None = use config default in evaluate_with_llm

        if not rubric:
            passed = False
            message = "No rubric provided for llm_rubric assertion"
        else:
            passed, reason = await evaluate_with_llm(
                user_input=turn.user_input,
                agent_response=turn.agent_response,
                rubric=rubric,
                model=eval_model
            )
            message = reason

    return {
        "assertion": assertion,
        "passed": passed,
        "turn_number": turn.turn_number,
        "message": message
    }

@entrypoint(checkpointer=checkpointer)
async def eval_workflow(test_case: dict) -> EvalResult:
    """Run test case with assertion evaluation.

    Args:
        test_case: Dict with 'name', 'turns' (with 'assertions'), and optional runtime options:
            - _runtime_model: LLM model to use
            - _runtime_start_agent: Starting agent ID
            - _runtime_version: Agent version to use
    """
    start_time = time.time()
    writer = get_stream_writer()

    test_name = test_case.get("name", "Unknown")
    writer({"event": "eval_started", "test_name": test_name})

    # Run the test using ainvoke - simpler and avoids nested streaming complexity
    # Per LangGraph docs, nested astream calls can have issues with stream mode propagation
    # Runtime options are already packed into test_case, just pass it through
    inner_thread = str(uuid.uuid4())

    # Use ainvoke for the inner workflow - more reliable than nested streaming
    test_result = await test_workflow.ainvoke(
        test_case,
        config=thread_config(inner_thread)
    )

    # Emit turn events from the completed test for real-time feedback
    for turn in test_result.turns:
        if turn.user_input != "[session_start]":
            writer({"event": "user_input", "turn": turn.turn_number, "content": turn.user_input})

        # Emit turn events (tool calls, handoffs, etc.)
        for event in turn.events:
            writer({
                "event": "turn_event",
                "turn": turn.turn_number,
                "type": event.type.value,
                "content": event.content
            })

        writer({"event": "agent_response", "turn": turn.turn_number, "content": turn.agent_response})

    writer({"event": "completed", "total_turns": len(test_result.turns)})

    # Evaluate assertions
    all_results = []
    turns_data = test_case.get("turns", [])
    assertion_index = 0

    # Determine offset: if first turn is greeting ([session_start]), actual turns start at index 1
    has_greeting = (
        test_result.turns and
        test_result.turns[0].user_input == "[session_start]"
    )
    turn_offset = 1 if has_greeting else 0

    for i, turn_data in enumerate(turns_data):
        assertions = turn_data.get("assertions", [])
        turn_index = i + turn_offset
        if assertions and turn_index < len(test_result.turns):
            turn = test_result.turns[turn_index]
            for assertion in assertions:
                result = await run_assertion(turn, assertion)
                all_results.append(result)
                writer({
                    "event": "assertion_result",
                    "index": assertion_index,
                    "passed": result["passed"],
                    "type": assertion.get("type", ""),
                    "value": assertion.get("value", ""),
                    "message": result.get("message")
                })
                assertion_index += 1

    # Compute score
    passed = sum(1 for r in all_results if r["passed"])
    total = len(all_results)
    score = passed / total if total > 0 else 1.0

    writer({"event": "eval_completed", "score": score, "passed": passed, "failed": total - passed})

    duration_ms = (time.time() - start_time) * 1000

    return EvalResult(
        turns=test_result.turns,
        total_turns=test_result.total_turns,
        duration_ms=duration_ms,
        stop_reason=test_result.stop_reason,
        error=test_result.error,
        test_name=test_result.test_name,
        metadata=test_result.metadata,
        score=score,
        passed_count=passed,
        failed_count=total - passed,
        assertions=all_results
    )
