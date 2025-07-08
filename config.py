from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# Application constants
TICKER = "AAPL"

# API call limits to avoid throttling / overuse of free tier
PRICE_API_CALLS_PER_DAY = 1  # fetch daily
NEWS_API_CALLS_PER_DAY = 1   # fetch daily

# Model and decision thresholds
SENTIMENT_WEIGHT = 0.6  # weight of sentiment score in final rating
PRICE_WEIGHT = 0.4      # weight of technical score in final rating

# Technical indicator periods
SMA_SHORT = 50
SMA_LONG = 200

# Rating thresholds (combined score)
THRESHOLDS = {
    "Strong Buy": 0.6,
    "Buy": 0.25,
    "Neutral": -0.25,
    "Sell": -0.6,
    "Strong Sell": -1.0,
}


def today_str() -> str:
    """Return today's date in YYYY-MM-DD format."""
    return datetime.utcnow().strftime("%Y-%m-%d")