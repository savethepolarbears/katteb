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
@click.pass_context
def wp_batch_expand(ctx: click.Context, site: str, post_type: str, limit: int, words: int, dry_run: bool):
    """Batch expand the lowest word count posts for a post type on WordPress."""
    client = get_client(ctx)
    wp_mgr = WordPressFleetManager(client)
    as_json = ctx.obj.get("as_json", False)

    low_posts = wp_mgr.audit_low_word_posts(site=site, post_types=[post_type], max_words=400)
    targets = low_posts[:limit]

    if not targets:
        console.print(f"[yellow]No posts under 400 words found for {post_type} on {site}.[/yellow]")
        return

    console.print(f"🎯 Selected {len(targets)} lowest word count posts from {site} for expansion:")
    for i, t in enumerate(targets, 1):
        console.print(f"  {i}. ID: {t['id']} | Title: {t['title']} | Current Words: {t['content_wc']}")

    if dry_run:
        console.print("\n[yellow]Dry-run mode active. No posts modified.[/yellow]")
        return

    results = []
    for idx, t in enumerate(targets, 1):
        console.print(f"\n[{idx}/{len(targets)}] Processing Post #{t['id']}: {t['title']}...")
        try:
            res = wp_mgr.expand_and_update_post(
                site=site,
                post_id=t["id"],
                word_count=words,
                on_status=lambda m: console.print(f"   {m}"),
            )
            results.append(res)
            console.print(f"   ✅ Updated Post #{t['id']}: {res['previous_word_count']}w ➔ {res['new_word_count']}w")
        except Exception as e:
            console.print(f"   ❌ Error on Post #{t['id']}: {e}")

    if as_json:
        print_json({"batch_results": results})
    else:
        console.print(f"\n🎉 [bold green]Batch Expansion Complete![/bold green] Processed {len(results)} posts.")


def main():
    cli(obj={})


if __name__ == "__main__":
    main()
