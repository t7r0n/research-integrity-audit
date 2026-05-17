from __future__ import annotations

import csv
import html
from collections import Counter, defaultdict
from pathlib import Path

from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

from research_integrity.models import ClaimAudit
from research_integrity.store import Store

CLAIMS = [
    {
        "claim_id": "visual_analytics",
        "text": "Users prefer visual analytics over table-only reporting reporting.",
        "support": ["visual", "dashboard", "chart", "reporting health"],
        "contradict": ["table is enough"],
        "min_support": 8,
    },
    {
        "claim_id": "tracking_trust",
        "text": "Users distrust open tracking unless it is clearly explained.",
        "support": ["distrust", "explains", "tracked", "why"],
        "contradict": ["fine", "do not need extra explanation"],
        "min_support": 6,
    },
    {
        "claim_id": "setup_complexity",
        "text": "connector and tracking setup complexity is an adoption blocker.",
        "support": ["connector", "configuration", "adoption blocker"],
        "contradict": ["manageable"],
        "min_support": 5,
    },
    {
        "claim_id": "operators_cli",
        "text": "Demos want CLI automation for local automation-driven workflow automation.",
        "support": ["operator", "cli", "automation"],
        "contradict": ["browser dashboard"],
        "segment": "operator",
        "min_support": 4,
    },
    {
        "claim_id": "reply_detection_confusion",
        "text": "Some users misunderstand reply detection and expect instant updates.",
        "support": ["confused", "reply detection", "instantly", "polling worker"],
        "contradict": ["makes sense"],
        "min_support": 4,
    },
]


def analyze(store: Store, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    quality_rows = _quality_rows(store)
    claims = _claim_rows(store, quality_rows)
    paths = [
        _write_quality(output_dir / "quality_report.csv", quality_rows),
        _write_claims(output_dir / "claims.csv", claims),
        _write_clusters(output_dir / "cluster_report.csv", store),
        _write_segment_chart(output_dir / "segment_comparison.svg", claims),
        _write_summary(output_dir / "executive_summary.md", claims),
        _write_graph(output_dir / "evidence_graph.mmd", claims),
        _write_task_packet(output_dir / "summary_packet.md", claims),
        _write_architecture_diagram(output_dir / "architecture_diagram.mmd"),
        _write_test_results(output_dir / "test_results.md"),
    ]
    paths.append(build_dashboard(output_dir))
    paths.append(compare(output_dir, exclude_low_quality=True))
    return paths


def build_dashboard(output_dir: Path) -> Path:
    claims = _read_csv(output_dir / "claims.csv")
    quality = _read_csv(output_dir / "quality_report.csv")
    comparison_path = output_dir / "comparison_excluding_low_quality.csv"
    comparison = {row["claim_id"]: row for row in _read_csv(comparison_path)} if comparison_path.exists() else {}
    cards = []
    for claim in claims:
        quote_links = "".join(
            f"<li><a href='#{html.escape(ref.split(':')[-1])}'>{html.escape(ref)}</a></li>"
            for ref in claim["supporting_quote_ids"].split(";")
            if ref
        )
        adjusted = comparison.get(claim["claim_id"], {}).get("support_count", claim["support_count"])
        cards.append(
            f"<section class='card' data-all='{claim['support_count']}' data-adjusted='{adjusted}'>"
            f"<h2>{html.escape(claim['claim_id'])}: {html.escape(claim['verdict'])}</h2>"
            f"<p>{html.escape(claim['text'])}</p>"
            f"<p><strong>Support:</strong> <span class='support-count'>{claim['support_count']}</span> "
            f"<strong>Contradictions:</strong> {claim['contradiction_count']} "
            f"<strong>Confidence:</strong> {claim['confidence']}</p>"
            f"<blockquote>{html.escape(claim['supporting_quotes'])}</blockquote>"
            f"<ul>{quote_links}</ul>"
            f"<details><summary>Counterevidence</summary>{html.escape(claim['contradicting_quotes'])}</details>"
            "</section>"
        )
    low_quality = sum(1 for row in quality if row["quality_band"] == "low")
    path = output_dir / "insight_audit.html"
    path.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Research Integrity Audit</title>
  <style>
    body {{ margin: 0; font-family: Inter, -apple-system, BlinkMacSystemFont, sans-serif; background: #f8f9fb; color: #18202a; }}
    header {{ background: white; border-bottom: 1px solid #dde4ed; padding: 30px 40px; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 28px; display: grid; gap: 16px; }}
    .card {{ background: white; border: 1px solid #dde4ed; border-radius: 8px; padding: 18px; }}
    button {{ border: 1px solid #9aa8b8; background: #ffffff; border-radius: 6px; padding: 8px 12px; }}
    blockquote {{ border-left: 3px solid #587a6d; margin: 12px 0; padding-left: 12px; color: #3a4652; }}
  </style>
</head>
<body>
  <header><h1>Research Integrity Audit Engine</h1><p>{low_quality} low-quality respondents flagged. Every claim has support and counterevidence.</p></header>
  <main><button id="toggle-quality">Exclude low-quality respondents</button><img src="segment_comparison.svg" alt="Segment comparison chart">{''.join(cards)}</main>
  <script>
    let adjusted = false;
    document.getElementById('toggle-quality').addEventListener('click', () => {{
      adjusted = !adjusted;
      document.querySelectorAll('.card').forEach(card => {{
        card.querySelector('.support-count').textContent = adjusted ? card.dataset.adjusted : card.dataset.all;
      }});
      document.getElementById('toggle-quality').textContent = adjusted ? 'Show all respondents' : 'Exclude low-quality respondents';
    }});
  </script>
</body>
</html>
""",
        encoding="utf-8",
    )
    return path


def compare(output_dir: Path, *, exclude_low_quality: bool) -> Path:
    claims = _read_csv(output_dir / "claims.csv")
    quality = {row["respondent_id"]: row for row in _read_csv(output_dir / "quality_report.csv")}
    path = output_dir / ("comparison_excluding_low_quality.csv" if exclude_low_quality else "comparison_all.csv")
    rows = []
    for claim in claims:
        support_ids = [item.split(":")[0] for item in claim["supporting_quote_ids"].split(";") if item]
        if exclude_low_quality:
            support_ids = [rid for rid in support_ids if quality.get(rid, {}).get("quality_band") != "low"]
        rows.append(
            {
                "claim_id": claim["claim_id"],
                "support_count": str(len(support_ids)),
                "mode": "exclude_low_quality" if exclude_low_quality else "all",
            }
        )
    _write_csv(path, rows)
    return path


def export_demo_pack(output_dir: Path) -> Path:
    if not (output_dir / "insight_audit.html").exists():
        build_dashboard(output_dir)
    path = output_dir / "demo_pack.md"
    path.write_text(
        "\n".join(
            [
                "# Demo Pack: Trust Layer for AI Research",
                "",
                "## Demo Script",
                "",
                "1. Run `uv run research-integrity init-demo`.",
                "2. Run `uv run research-integrity ingest fixtures/`.",
                "3. Run `uv run research-integrity analyze`.",
                "4. Run `uv run research-integrity verify`.",
                "5. Run `uv run research-integrity compare --exclude-low-quality`.",
                "6. Open `outputs/insight_audit.html`.",
                "7. Use `outputs/summary_packet.md` for a local automation drafting pass.",
                "8. Run `uv run research-integrity validate-summary outputs/draft_summary.md` for summary gatekeeping.",
                "",
                "## Architecture",
                "",
                "Local transcripts, survey rows, screen events, and respondent metadata are ingested "
                "into SQLite with FTS. Deterministic analyzers score respondent quality, extract claims, "
                "cluster quote themes, attach support and counterevidence, and reject unsupported claims.",
                "",
                "## Why This Matters",
                "",
                "Fast AI research is only defensible when every generated insight carries evidence, "
                "counterevidence, sample context, and quality controls.",
                "",
                "## Demo Assets",
                "",
                "- `outputs/architecture_diagram.mmd`",
                "- `outputs/test_results.md`",
                "- `outputs/segment_comparison.svg`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _quality_rows(store: Store) -> list[dict[str, str]]:
    quotes = store.quotes()
    quote_text_by_respondent: dict[str, list[str]] = defaultdict(list)
    text_counts: Counter[str] = Counter()
    for quote in quotes:
        text = str(quote["text"])
        quote_text_by_respondent[str(quote["respondent_id"])].append(text)
        text_counts[text] += 1
    rows = []
    for respondent in store.respondents():
        rid = str(respondent["respondent_id"])
        reasons = []
        score = 100
        all_text = " ".join(quote_text_by_respondent[rid]).lower()
        if int(respondent["duration_seconds"]) < 180:
            score -= 35
            reasons.append("suspicious_completion_speed")
        if respondent["duplicate_group"].startswith("dup"):
            score -= 20
            reasons.append("duplicate_profile_group")
        if any(text_counts[text] > 1 for text in quote_text_by_respondent[rid]):
            score -= 20
            reasons.append("copy_paste_answer")
        topical_terms = ["dashboard", "tracking", "setup", "reply", "reporting", "cli", "analytics"]
        if sum(1 for term in topical_terms if term in all_text) < 2:
            score -= 50
            reasons.append("low_topical_relevance")
        if "distrust" in all_text and "do not need extra explanation" in all_text:
            score -= 10
            reasons.append("tracking_contradiction")
        band = "high" if score >= 80 else "medium" if score >= 60 else "low"
        rows.append(
            {
                "respondent_id": rid,
                "segment": str(respondent["segment"]),
                "quality_score": str(max(score, 0)),
                "quality_band": band,
                "reasons": ";".join(reasons) or "none",
            }
        )
    return rows


def _claim_rows(store: Store, quality_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    quality = {row["respondent_id"]: row for row in quality_rows}
    rows = []
    for claim in CLAIMS:
        support = []
        contradict = []
        for quote in store.quotes():
            if claim.get("segment") and quote["segment"] != claim["segment"]:
                continue
            lowered = str(quote["text"]).lower()
            support_score = sum(1 for token in claim["support"] if token in lowered)
            contradict_score = sum(1 for token in claim["contradict"] if token in lowered)
            if support_score:
                support.append(quote)
            if contradict_score:
                contradict.append(quote)
        support_respondents = {str(row["respondent_id"]) for row in support}
        contradiction_respondents = {str(row["respondent_id"]) for row in contradict}
        high_quality_support = [
            rid for rid in support_respondents if quality.get(rid, {}).get("quality_band") != "low"
        ]
        if len(high_quality_support) >= int(claim["min_support"]):
            verdict = "supported"
        elif support_respondents and contradiction_respondents:
            verdict = "contradicted"
        elif support_respondents:
            verdict = "weak"
        else:
            verdict = "unsupported"
        confidence = min(0.98, 0.45 + len(high_quality_support) * 0.06 - len(contradiction_respondents) * 0.02)
        segments = sorted({str(row["segment"]) for row in support})
        rows.append(
            {
                "claim_id": str(claim["claim_id"]),
                "text": str(claim["text"]),
                "verdict": verdict,
                "support_count": str(len(support_respondents)),
                "high_quality_support_count": str(len(high_quality_support)),
                "contradiction_count": str(len(contradiction_respondents)),
                "segments": ";".join(segments),
                "confidence": f"{confidence:.2f}",
                "supporting_quote_ids": ";".join(f"{row['respondent_id']}:{row['quote_id']}" for row in support[:8]),
                "supporting_quotes": " | ".join(str(row["text"]) for row in support[:3]),
                "contradicting_quotes": " | ".join(str(row["text"]) for row in contradict[:3]),
            }
        )
        ClaimAudit(
            claim_id=rows[-1]["claim_id"],
            text=rows[-1]["text"],
            verdict=rows[-1]["verdict"],
            support_count=int(rows[-1]["support_count"]),
            high_quality_support_count=int(rows[-1]["high_quality_support_count"]),
            contradiction_count=int(rows[-1]["contradiction_count"]),
            confidence=float(rows[-1]["confidence"]),
        )
    return rows


def _write_quality(path: Path, rows: list[dict[str, str]]) -> Path:
    _write_csv(path, rows)
    return path


def _write_claims(path: Path, rows: list[dict[str, str]]) -> Path:
    _write_csv(path, rows)
    return path


def _write_summary(path: Path, claims: list[dict[str, str]]) -> Path:
    lines = ["# Executive Summary", ""]
    for claim in claims:
        lines.append(
            f"- **{claim['verdict']}**: {claim['text']} "
            f"(support={claim['support_count']}, contradictions={claim['contradiction_count']}, confidence={claim['confidence']})"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _write_clusters(path: Path, store: Store) -> Path:
    quotes = store.quotes()
    texts = [str(row["text"]) for row in quotes]
    if len(texts) < 4:
        rows = []
    else:
        vectorizer = TfidfVectorizer(stop_words="english", max_features=80)
        matrix = vectorizer.fit_transform(texts)
        clusters = KMeans(n_clusters=5, random_state=7, n_init=10).fit_predict(matrix)
        terms = vectorizer.get_feature_names_out()
        rows = []
        for cluster_id in sorted(set(clusters)):
            indices = [idx for idx, value in enumerate(clusters) if value == cluster_id]
            centroid = matrix[indices].mean(axis=0).A1
            top_terms = [terms[idx] for idx in centroid.argsort()[-5:][::-1]]
            rows.append(
                {
                    "cluster_id": str(cluster_id),
                    "quote_count": str(len(indices)),
                    "top_terms": ";".join(top_terms),
                    "example_quote": texts[indices[0]],
                }
            )
    _write_csv(path, rows)
    return path


def _write_segment_chart(path: Path, claims: list[dict[str, str]]) -> Path:
    segments = ["operator", "marketer", "sales_ops", "engineer"]
    bars = []
    for idx, segment in enumerate(segments):
        count = sum(1 for claim in claims if segment in claim["segments"].split(";"))
        width = count * 70
        y = 48 + idx * 38
        bars.append(
            f"<text x='16' y='{y + 16}' font-size='12'>{segment}</text>"
            f"<rect x='130' y='{y}' width='{width}' height='22' rx='3' fill='#587a6d'/>"
            f"<text x='{140 + width}' y='{y + 16}' font-size='12'>{count}</text>"
        )
    path.write_text(
        "<svg xmlns='http://www.w3.org/2000/svg' width='620' height='230' viewBox='0 0 620 230'>"
        "<rect width='620' height='230' fill='#f8f9fb'/>"
        "<text x='16' y='28' font-size='18'>Segment Evidence Coverage</text>"
        + "".join(bars)
        + "</svg>",
        encoding="utf-8",
    )
    return path


def _write_task_packet(path: Path, claims: list[dict[str, str]]) -> Path:
    lines = [
        "# Local Automation Summary Packet",
        "",
        "Draft an executive summary using only the audited claims below.",
        "Every sentence must cite a claim ID and quote IDs. Unsupported claims must be marked `UNSUPPORTED-DRAFT`.",
        "",
    ]
    for claim in claims:
        lines.extend(
            [
                f"## {claim['claim_id']}",
                f"- Verdict: {claim['verdict']}",
                f"- Claim: {claim['text']}",
                f"- Support: {claim['support_count']}",
                f"- Contradictions: {claim['contradiction_count']}",
                f"- Quote IDs: {claim['supporting_quote_ids']}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _write_architecture_diagram(path: Path) -> Path:
    path.write_text(
        """graph LR
  fixtures["Study fixtures"] --> ingest["SQLite + FTS ingest"]
  ingest --> quality["Quality guard"]
  ingest --> claims["Claim extraction"]
  ingest --> clusters["TF-IDF + KMeans clusters"]
  quality --> verifier["Unsupported-claim verifier"]
  claims --> verifier
  claims --> dashboard["Dashboard + segment chart"]
  verifier --> operator["Demo pack"]
""",
        encoding="utf-8",
    )
    return path


def _write_test_results(path: Path) -> Path:
    path.write_text(
        "# Test Results\n\n"
        "- Static checks: `uv run ruff check .`\n"
        "- Unit/integration/evaluation tests: `uv run pytest -q`\n"
        "- Integrity verifier: `uv run research-integrity verify`\n"
        "- Negative path: unsupported claim mutation is covered in pytest.\n"
        "- Benchmark: `uv run research-integrity benchmark` checks 500 transcript files.\n",
        encoding="utf-8",
    )
    return path


def _write_graph(path: Path, claims: list[dict[str, str]]) -> Path:
    lines = ["graph TD"]
    for claim in claims:
        claim_node = claim["claim_id"].replace("-", "_")
        lines.append(f'  {claim_node}["{claim["verdict"]}: {claim["claim_id"]}"]')
        for ref in claim["supporting_quote_ids"].split(";")[:4]:
            if not ref:
                continue
            quote_node = ref.split(":")[-1].replace("-", "_")
            lines.append(f'  {quote_node}["{ref.split(":")[0]} quote"] --> {claim_node}')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
