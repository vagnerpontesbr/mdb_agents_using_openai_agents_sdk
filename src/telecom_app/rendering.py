"""Critical text is rendered once from validated business facts, for both channels."""

from types import MappingProxyType

from .contracts import InvoiceFacts, ProtectedResponse
from .profile import Locale
from .turn_locale import validated_locale

TEMPLATES = MappingProxyType({
    "invoice_total.v1": "Your invoice total is {amount}, due on {due_date}.",
})


def render_invoice(facts: InvoiceFacts, locale: Locale = "en-US") -> ProtectedResponse:
    validated_locale(locale)
    # Integer arithmetic avoids binary floating-point monetary rounding.
    dollars, cents = divmod(facts.amount_minor, 100)
    if locale == "en-US":
        text = TEMPLATES["invoice_total.v1"].format(
            amount=f"USD {dollars:,}.{cents:02d}", due_date=facts.due_date.isoformat(),
        )
    else:
        template = {
            "pt-BR": "O total da sua fatura é {amount}, com vencimento em {due_date}.",
            "es-ES": "El total de tu factura es {amount}, con vencimiento el {due_date}.",
        }[locale]
        text = template.format(amount=f"USD {dollars}.{cents:02d}".replace(".", ","),
                               due_date=facts.due_date.strftime("%d/%m/%Y"))
    return ProtectedResponse(text=text, source_id=facts.invoice_id)
