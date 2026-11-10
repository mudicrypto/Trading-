"""Estimate effective spread (bp) from Binance aggTrades: price gap between consecutive opposite-side trades <1s apart."""
import sys, io, zipfile, requests, numpy as np, pandas as pd
from concurrent.futures import ThreadPoolExecutor
SYMS = ["SOLUSDT","XRPUSDT","DOGEUSDT","ADAUSDT","LINKUSDT","AVAXUSDT","SUIUSDT","BNBUSDT","TSLAUSDT","NVDAUSDT","AAPLUSDT","METAUSDT","GOOGLUSDT","MSFTUSDT","AMZNUSDT","COINUSDT","MSTRUSDT","HOODUSDT","XAUUSDT","XAGUSDT"]
DAYS = {"Wed": "2026-06-17", "Sat": "2026-06-20"}
def one(args):
    s, d = args
    r = requests.get(f"https://data.binance.vision/data/futures/um/daily/aggTrades/{s}/{s}-aggTrades-{d}.zip", timeout=120)
    if r.status_code != 200: return s, d, None
    z = zipfile.ZipFile(io.BytesIO(r.content))
    t = pd.read_csv(z.open(z.namelist()[0]))
    t.columns = ["id","price","qty","f","l","time","bm"][:len(t.columns)]
    p = t.price.values; bm = t.bm.astype(str).str.lower().eq("true").values; tm = t.time.values
    flip = (bm[1:] != bm[:-1]) & ((tm[1:] - tm[:-1]) < 1000)
    sp = np.abs(p[1:] - p[:-1])[flip] / p[1:][flip] * 1e4
    return s, d, (len(t), float(np.median(sp)), float(np.mean(sp)), float(np.quantile(sp, .9)))
with ThreadPoolExecutor(8) as ex:
    res = list(ex.map(one, [(s, d) for s in SYMS for d in DAYS.values()]))
print(f"{'sym':10} {'day':11} {'trades':>8} {'med_bp':>7} {'mean_bp':>7} {'p90_bp':>7}")
for s, d, x in res:
    print(f"{s:10} {d:11} " + ("n/a" if x is None else f"{x[0]:8d} {x[1]:7.2f} {x[2]:7.2f} {x[3]:7.2f}"))
