from unittest.mock import patch

import pytest

from katteb.client import KattebClient, KattebRateLimitError
from katteb.models import ArticleGenerateResponse, ArticleGetResponse
from katteb.queue import KattebQueueManager


@pytest.fixture
def queue_manager():
    client = KattebClient(api_key="mock_key")
    return KattebQueueManager(client)


def test_queue_generate_immediate_success(queue_manager):
    mock_gen_resp = ArticleGenerateResponse(
        success=True,
        job_id=101,
        credits_charged=1500,
        estimated_time="120s",
        status="pending",
    )

    with patch.object(queue_manager.client, "generate_article", return_value=mock_gen_resp):
        job_id = queue_manager.generate_with_concurrency_wait(topic="Test Topic")
        assert job_id == 101


def test_queue_generate_with_429_concurrency_interception(queue_manager):
    # First call raises KattebRateLimitError with active_job_id=555
    # Second call returns success
    mock_gen_resp = ArticleGenerateResponse(
        success=True,
        job_id=102,
        credits_charged=1500,
        status="pending",
    )
    rate_err = KattebRateLimitError(
        message="Active job running",
        retry_after=1,
        active_job_id=555,
        active_job_type="article",
    )

    with (
        patch.object(queue_manager.client, "generate_article", side_effect=[rate_err, mock_gen_resp]),
        patch.object(queue_manager.client, "poll_article_until_complete") as mock_poll,
    ):
        statuses = []
        job_id = queue_manager.generate_with_concurrency_wait(
            topic="Test 429 Topic",
            on_status=lambda msg: statuses.append(msg),
        )
        assert job_id == 102
        mock_poll.assert_called_once_with(555, interval_seconds=15, timeout_seconds=600)
        assert any("555" in s for s in statuses)


def test_queue_generate_and_wait(queue_manager):
    mock_article = ArticleGetResponse(
        success=True,
        job_id=103,
        topic="Rome Guide",
        status="completed",
        progress=100,
        content_html="<h1>Rome</h1>",
        word_count=2000,
    )

    with (
        patch.object(queue_manager, "generate_with_concurrency_wait", return_value=103),
        patch.object(queue_manager.client, "poll_article_until_complete", return_value=mock_article),
    ):
        res = queue_manager.generate_and_wait(topic="Rome Guide")
        assert res.job_id == 103
        assert res.status == "completed"
        assert res.word_count == 2000


def test_queue_preserves_credits_charged(queue_manager):
    mock_gen = ArticleGenerateResponse(success=True, job_id=205, credits_charged=1850, status="pending")
    mock_get = ArticleGetResponse(
        success=True,
        job_id=205,
        topic="Athens Guide",
        status="completed",
        word_count=1800,
        credits_charged=None,
    )
    with (
        patch.object(queue_manager.client, "generate_article", return_value=mock_gen),
        patch.object(queue_manager.client, "poll_article_until_complete", return_value=mock_get),
    ):
        res = queue_manager.generate_and_wait(topic="Athens Guide", word_count=1800)
        assert res.credits_charged == 1850
        assert queue_manager.last_credits_charged == 1850


def test_queue_seo_429_dispatches_poll_seo(queue_manager):
    from katteb.models import SEOAnalyzeResponse, SEOGetResponse

    rate_err = KattebRateLimitError(
        message="Active SEO job running",
        retry_after=1,
        active_job_id=777,
        active_job_type="seo",
    )
    mock_seo_submit = SEOAnalyzeResponse(success=True, job_id=778, credits_charged=50, status="pending")
    mock_seo_done = SEOGetResponse(success=True, job_id=778, status="completed", score=88.0)

    with (
        patch.object(queue_manager.client, "analyze_seo", side_effect=[rate_err, mock_seo_submit]),
        patch.object(queue_manager.client, "poll_seo_until_complete", side_effect=[mock_seo_done, mock_seo_done]) as mock_poll_seo,
        patch.object(queue_manager.client, "poll_article_until_complete") as mock_poll_article,
    ):
        res = queue_manager.analyze_seo_and_wait(type="url", value="https://viatravelers.com")
        assert res.job_id == 778
        assert res.score == 88.0
        assert res.credits_charged == 50
        assert mock_poll_seo.call_count == 2
        mock_poll_article.assert_not_called()

