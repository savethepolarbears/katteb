"""WordPress Fleet Integration for auditing and expanding low-word-count posts via WP-CLI."""

import base64
import datetime
import hashlib
import html
import json
import logging
import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from katteb.client import KattebClient
from katteb.models import ArticleGetResponse, PreflightResult
from katteb.queue import KattebQueueManager

logger = logging.getLogger("katteb.wordpress")

# BBM WordPress root resolution (configurable via BBM_WP_ROOT environment variable)
DEFAULT_BBM_WP_ROOT = Path.home() / "Projects" / "bbm-wordpress"
BBM_WP_ROOT = Path(os.getenv("BBM_WP_ROOT", str(DEFAULT_BBM_WP_ROOT))).expanduser()
WP_GLOBAL_SCRIPT = BBM_WP_ROOT / "scripts" / "wp-cli" / "wp-global"

# Common country name to ISO 3166-1 alpha-2 map for Katteb 'country' param
COUNTRY_ISO_MAP = {
    "united states": "us",
    "usa": "us",
    "us": "us",
    "united kingdom": "gb",
    "uk": "gb",
    "great britain": "gb",
    "canada": "ca",
    "australia": "au",
    "germany": "de",
    "france": "fr",
    "spain": "es",
    "italy": "it",
    "netherlands": "nl",
    "switzerland": "ch",
    "austria": "at",
    "greece": "gr",
    "portugal": "pt",
    "belgium": "be",
    "japan": "jp",
    "china": "cn",
    "india": "in",
    "thailand": "th",
    "vietnam": "vn",
    "indonesia": "id",
    "philippines": "ph",
    "laos": "la",
    "cambodia": "kh",
    "myanmar": "mm",
    "singapore": "sg",
    "malaysia": "my",
    "mexico": "mx",
    "colombia": "co",
    "peru": "pe",
    "brazil": "br",
    "argentina": "ar",
    "chile": "cl",
    "uruguay": "uy",
    "bolivia": "bo",
    "south africa": "za",
    "egypt": "eg",
    "morocco": "ma",
    "tanzania": "tz",
    "kenya": "ke",
    "oman": "om",
    "united arab emirates": "ae",
    "uae": "ae",
    "saudi arabia": "sa",
    "qatar": "qa",
    "jordan": "jo",
    "turkey": "tr",
    "croatia": "hr",
    "bulgaria": "bg",
    "georgia": "ge",
    "mongolia": "mn",
    "norway": "no",
    "sweden": "se",
    "denmark": "dk",
    "finland": "fi",
    "ireland": "ie",
    "new zealand": "nz",
    "czech republic": "cz",
    "hungary": "hu",
    "poland": "pl",
    "romania": "ro",
    "serbia": "rs",
    "slovakia": "sk",
}

# Canonical Fleet site profiles across all flagship digital publishing properties
FLEET_SITE_PROFILES: dict[str, dict[str, Any]] = {
    "destinations-ai": {
        "name": "Destinations AI",
        "domain": "destinations.ai",
        "default_post_type": "destinations",
        "wp_cli_alias": "@destinations-ai.prod",
    },
    "viatravelers": {
        "name": "ViaTravelers",
        "domain": "viatravelers.com",
        "default_post_type": "post",
        "wp_cli_alias": "@viatravelers.prod",
    },
    "santorinisecrets": {
        "name": "Santorini Secrets",
        "domain": "santorinisecrets.com",
        "default_post_type": "post",
        "wp_cli_alias": "@santorinisecrets.prod",
    },
    "amsterdamlocalgems": {
        "name": "Amsterdam Local Gems",
        "domain": "amsterdamlocalgems.com",
        "default_post_type": "post",
        "wp_cli_alias": "@amsterdamlocalgems.prod",
    },
    "parkervillas": {
        "name": "Parker Villas",
        "domain": "parkervillas.com",
        "default_post_type": "post",
        "wp_cli_alias": "@parkervillas.prod",
    },
    "realjourneytravels": {
        "name": "Real Journey Travels",
        "domain": "realjourneytravels.com",
        "default_post_type": "post",
        "wp_cli_alias": "@realjourneytravels.prod",
    },
    "everythingaboutgermany": {
        "name": "Everything About Germany",
        "domain": "everythingaboutgermany.com",
        "default_post_type": "post",
        "wp_cli_alias": "@everythingaboutgermany.prod",
        "aliases": ["everythingaboutgermany.de", "everythingaboutgermany.com"],
    },
    "gearbuddha": {
        "name": "Gear Buddha",
        "domain": "gearbuddha.com",
        "default_post_type": "gear",
        "wp_cli_alias": "@gearbuddha.prod",
    },
    "theimpactinvestor": {
        "name": "The Impact Investor",
        "domain": "theimpactinvestor.com",
        "default_post_type": "post",
        "wp_cli_alias": "@theimpactinvestor.prod",
    },
    "blackbearmedia": {
        "name": "Black Bear Media",
        "domain": "blackbearmedia.io",
        "default_post_type": "post",
        "wp_cli_alias": "@blackbearmedia.prod",
    },
    "traveleering": {
        "name": "Traveleering",
        "domain": "traveleering.com",
        "default_post_type": "post",
        "wp_cli_alias": "@traveleering.prod",
    },
    "workfromhomereviews": {
        "name": "Work From Home Reviews",
        "domain": "workfromhomereviews.net",
        "default_post_type": "post",
        "wp_cli_alias": "@workfromhomereviews.prod",
    },
    "reluctantfrugalist": {
        "name": "Reluctant Frugalist",
        "domain": "reluctantfrugalist.com",
        "default_post_type": "post",
        "wp_cli_alias": "@reluctantfrugalist.prod",
    },
    "paristopten": {
        "name": "Paris Top Ten",
        "domain": "paristopten.com",
        "default_post_type": "post",
        "wp_cli_alias": "@paristopten.prod",
    },
    "lovinglifeinspain": {
        "name": "Loving Life in Spain",
        "domain": "lovinglifeinspain.com",
        "default_post_type": "post",
        "wp_cli_alias": "@lovinglifeinspain.prod",
    },
}


def validate_site_alias(site: str) -> str:
    """Validate site alias to ensure it is alphanumeric with dashes/dots, preventing shell injection."""
    if not site or not isinstance(site, str):
        raise ValueError("Site alias must be a non-empty string.")
    cleaned = site.strip()
    check_str = cleaned[1:] if cleaned.startswith("@") else cleaned

    if not re.match(r"^[a-zA-Z0-9_.-]+$", check_str):
        raise ValueError(f"Invalid site alias '{site}': contains forbidden characters.")
    return cleaned


def resolve_fleet_profile(site_or_alias: str) -> dict[str, Any] | None:
    """Resolve a site name, domain, or WP-CLI alias to its canonical fleet profile."""
    if not site_or_alias or not isinstance(site_or_alias, str):
        return None
    clean = site_or_alias.strip().lower()
    if clean.startswith("@"):
        clean = clean[1:]
    if clean.endswith(".prod"):
        clean = clean[:-5]

    if clean in FLEET_SITE_PROFILES:
        return FLEET_SITE_PROFILES[clean]

    for profile in FLEET_SITE_PROFILES.values():
        if profile.get("domain", "").lower() == clean:
            return profile
        for alias in profile.get("aliases", []):
            if alias.lower() == clean:
                return profile

    return None


def validate_and_authorize_site_alias(site: str, allow_custom: bool = False) -> str:
    """Validate alias syntax and authorize against known fleet site profiles."""
    validated = validate_site_alias(site)
    profile = resolve_fleet_profile(validated)
    if profile:
        return str(profile.get("wp_cli_alias", f"@{validated}.prod"))
    if allow_custom:
        return f"@{validated}.prod" if not validated.startswith("@") else validated
    raise PermissionError(
        f"Site '{site}' is not an authorized fleet profile. Choose from: {sorted(list(FLEET_SITE_PROFILES.keys()))}"
    )


def resolve_country_code(country_name: str | None) -> str:
    """Map country string to ISO alpha-2 code, defaulting to 'us'."""
    if not country_name:
        return "us"
    clean = country_name.strip().lower()
    return COUNTRY_ISO_MAP.get(clean, "us")


def run_wp_cli(alias: str, command: str | list[str], timeout: int = 45, allow_custom: bool = False) -> str:
    """Execute a WP-CLI command via wp-global safely using structured argv list."""
    if not WP_GLOBAL_SCRIPT.is_file():
        raise FileNotFoundError(
            f"WP-CLI wrapper script not found at '{WP_GLOBAL_SCRIPT}'. "
            "Set BBM_WP_ROOT environment variable to the root directory of your WordPress repository."
        )

    target_alias = validate_and_authorize_site_alias(alias, allow_custom=allow_custom)
    cli_subcmd = command if isinstance(command, list) else shlex.split(command)

    cmd_args = ["bash", str(WP_GLOBAL_SCRIPT), target_alias, *cli_subcmd]

    res = subprocess.run(  # nosec B603
        cmd_args,
        shell=False,
        cwd=str(BBM_WP_ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if res.returncode != 0:
        raise RuntimeError(f"WP-CLI execution failed on {alias}:\n{res.stderr or res.stdout}")
    return res.stdout.strip()


def run_wp_eval(alias: str, php_code: str, timeout: int = 60, allow_custom: bool = False) -> Any:
    """Execute PHP code on remote site via base64 wrapper and return parsed JSON result."""
    b64_code = base64.b64encode(php_code.encode("utf-8")).decode("utf-8")
    runner_code = f"eval(base64_decode('{b64_code}'));"
    out = run_wp_cli(alias, ["eval", runner_code], timeout=timeout, allow_custom=allow_custom)
    try:
        return json.loads(out)
    except Exception:
        return out


def is_error_payload(text: str) -> tuple[bool, str]:
    """Check whether text represents a provider error response (JSON or HTML error page)."""
    if not text or not text.strip():
        return True, "Empty content payload received."

    stripped = text.strip()

    # 1. JSON error payload
    if (stripped.startswith("{") and stripped.endswith("}")) or (stripped.startswith("[") and stripped.endswith("]")):
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict) and (
                parsed.get("status") == "error" or parsed.get("success") is False or "error" in parsed
            ):
                err_detail = parsed.get("error") or parsed.get("message") or str(parsed)
                return True, f"JSON error payload from provider: {err_detail}"
        except (json.JSONDecodeError, ValueError):
            pass

    # 2. IP Authorization error signatures
    if "Error (401)" in text or "Your IP is not authorized" in text or "ip_auth_required" in text:
        return True, (
            "Katteb IP authorization error: 'Your IP is not authorized to make this request.' "
            "Add public IP at https://app.katteb.com/api_access"
        )

    # 3. Server 5xx / HTML error pages
    lower = text.lower()
    if any(sig in lower for sig in ["<title>500", "<title>502", "<title>503", "<title>504", "<title>error"]):
        return True, "HTML server error page received from provider."

    if any(sig in lower for sig in ["fatal error:", "parse error:", "uncaught exception", "502 bad gateway"]):
        return True, f"PHP/Server fatal error detected in payload: {text[:200]}"

    # 4. Short error payload (< 400 chars with 'Error' or 'failed')
    if len(stripped) < 400 and (
        "error (" in lower or "fatal error" in lower or ("error" in lower and "failed" in lower)
    ):
        return True, f"Short error payload detected: {stripped}"

    return False, ""


def sanitize_meta_description(meta_desc: str, max_chars: int = 160) -> str:
    """Sanitize meta description by removing CSS styles, scripts, HTML tags, and truncating cleanly."""
    if not meta_desc:
        return ""

    soup = BeautifulSoup(meta_desc, "html.parser")
    for elem in soup(["style", "script", "template"]):
        elem.decompose()

    text = soup.get_text(separator=" ", strip=True)
    text = html.unescape(text)

    # Remove any stray CSS selector rules (e.g. .class { ... } or #id { ... })
    text = re.sub(r"[.#a-zA-Z0-9_-]+\s*\{[^}]*\}", "", text)
    # Remove bracketed CSS remnant tags or style fragments
    text = re.sub(r"\[/?style[^\]]*\]", "", text, flags=re.IGNORECASE)
    # Remove CSS property remnants
    text = re.sub(r"[a-zA-Z-]+:\s*[^;]+;", "", text)
    # Collapse multiple whitespace
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > max_chars:
        truncated = text[:max_chars].rsplit(" ", 1)[0]
        return truncated if truncated else text[:max_chars]
    return text


class ContentQualityError(RuntimeError):
    """Raised when generated AI content fails editorial quality gates or contains placeholder tokens."""

    def __init__(self, message: str, errors: list[str] | None = None):
        super().__init__(message)
        self.errors = errors or []


def validate_generated_content(html_content: str, target_word_count: int = 1500) -> list[str]:
    """Validate that generated HTML content satisfies semantic heading structure, word count, and has no placeholder leakage."""
    errors: list[str] = []
    if not html_content or not html_content.strip():
        return ["Content is completely empty."]

    # Check for error payload first
    is_err, err_msg = is_error_payload(html_content)
    if is_err:
        return [f"Content is an error response, not article content: {err_msg}"]

    # Parse with BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")

    # Decompose hidden or non-content tags before text & heading checks
    for elem in soup(["script", "style", "template", "noscript", "svg"]):
        elem.decompose()

    # Extract visible text and compute actual word count
    clean_text = soup.get_text(separator=" ", strip=True)
    words = clean_text.split()
    actual_wc = len(words)

    # Word count validation against target
    if actual_wc < 50:
        errors.append(f"Content is excessively short: found only {actual_wc} visible words (minimum 50 required).")
    elif target_word_count >= 500 and actual_wc < int(target_word_count * 0.4):
        errors.append(
            f"Content length failure: found {actual_wc} visible words, falling below required floor for target {target_word_count}."
        )

    # Semantic Heading check
    headings_h2 = [
        h.get_text(strip=True)
        for h in soup.find_all("h2")
        if h.parent and h.parent.name not in ("pre", "code", "template") and h.get_text(strip=True)
    ]
    headings_h3 = [
        h.get_text(strip=True)
        for h in soup.find_all("h3")
        if h.parent and h.parent.name not in ("pre", "code", "template") and h.get_text(strip=True)
    ]

    if target_word_count >= 1000:
        if len(headings_h2) < 2:
            errors.append(
                f"Content lacks sufficient semantic H2 structure: found {len(headings_h2)} valid non-empty <h2> tags (minimum 2 required)."
            )
        if len(headings_h3) < 1:
            errors.append(
                f"Content lacks semantic H3 subsections: found {len(headings_h3)} valid non-empty <h3> tags (minimum 1 required)."
            )

    # Broadened placeholder check
    bracket_placeholders = re.findall(
        r"\[(City|Country|Name|Insert|Destination|State|Region|URL|Link|Date|Phone|Company|Brand|TODO|TBD|X)\]",
        html_content,
        re.IGNORECASE,
    )
    if bracket_placeholders:
        unique_matches = sorted(list(set(bracket_placeholders)))
        errors.append(f"Detected unreplaced placeholder token(s): {', '.join(unique_matches)}")

    if re.search(r"\[insert\s+[^\]]*\]", html_content, re.IGNORECASE):
        errors.append("Detected unreplaced '[insert ...]' placeholder tag in content.")

    if re.search(r"\{\{[a-zA-Z0-9_.\s-]+\}\}", html_content):
        errors.append("Detected unreplaced mustache/handlebars variable token '{{...}}'.")

    if re.search(r"%(CITY|COUNTRY|NAME|STATE|URL|LINK|DATE|BRAND)%", html_content, re.IGNORECASE):
        errors.append("Detected unreplaced percent-delimited placeholder token '%...%'.")

    if re.search(r"<<[a-zA-Z0-9_.\s-]+>>", html_content):
        errors.append("Detected unreplaced angle-bracket placeholder token '<<...>>'.")

    if re.search(r"\bINSERT\s+[A-Z\s_]+\s+HERE\b", html_content, re.IGNORECASE):
        errors.append("Detected unreplaced 'INSERT ... HERE' editorial instruction tag.")

    if re.search(r"https?://(?:www\.)?example\.com", html_content, re.IGNORECASE):
        errors.append("Detected unreplaced placeholder URL pointing to 'example.com'.")

    ai_phrases = [
        "as an ai language model",
        "i cannot provide",
        "lorem ipsum",
        "here is your generated article",
        "here is an expanded version",
    ]
    lower_html = html_content.lower()
    for phrase in ai_phrases:
        if phrase in lower_html:
            errors.append(f"Detected prohibited AI boilerplate / placeholder phrase: '{phrase}'.")

    return errors


def generate_expansion_receipt(
    site: str,
    results: list[dict[str, Any]],
    output_dir: str = "receipts",
    safe_root: Path | str | None = None,
) -> str:
    """Generate and write Markdown and JSON audit receipts for a batch expansion run."""
    allowed_root = Path(safe_root).resolve() if safe_root else Path.cwd().resolve()
    target_dir = (
        (allowed_root / output_dir).resolve() if not Path(output_dir).is_absolute() else Path(output_dir).resolve()
    )

    default_app_root = (Path.home() / ".katteb" / "receipts").resolve()
    is_safe = False
    for safe_base in [allowed_root, default_app_root]:
        try:
            target_dir.relative_to(safe_base)
            is_safe = True
            break
        except ValueError:
            continue

    if not is_safe:
        target_dir = allowed_root / "receipts"

    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    base_filename = f"expand-receipt-{timestamp}"
    md_file_path = target_dir / f"{base_filename}.md"
    json_file_path = target_dir / f"{base_filename}.json"

    results_str = json.dumps(results, sort_keys=True, default=str)
    audit_hash = hashlib.sha256(results_str.encode("utf-8")).hexdigest()[:16]

    def escape_cell(val: Any) -> str:
        s = str(val or "").replace("|", "\\|").replace("\n", " ").strip()
        return s if s else "N/A"

    lines = [
        f"# Katteb Content Expansion Receipt — {site}",
        "",
        f"- **Site**: `{site}`",
        f"- **Timestamp (UTC)**: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **Audit Hash**: `{audit_hash}`",
        f"- **Total Posts Processed**: {len(results)}",
        "",
        "## Summary of Processed Posts",
        "",
        "| Post ID | Title | Previous Words | New Words | Delta | Status | RankMath SEO |",
        "|---------|-------|----------------|-----------|-------|--------|--------------|",
    ]

    for r in results:
        pid = escape_cell(r.get("post_id"))
        title = escape_cell(r.get("title"))
        prev_w = r.get("previous_word_count", 0)
        new_w = r.get("new_word_count", 0)
        delta = f"+{new_w - prev_w}" if new_w >= prev_w else f"{new_w - prev_w}"
        status_text = "✅ Updated" if r.get("success") else f"❌ Failed ({escape_cell(r.get('error', 'Unknown'))})"
        has_seo = "Yes" if r.get("meta_title") else "No"
        lines.append(f"| {pid} | {title} | {prev_w} | {new_w} | {delta} | {status_text} | {has_seo} |")

    lines.append("")
    lines.append("---")
    lines.append("*Receipt auto-generated by Katteb WordPressFleetManager*")
    lines.append("")

    md_file_path.write_text("\n".join(lines), encoding="utf-8")

    json_payload = {
        "site": site,
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "audit_hash": audit_hash,
        "total_posts": len(results),
        "results": results,
    }
    json_file_path.write_text(json.dumps(json_payload, indent=2, default=str), encoding="utf-8")

    return str(md_file_path)


class WordPressFleetManager:
    """Manages post auditing and AI content updates for WordPress fleet sites."""

    def __init__(self, client: KattebClient | None = None):
        self.client = client or KattebClient()
        self.queue = KattebQueueManager(self.client)

    def check_site_connectivity(self, site: str, allow_custom: bool = False) -> PreflightResult:
        """Check if WP-CLI can connect to the target fleet site and return typed PreflightResult."""
        try:
            validate_and_authorize_site_alias(site, allow_custom=allow_custom)
        except PermissionError as e:
            return PreflightResult(
                success=False,
                site=site,
                category="unauthorized_alias",
                message=str(e),
                exit_code=1,
            )
        except ValueError as e:
            return PreflightResult(
                success=False,
                site=site,
                category="invalid_alias",
                message=str(e),
                exit_code=1,
            )

        try:
            out = run_wp_cli(site, ["core", "version"], timeout=15, allow_custom=allow_custom)
            return PreflightResult(
                success=True,
                site=site,
                category="ok",
                message=f"Connected to WordPress core {out}",
                version=out,
                exit_code=0,
            )
        except subprocess.TimeoutExpired:
            return PreflightResult(
                success=False,
                site=site,
                category="timeout",
                message=f"Connection to site '{site}' timed out after 15s.",
                exit_code=124,
            )
        except Exception as e:
            msg = str(e)
            category = "ssh_error" if "ssh" in msg.lower() or "permission denied" in msg.lower() else "wp_error"
            return PreflightResult(
                success=False,
                site=site,
                category=category,
                message=msg,
                exit_code=1,
            )

    def audit_low_word_posts(
        self,
        site: str = "destinations-ai",
        post_types: list[str] | None = None,
        max_words: int = 400,
        status: str = "publish,draft",
    ) -> list[dict[str, Any]]:
        """Audit all posts on target site having word count below max_words."""
        pts = post_types or ["destinations", "post", "gear", "restaurant", "page"]
        pts_json = json.dumps(pts)
        status_arr = [s.strip() for s in status.split(",")]
        status_json = json.dumps(status_arr)

        b64_pts = base64.b64encode(pts_json.encode("utf-8")).decode("utf-8")
        b64_statuses = base64.b64encode(status_json.encode("utf-8")).decode("utf-8")
        safe_max_words = int(max_words)

        # Construct PHP query script using base64 encoded parameters to eliminate injection vectors
        php_template = """
        global $wpdb;
        $pts = json_decode(base64_decode('__B64_PTS__'), true);
        $statuses = json_decode(base64_decode('__B64_STATUSES__'), true);
        $status_in = implode("','", array_map('esc_sql', $statuses));

        $low_posts = array();
        foreach ($pts as $pt) {
            $posts = $wpdb->get_results("
                SELECT ID, post_title, post_name, post_status, post_type, post_content
                FROM {$wpdb->posts}
                WHERE post_type = '" . esc_sql($pt) . "' AND post_status IN ('$status_in')
            ");

            foreach ($posts as $p) {
                $clean = trim(preg_replace('/\\s+/', ' ', strip_tags($p->post_content)));
                $wc = empty($clean) ? 0 : str_word_count($clean);

                if ($wc < __SAFE_MAX_WORDS__) {
                    $country = get_post_meta($p->ID, 'country', true) ?: '';
                    $region = get_post_meta($p->ID, 'region', true) ?: '';
                    $city = get_post_meta($p->ID, 'city', true) ?: get_post_meta($p->ID, 'city_name', true) ?: '';
                    $tg = get_post_meta($p->ID, 'travel_guide', true) ?: '';
                    $tg_wc = empty($tg) ? 0 : str_word_count(strip_tags($tg));

                    $low_posts[] = array(
                        'id' => (int)$p->ID,
                        'title' => $p->post_title,
                        'slug' => $p->post_name,
                        'post_type' => $p->post_type,
                        'status' => $p->post_status,
                        'content_wc' => $wc,
                        'travel_guide_wc' => $tg_wc,
                        'city' => $city,
                        'country' => $country,
                        'region' => $region
                    );
                }
            }
        }

        usort($low_posts, function($a, $b) { return $a['content_wc'] - $b['content_wc']; });
        echo json_encode($low_posts);
        """
        php_script = (
            php_template.replace("__B64_PTS__", b64_pts)
            .replace("__B64_STATUSES__", b64_statuses)
            .replace("__SAFE_MAX_WORDS__", str(safe_max_words))
        )

        result = run_wp_eval(site, php_script)
        if isinstance(result, list):
            return result
        return []

    def get_post_details(self, site: str, post_id: int) -> dict[str, Any]:
        """Fetch detailed post information including custom fields and meta."""
        safe_post_id = int(post_id)
        php_script = f"""
        $p = get_post({safe_post_id});
        if (!$p) {{
            echo json_encode(array('error' => 'Post not found'));
            exit;
        }}

        $meta_raw = get_post_meta({post_id});
        $meta = array();
        foreach ($meta_raw as $k => $v) {{
            if (!str_starts_with($k, '_edit_') && !str_starts_with($k, '_enclose')) {{
                $meta[$k] = maybe_unserialize($v[0]);
            }}
        }}

        $clean = trim(preg_replace('/\\s+/', ' ', strip_tags($p->post_content)));
        $wc = empty($clean) ? 0 : str_word_count($clean);

        $data = array(
            'id' => $p->ID,
            'title' => $p->post_title,
            'slug' => $p->post_name,
            'post_type' => $p->post_type,
            'status' => $p->post_status,
            'content' => $p->post_content,
            'word_count' => $wc,
            'meta' => $meta
        );
        echo json_encode($data);
        """
        res = run_wp_eval(site, php_script)
        from typing import cast

        if isinstance(res, dict):
            return cast(dict[str, Any], res)
        return {"error": str(res)}

    def expand_and_update_post(
        self,
        site: str,
        post_id: int,
        word_count: int = 1500,
        enhancements: list[str] | None = None,
        writing_style_id: int | None = None,
        brand_id: int | None = None,
        guidelines: str | None = None,
        dry_run: bool = False,
        allow_custom_alias: bool = False,
        on_status: Any | None = None,
    ) -> dict[str, Any]:
        """Generate expanded content with Katteb and update WordPress post."""
        # 1. Preflight site connectivity check BEFORE Katteb generation
        preflight = self.check_site_connectivity(site, allow_custom=allow_custom_alias)
        if not preflight.success:
            raise RuntimeError(f"Preflight check failed for site '{site}': {preflight.message} ({preflight.category})")

        # 2. Fetch existing post details
        post = self.get_post_details(site, post_id)
        if "error" in post:
            raise ValueError(f"Failed to fetch post {post_id}: {post['error']}")

        pt = post["post_type"]
        title = post["title"]
        meta = post.get("meta", {})
        city = meta.get("city") or meta.get("city_name") or title
        country = meta.get("country") or ""
        state = meta.get("state_name_full") or ""

        # Construct optimized Katteb generation topic based on post type
        if pt == "destinations":
            loc_parts = [p for p in [city, state, country] if p]
            loc_str = ", ".join(loc_parts)
            topic = f"Complete Travel Guide to {loc_str}: Best Things to Do, Itinerary, and Local Guide"
            default_guidelines = (
                f"Write an in-depth, authoritative travel guide for {loc_str}. "
                "Include sections on: Overview & Why Visit, Best Time to Visit, Top Attractions & Activities, "
                "Hidden Gems & Local Secrets, Where to Eat & Drink, Getting Around, and Practical Travel Tips. "
                "Use clean HTML structure with H2 and H3 headings, bullet points, and high-value insights."
            )
        elif pt == "gear":
            topic = f"{title}: Comprehensive In-Depth Review and Buyer's Guide"
            default_guidelines = (
                "Provide a thorough gear review with specs, performance testing, pros/cons, comparisons, and verdict."
            )
        else:
            topic = title
            default_guidelines = f"Expand this article on '{title}' into a comprehensive, highly engaging 2026 guide with actionable advice."

        final_guidelines = guidelines or default_guidelines
        target_country_code = resolve_country_code(country)
        final_enhancements = enhancements or ["tldr", "key_takeaways", "faq"]

        # 3. True Dry-Run: Return simulation result without Katteb API calls or WordPress mutations
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "post_id": post_id,
                "title": title,
                "topic": topic,
                "country": target_country_code,
                "word_count": word_count,
                "previous_word_count": post["word_count"],
                "current_word_count": post["word_count"],
                "enhancements": final_enhancements,
                "guidelines": final_guidelines,
                "simulated": True,
            }

        if on_status:
            on_status(f"Generating article for post #{post_id} ('{topic}') via Katteb API...")

        # 4. Generate via Katteb API
        import time

        start_time = time.time()
        article_res: ArticleGetResponse = self.queue.generate_and_wait(
            topic=topic,
            language="English",
            country=target_country_code,
            word_count=word_count,
            brand_id=brand_id,
            writing_style_id=writing_style_id,
            guidelines=final_guidelines,
            enhancements=final_enhancements,
            on_status=on_status,
        )

        new_html = article_res.content_html or ""
        meta_title = article_res.meta_title or title
        meta_desc = article_res.meta_description or ""

        # 5. Check provider error payloads
        is_err, err_msg = is_error_payload(new_html)
        if is_err:
            raise RuntimeError(f"Katteb generation returned an error payload: {err_msg}")

        # 6. Quality Gate: validate heading hierarchy, word count, and placeholder tokens
        val_errors = validate_generated_content(new_html, target_word_count=word_count)
        if val_errors:
            err_msg = "; ".join(val_errors)
            raise ContentQualityError(
                f"Generated content for post #{post_id} failed quality gates: {err_msg}",
                errors=val_errors,
            )

        # 7. Clean meta_description from stray css or tags
        meta_desc = sanitize_meta_description(meta_desc)

        if on_status:
            on_status(f"Article generated ({article_res.word_count} words). Updating WordPress post #{post_id}...")

        # 8. Update WordPress post via WP-CLI eval
        update_payload = {
            "post_id": post_id,
            "post_type": pt,
            "content": new_html,
            "meta_title": meta_title,
            "meta_desc": meta_desc,
            "focus_kw": city if pt == "destinations" else title,
        }

        update_json_str = json.dumps(update_payload)
        b64_payload = base64.b64encode(update_json_str.encode("utf-8")).decode("utf-8")

        php_update = f"""
        $raw = base64_decode('{b64_payload}');
        $data = json_decode($raw, true);
        $pid = (int)$data['post_id'];

        $update_res = wp_update_post(array(
            'ID' => $pid,
            'post_content' => $data['content'],
        ), true);

        if (is_wp_error($update_res)) {{
            echo json_encode(array('error' => $update_res->get_error_message()));
            exit;
        }}

        // Update travel_guide custom field if destinations CPT
        if ($data['post_type'] === 'destinations') {{
            update_post_meta($pid, 'travel_guide', $data['content']);
        }}

        // Update RankMath SEO metadata
        if (!empty($data['meta_title'])) {{
            update_post_meta($pid, 'rank_math_title', $data['meta_title']);
        }}
        if (!empty($data['meta_desc'])) {{
            update_post_meta($pid, 'rank_math_description', $data['meta_desc']);
        }}
        if (!empty($data['focus_kw'])) {{
            update_post_meta($pid, 'rank_math_focus_keyword', $data['focus_kw']);
        }}

        $updated_post = get_post($pid);
        $clean = trim(preg_replace('/\\s+/', ' ', strip_tags($updated_post->post_content)));
        $new_wc = str_word_count($clean);

        echo json_encode(array(
            'success' => true,
            'post_id' => $pid,
            'new_word_count' => $new_wc,
            'post_title' => $updated_post->post_title,
        ));
        """

        wp_res = run_wp_eval(site, php_update, allow_custom=allow_custom_alias)
        duration = round(time.time() - start_time, 2)

        if isinstance(wp_res, dict) and wp_res.get("error"):
            raise RuntimeError(f"WordPress post update failed: {wp_res['error']}")

        res_dict = {
            "success": True,
            "post_id": post_id,
            "title": title,
            "previous_word_count": post["word_count"],
            "new_word_count": wp_res.get("new_word_count") if isinstance(wp_res, dict) else article_res.word_count,
            "job_id": article_res.job_id,
            "meta_title": meta_title,
            "meta_description": meta_desc,
            "duration_seconds": duration,
        }

        try:
            from katteb.telemetry import log_telemetry_event

            log_telemetry_event(
                event_type="post_expansion",
                data={
                    "site": site,
                    "post_id": post_id,
                    "title": title,
                    "previous_word_count": res_dict["previous_word_count"],
                    "new_word_count": res_dict["new_word_count"],
                    "words_generated": max(
                        0, (res_dict["new_word_count"] or 0) - (res_dict["previous_word_count"] or 0)
                    ),
                    "estimated_credits": 1,
                    "duration_seconds": duration,
                    "success": True,
                },
            )
        except Exception as e:
            logger.warning("Failed to record post expansion telemetry: %s", e)

        return res_dict
