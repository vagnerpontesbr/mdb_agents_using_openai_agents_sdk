"""Read-only comparison of Engine STM retrieval with transcript requirements."""
import argparse
import json
import os


def assess(response):
    """Inspect redacted structure; never convert retrieval output to instructions."""
    chunks = response.get("selected_memories") or []
    formatted = response.get("formatted_context")
    metadata = [c.get("metadata") or {} for c in chunks]
    tools = [m for m in metadata if m.get("role") == "tool"]
    assistants = [m for m in metadata if m.get("role") == "assistant"]
    gaps = []
    if not chunks:
        gaps.append("no_selected_turns")
    if any(not m.get("tool_call_id") for m in tools):
        gaps.append("tool_result_correlation_missing")
    if any(isinstance(m.get("tool_calls"), dict) for m in assistants):
        gaps.append("assistant_calls_are_summary_not_arguments")
    if isinstance(formatted, list) and any(m.get("role") in ("system", "developer") for m in formatted):
        gaps.append("formatter_emits_privileged_role")
    # Context APIs budget/rank chunks and expose no transcript completeness or
    # cancelled/interrupted outcome contract. A syntactically usable subset
    # cannot silently pass as an authoritative chronological conversation.
    gaps.append("retrieval_has_no_transcript_completeness_or_outcome_contract")
    return {"status": "blocked", "sdk_restoration_proven": False,
            "selected_count": len(chunks),
            "roles": [m.get("role") for m in metadata],
            "turn_sequences": [m.get("turn_seq") for m in metadata],
            "gaps": gaps}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("project", "session", "user"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    try:
        from agent_engine_sdk_memory import Memory, MemoryRequestContext, SourceSpec
        with Memory(base_url="https://agentengine.mongodb.com", project_id=args.project,
                    service_account_token=os.environ["AGENT_ENGINE_SERVICE_ACCOUNT_TOKEN"]) as memory:
            chat = memory.bind(MemoryRequestContext(user_id=args.user, session_id=args.session))
            options = dict(query="Synthetic completed invoice conversation", visibility="private",
                           max_tokens=4096, format_style="openai", include_memories=True)
            legacy = chat.build_context(enabled_sources={"stm"}, **options)
            per_source = chat.build_context_from_sources(
                sources=[SourceSpec(source="stm", mode="text", top_k=20)], **options)
            evidence = {"legacy": assess(legacy.model_dump(mode="json")),
                        "per_source": assess(per_source.model_dump(mode="json"))}
    except Exception as error:
        evidence = {"status": "blocked", "error_class": type(error).__name__}
    print(json.dumps({"read_only": True, **evidence}, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
