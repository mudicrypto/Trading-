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
