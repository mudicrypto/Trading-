# Trading-

Research code for short-horizon (5-15 minute) signals on Binance USDT-M futures and Bybit linear perps,
covering crypto, tokenised-stock perps and metals.

**Status: no validated edge.** See [RESULTS.md](RESULTS.md). The scanner prints research alerts; it does not
place orders and should not be used to trade real money.

## Layout

- `scalp/data.py` - loaders for the public bulk dumps (`data.binance.vision`, `public.bybit.com`), cached as parquet
- `scalp/backtest.py` - 1-minute trade simulator with conservative fills and fees
- `scalp/strategies.py` - signal functions shared by the backtest and the scanner; `FROZEN` is the tested rule
- `scalp/scanner.py` - live or replay scanner
- `scanner.html` - the same scanner as a single web page; open it in a browser and press Start
- `research/` - the studies behind RESULTS.md
- `tests/` - engine and no-look-ahead tests

## Use

    pip install -r requirements.txt
    python -m pytest -q
    python -m scalp.scanner --replay 2026-08-22            # replay a cached day
    python -m scalp.scanner --venue binance                 # live, polls once a minute
    python -m scalp.scanner --venue bybit --once

The live mode reads public klines from `fapi.binance.com` or `api.bybit.com`. Both block some regions
(HTTP 451 / 403), so run it from a machine in a supported region; `BINANCE_FAPI_URL` and `BYBIT_API_URL`
override the base URLs. The live fetchers could not be exercised from the development container for that reason.
No API key is needed.

## Browser scanner

Open `scanner.html` in a browser, pick Binance or Bybit and press Start. It fetches public klines directly from
the exchange in your browser, rescans just after each minute closes, and lists signals with entry, target, stop
and the outcome of past signals in the loaded window (about 24 hours). Signals are LONG or SHORT, on crypto,
stock and metal perps, and each one shows the held-out backtest record for its type. It uses the same rule and maths as
`scalp/strategies.py`; on cached data its signals match the Python scanner exactly. If the exchange blocks your
region or network the page says so.
