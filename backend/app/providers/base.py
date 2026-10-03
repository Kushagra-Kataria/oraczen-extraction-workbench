"""Small provider boundary: a real LLM can implement the same async method."""

from typing import Protocol

from ..schemas import Ticket


class ExtractionProvider(Protocol):
    async def extract(self, ticket: Ticket, feedback: str | None = None) -> str:
        """Return raw JSON; feedback describes a previous schema-validation failure."""
        ...
