"""Signal generation. The same functions feed the backtest and the live scanner."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

DAY = 1440


@dataclass(frozen=True)
class SnapbackParams:
    """Dislocation snapback: fade a k-minute move that is extreme RELATIVE TO THE FACTOR (BTC / basket)."""
    k: int = 5              # lookback of the move, minutes (5, 10 or 15)
    z_long: float = 6.0     # enter long when residual z <= -z_long   (np.inf disables)
    z_short: float = np.inf # enter short when residual z >= z_short  (np.inf disables; shorts lost in research)
    tp_mult: float = 1.0    # target = tp_mult * |residual move|
    sl_mult: float = 1.0    # stop   = sl_mult * |residual move|
    hold: int = 15          # time stop, minutes
    min_move_bp: float = 100.  # ignore dislocations smaller than this (must clear costs)
    factor_z_min: float = 2.0  # require |factor k-min z| >= this: fade liquidity overshoots, not lone news dumps
    volx_min: float = 0.       # require k-minute volume >= volx_min * its 1-day average


def residual_features(sym: pd.DataFrame, factor_logret: pd.Series | None, k: int) -> pd.DataFrame:
    """Residual k-minute move of `sym` vs the factor, its z-score, and volume surge. No look-ahead:
    every statistic used to scale bar t is computed on bars <= t-1."""
    lc = np.log(sym["close"])
    ra = lc.diff(k)
    fz = pd.Series(0.0, index=sym.index)
    if factor_logret is None:
        resid = ra
    else:
        rf = factor_logret.reindex(sym.index).fillna(0.0).rolling(k).sum()
        beta = (ra.rolling(DAY).cov(rf) / rf.rolling(DAY).var()).shift(1).clip(-1, 4).fillna(1.0)
        resid = ra - beta * rf
        fz = rf / rf.rolling(DAY, min_periods=DAY // 2).std().shift(1)
    sd = resid.rolling(DAY, min_periods=DAY // 2).std().shift(1)
    vk = sym["volume"].rolling(k).sum()
    return pd.DataFrame({"resid": resid, "rz": resid / sd, "volx": vk / vk.rolling(DAY).mean().shift(1),
                         "fz": fz})


def snapback_signals(feat: pd.DataFrame, p: SnapbackParams) -> pd.DataFrame:
    """Rows = bars whose close fires a signal. Columns: side, tp_frac, sl_frac."""
    rz, resid = feat["rz"].values, feat["resid"].values
    mag = np.abs(resid)
    ok = (mag * 1e4 >= p.min_move_bp) & np.isfinite(rz)
    if p.factor_z_min > 0:
        ok &= np.abs(feat["fz"].values) >= p.factor_z_min
    if p.volx_min > 0:
        ok &= feat["volx"].values >= p.volx_min
    side = np.where(ok & (rz <= -p.z_long), 1, np.where(ok & (rz >= p.z_short), -1, 0))
    m = side != 0
    return pd.DataFrame({"side": side[m], "tp_frac": p.tp_mult * mag[m], "sl_frac": p.sl_mult * mag[m]},
                        index=feat.index[m])


# Frozen on in-sample data (2025-07 .. 2026-06) BEFORE the out-of-sample run. Do not tune on OOS.
FROZEN = tuple(SnapbackParams(k=k) for k in (5, 10, 15))
