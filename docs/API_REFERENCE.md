# Katteb API v2 — Python SDK Reference

The `katteb` Python package provides programmatic, type-safe access to all Katteb API v2 endpoints, automated concurrency queues, WordPress fleet expansion managers, pipeline execution handlers, and local telemetry logging.

---

## Installation

```bash
pip install katteb
```

---

## Architecture Overview

- **`KattebClient`**: Core HTTP client handling authentication, rate-limiting headers, automatic retries with exponential backoff and jitter, and Pydantic response parsing.
- **`KattebQueueManager`**: Handles Katteb's 1-active-heavy-job concurrency constraint. Automatically polls in-flight jobs and retries queued requests upon encountering HTTP 429 lockouts.
- **`WordPressFleetManager`**: Integrates with WP-CLI (`wp-global`) to audit thin posts (<400 words), extract structured destination/post metadata, expand content via Katteb, and update live WordPress databases.
- **`KattebPipelineRunner`**: Orchestrates end-to-end event execution from webhook payloads, validates schemas, logs structured telemetry, and generates audit receipts.
- **`telemetry`**: Local structured JSON Lines event logging in `~/.katteb/telemetry.jsonl` with aggregation and inspection utilities.

---

## Core Client: `KattebClient`

```python
from katteb import KattebClient

client = KattebClient()  # Resolves KATTEB_API_KEY from env or ~/.katteb/config.json
```

### Account & Configuration
- **`get_credits() -> AccountCreditsResponse`**: Returns account credit balances, brand allocations, and daily heavy/read API usage counts.
- **`get_limits() -> AccountLimitsResponse`**: Returns rate limit sliding window details.
- **`list_styles() -> List[WritingStyle]`**: Returns all custom writing styles.
- **`list_brands() -> List[Brand]`**: Returns all brand workspaces.

### Article Generation & Lifecycle
- **`generate_article(topic, language="English", country="us", word_count=1500, brand_id=None, writing_style_id=None, guidelines=None, enhancements=None) -> ArticleGenerateResponse`**: Submits an article generation job.
- **`get_article(job_id: int) -> ArticleGetResponse`**: Fetches generated article content, metadata, and status (`pending`, `processing`, `completed`, `failed`).
- **`list_articles(page=1, limit=20, status=None) -> ArticleListResponse`**: Lists historical articles with pagination.
- **`cancel_article(job_id: int) -> Dict[str, Any]`**: Cancels a pending job and refunds consumed credits.

### SEO & Competitor Analysis
- **`analyze_seo(type: str, value: str, keyword: str | None = None, brand_id: int | None = None) -> SEOAnalyzeResponse`**: Submits a URL or text content for SEO auditing.
- **`get_seo(job_id: int) -> SEOGetResponse`**: Retrieves SEO analysis results, scores, and actionable recommendations.

### AI Detection & Humanizer
- **`detect_ai(text: str, language: str = "English") -> HumanizerDetectResponse`**: Calculates the probability (0–100%) that text was AI-generated (`likely_human`, `mixed`, `likely_ai`).
- **`rewrite_humanizer(text: str, strength: str = "Moderate", language: str = "English", add_imperfections: bool = False, brand_id: int | None = None) -> HumanizerRewriteResponse`**: Rewrites text to bypass AI detection and sound natural.

### Fact Checking
- **`verify_fact(text: str, brand_id: int | None = None) -> FactCheckResponse`**: Fact-checks claims against real-time web searches (`TRUE`, `FALSE`, `INCONCLUSIVE`).

---

## Concurrency Queue: `KattebQueueManager`

Katteb enforces an account-wide limit of one concurrent heavy generation job. `KattebQueueManager` abstracts polling, retry loops, and error recovery:

```python
from katteb import KattebClient
from katteb.queue import KattebQueueManager

client = KattebClient()
queue = KattebQueueManager(client, poll_interval=10, max_wait=600)

article = queue.generate_and_wait(
    topic="Complete Guide to Tokyo 2026",
    word_count=2000,
    country="jp",
    enhancements=["tldr", "faq", "key_takeaways"],
    on_status=lambda msg: print(f"[Status] {msg}")
)
print(f"Generated {article.word_count} words: {article.meta_title}")
```

---

## WordPress Fleet Automation: `WordPressFleetManager`

Automates audit and expansion across WordPress sites configured in WP-CLI.

```python
from katteb import KattebClient
from katteb.wordpress import WordPressFleetManager

client = KattebClient()
manager = WordPressFleetManager(client=client)

# 1. Audit low-word posts
thin_posts = manager.get_low_word_count_posts(
    site="destinations-ai",
    threshold=400,
    post_types=["destinations", "post"],
    limit=10
)

# 2. Expand a single post
result = manager.expand_post(
    site="destinations-ai",
    post_id=97748,
    target_words=1800,
    dry_run=False
)
print(f"Status: {result.status} | Added: {result.words_added} words")
```

---

## Event Pipeline: `KattebPipelineRunner`

Executes incoming event payloads from webhooks, queues, or scripts:

```python
from katteb.pipeline import KattebPipelineRunner

runner = KattebPipelineRunner()
payload = {
    "site": "destinations-ai",
    "post_id": 97748,
    "target_words": 1800,
    "dry_run": False
}

result = runner.run_expansion_event(payload)
print(f"Result: {result['status']}")
```

---

## Telemetry: `katteb.telemetry`

Record and analyze operational telemetry:

```python
from katteb.telemetry import get_telemetry_summary, get_telemetry_events

# Get aggregated metrics
summary = get_telemetry_summary()
print(f"Total expansions: {summary['post_expansions']['total_runs']}")

# Inspect recent events
recent_events = get_telemetry_events(limit=5)
```
