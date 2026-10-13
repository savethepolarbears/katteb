"""Google Search Console striking-distance detector, 30-day post-expansion impact auditor, and Activepieces Content Refresh Queue formatter."""

from __future__ import annotations

import json
import logging
import subprocess  # nosec B404
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from katteb.telemetry import get_telemetry_events, log_telemetry_event
from katteb.wordpress import FLEET_SITE_PROFILES, resolve_fleet_profile, validate_site_alias

logger = logging.getLogger("katteb.gsc_feedback")

CONTENT_REFRESH_QUEUE_TABLE_ID = "Sr3ff44M4Fs6PCGaDdSAG"
DEFAULT_GOG_ACCOUNT = "klkroeger@gmail.com"
DEFAULT_GOG_CLIENT = "bbm-analytics-cloud"

GSC_SITE_PROPERTY_MAP: dict[str, str] = {
    alias: f"sc-domain:{profile['domain']}"
    for alias, profile in FLEET_SITE_PROFILES.items()
    if profile.get("domain")
}


def resolve_gsc_property(site: str) -> str:
    """Resolve a WordPress fleet site alias to its canonical Google Search Console property URI."""
    validated = validate_site_alias(site)
    if validated in GSC_SITE_PROPERTY_MAP:
        return GSC_SITE_PROPERTY_MAP[validated]
    profile = resolve_fleet_profile(validated)
    if profile and profile.get("domain"):
        return f"sc-domain:{profile['domain']}"
    clean = validated.removeprefix("sc-domain:").removeprefix("https://").removeprefix("http://").strip("/")
    if "." in clean:
        return f"sc-domain:{clean}"
    return f"sc-domain:{clean}.com"


def _parse_gsc_row(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a raw GSC analytics row into standard keys (query, page, clicks, impressions, ctr, position)."""
    keys = raw.get("keys") or []
    query = str(raw.get("query") or (keys[0] if len(keys) >= 1 else "")).strip()
    page = str(raw.get("page") or raw.get("url") or (keys[1] if len(keys) >= 2 else "")).strip()
    clicks = int(float(raw.get("clicks", 0) or 0))
    impressions = int(float(raw.get("impressions", 0) or 0))
    ctr = float(raw.get("ctr", 0.0) or 0.0)
    if ctr > 1.0:
        ctr = round(ctr / 100.0, 4)
    position = round(float(raw.get("position", 0.0) or 0.0), 2)
    return {
        "query": query,
        "page": page,
        "clicks": clicks,
        "impressions": impressions,
        "ctr": round(ctr, 4),
        "position": position,
    }


def compute_opportunity_score(impressions: int, position: float, ctr: float) -> float:
    """Compute a striking-distance priority score weighting impressions, proximity to top-3, and CTR headroom."""
    if impressions <= 0 or position <= 0:
        return 0.0
    proximity_weight = max(1.0, 16.0 - min(position, 15.0))
    ctr_headroom = max(0.1, 1.0 - min(ctr, 0.25))
    return round(impressions * proximity_weight * ctr_headroom, 2)


def format_refresh_queue_records(
    site: str,
    opportunities: list[dict[str, Any]],
    table_id: str = CONTENT_REFRESH_QUEUE_TABLE_ID,
) -> dict[str, Any]:
    """Format striking-distance opportunities into Activepieces Content Refresh Queue records."""
    gsc_prop = resolve_gsc_property(site)
    now_iso = datetime.now(timezone.utc).isoformat()
    records: list[dict[str, Any]] = []
    for item in opportunities:
        pos = float(item.get("position", 0.0) or 0.0)
        ctr = float(item.get("ctr", 0.0) or 0.0)
        if pos <= 8.0 and ctr < 0.03:
            action = "rankmath_title_meta_ctr_refresh"
        elif pos > 8.0:
            action = "katteb_section_and_faq_expansion"
        else:
            action = "content_and_internal_link_refresh"

        records.append(
            {
                "table_id": table_id,
                "site": site,
                "gsc_property": gsc_prop,
                "query": item.get("query", ""),
                "page_url": item.get("page", ""),
                "post_id": item.get("post_id"),
                "position": pos,
                "impressions": int(item.get("impressions", 0) or 0),
                "clicks": int(item.get("clicks", 0) or 0),
                "ctr": round(ctr, 4),
                "opportunity_score": float(item.get("opportunity_score", 0.0) or 0.0),
                "recommended_action": action,
                "status": "queued",
                "queued_at": now_iso,
            }
        )

    return {
        "table_id": table_id,
        "table_name": "Content Refresh Queue",
        "site": site,
        "gsc_property": gsc_prop,
        "record_count": len(records),
        "records": records,
    }


class GSCFeedbackAuditor:
    """Queries Google Search Console via gog CLI and audits 30-day post-expansion SEO impact."""

    def __init__(
        self,
        gog_account: str = DEFAULT_GOG_ACCOUNT,
        gog_client: str = DEFAULT_GOG_CLIENT,
    ):
        self.gog_account = gog_account
        self.gog_client = gog_client

    def fetch_gsc_analytics(
        self,
        site: str,
        days: int = 28,
        limit: int = 250,
        rows_override: list[dict[str, Any]] | None = None,
        input_file: str | Path | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch GSC search analytics rows via gog CLI or from an explicit override / JSON file."""
        if rows_override is not None:
            return [_parse_gsc_row(r) for r in rows_override if isinstance(r, dict)]

        if input_file is not None:
            file_path = Path(input_file)
            if not file_path.is_file():
                raise FileNotFoundError(f"GSC analytics input file not found at '{file_path}'.")
            raw_json = json.loads(file_path.read_text(encoding="utf-8"))
            raw_rows = raw_json.get("rows", raw_json) if isinstance(raw_json, dict) else raw_json
            return [_parse_gsc_row(r) for r in raw_rows if isinstance(r, dict)]

        gsc_property = resolve_gsc_property(site)
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=max(1, days))

        cmd = [
            "gog",
            "--account",
            self.gog_account,
            "--client",
            self.gog_client,
            "searchconsole",
            "query",
            gsc_property,
            "--start-date",
            start_date.isoformat(),
            "--end-date",
            end_date.isoformat(),
            "--dimensions",
            "query,page",
            "--limit",
            str(limit),
            "--json",
            "--results-only",
            "--no-input",
        ]
        res = subprocess.run(  # nosec B603
            cmd,
            shell=False,
            capture_output=True,
            text=True,
            timeout=45,
        )
        if res.returncode != 0:
            raise RuntimeError(f"gog searchconsole query failed for {gsc_property}: {res.stderr or res.stdout}")

        stdout_text = res.stdout.strip()
        if not stdout_text:
            return []
        parsed = json.loads(stdout_text)
        rows = parsed.get("rows", parsed) if isinstance(parsed, dict) else parsed
        if not isinstance(rows, list):
            return []
        return [_parse_gsc_row(r) for r in rows if isinstance(r, dict)]

    def detect_striking_distance_queries(
        self,
        site: str,
        days: int = 28,
        min_position: float = 4.0,
        max_position: float = 15.0,
        min_impressions: int = 50,
        limit: int = 25,
        rows_override: list[dict[str, Any]] | None = None,
        input_file: str | Path | None = None,
    ) -> list[dict[str, Any]]:
        """Filter GSC analytics to striking-distance queries (pos 4.0-15.0, impressions >= 50) ranked by opportunity."""
        rows = self.fetch_gsc_analytics(
            site=site,
            days=days,
            limit=max(250, limit * 5),
            rows_override=rows_override,
            input_file=input_file,
        )
        opportunities: list[dict[str, Any]] = []
        for row in rows:
            pos = row["position"]
            impr = row["impressions"]
            if min_position <= pos <= max_position and impr >= min_impressions:
                score = compute_opportunity_score(impr, pos, row["ctr"])
                enriched = {
                    **row,
                    "site": site,
                    "opportunity_score": score,
                }
                opportunities.append(enriched)

        opportunities.sort(key=lambda r: (r["opportunity_score"], r["impressions"]), reverse=True)
        return opportunities[:limit]

    def audit_expanded_posts_impact(
        self,
        site: str | None = None,
        min_days_age: int = 30,
        log_path: str | Path | None = None,
        rows_override: list[dict[str, Any]] | None = None,
        input_file: str | Path | None = None,
        record_telemetry: bool = True,
    ) -> dict[str, Any]:
        """Audit historical post_expansion telemetry records (>= min_days_age) against GSC search analytics."""
        events = get_telemetry_events(limit=1000, log_path=log_path)
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=max(0, min_days_age))

        eligible_expansions: list[dict[str, Any]] = []
        for ev in events:
            if ev.get("event_type") != "post_expansion" or not ev.get("success", False):
                continue
            if site and ev.get("site") != site:
                continue

            ts_raw = ev.get("timestamp", "")
            try:
                ev_dt = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                if ev_dt.tzinfo is None:
                    ev_dt = ev_dt.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                ev_dt = now

            if min_days_age <= 0 or ev_dt <= cutoff:
                eligible_expansions.append(ev)

        gsc_rows: list[dict[str, Any]] = []
        target_site = site or (eligible_expansions[0].get("site") if eligible_expansions else None)
        if target_site and (rows_override is not None or input_file is not None):
            gsc_rows = self.fetch_gsc_analytics(
                site=str(target_site),
                rows_override=rows_override,
                input_file=input_file,
            )
        elif target_site and eligible_expansions:
            try:
                gsc_rows = self.fetch_gsc_analytics(site=str(target_site))
            except Exception as exc:
                logger.warning("Could not fetch live GSC analytics for '%s': %s", target_site, exc)
                gsc_rows = []

        audited_posts: list[dict[str, Any]] = []
        refresh_candidates: list[dict[str, Any]] = []

        for exp in eligible_expansions:
            title = str(exp.get("title") or "").strip()
            post_id = exp.get("post_id")
            exp_site = str(exp.get("site") or site or "viatravelers")
            title_tokens = [
                t.lower() for t in title.split() if len(t) >= 4 and t.lower() not in {"guide", "best", "complete"}
            ]

            matched_rows = []
            for r in gsc_rows:
                haystack = f"{r.get('query', '')} {r.get('page', '')}".lower()
                if title and (
                    title.lower() in haystack
                    or (title_tokens and sum(1 for tok in title_tokens if tok in haystack) >= max(1, len(title_tokens) // 2))
                ):
                    matched_rows.append(r)

            total_impressions = sum(r["impressions"] for r in matched_rows)
            total_clicks = sum(r["clicks"] for r in matched_rows)
            avg_ctr = round(total_clicks / total_impressions, 4) if total_impressions > 0 else 0.0
            avg_position = (
                round(sum(r["position"] for r in matched_rows) / len(matched_rows), 2) if matched_rows else 0.0
            )

            needs_refresh = total_impressions >= 50 and (avg_ctr < 0.02 or (4.0 <= avg_position <= 15.0))
            audit_entry = {
                "site": exp_site,
                "post_id": post_id,
                "title": title,
                "expanded_at": exp.get("timestamp"),
                "previous_word_count": exp.get("previous_word_count", 0),
                "new_word_count": exp.get("new_word_count", 0),
                "impressions": total_impressions,
                "clicks": total_clicks,
                "ctr": avg_ctr,
                "avg_position": avg_position,
                "matched_queries": len(matched_rows),
                "needs_refresh": needs_refresh,
                "wp_admin_edit_url": exp.get("wp_admin_edit_url"),
            }
            audited_posts.append(audit_entry)
            if needs_refresh:
                refresh_candidates.append(
                    {
                        "post_id": post_id,
                        "query": matched_rows[0]["query"] if matched_rows else title,
                        "page": matched_rows[0]["page"] if matched_rows else "",
                        "impressions": total_impressions,
                        "clicks": total_clicks,
                        "ctr": avg_ctr,
                        "position": avg_position if avg_position > 0 else 10.0,
                        "opportunity_score": compute_opportunity_score(
                            total_impressions, avg_position if avg_position > 0 else 10.0, avg_ctr
                        ),
                    }
                )

        queue_payload = (
            format_refresh_queue_records(str(target_site or "viatravelers"), refresh_candidates)
            if refresh_candidates
            else {
                "table_id": CONTENT_REFRESH_QUEUE_TABLE_ID,
                "table_name": "Content Refresh Queue",
                "site": target_site,
                "record_count": 0,
                "records": [],
            }
        )

        summary = {
            "success": True,
            "site": target_site,
            "min_days_age": min_days_age,
            "audited_count": len(audited_posts),
            "needs_refresh_count": len(refresh_candidates),
            "audited_posts": audited_posts,
            "refresh_queue": queue_payload,
        }

        if record_telemetry and audited_posts:
            try:
                log_telemetry_event(
                    event_type="gsc_re_audit",
                    data={
                        "site": target_site,
                        "min_days_age": min_days_age,
                        "audited_count": len(audited_posts),
                        "needs_refresh_count": len(refresh_candidates),
                        "success": True,
                    },
                    log_path=log_path,
                )
            except Exception as exc:
                logger.warning("Failed to record gsc_re_audit telemetry event: %s", exc)

        return summary
