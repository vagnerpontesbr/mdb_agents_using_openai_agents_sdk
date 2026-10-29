"""Critical text is rendered once from validated business facts, for both channels."""

from types import MappingProxyType

from .contracts import InvoiceFacts, ProtectedResponse

TEMPLATES = MappingProxyType({
    "invoice_total.v1": "Your invoice total is {amount}, due on {due_date}.",
})


def render_invoice(facts: InvoiceFacts) -> ProtectedResponse:
    # Integer arithmetic avoids binary floating-point monetary rounding.
    dollars, cents = divmod(facts.amount_minor, 100)
    text = TEMPLATES["invoice_total.v1"].format(
        amount=f"USD {dollars:,}.{cents:02d}", due_date=facts.due_date.isoformat(),
    )
    return ProtectedResponse(text=text, source_id=facts.invoice_id)
