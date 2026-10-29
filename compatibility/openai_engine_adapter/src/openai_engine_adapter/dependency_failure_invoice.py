"""Opt-in hosted dependency-failure injection; never interrupts shared services."""
import socket

from .adapter import RemoteReadTool
from .app import OpenAIEngineApp
from .invoice import InvoiceArgs, InvoiceResult
from .openai_provider import OpenAIModelConfig, provider_factory

app = OpenAIEngineApp(
    name="agentsdk", instructions=(
        "This is a synthetic dependency-failure test. Always call lookup_invoice "
        "with invoice_id demo-service-unavailable. Never invent invoice data."
    ), llm_id="invoice-model", model_name="gpt-5.6-luna",
    provider_builder=OpenAIModelConfig, provider_adapter_factory=provider_factory,
)


@app.tool(contract=RemoteReadTool("lookup_invoice", "Probe synthetic unavailable invoice service", InvoiceArgs, InvoiceResult))
def lookup_invoice(invoice_id: str):
    if invoice_id != "demo-service-unavailable":
        raise PermissionError("Outside the dependency-failure fixture")
    # Reserve an ephemeral loopback endpoint without listening. No other process
    # can claim it, no external service is disrupted, and no credentials are sent.
    # A real OS connection refusal/timeout is injected inside the hosted Tool Pod.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as unavailable:
        unavailable.bind(("127.0.0.1", 0))
        try:
            with socket.create_connection(unavailable.getsockname(), timeout=1):
                raise RuntimeError("Unexpected dependency availability")
        except (ConnectionRefusedError, TimeoutError):
            raise ConnectionError("Synthetic invoice dependency unavailable") from None
