"""Event-driven trade simulator on 1-minute bars with conservative execution.

Rules (identical for every strategy):
  * A signal on the close of bar t is filled at the OPEN of bar t+1 as a taker (fee + slippage).
  * Take-profit is a resting limit: it fills only if price trades THROUGH it (strict), at maker fee.
  * Stop-loss is a taker order: fills at the stop (or at the bar open if price gapped past it) plus slippage.
  * If a bar touches both stop and target, the stop is assumed to have been hit first.
  * After `hold` minutes the position is closed at the next bar open as a taker.
  * One position per symbol at a time.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Costs:
    taker_bp: float = 5.0      # Binance USDT-M VIP0 taker; Bybit linear is 5.5
    maker_bp: float = 2.0      # both venues, VIP0
    slip_bp: float = 1.0       # per taker fill


def simulate(o, h, l, sig_idx, side, tp_frac, sl_frac, hold, costs: Costs, limit_px=None, wait: int = 3):
    """Simulate trades. Arrays o/h/l are 1m bars; sig_idx are bar indices whose close fired a signal.

    side/tp_frac/sl_frac are arrays aligned with sig_idx. If `limit_px` is given the entry is a resting
    limit order (maker fee) that lives for `wait` bars and fills only when price trades strictly through
    it; a take-profit can never fill on the entry bar in that mode. Returns a list of tuples
    (signal_idx, entry_idx, exit_idx, side, entry_px, exit_px, net_return, reason).
    """
    n = len(o)
    slip = costs.slip_bp / 1e4
    tk, mk = costs.taker_bp / 1e4, costs.maker_bp / 1e4
    out = []
    busy_until = -1
    for i, t in enumerate(sig_idx):
        e = t + 1
        if e <= busy_until or e + (wait if limit_px is not None else 0) + hold >= n:
            continue
        sd = side[i]
        if limit_px is None:
            entry = o[e] * (1 + sd * slip)
        else:
            entry = limit_px[i]; e = -1
            for j in range(t + 1, t + 1 + wait):
                if (sd > 0 and l[j] < entry) or (sd < 0 and h[j] > entry):
                    e = j
                    break
            if e < 0:
                continue
        tp = entry * (1 + sd * tp_frac[i])
        sl = entry * (1 - sd * sl_frac[i])
        exit_px = np.nan; reason = ""; x = e
        for j in range(e, e + hold):
            if sd > 0:
                if j > e and o[j] <= sl: exit_px, reason = o[j] * (1 - slip), "sl"
                elif l[j] <= sl: exit_px, reason = sl * (1 - slip), "sl"
                elif h[j] > tp and not (limit_px is not None and j == e): exit_px, reason = tp, "tp"
            else:
                if j > e and o[j] >= sl: exit_px, reason = o[j] * (1 + slip), "sl"
                elif h[j] >= sl: exit_px, reason = sl * (1 + slip), "sl"
                elif l[j] < tp and not (limit_px is not None and j == e): exit_px, reason = tp, "tp"
            if reason:
                x = j
                break
        if not reason:
            x = e + hold
            exit_px, reason = o[x] * (1 - sd * slip), "time"
        fee = (tk if limit_px is None else mk) + (mk if reason == "tp" else tk)
        net = sd * (exit_px / entry - 1) - fee
        out.append((t, e, x, sd, entry, exit_px, net, reason))
        busy_until = x
    return out


def trades_frame(trades, index, symbol: str) -> pd.DataFrame:
    df = pd.DataFrame(trades, columns=["sig", "entry", "exit", "side", "entry_px", "exit_px", "net", "reason"])
    df["symbol"] = symbol
    df["entry_time"] = index[df["entry"].values] if len(df) else pd.to_datetime([], utc=True)
    df["exit_time"] = index[df["exit"].values] if len(df) else pd.to_datetime([], utc=True)
    df["bars"] = df["exit"] - df["entry"]
    return df


def summarize(tr: pd.DataFrame) -> dict:
    """Portfolio statistics for a set of trades (net of all costs, per-trade in bp)."""
    if tr.empty:
        return {"n": 0}
    net = tr["net"].values * 1e4
    wins = net[net > 0]; losses = net[net <= 0]
    daily = tr.groupby(tr["entry_time"].dt.floor("D"))["net"].sum()
    monthly = tr.groupby(tr["entry_time"].dt.strftime("%Y-%m"))["net"].sum()
    return {
        "n": len(net),
        "mean_bp": round(float(net.mean()), 2),
        "median_bp": round(float(np.median(net)), 2),
        "win%": round(100 * len(wins) / len(net), 1),
        "pf": round(float(wins.sum() / -losses.sum()), 2) if losses.sum() < 0 else float("inf"),
        "t": round(float(net.mean() / (net.std(ddof=1) / np.sqrt(len(net)))), 2) if len(net) > 2 else 0.0,
        # t-stat of DAILY summed returns: robust to same-day clustering of trades
        "t_day": round(float(daily.mean() / (daily.std(ddof=1) / np.sqrt(len(daily)))), 2) if len(daily) > 2 else 0.0,
        "sum_%": round(float(net.sum() / 100), 1),
        "pos_months": f"{int((monthly > 0).sum())}/{len(monthly)}",
        "avg_bars": round(float(tr["bars"].mean()), 1),
    }
