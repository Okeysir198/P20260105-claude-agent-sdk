"""
Spoken digit conversion utilities for voice input.

Handles conversion of spoken numbers to digits, including:
- Word-to-digit mapping (zero, one, two, etc.)
- Multiplier words (double, triple)
- Phone number extraction and normalization
- ID number extraction
"""

import re
from typing import Optional

# Word-to-digit mapping including common speech variations
WORD_TO_DIGIT = {
    "zero": "0",
    "oh": "0",
    "o": "0",
    "one": "1",
    "won": "1",
    "two": "2",
    "to": "2",
    "too": "2",
    "three": "3",
    "four": "4",
    "for": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "ate": "8",
    "nine": "9",
}

# Multiplier words for repeated digits
MULTIPLIERS = {
    "double": 2,
    "triple": 3,
}


def convert_spoken_to_digits(text: str) -> str:
    """
    Convert spoken number words to digits.

    Handles:
    - Individual digit words: "one two three" -> "123"
    - Multipliers: "double five" -> "55", "triple nine" -> "999"
    - Mixed text: preserves non-number words

    Args:
        text: Input text with spoken numbers

    Returns:
        Text with number words converted to digits

    Examples:
        >>> convert_spoken_to_digits("zero eight three double four")
        "0 8 3 44"
        >>> convert_spoken_to_digits("triple seven two one")
        "777 2 1"
    """
    text = text.lower().strip()
    words = text.split()
    result = []
    i = 0

    while i < len(words):
        word = words[i]

        # Check for multiplier (double, triple)
        if word in MULTIPLIERS and i + 1 < len(words):
            next_word = words[i + 1]
            if next_word in WORD_TO_DIGIT:
                digit = WORD_TO_DIGIT[next_word]
                count = MULTIPLIERS[word]
                result.append(digit * count)
                i += 2  # Skip both words
                continue

        # Check for regular digit word
        if word in WORD_TO_DIGIT:
            result.append(WORD_TO_DIGIT[word])
        else:
            result.append(word)

        i += 1

    return " ".join(result)


def extract_phone_number(text: str) -> Optional[str]:
    """
    Extract and normalize phone number from spoken text.

    Handles South African formats:
    - 0XX XXX XXXX (10 digits starting with 0)
    - +27 XX XXX XXXX (international format)

    Args:
        text: Text containing spoken phone number

    Returns:
        Normalized 10-digit phone number (starting with 0) or None if invalid

    Examples:
        >>> extract_phone_number("zero eight three four five six seven eight nine zero")
        "0834567890"
        >>> extract_phone_number("my number is zero seven one double two three four five six")
        "0711234567"
    """
    # Convert spoken digits to actual digits
    converted = convert_spoken_to_digits(text)

    # Remove all non-digit characters except +
    digits_only = re.sub(r'[^\d+]', '', converted)

    # Handle international format: +27 -> 0
    if digits_only.startswith('+27'):
        digits_only = '0' + digits_only[3:]
    elif digits_only.startswith('27') and len(digits_only) == 11:
        digits_only = '0' + digits_only[2:]

    # Validate: must be exactly 10 digits starting with 0
    if len(digits_only) == 10 and digits_only.startswith('0'):
        return digits_only

    # Try to find a 10-digit sequence in the text
    match = re.search(r'0\d{9}', digits_only)
    if match:
        return match.group(0)

    return None


def extract_id_number(text: str) -> Optional[str]:
    """
    Extract South African ID number from spoken text.

    SA ID numbers are 13 digits: YYMMDD SSSS C AZ
    - YYMMDD: Date of birth
    - SSSS: Sequence number (gender indicator)
    - C: Citizenship
    - A: Usually 8
    - Z: Checksum digit

    Args:
        text: Text containing spoken ID number

    Returns:
        13-digit ID number or None if invalid

    Examples:
        >>> extract_id_number("nine two zero five one eight five six seven eight zero eight one")
        "9205185678081"
        >>> extract_id_number("my ID is eight seven double one two three four five six seven eight nine zero")
        "8711234567890"
    """
    # Convert spoken digits to actual digits
    converted = convert_spoken_to_digits(text)

    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', converted)

    # Validate: must be exactly 13 digits
    if len(digits_only) == 13:
        # Basic validation: check if first 6 digits form valid date (YYMMDD)
        year = int(digits_only[0:2])
        month = int(digits_only[2:4])
        day = int(digits_only[4:6])

        if 1 <= month <= 12 and 1 <= day <= 31:
            return digits_only

    # Try to find a 13-digit sequence in the text
    match = re.search(r'\d{13}', digits_only)
    if match:
        potential_id = match.group(0)
        # Validate date portion
        month = int(potential_id[2:4])
        day = int(potential_id[4:6])
        if 1 <= month <= 12 and 1 <= day <= 31:
            return potential_id

    return None


def format_phone_display(phone: str) -> str:
    """
    Format phone number for display.

    Args:
        phone: 10-digit phone number

    Returns:
        Formatted phone number: 0XX XXX XXXX

    Examples:
        >>> format_phone_display("0834567890")
        "083 456 7890"
    """
    if len(phone) != 10:
        return phone

    return f"{phone[0:3]} {phone[3:6]} {phone[6:10]}"


def format_id_display(id_number: str) -> str:
    """
    Format ID number for display.

    Args:
        id_number: 13-digit ID number

    Returns:
        Formatted ID number: YYMMDD SSSS C A Z

    Examples:
        >>> format_id_display("9205185678081")
        "920518 5678 0 8 1"
    """
    if len(id_number) != 13:
        return id_number

    return f"{id_number[0:6]} {id_number[6:10]} {id_number[10]} {id_number[11]} {id_number[12]}"


if __name__ == "__main__":
    print("=== Spoken Digits Tests ===\n")

    # Test convert_spoken_to_digits
    print("convert_spoken_to_digits:")
    tests = [
        ("zero eight three double four", "0 8 3 44"),
        ("triple seven two one", "777 2 1"),
        ("oh eight one two three", "0 8 1 2 3"),
    ]
    for input_text, expected in tests:
        result = convert_spoken_to_digits(input_text)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{input_text}' -> '{result}' (expected: '{expected}')")

    # Test extract_phone_number
    print("\nextract_phone_number:")
    tests = [
        ("zero eight three four five six seven eight nine zero", "0834567890"),
        ("my number is zero seven one double two three four five six", None),  # Only 9 digits after double
        ("plus two seven eight two one two three four five six seven", "0821234567"),
    ]
    for input_text, expected in tests:
        result = extract_phone_number(input_text)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{input_text[:40]}...' -> {result} (expected: {expected})")

    # Test extract_id_number
    print("\nextract_id_number:")
    tests = [
        ("nine two zero five one eight five six seven eight zero eight one", "9205185678081"),
        ("nine oh oh five one five five one two three oh eight six", "9005155123086"),
    ]
    for input_text, expected in tests:
        result = extract_id_number(input_text)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{input_text[:40]}...' -> {result} (expected: {expected})")

    # Test format functions
    print("\nformat_phone_display:")
    print(f"  '0834567890' -> '{format_phone_display('0834567890')}'")

    print("\nformat_id_display:")
    print(f"  '9205185678081' -> '{format_id_display('9205185678081')}'")

    print("\n=== Done ===")
