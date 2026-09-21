# Roadmap: Katteb API v2 — CLI & Developer SDK

## Overview

This roadmap defines the transition of the Katteb toolkit from initial v1 implementation into an enterprise-grade, hardened content enrichment engine for Black Bear Media's digital publishing fleet.

## Phases

- [x] **Phase 1: Guard Hardening & Test Verification** - Comprehensive unit test suites validating production safety guards and concurrency queue.
- [x] **Phase 2: Fleet Batch Expansion & Quality Gates** - Multi-site batch expansion workflows with backoff retries, content quality gates, and execution audit receipts.
- [x] **Phase 3: Omnichannel Pipeline Integration & Telemetry** - Activepieces automation bridges, credit depletion threshold alerts, and observability metrics.

## Phase Details

### Phase 1: Guard Hardening & Test Verification
**Goal**: Ensure 100% test coverage and resilience across IP authorization guards, payload error guards, meta description sanitizers, and credit pooling models.
**Mode**: mvp
**Depends on**: Nothing (baseline)
**Requirements**: [TEST-01, TEST-02, TEST-03, TEST-04, TEST-05, TEST-06]
**Success Criteria** (what must be TRUE):
  1. IP authorization guard prevents unhandled crashes on 401 and outputs clear egress IP setup guidance.
  2. Short error payloads (< 400 chars) are intercepted and rejected before mutating WordPress post content.
  3. Inline `<style>` blocks and CSS class selectors are stripped cleanly from RankMath meta descriptions.
  4. Credit pool responses correctly parse both `available_credits` and `pool_credits` aliases.
  5. All 27 unit tests pass cleanly in pytest.
**Plans**: 1 plan

Plans:
- [x] 01-01: Implement and verify comprehensive unit test suite covering guards, queue, and model parsing.

---

### Phase 2: Fleet Batch Expansion & Quality Gates
**Goal**: Automate robust, hands-off batch expansions across multiple WordPress fleet sites with resilient error handling and audit receipts.
**Mode**: mvp
**Depends on**: Phase 1
**Requirements**: [BATCH-01, BATCH-02, BATCH-03, BATCH-04]
**Success Criteria** (what must be TRUE):
  1. Operators can target distinct fleet sites via `--site <site-key>` with automatic profile validation.
  2. Transient network and 5xx API errors trigger exponential backoff without aborting the entire batch run.
  3. Every batch expansion outputs a persistent Markdown audit receipt (`expand-receipt-<timestamp>.md`).
  4. Content validator catches and rejects malformed headings or placeholder tokens before persistence.
**Plans**: 2 plans

Plans:
- [x] 02-01: Multi-site configuration profiles and exponential backoff retry handler.
- [x] 02-02: Content quality pre-validation and execution receipt generation.

---

### Phase 3: Omnichannel Pipeline Integration & Telemetry
**Goal**: Expose Katteb operations to autonomous workflow orchestration engines (Activepieces) and provide fleet-wide credit monitoring.
**Mode**: mvp
**Depends on**: Phase 2
**Requirements**: [OPS-01, OPS-02, OPS-03]
**Success Criteria** (what must be TRUE):
  1. Katteb CLI can be invoked or called via standard JSON stdin/stdout by Activepieces and external agent workflows.
  2. Credit balance checks trigger alerts when total available pooled credits drop below a configured safety threshold.
  3. Structured JSON logs are emitted for tracking total words generated, duration, and credit consumption per site.
**Plans**: 2 plans

Plans:
- [x] 03-01: Activepieces gateway integration and webhook payload adapters.
- [x] 03-02: Credit threshold monitoring and telemetry reporting.

---

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Guard Hardening & Test Verification | 1/1 | Complete | 2026-09-21 |
| 2. Fleet Batch Expansion & Quality Gates | 2/2 | Complete | 2026-09-21 |
| 3. Omnichannel Pipeline Integration & Telemetry | 2/2 | Complete | 2026-09-21 |
