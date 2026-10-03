"""Opt-in live Gemini check using invented tickets, never the assignment dataset.

Run from backend: .venv/Scripts/python.exe scripts/smoke_gemini.py
This uses the configured Gemini key and may consume API quota. All API state and
synthetic data live in an isolated application and temporary directory.
"""

import asyncio
import csv
import io
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx

# Direct script execution puts scripts/ on sys.path; expose the backend package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


def synthetic_tickets() -> list[dict]:
    common = {
        "channel": "web_form",
        "received_at": "2026-10-04T00:00:00Z",
        "from_email": "test@example.invalid",
        "attachments": 0,
    }
    return [
        {
            **common,
            "id": "synthetic_outage",
            "subject": "Zen Studio outage",
            "body": (
                "Fictional test data. Company: Example Test Company. "
                "Zen Studio is completely down for all users. This is critical severity. "
                "Please fix it immediately. This has not been escalated."
            ),
        },
        {
            **common,
            "id": "synthetic_billing",
            "subject": "Duplicate invoice",
            "body": (
                "Fictional test data. Company: Example Billing Company. "
                "We were charged twice for Zen Vault. This is medium severity. "
                "Please refund exactly USD 125.50. Please escalate this to your manager."
            ),
        },
        {**common, "id": "synthetic_empty", "subject": "", "body": "?"},
    ]


async def verify() -> None:
    with TemporaryDirectory(prefix="workbench-smoke-") as directory:
        dataset = Path(directory) / "synthetic.jsonl"
        tickets = synthetic_tickets()
        dataset.write_text("\n".join(json.dumps(ticket) for ticket in tickets), encoding="utf-8")
        settings = Settings(extraction_provider="gemini", tickets_path=dataset)
        app = create_app(settings)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://smoke"
            ) as client:
                health = (await client.get("/api/health")).json()
                assert health["provider"] == "gemini", health
                response = await client.post(
                    "/api/jobs", json={"ticket_ids": [ticket["id"] for ticket in tickets]}
                )
                assert response.status_code == 202, response.text
                job_id = response.json()["id"]
                await app.state.manager.tasks[job_id]
                status = (await client.get(f"/api/jobs/{job_id}")).json()
                assert status["state"] == "done", status
                assert status["done"] == 3 and status["failed"] == 0, status
                records = (await client.get(f"/api/jobs/{job_id}/results")).json()["records"]
                by_ticket = {record["ticket_id"]: record for record in records}
                outage = by_ticket["synthetic_outage"]
                billing = by_ticket["synthetic_billing"]
                assert outage["schema_valid"] and billing["schema_valid"], records
                assert outage["values"]["category"] == "outage", outage["values"]
                assert billing["values"]["category"] == "billing", billing["values"]
                assert billing["values"]["refund_amount"] == 125.50, billing["values"]
                sparse = by_ticket["synthetic_empty"]
                assert sparse["status"] == "needs_review" and sparse["attempts"] == 0

                record_url = f"/api/records/{outage['id']}"
                invalid = await client.patch(
                    record_url, json={"version": 1, "fields": {"severity": "urgent"}}
                )
                assert invalid.status_code == 422, invalid.text
                approved = await client.patch(
                    record_url,
                    json={
                        "version": 1,
                        "fields": {"company": "Example Test Company"},
                        "reviewed": True,
                    },
                )
                assert approved.status_code == 200, approved.text
                assert approved.json()["field_meta"]["company"]["source"] == "human"
                stale = await client.patch(record_url, json={"version": 1, "fields": {}})
                assert stale.status_code == 409, stale.text
                exported = await client.get(f"/api/jobs/{job_id}/export.csv")
                rows = list(csv.DictReader(io.StringIO(exported.text)))
                assert len(rows) == 1 and rows[0]["ticket_id"] == "synthetic_outage", rows
                assert rows[0]["human_edited_fields"] == "company", rows
                print(
                    json.dumps(
                        {
                            "provider": health["provider"],
                            "model": settings.gemini_model,
                            "synthetic_tickets": status["total"],
                            "processed": status["done"],
                            "failed": status["failed"],
                            "review_and_export": "passed",
                            "assignment_data_sent": False,
                        },
                        indent=2,
                    )
                )


if __name__ == "__main__":
    asyncio.run(verify())
