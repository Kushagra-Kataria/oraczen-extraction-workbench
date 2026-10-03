"""One ticket's validation/retry lifecycle, independent of HTTP and job scheduling."""

import asyncio
import json

from pydantic import ValidationError

from .providers.base import ExtractionProvider
from .schemas import (
    FIELDS,
    OPTIONAL_FIELDS,
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


def requires_human_review(record: Record) -> bool:
    """Keep the review queue for meaningful uncertainty, not harmless defaults.

    A missing quote for a customer-selected value needs a reviewer. By contrast,
    ``requested_action: none`` and ``escalated: false`` are safe negative defaults:
    the ticket does not need to explicitly say that it is *not* escalated or that it
    requests no action. They remain labelled as inferred in the UI without making a
    complete record look broken.

    Notes are informational by default. The small set below describes ambiguity or a
    transformation that a reviewer should actively check.
    """
    for name in FIELDS:
        meta = record.field_meta[name]
        value = record.values[name]
        if name in OPTIONAL_FIELDS or meta.grounding == "grounded":
            continue
        if name == "requested_action" and value == "none":
            continue
        if name == "escalated" and value is False:
            continue
        return True

    review_note_prefixes = (
        "Company was inferred",
        "Company in the body differs",
        "Product spelling was normalized",
        "Multiple USD amounts",
        "Original amount:",
        "Spoken amount is approximate",
        "Ambiguous deadline",
        "Multiple issues:",
    )
    return any(note.startswith(review_note_prefixes) for note in record.notes)


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

        record.values = extraction.model_dump(mode="json")
        record.schema_valid = True
        record.errors = []
        record.status = "needs_review" if requires_human_review(record) else "done"
        return record

    record.notes.append(
        "Output failed validation twice. Correct the draft or consult the raw output."
    )
    return record
