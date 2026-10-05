"""Unit tests for Katteb output formatters (table and JSON modes)."""

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
from katteb.models import (
    AccountCreditsResponse,
    ArticleGetResponse,
    FactCheckResponse,
    FactReference,
    HumanizerDetectResponse,
    WritingStyle,
)


def test_print_json(capsys):
    print_json({"key": "val", "number": 123})
    captured = capsys.readouterr()
    assert '"key": "val"' in captured.out
    assert '"number": 123' in captured.out


def test_format_credits_table(capsys):
    credits_data = AccountCreditsResponse(
        credits=500,
        credits_total=1000,
        plan_type="team",
        plan_tier="pro",
        api_usage_today={"heavy": 2, "read": 10},
    )
    format_credits(credits_data, as_json=False)
    out = capsys.readouterr().out
    assert "Katteb Credit Balance" in out
    assert "500" in out
    assert "1000" in out
    assert "TEAM" in out


def test_format_credits_json(capsys):
    credits_data = AccountCreditsResponse(credits=350, plan_type="starter")
    format_credits(credits_data, as_json=True)
    out = capsys.readouterr().out
    assert '"credits": 350' in out


def test_format_articles_list_table_and_json(capsys):
    articles = [
        {
            "job_id": 101,
            "topic": "Top 10 Santorini Hotels",
            "status": "completed",
            "word_count": 1800,
            "created_at": "2026-10-01",
        },
        {
            "job_id": 102,
            "topic": "Things to do in Amsterdam",
            "status": "processing",
            "word_count": 0,
            "created_at": "2026-10-02",
        },
    ]
    format_articles_list(articles, as_json=False)
    out = capsys.readouterr().out
    assert "Top 10 Santorini Hotels" in out
    assert "101" in out

    format_articles_list(articles, as_json=True)
    json_out = capsys.readouterr().out
    assert '"articles": [' in json_out
    assert "Santorini" in json_out


def test_format_article_get_table_and_json(capsys):
    art = ArticleGetResponse(
        job_id=456,
        topic="Best Athens Restaurants",
        status="completed",
        word_count=2100,
        meta_title="Best Athens Food Guide",
        meta_description="A local culinary journey in Athens",
        featured_image="https://example.com/image.jpg",
        content_html="<h2>Best Athens Food</h2><p>Here are delicious spots...</p>",
    )
    format_article_get(art, as_json=False)
    out = capsys.readouterr().out
    assert "Job #456" in out
    assert "Best Athens Restaurants" in out
    assert "2100" in out

    format_article_get(art, as_json=True)
    json_out = capsys.readouterr().out
    assert '"job_id": 456' in json_out
    assert '"word_count": 2100' in json_out


def test_format_styles_table_and_json(capsys):
    styles = [
        WritingStyle(id=1, name="Journalistic", description="Authoritative tone", is_active=True),
        {"id": 2, "name": "Conversational", "description": "Friendly blog tone", "is_active": False},
    ]
    format_styles(styles, as_json=False)
    out = capsys.readouterr().out
    assert "Journalistic" in out
    assert "Conversational" in out

    format_styles(styles, as_json=True)
    json_out = capsys.readouterr().out
    assert "Journalistic" in json_out


def test_format_brands_table_and_json(capsys):
    brands = [
        {"id": 10, "name": "ViaTravelers", "url": "https://viatravelers.com"},
        {"id": 11, "name": "Santorini Secrets", "url": "https://santorinisecrets.com"},
    ]
    format_brands(brands, as_json=False)
    out = capsys.readouterr().out
    assert "ViaTravelers" in out
    assert "Santorini Secrets" in out

    format_brands(brands, as_json=True)
    json_out = capsys.readouterr().out
    assert "ViaTravelers" in json_out


def test_format_humanizer_detect_table_and_json(capsys):
    res = HumanizerDetectResponse(
        ai_probability=12,
        verdict="likely_human",
        word_count=540,
        credits_charged=1,
    )
    format_humanizer_detect(res, as_json=False)
    out = capsys.readouterr().out
    assert "12%" in out
    assert "likely_human" in out

    format_humanizer_detect(res, as_json=True)
    json_out = capsys.readouterr().out
    assert '"ai_probability": 12' in json_out


def test_format_factcheck_table_and_json(capsys):
    fc = FactCheckResponse(
        verdict="TRUE",
        explanation="Verified against authoritative sources.",
        search_query="Oia sunset view Santorini",
        references=[FactReference(title="Greek Tourism", url="https://visitgreece.gr")],
    )
    format_factcheck(fc, as_json=False)
    out = capsys.readouterr().out
    assert "TRUE" in out
    assert "Greek Tourism" in out

    format_factcheck(fc, as_json=True)
    json_out = capsys.readouterr().out
    assert '"verdict": "TRUE"' in json_out
