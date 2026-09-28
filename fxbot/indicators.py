import pandas as pd


def ema(series, length):
    return series.ewm(span=length, adjust=False).mean()


def rsi(series, length):
    """Wilder RSI."""
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    return 100 - (100 / (1 + gain / loss))


def atr(df, length):
    """Wilder ATR on columns high/low/close."""
    prev_close = df["close"].shift()
    true_range = pd.concat([df["high"] - df["low"],
                            (df["high"] - prev_close).abs(),
                            (df["low"] - prev_close).abs()], axis=1).max(axis=1)
    return true_range.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
