"""Download real monthly 3-month interbank interest rates (OECD, measure IR3TIB, % per year) for the currencies
used by the strategy lab, and save them to data/rates/ir3m_monthly.csv (wide: one column per currency).

Used ONLY to model financing (swap / carry) costs, never as trading signals (edge/lab/AGENT.md).
FRED's CSV endpoint refused automated downloads from this machine (2026-09-30), so the OECD SDMX API is used.

Run:  python -m tools.rates
"""
from __future__ import annotations

import io
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "rates" / "ir3m_monthly.csv"
AREAS = {"USA": "USD", "EA20": "EUR", "GBR": "GBP", "JPN": "JPY", "AUS": "AUD", "CAN": "CAD", "CHE": "CHF",
         "NZL": "NZD", "NOR": "NOK", "SWE": "SEK", "POL": "PLN", "HUN": "HUF", "CZE": "CZK"}
URL = ("https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_FINMARK,4.0/"
       + "+".join(AREAS) + ".M.IR3TIB.PA.....?startPeriod=2006-01&dimensionAtObservation=AllDimensions"
       "&format=csvfilewithlabels")


def main():
    raw = urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"}), timeout=120).read()
    d = pd.read_csv(io.BytesIO(raw))
    d = d[["REF_AREA", "TIME_PERIOD", "OBS_VALUE"]]
    wide = d.pivot_table(index="TIME_PERIOD", columns="REF_AREA", values="OBS_VALUE").rename(columns=AREAS)
    wide = wide.sort_index().ffill()                     # carry the last published month forward (e.g. GBP after 2026-02)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wide.to_csv(OUT, float_format="%.4f")
    print(f"saved {OUT} {wide.shape}")


if __name__ == "__main__":
    main()
