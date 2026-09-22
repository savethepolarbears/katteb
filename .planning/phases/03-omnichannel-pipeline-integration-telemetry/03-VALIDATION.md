---
phase: "03"
slug: "omnichannel-pipeline-integration-telemetry"
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-09-21"
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (Python 3.11) |
| **Config file** | `pytest.ini` / `pyproject.toml` |
| **Quick run command** | `/Library/Frameworks/Python.framework/Versions/3.11/bin/pytest -o pythonpath=src tests/test_pipeline.py tests/test_telemetry.py` |
| **Full suite command** | `/Library/Frameworks/Python.framework/Versions/3.11/bin/pytest -o pythonpath=src` |
| **Estimated runtime** | ~0.25 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite command
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 1.0s

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | OPS-01 | — | Pydantic model validates inbound webhook payloads | unit | `pytest tests/test_pipeline.py::test_pipeline_payload_validation_valid` | ✅ | ✅ green |
| 03-01-02 | 01 | 1 | OPS-01 | — | Headless CLI reads stdin JSON and outputs parseable stdout JSON | integration | `pytest tests/test_pipeline.py::test_pipeline_dispatch_cli_stdin` | ✅ | ✅ green |
| 03-02-01 | 02 | 2 | OPS-03 | — | Post expansion logs ISO timestamped JSON lines | unit | `pytest tests/test_telemetry.py::test_log_telemetry_event` | ✅ | ✅ green |
| 03-02-02 | 02 | 2 | OPS-03 | — | Aggregator computes duration, words, credits, and site totals | unit | `pytest tests/test_telemetry.py::test_get_telemetry_summary_aggregation` | ✅ | ✅ green |
| 03-02-03 | 02 | 2 | OPS-02 | — | Depleted credits trigger exit code 2 for workflow alerts | integration | `pytest tests/test_telemetry.py::test_account_check_threshold_cli_warning_exit_code` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 1.0s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-09-21
