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


def test_cli_config_show():
    runner = CliRunner()
    result = runner.invoke(cli, ["--api-key", "test_api_key_12345", "config", "show"])
    assert result.exit_code == 0
    assert "Katteb Active Configuration" in result.output
    assert "test...2345" in result.output


def test_cli_account_limits():
    runner = CliRunner()
    with patch("katteb.cli.KattebClient.get_limits", return_value={"rate_limits": {"requests_per_minute": 60}}):
        result = runner.invoke(cli, ["--api-key", "dummy", "--json", "account", "limits"])
        assert result.exit_code == 0
        assert "requests_per_minute" in result.output


def test_cli_styles_list():
    from katteb.models import StylesListResponse, WritingStyle

    runner = CliRunner()
    mock_res = StylesListResponse(styles=[WritingStyle(id=1, name="Journalistic", is_active=True)])
    with patch("katteb.cli.KattebClient.list_styles", return_value=mock_res):
        result = runner.invoke(cli, ["--api-key", "dummy", "styles", "list"])
        assert result.exit_code == 0
        assert "Journalistic" in result.output


def test_cli_brands_list():
    from katteb.models import Brand, BrandsListResponse

    runner = CliRunner()
    mock_res = BrandsListResponse(brands=[Brand(id=1, name="Test Brand", url="https://example.com")])
    with patch("katteb.cli.KattebClient.list_brands", return_value=mock_res):
        result = runner.invoke(cli, ["--api-key", "dummy", "brands", "list"])
        assert result.exit_code == 0
        assert "Test Brand" in result.output


def test_cli_articles_list():
    from katteb.models import ArticleListResponse

    runner = CliRunner()
    mock_res = ArticleListResponse(articles=[{"job_id": 1, "topic": "AI Travel", "status": "completed"}])
    with patch("katteb.cli.KattebClient.list_articles", return_value=mock_res):
        result = runner.invoke(cli, ["--api-key", "dummy", "article", "list"])
        assert result.exit_code == 0
        assert "AI Travel" in result.output


def test_cli_articles_get():
    from katteb.models import ArticleGetResponse

    runner = CliRunner()
    mock_res = ArticleGetResponse(job_id=99, topic="Greek Islands Guide", status="completed", word_count=1500)
    with patch("katteb.cli.KattebClient.get_article", return_value=mock_res):
        result = runner.invoke(cli, ["--api-key", "dummy", "article", "get", "99"])
        assert result.exit_code == 0
        assert "Greek Islands Guide" in result.output


def test_cli_factcheck_verify():
    from katteb.models import FactCheckResponse

    runner = CliRunner()
    mock_res = FactCheckResponse(verdict="TRUE", explanation="Verified claim.")
    with patch("katteb.cli.KattebClient.verify_fact", return_value=mock_res):
        result = runner.invoke(cli, ["--api-key", "dummy", "factcheck", "verify", "--claim", "Earth orbits the sun."])
        assert result.exit_code == 0
        assert "TRUE" in result.output


def test_cli_humanizer_detect():
    from katteb.models import HumanizerDetectResponse

    runner = CliRunner()
    mock_res = HumanizerDetectResponse(ai_probability=10, verdict="likely_human", word_count=100)
    with patch("katteb.cli.KattebClient.detect_ai", return_value=mock_res):
        result = runner.invoke(
            cli, ["--api-key", "dummy", "humanizer", "detect", "--text", "This is human written text."]
        )
        assert result.exit_code == 0
        assert "likely_human" in result.output


def test_cli_humanizer_rewrite():
    from katteb.models import HumanizerRewriteResponse

    runner = CliRunner()
    mock_res = HumanizerRewriteResponse(rewritten_text="Humanized output text.", credits_charged=1)
    with patch("katteb.cli.KattebClient.rewrite_humanizer", return_value=mock_res):
        result = runner.invoke(cli, ["--api-key", "dummy", "humanizer", "rewrite", "--text", "Some robot text"])
        assert result.exit_code == 0
        assert "Humanized output text." in result.output


def test_cli_article_cancel():
    runner = CliRunner()
    with patch("katteb.cli.KattebClient.cancel_article", return_value={"success": True}):
        result = runner.invoke(cli, ["--api-key", "dummy", "article", "cancel", "42"])
        assert result.exit_code == 0
        assert "Job #42 cancelled" in result.output


def test_cli_seo_analyze_and_get():
    from katteb.models import SEOAnalyzeResponse

    runner = CliRunner()
    # Missing both url and text
    res_err = runner.invoke(cli, ["--api-key", "dummy", "seo", "analyze"])
    assert res_err.exit_code == 1
    assert "Error: Must specify either --url or --text" in res_err.output

    # Valid analyze
    mock_seo = SEOAnalyzeResponse(job_id=88, success=True)
    with patch("katteb.cli.KattebClient.analyze_seo", return_value=mock_seo):
        res_ok = runner.invoke(cli, ["--api-key", "dummy", "seo", "analyze", "--url", "https://example.com/guide"])
        assert res_ok.exit_code == 0
        assert "SEO Analysis Queued!" in res_ok.output

    # Get SEO results
    with patch("katteb.cli.KattebClient.get_seo", return_value={"job_id": 88, "score": 92}):
        res_get = runner.invoke(cli, ["--api-key", "dummy", "--json", "seo", "get", "88"])
        assert res_get.exit_code == 0
        assert '"score": 92' in res_get.output


def test_cli_telemetry_tail(tmp_path):
    import json

    log_file = tmp_path / "telemetry.jsonl"
    events = [
        {
            "timestamp": "2026-10-05T10:00:00",
            "event_type": "post_expansion",
            "site": "santorinisecrets",
            "success": True,
            "words_generated": 1500,
        },
    ]
    with open(log_file, "w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")

    runner = CliRunner()
    res = runner.invoke(cli, ["telemetry", "tail", "--file", str(log_file)])
    assert res.exit_code == 0
    assert "post_expansion" in res.output

    res_json = runner.invoke(cli, ["telemetry", "tail", "--file", str(log_file), "--json"])
    assert res_json.exit_code == 0
    assert "santorinisecrets" in res_json.output
