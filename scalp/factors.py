"""Factor (benchmark) return series used to isolate a symbol's idiosyncratic move."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .universe import METALS, STOCKS, asset_class


def factor_logret(sym: str, bars: dict[str, pd.DataFrame]) -> pd.Series | None:
    """1-minute log-return of the factor for `sym`.

    crypto + crypto-linked stocks -> BTC;  mega-cap stocks -> equal-weight basket of the OTHER stock perps;
    silver -> gold;  BTC and gold themselves -> None (raw move).
    """
    cls = asset_class(sym)
    if cls in ("crypto", "crypto_stock"):
        return None if sym == "BTCUSDT" else np.log(bars["BTCUSDT"]["close"]).diff()
    if cls == "stock":
        others = [np.log(bars[s]["close"]).diff() for s in STOCKS if s != sym and s in bars]
        return pd.concat(others, axis=1).mean(axis=1) if others else None
    if cls == "metal":
        return None if sym == "XAUUSDT" else np.log(bars[METALS[0]]["close"]).diff()
    return None
