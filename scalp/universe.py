"""Symbol universe and per-symbol factor/cost configuration."""
MAJORS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT"]
ALTS = ["ADAUSDT", "LINKUSDT", "AVAXUSDT", "SUIUSDT", "TRXUSDT", "LTCUSDT", "DOTUSDT", "BCHUSDT", "NEARUSDT",
        "APTUSDT", "ARBUSDT", "OPUSDT", "UNIUSDT", "AAVEUSDT", "FILUSDT", "ATOMUSDT", "INJUSDT", "TIAUSDT",
        "SEIUSDT", "WLDUSDT", "ENAUSDT", "HYPEUSDT", "1000PEPEUSDT", "1000SHIBUSDT", "WIFUSDT", "1000BONKUSDT",
        "FARTCOINUSDT", "TRUMPUSDT", "ONDOUSDT", "TAOUSDT", "HBARUSDT", "XLMUSDT", "ETCUSDT", "CRVUSDT",
        "LDOUSDT", "PENGUUSDT", "ZECUSDT"]
CRYPTO = MAJORS + ALTS
CRYPTO_STOCKS = ["MSTRUSDT", "COINUSDT", "HOODUSDT"]           # equities that trade off BTC
STOCKS = ["TSLAUSDT", "NVDAUSDT", "AAPLUSDT", "METAUSDT", "GOOGLUSDT", "MSFTUSDT", "AMZNUSDT"]
METALS = ["XAUUSDT", "XAGUSDT"]
ALL = CRYPTO + CRYPTO_STOCKS + STOCKS + METALS

# Per-side slippage in bp on taker fills (about half the measured effective spread, rounded up).
SLIP_BP = {"ADAUSDT": 3.0}
DEFAULT_SLIP_BP = 1.0


def asset_class(sym: str) -> str:
    if sym in CRYPTO_STOCKS: return "crypto_stock"
    if sym in STOCKS: return "stock"
    if sym in METALS: return "metal"
    return "crypto"


def slip_bp(sym: str) -> float:
    return SLIP_BP.get(sym, 1.5 if asset_class(sym) in ("stock", "crypto_stock") else DEFAULT_SLIP_BP)
