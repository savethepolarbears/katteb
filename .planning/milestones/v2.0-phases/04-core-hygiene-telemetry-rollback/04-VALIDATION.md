---
phase: 04
slug: core-hygiene-telemetry-rollback
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-10-13
---

# Phase 04 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest` >= 8.0.0 + `pytest-cov` >= 5.0.0 |
| **Config file** | `pyproject.toml` (`pythonpath = ["src"]`) |
| **Quick run command** | `pytest -q` |
| **Max feedback latency** | ~1.0s |

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Automated Command | Status |
|---------|------|------|-------------|-------------------|--------|
| 04-01-01 | 01 | 1 | CORE-01 | `pytest -q` | ✅ green |
| 04-01-02 | 01 | 1 | CORE-02 | `pytest tests/test_telemetry.py tests/test_wordpress.py -q` | ✅ green |
| 04-01-03 | 01 | 1 | CORE-03 | `pytest tests/test_client.py tests/test_queue.py -q` | ✅ green |
| 04-02-01 | 02 | 2 | CORE-04 | `pytest tests/test_wordpress.py tests/test_cli.py tests/test_pipeline.py -q` | ✅ green |

## Validation Sign-Off

- [x] All tasks have `<automated>` verify commands
- [x] `nyquist_compliant: true` set in frontmatter
