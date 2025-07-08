from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd
import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential

from config import CACHE_DIR, PRICE_API_CALLS_PER_DAY, NEWS_API_CALLS_PER_DAY, TICKER
from monitor import APICallMonitor

monitor = APICallMonitor()

PRICE_CACHE_PATH = CACHE_DIR / "price_AAPL.csv"
NEWS_CACHE_PATH = CACHE_DIR / "news_AAPL.json"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=10))
def _fetch_price_from_api() -> pd.DataFrame:
    monitor.increment("price")
    if monitor.get_count("price") > PRICE_API_CALLS_PER_DAY:
        raise RuntimeError("Daily price API call limit exceeded")
    df = yf.download(TICKER, period="1y", interval="1d", auto_adjust=True, progress=False)
    if df.empty:
        raise ValueError("No price data fetched")
    return df


def get_price(force_refresh: bool = False) -> pd.DataFrame:
    """Return daily price DataFrame. Caches to disk and obeys API limits."""
    if not force_refresh and PRICE_CACHE_PATH.exists():
        cached = pd.read_csv(PRICE_CACHE_PATH, index_col=0, parse_dates=True)
        last_date = cached.index[-1].date()
        if last_date == datetime.utcnow().date():
            return cached
    # else fetch
    df = _fetch_price_from_api()
    df.to_csv(PRICE_CACHE_PATH)
    return df


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=10))
def _fetch_news_from_api() -> List[Dict[str, Any]]:
    monitor.increment("news")
    if monitor.get_count("news") > NEWS_API_CALLS_PER_DAY:
        raise RuntimeError("Daily news API call limit exceeded")
    ticker = yf.Ticker(TICKER)
    news = ticker.get_news()  # limited items
    return news or []


def get_news(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """Fetch news for the ticker and cache result."""
    if not force_refresh and NEWS_CACHE_PATH.exists():
        cached = json.loads(NEWS_CACHE_PATH.read_text())
        cached_date_str = cached[0].get("cache_date") if cached else None
        if cached_date_str == datetime.utcnow().strftime("%Y-%m-%d"):
            return cached
    news_items = _fetch_news_from_api()
    # add cache_date meta
    for item in news_items:
        item["cache_date"] = datetime.utcnow().strftime("%Y-%m-%d")
    NEWS_CACHE_PATH.write_text(json.dumps(news_items))
    return news_items