---
phase: 01-guard-hardening-test-verification
plan: 01
title: Guard Hardening and Concurrency Queue Verification
subsystem: wordpress,models,queue
tags: [guards, ip-whitelist, sanitization, queue, pydantic]
duration: 15m
---

# Plan 01-01 Summary: Guard Hardening & Concurrency Queue Verification

## Objective Completed

Hardened production safety guards and verified all core models and queue mechanisms with comprehensive unit tests:
1. Validated Pydantic models for credit pooling (`credits_available` and `credits_pool` aliases).
2. Hardened IP authorization guard in `WordPressFleetManager`, surfacing explicit egress IP whitelisting URL upon 401 errors.
3. Implemented error payload guard rejecting short error responses (< 400 chars) before WordPress content persistence.
4. Sanitized RankMath meta descriptions by stripping inline `<style>` blocks and CSS selector rules.
5. Verified `KattebQueueManager` concurrency 429 interception and job polling.

## Key Changes

- `src/katteb/models.py`: Added model validators and aliases for credit pooling.
- `src/katteb/wordpress.py`: Added IP auth guard, payload size check, and RankMath CSS sanitizer.
- `src/katteb/queue.py`: Added concurrency 429 recovery logic.
- `tests/test_wordpress.py`, `tests/test_models.py`, `tests/test_queue.py`: Added 27 unit tests.

## Verification

Executed full test suite:
```bash
/Library/Frameworks/Python.framework/Versions/3.11/bin/pytest -o pythonpath=src
```
Result: All 27 unit tests passed cleanly.
