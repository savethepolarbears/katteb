from unittest.mock import patch

import pytest

from katteb.client import KattebClient
from katteb.models import ArticleGetResponse
from katteb.wordpress import WordPressFleetManager, resolve_country_code


@pytest.fixture
def wp_manager():
    client = KattebClient(api_key="mock_key")
    return WordPressFleetManager(client)


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

    with patch.object(wp_manager, "get_post_details", return_value=mock_post):
        res = wp_manager.expand_and_update_post(
            site="destinations-ai",
            post_id=12345,
            word_count=1800,
            dry_run=True,
        )
        assert res["dry_run"] is True
        assert res["post_id"] == 12345
        assert res["country"] == "ch"
        assert res["word_count"] == 1800
        assert "Complete Travel Guide to Zurich" in res["topic"]


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
        content_html="Error (500): Katteb backend generation failure",
        word_count=5,
    )

    with patch.object(wp_manager, "get_post_details", return_value=mock_post), \
         patch.object(wp_manager.queue, "generate_and_wait", return_value=mock_article):
        with pytest.raises(RuntimeError) as exc_info:
            wp_manager.expand_and_update_post(site="destinations-ai", post_id=12345)
        assert "Katteb generation returned an error payload" in str(exc_info.value)


def test_meta_description_sanitizer(wp_manager):
    mock_post = {
        "id": 12345,
        "title": "Zurich",
        "post_type": "destinations",
        "word_count": 250,
        "meta": {"city": "Zurich", "country": "Switzerland"},
    }
    raw_desc = "<style>.entry-content { font-size: 14px; }</style> Complete guide to visiting Zurich in 2026. .sidebar { display: none; }"
    mock_article = ArticleGetResponse(
        success=True,
        job_id=999,
        topic="Zurich",
        status="completed",
        content_html="<h2>Welcome to Zurich</h2><p>Here is full guide content...</p><h2>Top Attractions</h2><h3>Old Town</h3><p>Explore Zurich.</p>",
        word_count=1800,
        meta_title="Zurich Guide 2026",
        meta_description=raw_desc,
    )

    with patch.object(wp_manager, "get_post_details", return_value=mock_post), \
         patch.object(wp_manager.queue, "generate_and_wait", return_value=mock_article), \
         patch("katteb.wordpress.run_wp_eval", return_value={"success": True, "new_word_count": 1800}):
        res = wp_manager.expand_and_update_post(site="destinations-ai", post_id=12345)
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
        assert wp_manager.check_site_connectivity("destinations-ai") is True

    with patch("katteb.wordpress.run_wp_cli", side_effect=RuntimeError("Connection refused")):
        assert wp_manager.check_site_connectivity("offline-site") is False


def test_validate_generated_content_valid():
    from katteb.wordpress import validate_generated_content

    html = (
        "<h2>Overview</h2><p>Zurich is beautiful.</p>"
        "<h2>Best Things to Do</h2><p>Explore Old Town.</p>"
        "<h3>Lake Zurich</h3><p>Take a boat ride.</p>"
    )
    errors = validate_generated_content(html, target_word_count=1200)
    assert errors == []


def test_validate_generated_content_missing_headings():
    from katteb.wordpress import validate_generated_content

    # Missing H3
    html = "<h2>Overview</h2><p>Just one heading.</p><h2>Details</h2><p>Text.</p>"
    errors = validate_generated_content(html, target_word_count=1200)
    assert any("H3 subsections" in e for e in errors)

    # Missing H2
    html_no_h2 = "<p>Completely flat text with no headers.</p>"
    errors = validate_generated_content(html_no_h2, target_word_count=1200)
    assert any("H2 structure" in e for e in errors)


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
    )

    import os
    assert os.path.exists(receipt_file)
    with open(receipt_file, encoding="utf-8") as f:
        content = f.read()

    assert "# Katteb Content Expansion Receipt — destinations-ai" in content
    assert "| 101 | Zurich Guide | 300 | 1850 | +1550 | ✅ Updated | Yes |" in content
    assert "| 102 | Geneva Guide | 200 | 200 | +0 | ❌ Failed (IP not authorized) | No |" in content


