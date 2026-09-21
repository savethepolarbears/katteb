---
phase: 03-omnichannel-pipeline-integration-telemetry
plan: 02
title: Credit Threshold Monitoring and Telemetry Reporting
subsystem: telemetry,config,cli
tags: [telemetry, metrics, observability, credits, alerts, cli]
duration: 12m
---

# Plan 03-02 Summary: Credit Threshold Monitoring & Telemetry Reporting

## Objective Completed

Delivered fleet observability and proactive credit depletion monitoring:
1. Enhanced `KattebConfig` in `src/katteb/config.py` with configurable `telemetry_file` (default `~/.katteb/telemetry.jsonl`) and `credit_alert_threshold` (default 50 credits), resolving values across environment variables, `~/.katteb/config.json`, and constructor arguments.
2. Built `src/katteb/telemetry.py` providing:
   - `log_telemetry_event()`: Appends structured JSON lines with ISO 8601 UTC timestamps.
   - `get_telemetry_events()`: Reads the most recent N events from disk.
   - `get_telemetry_summary()`: Calculates aggregate metrics (total runs, words generated, success rate, credits used, average duration, and per-site breakdown).
   - `check_credit_threshold()`: Evaluates current account credits against warning thresholds, classifying status into `OK`, `WARNING`, or `CRITICAL`.
3. Wired post expansion telemetry into `WordPressFleetManager.expand_and_update_post()`, recording duration, word count deltas, and credits used.
4. Added CLI commands in `src/katteb/cli.py`:
   - `katteb account check-threshold`: Exits with code 0 if healthy, exit code 2 if at/below threshold (for automated CI/Activepieces conditional routing).
   - `katteb telemetry summary`: Formatted Rich table or JSON view of fleet metrics.
   - `katteb telemetry tail`: Formatted Rich table or JSON view of recent events.
5. Authored comprehensive unit tests in `tests/test_telemetry.py` (9 tests) covering JSONL logging, metrics aggregation, threshold alerting, and CLI exit codes.

## Key Changes

- `src/katteb/config.py`:
  - Added `DEFAULT_TELEMETRY_FILE` and `DEFAULT_CREDIT_ALERT_THRESHOLD`.
  - Added `telemetry_file` and `credit_alert_threshold` properties and resolvers.
- `src/katteb/telemetry.py`:
  - Structured event logger, reader, summary aggregator, and credit monitor.
- `src/katteb/wordpress.py`:
  - Measured post expansion duration and logged `post_expansion` telemetry event upon update.
- `src/katteb/cli.py`:
  - Added `account check-threshold`, `telemetry summary`, and `telemetry tail`.
- `tests/test_telemetry.py`:
  - Comprehensive unit test coverage for all telemetry and monitoring capabilities.

## Verification

Executed full test suite:
```bash
/Library/Frameworks/Python.framework/Versions/3.11/bin/pytest -o pythonpath=src
```
Result: All 56 unit tests passed in 0.25s.

## Phase 3 Completion

With Plans 03-01 and 03-02 completed:
- `OPS-01` (Activepieces pipeline integration adapter) is complete.
- `OPS-02` (Account credit threshold alerting) is complete.
- `OPS-03` (Structured JSON logging telemetry) is complete.
