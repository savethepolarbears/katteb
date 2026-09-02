"""Output formatters for Katteb CLI (Rich console tables + JSON output)."""

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def print_json(data: Any) -> None:
    """Print standard serialized JSON to stdout."""
    if hasattr(data, "model_dump"):
        data = data.model_dump(exclude_none=True)
    console.print_json(json.dumps(data, default=str))


def format_credits(data: Any, as_json: bool = False) -> None:
    if as_json:
        print_json(data)
        return

    table = Table(title="💎 Katteb Credit Balance & Plan", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="dim")
    table.add_column("Value", style="bold green")

    table.add_row("Available Credits", str(data.credits or 0))
    table.add_row("Total Credits", str(data.credits_total or "N/A"))
    table.add_row("Plan Type", str(data.plan_type or "N/A").upper())
    table.add_row("Plan Tier", str(data.plan_tier or "N/A").upper())

    if data.api_usage_today:
        table.add_row("Heavy Ops Today", str(data.api_usage_today.get("heavy", 0)))
        table.add_row("Read Ops Today", str(data.api_usage_today.get("read", 0)))

    console.print(table)


def format_articles_list(articles: list[dict[str, Any]], as_json: bool = False) -> None:
    if as_json:
        print_json({"articles": articles})
        return

    table = Table(title="📄 Katteb Articles List", show_header=True, header_style="bold cyan")
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Topic", style="bold")
    table.add_column("Status", style="magenta")
    table.add_column("Word Count", justify="right")
    table.add_column("Created", style="dim")

    for art in articles:
        job_id = art.get("job_id") or art.get("id") or "N/A"
        topic = art.get("topic") or "N/A"
        status = art.get("status") or "N/A"
        wc = str(art.get("word_count") or "-")
        created = art.get("created_at") or "-"
        table.add_row(str(job_id), topic[:60], status, wc, created)

    console.print(table)


def format_article_get(data: Any, as_json: bool = False) -> None:
    if as_json:
        print_json(data)
        return

    status_color = "green" if data.status == "completed" else "yellow" if data.status == "processing" else "red"
    header = f"Job #{data.job_id} — [{status_color}]{(data.status or '').upper()}[/{status_color}]"

    content_preview = ""
    if data.content_html:
        from bs4 import BeautifulSoup

        try:
            soup = BeautifulSoup(data.content_html, "html.parser")
            content_preview = soup.get_text()[:300] + "..."
        except Exception:
            content_preview = data.content_html[:300] + "..."

    info = (
        f"[bold]Topic:[/bold] {data.topic}\n"
        f"[bold]Word Count:[/bold] {data.word_count or 'N/A'}\n"
        f"[bold]Meta Title:[/bold] {data.meta_title or 'N/A'}\n"
        f"[bold]Meta Description:[/bold] {data.meta_description or 'N/A'}\n"
        f"[bold]Featured Image:[/bold] {data.featured_image or 'N/A'}\n\n"
        f"[bold]Content Preview:[/bold]\n{content_preview}"
    )

    console.print(Panel(info, title=header, expand=False, border_style="cyan"))


def format_styles(styles: list[Any], as_json: bool = False) -> None:
    if as_json:
        print_json([s.model_dump() if hasattr(s, "model_dump") else s for s in styles])
        return

    table = Table(title="✍️ Writing Styles", show_header=True, header_style="bold cyan")
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Name", style="bold")
    table.add_column("Description", style="dim")
    table.add_column("Active")

    for s in styles:
        s_id = str(getattr(s, "id", "") or s.get("id", ""))
        s_name = getattr(s, "name", "") or s.get("name", "")
        s_desc = getattr(s, "description", "") or s.get("description", "") or "-"
        active = (
            "✅" if (getattr(s, "is_active", True) if hasattr(s, "is_active") else s.get("is_active", True)) else "❌"
        )
        table.add_row(s_id, s_name, s_desc[:50], active)

    console.print(table)


def format_brands(brands: list[Any], as_json: bool = False) -> None:
    if as_json:
        print_json([b.model_dump() if hasattr(b, "model_dump") else b for b in brands])
        return

    table = Table(title="🏢 Brands / Workspaces", show_header=True, header_style="bold cyan")
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Name", style="bold")
    table.add_column("URL", style="dim")

    for b in brands:
        b_id = str(getattr(b, "id", "") or b.get("id", ""))
        b_name = getattr(b, "name", "") or b.get("name", "")
        b_url = getattr(b, "url", "") or b.get("url", "") or "-"
        table.add_row(b_id, b_name, b_url)

    console.print(table)


def format_humanizer_detect(data: Any, as_json: bool = False) -> None:
    if as_json:
        print_json(data)
        return

    verdict_style = "green" if data.verdict == "likely_human" else "yellow" if data.verdict == "mixed" else "red"
    table = Table(title="🔍 AI Text Detection", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="dim")
    table.add_column("Value", style="bold")

    table.add_row("AI Probability", f"{data.ai_probability}%")
    table.add_row("Verdict", f"[{verdict_style}]{data.verdict}[/{verdict_style}]")
    table.add_row("Word Count", str(data.word_count or "N/A"))
    table.add_row("Credits Charged", str(data.credits_charged or 1))

    console.print(table)


def format_factcheck(data: Any, as_json: bool = False) -> None:
    if as_json:
        print_json(data)
        return

    verdict_style = "green" if data.verdict == "TRUE" else "red" if data.verdict == "FALSE" else "yellow"
    panel_content = (
        f"[bold]Verdict:[/bold] [{verdict_style}]{data.verdict}[/{verdict_style}]\n"
        f"[bold]Explanation:[/bold] {data.explanation}\n"
        f"[bold]Search Query:[/bold] {data.search_query or 'N/A'}\n"
    )
    if data.references:
        panel_content += "\n[bold]References:[/bold]\n"
        for ref in data.references:
            panel_content += f"  - [{ref.title or 'Source'}]({ref.url})\n"

    console.print(Panel(panel_content, title="🔎 Fact-Check Verification", expand=False, border_style="cyan"))
