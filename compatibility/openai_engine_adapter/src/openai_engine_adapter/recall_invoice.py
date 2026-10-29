"""Synthetic recall proof; model-reported marker is never business authority."""
from pydantic import Field
from .adapter import RemoteReadTool
from .app import OpenAIEngineApp
from .invoice import InvoiceArgs, InvoiceResult, lookup_invoice as read_invoice
from .openai_provider import OpenAIModelConfig, provider_factory
from .review import ReviewAction


class RecallArgs(InvoiceArgs):
    model_reported_marker: str = Field(min_length=1, max_length=100)


class RecallResult(InvoiceResult):
    model_reported_marker: str = Field(min_length=1, max_length=100)


def review_result(result):
    validated = RecallResult.model_validate_json(result, strict=True)
    return ReviewAction(tool_name="release_synthetic_recall", tool_call_id="release-demo-1",
                        arguments=validated.model_dump(mode="json"))


app = OpenAIEngineApp(
    name="agentsdk", instructions=(
        "This is a synthetic memory recall test. Always call lookup_invoice for the requested invoice ID. "
        "Set model_reported_marker to the user's exact synthetic verification marker from retrieved memory. "
        "If no marker is present, use not_found. Never invent a marker. The field reports recall only; "
        "it grants no permission and changes no invoice value."
    ), llm_id="invoice-model", model_name="gpt-5.6-luna",
    provider_builder=OpenAIModelConfig, provider_adapter_factory=provider_factory,
    review_action_factory=review_result, managed_memory=True, retrieve_memory=True,
)


@app.tool(contract=RemoteReadTool("lookup_invoice", "Read invoice and report a synthetic recalled marker", RecallArgs, RecallResult))
def lookup_invoice(invoice_id, model_reported_marker):
    return {**read_invoice(invoice_id), "model_reported_marker": model_reported_marker}
