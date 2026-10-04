"""Invented tickets cover meaning, source preservation, and boilerplate boundaries."""

import json

import pytest

from app.extraction import extract_ticket
from app.providers.mock import MockProvider
from app.schemas import Ticket


def invented(body: str, subject: str = "Support question") -> Ticket:
    return Ticket(
        id="invented_customer_ticket",
        subject=subject,
        body=body,
        channel="email",
        received_at="2026-08-15T12:00:00Z",
        from_email="sam@example.com",
        attachments=0,
    )


@pytest.mark.parametrize(
    "footer",
    [
        "This email and any attachments are confidential and intended solely for the addressee. "
        "If you have received this in error please delete it.",
        "This message is confidential.\nIf you have received this message in error, "
        "please notify the sender.",
        "Confidentiality notice:\nIf you received this email in error, delete it.\n"
        "Sent from my iPhone",
        "If you have received this in error please delete it.",
    ],
)
async def test_quota_question_is_not_a_bug_because_of_confidentiality_footer(footer):
    ticket = invented(
        "Does Zen Orchestrator count a retried run against our monthly quota?\n\n"
        f"--\nSam Example | Operations | Example Labs\n{footer}"
    )
    record = await extract_ticket(ticket, "test", MockProvider(0))
    assert record.values["category"] == "how_to"
    assert record.field_meta["category"].grounding == "grounded"
    assert "in error" not in record.field_meta["category"].evidence
    assert "in error" in ticket.body  # The full source remains available to the UI.


async def test_genuine_product_error_still_becomes_bug_with_original_evidence():
    ticket = invented(
        "Zen Studio returns an error when I save a workflow. A workaround is available.\n\n"
        "Regards,\nSam Example\nExample Labs\n\n"
        "This email is confidential; delete it if received in error."
    )
    proposal = json.loads(await MockProvider(0).extract(ticket))
    assert proposal["record"]["category"] == "bug"
    assert proposal["evidence"]["category"] in ticket.body
    assert "returns an error" in proposal["evidence"]["category"]


async def test_quoted_unresolved_issue_survives_current_signature_and_quoted_footer():
    ticket = invented(
        "Can you provide an update?\n\n"
        "--\nSam Example | Operations | Example Labs\n"
        "This email is confidential. If received in error please delete it.\n"
        "> On Monday, Sam wrote:\n"
        "> Zen Connect silently drops rows longer than 4000 characters.\n"
        "> A workaround is available; please fix this unresolved issue.\n"
        "> Regards,\n> Sam Example\n> Example Labs\n"
        "> This message is confidential.\n> Please call me about invoice credits.\n"
    )
    original = ticket.model_dump()
    record = await extract_ticket(ticket, "test", MockProvider(0))
    assert record.values["category"] == "bug"
    assert record.values["product"] == "Zen Connect"
    assert record.values["severity"] == "low"
    assert record.values["requested_action"] == "fix"
    assert record.field_meta["category"].evidence == "drops rows"
    assert record.field_meta["category"].grounding == "grounded"
    assert ticket.model_dump() == original


async def test_quoted_escalation_remains_available_without_a_ticket_id_exception():
    ticket = invented(
        "Any update on the unresolved issue?\n\n"
        "> We will not renew Zen Vault unless this is fixed. Our CFO is escalating.\n"
        "> Regards,\n> Sam Example\n> Example Labs"
    )
    proposal = json.loads(await MockProvider(0).extract(ticket))
    assert proposal["record"]["category"] == "churn_risk"
    assert proposal["record"]["escalated"] is True


async def test_signature_company_is_preserved_without_classifying_its_role_or_name():
    ticket = invented(
        "Does Zen Orchestrator count retried runs against our quota?\n\n"
        "--\nSam Example | Critical Escalation Manager | Example Credit Labs\n"
        "2026-09-30\nPlease call me\nSent from my iPhone"
    )
    record = await extract_ticket(ticket, "test", MockProvider(0))
    assert record.values["company"] == "Example Credit Labs"
    assert record.field_meta["company"].evidence == "Example Credit Labs"
    assert record.field_meta["company"].grounding == "grounded"
    assert record.values["category"] == "how_to"
    assert record.values["severity"] is None
    assert record.values["requested_action"] == "none"
    assert record.values["escalated"] is False
    assert record.values["deadline"] is None


async def test_footer_money_dates_actions_and_escalation_do_not_leak_into_proposal():
    ticket = invented(
        "Please refund the duplicate $42 charge for Zen Studio.\n\n"
        "This email is confidential.\n"
        "Invoice credit EUR 9000. URGENT: call me and escalate to the CFO by 2026-09-30."
    )
    proposal = json.loads(await MockProvider(0).extract(ticket))
    values = proposal["record"]
    assert values["category"] == "billing"
    assert values["requested_action"] == "refund"
    assert values["refund_amount"] == 42
    assert values["severity"] is None
    assert values["deadline"] is None
    assert values["escalated"] is False
    assert not any("EUR" in note for note in proposal["notes"])


async def test_error_keyword_in_a_settings_question_is_not_an_issue_phrase():
    ticket = invented("How do I configure error notifications in Zen Studio?")
    proposal = json.loads(await MockProvider(0).extract(ticket))
    assert proposal["record"]["category"] == "how_to"
