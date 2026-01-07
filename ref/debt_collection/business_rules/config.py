"""
Configuration and Constants for Debt Collection Business Rules

Defines authorities, script types, fees, and installment rules used throughout
the debt collection process.
"""

from datetime import date, time, timedelta
from typing import Dict, Any


# Authority contact information
AUTHORITIES: Dict[str, Dict[str, str]] = {
    "cartrack": {
        "name": "Cartrack Accounts Department",
        "contact": "011-250-3000",
    },
    "viljoen": {
        "name": "Viljoen Attorneys",
        "contact": "010-140-0085",
    },
}


# Script type configurations
SCRIPT_TYPES: Dict[str, Dict[str, Any]] = {
    # Ratio 1 scripts (Cartrack Accounts)
    # NOTE: discount_enabled=False and discount_percentage=0 reflects current call scripts
    # which do not include discount offers.
    # max_payments=2 reflects payment portal arrangement (next payment within 30 days)
    "ratio1_inflow": {
        "authority": "cartrack",
        "discount_enabled": False,
        "max_payments": 2,
        "discount_percentage": 0,
        "consequence_level": "none",
        "description": "Ratio 1 Inflow - New accounts",
    },
    "ratio1_failed_ptp": {
        "authority": "cartrack",
        "discount_enabled": False,
        "max_payments": 2,
        "discount_percentage": 0,
        "consequence_level": "none",
        "description": "Ratio 1 Failed PTP - Broken payment promises",
    },
    "ratio1_short_paid": {
        "authority": "cartrack",
        "discount_enabled": False,
        "max_payments": 2,
        "discount_percentage": 0,
        "consequence_level": "none",
        "description": "Ratio 1 Short Paid - Partial payments received",
    },
    "ratio1_pro_rata": {
        "authority": "cartrack",
        "discount_enabled": False,
        "max_payments": 2,
        "consequence_level": "none",
        "description": "Ratio 1 Pro Rata - Proportional payment arrangements",
    },

    # Ratio 2-3 scripts (Cartrack Accounts)
    # NOTE: discount_enabled=False and discount_percentage=0 reflects current call scripts
    # which do not include discount offers.
    # max_payments=2 reflects payment portal arrangement (next payment within 30 days)
    "ratio2_3_inflow": {
        "authority": "cartrack",
        "discount_enabled": False,
        "max_payments": 2,
        "discount_percentage": 0,
        "consequence_level": "warning",
        "description": "Ratio 2-3 Inflow - New accounts higher risk",
    },
    "ratio2_3_failed_ptp": {
        "authority": "cartrack",
        "discount_enabled": False,
        "max_payments": 2,
        "discount_percentage": 0,
        "consequence_level": "warning",
        "description": "Ratio 2-3 Failed PTP - Broken promises higher risk",
    },
    "ratio2_3_short_paid": {
        "authority": "cartrack",
        "discount_enabled": False,
        "max_payments": 2,
        "discount_percentage": 0,
        "consequence_level": "warning",
        "description": "Ratio 2-3 Short Paid - Partial payments higher risk",
    },

    # Recently suspended scripts (Cartrack Accounts)
    "recently_suspended_120": {
        "authority": "cartrack",
        "discount_enabled": True,
        "max_payments": 3,
        "discount_percentage": 50,  # Settlement discount
        "installment_discount": 40,  # Installment discount
        "consequence_level": "prelegal",
        "description": "Recently Suspended 120 - Accounts suspended within 120 days",
        "deadline_days": {
            "tier1": 25,  # Tier 1 (50% discount) deadline
            "tier2": 28,  # Tier 2 (40% discount) deadline
        },
    },

    # Pre-legal scripts (Viljoen Attorneys)
    "prelegal_120": {
        "authority": "viljoen",
        "discount_enabled": True,
        "max_payments": 3,
        "consequence_level": "prelegal",
        "description": "Pre-Legal 120 - Accounts 120+ days overdue, attorney stage",
        "discount_tiers": {
            "210_plus": {  # 210+ days overdue
                "tier1": {"max_balance": 1500.0, "percentage": 60},
                "tier2": {"min_balance": 1500.01, "max_balance": 5000.0, "percentage": 65},
                "tier3": {"min_balance": 5000.01, "percentage": 70},
            },
            "180_plus": {  # 180-209 days overdue
                "tier1": {"max_balance": 1500.0, "percentage": 40},
                "tier2": {"min_balance": 1500.01, "max_balance": 5000.0, "percentage": 45},
                "tier3": {"min_balance": 5000.01, "percentage": 50},
            },
            "150_plus": {  # 150-179 days overdue
                "tier1": {"max_balance": 1500.0, "percentage": 30},
                "tier2": {"min_balance": 1500.01, "max_balance": 5000.0, "percentage": 35},
                "tier3": {"min_balance": 5000.01, "percentage": 40},
            },
        },
    },
    "prelegal_150": {
        "authority": "viljoen",
        "discount_enabled": True,
        "max_payments": 3,
        "consequence_level": "attorney",
        "description": "Pre-Legal 150 - Accounts 150+ days overdue, attorney stage",
        "discount_tiers": {
            "210_plus": {
                "tier1": {"max_balance": 1500.0, "percentage": 60},
                "tier2": {"min_balance": 1500.01, "max_balance": 5000.0, "percentage": 65},
                "tier3": {"min_balance": 5000.01, "percentage": 70},
            },
            "180_plus": {
                "tier1": {"max_balance": 1500.0, "percentage": 40},
                "tier2": {"min_balance": 1500.01, "max_balance": 5000.0, "percentage": 45},
                "tier3": {"min_balance": 5000.01, "percentage": 50},
            },
            "150_plus": {
                "tier1": {"max_balance": 1500.0, "percentage": 30},
                "tier2": {"min_balance": 1500.01, "max_balance": 5000.0, "percentage": 35},
                "tier3": {"min_balance": 5000.01, "percentage": 40},
            },
        },
    },

    # Legal stage scripts (Viljoen Attorneys)
    "legal_stage": {
        "authority": "viljoen",
        "discount_enabled": True,
        "settlement_discount": {
            "tier1": 70,  # Balance <= R1,500
            "tier2": 75,  # R1,500 < Balance <= R5,000
            "tier3": 75,  # Balance > R5,000
        },
        "installment_discount": {
            "tier1": 65,
            "tier2": 70,
            "tier3": 70,
        },
        "max_payments": 6,
        "consequence_level": "legal",
        "description": "Legal stage - court proceedings initiated",
    },
    "booksale_stage": {
        "authority": "viljoen",
        "discount_enabled": True,
        "settlement_discount": {
            "tier1": 75,  # Balance <= R1,500
            "tier2": 80,  # R1,500 < Balance <= R5,000
            "tier3": 80,  # Balance > R5,000
        },
        "installment_discount": {
            "tier1": 70,
            "tier2": 75,
            "tier3": 75,
        },
        "max_payments": 6,
        "consequence_level": "booksale",
        "description": "Booksale stage - final collection before write-off",
    },
}


# Fee structure
FEES: Dict[str, float] = {
    "DEBICHECK_FEE": 10.0,  # Per month for DebiCheck payment method
    "CREDIT_CLEARANCE_FEE": 1800.0,  # One-time fee for credit bureau clearance
    "RECOVERY_FEE": 25000.0,  # Fee for vehicle recovery process
}


# Business hours configuration
BUSINESS_HOURS = {
    "start": time(7, 0),   # 07:00
    "end": time(18, 0),    # 18:00
    "days": [0, 1, 2, 3, 4, 5],  # Monday=0 to Saturday=5 (Sunday=6 excluded)
    "closing_buffer_minutes": 30,  # No calls within 30 min of closing
}


# Installment payment rules based on balance
INSTALLMENT_RULES: Dict[str, Any] = {
    "tier1": {
        "max_balance": 1500.0,
        "min_months": 3,
        "description": "Balances up to R1,500 - minimum 3 months",
    },
    "tier2": {
        "min_balance": 1500.01,
        "max_balance": 5000.0,
        "min_months": 4,
        "description": "Balances R1,500-R5,000 - minimum 4 months",
    },
    "tier3": {
        "min_balance": 5000.01,
        "min_months": 6,
        "description": "Balances above R5,000 - minimum 6 months",
    },
}


def get_script_config(script_type: str) -> Dict[str, Any] | None:
    """
    Get configuration for a specific script type.

    Args:
        script_type: The script type identifier

    Returns:
        Configuration dict or None if script type not found
    """
    return SCRIPT_TYPES.get(script_type)


def get_authority_info(authority_key: str) -> Dict[str, str] | None:
    """
    Get authority contact information.

    Args:
        authority_key: The authority identifier (cartrack/viljoen)

    Returns:
        Authority info dict or None if not found
    """
    return AUTHORITIES.get(authority_key)


def get_fee(fee_type: str) -> float | None:
    """
    Get fee amount by type.

    Args:
        fee_type: The fee type (DEBICHECK_FEE, CREDIT_CLEARANCE_FEE, RECOVERY_FEE)

    Returns:
        Fee amount or None if not found
    """
    return FEES.get(fee_type)


def get_discount_tiers(script_type: str) -> Dict[str, Any] | None:
    """
    Get discount tier configuration for a specific script type.

    Args:
        script_type: The script type identifier

    Returns:
        Discount tiers dict or None if not found or not applicable
    """
    script_config = SCRIPT_TYPES.get(script_type)
    if not script_config:
        return None
    return script_config.get("discount_tiers")


def get_campaign_deadline(tier: int, script_type: str = "recently_suspended_120") -> date:
    """
    Get campaign deadline for a script with deadline configuration.

    Default for recently_suspended_120:
    - Tier 1 (50% discount): 25th of current month
    - Tier 2 (40% discount): 28th of current month

    If current date is past the deadline, use next month.

    Args:
        tier: Campaign tier (1 or 2)
        script_type: Script type to get deadline configuration from

    Returns:
        Campaign deadline date
    """
    today = date.today()
    current_year = today.year
    current_month = today.month

    # Get deadline days from script configuration
    script_config = SCRIPT_TYPES.get(script_type, {})
    deadline_days_config = script_config.get("deadline_days", {"tier1": 25, "tier2": 28})
    deadline_day = deadline_days_config.get(f"tier{tier}", 25 if tier == 1 else 28)

    # Try to create deadline in current month
    try:
        deadline = date(current_year, current_month, deadline_day)
    except ValueError:
        # Handle months with fewer days (e.g., February)
        # Use last day of the month
        if current_month == 12:
            deadline = date(current_year + 1, 1, 1) - timedelta(days=1)
        else:
            deadline = date(current_year, current_month + 1, 1) - timedelta(days=1)

    # If we're past the deadline, move to next month
    if today > deadline:
        if current_month == 12:
            next_month = 1
            next_year = current_year + 1
        else:
            next_month = current_month + 1
            next_year = current_year

        try:
            deadline = date(next_year, next_month, deadline_day)
        except ValueError:
            # Handle months with fewer days
            if next_month == 12:
                deadline = date(next_year + 1, 1, 1) - timedelta(days=1)
            else:
                deadline = date(next_year, next_month + 1, 1) - timedelta(days=1)

    return deadline
