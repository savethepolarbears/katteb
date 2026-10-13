from unittest.mock import patch

import pytest

from katteb.client import KattebClient
from katteb.models import ArticleGetResponse, PreflightResult
from katteb.wordpress import WordPressFleetManager, resolve_country_code


@pytest.fixture
def wp_manager():
    client = KattebClient(api_key="mock_key")
    mgr = WordPressFleetManager(client)
    return mgr


@pytest.fixture(autouse=True)
def mock_default_preflight(tmp_path, monkeypatch):
    """Default patch for run_wp_cli and isolated backup/telemetry paths in tests."""
    monkeypatch.setenv("KATTEB_BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.setenv("KATTEB_TELEMETRY_FILE", str(tmp_path / "telemetry.jsonl"))
    with patch("katteb.wordpress.run_wp_cli", return_value="6.4.2"):
        yield


def test_resolve_country_code():
    assert resolve_country_code("United States") == "us"
    assert resolve_country_code("germany") == "de"
    assert resolve_country_code("Greece") == "gr"
    assert resolve_country_code("Japan") == "jp"
    assert resolve_country_code("Switzerland") == "ch"
    assert resolve_country_code(None) == "us"
    assert resolve_country_code("UnknownCountry123") == "us"


def test_expand_post_dry_run(wp_manager):
    mock_post = {
        "id": 12345,
        "title": "Zurich",
        "post_type": "destinations",
        "word_count": 250,
        "meta": {
            "city": "Zurich",
            "country": "Switzerland",
            "state_name_full": "Zurich",
        },
    }

    with (
        patch.object(wp_manager, "get_post_details", return_value=mock_post),
        patch.object(wp_manager.queue, "generate_and_wait") as mock_gen,
        patch("katteb.wordpress.run_wp_eval") as mock_eval,
    ):
        res = wp_manager.expand_and_update_post(
            site="destinations-ai",
            post_id=12345,
            word_count=1800,
            dry_run=True,
        )
        assert res["success"] is True
        assert res["dry_run"] is True
        assert res["simulated"] is True
        assert res["post_id"] == 12345
        assert res["country"] == "ch"
        assert res["word_count"] == 1800
        assert "Complete Travel Guide to Zurich" in res["topic"]
        # In dry run mode, neither Katteb generation nor WordPress eval mutation should be invoked
        mock_gen.assert_not_called()
        mock_eval.assert_not_called()


def test_ip_authorization_guard(wp_manager):
    mock_post = {
        "id": 12345,
        "title": "Zurich",
        "post_type": "destinations",
        "word_count": 250,
        "meta": {"city": "Zurich", "country": "Switzerland"},
    }
    mock_article = ArticleGetResponse(
        success=True,
        job_id=999,
        topic="Zurich",
        status="completed",
        content_html="Error (401): Your IP is not authorized to make this request.",
        word_count=10,
    )

    with (
        patch.object(wp_manager, "get_post_details", return_value=mock_post),
        patch.object(wp_manager.queue, "generate_and_wait", return_value=mock_article),
    ):
        with pytest.raises(RuntimeError) as exc_info:
            wp_manager.expand_and_update_post(site="destinations-ai", post_id=12345)
        assert "Your IP is not authorized" in str(exc_info.value)
        assert "https://app.katteb.com/api_access" in str(exc_info.value)


def test_error_payload_guard(wp_manager):
    mock_post = {
        "id": 12345,
        "title": "Zurich",
        "post_type": "destinations",
        "word_count": 250,
        "meta": {"city": "Zurich", "country": "Switzerland"},
    }
    mock_article = ArticleGetResponse(
        success=True,
        job_id=999,
        topic="Zurich",
        status="completed",
        content_html='{"status": "error", "error": "Backend generation timeout"}',
        word_count=5,
    )

    with (
        patch.object(wp_manager, "get_post_details", return_value=mock_post),
        patch.object(wp_manager.queue, "generate_and_wait", return_value=mock_article),
    ):
        with pytest.raises(RuntimeError) as exc_info:
            wp_manager.expand_and_update_post(site="destinations-ai", post_id=12345)
        assert "error payload" in str(exc_info.value).lower()


def test_meta_description_sanitizer(wp_manager):
    mock_post = {
        "id": 12345,
        "title": "Zurich",
        "post_type": "destinations",
        "word_count": 250,
        "meta": {"city": "Zurich", "country": "Switzerland"},
    }
    raw_desc = "<style>.entry-content { font-size: 14px; }</style> Complete guide to visiting Zurich in 2026. .sidebar { display: none; }"
    valid_html = (
        "<h2>Welcome to Zurich</h2><p>"
        + " ".join(["Zurich is a magnificent Swiss destination rich in history."] * 15)
        + "</p>"
        "<h2>Top Attractions</h2><p>"
        + " ".join(["Explore the picturesque alleys of the medieval Altstadt."] * 15)
        + "</p>"
        "<h3>Lake Zurich Cruises</h3><p>"
        + " ".join(["Take a scenic boat trip across the pristine waters."] * 15)
        + "</p>"
    )
    mock_article = ArticleGetResponse(
        success=True,
        job_id=999,
        topic="Zurich",
        status="completed",
        content_html=valid_html,
        word_count=1800,
        meta_title="Zurich Guide 2026",
        meta_description=raw_desc,
    )

    with (
        patch.object(wp_manager, "get_post_details", return_value=mock_post),
        patch.object(wp_manager.queue, "generate_and_wait", return_value=mock_article),
        patch("katteb.wordpress.run_wp_eval", return_value={"success": True, "new_word_count": 1800}),
    ):
        res = wp_manager.expand_and_update_post(site="destinations-ai", post_id=12345, word_count=500)
        assert res["success"] is True
        assert "<style>" not in res["meta_description"]
        assert ".entry-content" not in res["meta_description"]
        assert "Complete guide to visiting Zurich in 2026." in res["meta_description"]


def test_validate_site_alias():
    from katteb.wordpress import FLEET_SITE_PROFILES, validate_site_alias

    assert validate_site_alias("destinations-ai") == "destinations-ai"
    assert validate_site_alias("viatravelers") == "viatravelers"
    assert validate_site_alias("@santorinisecrets") == "@santorinisecrets"
    assert validate_site_alias("custom-site.prod") == "custom-site.prod"

    # Check known fleet profiles
    assert "destinations-ai" in FLEET_SITE_PROFILES
    assert "viatravelers" in FLEET_SITE_PROFILES
    assert FLEET_SITE_PROFILES["gearbuddha"]["default_post_type"] == "gear"

    # Test invalid shell strings
    with pytest.raises(ValueError):
        validate_site_alias("site; rm -rf /")
    with pytest.raises(ValueError):
        validate_site_alias("site`whoami`")
    with pytest.raises(ValueError):
        validate_site_alias("site$(id)")
    with pytest.raises(ValueError):
        validate_site_alias("")


def test_check_site_connectivity(wp_manager):
    with patch("katteb.wordpress.run_wp_cli", return_value="6.4.2"):
        res = wp_manager.check_site_connectivity("destinations-ai")
        assert res.success is True
        assert bool(res) is True
        assert res.version == "6.4.2"
        assert res.category == "ok"

    with patch("katteb.wordpress.run_wp_cli", side_effect=RuntimeError("Connection refused")):
        res_fail = wp_manager.check_site_connectivity("destinations-ai")
        assert res_fail.success is False
        assert bool(res_fail) is False
        assert res_fail.category == "wp_error"

    # Unauthorized alias
    res_unauth = wp_manager.check_site_connectivity("unknown-site-alias-xyz")
    assert res_unauth.success is False
    assert res_unauth.category == "unauthorized_alias"


def test_preflight_failure_blocks_generation(wp_manager):
    with (
        patch.object(
            wp_manager,
            "check_site_connectivity",
            return_value=PreflightResult(
                success=False, site="destinations-ai", category="ssh_error", message="SSH timeout"
            ),
        ),
        patch.object(wp_manager.queue, "generate_and_wait") as mock_gen,
    ):
        with pytest.raises(RuntimeError, match="Preflight check failed"):
            wp_manager.expand_and_update_post(site="destinations-ai", post_id=12345)
        # Katteb API generation must never be invoked if preflight connectivity fails
        mock_gen.assert_not_called()


def test_validate_generated_content_valid():
    from katteb.wordpress import validate_generated_content

    paragraphs = [
        "<h2>Overview & History</h2>",
        "<p>"
        + " ".join(["Zurich is Switzerland's financial and cultural center nestled beside Lake Zurich."] * 15)
        + "</p>",
        "<h2>Top Things to Do</h2>",
        "<p>"
        + " ".join(["Wander through the historic Niederdorf quarter with ancient cobblestone streets."] * 15)
        + "</p>",
        "<h3>Lake Zurich Boat Excursions</h3>",
        "<p>"
        + " ".join(["Scenic passenger ships navigate the alpine waters offering views of snowcapped peaks."] * 15)
        + "</p>",
    ]
    html = "".join(paragraphs)
    errors = validate_generated_content(html, target_word_count=500)
    assert errors == []


def test_validate_generated_content_missing_headings():
    from katteb.wordpress import validate_generated_content

    # Missing H3
    html = (
        "<h2>Overview</h2><p>"
        + " ".join(["Text content."] * 30)
        + "</p><h2>Details</h2><p>"
        + " ".join(["More text."] * 30)
        + "</p>"
    )
    errors = validate_generated_content(html, target_word_count=1200)
    assert any("H3 subsections" in e for e in errors)

    # Missing H2
    html_no_h2 = "<p>" + " ".join(["Completely flat text with no headers."] * 30) + "</p>"
    errors = validate_generated_content(html_no_h2, target_word_count=1200)
    assert any("H2 structure" in e for e in errors)


def test_validate_generated_content_rejects_empty_and_code_headings():
    from katteb.wordpress import validate_generated_content

    # Empty H2s and H3s
    html_empty = "<h2>   </h2><h2>&nbsp;</h2><h3></h3><p>" + " ".join(["Body paragraph text."] * 40) + "</p>"
    errors = validate_generated_content(html_empty, target_word_count=1200)
    assert any("H2 structure" in e for e in errors)
    assert any("H3 subsections" in e for e in errors)

    # Headings inside <pre><code> blocks should not count as semantic article structure
    html_in_pre = (
        "<pre><h2>Fake Heading In Code</h2><h3>Fake Subheading</h3></pre><p>"
        + " ".join(["Article body."] * 40)
        + "</p>"
    )
    errors_pre = validate_generated_content(html_in_pre, target_word_count=1200)
    assert any("H2 structure" in e for e in errors_pre)


def test_validate_generated_content_placeholders():
    from katteb.wordpress import validate_generated_content

    html = (
        "<h2>Overview</h2><p>Welcome to [City], the crown jewel of [Country].</p>"
        "<h2>Things to Do</h2><p>[insert link here] for tickets.</p>"
        "<h3>Details</h3><p>As an AI language model, I cannot provide personal views.</p>"
    )
    errors = validate_generated_content(html, target_word_count=1200)
    assert any("placeholder token" in e for e in errors)
    assert any("insert" in e for e in errors)
    assert any("AI boilerplate" in e for e in errors)


def test_validate_generated_content_placeholders_extended():
    from katteb.wordpress import validate_generated_content

    html = (
        "<h2>Overview</h2><p>Our guide to {{destination_name}} in %COUNTRY%.</p>"
        "<h2>Accommodations</h2><p>Check out <<hotel_options>> and INSERT LINK HERE.</p>"
        "<h3>Resources</h3><p>Visit https://example.com for booking details.</p>"
    )
    errors = validate_generated_content(html, target_word_count=1200)
    assert any("mustache" in e for e in errors)
    assert any("percent-delimited" in e for e in errors)
    assert any("angle-bracket" in e for e in errors)
    assert any("INSERT ... HERE" in e for e in errors)
    assert any("example.com" in e for e in errors)


def test_is_error_payload():
    from katteb.wordpress import is_error_payload

    # JSON error payloads
    is_err, msg = is_error_payload('{"status": "error", "message": "API key quota reached"}')
    assert is_err is True
    assert "JSON error payload" in msg

    is_err, msg = is_error_payload('{"success": false, "error": "Operation blocked"}')
    assert is_err is True

    # HTML 500/502 page
    is_err, msg = is_error_payload(
        "<html><head><title>502 Bad Gateway</title></head><body>502 Server Error</body></html>"
    )
    assert is_err is True
    assert "HTML server error page" in msg

    # IP auth string
    is_err, msg = is_error_payload("Error (401): Your IP is not authorized")
    assert is_err is True
    assert "IP authorization error" in msg

    # Normal valid HTML
    is_err, msg = is_error_payload(
        "<h2>Overview</h2><p>Zurich is a beautiful destination in Switzerland with mountain views.</p>"
    )
    assert is_err is False
    assert msg == ""


def test_expand_post_raises_content_quality_error(wp_manager):
    from katteb.wordpress import ContentQualityError

    mock_post = {
        "id": 12345,
        "title": "Zurich",
        "post_type": "destinations",
        "word_count": 250,
        "meta": {"city": "Zurich", "country": "Switzerland"},
    }
    # Article with unreplaced placeholder
    mock_article = ArticleGetResponse(
        success=True,
        job_id=999,
        topic="Zurich",
        status="completed",
        content_html="<h2>Overview</h2><p>Visiting [City] is amazing.</p><h2>Top Sights</h2><p>Explore!</p><h3>Lake</h3><p>Nice.</p>",
        word_count=1200,
        meta_title="Zurich",
        meta_description="Guide",
    )

    with (
        patch.object(wp_manager, "get_post_details", return_value=mock_post),
        patch.object(wp_manager.queue, "generate_and_wait", return_value=mock_article),
    ):
        with pytest.raises(ContentQualityError) as exc_info:
            wp_manager.expand_and_update_post(site="destinations-ai", post_id=12345, word_count=1200)
        assert "failed quality gates" in str(exc_info.value)
        assert "City" in str(exc_info.value)


def test_generate_expansion_receipt(tmp_path):
    from katteb.wordpress import generate_expansion_receipt

    results = [
        {
            "success": True,
            "post_id": 101,
            "title": "Zurich Guide",
            "previous_word_count": 300,
            "new_word_count": 1850,
            "meta_title": "Complete Zurich Guide 2026",
        },
        {
            "success": False,
            "post_id": 102,
            "title": "Geneva Guide",
            "error": "IP not authorized",
            "previous_word_count": 200,
            "new_word_count": 200,
        },
    ]

    receipt_file = generate_expansion_receipt(
        site="destinations-ai",
        results=results,
        output_dir=str(tmp_path),
        safe_root=str(tmp_path),
    )

    import json
    import os

    assert os.path.exists(receipt_file)
    with open(receipt_file, encoding="utf-8") as f:
        content = f.read()

    assert "# Katteb Content Expansion Receipt — destinations-ai" in content
    assert "| 101 | Zurich Guide | 300 | 1850 | +1550 | ✅ Updated | Yes |" in content
    assert "| 102 | Geneva Guide | 200 | 200 | +0 | ❌ Failed (IP not authorized) | No |" in content

    # Assert companion JSON receipt was also created
    json_receipt = receipt_file.replace(".md", ".json")
    assert os.path.exists(json_receipt)
    with open(json_receipt, encoding="utf-8") as jf:
        json_data = json.load(jf)
    assert json_data["site"] == "destinations-ai"
    assert json_data["total_posts"] == 2
    assert "audit_hash" in json_data


def test_expand_post_saves_backup_and_logs_credits_and_admin_url(wp_manager, tmp_path):
    import json

    from katteb.telemetry import get_telemetry_events, get_telemetry_summary

    mock_post = {
        "id": 777,
        "title": "Santorini Sunset Guide",
        "slug": "santorini-sunset-guide",
        "post_type": "post",
        "status": "publish",
        "word_count": 300,
        "content": "<p>Original short Santorini post.</p>",
        "meta": {"city": "Oia", "country": "Greece", "rank_math_title": "Old Title"},
    }
    valid_html = (
        "<h2>Overview of Oia Sunsets</h2><p>"
        + " ".join(["Oia offers breathtaking caldera views across the Aegean Sea."] * 30)
        + "</p>"
        "<h2>Best Viewing Spots</h2><p>"
        + " ".join(["Arrive early near the Byzantine Castle ruins for unobstructed vistas."] * 30)
        + "</p>"
        "<h3>Photography Tips</h3><p>"
        + " ".join(["Bring a tripod and wide-angle lens for blue hour shots."] * 30)
        + "</p>"
    )
    mock_article = ArticleGetResponse(
        success=True,
        job_id=501,
        topic="Santorini Sunset Guide",
        status="completed",
        content_html=valid_html,
        word_count=1650,
        credits_charged=1720,
        meta_title="Santorini Sunset Guide 2026",
        meta_description="Where to watch the sunset in Santorini.",
    )

    backup_dir = tmp_path / "custom_backups"
    with (
        patch.object(wp_manager, "get_post_details", return_value=mock_post),
        patch.object(wp_manager.queue, "generate_and_wait", return_value=mock_article),
        patch(
            "katteb.wordpress.run_wp_eval",
            return_value={"success": True, "new_word_count": 1650, "post_status": "draft"},
        ),
    ):
        res = wp_manager.expand_and_update_post(
            site="santorinisecrets",
            post_id=777,
            word_count=1500,
            stage_draft=True,
            backup_dir=backup_dir,
        )

    assert res["success"] is True
    assert res["credits_used"] == 1720
    assert res["stage_draft"] is True
    assert res["post_status"] == "draft"
    assert res["wp_admin_edit_url"] == "https://santorinisecrets.com/wp-admin/post.php?post=777&action=edit"
    assert res["backup_path"] is not None

    from pathlib import Path

    snap_data = json.loads(Path(res["backup_path"]).read_text(encoding="utf-8"))
    assert snap_data["post_id"] == 777
    assert snap_data["content"] == "<p>Original short Santorini post.</p>"
    assert snap_data["meta"]["rank_math_title"] == "Old Title"

    summary = get_telemetry_summary()
    assert summary["post_expansions"]["total_credits_used"] == 1720
    events = get_telemetry_events(limit=5)
    assert events[-1]["credits_used"] == 1720
    assert events[-1]["wp_admin_edit_url"] == "https://santorinisecrets.com/wp-admin/post.php?post=777&action=edit"


def test_expand_post_failure_records_failed_telemetry(wp_manager):
    from katteb.telemetry import get_telemetry_summary
    from katteb.wordpress import ContentQualityError

    mock_post = {
        "id": 888,
        "title": "Broken Post",
        "post_type": "post",
        "status": "publish",
        "word_count": 200,
        "content": "<p>Short text</p>",
        "meta": {},
    }
    bad_article = ArticleGetResponse(
        success=True,
        job_id=502,
        topic="Broken Post",
        status="completed",
        content_html="<h2>Heading</h2><p>Welcome to [City]!</p>",
        word_count=1200,
        credits_charged=1200,
    )

    with (
        patch.object(wp_manager, "get_post_details", return_value=mock_post),
        patch.object(wp_manager.queue, "generate_and_wait", return_value=bad_article),
        pytest.raises(ContentQualityError),
    ):
        wp_manager.expand_and_update_post(site="viatravelers", post_id=888, word_count=1200)

    summary = get_telemetry_summary()
    assert summary["post_expansions"]["total_runs"] == 1
    assert summary["post_expansions"]["failed_runs"] == 1
    assert summary["post_expansions"]["successful_runs"] == 0
    assert summary["post_expansions"]["total_credits_used"] == 1200


def test_rollback_post_restores_snapshot(wp_manager, tmp_path):
    from katteb.wordpress import save_post_backup_snapshot

    post_details = {
        "id": 909,
        "title": "Original Berlin Guide",
        "slug": "berlin-guide",
        "post_type": "destinations",
        "status": "publish",
        "word_count": 320,
        "content": "<p>Original Berlin content.</p>",
        "meta": {
            "travel_guide": "<p>Original Berlin content.</p>",
            "rank_math_title": "Original Berlin SEO Title",
            "rank_math_description": "Original Berlin SEO Desc",
            "rank_math_focus_keyword": "Berlin",
        },
    }
    snap_path = save_post_backup_snapshot("everythingaboutgermany", post_details, backup_dir=tmp_path)

    with patch(
        "katteb.wordpress.run_wp_eval",
        return_value={"success": True, "post_id": 909, "restored_word_count": 320, "restored_status": "publish"},
    ) as mock_eval:
        res = wp_manager.rollback_post("everythingaboutgermany", snap_path)
        assert res["success"] is True
        assert res["post_id"] == 909
        assert res["restored_word_count"] == 320
        assert res["restored_status"] == "publish"
        assert res["wp_admin_edit_url"] == "https://everythingaboutgermany.com/wp-admin/post.php?post=909&action=edit"
        mock_eval.assert_called_once()


def test_resolve_site_language_and_country():
    from katteb.wordpress import normalize_language_name, resolve_site_language_and_country

    assert normalize_language_name("de") == "German"
    assert normalize_language_name("es") == "Spanish"
    assert normalize_language_name("fr") == "French"
    assert normalize_language_name("el") == "Greek"
    assert normalize_language_name("nl") == "Dutch"
    assert normalize_language_name("it") == "Italian"
    assert normalize_language_name("English") == "English"

    assert resolve_site_language_and_country("santorinisecrets") == ("English", "gr")
    assert resolve_site_language_and_country("everythingaboutgermany") == ("English", "de")
    assert resolve_site_language_and_country("everythingaboutgermany.de") == ("German", "de")
    assert resolve_site_language_and_country("paristopten") == ("English", "fr")
    assert resolve_site_language_and_country("lovinglifeinspain") == ("English", "es")
    assert resolve_site_language_and_country("amsterdamlocalgems") == ("English", "nl")
    assert resolve_site_language_and_country("parkervillas") == ("English", "it")
    assert resolve_site_language_and_country("viatravelers", language_override="de") == ("German", "de")
    assert resolve_site_language_and_country("viatravelers", post_country="es", language_override="es") == (
        "Spanish",
        "es",
    )


def test_build_localized_guidelines():
    from katteb.wordpress import build_localized_guidelines

    de_guide = build_localized_guidelines(
        "Base guidelines.",
        language="German",
        country_code="de",
        site="everythingaboutgermany",
    )
    assert "Deutschlandticket" in de_guide
    assert "Euro (€)" in de_guide
    assert "Write natively in German" in de_guide

    gr_guide = build_localized_guidelines(
        "Santorini guide.",
        language="English",
        country_code="gr",
        site="santorinisecrets",
    )
    assert "donkey riding or donkey luggage transit" in gr_guide.lower()
    assert "KTEL" in gr_guide

    disabled_guide = build_localized_guidelines(
        "Base guidelines.",
        language="German",
        country_code="de",
        site="everythingaboutgermany",
        localize_idioms=False,
    )
    assert disabled_guide == "Base guidelines."


def test_validate_generated_content_multilingual_and_donkey_ban():
    from katteb.wordpress import validate_generated_content

    errs_de = validate_generated_content(
        "<h2>Einführung</h2><p>Als KI-Sprachmodell kann ich keine aktuellen Preise nennen.</p>",
        target_word_count=100,
        language="German",
        country="de",
    )
    assert any("als ki-sprachmodell" in e.lower() for e in errs_de)

    errs_es = validate_generated_content(
        "<h2>Introducción</h2><p>Como modelo de lenguaje, no tengo acceso en tiempo real.</p>",
        target_word_count=100,
        language="Spanish",
        country="es",
    )
    assert any("como modelo de lenguaje" in e.lower() for e in errs_es)

    errs_donkey_en = validate_generated_content(
        "<h2>Getting to Fira</h2><p>Many tourists take a donkey ride up the steps from the Old Port in Santorini.</p>",
        target_word_count=100,
        language="English",
        country="gr",
    )
    assert any("donkey" in e.lower() for e in errs_donkey_en)

    errs_donkey_de = validate_generated_content(
        "<h2>Anreise in Santorini</h2><p>Vermeiden Sie das Eselreiten in Fira nicht.</p>",
        target_word_count=100,
        language="German",
        country="gr",
    )
    assert any("donkey" in e.lower() for e in errs_donkey_de)


def test_expand_and_update_post_passes_language_and_localized_guidelines(wp_manager):
    mock_post = {
        "id": 610,
        "title": "München Sehenswürdigkeiten",
        "post_type": "destinations",
        "status": "publish",
        "word_count": 300,
        "content": "<p>Kurzer Text über München.</p>",
        "meta": {},
    }
    valid_de_html = (
        "<h2>Die besten Sehenswürdigkeiten in München</h2><p>"
        + " ".join(["Der Marienplatz bildet das historische Herz der bayerischen Landeshauptstadt München."] * 35)
        + "</p>"
        "<h2>Anreise mit der S-Bahn und U-Bahn</h2><p>"
        + " ".join(["Mit dem Deutschlandticket und der DB Navigator App fahren Sie bequem durch die Stadt."] * 35)
        + "</p>"
        "<h3>Praktische Tipps für Besucher</h3><p>"
        + " ".join(["Besuchen Sie den Viktualienmarkt am Vormittag für frische Spezialitäten."] * 30)
        + "</p>"
    )
    mock_article = ArticleGetResponse(
        success=True,
        job_id=611,
        topic="München Sehenswürdigkeiten",
        status="completed",
        content_html=valid_de_html,
        word_count=1550,
        credits_charged=1550,
    )

    with (
        patch.object(wp_manager, "get_post_details", return_value=mock_post),
        patch.object(wp_manager.queue, "generate_and_wait", return_value=mock_article) as mock_gen,
        patch(
            "katteb.wordpress.run_wp_eval",
            return_value={"success": True, "new_word_count": 1550, "post_status": "publish"},
        ),
    ):
        res = wp_manager.expand_and_update_post(
            site="everythingaboutgermany",
            post_id=610,
            word_count=1500,
            language="de",
            localize_idioms=True,
        )

    assert res["success"] is True
    assert res["language"] == "German"
    assert res["country"] == "de"
    call_kwargs = mock_gen.call_args.kwargs
    assert call_kwargs["language"] == "German"
    assert call_kwargs["country"] == "de"
    assert "Deutschlandticket" in call_kwargs["guidelines"]
