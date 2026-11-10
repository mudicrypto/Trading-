import sys; sys.path.insert(0, ".")
from scalp.data import load_binance
from scalp.universe import ALL
ok = []
for s in ALL:
    try:
        df = load_binance(s, "2025-07", "2026-10"); ok.append(s)
        print(s, len(df), str(df.index[0])[:10], f"medQV/min={df.quote_volume.median():.0f}", flush=True)
    except Exception as e:
        print(s, "MISSING", e, flush=True)
