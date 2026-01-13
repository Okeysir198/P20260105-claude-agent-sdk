"""
Debt Collection Agent Testing Framework

This package provides comprehensive testing tools for the debt collection
multi-agent voice system.

Usage:
    # CLI
    cd debt_collection/eval
    python run_tests.py --list
    python run_tests.py --test "Person confirms identity"

    # Programmatic
    from debt_collection.eval import run_test_case, load_test_cases

    tests = load_test_cases()
    result = run_test_case(tests[0])
"""

from ._provider import (
    run_test_case,
    run_single_turn,
    run_conversation,
    load_test_cases,
    get_test_case,
    ConversationResult,
    TurnResult,
    ConversationEvent,
)

from ._console import (
    console,
    print_header,
    print_success,
    print_error,
    print_warning,
    print_info,
    print_conversation_result,
    create_test_table,
)

__all__ = [
    # Test execution
    "run_test_case",
    "run_single_turn",
    "run_conversation",
    "load_test_cases",
    "get_test_case",

    # Data structures
    "ConversationResult",
    "TurnResult",
    "ConversationEvent",

    # Console utilities
    "console",
    "print_header",
    "print_success",
    "print_error",
    "print_warning",
    "print_info",
    "print_conversation_result",
    "create_test_table",
]
