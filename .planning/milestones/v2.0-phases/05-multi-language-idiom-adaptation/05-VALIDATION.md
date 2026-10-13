---
phase: 5
slug: multi-language-idiom-adaptation
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-16
---

# Phase 5 — Validation Strategy

## Test Infrastructure
| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest tests/test_wordpress.py -q` |
| **Full suite command** | `pytest -q` |

## Per-Task Verification Map
| Task ID | Plan | Wave | Requirement | Automated Command | Status |
|---------|------|------|-------------|-------------------|--------|
| 05-01-01 | 01 | 1 | LANG-01, LANG-03 | `pytest tests/test_wordpress.py -k "resolve_site_language_and_country" -q` | ✅ green |
| 05-01-02 | 01 | 1 | LANG-02 | `pytest tests/test_wordpress.py -k "build_localized_guidelines" -q` | ✅ green |
| 05-01-03 | 01 | 1 | LANG-03 | `pytest tests/test_wordpress.py -k "validate_generated_content_multilingual_and_donkey_ban" -q` | ✅ green |
| 05-01-04 | 01 | 1 | LANG-01, LANG-02 | `pytest tests/test_wordpress.py -k "expand_and_update_post_passes_language_and_localized_guidelines" -q` | ✅ green |

## Validation Sign-Off
- [x] All tasks have automated verify commands
- [x] `nyquist_compliant: true` set in frontmatter
