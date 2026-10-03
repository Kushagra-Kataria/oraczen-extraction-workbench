"""Process-local state. All mutations run on the same asyncio event loop."""

from dataclasses import dataclass, field

from .schemas import Job, Record, Ticket


@dataclass
class Store:
    tickets: dict[str, Ticket]
    jobs: dict[str, Job] = field(default_factory=dict)
    records: dict[str, Record] = field(default_factory=dict)
