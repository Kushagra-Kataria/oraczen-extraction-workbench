import asyncio
import csv
import io

import httpx
import pytest

from app.config import Settings
from app.main import create_app
from app.schemas import FIELDS


@pytest.fixture
async def session():
    app = create_app(Settings(mock_delay_ms=0))
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client, app.state.manager


async def completed_job(client, manager, ids=None):
    response = await client.post("/api/jobs", json={"ticket_ids": ids or ["tkt_0003"]})
    assert response.status_code == 202
    job_id = response.json()["id"]
    task = manager.tasks.get(job_id)
    if task:
        await task
    records = (await client.get(f"/api/jobs/{job_id}/results")).json()["records"]
    return job_id, records[0]


async def test_correction_rejects_invalid_fields_without_mutating(session):
    client, manager = session
    _, record = await completed_job(client, manager)
    response = await client.patch(
        f"/api/records/{record['id']}",
        json={
            "version": record["version"],
            "fields": {"severity": "urgent", "company": "New"},
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["field"] == "severity"
    assert manager.store.records[record["id"]].values["company"] == record["values"]["company"]
    assert manager.store.records[record["id"]].version == 1


async def test_partial_repair_tracks_human_fields_and_rejects_stale_versions(session):
    client, manager = session
    _, record = await completed_job(client, manager)
    url = f"/api/records/{record['id']}"
    response = await client.patch(url, json={"version": 1, "fields": {"product": "Zen Vault"}})
    assert response.status_code == 200
    updated = response.json()
    assert updated["field_meta"]["product"]["source"] == "human"
    assert updated["field_meta"]["company"]["source"] == "model"
    assert updated["status"] == "needs_review"
    assert not updated["schema_valid"]  # Severity still missing.
    assert updated["version"] == 2
    stale = await client.patch(url, json={"version": 1, "fields": {"company": "Other"}})
    assert stale.status_code == 409
    assert manager.store.records[record["id"]].values["company"] != "Other"


async def test_incomplete_record_cannot_be_approved(session):
    client, manager = session
    _, record = await completed_job(client, manager)
    response = await client.patch(
        f"/api/records/{record['id']}",
        json={
            "version": 1,
            "reviewed": True,
        },
    )
    assert response.status_code == 422
    assert not manager.store.records[record["id"]].reviewed


async def test_export_includes_only_reviewed_records_and_handles_csv_text(session):
    client, manager = session
    job_id, record = await completed_job(client, manager, ["tkt_0003", "tkt_0005"])
    response = await client.patch(
        f"/api/records/{record['id']}",
        json={
            "version": 1,
            "fields": {
                "company": 'Acme, "North"\nDivision',
                "product": "Zen Vault",
                "severity": "low",
            },
            "reviewed": True,
        },
    )
    assert response.status_code == 200
    exported = await client.get(f"/api/jobs/{job_id}/export.csv")
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/csv")
    assert "attachment" in exported.headers["content-disposition"]
    rows = list(csv.DictReader(io.StringIO(exported.text)))
    assert len(rows) == 1
    assert rows[0]["company"] == 'Acme, "North"\nDivision'
    assert rows[0]["escalated"] == "false"
    assert set(FIELDS).issubset(rows[0])
    assert "product" in rows[0]["human_edited_fields"]
    assert exported.headers["x-skipped-records"] == "1"
    # Formula-like customer text is escaped, not executed on opening a spreadsheet.
    updated = response.json()
    await client.patch(
        f"/api/records/{record['id']}",
        json={
            "version": updated["version"],
            "fields": {"company": "=SUM(1,2)"},
            "reviewed": True,
        },
    )
    exported = await client.get(f"/api/jobs/{job_id}/export.csv")
    assert list(csv.DictReader(io.StringIO(exported.text)))[0]["company"] == "'=SUM(1,2)"


async def test_job_input_validation_and_missing_job(session):
    client, _ = session
    for ids in ([], ["unknown"], ["tkt_0001", "tkt_0001"]):
        response = await client.post("/api/jobs", json={"ticket_ids": ids})
        assert response.status_code == 422
    assert (await client.get("/api/jobs/nonexistent")).status_code == 404
    assert len((await client.get("/api/tickets")).json()["tickets"]) == 150


async def test_provider_failure_is_isolated_and_cancel_before_first_turn(session):
    _, manager = session

    class FailingProvider:
        async def extract(self, ticket, feedback=None):
            raise RuntimeError("Provider unavailable")

    manager.provider = FailingProvider()
    job = manager.submit(["tkt_0006", "tkt_0020"])
    await manager.tasks[job.id]
    assert job.state == "done"
    assert job.snapshot()["failed"] == 1
    assert job.snapshot()["done"] == 1
    early = manager.submit(["tkt_0006"])
    await manager.cancel(early.id)
    assert early.state == "cancelled"
    assert early.items[0].record_id in manager.store.records
    await asyncio.sleep(0)
    assert not manager.tasks
