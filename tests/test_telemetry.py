"""Unit tests for Katteb telemetry event logging, metrics aggregation, and credit threshold monitoring."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from katteb.cli import cli
from katteb.models import AccountCreditsResponse
from katteb.telemetry import (
    check_credit_threshold,
    get_telemetry_events,
    get_telemetry_summary,
    log_telemetry_event,
)


def test_log_telemetry_event(tmp_path: Path):
    log_file = tmp_path / "test_telemetry.jsonl"
    log_telemetry_event("test_event", {"foo": "bar", "count": 42}, log_path=log_file)

    assert log_file.is_file()
    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1

    entry = json.loads(lines[0])
    assert entry["event_type"] == "test_event"
    assert entry["foo"] == "bar"
    assert entry["count"] == 42
    assert "timestamp" in entry


def test_get_telemetry_events_tail(tmp_path: Path):
    log_file = tmp_path / "tail_test.jsonl"
    for i in range(5):
        log_telemetry_event("ping", {"index": i}, log_path=log_file)

    events = get_telemetry_events(limit=2, log_path=log_file)
    assert len(events) == 2
    assert events[0]["index"] == 3
    assert events[1]["index"] == 4


def test_get_telemetry_summary_aggregation(tmp_path: Path):
    log_file = tmp_path / "summary_test.jsonl"

    # Event 1: success, destinations-ai, 1500 words, 1 credit, 10.0s
    log_telemetry_event(
        "post_expansion",
        {
            "site": "destinations-ai",
            "post_id": 101,
            "success": True,
            "words_generated": 1500,
            "credits_used": 1,
            "duration_seconds": 10.0,
        },
        log_path=log_file,
    )
    # Event 2: success, viatravelers, 2000 words, 1 credit, 20.0s
    log_telemetry_event(
        "post_expansion",
        {
            "site": "viatravelers",
            "post_id": 102,
            "success": True,
            "words_generated": 2000,
            "credits_used": 1,
            "duration_seconds": 20.0,
        },
        log_path=log_file,
    )
    # Event 3: failure, destinations-ai, 0 words, 0 credits, 2.0s
    log_telemetry_event(
        "post_expansion",
        {
            "site": "destinations-ai",
            "post_id": 103,
            "success": False,
            "words_generated": 0,
            "credits_used": 0,
            "duration_seconds": 2.0,
        },
        log_path=log_file,
    )

    summary = get_telemetry_summary(log_path=log_file)
    assert summary["total_events"] == 3
    assert summary["events_by_type"]["post_expansion"] == 3

    pe = summary["post_expansions"]
    assert pe["total_runs"] == 3
    assert pe["successful_runs"] == 2
    assert pe["failed_runs"] == 1
    assert pe["success_rate_percent"] == 66.7
    assert pe["total_words_generated"] == 3500
    assert pe["total_credits_used"] == 2
    assert pe["total_duration_seconds"] == 32.0
    assert pe["avg_duration_seconds"] == 10.67

    # Per site checks
    assert "destinations-ai" in pe["sites"]
    assert pe["sites"]["destinations-ai"]["runs"] == 2
    assert pe["sites"]["destinations-ai"]["successful_runs"] == 1
    assert pe["sites"]["destinations-ai"]["words_generated"] == 1500

    assert "viatravelers" in pe["sites"]
    assert pe["sites"]["viatravelers"]["runs"] == 1
    assert pe["sites"]["viatravelers"]["successful_runs"] == 1
    assert pe["sites"]["viatravelers"]["words_generated"] == 2000


def test_check_credit_threshold_ok():
    mock_client = MagicMock()
    mock_client.get_credits.return_value = AccountCreditsResponse(
        success=True,
        credits=250,
        plan_tier="Enterprise Pro",
    )

    res = check_credit_threshold(mock_client, threshold=50)
    assert res["status"] == "OK"
    assert res["available_credits"] == 250
    assert res["threshold"] == 50
    assert res["depleted"] is False
    assert "healthy" in res["alert_message"].lower()


def test_check_credit_threshold_warning():
    mock_client = MagicMock()
    mock_client.get_credits.return_value = AccountCreditsResponse(
        success=True,
        credits=30,
        plan_tier="Standard",
    )

    res = check_credit_threshold(mock_client, threshold=50)
    assert res["status"] == "WARNING"
    assert res["available_credits"] == 30
    assert res["depleted"] is True
    assert "warning" in res["alert_message"].lower()


def test_check_credit_threshold_critical():
    mock_client = MagicMock()
    mock_client.get_credits.return_value = AccountCreditsResponse(
        success=True,
        credits=0,
        plan_tier="Standard",
    )

    res = check_credit_threshold(mock_client, threshold=50)
    assert res["status"] == "CRITICAL"
    assert res["available_credits"] == 0
    assert res["depleted"] is True
    assert "critical" in res["alert_message"].lower()


def test_account_check_threshold_cli_ok():
    runner = CliRunner()
    mock_res = AccountCreditsResponse(success=True, credits=120, plan_tier="Pro")

    with patch("katteb.cli.get_client") as mock_gc:
        client = MagicMock()
        client.config.credit_alert_threshold = 50
        client.get_credits.return_value = mock_res
        mock_gc.return_value = client

        result = runner.invoke(cli, ["account", "check-threshold", "--threshold", "50", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "OK"
        assert data["available_credits"] == 120


def test_account_check_threshold_cli_warning_exit_code():
    runner = CliRunner()
    mock_res = AccountCreditsResponse(success=True, credits=25, plan_tier="Pro")

    with patch("katteb.cli.get_client") as mock_gc:
        client = MagicMock()
        client.config.credit_alert_threshold = 50
        client.get_credits.return_value = mock_res
        mock_gc.return_value = client

        result = runner.invoke(cli, ["account", "check-threshold", "--threshold", "50", "--json"])
        # Exit code 2 on warning/depleted status
        assert result.exit_code == 2
        data = json.loads(result.output)
        assert data["status"] == "WARNING"
        assert data["depleted"] is True


def test_telemetry_cli_summary(tmp_path: Path):
    log_file = tmp_path / "cli_summary.jsonl"
    log_telemetry_event(
        "post_expansion",
        {
            "site": "destinations-ai",
            "post_id": 1,
            "success": True,
            "words_generated": 1000,
            "credits_used": 1,
            "duration_seconds": 5.0,
        },
        log_path=log_file,
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["telemetry", "summary", "--file", str(log_file), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["total_events"] == 1
    assert data["post_expansions"]["total_runs"] == 1
    assert data["post_expansions"]["total_words_generated"] == 1000


def test_get_telemetry_events_invalid_limit(tmp_path: Path):
    import pytest
    with pytest.raises(ValueError) as exc:
        get_telemetry_events(limit=0)
    assert "greater than 0" in str(exc.value)

    with pytest.raises(ValueError) as exc:
        get_telemetry_events(limit=-5)
    assert "greater than 0" in str(exc.value)


def test_get_telemetry_summary_corrupted_lines(tmp_path: Path):
    log_file = tmp_path / "corrupt_summary.jsonl"
    log_file.write_text(
        '{"timestamp": "2026-09-22T00:00:00Z", "event_type": "post_expansion", "success": true, "words_generated": 1000}\n'
        'NOT_A_VALID_JSON_LINE\n'
        '{"timestamp": "2026-09-22T00:01:00Z", "event_type": "post_expansion", "success": false}\n'
        'ANOTHER_CORRUPTED_LINE{{{\n',
        encoding="utf-8",
    )

    summary = get_telemetry_summary(log_path=log_file)
    assert summary["total_events"] == 2
    assert summary["corrupted_lines_count"] == 2
    assert summary["post_expansions"]["total_runs"] == 2
    assert summary["post_expansions"]["successful_runs"] == 1
    assert summary["post_expansions"]["failed_runs"] == 1


def test_log_telemetry_concurrent_writes(tmp_path: Path):
    from concurrent.futures import ThreadPoolExecutor

    log_file = tmp_path / "concurrent_telemetry.jsonl"
    total_writers = 20

    def write_worker(idx: int):
        log_telemetry_event(
            event_type="concurrent_test",
            data={"worker_id": idx, "message": f"Message from worker {idx}"},
            log_path=log_file,
        )

    with ThreadPoolExecutor(max_workers=5) as executor:
        list(executor.map(write_worker, range(total_writers)))

    events = get_telemetry_events(limit=100, log_path=log_file)
    assert len(events) == total_writers
    worker_ids = {e["worker_id"] for e in events}
    assert worker_ids == set(range(total_writers))
