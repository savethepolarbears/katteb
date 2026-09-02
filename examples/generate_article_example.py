#!/usr/bin/env python3
"""Example: Generate an AI article using Katteb Python SDK."""

from katteb import KattebClient
from katteb.queue import KattebQueueManager


def main():
    client = KattebClient()
    queue = KattebQueueManager(client)

    print("Checking account credits...")
    credits = client.get_credits()
    print(f"Available credits: {credits.credits}")

    topic = "Top 10 Hidden Gem Destinations in Europe for 2026"
    print(f"\nGenerating article: '{topic}'...")

    article = queue.generate_and_wait(
        topic=topic,
        word_count=1800,
        country="us",
        enhancements=["tldr", "key_takeaways", "faq"],
        on_status=lambda msg: print(f"  [Progress] {msg}"),
    )

    print(f"\nArticle Generated Successfully (Job #{article.job_id})!")
    print(f"Word Count: {article.word_count}")
    print(f"Meta Title: {article.meta_title}")
    print(f"Meta Description: {article.meta_description}")


if __name__ == "__main__":
    main()
