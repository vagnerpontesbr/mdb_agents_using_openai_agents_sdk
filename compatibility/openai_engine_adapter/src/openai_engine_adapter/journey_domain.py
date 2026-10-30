"""Synthetic business contracts. No live billing/provisioning side effects."""

import hashlib
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class InvoiceQuery(Contract):
    invoice_id: str = Field(min_length=1, max_length=64)


class EmptyQuery(Contract):
    pass


class PlanQuery(Contract):
    plan_id: Literal["fiber-500", "fiber-1000"]
    propose_change: bool


class BusinessResult(Contract):
    kind: Literal["invoice", "technical", "offer", "proposal", "simulation"]
    account_ref: str = Field(min_length=1, max_length=128)
    reference: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=2000)
    plan_id: Literal["none", "fiber-500", "fiber-1000"] = "none"
    monthly_minor: int = Field(default=0, ge=0, strict=True)
    currency: Literal["USD"] = "USD"
    simulation: Literal[True] = True


class ChangeQuery(Contract):
    plan_id: Literal["fiber-500", "fiber-1000"]
    monthly_minor: int = Field(ge=0, strict=True)
    proposal_id: str = Field(min_length=1, max_length=128)


PLANS = {"fiber-500": (500, 8990), "fiber-1000": (1000, 10990)}


def subject(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise ValueError("Authenticated Engine user is required")
    return value


def proposal_id(user, plan):
    return hashlib.sha256(f"telecom-simulation-v1|{subject(user)}|{plan}".encode()).hexdigest()


def read_invoice(user, invoice_id):
    subject(user)
    if invoice_id != "demo-1":
        raise ValueError("Invoice outside the authenticated synthetic fixture")
    return BusinessResult(kind="invoice", account_ref=user, reference="demo-1",
                          text="Your synthetic invoice total is USD 79.90, due on 2026-12-01.")


def check_connection(user):
    subject(user)
    return BusinessResult(kind="technical", account_ref=user, reference="network-fixture-v1",
        text="The synthetic network reports no regional outage. Check the router power and cables, "
             "then compare a wired connection with Wi-Fi. If the problem persists, contact support.")


def offer_plan(user, plan_id, propose_change):
    subject(user)
    speed, amount = PLANS[plan_id]
    price = f"USD {amount // 100}.{amount % 100:02d}"
    if propose_change:
        text = (f"Simulate a change to {plan_id} ({speed} Mbps) at {price} per month? "
                "Approval produces a simulation receipt only; no live plan or charge changes.")
    else:
        text = (f"The synthetic {plan_id} plan offers {speed} Mbps for {price} per month. "
                "This demo account is eligible. No plan change has been requested.")
    return BusinessResult(kind="proposal" if propose_change else "offer", account_ref=user,
        reference=proposal_id(user, plan_id), text=text, plan_id=plan_id, monthly_minor=amount)


def simulate_change(user, plan_id, monthly_minor, proposal_id_value):
    expected = offer_plan(user, plan_id, True)
    if monthly_minor != expected.monthly_minor or proposal_id_value != expected.reference:
        raise ValueError("Proposal no longer matches current simulated eligibility and price")
    # A pure business simulation: repeated identical commands have the same receipt
    # and no external effect. Engine persists/replays the remote activity result.
    return BusinessResult(kind="simulation", account_ref=user, reference=expected.reference,
        plan_id=plan_id, monthly_minor=monthly_minor,
        text=f"Simulation approved for {plan_id} at USD {monthly_minor // 100}."
             f"{monthly_minor % 100:02d} per month. No live plan or charge was changed.")


class JourneyResult(Contract):
    contract: Literal["telecom-journey-v1"] = "telecom-journey-v1"
    status: Literal["completed", "rejected", "expired", "needs_information"]
    text: str = Field(min_length=1, max_length=8000)
    specialists: list[Literal["financial", "technical", "sales"]] = Field(max_length=3)
    results: list[BusinessResult] = Field(max_length=4)
