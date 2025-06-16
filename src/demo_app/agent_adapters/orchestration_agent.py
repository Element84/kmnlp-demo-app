import base64
import json
import logging
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

import chainlit as cl
from e84_geoai_common.llm.core import (
    Base64ImageContent,
    JSONContent,
    LLMMessage,
    LLMToolResultContent,
    LLMToolUseContent,
    TextContent,
)
from llm_agent.agents.orchestration_agent import OrchestrationAgent
from llm_agent.tools.data_analysis_tool import (
    DataAnalysisToolOutput,
    data_analysis_tool,
)
from llm_agent.tools.data_search_tool import (
    DataSearchToolResult,
    data_search_tool,
)
from llm_agent.utils import DEFAULT_LLM

from demo_app.agent_adapters.base import ChainlitAdapter

if TYPE_CHECKING:
    from e84_geoai_common.llm.core import LLMTool
    from pydantic import BaseModel

log = logging.getLogger(__name__)

type ToolUseID = str


tool_name_to_tool: dict[str, "LLMTool"] = {
    "DataAnalysisTool": data_analysis_tool,
    "DataSearchTool": data_search_tool,
}


@dataclass
class ToolCall:
    """Model for tracking a tool call and associated UI element."""

    tool_use_request: LLMToolUseContent
    ui_step: cl.Step

    @property
    def output_data_model(self) -> type["BaseModel"] | None:
        """Get data model for tool's output."""
        tool = tool_name_to_tool[self.tool_use_request.name]
        return tool.output_model


def _as_markdown_codeblock(code: str, lang: str = "") -> str:
    """Wrap code in a markdown codeblock."""
    return f"```{lang}\n{code}\n```"


class OrchestrationAgentChainlitAdapter(ChainlitAdapter):
    """Chainlit adapter for the OrchestrationAgent."""

    agent: OrchestrationAgent

    def __init__(self) -> None:
        """Constructor."""
        if os.getenv("DASK_ADDRESS") is None:
            msg = "DASK_ADDRESS environment variable is required."
            raise ValueError(msg)
        self.agent = OrchestrationAgent(
            DEFAULT_LLM, tools=[data_search_tool, data_analysis_tool]
        )
        log.debug(self.agent.system_prompt)

    async def process_message(self, message: cl.Message) -> None:
        """Handle user message by updating the UI."""
        msg = LLMMessage(role="user", content=message.content.strip())
        log.info(
            "User message: %s", msg
        )  # Info level to be sure it shows up in CloudWatch
        responses = self.agent.run(msg)

        async with cl.Step(name="Working") as waiting_step:
            pass

        prev_waiting_step = waiting_step

        tool_calls: dict[ToolUseID, ToolCall] = {}
        async for response in responses:
            await prev_waiting_step.remove()
            log.info("Response: %s", response)

            await waiting_step.update()

            match response:
                case LLMMessage():
                    await self._handle_llm_message(response, tool_calls)
                    async with cl.Step(name="Working") as waiting_step:
                        pass
                    prev_waiting_step = waiting_step
                case LLMToolResultContent():
                    await self._handle_tool_result(response, tool_calls)
                    async with cl.Step(name="Working") as waiting_step:
                        pass
                    prev_waiting_step = waiting_step

        await prev_waiting_step.remove()

    async def _handle_llm_message(
        self, message: LLMMessage, tool_calls: dict[ToolUseID, ToolCall]
    ) -> None:
        """Update UI based on message contents."""
        for content in message.content:
            match content:
                case str():
                    log.debug(content)
                    await cl.Message(content=content).send()
                case TextContent():
                    log.debug(content.text)
                    await cl.Message(content=content.text).send()
                case LLMToolUseContent():
                    async with cl.Step(
                        name=f"Using {content.name}", type="tool"
                    ) as tool_step:
                        tool_calls[content.id] = ToolCall(
                            tool_use_request=content, ui_step=tool_step
                        )
                        tool_input_json = json.dumps(content.input, indent=2)
                        tool_step.input = _as_markdown_codeblock(
                            tool_input_json, lang="json"
                        )
                        await tool_step.update()

                case _:
                    raise NotImplementedError

    async def _handle_tool_result(
        self,
        tool_result: LLMToolResultContent,
        tool_calls: dict[ToolUseID, ToolCall],
    ) -> None:
        """Update corresponding Chainlit step with tool call results."""
        tool_call = tool_calls[tool_result.id]
        for content in tool_result.content:
            match content:
                case TextContent():
                    tool_call.ui_step.output += content.text
                case JSONContent():
                    await self._handle_json_tool_result_content(
                        content, tool_call
                    )
                case Base64ImageContent():
                    image_bytes = base64.b64decode(content.data)
                    image = cl.Image(display="inline", content=image_bytes)
                    await cl.Message(content="", elements=[image]).send()

        tool_call.ui_step.name = tool_call.ui_step.name.replace(
            "Using", "Used"
        )
        await tool_call.ui_step.update()

    async def _handle_json_tool_result_content(
        self, content: JSONContent, tool_call: ToolCall
    ) -> None:
        output_data_model = tool_call.output_data_model
        if output_data_model is None:
            msg = (
                f"Did not expect output to be JSON for tool call {tool_call}."
            )
            raise ValueError(msg)

        # Show tool output as JSON inside the corresponding Step.
        # We could potentially replace this with something fancier e.g.
        # displaying search results as a table etc.
        tool_output_json = json.dumps(content.data, indent=2)
        tool_call.ui_step.output += _as_markdown_codeblock(
            tool_output_json, lang="json"
        )
        await tool_call.ui_step.update()

        parsed_output = output_data_model.model_validate(content.data)
        match parsed_output:
            case DataAnalysisToolOutput():
                if parsed_output.error_message:
                    tool_call.ui_step.is_error = True
                    await tool_call.ui_step.update()
                    await cl.Message(
                        content=f"<Error: {parsed_output.error_message}>"
                    ).send()
                else:
                    async with cl.Step(name="Pseudocode") as code_step:
                        code_step.output = _as_markdown_codeblock(
                            parsed_output.solution_pseudocode, lang="py"
                        )
                        await code_step.update()
            case DataSearchToolResult():
                log.debug("Got data search tool result. Doing nothing.")
            case result:
                log.error("Got a tool result of unknown type: %s", result)
                raise NotImplementedError
