"""Tracked background jobs with a provider cap shared across all submitted batches."""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from .config import Settings
from .extraction import extract_ticket
from .providers.base import ExtractionProvider
from .schemas import Job, JobItem, Record
from .store import Store


class JobManager:
    def __init__(self, store: Store, provider: ExtractionProvider, settings: Settings):
        self.store = store
        self.provider = provider
        self.settings = settings
        self.semaphore = asyncio.Semaphore(settings.max_concurrency)
        # Strong references keep tasks alive and allow orderly shutdown/cancellation.
        self.tasks: dict[str, asyncio.Task] = {}

    def submit(self, ticket_ids: list[str]) -> Job:
        job = Job(
            id=uuid4().hex,
            created_at=datetime.now(UTC),
            items=[JobItem(ticket_id=ticket_id) for ticket_id in ticket_ids],
        )
        self.store.jobs[job.id] = job
        task = asyncio.create_task(self._run(job))
        self.tasks[job.id] = task
        task.add_done_callback(lambda _: self.tasks.pop(job.id, None))
        return job

    async def _process(self, job: Job, item: JobItem) -> None:
        async with self.semaphore:
            item.status = "running"
            try:
                record = await extract_ticket(
                    self.store.tickets[item.ticket_id],
                    job.id,
                    self.provider,
                    self.settings.provider_timeout_seconds,
                )
            except Exception as exc:
                # A malformed provider adapter must not abort unrelated items either.
                record = Record(
                    id=f"{job.id}:{item.ticket_id}",
                    job_id=job.id,
                    ticket_id=item.ticket_id,
                    status="failed",
                    notes=[f"Processing failed ({type(exc).__name__})."],
                )
            self.store.records[record.id] = record
            item.record_id = record.id
            item.status = record.status

    async def _run(self, job: Job) -> None:
        job.state = "running"
        try:
            await asyncio.gather(*(self._process(job, item) for item in job.items))
        except asyncio.CancelledError:
            self._cancel_unfinished(job)
            return
        job.state = "done"

    def _cancel_unfinished(self, job: Job) -> None:
        # Terminalize unfinished items so progress sums to total even after cancellation.
        for item in job.items:
            if item.status in {"queued", "running"}:
                record = Record(
                    id=f"{job.id}:{item.ticket_id}",
                    job_id=job.id,
                    ticket_id=item.ticket_id,
                    status="failed",
                    notes=["Cancelled before processing completed."],
                )
                self.store.records[record.id] = record
                item.record_id, item.status = record.id, "failed"
        job.state = "cancelled"

    async def cancel(self, job_id: str) -> None:
        task = self.tasks.get(job_id)
        if task and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            # A task cancelled before its first event-loop turn has not entered _run.
            job = self.store.jobs[job_id]
            if job.state == "queued":
                self._cancel_unfinished(job)

    async def close(self) -> None:
        for job_id in list(self.tasks):
            await self.cancel(job_id)
