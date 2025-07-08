#!/usr/bin/env python
"""Command-line application that outputs buy/sell recommendation for AAPL."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from pprint import pprint

from analytics.decision_engine import recommend
from data.fetchers import get_price, get_news
from models.finbert_model import FinBertSentiment


def parse_args():
    p = argparse.ArgumentParser(description="AAPL advisor (daily sentiment + technicals)")
    p.add_argument("--force-refresh", action="store_true", help="Ignore cache and call APIs (will count towards quota)")
    return p.parse_args()


def main():
    args = parse_args()
    print("Fetching data...")
    price_df = get_price(force_refresh=args.force_refresh)
    news_items = get_news(force_refresh=args.force_refresh)

    print(f"Loaded {len(news_items)} news items and {len(price_df)} price rows")

    finbert = FinBertSentiment()
    headlines = [item.get("title") for item in news_items if item.get("title")]
    if not headlines:
        print("No headlines found; defaulting neutral sentiment")
        sentiment_score = 0.0
    else:
        sentiment_score = finbert.average_sentiment_score(headlines)
    results = recommend(price_df, sentiment_score)

    print("\n=== Recommendation (AAPL) ===")
    pprint(results)
    print(f"Timestamp: {datetime.utcnow().isoformat()}Z")


if __name__ == "__main__":
    main()