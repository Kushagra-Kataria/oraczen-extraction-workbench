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
    assert result.status == "done"


async def test_complete_record_without_evidence_or_optional_fields_is_done(tickets, valid):
    values = {
        name: value for name, value in valid.items() if name not in {"refund_amount", "deadline"}
    }
    result = await extract_ticket(tickets["tkt_0005"], "job", ScriptedProvider([values]))
    assert result.status == "done"
    assert result.schema_valid
    assert result.values["refund_amount"] is None
    assert result.values["deadline"] is None
    assert result.values["escalated"] is False
    assert all(meta.evidence is None for meta in result.field_meta.values())
    assert not result.reviewed  # Extraction completion does not grant export approval.


async def test_notes_and_unmatched_evidence_do_not_route_a_complete_record_to_review(
    tickets, valid
):
    class AnnotatedProvider:
        async def extract(self, ticket, feedback=None):
            return json.dumps(
                {
                    "record": valid,
                    "evidence": {name: "Quote absent from this ticket" for name in valid},
                    "notes": [
                        "Company was inferred",
                        "Ambiguous deadline",
                        "Multiple issues: billing",
                    ],
                }
            )

    result = await extract_ticket(tickets["tkt_0005"], "job", AnnotatedProvider())
    assert result.status == "done"
    assert result.schema_valid
    assert len(result.notes) == 3
    assert result.field_meta["company"].grounding == "inferred"


@pytest.mark.parametrize(
    "name", ["company", "product", "category", "severity", "requested_action", "escalated"]
)
@pytest.mark.parametrize("missing", ["absent", "null"])
async def test_each_missing_required_field_routes_to_review(tickets, valid, name, missing):
    values = valid.copy()
    if missing == "absent":
        values.pop(name)
    else:
        values[name] = None
    result = await extract_ticket(tickets["tkt_0005"], "job", ScriptedProvider([values]))
    assert result.status == "needs_review"
    assert not result.schema_valid
    assert result.values[name] is None
    assert any(error.field == name for error in result.errors)
    assert result.attempts == 2


@pytest.mark.parametrize("change", [{"refund_amount": "125 USD"}, {"deadline": "Thursday"}])
async def test_invalid_optional_value_can_be_omitted_without_review(tickets, valid, change):
    result = await extract_ticket(
        tickets["tkt_0005"], "job", ScriptedProvider([{**valid, **change}])
    )
    name = next(iter(change))
    assert result.status == "done"
    assert result.schema_valid
    assert result.values[name] is None
    assert result.attempts == 2
    assert len(result.raw_outputs) == 2
    assert any("validated draft" in note for note in result.notes)


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
