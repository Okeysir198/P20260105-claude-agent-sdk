"""
Generate promptfooconfig.yaml from test cases.

This module auto-generates the promptfoo configuration file from our
test case YAML files. The generated config should NOT be edited manually -
regenerate it using this module.

Usage:
    from eval.promptfoo.config_generator import generate_promptfoo_config

    # Generate with defaults
    config_path = generate_promptfoo_config()

    # Generate with options
    config_path = generate_promptfoo_config(
        versions=["v1", "v2"],
        tags=["unit", "introduction"]
    )
"""

import yaml
from pathlib import Path
from typing import Optional

from ..core.loader import load_test_cases, get_prompt_info
from ..core.config import get_eval_dir, get_config


def _filter_test_cases(
    pattern: Optional[str] = None,
    limit: Optional[int] = None,
    tags: Optional[list[str]] = None,
) -> list[dict]:
    """
    Load and filter test cases by pattern and limit.

    Args:
        pattern: Test code prefix or YAML filename
        limit: Maximum number of tests to return
        tags: Filter by tags

    Returns:
        Filtered list of test cases
    """
    # Determine file filter from pattern
    file_filter = None
    name_prefix = None

    if pattern:
        if pattern.endswith(".yaml"):
            file_filter = pattern
        else:
            name_prefix = pattern

    # Load test cases
    test_cases = load_test_cases(file=file_filter, tags=tags)

    # Filter by name prefix if specified
    if name_prefix:
        test_cases = [tc for tc in test_cases if tc.get("name", "").startswith(name_prefix)]

    # Apply limit
    if limit:
        test_cases = test_cases[:limit]

    return test_cases


def generate_promptfoo_config(
    output_path: Optional[Path] = None,
    pattern: Optional[str] = None,
    limit: Optional[int] = None,
    versions: Optional[list[str]] = None,
    tags: Optional[list[str]] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
) -> Path:
    """
    Generate promptfooconfig.yaml from test cases.

    Args:
        output_path: Where to write config (default: eval/promptfooconfig.yaml)
        pattern: Test code prefix or YAML filename to filter tests
        limit: Maximum number of tests to include
        versions: Prompt versions to test (enables side-by-side comparison)
        tags: Filter tests by tags (e.g., ["unit", "introduction"])
        model: Default LLM model to use
        temperature: Default LLM temperature (0.0-2.0)

    Returns:
        Path to the generated config file
    """
    eval_dir = get_eval_dir()
    output_path = output_path or eval_dir / "promptfooconfig.yaml"

    # Load and filter test cases
    test_cases = _filter_test_cases(pattern=pattern, limit=limit, tags=tags)

    if not test_cases:
        filters = []
        if pattern:
            filters.append(f"pattern={pattern}")
        if tags:
            filters.append(f"tags={tags}")
        if limit:
            filters.append(f"limit={limit}")
        filter_str = ", ".join(filters) if filters else "none"
        raise ValueError(f"No test cases found (filters: {filter_str})")

    # Determine versions to use
    # Priority: explicit versions > active_version from agent.yaml > "default"
    if not versions:
        eval_cfg = get_config()
        active = eval_cfg.get_active_version()
        if active:
            versions = [active]
        else:
            versions = ["default"]

    # Build providers (one per version for comparison) with version metadata
    # Label is simple (v1, v2), config contains full details shown on hover in UI
    eval_cfg = get_config()
    providers = []

    # Collect unique sub_agent_ids from test cases to load their prompts
    sub_agent_ids = set(tc.get("_sub_agent_id", "") for tc in test_cases if tc.get("_sub_agent_id"))

    for version in versions:
        version_cfg = eval_cfg.get_version_config(version)

        # Build provider config with description above model
        provider_config = {"version": version}

        # Add version metadata for hover tooltip in promptfoo UI
        if version_cfg:
            provider_config["description"] = version_cfg.get("description", "")

        # Resolve model: CLI override > version config > agent.yaml default (strict)
        provider_config["model"] = eval_cfg.resolve_model(cli_override=model, version=version)

        # Resolve temperature: CLI override > version config > agent.yaml default (strict)
        provider_config["temperature"] = eval_cfg.resolve_temperature(cli_override=temperature, version=version)

        if version_cfg and version_cfg.get("sub_agents"):
            provider_config["sub_agents"] = version_cfg.get("sub_agents", {})

        # Add version-specific prompt file paths for all sub_agents
        prompts_info = {}
        for sub_agent in eval_cfg.get_all_sub_agents():
            agent_id = sub_agent.get("id", "")
            if agent_id:
                prompt_info = get_prompt_info(agent_id, version=version)
                if prompt_info.get("file"):
                    prompts_info[f"[{agent_id}]"] = prompt_info["file"]
        if prompts_info:
            provider_config["prompts"] = prompts_info

        providers.append({
            "id": "file://promptfoo/provider.py",
            "label": version,  # Simple label (v1, v2)
            "config": provider_config,  # Full details shown on hover
        })

    # Build tests from test cases with clean display info
    tests = []
    for tc in test_cases:
        turns = tc.get("turns", [])
        turn_type = "single_turn" if len(turns) == 1 else f"multi_turn ({len(turns)})"

        # Extract user inputs for display
        user_inputs = [t.get("user_input", "") for t in turns]

        # Extract assertions summary for display
        assertions_summary = []
        for turn in turns:
            for a in turn.get("assertions", []):
                atype = a.get("type", "")
                # Get value from different possible keys
                avalue = a.get("value") or a.get("expected") or a.get("name") or a.get("rubric") or ""
                assertions_summary.append(f"{atype}: {avalue}")

        # Combine all test case info into single variable for clean display
        # Add blank lines between sections: [name + type] [user inputs] [assertions]
        # Each assertion on its own line
        assertions_text = "\n".join(f"  - {a}" for a in assertions_summary)
        test_case_definition = (
            f"Name: {tc['name']}\n"
            f"Type: {turn_type}\n"
            f"\n"
            f"User: {' | '.join(user_inputs)}\n"
            f"\n"
            f"Assert:\n{assertions_text}"
        )

        # Format test_data as readable string
        test_data = tc.get("_default_test_data", {})
        test_data_lines = [f"  {k}: {v}" for k, v in test_data.items()]
        test_data_str = "\n".join(test_data_lines) if test_data_lines else ""

        # Get sub_agent_id for metadata
        sub_agent_id = tc.get("_sub_agent_id", "")

        test_entry = {
            "description": tc.get("name", "Unknown"),
            "vars": {
                "test_case_definition": test_case_definition,  # Contains name, type, user input, assertions
            },
            "assert": [],
            "metadata": {
                "tags": tc.get("tags", []),
                "source_file": tc.get("_source_file", ""),
                "agent_id": tc.get("_agent_id", ""),
                "sub_agent_id": sub_agent_id,
                "test_data": test_data_str,
            },
        }

        # Extract assertions from turns for promptfoo evaluation
        for turn in turns:
            for assertion in turn.get("assertions", []):
                converted = convert_assertion(assertion)
                if converted:
                    test_entry["assert"].append(converted)

        tests.append(test_entry)

    # Build complete config
    config = {
        "description": "LiveKit Voice Agent Evaluation",
        "providers": providers,
        "prompts": ["{{test_case_definition}}"],
        "tests": tests,
        "outputPath": str(eval_dir / "results.json"),
        "defaultTest": {
            "options": {
                "timeout": 60000,  # 60 second timeout per test
            },
        },
    }

    # Write config with nice formatting
    yaml_content = yaml.dump(
        config,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=120,
    )

    # Add header comment
    header = """# ============================================
# PROMPTFOO CONFIGURATION (AUTO-GENERATED)
# ============================================
# DO NOT EDIT MANUALLY - regenerate with:
#   python run_promptfoo.py generate
# ============================================

"""
    output_path.write_text(header + yaml_content)

    return output_path


def convert_assertion(assertion: dict) -> Optional[dict]:
    """
    Convert our assertion format to promptfoo format.

    Args:
        assertion: Our assertion dict with 'type' and other fields

    Returns:
        Promptfoo assertion dict, or None if unsupported
    """
    atype = assertion.get("type")

    if atype == "contains":
        return {
            "type": "contains",
            "value": assertion.get("expected", ""),
        }

    elif atype == "not_contains":
        return {
            "type": "not-contains",
            "value": assertion.get("expected", ""),
        }

    elif atype == "contains_function_call":
        # Check if a specific tool was called
        # Support both 'name' and 'value' keys for tool name
        # Provider embeds tool calls as [TOOL:name] tags in output
        tool_name = assertion.get("name") or assertion.get("value", "")
        return {
            "type": "contains",
            "value": f"[TOOL:{tool_name}]",
        }

    elif atype == "llm_rubric":
        # Use LLM to evaluate response quality
        rubric = assertion.get("rubric") or assertion.get("expected", "")
        return {
            "type": "llm-rubric",
            "value": rubric,
        }

    elif atype == "matches":
        # Regex pattern matching
        return {
            "type": "regex",
            "value": assertion.get("pattern", ""),
        }

    elif atype == "equals":
        return {
            "type": "equals",
            "value": assertion.get("expected", ""),
        }

    else:
        # Default to contains for unknown types
        if "expected" in assertion:
            return {
                "type": "contains",
                "value": str(assertion["expected"]),
            }
        return None


def get_test_stats(
    pattern: Optional[str] = None,
    limit: Optional[int] = None,
    tags: Optional[list[str]] = None,
) -> dict:
    """
    Get statistics about available test cases.

    Args:
        pattern: Test code prefix or YAML filename
        limit: Maximum number of tests
        tags: Filter by tags

    Returns:
        Dict with counts and tag breakdown
    """
    test_cases = _filter_test_cases(pattern=pattern, limit=limit, tags=tags)

    # Count by source file
    by_file = {}
    all_tags = set()

    for tc in test_cases:
        source = tc.get("_source_file", "unknown")
        by_file[source] = by_file.get(source, 0) + 1
        all_tags.update(tc.get("tags", []))

    return {
        "total": len(test_cases),
        "by_file": by_file,
        "all_tags": sorted(all_tags),
    }
