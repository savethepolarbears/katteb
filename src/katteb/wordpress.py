"""WordPress Fleet Integration for auditing and expanding low-word-count posts via WP-CLI."""

import json
import subprocess
from pathlib import Path
from typing import Any

from katteb.client import KattebClient
from katteb.models import ArticleGetResponse
from katteb.queue import KattebQueueManager

# BBM WordPress root resolution
BBM_WP_ROOT = Path("/Users/klkro/Projects/bbm-wordpress")
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


def resolve_country_code(country_name: str | None) -> str:
    """Map country string to ISO alpha-2 code, defaulting to 'us'."""
    if not country_name:
        return "us"
    clean = country_name.strip().lower()
    return COUNTRY_ISO_MAP.get(clean, "us")


def run_wp_cli(alias: str, command: str, timeout: int = 45) -> str:
    """Execute a WP-CLI command via wp-global."""
    import shlex

    target_alias = f"@{alias}.prod" if not alias.startswith("@") else alias
    cmd_args = ["bash", str(WP_GLOBAL_SCRIPT), target_alias, *shlex.split(command)]

    res = subprocess.run(
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


def run_wp_eval(alias: str, php_code: str, timeout: int = 60) -> Any:
    """Execute PHP code on remote site via base64 wrapper and return parsed JSON result."""
    import base64

    b64_code = base64.b64encode(php_code.encode("utf-8")).decode("utf-8")
    runner_code = f"eval(base64_decode('{b64_code}'));"
    out = run_wp_cli(alias, f'eval "{runner_code}"', timeout=timeout)
    try:
        return json.loads(out)
    except Exception:
        return out


class WordPressFleetManager:
    """Manages post auditing and AI content updates for WordPress fleet sites."""

    def __init__(self, client: KattebClient):
        self.client = client
        self.queue = KattebQueueManager(client)

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

        php_script = f"""
        global $wpdb;
        $pts = json_decode('{pts_json}', true);
        $statuses = json_decode('{status_json}', true);
        $status_in = implode("','", array_map('esc_sql', $statuses));

        $low_posts = array();
        foreach ($pts as $pt) {{
            $posts = $wpdb->get_results("
                SELECT ID, post_title, post_name, post_status, post_type, post_content
                FROM {{$wpdb->posts}}
                WHERE post_type = '" . esc_sql($pt) . "' AND post_status IN ('$status_in')
            ");

            foreach ($posts as $p) {{
                $clean = trim(preg_replace('/\\s+/', ' ', strip_tags($p->post_content)));
                $wc = empty($clean) ? 0 : str_word_count($clean);

                if ($wc < {max_words}) {{
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
                }}
            }}
        }}

        usort($low_posts, function($a, $b) {{ return $a['content_wc'] - $b['content_wc']; }});
        echo json_encode($low_posts);
        """

        result = run_wp_eval(site, php_script)
        if isinstance(result, list):
            return result
        return []

    def get_post_details(self, site: str, post_id: int) -> dict[str, Any]:
        """Fetch detailed post information including custom fields and meta."""
        php_script = f"""
        $p = get_post({post_id});
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
        on_status: Any | None = None,
    ) -> dict[str, Any]:
        """Generate expanded content with Katteb and update WordPress post."""
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

        if on_status:
            on_status(f"Generating article for post #{post_id} ('{topic}') via Katteb API...")

        if dry_run:
            return {
                "dry_run": True,
                "post_id": post_id,
                "title": title,
                "topic": topic,
                "country": target_country_code,
                "word_count": word_count,
                "enhancements": final_enhancements,
                "guidelines": final_guidelines,
                "current_word_count": post["word_count"],
            }

        # Submit and poll Katteb API
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

        # Content Quality & Authorization Guard
        if "Error (401)" in new_html or "Your IP is not authorized" in new_html:
            raise RuntimeError(
                "Katteb returned an IP authorization error: 'Your IP is not authorized to make this request.'\n"
                "Please add your current public IP to the allowed IP list in your Katteb account dashboard at https://app.katteb.com/api_access"
            )

        if "Error (" in new_html and len(new_html) < 400:
            raise RuntimeError(f"Katteb generation returned an error payload: {new_html}")

        # Clean meta_description from stray css or tags
        import re

        meta_desc = re.sub(r"<style[\s\S]*?</style>", "", meta_desc)
        meta_desc = re.sub(r"\.[a-zA-Z0-9_-]+\s*\{[^}]*\}", "", meta_desc).strip()

        if on_status:
            on_status(f"Article generated ({article_res.word_count} words). Updating WordPress post #{post_id}...")

        # Update WordPress post via WP-CLI eval
        update_payload = {
            "post_id": post_id,
            "post_type": pt,
            "content": new_html,
            "meta_title": meta_title,
            "meta_desc": meta_desc,
            "focus_kw": city if pt == "destinations" else title,
        }

        update_json_str = json.dumps(update_payload)
        # Base64 encode the payload to prevent escaping issues in bash/PHP
        import base64

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

        wp_res = run_wp_eval(site, php_update)

        return {
            "success": True,
            "post_id": post_id,
            "title": title,
            "previous_word_count": post["word_count"],
            "new_word_count": wp_res.get("new_word_count") if isinstance(wp_res, dict) else article_res.word_count,
            "job_id": article_res.job_id,
            "meta_title": meta_title,
            "meta_description": meta_desc,
        }
