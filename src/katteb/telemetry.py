"""Telemetry logger, fleet metrics aggregator, and credit depletion monitor for Katteb."""

from __future__ import annotations

import fcntl
import json
import os
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from katteb.client import KattebClient
from katteb.config import KattebConfig, get_config


def resolve_log_path(log_path: Path | str | None = None) -> Path:
    """Resolve active telemetry log file path."""
    if log_path:
        return Path(log_path).expanduser()
    cfg = get_config()
    return cfg.telemetry_file


def log_telemetry_event(
    event_type: str,
    data: dict[str, Any],
    log_path: Path | str | None = None,
) -> Path:
    """Append a structured JSON line event to the telemetry log file with atomic file locking."""
    path = resolve_log_path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        **data,
    }

    payload = json.dumps(record, default=str) + "\n"
    with open(path, "a", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    return path


def get_telemetry_events(
    limit: int = 50,
    log_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Read the most recent N telemetry events from log file with bounded memory usage."""
    if limit <= 0:
        raise ValueError(f"limit must be greater than 0, got {limit}")
    limit = min(limit, 50000)

    path = resolve_log_path(log_path)
    if not path.is_file():
        return []

    events_deque: deque[dict[str, Any]] = deque(maxlen=limit)
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    events_deque.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []

    return list(events_deque)


def get_telemetry_summary(log_path: Path | str | None = None) -> dict[str, Any]:
    """Calculate aggregate telemetry and performance metrics by streaming events directly."""
    path = resolve_log_path(log_path)

    summary: dict[str, Any] = {
        "total_events": 0,
        "corrupted_lines_count": 0,
        "events_by_type": {},
        "post_expansions": {
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "success_rate_percent": 100.0,
            "total_words_generated": 0,
            "total_credits_used": 0,
            "total_duration_seconds": 0.0,
            "avg_duration_seconds": 0.0,
            "sites": {},
        },
    }

    if not path.is_file():
        return summary

    pe = summary["post_expansions"]

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    summary["corrupted_lines_count"] += 1
                    continue

                summary["total_events"] += 1
                etype = ev.get("event_type", "unknown")
                summary["events_by_type"][etype] = summary["events_by_type"].get(etype, 0) + 1

                if etype == "post_expansion":
                    pe["total_runs"] += 1
                    success = ev.get("success", False)
                    if success:
                        pe["successful_runs"] += 1
                    else:
                        pe["failed_runs"] += 1

                    words = int(ev.get("words_generated") or 0)
                    credits_used = int(ev.get("credits_used") or 0)
                    duration = float(ev.get("duration_seconds") or 0.0)

                    pe["total_words_generated"] += words
                    pe["total_credits_used"] += credits_used
                    pe["total_duration_seconds"] += duration

                    site = ev.get("site") or "unknown"
                    if site not in pe["sites"]:
                        pe["sites"][site] = {
                            "runs": 0,
                            "successful_runs": 0,
                            "words_generated": 0,
                            "credits_used": 0,
                        }
                    site_stat = pe["sites"][site]
                    site_stat["runs"] += 1
                    if success:
                        site_stat["successful_runs"] += 1
                    site_stat["words_generated"] += words
                    site_stat["credits_used"] += credits_used
    except OSError:
        pass

    if pe["total_runs"] > 0:
        pe["success_rate_percent"] = round((pe["successful_runs"] / pe["total_runs"]) * 100, 1)
        pe["avg_duration_seconds"] = round(pe["total_duration_seconds"] / pe["total_runs"], 2)
        pe["total_duration_seconds"] = round(pe["total_duration_seconds"], 2)

    return summary


def check_credit_threshold(
    client: KattebClient,
    threshold: int | None = None,
) -> dict[str, Any]:
    """Check account credits against safety threshold and return alert status payload.

    Status is:
    - 'OK' if available credits > threshold
    - 'WARNING' if available credits <= threshold and > 0
    - 'CRITICAL' if available credits <= 0
    """
    effective_threshold = (
        threshold
        if threshold is not None
        else client.config.credit_alert_threshold
    )

    credits_res = client.get_credits()
    avail = credits_res.credits if credits_res.credits is not None else 0

    if avail <= 0:
        status = "CRITICAL"
        depleted = True
        msg = f"CRITICAL: Katteb account has 0 credits remaining! Refill required immediately."
    elif avail <= effective_threshold:
        status = "WARNING"
        depleted = True
        msg = f"WARNING: Katteb credit balance ({avail}) has fallen to or below alert threshold ({effective_threshold})."
    else:
        status = "OK"
        depleted = False
        msg = f"OK: Credit balance ({avail}) is healthy and above threshold ({effective_threshold})."

    return {
        "status": status,
        "available_credits": avail,
        "threshold": effective_threshold,
        "plan_tier": credits_res.plan_tier or credits_res.plan_type or "Unknown",
        "depleted": depleted,
        "alert_message": msg,
    }
