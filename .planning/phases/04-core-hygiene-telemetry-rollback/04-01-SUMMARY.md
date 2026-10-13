---
phase: 04-core-hygiene-telemetry-rollback
plan: 01
subsystem: core-telemetry-queue
tags: [pytest, telemetry, credits, seo-queue]
requires: []
provides:
  - "Zero-config pytest execution via pyproject.toml pythonpath=['src']"
  - "End-to-end Katteb credit propagation (ArticleGenerateResponse -> KattebQueueManager -> ArticleGetResponse -> telemetry.jsonl)"
  - "Failed post_expansion telemetry capture on generation, quality gate, or WP update errors"
  - "KattebClient.poll_seo_until_complete() and SEO 429 active_job_type queue routing"
affects:
  - pyproject.toml
  - src/katteb/models.py
  - src/katteb/client.py
  - src/katteb/queue.py
  - src/katteb/telemetry.py
  - src/katteb/wordpress.py
completed: 2026-10-13
---

# Phase 4 Plan 01 Summary: Core Hygiene, Telemetry Accuracy & SEO Queue Polling

## Accomplishments
- **CORE-01**: Configured `pythonpath = ["src"]` in `pyproject.toml`, removed shadowing `pytest.ini`, and purged duplicate root `.planning/phases/01..03` and `.planning/MILESTONE-AUDIT.md`.
- **CORE-02**: Added `credits_charged` to `ArticleGetResponse` and `SEOGetResponse`, preserved `last_credits_charged` in `KattebQueueManager`, logged `credits_used` on both successful and failed `post_expansion` runs, and updated `get_telemetry_summary()` to aggregate `credits_used` with fallback to `estimated_credits`.
- **CORE-03**: Implemented `KattebClient.poll_seo_until_complete()`, `KattebQueueManager.analyze_seo_with_concurrency_wait()`, and `KattebQueueManager.analyze_seo_and_wait()`, routing `active_job_type == "seo"` on HTTP 429 to `poll_seo_until_complete()`.
