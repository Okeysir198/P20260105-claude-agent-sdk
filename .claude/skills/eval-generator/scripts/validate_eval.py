#!/usr/bin/env python3
"""Validate a generated eval folder for completeness and correctness."""

import argparse
import json
import sys
from pathlib import Path
from typing import NamedTuple

import yaml

VALID_ASSERTION_TYPES = {
    "contains", "not_contains", "contains_any", "contains_all",
    "equals", "matches", "contains_function_call", "llm_rubric",
}

REQUIRED_CORE_FILES = ["config.py", "loader.py", "session.py", "events.py", "userdata.py"]
REQUIRED_WORKFLOW_FILES = ["test_workflow.py", "eval_workflow.py", "simulation_workflow.py", "batch_workflow.py"]
REQUIRED_SCHEMA_FILES = ["models.py", "test_case.py"]


class Issue(NamedTuple):
    level: str  # "error", "warning"
    message: str


def check_structure(eval_dir: Path) -> list[Issue]:
    """Verify all required files/folders exist."""
    issues = []

    for f in REQUIRED_CORE_FILES:
        if not (eval_dir / "core" / f).exists():
            issues.append(Issue("error", f"Missing core/{f}"))

    for f in REQUIRED_WORKFLOW_FILES:
        if not (eval_dir / "workflows" / f).exists():
            issues.append(Issue("error", f"Missing workflows/{f}"))

    for f in REQUIRED_SCHEMA_FILES:
        if not (eval_dir / "schemas" / f).exists():
            issues.append(Issue("error", f"Missing schemas/{f}"))

    if not (eval_dir / "eval_config.yaml").exists():
        issues.append(Issue("error", "Missing eval_config.yaml"))

    testcases_dir = eval_dir / "testcases"
    if not testcases_dir.exists():
        issues.append(Issue("error", "Missing testcases/ directory"))
    elif not list(testcases_dir.glob("*.yaml")):
        issues.append(Issue("error", "No .yaml files in testcases/"))

    return issues


def check_config(eval_dir: Path) -> tuple[list[Issue], list[str]]:
    """Validate eval_config.yaml and return agent_ids."""
    config_path = eval_dir / "eval_config.yaml"
    if not config_path.exists():
        return [Issue("error", "eval_config.yaml not found")], []

    issues = []
    try:
        config = yaml.safe_load(config_path.read_text()) or {}
    except yaml.YAMLError as e:
        return [Issue("error", f"Invalid YAML in eval_config.yaml: {e}")], []

    agent_ids = config.get("agent_ids", [])
    if not agent_ids:
        issues.append(Issue("warning", "eval_config.yaml has no agent_ids"))

    if "imports" not in config:
        issues.append(Issue("warning", "eval_config.yaml has no imports section"))

    return issues, agent_ids


def check_test_case(file_path: Path, config_agent_ids: list[str], known_tools: set[str] | None) -> tuple[list[Issue], int]:
    """Validate a single test case file. Returns issues and test count."""
    issues = []
    test_count = 0

    try:
        data = yaml.safe_load(file_path.read_text()) or {}
    except yaml.YAMLError as e:
        return [Issue("error", f"{file_path.name}: Invalid YAML - {e}")], 0

    # Required top-level fields
    if "test_cases" not in data:
        issues.append(Issue("error", f"{file_path.name}: Missing 'test_cases' field"))
        return issues, 0

    sub_agent_id = data.get("sub_agent_id") or data.get("agent_id", "default")
    if config_agent_ids and sub_agent_id not in config_agent_ids and sub_agent_id != "default":
        issues.append(Issue("warning", f"{file_path.name}: sub_agent_id '{sub_agent_id}' not in config agent_ids"))

    test_cases = data.get("test_cases", [])
    if not test_cases:
        issues.append(Issue("warning", f"{file_path.name}: Empty test_cases list"))
        return issues, 0

    for i, tc in enumerate(test_cases):
        test_count += 1
        tc_loc = f"{file_path.name}[{i}]"

        if not tc.get("name"):
            issues.append(Issue("error", f"{tc_loc}: Missing 'name'"))

        turns = tc.get("turns", [])
        if not turns:
            issues.append(Issue("error", f"{tc_loc}: Missing or empty 'turns'"))
            continue

        for j, turn in enumerate(turns):
            turn_loc = f"{tc_loc}.turns[{j}]"

            if not turn.get("user_input"):
                issues.append(Issue("error", f"{turn_loc}: Missing 'user_input'"))

            for k, assertion in enumerate(turn.get("assertions", [])):
                assert_loc = f"{turn_loc}.assertions[{k}]"
                atype = assertion.get("type", "").replace("-", "_").lower()

                if atype not in VALID_ASSERTION_TYPES:
                    issues.append(Issue("error", f"{assert_loc}: Invalid assertion type '{assertion.get('type')}'"))
                elif atype == "llm_rubric":
                    if not assertion.get("rubric") and not assertion.get("value"):
                        issues.append(Issue("warning", f"{assert_loc}: llm_rubric has empty rubric"))
                elif atype == "contains_function_call":
                    func_name = assertion.get("value")
                    if not func_name:
                        issues.append(Issue("error", f"{assert_loc}: contains_function_call missing 'value'"))
                    elif known_tools and func_name not in known_tools:
                        issues.append(Issue("warning", f"{assert_loc}: Tool '{func_name}' not in analysis"))

    return issues, test_count


def validate_eval(eval_dir: Path, strict: bool = False, analysis_path: Path | None = None) -> int:
    """Run all validation checks. Returns exit code (0=success, 1=failure)."""
    all_issues: list[Issue] = []
    total_tests = 0

    # Load known tools from analysis if provided
    known_tools: set[str] | None = None
    if analysis_path and analysis_path.exists():
        try:
            analysis = json.loads(analysis_path.read_text())
            known_tools = set(analysis.get("tools", {}).keys())
        except (json.JSONDecodeError, KeyError):
            pass

    # Structure check
    structure_issues = check_structure(eval_dir)
    all_issues.extend(structure_issues)
    structure_ok = not any(i.level == "error" for i in structure_issues)
    print(f"{'[ok]' if structure_ok else '[FAIL]'} Structure: {'All required files present' if structure_ok else 'Missing files'}")

    # Config check
    config_issues, agent_ids = check_config(eval_dir)
    all_issues.extend(config_issues)
    config_ok = not any(i.level == "error" for i in config_issues)
    print(f"{'[ok]' if config_ok else '[FAIL]'} Config: {'eval_config.yaml valid' if config_ok else 'Config errors'}")

    # Test case checks
    testcases_dir = eval_dir / "testcases"
    tc_files = list(testcases_dir.glob("*.yaml")) if testcases_dir.exists() else []
    tc_errors = 0

    for tc_file in tc_files:
        issues, count = check_test_case(tc_file, agent_ids, known_tools)
        all_issues.extend(issues)
        total_tests += count
        if any(i.level == "error" for i in issues):
            tc_errors += 1

    tc_ok = tc_errors == 0
    print(f"{'[ok]' if tc_ok else '[FAIL]'} Test Cases: {len(tc_files)} files validated ({total_tests} tests)")

    # Print all issues
    errors = [i for i in all_issues if i.level == "error"]
    warnings = [i for i in all_issues if i.level == "warning"]

    for w in warnings:
        print(f"[WARN] {w.message}")
    for e in errors:
        print(f"[ERROR] {e.message}")

    # Summary
    effective_errors = len(errors) + (len(warnings) if strict else 0)
    print(f"\nSummary: {len(all_issues) - len(errors) - len(warnings)} passed, {len(warnings)} warning(s), {len(errors)} error(s)")

    return 1 if effective_errors > 0 else 0


def main():
    parser = argparse.ArgumentParser(description="Validate eval folder structure and test cases")
    parser.add_argument("eval_dir", type=Path, help="Path to eval directory")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    parser.add_argument("--analysis", type=Path, help="Path to analysis.json for tool cross-reference")
    args = parser.parse_args()

    if not args.eval_dir.is_dir():
        print(f"Error: {args.eval_dir} is not a directory")
        sys.exit(1)

    sys.exit(validate_eval(args.eval_dir, args.strict, args.analysis))


if __name__ == "__main__":
    main()
