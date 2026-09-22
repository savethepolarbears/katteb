"""Unit tests for Katteb pipeline webhook adapters and CLI event dispatcher."""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from katteb.cli import cli
from katteb.pipeline import PipelineEventPayload, process_pipeline_event


def test_pipeline_payload_validation_valid():
    payload = {
        "event": "post_expansion_requested",
        "site": "destinations-ai",
        "post_id": 1234,
        "target_words": 2000,
        "enhancements": ["tldr", "faq"],
        "dry_run": True,
    }
    model = PipelineEventPayload.model_validate(payload)
    assert model.event == "post_expansion_requested"
    assert model.site == "destinations-ai"
    assert model.post_id == 1234
    assert model.target_words == 2000
    assert model.dry_run is True


def test_pipeline_payload_defaults():
    payload = {
        "site": "viatravelers",
        "post_id": 555,
    }
    model = PipelineEventPayload.model_validate(payload)
    assert model.event == "post_expansion_requested"
    assert model.target_words == 1500
    assert model.enhancements == ["tldr", "key_takeaways", "faq"]
    assert model.dry_run is False


def test_process_pipeline_event_invalid_json():
    res = process_pipeline_event("not-a-valid-json{")
    assert res["success"] is False
    assert "Invalid JSON payload" in res["error"]


def test_process_pipeline_event_validation_failure():
    # Missing required post_id
    res = process_pipeline_event({"site": "viatravelers"})
    assert res["success"] is False
    assert "Validation error" in res["error"]


def test_process_pipeline_event_unsupported_event():
    res = process_pipeline_event({"event": "unknown_event", "site": "viatravelers", "post_id": 123})
    assert res["success"] is False
    assert "Unsupported event type" in res["error"]


def test_process_pipeline_event_invalid_site():
    res = process_pipeline_event({
        "event": "post_expansion_requested",
        "site": "invalid;site|injection",
        "post_id": 123,
    })
    assert res["success"] is False
    assert "Invalid site alias" in res["error"]


def test_process_pipeline_event_dry_run():
    mock_manager = MagicMock()
    mock_manager.expand_and_update_post.return_value = {
        "dry_run": True,
        "post_id": 100,
        "title": "Santorini Guide",
        "current_word_count": 300,
    }

    payload = {
        "event": "post_expansion_requested",
        "site": "santorinisecrets",
        "post_id": 100,
        "dry_run": True,
    }
    res = process_pipeline_event(payload, wp_manager=mock_manager)
    assert res["success"] is True
    assert res["site"] == "santorinisecrets"
    assert res["post_id"] == 100
    assert res["dry_run"] is True
    assert res["title"] == "Santorini Guide"
    assert res["old_word_count"] == 300


def test_process_pipeline_event_live_success():
    mock_manager = MagicMock()
    mock_manager.expand_and_update_post.return_value = {
        "success": True,
        "post_id": 200,
        "title": "Amsterdam Local Gems",
        "old_word_count": 400,
        "new_word_count": 1850,
        "meta_description": "Curated guide to Amsterdam.",
    }

    payload = json.dumps({
        "event": "post_expansion_requested",
        "site": "amsterdamlocalgems",
        "post_id": 200,
        "target_words": 1800,
    })

    res = process_pipeline_event(payload, wp_manager=mock_manager)
    assert res["success"] is True
    assert res["site"] == "amsterdamlocalgems"
    assert res["post_id"] == 200
    assert res["new_word_count"] == 1850
    assert res["meta_description"] == "Curated guide to Amsterdam."


def test_pipeline_dispatch_cli_dry_run():
    runner = CliRunner()
    mock_result = {
        "success": True,
        "event": "post_expansion_requested",
        "site": "destinations-ai",
        "post_id": 300,
        "dry_run": True,
        "title": "Berlin Guide",
        "old_word_count": 250,
        "new_word_count": None,
        "meta_description": None,
        "receipt_path": None,
    }

    with patch("katteb.pipeline.process_pipeline_event", return_value=mock_result):
        result = runner.invoke(
            cli,
            ["pipeline-dispatch", "--site", "destinations-ai", "--post-id", "300", "--dry-run", "--json"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["post_id"] == 300


def test_pipeline_dispatch_cli_stdin():
    runner = CliRunner()
    mock_result = {
        "success": True,
        "event": "post_expansion_requested",
        "site": "viatravelers",
        "post_id": 400,
        "dry_run": False,
        "title": "Paris Guide",
        "old_word_count": 300,
        "new_word_count": 1750,
        "meta_description": "Paris travel tips.",
        "receipt_path": None,
    }

    input_payload = json.dumps({
        "event": "post_expansion_requested",
        "site": "viatravelers",
        "post_id": 400,
    })

    with patch("katteb.pipeline.process_pipeline_event", return_value=mock_result):
        result = runner.invoke(
            cli,
            ["pipeline-dispatch", "--stdin"],
            input=input_payload,
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["new_word_count"] == 1750


def test_pipeline_payload_forbids_extra_fields():
    payload = {
        "event": "post_expansion_requested",
        "site": "destinations-ai",
        "post_id": 123,
        "unexpected_field": "injected_value",
    }
    with pytest.raises(Exception):
        PipelineEventPayload.model_validate(payload)


def test_process_pipeline_event_insecure_receipt_dir():
    payload = {
        "event": "post_expansion_requested",
        "site": "destinations-ai",
        "post_id": 123,
        "receipt_dir": "/etc/shadow_leak",
    }
    res = process_pipeline_event(payload)
    assert res["success"] is False
    assert "Insecure receipt_dir" in res["error"]


def test_process_pipeline_event_propagates_failure():
    mock_manager = MagicMock()
    mock_manager.expand_and_update_post.return_value = {
        "success": False,
        "error": "WP CLI post update failed with exit code 1",
    }
    payload = {
        "event": "post_expansion_requested",
        "site": "destinations-ai",
        "post_id": 123,
    }
    res = process_pipeline_event(payload, wp_manager=mock_manager)
    assert res["success"] is False
    assert "WP CLI post update failed" in res["error"]


def test_process_pipeline_event_redacts_tokens():
    mock_manager = MagicMock()
    mock_manager.expand_and_update_post.side_effect = RuntimeError(
        "Katteb API error with api_key=secret_katteb_token_12345 and Bearer sensitive_bearer_token_xyz"
    )
    payload = {
        "event": "post_expansion_requested",
        "site": "destinations-ai",
        "post_id": 123,
    }
    res = process_pipeline_event(payload, wp_manager=mock_manager)
    assert res["success"] is False
    assert "secret_katteb_token_12345" not in res["error"]
    assert "sensitive_bearer_token_xyz" not in res["error"]
    assert "[REDACTED]" in res["error"]
