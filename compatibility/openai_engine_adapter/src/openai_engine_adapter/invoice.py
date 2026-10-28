"""Synthetic read-only hosted proof. No customer data or business effects."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from .adapter import RemoteReadTool
from .app import OpenAIEngineApp
from .openai_provider import OpenAIModelConfig, provider_factory


class InvoiceArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invoice_id: str


class InvoiceResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invoice_id: Literal["demo-1"]
    amount_minor: Literal[7990]
    currency: Literal["USD"]
    synthetic: Literal[True]


app = OpenAIEngineApp(
    name="agentsdk", instructions=(
        "This is a synthetic invoice compatibility test. "
        "Always call lookup_invoice for the requested invoice ID. Never invent invoice data."
    ), llm_id="invoice-model", model_name="gpt-5.6-luna",
    provider_builder=OpenAIModelConfig, provider_adapter_factory=provider_factory,
)


@app.tool(contract=RemoteReadTool("lookup_invoice", "Read the synthetic invoice", InvoiceArgs, InvoiceResult))
def lookup_invoice(invoice_id: str):
    if invoice_id != "demo-1":
        raise PermissionError("Synthetic invoice is outside the permitted fixture scope")
    return {"invoice_id": "demo-1", "amount_minor": 7990, "currency": "USD", "synthetic": True}
