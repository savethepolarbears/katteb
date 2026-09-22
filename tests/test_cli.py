from unittest.mock import MagicMock, patch

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


def test_account_check_threshold_api_error_json():
    import json
    runner = CliRunner()
    with patch("katteb.cli.get_client") as mock_gc:
        client = MagicMock()
        client.get_credits.side_effect = RuntimeError("Katteb API network timeout")
        mock_gc.return_value = client

        result = runner.invoke(cli, ["account", "check-threshold", "--json"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["status"] == "ERROR"
        assert "network timeout" in data["error"]


def test_wp_batch_expand_json_purity():
    import json
    runner = CliRunner()
    with patch("katteb.cli.WordPressFleetManager") as mock_wp_cls:
        mock_wp = MagicMock()
        mock_wp.audit_low_word_posts.return_value = [
            {"id": 101, "title": "Zurich", "content_wc": 250},
        ]
        mock_wp.expand_and_update_post.return_value = {
            "success": True,
            "post_id": 101,
            "title": "Zurich",
            "previous_word_count": 250,
            "new_word_count": 1800,
        }
        mock_wp_cls.return_value = mock_wp

        result = runner.invoke(cli, ["--api-key", "dummy", "--json", "wp", "batch-expand", "--limit", "1"])
        assert result.exit_code == 0
        # Must be pure JSON parseable without leading/trailing non-JSON stdout
        data = json.loads(result.output)
        assert "batch_results" in data
        assert len(data["batch_results"]) == 1
        assert data["batch_results"][0]["new_word_count"] == 1800


def test_pipeline_dispatch_missing_payload_sources():
    runner = CliRunner()
    result = runner.invoke(cli, ["pipeline-dispatch", "--json"])
    assert result.exit_code == 1
    import json
    data = json.loads(result.output)
    assert data["success"] is False
    assert "Missing payload source" in data["error"]
