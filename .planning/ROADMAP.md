# Roadmap: Katteb SEO Content Engine

## Completed Milestones
- **v1.0 — Hardened WordPress Fleet SEO Expansion Engine** (Phases 1–3, Shipped 2026-04-11) — See `.planning/milestones/v1.0-ROADMAP.md`
- **v2.0 — Omnichannel Localization, DAM Media & Closed-Loop SEO Engine** (Phases 4–7, Completed 2026-04-16) — See `.planning/milestones/v2.0-MILESTONE-AUDIT.md`

---

## Milestone v2.0: Omnichannel Localization, DAM Media & Closed-Loop SEO Engine

### Phase 4: Core Hygiene, Real Credit Telemetry & Safe Rollback
- **Status:** Complete (2026-04-16)
- **Requirements:** `CORE-01`, `CORE-02`, `CORE-03`, `CORE-04`
- **Plans:**
  - [x] `04-01`: Config consolidation (`pyproject.toml`), real `credits_charged` telemetry, and SEO concurrency polling (`poll_seo_until_complete`).
  - [x] `04-02`: Pre-mutation post backup snapshots, `katteb wp rollback-post`, `--stage-draft` safeguard, and `wp_admin_edit_url` output invariant.

### Phase 5: Multi-Language & Regional Idiom Adaptation
- **Status:** Complete (2026-04-16)
- **Requirements:** `LANG-01`, `LANG-02`, `LANG-03`
- **Plans:**
  - [x] `05-01`: Multi-language parameter resolution (`--language` CLI flag + site profile defaults), regional idiom/currency/metric prompt injection, multi-language quality gates, and Greece donkey ban.

### Phase 6: Authentic Media & TravelMediaDAM Integration
- **Status:** Complete (2026-04-16)
- **Requirements:** `MEDIA-01`, `MEDIA-02`, `MEDIA-03`
- **Plans:**
  - [x] `06-01`: `TravelMediaDAMResolver` (`src/katteb/dam.py`), SHA-256 deduplication, Greece donkey ban, two-phase `magick` + `exiftool` optimization (`< 1MB`), IPTC cleanliness, and semantic `<figure>` HTML injection.

### Phase 7: Autonomous CTR & Striking-Distance Feedback Loop
- **Status:** Complete (2026-04-16)
- **Requirements:** `FEED-01`, `FEED-02`, `FEED-03`
- **Plans:**
  - [x] `07-01`: `GSCFeedbackAuditor` (`src/katteb/gsc_feedback.py`), `katteb wp striking-distance`, `katteb wp audit-impact` 30-day impact correlation, and Activepieces `Content Refresh Queue` (`Sr3ff44M4Fs6PCGaDdSAG`) payload formatting.
