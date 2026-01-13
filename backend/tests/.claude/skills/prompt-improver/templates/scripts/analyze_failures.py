#!/usr/bin/env python3
"""
Analyze eval results and categorize failures by pattern.

Usage:
    python analyze_failures.py results.json
    python analyze_failures.py results.json --output failures_report.json
    python analyze_failures.py results.json --verbose
"""

import json
import re
import sys
from pathlib import Path
from typing import Any
from collections import defaultdict
from dataclasses import dataclass, asdict


@dataclass
class FailurePattern:
    """Represents a categorized failure pattern."""
    category: str
    description: str
    test_ids: list[str]
    count: int
    examples: list[dict]


def load_results(path: str) -> dict:
    """Load eval results from JSON file."""
    with open(path, 'r') as f:
        return json.load(f)


def extract_failures(results: dict) -> list[dict]:
    """Extract failed test cases from results."""
    failures = []

    # Handle promptfoo format
    if 'results' in results and 'results' in results['results']:
        for result in results['results']['results']:
            if not result.get('success', True):
                failures.append({
                    'test_id': result.get('testCase', {}).get('description', 'Unknown'),
                    'error': result.get('error', ''),
                    'reason': result.get('gradingResult', {}).get('reason', ''),
                    'output': result.get('response', {}).get('output', ''),
                    'expected': extract_expected(result),
                    'metadata': result.get('metadata', {}),
                    'component_results': result.get('gradingResult', {}).get('componentResults', []),
                    'score': result.get('score', 0),
                    'tags': result.get('testCase', {}).get('metadata', {}).get('tags', []),
                    'source_file': result.get('testCase', {}).get('metadata', {}).get('source_file', ''),
                })
    # Handle simple format (list of results)
    elif isinstance(results, list):
        for result in results:
            if not result.get('passed', result.get('success', True)):
                failures.append({
                    'test_id': result.get('test_id', result.get('name', 'Unknown')),
                    'error': result.get('error', ''),
                    'reason': result.get('reason', ''),
                    'output': result.get('output', result.get('response', '')),
                    'expected': result.get('expected', ''),
                    'metadata': result.get('metadata', {}),
                    'score': result.get('score', 0),
                })

    return failures


def extract_expected(result: dict) -> str:
    """Extract expected value from test case assertions."""
    expected_parts = []
    test_case = result.get('testCase', {})
    for assertion in test_case.get('assert', []):
        if 'value' in assertion:
            expected_parts.append(f"{assertion.get('type', 'unknown')}: {assertion['value']}")
    return ' | '.join(expected_parts) if expected_parts else ''


def categorize_failure(failure: dict) -> str:
    """Categorize a failure based on error patterns."""
    error = failure.get('error', '').lower()
    reason = failure.get('reason', '').lower()
    output = failure.get('output', '').lower()
    combined = f"{error} {reason} {output}"

    # Tool usage issues
    if 'tool' in combined or 'function' in combined:
        if 'contain' in combined or 'expected' in combined:
            return 'tool_missing'
        if 'wrong' in combined or 'incorrect' in combined:
            return 'tool_wrong'
        return 'tool_issues'

    # Formatting issues
    if any(marker in output for marker in ['**', '##', '- ', '```', '{', '[']):
        return 'formatting'

    # Verbosity issues
    if len(output.split()) > 100:
        return 'verbosity'

    # Tone issues
    if any(word in combined for word in ['tone', 'empathy', 'cold', 'robotic', 'aggressive']):
        return 'tone'

    # Missing information
    if any(word in combined for word in ['missing', 'didn\'t answer', 'incomplete', 'omit']):
        return 'missing_info'

    # Guardrail violations
    if any(word in combined for word in ['guardrail', 'off-topic', 'scope', 'unauthorized']):
        return 'guardrail'

    # Assertion failures
    if 'assertion' in combined or 'expected' in combined:
        return 'assertion_failed'

    return 'other'


def get_category_description(category: str) -> str:
    """Get human-readable description for failure category."""
    descriptions = {
        'tool_missing': 'Tool not called when expected',
        'tool_wrong': 'Wrong tool called or incorrect parameters',
        'tool_issues': 'General tool usage problems',
        'formatting': 'Output contains markdown, JSON, or special formatting',
        'verbosity': 'Response is too long (>100 words)',
        'tone': 'Response tone is inappropriate (cold, robotic, aggressive)',
        'missing_info': 'Response missing required information',
        'guardrail': 'Response violated guardrails or went off-topic',
        'assertion_failed': 'Test assertion failed',
        'other': 'Uncategorized failure',
    }
    return descriptions.get(category, 'Unknown failure type')


def analyze_failures(failures: list[dict]) -> dict:
    """Analyze failures and group by pattern."""
    patterns = defaultdict(lambda: {'test_ids': [], 'examples': []})

    for failure in failures:
        category = categorize_failure(failure)
        patterns[category]['test_ids'].append(failure['test_id'])

        # Keep up to 3 examples per category
        if len(patterns[category]['examples']) < 3:
            patterns[category]['examples'].append({
                'test_id': failure['test_id'],
                'error': failure.get('error', ''),
                'output_excerpt': failure.get('output', '')[:500],
                'expected': failure.get('expected', ''),
            })

    # Convert to structured output
    result = {
        'total_failures': len(failures),
        'categories': {},
        'patterns': [],
    }

    for category, data in sorted(patterns.items(), key=lambda x: -len(x[1]['test_ids'])):
        count = len(data['test_ids'])
        result['categories'][category] = count
        result['patterns'].append({
            'category': category,
            'description': get_category_description(category),
            'count': count,
            'percentage': round(count / len(failures) * 100, 1) if failures else 0,
            'test_ids': data['test_ids'],
            'examples': data['examples'],
        })

    return result


def get_fix_suggestions(category: str) -> list[str]:
    """Get fix suggestions for a failure category."""
    suggestions = {
        'tool_missing': [
            'Add explicit tool trigger conditions in prompt',
            'Example: "CALL tool_name IMMEDIATELY when user mentions X"',
            'Check if tool is properly registered in agent',
        ],
        'tool_wrong': [
            'Clarify when each tool should be used',
            'Add parameter validation instructions',
            'Provide example tool calls in prompt',
        ],
        'formatting': [
            'Add: "Respond in plain text only, NO markdown"',
            'Add: "NEVER use bullets, asterisks, or special characters"',
            'Add: "Use verbal transitions instead of lists"',
        ],
        'verbosity': [
            'Add explicit word/sentence limit: "Keep responses under 25 words"',
            'Add: "Answer the question directly, then stop"',
            'Add: "No preamble or filler phrases"',
        ],
        'tone': [
            'Add empathy instructions: "Acknowledge emotions before problem-solving"',
            'Add style guidance: "Use warm, natural language"',
            'Add: "Match the user\'s energy level"',
        ],
        'missing_info': [
            'Add: "Answer the question asked, not a related question"',
            'Add: "Include specific numbers, dates, or facts when known"',
            'Improve goal clarity in prompt',
        ],
        'guardrail': [
            'Add explicit guardrails section',
            'Add redirect phrases for out-of-scope topics',
            'Define scope boundaries clearly',
        ],
    }
    return suggestions.get(category, ['Review failure details and adjust prompt accordingly'])


def format_report(analysis: dict, verbose: bool = False) -> str:
    """Format analysis as human-readable report."""
    lines = [
        "=" * 60,
        "FAILURE ANALYSIS REPORT",
        "=" * 60,
        "",
        f"Total Failures: {analysis['total_failures']}",
        "",
        "FAILURE CATEGORIES:",
        "-" * 40,
    ]

    for pattern in analysis['patterns']:
        lines.append(f"\n{pattern['category'].upper()} ({pattern['count']} - {pattern['percentage']}%)")
        lines.append(f"  Description: {pattern['description']}")
        lines.append(f"  Affected Tests: {', '.join(pattern['test_ids'][:5])}")
        if len(pattern['test_ids']) > 5:
            lines.append(f"    ... and {len(pattern['test_ids']) - 5} more")

        if verbose and pattern['examples']:
            lines.append("\n  Examples:")
            for i, ex in enumerate(pattern['examples'], 1):
                lines.append(f"    {i}. {ex['test_id']}")
                if ex['error']:
                    lines.append(f"       Error: {ex['error'][:100]}")
                if ex['expected']:
                    lines.append(f"       Expected: {ex['expected'][:100]}")

        lines.append("\n  Suggested Fixes:")
        for fix in get_fix_suggestions(pattern['category']):
            lines.append(f"    - {fix}")

    lines.extend([
        "",
        "=" * 60,
        "Next Steps:",
        "1. Review the patterns above",
        "2. Prioritize by count/percentage",
        "3. Apply fixes to prompts one category at a time",
        "4. Re-run evals to validate improvements",
        "=" * 60,
    ])

    return '\n'.join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Analyze eval failures and categorize by pattern')
    parser.add_argument('results_file', help='Path to results.json file')
    parser.add_argument('--output', '-o', help='Output JSON file for structured results')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed examples')
    parser.add_argument('--json', action='store_true', help='Output as JSON instead of text report')

    args = parser.parse_args()

    # Load and analyze
    results = load_results(args.results_file)
    failures = extract_failures(results)
    analysis = analyze_failures(failures)

    # Add suggestions to patterns
    for pattern in analysis['patterns']:
        pattern['suggestions'] = get_fix_suggestions(pattern['category'])

    # Output
    if args.json:
        print(json.dumps(analysis, indent=2))
    else:
        print(format_report(analysis, verbose=args.verbose))

    # Write to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(analysis, f, indent=2)
        print(f"\nStructured results written to: {args.output}")

    # Exit with non-zero if there are failures
    sys.exit(1 if analysis['total_failures'] > 0 else 0)


if __name__ == '__main__':
    main()
