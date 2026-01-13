# Utils

Voice input processing and identity verification utilities (13 functions).

## Public API

```python
from utils import (
    # Verification
    fuzzy_match,
    verify_field,
    is_identity_verified,
    get_next_verification_field,
    normalize_value,
    # Extraction
    extract_phone_number,
    extract_id_number,
    # Date/time
    parse_spoken_date,
    parse_spoken_time,
    validate_business_hours,
    validate_callback_window,
    format_date_friendly,
    format_time_friendly,
)
```

## Functions

### Verification (5)
- `fuzzy_match(provided, expected, field)` - Compare values with similarity score
- `verify_field(field, value, profile)` - Verify field against debtor profile
- `is_identity_verified(verified, results)` - Check if POPI requirements met
- `get_next_verification_field(verified, unavailable)` - Get next field to verify
- `normalize_value(value, field)` - Normalize value for comparison

### Extraction (2)
- `extract_phone_number(text)` - Extract SA phone from spoken input
- `extract_id_number(text)` - Extract SA ID from spoken input

### Date/Time (6)
- `parse_spoken_date(text)` - Parse "tomorrow", "next Monday", "the 25th"
- `parse_spoken_time(text)` - Parse "9:30 AM", "afternoon", "noon"
- `validate_business_hours(date, time)` - Check Mon-Sat 07:00-17:30
- `validate_callback_window(date)` - Check today or tomorrow only
- `format_date_friendly(date)` - Format for TTS ("tomorrow", "Monday")
- `format_time_friendly(time)` - Format for TTS ("9:30 AM")

## Usage

```python
from utils import verify_field, parse_spoken_date, validate_business_hours

# Verify a field
result = verify_field("id_number", "9005155123086", profile)
# Returns: {"status": "MATCHED", "similarity": 1.0}

# Parse callback date/time
callback_date = parse_spoken_date("tomorrow")
callback_time = parse_spoken_time("9:30 AM")
if validate_business_hours(callback_date, callback_time):
    # Schedule callback
    pass
```

## POPI Compliance

- **Minimum verification**: 1 priority field OR 3 regular fields
- **Priority fields**: `id_number`, `passport_number`
- **Audit trail**: All verification attempts logged

## Match Thresholds

| Field | Threshold |
|-------|-----------|
| `id_number`, `passport_number` | 0.95 |
| `contact_number` | 0.90 |
| `email`, `vehicle_registration` | 0.85 |
| `birth_date`, `username` | 0.80 |
| `vehicle_color`, `residential_address` | 0.70 |

## Internal Modules

For advanced use, import directly:

```python
from utils.fuzzy_match import MATCH_THRESHOLDS, VERIFICATION_FIELDS
from utils.spoken_digits import convert_spoken_to_digits
from utils.date_parser import get_payment_deadline
```
