#!/usr/bin/env python3
"""Example: WordPress low-word-count post expansion on destinations.ai using Katteb SDK."""

from katteb import KattebClient
from katteb.wordpress import WordPressFleetManager


def main():
    client = KattebClient()
    wp_mgr = WordPressFleetManager(client)

    site = "destinations-ai"
    print(f"Auditing low word count posts on {site} (< 400 words)...")
    low_posts = wp_mgr.audit_low_word_posts(site=site, post_types=["destinations"], max_words=400)
    print(f"Found {len(low_posts)} thin destination posts.")

    if low_posts:
        target = low_posts[0]
        print(
            f"\nExpanding lowest post ID #{target['id']} ({target['title']}, currently {target['content_wc']} words)..."
        )
        result = wp_mgr.expand_and_update_post(
            site=site,
            post_id=target["id"],
            word_count=1800,
            dry_run=True,  # Set to False for live execution
            on_status=lambda msg: print(f"  {msg}"),
        )
        print(f"\nDry Run Result:\n{result}")


if __name__ == "__main__":
    main()
