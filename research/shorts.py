from common import *
from scalp.universe import CRYPTO, CRYPTO_STOCKS, STOCKS, METALS
pd.set_option("display.width", 250)
ALTS = [s for s in CRYPTO if s != "BTCUSDT"]
rows = []
for g, syms in (("crypto", ALTS), ("crypto_stock", CRYPTO_STOCKS), ("stock", STOCKS), ("metal", METALS)):
    for side in ("long", "short"):
        for period in ("is", "oos"):
            ps = [SnapbackParams(k=k, z_long=6 if side == "long" else np.inf, z_short=6 if side == "short" else np.inf) for k in (5, 10, 15)]
            tr = pd.concat([run(p, syms, period) for p in ps])
            rows.append({"grp": g, "side": side, "period": period, **summarize(tr)})
print(pd.DataFrame(rows).to_string(index=False))
