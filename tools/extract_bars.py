"""Rebuild data/tradestation/<SYMBOL>_<unit>.csv from TradeStation get-bars results.

The TradeStation MCP returns at most 100 bars per call, so history is fetched in
chunks. This script collects every chunk from the Claude Code session transcript
(JSONL), de-duplicates by bar timestamp, checks that overlapping chunks agree,
and writes one CSV per symbol and bar unit. Prices are exactly as TradeStation
returned them.

    python tools/extract_bars.py [transcript.jsonl ...]
"""

import glob
import json
import sys
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent.parent / "data" / "tradestation"
DEFAULT_GLOB = "/root/.claude/projects/*/*.jsonl"


def chunks(paths):
    for f in paths:
        for line in open(f):
            if "TimeStamp" not in line:
                continue
            msg = json.loads(line).get("message", {})
            content = msg.get("content")
            if not isinstance(content, list):
                continue
            for blk in content:
                if blk.get("type") != "tool_result":
                    continue
                cc = blk.get("content")
                texts = [x.get("text", "") for x in cc] if isinstance(cc, list) else [cc]
                for t in texts:
                    try:
                        j = json.loads(t)
                    except (TypeError, ValueError):
                        continue
                    if isinstance(j, dict) and j.get("bars"):
                        yield j


def main(paths):
    rows = []
    for j in chunks(paths):
        for b in j["bars"]:
            rows.append({"symbol": j["symbol"], "unit": j["unit"], "ts": b["TimeStamp"],
                         "open": float(b["Open"]), "high": float(b["High"]),
                         "low": float(b["Low"]), "close": float(b["Close"]),
                         "volume": float(b.get("TotalVolume", 0))})
    df = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    for (sym, unit), g in df.groupby(["symbol", "unit"]):
        conflicts = g.groupby("ts")[["open", "high", "low", "close"]].nunique().gt(1).any(axis=1).sum()
        g = g.drop_duplicates("ts").copy()
        g["date"] = pd.to_datetime(g["ts"]).dt.tz_convert("America/New_York").dt.date
        g = g.sort_values("date")[["date", "open", "high", "low", "close", "volume"]]
        bad = ((g["high"] < g[["open", "close"]].max(axis=1)) | (g["low"] > g[["open", "close"]].min(axis=1))).sum()
        path = OUT / f"{sym}_{unit.lower()}.csv"
        g.to_csv(path, index=False)
        print(f"{sym:8s} {unit:8s} {len(g):5d} bars  {g['date'].iloc[0]} .. {g['date'].iloc[-1]}"
              f"  conflicts={conflicts} ohlc_violations={bad}")


if __name__ == "__main__":
    main(sys.argv[1:] or glob.glob(DEFAULT_GLOB))
