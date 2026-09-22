---
phase: 02-fleet-batch-expansion-quality-gates
plan: 02
title: Content Quality Pre-Validation and Execution Receipt Generation
subsystem: wordpress,cli
tags: [wordpress, quality, validation, receipts, cli]
duration: 10m
---

# Plan 02-02 Summary: Content Quality Pre-Validation & Execution Receipts

## Objective Completed

Delivered rigorous pre-validation quality gates and execution audit receipt generation for WordPress content expansion:
1. Created `ContentQualityError` custom exception to cleanly differentiate content quality defects from API/network/WP-CLI errors.
2. Implemented `validate_generated_content()` enforcing heading hierarchy rules (H2/H3 requirements), detecting unreplaced template tokens (`[City]`, `[Insert]`, `[TODO]`), flagging LLM canned intros ("As an AI language model"), and verifying target word counts.
3. Integrated quality validation directly into `WordPressFleetManager.expand_and_update_post()` before committing updates to WordPress.
4. Implemented `generate_expansion_receipt()` generating timestamped, structured Markdown execution receipts with run summaries, quality gate status, and per-post audit tables.
5. Enhanced `katteb wp-batch-expand` CLI with `--receipt-dir` to persist execution receipts to disk upon completing batch operations.
6. Authored comprehensive unit tests covering all quality gate validation scenarios and receipt formatting.

## Key Changes

- `src/katteb/wordpress.py`:
  - Added `ContentQualityError` exception class.
  - Added `validate_generated_content(html, target_word_count)` with heading hierarchy and placeholder pattern matching.
  - Integrated `validate_generated_content` into `expand_and_update_post()`.
  - Added `generate_expansion_receipt(site, results, output_dir)` creating structured Markdown audit receipts.
- `src/katteb/cli.py`:
  - Added `--receipt-dir` option to `wp_batch_expand` command.
  - Wired `generate_expansion_receipt()` into batch completion logic.
- `tests/test_wordpress.py`:
  - Updated `test_meta_description_sanitizer` mock payload to satisfy H2/H3 validation rules.
  - Added `test_validate_generated_content_valid`.
  - Added `test_validate_generated_content_missing_headings`.
  - Added `test_validate_generated_content_placeholders`.
  - Added `test_expand_post_raises_content_quality_error`.
  - Added `test_generate_expansion_receipt`.

## Verification

Executed full test suite:
```bash
/Library/Frameworks/Python.framework/Versions/3.11/bin/pytest -o pythonpath=src
```
Result: All 37 unit tests passed in 0.15s.

## Phase 2 Completion

With Plans 02-01 and 02-02 fully implemented and validated:
- Multi-site fleet profiles and sanitized alias targeting are in place (`BATCH-01`).
- Exponential backoff retry logic handles transient 5xx / connection drops (`BATCH-02`).
- Content quality validation rejects degraded or unreplaced template output (`BATCH-03`).
- Execution audit receipts provide durable operational records for batch runs (`BATCH-04`).
