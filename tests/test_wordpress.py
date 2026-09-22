from unittest.mock import MagicMock, patch

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
def mock_default_preflight():
    """Default patch for run_wp_cli to allow WordPress post updates in tests unless explicitly overridden."""
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

    with patch.object(wp_manager, "get_post_details", return_value=mock_post), \
         patch.object(wp_manager.queue, "generate_and_wait") as mock_gen, \
         patch("katteb.wordpress.run_wp_eval") as mock_eval:
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

    with patch.object(wp_manager, "get_post_details", return_value=mock_post), \
         patch.object(wp_manager.queue, "generate_and_wait", return_value=mock_article):
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

    with patch.object(wp_manager, "get_post_details", return_value=mock_post), \
         patch.object(wp_manager.queue, "generate_and_wait", return_value=mock_article):
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
        "<h2>Welcome to Zurich</h2><p>" + " ".join(["Zurich is a magnificent Swiss destination rich in history."] * 15) + "</p>"
        "<h2>Top Attractions</h2><p>" + " ".join(["Explore the picturesque alleys of the medieval Altstadt."] * 15) + "</p>"
        "<h3>Lake Zurich Cruises</h3><p>" + " ".join(["Take a scenic boat trip across the pristine waters."] * 15) + "</p>"
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

    with patch.object(wp_manager, "get_post_details", return_value=mock_post), \
         patch.object(wp_manager.queue, "generate_and_wait", return_value=mock_article), \
         patch("katteb.wordpress.run_wp_eval", return_value={"success": True, "new_word_count": 1800}):
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
    with patch.object(
        wp_manager,
        "check_site_connectivity",
        return_value=PreflightResult(success=False, site="destinations-ai", category="ssh_error", message="SSH timeout"),
    ), patch.object(wp_manager.queue, "generate_and_wait") as mock_gen:
        with pytest.raises(RuntimeError, match="Preflight check failed"):
            wp_manager.expand_and_update_post(site="destinations-ai", post_id=12345)
        # Katteb API generation must never be invoked if preflight connectivity fails
        mock_gen.assert_not_called()


def test_validate_generated_content_valid():
    from katteb.wordpress import validate_generated_content

    paragraphs = [
        "<h2>Overview & History</h2>",
        "<p>" + " ".join(["Zurich is Switzerland's financial and cultural center nestled beside Lake Zurich."] * 15) + "</p>",
        "<h2>Top Things to Do</h2>",
        "<p>" + " ".join(["Wander through the historic Niederdorf quarter with ancient cobblestone streets."] * 15) + "</p>",
        "<h3>Lake Zurich Boat Excursions</h3>",
        "<p>" + " ".join(["Scenic passenger ships navigate the alpine waters offering views of snowcapped peaks."] * 15) + "</p>",
    ]
    html = "".join(paragraphs)
    errors = validate_generated_content(html, target_word_count=500)
    assert errors == []


def test_validate_generated_content_missing_headings():
    from katteb.wordpress import validate_generated_content

    # Missing H3
    html = "<h2>Overview</h2><p>" + " ".join(["Text content."] * 30) + "</p><h2>Details</h2><p>" + " ".join(["More text."] * 30) + "</p>"
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
    html_in_pre = "<pre><h2>Fake Heading In Code</h2><h3>Fake Subheading</h3></pre><p>" + " ".join(["Article body."] * 40) + "</p>"
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
    is_err, msg = is_error_payload("<html><head><title>502 Bad Gateway</title></head><body>502 Server Error</body></html>")
    assert is_err is True
    assert "HTML server error page" in msg

    # IP auth string
    is_err, msg = is_error_payload("Error (401): Your IP is not authorized")
    assert is_err is True
    assert "IP authorization error" in msg

    # Normal valid HTML
    is_err, msg = is_error_payload("<h2>Overview</h2><p>Zurich is a beautiful destination in Switzerland with mountain views.</p>")
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

    with patch.object(wp_manager, "get_post_details", return_value=mock_post), \
         patch.object(wp_manager.queue, "generate_and_wait", return_value=mock_article):
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



