---
phase: 02-fleet-batch-expansion-quality-gates
plan: 01
title: Multi-Site Configuration Profiles and Exponential Backoff Retry Handler
subsystem: wordpress,client
tags: [wordpress, fleet, retry, backoff, profiles]
duration: 10m
---

# Plan 02-01 Summary: Multi-Site Profiles & Exponential Backoff Retries

## Objective Completed

Delivered multi-site targeting and robust error resilience for WordPress batch expansions:
1. Created `FLEET_SITE_PROFILES` registry mapping known fleet properties (`destinations-ai`, `viatravelers`, `santorinisecrets`, `amsterdamlocalgems`, `parkervillas`, `realjourneytravels`, `everythingaboutgermany`, `gearbuddha`, `theimpactinvestor`).
2. Implemented `validate_site_alias` to sanitize site identifiers and prevent shell injection vulnerabilities in WP-CLI execution.
3. Added `check_site_connectivity` to `WordPressFleetManager` for preflight verification.
4. Implemented exponential backoff with jitter in `KattebClient._request` to automatically retry transient 5xx server errors and network connection drops (3 retries, exponential factor 2.0).
5. Authored comprehensive unit tests covering alias validation, site connectivity, 502 retry recovery, and connection error handling.

## Key Changes

- `src/katteb/wordpress.py`:
  - Added `FLEET_SITE_PROFILES` with domain and default post type mappings.
  - Added `validate_site_alias()` enforcing alphanumeric/dash/dot syntax.
  - Added `check_site_connectivity()` to `WordPressFleetManager`.
  - Updated `run_wp_cli()` to validate all aliases before passing to `subprocess`.
- `src/katteb/client.py`:
  - Enhanced `_request()` with `max_retries`, `backoff_factor`, and `initial_delay`.
  - Added automatic retries with random jitter on 5xx errors and `RequestException`.
  - Preserved discrete 401, 402, and 429 exceptions without blind retry loops.
- `tests/test_wordpress.py`:
  - Added `test_validate_site_alias` and `test_check_site_connectivity`.
- `tests/test_client.py`:
  - Added `test_request_retry_on_502_success`, `test_request_retry_exhausted_raises_api_error`, and `test_request_retry_on_network_connection_error`.

## Verification

Executed full test suite:
```bash
/Library/Frameworks/Python.framework/Versions/3.11/bin/pytest -o pythonpath=src
```
Result: All 32 unit tests passed in 0.21s.

## Next Step

Proceed to Wave 2: `02-02-PLAN.md` (Content Quality Pre-Validation and Execution Receipt Generation).
