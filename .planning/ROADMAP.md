# Roadmap: Katteb API v2 — CLI & Developer SDK

## Milestones

<details>
<summary><b>Milestone v1.0: Hardened Fleet Engine</b> — ✅ SHIPPED 2026-09-22</summary>

Full phase details archived at [.planning/milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md).  
Audit report: [.planning/milestones/v1.0-MILESTONE-AUDIT.md](milestones/v1.0-MILESTONE-AUDIT.md).

- [x] **Phase 1: Guard Hardening & Test Verification** (1/1 plans complete) — Shipped 2026-09-21
- [x] **Phase 2: Fleet Batch Expansion & Quality Gates** (2/2 plans complete) — Shipped 2026-09-21
- [x] **Phase 3: Omnichannel Pipeline Integration & Telemetry** (2/2 plans complete) — Shipped 2026-09-21
</details>

---

## Active Milestone: v2.0 — Omnichannel Localization, DAM Media & Closed-Loop SEO Engine

**Goal:** Evolve Katteb from a single-language text expansion utility into an omnichannel, multi-language, media-enriched, and self-auditing SEO growth engine for Black Bear Media's 15 publishing properties.

### Phase 4: Core Hygiene, Telemetry Accuracy & Editorial Rollback Guards
**Goal**: Eliminate planning/test configuration drift, propagate real credit billing and failure metrics into telemetry, support SEO queue polling, and enforce WordPress draft staging and pre-mutation rollback snapshots.  
**Depends on**: Milestone v1.0  
**Requirements**: `CORE-01`, `CORE-02`, `CORE-03`, `CORE-04`  
**Plans**: 2 plans

Plans:
- [ ] 04-01: Repository hygiene, pytest config unification, SEO queue polling, and telemetry credit/failure accuracy.
- [ ] 04-02: WordPress editorial draft safeguard (`--stage-draft`), WP Admin review links, and pre-mutation backup/rollback (`katteb wp rollback-post`).

### Phase 5: Multi-Language & Localized Idiom Adaptation
**Goal**: Enable native multi-language content generation and localized cultural idiom adaptation across German, Greek, Spanish, French, Dutch, and Italian fleet properties with cultural safety gates.  
**Depends on**: Phase 4  
**Requirements**: `LANG-01`, `LANG-02`, `LANG-03`  
**Plans**: 1 plan

Plans:
- [ ] 05-01: Fleet localization profiles, idiom-aware expansion prompts, multi-language CLI/pipeline flags, and cultural quality gates (including Greece donkey-transportation ban).

### Phase 6: Authentic Media DAM Integration
**Goal**: Connect Katteb post expansions to the local TravelMediaDAM archive (`/Volumes/External-HD/TravelMediaDAM`), automating authentic photo selection, SHA-256 deduplication, local ImageMagick/ExifTool optimization, and semantic HTML `<figure>` embedding.  
**Depends on**: Phase 5  
**Requirements**: `MEDIA-01`, `MEDIA-02`, `MEDIA-03`  
**Plans**: 1 plan

Plans:
- [ ] 06-01: `TravelMediaDAMResolver`, two-phase `magick` + `exiftool` web compression, semantic `<figure>` post injection, and `katteb dam` CLI commands.

### Phase 7: Autonomous CTR & Striking-Distance Feedback Loop
**Goal**: Close the SEO optimization loop by querying Google Search Console via `gog searchconsole` (`--client bbm-analytics-cloud`) to identify striking-distance posts (positions 4.0–15.0, impressions >= 50) and evaluate 30-day post-expansion ranking uplift.  
**Depends on**: Phase 6  
**Requirements**: `FEED-01`, `FEED-02`, `FEED-03`  
**Plans**: 1 plan

Plans:
- [ ] 07-01: `GSCFeedbackAuditor`, striking-distance query detector, 30-day telemetry correlation re-audit, and `katteb wp striking-distance` / `audit-impact` CLI & pipeline commands.
