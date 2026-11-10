from common import *
from scalp.universe import CRYPTO, CRYPTO_STOCKS, STOCKS, METALS
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500)
rows = []
for gname, syms in (("stock", STOCKS), ("crypto_stock", CRYPTO_STOCKS), ("metal", METALS), ("crypto", CRYPTO)):
    for k in (5, 15):
        for z in (3, 5):
            for direction in (1, -1):
                for tp, sl in ((0.5, 1.0), (1.0, 1.0)):
                    out = []
                    for s in syms:
                        df = bars()[s]; f = feat(s, k)
                        m = ((f.rz <= -z) if direction > 0 else (f.rz >= z)) & (f.index < IS_END)
                        idx = np.flatnonzero(m.values); mag = np.abs(f.resid.values[idx])
                        tr = simulate(df.open.values, df.high.values, df.low.values, idx, np.full(len(idx), direction), tp * mag, sl * mag, 15,
                                      Costs(slip_bp=slip_bp(s)), limit_px=df.close.values[idx], wait=3)
                        out.append(trades_frame(tr, df.index, s))
                    rows.append({"grp": gname, "k": k, "z": z, "dir": "long" if direction > 0 else "short", "tp": tp, "sl": sl, **summarize(pd.concat(out))})
    print(pd.DataFrame([r for r in rows if r["grp"] == gname]).to_string(index=False), flush=True)
