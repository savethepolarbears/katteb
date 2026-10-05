# Katteb CLI Reference Guide

The `katteb` CLI provides command-line control for all Katteb API operations, local configuration, WordPress fleet content enrichment, automated pipeline dispatch, and telemetry observability.

---

## Global Flags

- `--api-key TEXT`: Override API key for this command.
- `--base-url TEXT`: Override base API URL.
- `--json`: Format all command output as machine-readable JSON.
- `-h, --help`: Display help and usage information.

---

## Configuration Commands (`katteb config`)

### `katteb config set-key <KEY>`
Persists your Katteb API key securely in `~/.katteb/config.json` with `0600` filesystem permissions.
```bash
katteb config set-key katteb_live_xxxxxxxx
```

### `katteb config show`
Displays active configuration sources, base URL, and masked API key.
```bash
katteb config show
```

---

## Account Commands (`katteb account`)

### `katteb account credits`
Shows remaining credit balance, pooled/available credits, brand allocations, and daily API usage counts.
```bash
katteb account credits
katteb account credits --json
```

### `katteb account limits`
Displays current plan sliding-window rate limit counters.
```bash
katteb account limits
```

---

## Writing Styles & Brands (`katteb styles`, `katteb brands`)

### `katteb styles list`
Lists all writing styles configured in your Katteb account.
```bash
katteb styles list
```

### `katteb brands list`
Lists all brand workspaces configured in your account.
```bash
katteb brands list
```

---

## Article Commands (`katteb article`)

### `katteb article generate`
Generates an article. By default, waits and polls until generation is complete.

**Options:**
- `-t, --topic TEXT` (required): Article topic.
- `-w, --words INTEGER`: Word count target (500–5000, default: 1500).
- `-l, --language TEXT`: Language (default: "English").
- `-c, --country TEXT`: 2-letter ISO country code (e.g. us, gb, de, fr, jp).
- `--style-id INTEGER`: Custom writing style ID.
- `--brand-id INTEGER`: Brand workspace ID.
- `-g, --guidelines TEXT`: Custom instructions (max 2000 chars).
- `-e, --enhancement TEXT`: Can be specified multiple times (`-e tldr -e faq -e key_takeaways -e featured_image`).
- `--wait / --no-wait`: Toggle blocking poll vs instant background job return.

**Examples:**
```bash
# Generate with live progress and table output
katteb article generate -t "Best Digital Nomad Destinations in Portugal" -w 2000 -c pt

# Include specific enhancements
katteb article generate -t "Top AI Coding Tools" -w 1500 -e tldr -e key_takeaways -e faq

# Non-blocking async queue
katteb article generate -t "Top Hiking Backpacks" -w 1500 --no-wait
```

### `katteb article get <JOB_ID>`
Fetches the content and metadata of a specific article job.
```bash
katteb article get 4521
```

### `katteb article list`
Lists past articles with pagination and status filters.
```bash
katteb article list --page 1 --limit 20 --status completed
```

### `katteb article cancel <JOB_ID>`
Cancels a pending article job and refunds credits.
```bash
katteb article cancel 4521
```

---

## SEO & AI Tools (`katteb seo`, `katteb humanizer`, `katteb factcheck`)

### `katteb seo analyze`
Submits a URL or content string for competitor SEO analysis.
```bash
katteb seo analyze --url "https://destinations.ai/zurich/" --keyword "Zurich travel guide"
```

### `katteb seo get <JOB_ID>`
Fetches SEO analysis score and recommendations.
```bash
katteb seo get 4522
```

### `katteb humanizer detect`
Calculates the AI writing probability (0–100%) and verdict.
```bash
katteb humanizer detect -t "The landscape of artificial intelligence continues to expand..."
```

### `katteb humanizer rewrite`
Rewrites text to bypass AI detection and read naturally.
```bash
katteb humanizer rewrite -t "Text here..." --strength Strong --add-imperfections
```

### `katteb factcheck verify`
Verifies a factual claim against live web searches.
```bash
katteb factcheck verify -c "The Great Wall of China is visible from space with the naked eye."
```

---

## WordPress Fleet Automation (`katteb wp`)

### `katteb wp audit-low-words`
Audits thin posts on target WordPress site below a given word threshold.
```bash
katteb wp audit-low-words --site destinations-ai --threshold 400 --limit 25
```

### `katteb wp expand-post`
Expands a specific post on WordPress via Katteb API and updates `post_content`, Pods custom fields, and RankMath SEO metadata.
```bash
# Dry-run preview
katteb wp expand-post --site destinations-ai --id 97748 --dry-run

# Live generation and update
katteb wp expand-post --site destinations-ai --id 97748 --words 1800

# Specify custom receipt directory
katteb wp expand-post --site destinations-ai --id 97748 --receipt-dir ./audit-receipts
```

### `katteb wp batch-expand`
Batch expands the lowest word count posts of a specific post type.
```bash
katteb wp batch-expand --site destinations-ai --post-type destinations --limit 5 --words 1800 --receipt-dir ./audit-receipts
```

---

## Event Pipeline Dispatch (`katteb pipeline-dispatch`)

Executes automated expansion pipelines triggered by webhook payloads, Activepieces flows, or stdin streams.

**Options:**
- `--stdin`: Read JSON event payload from standard input.
- `-f, --file PATH`: Read JSON event payload from a file.
- `--site TEXT`: Override site alias in payload.
- `--post-id INTEGER`: Override post ID in payload.
- `--words INTEGER`: Override target word count.
- `--dry-run`: Run in dry-run simulation mode without updating the remote database.

**Examples:**
```bash
# Dispatch from payload file
katteb pipeline-dispatch -f event.json

# Dispatch via piped stdin stream
echo '{"site": "destinations-ai", "post_id": 97748, "target_words": 1800}' | katteb pipeline-dispatch --stdin
```

---

## Telemetry & Observability (`katteb telemetry`)

Track fleet-wide performance metrics, credit expenditures, execution durations, and run histories stored locally in `~/.katteb/telemetry.jsonl`.

### `katteb telemetry summary`
Displays aggregated metrics including total runs, success rates, words generated, and per-site breakdowns.
```bash
katteb telemetry summary
katteb telemetry summary --json
```

### `katteb telemetry tail`
Inspects the most recent recorded telemetry events.
```bash
katteb telemetry tail -n 20
katteb telemetry tail -n 20 --json
```
