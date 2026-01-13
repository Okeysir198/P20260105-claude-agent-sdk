#!/usr/bin/env python3
"""
Promptfoo Evaluation Runner

Auto-generates promptfooconfig.yaml from testcases/*.yaml and runs evaluation.

Usage:
    cd agents/debt_collection/eval
    python run_eval.py              # Generate config and run
    python run_eval.py --view       # View results in browser
    python run_eval.py --generate-only
"""

import os
import subprocess
import sys
import yaml
from pathlib import Path

from _console import console, print_header, print_success, print_error, print_info


def load_env():
    """Load .env file from backend directory."""
    # eval -> debt_collection -> agents -> livekit-backend
    backend_dir = Path(__file__).parent.parent.parent.parent
    env_file = backend_dir / ".env"

    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    value = value.strip().strip('"').strip("'")
                    os.environ.setdefault(key.strip(), value)
        return True
    return False


load_env()


def load_test_files(testcases_dir: Path) -> list[dict]:
    """Load all test YAML files from the testcases directory."""
    test_files = []

    for yaml_file in sorted(testcases_dir.glob("*.yaml")):
        data = yaml.safe_load(yaml_file.read_text())
        if data and "test_cases" in data:
            test_files.append({
                "file": yaml_file.name,
                "agent_id": data.get("agent_id", "debt_collection"),
                "sub_agent_id": data.get("sub_agent_id"),
                "description": data.get("description", ""),
                "test_cases": data["test_cases"]
            })

    return test_files


def generate_promptfoo_test(test_case: dict, file_info: dict) -> dict:
    """Generate a promptfoo test entry from a test case."""
    name = test_case["name"]
    tags = test_case.get("tags", [])
    sub_agent = file_info.get("sub_agent_id", "")

    description = f"{sub_agent.capitalize()}: {name}" if sub_agent else f"Test: {name}"

    all_assertions = [
        {"type": a["type"], "value": a.get("value", a.get("intent", ""))}
        for turn in test_case.get("turns", [])
        for a in turn.get("assertions", [])
    ]

    return {
        "description": description,
        "vars": {"test_name": name},
        "assert": all_assertions,
        "metadata": {
            "tags": tags,
            "source_file": file_info["file"],
            "sub_agent": sub_agent or "main"
        }
    }


def generate_promptfoo_config(testcases_dir: Path, agent_yaml_path: Path) -> dict:
    """Generate promptfoo config with all versions as providers."""
    config = yaml.safe_load(agent_yaml_path.read_text()) if agent_yaml_path.exists() else {}
    versions = config.get("versions", {})

    # Create a provider for each version
    providers = []
    for version_id in versions.keys():
        providers.append({
            "id": "file://_provider.py",
            "label": version_id,
            "config": {"version": version_id}
        })

    if not providers:
        providers = [{"id": "file://_provider.py", "label": "default"}]

    test_files = load_test_files(testcases_dir)
    tests = [generate_promptfoo_test(tc, fi) for fi in test_files for tc in fi["test_cases"]]

    return {
        "description": f"Agent Evaluation - {config.get('id', 'debt_collection')}",
        "providers": providers,
        "prompts": ["{{test_name}}"],
        "defaultTest": {"options": {"timeout": 60000}},
        "tests": tests,
        "commandLineOptions": {
            "table": True,
            "tableCellMaxLength": 150,
            "verbose": True,
            "progressBar": True
        },
        "outputPath": [
            "results.html",
            "results.json"
        ]
    }


def write_config(config: dict, output_file: Path):
    """Write config to YAML file."""
    def str_representer(dumper, data):
        if '\n' in data:
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
        return dumper.represent_scalar('tag:yaml.org,2002:str', data)

    yaml.add_representer(str, str_representer)

    header = """# Promptfoo Evaluation Config
# AUTO-GENERATED from testcases/*.yaml - DO NOT EDIT MANUALLY
#
# To regenerate: python run_eval.py --generate-only
# Single source of truth: testcases/*.yaml

"""

    with open(output_file, 'w') as f:
        f.write(header)
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print_success(f"Generated: {output_file.name}")
    console.print(f"  [dim]{len(config['tests'])} test cases[/dim]")


def generate_config() -> bool:
    """Generate promptfooconfig.yaml from testcases/*.yaml."""
    script_dir = Path(__file__).parent
    testcases_dir = script_dir / "testcases"
    agent_yaml_path = script_dir.parent / "agent.yaml"
    output_file = script_dir / "promptfooconfig.yaml"

    if not testcases_dir.exists():
        print_error(f"Testcases directory not found: {testcases_dir}")
        return False

    try:
        config = generate_promptfoo_config(testcases_dir, agent_yaml_path)
        write_config(config, output_file)
        return True
    except Exception as e:
        print_error(f"Failed to generate config: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_promptfoo() -> bool:
    """Check if promptfoo is available."""
    try:
        result = subprocess.run(["npx", "promptfoo@latest", "--version"], capture_output=True, text=True, timeout=30)
        return result.returncode == 0
    except Exception:
        return False


def run_evaluation(config_file: Path, verbose: bool = False) -> int:
    """Run promptfoo evaluation."""
    cmd = ["npx", "promptfoo@latest", "eval", "-c", str(config_file)]
    if verbose:
        cmd.append("--verbose")

    print_info(f"Running: {' '.join(cmd)}")
    console.print()

    return subprocess.run(cmd, cwd=str(config_file.parent), env=os.environ.copy()).returncode


def view_results() -> int:
    """Open promptfoo results in browser."""
    return subprocess.run(["npx", "promptfoo@latest", "view"], cwd=str(Path(__file__).parent), env=os.environ.copy()).returncode


def list_configs() -> None:
    """List all available config files."""
    eval_dir = Path(__file__).parent
    configs = list(eval_dir.glob("*.yaml")) + list(eval_dir.glob("*.yml"))

    print("Available configurations:")
    print("-" * 60)

    if not configs:
        print("  No .yaml/.yml files found in eval/ directory")
        return

    for config in configs:
        print(f"  - {config.name}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Promptfoo Evaluation Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_eval.py              # Generate and run
  python run_eval.py --view       # View results
  python run_eval.py --generate-only
  python run_eval.py --list       # List configs
        """
    )
    parser.add_argument("--view", "-v", action="store_true", help="View results in browser")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--check", action="store_true", help="Check promptfoo installation")
    parser.add_argument("--no-generate", action="store_true", help="Skip config generation")
    parser.add_argument("--generate-only", action="store_true", help="Only generate config")
    parser.add_argument("--list", "-l", action="store_true", help="List available configs")

    args = parser.parse_args()
    config_file = Path(__file__).parent / "promptfooconfig.yaml"

    if args.list:
        list_configs()
        sys.exit(0)

    if args.check:
        if check_promptfoo():
            print_success("Promptfoo is available")
            sys.exit(0)
        else:
            print_error("Promptfoo not found. Install with: npm install -g promptfoo")
            sys.exit(1)

    if args.view:
        print_header("Promptfoo Results Viewer")
        sys.exit(view_results())

    if not args.no_generate:
        print_header("Generating Config", "From testcases/*.yaml")
        if not generate_config():
            sys.exit(1)
        console.print()

    if args.generate_only:
        print_success("Config generated successfully")
        sys.exit(0)

    if not config_file.exists():
        print_error(f"Config not found: {config_file}")
        sys.exit(1)

    print_header("Promptfoo Evaluation", f"Config: {config_file.name}")
    returncode = run_evaluation(config_file, args.verbose)

    if returncode == 0:
        console.print()
        print_success("Evaluation complete!")
        print_info("Run 'python run_eval.py --view' to see results")

    sys.exit(returncode)


if __name__ == "__main__":
    main()
