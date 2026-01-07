"""
Helper utilities for business rules

Provides convenience functions for formatting, validation, and common operations.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, Any, Optional
from .config import SCRIPT_TYPES, AUTHORITIES, get_script_config, get_authority_info


def format_currency(amount: float, currency: str = "R") -> str:
    """
    Format currency amount for display.

    Args:
        amount: Amount to format
        currency: Currency symbol (default: R for Rand)

    Returns:
        Formatted currency string (e.g., "R1,234.56")
    """
    return f"{currency}{amount:,.2f}"


def format_discount_offer(discount_info: Dict[str, Any]) -> str:
    """
    Format discount information into human-readable text.

    Args:
        discount_info: Dictionary from calculate_discount()

    Returns:
        Formatted discount offer text
    """
    if not discount_info:
        return "No discount available"

    percentage = discount_info["percentage"]
    amount = discount_info["amount"]
    final = discount_info["discounted_balance"]
    deadline = discount_info["deadline"]

    return (
        f"Special offer: {percentage}% discount saves you {format_currency(amount)}. "
        f"Your new balance would be {format_currency(final)}. "
        f"This offer expires on {deadline.strftime('%B %d, %Y')}."
    )


def format_installment_plan(plan_info: Dict[str, Any]) -> str:
    """
    Format installment plan into human-readable text.

    Args:
        plan_info: Dictionary from calculate_installment()

    Returns:
        Formatted installment plan text
    """
    monthly = plan_info["total_installment"]
    months = plan_info["months"]
    breakdown = plan_info["breakdown"]

    text = f"Your monthly payment would be {format_currency(monthly)} for {months} months.\n"
    text += f"This includes:\n"
    text += f"  - Debt payment: {format_currency(breakdown['debt_portion'])}\n"

    if breakdown.get("subscription", 0) > 0:
        text += f"  - Subscription: {format_currency(breakdown['subscription'])}\n"

    if breakdown.get("fees", 0) > 0:
        text += f"  - DebiCheck fee: {format_currency(breakdown['fees'])}\n"

    total_paid = plan_info["total_paid"]
    text += f"\nTotal amount over {months} months: {format_currency(total_paid)}"

    return text


def calculate_days_overdue(due_date: date, current_date: Optional[date] = None) -> int:
    """
    Calculate number of days overdue.

    Args:
        due_date: Original due date
        current_date: Current date (defaults to today)

    Returns:
        Number of days overdue (0 if not overdue)
    """
    if current_date is None:
        current_date = date.today()

    delta = current_date - due_date
    return max(0, delta.days)


def get_overdue_tier(days: int) -> str:
    """
    Categorize overdue days into tier.

    Args:
        days: Number of days overdue

    Returns:
        Tier name: "current", "30_days", "60_days", "90_days", "120_days", "150_days", "180_plus"
    """
    if days < 30:
        return "current"
    elif days < 60:
        return "30_days"
    elif days < 90:
        return "60_days"
    elif days < 120:
        return "90_days"
    elif days < 150:
        return "120_days"
    elif days < 180:
        return "150_days"
    else:
        return "180_plus"


def is_discount_eligible(script_type: str) -> bool:
    """
    Check if a script type allows discounts.

    Args:
        script_type: Script type identifier

    Returns:
        True if discounts are enabled for this script type
    """
    config = get_script_config(script_type)
    if not config:
        return False
    return config.get("discount_enabled", False)


def get_payment_deadline(days_from_now: int = 7) -> date:
    """
    Calculate payment deadline.

    Args:
        days_from_now: Number of days until deadline (default: 7)

    Returns:
        Deadline date
    """
    return date.today() + timedelta(days=days_from_now)


def format_payment_deadline(deadline: date) -> str:
    """
    Format deadline in friendly text.

    Args:
        deadline: Deadline date

    Returns:
        Formatted string (e.g., "by December 12, 2025")
    """
    return f"by {deadline.strftime('%B %d, %Y')}"


def validate_balance(balance: float) -> tuple[bool, Optional[str]]:
    """
    Validate balance amount.

    Args:
        balance: Balance amount to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if balance < 0:
        return False, "Balance cannot be negative"
    if balance == 0:
        return False, "Balance cannot be zero"
    if balance > 1_000_000:
        return False, "Balance exceeds maximum allowed amount"
    return True, None


def validate_months(months: int, script_type: str) -> tuple[bool, Optional[str]]:
    """
    Validate installment months.

    Args:
        months: Number of months proposed
        script_type: Script type identifier

    Returns:
        Tuple of (is_valid, error_message)
    """
    if months < 1:
        return False, "Months must be at least 1"

    config = get_script_config(script_type)
    if not config:
        return False, f"Invalid script type: {script_type}"

    max_months = config.get("max_payments", 6)
    if months > max_months:
        return False, f"Exceeds maximum of {max_months} months for this account type"

    return True, None


def get_authority_contact_info(script_type: str) -> Optional[Dict[str, str]]:
    """
    Get authority contact information for a script type.

    Args:
        script_type: Script type identifier

    Returns:
        Authority info dict or None if not found
    """
    config = get_script_config(script_type)
    if not config:
        return None

    authority_key = config.get("authority")
    if not authority_key:
        return None

    return get_authority_info(authority_key)


def format_authority_info(script_type: str) -> str:
    """
    Format authority contact information for voice agent.

    Args:
        script_type: Script type identifier

    Returns:
        Formatted string with authority name and contact
    """
    authority = get_authority_contact_info(script_type)
    if not authority:
        return "Please contact our office for assistance."

    name = authority["name"]
    contact = authority["contact"]

    # Format phone number for speech
    # "011-250-3000" -> "zero one one, two five zero, three thousand"
    formatted_contact = format_phone_for_speech(contact)

    return f"Please contact {name} at {formatted_contact}."


def format_phone_for_speech(phone: str) -> str:
    """
    Format phone number for natural speech.

    Args:
        phone: Phone number (e.g., "011-250-3000")

    Returns:
        Speech-friendly format
    """
    # Remove common separators
    digits = phone.replace("-", " ").replace("(", "").replace(")", "").strip()

    # For South African numbers, group appropriately
    # 011-250-3000 -> "011, 250, 3000"
    parts = digits.split()
    if len(parts) == 1:
        # Split into groups if no spaces
        digits = parts[0]
        if len(digits) == 10:
            # Format as: 012 345 6789
            return f"{digits[:3]} {digits[3:6]} {digits[6:]}"
        elif len(digits) == 11:
            # Format as: 011 234 5678
            return f"{digits[:3]} {digits[3:6]} {digits[6:]}"

    return digits


def summarize_account_status(
    balance: float,
    overdue_days: int,
    script_type: str,
    last_payment_date: Optional[date] = None
) -> str:
    """
    Create summary of account status for agent.

    Args:
        balance: Outstanding balance
        overdue_days: Days overdue
        script_type: Script type
        last_payment_date: Date of last payment (optional)

    Returns:
        Human-readable account summary
    """
    config = get_script_config(script_type)
    tier = get_overdue_tier(overdue_days)

    summary = f"Outstanding balance: {format_currency(balance)}. "
    summary += f"Account is {overdue_days} days overdue. "

    if last_payment_date:
        days_since = (date.today() - last_payment_date).days
        summary += f"Last payment was {days_since} days ago. "

    if config and config.get("discount_enabled"):
        summary += "This account qualifies for discount offers. "

    return summary


def parse_date_string(date_str: str) -> Optional[date]:
    """
    Parse date string into date object.

    Supports formats: YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY

    Args:
        date_str: Date string to parse

    Returns:
        Date object or None if parsing fails
    """
    formats = [
        "%Y-%m-%d",  # 2025-12-05
        "%d/%m/%Y",  # 05/12/2025
        "%m/%d/%Y",  # 12/05/2025
        "%Y/%m/%d",  # 2025/12/05
        "%d-%m-%Y",  # 05-12-2025
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    return None


def calculate_settlement_savings(
    balance: float,
    discount_percentage: float,
    installment_months: int,
    monthly_subscription: float = 499.0
) -> Dict[str, float]:
    """
    Calculate savings between settlement vs installment.

    Args:
        balance: Outstanding balance
        discount_percentage: Discount percentage
        installment_months: Number of installment months
        monthly_subscription: Monthly subscription amount

    Returns:
        Dictionary with settlement vs installment comparison
    """
    discount_amount = balance * (discount_percentage / 100)
    settlement_amount = balance - discount_amount

    # Installment: discounted balance + subscription over months
    installment_total = (balance - discount_amount) + (monthly_subscription * installment_months)

    savings = installment_total - settlement_amount

    return {
        "settlement_amount": round(settlement_amount, 2),
        "installment_total": round(installment_total, 2),
        "savings_with_settlement": round(savings, 2),
        "monthly_subscription_cost": round(monthly_subscription * installment_months, 2),
    }
