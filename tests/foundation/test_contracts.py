from datetime import date

import pytest
from pydantic import ValidationError

from telecom_app.config import Settings
from telecom_app.contracts import InvoiceFacts, RequestInterpretation
from telecom_app.rendering import render_invoice
from tests.foundation.conftest import URI


@pytest.mark.parametrize("uri", [
    "mongodb://localhost/", URI.replace("openai-sdk", "clusterdemotelco"),
    URI + "?tls=false", URI + "?tlsAllowInvalidCertificates=true", URI + "telecom_eval",
])
def test_rejects_unapproved_database_or_insecure_transport(uri):
    with pytest.raises(ValueError):
        Settings(uri)


@pytest.mark.parametrize("origin", ["https://example.com", "http://0.0.0.0:8000",
                                     "http://127.0.0.1:8000/", "http://127.0.0.1:80"])
def test_loopback_origin_only(origin):
    with pytest.raises(ValueError):
        Settings(URI, origin=origin)


def test_settings_do_not_display_credentials():
    assert "synthetic" not in repr(Settings(URI))


def test_rendering_is_exact_and_sensitive_to_authoritative_facts():
    facts = InvoiceFacts(invoice_id="demo-1", amount_minor=123456, due_date=date(2026, 12, 1))
    result = render_invoice(facts)
    assert result.text == "Your invoice total is USD 1,234.56, due on 2026-12-01."
    assert result == render_invoice(facts)
    changed = InvoiceFacts(invoice_id="demo-1", amount_minor=100, due_date=date(2026, 12, 2))
    assert render_invoice(changed).text == "Your invoice total is USD 1.00, due on 2026-12-02."
    for amount in [-1, True, "100", 1.5]:
        with pytest.raises(ValidationError):
            InvoiceFacts(invoice_id="demo-1", amount_minor=amount, due_date=date(2026, 12, 1))


def test_model_interpretation_cannot_supply_identity_or_authorization():
    with pytest.raises(ValidationError):
        RequestInterpretation(summary="Read invoice", needs_clarification=False,
                              user_id="forged", approved=True)
