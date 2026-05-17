from __future__ import annotations

import csv
from pathlib import Path

from research_integrity.models import IngestResult, Quote
from research_integrity.store import Store, stable_id


def ingest(store: Store, fixtures: Path) -> IngestResult:
    respondents = _read_csv(fixtures / "respondents.csv")
    for row in respondents:
        store.upsert_respondent(row)

    quotes = _read_csv(fixtures / "transcripts" / "interviews.csv")
    for row in quotes:
        respondent = next(item for item in respondents if item["respondent_id"] == row["respondent_id"])
        store.upsert_quote(
            Quote(
                quote_id=stable_id(
                    "quote", row["respondent_id"], row["timestamp"], row["question_id"], row["text"]
                ),
                respondent_id=row["respondent_id"],
                segment=respondent["segment"],
                timestamp=row["timestamp"],
                question_id=row["question_id"],
                text=row["text"],
                source_file="fixtures/transcripts/interviews.csv",
            )
        )

    survey_rows = _read_csv(fixtures / "survey_responses.csv")
    for row in survey_rows:
        store.upsert_survey(row)

    screen_events = _read_csv(fixtures / "screen_events" / "events.csv")
    for row in screen_events:
        store.upsert_screen_event(row)

    return IngestResult(
        respondents=len(respondents),
        quotes=len(quotes),
        survey_rows=len(survey_rows),
        screen_events=len(screen_events),
    )


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

