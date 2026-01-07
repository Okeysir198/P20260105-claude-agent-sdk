"""Dynamic imports and test case loading."""

import importlib
import logging
import sys
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv

from .config import EvalConfig, get_agent_dir, get_eval_dir, get_config, clear_config_cache, ConfigurationError
from .userdata import apply_test_data_overrides, build_template_variables
from ..schemas.test_case import (
    validate_test_file,
    TestCaseValidationError,
)

logger = logging.getLogger(__name__)

# Ensure agent directory is in path for imports
_agent_dir = get_agent_dir()
if str(_agent_dir) not in sys.path:
    sys.path.insert(0, str(_agent_dir))

# Load environment variables from .env file
_backend_dir = _agent_dir.parent  # agents/ -> livekit-backend/
load_dotenv(_backend_dir / ".env")

# Optional import: format_instruction from agent's prompts module
# This module is dynamically loaded from the agent directory added to sys.path above
try:
    from prompts import format_instruction as _format_instruction  # type: ignore[import-not-found]
except ImportError:
    _format_instruction = None

# Module cache for dynamic imports
_cache: dict[str, Any] = {}


def clear_cache() -> None:
    """Clear all caches. Useful for testing."""
    global _cache
    _cache = {}
    clear_config_cache()


def _dynamic_import(module_path: str, attr_name: Optional[str] = None) -> Any:
    """Import a module or attribute dynamically.

    Args:
        module_path: Module to import (e.g., "shared_state")
        attr_name: Optional attribute to get from module
    """
    cache_key = f"{module_path}:{attr_name}" if attr_name else module_path

    if cache_key in _cache:
        return _cache[cache_key]

    module = importlib.import_module(module_path)
    result = getattr(module, attr_name) if attr_name else module

    _cache[cache_key] = result
    return result


def get_userdata_class(config: Optional[EvalConfig] = None) -> type:
    """Get the UserData class for this agent."""
    if config is None:
        config = get_config()

    module = config.get_import("userdata_module", "shared_state")
    cls = config.get_import("userdata_class", "UserData")
    assert module is not None and cls is not None
    return _dynamic_import(module, cls)


def get_agent_classes(config: Optional[EvalConfig] = None) -> dict[str, type]:
    """Get agent class mapping {agent_id: AgentClass}."""
    if config is None:
        config = get_config()

    module = config.get_import("agent_classes_module", "sub_agents")
    var = config.get_import("agent_classes_var", "AGENT_CLASSES")
    assert module is not None and var is not None
    return _dynamic_import(module, var)


def get_tools_function(config: Optional[EvalConfig] = None) -> Any:
    """Get the tools lookup function."""
    if config is None:
        config = get_config()

    module = config.get_import("tools_module", "tools")
    func = config.get_import("tools_function", "get_tools_by_names")
    assert module is not None and func is not None
    return _dynamic_import(module, func)


def create_test_userdata(
    config: Optional[EvalConfig] = None,
    test_data: Optional[dict] = None
):
    """Create test userdata using agent-specific factory.

    Args:
        config: EvalConfig instance
        test_data: Optional test-specific data to override defaults
    """
    if config is None:
        config = get_config()

    factory_path = config.get_import("test_data_factory")

    if factory_path:
        try:
            # Parse "module.path:function_name" or "module.path.function_name"
            if ":" in factory_path:
                module_path, func_name = factory_path.rsplit(":", 1)
            else:
                module_path, func_name = factory_path.rsplit(".", 1)

            factory_func = _dynamic_import(module_path, func_name)
            userdata = factory_func()

            # Apply test-specific overrides if provided
            if test_data:
                apply_test_data_overrides(userdata, test_data)

            return userdata
        except (ImportError, AttributeError) as e:
            logger.debug(f"Factory import failed, using fallback: {e}")

    # Default: create empty UserData
    UserData = get_userdata_class(config)
    return UserData()


def load_test_cases(
    file: Optional[str] = None,
    tags: Optional[list[str]] = None,
    config: Optional[EvalConfig] = None,
    strict: bool = True,
) -> list[dict]:
    """Load test cases from testcases/*.yaml files with STRICT validation.

    Args:
        file: Optional specific file to load
        tags: Optional list of tags to filter by
        config: Optional EvalConfig instance
        strict: If True (default), raise on invalid test files

    Returns:
        List of validated test case dictionaries

    Raises:
        TestCaseValidationError: If strict=True and validation fails
    """
    if config is None:
        config = get_config()

    testcases_dir = get_eval_dir() / "testcases"

    if not testcases_dir.exists():
        return []

    # Determine which files to load
    if file:
        file_path = testcases_dir / file
        files = [file_path] if file_path.exists() else []
    else:
        files = sorted(testcases_dir.glob("*.yaml"))

    test_cases = []
    default_agent = config.default_agent

    for yaml_file in files:
        raw_data = yaml.safe_load(yaml_file.read_text()) or {}

        # STRICT validation - validate against Pydantic schema
        if strict:
            validated_file = validate_test_file(raw_data, str(yaml_file))
            # Extract validated data
            agent_id = validated_file.agent_id
            sub_agent_id = validated_file.sub_agent_id or default_agent
            default_test_data = validated_file.default_test_data or {}

            for tc_model in validated_file.test_cases:
                # Convert validated model back to dict for compatibility
                tc = tc_model.to_dict()

                # Add metadata
                tc["_source_file"] = yaml_file.name
                tc["_agent_id"] = agent_id
                tc["_sub_agent_id"] = tc.get("start_agent", sub_agent_id)
                tc["_default_test_data"] = default_test_data

                # Filter by tags if specified
                if tags:
                    tc_tags = tc.get("tags", [])
                    if not any(tag in tc_tags for tag in tags):
                        continue

                test_cases.append(tc)
        else:
            # Legacy non-strict mode (for backward compatibility)
            agent_id = raw_data.get("agent_id", "default")
            sub_agent_id = raw_data.get("sub_agent_id", default_agent)
            default_test_data = raw_data.get("default_test_data", {})

            for tc in raw_data.get("test_cases", []):
                # Add metadata
                tc["_source_file"] = yaml_file.name
                tc["_agent_id"] = agent_id
                tc["_sub_agent_id"] = tc.get("start_agent", sub_agent_id)
                tc["_default_test_data"] = default_test_data

                # Filter by tags if specified
                if tags:
                    tc_tags = tc.get("tags", [])
                    if not any(tag in tc_tags for tag in tags):
                        continue

                test_cases.append(tc)

    return test_cases


def get_test_case(name: str, config: Optional[EvalConfig] = None) -> Optional[dict]:
    """Get a single test case by name or prefix.

    Supports exact match or prefix match (e.g., "INT-001" matches "INT-001: Person confirms").
    """
    all_tests = load_test_cases(config=config)

    # Try exact match first
    for tc in all_tests:
        if tc.get("name") == name:
            return tc

    # Try prefix match
    for tc in all_tests:
        tc_name = tc.get("name", "")
        if tc_name.startswith(name):
            return tc

    return None


def load_agent_config() -> dict:
    """Load agent configuration from agent.yaml."""
    config_path = get_agent_dir() / "agent.yaml"

    if not config_path.exists():
        return {}

    return yaml.safe_load(config_path.read_text()) or {}


def get_prompt_info(agent_id: str, version: Optional[str] = None, config: Optional[dict] = None) -> dict:
    """Get prompt file path and raw content for an agent.

    Args:
        agent_id: The sub-agent ID (e.g., "introduction")
        version: Optional version name to apply prompt_version suffix
        config: Optional agent.yaml config dict

    Returns:
        Dict with 'file' (relative path) and 'content' (raw prompt text)
    """
    if config is None:
        config = load_agent_config()

    # Find agent config
    sub_agents = {a["id"]: a for a in config.get("sub_agents", [])}
    agent_cfg = sub_agents.get(agent_id, {})
    instructions = agent_cfg.get("instructions", "")

    if not instructions:
        return {"file": "", "content": ""}

    agent_dir = get_agent_dir()

    # YAML file path
    if "/" in instructions or instructions.endswith(".yaml"):
        prompt_file = agent_dir / instructions

        # Apply prompt_version suffix from version config if specified
        if version:
            eval_cfg = get_config()
            prompt_version = eval_cfg.get_version_prompt_version(version, agent_id)
            if prompt_version:
                # prompts/prompt01_introduction.yaml -> prompts/prompt01_introduction_v2.yaml
                base_path = str(prompt_file)
                if base_path.endswith(".yaml"):
                    versioned_path = base_path.replace(".yaml", f"_{prompt_version}.yaml")
                    versioned_file = Path(versioned_path)
                    if not versioned_file.exists():
                        # STRICT: Raise error if versioned prompt file not found
                        raise ConfigurationError(
                            f"Versioned prompt file not found: {versioned_path}\n"
                            f"Version '{version}' specifies prompt_version='{prompt_version}' for agent '{agent_id}', "
                            f"but the file does not exist."
                        )
                    prompt_file = versioned_file
                    instructions = str(prompt_file.relative_to(agent_dir))

        if prompt_file.exists():
            prompt_data = yaml.safe_load(prompt_file.read_text()) or {}
            raw_content = prompt_data.get("prompt", "")
            return {
                "file": instructions,
                "content": raw_content
            }
        # STRICT: Raise error if base prompt file not found
        raise ConfigurationError(
            f"Prompt file not found: {prompt_file}\n"
            f"Agent '{agent_id}' specifies instructions='{instructions}', but the file does not exist."
        )

    # Function reference
    if instructions.startswith("func:"):
        return {"file": instructions, "content": "(dynamic function)"}

    # Direct text
    return {"file": "(inline)", "content": instructions}


def load_instructions(
    agent_id: str,
    userdata=None,
    config: Optional[dict] = None,
    version: Optional[str] = None,
) -> str:
    """Load and process agent instructions from YAML, function ref, or text.

    Args:
        agent_id: The sub-agent ID (e.g., "introduction")
        userdata: Optional userdata for template variable substitution
        config: Optional agent.yaml config dict (loaded if not provided)
        version: Optional version string for prompt version lookup from eval_config
    """
    if config is None:
        config = load_agent_config()

    # Find agent config
    sub_agents = {a["id"]: a for a in config.get("sub_agents", [])}
    agent_cfg = sub_agents.get(agent_id, {})
    instructions = agent_cfg.get("instructions", "")

    if not instructions:
        return ""

    agent_dir = get_agent_dir()

    # YAML file path
    if "/" in instructions or instructions.endswith(".yaml"):
        prompt_file = agent_dir / instructions

        # Apply prompt_version suffix from version config if specified
        if version:
            eval_cfg = get_config()
            prompt_version = eval_cfg.get_version_prompt_version(version, agent_id)
            if prompt_version:
                # prompts/prompt01_introduction.yaml -> prompts/prompt01_introduction_v2.yaml
                base_path = str(prompt_file)
                if base_path.endswith(".yaml"):
                    versioned_path = base_path.replace(".yaml", f"_{prompt_version}.yaml")
                    versioned_file = Path(versioned_path)
                    if not versioned_file.exists():
                        # STRICT: Raise error if versioned prompt file not found
                        raise ConfigurationError(
                            f"Versioned prompt file not found: {versioned_path}\n"
                            f"Version '{version}' specifies prompt_version='{prompt_version}' for agent '{agent_id}', "
                            f"but the file does not exist."
                        )
                    prompt_file = versioned_file

        if prompt_file.exists():
            prompt_data = yaml.safe_load(prompt_file.read_text()) or {}
            template = prompt_data.get("prompt", "")

            # Use format_instruction if available, otherwise simple substitution
            if _format_instruction is not None:
                return _format_instruction(template, **build_template_variables(userdata, config))
            else:
                variables = build_template_variables(userdata, config)
                for key, value in variables.items():
                    template = template.replace(f"{{{key}}}", str(value))
                return template

        # STRICT: Raise error if base prompt file not found
        raise ConfigurationError(
            f"Prompt file not found: {prompt_file}\n"
            f"Agent '{agent_id}' specifies instructions='{instructions}', but the file does not exist."
        )

    # Function reference (func:module.function)
    if instructions.startswith("func:"):
        func_path = instructions[5:]  # Remove "func:" prefix
        module_name, func_name = func_path.rsplit(".", 1)

        try:
            func = _dynamic_import(module_name, func_name)
            return func(userdata, config.get("variables", {}))
        except (ImportError, AttributeError) as e:
            # STRICT: Raise error if function import fails
            raise ConfigurationError(
                f"Failed to load instruction function: {instructions}\n"
                f"Error: {e}"
            )

    # Direct text with template variable substitution
    if _format_instruction is not None:
        return _format_instruction(instructions, **build_template_variables(userdata, config))
    else:
        variables = build_template_variables(userdata, config)
        result = instructions
        for key, value in variables.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result
