from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from research_integrity.models import Quote


def stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("||".join(str(part) for part in parts).encode()).hexdigest()[:12]
    return f"{prefix}-{digest}"


class Store:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.state_dir = root / ".research-integrity"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.state_dir / "state.sqlite3"
        self._init()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def reset(self) -> None:
        for suffix in ("", "-wal", "-shm"):
            path = Path(str(self.db_path) + suffix)
            if path.exists():
                path.unlink()
        self._init()

    def _init(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS respondents (
                    respondent_id TEXT PRIMARY KEY,
                    segment TEXT NOT NULL,
                    role TEXT NOT NULL,
                    participant_ref TEXT NOT NULL,
                    duration_seconds INTEGER NOT NULL,
                    duplicate_group TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS quotes (
                    quote_id TEXT PRIMARY KEY,
                    respondent_id TEXT NOT NULL,
                    segment TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    question_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    source_file TEXT NOT NULL
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS quotes_fts
                USING fts5(quote_id, respondent_id, segment, question_id, text);
                CREATE TABLE IF NOT EXISTS survey_rows (
                    respondent_id TEXT PRIMARY KEY,
                    visual_score INTEGER NOT NULL,
                    setup_difficulty INTEGER NOT NULL,
                    trust_tracking INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS screen_events (
                    event_id TEXT PRIMARY KEY,
                    respondent_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    detail TEXT NOT NULL
                );
                """
            )

    def upsert_respondent(self, row: dict[str, str]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO respondents
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    row["respondent_id"],
                    row["segment"],
                    row["role"],
                    row["participant_ref"],
                    int(row["duration_seconds"]),
                    row["duplicate_group"],
                ),
            )

    def upsert_quote(self, quote: Quote) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO quotes VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    quote.quote_id,
                    quote.respondent_id,
                    quote.segment,
                    quote.timestamp,
                    quote.question_id,
                    quote.text,
                    quote.source_file,
                ),
            )
            conn.execute(
                "INSERT INTO quotes_fts VALUES (?, ?, ?, ?, ?)",
                (quote.quote_id, quote.respondent_id, quote.segment, quote.question_id, quote.text),
            )

    def upsert_survey(self, row: dict[str, str]) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO survey_rows VALUES (?, ?, ?, ?)",
                (
                    row["respondent_id"],
                    int(row["visual_score"]),
                    int(row["setup_difficulty"]),
                    int(row["trust_tracking"]),
                ),
            )

    def upsert_screen_event(self, row: dict[str, str]) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO screen_events VALUES (?, ?, ?, ?, ?)",
                (
                    stable_id("event", row["respondent_id"], row["timestamp"], row["detail"]),
                    row["respondent_id"],
                    row["timestamp"],
                    row["event_type"],
                    row["detail"],
                ),
            )

    def respondents(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(conn.execute("SELECT * FROM respondents ORDER BY respondent_id"))

    def quotes(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(conn.execute("SELECT * FROM quotes ORDER BY respondent_id, timestamp"))

    def survey_rows(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(conn.execute("SELECT * FROM survey_rows ORDER BY respondent_id"))
