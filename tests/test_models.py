import pytest
from pydantic import ValidationError

from katteb.models import (
    AccountCreditsResponse,
    ArticleGenerateRequest,
    ArticleGetResponse,
)


def test_article_generate_request_valid():
    req = ArticleGenerateRequest(
        topic="Best Swiss Alps Hikes",
        language="English",
        country="ch",
        word_count=2000,
        enhancements=["faq", "key_takeaways"],
    )
    assert req.topic == "Best Swiss Alps Hikes"
    assert req.word_count == 2000
    assert req.country == "ch"


def test_article_generate_request_constraints():
    with pytest.raises(ValidationError):
        ArticleGenerateRequest(topic="Test", word_count=200)  # ge=500 constraint


def test_article_get_response_parsing():
    raw = {
        "success": True,
        "job_id": 4521,
        "topic": "Zurich Travel Guide",
        "status": "completed",
        "progress": 100,
        "content_html": "<h1>Zurich</h1><p>Guide content...</p>",
        "word_count": 1845,
        "meta_title": "Zurich Guide",
        "meta_description": "Explore Zurich with our complete guide.",
    }
    res = ArticleGetResponse.model_validate(raw)
    assert res.job_id == 4521
    assert res.status == "completed"
    assert res.word_count == 1845


def test_account_credits_parsing():
    raw = {
        "success": True,
        "credits": 45000,
        "credits_total": 50000,
        "plan_type": "pro",
        "api_usage_today": {"heavy": 2, "read": 10},
    }
    res = AccountCreditsResponse.model_validate(raw)
    assert res.credits == 45000
    assert res.plan_type == "pro"
