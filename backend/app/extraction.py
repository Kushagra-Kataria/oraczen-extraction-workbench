"""One ticket's validation/retry lifecycle, independent of HTTP and job scheduling."""

import asyncio
import json

from pydantic import ValidationError

from .providers.base import ExtractionProvider
from .schemas import (
    FIELDS,
    Extraction,
    FieldError,
    FieldMeta,
    Proposal,
    Record,
    Ticket,
    validate_field,
)


def field_errors(exc: ValidationError) -> list[FieldError]:
    return [
        FieldError(
            field=str(error["loc"][0]) if error["loc"] and error["loc"][0] in FIELDS else "record",
            message=error["msg"],
        )
        for error in exc.errors(include_url=False)
    ]


def populate_draft(record: Record, proposal: Proposal, ticket: Ticket) -> None:
    """Salvage individually valid values without accepting an invalid complete record."""
    text = f"{ticket.subject}\n{ticket.body}"
    record.notes = proposal.notes.copy()
    for name in FIELDS:
        value = proposal.record.get(name)
        try:
            value = validate_field(name, value)
        except (ValueError, TypeError):
            value = None
        record.values[name] = value
        quote = proposal.evidence.get(name)
        grounded = bool(quote and quote in text)
        # Negative defaults are useful, but still explicitly inferred rather than quoted facts.
        record.field_meta[name] = FieldMeta(
            source="model" if value is not None else "missing",
            grounding="missing" if value is None else "grounded" if grounded else "inferred",
            evidence=quote if grounded else None,
        )


def complete_record(record: Record, extraction: Extraction) -> Record:
    """Complete records leave the review queue; evidence and approval stay separate."""
    record.values = extraction.model_dump(mode="json")
    record.schema_valid = True
    record.errors = []
    record.status = "done"
    return record


async def extract_ticket(
    ticket: Ticket, job_id: str, provider: ExtractionProvider, timeout_seconds: float = 30
) -> Record:
    record = Record(id=f"{job_id}:{ticket.id}", job_id=job_id, ticket_id=ticket.id)
    if ticket.body.strip().lower() in {"?", "please advise"}:
        record.notes = [
            "Insufficient content. Provider call skipped; request customer clarification."
        ]
        record.errors = [FieldError(field="record", message="Required information is missing")]
        return record

    feedback = None
    for attempt in (1, 2):
        record.attempts = attempt
        try:
            raw = await asyncio.wait_for(provider.extract(ticket, feedback), timeout_seconds)
        except Exception as exc:
            # Cancellation is a BaseException and intentionally propagates to the job manager.
            record.status = "failed"
            record.notes.append(f"Provider failed ({type(exc).__name__}); other tickets continue.")
            return record
        record.raw_outputs.append(raw)
        try:
            proposal = Proposal.model_validate_json(raw)
            populate_draft(record, proposal, ticket)
            extraction = Extraction.model_validate_json(json.dumps(proposal.record))
        except ValidationError as exc:
            record.errors = field_errors(exc)
            feedback = json.dumps([error.model_dump() for error in record.errors])
            continue

        return complete_record(record, extraction)

    # A usable partial draft does not make a rejected provider output acceptable.
    # Retain the last validation errors and both raw attempts for a human decision.
    record.notes.append(
        "Output failed validation twice. Review the errors and retained draft before approval."
    )
    return record
