"""Opt-in managed-memory and 60-second review expiry compatibility fixture."""
from .app import OpenAIEngineApp
from .review_invoice import app as review_app
from .invoice import lookup_invoice

app = OpenAIEngineApp(
    name=review_app.name, instructions=review_app.instructions,
    llm_id=review_app.llm_id, model_name=review_app.model_name,
    provider_builder=review_app.provider_builder,
    provider_adapter_factory=review_app.provider_adapter_factory,
    review_action_factory=review_app.review_action_factory,
    review_ttl_seconds=60, managed_memory=True,
)
app.tool(contract=review_app.tools()[0])(lookup_invoice)
