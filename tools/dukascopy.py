"""Download real Dukascopy FX history (1-minute BID and ASK candles) and aggregate to 5-minute bid/ask bars.

Real broker data only; nothing is generated. Each day file is Dukascopy's own LZMA-compressed binary:
records of 24 bytes (big-endian): seconds-from-midnight-UTC uint32, open, close, low, high int32 (price / point), volume float32.

Output: data/dukascopy/{PAIR}/{YEAR}.csv.gz, 5-minute bars labelled by bar START time (UTC), columns
  ts, bo, bh, bl, bc, ao, ah, al, ac   (bid / ask OHLC)
Bars with no trading minutes are omitted. data/dukascopy/ is git-ignored (hundreds of MB); MANIFEST.csv (committed)
lists every file with its row count and SHA-256 so results can be reproduced by re-running this script.

Run:  python -m tools.dukascopy --pairs EURUSD USDJPY --start 2012 --end 2026-09-25
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import lzma
import struct
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "dukascopy"
URL = "https://datafeed.dukascopy.com/datafeed/{pair}/{y:04d}/{m0:02d}/{d:02d}/{side}_candles_min_1.bi5"
UA = {"User-Agent": "Mozilla/5.0 (research download)"}
REC = struct.Struct(">IIIIIf")


def point(pair: str) -> float:
    return 1e-3 if pair.endswith("JPY") else 1e-5


RAW = OUT / "_raw"
PACE = 0.25          # seconds between requests per thread; Dukascopy throttles bursts per IP with HTTP 503


def fetch(pair: str, day: dt.date, side: str) -> bytes:
    """Fetch one day file, caching the raw bytes so an interrupted download resumes where it stopped."""
    cache = RAW / pair / f"{day.isoformat()}_{side}.bi5"
    if cache.exists():
        return cache.read_bytes()
    url = URL.format(pair=pair, y=day.year, m0=day.month - 1, d=day.day, side=side)   # month is 0-based
    for attempt in range(10):
        try:
            time.sleep(PACE)
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                data = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                data = b""
                break
            time.sleep(min(5 * 2 ** attempt, 300))
        except Exception:
            time.sleep(min(5 * 2 ** attempt, 300))
    else:
        raise RuntimeError(f"failed after retries: {url}")
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(data)
    return data


def decode(raw: bytes, pair: str, day: dt.date) -> pd.DataFrame:
    if not raw:
        return pd.DataFrame()
    data = lzma.decompress(raw)
    n = len(data) // REC.size
    a = np.frombuffer(data[: n * REC.size], dtype=np.dtype([("t", ">u4"), ("o", ">i4"), ("c", ">i4"),
                                                           ("l", ">i4"), ("h", ">i4"), ("v", ">f4")]))
    p = point(pair)
    t0 = pd.Timestamp(day, tz="UTC")
    df = pd.DataFrame({"ts": t0 + pd.to_timedelta(a["t"].astype(np.int64), unit="s"),
                       "o": a["o"] * p, "h": a["h"] * p, "l": a["l"] * p, "c": a["c"] * p, "v": a["v"].astype(float)})
    return df[df.v > 0]                     # Dukascopy pads non-trading minutes with flat zero-volume candles


def day_bars(pair: str, day: dt.date) -> pd.DataFrame:
    sides = {}
    for side, pre in (("BID", "b"), ("ASK", "a")):
        m = decode(fetch(pair, day, side), pair, day)
        if m.empty:
            return pd.DataFrame()
        g = m.set_index("ts").resample("5min", label="left", closed="left")
        sides[pre] = pd.DataFrame({pre + "o": g.o.first(), pre + "h": g.h.max(), pre + "l": g.l.min(), pre + "c": g.c.last()})
    out = sides["b"].join(sides["a"], how="inner").dropna()
    return out.reset_index()


def download_year(pair: str, year: int, last: dt.date, threads: int) -> Path | None:
    days = [d for d in pd.date_range(f"{year}-01-01", min(pd.Timestamp(f"{year}-12-31"), pd.Timestamp(last))).date
            if d.weekday() != 5]            # Saturday has no FX trading
    if not days:
        return None
    with ThreadPoolExecutor(threads) as ex:
        parts = list(ex.map(lambda d: day_bars(pair, d), days))
    df = pd.concat([p for p in parts if not p.empty], ignore_index=True).sort_values("ts")
    df["ts"] = df["ts"].dt.strftime("%Y-%m-%d %H:%M")
    dest = OUT / pair / f"{year}.csv.gz"
    dest.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    df.to_csv(buf, index=False, float_format="%.6g", compression={"method": "gzip", "mtime": 0})
    dest.write_bytes(buf.getvalue())
    return dest


def write_manifest():
    rows = []
    for f in sorted(OUT.glob("[A-Z]*/*.csv.gz")):
        b = f.read_bytes()
        n = len(pd.read_csv(io.BytesIO(b), usecols=["ts"], compression="gzip"))
        rows.append({"file": f.relative_to(ROOT).as_posix(), "rows": n, "sha256": hashlib.sha256(b).hexdigest()})
    pd.DataFrame(rows).to_csv(OUT.parent / "dukascopy_MANIFEST.csv", index=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", nargs="+", required=True)
    ap.add_argument("--start", type=int, required=True)
    ap.add_argument("--end", required=True, help="last date, YYYY-MM-DD")
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    last = dt.date.fromisoformat(a.end)
    for pair in a.pairs:
        for year in range(a.start, last.year + 1):
            dest = OUT / pair / f"{year}.csv.gz"
            if dest.exists() and not a.force and year < last.year:
                print(f"{pair} {year}: exists, skipped", flush=True)
                continue
            t = time.time()
            p = download_year(pair, year, last, a.threads)
            print(f"{pair} {year}: {p.name if p else 'none'} in {time.time()-t:.0f}s", flush=True)
    write_manifest()


if __name__ == "__main__":
    sys.exit(main())
