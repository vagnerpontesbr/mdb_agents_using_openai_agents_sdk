"""Acknowledge content-free control activities through the Engine-owned state."""
from agent_engine_runner_shared.context import get_current_wrapper


def acknowledge_control(client, context, result):
    wrapper = get_current_wrapper()
    if wrapper is not None and wrapper.durable_memory is not None:
        wrapper.durable_memory.acknowledge(client, context)
