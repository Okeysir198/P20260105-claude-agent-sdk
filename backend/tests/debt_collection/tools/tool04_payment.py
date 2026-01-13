"""Payment agent tools."""

from typing import Annotated, Optional, Literal
from pydantic import Field
from livekit.agents.llm import function_tool
from livekit.agents.voice import Agent, RunContext

from business_rules import FEES
from .common_tools import transfer_to_agent
from shared_state import UserData
from state.types import PaymentMethod, CallOutcome

RunContext_T = RunContext[UserData]


# South African banks whitelist
SA_BANKS = {
    "fnb", "first national bank", "wesbank",
    "standard bank", "sbsa",
    "absa", "absabank",
    "capitec", "capitec bank",
    "nedbank",
    "african bank",
    "investec",
    "tyme bank", "tymebank",
    "discovery bank",
    "bidvest bank"
}


def validate_bank_name(bank_name: str) -> tuple[bool, str]:
    """Validate bank name against South African bank whitelist."""
    normalized_name = bank_name.lower().strip()
    if normalized_name in SA_BANKS:
        return True, ""
    return False, f"Invalid bank name '{bank_name}'. Please provide a recognized South African bank."


def validate_branch_code(branch_code: str) -> tuple[bool, str]:
    """Validate South African bank branch code format (6 digits)."""
    cleaned_code = branch_code.strip()
    if not cleaned_code.isdigit():
        return False, "Branch code must contain only digits"
    if len(cleaned_code) != 6:
        return False, f"Branch code must be exactly 6 digits (got {len(cleaned_code)})"
    return True, ""


def validate_account_number(account_number: str) -> tuple[bool, str]:
    """Validate South African bank account number format (8-12 digits)."""
    cleaned_number = account_number.strip()
    if not cleaned_number.isdigit():
        return False, "Account number must contain only digits"
    if len(cleaned_number) < 8 or len(cleaned_number) > 12:
        return False, f"Account number must be 8-12 digits (got {len(cleaned_number)})"
    return True, ""


def validate_amount(amount: float) -> tuple[bool, str]:
    """Validate payment amount."""
    if amount <= 0:
        return False, "Amount must be positive"
    if amount > 1_000_000:
        return False, "Amount exceeds maximum limit of R1,000,000"
    return True, ""


@function_tool()
async def capture_immediate_debit(
    amount: Annotated[float, Field(description="Amount to debit immediately (same-day debit in Rands)")],
    context: RunContext_T,
) -> str:
    """
    Capture immediate same-day debit order payment.

    Usage: Call when customer agrees to immediate debit from their account.
    Requires existing bank details on file.
    """
    userdata = context.userdata

    is_valid, error_msg = validate_amount(amount)
    if not is_valid:
        return f"ERROR: {error_msg}"

    userdata.call.add_payment_arrangement(
        amount=amount,
        date="immediate",
        method="same_day_debit",
        description=f"Immediate same-day debit order for R{amount:.2f}"
    )
    userdata.call.payment_method = PaymentMethod.DEBIT_ORDER
    userdata.call.append_call_notes(f"Immediate debit captured: R{amount:.2f}")

    bank_name = userdata.debtor.bank_name or "your bank"
    account_number = userdata.debtor.bank_account_number or "on file"
    account_last4 = account_number[-4:] if userdata.debtor.bank_account_number and len(account_number) >= 4 else "XXXX"

    return f"Immediate debit of R{amount:.2f} has been captured from {bank_name} account ending in {account_last4}. The debit will process within 24 hours."


@function_tool()
async def validate_bank_details(
    bank_name: Annotated[str, Field(description="Bank name provided by customer (e.g., 'FNB', 'Standard Bank', 'Capitec')")],
    account_number: Annotated[str, Field(description="Bank account number provided by customer")],
    branch_code: Annotated[str, Field(description="Bank branch code provided by customer (6 digits)")],
    context: RunContext_T,
) -> str:
    """
    Validate bank details against existing records and payment history.

    Returns detailed status:
    - VALID: Details match records and no issues
    - SAME_AS_FAILED: Same details as previous failed debit (for failed_ptp scripts)
    - PREVIOUS_REVERSAL: Customer has history of payment reversals
    - DETAILS_CHANGED: Different from records on file
    - NEW_DETAILS: No previous records
    """
    userdata = context.userdata
    debtor = userdata.debtor

    # Validate input formats
    is_valid_bank, bank_error = validate_bank_name(bank_name)
    if not is_valid_bank:
        return f"ERROR: {bank_error}"

    is_valid_account, account_error = validate_account_number(account_number)
    if not is_valid_account:
        return f"ERROR: {account_error}"

    is_valid_branch, branch_error = validate_branch_code(branch_code)
    if not is_valid_branch:
        return f"ERROR: {branch_error}"

    # Normalize inputs
    provided_bank = bank_name.lower().strip()
    provided_account = account_number.strip()
    provided_branch = branch_code.strip()

    current_bank = (debtor.bank_name or "").lower().strip()
    current_account = (debtor.bank_account_number or "").strip()
    current_branch = (debtor.branch_code or "").strip()

    # Check if same as current records
    if provided_bank == current_bank and provided_account == current_account and provided_branch == current_branch:
        if debtor.has_reversal_history:
            return "PREVIOUS_REVERSAL: These details have a history of reversed debit orders. WARNING: I strongly recommend setting up DebiCheck instead, which requires your authentication and helps prevent failed payments. DebiCheck has an R10 monthly fee. Would you like to proceed with DebiCheck?"

        if "failed_ptp" in userdata.call.script_type:
            return "SAME_AS_FAILED: These are the same bank details from which our previous debit order was unsuccessful. Please confirm these details are correct and that you will have sufficient funds available on the agreed date. If you've changed banks, please provide your new banking information."

        return "VALID: Bank details verified successfully. You can proceed with payment setup."

    # Details are different from records
    if current_bank and current_account:
        return f"DETAILS_CHANGED: These details are different from what we have on file (was {current_bank.title()} account ending {current_account[-4:]}). I'll update your banking information in our system. Please use the update_bank_details tool to save these new details."

    return "NEW_DETAILS: No bank details on file. Please capture these new details using the update_bank_details tool before proceeding with payment setup."


@function_tool()
async def update_bank_details(
    bank_name: Annotated[str, Field(description="Bank name (e.g., 'FNB', 'Standard Bank', 'Capitec')")],
    account_number: Annotated[str, Field(description="Bank account number")],
    branch_code: Annotated[str, Field(description="Bank branch code (6 digits)")],
    context: RunContext_T,
) -> str:
    """
    Update customer's bank details in the system.

    Usage: Call after validate_bank_details indicates DETAILS_CHANGED or NEW_DETAILS,
    and customer confirms the new banking information.

    NOTE: DebtorProfile is frozen (immutable). Updated bank details are stored in
    CallState and payment arrangements for the CRM system to process.
    """
    userdata = context.userdata

    # Validate all inputs
    is_valid_bank, bank_error = validate_bank_name(bank_name)
    if not is_valid_bank:
        return f"ERROR: {bank_error}"

    is_valid_account, account_error = validate_account_number(account_number)
    if not is_valid_account:
        return f"ERROR: {account_error}"

    is_valid_branch, branch_error = validate_branch_code(branch_code)
    if not is_valid_branch:
        return f"ERROR: {branch_error}"

    userdata.call.add_payment_arrangement(
        amount=0.0,
        date="n/a",
        method="bank_details_update",
        description=f"Updated banking details: {bank_name}, Account: {account_number}, Branch: {branch_code}"
    )

    userdata.call.bank_details_updated = True
    userdata.call.append_call_notes(f"Bank details updated - Bank: {bank_name}, Account: ***{account_number[-4:]}, Branch: {branch_code}")

    return f"Bank details updated: {bank_name} account {account_number} (Branch: {branch_code}). You can now proceed with payment setup."


@function_tool()
async def setup_debicheck(
    amount: Annotated[float, Field(description="Monthly debit amount (in Rands)")],
    date: Annotated[int, Field(description="Day of month for debit (1-31, typically 25 for salary date)")],
    bank_name: Annotated[str, Field(description="Bank name for DebiCheck mandate")],
    account_number: Annotated[str, Field(description="Account number for DebiCheck mandate")],
    context: RunContext_T,
) -> str:
    """
    Setup DebiCheck mandate for recurring payments.

    DebiCheck is a secure debit order authentication system that prevents unauthorized debits.
    Customer will receive an SMS to authenticate the mandate.

    NOTE: R10 monthly fee applies for DebiCheck service.
    """
    userdata = context.userdata

    is_valid, error_msg = validate_amount(amount)
    if not is_valid:
        return f"ERROR: {error_msg}"

    if not isinstance(date, int) or date < 1 or date > 31:
        return "ERROR: Day of month must be between 1 and 31"

    is_valid_bank, bank_error = validate_bank_name(bank_name)
    if not is_valid_bank:
        return f"ERROR: {bank_error}"

    is_valid_account, account_error = validate_account_number(account_number)
    if not is_valid_account:
        return f"ERROR: {account_error}"

    userdata.call.add_payment_arrangement(
        amount=amount,
        date=str(date),
        method="debicheck",
        description=f"DebiCheck mandate: R{amount:.2f} on day {date} of each month from {bank_name} {account_number[-4:]}"
    )

    userdata.call.debicheck_sent = True
    userdata.call.payment_method = PaymentMethod.DEBICHECK
    userdata.call.append_call_notes(f"DebiCheck initiated: R{amount:.2f} on day {date}, {bank_name}")

    fee = FEES.get("DEBICHECK_FEE", 10.0)

    ordinal_suffix = "th"
    if date in [1, 21, 31]:
        ordinal_suffix = "st"
    elif date in [2, 22]:
        ordinal_suffix = "nd"
    elif date in [3, 23]:
        ordinal_suffix = "rd"

    return f"DebiCheck mandate has been initiated for R{amount:.2f} on the {date}{ordinal_suffix} of each month from {bank_name} account ending {account_number[-4:]}. The customer will receive an SMS to authenticate this mandate within the next 30 minutes. Please remind them to approve it. Monthly DebiCheck fee: R{fee:.2f}."


@function_tool()
async def send_portal_link(context: RunContext_T) -> str:
    """
    Send payment portal SMS link to customer's phone.

    Usage: Call when customer prefers to pay via online portal.
    Portal link is sent to the contact number on file.

    Portal features:
    - Valid for 24 hours
    - Payment methods: Credit/Debit Card, Ozow (instant EFT), CapitecPay, Pay@ (retailers)
    - WhatsApp support available for assistance
    """
    userdata = context.userdata

    contact_number = userdata.debtor.contact_number or "the number on file"

    userdata.call.portal_link_sent = True
    userdata.call.payment_method = PaymentMethod.PORTAL
    userdata.call.append_call_notes(f"Payment portal link sent to {contact_number}")

    return f"Payment portal link has been sent via SMS to {contact_number}. The link is valid for 24 hours. Customer can pay using Credit/Debit Card, Ozow instant EFT, CapitecPay, or Pay@ at any retailer. WhatsApp support is available if they need assistance. Please remind them to check their messages and complete payment within 24 hours."


@function_tool()
async def confirm_portal_payment(
    method: Annotated[Literal["card", "eft", "instant_eft"], Field(description="Payment method used in portal")],
    amount: Annotated[float, Field(description="Amount paid through portal (in Rands)")],
    context: RunContext_T,
) -> str:
    """
    Confirm that payment was received through the portal.

    Usage: Call when payment system notifies successful portal payment,
    or when customer confirms they completed the portal payment.
    """
    userdata = context.userdata

    is_valid, error_msg = validate_amount(amount)
    if not is_valid:
        return f"ERROR: {error_msg}"

    method_names = {
        "card": "credit/debit card",
        "eft": "EFT transfer",
        "instant_eft": "Instant EFT"
    }

    userdata.call.add_payment_arrangement(
        amount=amount,
        date="immediate",
        method=f"portal_{method}",
        description=f"Portal payment: R{amount:.2f} via {method_names.get(method, method)}"
    )

    userdata.call.payment_confirmed = True
    userdata.call.payment_method = f"portal_{method}"
    userdata.call.append_call_notes(f"Portal payment confirmed: R{amount:.2f} via {method_names.get(method, method)}")

    return f"Payment confirmed: R{amount:.2f} received via {method_names.get(method, method)}. Transaction is being processed. Customer will receive a payment confirmation email within 24 hours."


@function_tool()
async def confirm_arrangement(context: RunContext_T) -> tuple[Agent, str] | Agent:
    """
    Finalize and confirm the payment arrangement.

    Usage: Call after all payment details are captured and customer has confirmed everything.
    This marks the arrangement as committed and transfers to closing agent.

    Note: Silent handoff - closing agent will wrap up the call.
    """
    userdata = context.userdata

    userdata.call.payment_confirmed = True
    userdata.call.call_outcome = CallOutcome.SUCCESS
    userdata.call.append_call_notes("Payment arrangement confirmed and finalized")

    return await transfer_to_agent("closing", context, silent=True)
