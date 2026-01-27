#!/usr/bin/env python3
"""
Agent Architecture Analyzer for LLM-Powered Test Case Generation.

Extracts agent structure from:
- agent.yaml: sub_agents, tools, handoffs, versions, LLM config
- prompts/*.yaml: full prompt content and expected behaviors
- sub_agents/*.py: agent classes, tool registrations (via AST)
- tools/*.py: tool functions, docstrings, parameters (via AST)
- shared_state.py: UserData dataclass fields (via AST)

Output: JSON structure suitable for LLM test case generation.
"""

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any

import yaml


def parse_agent_yaml(agent_dir: Path) -> dict[str, Any]:
    """Parse agent.yaml to extract configuration."""
    yaml_path = agent_dir / "agent.yaml"
    if not yaml_path.exists():
        return {}

    with open(yaml_path) as f:
        return yaml.safe_load(f) or {}


def parse_prompt_file(prompt_path: Path) -> dict[str, Any]:
    """Parse a single prompt YAML file."""
    if not prompt_path.exists():
        return {}

    with open(prompt_path) as f:
        data = yaml.safe_load(f) or {}

    return {
        "version": data.get("version", "1.0"),
        "agent_id": data.get("agent_id"),
        "metadata": data.get("metadata", {}),
        "prompt_content": data.get("prompt", ""),
    }


def extract_tool_info_from_ast(file_path: Path) -> list[dict[str, Any]]:
    """Extract tool functions from Python file using AST."""
    if not file_path.exists():
        return []

    with open(file_path) as f:
        source = f.read()

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    tools = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.AsyncFunctionDef):
            continue

        # Check for @function_tool() decorator
        has_function_tool = any(
            (isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "function_tool")
            or (isinstance(d, ast.Name) and d.id == "function_tool")
            for d in node.decorator_list
        )
        if not has_function_tool:
            continue

        # Extract docstring
        docstring = ast.get_docstring(node) or ""

        # Extract parameters (excluding 'context' and 'self')
        params = []
        for arg in node.args.args:
            if arg.arg in ("context", "self"):
                continue

            param_info = {"name": arg.arg, "type": "Any"}

            # Try to extract type annotation
            if arg.annotation:
                param_info["type"] = _annotation_to_str(arg.annotation)

            # Try to extract Field description from Annotated
            if isinstance(arg.annotation, ast.Subscript):
                if isinstance(arg.annotation.value, ast.Name) and arg.annotation.value.id == "Annotated":
                    desc = _extract_field_description(arg.annotation)
                    if desc:
                        param_info["description"] = desc

            params.append(param_info)

        tools.append({
            "name": node.name,
            "description": docstring.split("\n\n")[0].strip() if docstring else "",
            "full_docstring": docstring,
            "parameters": params,
        })

    return tools


def _annotation_to_str(annotation: ast.AST) -> str:
    """Convert AST annotation to string representation."""
    if isinstance(annotation, ast.Name):
        return annotation.id
    if isinstance(annotation, ast.Constant):
        return str(annotation.value)
    if isinstance(annotation, ast.Subscript):
        if isinstance(annotation.value, ast.Name):
            if annotation.value.id == "Annotated":
                # Return the base type
                if isinstance(annotation.slice, ast.Tuple) and annotation.slice.elts:
                    return _annotation_to_str(annotation.slice.elts[0])
            return annotation.value.id
    return "Any"


def _extract_field_description(annotation: ast.Subscript) -> str | None:
    """Extract Field description from Annotated[type, Field(...)]."""
    if not isinstance(annotation.slice, ast.Tuple):
        return None

    for elt in annotation.slice.elts[1:]:
        if isinstance(elt, ast.Call) and isinstance(elt.func, ast.Name) and elt.func.id == "Field":
            for kw in elt.keywords:
                if kw.arg == "description" and isinstance(kw.value, ast.Constant):
                    return str(kw.value.value)
    return None


def extract_dataclass_fields(file_path: Path, class_name: str = "UserData") -> dict[str, str]:
    """Extract dataclass field names and types from Python file."""
    if not file_path.exists():
        return {}

    with open(file_path) as f:
        source = f.read()

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue

        fields = {}
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                field_name = item.target.id
                field_type = _annotation_to_str(item.annotation)
                fields[field_name] = field_type
        return fields

    return {}


def extract_agent_classes(sub_agents_dir: Path) -> list[dict[str, Any]]:
    """Extract agent class info from sub_agents/*.py files."""
    agents = []

    for py_file in sub_agents_dir.glob("agent*.py"):
        with open(py_file) as f:
            source = f.read()

        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        module_docstring = ast.get_docstring(tree) or ""

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            # Check if inherits from BaseAgent or Agent
            is_agent = any(
                (isinstance(b, ast.Name) and b.id in ("BaseAgent", "Agent"))
                or (isinstance(b, ast.Attribute) and b.attr in ("BaseAgent", "Agent"))
                for b in node.bases
            )
            if not is_agent:
                continue

            agents.append({
                "class_name": node.name,
                "file": py_file.name,
                "docstring": ast.get_docstring(node) or "",
                "module_docstring": module_docstring,
            })

    return agents


def build_sub_agent_analysis(
    agent_config: dict[str, Any],
    prompts_dir: Path,
    tools_dir: Path,
    handoffs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build sub-agent analysis combining config, prompts, and tools."""
    sub_agents_config = agent_config.get("sub_agents", [])

    # Pre-load all tools from tool files
    all_tools = {}
    for tool_file in tools_dir.glob("tool*.py"):
        for tool in extract_tool_info_from_ast(tool_file):
            all_tools[tool["name"]] = tool

    # Also check common_tools.py
    common_tools_path = tools_dir / "common_tools.py"
    for tool in extract_tool_info_from_ast(common_tools_path):
        all_tools[tool["name"]] = tool

    results = []
    for sub_agent in sub_agents_config:
        agent_id = sub_agent.get("id", "")
        instructions = sub_agent.get("instructions", "")

        # Load prompt content
        prompt_data = {}
        if instructions.startswith("prompts/") and instructions.endswith(".yaml"):
            prompt_path = prompts_dir.parent / instructions
            prompt_data = parse_prompt_file(prompt_path)

        # Get tools for this agent
        tool_names = sub_agent.get("tools", [])
        tools = [all_tools.get(name, {"name": name, "description": "", "parameters": []}) for name in tool_names]

        # Find handoff targets
        handoffs_to = [h["target"] for h in handoffs if h.get("source") == agent_id]

        # Extract expected behaviors from prompt
        expected_behaviors = _extract_expected_behaviors(prompt_data.get("prompt_content", ""))

        results.append({
            "id": agent_id,
            "name": sub_agent.get("name", ""),
            "description": sub_agent.get("description", ""),
            "prompt_content": prompt_data.get("prompt_content", ""),
            "prompt_metadata": prompt_data.get("metadata", {}),
            "tools": tools,
            "handoffs_to": handoffs_to,
            "expected_behaviors": expected_behaviors,
        })

    return results


def _extract_expected_behaviors(prompt_content: str) -> list[str]:
    """Extract expected behaviors from prompt content."""
    behaviors = []
    lines = prompt_content.split("\n")

    for line in lines:
        line = line.strip()
        # Look for behavioral directives
        if line.startswith("- ") and any(kw in line.lower() for kw in ["if", "when", "never", "always", "must"]):
            behaviors.append(line[2:].strip())
        # Look for response handling sections
        if "call " in line.lower() and "()" in line:
            behaviors.append(line.lstrip("- ").strip())

    return behaviors[:10]  # Limit to 10 most relevant


def extract_sample_userdata(agent_dir: Path) -> dict[str, Any]:
    """Extract sample userdata from shared_state.py get_test_debtor function."""
    shared_state_path = agent_dir / "shared_state.py"
    if not shared_state_path.exists():
        return {}

    with open(shared_state_path) as f:
        source = f.read()

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "get_test_debtor":
            # Try to find and evaluate the return dict
            for stmt in ast.walk(node):
                if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Dict):
                    try:
                        # Safe evaluation of literal dict
                        return ast.literal_eval(ast.unparse(stmt.value))
                    except (ValueError, SyntaxError):
                        pass
    return {}


def analyze_agent(agent_dir: Path) -> dict[str, Any]:
    """Perform full analysis of agent directory."""
    agent_config = parse_agent_yaml(agent_dir)

    # Derive agent identity
    agent_id = agent_config.get("id", agent_dir.name)
    name = agent_config.get("name", "")
    description = agent_config.get("description", "")

    # Extract domain from description
    domain = _infer_domain(description, name)

    # Parse handoffs
    handoffs = agent_config.get("handoffs", [])

    # Build sub-agent analysis
    prompts_dir = agent_dir / "prompts"
    tools_dir = agent_dir / "tools"
    sub_agents = build_sub_agent_analysis(agent_config, prompts_dir, tools_dir, handoffs)

    # Extract all unique tools
    all_tools = {}
    for tool_file in tools_dir.glob("*.py"):
        for tool in extract_tool_info_from_ast(tool_file):
            all_tools[tool["name"]] = tool

    # Extract UserData fields from shared_state.py
    shared_state_path = agent_dir / "shared_state.py"
    userdata_fields = extract_dataclass_fields(shared_state_path, "UserData")

    # Get sample userdata
    sample_userdata = extract_sample_userdata(agent_dir)

    # Extract versions config
    versions = agent_config.get("versions", {})
    active_version = agent_config.get("active_version")

    # LLM config
    llm_config = agent_config.get("llm", {})

    return {
        "agent_id": agent_id,
        "name": name,
        "domain": domain,
        "purpose": description,
        "llm_config": llm_config,
        "sub_agents": sub_agents,
        "tools": list(all_tools.values()),
        "handoffs": handoffs,
        "userdata_fields": userdata_fields,
        "sample_userdata": sample_userdata,
        "versions": versions,
        "active_version": active_version,
    }


def _infer_domain(description: str, name: str) -> str:
    """Infer domain from agent description or name."""
    text = (description + " " + name).lower()

    domains = {
        "debt collection": ["debt", "collection", "payment", "overdue"],
        "customer service": ["customer", "service", "support", "help"],
        "sales": ["sales", "selling", "purchase", "buy"],
        "appointment": ["appointment", "booking", "schedule"],
        "survey": ["survey", "feedback", "questionnaire"],
    }

    for domain, keywords in domains.items():
        if any(kw in text for kw in keywords):
            return domain

    return "general"


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze agent architecture for LLM test case generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/analyze_agent.py /path/to/agent -o analysis.json
  python scripts/analyze_agent.py /path/to/agent  # outputs to stdout
        """,
    )
    parser.add_argument("agent_path", type=Path, help="Path to agent directory")
    parser.add_argument("-o", "--output", type=Path, help="Output JSON file (default: stdout)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")

    args = parser.parse_args()

    agent_dir = args.agent_path.resolve()
    if not agent_dir.is_dir():
        print(f"Error: {agent_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    analysis = analyze_agent(agent_dir)

    indent = 2 if args.pretty or args.output else None
    json_output = json.dumps(analysis, indent=indent, default=str)

    if args.output:
        args.output.write_text(json_output)
        print(f"Analysis written to {args.output}", file=sys.stderr)
    else:
        print(json_output)


if __name__ == "__main__":
    main()
