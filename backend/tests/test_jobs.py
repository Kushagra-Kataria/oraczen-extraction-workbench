import asyncio

import httpx

from app.config import Settings
from app.jobs import JobManager
from app.main import create_app
from app.providers.mock import MockProvider
from app.store import Store
from app.tickets import load_tickets


def make_manager(provider=None, cap=1):
    settings = Settings(mock_delay_ms=0, max_concurrency=cap)
    return JobManager(
        Store(load_tickets(settings.dataset_path())), provider or MockProvider(0), settings
    )


async def test_twice_invalid_item_does_not_prevent_job_completion():
    manager = make_manager()
    job = manager.submit(["tkt_0003", "tkt_0005"])
    await manager.tasks[job.id]
    assert job.state == "done"
    record = manager.store.records[job.items[0].record_id]
    assert record.status == "needs_review"
    assert record.attempts == 2
    assert not record.schema_valid
    repaired = manager.store.records[job.items[1].record_id]
    assert repaired.schema_valid
    assert repaired.attempts == 2
    assert job.snapshot()["done"] == 2
    assert job.snapshot()["failed"] == 0


class GateProvider(MockProvider):
    def __init__(self):
        super().__init__(0)
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.active = 0
        self.peak = 0

    async def extract(self, ticket, feedback=None):
        self.active += 1
        self.peak = max(self.peak, self.active)
        self.started.set()
        try:
            await self.release.wait()
            return await super().extract(ticket, feedback)
        finally:
            self.active -= 1


async def test_progress_arithmetic_and_completion_transition():
    provider = GateProvider()
    manager = make_manager(provider)
    job = manager.submit(["tkt_0006", "tkt_0005", "tkt_0020"])
    initial = job.snapshot()
    assert initial["queued"] == initial["total"] == 3
    assert initial["state"] == "queued"
    await asyncio.wait_for(provider.started.wait(), 2)
    running = job.snapshot()
    assert running["state"] == "running"
    assert (running["queued"], running["running"], running["done"], running["failed"]) == (
        2,
        1,
        0,
        0,
    )
    assert sum(running[key] for key in ("queued", "running", "done", "failed")) == 3
    provider.release.set()
    await manager.tasks[job.id]
    final = job.snapshot()
    assert final["state"] == "done"
    assert (final["queued"], final["running"], final["done"], final["failed"]) == (0, 0, 3, 0)
    assert provider.peak == 1


async def test_http_202_returns_while_provider_is_still_blocked():
    provider = GateProvider()
    app = create_app(Settings(mock_delay_ms=0), provider)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await asyncio.wait_for(
                client.post("/api/jobs", json={"ticket_ids": ["tkt_0006"]}), 2
            )
            assert response.status_code == 202
            job_id = response.json()["id"]
            await asyncio.wait_for(provider.started.wait(), 2)
            status = (await client.get(f"/api/jobs/{job_id}")).json()
            assert status["state"] == "running"
            assert status["running"] == 1
            provider.release.set()
            await app.state.manager.tasks[job_id]


async def test_concurrency_cap_is_shared_across_jobs():
    provider = GateProvider()
    manager = make_manager(provider, cap=2)
    one = manager.submit(["tkt_0006", "tkt_0007"])
    two = manager.submit(["tkt_0008", "tkt_0009"])
    await asyncio.wait_for(provider.started.wait(), 2)
    # Yield once so all workers can attempt to acquire the same semaphore.
    await asyncio.sleep(0)
    assert provider.peak == 2
    provider.release.set()
    await asyncio.gather(manager.tasks[one.id], manager.tasks[two.id])
    assert provider.peak == 2


async def test_cancel_terminalizes_unfinished_items():
    provider = GateProvider()
    manager = make_manager(provider)
    job = manager.submit(["tkt_0006", "tkt_0007"])
    await asyncio.wait_for(provider.started.wait(), 2)
    await manager.cancel(job.id)
    snapshot = job.snapshot()
    assert snapshot["state"] == "cancelled"
    assert snapshot["running"] == snapshot["queued"] == 0
    assert snapshot["failed"] == snapshot["total"] == 2
    assert provider.active == 0
