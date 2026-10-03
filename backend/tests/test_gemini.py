import json

import httpx
import pytest
from pydantic import SecretStr

from app.config import Settings
from app.extraction import extract_ticket
from app.providers.gemini import GeminiProvider
from app.tickets import load_tickets


async def test_real_adapter_uses_shared_validation_retry_and_keeps_key_out_of_url():
    requests = []

    def reply(request):
        requests.append(request)
        assert "example-key" not in str(request.url)
        assert request.headers["x-goog-api-key"] == "example-key"
        payload = json.loads(request.content)
        assert payload["generationConfig"]["responseMimeType"] == "application/json"
        record = {
            "company": "Acme",
            "product": "Zen Studio",
            "category": "outage",
            "severity": "urgent" if len(requests) == 1 else "critical",
            "requested_action": "fix",
            "escalated": False,
        }
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"parts": [{"text": json.dumps({"record": record})}]}}],
            },
        )

    settings = Settings(gemini_api_key=SecretStr("example-key"))
    ticket = load_tickets(settings.dataset_path())["tkt_0005"]
    async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
        provider = GeminiProvider(settings, client)
        result = await extract_ticket(ticket, "job", provider)
    assert result.schema_valid
    assert result.attempts == 2
    second = json.loads(requests[1].content)
    feedback = json.loads(second["contents"][0]["parts"][0]["text"])["validation_feedback"]
    assert "severity" in feedback


def test_real_provider_requires_a_key_but_mock_configuration_does_not():
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        GeminiProvider(Settings(gemini_api_key=SecretStr("")))
    assert Settings(gemini_api_key=SecretStr("")).extraction_provider == "mock"


async def test_malformed_json_retries_and_preserves_raw_output():
    class BrokenJsonProvider:
        async def extract(self, ticket, feedback=None):
            return "{broken json"

    ticket = load_tickets(Settings().dataset_path())["tkt_0005"]
    result = await extract_ticket(ticket, "job", BrokenJsonProvider())
    assert result.status == "needs_review"
    assert result.attempts == 2
    assert result.raw_outputs == ["{broken json", "{broken json"]
    assert result.errors[0].field == "record"
