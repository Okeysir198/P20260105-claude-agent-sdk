"""
Generic LiveKit Voice Agent Test Provider

Runs agent sessions in text mode and collects all events.
Self-contained eval framework - copy the entire eval/ folder to any agent.

Usage:
    from _provider import run_test_case, run_conversation, run_single_turn

    result = run_single_turn("Hello", target_agent="introduction")
    result = run_test_case(get_test_case("Person confirms identity"))

Configuration:
    Edit eval_config.yaml in the eval/ folder to configure the framework.
    See eval_config.yaml for all available options.
"""

from __future__ import annotations

import asyncio
import copy
import importlib
import json
import sys
import yaml
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Callable, Awaitable, Any

from rich.console import Console

# Path setup
_eval_dir = Path(__file__).parent  # eval/ folder
_agent_dir = _eval_dir.parent  # agent root folder
sys.path.insert(0, str(_agent_dir))

from dotenv import load_dotenv
_backend_dir = _agent_dir.parent
load_dotenv(_backend_dir / ".env")

from livekit.agents import AgentSession, Agent
from livekit.plugins import openai

# Shared console for logging
_console = Console()

# Caches for dynamic imports
_eval_config_cache: dict = {}
_imported_modules_cache: dict = {}

# Global version setting
_current_version: str | None = None


# =============================================================================
# Test Separator
# =============================================================================

def print_test_separator(test_name: str | None = None, is_start: bool = True) -> None:
    """Print a clear separator line for test case logging using rich."""
    if is_start:
        title = f"TEST: {test_name}" if test_name else "TEST CASE"
        _console.print()
        # Left-aligned with dashes on both sides
        prefix = "─" * 6
        suffix_len = max(10, 80 - len(title) - 8)  # 8 = prefix + spaces
        suffix = "─" * suffix_len
        _console.print(f"[cyan]{prefix}[/cyan] [bold cyan]{title}[/bold cyan] [cyan]{suffix}[/cyan]")


# =============================================================================
# Configuration
# =============================================================================

def load_agent_config() -> dict:
    """Load agent configuration from agent.yaml."""
    config_path = _agent_dir / "agent.yaml"
    return yaml.safe_load(config_path.read_text()) if config_path.exists() else {}


def load_eval_config_file() -> dict:
    """Load eval configuration from eval_config.yaml."""
    config_path = _eval_dir / "eval_config.yaml"
    return yaml.safe_load(config_path.read_text()) if config_path.exists() else {}


def get_eval_config() -> dict:
    """
    Get eval configuration from eval_config.yaml (self-contained).

    Priority:
    1. eval_config.yaml in eval/ folder (primary - self-contained)
    2. Defaults based on common conventions
    """
    global _eval_config_cache
    if _eval_config_cache:
        return _eval_config_cache

    # Load from eval_config.yaml (self-contained)
    eval_cfg = load_eval_config_file()

    # Defaults for missing values
    defaults = {
        "type": "single",
        "default_agent": "main",
        "agent_ids": ["main"],
        "imports": {
            "userdata_module": "shared_state",
            "userdata_class": "UserData",
            "test_data_factory": "shared_state:create_test_userdata",
            "agent_classes_module": "sub_agents",
            "agent_classes_var": "AGENT_CLASSES",
            "tools_module": "tools",
            "tools_function": "get_tools_by_names",
        }
    }

    # Merge with eval_config.yaml taking precedence
    result = {**defaults, **eval_cfg}
    result["imports"] = {**defaults["imports"], **eval_cfg.get("imports", {})}

    _eval_config_cache.update(result)
    return result


def clear_eval_config_cache() -> None:
    """Clear the eval config cache. Useful for testing."""
    global _eval_config_cache, _imported_modules_cache
    _eval_config_cache = {}
    _imported_modules_cache = {}


def set_version(version: str | None) -> None:
    """Set the global prompt version for testing."""
    global _current_version
    _current_version = version
    _console.print(f"[dim]Version set to: {version or 'default'}[/dim]")


def get_version() -> str | None:
    """Get the current prompt version."""
    return _current_version


# =============================================================================
# Dynamic Import System
# =============================================================================

def _dynamic_import(module_path: str, attr_name: str | None = None) -> Any:
    """
    Dynamically import a module or attribute.

    Args:
        module_path: The module to import (e.g., "shared_state")
        attr_name: Optional attribute to get from the module (e.g., "UserData")

    Returns:
        The imported module or attribute
    """
    cache_key = f"{module_path}:{attr_name}"
    if cache_key in _imported_modules_cache:
        return _imported_modules_cache[cache_key]

    module = importlib.import_module(module_path)
    result = getattr(module, attr_name) if attr_name else module
    _imported_modules_cache[cache_key] = result
    return result


def get_userdata_class():
    """Get the UserData class for this agent."""
    cfg = get_eval_config()["imports"]
    return _dynamic_import(cfg["userdata_module"], cfg["userdata_class"])


def get_agent_classes() -> dict:
    """Get agent class mapping {agent_id: AgentClass}."""
    cfg = get_eval_config()["imports"]
    return _dynamic_import(cfg["agent_classes_module"], cfg["agent_classes_var"])


def get_tools_function():
    """Get the tools lookup function."""
    cfg = get_eval_config()["imports"]
    return _dynamic_import(cfg["tools_module"], cfg["tools_function"])


def get_agent_ids() -> list[str]:
    """Get list of agent IDs to instantiate."""
    return get_eval_config()["agent_ids"]


def get_default_agent() -> str:
    """Get the default starting agent ID."""
    return get_eval_config()["default_agent"]


# =============================================================================
# Test Data Factory
# =============================================================================

def create_test_userdata():
    """
    Create test userdata using agent-specific factory.

    The factory is specified in agent.yaml:
        eval:
          imports:
            test_data_factory: eval.test_data:create_test_userdata

    If not specified or factory not found, creates default UserData.
    """
    cfg = get_eval_config()["imports"]
    factory_path = cfg.get("test_data_factory")

    if factory_path:
        try:
            # Parse "module.path:function_name" or "module.path.function_name"
            if ":" in factory_path:
                module_path, func_name = factory_path.rsplit(":", 1)
            else:
                module_path, func_name = factory_path.rsplit(".", 1)

            factory_func = _dynamic_import(module_path, func_name)
            return factory_func()
        except (ImportError, AttributeError) as e:
            _console.print(f"[yellow]Warning: Could not load test data factory '{factory_path}': {e}[/yellow]")

    # Default: create empty UserData
    UserData = get_userdata_class()
    return UserData()


# =============================================================================
# Configuration Helpers
# =============================================================================

def _build_template_variables(userdata=None, config: dict | None = None) -> dict:
    """Build template variables from userdata and config."""
    variables = {}

    # Add config variables
    if config:
        variables.update(config.get("variables", {}))

    # Add userdata fields if available
    if userdata:
        debtor = getattr(userdata, "debtor", None)
        call = getattr(userdata, "call", None)

        if debtor:
            variables.update({
                "debtor_name": getattr(debtor, "full_name", "") or "",
                "outstanding_amount": f"R{getattr(debtor, 'outstanding_amount', 0):,.2f}",
                "overdue_days": getattr(debtor, "overdue_days", 0) or 0,
                "contact_number": getattr(debtor, "contact_number", "") or "",
            })

        if call:
            variables.update({
                "authority": getattr(call, "authority", "") or "",
                "authority_contact": getattr(call, "authority_contact", "") or "",
            })

    return variables


def load_instructions(agent_id: str, userdata=None, config: dict | None = None, version: str | None = None) -> str:
    """Load and process agent instructions from config.

    Args:
        agent_id: The agent identifier
        userdata: Optional user data for template variables
        config: Optional agent config (loaded if not provided)
        version: Optional prompt version (e.g., 'v1', 'v2'). Uses global version if not specified.
    """
    if config is None:
        config = load_agent_config()

    # Use global version if not explicitly provided
    version = version or get_version()

    sub_agents = {a["id"]: a for a in config.get("sub_agents", [])}
    instructions = sub_agents.get(agent_id, {}).get("instructions", "")

    # YAML file path (e.g., prompts/prompt01_introduction.yaml)
    if "/" in instructions or instructions.endswith(".yaml"):
        prompt_file = _agent_dir / instructions

        # Try versioned file first if version specified
        if version:
            versioned_path = prompt_file.with_suffix(f".{version}.yaml")
            if versioned_path.exists():
                prompt_file = versioned_path
                _console.print(f"[dim]Loading versioned prompt: {versioned_path.name}[/dim]")

        if prompt_file.exists():
            prompt_data = yaml.safe_load(prompt_file.read_text())

            # Check for version key within the YAML file
            if version and "versions" in prompt_data and version in prompt_data["versions"]:
                template = prompt_data["versions"][version].get("prompt", prompt_data.get("prompt", ""))
                _console.print(f"[dim]Using version '{version}' from prompt file[/dim]")
            else:
                template = prompt_data.get("prompt", "")

            from prompts import format_instruction
            return format_instruction(template, **_build_template_variables(userdata, config))
        return ""

    # Function reference (e.g., func:prompts.get_negotiation_prompt)
    if instructions.startswith("func:"):
        module_name, func_name = instructions[5:].rsplit(".", 1)
        func = getattr(importlib.import_module(module_name), func_name)
        # Pass version to function if it accepts it
        import inspect
        sig = inspect.signature(func)
        if 'version' in sig.parameters:
            return func(userdata, config.get("variables", {}), version=version)
        return func(userdata, config.get("variables", {}))

    # Direct text - also render template variables
    from prompts import format_instruction
    return format_instruction(instructions, **_build_template_variables(userdata, config))


def load_test_cases(file: str | None = None) -> list[dict]:
    """Load test cases from testcases/*.yaml files in eval folder."""
    testcases_dir = _eval_dir / "testcases"

    test_cases = []

    if not testcases_dir.exists():
        return test_cases

    if file and (testcases_dir / file).exists():
        files = [testcases_dir / file]
    else:
        files = sorted(testcases_dir.glob("*.yaml"))

    default_agent = get_default_agent()

    for yaml_file in files:
        data = yaml.safe_load(yaml_file.read_text())
        agent_id = data.get("agent_id", "default")
        sub_agent_id = data.get("sub_agent_id", default_agent)

        for tc in data.get("test_cases", []):
            tc["_source_file"] = yaml_file.name
            tc["_agent_id"] = agent_id
            tc["_sub_agent_id"] = tc.get("start_agent", sub_agent_id)
            test_cases.append(tc)

    return test_cases


def get_test_case(name: str) -> Optional[dict]:
    """Get a single test case by name."""
    return next((tc for tc in load_test_cases() if tc.get("name") == name), None)


def get_llm_model(version: str | None = None) -> str:
    """Get LLM model from agent.yaml config.

    Args:
        version: Optional version override. Uses global version if not specified.
    """
    config = load_agent_config()
    # Use global version if not explicitly provided
    version = version or get_version()
    if version:
        version_config = config.get("versions", {}).get(version, {})
        if version_config:
            base = copy.deepcopy(config)
            for k, v in version_config.items():
                if k != "description":
                    if isinstance(v, dict) and isinstance(base.get(k), dict):
                        base[k].update(v)
                    else:
                        base[k] = v
            config = base
    return config.get("llm", {}).get("model", "gpt-4o-mini")


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class ConversationEvent:
    """Single event in a conversation."""
    type: str  # user_input | tool_call | tool_output | assistant_message
    content: dict

    def to_dict(self):
        return asdict(self)


@dataclass
class TurnResult:
    """Result of a single conversation turn."""
    user_input: str
    events: list[ConversationEvent] = field(default_factory=list)

    def to_dict(self):
        return {"user_input": self.user_input, "events": [e.to_dict() for e in self.events]}


@dataclass
class ConversationResult:
    """Result of a full conversation."""
    turns: list[TurnResult] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self):
        return {"turns": [t.to_dict() for t in self.turns], "error": self.error}

    def to_json(self, indent=2):
        return json.dumps(self.to_dict(), indent=indent)

    def get_all_events(self) -> list[ConversationEvent]:
        return [e for turn in self.turns for e in turn.events]

    def get_assistant_messages(self) -> list[str]:
        return [e.content.get("text", "") for e in self.get_all_events() if e.type == "assistant_message"]

    def get_tool_calls(self) -> list[dict]:
        return [e.content for e in self.get_all_events() if e.type == "tool_call"]


# =============================================================================
# Agent Creation & Session Runner
# =============================================================================

def create_agent(agent_id: str, userdata=None, config: dict | None = None) -> Agent:
    """Create a real agent instance for testing."""
    AGENT_CLASSES = get_agent_classes()
    get_tools = get_tools_function()

    agent_class = AGENT_CLASSES.get(agent_id)
    if not agent_class:
        raise ValueError(f"Agent '{agent_id}' not found. Available: {list(AGENT_CLASSES.keys())}")

    if config is None:
        config = load_agent_config()

    sub_agents = {a["id"]: a for a in config.get("sub_agents", [])}
    agent_cfg = sub_agents.get(agent_id, {})

    instructions = load_instructions(agent_id, userdata, config)
    tools = get_tools(agent_cfg.get("tools", []), strict=False)

    return agent_class(instructions=instructions, tools=tools)


def create_agents_for_session(userdata, config: dict | None = None) -> dict:
    """
    Create all agents for a test session.

    For multi-agent systems: Creates all agents defined in agent_ids
    For single-agent systems: Creates only the default agent
    """
    if config is None:
        config = load_agent_config()

    agent_ids = get_agent_ids()

    return {
        agent_id: create_agent(agent_id, userdata, config)
        for agent_id in agent_ids
    }


def _extract_events(run_result) -> list[ConversationEvent]:
    """Extract events from LiveKit RunResult."""
    events = []

    for event in run_result.events:
        item = getattr(event, 'item', None)
        if item is None:
            continue

        # Assistant message
        if hasattr(item, 'role') and item.role == 'assistant':
            content = getattr(item, 'content', '')
            if isinstance(content, list):
                content = ' '.join(str(c) for c in content)
            events.append(ConversationEvent(type="assistant_message", content={"text": str(content)}))

        # Tool call
        elif hasattr(item, 'name') and hasattr(item, 'arguments'):
            args = item.arguments
            if args and not isinstance(args, dict):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {"raw": args}
            events.append(ConversationEvent(type="tool_call", content={"name": item.name, "arguments": args or {}}))

        # Tool output
        elif hasattr(item, 'output'):
            events.append(ConversationEvent(
                type="tool_output",
                content={"result": str(item.output), "is_error": getattr(item, 'is_error', False)}
            ))

        # Agent handoff
        elif hasattr(item, 'new_agent_id') and hasattr(item, 'old_agent_id'):
            events.append(ConversationEvent(
                type="handoff",
                content={
                    "from_agent": item.old_agent_id or "unknown",
                    "to_agent": item.new_agent_id or "unknown"
                }
            ))

    return events


async def _run_session(turns: list[dict], start_agent: str | None = None, model: str = "gpt-4o-mini") -> ConversationResult:
    """Run agent session and collect events."""
    result = ConversationResult()

    # Use configured default if not specified
    if start_agent is None:
        start_agent = get_default_agent()

    try:
        async with openai.LLM(model=model) as llm:
            # Use pluggable test data factory
            userdata = create_test_userdata()
            config = load_agent_config()

            # Create all agents dynamically
            userdata.agents = create_agents_for_session(userdata, config)

            # Get starting agent with fallback
            default_agent = get_default_agent()
            agent = userdata.agents.get(start_agent)
            if agent is None:
                agent = userdata.agents.get(default_agent)
            if agent is None and userdata.agents:
                agent = next(iter(userdata.agents.values()))

            if agent is None:
                raise ValueError(f"Agent '{start_agent}' not found. Available: {list(userdata.agents.keys())}")

            async with AgentSession(llm=llm, userdata=userdata) as session:
                await session.start(agent)

                # Wait for on_enter generate_reply to complete and add message to history
                await asyncio.sleep(1.5)

                initial_events = []
                for item in session.history.items:
                    if hasattr(item, 'role') and item.role == 'assistant':
                        text = getattr(item, 'text_content', '') or ''
                        if text:
                            initial_events.append(ConversationEvent(
                                type="assistant_message",
                                content={"text": text}
                            ))
                    elif hasattr(item, 'new_agent_id') and hasattr(item, 'old_agent_id'):
                        initial_events.append(ConversationEvent(
                            type="handoff",
                            content={
                                "from_agent": item.old_agent_id or "unknown",
                                "to_agent": item.new_agent_id or "unknown"
                            }
                        ))

                # Add initial turn (Turn 0) if there are on_enter events
                if initial_events:
                    turn_result = TurnResult(user_input="[session_start]")
                    turn_result.events = initial_events
                    result.turns.append(turn_result)

                for turn in turns:
                    user_input = turn.get("user_input", "")
                    turn_result = TurnResult(user_input=user_input)
                    turn_result.events.append(ConversationEvent(type="user_input", content={"text": user_input}))

                    run_result = await session.run(user_input=user_input)
                    turn_result.events.extend(_extract_events(run_result))
                    result.turns.append(turn_result)

    except Exception as e:
        result.error = str(e)

    return result


# =============================================================================
# Public API
# =============================================================================

def run_single_turn(user_input: str, target_agent: str | None = None, model: str | None = None) -> ConversationResult:
    """Run a single turn conversation."""
    if target_agent is None:
        target_agent = get_default_agent()
    return asyncio.run(_run_session(
        turns=[{"user_input": user_input}],
        start_agent=target_agent,
        model=model or get_llm_model()
    ))


def run_conversation(turns: list[dict], start_agent: str | None = None, model: str | None = None) -> ConversationResult:
    """Run a multi-turn conversation."""
    if start_agent is None:
        start_agent = get_default_agent()
    return asyncio.run(_run_session(turns=turns, start_agent=start_agent, model=model or get_llm_model()))


def run_test_case(test_case: dict, model: str | None = None) -> ConversationResult:
    """Run a test case loaded from YAML."""
    test_name = test_case.get("name", "Unknown")
    version = get_version()
    print_test_separator(test_name, is_start=True)

    if version:
        _console.print(f"[dim]Testing with prompt version: {version}[/dim]")

    default_agent = get_default_agent()
    agent_id = test_case.get("_sub_agent_id", default_agent)
    turns = [{"user_input": t["user_input"]} for t in test_case.get("turns", [])]
    result = run_conversation(turns, start_agent=agent_id, model=model or get_llm_model())

    print_test_separator(test_name, is_start=False)
    return result


async def interactive_session(
    start_agent: str | None = None,
    model: str | None = None,
    get_input: Callable[[], Awaitable[str | None]] | None = None,
    on_output: Callable[[TurnResult], Awaitable[None]] | None = None,
    on_thinking_start: Callable[[], None] | None = None,
    on_thinking_end: Callable[[], None] | None = None
) -> None:
    """Run an interactive session with persistent context."""
    if get_input is None or on_output is None:
        raise ValueError("get_input and on_output callbacks are required")

    # Use configured default if not specified
    if start_agent is None:
        start_agent = get_default_agent()

    model = model or get_llm_model()

    while True:
        status = "done"
        async with openai.LLM(model=model) as llm:
            # Use pluggable test data factory
            userdata = create_test_userdata()
            config = load_agent_config()

            # Create all agents dynamically
            userdata.agents = create_agents_for_session(userdata, config)

            # Get starting agent with fallback
            default_agent = get_default_agent()
            agent = userdata.agents.get(start_agent)
            if agent is None:
                agent = userdata.agents.get(default_agent)
            if agent is None and userdata.agents:
                agent = next(iter(userdata.agents.values()))

            async with AgentSession(llm=llm, userdata=userdata) as session:
                await session.start(agent)

                while True:
                    user_input = await get_input()

                    if user_input is None:
                        break
                    if user_input == "reset":
                        status = "reset"
                        break
                    if not user_input:
                        continue

                    turn_result = TurnResult(user_input=user_input)
                    turn_result.events.append(ConversationEvent(type="user_input", content={"text": user_input}))

                    try:
                        if on_thinking_start:
                            on_thinking_start()
                        run_result = await session.run(user_input=user_input)
                        turn_result.events.extend(_extract_events(run_result))
                    except Exception as e:
                        turn_result.events.append(ConversationEvent(type="error", content={"message": str(e)}))
                    finally:
                        if on_thinking_end:
                            on_thinking_end()

                    await on_output(turn_result)

        if status != "reset":
            break


# =============================================================================
# Promptfoo Provider Interface
# =============================================================================

def call_api(prompt: str, options: dict, context: dict) -> dict:
    """Promptfoo provider interface."""
    vars_dict = context.get("vars", {})

    # Set version from vars if provided
    version = vars_dict.get("version") or options.get("config", {}).get("version")
    if version:
        set_version(version)

    model = options.get("config", {}).get("model") or get_llm_model()

    try:
        # Mode 1: Load test by name
        test_name = vars_dict.get("test_name", prompt if prompt else None)
        if test_name:
            test_case = get_test_case(test_name)
            if test_case:
                result = run_test_case(test_case, model)
                return {
                    "output": result.to_json(),
                    "metadata": {
                        "test_name": test_name,
                        "version": version or "default",
                        "assistant_messages": result.get_assistant_messages(),
                        "tool_calls": result.get_tool_calls(),
                    }
                }

        # Mode 2 & 3: Direct input
        user_input = vars_dict.get("user_input", "")
        default_agent = get_default_agent()
        target_agent = vars_dict.get("target_agent", default_agent)
        turns_data = vars_dict.get("turns")

        if turns_data:
            result = run_conversation(turns_data, target_agent, model)
        elif user_input:
            result = run_single_turn(user_input, target_agent, model)
        else:
            return {"output": "", "error": "No test_name, user_input, or turns provided"}

        return {
            "output": result.to_json(),
            "metadata": {
                "version": version or "default",
                "assistant_messages": result.get_assistant_messages(),
                "tool_calls": result.get_tool_calls()
            }
        }

    except Exception as e:
        return {"output": "", "error": str(e)}


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    from _console import console, print_header, print_conversation_result, create_test_table
    import argparse

    parser = argparse.ArgumentParser(description="LiveKit Voice Agent Test Provider")
    parser.add_argument("--list", action="store_true", help="List all test cases")
    parser.add_argument("--test", type=str, help="Run specific test by name")
    parser.add_argument("--config", action="store_true", help="Show agent config")
    parser.add_argument("--eval-config", action="store_true", help="Show eval config")
    args = parser.parse_args()

    if args.config:
        print_header("Agent Configuration")
        console.print(yaml.dump(load_agent_config(), default_flow_style=False))

    elif args.eval_config:
        print_header("Eval Configuration")
        console.print(yaml.dump(get_eval_config(), default_flow_style=False))

    elif args.list:
        tests = load_test_cases()
        default_agent = get_default_agent()
        table = create_test_table(f"Test Cases ({len(tests)})")
        for tc in tests:
            table.add_row(
                tc["name"],
                tc.get("_sub_agent_id", default_agent),
                tc.get("test_type", "unknown"),
                ", ".join(tc.get("tags", []))
            )
        console.print(table)

    elif args.test:
        tc = get_test_case(args.test)
        if tc:
            result = run_test_case(tc)
            print_conversation_result(result, tc["name"])
        else:
            console.print(f"[red]Test not found: {args.test}[/red]")

    else:
        default_agent = get_default_agent()
        print_header("Quick Test", f"Single turn with {default_agent} agent")
        result = run_single_turn("Yes, speaking", target_agent=default_agent)
        print_conversation_result(result)
