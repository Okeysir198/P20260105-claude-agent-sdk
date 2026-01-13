"""Negotiation agent tools."""

from typing import Annotated, Literal
from pydantic import Field
from livekit.agents.llm import function_tool
from livekit.agents.voice import Agent, RunContext

from business_rules.config import get_campaign_deadline
from business_rules.script_context import get_consequences, get_benefits
from .common_tools import transfer_to_agent
from shared_state import UserData

RunContext_T = RunContext[UserData]


@function_tool()
async def offer_settlement(
    discount_percentage: Annotated[float, Field(description="Discount percentage offered (e.g., 50 for 50% discount)")],
    settlement_amount: Annotated[float, Field(description="Final settlement amount after discount (in Rands)")],
    context: RunContext_T,
) -> str:
    """
    Record a settlement offer (one-time payment with discount).

    For recently_suspended_120 script:
    - Tier 1 (50% discount): Payment by 25th of current month
    - Tier 2 (40% in 2 installments): Two payments by 28th

    Usage: Call when customer agrees to pay in full immediately.
    """
    userdata = context.userdata
    call = userdata.call

    call.payment_arrangement_type = "settlement"
    call.discount_applied = True
    call.discount_percentage = discount_percentage
    call.settlement_amount = settlement_amount

    if call.script_type == "recently_suspended_120":
        if discount_percentage >= 50:
            deadline = get_campaign_deadline(1)
            call.tier1_offered = True
            return f"Settlement offer recorded: 50% discount, final amount R{settlement_amount:.2f}. Payment deadline: {deadline.strftime('%d %B %Y')}. Explain the payment process and deadline urgency to the customer."
        else:
            deadline = get_campaign_deadline(2)
            installment_amount = settlement_amount / 2
            return f"Installment settlement recorded: 40% discount with 2 payments of R{installment_amount:.2f}. First payment deadline: {deadline.strftime('%d %B %Y')}. Explain the payment process and ask for customer's acceptance."

    return f"Settlement offer recorded: {discount_percentage}% discount, final amount R{settlement_amount:.2f}. Explain the payment process and ask for customer's acceptance."


@function_tool()
async def offer_installment(
    monthly_amount: Annotated[float, Field(description="Monthly installment amount (in Rands)")],
    num_months: Annotated[int, Field(description="Number of monthly payments")],
    context: RunContext_T,
) -> str:
    """
    Record an installment arrangement offer.

    Usage: Call when customer agrees to pay over multiple months.
    Ensure num_months doesn't exceed script's max_payments configuration.
    """
    userdata = context.userdata
    call = userdata.call

    call.payment_arrangement_type = "installment"
    call.installment_amount = monthly_amount
    call.installment_months = num_months
    call.total_installment_amount = monthly_amount * num_months

    return f"Installment offer recorded: R{monthly_amount:.2f} per month for {num_months} months (Total: R{monthly_amount * num_months:.2f}). Explain the payment process and ask for customer's acceptance."


@function_tool()
async def accept_arrangement(
    arrangement_type: Annotated[Literal["settlement", "installment"], Field(description="Type of arrangement customer accepted")],
    context: RunContext_T,
) -> tuple[Agent, str] | Agent:
    """
    Customer accepts the payment arrangement.

    Usage: Call ONLY after customer explicitly says "Yes", "I accept", "I agree", etc.

    Note: Silent handoff - payment agent will introduce itself.
    """
    userdata = context.userdata
    call = userdata.call

    call.arrangement_accepted = True
    call.negotiation_outcome = f"{arrangement_type}_accepted"

    return await transfer_to_agent("payment", context, silent=True)


@function_tool()
async def explain_consequences(context: RunContext_T) -> str:
    """
    Retrieve consequences script for the agent to explain.

    Usage: Call when customer asks "What happens if I don't pay?" or needs motivation.
    The returned text should be spoken by the agent, not shown verbatim.
    """
    userdata = context.userdata
    consequences = get_consequences(userdata)

    if consequences:
        return "\n".join(f"- {c}" for c in consequences)

    return "Non-payment may result in service suspension and credit listing."


@function_tool()
async def explain_benefits(context: RunContext_T) -> str:
    """
    Retrieve benefits script for the agent to explain.

    Usage: Call when customer asks "Why should I pay?" or needs positive reinforcement.
    The returned text should be spoken by the agent conversationally.
    """
    userdata = context.userdata
    benefits = get_benefits(userdata)

    if benefits:
        return "\n".join(f"- {b}" for b in benefits)

    return "Payment will restore your services and prevent further action."


@function_tool()
async def offer_tier2_fallback(context: RunContext_T) -> str:
    """
    Offer tier 2 (40% discount in 2 installments) after customer declines tier 1.

    Usage: Call when customer declines the 50% settlement offer and needs
    an alternative payment option. Only for recently_suspended_120 script.
    """
    userdata = context.userdata
    call = userdata.call

    if call.script_type != "recently_suspended_120":
        return "ERROR: Tier fallback only available for recently_suspended_120 script."

    debtor = userdata.debtor
    original_amount = debtor.outstanding_amount
    discount_percentage = 40
    discounted_amount = original_amount * (1 - discount_percentage / 100)
    installment_amount = discounted_amount / 2

    deadline = get_campaign_deadline(2)

    call.payment_arrangement_type = "installment"
    call.discount_applied = True
    call.discount_percentage = discount_percentage
    call.installment_amount = installment_amount
    call.installment_months = 2
    call.tier2_offered = True

    return f"Tier 2 offer recorded: 40% discount with 2 payments of R{installment_amount:.2f} each. Total after discount: R{discounted_amount:.2f}. First payment deadline: {deadline.strftime('%d %B %Y')}. Explain this alternative option emphasizing it's still a significant saving."
