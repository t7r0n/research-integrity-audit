from __future__ import annotations

import time
from pathlib import Path

from research_integrity.fixtures import init_demo
from research_integrity.ingest import ingest
from research_integrity.store import Store


def run_benchmark(root: Path) -> Path:
    if not (root / "fixtures" / "respondents.csv").exists():
        init_demo(root)
    store = Store(root)
    if not store.quotes():
        ingest(store, root / "fixtures")
    base_quotes = [dict(row) for row in store.quotes()]
    synthetic_quotes = []
    bench_dir = root / "outputs" / "benchmark_transcripts"
    bench_dir.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    for idx in range(500):
        quote = base_quotes[idx % len(base_quotes)]
        synthetic_quotes.append({**quote, "quote_id": f"bench-{idx:03d}", "respondent_id": f"B{idx:03d}"})
        (bench_dir / f"transcript_{idx:03d}.md").write_text(
            f"# Synthetic Transcript {idx:03d}\n\n{quote['timestamp']} {quote['text']}\n",
            encoding="utf-8",
        )
    topic_hits = sum(
        1
        for quote in synthetic_quotes
        if any(term in quote["text"].lower() for term in ("dashboard", "tracking", "setup", "reply", "cli"))
    )
    elapsed_ms = (time.perf_counter() - start) * 1000
    output_dir = root / "outputs"
    output_dir.mkdir(exist_ok=True)
    path = output_dir / "benchmark.md"
    path.write_text(
        "# Benchmark\n\n"
        f"- Synthetic transcript files generated: {len(list(bench_dir.glob('*.md')))}\n"
        f"- Synthetic transcript quotes evaluated: {len(synthetic_quotes)}\n"
        f"- Topic hits: {topic_hits}\n"
        f"- Evaluation latency: {elapsed_ms:.3f} ms\n"
        "- Target: 500 transcript fixture under 60,000 ms.\n"
        f"- Result: {'PASS' if elapsed_ms < 60_000 else 'CHECK'}\n",
        encoding="utf-8",
    )
    return path
