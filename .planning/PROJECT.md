# Katteb API v2 — CLI & Developer SDK

## What This Is

A developer toolkit, command-line interface, and Python SDK for the Katteb API v2. It empowers digital publishing fleets and AI coding agents to generate 500–5,000 word SEO-optimized articles, execute competitor on-page SEO audits, humanize AI-generated text, perform real-time web-search fact-checking, and automate high-scale WordPress post auditing and expansion via WP-CLI with strict production safety gates and fleet observability.

## Current State

**Shipped Version:** v1.0 (Hardened Fleet Engine) — 2026-09-22  
**Test Suite:** 56 unit tests passing in 0.19s  
**Nyquist Compliance:** 100% COMPLIANT across all 3 phases  

## Core Value

Resilient, production-safe generation and bulk enrichment of WordPress content across digital publishing fleets without crashing from concurrency lockouts (HTTP 429) or corrupting production databases with backend error payloads or unvetted output.

## Business Context

- **Customer**: Black Bear Media digital publishing properties (e.g., destinations.ai, viatravelers.com, santorinisecrets.com) and external developers using Katteb API v2.
- **Revenue model**: Organic search monetization (AdSense, display ads, affiliate conversions) driven by expanding thin content into high-ranking, rich travel and gear guides.
- **Success metric**: 100% successful post expansions with zero production database regressions or malformed HTML writes.
- **Strategy notes**: Core engine for Black Bear Media's omnichannel autonomous content pipeline.

## Requirements

### Validated in v1.0

- ✓ **AUTH-01**: Credential resolution hierarchy (explicit parameter > `KATTEB_API_KEY` env var > `~/.katteb/config.json` > local `.env`)
- ✓ **CRED-01**: Credit and limit tracking (`katteb account credits`, `katteb account limits`) with credit pooling support (`pool_credits`, `available_credits`)
- ✓ **GEN-01**: Long-form article generation (500–5,000 words) with structured enhancements (`tldr`, `key_takeaways`, `faq`, `featured_image`, `internal_links`)
- ✓ **QUEUE-01**: Smart concurrency queue manager (`KattebQueueManager`) automatically intercepting HTTP 429 lockouts, polling running jobs until completion, and submitting queued requests
- ✓ **SEO-01**: On-page competitor SEO analysis via `katteb seo analyze`
- ✓ **HUMAN-01**: AI text detection and humanizer rewriting with strength levels and imperfection injection
- ✓ **FACT-01**: Web-search grounded claim verification via `katteb factcheck verify`
- ✓ **WP-01**: WordPress fleet post auditing for thin content (< 400 words) across custom post types (`destinations`, `post`, `gear`, `restaurant`) via WP-CLI
- ✓ **WP-02**: Destination CPT enrichment updating `post_content`, Pods `travel_guide`, and RankMath SEO metadata
- ✓ **GUARD-01**: Egress IP authorization guard intercepting 401 unauthorized errors with dashboard portal resolution links (`TEST-01`)
- ✓ **GUARD-02**: Payload error guard preventing short error payloads (< 400 chars) from corrupting WordPress database fields (`TEST-02`)
- ✓ **GUARD-03**: RankMath meta description sanitizer stripping inline `<style>` tags and stray CSS classes (`TEST-03`)
- ✓ **CLI-01**: Dual-mode terminal output: Rich interactive visual tables vs machine-readable `--json` format
- ✓ **BATCH-01**: Multi-site WordPress batch expansion orchestration with configurable site aliases and shell-injection whitelist
- ✓ **BATCH-02**: Exponential backoff retry policy with jitter for transient 5xx server errors and network connection drops
- ✓ **BATCH-03**: Execution receipt generator writing timestamped markdown audit summaries (`expand-receipt-<timestamp>.md`)
- ✓ **BATCH-04**: Content quality validator ensuring minimum H2/H3 heading hierarchy and rejecting unreplaced placeholder tokens
- ✓ **OPS-01**: Activepieces webhook trigger / CLI integration interface for event-driven post expansions (`katteb pipeline-dispatch`)
- ✓ **OPS-02**: Account credit threshold alert trigger warning operators when credit pool falls below configurable threshold (exit code 2)
- ✓ **OPS-03**: Structured JSONL logging telemetry (`~/.katteb/telemetry.jsonl`) for integration into central fleet observability dashboards

### Next Milestone Goals (v2.0)

- [ ] **LANG-01**: Automatic language translation and localized idiom adaptation for German, Greek, and Spanish fleet sites.
- [ ] **MEDIA-01**: Integration with local media asset DAM (`/Volumes/External-HD/TravelMediaDAM`) to automatically select and inject authentic photography into generated posts.
- [ ] **FEED-01**: Automated re-audit of expanded posts 30 days post-publish comparing GSC rankings and CTR striking distance performance.

### Out of Scope

- Direct database SQL mutations to WordPress — all WordPress writes must strictly route through validated WP-CLI commands (`wp-global`).
- GUI desktop application — CLI and Python SDK are the primary interaction surfaces.
- Multi-threaded bypass of Katteb concurrency locks — Katteb enforces a strict 1-heavy-job server limit; client-side concurrency must poll and queue cleanly rather than spamming requests.

## Context

- **Technical Environment**: Python 3.10+ package built with Hatchling, Pydantic v2 data models, Click CLI, Rich terminal styling, and Requests HTTP client.
- **Ecosystem**: Runs in headless automation scripts, Activepieces / Make workflows, CI/CD runners, and local developer environments.
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
| Graphify Knowledge Graph in `.planning/graphs/` | Enables instant AST and community-based navigation across 518 nodes and 33 communities | ✓ Good |

---
*Last updated: 2026-09-22 upon Milestone 1.0 Completion*
