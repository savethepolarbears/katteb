# Katteb API v2 — CLI & Developer SDK

## What This Is

A developer toolkit, command-line interface, and Python SDK for the Katteb API v2. It empowers digital publishing fleets and AI coding agents to generate 500–5,000 word SEO-optimized articles across multiple languages, execute competitor on-page SEO audits, humanize AI-generated text, perform real-time web-search fact-checking, inject authentic local DAM travel photography, and automate high-scale WordPress post auditing, expansion, and GSC striking-distance re-audits via WP-CLI and `gog` with strict production safety gates and fleet observability.

## Current State

**Shipped Version:** v2.0 (Omnichannel Localization, DAM Media & Closed-Loop SEO Engine) — 2026-10-13  
**Previous Shipped Version:** v1.0 (Hardened Fleet Engine) — 2026-09-22  
**Test Suite:** 123 unit tests passing (`81.06%` line coverage across 10 test suites)  
**Nyquist Compliance:** 100% COMPLIANT  

## Core Value

Resilient, production-safe generation, multi-language localization, authentic media enrichment, and closed-loop SEO optimization of WordPress content across digital publishing fleets without crashing from concurrency lockouts (HTTP 429) or corrupting production databases with backend error payloads or unvetted output.

## Business Context

- **Customer**: Black Bear Media digital publishing properties (e.g., destinations.ai, viatravelers.com, santorinisecrets.com, everythingaboutgermany.com, lovinglifeinspain.com) and external developers using Katteb API v2.
- **Revenue model**: Organic search monetization (AdSense, display ads, affiliate conversions) driven by expanding thin content into high-ranking, media-rich, localized travel and gear guides.
- **Success metric**: 100% successful post expansions with zero production database regressions, 1-command rollback safety, authentic photo enrichment, and measurable GSC striking-distance uplift.
- **Strategy notes**: Core engine for Black Bear Media's omnichannel autonomous content pipeline.

## Requirements

### Milestone 2.0 Scope: Omnichannel Localization, DAM Media & Closed-Loop SEO Engine (13/13 Validated & Shipped)

- ✓ **CORE-01**: Unified pytest configuration in `pyproject.toml` (`pythonpath = ["src"]`), removal of shadowing `pytest.ini`, and cleanup of duplicate v1.0 planning artifacts
- ✓ **CORE-02**: Real `credits_charged` propagation from `ArticleGenerateResponse` through `KattebQueueManager` into `telemetry.py`, aggregating both `credits_used` and `estimated_credits`, plus failed expansion telemetry logging
- ✓ **CORE-03**: WordPress editorial draft safeguard (`--stage-draft`), canonical `wp_admin_edit_url` output, and pre-mutation rollback snapshots (`~/.katteb/backups/`) with `katteb wp rollback-post`
- ✓ **CORE-04**: `poll_seo_until_complete()` in `KattebClient` and `active_job_type == "seo"` 429 concurrency lockout routing in `KattebQueueManager`
- ✓ **LANG-01**: Enriched `FLEET_SITE_PROFILES` and `LOCALIZATION_PROFILES` with canonical `default_language`, `default_country`, and native regional idiom/terminology rules for German, Greek, Spanish, French, Dutch, and Italian fleet properties
- ✓ **LANG-02**: Multi-language expansion (`--language`, `--localize-idioms`) across `WordPressFleetManager`, CLI commands (`wp expand-post`, `wp batch-expand`), and `PipelineEventPayload`
- ✓ **LANG-03**: Multi-language AI-boilerplate detection and cultural guardrail validation in `validate_generated_content()` (including strict Greece donkey-transportation exclusion)
- ✓ **MEDIA-01**: `TravelMediaDAMResolver` (`src/katteb/dam.py`) querying authentic local fleet photography (`/Volumes/External-HD/TravelMediaDAM/locations/places.csv`) with SHA-256 deduplication and Greece donkey ban
- ✓ **MEDIA-02**: Two-phase local web optimization wrapping `magick` (`2048x2048>`, quality 82, progressive plane) and `exiftool` (clean IPTC creator `Kyle Kroeger` and copyright `© Kyle Kroeger`)
- ✓ **MEDIA-03**: Semantic `<figure>` HTML media injection in `expand_and_update_post()` (`--inject-dam-media`) and `katteb dam search` / `katteb dam optimize` CLI commands
- ✓ **FEED-01**: `GSCFeedbackAuditor` (`src/katteb/gsc_feedback.py`) wrapping `gog searchconsole` (`--client bbm-analytics-cloud`) to detect striking-distance queries (positions 4.0–15.0, impressions >= 50)
- ✓ **FEED-02**: 30-day post-publish expansion impact auditing (`audit_expanded_posts_impact()`) correlating `telemetry.jsonl` records against GSC metrics and logging `gsc_re_audit` telemetry
- ✓ **FEED-03**: `katteb wp striking-distance` and `katteb wp audit-impact` CLI commands and `gsc_striking_distance_audit` pipeline event dispatch

### Milestone 1.0 Hardened Fleet Engine Scope (13/13 Validated & Shipped)

- ✓ **TEST-01**: IP authorization guard intercepting 401 unauthorized errors with dashboard portal resolution links (`client.py`, `wordpress.py`)
- ✓ **TEST-02**: Payload error guard preventing short or non-HTML error payloads (< 400 chars) from corrupting WordPress database fields (`wordpress.py`)
- ✓ **TEST-03**: RankMath meta description sanitizer stripping inline `<style>` tags, scripts, and stray CSS rules (`wordpress.py`)
- ✓ **TEST-04**: Credit pooling model parsing and aliases (`available_credits`, `pool_credits`) (`models.py`)
- ✓ **TEST-05**: Queue concurrency 429 interception, polling, and serial submission (`queue.py`)
- ✓ **TEST-06**: Comprehensive test suite pass in local and CI environments (`tests/`)
- ✓ **BATCH-01**: Multi-site WordPress batch expansion orchestration with fleet profile registry and alias authorization (`wordpress.py`)
- ✓ **BATCH-02**: Exponential backoff retry policy with jitter for transient 5xx server errors and network connection drops (`client.py`)
- ✓ **BATCH-03**: Execution receipt generator writing timestamped markdown and JSON audit summaries (`expand-receipt-<timestamp>.md`)
- ✓ **BATCH-04**: Content quality gate enforcing visible-text word counts, DOM heading hierarchy, and extended placeholder token rejection (`wordpress.py`)
- ✓ **OPS-01**: Activepieces webhook trigger and headless pipeline dispatch interface (`katteb pipeline-dispatch`, `pipeline.py`)
- ✓ **OPS-02**: Account credit threshold alert trigger warning operators when credit pool falls below configurable threshold (exit code 2) (`telemetry.py`, `cli.py`)
- ✓ **OPS-03**: Structured JSONL logging telemetry (`~/.katteb/telemetry.jsonl`) with atomic file locking and stream aggregation (`telemetry.py`)

### Foundational SDK Features (Pre-existing Baseline)

- ✓ **AUTH-01**: Credential resolution hierarchy (explicit parameter > `KATTEB_API_KEY` env var > local `.env` > `~/.katteb/config.json` > `~/.env`)
- ✓ **CRED-01**: Credit and limit tracking (`katteb account credits`, `katteb account limits`)
- ✓ **GEN-01**: Long-form article generation (500–5,000 words) with structured enhancements (`tldr`, `key_takeaways`, `faq`)
- ✓ **QUEUE-01**: Smart concurrency queue manager (`KattebQueueManager`)
- ✓ **SEO-01**: On-page competitor SEO analysis via `katteb seo analyze`
- ✓ **HUMAN-01**: AI text detection and humanizer rewriting with strength levels and imperfection injection
- ✓ **FACT-01**: Web-search grounded claim verification via `katteb factcheck verify`
- ✓ **WP-01**: WordPress fleet post auditing for thin content (< 400 words) across custom post types
- ✓ **WP-02**: Destination CPT enrichment updating `post_content`, Pods `travel_guide`, and RankMath SEO metadata
- ✓ **CLI-01**: Dual-mode terminal output: Rich interactive visual tables vs machine-readable `--json` format

### Out of Scope

- Direct database SQL mutations to WordPress — all WordPress writes must strictly route through validated WP-CLI commands (`wp-global`).
- GUI desktop application — CLI and Python SDK are the primary interaction surfaces.
- Multi-threaded bypass of Katteb concurrency locks — Katteb enforces a strict 1-heavy-job server limit; client-side concurrency must poll and queue cleanly rather than spamming requests.

## Context

- **Technical Environment**: Python 3.10+ package built with Hatchling, Pydantic v2 data models, Click CLI, Rich terminal styling, BeautifulSoup4 HTML DOM processing, and Requests HTTP client.
- **Ecosystem**: Runs in headless automation scripts, Activepieces / Make workflows, CI/CD runners, and local developer environments alongside `wp-global`, `magick`, `exiftool`, and `gog`.
- **WordPress Architecture**: Integrates with standard WordPress core (`wp_posts`), Pods Framework custom fields, and RankMath SEO meta tags.

## Constraints

- **Language & Runtime**: Python >= 3.10 required for modern type hinting and Pydantic v2 compatibility.
- **Katteb Concurrency Ceiling**: Strict 1-active-heavy-job limit on Katteb API v2 endpoints; heavy tasks must be queued sequentially or polled.
- **Egress IP Whitelisting**: Katteb API v2 requires explicit egress IP authorization via operator dashboard.
- **Zero-Dependency Core Policy**: SDK core dependencies must remain lean (`requests`, `pydantic`, `click`, `rich`, `python-dotenv`, `beautifulsoup4`).

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Pydantic v2 for data schemas | Enforces strict validation, alias generators (`available_credits`, `pool_credits`), and fast deserialization | ✓ Good |
| Queue Manager over raw HTTP retries | Intercepts 429 responses specifically, parses active job IDs, and polls gracefully without hitting rate limit bans | ✓ Good |
| WP-CLI wrapper over XML-RPC/REST | Executes natively with site aliases on target WordPress servers without exposing external endpoints or requiring separate auth tokens | ✓ Good |
| Dual Rich/JSON CLI formatters | Humans get styled terminal cards; agentic systems and CI get deterministic JSON payloads | ✓ Good |
| Site alias regex whitelist | Enforces alphanumeric/dash/dot patterns to prevent shell injection vulnerabilities in WP-CLI execution | ✓ Good |
| Exponential backoff with jitter on 5xx | Automatically retries transient cloud errors while preserving discrete 401/402/429 exception paths | ✓ Good |
| Content quality pre-validation | Rejects malformed headings and unreplaced placeholders via `ContentQualityError` before committing WP updates | ✓ Good |
| Stdin/Stdout JSON pipeline dispatch | Standardizes headless Activepieces / automation invocation without terminal formatting interference | ✓ Good |
| Exit code 2 on credit alerts | Enables native conditional branch routing in Activepieces and CI monitoring workflows | ✓ Good |
| Graphify Knowledge Graph in `.planning/graphs/` | Enables instant AST and community-based navigation across the codebase | ✓ Good |
| Pre-mutation JSON rollback snapshots & `--stage-draft` | Protects live WordPress content with 1-command rollback (`katteb wp rollback-post`) and editorial draft staging | ✓ Good |
| Local DAM curation before AI image generation | Prioritizes authentic travel photography (`TravelMediaDAM`) with `magick` + `exiftool` optimization and Greece donkey ban | ✓ Good |
| Closed-loop GSC striking-distance auditing via `gog` | Connects `telemetry.jsonl` expansion history with live Google Search Console query performance | ✓ Good |

---
*Last updated: 2026-10-13 for Milestone v2.0*
