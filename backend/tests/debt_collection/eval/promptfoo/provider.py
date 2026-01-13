"""
Promptfoo provider - bridges promptfoo to our eval system.

This module is called by promptfoo to execute tests. It receives test
configuration from promptfoo and uses our EvalRunner to execute the test.

Usage:
    In promptfooconfig.yaml:
    providers:
      - id: file://promptfoo/provider.py
        config:
          model: gpt-4o-mini
"""

import sys
from pathlib import Path

# Add parent directories to path for imports
_current_dir = Path(__file__).parent
_eval_dir = _current_dir.parent
_agent_dir = _eval_dir.parent

if str(_agent_dir) not in sys.path:
    sys.path.insert(0, str(_agent_dir))

from eval import EvalRunner
from eval.core.loader import get_test_case
from eval.core.config import request_scope
from eval.schemas import EventType, EvalResult


def _format_conversation(result: EvalResult) -> str:
    """Format full conversation as human-readable text (same format as console.py).

    Format:
        User: {content}
        Agent: {content}
          -> Tool: {name}({args})
          <- Result: {result}
          -> Handoff: {from} -> {to}
    """
    lines = []

    for turn in result.turns:
        # User input (skip session_start marker)
        if turn.user_input and turn.user_input != "[session_start]":
            lines.append(f"User: {turn.user_input}")

        # Agent response
        if turn.agent_response:
            lines.append(f"Agent: {turn.agent_response}")

        # Events (tool calls and outputs) - indented like console.py
        for event in turn.events:
            if event.type == EventType.TOOL_CALL:
                name = event.content.get("name", "unknown")
                args = event.content.get("arguments", {})
                lines.append(f"  -> Tool: {name}({args})")
            elif event.type == EventType.TOOL_OUTPUT:
                result_text = event.content.get("result", "")
                is_error = event.content.get("is_error", False)
                if is_error:
                    lines.append(f"  <- Error: {result_text}")
                else:
                    lines.append(f"  <- Result: {result_text}")
            elif event.type == EventType.HANDOFF:
                from_agent = event.content.get("from_agent", "?")
                to_agent = event.content.get("to_agent", "?")
                lines.append(f"  -> Handoff: {from_agent} -> {to_agent}")

        lines.append("")  # Empty line between turns

    return "\n".join(lines)


def call_api(prompt: str, options: dict, context: dict) -> dict:
    """
    Promptfoo entry point. Called for each test case.

    This is the main entry point that promptfoo calls. It:
    1. Extracts the test name from context.vars
    2. Loads the test case from our YAML files
    3. Runs the test using our EvalRunner
    4. Formats the result for promptfoo

    Args:
        prompt: The prompt template (unused - we use test_name)
        options: Provider options from promptfooconfig.yaml
            - model: LLM model to use (default: from agent.yaml)
            - temperature: LLM temperature (default: from agent.yaml)
            - version: Prompt version for comparison
        context: Execution context with 'vars' containing test_name

    Returns:
        Dict with:
            - output: Agent's final response
            - metadata: Test execution details
            - tool_calls: List of tool invocations
            - error: Error message if failed
    """
    # Extract test name from test_case_definition (format: "Name: TEST-001: Description\n...")
    test_case_def = context.get("vars", {}).get("test_case_definition", "")
    test_name = None
    for line in test_case_def.split("\n"):
        if line.startswith("Name: "):
            test_name = line[6:].strip()  # Remove "Name: " prefix
            break

    if not test_name:
        return {"error": "No test_name found in test_case_definition"}

    # Use request-scoped config for test isolation (thread-safe, no cache clearing needed)
    with request_scope():
        # Load test case within scope
        test_case = get_test_case(test_name)
        if not test_case:
            return {"error": f"Test case not found: {test_name}"}

        try:
            # Run test with our eval system
            # Provider config is nested under options['config']
            # EvalRunner handles config resolution - no fallbacks here
            config = options.get("config", {})
            model = config.get("model") or options.get("model")  # None if not specified
            temperature = config.get("temperature")  # None if not specified
            version = config.get("version")

            # EvalRunner will resolve from agent.yaml if None (strict - raises on missing config)
            runner = EvalRunner(model=model, temperature=temperature, version=version)
            result = runner.run_eval(test_case)

            # Extract tool calls from events
            tool_calls = []
            tool_names = []
            for turn in result.turns:
                for event in turn.events:
                    if event.type == EventType.TOOL_CALL:
                        name = event.content.get("name")
                        tool_calls.append({
                            "name": name,
                            "arguments": event.content.get("arguments", {}),
                        })
                        if name:
                            tool_names.append(name)

            # Build output with full conversation in human-readable format
            # Same format as console.py for consistency
            output_text = _format_conversation(result)

            # Append tool tags for assertions (promptfoo assertions check 'output')
            # Format: [TOOL:name] for each tool called, easy to check with contains
            if tool_names:
                tool_tags = " ".join(f"[TOOL:{name}]" for name in tool_names)
                output_text += f"\n{tool_tags}"

            # Format response for promptfoo
            return {
                "output": output_text,
                "metadata": {
                    "test_name": result.test_name,
                    "turns": result.total_turns,
                    "duration_ms": round(result.duration_ms, 2),
                    "score": result.score,
                    "passed": result.passed_count,
                    "failed": result.failed_count,
                    "stop_reason": result.stop_reason,
                    "tool_names": tool_names,
                },
                "tool_calls": tool_calls,
            }

        except Exception as e:
            return {
                "error": str(e),
                "metadata": {"test_name": test_name},
            }
