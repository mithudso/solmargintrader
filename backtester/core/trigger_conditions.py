"""Causal trading conditions shared by the trigger miner and `trigger_trade`.

Every value at index t is computed from bars 0..t only (trailing windows, EMAs).
`research/triggers.py` mines conjunctions of these; `core/strategies/trigger.py`
trades them. One implementation keeps the mined edge and the traded edge the same
measurement. No I/O here.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# One condition per group in a conjunction: two conditions from the same group
# restate each other (rsi<30 and rsi<20), which would inflate the hypothesis count
# with near-duplicates and make the FDR denominator meaningless.
GROUPS = {
    "macd_x_up": "macd", "macd_x_dn": "macd", "macd_hist_pos": "macd", "macd_hist_neg": "macd",
    "macd_hist_rise": "macd_slope", "macd_hist_fall": "macd_slope",
    "rsi_lt30": "rsi", "rsi_gt70": "rsi", "rsi_lt20": "rsi", "rsi_gt80": "rsi",
    "ma20_slope_up": "ma_slope", "ma20_slope_dn": "ma_slope", "ma50_slope_up": "ma_slope", "ma50_slope_dn": "ma_slope",
    "px_above_ma20": "ma_px", "px_below_ma20": "ma_px", "px_above_ma50": "ma_px", "px_below_ma50": "ma_px",
    "bb_touch_lo": "band", "bb_touch_up": "band", "z_lt_m2": "band", "z_gt_2": "band", "z_lt_m3": "band", "z_gt_3": "band",
    "vol_3x": "vol", "vol_5x": "vol", "vol_10x": "vol",
    "obv_up": "obv", "obv_dn": "obv",
    "bop_bull": "candle", "bop_bear": "candle", "clv_hi": "candle", "clv_lo": "candle",
    "bal5_pos": "balance", "bal5_neg": "balance",
    "atr_expand": "atr", "tr_spike": "atr",
    "consec_up3": "consec", "consec_dn3": "consec", "consec_up5": "consec", "consec_dn5": "consec",
    "gap_up": "gap", "gap_dn": "gap",
    "funding_hi": "funding", "funding_lo": "funding",
    "dd_gt10": "drawdown", "dd_gt20": "drawdown", "dd_gt35": "drawdown", "near_high": "drawdown",
}
FUNDING_CONDITIONS = ("funding_hi", "funding_lo")
BASE_CONDITIONS = tuple(GROUPS)


def _ema(x: pd.Series, span: int) -> pd.Series:
    return x.ewm(span=span, adjust=False).mean()


def compute_conditions(o, h, l, c, v, funding=None, names=None) -> dict[str, np.ndarray]:
    """Boolean arrays, one per condition. `names` restricts the work (trigger_trade)."""
    o, h, l, c, v = (pd.Series(np.asarray(a, float)) for a in (o, h, l, c, v))
    if len({len(a) for a in (o, h, l, c, v)}) != 1 or any(not np.isfinite(a).all() for a in (o, h, l, c, v)):
        raise ValueError("conditions require aligned finite OHLCV")
    # Missing funding is expected before its first settlement; infinity is not.
    if funding is not None and (len(funding) != len(c) or np.isinf(np.asarray(funding, float)).any()):
        raise ValueError("invalid funding measurements")
    want = set(names) if names is not None else set(BASE_CONDITIONS)
    out: dict[str, pd.Series] = {}
    eps = 1e-12
    prev = c.shift(1)

    if want & {"macd_x_up", "macd_x_dn", "macd_hist_pos", "macd_hist_neg", "macd_hist_rise", "macd_hist_fall"}:
        macd = _ema(c, 12) - _ema(c, 26)
        sig = _ema(macd, 9)
        hist = macd - sig
        out["macd_x_up"] = (macd > sig) & (macd.shift(1) <= sig.shift(1))
        out["macd_x_dn"] = (macd < sig) & (macd.shift(1) >= sig.shift(1))
        out["macd_hist_pos"], out["macd_hist_neg"] = hist > 0, hist < 0
        out["macd_hist_rise"], out["macd_hist_fall"] = hist > hist.shift(1), hist < hist.shift(1)
    if want & {"rsi_lt30", "rsi_gt70", "rsi_lt20", "rsi_gt80"}:
        d = c.diff()
        up = d.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
        dn = (-d.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
        rsi = 100 - 100 / (1 + up / (dn + eps))
        out["rsi_lt30"], out["rsi_gt70"] = rsi < 30, rsi > 70
        out["rsi_lt20"], out["rsi_gt80"] = rsi < 20, rsi > 80
    sma20, sma50 = c.rolling(20).mean(), c.rolling(50).mean()
    out["ma20_slope_up"], out["ma20_slope_dn"] = sma20 > sma20.shift(5), sma20 < sma20.shift(5)
    out["ma50_slope_up"], out["ma50_slope_dn"] = sma50 > sma50.shift(5), sma50 < sma50.shift(5)
    out["px_above_ma20"], out["px_below_ma20"] = c > sma20, c < sma20
    out["px_above_ma50"], out["px_below_ma50"] = c > sma50, c < sma50
    sd20 = c.rolling(20).std(ddof=0)
    z = (c - sma20) / (sd20 + eps)
    out["bb_touch_lo"], out["bb_touch_up"] = l <= sma20 - 2 * sd20, h >= sma20 + 2 * sd20
    out["z_lt_m2"], out["z_gt_2"], out["z_lt_m3"], out["z_gt_3"] = z < -2, z > 2, z < -3, z > 3
    med = v.rolling(20).median().shift(1)
    for k in (3, 5, 10):
        out[f"vol_{k}x"] = (med > 0) & (v >= k * med)
    obv = (np.sign(c.diff()).fillna(0) * v).cumsum()
    out["obv_up"], out["obv_dn"] = obv > obv.shift(10), obv < obv.shift(10)
    rng = (h - l)
    bop = (c - o) / (rng + eps)
    clv = ((c - l) - (h - c)) / (rng + eps)
    out["bop_bull"], out["bop_bear"] = bop > 0.5, bop < -0.5
    out["clv_hi"], out["clv_lo"] = clv > 0.8, clv < -0.8
    bal5 = bop.rolling(5).mean()
    out["bal5_pos"], out["bal5_neg"] = bal5 > 0.25, bal5 < -0.25
    tr = pd.concat([h - l, (h - prev).abs(), (l - prev).abs()], axis=1).max(axis=1)
    atr14 = tr.ewm(alpha=1 / 14, adjust=False).mean()
    out["atr_expand"] = atr14 > 1.5 * tr.rolling(50).mean()
    out["tr_spike"] = tr > 2.5 * atr14.shift(1)
    upc, dnc = (c > prev).astype(int), (c < prev).astype(int)
    out["consec_up3"], out["consec_dn3"] = upc.rolling(3).sum() == 3, dnc.rolling(3).sum() == 3
    out["consec_up5"], out["consec_dn5"] = upc.rolling(5).sum() == 5, dnc.rolling(5).sum() == 5
    gap = (o - prev) / (atr14.shift(1) + eps)
    out["gap_up"], out["gap_dn"] = gap > 0.3, gap < -0.3
    if funding is not None:
        f = pd.Series(np.asarray(funding, float))
        rk = f.rolling(90, min_periods=60).rank(pct=True)
        out["funding_hi"], out["funding_lo"] = (rk >= 0.9) & (f > 0), (rk <= 0.1) & (f < 0)
    hi60 = h.rolling(60).max()
    dd = c / hi60 - 1.0
    out["dd_gt10"], out["dd_gt20"], out["dd_gt35"] = dd <= -0.10, dd <= -0.20, dd <= -0.35
    out["near_high"] = dd >= -0.02
    keep = want if names is not None else set(out)
    return {k: out[k].fillna(False).to_numpy(bool) for k in out if k in keep}


