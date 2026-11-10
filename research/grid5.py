from common import *
from scalp.universe import CRYPTO
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500)
ALTS = [s for s in CRYPTO if s != "BTCUSDT"]
def runf(k, z, tp, sl, mm, fmode, period="is", slip_mult=1.0, taker=5.0, syms=ALTS):
    out = []
    for s in syms:
        df = bars()[s]; f = feat(s, k)
        m = (f.rz <= -z) & (f.resid.abs() * 1e4 >= mm)
        if fmode == "moving": m &= f.fz.abs() >= 0.5
        elif fmode == "strong": m &= f.fz.abs() >= 2
        elif fmode == "down": m &= f.fz <= -2
        m &= (f.index < IS_END) if period == "is" else (f.index >= IS_END)
        idx = np.flatnonzero(m.values); mag = np.abs(f.resid.values[idx])
        tr = simulate(df.open.values, df.high.values, df.low.values, idx, np.ones(len(idx)), tp * mag, sl * mag, 15, Costs(taker_bp=taker, slip_bp=slip_bp(s) * slip_mult))
        out.append(trades_frame(tr, df.index, s))
    return pd.concat(out, ignore_index=True)
def extra(tr):
    d = tr.groupby(tr.entry_time.dt.floor("D")).net.sum().sort_values(ascending=False)
    ex = tr[~tr.entry_time.dt.floor("D").isin(d.index[:3])]
    return {"top3d%": round(100 * d.iloc[:3].sum() / max(d.sum(), 1e-9)), "mean_ex3": round(ex.net.mean() * 1e4, 1), "med_ex3": round(ex.net.median() * 1e4, 1)}
if __name__ == "__main__":
    rows = []
    for k in (1, 5, 10, 15):
        for z in (6, 8):
            for fmode in ("none", "moving", "strong", "down"):
                tr = runf(k, z, 1.0, 1.0, 100, fmode)
                rows.append({"k": k, "z": z, "btc": fmode, **summarize(tr), **extra(tr)})
    print(pd.DataFrame(rows).to_string(index=False))
