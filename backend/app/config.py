"""Explicit, validated configuration shared by the application and job runner."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    extraction_provider: Literal["mock"] = "mock"
    max_concurrency: int = Field(default=4, ge=1, le=20)
    mock_delay_ms: int = Field(default=650, ge=0, le=10000)
    provider_timeout_seconds: float = Field(default=30, gt=0, le=120)
    tickets_path: Path = ROOT / "data" / "tickets.jsonl"

    def dataset_path(self) -> Path:
        # Relative paths always refer to the repo, regardless of the launch directory.
        return self.tickets_path if self.tickets_path.is_absolute() else ROOT / self.tickets_path
