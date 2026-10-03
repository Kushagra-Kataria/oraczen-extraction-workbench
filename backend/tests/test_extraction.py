import json

import pytest

from app.config import Settings
from app.extraction import extract_ticket
from app.providers.mock import MockProvider
from app.schemas import Extraction
from app.tickets import load_tickets


class ScriptedProvider:
    def __init__(self, records):
        self.records = records
        self.feedback = []

    async def extract(self, ticket, feedback=None):
        self.feedback.append(feedback)
        return json.dumps(
            {"record": self.records[min(len(self.feedback) - 1, len(self.records) - 1)]}
        )


@pytest.fixture
def tickets():
    return load_tickets(Settings().dataset_path())


@pytest.fixture
def valid():
    return {
        "company": "Acme",
        "product": "Zen Studio",
        "category": "outage",
        "severity": "critical",
        "requested_action": "fix",
        "escalated": False,
        "refund_amount": None,
        "deadline": None,
    }


async def test_invalid_output_is_retried_with_actual_validation_errors(tickets, valid):
    provider = ScriptedProvider([{**valid, "severity": "urgent"}, valid])
    result = await extract_ticket(tickets["tkt_0005"], "job", provider)
    assert result.attempts == 2
    assert provider.feedback[0] is None
    assert "severity" in provider.feedback[1]
    assert "critical" in provider.feedback[1]
    assert result.schema_valid
    assert result.values["severity"] == "critical"
    assert len(result.raw_outputs) == 2


async def test_safe_negative_defaults_do_not_force_a_valid_ticket_into_review(tickets):
    result = await extract_ticket(tickets["tkt_0005"], "job", MockProvider(0))
    assert result.schema_valid
    assert result.attempts == 2
    assert result.values["requested_action"] == "none"
    assert result.values["escalated"] is False
    assert result.status == "done"


async def test_repeated_invalid_output_preserves_a_reviewable_draft(tickets, valid):
    provider = ScriptedProvider([{**valid, "product": "Imaginary"}])
    result = await extract_ticket(tickets["tkt_0003"], "job", provider)
    assert result.status == "needs_review"
    assert not result.schema_valid
    assert result.values["product"] is None
    assert result.values["company"] == "Acme"
    assert result.errors[0].field == "product"
    assert len(result.raw_outputs) == 2


async def test_sparse_ticket_never_calls_provider(tickets, valid):
    provider = ScriptedProvider([valid])
    result = await extract_ticket(tickets["tkt_0020"], "job", provider)
    assert result.status == "needs_review"
    assert result.attempts == 0
    assert provider.feedback == []


async def test_mock_is_deterministic_and_currency_is_not_converted(tickets):
    provider = MockProvider(0)
    first = await provider.extract(tickets["tkt_0058"])
    assert first == await provider.extract(tickets["tkt_0058"])
    result = await extract_ticket(tickets["tkt_0058"], "job", provider)
    assert result.values["company"] == "Orchid Hospitality"
    assert result.values["refund_amount"] is None
    assert any("EUR" in note for note in result.notes)


@pytest.mark.parametrize(
    "change",
    [
        {"refund_amount": "300"},
        {"refund_amount": -1},
        {"refund_amount": float("inf")},
        {"escalated": "false"},
        {"escalated": 1},
        {"company": "   "},
        {"deadline": "2026-02-30"},
        {"surprise": "extra field"},
    ],
)
def test_schema_rejects_coercions_invalid_dates_and_extra_fields(valid, change):
    with pytest.raises(ValueError):
        Extraction.model_validate_json(json.dumps({**valid, **change}))
