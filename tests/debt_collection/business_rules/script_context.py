"""
Script Context Generator for Debt Collection Voice Agents

This module builds dynamic context for agent prompts based on debtor profile
and script type. It generates reason-for-call messages, consequences, benefits,
third-party messages, and complete context dictionaries for negotiation and
payment agents.

The context is used to personalize agent instructions with specific amounts,
dates, script-type requirements, and discount offers.
"""

from typing import Dict, List, Optional, Any
from datetime import date, timedelta
from shared_state import UserData
from .config import (
    AUTHORITIES,
    SCRIPT_TYPES,
    FEES,
    get_script_config,
    get_authority_info,
)
from .discount_calculator import calculate_discount, calculate_installment


def get_reason_for_call(userdata: UserData) -> str:
    """
    Generate reason for call message based on script type and debtor profile.

    Args:
        userdata: UserData object containing debtor profile and call state

    Returns:
        Formatted reason for call message for the agent to communicate
    """
    debtor = userdata.debtor
    script_type = userdata.call.script_type
    amount = debtor.outstanding_amount or 0.0
    amount_str = f"R{amount:,.2f}"

    # Ratio 1 scripts - Cartrack Accounts
    if script_type == "ratio1_inflow":
        return (
            f"We did not receive your subscription payment and your account is now overdue. "
            f"An immediate payment of {amount_str} is required."
        )

    elif script_type == "ratio1_failed_ptp":
        return (
            f"We did not receive your payment of {amount_str} as per our last arrangement with you "
            f"and your account is overdue."
        )

    elif script_type == "ratio1_short_paid":
        # Extract actual paid amount from debtor profile
        partial_payment = debtor.partial_payment_received
        agreed_amt = debtor.agreed_amount

        if partial_payment is not None and agreed_amt is not None:
            partial_str = f"R{partial_payment:,.2f}"
            agreed_str = f"R{agreed_amt:,.2f}"
            shortfall = debtor.shortfall_amount
            shortfall_str = f"R{shortfall:,.2f}" if shortfall else amount_str

            return (
                f"We received a payment of {partial_str}, but this was less than the agreed amount of {agreed_str}. "
                f"The shortfall is {shortfall_str} and your total outstanding balance is {amount_str}."
            )
        else:
            # Fallback if payment details not available
            return (
                f"We received a payment but this was less than the agreed amount. "
                f"Your outstanding balance is {amount_str}."
            )

    elif script_type == "ratio1_pro_rata":
        return (
            f"This is a pro rata payment for your new customer setup. "
            f"An immediate payment of {amount_str} is required to activate your account."
        )

    # Ratio 2-3 scripts - Higher risk accounts
    elif script_type.startswith("ratio2_3"):
        return (
            f"Your account is overdue for more than 2 months with a balance of {amount_str}. "
            f"Immediate payment is required to bring your account up to date."
        )

    # Recently suspended - Campaign with discounts
    elif script_type == "recently_suspended_120":
        return (
            f"Your account has been overdue for more than 4 months and is in our pre-legal department. "
            f"A letter of demand has been sent. Immediate payment of {amount_str} is required. "
            f"This is a special campaign offering settlement and installment discounts."
        )

    # Pre-legal scripts - Viljoen Attorneys
    elif script_type in ["prelegal_120", "prelegal_150"]:
        authority = get_authority_info("viljoen")
        authority_name = authority["name"] if authority else "our attorneys"
        return (
            f"Your account has been handed over to {authority_name} due to non-payment. "
            f"Your total arrears are {amount_str}. A letter of demand has been sent."
        )

    # Default fallback
    return (
        f"Your account has an outstanding balance of {amount_str}. "
        f"We need to discuss payment arrangements."
    )


def get_consequences(userdata: UserData) -> List[str]:
    """
    Generate consequences of non-payment based on account status and script type.

    Args:
        userdata: UserData object containing debtor profile and call state

    Returns:
        List of consequence statements for the agent to communicate
    """
    debtor = userdata.debtor
    script_type = userdata.call.script_type
    account_status = debtor.account_status or "active"
    consequences = []

    recovery_fee_str = f"R{FEES['RECOVERY_FEE']:,.2f}"
    clearance_fee_str = f"R{FEES['CREDIT_CLEARANCE_FEE']:,.2f}"

    # Active account consequences
    if account_status.lower() in ["active", "overdue"]:
        # Service suspensions
        consequences.append("Your Cartrack App access will be suspended")
        consequences.append("Vehicle positioning through control room will be unavailable")
        consequences.append("Vehicle notifications will be suspended")

        # Risk-based consequences
        if script_type.startswith("ratio2_3") or "suspended" in script_type or "prelegal" in script_type:
            consequences.append(
                f"If your vehicle is stolen or hijacked, you may be charged a recovery fee of up to {recovery_fee_str}"
            )

        # Credit bureau consequences for pre-legal and suspended accounts
        if "prelegal" in script_type or "suspended" in script_type:
            consequences.append(
                f"You have been or will be listed as a default payer on your credit profile"
            )
            consequences.append(
                f"A clearance fee of {clearance_fee_str} applies if you wish to clear the listing after settling"
            )

        # Legal escalation for serious cases
        if "prelegal" in script_type:
            consequences.append("Failure to pay will result in legal action and summons")
            consequences.append("Additional legal fees and court costs will apply")

    # Cancelled account consequences
    else:
        consequences.append("Services remain suspended and your account is overdue")

        # Credit profile impact
        if "prelegal" in script_type or "suspended" in script_type:
            consequences.append("You have been listed as a default payer on your credit profile")
            consequences.append("This listing will make it difficult to get credit approved")
            consequences.append(
                f"A clearance fee of {clearance_fee_str} applies if you wish to clear the listing"
            )

        # Legal consequences
        if "prelegal" in script_type or script_type.startswith("ratio2_3"):
            consequences.append("Failure to pay will result in handover to attorneys")
            consequences.append("Legal action and summons will be issued")
            consequences.append("Additional legal fees will be added to your balance")
            consequences.append("You will lose the ability to settle the account")

    return consequences


def get_benefits(userdata: UserData) -> List[str]:
    """
    Generate benefits of payment based on account status and payment type.

    Args:
        userdata: UserData object containing debtor profile and call state

    Returns:
        List of benefit statements for the agent to communicate
    """
    debtor = userdata.debtor
    script_type = userdata.call.script_type
    account_status = debtor.account_status or "active"
    payment_type = userdata.call.payment_type or "settlement"
    benefits = []

    # Active account benefits
    if account_status.lower() in ["active", "overdue"]:
        if payment_type == "settlement":
            # Full settlement benefits
            benefits.append("Your account will be brought up to date")
            benefits.append("Legal action will be stopped immediately")
            benefits.append("All Cartrack services will be reinstated")
            benefits.append("Cartrack App access restored")
            benefits.append("Vehicle positioning through control room restored")
            benefits.append("Vehicle notifications restored")
            benefits.append("No recovery fee if vehicle is stolen or hijacked")

        else:  # installment/arrangement
            # Installment arrangement benefits
            benefits.append("Legal action will be put on hold while you are paying")
            benefits.append("All Cartrack services will be reinstated after first payment")
            benefits.append("Account will be brought up to date upon completion")
            benefits.append("No recovery fee if vehicle is stolen or hijacked")

    # Cancelled account benefits
    else:
        if payment_type == "settlement":
            # Settlement for cancelled account
            benefits.append("Your account will be closed and settled")
            benefits.append("Legal action will be stopped immediately")
            benefits.append("A paid-up letter will be provided as proof of zero balance")
            benefits.append("You can request credit bureau clearance")

        else:  # installment
            # Installment for cancelled account
            benefits.append("Legal action will be put on hold while you are paying")
            benefits.append("Account will be closed upon completion of all payments")
            benefits.append("A paid-up letter will be provided after final payment")
            benefits.append("You can request credit bureau clearance after settling")

    return benefits


def get_third_party_message(userdata: UserData) -> str:
    """
    Generate third-party contact message based on authority handling the account.

    Args:
        userdata: UserData object containing debtor profile and call state

    Returns:
        Formatted message to leave with third party contacts
    """
    debtor = userdata.debtor
    script_type = userdata.call.script_type
    name = debtor.full_name

    # Determine which authority is handling the account
    script_config = get_script_config(script_type)
    if not script_config:
        # Default to Cartrack
        authority_key = "cartrack"
    else:
        authority_key = script_config.get("authority", "cartrack")

    authority = get_authority_info(authority_key)

    if authority_key == "viljoen":
        return (
            f"Please advise {name} that Cartrack's Attorneys called regarding an outstanding "
            f"Cartrack account. Ask them to contact {authority['name']} urgently on "
            f"{authority['contact']} to resolve the outstanding matter."
        )
    else:
        return (
            f"Please advise {name} that Cartrack called regarding an outstanding account. "
            f"Ask them to contact Cartrack urgently on {authority['contact']} to resolve "
            f"the outstanding matter."
        )


def build_negotiation_context(userdata: UserData) -> Dict[str, Any]:
    """
    Build complete negotiation context for agent prompt injection.

    Combines reason for call, consequences, benefits, discount info, and payment
    parameters into a single context dictionary.

    Args:
        userdata: UserData object containing debtor profile and call state

    Returns:
        Dictionary containing:
        - reason_for_call: str
        - consequences: List[str]
        - benefits: List[str]
        - discount: Optional[Dict] - discount details if applicable
        - max_payments: int - maximum installment months allowed
        - third_party_message: str
    """
    debtor = userdata.debtor
    script_type = userdata.call.script_type
    balance = debtor.outstanding_amount or 0.0
    overdue_days = debtor.overdue_days or 0

    context = {
        "reason_for_call": get_reason_for_call(userdata),
        "consequences": get_consequences(userdata),
        "benefits": get_benefits(userdata),
        "third_party_message": get_third_party_message(userdata),
    }

    # Add script configuration
    script_config = get_script_config(script_type)
    if script_config:
        context["max_payments"] = script_config.get("max_payments", 6)
    else:
        context["max_payments"] = 6

    # Calculate and add discount information if applicable
    discount_info = calculate_discount(
        script_type=script_type,
        balance=balance,
        overdue_days=overdue_days,
        payment_type="settlement"
    )

    if discount_info:
        context["discount"] = {
            "percentage": discount_info["percentage"],
            "amount": discount_info["amount"],
            "discounted_balance": discount_info["discounted_balance"],
            "deadline": discount_info["deadline"].strftime("%B %d, %Y"),
            "settlement_amount": f"R{discount_info['discounted_balance']:,.2f}",
        }

        # Also check installment discount for recently_suspended_120
        if script_type == "recently_suspended_120":
            installment_discount = calculate_discount(
                script_type=script_type,
                balance=balance,
                overdue_days=overdue_days,
                payment_type="installment"
            )
            if installment_discount:
                context["discount"]["installment_percentage"] = installment_discount["percentage"]
                context["discount"]["installment_discounted_balance"] = installment_discount["discounted_balance"]
    else:
        context["discount"] = None

    return context


def build_payment_context(userdata: UserData) -> Dict[str, Any]:
    """
    Build payment context for payment agent prompt injection.

    Args:
        userdata: UserData object containing debtor profile and call state

    Returns:
        Dictionary containing:
        - payment_type: str - settlement/installment/arrangement
        - arrangement_details: Optional[Dict] - installment calculation details
        - debicheck_fee: float
        - subscription_amount: float
        - portal_options: List[str]
    """
    debtor = userdata.debtor
    call_state = userdata.call

    context = {
        "payment_type": call_state.payment_type or "settlement",
        "debicheck_fee": FEES["DEBICHECK_FEE"],
        "subscription_amount": debtor.monthly_subscription or 0.0,
        "portal_options": [
            "Credit/Debit Card",
            "Instant EFT",
            "SnapScan",
            "Zapper",
        ],
    }

    # Add arrangement details if payment type is installment
    if call_state.payment_type in ["installment", "arrangement"] and call_state.payment_arrangements:
        # Get the most recent arrangement
        arrangement = call_state.payment_arrangements[-1]
        context["arrangement_details"] = arrangement

        # Calculate installment breakdown
        balance = debtor.outstanding_amount or 0.0
        discount_pct = 0.0

        # Check if discount was accepted
        if call_state.discount_accepted and call_state.discount_amount:
            discount_pct = (call_state.discount_amount / balance) * 100

        # Calculate installment details
        installment_calc = calculate_installment(
            balance=balance,
            discount_pct=discount_pct,
            months=None,  # Will auto-calculate based on balance
            subscription=debtor.monthly_subscription or 0.0,
            debicheck_fee=FEES["DEBICHECK_FEE"],
            apply_debicheck=call_state.payment_method == "debicheck",
        )

        context["installment_calculation"] = installment_calc

    return context


def format_amount(amount: float) -> str:
    """
    Format currency amount for display.

    Args:
        amount: Amount to format

    Returns:
        Formatted string (e.g., "R1,234.56")
    """
    return f"R{amount:,.2f}"


def format_date(date_obj: date) -> str:
    """
    Format date for display.

    Args:
        date_obj: Date object to format

    Returns:
        Formatted string (e.g., "December 5, 2025")
    """
    return date_obj.strftime("%B %d, %Y")


def calculate_payment_deadline(months_from_now: int = 0, day_of_month: int = 25) -> date:
    """
    Calculate payment deadline date.

    Args:
        months_from_now: Number of months to add to current date
        day_of_month: Day of month for deadline (default: 25)

    Returns:
        Date object for the deadline
    """
    today = date.today()

    # Calculate target month
    target_month = today.month + months_from_now
    target_year = today.year

    # Handle year rollover
    while target_month > 12:
        target_month -= 12
        target_year += 1

    # Handle day of month overflow (e.g., February 30)
    try:
        deadline = date(target_year, target_month, day_of_month)
    except ValueError:
        # Use last day of month if day doesn't exist
        if target_month == 12:
            next_month = date(target_year + 1, 1, 1)
        else:
            next_month = date(target_year, target_month + 1, 1)
        deadline = next_month - timedelta(days=1)

    return deadline


def build_complete_agent_context(userdata: UserData, agent_type: str = "negotiation") -> str:
    """
    Build complete formatted context string for agent instructions.

    Args:
        userdata: UserData object containing debtor profile and call state
        agent_type: Type of agent ("negotiation", "payment", "closing")

    Returns:
        Formatted multi-line string for injection into agent instructions
    """
    if agent_type == "negotiation":
        context = build_negotiation_context(userdata)

        lines = [
            "# Current Call Context",
            "",
            f"**Debtor:** {userdata.debtor.full_name}",
            f"**Outstanding Amount:** {format_amount(userdata.debtor.outstanding_amount or 0.0)}",
            f"**Overdue Days:** {userdata.debtor.overdue_days or 0}",
            f"**Script Type:** {userdata.call.script_type}",
            "",
            "## Reason for Call",
            context["reason_for_call"],
            "",
            "## Consequences of Non-Payment",
        ]

        for consequence in context["consequences"]:
            lines.append(f"- {consequence}")

        lines.append("")
        lines.append("## Benefits of Payment")

        for benefit in context["benefits"]:
            lines.append(f"- {benefit}")

        if context.get("discount"):
            discount = context["discount"]
            lines.append("")
            lines.append("## Discount Offer Available")
            lines.append(f"- Settlement Discount: {discount['percentage']}%")
            lines.append(f"- Settlement Amount: {discount['settlement_amount']}")
            lines.append(f"- Offer Deadline: {discount['deadline']}")

            if "installment_percentage" in discount:
                lines.append(f"- Installment Discount: {discount['installment_percentage']}%")

        lines.append("")
        lines.append(f"## Maximum Payment Installments: {context['max_payments']} months")

        return "\n".join(lines)

    elif agent_type == "payment":
        context = build_payment_context(userdata)

        lines = [
            "# Payment Processing Context",
            "",
            f"**Payment Type:** {context['payment_type']}",
            f"**DebiCheck Fee:** {format_amount(context['debicheck_fee'])} per month",
            f"**Monthly Subscription:** {format_amount(context['subscription_amount'])}",
            "",
            "## Payment Portal Options",
        ]

        for option in context["portal_options"]:
            lines.append(f"- {option}")

        if context.get("installment_calculation"):
            calc = context["installment_calculation"]
            lines.append("")
            lines.append("## Installment Breakdown")
            lines.append(f"- Original Balance: {format_amount(calc['original_balance'])}")

            if calc["discount_percentage"] > 0:
                lines.append(f"- Discount: {calc['discount_percentage']}% ({format_amount(calc['discount_amount'])})")
                lines.append(f"- Discounted Balance: {format_amount(calc['discounted_balance'])}")

            lines.append(f"- Number of Months: {calc['months']}")
            lines.append(f"- Debt Installment: {format_amount(calc['base_installment'])}")
            lines.append(f"- Subscription: {format_amount(calc['subscription'])}")
            lines.append(f"- DebiCheck Fee: {format_amount(calc['debicheck_fee'])}")
            lines.append(f"- **Total Monthly Payment: {format_amount(calc['total_installment'])}**")

        return "\n".join(lines)

    else:
        # Generic context for other agent types
        return userdata.summarize()
