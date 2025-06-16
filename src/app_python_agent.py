import logging

import chainlit as cl

from demo_app.agent_adapters.scientific_python_agent import (
    ScientificPythonAgentChainlitAdapter,
)

log = logging.getLogger(__name__)

agent_adapter: ScientificPythonAgentChainlitAdapter


@cl.on_chat_start  # type: ignore[reportUnknownMemberType]
async def init_agent() -> None:
    """Initialize agent."""
    global agent_adapter  # noqa: PLW0603
    agent_adapter = ScientificPythonAgentChainlitAdapter()


@cl.on_message  # type: ignore[reportUnknownMemberType]
async def message_handler(message: cl.Message) -> None:
    """Handle user message."""
    await agent_adapter.process_message(message)
