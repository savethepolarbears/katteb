---
phase: "02"
slug: "fleet-batch-expansion-quality-gates"
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-09-21"
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (Python 3.11) |
| **Config file** | `pytest.ini` / `pyproject.toml` |
| **Quick run command** | `/Library/Frameworks/Python.framework/Versions/3.11/bin/pytest -o pythonpath=src tests/test_wordpress.py tests/test_client.py` |
| **Full suite command** | `/Library/Frameworks/Python.framework/Versions/3.11/bin/pytest -o pythonpath=src` |
| **Estimated runtime** | ~0.20 seconds |

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
| 02-01-01 | 01 | 1 | BATCH-01 | — | Whitelist regex prevents command injection in site aliases | unit | `pytest tests/test_wordpress.py::test_validate_site_alias` | ✅ | ✅ green |
| 02-01-02 | 01 | 1 | BATCH-01 | — | Connectivity check verifies site before queue submission | unit | `pytest tests/test_wordpress.py::test_check_site_connectivity` | ✅ | ✅ green |
| 02-01-03 | 01 | 1 | BATCH-02 | — | 5xx errors and connection drops trigger exponential backoff | unit | `pytest tests/test_client.py::test_request_retry_on_502_success` | ✅ | ✅ green |
| 02-02-01 | 02 | 2 | BATCH-04 | — | Content without 2 H2s and 1 H3 raises ContentQualityError | unit | `pytest tests/test_wordpress.py::test_validate_generated_content_missing_headings` | ✅ | ✅ green |
| 02-02-02 | 02 | 2 | BATCH-04 | — | Hallucinated tokens (`[City]`, `[Insert]`) rejected | unit | `pytest tests/test_wordpress.py::test_validate_generated_content_placeholders` | ✅ | ✅ green |
| 02-02-03 | 02 | 2 | BATCH-03 | — | Batch expansions write timestamped Markdown audit receipts | unit | `pytest tests/test_wordpress.py::test_generate_expansion_receipt` | ✅ | ✅ green |

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
