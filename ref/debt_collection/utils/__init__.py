"""
Utility modules for debt collection voice agent.

Public API for:
- Identity verification (fuzzy matching)
- Phone/ID number extraction
- Date/time parsing
"""

from .fuzzy_match import (
    fuzzy_match,
    normalize_value,
    verify_field,
    get_next_verification_field,
    is_identity_verified,
)

from .spoken_digits import (
    extract_phone_number,
    extract_id_number,
)

from .date_parser import (
    parse_spoken_date,
    parse_spoken_time,
    validate_business_hours,
    validate_callback_window,
    format_date_friendly,
    format_time_friendly,
)

from .id_generator import (
    generate_agent_id,
    generate_sub_agent_id,
    generate_session_id,
)

__all__ = [
    # Verification
    "fuzzy_match",
    "verify_field",
    "is_identity_verified",
    "get_next_verification_field",
    "normalize_value",
    # Extraction
    "extract_phone_number",
    "extract_id_number",
    # Date/time
    "parse_spoken_date",
    "parse_spoken_time",
    "validate_business_hours",
    "validate_callback_window",
    "format_date_friendly",
    "format_time_friendly",
    # ID generation
    "generate_agent_id",
    "generate_sub_agent_id",
    "generate_session_id",
]
