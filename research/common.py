import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import pickle, os
import numpy as np, pandas as pd
from scalp.data import load_binance
from scalp.universe import ALL, asset_class, slip_bp
from scalp.factors import factor_logret
from scalp.strategies import residual_features, snapback_signals, SnapbackParams
from scalp.backtest import simulate, trades_frame, summarize, Costs
IS_END = pd.Timestamp("2026-07-01", tz="UTC")
_bars = None
def bars():
    global _bars
    if _bars is None:
        _bars = {s: load_binance(s, "2025-07", "2026-10") for s in ALL}
    return _bars
_feat = {}
def feat(sym, k):
    if (sym, k) not in _feat:
        b = bars(); _feat[(sym, k)] = residual_features(b[sym], factor_logret(sym, b), k)
    return _feat[(sym, k)]
def run(p, syms, period="is", taker_bp=5.0, slip_mult=1.0):
    out = []
    for s in syms:
        df = bars()[s]; f = feat(s, p.k)
        sg = snapback_signals(f, p)
        sg = sg[sg.index < IS_END] if period == "is" else sg[sg.index >= IS_END] if period == "oos" else sg
        if sg.empty: continue
        idx = df.index.get_indexer(sg.index)
        tr = simulate(df.open.values, df.high.values, df.low.values, idx, sg.side.values, sg.tp_frac.values,
                      sg.sl_frac.values, p.hold, Costs(taker_bp=taker_bp, slip_bp=slip_bp(s) * slip_mult))
        out.append(trades_frame(tr, df.index, s))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()
