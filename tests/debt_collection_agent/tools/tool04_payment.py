"""Payment agent tools."""

from typing import Annotated
from pydantic import Field
from livekit.agents.llm import function_tool, ToolError
from livekit.agents.voice import Agent, RunContext

from .common_tools import transfer_to_agent
from shared_state import UserData
from state.types import PaymentMethod, PaymentType

RunContext_T = RunContext[UserData]


@function_tool()
async def capture_immediate_debit(
    amount: Annotated[float, Field(description="Immediate debit amount")],
    debit_date: Annotated[str, Field(description="Debit date in YYYY-MM-DD format")],
    context: RunContext_T,
) -> str:
    """
    Capture immediate debit order payment details.

    Usage: Call when customer agrees to immediate debit order payment.
    """
    userdata = context.userdata
    userdata.call.payment_type = PaymentType.FULL
    userdata.call.payment_method = PaymentMethod.DEBIT_ORDER
    userdata.call.add_payment_arrangement(amount=amount, date=debit_date, method=PaymentMethod.DEBIT_ORDER)
    userdata.call.add_note(f"Immediate debit captured: R{amount:,.2f} on {debit_date}")

    return f"Thank you. I've captured the immediate debit of R{amount:,.2f} for {debit_date}. Let me confirm the details."


@function_tool()
async def validate_bank_details(
    account_number: Annotated[str, Field(description="Bank account number")],
    bank_name: Annotated[str, Field(description="Bank name")],
    context: RunContext_T,
) -> str:
    """
    Validate bank account details.

    Usage: Call when customer provides bank account information for verification.
    """
    userdata = context.userdata
    profile = userdata.debtor

    # Basic validation
    if profile.bank_account_number and account_number != profile.bank_account_number:
        userdata.call.bank_validation_status = "invalid"
        raise ToolError("Bank account number does not match our records.")

    userdata.call.bank_validation_status = "valid"
    userdata.call.add_note(f"Bank details validated: {bank_name} - {account_number}")

    return "Bank details validated successfully."


@function_tool()
async def confirm_arrangement(
    context: RunContext_T,
):
    """
    Confirm payment arrangement and transfer to closing agent.

    Usage: Call when payment arrangement is confirmed and captured.
    """
    userdata = context.userdata
    userdata.call.payment_confirmed = True
    userdata.call.add_note("Payment arrangement confirmed")

    return await transfer_to_agent("closing", context, silent=True)
