import numpy as np
import pandas as pd

from scalp.backtest import Costs, simulate
from scalp.scanner import scan
from scalp.strategies import SnapbackParams, residual_features, snapback_signals

Z = Costs(taker_bp=0, maker_bp=0, slip_bp=0)


def test_entry_is_next_bar_open_and_time_stop():
    o = np.array([100, 101, 102, 103, 104, 105.0]); h = o + .1; l = o - .1
    (t, e, x, sd, ep, xp, net, why), = simulate(o, h, l, [0], [1], [1.0], [1.0], 3, Z)
    assert (e, x, ep, xp, why) == (1, 4, 101, 104, "time") and abs(net - (104 / 101 - 1)) < 1e-12


def test_stop_wins_when_bar_touches_both():
    o = np.array([100, 100, 100, 100, 100.0]); h = np.array([100, 100, 103, 100, 100.0]); l = np.array([100, 100, 97, 100, 100.0])
    (*_, net, why), = simulate(o, h, l, [0], [1], [0.02], [0.02], 3, Z)
    assert why == "sl" and net < 0


def test_take_profit_needs_trade_through_and_pays_maker():
    o = np.full(6, 100.0); l = o.copy(); h = np.array([100, 100, 102, 100, 102.5, 100.0])
    (_, _, x, *_, net, why), = simulate(o, h, l, [0], [1], [0.02], [0.05], 4, Costs(taker_bp=5, maker_bp=2, slip_bp=0))
    assert why == "tp" and x == 4                      # a touch at exactly 102 on bar 2 does not fill
    assert abs(net - (0.02 - 7e-4)) < 1e-12            # taker in, maker out


def test_stop_gap_fills_at_open_and_short_side():
    o = np.array([100, 100, 106, 100, 100.0]); h = o + .5; l = o - .5
    (*_, xp, net, why), = simulate(o, h, l, [0], [-1], [0.05], [0.03], 3, Z)
    assert why == "sl" and xp == 106 and abs(net + 0.06) < 1e-12


def test_one_position_at_a_time():
    o = np.full(20, 100.0)
    tr = simulate(o, o + .1, o - .1, [0, 1, 2, 10], [1] * 4, [1.0] * 4, [1.0] * 4, 5, Z)
    assert [t[0] for t in tr] == [0, 10]


def _market(n=6000, seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2026-01-01", periods=n, freq="1min", tz="UTC")
    rb = rng.normal(0, 5e-4, n); ra = 1.2 * rb + rng.normal(0, 5e-4, n)
    rb[4000:4005] -= 0.004; ra[4000:4005] -= 0.004 * 1.2 + 0.012      # market flush + alt overshoot
    def frame(r):
        c = 100 * np.exp(np.cumsum(r)); o = np.r_[100, c[:-1]]
        return pd.DataFrame({"open": o, "high": np.maximum(o, c), "low": np.minimum(o, c), "close": c, "volume": 1.0}, index=idx)
    return frame(ra), frame(rb)


def test_features_have_no_lookahead():
    alt, btc = _market(); f = np.log(btc.close).diff(); p = SnapbackParams(k=5)
    full = residual_features(alt, f, 5); cut = residual_features(alt.iloc[:4500], f.iloc[:4500], 5)
    pd.testing.assert_frame_equal(full.iloc[:4500], cut)
    sg = snapback_signals(full, p)
    assert len(sg) and (sg.side == 1).all() and sg.index.min() >= alt.index[4000]


def test_scanner_matches_backtest_signal():
    alt, btc = _market(); p = SnapbackParams(k=5)
    sg = snapback_signals(residual_features(alt, np.log(btc.close).diff(), 5), p)
    t = sg.index[0]
    got = scan({"ETHUSDT": alt.loc[:t], "BTCUSDT": btc.loc[:t]}, params=(p,))
    assert len(got) == 1 and got[0]["side"] == "LONG" and got[0]["stop_loss"] < got[0]["ref_price"] < got[0]["take_profit"]
    assert scan({"ETHUSDT": alt.loc[:t - pd.Timedelta(minutes=30)], "BTCUSDT": btc.loc[:t]}, params=(p,)) == []
