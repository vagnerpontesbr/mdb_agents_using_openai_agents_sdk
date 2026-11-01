"""Synthetic business contracts. No live billing/provisioning side effects."""

import hashlib
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .journey_locale import Locale, price, render


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class InvoiceQuery(Contract):
    locale: Locale = "en-US"
    invoice_id: str = Field(min_length=1, max_length=64)


class EmptyQuery(Contract):
    locale: Locale = "en-US"


class PlanQuery(Contract):
    locale: Locale = "en-US"
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


def read_invoice(user, invoice_id, locale="en-US"):
    subject(user)
    if invoice_id != "demo-1":
        raise ValueError("Invoice outside the authenticated synthetic fixture")
    return BusinessResult(kind="invoice", account_ref=user, reference="demo-1",
                          text=render("invoice.v1", locale))


def check_connection(user, locale="en-US"):
    subject(user)
    return BusinessResult(kind="technical", account_ref=user, reference="network-fixture-v1",
        text=render("connection.v1", locale))


def offer_plan(user, plan_id, propose_change, locale="en-US"):
    subject(user)
    speed, amount = PLANS[plan_id]
    text = render("proposal.v1" if propose_change else "offer.v1", locale,
                  plan=plan_id, speed=speed, price=price(amount, locale))
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
    locale: Locale = "en-US"
    contract: Literal["telecom-journey-v1"] = "telecom-journey-v1"
    status: Literal["completed", "rejected", "expired", "needs_information"]
    text: str = Field(min_length=1, max_length=8000)
    specialists: list[Literal["financial", "technical", "sales"]] = Field(max_length=3)
    results: list[BusinessResult] = Field(max_length=4)
