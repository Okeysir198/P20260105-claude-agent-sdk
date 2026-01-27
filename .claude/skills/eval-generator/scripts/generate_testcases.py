#!/usr/bin/env python3
"""Generate test cases from agent analysis using Claude API.

This script takes an analysis JSON file and generates test case YAML files
for each sub-agent plus E2E critical path tests.

Usage:
    python scripts/generate_testcases.py analysis.json /path/to/agent/eval \
        --model claude-sonnet-4-20250514 \
        --streaming \
        --max-concurrent 5
"""

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncGenerator

import anthropic
import yaml


@dataclass
class GenerationEvent:
    """Event emitted during test case generation."""
    type: str
    agent_id: str = ""
    subagent_id: str = ""
    test_count: int = 0
    total_tests: int = 0
    files: list[str] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        result = {"type": self.type}
        if self.agent_id:
            result["agent_id"] = self.agent_id
        if self.subagent_id:
            result["subagent_id"] = self.subagent_id
        if self.test_count:
            result["test_count"] = self.test_count
        if self.total_tests:
            result["total_tests"] = self.total_tests
        if self.files:
            result["files"] = self.files
        if self.error:
            result["error"] = self.error
        return result


SUBAGENT_PROMPT = """You are an expert QA engineer generating test cases for a voice AI agent sub-component.

## Context

Agent: {agent_id}
Domain: {domain}
Purpose: {agent_purpose}

## Sub-Agent Under Test: {subagent_id}

Purpose: {subagent_purpose}
Prompts/Instructions:
{subagent_prompts}

Available Tools:
{subagent_tools}

## Test Generation Requirements

Generate comprehensive test cases in YAML format for this sub-agent:

1. **Tool Tests** (3-5 per tool):
   - Happy path: Normal expected usage
   - Edge case: Boundary conditions, unusual but valid inputs
   - Negative: Invalid inputs, error conditions

2. **Behavior Tests** (2-3 total):
   - Verify agent follows instructions from prompts
   - Test conversational flow and tone

## Assertion Types Available

- `contains_function_call`: Verify a tool was called (value: "tool_name")
- `llm_rubric`: LLM evaluates response quality (value: "Agent should...")
- `contains`: Check response contains text (value: "keyword")
- `not_contains`: Ensure response excludes text (value: "forbidden_word")
- `contains_any`: Response contains at least one (value: ["opt1", "opt2"])
- `contains_all`: Response contains all (value: ["req1", "req2"])

## Naming Convention

Use 3-letter prefix derived from sub-agent name:
- introduction -> INT
- verification -> VER
- negotiation -> NEG
- confirmation -> CNF
- farewell -> FAR

Test name format: "{PREFIX}-{NNN}: {Description}"

## Output Format

Output ONLY valid YAML, no explanations. Follow this structure:

```yaml
agent_id: {agent_id}
sub_agent_id: {subagent_id}
description: "Tests for {subagent_id} - {brief_purpose}"

default_test_data:
  full_name: "Test User"
  user_id: "U00001"
  # Add relevant domain fields

test_cases:
  - name: "XXX-001: Happy path scenario"
    test_type: single_turn
    tags: [unit, {subagent_id}, happy-path]
    turns:
      - user_input: "User speech here"
        assertions:
          - type: contains_function_call
            value: "expected_tool"
```

Generate the test cases now:"""


E2E_PROMPT = """You are an expert QA engineer generating end-to-end critical path tests for a voice AI agent.

## Agent Overview

Agent ID: {agent_id}
Domain: {domain}
Purpose: {agent_purpose}

## Sub-Agents and Flow

{subagent_summary}

## Workflow Transitions

{transitions}

## Test Generation Requirements

Generate E2E tests covering critical user journeys:

1. **Happy Path Flow** (1-2 tests):
   - Complete successful workflow from start to finish
   - Test typical user journey

2. **Alternative Paths** (1-2 tests):
   - User takes different valid paths
   - Different decision branches

3. **Recovery Flow** (1 test):
   - User provides incorrect info initially
   - Agent recovers gracefully

## Assertion Types

- `contains_function_call`: Verify tool invocation
- `llm_rubric`: Semantic behavior check
- `contains`: Text presence check
- `not_contains`: Text absence check
- `contains_any`: At least one of list
- `contains_all`: All items in list

## Output Format

Output ONLY valid YAML:

```yaml
agent_id: {agent_id}
sub_agent_id: e2e_critical
description: "Critical E2E workflow tests"

default_test_data:
  full_name: "Test User"
  user_id: "U00001"
  # Domain-specific fields

test_cases:
  - name: "E2E-001: Complete happy path"
    test_type: multi_turn
    tags: [critical, e2e, integration]
    turns:
      - user_input: "First user message"
        assertions:
          - type: llm_rubric
            value: "Agent should greet and begin flow"
      - user_input: "Second message"
        assertions:
          - type: contains_function_call
            value: "expected_tool"
```

Generate E2E tests now:"""


class TestCaseGenerator:
    """Generate test cases using Claude API."""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        """Initialize with specified model.

        Args:
            model: Claude model to use for generation.
        """
        self.client = anthropic.Anthropic()
        self.model = model

    def _format_tools(self, tools: list[dict]) -> str:
        """Format tool definitions for prompt."""
        if not tools:
            return "No tools defined"

        lines = []
        for tool in tools:
            name = tool.get("name", "unknown")
            desc = tool.get("description", "No description")
            params = tool.get("parameters", {})
            lines.append(f"- **{name}**: {desc}")
            if params:
                lines.append(f"  Parameters: {json.dumps(params, indent=2)}")
        return "\n".join(lines)

    def _format_prompts(self, prompts: list[dict]) -> str:
        """Format prompt definitions for context."""
        if not prompts:
            return "No prompts defined"

        lines = []
        for p in prompts:
            name = p.get("name", p.get("id", "unnamed"))
            content = p.get("content", p.get("text", ""))
            # Truncate long prompts
            if len(content) > 500:
                content = content[:500] + "..."
            lines.append(f"### {name}\n{content}")
        return "\n\n".join(lines)

    def _get_prefix(self, subagent_id: str) -> str:
        """Generate 3-letter prefix from sub-agent ID."""
        # Common mappings
        prefix_map = {
            "introduction": "INT",
            "verification": "VER",
            "negotiation": "NEG",
            "confirmation": "CNF",
            "farewell": "FAR",
            "greeting": "GRT",
            "triage": "TRI",
            "resolution": "RES",
            "escalation": "ESC",
            "closing": "CLS",
        }
        lower_id = subagent_id.lower()
        if lower_id in prefix_map:
            return prefix_map[lower_id]
        # Default: first 3 uppercase letters
        return subagent_id[:3].upper()

    async def generate_for_subagent(
        self, sub_agent: dict, analysis: dict
    ) -> str:
        """Generate test cases YAML for a single sub-agent.

        Args:
            sub_agent: Sub-agent definition with id, purpose, tools, prompts.
            analysis: Full agent analysis for context.

        Returns:
            Generated YAML string.
        """
        agent_id = analysis.get("agent_id", "unknown")
        domain = analysis.get("domain", "general")
        agent_purpose = analysis.get("purpose", "Voice AI agent")

        subagent_id = sub_agent.get("id", sub_agent.get("name", "unknown"))
        subagent_purpose = sub_agent.get("purpose", sub_agent.get("description", ""))
        tools = sub_agent.get("tools", [])
        prompts = sub_agent.get("prompts", [])

        prompt = SUBAGENT_PROMPT.format(
            agent_id=agent_id,
            domain=domain,
            agent_purpose=agent_purpose,
            subagent_id=subagent_id,
            subagent_purpose=subagent_purpose,
            subagent_tools=self._format_tools(tools),
            subagent_prompts=self._format_prompts(prompts),
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        return self._extract_yaml(response.content[0].text)

    async def generate_e2e(self, analysis: dict) -> str:
        """Generate E2E critical path tests.

        Args:
            analysis: Full agent analysis.

        Returns:
            Generated YAML string.
        """
        agent_id = analysis.get("agent_id", "unknown")
        domain = analysis.get("domain", "general")
        agent_purpose = analysis.get("purpose", "Voice AI agent")
        sub_agents = analysis.get("sub_agents", [])
        transitions = analysis.get("transitions", analysis.get("workflow", {}))

        # Summarize sub-agents
        summary_lines = []
        for idx, sa in enumerate(sub_agents, 1):
            sa_id = sa.get("id", sa.get("name", f"agent{idx}"))
            sa_purpose = sa.get("purpose", sa.get("description", ""))
            summary_lines.append(f"{idx}. **{sa_id}**: {sa_purpose}")
        subagent_summary = "\n".join(summary_lines) if summary_lines else "No sub-agents defined"

        # Format transitions
        if isinstance(transitions, dict):
            transitions_str = yaml.dump(transitions, default_flow_style=False)
        elif isinstance(transitions, list):
            transitions_str = "\n".join(f"- {t}" for t in transitions)
        else:
            transitions_str = str(transitions) if transitions else "Linear flow through sub-agents"

        prompt = E2E_PROMPT.format(
            agent_id=agent_id,
            domain=domain,
            agent_purpose=agent_purpose,
            subagent_summary=subagent_summary,
            transitions=transitions_str,
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        return self._extract_yaml(response.content[0].text)

    def _extract_yaml(self, text: str) -> str:
        """Extract YAML from response, handling code blocks."""
        # Remove markdown code fences if present
        if "```yaml" in text:
            start = text.find("```yaml") + 7
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()
        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()
        return text.strip()

    def _count_tests(self, yaml_content: str) -> int:
        """Count test cases in YAML content."""
        try:
            data = yaml.safe_load(yaml_content)
            return len(data.get("test_cases", []))
        except yaml.YAMLError:
            return 0

    async def astream_generate(
        self, analysis: dict
    ) -> AsyncGenerator[GenerationEvent, None]:
        """Stream generation with progress events.

        Args:
            analysis: Agent analysis dictionary.

        Yields:
            GenerationEvent objects for progress tracking.
        """
        agent_id = analysis.get("agent_id", "unknown")
        sub_agents = analysis.get("sub_agents", [])
        files_created = []
        total_tests = 0

        yield GenerationEvent(type="started", agent_id=agent_id)

        # Generate for each sub-agent sequentially for streaming
        for idx, sub_agent in enumerate(sub_agents, 1):
            subagent_id = sub_agent.get("id", sub_agent.get("name", f"agent{idx}"))
            yield GenerationEvent(
                type="subagent_start",
                agent_id=agent_id,
                subagent_id=subagent_id,
            )

            try:
                yaml_content = await self.generate_for_subagent(sub_agent, analysis)
                test_count = self._count_tests(yaml_content)
                total_tests += test_count

                filename = f"agent{idx:02d}_{subagent_id}.yaml"
                files_created.append(filename)

                # Store content for later writing
                sub_agent["_generated_yaml"] = yaml_content
                sub_agent["_filename"] = filename

                yield GenerationEvent(
                    type="subagent_complete",
                    agent_id=agent_id,
                    subagent_id=subagent_id,
                    test_count=test_count,
                )
            except Exception as e:
                yield GenerationEvent(
                    type="error",
                    agent_id=agent_id,
                    subagent_id=subagent_id,
                    error=str(e),
                )

        # Generate E2E tests
        yield GenerationEvent(type="e2e_start", agent_id=agent_id)

        try:
            e2e_yaml = await self.generate_e2e(analysis)
            e2e_test_count = self._count_tests(e2e_yaml)
            total_tests += e2e_test_count
            files_created.append("e2e_critical.yaml")

            # Store for later writing
            analysis["_e2e_yaml"] = e2e_yaml
        except Exception as e:
            yield GenerationEvent(
                type="error",
                agent_id=agent_id,
                subagent_id="e2e",
                error=str(e),
            )

        yield GenerationEvent(
            type="completed",
            agent_id=agent_id,
            total_tests=total_tests,
            files=files_created,
        )

    async def batch_generate(
        self, analysis: dict, max_concurrent: int = 5
    ) -> tuple[dict[str, str], int]:
        """Generate all sub-agents in parallel.

        Args:
            analysis: Agent analysis dictionary.
            max_concurrent: Maximum concurrent API calls.

        Returns:
            Tuple of (filename -> yaml_content dict, total_test_count).
        """
        sub_agents = analysis.get("sub_agents", [])
        results: dict[str, str] = {}
        total_tests = 0

        semaphore = asyncio.Semaphore(max_concurrent)

        async def generate_one(idx: int, sub_agent: dict) -> tuple[str, str, int]:
            async with semaphore:
                subagent_id = sub_agent.get("id", sub_agent.get("name", f"agent{idx}"))
                yaml_content = await self.generate_for_subagent(sub_agent, analysis)
                filename = f"agent{idx:02d}_{subagent_id}.yaml"
                test_count = self._count_tests(yaml_content)
                return filename, yaml_content, test_count

        # Generate sub-agent tests in parallel
        tasks = [
            generate_one(idx, sa)
            for idx, sa in enumerate(sub_agents, 1)
        ]
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for result in completed:
            if isinstance(result, Exception):
                print(f"Error: {result}", file=sys.stderr)
                continue
            filename, yaml_content, test_count = result
            results[filename] = yaml_content
            total_tests += test_count

        # Generate E2E tests
        e2e_yaml = await self.generate_e2e(analysis)
        results["e2e_critical.yaml"] = e2e_yaml
        total_tests += self._count_tests(e2e_yaml)

        return results, total_tests


def write_testcases(
    output_dir: Path,
    results: dict[str, str],
) -> list[str]:
    """Write generated test cases to files.

    Args:
        output_dir: Directory to write files (eval/testcases/).
        results: Dict mapping filename to YAML content.

    Returns:
        List of created file paths.
    """
    testcases_dir = output_dir / "testcases"
    testcases_dir.mkdir(parents=True, exist_ok=True)

    created_files = []
    for filename, content in results.items():
        filepath = testcases_dir / filename
        filepath.write_text(content)
        created_files.append(str(filepath))

    return created_files


async def run_streaming(
    generator: TestCaseGenerator,
    analysis: dict,
    output_dir: Path,
) -> int:
    """Run generation with streaming output.

    Args:
        generator: TestCaseGenerator instance.
        analysis: Agent analysis dictionary.
        output_dir: Output directory for files.

    Returns:
        Total test count.
    """
    results: dict[str, str] = {}
    total_tests = 0

    async for event in generator.astream_generate(analysis):
        # Print event as JSON
        print(json.dumps(event.to_dict()))

        if event.type == "subagent_complete":
            # Find sub-agent and get generated content
            for sa in analysis.get("sub_agents", []):
                if sa.get("_filename") and sa.get("_generated_yaml"):
                    results[sa["_filename"]] = sa["_generated_yaml"]
            total_tests = event.test_count

        if event.type == "completed":
            total_tests = event.total_tests
            # Add E2E if generated
            if "_e2e_yaml" in analysis:
                results["e2e_critical.yaml"] = analysis["_e2e_yaml"]

    # Write all files
    if results:
        write_testcases(output_dir, results)

    return total_tests


async def run_batch(
    generator: TestCaseGenerator,
    analysis: dict,
    output_dir: Path,
    max_concurrent: int,
) -> int:
    """Run batch generation.

    Args:
        generator: TestCaseGenerator instance.
        analysis: Agent analysis dictionary.
        output_dir: Output directory for files.
        max_concurrent: Max concurrent API calls.

    Returns:
        Total test count.
    """
    agent_id = analysis.get("agent_id", "unknown")
    print(json.dumps({"type": "started", "agent_id": agent_id}))

    results, total_tests = await generator.batch_generate(analysis, max_concurrent)

    # Write files
    created_files = write_testcases(output_dir, results)

    print(json.dumps({
        "type": "completed",
        "agent_id": agent_id,
        "total_tests": total_tests,
        "files": [Path(f).name for f in created_files],
    }))

    return total_tests


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate test cases from agent analysis using Claude API"
    )
    parser.add_argument(
        "analysis_file",
        type=Path,
        help="Path to analysis JSON file",
    )
    parser.add_argument(
        "output_dir",
        type=Path,
        help="Path to agent's eval/ directory",
    )
    parser.add_argument(
        "--model",
        default="claude-sonnet-4-20250514",
        help="Claude model to use (default: claude-sonnet-4-20250514)",
    )
    parser.add_argument(
        "--streaming",
        action="store_true",
        help="Enable streaming progress events",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=5,
        help="Max concurrent API calls for batch mode (default: 5)",
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.analysis_file.exists():
        print(f"Error: Analysis file not found: {args.analysis_file}", file=sys.stderr)
        sys.exit(1)

    # Load analysis
    with open(args.analysis_file) as f:
        analysis = json.load(f)

    # Create generator
    generator = TestCaseGenerator(model=args.model)

    # Run generation
    if args.streaming:
        total = asyncio.run(run_streaming(generator, analysis, args.output_dir))
    else:
        total = asyncio.run(run_batch(generator, analysis, args.output_dir, args.max_concurrent))

    print(f"Generated {total} test cases", file=sys.stderr)


if __name__ == "__main__":
    main()
