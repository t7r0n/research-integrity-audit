from typer.testing import CliRunner

from research_integrity.cli import app


def test_cli_help() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Listen integrity CLI" in result.output or "research integrity" in result.output

