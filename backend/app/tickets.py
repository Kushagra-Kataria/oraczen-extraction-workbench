"""Load and validate the original JSONL dataset at startup."""

from pathlib import Path

from .schemas import Ticket


def load_tickets(path: Path) -> dict[str, Ticket]:
    tickets: dict[str, Ticket] = {}
    with path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                ticket = Ticket.model_validate_json(line)
            except ValueError as exc:
                raise ValueError(f"Invalid ticket at line {line_number}: {exc}") from exc
            if ticket.id in tickets:
                raise ValueError(f"Duplicate ticket ID at line {line_number}: {ticket.id}")
            tickets[ticket.id] = ticket
    if not tickets:
        raise ValueError("The ticket dataset is empty")
    return tickets
