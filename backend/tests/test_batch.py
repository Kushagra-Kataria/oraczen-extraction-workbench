import asyncio
import json

from app.config import Settings
from app.extraction import extract_ticket
from app.jobs import JobManager
from app.providers.mock import MockProvider
from app.schemas import Extraction
from app.store import Store
from app.tickets import load_tickets


async def test_all_150_tickets_terminalize_with_valid_progress_and_no_provider_failures():
    settings = Settings(mock_delay_ms=0, max_concurrency=4)
    tickets = load_tickets(settings.dataset_path())
    manager = JobManager(Store(tickets), MockProvider(0), settings)
    job = manager.submit(list(tickets))
    await manager.tasks[job.id]
    snapshot = job.snapshot()
    assert snapshot["state"] == "done"
    assert snapshot["total"] == snapshot["done"] == len(manager.store.records) == 150
    assert snapshot["queued"] == snapshot["running"] == snapshot["failed"] == 0
    for record in manager.store.records.values():
        assert set(record.field_meta) == set(Extraction.model_fields)
        if record.schema_valid:
            Extraction.model_validate_json(json.dumps(record.values))
        else:
            assert record.status == "needs_review"
        assert record.attempts <= 2


async def test_multi_issue_and_spoken_amount_policies_are_visible():
    tickets = load_tickets(Settings().dataset_path())
    multi = await extract_ticket(tickets["tkt_0089"], "job", MockProvider(0))
    assert multi.values["category"] == "churn_risk"
    assert multi.values["refund_amount"] is None
    assert multi.values["deadline"] is None
    assert multi.values["escalated"] is True
    assert any("Multiple issues" in note for note in multi.notes)
    assert any("sender domain" in note for note in multi.notes)
    spoken = await extract_ticket(tickets["tkt_0131"], "job", MockProvider(0))
    assert spoken.values["requested_action"] == "credit"
    assert spoken.values["refund_amount"] is None
    assert any("approximate" in note for note in spoken.notes)


async def test_provider_timeout_becomes_a_failed_item():
    class SlowProvider:
        async def extract(self, ticket, feedback=None):
            await asyncio.Event().wait()

    ticket = load_tickets(Settings().dataset_path())["tkt_0005"]
    result = await extract_ticket(ticket, "job", SlowProvider(), timeout_seconds=0.01)
    assert result.status == "failed"
    assert result.attempts == 1
    assert "TimeoutError" in result.notes[0]
