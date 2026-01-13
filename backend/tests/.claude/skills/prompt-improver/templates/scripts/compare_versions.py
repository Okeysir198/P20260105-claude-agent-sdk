#!/usr/bin/env python3
"""
Compare metrics across prompt versions from _versions.yaml.

Usage:
    python compare_versions.py prompts/_versions.yaml
    python compare_versions.py prompts/_versions.yaml --prompt prompt01_agent
    python compare_versions.py prompts/_versions.yaml --v1 v1 --v2 v2
    python compare_versions.py prompts/_versions.yaml --output comparison.md
"""

import json
import sys
from pathlib import Path
from typing import Any, Optional


def load_yaml(path: str) -> dict:
    """Load YAML file (simple parser for _versions.yaml format)."""
    import re

    with open(path, 'r') as f:
        content = f.read()

    # Try to use PyYAML if available
    try:
        import yaml
        return yaml.safe_load(content)
    except ImportError:
        pass

    # Simple fallback parser for basic _versions.yaml structure
    # This handles the specific format used in prompt versioning
    result = {'versions': {}, 'defaults': {}, 'metrics': {}}

    current_section = None
    current_version = None
    current_prompt = None

    for line in content.split('\n'):
        line_stripped = line.strip()

        # Skip comments and empty lines
        if not line_stripped or line_stripped.startswith('#'):
            continue

        # Detect section headers
        if line_stripped == 'versions:':
            current_section = 'versions'
            continue
        elif line_stripped == 'defaults:':
            current_section = 'defaults'
            continue
        elif line_stripped == 'metrics:':
            current_section = 'metrics'
            continue

        # Parse section content
        if current_section == 'versions':
            # Match version entry like "v1:" or "  v1:"
            version_match = re.match(r'^(\s*)(v\d+):$', line)
            if version_match:
                current_version = version_match.group(2)
                result['versions'][current_version] = {}
                continue

            # Match version properties
            if current_version:
                prop_match = re.match(r'^\s+(\w+):\s*["\']?([^"\']+)["\']?\s*$', line)
                if prop_match:
                    key, value = prop_match.groups()
                    result['versions'][current_version][key] = value

        elif current_section == 'defaults':
            # Match default entry like "prompt01_agent: v2"
            default_match = re.match(r'^\s*(\w+):\s*(v\d+)\s*$', line)
            if default_match:
                prompt, version = default_match.groups()
                result['defaults'][prompt] = version

        elif current_section == 'metrics':
            # Match prompt name
            prompt_match = re.match(r'^(\s*)(\w+):$', line)
            if prompt_match and not prompt_match.group(2).startswith('v'):
                current_prompt = prompt_match.group(2)
                result['metrics'][current_prompt] = {}
                continue

            # Match version metrics like "v1: {evaluations: 50, success_rate: 0.72}"
            if current_prompt:
                metrics_match = re.match(r'^\s+(v\d+):\s*\{(.+)\}\s*$', line)
                if metrics_match:
                    version = metrics_match.group(1)
                    metrics_str = metrics_match.group(2)

                    # Parse metrics
                    metrics = {}
                    for part in metrics_str.split(','):
                        if ':' in part:
                            k, v = part.split(':', 1)
                            k = k.strip()
                            v = v.strip()
                            if v == 'null':
                                metrics[k] = None
                            else:
                                try:
                                    metrics[k] = float(v) if '.' in v else int(v)
                                except ValueError:
                                    metrics[k] = v

                    result['metrics'][current_prompt][version] = metrics

    return result


def compare_versions(
    versions_data: dict,
    prompt_name: Optional[str] = None,
    v1: str = 'v1',
    v2: str = 'v2',
) -> dict:
    """Compare metrics between two versions."""
    metrics = versions_data.get('metrics', {})
    versions = versions_data.get('versions', {})
    defaults = versions_data.get('defaults', {})

    comparisons = []

    # Get prompts to compare
    prompts_to_compare = [prompt_name] if prompt_name else list(metrics.keys())

    for prompt in prompts_to_compare:
        if prompt not in metrics:
            continue

        prompt_metrics = metrics[prompt]

        if v1 not in prompt_metrics and v2 not in prompt_metrics:
            continue

        m1 = prompt_metrics.get(v1, {})
        m2 = prompt_metrics.get(v2, {})

        comparison = {
            'prompt': prompt,
            'default_version': defaults.get(prompt, 'unknown'),
            'v1': {
                'version': v1,
                'description': versions.get(v1, {}).get('description', ''),
                'status': versions.get(v1, {}).get('status', ''),
                'metrics': m1,
            },
            'v2': {
                'version': v2,
                'description': versions.get(v2, {}).get('description', ''),
                'status': versions.get(v2, {}).get('status', ''),
                'metrics': m2,
            },
            'changes': {},
        }

        # Calculate changes
        all_metric_keys = set(m1.keys()) | set(m2.keys())
        for key in all_metric_keys:
            val1 = m1.get(key)
            val2 = m2.get(key)

            if val1 is not None and val2 is not None:
                if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                    diff = val2 - val1
                    # Handle division by zero
                    if val1 != 0:
                        pct_change = round(diff / val1 * 100, 2)
                    elif diff == 0:
                        pct_change = 0.0
                    else:
                        pct_change = None  # Can't calculate percentage change from 0
                    comparison['changes'][key] = {
                        'v1': val1,
                        'v2': val2,
                        'diff': round(diff, 4),
                        'pct_change': pct_change,
                        'improved': diff > 0 if key in ['success_rate', 'tool_accuracy'] else diff < 0,
                    }
                else:
                    comparison['changes'][key] = {
                        'v1': val1,
                        'v2': val2,
                    }
            elif val2 is not None:
                comparison['changes'][key] = {
                    'v1': None,
                    'v2': val2,
                    'note': 'New in v2',
                }

        # Generate recommendation
        sr1 = m1.get('success_rate')
        sr2 = m2.get('success_rate')

        if sr1 is not None and sr2 is not None:
            if sr2 > sr1:
                comparison['recommendation'] = f'Promote {v2} (success rate improved by {(sr2-sr1)*100:.1f}%)'
            elif sr2 < sr1:
                comparison['recommendation'] = f'Keep {v1} (success rate decreased by {(sr1-sr2)*100:.1f}%)'
            else:
                comparison['recommendation'] = 'No change in success rate - review other metrics'
        elif sr2 is not None:
            comparison['recommendation'] = f'{v2} has metrics but {v1} does not - run baseline eval'
        else:
            comparison['recommendation'] = 'Run evaluations to collect metrics'

        comparisons.append(comparison)

    return {
        'versions_compared': [v1, v2],
        'comparisons': comparisons,
        'versions_info': versions,
    }


def format_markdown_report(comparison: dict) -> str:
    """Format comparison as Markdown report."""
    lines = [
        "# Version Comparison Report",
        "",
        f"**Versions Compared:** {comparison['versions_compared'][0]} vs {comparison['versions_compared'][1]}",
        "",
    ]

    # Version descriptions
    versions_info = comparison.get('versions_info', {})
    if versions_info:
        lines.extend([
            "## Version Descriptions",
            "",
        ])
        for v, info in sorted(versions_info.items()):
            lines.append(f"- **{v}**: {info.get('description', 'No description')} ({info.get('status', 'unknown')})")
        lines.append("")

    # Comparisons
    for comp in comparison['comparisons']:
        lines.extend([
            f"## {comp['prompt']}",
            "",
            f"**Current Default:** {comp['default_version']}",
            "",
            "### Metrics Comparison",
            "",
            "| Metric | " + comp['v1']['version'] + " | " + comp['v2']['version'] + " | Change |",
            "|--------|-----|-----|--------|",
        ])

        for key, change in comp.get('changes', {}).items():
            v1_val = change.get('v1', 'N/A')
            v2_val = change.get('v2', 'N/A')

            if v1_val is None:
                v1_val = 'N/A'
            if v2_val is None:
                v2_val = 'N/A'

            # Format values
            if isinstance(v1_val, float):
                if key == 'success_rate':
                    v1_val = f"{v1_val*100:.1f}%"
                else:
                    v1_val = f"{v1_val:.2f}"
            if isinstance(v2_val, float):
                if key == 'success_rate':
                    v2_val = f"{v2_val*100:.1f}%"
                else:
                    v2_val = f"{v2_val:.2f}"

            # Change indicator
            change_str = ''
            if 'pct_change' in change and change['pct_change'] is not None:
                pct = change['pct_change']
                improved = change.get('improved', False)
                arrow = '+' if pct > 0 else ''
                indicator = '' if improved else ' (worse)' if pct != 0 else ''
                change_str = f"{arrow}{pct:.1f}%{indicator}"
            elif 'diff' in change:
                diff = change.get('diff', 0)
                if diff == 0:
                    change_str = 'no change'
                else:
                    change_str = f"{'+'if diff > 0 else ''}{diff}"
            elif 'note' in change:
                change_str = change['note']

            lines.append(f"| {key} | {v1_val} | {v2_val} | {change_str} |")

        lines.extend([
            "",
            f"### Recommendation",
            "",
            comp.get('recommendation', 'No recommendation available'),
            "",
        ])

    return '\n'.join(lines)


def format_text_report(comparison: dict) -> str:
    """Format comparison as text report."""
    lines = [
        "=" * 60,
        "VERSION COMPARISON REPORT",
        "=" * 60,
        "",
        f"Comparing: {comparison['versions_compared'][0]} vs {comparison['versions_compared'][1]}",
        "",
    ]

    for comp in comparison['comparisons']:
        lines.extend([
            "-" * 40,
            f"PROMPT: {comp['prompt']}",
            f"Default: {comp['default_version']}",
            "",
        ])

        # Show metrics
        lines.append("Metrics:")
        for key, change in comp.get('changes', {}).items():
            v1_val = change.get('v1', 'N/A')
            v2_val = change.get('v2', 'N/A')

            if isinstance(v1_val, float) and key == 'success_rate':
                v1_val = f"{v1_val*100:.1f}%"
            if isinstance(v2_val, float) and key == 'success_rate':
                v2_val = f"{v2_val*100:.1f}%"

            lines.append(f"  {key}: {v1_val} -> {v2_val}")

        lines.extend([
            "",
            f"Recommendation: {comp.get('recommendation', 'N/A')}",
            "",
        ])

    lines.append("=" * 60)
    return '\n'.join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Compare prompt version metrics')
    parser.add_argument('versions_file', help='Path to _versions.yaml file')
    parser.add_argument('--prompt', '-p', help='Specific prompt to compare')
    parser.add_argument('--v1', default='v1', help='First version to compare (default: v1)')
    parser.add_argument('--v2', default='v2', help='Second version to compare (default: v2)')
    parser.add_argument('--output', '-o', help='Output file')
    parser.add_argument('--format', '-f', choices=['json', 'markdown', 'text'], default='text',
                        help='Output format (default: text)')

    args = parser.parse_args()

    # Load and compare
    versions_data = load_yaml(args.versions_file)
    comparison = compare_versions(versions_data, args.prompt, args.v1, args.v2)

    # Format output
    if args.format == 'json':
        output = json.dumps(comparison, indent=2)
    elif args.format == 'markdown':
        output = format_markdown_report(comparison)
    else:
        output = format_text_report(comparison)

    print(output)

    # Write to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            if args.format == 'json':
                json.dump(comparison, f, indent=2)
            else:
                f.write(output)
        print(f"\nComparison written to: {args.output}")


if __name__ == '__main__':
    main()
