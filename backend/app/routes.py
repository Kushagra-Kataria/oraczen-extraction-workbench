"""HTTP boundaries: validate requests, delegate work, and serialize current state."""

import csv
import io
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from .jobs import JobManager
from .review import correct_record
from .schemas import FIELDS, Correction, Job, JobRequest

router = APIRouter(prefix="/api")


def manager(request: Request) -> JobManager:
    return request.app.state.manager


Manager = Annotated[JobManager, Depends(manager)]


def find_job(service: JobManager, job_id: str) -> Job:
    job = service.store.jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found. Backend restarts clear in-memory jobs.")
    return job


@router.get("/health")
async def health(service: Manager):
    return {"status": "ok", "provider": service.settings.extraction_provider}


@router.get("/tickets")
async def tickets(service: Manager):
    return {
        "tickets": [ticket.model_dump(mode="json") for ticket in service.store.tickets.values()]
    }


@router.post("/jobs", status_code=202)
async def create_job(body: JobRequest, service: Manager):
    if len(body.ticket_ids) != len(set(body.ticket_ids)):
        raise HTTPException(
            422, [{"field": "ticket_ids", "message": "Duplicate IDs are not allowed"}]
        )
    unknown = [ticket_id for ticket_id in body.ticket_ids if ticket_id not in service.store.tickets]
    if unknown:
        raise HTTPException(422, [{"field": "ticket_ids", "message": f"Unknown IDs: {unknown}"}])
    return service.submit(body.ticket_ids).snapshot()


@router.get("/jobs/{job_id}")
async def job_status(job_id: str, service: Manager):
    return find_job(service, job_id).snapshot()


@router.get("/jobs/{job_id}/results")
async def results(job_id: str, service: Manager):
    job = find_job(service, job_id)
    return {
        "records": [
            {
                **service.store.records[item.record_id].model_dump(mode="json"),
                "ticket": service.store.tickets[item.ticket_id].model_dump(mode="json"),
            }
            for item in job.items
            if item.record_id
        ]
    }


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str, service: Manager):
    job = find_job(service, job_id)
    await service.cancel(job_id)
    return job.snapshot()


@router.patch("/records/{record_id}")
async def patch_record(record_id: str, body: Correction, service: Manager):
    record = service.store.records.get(record_id)
    if not record:
        raise HTTPException(404, "Record not found")
    updated = correct_record(service, record, body)
    return {
        **updated.model_dump(mode="json"),
        "ticket": service.store.tickets[updated.ticket_id].model_dump(mode="json"),
    }


def csv_cell(value):
    # Prevent customer text from being interpreted as a formula by spreadsheet apps.
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    if isinstance(value, bool):
        return str(value).lower()
    return value


@router.get("/jobs/{job_id}/export.csv")
async def export_csv(job_id: str, service: Manager):
    job = find_job(service, job_id)
    records = [service.store.records[item.record_id] for item in job.items if item.record_id]
    reviewed = [record for record in records if record.reviewed and record.schema_valid]
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["ticket_id", *FIELDS, "human_edited_fields"])
    for record in reviewed:
        edited = ";".join(name for name in FIELDS if record.field_meta[name].source == "human")
        writer.writerow(
            [record.ticket_id, *[csv_cell(record.values[name]) for name in FIELDS], edited]
        )
    return Response(
        output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="reviewed-{job.id}.csv"',
            "X-Exported-Records": str(len(reviewed)),
            "X-Skipped-Records": str(len(job.items) - len(reviewed)),
        },
    )
