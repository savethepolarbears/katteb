# Requirements: Katteb API v2 — CLI & Developer SDK (Milestone v2.0)

**Milestone:** v2.0 — Omnichannel Localization, DAM Media & Closed-Loop SEO Engine  
**Status:** Active  
**Core Value:** Resilient, production-safe generation, multi-language localization, authentic media enrichment, and closed-loop GSC striking-distance optimization across Black Bear Media's digital publishing fleet.

---

## Scoped Requirements (Milestone v2.0)

### Phase 4: Core Hygiene, Telemetry Accuracy & Editorial Rollback Guards
- [ ] **CORE-01**: Unify pytest configuration in `pyproject.toml` (`pythonpath = ["src"]`), remove shadowing `pytest.ini`, and purge duplicate v1.0 phase/audit files from `.planning/`.
- [ ] **CORE-02**: Propagate real `credits_charged` from `ArticleGenerateResponse` through `KattebQueueManager` into `ArticleGetResponse` and `telemetry.py`, aggregate both `credits_used` and `estimated_credits`, and record failed expansion runs (`success=False`) in telemetry.
- [ ] **CORE-03**: Enforce editorial publishing safeguards in `WordPressFleetManager.expand_and_update_post()` — write pre-mutation JSON rollback snapshots (`~/.katteb/backups/`), add `katteb wp rollback-post`, support `--stage-draft` (`post_status="draft"`), and emit `wp_admin_edit_url` (`https://<domain>/wp-admin/post.php?post=<id>&action=edit`).
- [ ] **CORE-04**: Add `poll_seo_until_complete()` to `KattebClient` and route `active_job_type == "seo"` 429 concurrency lockouts in `KattebQueueManager` to SEO job polling.

### Phase 5: Multi-Language & Localized Idiom Adaptation
- [ ] **LANG-01**: Enrich `FLEET_SITE_PROFILES` and define `LOCALIZATION_PROFILES` with canonical `default_language`, `default_country`, and native regional idiom/terminology rules for German, Greek, Spanish, French, Dutch, and Italian fleet properties.
- [ ] **LANG-02**: Support `--language` and `--localize-idioms` across `WordPressFleetManager.expand_and_update_post()`, CLI commands (`wp expand-post`, `wp batch-expand`), and `PipelineEventPayload`, replacing hardcoded `language="English"` with site-aware localization.
- [ ] **LANG-03**: Upgrade `validate_generated_content()` with multi-language AI-boilerplate rejection and cultural guardrail enforcement (strictly banning any depiction or recommendation of donkey riding or luggage transit in Greece/Santorini).

### Phase 6: Authentic Media DAM Integration
- [ ] **MEDIA-01**: Implement `TravelMediaDAMResolver` (`src/katteb/dam.py`) to query authentic local fleet photography from `/Volumes/External-HD/TravelMediaDAM/locations/places.csv` (or configurable catalog path) by destination (`city`, `region`, `country`, `topic`), enforcing SHA-256/stem deduplication and Greece donkey-transportation exclusion.
- [ ] **MEDIA-02**: Implement two-phase local web optimization in `src/katteb/dam.py` wrapping `magick` (`2048x2048>`, 4:2:0, strip, quality 82, progressive plane) and `exiftool` (clean IPTC creator `Kyle Kroeger`, copyright `© Kyle Kroeger`, and location metadata).
- [ ] **MEDIA-03**: Integrate authentic media selection and semantic `<figure>` HTML injection into `WordPressFleetManager.expand_and_update_post()` (`--inject-dam-media`, `--dam-catalog`, `--max-images`) and add `katteb dam search` and `katteb dam optimize` CLI commands.

### Phase 7: Autonomous CTR & Striking-Distance Feedback Loop
- [ ] **FEED-01**: Implement `GSCFeedbackAuditor` (`src/katteb/gsc_feedback.py`) wrapping `gog searchconsole` (`--client bbm-analytics-cloud --json --results-only --no-input`) to query search analytics and detect striking-distance queries (positions `4.0`–`15.0`, impressions `>= 50` over trailing 28 days).
- [ ] **FEED-02**: Implement 30-day post-publish expansion impact auditing (`audit_expanded_posts_impact()`) correlating `post_expansion` telemetry records against GSC performance metrics and logging `gsc_re_audit` telemetry events.
- [ ] **FEED-03**: Expose `katteb wp striking-distance` and `katteb wp audit-impact` CLI commands and extend `process_pipeline_event()` to support `gsc_striking_distance_audit` automation events.

---

## Traceability Matrix

| Requirement ID | Phase | Category | Status |
|---|---|---|---|
| `CORE-01` | Phase 4 | Hygiene & Config | Pending |
| `CORE-02` | Phase 4 | Telemetry Accuracy | Pending |
| `CORE-03` | Phase 4 | Editorial Safeguards & Rollback | Pending |
| `CORE-04` | Phase 4 | Queue Concurrency | Pending |
| `LANG-01` | Phase 5 | Localization Profiles | Pending |
| `LANG-02` | Phase 5 | Multi-Language Expansion | Pending |
| `LANG-03` | Phase 5 | Cultural & Quality Guards | Pending |
| `MEDIA-01` | Phase 6 | DAM Discovery & Curation | Pending |
| `MEDIA-02` | Phase 6 | Image Optimization & IPTC | Pending |
| `MEDIA-03` | Phase 6 | Content Injection & CLI | Pending |
| `FEED-01` | Phase 7 | GSC Striking-Distance Detector | Pending |
| `FEED-02` | Phase 7 | 30-Day Re-Audit Telemetry | Pending |
| `FEED-03` | Phase 7 | Closed-Loop CLI & Pipeline | Pending |
