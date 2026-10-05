# WordPress Fleet Integration Guide

The Katteb toolkit includes deep integration with the Black Bear Media WordPress fleet via WP-CLI (`scripts/wp-cli/wp-global`).

## Supported Post Types & Field Mappings

### 1. `destinations` Custom Post Type (e.g. `destinations.ai`)
- **Source Post Data:**
  - Extracts title, slug, city (`city` / `city_name`), state (`state_name_full`), country (`country`), region (`region`).
  - Maps country name to ISO 3166-1 alpha-2 code (e.g. India ➔ `in`, Switzerland ➔ `ch`).
- **Target Generation Topic:**
  - `Complete Travel Guide to {City}, {Country}: Best Things to Do, Itinerary, and Local Guide`
- **Updated Fields in WordPress:**
  1. `post_content` — Updated with structured HTML (H2s, H3s, itineraries, local secrets, practical tips, FAQ).
  2. `travel_guide` (Pods paragraph field) — Updated to match rich guide content.
  3. `rank_math_title` — Updated to optimized high-CTR title.
  4. `rank_math_description` — Updated to Katteb's generated meta description (150–160 chars).
  5. `rank_math_focus_keyword` — Target city name.

### 2. Standard `post` Editorial Articles
- **Source Post Data:**
  - Extracts title, status (e.g. draft), and existing outline.
- **Updated Fields in WordPress:**
  1. `post_content` — Expanded article copy.
  2. `rank_math_title` & `rank_math_description`.

### 3. Production Safety Guards & Meta Sanitization
- **IP Authorization Guard**: Intercepts `Error (401)` and `Your IP is not authorized` responses, prompting operators to add egress IPs at `https://app.katteb.com/api_access`.
- **Payload Error Guard**: Validates that generated payloads under 400 characters do not contain raw backend error strings before updating the WordPress database.
- **RankMath Meta Description Sanitizer**: Automatically strips inline `<style>...</style>` tags and stray CSS class selectors from generated meta descriptions before persistence.

---

## Batch Operations SOP

1. **Perform Audit:**
   ```bash
   katteb wp audit-low-words --site destinations-ai --threshold 400 --limit 50
   ```
2. **Review Candidates in Dry-Run Mode:**
   ```bash
   katteb wp expand-post --site destinations-ai --id 97748 --dry-run
   ```
3. **Execute Batch Expansion:**
   ```bash
   katteb wp batch-expand --site destinations-ai --post-type destinations --limit 5 --words 1800
   ```
4. **Verify on Live WordPress:**
   ```bash
   bash "${BBM_WP_ROOT:-$HOME/Projects/bbm-wordpress}/scripts/wp-cli/wp-global" @destinations-ai.prod post get 97748 --field=post_content
   ```

## Configuration

Set `BBM_WP_ROOT` in your environment or `.env` file if your local WordPress repository is installed in a non-default path:

```bash
export BBM_WP_ROOT="/path/to/bbm-wordpress"
```

If not provided, Katteb defaults to checking `os.getenv("BBM_WP_ROOT")` or `$HOME/Projects/bbm-wordpress`. If the required `wp-global` script is not located, a clean `FileNotFoundError` will be raised with actionable guidance.
