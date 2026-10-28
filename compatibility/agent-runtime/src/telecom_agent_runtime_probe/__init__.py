"""Import contracts for the isolated Phase 0 agent dependency graph."""

def check() -> dict:
    from importlib.metadata import version
    import platform
    from agents import Agent, Runner, function_tool
    from agents.voice import VoicePipeline, SingleAgentVoiceWorkflow
    from agent_engine_sdk_memory import Memory, MemoryRequestContext
    from pymongo import MongoClient

    assert all((Agent, Runner, function_tool, VoicePipeline,
                SingleAgentVoiceWorkflow, Memory, MemoryRequestContext, MongoClient))
    return {"scope": "agent_dependency_imports", "python": platform.python_version(),
            "versions": {name: version(name) for name in
                         ("openai-agents", "pymongo", "agent-engine-sdk-memory")},
            "provider_calls": False, "phase0_complete": False}
