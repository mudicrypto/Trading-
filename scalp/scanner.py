"""Live / replay dislocation scanner for Binance USDT-M futures and Bybit linear perps.

    python -m scalp.scanner --venue binance            # poll live REST klines once a minute
    python -m scalp.scanner --venue bybit --once
    python -m scalp.scanner --replay 2026-08-22        # replay a cached day through the same code path

It only READS public market data and PRINTS signals; it never places orders and needs no API key.
Signals come from scalp.strategies (the exact functions the backtest uses).

Signals are long AND short on every asset class. Only crypto longs were ever positive in-sample, and even
they showed no edge out-of-sample; shorts lost everywhere (see RESULTS.md). Treat output as research alerts.
"""
from __future__ import annotations

import argparse
import os
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import requests

from .factors import factor_logret
from .strategies import BOTH_SIDES, FROZEN, DAY, SnapbackParams, residual_features, snapback_signals
from .universe import ALL, asset_class

BINANCE_URL = os.environ.get("BINANCE_FAPI_URL", "https://fapi.binance.com")
BYBIT_URL = os.environ.get("BYBIT_API_URL", "https://api.bybit.com")
NEED = DAY * 2 + 60          # bars of history required for the rolling statistics
COLS = ["open", "high", "low", "close", "volume"]


def _frame(rows) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["t"] + COLS).astype("float64")
    df.index = pd.to_datetime(df.pop("t").astype("int64"), unit="ms", utc=True)
    return df.sort_index()


def fetch_binance(symbol: str, bars: int = NEED) -> pd.DataFrame:
    out, end = [], None
    while bars > 0:
        q = {"symbol": symbol, "interval": "1m", "limit": min(1500, bars)}
        if end is not None:
            q["endTime"] = end
        r = requests.get(f"{BINANCE_URL}/fapi/v1/klines", params=q, timeout=15)
        r.raise_for_status()
        rows = r.json()
        if not rows:
            break
        out = [x[:6] for x in rows] + out
        end = int(rows[0][0]) - 1
        bars -= len(rows)
    return _frame(out)


def fetch_bybit(symbol: str, bars: int = NEED) -> pd.DataFrame:
    out, end = [], None
    while bars > 0:
        q = {"category": "linear", "symbol": symbol, "interval": "1", "limit": min(1000, bars)}
        if end is not None:
            q["end"] = end
        r = requests.get(f"{BYBIT_URL}/v5/market/kline", params=q, timeout=15)
        r.raise_for_status()
        rows = r.json()["result"]["list"]          # newest first
        if not rows:
            break
        out = [x[:6] for x in rows[::-1]] + out
        end = int(rows[-1][0]) - 1
        bars -= len(rows)
    return _frame(out)


def scan(bars: dict[str, pd.DataFrame], params=BOTH_SIDES, at: pd.Timestamp | None = None) -> list[dict]:
    """Signals fired by the last CLOSED bar (or by the bar at `at`). `bars` maps symbol -> 1m OHLCV."""
    found = []
    for sym, df in bars.items():
        f = factor_logret(sym, bars)
        if f is None:                                         # factor itself (BTC, gold): nothing to fade against
            continue
        t = df.index[-1] if at is None else at
        for p in params:
            feat = residual_features(df, f, p.k)
            sg = snapback_signals(feat, p)
            if t in sg.index:
                row, px = sg.loc[t], float(df["close"].loc[t])
                found.append({
                    "time": t, "symbol": sym, "side": "LONG" if row.side > 0 else "SHORT", "lookback_min": p.k,
                    "ref_price": px, "take_profit": px * (1 + row.side * row.tp_frac),
                    "stop_loss": px * (1 - row.side * row.sl_frac), "time_stop_min": p.hold,
                    "move_bp": round(float(feat["resid"].loc[t]) * 1e4, 1), "z": round(float(feat["rz"].loc[t]), 1),
                    "btc_z": round(float(feat["fz"].loc[t]), 1),
                })
    return found


def _print(sigs: list[dict]) -> None:
    for s in sigs:
        print(f"{s['time']:%Y-%m-%d %H:%M} {s['symbol']:<14} {s['side']} k={s['lookback_min']:>2}m "
              f"move={s['move_bp']:>7.1f}bp z={s['z']:>6.1f} btc_z={s['btc_z']:>5.1f} | enter next bar open "
              f"(ref {s['ref_price']:.6g})  TP {s['take_profit']:.6g}  SL {s['stop_loss']:.6g}  "
              f"exit after {s['time_stop_min']}m", flush=True)


def live(venue: str, symbols: list[str], once: bool) -> None:
    fetch = fetch_binance if venue == "binance" else fetch_bybit
    while True:
        with ThreadPoolExecutor(8) as ex:
            got = dict(zip(symbols, ex.map(lambda s: _safe(fetch, s), symbols)))
        now = pd.Timestamp.now(tz="UTC").floor("1min")
        bars = {s: d[d.index < now] for s, d in got.items() if d is not None and len(d) > DAY}  # closed bars only
        sigs = scan(bars) if "BTCUSDT" in bars else []
        _print(sigs)
        if not sigs:
            print(f"{now:%H:%M} scanned {len(bars)} symbols on {venue}: no signal", flush=True)
        if once:
            return
        time.sleep(max(1.0, 60 - time.time() % 60 + 2))


def _safe(fetch, sym):
    try:
        return fetch(sym)
    except Exception as e:                                   # one bad symbol must not stop the scan
        print(f"skip {sym}: {e}", flush=True)
        return None


def replay(day: str, symbols: list[str]) -> list[dict]:
    """Run the scanner over one cached day, bar by bar equivalent (vectorised over the day)."""
    from .data import load_binance
    d0 = pd.Timestamp(day, tz="UTC"); d1 = d0 + pd.Timedelta(days=1)
    start = (d0 - pd.Timedelta(days=4)).strftime("%Y-%m")
    bars = {s: load_binance(s, start, d0.strftime("%Y-%m")).loc[d0 - pd.Timedelta(days=3):d1] for s in symbols}
    out = []
    for sym, df in bars.items():
        if factor_logret(sym, bars) is None:
            continue
        for p in BOTH_SIDES:
            feat = residual_features(df, factor_logret(sym, bars), p.k)
            sg = snapback_signals(feat, p)
            for t in sg.index[sg.index >= d0]:
                out += scan({**{s: b.loc[:t] for s, b in bars.items() if s != sym}, sym: df.loc[:t]}, params=(p,))
    out.sort(key=lambda s: s["time"])
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--venue", choices=["binance", "bybit"], default="binance")
    ap.add_argument("--symbols", nargs="*", default=ALL)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--replay", metavar="YYYY-MM-DD")
    a = ap.parse_args()
    syms = list(dict.fromkeys(["BTCUSDT"] + a.symbols))
    if a.replay:
        sigs = replay(a.replay, syms); _print(sigs); print(f"{len(sigs)} signals on {a.replay}")
    else:
        live(a.venue, syms, a.once)


if __name__ == "__main__":
    main()
