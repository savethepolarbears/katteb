"""Command-line interface (CLI) for Katteb API v2 and WordPress Fleet operations."""

import sys

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from katteb.client import KattebClient
from katteb.config import KattebConfig, get_config
from katteb.formatters import (
    format_article_get,
    format_articles_list,
    format_brands,
    format_credits,
    format_factcheck,
    format_humanizer_detect,
    format_styles,
    print_json,
)
from katteb.queue import KattebQueueManager
from katteb.wordpress import WordPressFleetManager

console = Console()


def get_client(ctx: click.Context) -> KattebClient:
    """Helper to instantiate KattebClient from context or config."""
    api_key = ctx.obj.get("api_key") if ctx.obj else None
    base_url = ctx.obj.get("base_url") if ctx.obj else None
    client = KattebClient(api_key=api_key, base_url=base_url)
    if not client.config.has_api_key():
        console.print("[bold red]Configuration Error:[/bold red] Katteb API key is not configured.")
        console.print("Set [cyan]KATTEB_API_KEY[/cyan] in your environment, or run:")
        console.print("  [bold green]katteb config set-key <YOUR_KEY>[/bold green]")
        sys.exit(1)
    return client


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--api-key", envvar="KATTEB_API_KEY", help="Katteb API key (or set KATTEB_API_KEY env)")
@click.option("--base-url", envvar="KATTEB_BASE_URL", help="Katteb API base URL")
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON format")
@click.pass_context
def cli(ctx: click.Context, api_key: str | None, base_url: str | None, as_json: bool):
    """Katteb API v2 CLI — AI Article Generation, SEO Analysis, and WordPress Fleet Integration."""
    ctx.ensure_object(dict)
    ctx.obj["api_key"] = api_key
    ctx.obj["base_url"] = base_url
    ctx.obj["as_json"] = as_json


# =============================================================================
# Config Commands
# =============================================================================


@cli.group()
def config():
    """Manage local Katteb configuration and credentials."""
    pass


@config.command("set-key")
@click.argument("key")
@click.option("--base-url", default=None, help="Custom base URL")
def config_set_key(key: str, base_url: str | None):
    """Save Katteb API key globally to ~/.katteb/config.json."""
    saved_path = KattebConfig.save_global_api_key(key, base_url)
    console.print(f"✅ Katteb API key securely saved to [bold green]{saved_path}[/bold green]")


@config.command("show")
@click.pass_context
def config_show(ctx: click.Context):
    """Display current active configuration sources and masked API key."""
    cfg = get_config(api_key=ctx.obj.get("api_key"), base_url=ctx.obj.get("base_url"))
    as_json = ctx.obj.get("as_json", False)

    masked_key = (
        (cfg._api_key[:4] + "..." + cfg._api_key[-4:])
        if cfg._api_key and len(cfg._api_key) > 8
        else ("***" if cfg._api_key else None)
    )

    data = {
        "configured": cfg.has_api_key(),
        "masked_api_key": masked_key,
        "base_url": cfg.base_url,
    }

    if as_json:
        print_json(data)
        return

    table = Table(title="🔧 Katteb Active Configuration", show_header=True)
    table.add_column("Setting", style="dim")
    table.add_column("Value", style="bold")

    table.add_row("API Key Status", "✅ Set" if cfg.has_api_key() else "❌ Missing")
    table.add_row("Masked Key", masked_key or "[red]None[/red]")
    table.add_row("Base URL", cfg.base_url)
    console.print(table)


# =============================================================================
# Account & Metadata Commands
# =============================================================================


@cli.group()
def account():
    """Check credit balance, usage, and rate limits."""
    pass


@account.command("credits")
@click.pass_context
def account_credits(ctx: click.Context):
    """Get available credit balance and daily usage."""
    client = get_client(ctx)
    res = client.get_credits()
    format_credits(res, as_json=ctx.obj.get("as_json", False))


@account.command("limits")
@click.pass_context
def account_limits(ctx: click.Context):
    """Get rate limits and sliding window quotas."""
    client = get_client(ctx)
    res = client.get_limits()
    if ctx.obj.get("as_json", False):
        print_json(res)
    else:
        console.print(res)


@account.command("check-threshold")
@click.option("--threshold", type=int, default=None, help="Credit warning threshold")
@click.option("--json", "output_json", is_flag=True, help="Output pure JSON format")
@click.pass_context
def account_check_threshold(ctx: click.Context, threshold: int | None, output_json: bool):
    """Check if credit reserves are above alert threshold (exits with code 2 if depleted)."""
    from katteb.telemetry import check_credit_threshold

    as_json = ctx.obj.get("as_json", False) or output_json
    try:
        client = get_client(ctx)
        status_data = check_credit_threshold(client, threshold=threshold)
    except Exception as exc:
        if as_json:
            print_json({"success": False, "error": str(exc), "status": "ERROR"})
        else:
            console.print(f"❌ [bold red]Error checking credit threshold:[/bold red] {exc}")
        sys.exit(1)

    if as_json:
        print_json(status_data)
    else:
        status = status_data["status"]
        avail = status_data["available_credits"]
        thresh = status_data["threshold"]
        tier = status_data["plan_tier"]

        if status == "OK":
            console.print(f"✅ [bold green]Credits Healthy:[/bold green] {avail} remaining (threshold: {thresh}) | Tier: {tier}")
        elif status == "WARNING":
            console.print(f"⚠️  [bold yellow]Credit Warning:[/bold yellow] {avail} remaining (at/below threshold {thresh}) | Tier: {tier}")
        else:
            console.print(f"🚨 [bold red]Credits Depleted:[/bold red] 0 credits remaining! Tier: {tier}")

    if status_data.get("depleted"):
        sys.exit(2)


@cli.group()
def styles():
    """Manage writing styles."""
    pass


@styles.command("list")
@click.pass_context
def styles_list(ctx: click.Context):
    """List writing styles available in your Katteb account."""
    client = get_client(ctx)
    res = client.list_styles()
    format_styles(res.styles, as_json=ctx.obj.get("as_json", False))


@cli.group()
def brands():
    """Manage brands / workspaces."""
    pass


@brands.command("list")
@click.pass_context
def brands_list(ctx: click.Context):
    """List brands/workspaces configured in your Katteb account."""
    client = get_client(ctx)
    res = client.list_brands()
    format_brands(res.brands, as_json=ctx.obj.get("as_json", False))


# =============================================================================
# Article Operations
# =============================================================================


@cli.group()
def article():
    """Generate, poll, list, and cancel AI articles."""
    pass


@article.command("generate")
@click.option("--topic", "-t", required=True, help="Article topic (max 500 chars)")
@click.option("--words", "-w", default=1500, type=int, help="Target word count (500-5000, default: 1500)")
@click.option("--language", "-l", default="English", help="Language name (e.g. English, Spanish)")
@click.option("--country", "-c", default="us", help="ISO country code (e.g. us, gb, de)")
@click.option("--style-id", type=int, default=None, help="Writing style ID from 'katteb styles list'")
@click.option("--brand-id", type=int, default=None, help="Brand ID from 'katteb brands list'")
@click.option("--guidelines", "-g", default=None, help="Custom instructions (max 2000 chars)")
@click.option("--enhancement", "-e", multiple=True, help="Enhancement: tldr, featured_image, faq, key_takeaways, etc.")
@click.option("--wait/--no-wait", default=True, help="Wait and poll until article generation completes")
@click.option("--timeout", default=600, type=int, help="Polling timeout in seconds (default: 600)")
@click.pass_context
def article_generate(
    ctx: click.Context,
    topic: str,
    words: int,
    language: str,
    country: str,
    style_id: int | None,
    brand_id: int | None,
    guidelines: str | None,
    enhancement: tuple,
    wait: bool,
    timeout: int,
):
    """Generate a high-quality, SEO-optimized AI article."""
    client = get_client(ctx)
    queue = KattebQueueManager(client)
    enhancements_list = list(enhancement) if enhancement else ["tldr", "key_takeaways", "faq"]

    as_json = ctx.obj.get("as_json", False)

    if not wait:
        res = client.generate_article(
            topic=topic,
            language=language,
            country=country,
            word_count=words,
            brand_id=brand_id,
            writing_style_id=style_id,
            guidelines=guidelines,
            enhancements=enhancements_list,
        )
        if as_json:
            print_json(res)
        else:
            console.print(f"🚀 [bold green]Article Job Queued![/bold green] Job ID: [bold]{res.job_id}[/bold]")
            console.print(f"Topic: {res.topic} | Credits: {res.credits_charged}")
            console.print(f"Poll with: [cyan]katteb article get {res.job_id}[/cyan]")
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task(f"Generating article: '{topic}'...", total=None)

        def update_status(msg: str):
            progress.update(task, description=msg)

        completed_article = queue.generate_and_wait(
            topic=topic,
            language=language,
            country=country,
            word_count=words,
            brand_id=brand_id,
            writing_style_id=style_id,
            guidelines=guidelines,
            enhancements=enhancements_list,
            on_status=update_status,
        )

    format_article_get(completed_article, as_json=as_json)


@article.command("get")
@click.argument("job_id", type=int)
@click.pass_context
def article_get(ctx: click.Context, job_id: int):
    """Retrieve article generation status and content."""
    client = get_client(ctx)
    res = client.get_article(job_id)
    format_article_get(res, as_json=ctx.obj.get("as_json", False))


@article.command("list")
@click.option("--page", default=1, type=int, help="Page number")
@click.option("--limit", default=20, type=int, help="Items per page (1-50)")
@click.option("--status", default=None, help="Filter: pending, processing, completed, failed")
@click.pass_context
def article_list(ctx: click.Context, page: int, limit: int, status: str | None):
    """List previously generated articles."""
    client = get_client(ctx)
    res = client.list_articles(page=page, limit=limit, status=status)
    format_articles_list(res.articles, as_json=ctx.obj.get("as_json", False))


@article.command("cancel")
@click.argument("job_id", type=int)
@click.pass_context
def article_cancel(ctx: click.Context, job_id: int):
    """Cancel a pending article job and refund credits."""
    client = get_client(ctx)
    res = client.cancel_article(job_id)
    if ctx.obj.get("as_json", False):
        print_json(res)
    else:
        console.print(f"✅ [bold]Job #{job_id} cancelled.[/bold] Response: {res}")


# =============================================================================
# SEO & AI Tools
# =============================================================================


@cli.group()
def seo():
    """Run SEO analyses and retrieve audit reports."""
    pass


@seo.command("analyze")
@click.option("--url", default=None, help="Target URL to analyze")
@click.option("--text", default=None, help="Raw HTML/text content to analyze")
@click.option("--keyword", "-k", default=None, help="Target SEO keyword")
@click.pass_context
def seo_analyze(ctx: click.Context, url: str | None, text: str | None, keyword: str | None):
    """Submit a URL or content for AI SEO analysis."""
    if not url and not text:
        console.print("[red]Error: Must specify either --url or --text[/red]")
        sys.exit(1)

    client = get_client(ctx)
    req_type = "url" if url else "text"
    val = url if url else text
    res = client.analyze_seo(type=req_type, value=val, keyword=keyword)  # type: ignore
    if ctx.obj.get("as_json", False):
        print_json(res)
    else:
        console.print(f"🚀 [bold green]SEO Analysis Queued![/bold green] Job ID: [bold]{res.job_id}[/bold]")
        console.print(f"Poll results with: [cyan]katteb seo get {res.job_id}[/cyan]")


@seo.command("get")
@click.argument("job_id", type=int)
@click.pass_context
def seo_get(ctx: click.Context, job_id: int):
    """Retrieve SEO analysis results."""
    client = get_client(ctx)
    res = client.get_seo(job_id)
    if ctx.obj.get("as_json", False):
        print_json(res)
    else:
        console.print(res)


@cli.group()
def humanizer():
    """Detect and rewrite AI text."""
    pass


@humanizer.command("detect")
@click.option("--text", "-t", required=True, help="Text to analyze (50-50,000 chars)")
@click.option("--language", "-l", default="English", help="Language name")
@click.pass_context
def humanizer_detect(ctx: click.Context, text: str, language: str):
    """Detect AI writing probability."""
    client = get_client(ctx)
    res = client.detect_ai(text=text, language=language)
    format_humanizer_detect(res, as_json=ctx.obj.get("as_json", False))


@humanizer.command("rewrite")
@click.option("--text", "-t", required=True, help="Text to humanize (20-50,000 chars)")
@click.option("--strength", "-s", default="Moderate", type=click.Choice(["Subtle", "Moderate", "Strong"]))
@click.option("--language", "-l", default="English")
@click.option("--add-imperfections", is_flag=True, default=False)
@click.pass_context
def humanizer_rewrite(ctx: click.Context, text: str, strength: str, language: str, add_imperfections: bool):
    """Rewrite AI text to sound human."""
    client = get_client(ctx)
    res = client.rewrite_humanizer(
        text=text,
        strength=strength,
        language=language,
        add_imperfections=add_imperfections,
    )
    if ctx.obj.get("as_json", False):
        print_json(res)
    else:
        console.print(f"[bold green]Rewritten Text:[/bold green]\n{res.rewritten_text}")


@cli.group()
def factcheck():
    """Verify factual claims using web search."""
    pass


@factcheck.command("verify")
@click.option("--claim", "-c", required=True, help="The claim to verify (3-300 words)")
@click.pass_context
def factcheck_verify(ctx: click.Context, claim: str):
    """Verify a factual claim against live web sources."""
    client = get_client(ctx)
    res = client.verify_fact(text=claim)
    format_factcheck(res, as_json=ctx.obj.get("as_json", False))


# =============================================================================
# WordPress Fleet Integration Commands
# =============================================================================


@cli.group()
def wp():
    """WordPress Fleet auditing, content generation, and post updates."""
    pass


@wp.command("audit-low-words")
@click.option("--site", "-s", default="destinations-ai", help="WP alias (e.g. destinations-ai, realjourneytravels)")
@click.option("--threshold", "-t", default=400, type=int, help="Maximum word count threshold (default: 400)")
@click.option(
    "--post-type",
    "-p",
    multiple=True,
    help="Post types to inspect (default: destinations, post, gear, restaurant, page)",
)
@click.option("--limit", "-n", default=50, type=int, help="Limit output results")
@click.pass_context
def wp_audit_low_words(ctx: click.Context, site: str, threshold: int, post_type: tuple, limit: int):
    """Audit all posts on target WordPress site with word count below threshold."""
    client = get_client(ctx)
    wp_mgr = WordPressFleetManager(client)
    pts = list(post_type) if post_type else ["destinations", "post", "gear", "restaurant", "page"]

    with Progress(
        SpinnerColumn(),
        TextColumn(f"[cyan]Auditing {site} for posts < {threshold} words...[/cyan]"),
        console=console,
        transient=True,
    ):
        results = wp_mgr.audit_low_word_posts(site=site, post_types=pts, max_words=threshold)

    as_json = ctx.obj.get("as_json", False)
    if as_json:
        print_json({"site": site, "threshold": threshold, "count": len(results), "posts": results[:limit]})
        return

    table = Table(
        title=f"📊 Low Word Count Posts on {site} (< {threshold} words) — Found {len(results)}",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Word Count", justify="right", style="bold red")
    table.add_column("Status", style="dim")
    table.add_column("Title", style="bold")
    table.add_column("Location/Meta", style="dim")

    for r in results[:limit]:
        loc = f"{r.get('city') or ''}, {r.get('country') or ''}".strip(", ")
        table.add_row(
            str(r["id"]),
            r["post_type"],
            str(r["content_wc"]),
            r["status"],
            r["title"][:45],
            loc[:25],
        )

    console.print(table)
    if len(results) > limit:
        console.print(f"[dim]... and {len(results) - limit} more items (use --limit to show more).[/dim]")


@wp.command("expand-post")
@click.option("--site", "-s", default="destinations-ai", help="WP alias (default: destinations-ai)")
@click.option("--id", "-i", "post_id", required=True, type=int, help="WordPress Post ID to expand")
@click.option("--words", "-w", default=1500, type=int, help="Target word count (default: 1500)")
@click.option("--dry-run", is_flag=True, help="Preview generation prompt and parameters without calling Katteb")
@click.pass_context
def wp_expand_post(ctx: click.Context, site: str, post_id: int, words: int, dry_run: bool):
    """Generate expanded AI content via Katteb and update WordPress post."""
    client = get_client(ctx)
    wp_mgr = WordPressFleetManager(client)
    as_json = ctx.obj.get("as_json", False)

    def on_status(msg: str):
        if not as_json:
            console.print(f"ℹ️ {msg}")

    result = wp_mgr.expand_and_update_post(
        site=site,
        post_id=post_id,
        word_count=words,
        dry_run=dry_run,
        on_status=on_status,
    )

    if as_json:
        print_json(result)
    elif dry_run:
        console.print("\n[bold yellow]🔍 DRY RUN PREVIEW:[/bold yellow]")
        console.print(f"Post ID: {result['post_id']} ({result['title']})")
        console.print(f"Target Topic: [cyan]{result['topic']}[/cyan]")
        console.print(f"Country Code: {result['country']} | Target Words: {result['word_count']}")
        console.print(f"Enhancements: {result['enhancements']}")
        console.print(f"Guidelines: {result['guidelines']}")
    else:
        console.print("\n🎉 [bold green]Post Successfully Expanded & Updated in WordPress![/bold green]")
        console.print(f"Post ID: {result['post_id']} | Title: {result['title']}")
        console.print(
            f"Word Count: [red]{result['previous_word_count']} words[/red] ➔ [bold green]{result['new_word_count']} words[/bold green]"
        )
        console.print(f"SEO Title: {result['meta_title']}")
        console.print(f"SEO Description: {result['meta_description']}")


@wp.command("batch-expand")
@click.option("--site", "-s", default="destinations-ai", help="WP alias (default: destinations-ai)")
@click.option("--post-type", "-p", default="destinations", help="Post type to expand (default: destinations)")
@click.option("--limit", "-n", default=3, type=int, help="Number of lowest word count posts to expand (default: 3)")
@click.option("--words", "-w", default=1500, type=int, help="Target word count per article")
@click.option("--dry-run", is_flag=True, help="Preview batch plan without executing")
@click.option("--receipt-dir", "-r", default="receipts", help="Directory to save markdown audit receipt (default: receipts)")
@click.pass_context
def wp_batch_expand(ctx: click.Context, site: str, post_type: str, limit: int, words: int, dry_run: bool, receipt_dir: str):
    """Batch expand the lowest word count posts for a post type on WordPress."""
    client = get_client(ctx)
    wp_mgr = WordPressFleetManager(client)
    as_json = ctx.obj.get("as_json", False)

    low_posts = wp_mgr.audit_low_word_posts(site=site, post_types=[post_type], max_words=400)
    targets = low_posts[:limit]

    if not targets:
        if as_json:
            print_json({"batch_results": [], "message": f"No posts under 400 words found for {post_type} on {site}."})
        else:
            console.print(f"[yellow]No posts under 400 words found for {post_type} on {site}.[/yellow]")
        return

    if not as_json:
        console.print(f"🎯 Selected {len(targets)} lowest word count posts from {site} for expansion:")
        for i, t in enumerate(targets, 1):
            console.print(f"  {i}. ID: {t['id']} | Title: {t['title']} | Current Words: {t['content_wc']}")

    if dry_run:
        if as_json:
            print_json({"dry_run": True, "site": site, "post_type": post_type, "targets": targets})
        else:
            console.print("\n[yellow]Dry-run mode active. No posts modified.[/yellow]")
        return

    results = []
    for idx, t in enumerate(targets, 1):
        if not as_json:
            console.print(f"\n[{idx}/{len(targets)}] Processing Post #{t['id']}: {t['title']}...")
        try:
            res = wp_mgr.expand_and_update_post(
                site=site,
                post_id=t["id"],
                word_count=words,
                on_status=None if as_json else (lambda m: console.print(f"   {m}")),
            )
            results.append(res)
            if not as_json:
                console.print(f"   ✅ Updated Post #{t['id']}: {res['previous_word_count']}w ➔ {res['new_word_count']}w")
        except Exception as e:
            results.append({
                "success": False,
                "post_id": t["id"],
                "title": t["title"],
                "error": str(e),
                "previous_word_count": t.get("content_wc", 0),
                "new_word_count": t.get("content_wc", 0),
            })
            if not as_json:
                console.print(f"   ❌ Error on Post #{t['id']}: {e}")

    receipt_file = None
    if results:
        from katteb.wordpress import generate_expansion_receipt

        receipt_file = generate_expansion_receipt(site=site, results=results, output_dir=receipt_dir)

    if as_json:
        payload = {"batch_results": results}
        if receipt_file:
            payload["receipt_file"] = receipt_file
        print_json(payload)
    else:
        console.print(f"\n🎉 [bold green]Batch Expansion Complete![/bold green] Processed {len(results)} posts.")
        if receipt_file:
            console.print(f"📄 Audit receipt written to: [bold cyan]{receipt_file}[/bold cyan]")


@cli.command("pipeline-dispatch")
@click.option("--stdin", "use_stdin", is_flag=True, help="Read JSON event payload from standard input")
@click.option("-f", "--file", "payload_file", type=click.Path(exists=True), help="Path to JSON event payload file")
@click.option("--site", help="Override site alias")
@click.option("--post-id", type=int, help="Override post ID")
@click.option("--words", type=int, help="Override target word count")
@click.option("--dry-run", is_flag=True, default=None, help="Run in dry-run simulation mode")
@click.option("--receipt-dir", help="Directory to save execution receipts")
@click.option("--json", "output_json", is_flag=True, help="Output JSON format")
@click.pass_context
def pipeline_dispatch(
    ctx: click.Context,
    use_stdin: bool,
    payload_file: str | None,
    site: str | None,
    post_id: int | None,
    words: int | None,
    dry_run: bool | None,
    receipt_dir: str | None,
    output_json: bool = False,
):
    """Activepieces & headless pipeline dispatch adapter for post expansion events."""
    import json
    from katteb.pipeline import process_pipeline_event

    as_json = ctx.obj.get("as_json", False) or output_json or use_stdin

    if not use_stdin and not payload_file and not (site and post_id):
        err_msg = "Missing payload source: Provide --stdin, --file, or both --site and --post-id."
        if as_json:
            print_json({"success": False, "error": err_msg})
        else:
            console.print(f"[bold red]Error:[/bold red] {err_msg}")
        sys.exit(1)

    raw_payload: dict = {}
    if use_stdin:
        try:
            stdin_text = sys.stdin.read()
            if stdin_text.strip():
                raw_payload = json.loads(stdin_text)
        except Exception as e:
            err_res = {"success": False, "error": f"Failed to read JSON from stdin: {e}"}
            print_json(err_res)
            sys.exit(1)
    elif payload_file:
        try:
            with open(payload_file, "r", encoding="utf-8") as f:
                raw_payload = json.load(f)
        except Exception as e:
            err_res = {"success": False, "error": f"Failed to read payload file: {e}"}
            if as_json:
                print_json(err_res)
            else:
                console.print(f"[bold red]Error:[/bold red] {e}")
            sys.exit(1)

    # CLI option overrides take precedence
    if site:
        raw_payload["site"] = site
    if post_id:
        raw_payload["post_id"] = post_id
    if words:
        raw_payload["target_words"] = words
    if dry_run is not None:
        raw_payload["dry_run"] = dry_run
    if receipt_dir:
        raw_payload["receipt_dir"] = receipt_dir
    if "event" not in raw_payload:
        raw_payload["event"] = "post_expansion_requested"

    # Process through pipeline
    result = process_pipeline_event(raw_payload)

    if as_json:
        print_json(result)
    else:
        if result.get("success"):
            console.print(f"✅ [bold green]Pipeline event completed:[/bold green] Site: {result.get('site')} | Post #{result.get('post_id')}")
            if result.get("dry_run"):
                console.print(f"   [yellow]Simulation mode[/yellow]: Target {result.get('old_word_count')}w")
            else:
                console.print(f"   Updated word count: {result.get('old_word_count')} ➔ {result.get('new_word_count')}")
            if result.get("receipt_path"):
                console.print(f"   Receipt: [cyan]{result.get('receipt_path')}[/cyan]")
        else:
            console.print(f"❌ [bold red]Pipeline event failed:[/bold red] {result.get('error')}")

    if not result.get("success"):
        sys.exit(1)


# =============================================================================
# Telemetry Commands
# =============================================================================


@cli.group()
def telemetry():
    """Observability, execution telemetry, and fleet metrics."""
    pass


@telemetry.command("summary")
@click.option("-f", "--file", "log_file", type=click.Path(exists=True), help="Custom telemetry log path")
@click.option("--json", "output_json", is_flag=True, help="Output JSON format")
@click.pass_context
def telemetry_summary(ctx: click.Context, log_file: str | None, output_json: bool):
    """Display fleet-wide performance and execution summary."""
    from katteb.telemetry import get_telemetry_summary

    as_json = ctx.obj.get("as_json", False) or output_json
    summary = get_telemetry_summary(log_path=log_file)

    if as_json:
        print_json(summary)
        return

    pe = summary.get("post_expansions", {})
    table = Table(title="📊 Katteb Fleet Telemetry Summary", show_header=True)
    table.add_column("Metric", style="dim")
    table.add_column("Value", style="bold")

    table.add_row("Total Events Recorded", str(summary.get("total_events", 0)))
    table.add_row("Total Post Expansions", str(pe.get("total_runs", 0)))
    table.add_row("Success Rate", f"{pe.get('success_rate_percent', 0.0)}%")
    table.add_row("Total Words Generated", f"{pe.get('total_words_generated', 0):,}")
    table.add_row("Total Credits Used", str(pe.get("total_credits_used", 0)))
    table.add_row("Average Duration", f"{pe.get('avg_duration_seconds', 0.0)}s")

    console.print(table)

    sites = pe.get("sites", {})
    if sites:
        site_table = Table(title="🌐 Per-Site Activity Breakdown", show_header=True)
        site_table.add_column("Site Alias", style="cyan")
        site_table.add_column("Runs", style="bold")
        site_table.add_column("Words Generated", style="green")
        site_table.add_column("Credits", style="magenta")

        for site_alias, sdata in sites.items():
            site_table.add_row(
                site_alias,
                str(sdata.get("runs", 0)),
                f"{sdata.get('words_generated', 0):,}",
                str(sdata.get("credits_used", 0)),
            )
        console.print(site_table)


@telemetry.command("tail")
@click.option("-n", "--limit", type=int, default=10, help="Number of recent events to display")
@click.option("-f", "--file", "log_file", type=click.Path(exists=True), help="Custom telemetry log path")
@click.option("--json", "output_json", is_flag=True, help="Output JSON format")
@click.pass_context
def telemetry_tail(ctx: click.Context, limit: int, log_file: str | None, output_json: bool):
    """View recent telemetry event log records."""
    from katteb.telemetry import get_telemetry_events

    as_json = ctx.obj.get("as_json", False) or output_json
    events = get_telemetry_events(limit=limit, log_path=log_file)

    if as_json:
        print_json({"events": events})
        return

    if not events:
        console.print("[dim]No telemetry events recorded yet.[/dim]")
        return

    table = Table(title=f"📜 Recent Katteb Events (Last {len(events)})", show_header=True)
    table.add_column("Timestamp", style="dim")
    table.add_column("Type", style="cyan")
    table.add_column("Site / Target", style="green")
    table.add_column("Status", style="bold")
    table.add_column("Words / Details", style="white")

    for ev in events:
        table.add_row(
            ev.get("timestamp", "")[:19].replace("T", " "),
            ev.get("event_type", ""),
            str(ev.get("site") or ev.get("topic") or ""),
            "[green]Success[/green]" if ev.get("success") else "[red]Failed[/red]",
            f"+{ev.get('words_generated', 0)}w" if ev.get("words_generated") else str(ev.get("post_id") or ""),
        )
    console.print(table)


def main():
    cli(obj={})


if __name__ == "__main__":
    main()
