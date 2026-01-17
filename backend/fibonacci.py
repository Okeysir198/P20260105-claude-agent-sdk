def fibonacci(n: int) -> int:
    """
    Calculate the nth Fibonacci number.

    Args:
        n: The position in the Fibonacci sequence (0-indexed).

    Returns:
        The nth Fibonacci number.

    Raises:
        ValueError: If n is negative.

    Examples:
        >>> fibonacci(0)
        0
        >>> fibonacci(1)
        1
        >>> fibonacci(10)
        55
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return n

    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


def fibonacci_recursive(n: int) -> int:
    """
    Calculate the nth Fibonacci number using recursion.

    Warning: This implementation has exponential time complexity O(2^n)
    and is not recommended for n > 30.

    Args:
        n: The position in the Fibonacci sequence (0-indexed).

    Returns:
        The nth Fibonacci number.

    Raises:
        ValueError: If n is negative.
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return n
    return fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2)


def fibonacci_sequence(count: int) -> list[int]:
    """
    Generate a sequence of Fibonacci numbers.

    Args:
        count: The number of Fibonacci numbers to generate.

    Returns:
        A list of Fibonacci numbers.

    Raises:
        ValueError: If count is negative.

    Examples:
        >>> fibonacci_sequence(10)
        [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
    """
    if count < 0:
        raise ValueError("count must be non-negative")
    if count == 0:
        return []

    sequence = [0]
    if count == 1:
        return sequence

    sequence.append(1)
    for _ in range(2, count):
        sequence.append(sequence[-1] + sequence[-2])
    return sequence


if __name__ == "__main__":
    # Example usage
    print("First 15 Fibonacci numbers:")
    print(fibonacci_sequence(15))

    print("\nSpecific Fibonacci numbers:")
    for i in [0, 1, 5, 10, 20, 50]:
        print(f"fibonacci({i}) = {fibonacci(i)}")
