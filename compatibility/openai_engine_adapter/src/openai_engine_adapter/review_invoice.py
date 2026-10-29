"""Opt-in synthetic review before releasing an invoice; no business writes."""

from .app import OpenAIEngineApp
from .invoice import app as read_app, InvoiceResult, lookup_invoice
from .openai_provider import OpenAIModelConfig, provider_factory
from .review import ReviewAction


def review_invoice_result(result):
    invoice = InvoiceResult.model_validate_json(result, strict=True)
    return ReviewAction(
        tool_name="release_synthetic_invoice", tool_call_id="release-demo-1",
        arguments=invoice.model_dump(mode="json"),
    )


app = OpenAIEngineApp(
    name="agentsdk", instructions=read_app.instructions,
    llm_id="invoice-model", model_name="gpt-5.6-luna",
    provider_builder=OpenAIModelConfig, provider_adapter_factory=provider_factory,
    review_action_factory=review_invoice_result,
)
app.tool(contract=read_app.tools()[0])(lookup_invoice)
