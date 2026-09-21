---
phase: "01"
slug: "guard-hardening-test-verification"
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-09-21"
---

# Phase 01 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (Python 3.11) |
| **Config file** | `pytest.ini` / `pyproject.toml` |
| **Quick run command** | `/Library/Frameworks/Python.framework/Versions/3.11/bin/pytest -o pythonpath=src tests/test_wordpress.py tests/test_models.py tests/test_queue.py` |
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
| 01-01-01 | 01 | 1 | TEST-04 | — | Parses credit fields safely with alias fallbacks | unit | `pytest tests/test_models.py` | ✅ | ✅ green |
| 01-01-02 | 01 | 1 | TEST-01 | — | 401 raises IP auth error with portal link | unit | `pytest tests/test_wordpress.py::test_ip_authorization_guard` | ✅ | ✅ green |
| 01-01-03 | 01 | 1 | TEST-02 | — | Short error payloads rejected before WP write | unit | `pytest tests/test_wordpress.py::test_error_payload_guard` | ✅ | ✅ green |
| 01-01-04 | 01 | 1 | TEST-03 | — | Strips style tags and css selectors from meta desc | unit | `pytest tests/test_wordpress.py::test_meta_description_sanitizer` | ✅ | ✅ green |
| 01-01-05 | 01 | 1 | TEST-05 | — | Intercepts 429 lockout and polls active job | unit | `pytest tests/test_queue.py` | ✅ | ✅ green |
| 01-01-06 | 01 | 1 | TEST-06 | — | All 27 unit tests pass in local and CI | integration | `pytest` | ✅ | ✅ green |

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
