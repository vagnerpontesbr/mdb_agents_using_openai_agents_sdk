"""Versioned input format, profile defaults and protected local templates."""

from datetime import date

import pytest

from telecom_app.config import Settings
from telecom_app.contracts import InvoiceFacts
from telecom_app.rendering import render_invoice
from telecom_app.turn_locale import PREFIX, Turn, execution_locale


def test_wire_preserves_unicode_and_does_not_reinterpret_nested_message():
    nested = PREFIX + '{"locale":"es-ES","message":"nested"}'
    wire = Turn(locale="pt-BR", message=nested).wire()
    assert execution_locale(wire) == "pt-BR"
    assert execution_locale("legacy English request") == "en-US"
    assert execution_locale(None) == "en-US"
    assert len(Turn(locale="pt-BR", message="🙂" * 4000).wire()) < 25000


@pytest.mark.parametrize("body", ['{"locale":"pt-BR","locale":"es-ES","message":"x"}',
                                  '{"locale":"fr-FR","message":"x"}',
                                  '{"locale":"pt-BR","message":"x","user_id":"other"}',
                                  '{"locale":"pt-BR","message":" "}', '[]'])
def test_bad_envelopes_are_rejected(body):
    with pytest.raises(ValueError):
        execution_locale(PREFIX + body)


def test_rollout_switch_requires_explicit_configuration(monkeypatch):
    from tests.foundation.conftest import URI

    monkeypatch.setenv("APP_MONGODB_URI", URI)
    monkeypatch.delenv("APP_JOURNEY_LOCALE_ENABLED", raising=False)
    assert not Settings.from_env().journey_locale_enabled
    monkeypatch.setenv("APP_JOURNEY_LOCALE_ENABLED", "true")
    assert Settings.from_env().journey_locale_enabled
    monkeypatch.setenv("APP_JOURNEY_LOCALE_ENABLED", "yes")
    with pytest.raises(ValueError):
        Settings.from_env()


def test_local_invoice_templates_preserve_exact_facts():
    facts = InvoiceFacts(invoice_id="synthetic", amount_minor=7990, due_date=date(2026, 12, 1))
    assert render_invoice(facts, "pt-BR").text == (
        "O total da sua fatura é USD 79,90, com vencimento em 01/12/2026.")
    assert render_invoice(facts, "es-ES").text == (
        "El total de tu factura es USD 79,90, con vencimiento el 01/12/2026.")
    assert render_invoice(facts).text == "Your invoice total is USD 79.90, due on 2026-12-01."
    assert facts.amount_minor == 7990 and facts.currency == "USD"
