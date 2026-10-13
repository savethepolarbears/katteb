"""Concurrency queue manager for Katteb heavy operations."""

import logging
import time
from collections.abc import Callable

from katteb.client import KattebClient, KattebRateLimitError
from katteb.models import ArticleGetResponse, SEOGetResponse

logger = logging.getLogger("katteb.queue")


class KattebQueueManager:
    """Handles Katteb single-job concurrency limits by polling active jobs on 429."""

    def __init__(self, client: KattebClient):
        self.client = client
        self.last_credits_charged: int | None = None

    def _wait_out_active_job(
        self,
        e: KattebRateLimitError,
        attempt: int,
        max_retries: int,
        on_status: Callable[[str], None] | None = None,
    ) -> None:
        """Poll an active blocking job (article or seo) or sleep for retry_after."""
        if e.active_job_id:
            job_type = (e.active_job_type or "heavy").lower()
            msg = f"Active job #{e.active_job_id} ({job_type}) in progress. Polling active job until completion..."
            if on_status:
                on_status(msg)
            logger.info(msg)

            try:
                if "seo" in job_type:
                    self.client.poll_seo_until_complete(
                        e.active_job_id,
                        interval_seconds=15,
                        timeout_seconds=600,
                    )
                else:
                    self.client.poll_article_until_complete(
                        e.active_job_id,
                        interval_seconds=15,
                        timeout_seconds=600,
                    )
            except Exception as poll_err:
                logger.warning(f"Error while waiting for active job: {poll_err}")
                time.sleep(e.retry_after or 30)
        else:
            wait_time = e.retry_after or 60
            if on_status:
                on_status(f"Rate limited. Waiting {wait_time}s before retry (attempt {attempt + 1}/{max_retries})...")
            time.sleep(wait_time)

    def generate_with_concurrency_wait(
        self,
        topic: str,
        language: str = "English",
        country: str = "us",
        word_count: int = 1500,
        brand_id: int | None = None,
        writing_style_id: int | None = None,
        guidelines: str | None = None,
        enhancements: list[str] | None = None,
        on_status: Callable[[str], None] | None = None,
        max_retries: int = 5,
    ) -> int:
        """Submit an article generation job, waiting out active job blockers if 429 encountered."""
        for attempt in range(max_retries):
            try:
                res = self.client.generate_article(
                    topic=topic,
                    language=language,
                    country=country,
                    word_count=word_count,
                    brand_id=brand_id,
                    writing_style_id=writing_style_id,
                    guidelines=guidelines,
                    enhancements=enhancements,
                )
                if res.job_id:
                    self.last_credits_charged = res.credits_charged
                    if on_status:
                        on_status(
                            f"Job #{res.job_id} submitted for topic '{topic}' ({res.credits_charged or word_count} credits)"
                        )
                    return res.job_id
                raise ValueError("No job_id returned from generate_article")

            except KattebRateLimitError as e:
                self._wait_out_active_job(e, attempt=attempt, max_retries=max_retries, on_status=on_status)

        raise KattebRateLimitError(f"Failed to submit article after {max_retries} concurrency retry attempts.")

    def generate_and_wait(
        self,
        topic: str,
        language: str = "English",
        country: str = "us",
        word_count: int = 1500,
        brand_id: int | None = None,
        writing_style_id: int | None = None,
        guidelines: str | None = None,
        enhancements: list[str] | None = None,
        on_status: Callable[[str], None] | None = None,
    ) -> ArticleGetResponse:
        """Generate an article, handle concurrency locks, and poll until full content is ready."""
        self.last_credits_charged = None
        job_id = self.generate_with_concurrency_wait(
            topic=topic,
            language=language,
            country=country,
            word_count=word_count,
            brand_id=brand_id,
            writing_style_id=writing_style_id,
            guidelines=guidelines,
            enhancements=enhancements,
            on_status=on_status,
        )

        if on_status:
            on_status(f"Polling job #{job_id} until completed...")

        res = self.client.poll_article_until_complete(
            job_id=job_id,
            interval_seconds=10,
            timeout_seconds=600,
            on_progress=lambda r: (
                on_status(f"Job #{job_id} progress: {r.progress or 0}% ({r.status})") if on_status else None
            ),
        )
        if res.credits_charged is None and self.last_credits_charged is not None:
            res.credits_charged = self.last_credits_charged
        return res

    def analyze_seo_with_concurrency_wait(
        self,
        type: str,
        value: str,
        keyword: str | None = None,
        brand_id: int | None = None,
        on_status: Callable[[str], None] | None = None,
        max_retries: int = 5,
    ) -> int:
        """Submit an SEO analysis job, waiting out active job blockers if 429 encountered."""
        for attempt in range(max_retries):
            try:
                res = self.client.analyze_seo(
                    type=type,
                    value=value,
                    keyword=keyword,
                    brand_id=brand_id,
                )
                if res.job_id:
                    self.last_credits_charged = res.credits_charged
                    if on_status:
                        on_status(f"SEO Job #{res.job_id} submitted ({res.credits_charged or 0} credits)")
                    return res.job_id
                raise ValueError("No job_id returned from analyze_seo")

            except KattebRateLimitError as e:
                self._wait_out_active_job(e, attempt=attempt, max_retries=max_retries, on_status=on_status)

        raise KattebRateLimitError(f"Failed to submit SEO analysis after {max_retries} concurrency retry attempts.")

    def analyze_seo_and_wait(
        self,
        type: str,
        value: str,
        keyword: str | None = None,
        brand_id: int | None = None,
        on_status: Callable[[str], None] | None = None,
    ) -> SEOGetResponse:
        """Submit SEO analysis, handle concurrency locks, and poll until full report is ready."""
        self.last_credits_charged = None
        job_id = self.analyze_seo_with_concurrency_wait(
            type=type,
            value=value,
            keyword=keyword,
            brand_id=brand_id,
            on_status=on_status,
        )
        res = self.client.poll_seo_until_complete(job_id=job_id, interval_seconds=10, timeout_seconds=600)
        if res.credits_charged is None and self.last_credits_charged is not None:
            res.credits_charged = self.last_credits_charged
        return res
