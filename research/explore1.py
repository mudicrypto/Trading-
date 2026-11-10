"""In-sample signal study: gross forward returns (bp) after candidate triggers. IS = data < 2026-07-01."""
import sys; sys.path.insert(0, ".")
import numpy as np, pandas as pd
from scalp.data import load_binance
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500)
CRYPTO = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT","DOGEUSDT","ADAUSDT","LINKUSDT","AVAXUSDT","SUIUSDT"]
STOCKS = ["TSLAUSDT","NVDAUSDT","AAPLUSDT","METAUSDT","GOOGLUSDT","MSFTUSDT","AMZNUSDT","COINUSDT","MSTRUSDT","HOODUSDT"]
METALS = ["XAUUSDT","XAGUSDT"]
IS_END = "2026-06-30 23:59"
H = [1, 5, 10, 15]

def feats(df):
    o, h, l, c, v = df.open, df.high, df.low, df.close, df.volume
    r1 = np.log(c).diff()
    vol = r1.rolling(240).std()                       # 4h realised 1m vol
    f = pd.DataFrame(index=df.index)
    for k in (1, 3, 5, 15, 30, 60):
        f[f"z{k}"] = np.log(c / c.shift(k)) / (vol * np.sqrt(k))
    f["volx"] = v / v.rolling(240).mean()
    imb = (2 * df.taker_buy_base - v)
    f["imb1"] = imb / v.replace(0, np.nan)
    f["imb5"] = imb.rolling(5).sum() / v.rolling(5).sum().replace(0, np.nan)
    f["imb15"] = imb.rolling(15).sum() / v.rolling(15).sum().replace(0, np.nan)
    pv = (c * v).rolling(240).sum() / v.rolling(240).sum()
    f["vwapz"] = np.log(c / pv) / (vol * np.sqrt(120))
    rng = (h - l).replace(0, np.nan)
    f["lowwick"] = (np.minimum(o, c) - l) / rng
    f["upwick"] = (h - np.maximum(o, c)) / rng
    f["rngx"] = (h - l) / (h - l).rolling(240).mean()
    f["hh60"] = (c > h.shift(1).rolling(60).max()).astype(float)
    f["ll60"] = (c < l.shift(1).rolling(60).min()).astype(float)
    f["volbp"] = vol * 1e4
    for hz in H:
        f[f"fwd{hz}"] = (o.shift(-(1 + hz)) / o.shift(-1) - 1) * 1e4
    return f

def load_group(syms):
    out = {}
    for s in syms:
        df = load_binance(s, "2025-07", "2026-10")
        out[s] = feats(df).loc[:IS_END]
    return out

def report(name, group, conds):
    rows = []
    for label, fn, sign in conds:
        parts = []
        for s, f in group.items():
            m = fn(f).fillna(False)
            parts.append(f.loc[m, [f"fwd{h}" for h in H]] * sign)
        x = pd.concat(parts)
        row = {"signal": label, "n": len(x)}
        for h in H:
            col = x[f"fwd{h}"].dropna()
            row[f"bp{h}"] = round(col.mean(), 2)
            row[f"t{h}"] = round(col.mean() / (col.std() / np.sqrt(len(col))), 1) if len(col) > 30 else np.nan
        rows.append(row)
    print(f"\n=== {name} (gross bp, sign-adjusted; cost hurdle ~10-12bp taker RT, ~4-7bp maker) ===")
    print(pd.DataFrame(rows).to_string(index=False))

conds = [
    ("rev: z1<-3 long",                 lambda f: f.z1 < -3, 1),
    ("rev: z1>3 short",                 lambda f: f.z1 > 3, -1),
    ("rev: z1<-5 long",                 lambda f: f.z1 < -5, 1),
    ("rev: z1>5 short",                 lambda f: f.z1 > 5, -1),
    ("rev: z5<-3 long",                 lambda f: f.z5 < -3, 1),
    ("rev: z5>3 short",                 lambda f: f.z5 > 3, -1),
    ("rev: z5<-4 & volx>3 long",        lambda f: (f.z5 < -4) & (f.volx > 3), 1),
    ("rev: z5>4 & volx>3 short",        lambda f: (f.z5 > 4) & (f.volx > 3), -1),
    ("rev: z15<-3 long",                lambda f: f.z15 < -3, 1),
    ("rev: z15>3 short",                lambda f: f.z15 > 3, -1),
    ("rev: z15<-4 & imb15<-.15 long",   lambda f: (f.z15 < -4) & (f.imb15 < -.15), 1),
    ("rev: z15>4 & imb15>.15 short",    lambda f: (f.z15 > 4) & (f.imb15 > .15), -1),
    ("wick: rngx>4 lowwick>.6 long",    lambda f: (f.rngx > 4) & (f.lowwick > .6), 1),
    ("wick: rngx>4 upwick>.6 short",    lambda f: (f.rngx > 4) & (f.upwick > .6), -1),
    ("capit: z1<-6 volx>8 long",        lambda f: (f.z1 < -6) & (f.volx > 8), 1),
    ("blowoff: z1>6 volx>8 short",      lambda f: (f.z1 > 6) & (f.volx > 8), -1),
    ("mom: hh60 & volx>3 long",         lambda f: (f.hh60 == 1) & (f.volx > 3), 1),
    ("mom: ll60 & volx>3 short",        lambda f: (f.ll60 == 1) & (f.volx > 3), -1),
    ("mom: hh60 volx>3 imb1>.3 long",   lambda f: (f.hh60 == 1) & (f.volx > 3) & (f.imb1 > .3), 1),
    ("mom: ll60 volx>3 imb1<-.3 short", lambda f: (f.ll60 == 1) & (f.volx > 3) & (f.imb1 < -.3), -1),
    ("mom: z30>3 long",                 lambda f: f.z30 > 3, 1),
    ("mom: z30<-3 short",               lambda f: f.z30 < -3, -1),
    ("vwap: vwapz<-2.5 long",           lambda f: f.vwapz < -2.5, 1),
    ("vwap: vwapz>2.5 short",           lambda f: f.vwapz > 2.5, -1),
    ("flow: imb5>.4 long",              lambda f: f.imb5 > .4, 1),
    ("flow: imb5<-.4 short",            lambda f: f.imb5 < -.4, -1),
    ("absorb: imb5<-.3 & z5>0 long",    lambda f: (f.imb5 < -.3) & (f.z5 > 0), 1),
    ("absorb: imb5>.3 & z5<0 short",    lambda f: (f.imb5 > .3) & (f.z5 < 0), -1),
]
for name, syms in (("CRYPTO majors BTC/ETH/SOL", CRYPTO[:3]), ("CRYPTO alts", CRYPTO[3:]), ("STOCK perps", STOCKS), ("METALS", METALS)):
    g = load_group(syms)
    print(name, "median 1m vol bp:", {s: round(float(f.volbp.median()), 1) for s, f in g.items()})
    report(name, g, conds)
