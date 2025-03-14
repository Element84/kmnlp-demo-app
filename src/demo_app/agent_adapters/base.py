import logging
from abc import ABC, abstractmethod

import chainlit as cl

log = logging.getLogger(__name__)


class ChainlitAdapter(ABC):
    """Chainlit adapter base class."""

    @abstractmethod
    async def process_message(self, message: cl.Message) -> None:
        """Handle user message by updating the UI."""
