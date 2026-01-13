"""
Discount Calculator for Debt Collection

Implements tiered discount matrix based on script type, balance amount,
and overdue days. Calculates installment amounts and payment schedules.

All discount configurations are now sourced from config.py SCRIPT_TYPES.
"""

from datetime import date, timedelta
from typing import Dict, Any, Optional, Tuple
from .config import INSTALLMENT_RULES, SCRIPT_TYPES, get_discount_tiers


def get_balance_tier(balance: float) -> Tuple[str, str]:
    """
    Determine balance tier based on amount.

    Args:
        balance: Outstanding balance amount

    Returns:
        Tuple of (tier_name, tier_description)
    """
    if balance <= 1500.0:
        return ("tier1", "Balance <= R1,500")
    elif balance <= 5000.0:
        return ("tier2", "R1,500 < Balance <= R5,000")
    else:
        return ("tier3", "Balance > R5,000")


def get_prelegal_discount(days_overdue: int, balance: float, is_settlement: bool = True) -> int:
    """
    Get discount percentage based on days overdue and balance tier.

    Uses the DISCOUNT_MANDATE_TABLE thresholds:
    - Tier 1: Balance <= R1,500
    - Tier 2: R1,500 < Balance <= R5,000
    - Tier 3: Balance > R5,000

    Pre-Legal tiered discounts by days overdue:
    - 150 days: 30% / 35% / 40%
    - 180 days: 40% / 45% / 50%
    - 210 days: 60% / 65% / 70%

    Args:
        days_overdue: Number of days account is overdue
        balance: Outstanding balance amount
        is_settlement: True for settlement discount, False for installment (10% less)

    Returns:
        Discount percentage (0 if not eligible)
    """
    # Determine base discount based on days overdue and balance tier
    tier_name, _ = get_balance_tier(balance)

    base_discount = 0
    if days_overdue >= 210:
        # 210+ days tier
        if tier_name == "tier1":
            base_discount = 60
        elif tier_name == "tier2":
            base_discount = 65
        else:  # tier3
            base_discount = 70
    elif days_overdue >= 180:
        # 180-209 days tier
        if tier_name == "tier1":
            base_discount = 40
        elif tier_name == "tier2":
            base_discount = 45
        else:  # tier3
            base_discount = 50
    elif days_overdue >= 150:
        # 150-179 days tier
        if tier_name == "tier1":
            base_discount = 30
        elif tier_name == "tier2":
            base_discount = 35
        else:  # tier3
            base_discount = 40
    else:
        return 0  # Not eligible

    # For installment plans, reduce discount by 5%
    if not is_settlement:
        base_discount = max(0, base_discount - 5)

    return base_discount


def calculate_discount(
    script_type: str,
    balance: float,
    overdue_days: int,
    payment_type: str = "settlement"
) -> Optional[Dict[str, Any]]:
    """
    Calculate discount based on script type, balance, and overdue days.

    Args:
        script_type: Type of script (e.g., 'prelegal_120', 'recently_suspended_120')
        balance: Outstanding balance amount
        overdue_days: Number of days account is overdue
        payment_type: 'settlement' or 'installment' (for scripts with payment-specific discounts)

    Returns:
        Dictionary containing:
        - percentage: Discount percentage
        - amount: Discount amount in currency
        - deadline: Offer expiry date (7 days from today)
        - discounted_balance: Final amount after discount
        Returns None if no discount applies
    """
    # Check if script type supports discounts
    script_config = SCRIPT_TYPES.get(script_type)
    if not script_config or not script_config.get("discount_enabled"):
        return None

    # Handle recently_suspended_120 special case (flat percentage from config)
    if script_type == "recently_suspended_120":
        if payment_type == "settlement":
            percentage = script_config.get("discount_percentage")
        else:  # installment
            percentage = script_config.get("installment_discount")

        if not percentage:
            return None

        discount_amount = balance * (percentage / 100)

        return {
            "percentage": percentage,
            "amount": round(discount_amount, 2),
            "discounted_balance": round(balance - discount_amount, 2),
            "deadline": date.today() + timedelta(days=7),
            "payment_type": payment_type,
        }

    # Handle legal_stage and booksale_stage (tiered by balance and payment type)
    if script_type in ["legal_stage", "booksale_stage"]:
        # Get the appropriate tier matrix based on payment type
        discount_key = f"{payment_type}_discount"
        tier_matrix = script_config.get(discount_key)
        if not tier_matrix:
            return None

        # Find applicable balance tier
        percentage = None
        for tier_name, tier_config in tier_matrix.items():
            max_bal = tier_config.get("max_balance")
            min_bal = tier_config.get("min_balance", 0)

            if max_bal and balance <= max_bal:
                percentage = tier_config["percentage"]
                break
            elif min_bal and balance >= min_bal:
                percentage = tier_config["percentage"]
                break

        if percentage is None:
            return None

        discount_amount = balance * (percentage / 100)

        return {
            "percentage": percentage,
            "amount": round(discount_amount, 2),
            "discounted_balance": round(balance - discount_amount, 2),
            "deadline": date.today() + timedelta(days=7),
            "payment_type": payment_type,
            "tier": get_balance_tier(balance)[0],
        }

    # Get discount tiers for script type
    discount_tiers = get_discount_tiers(script_type)
    if not discount_tiers:
        # Use fixed discount from script config if available
        fixed_percentage = script_config.get("discount_percentage")
        if fixed_percentage:
            discount_amount = balance * (fixed_percentage / 100)
            return {
                "percentage": fixed_percentage,
                "amount": round(discount_amount, 2),
                "discounted_balance": round(balance - discount_amount, 2),
                "deadline": date.today() + timedelta(days=7),
            }
        return None

    # Determine overdue tier for prelegal scripts
    if script_type in ["prelegal_120", "prelegal_150"]:
        if overdue_days >= 210:
            tier_key = "210_plus"
        elif overdue_days >= 180:
            tier_key = "180_plus"
        elif overdue_days >= 150:
            tier_key = "150_plus"
        else:
            return None  # Not eligible for discount yet

        tier_matrix = discount_tiers.get(tier_key)
        if not tier_matrix:
            return None
    else:
        # Other scripts may use "all" tier
        tier_matrix = discount_tiers.get("all", {})
        tier_key = "all"

    # Find applicable balance tier
    percentage = None
    for tier_name, tier_config in tier_matrix.items():
        max_bal = tier_config.get("max_balance")
        min_bal = tier_config.get("min_balance", 0)

        if max_bal and balance <= max_bal:
            percentage = tier_config["percentage"]
            break
        elif min_bal and balance >= min_bal:
            percentage = tier_config["percentage"]
            break

    if percentage is None:
        return None

    discount_amount = balance * (percentage / 100)

    return {
        "percentage": percentage,
        "amount": round(discount_amount, 2),
        "discounted_balance": round(balance - discount_amount, 2),
        "deadline": date.today() + timedelta(days=7),
        "overdue_tier": tier_key,
    }


def get_installment_months(balance: float) -> int:
    """
    Calculate minimum number of installment months based on balance.

    Args:
        balance: Outstanding balance amount

    Returns:
        Minimum number of months required for installment plan
    """
    if balance <= INSTALLMENT_RULES["tier1"]["max_balance"]:
        return INSTALLMENT_RULES["tier1"]["min_months"]
    elif balance <= INSTALLMENT_RULES["tier2"]["max_balance"]:
        return INSTALLMENT_RULES["tier2"]["min_months"]
    else:
        return INSTALLMENT_RULES["tier3"]["min_months"]


def calculate_installment(
    balance: float,
    discount_pct: float = 0.0,
    months: Optional[int] = None,
    subscription: float = 0.0,
    debicheck_fee: float = 10.0,
    apply_debicheck: bool = True,
) -> Dict[str, Any]:
    """
    Calculate monthly installment amount including fees and subscription.

    Args:
        balance: Outstanding balance amount
        discount_pct: Discount percentage to apply (0-100)
        months: Number of months for installment plan (if None, calculates minimum)
        subscription: Monthly subscription amount to include
        debicheck_fee: DebiCheck fee per month
        apply_debicheck: Whether to include DebiCheck fee

    Returns:
        Dictionary containing:
        - original_balance: Original balance before discount
        - discount_percentage: Applied discount percentage
        - discount_amount: Discount amount
        - discounted_balance: Balance after discount
        - months: Number of installment months
        - base_installment: Installment amount for debt only
        - subscription: Monthly subscription amount
        - debicheck_fee: DebiCheck fee (if applicable)
        - total_installment: Total monthly payment
        - total_paid: Total amount paid over all months
    """
    # Calculate discounted balance
    discount_amount = balance * (discount_pct / 100)
    discounted_balance = balance - discount_amount

    # Determine installment months
    if months is None:
        months = get_installment_months(discounted_balance)

    # Validate minimum months requirement
    min_months = get_installment_months(discounted_balance)
    if months < min_months:
        months = min_months

    # Calculate base installment (debt portion only)
    base_installment = discounted_balance / months

    # Calculate total monthly payment
    monthly_fees = debicheck_fee if apply_debicheck else 0.0
    total_installment = base_installment + subscription + monthly_fees

    # Calculate total amount to be paid
    total_paid = (total_installment * months)

    return {
        "original_balance": round(balance, 2),
        "discount_percentage": discount_pct,
        "discount_amount": round(discount_amount, 2),
        "discounted_balance": round(discounted_balance, 2),
        "months": months,
        "base_installment": round(base_installment, 2),
        "subscription": round(subscription, 2),
        "debicheck_fee": round(monthly_fees, 2),
        "total_installment": round(total_installment, 2),
        "total_paid": round(total_paid, 2),
        "breakdown": {
            "debt_portion": round(base_installment, 2),
            "subscription": round(subscription, 2),
            "fees": round(monthly_fees, 2),
        }
    }


def validate_payment_plan(
    script_type: str,
    months: int,
    balance: float,
) -> Dict[str, Any]:
    """
    Validate if a payment plan meets business rules.

    Args:
        script_type: Type of script
        months: Proposed number of months
        balance: Balance amount

    Returns:
        Dictionary containing:
        - valid: Boolean indicating if plan is valid
        - reason: Explanation if invalid
        - min_months: Minimum months required
        - max_months: Maximum months allowed
    """
    script_config = SCRIPT_TYPES.get(script_type)
    if not script_config:
        return {
            "valid": False,
            "reason": f"Unknown script type: {script_type}",
        }

    # Check maximum months constraint from script config
    max_months = script_config.get("max_payments", 6)
    if months > max_months:
        return {
            "valid": False,
            "reason": f"Exceeds maximum of {max_months} months for {script_type}",
            "max_months": max_months,
        }

    # Check minimum months based on balance
    min_months = get_installment_months(balance)
    if months < min_months:
        return {
            "valid": False,
            "reason": f"Balance requires minimum {min_months} months",
            "min_months": min_months,
        }

    return {
        "valid": True,
        "min_months": min_months,
        "max_months": max_months,
    }
