from __future__ import annotations

from pydantic import BaseModel, Field


class IngestResult(BaseModel, frozen=True):
    respondents: int = Field(ge=0)
    quotes: int = Field(ge=0)
    survey_rows: int = Field(ge=0)
    screen_events: int = Field(ge=0)


class Quote(BaseModel, frozen=True):
    quote_id: str
    respondent_id: str
    segment: str
    timestamp: str
    question_id: str
    text: str = Field(min_length=1)
    source_file: str


class ClaimAudit(BaseModel, frozen=True):
    claim_id: str
    text: str = Field(min_length=1)
    verdict: str
    support_count: int = Field(ge=0)
    high_quality_support_count: int = Field(ge=0)
    contradiction_count: int = Field(ge=0)
    confidence: float = Field(ge=0, le=1)
