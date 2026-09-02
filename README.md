# Katteb API v2 — CLI & Developer SDK

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A developer toolkit and command-line interface for the **[Katteb API v2](https://app.katteb.com/api/v2/docs)**. Generate SEO-optimized AI articles, run on-page competitor audits, humanize AI text, verify factual claims, and automate WordPress post expansion at scale.

---

## Features

- **Full Katteb API v2 Support:**
  - AI Article Generation (500–5,000 words with TL;DR, FAQ, Key Takeaways, and image embeddings).
  - Competitor SEO Analysis (on-page scoring & recommendations).
  - AI Text Detection & Humanizer Rewriting (strength levels + imperfection injection).
  - Real-time Web-Search Fact-Checking (instant claim verification).
  - Account credit balances, rate limit monitoring, brand workspaces, and writing style management.
- **Smart Concurrency Queue:** Automatically intercepts Katteb's 1-active-heavy-job HTTP 429 lockouts, polls the running job until completed, and submits queued requests without crashing.
- **Dual-Mode Output:** Interactive Rich tables for terminal users vs. machine-readable `--json` format for AI coding agents and automated CI/CD pipelines.
- **WordPress Fleet Integration:** Audit thin posts (<400 words) across WordPress custom post types (`destinations`, `post`, `gear`, `restaurant`), generate expanded content, and atomically update `post_content`, Pods custom fields (`travel_guide`), and RankMath SEO tags via WP-CLI.

---

## Installation

### Local Global CLI Setup

```bash
git clone https://github.com/savethepolarbears/katteb.git
cd katteb
pip install -e .
```

The `katteb` executable will be automatically available on your system path.

---

## Authentication & Configuration

The toolkit resolves credentials in the following priority:

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
# Generate with automatic progress tracking
katteb article generate -t "Complete Travel Guide to Zurich 2026" -w 2000 -c ch

# Include specific enhancements
katteb article generate -t "Top AI Coding Tools" -w 1500 -e tldr -e key_takeaways -e faq

# Non-blocking async queue
katteb article generate -t "Best Hiking Backpacks" --no-wait
```

### 3. SEO, Humanizer & Fact-Checking
```bash
# Analyze URL for SEO
katteb seo analyze --url "https://destinations.ai/zurich/" --keyword "Zurich guide"

# Detect AI content probability
katteb humanizer detect -t "The landscape of artificial intelligence continues to evolve rapidly..."

# Humanize AI text
katteb humanizer rewrite -t "Text to humanize..." --strength Strong --add-imperfections

# Verify fact
katteb factcheck verify -c "The Great Wall of China is visible from space with the naked eye."
```

### 4. WordPress Fleet Automation
```bash
# Audit all posts under 400 words on destinations.ai
katteb wp audit-low-words --site destinations-ai --threshold 400 --limit 25

# Expand single post (dry-run preview)
katteb wp expand-post --site destinations-ai --id 97748 --dry-run

# Live expand and update post
katteb wp expand-post --site destinations-ai --id 97748 --words 1800

# Batch expand top 5 lowest word count destinations
katteb wp batch-expand --site destinations-ai --post-type destinations --limit 5 --words 1800
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
print(f"Credits: {credits.credits}")

# Generate article with smart concurrency management
queue = KattebQueueManager(client)
article = queue.generate_and_wait(
    topic="Best Places to Visit in Japan 2026",
    word_count=2000,
    country="jp",
    enhancements=["tldr", "key_takeaways", "faq"],
    on_status=lambda msg: print(f"Progress: {msg}")
)

print(f"Generated {article.word_count} words: {article.meta_title}")
```

---

## Documentation

- [API Reference](docs/API_REFERENCE.md) — Complete Python SDK classes and methods
- [CLI Reference](docs/CLI_REFERENCE.md) — Command flags and usage guide
- [WordPress Integration](docs/WORDPRESS_INTEGRATION.md) — WordPress Fleet & WP-CLI automation guide
- [Contributing](CONTRIBUTING.md) — Developer guidelines and testing setup
- [Security Policy](SECURITY.md) — Vulnerability reporting and credential safety

---

## Testing

```bash
pytest tests/ -v
```

---

## License

This project is licensed under the [MIT License](LICENSE).
