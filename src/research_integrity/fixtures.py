from __future__ import annotations

import csv
from pathlib import Path

from research_integrity.store import Store


def init_demo(root: Path) -> Path:
    Store(root).reset()
    fixtures = root / "fixtures"
    transcripts = fixtures / "transcripts"
    screens = fixtures / "screen_events"
    transcripts.mkdir(parents=True, exist_ok=True)
    screens.mkdir(parents=True, exist_ok=True)
    (fixtures / "study.yaml").write_text(
        "product: AI operations dashboard\nmethod: moderated synthetic interview demo\n",
        encoding="utf-8",
    )
    (fixtures / "discussion_guide.md").write_text(
        "# Discussion Guide\n\n1. Visual analytics\n2. Tracking trust\n3. Setup complexity\n4. CLI automation\n5. Reply detection\n",
        encoding="utf-8",
    )
    respondent_rows = []
    segments = ["operator", "marketer", "sales_ops", "engineer"]
    for idx in range(1, 25):
        segment = segments[(idx - 1) % len(segments)]
        respondent_rows.append(
            {
                "respondent_id": f"R{idx:02d}",
                "segment": segment,
                "role": segment.replace("_", " ").title(),
                "participant_ref": f"participant-{idx:02d}",
                "duration_seconds": "120" if idx == 22 else str(560 + idx * 8),
                "duplicate_group": "dup-a" if idx in (21, 23) else f"unique-{idx:02d}",
            }
        )
    _write_csv(fixtures / "respondents.csv", respondent_rows)

    transcript_rows = []
    for row in respondent_rows:
        rid = row["respondent_id"]
        segment = row["segment"]
        transcript_rows.extend(_quotes_for(rid, segment))
    _write_csv(transcripts / "interviews.csv", transcript_rows)

    survey_rows = []
    for row in respondent_rows:
        rid_num = int(row["respondent_id"][1:])
        survey_rows.append(
            {
                "respondent_id": row["respondent_id"],
                "visual_score": str(5 if rid_num % 3 else 4),
                "setup_difficulty": str(5 if rid_num in (2, 6, 10, 14, 18, 22) else 3),
                "trust_tracking": str(2 if rid_num % 4 else 4),
            }
        )
    _write_csv(fixtures / "survey_responses.csv", survey_rows)

    event_rows = [
        {
            "respondent_id": row["respondent_id"],
            "timestamp": "00:03:10",
            "event_type": "navigation",
            "detail": "opened analytics chart panel",
        }
        for row in respondent_rows
    ]
    _write_csv(screens / "events.csv", event_rows)
    return fixtures


def _quotes_for(respondent_id: str, segment: str) -> list[dict[str, str]]:
    idx = int(respondent_id[1:])
    if idx == 24:
        return [
            {
                "respondent_id": respondent_id,
                "timestamp": "00:00:30",
                "question_id": "off_topic",
                "text": "I mostly want to talk about lunch and keyboard switches, not outreach analytics.",
            }
        ]
    copied = "The charts make the reporting health obvious and I would show them to my team every Monday."
    visual = copied if idx in (21, 23) else "The visual dashboard helps me understand opens, replies, failures, and reporting health faster than a table."
    tracking = (
        "I distrust open tracking unless the sender explains what is tracked and why."
        if idx % 4
        else "Open tracking is fine for my team and I do not need extra explanation."
    )
    setup = (
        "Local connector configuration feels like the biggest adoption blocker."
        if idx in (2, 6, 10, 14, 18, 22)
        else "Setup seems manageable if the checklist is clear."
    )
    cli = (
        "As an operator, I want a CLI so local automation can launch reports and inspect updates without opening a browser."
        if segment == "operator"
        else "The browser dashboard is useful for teammates who do not live in the terminal."
    )
    replies = (
        "I am confused about reply detection because I expected it to update instantly, not from a polling worker."
        if idx in (3, 7, 11, 15, 19)
        else "Reply detection makes sense once the polling worker and source-system metadata are explained."
    )
    return [
        {"respondent_id": respondent_id, "timestamp": "00:01:00", "question_id": "visual", "text": visual},
        {"respondent_id": respondent_id, "timestamp": "00:02:00", "question_id": "tracking", "text": tracking},
        {"respondent_id": respondent_id, "timestamp": "00:03:00", "question_id": "setup", "text": setup},
        {"respondent_id": respondent_id, "timestamp": "00:04:00", "question_id": "cli", "text": cli},
        {"respondent_id": respondent_id, "timestamp": "00:05:00", "question_id": "replies", "text": replies},
    ]


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
