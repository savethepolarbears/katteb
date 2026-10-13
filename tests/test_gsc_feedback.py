"""Unit tests for Google Search Console striking-distance detector and 30-day post-expansion impact auditor."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from katteb.cli import cli
from katteb.gsc_feedback import (
    CONTENT_REFRESH_QUEUE_TABLE_ID,
    GSCFeedbackAuditor,
    compute_opportunity_score,
    format_refresh_queue_records,
    resolve_gsc_property,
)
from katteb.pipeline import process_pipeline_event
from katteb.telemetry import get_telemetry_events


def test_resolve_gsc_property_and_opportunity_score():
    assert resolve_gsc_property("santorinisecrets") == "sc-domain:santorinisecrets.com"
    assert resolve_gsc_property("everythingaboutgermany") == "sc-domain:everythingaboutgermany.com"
    assert resolve_gsc_property("viatravelers") == "sc-domain:viatravelers.com"

    score_top5 = compute_opportunity_score(impressions=500, position=5.0, ctr=0.01)
    score_pos14 = compute_opportunity_score(impressions=500, position=14.0, ctr=0.01)
    assert score_top5 > score_pos14 > 0
    assert compute_opportunity_score(impressions=0, position=5.0, ctr=0.02) == 0.0


def test_detect_striking_distance_queries_filtering_and_ranking():
    auditor = GSCFeedbackAuditor()
    sample_rows = [
        {"query": "best areas to stay in santorini", "page": "https://santorinisecrets.com/where-to-stay", "clicks": 8, "impressions": 620, "ctr": 0.0129, "position": 5.4},
        {"query": "fira vs oia santorini", "page": "https://santorinisecrets.com/fira-vs-oia", "clicks": 3, "impressions": 210, "ctr": 0.014, "position": 11.2},
        {"query": "santorini hotels", "page": "https://santorinisecrets.com/hotels", "clicks": 90, "impressions": 900, "ctr": 0.10, "position": 2.1},  # Too high (pos < 4.0)
        {"query": "obscure cyclades ferry", "page": "https://santorinisecrets.com/ferry", "clicks": 1, "impressions": 25, "ctr": 0.04, "position": 7.5},  # Too few impressions (< 50)
        {"query": "deep page 3 query", "page": "https://santorinisecrets.com/page3", "clicks": 0, "impressions": 300, "ctr": 0.0, "position": 22.0},  # Pos > 15.0
    ]

    opportunities = auditor.detect_striking_distance_queries(
        site="santorinisecrets",
        rows_override=sample_rows,
    )
    assert len(opportunities) == 2
    assert opportunities[0]["query"] == "best areas to stay in santorini"
    assert opportunities[1]["query"] == "fira vs oia santorini"
    assert opportunities[0]["opportunity_score"] > opportunities[1]["opportunity_score"]


def test_fetch_gsc_analytics_via_gog_subprocess():
    auditor = GSCFeedbackAuditor()
    fake_stdout = json.dumps(
        {
            "rows": [
                {
                    "keys": ["munich 3 day itinerary", "https://everythingaboutgermany.com/munich-itinerary/"],
                    "clicks": 12,
                    "impressions": 450,
                    "ctr": 0.0266,
                    "position": 6.8,
                }
            ]
        }
    )
    mock_proc = MagicMock(returncode=0, stdout=fake_stdout, stderr="")
    with patch("katteb.gsc_feedback.subprocess.run", return_value=mock_proc) as mock_run:
        rows = auditor.fetch_gsc_analytics(site="everythingaboutgermany", days=28)

    assert len(rows) == 1
    assert rows[0]["query"] == "munich 3 day itinerary"
    assert rows[0]["page"] == "https://everythingaboutgermany.com/munich-itinerary/"
    cmd_called = mock_run.call_args[0][0]
    assert cmd_called[0] == "gog"
    assert "--client" in cmd_called
    assert "bbm-analytics-cloud" in cmd_called
    assert "sc-domain:everythingaboutgermany.com" in cmd_called


def test_audit_expanded_posts_impact_30_day_correlation_and_refresh_queue(tmp_path: Path):
    log_file = tmp_path / "telemetry.jsonl"
    old_ts = (datetime.now(timezone.utc) - timedelta(days=35)).isoformat()
    recent_ts = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()

    events = [
        {
            "timestamp": old_ts,
            "event_type": "post_expansion",
            "site": "santorinisecrets",
            "post_id": 401,
            "title": "Santorini Sunset Guide",
            "previous_word_count": 310,
            "new_word_count": 1680,
            "credits_used": 1680,
            "wp_admin_edit_url": "https://santorinisecrets.com/wp-admin/post.php?post=401&action=edit",
            "success": True,
        },
        {
            "timestamp": recent_ts,
            "event_type": "post_expansion",
            "site": "santorinisecrets",
            "post_id": 402,
            "title": "Recent Oia Post",
            "previous_word_count": 290,
            "new_word_count": 1520,
            "credits_used": 1520,
            "success": True,
        },
    ]
    log_file.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")

    gsc_rows = [
        {
            "query": "santorini sunset guide oia",
            "page": "https://santorinisecrets.com/santorini-sunset-guide/",
            "clicks": 4,
            "impressions": 380,
            "ctr": 0.0105,
            "position": 7.2,
        }
    ]

    auditor = GSCFeedbackAuditor()
    summary = auditor.audit_expanded_posts_impact(
        site="santorinisecrets",
        min_days_age=30,
        log_path=log_file,
        rows_override=gsc_rows,
        record_telemetry=True,
    )

    assert summary["success"] is True
    assert summary["audited_count"] == 1
    assert summary["needs_refresh_count"] == 1
    assert summary["audited_posts"][0]["post_id"] == 401
    assert summary["audited_posts"][0]["needs_refresh"] is True

    rq = summary["refresh_queue"]
    assert rq["table_id"] == CONTENT_REFRESH_QUEUE_TABLE_ID
    assert rq["record_count"] == 1
    assert rq["records"][0]["recommended_action"] == "rankmath_title_meta_ctr_refresh"

    recorded = get_telemetry_events(limit=10, log_path=log_file)
    assert recorded[-1]["event_type"] == "gsc_re_audit"
    assert recorded[-1]["needs_refresh_count"] == 1


def test_cli_and_pipeline_striking_distance(tmp_path: Path):
    gsc_json = tmp_path / "gsc_sample.json"
    gsc_json.write_text(
        json.dumps(
            [
                {
                    "query": "best neighborhoods in amsterdam",
                    "page": "https://amsterdamlocalgems.com/neighborhoods/",
                    "clicks": 5,
                    "impressions": 410,
                    "ctr": 0.012,
                    "position": 9.4,
                }
            ]
        ),
        encoding="utf-8",
    )

    runner = CliRunner()
    cli_res = runner.invoke(
        cli,
        ["wp", "striking-distance", "--site", "amsterdamlocalgems", "--input-file", str(gsc_json), "--json"],
    )
    assert cli_res.exit_code == 0
    parsed = json.loads(cli_res.output)
    assert parsed["success"] is True
    assert parsed["count"] == 1
    assert parsed["refresh_queue"]["table_id"] == CONTENT_REFRESH_QUEUE_TABLE_ID
    assert parsed["refresh_queue"]["records"][0]["recommended_action"] == "katteb_section_and_faq_expansion"

    pipe_res = process_pipeline_event(
        {
            "event": "gsc_striking_distance_audit",
            "site": "amsterdamlocalgems",
            "days": 28,
            "gsc_input_file": str(gsc_json),
        }
    )
    assert pipe_res["success"] is True
    assert pipe_res["opportunities_count"] == 1
    assert pipe_res["refresh_queue"]["table_id"] == CONTENT_REFRESH_QUEUE_TABLE_ID

    # Also test Rich table output (without --json) and wp audit-impact CLI
    table_res = runner.invoke(
        cli,
        ["wp", "striking-distance", "--site", "amsterdamlocalgems", "--input-file", str(gsc_json)],
    )
    assert table_res.exit_code == 0
    assert "best neighborhoods in amsterdam" in table_res.output

    log_file = tmp_path / "audit_tel.jsonl"
    old_ts = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
    log_file.write_text(
        json.dumps(
            {
                "timestamp": old_ts,
                "event_type": "post_expansion",
                "site": "amsterdamlocalgems",
                "post_id": 505,
                "title": "Best Neighborhoods in Amsterdam",
                "previous_word_count": 300,
                "new_word_count": 1700,
                "success": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    audit_json_res = runner.invoke(
        cli,
        [
            "wp",
            "audit-impact",
            "--site",
            "amsterdamlocalgems",
            "--min-days",
            "30",
            "--log-file",
            str(log_file),
            "--gsc-file",
            str(gsc_json),
            "--json",
        ],
    )
    assert audit_json_res.exit_code == 0
    audit_data = json.loads(audit_json_res.output)
    assert audit_data["audited_count"] == 1
    assert audit_data["needs_refresh_count"] == 1

    audit_human_res = runner.invoke(
        cli,
        [
            "wp",
            "audit-impact",
            "--site",
            "amsterdamlocalgems",
            "--min-days",
            "30",
            "--log-file",
            str(log_file),
            "--gsc-file",
            str(gsc_json),
        ],
    )
    assert audit_human_res.exit_code == 0
    assert "30-Day Impact Audit Complete" in audit_human_res.output

