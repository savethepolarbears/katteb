---
name: katteb-api-cli
description: CLI and automation toolkit for Katteb API v2. Generates SEO-optimized articles, runs on-page SEO audits, humanizes AI text, verifies factual claims, and audits/expands WordPress posts (custom post types, Pods, RankMath) across the Black Bear Media fleet.
---

# Katteb API v2 Integration & CLI Skill

Use this skill to interact with the Katteb API v2 for AI content generation, SEO analysis, AI detection/rewriting, fact-checking, and automated WordPress post enrichment.

## Capabilities

- **Article Generation:** Create 500–5,000 word articles with enhancements (`tldr`, `key_takeaways`, `faq`, `featured_image`, `internal_links`).
- **Concurrency Management:** Automatically handles Katteb's 1-heavy-job concurrency rule (polls active jobs on 429 rather than failing).
- **SEO & AI Tools:** Run competitor SEO audits, detect AI probability, humanize text with strength levels, and verify claims via web search.
- **WordPress Fleet Integration:** Audit low-word-count content (< 400 words) across custom post types (`destinations`, `post`, `gear`, `restaurant`), generate expanded copy, and update `post_content`, Pods custom fields (`travel_guide`), and RankMath SEO metadata via WP-CLI.

## Configuration & Authentication

The CLI resolves credentials hierarchically:
1. `KATTEB_API_KEY` environment variable
2. `~/.katteb/config.json` (managed via `katteb config set-key <KEY>`)
3. `.env` in current directory or project roots

## Common CLI Commands

```bash
# Check Credit Balance & Limits
katteb account credits
katteb account limits

# Manage Styles & Brands
katteb styles list
katteb brands list

# Generate Article
katteb article generate --topic "Complete Travel Guide to Zurich 2026" --words 2000 --country ch
katteb article get <JOB_ID>
katteb article list --status completed

# AI Tools
katteb humanizer detect --text "..."
katteb humanizer rewrite --text "..." --strength Strong
katteb factcheck verify --claim "..."

# WordPress Fleet Operations (destinations.ai & fleet)
katteb wp audit-low-words --site destinations-ai --threshold 400
katteb wp expand-post --site destinations-ai --id 97748 --words 1800
katteb wp batch-expand --site destinations-ai --post-type destinations --limit 5 --words 1800
```

## Python SDK Example

```python
from katteb import KattebClient
from katteb.queue import KattebQueueManager

client = KattebClient()
queue = KattebQueueManager(client)

article = queue.generate_and_wait(
    topic="Best Places to Visit in Japan 2026",
    word_count=2000,
    country="jp",
    enhancements=["tldr", "key_takeaways", "faq"],
)

print(f"Generated {article.word_count} words: {article.meta_title}")
```
