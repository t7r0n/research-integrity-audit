from pathlib import Path

import typer
from rich.console import Console

from research_integrity.analysis import analyze, build_dashboard, compare, export_demo_pack
from research_integrity.benchmark import run_benchmark
from research_integrity.fixtures import init_demo
from research_integrity.ingest import ingest
from research_integrity.store import Store
from research_integrity.verify import validate_summary, verify

app = typer.Typer(help="Local research integrity audit engine prototype.")
console = Console()


@app.callback()
def main() -> None:
    """Research integrity CLI."""


@app.command("init-demo")
def init_demo_command(root: Path = typer.Option(Path("."), "--root")) -> None:
    """Create deterministic local research fixtures."""
    path = init_demo(root)
    console.print(f"Demo study fixtures ready: [bold]{path}[/bold]")


@app.command("ingest")
def ingest_command(
    path: Path = typer.Argument(Path("fixtures")),
    root: Path = typer.Option(Path("."), "--root"),
) -> None:
    """Ingest local study fixtures into the evidence store."""
    result = ingest(Store(root), path if path.is_absolute() else root / path)
    console.print(
        f"Ingested {result.respondents} respondents, {result.quotes} quotes, "
        f"{result.survey_rows} survey rows, {result.screen_events} screen events."
    )


@app.command("analyze")
def analyze_command(root: Path = typer.Option(Path("."), "--root")) -> None:
    """Analyze quality, claims, evidence, and summary outputs."""
    outputs = analyze(Store(root), root / "outputs")
    console.print(f"Analysis complete: {len(outputs)} outputs written.")


@app.command("verify")
def verify_command(root: Path = typer.Option(Path("."), "--root")) -> None:
    """Verify claims have enough evidence and no unsupported verdicts pass."""
    report = verify(root / "outputs")
    for message in report.messages:
        console.print(message)
    if not report.ok:
        raise typer.Exit(1)


@app.command("dashboard")
def dashboard_command(root: Path = typer.Option(Path("."), "--root")) -> None:
    """Build a static insight audit dashboard."""
    path = build_dashboard(root / "outputs")
    console.print(f"Dashboard written: [bold]{path}[/bold]")


@app.command("compare")
def compare_command(
    exclude_low_quality: bool = typer.Option(False, "--exclude-low-quality"),
    root: Path = typer.Option(Path("."), "--root"),
) -> None:
    """Compare insight support with or without low-quality respondents."""
    path = compare(root / "outputs", exclude_low_quality=exclude_low_quality)
    console.print(f"Comparison written: [bold]{path}[/bold]")


@app.command("export-demo-pack")
def export_demo_pack_command(root: Path = typer.Option(Path("."), "--root")) -> None:
    """Export demo notes."""
    path = export_demo_pack(root / "outputs")
    console.print(f"Demo pack written: [bold]{path}[/bold]")


@app.command("benchmark")
def benchmark_command(root: Path = typer.Option(Path("."), "--root")) -> None:
    """Run the 500-transcript local evaluation benchmark."""
    path = run_benchmark(root)
    console.print(f"Benchmark written: [bold]{path}[/bold]")


@app.command("validate-summary")
def validate_summary_command(
    summary_path: Path,
    root: Path = typer.Option(Path("."), "--root"),
) -> None:
    """Validate a local automation-drafted summary against audited claim IDs."""
    report = validate_summary(root / "outputs", summary_path if summary_path.is_absolute() else root / summary_path)
    for message in report.messages:
        console.print(message)
    if not report.ok:
        raise typer.Exit(1)
