"""Keep automated tests independent of local secrets and provider configuration."""

import pytest

from app.config import Settings


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch):
    # Tests supply their own settings and fake transports. A developer's Gemini key
    # must never silently turn an offline test into a request to the real API.
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)
