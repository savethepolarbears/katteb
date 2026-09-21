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
        content_html="<h2>Welcome to Zurich</h2><p>Here is full guide content...</p>",
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
