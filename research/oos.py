from common import *
from scalp.universe import CRYPTO, CRYPTO_STOCKS, STOCKS, METALS
from scalp.strategies import FROZEN
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500)
ALTS = [s for s in CRYPTO if s != "BTCUSDT"]
def extra(tr):
    d = tr.groupby(tr.entry_time.dt.floor("D")).net.sum().sort_values(ascending=False)
    ex = tr[~tr.entry_time.dt.floor("D").isin(d.index[:3])]
    return {"top3d%": round(100 * d.iloc[:3].sum() / max(d.sum(), 1e-9)), "mean_ex3": round(ex.net.mean() * 1e4, 1), "med_ex3": round(ex.net.median() * 1e4, 1), "days": len(d)}
rows = []; keep = {}
for period in ("is", "oos"):
    for p in FROZEN:
        tr = run(p, ALTS, period); keep[(period, p.k)] = tr
        rows.append({"period": period, "k": p.k, **summarize(tr), **extra(tr)})
print(pd.DataFrame(rows).to_string(index=False))
print("\nOOS cost stress (all three lookbacks pooled)")
rows = []
for label, taker, sm in (("Binance base 5.0bp taker, 1x slip", 5.0, 1), ("Bybit 5.5bp taker, 1x slip", 5.5, 1), ("5.5bp taker, 3x slip", 5.5, 3), ("5.5bp taker, 6x slip", 5.5, 6), ("5.5bp taker, 10x slip", 5.5, 10)):
    tr = pd.concat([run(p, ALTS, "oos", taker_bp=taker, slip_mult=sm) for p in FROZEN])
    rows.append({"scenario": label, **summarize(tr), **extra(tr)})
print(pd.DataFrame(rows).to_string(index=False))
oos = pd.concat([keep[("oos", p.k)].assign(k=p.k) for p in FROZEN]); oos.to_parquet("../data/oos_trades.parquet")
pd.concat([keep[("is", p.k)].assign(k=p.k) for p in FROZEN]).to_parquet("../data/is_trades.parquet")
print("\nOOS by month"); print(oos.groupby(oos.entry_time.dt.strftime("%Y-%m")).net.agg(n="size", mean_bp=lambda x: round(x.mean() * 1e4, 1), win=lambda x: round((x > 0).mean() * 100, 1), sum_pct=lambda x: round(x.sum() * 100, 1)).to_string())
print("\nOOS exit reasons"); print(oos.groupby("reason").net.agg(n="size", mean_bp=lambda x: round(x.mean() * 1e4, 1)).to_string())
print("\nOOS top/bottom days"); d = oos.groupby(oos.entry_time.dt.floor("D")).net.agg(["size", "sum"]).sort_values("sum"); print((d.head(5)).to_string()); print(d.tail(5).to_string())
print("\nSame frozen rule on non-crypto groups, OOS (expected: no edge)")
rows = []
for g, syms in (("crypto_stock", CRYPTO_STOCKS), ("stock", STOCKS), ("metal", METALS)):
    for mm in (100, 40):
        tr = pd.concat([run(SnapbackParams(k=p.k, min_move_bp=mm), syms, "oos") for p in FROZEN])
        rows.append({"grp": g, "min_move_bp": mm, **summarize(tr)})
print(pd.DataFrame(rows).to_string(index=False))
