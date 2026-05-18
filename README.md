# Research Integrity Audit

A local-first prototype for auditing qualitative research insights with quote-level evidence.

The project creates a deterministic synthetic study, ingests transcripts and survey-style fixtures, scores participant quality, extracts claim support and counterevidence, and produces an evidence dashboard. It is designed to make generated research summaries easier to verify without relying on external APIs.

## Problem shape

Local research integrity audit engine prototype for evidence-backed insights.

## What the harness exercises

- Synthetic respondent, transcript, survey, and screen-event fixtures
- SQLite WAL evidence store with full-text quote search
- Transparent participant quality scoring
- Claim extraction with support counts and contradiction counts
- Segment comparison and low-quality respondent filtering
- Quote clustering for theme discovery
- Unsupported-claim verification
- Static HTML audit dashboard
- 500-transcript local benchmark

## Local workflow

```bash
uv sync
rm -rf fixtures outputs .research-integrity
uv run research-integrity init-demo
uv run research-integrity ingest fixtures/
uv run research-integrity analyze
uv run research-integrity verify
uv run research-integrity benchmark
uv run research-integrity compare --exclude-low-quality
uv run research-integrity dashboard
uv run research-integrity export-demo-pack
```

## Review surfaces

- `fixtures/respondents.csv`
- `fixtures/transcripts/interviews.csv`
- `.research-integrity/state.sqlite3`
- `outputs/quality_report.csv`
- `outputs/claims.csv`
- `outputs/cluster_report.csv`
- `outputs/summary_packet.md`

## Quality checks

```bash
uv run ruff check .
uv run pytest -q
uv run research-integrity --help
```

## Repository hygiene

The `research-integrity-audit` public surface is source, tests, lockfile, and docs. It does not need credentials, browser state, customer records, or hosted services.
