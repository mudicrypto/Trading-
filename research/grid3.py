from common import *
from scalp.universe import CRYPTO, CRYPTO_STOCKS, STOCKS, METALS
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500)
# 1) where does the long-snapback edge live, by factor (BTC) state at signal time?
for k, z in ((5, 6), (5, 8), (15, 6)):
    p = SnapbackParams(k=k, z_long=z, tp_mult=1.0, sl_mult=1.0, hold=15, min_move_bp=100)
    tr = run(p, [s for s in CRYPTO if s != "BTCUSDT"], "is")
    fz = np.concatenate([feat(s, k).fz.values[g.sig.values] for s, g in tr.groupby("symbol", sort=False)])
    tr["fz"] = fz
    tr["btc"] = pd.cut(tr.fz, [-np.inf, -4, -2, -0.5, 0.5, 2, np.inf])
    print(f"\nlong snapback k={k} z={z} by BTC k-min z at signal")
    print(pd.DataFrame({str(b): summarize(g) for b, g in tr.groupby("btc", observed=True)}).T.to_string())
# 2) catch-up short: BTC dumped, alt has not followed (resid high)
rows = []
for k in (1, 5, 15):
    f0 = {s: feat(s, k) for s in CRYPTO if s != "BTCUSDT"}
    for fzmax in (-3, -5):
        for rzmin in (1, 2, 3):
            out = []
            for s, f in f0.items():
                df = bars()[s]
                m = (f.fz <= fzmax) & (f.rz >= rzmin) & (f.index < IS_END)
                idx = np.flatnonzero(m.values)
                mag = np.abs(f.resid.values[idx]) + 0  # target sized by the lag
                tr = simulate(df.open.values, df.high.values, df.low.values, idx, -np.ones(len(idx)), mag * 1.0, mag * 1.0, 15, Costs(slip_bp=slip_bp(s)))
                out.append(trades_frame(tr, df.index, s))
            rows.append({"k": k, "btc_z<=": fzmax, "resid_z>=": rzmin, **summarize(pd.concat(out))})
print("\ncatch-up SHORT (BTC dumped, alt lagging), IS"); print(pd.DataFrame(rows).to_string(index=False))
# 3) stock perps at the US cash open: follow / fade the first 5 minutes
rows = []
for gname, syms in (("stock", STOCKS), ("crypto_stock", CRYPTO_STOCKS)):
    for first, hold in ((5, 10), (5, 15), (15, 15), (1, 5)):
        for thr in (0, 20, 40):
            res = []
            for s in syms:
                df = bars()[s]; df = df[df.index < IS_END]
                ny = df.index.tz_convert("America/New_York")
                mins = ny.hour * 60 + ny.minute
                opens = np.flatnonzero((mins == 570) & (ny.dayofweek < 5))
                o = df.open.values
                for i in opens:
                    if i + first + hold >= len(o): continue
                    r0 = o[i + first] / o[i] - 1
                    if abs(r0) * 1e4 < thr or r0 == 0: continue
                    sd = np.sign(r0); sl = slip_bp(s) / 1e4
                    res.append(sd * (o[i + first + hold] / o[i + first] - 1) - 2 * sl - 10e-4)
            x = np.array(res) * 1e4
            rows.append({"grp": gname, "first_min": first, "hold": hold, "min|r|bp": thr, "n": len(x), "net_follow_bp": round(x.mean(), 2),
                         "gross_follow_bp": round(x.mean() + 10 + 2 * 1.5, 2), "t_gross": round((x.mean() + 13) / (x.std() / np.sqrt(len(x))), 2)})
print("\nSTOCK perps cash-open drive (9:30 ET): follow first N min, IS"); print(pd.DataFrame(rows).to_string(index=False))
