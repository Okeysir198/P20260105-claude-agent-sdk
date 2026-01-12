"""
Date and time parsing utilities for voice input.

Handles natural language date/time expressions for:
- Callback scheduling
- Payment date commitments
- Business hours validation
"""

import re
from datetime import datetime, date, time, timedelta
from typing import Optional

from business_rules import BUSINESS_HOURS

# Day name mapping
DAY_NAMES = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

# Month name mapping
MONTH_NAMES = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

# Business hours from centralized config
BUSINESS_START = BUSINESS_HOURS["start"]
BUSINESS_END = BUSINESS_HOURS["end"]
BUSINESS_DAYS = BUSINESS_HOURS["days"]
CLOSING_BUFFER_MINUTES = BUSINESS_HOURS["closing_buffer_minutes"]


def parse_spoken_date(text: str, reference_date: Optional[date] = None) -> Optional[date]:
    """
    Parse natural language date expression.

    Handles:
    - "today", "tomorrow"
    - Day names: "Monday", "Tuesday", etc. (next occurrence)
    - Ordinal dates: "the 25th", "25th of this month"
    - Relative: "next week", "next Monday"
    - Specific dates: "May 15th", "15th of May"

    Args:
        text: Natural language date expression
        reference_date: Base date for relative calculations (defaults to today)

    Returns:
        Parsed date object or None if unable to parse

    Examples:
        >>> parse_spoken_date("tomorrow")
        datetime.date(2025, 12, 6)  # If today is Dec 5
        >>> parse_spoken_date("next Monday")
        datetime.date(2025, 12, 8)  # Next Monday from today
    """
    if reference_date is None:
        reference_date = date.today()

    text = text.lower().strip()

    # Handle "today"
    if "today" in text:
        return reference_date

    # Handle "tomorrow"
    if "tomorrow" in text:
        return reference_date + timedelta(days=1)

    # Handle day names (e.g., "Monday", "next Tuesday")
    for day_name, day_num in DAY_NAMES.items():
        if day_name in text:
            current_day = reference_date.weekday()
            days_ahead = day_num - current_day

            # If the day has passed this week, get next week's occurrence
            if days_ahead <= 0:
                days_ahead += 7

            return reference_date + timedelta(days=days_ahead)

    # Handle "next week"
    if "next week" in text:
        return reference_date + timedelta(days=7)

    # Handle ordinal dates (e.g., "the 25th", "25th of this month")
    ordinal_match = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)\b', text)
    if ordinal_match:
        day = int(ordinal_match.group(1))

        # Determine month
        month = reference_date.month
        year = reference_date.year

        # Check if a specific month is mentioned
        for month_name, month_num in MONTH_NAMES.items():
            if month_name in text:
                month = month_num
                # If month is mentioned and is before current month, assume next year
                if month < reference_date.month:
                    year += 1
                break
        else:
            # No month mentioned, use current or next month
            if day < reference_date.day:
                # Day has passed this month, use next month
                month += 1
                if month > 12:
                    month = 1
                    year += 1

        try:
            return date(year, month, day)
        except ValueError:
            # Invalid date (e.g., Feb 30)
            return None

    # Handle numeric date formats (e.g., "12/25", "25-12")
    date_match = re.search(r'\b(\d{1,2})[/-](\d{1,2})\b', text)
    if date_match:
        num1, num2 = int(date_match.group(1)), int(date_match.group(2))

        # Try day/month format (common in South Africa)
        if 1 <= num1 <= 31 and 1 <= num2 <= 12:
            day, month = num1, num2
            year = reference_date.year
            if month < reference_date.month or (month == reference_date.month and day < reference_date.day):
                year += 1
            try:
                return date(year, month, day)
            except ValueError:
                pass

        # Try month/day format (US style)
        if 1 <= num1 <= 12 and 1 <= num2 <= 31:
            month, day = num1, num2
            year = reference_date.year
            if month < reference_date.month or (month == reference_date.month and day < reference_date.day):
                year += 1
            try:
                return date(year, month, day)
            except ValueError:
                pass

    return None


def parse_spoken_time(text: str) -> Optional[time]:
    """
    Parse natural language time expression.

    Handles:
    - "9 AM", "9:30 PM", "nine o'clock"
    - "morning" (9:00 AM), "afternoon" (2:00 PM), "evening" (5:00 PM)
    - 24-hour format: "14:00", "1400"

    Args:
        text: Natural language time expression

    Returns:
        Parsed time object or None if unable to parse

    Examples:
        >>> parse_spoken_time("9:30 AM")
        datetime.time(9, 30)
        >>> parse_spoken_time("morning")
        datetime.time(9, 0)
    """
    text = text.lower().strip()

    # Handle general time-of-day expressions
    if "morning" in text:
        return time(9, 0)
    if "afternoon" in text:
        return time(14, 0)
    if "evening" in text:
        return time(17, 0)

    # Handle "noon" or "midday"
    if "noon" in text or "midday" in text:
        return time(12, 0)

    # Handle HH:MM format with AM/PM
    time_match = re.search(r'\b(\d{1,2}):(\d{2})\s*(am|pm)?\b', text)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2))
        meridiem = time_match.group(3)

        if meridiem == "pm" and hour != 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0

        if 0 <= hour < 24 and 0 <= minute < 60:
            return time(hour, minute)

    # Handle hour-only format (e.g., "9 AM", "9am", "nine o'clock")
    hour_match = re.search(r'\b(\d{1,2})\s*(am|pm|o\'?clock)?\b', text)
    if hour_match:
        hour = int(hour_match.group(1))
        meridiem = hour_match.group(2)

        if meridiem:
            if "pm" in meridiem and hour != 12:
                hour += 12
            elif "am" in meridiem and hour == 12:
                hour = 0

        if 0 <= hour < 24:
            return time(hour, 0)

    # Handle 24-hour format (e.g., "14:00", "1400")
    military_match = re.search(r'\b(\d{2}):?(\d{2})\b', text)
    if military_match:
        hour = int(military_match.group(1))
        minute = int(military_match.group(2))

        if 0 <= hour < 24 and 0 <= minute < 60:
            return time(hour, minute)

    return None


def validate_business_hours(target_date: date, target_time: time) -> bool:
    """
    Validate if the given date and time fall within business hours.

    Business hours are configured in business_rules/config.py (BUSINESS_HOURS).

    Args:
        target_date: Date to validate
        target_time: Time to validate

    Returns:
        True if within business hours, False otherwise
    """
    # Check if day is a business day
    if target_date.weekday() not in BUSINESS_DAYS:
        return False

    # Check time range
    if target_time < BUSINESS_START:
        return False

    # Apply closing buffer
    closing_with_buffer = datetime.combine(date.today(), BUSINESS_END) - timedelta(minutes=CLOSING_BUFFER_MINUTES)
    if target_time >= closing_with_buffer.time():
        return False

    return True


def validate_callback_window(target_date: date, reference_date: Optional[date] = None) -> bool:
    """
    Validate if the callback date is within allowed window.

    Callbacks are only allowed for:
    - Today (if before 5:30 PM)
    - Tomorrow

    Args:
        target_date: Requested callback date
        reference_date: Current date (defaults to today)

    Returns:
        True if within allowed window, False otherwise
    """
    if reference_date is None:
        reference_date = date.today()

    # Calculate days from reference date
    days_ahead = (target_date - reference_date).days

    # Only allow today or tomorrow
    if days_ahead < 0 or days_ahead > 1:
        return False

    # If scheduling for today, check if we have enough time
    if days_ahead == 0:
        current_time = datetime.now().time()
        closing_with_buffer = datetime.combine(date.today(), BUSINESS_END) - timedelta(minutes=CLOSING_BUFFER_MINUTES)
        if current_time >= closing_with_buffer.time():
            return False

    return True


def get_payment_deadline(script_type: str, reference_date: Optional[date] = None) -> date:
    """
    Calculate payment deadline based on script type.

    Deadlines:
    - ratio1/ratio2: End of next month
    - prelegal: End of current month
    - legal: Immediate (today)

    Args:
        script_type: Type of script (ratio1, ratio2, prelegal, legal)
        reference_date: Current date (defaults to today)

    Returns:
        Deadline date for payment
    """
    if reference_date is None:
        reference_date = date.today()

    script_type = script_type.lower()

    if script_type in ["ratio1", "ratio2"]:
        # End of next month
        if reference_date.month == 12:
            # December -> January of next year
            return date(reference_date.year + 1, 1, 31)
        else:
            # Get last day of next month
            next_month = reference_date.month + 1
            # Find last day by going to first of month after next, then subtracting 1 day
            if next_month == 12:
                last_day = date(reference_date.year, 12, 31)
            else:
                last_day = date(reference_date.year, next_month + 1, 1) - timedelta(days=1)
            return last_day

    elif script_type == "prelegal":
        # End of current month
        if reference_date.month == 12:
            return date(reference_date.year, 12, 31)
        else:
            # First day of next month minus 1 day
            return date(reference_date.year, reference_date.month + 1, 1) - timedelta(days=1)

    else:  # legal or unknown
        # Immediate (today)
        return reference_date


def format_date_friendly(target_date: date, reference_date: Optional[date] = None) -> str:
    """
    Format date in a friendly, conversational way.

    Args:
        target_date: Date to format
        reference_date: Current date for relative formatting (defaults to today)

    Returns:
        Friendly date string

    Examples:
        >>> format_date_friendly(date.today())
        "today"
        >>> format_date_friendly(date.today() + timedelta(days=1))
        "tomorrow"
        >>> format_date_friendly(date(2025, 12, 25))
        "Thursday, December 25th"
    """
    if reference_date is None:
        reference_date = date.today()

    days_diff = (target_date - reference_date).days

    if days_diff == 0:
        return "today"
    elif days_diff == 1:
        return "tomorrow"
    elif days_diff == -1:
        return "yesterday"
    elif 2 <= days_diff <= 6:
        return target_date.strftime("%A")  # Day name (e.g., "Monday")
    else:
        # Full date with ordinal suffix
        day = target_date.day
        if 10 <= day % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

        return target_date.strftime(f"%A, %B {day}{suffix}")


def format_time_friendly(target_time: time) -> str:
    """
    Format time in a friendly, conversational way.

    Args:
        target_time: Time to format

    Returns:
        Friendly time string

    Examples:
        >>> format_time_friendly(time(9, 0))
        "9:00 AM"
        >>> format_time_friendly(time(14, 30))
        "2:30 PM"
    """
    hour = target_time.hour
    minute = target_time.minute

    # Convert to 12-hour format
    if hour == 0:
        hour_12 = 12
        meridiem = "AM"
    elif hour < 12:
        hour_12 = hour
        meridiem = "AM"
    elif hour == 12:
        hour_12 = 12
        meridiem = "PM"
    else:
        hour_12 = hour - 12
        meridiem = "PM"

    if minute == 0:
        return f"{hour_12}:00 {meridiem}"
    else:
        return f"{hour_12}:{minute:02d} {meridiem}"


if __name__ == "__main__":
    print("=== Date Parser Tests ===\n")

    today = date.today()
    print(f"Reference date: {today}\n")

    # Test parse_spoken_date
    print("parse_spoken_date:")
    tests = [
        ("today", today),
        ("tomorrow", today + timedelta(days=1)),
        ("next week", today + timedelta(days=7)),
    ]
    for input_text, expected in tests:
        result = parse_spoken_date(input_text, today)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{input_text}' -> {result} (expected: {expected})")

    # Test parse_spoken_time
    print("\nparse_spoken_time:")
    tests = [
        ("9:30 AM", time(9, 30)),
        ("morning", time(9, 0)),
        ("noon", time(12, 0)),
        ("afternoon", time(14, 0)),
        ("2 PM", time(14, 0)),
    ]
    for input_text, expected in tests:
        result = parse_spoken_time(input_text)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{input_text}' -> {result} (expected: {expected})")

    # Test validate_business_hours
    print("\nvalidate_business_hours (Mon-Sat 07:00-17:30):")
    test_date = today if today.weekday() < 6 else today + timedelta(days=1)  # Use weekday
    tests = [
        (test_date, time(6, 30), False),   # Too early
        (test_date, time(10, 0), True),    # Valid
        (test_date, time(17, 45), False),  # Too late (buffer)
    ]
    for d, t, expected in tests:
        result = validate_business_hours(d, t)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {d.strftime('%a')} {t} -> {result} (expected: {expected})")

    # Test validate_callback_window
    print("\nvalidate_callback_window:")
    tests = [
        (today, True),
        (today + timedelta(days=1), True),
        (today + timedelta(days=2), False),
    ]
    for d, expected in tests:
        result = validate_callback_window(d, today)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {d} -> {result} (expected: {expected})")

    # Test format functions
    print("\nformat_date_friendly:")
    tests = [
        (today, "today"),
        (today + timedelta(days=1), "tomorrow"),
    ]
    for d, expected in tests:
        result = format_date_friendly(d, today)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {d} -> '{result}' (expected: '{expected}')")

    print("\nformat_time_friendly:")
    tests = [
        (time(9, 0), "9:00 AM"),
        (time(14, 30), "2:30 PM"),
    ]
    for t, expected in tests:
        result = format_time_friendly(t)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {t} -> '{result}' (expected: '{expected}')")

    print("\n=== Done ===")
