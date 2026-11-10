from common import *
from scalp.universe import CRYPTO, CRYPTO_STOCKS, STOCKS, METALS
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500)
def extra(tr):
    if tr.empty: return {}
    d = tr.groupby(tr.entry_time.dt.floor("D")).net.sum().sort_values(ascending=False)
    ex = tr[~tr.entry_time.dt.floor("D").isin(d.index[:3])]
    return {"top3d_share%": round(100 * d.iloc[:3].sum() / max(d.sum(), 1e-9), 0), "mean_ex_top3d": round(ex.net.mean() * 1e4, 1),
            "days": len(d)}
rows = []
for k in (5, 15):
    for z in (6, 8):
        for mm in (0, 100, 200):
            for tp, sl in ((0.5, 1.0), (1.0, 1.0), (1.0, 0.5), (9.0, 1.0), (9.0, 9.0)):
                for hold in (15,):
                    p = SnapbackParams(k=k, z_long=z, tp_mult=tp, sl_mult=sl, hold=hold, min_move_bp=mm)
                    tr = run(p, CRYPTO, "is")
                    rows.append({"k": k, "z": z, "minbp": mm, "tp": tp, "sl": sl, **summarize(tr), **extra(tr)})
print("CRYPTO long-only snapback, IS"); print(pd.DataFrame(rows).to_string(index=False), flush=True)
# absolute-size dislocations in stocks/metals (z disabled via z=0 + min move)
rows = []
for gname, syms in (("crypto_stock", CRYPTO_STOCKS), ("stock", STOCKS), ("metal", METALS)):
    for k in (5, 15):
        for mm in (60, 100, 150):
            for direction in ("long", "short"):
                p = SnapbackParams(k=k, z_long=3 if direction == "long" else np.inf, z_short=3 if direction == "short" else np.inf,
                                   tp_mult=1.0, sl_mult=1.0, hold=15, min_move_bp=mm)
                tr = run(p, syms, "is")
                rows.append({"grp": gname, "k": k, "minbp": mm, "dir": direction, **summarize(tr)})
print("\nSTOCK/METAL absolute dislocations, IS"); print(pd.DataFrame(rows).to_string(index=False))
