"""
Core infrastructure for the LangGraph-based eval system v2.

This module provides configuration, dynamic imports, and test loading
capabilities that make the eval framework agent-agnostic.

Submodules:
    config: Configuration management (EvalConfig, path utilities)
    loader: Dynamic imports and test case loading
    session: TestSession wrapper for AgentSession
    events: Event extraction from LiveKit run results

Configuration (config.py):
    EvalConfig: Dataclass holding framework configuration
        - type: "single" or "multi" agent system
        - default_agent: Starting agent ID
        - agent_ids: List of agent IDs to instantiate
        - imports: Dict of module/class import paths

    get_eval_dir(): Path to eval/ directory
    get_agent_dir(): Path to parent agent directory
    get_config(): Get cached EvalConfig singleton

Dynamic Imports (loader.py):
    get_userdata_class(config): Get UserData class for this agent
    get_agent_classes(config): Get {agent_id: AgentClass} mapping
    get_tools_function(config): Get tools lookup function
    create_test_userdata(config): Create populated test UserData

Test Loading (loader.py):
    load_test_cases(file, tags): Load tests from testcases/*.yaml
    get_test_case(name): Get single test by name
    load_agent_config(): Load agent.yaml configuration
    load_instructions(agent_id, userdata): Load processed instructions

Session (session.py):
    TestSession: Context manager wrapping AgentSession
        - Handles agent instantiation and cleanup
        - Captures initial greeting from on_enter()
        - Provides send_message() for turn processing

Events (events.py):
    extract_events(run_result): Extract TurnEvents from LiveKit result
    get_response_text(events): Concatenate agent message text

Usage:
    >>> from eval.core import EvalConfig, load_test_cases
    >>> config = EvalConfig.load()
    >>> tests = load_test_cases(tags=["unit"])
"""

from .config import (
    EvalConfig,
    get_eval_dir,
    get_agent_dir,
    request_scope,
)

from .loader import (
    get_userdata_class,
    get_agent_classes,
    get_tools_function,
    create_test_userdata,
    load_test_cases,
    get_test_case,
    load_agent_config,
    load_instructions,
    clear_cache,
)

from .userdata import (
    apply_test_data_overrides,
    build_template_variables,
)

__all__ = [
    # Config
    "EvalConfig",
    "get_eval_dir",
    "get_agent_dir",
    "request_scope",
    # Loader
    "get_userdata_class",
    "get_agent_classes",
    "get_tools_function",
    "create_test_userdata",
    "load_test_cases",
    "get_test_case",
    "load_agent_config",
    "load_instructions",
    "clear_cache",
    # Userdata
    "apply_test_data_overrides",
    "build_template_variables",
]
