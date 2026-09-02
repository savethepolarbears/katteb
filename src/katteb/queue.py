"""Concurrency queue manager for Katteb heavy operations."""

import logging
import time
from collections.abc import Callable

from katteb.client import KattebClient, KattebRateLimitError
from katteb.models import ArticleGetResponse

logger = logging.getLogger("katteb.queue")


class KattebQueueManager:
    """Handles Katteb single-job concurrency limits by polling active jobs on 429."""

    def __init__(self, client: KattebClient):
        self.client = client

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
                    if on_status:
                        on_status(
                            f"Job #{res.job_id} submitted for topic '{topic}' ({res.credits_charged or 1500} credits)"
                        )
                    return res.job_id
                raise ValueError("No job_id returned from generate_article")

            except KattebRateLimitError as e:
                if e.active_job_id:
                    msg = f"Active job #{e.active_job_id} ({e.active_job_type or 'heavy'}) in progress. Polling active job until completion..."
                    if on_status:
                        on_status(msg)
                    logger.info(msg)

                    try:
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
                        on_status(
                            f"Rate limited. Waiting {wait_time}s before retry (attempt {attempt + 1}/{max_retries})..."
                        )
                    time.sleep(wait_time)

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

        return self.client.poll_article_until_complete(
            job_id=job_id,
            interval_seconds=10,
            timeout_seconds=600,
            on_progress=lambda r: (
                on_status(f"Job #{job_id} progress: {r.progress or 0}% ({r.status})") if on_status else None
            ),
        )
