# Requirements: Katteb API v2 CLI & Developer SDK

**Defined:** 2026-09-21
**Core Value:** Resilient, production-safe generation and bulk enrichment of WordPress content across digital publishing fleets without crashing from concurrency lockouts or corrupting production databases.

## v1 Requirements

Requirements for active milestone. Each maps directly to roadmap phases.

### Phase 1: Guard Hardening & Test Verification

- [x] **TEST-01**: Complete unit test coverage for `WordPressFleetManager` IP authorization guard (HTTP 401 intercept and portal guidance).
- [x] **TEST-02**: Complete unit test coverage for `WordPressFleetManager` payload error guard (rejecting short/error payloads < 400 chars).
- [x] **TEST-03**: Complete unit test coverage for `WordPressFleetManager` RankMath meta description sanitizer (stripping inline `<style>` and CSS selectors).
- [x] **TEST-04**: Test coverage for `AccountCreditsResponse` model parsing with credit pooling and available credits field aliases.
- [x] **TEST-05**: Test coverage for `KattebQueueManager` handling immediate job success and concurrency 429 lockouts.
- [x] **TEST-06**: Verification that all 27 unit tests pass cleanly in local and CI environments.

### Phase 2: Fleet Batch Expansion & Quality Gates

- [x] **BATCH-01**: Multi-site target support in batch expansion command (`--site` selector with fallback profile validation).
- [x] **BATCH-02**: Exponential backoff and retry policy when Katteb API returns intermittent 5xx or connection drops during long-running batch jobs.
- [x] **BATCH-03**: Execution receipt generator writing markdown audit summaries (`expand-receipt-<timestamp>.md`) detailing affected post IDs, word counts, and modified custom fields.
- [x] **BATCH-04**: Content quality validator ensuring generated content adheres to minimum H2/H3 heading hierarchy and contains no hallucinated placeholder tokens before WP update.

### Phase 3: Omnichannel Pipeline Integration & Telemetry

- [x] **OPS-01**: Activepieces webhook trigger / CLI integration interface for event-driven post expansions.
- [x] **OPS-02**: Account credit threshold alert trigger warning operators when credit pool falls below configurable threshold.
- [x] **OPS-03**: Structured JSON logging telemetry for integration into central fleet observability dashboards.

## v2 Requirements

Deferred to future releases.

### Advanced Formatting & Multi-Language
- **LANG-01**: Automatic language translation and localized idiom adaptation for German, Greek, and Spanish fleet sites.
- **MEDIA-01**: Integration with local media asset DAM (`/Volumes/External-HD/TravelMediaDAM`) to automatically select and inject authentic photography into generated posts.

### Autonomous SEO Feedback Loop
- **FEED-01**: Automated re-audit of expanded posts 30 days post-publish comparing GSC rankings and CTR striking distance performance.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Direct MySQL/MariaDB database access | High risk of schema drift or cache inconsistency; all WordPress persistence must execute through WP-CLI |
| Native Desktop GUI application | Unnecessary overhead; CLI and Python SDK are designed for automation and developer workflows |
| Multi-threaded bypass of Katteb concurrency | Violates Katteb API v2 server restrictions; queuing and polling must be strictly adhered to |

## Traceability

Which phases cover which requirements.

| Requirement | Phase | Status |
|-------------|-------|--------|
| TEST-01 | Phase 1: Guard Hardening & Test Verification | Complete |
| TEST-02 | Phase 1: Guard Hardening & Test Verification | Complete |
| TEST-03 | Phase 1: Guard Hardening & Test Verification | Complete |
| TEST-04 | Phase 1: Guard Hardening & Test Verification | Complete |
| TEST-05 | Phase 1: Guard Hardening & Test Verification | Complete |
| TEST-06 | Phase 1: Guard Hardening & Test Verification | Complete |
| BATCH-01 | Phase 2: Fleet Batch Expansion & Quality Gates | Complete |
| BATCH-02 | Phase 2: Fleet Batch Expansion & Quality Gates | Complete |
| BATCH-03 | Phase 2: Fleet Batch Expansion & Quality Gates | Complete |
| BATCH-04 | Phase 2: Fleet Batch Expansion & Quality Gates | Complete |
| OPS-01 | Phase 3: Omnichannel Pipeline Integration & Telemetry | Complete |
| OPS-02 | Phase 3: Omnichannel Pipeline Integration & Telemetry | Complete |
| OPS-03 | Phase 3: Omnichannel Pipeline Integration & Telemetry | Complete |

**Coverage:**
- v1 requirements: 13 total
- Mapped to phases: 13
- Unmapped: 0 ✓

---
*Requirements defined: 2026-09-21*
*Last updated: 2026-09-21 after initialization*
