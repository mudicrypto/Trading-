"""IS study 2: lead-lag, residual reversion, stock-session effects. IS = data < 2026-07-01."""
import sys; sys.path.insert(0, ".")
import numpy as np, pandas as pd
from scalp.data import load_binance
pd.set_option("display.width", 250)
ALTS = ["ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT","DOGEUSDT","ADAUSDT","LINKUSDT","AVAXUSDT","SUIUSDT"]
STOCKS = ["TSLAUSDT","NVDAUSDT","AAPLUSDT","METAUSDT","GOOGLUSDT","MSFTUSDT","AMZNUSDT","COINUSDT","MSTRUSDT","HOODUSDT"]
IS_END = "2026-06-30 23:59"; H = [1, 5, 10, 15]
btc = load_binance("BTCUSDT", "2025-07", "2026-10").loc[:IS_END]
lb = np.log(btc.close)

def fwd(df):
    return pd.DataFrame({h: (df.open.shift(-(1 + h)) / df.open.shift(-1) - 1) * 1e4 for h in H})

def stat(x, sign=1):
    x = (x * sign).dropna(how="all")
    d = {"n": len(x)}
    for h in H:
        c = x[h].dropna(); d[f"bp{h}"] = round(c.mean(), 2); d[f"t{h}"] = round(c.mean() / (c.std() / np.sqrt(max(len(c), 2))), 1)
    return d

def session(idx):
    ny = idx.tz_convert("America/New_York"); m = ny.hour * 60 + ny.minute
    wk = ny.dayofweek < 5
    return np.where(wk & (m >= 570) & (m < 960), "RTH", np.where(wk & (((m >= 240) & (m < 570)) | ((m >= 960) & (m < 1200))), "EXT", "CLOSED"))

rows = []
def add(label, sub, sign=1): rows.append({"signal": label, **stat(sub, sign)})

for grp, syms in (("ALT", ALTS), ("CRYPTOSTK", ["MSTRUSDT", "COINUSDT", "HOODUSDT"])):
    acc = {}
    for s in syms:
        df = load_binance(s, "2025-07", "2026-10").loc[:IS_END]
        b = lb.reindex(df.index); la = np.log(df.close); F = fwd(df)
        for k in (1, 5, 15):
            rb = b.diff(k); ra = la.diff(k)
            beta = (ra.rolling(1440).cov(rb) / rb.rolling(1440).var()).shift(1)
            resid = ra - beta * rb
            rz = resid / resid.rolling(1440).std().shift(1)
            bz = rb / rb.rolling(1440).std().shift(1)
            # lead-lag: BTC jumped, alt has not caught up
            acc.setdefault(f"{grp} leadlag k{k}: btc z>3 & resid z<-1 long", []).append(F[(bz > 3) & (rz < -1)])
            acc.setdefault(f"{grp} leadlag k{k}: btc z<-3 & resid z>1 short", []).append(-F[(bz < -3) & (rz > 1)])
            acc.setdefault(f"{grp} follow k{k}: btc z>3 long", []).append(F[bz > 3])
            acc.setdefault(f"{grp} follow k{k}: btc z<-3 short", []).append(-F[bz < -3])
            # residual reversion: idiosyncratic move while BTC quiet
            acc.setdefault(f"{grp} resid-rev k{k}: resid z<-4 long", []).append(F[rz < -4])
            acc.setdefault(f"{grp} resid-rev k{k}: resid z>4 short", []).append(-F[rz > 4])
            acc.setdefault(f"{grp} resid-rev k{k}: resid z<-6 long", []).append(F[rz < -6])
            acc.setdefault(f"{grp} resid-rev k{k}: resid z>6 short", []).append(-F[rz > 6])
    for k, v in acc.items(): add(k, pd.concat(v))

# stock perps by cash-market session
acc = {}
for s in STOCKS:
    df = load_binance(s, "2026-01", "2026-10").loc[:IS_END]
    F = fwd(df); lc = np.log(df.close); r1 = lc.diff(); vol = r1.rolling(240).std()
    ses = pd.Series(session(df.index), index=df.index)
    for k in (5, 15, 60):
        z = lc.diff(k) / (vol * np.sqrt(k))
        for se in ("RTH", "EXT", "CLOSED"):
            acc.setdefault(f"STK {se} rev k{k}: z<-3 long", []).append(F[(z < -3) & (ses == se)])
            acc.setdefault(f"STK {se} rev k{k}: z>3 short", []).append(-F[(z > 3) & (ses == se)])
    for se in ("RTH", "EXT", "CLOSED"):
        acc.setdefault(f"STK {se} unconditional long (drift)", []).append(F[ses == se])
for k, v in acc.items(): add(k, pd.concat(v))
print(pd.DataFrame(rows).to_string(index=False))
