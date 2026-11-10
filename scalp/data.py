"""Historical data loaders for Binance (data.binance.vision) and Bybit (public.bybit.com).

Both sources are public bulk dumps that need no API key and are not geo-restricted,
unlike the live REST APIs.
"""
from __future__ import annotations

import gzip
import io
import os
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import requests

DATA_DIR = Path(os.environ.get("SCALP_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
BINANCE_DUMP = "https://data.binance.vision/data/futures/um/monthly/klines"
BYBIT_DUMP = "https://public.bybit.com/trading"

KCOLS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
         "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore"]


def _get(url: str, timeout: int = 60) -> bytes | None:
    for attempt in range(4):
        try:
            r = requests.get(url, timeout=timeout)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.content
        except requests.RequestException:
            if attempt == 3:
                raise
    return None


def _binance_month(symbol: str, month: str) -> pd.DataFrame | None:
    """One month of 1m USDT-M futures klines; cached as parquet."""
    out = DATA_DIR / "binance" / symbol / f"{month}.parquet"
    if out.exists():
        return pd.read_parquet(out)
    raw = _get(f"{BINANCE_DUMP}/{symbol}/1m/{symbol}-1m-{month}.zip")
    if raw is None:
        return None
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        with z.open(z.namelist()[0]) as f:
            df = pd.read_csv(f, header=None, names=KCOLS, low_memory=False)
    if not str(df.iloc[0, 0]).isdigit():  # some files carry a header row
        df = df.iloc[1:]
    df = df.astype({c: "float64" for c in KCOLS if c not in ("open_time", "close_time")})
    df["open_time"] = pd.to_datetime(df["open_time"].astype("int64"), unit="ms", utc=True)
    df = df.drop(columns=["close_time", "ignore"]).set_index("open_time")
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out)
    return df


def load_binance(symbol: str, start: str, end: str) -> pd.DataFrame:
    """1m klines for [start, end] months inclusive, e.g. load_binance('BTCUSDT','2026-01','2026-10')."""
    months = [p.strftime("%Y-%m") for p in pd.period_range(start, end, freq="M")]
    with ThreadPoolExecutor(8) as ex:
        parts = [d for d in ex.map(lambda m: _binance_month(symbol, m), months) if d is not None]
    if not parts:
        raise FileNotFoundError(f"no Binance data for {symbol} {start}..{end}")
    df = pd.concat(parts).sort_index()
    return df[~df.index.duplicated()]


def _bybit_day(symbol: str, day: str) -> pd.DataFrame | None:
    """One day of Bybit linear-perp trades aggregated to 1m bars with taker-buy volume."""
    out = DATA_DIR / "bybit" / symbol / f"{day}.parquet"
    if out.exists():
        return pd.read_parquet(out)
    raw = _get(f"{BYBIT_DUMP}/{symbol}/{symbol}{day}.csv.gz", timeout=120)
    if raw is None:
        return None
    t = pd.read_csv(io.BytesIO(gzip.decompress(raw)), usecols=["timestamp", "side", "size", "price"])
    t["open_time"] = pd.to_datetime(t["timestamp"], unit="s", utc=True).dt.floor("1min")
    t["buy"] = np.where(t["side"] == "Buy", t["size"], 0.0)
    t["quote"] = t["size"] * t["price"]
    g = t.groupby("open_time")
    df = pd.DataFrame({
        "open": g["price"].first(), "high": g["price"].max(), "low": g["price"].min(),
        "close": g["price"].last(), "volume": g["size"].sum(), "quote_volume": g["quote"].sum(),
        "trades": g["price"].size().astype("float64"), "taker_buy_base": g["buy"].sum(),
    })
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out)
    return df


def load_bybit(symbol: str, start: str, end: str) -> pd.DataFrame:
    """1m bars built from Bybit trade dumps for [start, end] days inclusive (YYYY-MM-DD)."""
    days = [d.strftime("%Y-%m-%d") for d in pd.date_range(start, end, freq="D")]
    with ThreadPoolExecutor(8) as ex:
        parts = [d for d in ex.map(lambda x: _bybit_day(symbol, x), days) if d is not None]
    if not parts:
        raise FileNotFoundError(f"no Bybit data for {symbol} {start}..{end}")
    return pd.concat(parts).sort_index()


def resample(df: pd.DataFrame, minutes: int) -> pd.DataFrame:
    """Aggregate 1m bars to N-minute bars."""
    if minutes == 1:
        return df
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum",
           "quote_volume": "sum", "trades": "sum", "taker_buy_base": "sum"}
    agg = {k: v for k, v in agg.items() if k in df.columns}
    return df.resample(f"{minutes}min", label="left", closed="left").agg(agg).dropna(subset=["open"])
