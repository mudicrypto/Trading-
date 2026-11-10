# Research results: scalp signals on Binance / Bybit perps

**Bottom line: no strategy tested here has a validated edge after costs. The one rule that looked
profitable in-sample did not hold up out-of-sample. Do not trade this with real money.**

## Setup

- Data: Binance USDT-M futures 1-minute bars from `data.binance.vision`.
  43 crypto perps (2025-07 to 2026-10), 10 stock perps (TSLA, NVDA, AAPL, META, GOOGL, MSFT, AMZN, COIN, MSTR, HOOD;
  from listing in Jan-Apr 2026), gold and silver.
- Split, fixed before any testing: **in-sample** = up to 2026-06-30, **out-of-sample** = 2026-07-01 to 2026-10-31.
  The out-of-sample period was run once, after the rule was frozen.
- Execution model (`scalp/backtest.py`): signal on bar close, fill at next bar open as taker; stop assumed hit
  first if a bar touches stop and target; targets need a strict trade-through.
- Costs: 5 bp taker / 2 bp maker per side (Binance VIP0; Bybit taker is 5.5 bp) plus 1-3 bp slippage per taker fill.
  Slippage was calibrated from tick data (`research/spreads.py`): effective spread is about 1 bp on most symbols,
  including stock perps, and about 6 bp on ADA.
- Round-trip taker cost is therefore about 12 bp. Median 1-minute volatility is 3-10 bp.

## What was tested (in-sample)

| Family | Result net of costs |
|---|---|
| Z-score reversal 1/5/15 min, volume-spike reversal, wick and capitulation bars | 0-5 bp gross; loses about the cost |
| Breakout of 60-min high/low with volume and taker-flow confirmation | about 0 bp gross; loses |
| VWAP deviation, taker-flow imbalance, absorption | 0-1 bp gross; loses |
| BTC to alt lead-lag, catch-up longs and shorts | 2-10 bp gross; shorts lose in all 18 variants |
| BTC to MSTR/COIN/HOOD lead-lag | 5-8 bp gross (t up to 11) but below cost |
| Stock perps: cash-open drive, session-conditional reversal | no effect (t < 1) |
| Stock / metal perps: dislocation fades, taker and maker entries | negative in every variant |
| Shorting extreme spikes (all groups) | negative, 0/12 positive months in crypto |
| **Crypto long snapback** (buy an extreme drop relative to BTC) | **positive in-sample, see below** |

## The one candidate: crypto dislocation snapback

Rule, frozen on in-sample data (`scalp/strategies.py: FROZEN`): for each alt, take the 5, 10 or 15-minute return
minus beta times BTC's return. Go long when that residual is at least 6 standard deviations negative, at least
100 bp in size, and BTC itself is moving (|z| >= 2). Target and stop are each 1x the size of the dislocation;
close after 15 minutes. A 1-minute lookback had no edge in-sample and was dropped.

| Period | Lookback | Trades | Mean net / trade | Win % | Profit factor | t (daily) | Mean excl. best 3 days |
|---|---|---|---|---|---|---|---|
| In-sample | 5 min | 2020 | +34.0 bp | 57.1 | 1.25 | 2.88 | +23.7 bp |
| In-sample | 10 min | 1614 | +74.1 bp | 59.7 | 1.50 | 2.56 | +41.6 bp |
| In-sample | 15 min | 1348 | +102.9 bp | 59.0 | 1.59 | 2.00 | +47.3 bp |
| **Out-of-sample** | 5 min | 713 | **-6.2 bp** | 48.9 | 0.92 | -0.57 | -16.3 bp |
| **Out-of-sample** | 10 min | 576 | **+6.2 bp** | 50.9 | 1.08 | 0.30 | -17.8 bp |
| **Out-of-sample** | 15 min | 478 | **+10.1 bp** | 52.1 | 1.12 | 0.40 | -19.0 bp |

Out-of-sample, pooled: 1767 trades, +2.2 bp per trade, t = 0.35, profit factor 1.03, 2 of 4 months positive.
With Bybit fees and 3x slippage it is -2.7 bp per trade; slippage is likely to be worse than 1x in exactly the
flush conditions that trigger this rule. One day (2026-10-08) lost more than the best day made.

The in-sample profit was concentrated in a few market-wide crash days (the best 3 days were 37-67% of the total).
That did not repeat. The honest reading is that this is not a reliable edge.

## Long and short on every group (what the scanners now show)

Same rule as above, mirrored for shorts (sell when the residual is at least 6 standard deviations UP), on every
asset group. Net per trade, 5/10/15-minute lookbacks combined (`research/shorts.py`):

| Group | Side | Design data | Held-out | Held-out trades | Held-out win % |
|---|---|---|---|---|---|
| Crypto | Long | +65.6 bp | +2.2 bp | 1767 | 50.4 |
| Crypto | Short | -85.3 bp | -29.0 bp | 854 | 41.2 |
| MSTR/COIN/HOOD | Long | -10.6 bp | +13.9 bp | 275 | 56.7 |
| MSTR/COIN/HOOD | Short | -21.5 bp | -8.4 bp | 328 | 47.9 |
| Stocks | Long | -14.7 bp | -10.0 bp | 397 | 40.8 |
| Stocks | Short | -5.7 bp | -20.6 bp | 466 | 41.8 |
| Metals | Long | +15.6 bp | -26.3 bp | 4 | 0 |
| Metals | Short | -19.8 bp | -113.8 bp | 1 | 0 |

Shorts lose in every group. The MSTR/COIN/HOOD long result is positive on held-out data but negative on the design
data, so it is not evidence of an edge.

## Caveats

- The universe is today's liquid perps, so there is survivorship bias in favour of the results.
- Stock perps only have 5 months of in-sample history, and they are thin (about $1-15k traded per minute).
- Trades cluster: one flush fires dozens of signals at once. Per-trade averages overstate what one account could capture.
- Bybit was not backtested separately; the Bybit numbers above are the same Binance fills with Bybit's fee.
- Only bar data was used. Order-book signals were not tested.

## Reproduce

    pip install -r requirements.txt
    python research/fetch.py        # about 1.6 GB into data/
    python research/explore1.py     # textbook signals
    python research/explore2.py     # lead-lag, residuals, stock sessions
    cd research && python grid1.py && python grid2.py && python grid3.py && python grid4.py && python grid5.py
    cd research && python oos.py    # frozen rule, in-sample vs out-of-sample
    cd research && python shorts.py # long and short, every group
