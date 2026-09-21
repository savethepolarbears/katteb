# Katteb API v2 — CLI & Developer SDK

## What This Is

A developer toolkit, command-line interface, and Python SDK for the Katteb API v2. It empowers digital publishing fleets and AI coding agents to generate 500–5,000 word SEO-optimized articles, execute competitor on-page SEO audits, humanize AI-generated text, perform real-time web-search fact-checking, and automate high-scale WordPress post auditing and expansion via WP-CLI with strict production safety guards.

## Core Value

Resilient, production-safe generation and bulk enrichment of WordPress content across digital publishing fleets without crashing from concurrency lockouts (HTTP 429) or corrupting production databases with backend error payloads or unvetted output.

## Business Context

- **Customer**: Black Bear Media digital publishing properties (e.g., destinations.ai, viatravelers.com, santorinisecrets.com) and external developers using Katteb API v2.
- **Revenue model**: Organic search monetization (AdSense, display ads, affiliate conversions) driven by expanding thin content into high-ranking, rich travel and gear guides.
- **Success metric**: 100% successful post expansions with zero production database regressions or malformed HTML writes.
- **Strategy notes**: Integral component of Black Bear Media's omnichannel autonomous content pipeline.

## Requirements

### Validated

- ✓ **AUTH-01**: Credential resolution hierarchy (explicit parameter > `KATTEB_API_KEY` env var > `~/.katteb/config.json` > local `.env`) — v1.0
- ✓ **CRED-01**: Credit and limit tracking (`katteb account credits`, `katteb account limits`) with credit pooling support (`pool_credits`, `available_credits`) — v1.0
- ✓ **GEN-01**: Long-form article generation (500–5,000 words) with structured enhancements (`tldr`, `key_takeaways`, `faq`, `featured_image`, `internal_links`) — v1.0
- ✓ **QUEUE-01**: Smart concurrency queue manager (`KattebQueueManager`) automatically intercepting HTTP 429 lockouts, polling running jobs until completion, and submitting queued requests — v1.0
- ✓ **SEO-01**: On-page competitor SEO analysis via `katteb seo analyze` — v1.0
- ✓ **HUMAN-01**: AI text detection and humanizer rewriting with strength levels and imperfection injection — v1.0
- ✓ **FACT-01**: Web-search grounded claim verification via `katteb factcheck verify` — v1.0
- ✓ **WP-01**: WordPress fleet post auditing for thin content (< 400 words) across custom post types (`destinations`, `post`, `gear`, `restaurant`) via WP-CLI — v1.0
- ✓ **WP-02**: Destination CPT enrichment updating `post_content`, Pods `travel_guide`, and RankMath SEO metadata — v1.0
- ✓ **GUARD-01**: Egress IP authorization guard intercepting 401 unauthorized errors with dashboard portal resolution links — v1.0
- ✓ **GUARD-02**: Payload error guard preventing short error payloads (< 400 chars) from corrupting WordPress database fields — v1.0
- ✓ **GUARD-03**: RankMath meta description sanitizer stripping inline `<style>` tags and stray CSS classes — v1.0
- ✓ **CLI-01**: Dual-mode terminal output: Rich interactive visual tables vs machine-readable `--json` format — v1.0

### Active

- [ ] **TEST-01**: Comprehensive end-to-end unit and regression test suite validation across all guard rails, queue handlers, and model aliases
- [ ] **BATCH-01**: Multi-site WordPress batch expansion orchestration with configurable retry-backoff policies and execution receipts
- [ ] **OPS-01**: Webhook/Activepieces integration bridge exposing Katteb operations to external agent pipelines and credit depletion threshold alerts

### Out of Scope

- Direct database SQL mutations to WordPress — all WordPress writes must strictly route through validated WP-CLI commands (`wp-global`).
- GUI desktop application — CLI and Python SDK are the primary interaction surfaces.
- Multi-threaded bypass of Katteb concurrency locks — Katteb enforces a strict 1-heavy-job server limit; client-side concurrency must poll and queue cleanly rather than spamming requests.

## Context

- **Technical Environment**: Python 3.10+ package built with Hatchling, Pydantic v2 data models, Click CLI, Rich terminal styling, and Requests HTTP client.
- **Ecosystem**: Runs in headless automation scripts, CI/CD runners, and local developer environments across macOS and Linux.
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
| Graphify Knowledge Graph in `.planning/graphs/` | Enables instant AST and community-based navigation across modules, god nodes, and inter-dependencies | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `$gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `$gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-09-21 after initialization*
