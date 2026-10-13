---
phase: 04-core-hygiene-telemetry-rollback
plan: 02
subsystem: wordpress-backup-rollback
tags: [wordpress, backup, rollback, stage-draft, editorial-safeguard]
requires:
  - 04-01
provides:
  - "Pre-mutation JSON backup snapshots in ~/.katteb/backups/ (save_post_backup_snapshot)"
  - "WordPressFleetManager.rollback_post() and `katteb wp rollback-post` CLI command"
  - "Draft staging mode (--stage-draft / stage_draft=True) preserving canonical slugs and dates"
  - "Canonical WP Admin review links (get_wp_admin_edit_url) in CLI, SDK, and pipeline responses"
affects:
  - src/katteb/wordpress.py
  - src/katteb/pipeline.py
  - src/katteb/cli.py
completed: 2026-10-13
---

# Phase 4 Plan 02 Summary: Pre-Mutation Post Backup, Rollback & Draft Staging Safeguard

## Accomplishments
- **CORE-04**:
  - Added `get_wp_admin_edit_url(site, post_id)` returning `https://<domain>/wp-admin/post.php?post=<id>&action=edit`.
  - Added `save_post_backup_snapshot(site, post_details, backup_dir=None)` capturing original `post_content`, `title`, `status`, `slug`, and RankMath/ACF `meta` before any WordPress update.
  - Added `WordPressFleetManager.rollback_post()` and `katteb wp rollback-post --site <site> --snapshot <path>` to restore a post to its pre-expansion state.
  - Added `stage_draft: bool = False` (`--stage-draft`) across `expand_and_update_post()`, `wp expand-post`, `wp batch-expand`, and `pipeline-dispatch`.
