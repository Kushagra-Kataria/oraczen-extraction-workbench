"""Apply corrections atomically and retain field-level human provenance."""

import json

from fastapi import HTTPException
from pydantic import ValidationError

from .extraction import field_errors
from .jobs import JobManager
from .schemas import FIELDS, Correction, Extraction, FieldError, FieldMeta, Record, validate_field


def correct_record(service: JobManager, record: Record, correction: Correction) -> Record:
    if correction.version != record.version:
        raise HTTPException(409, "This record changed. Reload the record before saving your edits.")
    errors: list[FieldError] = []
    changes = {}
    for name, value in correction.fields.items():
        if name not in FIELDS:
            errors.append(FieldError(field=name, message="Unknown extraction field"))
            continue
        try:
            changes[name] = validate_field(name, value)
        except ValidationError as exc:
            errors.extend(FieldError(field=name, message=item["msg"]) for item in exc.errors())
        except ValueError as exc:
            errors.append(FieldError(field=name, message=str(exc)))
    if errors:
        raise HTTPException(422, [error.model_dump() for error in errors])

    merged = {**record.values, **changes}
    try:
        valid = Extraction.model_validate_json(json.dumps(merged))
        merged = valid.model_dump(mode="json")
        validation_errors = []
    except ValidationError as exc:
        validation_errors = field_errors(exc)

    # Review approval is a separate action and requires a complete, valid record.
    if correction.reviewed is True and validation_errors:
        raise HTTPException(422, [error.model_dump() for error in validation_errors])

    # No awaits below: check-version, validate, and replace are atomic on this event loop.
    updated = record.model_copy(deep=True)
    updated.values = merged
    for name in changes:
        updated.field_meta[name] = FieldMeta(source="human", grounding="grounded")
    updated.schema_valid = not validation_errors
    updated.errors = validation_errors
    if changes:
        updated.reviewed = False  # Any later edit requires an explicit review decision again.
    if correction.reviewed is not None:
        updated.reviewed = correction.reviewed
    updated.status = "done" if updated.reviewed else "needs_review"
    updated.version += 1
    service.store.records[updated.id] = updated
    for item in service.store.jobs[updated.job_id].items:
        if item.record_id == updated.id:
            item.status = updated.status
            break
    return updated
