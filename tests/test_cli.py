from unittest.mock import patch

from click.testing import CliRunner

from katteb.cli import cli
from katteb.models import AccountCreditsResponse


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Katteb API v2 CLI" in result.output


def test_config_set_key_command(tmp_path, monkeypatch):
    test_config_file = tmp_path / "config.json"
    monkeypatch.setattr("katteb.config.CONFIG_FILE", test_config_file)
    monkeypatch.setattr("katteb.config.CONFIG_DIR", tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "set-key", "my_new_secret_key_123"])
    assert result.exit_code == 0
    assert "Katteb API key securely saved" in result.output
    assert test_config_file.is_file()


def test_account_credits_cli():
    runner = CliRunner()
    mock_res = AccountCreditsResponse(
        success=True,
        credits=30000,
        credits_total=50000,
        plan_type="pro",
    )

    with patch("katteb.cli.KattebClient.get_credits", return_value=mock_res):
        result = runner.invoke(cli, ["--api-key", "dummy_key", "account", "credits"])
        assert result.exit_code == 0
        assert "30000" in result.output
        assert "PRO" in result.output


def test_account_credits_cli_json():
    runner = CliRunner()
    mock_res = AccountCreditsResponse(
        success=True,
        credits=30000,
        credits_total=50000,
        plan_type="pro",
    )

    with patch("katteb.cli.KattebClient.get_credits", return_value=mock_res):
        result = runner.invoke(cli, ["--api-key", "dummy_key", "--json", "account", "credits"])
        assert result.exit_code == 0
        assert '"credits": 30000' in result.output
