import csv
from pathlib import Path

from typer.testing import CliRunner

from research_integrity.analysis import analyze
from research_integrity.benchmark import run_benchmark
from research_integrity.cli import app
from research_integrity.fixtures import init_demo
from research_integrity.ingest import ingest
from research_integrity.store import Store
from research_integrity.verify import verify


def test_full_research_integrity_pipeline(tmp_path: Path) -> None:
    runner = CliRunner()
    assert runner.invoke(app, ["init-demo", "--root", str(tmp_path)]).exit_code == 0

    ingest_result = runner.invoke(app, ["ingest", str(tmp_path / "fixtures"), "--root", str(tmp_path)])
    assert ingest_result.exit_code == 0
    assert "24 respondents" in ingest_result.output

    analyze_result = runner.invoke(app, ["analyze", "--root", str(tmp_path)])
    assert analyze_result.exit_code == 0

    verify_result = runner.invoke(app, ["verify", "--root", str(tmp_path)])
    assert verify_result.exit_code == 0
    assert "Verification passed" in verify_result.output

    assert (tmp_path / "outputs" / "insight_audit.html").exists()
    assert (tmp_path / "outputs" / "claims.csv").exists()
    assert (tmp_path / "outputs" / "quality_report.csv").exists()
    assert (tmp_path / "outputs" / "cluster_report.csv").exists()
    assert (tmp_path / "outputs" / "summary_packet.md").exists()
    assert (tmp_path / "outputs" / "segment_comparison.svg").exists()
    assert (tmp_path / "outputs" / "architecture_diagram.mmd").exists()
    assert (tmp_path / "outputs" / "test_results.md").exists()
    dashboard = (tmp_path / "outputs" / "insight_audit.html").read_text(encoding="utf-8")
    assert "toggle-quality" in dashboard


def test_quality_flags_planted_low_quality_respondents(tmp_path: Path) -> None:
    init_demo(tmp_path)
    store = Store(tmp_path)
    ingest(store, tmp_path / "fixtures")
    analyze(store, tmp_path / "outputs")

    quality = _read_csv(tmp_path / "outputs" / "quality_report.csv")
    low_quality_ids = {row["respondent_id"] for row in quality if row["quality_band"] == "low"}
    assert {"R22", "R24"}.issubset(low_quality_ids)


def test_claims_have_support_and_counterevidence(tmp_path: Path) -> None:
    init_demo(tmp_path)
    store = Store(tmp_path)
    ingest(store, tmp_path / "fixtures")
    analyze(store, tmp_path / "outputs")

    claims = {row["claim_id"]: row for row in _read_csv(tmp_path / "outputs" / "claims.csv")}
    assert claims["visual_analytics"]["verdict"] == "supported"
    assert int(claims["tracking_trust"]["contradiction_count"]) > 0
    assert int(claims["operators_cli"]["support_count"]) >= 4


def test_verify_rejects_unsupported_claim(tmp_path: Path) -> None:
    init_demo(tmp_path)
    store = Store(tmp_path)
    ingest(store, tmp_path / "fixtures")
    analyze(store, tmp_path / "outputs")

    claims_path = tmp_path / "outputs" / "claims.csv"
    rows = _read_csv(claims_path)
    rows[0]["verdict"] = "unsupported"
    with claims_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    result = verify(tmp_path / "outputs")
    assert not result.ok
    assert any("Unsupported claim present" in message for message in result.messages)


def test_cluster_packet_and_benchmark_outputs(tmp_path: Path) -> None:
    init_demo(tmp_path)
    store = Store(tmp_path)
    ingest(store, tmp_path / "fixtures")
    analyze(store, tmp_path / "outputs")
    clusters = _read_csv(tmp_path / "outputs" / "cluster_report.csv")
    assert clusters
    packet = (tmp_path / "outputs" / "summary_packet.md").read_text(encoding="utf-8")
    assert "UNSUPPORTED-DRAFT" in packet
    benchmark = run_benchmark(tmp_path)
    benchmark_text = benchmark.read_text(encoding="utf-8")
    assert "Synthetic transcript files generated: 500" in benchmark_text
    assert "PASS" in benchmark_text


def test_pydantic_claims_and_summary_validation(tmp_path: Path) -> None:
    runner = CliRunner()
    assert runner.invoke(app, ["init-demo", "--root", str(tmp_path)]).exit_code == 0
    assert runner.invoke(app, ["ingest", str(tmp_path / "fixtures"), "--root", str(tmp_path)]).exit_code == 0
    assert runner.invoke(app, ["analyze", "--root", str(tmp_path)]).exit_code == 0
    draft = tmp_path / "outputs" / "draft_summary.md"
    draft.write_text(
        "visual_analytics shows respondents value visual reporting. tracking_trust has audited evidence.",
        encoding="utf-8",
    )
    ok = runner.invoke(app, ["validate-summary", str(draft), "--root", str(tmp_path)])
    assert ok.exit_code == 0
    bad = tmp_path / "outputs" / "bad_summary.md"
    bad.write_text("This sentence cites nothing.", encoding="utf-8")
    rejected = runner.invoke(app, ["validate-summary", str(bad), "--root", str(tmp_path)])
    assert rejected.exit_code == 1


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
