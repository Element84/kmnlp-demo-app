import logging
import os

import chainlit as cl
from e84_geoai_common.llm.models import (
    CLAUDE_BEDROCK_MODEL_IDS,
    BedrockClaudeLLM,
)
from llm_agent.agents.scientific_python_agent import (
    ExecEnv,
    ScientificPythonAgent,
)

from demo_app.agent_adapters.base import ChainlitAdapter

log = logging.getLogger(__name__)


SETUP_CODE = """\
import asyncio
import fsspec
import os
import numpy as np
import xarray as xr
from dask.distributed import Client
from pprint import pprint

dask_scheduler_address = os.getenv("DASK_ADDRESS")
dask_client = Client(dask_scheduler_address, asynchronous=True)

zarr_reference_path = os.getenv("ZARR_REFERENCE_PATH")
mapper = fsspec.get_mapper(
    "reference://", fo=zarr_reference_path, remote_protocol="s3",
)
ds = xr.open_zarr(mapper, consolidated=False)
ds = ds.unify_chunks()

print("Dataset:")
print(ds)
print("----------")

print("Data variables in the dataset:")
for k, v in ds.data_vars.items():
    print(k)
    print(v)
    print("----------")

print("Dataset attributes:")
pprint(ds.attrs)
"""


PLT_MONKEY_PATCH = """\
import chainlit as cl
from matplotlib import pyplot as plt

def render_to_chainlit_ui(fig: plt.Figure | None = None, msg: str = ""):
    fig = fig or plt.gcf()
    elements = [
        cl.Pyplot(name="plot", figure=fig, display="inline"),
    ]
    asyncio.run(cl.Message(content=msg, elements=elements).send())

plt.show = render_to_chainlit_ui
"""

# replaces geocode_natural_language_description() with a function that calls
# the original geocode_natural_language_description() and then plots the
# returned geometry
GEOCODING_VIZ_MONKEY_PATCH = """\
import contextily as cx
import geopandas as gpd
from shapely.geometry.base import BaseGeometry

def plot_geometry(geometry: "BaseGeometry", name: str = "") -> plt.Figure:
    '''Plot a geometry on a basemap and return the pyplot Figure.'''
    fig, ax = plt.subplots()
    gdf = gpd.GeoDataFrame(geometry=[geometry], crs="EPSG:4326")
    gdf.plot(ax=ax, ec="r", fc="r", alpha=0.1)
    gdf.plot(ax=ax, ec="r", fc="none", alpha=1, lw=2)
    cx.add_basemap(ax, crs="epsg:4326", source=cx.providers.CartoDB.Voyager)
    ax.set_xlabel("longitude")
    ax.set_ylabel("latitude")
    ax.set_title(f'Geocoding for "{name}"')
    return fig


_geocode_natural_language_description = geocode_natural_language_description

def geocode_natural_language_description(text: str):
    geometry = _geocode_natural_language_description(text)
    fig = plot_geometry(geometry, text)
    render_to_chainlit_ui(fig, msg=f'Geocoded "{text}"')
    return geometry
"""


def has_actual_code(code_block: str) -> bool:
    """Check if code block has any non-whitespace and non-comment lines."""
    lines = [line.strip() for line in code_block.splitlines()]
    return any(len(line) > 0 and not line.startswith("#") for line in lines)


class ScientificPythonAgentChainlitAdapter(ChainlitAdapter):
    """Chainlit adapter for the ScientificPythonAgent.

    Attributes:
        agent (ScientificPythonAgent): The LLM Agent.
        exec_env (ExecEnv): The execution environment where code written by
            the agent will be run.
        debug_mode (bool): In debug mode, user messages are directly executed
            as code. Can be enabled by entering "!DEBUG" and disabled by
            entering "!CHAT". Defaults to False.
    """

    agent: ScientificPythonAgent
    exec_env: ExecEnv
    debug_mode: bool = False

    def __init__(self, setup_code: str = SETUP_CODE) -> None:
        """Constructor.

        Args:
            setup_code (str): Code to set up agent's execution environment.
                Defaults to SETUP_CODE.

        Raises:
            ValueError: If ZARR_REFERENCE_PATH environment variable is not set.
        """
        self.exec_env = ExecEnv(extra_imports=ScientificPythonAgent.utils)

        if os.getenv("ZARR_REFERENCE_PATH") is None:
            msg = "ZARR_REFERENCE_PATH environment variable is required."
            raise ValueError(msg)

        setup_code_out = self.exec_env.exec(setup_code)
        log.info("Code output:\n%s", setup_code_out)

        llm = BedrockClaudeLLM(
            model_id=CLAUDE_BEDROCK_MODEL_IDS["Claude 3.5 Sonnet"]
        )
        self.agent = ScientificPythonAgent(
            llm,
            setup_code=SETUP_CODE,
            setup_output=setup_code_out,
        )
        log.info("Prompt template:\n%s", self.agent.prompt_template)

        # hijack plt.show() to make it render figures to the chainlit UI
        _ = self.exec_env.exec(PLT_MONKEY_PATCH)
        # hijack geocode_natural_language_description() to make it plot the
        # geocoded polygon
        _ = self.exec_env.exec(GEOCODING_VIZ_MONKEY_PATCH)

    async def process_message(self, message: cl.Message) -> None:
        """Handle user message by updating the UI."""
        msg = message.content.strip()
        if msg.upper() == "!DEBUG" and not self.debug_mode:
            self.debug_mode = True
            await cl.Message(
                content=(
                    "Debug mode enabled. Messages will be executed as code."
                )
            ).send()
            return
        if msg.upper() == "!CHAT" and self.debug_mode:
            self.debug_mode = False
            await cl.Message(
                content="Debugging mode disabled. Resuming chat."
            ).send()
            return
        if self.debug_mode:
            async with cl.Step(name="Code", type="run") as debug_step:
                debug_step.input = f"```python\n{msg}\n```"
                out = self.exec_env.exec(msg)
                log.info("Code output:\n%s", out)
                debug_step.output = str(out)
            return

        await self._process_message(msg)

    async def _process_message(self, message: str) -> None:
        """Send query to agent and update UI with response."""
        async with cl.Step(name="Thinking") as step:
            response = self.agent.run(message)
            log.info(response)
            await step.remove()

        async with cl.Step(name="Thoughts") as thought_step:
            thought_step.output = response.thoughts

        has_code = has_actual_code(response.code)
        if not has_code:
            answer = response.explanation
            answer = answer.replace("$ANSWER$ ", "").replace("$ANSWER$", "")
            await cl.Message(content=response.explanation).send()
            return

        async with cl.Step(name="Code", type="run") as code_step:
            code_step.output = f"```python\n{response.code}\n```"
        async with cl.Step(name="Explanation") as explanation_step:
            explanation_step.output = response.explanation
        async with cl.Step(name="Executing code", type="run") as exec_step:
            out = self.exec_env.exec(response.code)
            log.info("Code output:\n%s", out)
            exec_step.output = str(out)
            exec_step.name = "Executed code"
        # extract answer into a separate message
        answer_lines = [
            line[len("$ANSWER$") :].strip()
            for line in out.stdout.splitlines()
            if line.startswith("$ANSWER$")
        ]
        if len(answer_lines) > 0:
            answer = "\n".join(answer_lines)
            await cl.Message(content=answer).send()
