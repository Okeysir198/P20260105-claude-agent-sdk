#!/usr/bin/env python3
"""
Calculate success rate and other metrics from eval results.

Usage:
    python calculate_metrics.py results.json
    python calculate_metrics.py results.json --output metrics.json
    python calculate_metrics.py results.json --format yaml
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Any
from collections import defaultdict


def load_results(path: str) -> dict:
    """Load eval results from JSON file."""
    with open(path, 'r') as f:
        return json.load(f)


def extract_test_results(results: dict) -> list[dict]:
    """Extract individual test results from various formats."""
    test_results = []

    # Handle promptfoo format
    if 'results' in results and 'results' in results['results']:
        for result in results['results']['results']:
            test_results.append({
                'test_id': result.get('testCase', {}).get('description', 'Unknown'),
                'passed': result.get('success', False),
                'score': result.get('score', 0),
                'latency_ms': result.get('latencyMs', 0),
                'error': result.get('error', ''),
                'tags': result.get('testCase', {}).get('metadata', {}).get('tags', []),
                'source_file': result.get('testCase', {}).get('metadata', {}).get('source_file', ''),
                'sub_agent': result.get('testCase', {}).get('metadata', {}).get('sub_agent_id', ''),
                'tool_calls': result.get('response', {}).get('tool_calls', []),
            })
    # Handle promptfoo stats directly
    elif 'results' in results and 'stats' in results['results']:
        stats = results['results']['stats']
        # Return aggregate data
        return [{
            'test_id': 'aggregate',
            'passed': True,
            'score': 1,
            'successes': stats.get('successes', 0),
            'failures': stats.get('failures', 0),
            'errors': stats.get('errors', 0),
        }]
    # Handle simple list format
    elif isinstance(results, list):
        for result in results:
            test_results.append({
                'test_id': result.get('test_id', result.get('name', 'Unknown')),
                'passed': result.get('passed', result.get('success', False)),
                'score': result.get('score', 1 if result.get('passed') else 0),
                'latency_ms': result.get('latency_ms', result.get('duration_ms', 0)),
                'error': result.get('error', ''),
                'tags': result.get('tags', []),
            })

    return test_results


def calculate_metrics(test_results: list[dict]) -> dict:
    """Calculate comprehensive metrics from test results."""
    if not test_results:
        return {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'success_rate': None,
            'error': 'No test results found',
        }

    # Check for aggregate format
    if len(test_results) == 1 and test_results[0].get('test_id') == 'aggregate':
        agg = test_results[0]
        total = agg.get('successes', 0) + agg.get('failures', 0) + agg.get('errors', 0)
        passed = agg.get('successes', 0)
        return {
            'total': total,
            'passed': passed,
            'failed': agg.get('failures', 0),
            'errors': agg.get('errors', 0),
            'success_rate': round(passed / total, 4) if total > 0 else None,
            'success_rate_pct': round(passed / total * 100, 2) if total > 0 else None,
        }

    total = len(test_results)
    passed = sum(1 for r in test_results if r['passed'])
    failed = total - passed

    # Calculate scores
    scores = [r['score'] for r in test_results if r['score'] is not None]
    avg_score = sum(scores) / len(scores) if scores else None

    # Calculate latency
    latencies = [r['latency_ms'] for r in test_results if r['latency_ms'] > 0]
    avg_latency = sum(latencies) / len(latencies) if latencies else None

    # Group by tags
    tag_metrics = defaultdict(lambda: {'passed': 0, 'total': 0})
    for result in test_results:
        for tag in result.get('tags', []):
            tag_metrics[tag]['total'] += 1
            if result['passed']:
                tag_metrics[tag]['passed'] += 1

    # Group by sub-agent
    agent_metrics = defaultdict(lambda: {'passed': 0, 'total': 0})
    for result in test_results:
        agent = result.get('sub_agent', 'unknown')
        if agent:
            agent_metrics[agent]['total'] += 1
            if result['passed']:
                agent_metrics[agent]['passed'] += 1

    # Group by source file
    file_metrics = defaultdict(lambda: {'passed': 0, 'total': 0})
    for result in test_results:
        source = result.get('source_file', 'unknown')
        if source:
            file_metrics[source]['total'] += 1
            if result['passed']:
                file_metrics[source]['passed'] += 1

    # Build metrics dict
    metrics = {
        'summary': {
            'total': total,
            'passed': passed,
            'failed': failed,
            'success_rate': round(passed / total, 4) if total > 0 else None,
            'success_rate_pct': round(passed / total * 100, 2) if total > 0 else None,
            'avg_score': round(avg_score, 4) if avg_score else None,
            'avg_latency_ms': round(avg_latency, 2) if avg_latency else None,
        },
        'by_tag': {
            tag: {
                'passed': data['passed'],
                'total': data['total'],
                'success_rate': round(data['passed'] / data['total'], 4) if data['total'] > 0 else None,
            }
            for tag, data in sorted(tag_metrics.items())
        },
        'by_agent': {
            agent: {
                'passed': data['passed'],
                'total': data['total'],
                'success_rate': round(data['passed'] / data['total'], 4) if data['total'] > 0 else None,
            }
            for agent, data in sorted(agent_metrics.items())
        },
        'by_file': {
            file: {
                'passed': data['passed'],
                'total': data['total'],
                'success_rate': round(data['passed'] / data['total'], 4) if data['total'] > 0 else None,
            }
            for file, data in sorted(file_metrics.items())
        },
        'failed_tests': [
            r['test_id'] for r in test_results if not r['passed']
        ],
    }

    return metrics


def format_yaml(metrics: dict) -> str:
    """Format metrics as YAML string."""
    lines = []

    def format_value(v, indent=0):
        prefix = '  ' * indent
        if isinstance(v, dict):
            result = []
            for k, val in v.items():
                if isinstance(val, dict):
                    result.append(f"{prefix}{k}:")
                    result.append(format_value(val, indent + 1))
                elif isinstance(val, list):
                    result.append(f"{prefix}{k}:")
                    for item in val:
                        result.append(f"{prefix}  - {item}")
                else:
                    result.append(f"{prefix}{k}: {val}")
            return '\n'.join(result)
        return str(v)

    return format_value(metrics)


def format_text_report(metrics: dict) -> str:
    """Format metrics as human-readable text report."""
    lines = [
        "=" * 50,
        "EVALUATION METRICS REPORT",
        "=" * 50,
        "",
    ]

    summary = metrics.get('summary', {})
    lines.extend([
        "SUMMARY",
        "-" * 30,
        f"Total Tests:    {summary.get('total', 0)}",
        f"Passed:         {summary.get('passed', 0)}",
        f"Failed:         {summary.get('failed', 0)}",
        f"Success Rate:   {summary.get('success_rate_pct', 'N/A')}%",
    ])

    if summary.get('avg_score') is not None:
        lines.append(f"Average Score:  {summary.get('avg_score')}")
    if summary.get('avg_latency_ms') is not None:
        lines.append(f"Avg Latency:    {summary.get('avg_latency_ms')} ms")

    # By tag
    if metrics.get('by_tag'):
        lines.extend([
            "",
            "BY TAG",
            "-" * 30,
        ])
        for tag, data in metrics['by_tag'].items():
            rate = data.get('success_rate', 0) or 0
            lines.append(f"  {tag}: {data['passed']}/{data['total']} ({rate*100:.1f}%)")

    # By agent
    if metrics.get('by_agent') and any(a != 'unknown' for a in metrics['by_agent']):
        lines.extend([
            "",
            "BY SUB-AGENT",
            "-" * 30,
        ])
        for agent, data in metrics['by_agent'].items():
            if agent != 'unknown':
                rate = data.get('success_rate', 0) or 0
                lines.append(f"  {agent}: {data['passed']}/{data['total']} ({rate*100:.1f}%)")

    # Failed tests
    failed = metrics.get('failed_tests', [])
    if failed:
        lines.extend([
            "",
            f"FAILED TESTS ({len(failed)})",
            "-" * 30,
        ])
        for test_id in failed[:10]:
            lines.append(f"  - {test_id}")
        if len(failed) > 10:
            lines.append(f"  ... and {len(failed) - 10} more")

    lines.extend([
        "",
        "=" * 50,
    ])

    return '\n'.join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Calculate metrics from eval results')
    parser.add_argument('results_file', help='Path to results.json file')
    parser.add_argument('--output', '-o', help='Output file for metrics')
    parser.add_argument('--format', '-f', choices=['json', 'yaml', 'text'], default='text',
                        help='Output format (default: text)')
    parser.add_argument('--summary-only', action='store_true',
                        help='Only output summary metrics')

    args = parser.parse_args()

    # Load and calculate
    results = load_results(args.results_file)
    test_results = extract_test_results(results)
    metrics = calculate_metrics(test_results)

    # Add metadata
    metrics['metadata'] = {
        'source_file': args.results_file,
        'calculated_at': datetime.now().isoformat(),
    }

    # Extract eval metadata if available
    if 'evalId' in results:
        metrics['metadata']['eval_id'] = results['evalId']
    if 'metadata' in results:
        metrics['metadata']['promptfoo_version'] = results['metadata'].get('promptfooVersion')

    # Summary only mode
    if args.summary_only:
        metrics = {'summary': metrics['summary'], 'metadata': metrics['metadata']}

    # Format output
    if args.format == 'json':
        output = json.dumps(metrics, indent=2)
    elif args.format == 'yaml':
        output = format_yaml(metrics)
    else:
        output = format_text_report(metrics)

    print(output)

    # Write to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            if args.format == 'json':
                json.dump(metrics, f, indent=2)
            else:
                f.write(output)
        print(f"\nMetrics written to: {args.output}")

    # Exit with code based on success rate
    summary = metrics.get('summary', {})
    success_rate = summary.get('success_rate', 0) or 0
    sys.exit(0 if success_rate >= 0.85 else 1)


if __name__ == '__main__':
    main()
