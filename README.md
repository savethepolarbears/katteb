# Katteb API v2 — CLI & Developer SDK

[![CI](https://github.com/savethepolarbears/katteb/actions/workflows/ci.yml/badge.svg)](https://github.com/savethepolarbears/katteb/actions/workflows/ci.yml)
[![Security Scan](https://github.com/savethepolarbears/katteb/actions/workflows/security.yml/badge.svg)](https://github.com/savethepolarbears/katteb/actions/workflows/security.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type Checker: mypy](https://img.shields.io/badge/types-mypy-blue.svg)](https://mypy-lang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A modern, production-grade developer toolkit and command-line interface for the **[Katteb API v2](https://app.katteb.com/api/v2/docs)**. Generate factual, SEO-optimized AI articles, audit competitor SERPs, detect and humanize AI text, verify factual claims, and automate WordPress fleet content enrichment at scale.

---

## Key Features

- **Full Katteb API v2 Coverage:**
  - AI Article Generation (500–5,000 words with TL;DR, FAQ, Key Takeaways, and image embeddings).
  - Competitor SEO Analysis (on-page scoring, keyword density, and actionable recommendations).
  - AI Text Detection & Humanizer Rewriting (multiple strength tiers + imperfection injection).
  - Real-time Web-Search Fact-Checking (instant claim verification against live web sources).
  - Account credit balances, rate limit monitoring, brand workspaces, and writing style management.
- **Smart Concurrency Queue:** Automatically intercepts Katteb's 1-active-heavy-job HTTP 429 lockouts, polls active jobs until completion, and processes queued tasks without failure.
- **Production Hardened & Secure:**
  - Sanitized shell arguments with base64 payload transport to eliminate CLI injection risks.
  - Strict input validation via Pydantic v2 schemas and Mypy strict type checking.
  - Cryptographically secure jitter for API retry backoff.
  - Config files persisted with restricted `0600` filesystem permissions.
- **Dual-Mode Output:** Rich interactive tables for terminal operators vs. machine-readable `--json` format for AI coding agents and CI/CD pipelines.
- **WordPress Fleet Integration:** Audit thin posts (<400 words) across custom post types (`destinations`, `post`), generate expanded guides, and atomically update `post_content`, Pods custom fields, and RankMath SEO metadata via WP-CLI (`wp-global`).
- **Telemetry & Event Dispatch:** Built-in event pipeline for webhooks and automated background tasks with local structured JSONL metrics.

---

## Installation

### From Source (Recommended for Development)

```bash
git clone https://github.com/savethepolarbears/katteb.git
cd katteb
pip install -e ".[dev]"
```

The `katteb` executable will be automatically available on your system path.

---

## Authentication & Configuration

The toolkit resolves credentials in the following order of precedence:

1. **Global Configuration File (`~/.katteb/config.json`):**
   ```bash
   katteb config set-key <YOUR_KATTEB_API_KEY>
   ```
2. **Environment Variable:**
   ```bash
   export KATTEB_API_KEY="your_katteb_api_key_here"
   ```
3. **Local `.env` File:**
   ```env
   KATTEB_API_KEY=your_katteb_api_key_here
   ```

Verify your active configuration:
```bash
katteb config show
```

---

## Quick Start CLI Examples

### 1. Account & Credits
```bash
katteb account credits
katteb account limits
katteb styles list
katteb brands list
```

### 2. Generate Articles
```bash
# Generate with live progress tracking
katteb article generate -t "Complete Travel Guide to Zurich 2026" -w 2000 -c ch

# Include specific enhancements
katteb article generate -t "Top AI Coding Tools" -w 1500 -e tldr -e key_takeaways -e faq

# Non-blocking async queue
katteb article generate -t "Best Hiking Backpacks" --no-wait
```

### 3. SEO, Humanizer & Fact-Checking
```bash
# Analyze URL for SEO
katteb seo analyze --url "https://example.com/guide" --keyword "travel guide"

# Detect AI content probability
katteb humanizer detect -t "The landscape of artificial intelligence continues to evolve rapidly..."

# Humanize AI text
katteb humanizer rewrite -t "Text to humanize..." --strength Strong --add-imperfections

# Verify a factual claim
katteb factcheck verify -c "The Great Wall of China is visible from space with the naked eye."
```

### 4. WordPress Fleet Automation
```bash
# Audit thin posts under 400 words
katteb wp audit-low-words --site destinations-ai --threshold 400 --limit 25

# Expand single post (dry-run preview)
katteb wp expand-post --site destinations-ai --id 97748 --dry-run

# Live expand and update post
katteb wp expand-post --site destinations-ai --id 97748 --words 1800

# Batch expand top 5 lowest word count posts
katteb wp batch-expand --site destinations-ai --post-type destinations --limit 5 --words 1800
```

### 5. Telemetry & Pipeline Dispatch
```bash
# View aggregated execution telemetry
katteb telemetry summary

# Inspect recent runs
katteb telemetry tail -n 10

# Dispatch via pipeline event payload
katteb pipeline-dispatch -f event.json
```

---

## Python SDK Usage

```python
from katteb import KattebClient
from katteb.queue import KattebQueueManager

# Initialize client
client = KattebClient()

# Check available credits
credits = client.get_credits()
print(f"Available credits: {credits.credits}")

# Generate article with smart concurrency management
queue = KattebQueueManager(client)
article = queue.generate_and_wait(
    topic="Best Places to Visit in Japan 2026",
    word_count=2000,
    country="jp",
    enhancements=["tldr", "key_takeaways", "faq"],
    on_status=lambda msg: print(f"Progress: {msg}"),
)

print(f"Generated {article.word_count} words: {article.meta_title}")
```

---

## Documentation

- [API Reference](docs/API_REFERENCE.md) — Complete Python SDK classes and methods
- [CLI Reference](docs/CLI_REFERENCE.md) — Command flags and usage guide
- [WordPress Integration](docs/WORDPRESS_INTEGRATION.md) — Fleet management & WP-CLI automation guide
- [Contributing Guide](CONTRIBUTING.md) — Developer guidelines and testing setup
- [Security Policy](SECURITY.md) — Vulnerability reporting and credential hygiene

---

## Testing & Quality Assurance

Run the test suite with test coverage:
```bash
pytest --cov=katteb --cov-report=term-missing --cov-fail-under=80
```

Run linting and type checks:
```bash
ruff check .
ruff format --check .
mypy src/
bandit -r src/ -ll
```

---

## License

This project is licensed under the [MIT License](LICENSE).
