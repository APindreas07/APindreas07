"""Download real HistData.com FX history (free 1-minute BID bars) and aggregate to 5-minute bars.

Owner-approved on 2026-09-29 as the intraday source, because Dukascopy throttled this connection to a crawl.
Real data only; nothing is generated.

HistData's ASCII M1 files are time-stamped in New York local time WITH daylight saving (verified against Dukascopy,
see parse()), converted here to UTC.
Completed years come as one yearly zip; the current year comes month by month.

Output: data/histdata/{PAIR}/{YEAR}.csv.gz, 5-minute BID bars labelled by bar START time (UTC), columns
  ts, bo, bh, bl, bc
data/histdata/ is git-ignored; data/histdata_MANIFEST.csv (committed) lists each file's row count and SHA-256.

Run:  python -m tools.histdata --pairs USDJPY EURUSD --start 2012 --end 2026-09-25
"""
from __future__ import annotations

import argparse
import hashlib
import http.cookiejar
import io
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "histdata"
RAW = OUT / "_raw"
BASE = "https://www.histdata.com"
PAGE = BASE + "/download-free-forex-historical-data/?/ascii/1-minute-bar-quotes/{pair}/{year}{month}"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) research download"

_jar = http.cookiejar.CookieJar()
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_jar))
_opener.addheaders = [("User-Agent", UA)]


def fetch_zip(pair: str, year: int, month: int | None) -> bytes:
    """Download one HistData zip (yearly, or monthly when month is given), caching it in _raw/."""
    tag = f"{year}" if month is None else f"{year}{month:02d}"
    cache = RAW / pair / f"{tag}.zip"
    if cache.exists():
        return cache.read_bytes()
    page_url = PAGE.format(pair=pair.lower(), year=year, month="" if month is None else f"/{month}")
    for attempt in range(6):
        try:
            html = _opener.open(page_url, timeout=60).read().decode("utf-8", "replace")
            form = html[html.index('id="file_down"'):]
            fields = dict(re.findall(r'name="(\w+)" id="\w+" value="([^"]*)"', form[: form.index("</form>")]))
            req = urllib.request.Request(BASE + "/get.php", data=urllib.parse.urlencode(fields).encode(),
                                         headers={"Referer": page_url, "User-Agent": UA})
            data = _opener.open(req, timeout=300).read()
            if not data.startswith(b"PK"):
                raise RuntimeError(f"not a zip ({len(data)} bytes)")
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(data)
            time.sleep(2)                                  # be polite
            return data
        except ValueError:                                  # no download form: data not published
            return b""
        except Exception as e:
            print(f"  retry {pair} {tag}: {e}", flush=True)
            time.sleep(10 * 2 ** attempt)
    raise RuntimeError(f"failed: {page_url}")


def parse(zbytes: bytes) -> pd.DataFrame:
    if not zbytes:
        return pd.DataFrame()
    with zipfile.ZipFile(io.BytesIO(zbytes)) as z:
        name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        df = pd.read_csv(z.open(name), sep=";", header=None, names=["t", "o", "h", "l", "c", "v"],
                         dtype={"t": str})
    # Verified 2026-09-29 against Dukascopy (median difference 0.0 pip in both January and June 2019): the
    # timestamps are New York local time WITH daylight saving, despite HistData's "EST" label.
    # The repeated autumn fall-back hour is ambiguous and is dropped (about 12 five-minute bars a year).
    ts = pd.to_datetime(df["t"], format="%Y%m%d %H%M%S").dt.tz_localize(
        "America/New_York", ambiguous="NaT", nonexistent="shift_forward")
    df.index = ts.dt.tz_convert("UTC")
    return df.loc[df.index.notna(), ["o", "h", "l", "c"]]


def to_5min(m1: pd.DataFrame) -> pd.DataFrame:
    g = m1.resample("5min", label="left", closed="left")
    out = pd.DataFrame({"bo": g.o.first(), "bh": g.h.max(), "bl": g.l.min(), "bc": g.c.last()}).dropna()
    out.index.name = "ts"
    return out.reset_index()


def build_year(pair: str, year: int, last: pd.Timestamp) -> Path | None:
    if year < last.year:
        m1 = parse(fetch_zip(pair, year, None))
    else:
        parts = [parse(fetch_zip(pair, year, m)) for m in range(1, last.month + 1)]
        parts = [p for p in parts if not p.empty]
        m1 = pd.concat(parts) if parts else pd.DataFrame()
    if m1.empty:
        return None
    m1 = m1[~m1.index.duplicated()].sort_index()
    m1 = m1[m1.index < last.tz_localize("UTC") + pd.Timedelta(days=1)]
    df = to_5min(m1)
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
        rows.append({"file": f.relative_to(ROOT).as_posix(),
                     "rows": len(pd.read_csv(io.BytesIO(b), usecols=["ts"], compression="gzip")),
                     "sha256": hashlib.sha256(b).hexdigest()})
    pd.DataFrame(rows).to_csv(OUT.parent / "histdata_MANIFEST.csv", index=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", nargs="+", required=True)
    ap.add_argument("--start", type=int, required=True)
    ap.add_argument("--end", required=True)
    a = ap.parse_args()
    last = pd.Timestamp(a.end)
    for pair in a.pairs:
        for year in range(a.start, last.year + 1):
            t = time.time()
            p = build_year(pair, year, last)
            print(f"{pair} {year}: {'ok' if p else 'no data'} in {time.time() - t:.0f}s", flush=True)
    write_manifest()
    print("DONE", flush=True)


if __name__ == "__main__":
    sys.exit(main())
