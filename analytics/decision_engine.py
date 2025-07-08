from __future__ import annotations

from typing import Tuple, Dict

import pandas as pd

from config import SMA_LONG, SMA_SHORT, SENTIMENT_WEIGHT, PRICE_WEIGHT, THRESHOLDS


def _calc_technical_score(df: pd.DataFrame) -> float:
    """Return a score between -1 and 1 based on moving average crossover."""
    if df.empty:
        return 0.0
    df = df.copy()
    df["sma_short"] = df["Close"].rolling(window=SMA_SHORT).mean()
    df["sma_long"] = df["Close"].rolling(window=SMA_LONG).mean()
    latest = df.iloc[-1]
    sma_short = latest["sma_short"]
    sma_long = latest["sma_long"]
    price = latest["Close"]
    # Basic scoring: price above short and short above long => bullish
    if pd.isna(sma_short) or pd.isna(sma_long):
        return 0.0
    score = 0.0
    if price > sma_short:
        score += 0.5
    else:
        score -= 0.5
    if sma_short > sma_long:
        score += 0.5
    else:
        score -= 0.5
    return score  # ranges -1 to 1


def combine_scores(sentiment_score: float, technical_score: float) -> float:
    return SENTIMENT_WEIGHT * sentiment_score + PRICE_WEIGHT * technical_score


def classify(final_score: float) -> str:
    """Return rating based on thresholds sorted descending."""
    # thresholds defined descending strong buy 0.6 > buy 0.25 > neutral -0.25 > sell -0.6
    for label, threshold in THRESHOLDS.items():
        if final_score >= threshold:
            return label
    return "Strong Sell"  # worst-case


def recommend(df: pd.DataFrame, sentiment_score: float) -> Dict[str, float | str]:
    technical_score = _calc_technical_score(df)
    combined = combine_scores(sentiment_score, technical_score)
    rating = classify(combined)
    return {
        "sentiment_score": round(sentiment_score, 3),
        "technical_score": round(technical_score, 3),
        "combined_score": round(combined, 3),
        "rating": rating,
    }