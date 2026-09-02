#!/usr/bin/env python3
"""Example: AI Text Detection, Humanizer, and Fact-Checking using Katteb SDK."""

from katteb import KattebClient


def main():
    client = KattebClient()

    sample_ai_text = (
        "Artificial intelligence continues to evolve rapidly, transforming the landscape "
        "of digital content creation across modern enterprise ecosystems."
    )

    print("--- 1. Detect AI Probability ---")
    detect_res = client.detect_ai(text=sample_ai_text)
    print(f"AI Probability: {detect_res.ai_probability}% (Verdict: {detect_res.verdict})")

    print("\n--- 2. Humanize Text ---")
    rewrite_res = client.rewrite_humanizer(
        text=sample_ai_text,
        strength="Strong",
        add_imperfections=True,
    )
    print(f"Humanized Output:\n{rewrite_res.rewritten_text}")

    print("\n--- 3. Fact-Check Verification ---")
    claim = "The Eiffel Tower can be 15 cm taller during the summer due to thermal expansion."
    fact_res = client.verify_fact(text=claim)
    print(f"Claim: {claim}")
    print(f"Verdict: {fact_res.verdict} (Is Fact: {fact_res.is_fact})")
    print(f"Explanation: {fact_res.explanation}")


if __name__ == "__main__":
    main()
