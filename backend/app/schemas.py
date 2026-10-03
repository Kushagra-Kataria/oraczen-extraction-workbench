"""The business contract and separate models for job/review metadata."""

import json
from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, TypeAdapter, field_validator

Product = Literal[
    "Zen Orchestrator", "Zen Studio", "Zen Connect", "Zen Insights", "Zen Vault"
]
Category = Literal["outage", "billing", "bug", "feature_request", "how_to", "churn_risk"]
Severity = Literal["low", "medium", "high", "critical"]
Action = Literal["refund", "credit", "fix", "callback", "information", "none"]
Company = Annotated[str, Field(strict=True, min_length=1, max_length=200)]
Amount = Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)]


class Ticket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    subject: str
    body: str
    channel: Literal["email", "web_form", "chat", "phone_transcript"]
    received_at: datetime
    from_email: str
    attachments: int = Field(ge=0)


class Extraction(BaseModel):
    # JSON mode permits ISO dates while preventing string-to-number/bool coercion.
    model_config = ConfigDict(extra="forbid", strict=True)

    company: Company
    product: Product
    category: Category
    severity: Severity
    requested_action: Action
    refund_amount: Amount | None = None
    deadline: date | None = None
    escalated: StrictBool

    @field_validator("company")
    @classmethod
    def company_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Company must not be blank")
        return value


FIELDS = tuple(Extraction.model_fields)
OPTIONAL_FIELDS = {"refund_amount", "deadline"}
ADAPTERS = {
    name: TypeAdapter(field.rebuild_annotation(), config=ConfigDict(strict=True))
    for name, field in Extraction.model_fields.items()
}


def validate_field(name: str, value: Any) -> Any:
    """Use the extraction field's actual annotation for partial human corrections."""
    parsed = ADAPTERS[name].validate_json(json.dumps(value))
    if name == "company":
        return Extraction.company_not_blank(parsed)
    return parsed.isoformat() if isinstance(parsed, date) else parsed


class Proposal(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    record: dict[str, Any]
    evidence: dict[str, str | None] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class FieldMeta(BaseModel):
    source: Literal["model", "human", "missing"] = "missing"
    grounding: Literal["grounded", "inferred", "missing"] = "missing"
    evidence: str | None = None


class FieldError(BaseModel):
    field: str
    message: str


class Record(BaseModel):
    id: str
    job_id: str
    ticket_id: str
    values: dict[str, Any] = Field(default_factory=lambda: dict.fromkeys(FIELDS))
    field_meta: dict[str, FieldMeta] = Field(
        default_factory=lambda: {name: FieldMeta() for name in FIELDS}
    )
    status: Literal["done", "needs_review", "failed"] = "needs_review"
    schema_valid: bool = False
    reviewed: bool = False
    attempts: int = 0
    raw_outputs: list[str] = Field(default_factory=list)
    errors: list[FieldError] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    version: int = 1


class JobItem(BaseModel):
    ticket_id: str
    status: Literal["queued", "running", "done", "needs_review", "failed"] = "queued"
    record_id: str | None = None


class Job(BaseModel):
    id: str
    state: Literal["queued", "running", "done", "cancelled"] = "queued"
    created_at: datetime
    items: list[JobItem]

    def snapshot(self) -> dict[str, Any]:
        # Derive counters from items so an independently updated counter cannot drift.
        statuses = [item.status for item in self.items]
        return {
            **self.model_dump(mode="json"),
            "total": len(statuses),
            "queued": statuses.count("queued"),
            "running": statuses.count("running"),
            "done": statuses.count("done") + statuses.count("needs_review"),
            "failed": statuses.count("failed"),
            "needs_review": statuses.count("needs_review"),
        }


class JobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticket_ids: list[str] = Field(min_length=1, max_length=150)


class Correction(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    fields: dict[str, Any] = Field(default_factory=dict)
    reviewed: StrictBool | None = None
    version: int = Field(ge=1)
