from common import *
from scalp.universe import CRYPTO, CRYPTO_STOCKS, STOCKS, METALS
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500)
groups = {"crypto": CRYPTO, "crypto_stock": CRYPTO_STOCKS, "stock": STOCKS, "metal": METALS}
rows = []
for gname, syms in groups.items():
    for k in (1, 5, 15):
        for z in (4, 6, 8):
            for direction in ("long", "short"):
                for tp, sl in ((0.5, 1.0), (1.0, 1.0)):
                    p = SnapbackParams(k=k, z_long=z if direction == "long" else np.inf,
                                       z_short=z if direction == "short" else np.inf, tp_mult=tp, sl_mult=sl, hold=15)
                    tr = run(p, syms, "is")
                    rows.append({"grp": gname, "k": k, "z": z, "dir": direction, "tp": tp, "sl": sl, **summarize(tr)})
    print(pd.DataFrame([r for r in rows if r["grp"] == gname]).to_string(index=False), flush=True)
