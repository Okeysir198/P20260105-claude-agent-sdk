"""Negotiation agent tools."""

from typing import Annotated
from pydantic import Field
from livekit.agents.llm import function_tool
from livekit.agents.voice import Agent, RunContext

from .common_tools import transfer_to_agent
from shared_state import UserData
from state.types import PaymentType, NegotiationOutcome, CallOutcome

RunContext_T = RunContext[UserData]


@function_tool()
async def offer_settlement(
    discount_percentage: Annotated[float, Field(description="Discount percentage to offer (e.g., 20 for 20% off)")],
    settlement_amount: Annotated[float, Field(description="Settlement amount after discount")],
    context: RunContext_T,
) -> str:
    """
    Offer a settlement discount for immediate payment.

    Usage: Call when offering to settle the debt for less than the full amount
    if paid immediately or within a short timeframe.
    """
    userdata = context.userdata
    userdata.call.discount_offered = True
    userdata.call.discount_percentage = discount_percentage
    userdata.call.settlement_amount = settlement_amount
    userdata.call.payment_arrangement_type = PaymentType.SETTLEMENT
    userdata.call.add_note(f"Settlement offered: {discount_percentage}% discount = R{settlement_amount:,.2f}")

    return f"I can offer you a settlement. Pay R{settlement_amount:,.2f} instead of the full amount. This is a {discount_percentage}% discount."


@function_tool()
async def offer_installment(
    monthly_amount: Annotated[float, Field(description="Monthly installment amount")],
    number_of_months: Annotated[int, Field(description="Number of months for the installment plan")],
    total_amount: Annotated[float, Field(description="Total amount to be paid over the period")],
    context: RunContext_T,
) -> str:
    """
    Offer an installment plan to pay off the debt over time.

    Usage: Call when arranging a payment plan with monthly installments.
    """
    userdata = context.userdata
    userdata.call.installment_amount = monthly_amount
    userdata.call.installment_months = number_of_months
    userdata.call.total_installment_amount = total_amount
    userdata.call.payment_arrangement_type = PaymentType.INSTALLMENT
    userdata.call.add_note(f"Installment plan: R{monthly_amount:,.2f}/month for {number_of_months} months")

    return f"I can set up a payment plan of R{monthly_amount:,.2f} per month for {number_of_months} months. Total amount will be R{total_amount:,.2f}."


@function_tool()
async def accept_arrangement(
    arrangement_type: Annotated[str, Field(description="Type of arrangement: 'settlement' or 'installment'")],
    context: RunContext_T,
):
    """
    Accept the customer's payment arrangement and transfer to payment agent.

    Usage: Call when customer agrees to the proposed payment arrangement.
    """
    userdata = context.userdata
    userdata.call.arrangement_accepted = True
    userdata.call.negotiation_outcome = NegotiationOutcome.ACCEPTED
    userdata.call.add_note(f"Arrangement accepted: {arrangement_type}")

    return await transfer_to_agent("payment", context, silent=True)


@function_tool()
async def explain_consequences(context: RunContext_T) -> str:
    """
    Explain the consequences of not paying the debt.

    Usage: Call when customer asks what happens if they don't pay.
    """
    userdata = context.userdata
    userdata.call.consequences_explained = True
    userdata.call.add_note("Consequences explained to customer")

    return "If you don't pay, your account may be handed over to external collections, which can affect your credit score and result in legal action."


@function_tool()
async def explain_benefits(context: RunContext_T) -> str:
    """
    Explain the benefits of paying the debt or accepting an arrangement.

    Usage: Call when motivating the customer to pay or accept an arrangement.
    """
    userdata = context.userdata
    userdata.call.benefits_explained = True
    userdata.call.add_note("Benefits explained to customer")

    return "Paying now will stop any additional fees, protect your credit score, and resolve this matter quickly."
