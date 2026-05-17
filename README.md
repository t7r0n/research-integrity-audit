# Research Integrity Audit

A local-first prototype for auditing qualitative research insights with quote-level evidence.

The project creates a deterministic synthetic study, ingests transcripts and survey-style fixtures, scores participant quality, extracts claim support and counterevidence, and produces an evidence dashboard. It is designed to make generated research summaries easier to verify without relying on external APIs.

## Features

- Synthetic respondent, transcript, survey, and screen-event fixtures
- SQLite WAL evidence store with full-text quote search
- Transparent participant quality scoring
- Claim extraction with support counts and contradiction counts
- Segment comparison and low-quality respondent filtering
- Quote clustering for theme discovery
- Unsupported-claim verification
- Static HTML audit dashboard
- 500-transcript local benchmark

## Quick Start

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

The demo writes audited claims, quality reports, graph artifacts, and a static dashboard under `outputs/`.

## Validation

```bash
uv run ruff check .
uv run pytest -q
uv run research-integrity --help
```

## Generated Artifacts

- `fixtures/respondents.csv`
- `fixtures/transcripts/interviews.csv`
- `.research-integrity/state.sqlite3`
- `outputs/quality_report.csv`
- `outputs/claims.csv`
- `outputs/cluster_report.csv`
- `outputs/summary_packet.md`
- `outputs/evidence_graph.mmd`
- `outputs/executive_summary.md`
- `outputs/benchmark.md`
- `outputs/insight_audit.html`
- `outputs/demo_pack.md`

## Local Data Policy

The included demo data is synthetic. Runtime state and generated artifacts are ignored by git so public commits remain limited to source, tests, and reproducible setup files.
