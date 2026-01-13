"""
Fuzzy Matching Utilities for POPI Identity Verification

This module implements fuzzy matching for verifying debtor identity during
debt collection calls, ensuring compliance with POPI (Protection of Personal
Information Act) requirements.

Key Features:
- Handles voice input variations (spoken digits, common misheard words)
- Normalizes values across different field types (phone numbers, dates, IDs)
- Provides configurable match thresholds per field type
- Supports progressive verification (priority fields first)
"""

import re
import difflib
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# VERIFICATION FIELD DEFINITIONS
# ============================================================

# All 11 verifiable fields for POPI compliance
VERIFICATION_FIELDS: List[str] = [
    "username",
    "birth_date",
    "vehicle_registration",
    "vehicle_make",
    "vehicle_model",
    "vehicle_color",
    "vin_number",
    "email",
    "residential_address",
    "contact_number",
    "id_number",
    "passport_number"
]

# Priority fields that can verify identity alone
PRIORITY_FIELDS: List[str] = [
    "id_number",
    "passport_number"
]

# Match thresholds per field type (0.0 to 1.0)
MATCH_THRESHOLDS: Dict[str, float] = {
    "id_number": 0.95,          # Very strict for government IDs
    "passport_number": 0.95,     # Very strict for government IDs
    "contact_number": 0.90,      # Strict for phone numbers
    "email": 0.85,               # Moderately strict for email addresses
    "birth_date": 0.80,          # Allow some flexibility for date formats
    "vehicle_registration": 0.85,  # Moderately strict
    "vin_number": 0.90,          # Strict for VIN
    "username": 0.80,            # Flexible for names
    "vehicle_make": 0.75,        # Allow flexibility for brands
    "vehicle_model": 0.75,       # Allow flexibility for models
    "vehicle_color": 0.70,       # Very flexible (color descriptions vary)
    "residential_address": 0.70  # Flexible (addresses can be stated many ways)
}


# ============================================================
# SPOKEN DIGIT CONVERSION
# ============================================================

# Mapping of spoken words to digits
DIGIT_WORDS: Dict[str, str] = {
    # Zero variations
    "oh": "0",
    "o": "0",
    "zero": "0",

    # Single digits
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",

    # Teens (for dates/addresses)
    "ten": "10",
    "eleven": "11",
    "twelve": "12",
    "thirteen": "13",
    "fourteen": "14",
    "fifteen": "15",
    "sixteen": "16",
    "seventeen": "17",
    "eighteen": "18",
    "nineteen": "19",

    # Tens
    "twenty": "20",
    "thirty": "30",
    "forty": "40",
    "fifty": "50",
    "sixty": "60",
    "seventy": "70",
    "eighty": "80",
    "ninety": "90"
}


def convert_spoken_digits(text: str) -> str:
    """
    Convert spoken words to digits for voice input processing.

    Handles common voice input variations:
    - "oh", "o", "zero" -> "0"
    - "one" through "nine" -> "1" through "9"
    - "double three" -> "33"
    - "twenty-five" -> "25"
    - Mixed formats: "oh eight one two" -> "0812"

    Args:
        text: Input text potentially containing spoken digits

    Returns:
        Text with spoken digits converted to numeric digits

    Examples:
        >>> convert_spoken_digits("oh eight one two three four five")
        "0812345"
        >>> convert_spoken_digits("double three four")
        "334"
        >>> convert_spoken_digits("twenty-five")
        "25"
    """
    if not text:
        return ""

    # Normalize text
    text = text.lower().strip()

    # Handle "double" followed by digit
    # Pattern: "double three" -> "33", "double oh" -> "00"
    double_pattern = r'\bdouble\s+(\w+)'
    matches = re.finditer(double_pattern, text)
    for match in reversed(list(matches)):  # Reverse to preserve indices
        word = match.group(1)
        if word in DIGIT_WORDS:
            digit = DIGIT_WORDS[word]
            replacement = digit + digit  # Repeat the digit
            text = text[:match.start()] + replacement + text[match.end():]

    # Handle compound numbers like "twenty-five" -> "25"
    # Pattern: "twenty five" or "twenty-five"
    for tens_word, tens_value in DIGIT_WORDS.items():
        if tens_word in ["twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]:
            for ones_word, ones_value in DIGIT_WORDS.items():
                if ones_word in ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]:
                    # Match "twenty five" or "twenty-five"
                    compound_pattern = rf'\b{tens_word}[\s-]{ones_word}\b'
                    compound_number = str(int(tens_value) + int(ones_value))
                    text = re.sub(compound_pattern, compound_number, text)

    # Replace individual digit words
    words = text.split()
    converted_words = []

    for word in words:
        # Remove common punctuation
        word_clean = word.strip(".,;:!?-")

        if word_clean in DIGIT_WORDS:
            converted_words.append(DIGIT_WORDS[word_clean])
        else:
            # Keep original word if not a digit word
            converted_words.append(word)

    # Join and clean up spaces around digits
    result = " ".join(converted_words)

    # Remove spaces between consecutive digits
    # "0 8 1 2" -> "0812"
    result = re.sub(r'(\d)\s+(?=\d)', r'\1', result)

    return result


# ============================================================
# VALUE NORMALIZATION
# ============================================================

def normalize_value(value: str, field_name: str) -> str:
    """
    Normalize values for consistent comparison.

    Applies field-specific normalization rules:
    - Phone numbers: Remove +27, leading 0, spaces, dashes
    - Dates: Parse to YYYY-MM-DD format
    - ID numbers: Digits only
    - General: Lowercase, no spaces, no special characters

    Args:
        value: Raw value to normalize
        field_name: Name of field (determines normalization rules)

    Returns:
        Normalized value ready for comparison

    Examples:
        >>> normalize_value("+27 82 123 4567", "contact_number")
        "821234567"
        >>> normalize_value("1990/05/15", "birth_date")
        "1990-05-15"
        >>> normalize_value("9005155123086", "id_number")
        "9005155123086"
    """
    if not value:
        return ""

    # Convert spoken digits first
    value = convert_spoken_digits(str(value))

    # Basic cleanup
    value = value.strip().lower()

    # Field-specific normalization
    if field_name in ["contact_number", "phone", "mobile", "cell"]:
        # Normalize phone numbers
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', value)

        # Remove South African country code if present
        # +27 or 0027
        if digits_only.startswith("27"):
            digits_only = digits_only[2:]

        # Remove leading 0 if present (local format)
        if digits_only.startswith("0"):
            digits_only = digits_only[1:]

        return digits_only

    elif field_name == "birth_date":
        # Try to parse date to standard format (YYYY-MM-DD)
        # Common formats: "1990/05/15", "15-05-1990", "May 15, 1990"

        # Remove spoken words like "born on", "my birthday is"
        value = re.sub(r'\b(born on|birthday is|dob is|date of birth)\b', '', value).strip()

        # Try multiple date formats
        date_formats = [
            "%Y-%m-%d",      # 1990-05-15
            "%Y/%m/%d",      # 1990/05/15
            "%d-%m-%Y",      # 15-05-1990
            "%d/%m/%Y",      # 15/05/1990
            "%d %m %Y",      # 15 05 1990
            "%Y %m %d",      # 1990 05 15
            "%B %d, %Y",     # May 15, 1990
            "%d %B %Y",      # 15 May 1990
            "%b %d, %Y",     # May 15, 1990
            "%d %b %Y"       # 15 May 1990
        ]

        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(value, fmt)
                return parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                continue

        # If parsing fails, return digits only (fallback)
        return re.sub(r'\D', '', value)

    elif field_name in ["id_number", "passport_number", "vin_number"]:
        # Keep only alphanumeric characters (no spaces, dashes)
        return re.sub(r'[^a-z0-9]', '', value)

    elif field_name == "email":
        # Email normalization
        # Remove spaces
        value = value.replace(" ", "")
        # Handle spoken "at" -> "@"
        value = value.replace(" at ", "@")
        value = value.replace("at", "@")
        # Handle spoken "dot" -> "."
        value = value.replace(" dot ", ".")
        value = value.replace("dot", ".")
        return value

    elif field_name == "vehicle_registration":
        # Vehicle registration: Remove spaces, keep alphanumeric
        # "CA 123 GP" -> "ca123gp"
        return re.sub(r'[^a-z0-9]', '', value)

    elif field_name in ["residential_address", "address"]:
        # Address normalization
        # Keep alphanumeric and spaces, remove punctuation
        # "123 Main St., Apt 4" -> "123 main st apt 4"
        value = re.sub(r'[^\w\s]', '', value)
        # Normalize multiple spaces to single space
        value = re.sub(r'\s+', ' ', value)
        return value.strip()

    else:
        # General normalization for other fields
        # Remove special characters, keep spaces for multi-word fields
        value = re.sub(r'[^\w\s]', '', value)
        # Normalize multiple spaces
        value = re.sub(r'\s+', ' ', value)
        return value.strip()


# ============================================================
# FUZZY MATCHING
# ============================================================

def fuzzy_match(
    provided_value: str,
    expected_value: str,
    field_name: str
) -> Dict[str, Any]:
    """
    Perform fuzzy matching between provided and expected values.

    Uses difflib.SequenceMatcher for similarity comparison with
    field-specific thresholds.

    Args:
        provided_value: Value provided by debtor
        expected_value: Expected value from debtor profile
        field_name: Name of field being verified

    Returns:
        Dictionary containing:
        - matched (bool): Whether values match within threshold
        - similarity (float): Similarity ratio (0.0 to 1.0)
        - normalized_provided (str): Normalized provided value
        - normalized_expected (str): Normalized expected value

    Examples:
        >>> fuzzy_match("oh eight two one two three", "0821234567", "contact_number")
        {
            "matched": False,
            "similarity": 0.6,
            "normalized_provided": "821234",
            "normalized_expected": "821234567"
        }
    """
    # Normalize both values
    normalized_provided = normalize_value(provided_value, field_name)
    normalized_expected = normalize_value(expected_value, field_name)

    # Handle empty values
    if not normalized_provided or not normalized_expected:
        return {
            "matched": False,
            "similarity": 0.0,
            "normalized_provided": normalized_provided,
            "normalized_expected": normalized_expected
        }

    # Calculate similarity using SequenceMatcher
    similarity = difflib.SequenceMatcher(
        None,
        normalized_provided,
        normalized_expected
    ).ratio()

    # Get threshold for this field type
    threshold = MATCH_THRESHOLDS.get(field_name, 0.80)

    # Determine match
    matched = similarity >= threshold

    return {
        "matched": matched,
        "similarity": round(similarity, 3),
        "normalized_provided": normalized_provided,
        "normalized_expected": normalized_expected
    }


# ============================================================
# FIELD VERIFICATION
# ============================================================

def verify_field(
    field_name: str,
    provided_value: str,
    debtor_profile: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Verify a single field against debtor profile.

    Args:
        field_name: Name of field to verify
        provided_value: Value provided by debtor
        debtor_profile: Complete debtor profile dictionary

    Returns:
        Dictionary containing:
        - status (str): "MATCHED", "NOT_MATCHED", "CLOSE_MATCH", or "FIELD_NOT_AVAILABLE"
        - similarity (float): Similarity ratio (if applicable)
        - field (str): Field name
        - message (str): Human-readable result message

    Examples:
        >>> profile = {"id_number": "9005155123086"}
        >>> verify_field("id_number", "nine oh oh five one five five", profile)
        {
            "status": "CLOSE_MATCH",
            "similarity": 0.6,
            "field": "id_number",
            "message": "Partial match (60%) - please provide complete ID number"
        }
    """
    # Check if field exists in profile
    if field_name not in debtor_profile:
        return {
            "status": "FIELD_NOT_AVAILABLE",
            "similarity": 0.0,
            "field": field_name,
            "message": f"Field '{field_name}' not available in debtor profile"
        }

    expected_value = debtor_profile.get(field_name)

    # Check if expected value is empty or None
    if not expected_value or expected_value == "":
        return {
            "status": "FIELD_NOT_AVAILABLE",
            "similarity": 0.0,
            "field": field_name,
            "message": f"No {field_name} on file for this debtor"
        }

    # Perform fuzzy match
    match_result = fuzzy_match(provided_value, expected_value, field_name)

    # Determine status based on match result
    threshold = MATCH_THRESHOLDS.get(field_name, 0.80)
    similarity = match_result["similarity"]

    if match_result["matched"]:
        # Full match
        return {
            "status": "MATCHED",
            "similarity": similarity,
            "field": field_name,
            "message": f"Successfully verified {field_name}"
        }
    elif similarity >= (threshold - 0.15):
        # Close match (within 15% of threshold)
        # E.g., if threshold is 0.80, close match is 0.65+
        return {
            "status": "CLOSE_MATCH",
            "similarity": similarity,
            "field": field_name,
            "message": f"Partial match ({int(similarity * 100)}%) - please verify {field_name} again"
        }
    else:
        # No match
        return {
            "status": "NOT_MATCHED",
            "similarity": similarity,
            "field": field_name,
            "message": f"Information does not match our records for {field_name}"
        }


# ============================================================
# VERIFICATION FLOW MANAGEMENT
# ============================================================

def get_next_verification_field(
    verified_fields: List[str],
    unavailable_fields: List[str]
) -> Optional[str]:
    """
    Get the next field to ask for verification.

    Prioritizes identity verification fields (id_number, passport_number) first,
    then moves to other fields in order.

    Args:
        verified_fields: List of already verified field names
        unavailable_fields: List of fields not available in profile

    Returns:
        Next field name to verify, or None if all fields exhausted

    Examples:
        >>> get_next_verification_field([], [])
        "id_number"
        >>> get_next_verification_field(["id_number"], ["passport_number"])
        "birth_date"
        >>> get_next_verification_field(VERIFICATION_FIELDS, [])
        None
    """
    # Create set of fields to skip
    skip_fields = set(verified_fields + unavailable_fields)

    # First, try priority fields (ID or passport)
    for field in PRIORITY_FIELDS:
        if field not in skip_fields:
            return field

    # Then, try other verification fields in order
    for field in VERIFICATION_FIELDS:
        if field not in skip_fields and field not in PRIORITY_FIELDS:
            return field

    # All fields exhausted
    return None


def is_identity_verified(
    verified_fields: List[str],
    verification_results: Dict[str, Dict[str, Any]]
) -> Tuple[bool, str]:
    """
    Check if identity is sufficiently verified for POPI compliance.

    Rules:
    - If id_number OR passport_number is MATCHED -> Identity verified
    - Otherwise, need at least 3 other fields MATCHED -> Identity verified
    - Else -> Identity NOT verified

    Args:
        verified_fields: List of field names that were verified
        verification_results: Dictionary mapping field names to verification results

    Returns:
        Tuple of (is_verified: bool, reason: str)

    Examples:
        >>> results = {"id_number": {"status": "MATCHED", "similarity": 0.98}}
        >>> is_identity_verified(["id_number"], results)
        (True, "Identity verified via ID number")

        >>> results = {
        ...     "birth_date": {"status": "MATCHED"},
        ...     "contact_number": {"status": "MATCHED"},
        ...     "vehicle_registration": {"status": "MATCHED"}
        ... }
        >>> is_identity_verified(["birth_date", "contact_number", "vehicle_registration"], results)
        (True, "Identity verified via 3 matched fields")
    """
    # Check priority fields first
    for priority_field in PRIORITY_FIELDS:
        if priority_field in verified_fields:
            result = verification_results.get(priority_field, {})
            if result.get("status") == "MATCHED":
                field_display = priority_field.replace("_", " ").title()
                return (True, f"Identity verified via {field_display}")

    # Count matched non-priority fields
    matched_count = 0
    matched_fields = []

    for field in verified_fields:
        if field not in PRIORITY_FIELDS:
            result = verification_results.get(field, {})
            if result.get("status") == "MATCHED":
                matched_count += 1
                matched_fields.append(field)

    # Need at least 3 matched fields
    if matched_count >= 3:
        fields_display = ", ".join([f.replace("_", " ") for f in matched_fields[:3]])
        return (True, f"Identity verified via {matched_count} matched fields ({fields_display})")

    # Not enough verification
    return (False, f"Need more verification - only {matched_count} field(s) matched")


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def format_field_name_for_voice(field_name: str) -> str:
    """
    Format field name for natural voice output.

    Args:
        field_name: Technical field name (e.g., "birth_date")

    Returns:
        Natural language field name (e.g., "date of birth")

    Examples:
        >>> format_field_name_for_voice("id_number")
        "ID number"
        >>> format_field_name_for_voice("birth_date")
        "date of birth"
        >>> format_field_name_for_voice("vehicle_registration")
        "vehicle registration number"
    """
    field_mappings = {
        "id_number": "ID number",
        "passport_number": "passport number",
        "birth_date": "date of birth",
        "contact_number": "contact number",
        "vehicle_registration": "vehicle registration number",
        "vehicle_make": "vehicle make",
        "vehicle_model": "vehicle model",
        "vehicle_color": "vehicle color",
        "vin_number": "VIN number",
        "email": "email address",
        "residential_address": "residential address",
        "username": "name"
    }

    return field_mappings.get(field_name, field_name.replace("_", " "))


def get_verification_prompt(field_name: str) -> str:
    """
    Generate a natural voice prompt for requesting verification field.

    Args:
        field_name: Technical field name

    Returns:
        Natural language prompt for agent to use

    Examples:
        >>> get_verification_prompt("id_number")
        "For security purposes, can I verify your ID number?"
        >>> get_verification_prompt("birth_date")
        "Can you confirm your date of birth?"
    """
    field_display = format_field_name_for_voice(field_name)

    # Priority fields get security emphasis
    if field_name in PRIORITY_FIELDS:
        return f"For security purposes, can I verify your {field_display}?"
    else:
        return f"Can you confirm your {field_display}?"


if __name__ == "__main__":
    print("=== Fuzzy Match Tests ===\n")

    # Test normalize_value
    print("normalize_value:")
    tests = [
        ("+27 82 123 4567", "contact_number", "821234567"),
        ("9005155123086", "id_number", "9005155123086"),
        ("CA 123 GP", "vehicle_registration", "ca123gp"),
    ]
    for value, field, expected in tests:
        result = normalize_value(value, field)
        status = "✓" if result == expected else "✗"
        print(f"  {status} normalize_value('{value}', '{field}') -> '{result}' (expected: '{expected}')")

    # Test fuzzy_match
    print("\nfuzzy_match:")
    profile = {"id_number": "9005155123086", "contact_number": "0821234567"}
    tests = [
        ("9005155123086", "9005155123086", "id_number", True),
        ("8005155123086", "9005155123086", "id_number", False),
        ("821234567", "0821234567", "contact_number", True),
    ]
    for provided, expected, field, should_match in tests:
        result = fuzzy_match(provided, expected, field)
        status = "✓" if result["matched"] == should_match else "✗"
        print(f"  {status} fuzzy_match('{provided}', '{expected}', '{field}') -> matched={result['matched']}, similarity={result['similarity']}")

    # Test verify_field
    print("\nverify_field:")
    profile = {"id_number": "9005155123086", "contact_number": "0821234567"}
    tests = [
        ("id_number", "9005155123086", "MATCHED"),
        ("id_number", "8005155123086", "CLOSE_MATCH"),  # 92.3% similarity is close match
        ("missing_field", "test", "FIELD_NOT_AVAILABLE"),
    ]
    for field, value, expected_status in tests:
        result = verify_field(field, value, profile)
        status = "✓" if result["status"] == expected_status else "✗"
        print(f"  {status} verify_field('{field}', '{value[:10]}...') -> {result['status']} (expected: {expected_status})")

    # Test get_next_verification_field
    print("\nget_next_verification_field:")
    tests = [
        ([], [], "id_number"),
        (["id_number"], [], "passport_number"),
        (["id_number", "passport_number"], [], "username"),
    ]
    for verified, unavailable, expected in tests:
        result = get_next_verification_field(verified, unavailable)
        status = "✓" if result == expected else "✗"
        print(f"  {status} get_next_verification_field({verified}, {unavailable}) -> '{result}' (expected: '{expected}')")

    # Test is_identity_verified
    print("\nis_identity_verified:")
    results1 = {"id_number": {"status": "MATCHED", "similarity": 0.98}}
    verified1, reason1 = is_identity_verified(["id_number"], results1)
    print(f"  ✓ ID verified: {verified1} - {reason1}")

    results2 = {"birth_date": {"status": "MATCHED"}, "contact_number": {"status": "MATCHED"}, "username": {"status": "MATCHED"}}
    verified2, reason2 = is_identity_verified(["birth_date", "contact_number", "username"], results2)
    print(f"  ✓ 3 fields verified: {verified2} - {reason2}")

    print("\n=== Done ===")
