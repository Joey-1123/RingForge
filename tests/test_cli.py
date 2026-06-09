"""
Tests for CLI commands (without network requests).
"""

from click.testing import CliRunner
from app.cli import main


class TestCLI:
    """Test basic CLI invocation."""

    def test_help(self):
        """--help should display all commands."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "download" in result.output
        assert "generate" in result.output
        assert "batch" in result.output
        assert "gui" in result.output
        assert "info" in result.output
        assert "preview" in result.output
        assert "export" in result.output

    def test_generate_help(self):
        """generate --help should show mode options."""
        runner = CliRunner()
        result = runner.invoke(main, ["generate", "--help"])
        assert result.exit_code == 0
        assert "manual" in result.output
        assert "heatmap" in result.output
        assert "auto" in result.output
        assert "notification" in result.output

    def test_export_help(self):
        """export --help should show profile options."""
        runner = CliRunner()
        result = runner.invoke(main, ["export", "--help"])
        assert result.exit_code == 0
        assert "android" in result.output
        assert "iphone" in result.output
        assert "notification" in result.output

    def test_batch_help(self):
        """batch --help should show its arguments."""
        runner = CliRunner()
        result = runner.invoke(main, ["batch", "--help"])
        assert result.exit_code == 0
        assert "INPUT_FILE" in result.output
        assert "mode" in result.output
        assert "limit" in result.output
