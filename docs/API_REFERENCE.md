# Katteb API v2 — Python SDK Reference

The `katteb` Python package provides programmatic, type-safe access to all Katteb API v2 endpoints.

## Installation

```bash
pip install katteb
```

## Quick Start

```python
from katteb import KattebClient

client = KattebClient()  # Automatically reads KATTEB_API_KEY from environment or ~/.katteb/config.json

# Check credits
credits = client.get_credits()
print(f"Available credits: {credits.credits}")
```

---

## API Endpoints & Methods

### 1. `get_credits()`
Returns current credit balance, total credits, pooled/available credits, brand allocations, and daily heavy/read API usage counts.

- **Method:** `client.get_credits()`
- **Returns:** `AccountCreditsResponse` (`credits`, `credits_available`, `credits_pool`, `credits_total`, `brand_allocated`, `brands`, `plan_type`, `api_usage_today`)

### 2. `get_limits()`
Returns rate limit sliding window details.

- **Method:** `client.get_limits()`
- **Returns:** `AccountLimitsResponse`

### 3. `generate_article(...)`
Submits an article generation job for background processing.

- **Parameters:**
  - `topic` (str, required): Article topic (max 500 chars).
  - `language` (str, default: `"English"`): Target language.
  - `country` (str, default: `"us"`): ISO 3166-1 alpha-2 country code for geo-targeted search results.
  - `word_count` (int, default: `1500`): 500–5000 words.
  - `brand_id` (int, optional): Brand workspace ID from `list_brands()`.
  - `writing_style_id` (int, optional): Writing style ID from `list_styles()`.
  - `guidelines` (str, optional): Custom instructions (max 2000 chars).
  - `enhancements` (List[str], optional): List of add-ons: `"tldr"`, `"key_takeaways"`, `"faq"`, `"featured_image"`, `"internal_links"`, `"video_embed"`, `"quotes"`, `"patent"`.
- **Returns:** `ArticleGenerateResponse` (`job_id`, `credits_charged`, `estimated_time`, `status`, `poll_url`)

### 4. `get_article(job_id)`
Polls the status of an article or fetches its generated content.

- **Parameters:** `job_id` (int, required)
- **Returns:** `ArticleGetResponse` (`job_id`, `status`, `progress`, `content_html`, `featured_image`, `meta_title`, `meta_description`, `word_count`)

### 5. `list_articles(page=1, limit=20, status=None)`
Lists previously generated articles with pagination.

- **Parameters:**
  - `page` (int, default: `1`)
  - `limit` (int, default: `20`, max 50)
  - `status` (str, optional): Filter by `"pending"`, `"processing"`, `"completed"`, `"failed"`.
- **Returns:** `ArticleListResponse` (`articles`, `count`, `page`, `limit`)

### 6. `cancel_article(job_id)`
Cancels a pending or queued article and refunds consumed credits.

- **Parameters:** `job_id` (int, required)
- **Returns:** `Dict[str, Any]`

### 7. `analyze_seo(type, value, keyword=None, brand_id=None)`
Submits a live URL or raw HTML text for AI-powered SEO and competitor analysis.

- **Parameters:**
  - `type` (str, required): `"url"` or `"text"`.
  - `value` (str, required): The URL or text content.
  - `keyword` (str, optional): Target keyword.
- **Returns:** `SEOAnalyzeResponse` (`job_id`, `keyword`, `credits_charged`, `status`, `poll_url`)

### 8. `get_seo(job_id)`
Fetches the results and recommendations of an SEO analysis job.

- **Parameters:** `job_id` (int, required)
- **Returns:** `SEOGetResponse` (`job_id`, `status`, `keyword`, `score`, `recommendations`)

### 9. `detect_ai(text, language="English")`
Analyzes text to determine the probability that it was AI-generated (0–100 score).

- **Parameters:**
  - `text` (str, required): 50–50,000 characters.
  - `language` (str, default: `"English"`).
- **Returns:** `HumanizerDetectResponse` (`ai_probability`, `verdict`, `credits_charged`, `word_count`)
  - `verdict`: `"likely_human"` (<30%), `"mixed"` (30–69%), `"likely_ai"` (≥70%).

### 10. `rewrite_humanizer(text, strength="Moderate", language="English", add_imperfections=False, brand_id=None)`
Rewrites AI-generated text to sound natural and pass AI detection while preserving meaning.

- **Parameters:**
  - `text` (str, required): 20–50,000 characters.
  - `strength` (str, default: `"Moderate"`): `"Subtle"`, `"Moderate"`, or `"Strong"`.
  - `add_imperfections` (bool, default: `False`): Subtle human-like imperfections.
- **Returns:** `HumanizerRewriteResponse` (`rewritten_text`, `strength`, `credits_charged`, `original_length`, `rewritten_length`)

### 11. `verify_fact(text, brand_id=None)`
Verifies a factual statement against live web search results.

- **Parameters:** `text` (str, required): 3–300 words.
- **Returns:** `FactCheckResponse` (`verdict` [`"TRUE"`, `"FALSE"`, `"INCONCLUSIVE"`], `is_fact`, `explanation`, `search_query`, `references`, `credits_charged`)

---

## Concurrency Queue Manager

Katteb restricts concurrent heavy operations (1 active article generation at a time per account). `KattebQueueManager` automatically handles HTTP 429 lockouts by polling active jobs until completion and retrying submissions.

```python
from katteb import KattebClient
from katteb.queue import KattebQueueManager

client = KattebClient()
queue = KattebQueueManager(client)

# Automatically handles concurrency locks and polls until ready
article = queue.generate_and_wait(
    topic="Complete Guide to Rome 2026",
    word_count=2000,
    country="it",
    enhancements=["tldr", "faq", "key_takeaways"],
    on_status=lambda msg: print(f"[Status] {msg}")
)
```
