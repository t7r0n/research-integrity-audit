from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VerificationReport:
    ok: bool
    messages: list[str]


def verify(output_dir: Path) -> VerificationReport:
    required = [
        output_dir / "quality_report.csv",
        output_dir / "claims.csv",
        output_dir / "cluster_report.csv",
        output_dir / "summary_packet.md",
        output_dir / "segment_comparison.svg",
        output_dir / "architecture_diagram.mmd",
        output_dir / "test_results.md",
        output_dir / "executive_summary.md",
        output_dir / "evidence_graph.mmd",
        output_dir / "insight_audit.html",
    ]
    messages: list[str] = []
    ok = True
    for path in required:
        if not path.exists():
            ok = False
            messages.append(f"Missing output: {path}")
    if not ok:
        return VerificationReport(False, messages)

    claims = _read_csv(output_dir / "claims.csv")
    for claim in claims:
        support = int(claim["support_count"])
        high_quality_support = int(claim["high_quality_support_count"])
        verdict = claim["verdict"]
        if verdict == "supported" and high_quality_support < 4:
            ok = False
            messages.append(f"Supported claim lacks enough high-quality evidence: {claim['claim_id']}")
        if verdict == "unsupported":
            ok = False
            messages.append(f"Unsupported claim present: {claim['claim_id']}")
        if support <= 0:
            ok = False
            messages.append(f"Claim has no source quote evidence: {claim['claim_id']}")
        if not claim["supporting_quote_ids"]:
            ok = False
            messages.append(f"Claim has no quote IDs: {claim['claim_id']}")

    quality = _read_csv(output_dir / "quality_report.csv")
    if not any(row["quality_band"] == "low" for row in quality):
        ok = False
        messages.append("Expected at least one low-quality respondent to be flagged.")
    if ok:
        messages.append(
            f"Verification passed: {len(claims)} claims audited, "
            f"{len(quality)} respondents scored, unsupported claims rejected."
        )
    return VerificationReport(ok, messages)


def validate_summary(output_dir: Path, summary_path: Path) -> VerificationReport:
    if not summary_path.exists():
        return VerificationReport(False, [f"Missing summary: {summary_path}"])
    claims = {row["claim_id"]: row for row in _read_csv(output_dir / "claims.csv")}
    text = summary_path.read_text(encoding="utf-8")
    messages: list[str] = []
    ok = True
    for sentence in [part.strip() for part in text.replace("\n", " ").split(".") if part.strip()]:
        if "UNSUPPORTED-DRAFT" in sentence:
            ok = False
            messages.append("Unsupported draft marker present.")
            continue
        if not any(claim_id in sentence for claim_id in claims):
            ok = False
            messages.append(f"Sentence lacks claim citation: {sentence}")
    if ok:
        messages.append("Summary validation passed: every sentence cites an audited claim.")
    return VerificationReport(ok, messages)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
