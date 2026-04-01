"""
valuation_engine.py — Layered dynasty valuation: model vs market.

Architecture
------------
1. MarketComposite   KTC (sentiment) + FantasyCalc (executed) → market_price
2. IntrinsicModel    Age-forward present-value formula         → intrinsic_value
3. ScarcityModel     Replacement-level premium                 → scarcity_mult
4. build_valuation_results   Portfolio-level calibration + spread scoring

Framing
-------
- KTC  = perceived community sentiment (what people say players are worth)
- FC   = cleared market price (what people actually pay in completed trades)
- Neither is the "intrinsic value" of the player.  Both feed only the market layer.
- Intrinsic value is estimated independently via a 3-year present-value model.
- Spread = intrinsic_value − market_price → buy / hold / sell signal.

Key design decisions
--------------------
- Market composite uses a configurable KTC/FC split (default 50/50).
  The old 65/35 bias toward KTC introduced unwarranted sentiment weighting.
- The ±4 %/−8 % disagreement boosts are removed.  KTC vs FC disagreement is
  surfaced as sentiment_gap but does NOT directly inflate or deflate the score.
- The flat rookie_contract_bonus and hard veteran_floor are removed.
  Age effects belong exclusively in the intrinsic model's survival + age curves.
- Static scarcity tiers ("top-5 QB +8 %") are replaced with a continuous
  replacement-level function driven by actual league settings.
- Intrinsic values are portfolio-calibrated so spreads are meaningful comparisons
  on the same ~10 000-point scale as KTC/FC market prices.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

# ---------------------------------------------------------------------------
# Module-level configuration (single source of truth for all model constants)
# ---------------------------------------------------------------------------

INTRINSIC_DISCOUNT_RATE: float = 0.12     # Annual time-discount for dynasty PV
INTRINSIC_HORIZON:       int   = 3        # Projection years (3-year credible window)
MARKET_KTC_WEIGHT:       float = 0.50     # KTC share of market composite
MARKET_FC_WEIGHT:        float = 0.50     # FantasyCalc share of market composite
BUY_SPREAD_THRESHOLD_PCT:  float =  8.0   # spread_pct >= this → buy signal
SELL_SPREAD_THRESHOLD_PCT: float = -8.0   # spread_pct <= this → sell signal
N_SIMULATIONS:           int   = 150      # MC sims per player for uncertainty bands

# Intrinsic anchor: peak-career dynasty worth on a 10 000-point scale.
# Calibrated so an elite player at their peak age maps near the Elite tier (≥ 9 000).
POSITION_PEAK_INTRINSIC: dict[str, float] = {
    "QB": 9_200.0,
    "RB": 8_400.0,
    "WR": 9_500.0,
    "TE": 8_800.0,
}

# Base P(active at year t) for a peak-age player.
# Drawn from historical NFL career-length distributions by position.
_SURVIVAL_BASE: dict[str, dict[int, float]] = {
    "QB": {1: 0.94, 2: 0.88, 3: 0.81},
    "RB": {1: 0.88, 2: 0.76, 3: 0.63},
    "WR": {1: 0.91, 2: 0.82, 3: 0.71},
    "TE": {1: 0.92, 2: 0.83, 3: 0.72},
}

# Max scarcity premium above replacement level, by position.
# Linear gradient: rank 1 → +premium, replacement rank → +0 %.
_SCARCITY_PREMIUMS: dict[str, float] = {
    "QB": 0.10,
    "RB": 0.06,
    "WR": 0.04,
    "TE": 0.12,
}

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class MarketResult:
    """Output of the market composite layer."""
    market_price:   float          # Blended KTC + FC (normalised to ~10 000 scale)
    ktc_normalized: float | None
    fc_normalized:  float | None
    sentiment_gap:  float          # (KTC_norm − FC_norm) / max; informational only
    data_sources:   str            # "both" | "ktc_only" | "fc_only" | "none"


@dataclass
class IntrinsicResult:
    """Output of the intrinsic model before portfolio calibration."""
    raw_pv:                   float              # Uncalibrated PV sum
    year_contributions:       dict[int, float]   # Deterministic contribution per year
    p10:                      float              # 10th-percentile simulation outcome
    p50:                      float              # Median (used as point estimate)
    p90:                      float              # 90th-percentile simulation outcome
    bust_probability:         float              # P(outcome < 15th percentile)
    elite_outcome_probability: float             # P(outcome > 80th percentile)


@dataclass
class ValuationResult:
    """Combined output: market price, intrinsic value, spread, uncertainty."""
    market_price:     float   # Market composite (KTC + FC)
    intrinsic_value:  float   # Portfolio-calibrated PV model estimate
    spread:           float   # intrinsic − market  (+ = undervalued, − = overvalued)
    spread_pct:       float   # spread / market × 100
    confidence_low:   float   # p10 of intrinsic (calibrated)
    confidence_high:  float   # p90 of intrinsic (calibrated)
    uncertainty_label: str    # "low" | "moderate" | "high"
    bust_prob:        float
    elite_prob:       float
    sentiment_gap:    float   # KTC vs FC disagreement (informational)
    buy_signal:       bool
    sell_signal:      bool
    scarcity_mult:    float
    data_sources:     str


# ---------------------------------------------------------------------------
# Survival probability
# ---------------------------------------------------------------------------


def survival_probability(
    position:   str,
    age:        float,
    peak_age:   int,
    years_ahead: int,
) -> float:
    """P(player still on a dynasty-relevant roster at year t).

    Adjusts the position's base survival rate for age relative to peak:
    - Past-prime players face accelerating attrition.
    - Very young players carry extra developmental/roster risk.
    """
    base = _SURVIVAL_BASE.get(position, {}).get(years_ahead, 0.65)
    if age > peak_age + 2:
        penalty = 0.04 * (age - peak_age - 2)
        base = max(0.15, base * (1.0 - penalty))
    elif age < peak_age - 5:
        base = max(0.40, base - 0.08)
    return base


# ---------------------------------------------------------------------------
# Role persistence
# ---------------------------------------------------------------------------


def role_persistence(position_rank_pct: float, years_ahead: int) -> float:
    """P(still a starting-caliber asset at year t | active).

    Args:
        position_rank_pct: 0.0 = best player at position, 1.0 = worst.
        years_ahead:       Forward horizon in years.
    """
    # Top-ranked player ≈ 0.85 base; bottom-ranked ≈ 0.15 base
    base = max(0.15, 1.0 - position_rank_pct * 0.85)
    # Starting roles erode roughly 8 % per year
    decay = 0.92 ** years_ahead
    return max(0.08, base * decay)


# ---------------------------------------------------------------------------
# Market composite
# ---------------------------------------------------------------------------


class MarketComposite:
    """Combines KTC (sentiment) and FantasyCalc (executed) into a market price.

    Deliberately neutral: no disagreement bonuses or penalties.
    The KTC-vs-FC gap is surfaced as ``sentiment_gap`` for information only.
    """

    def __init__(
        self,
        ktc_weight: float = MARKET_KTC_WEIGHT,
        fc_weight:  float = MARKET_FC_WEIGHT,
    ) -> None:
        self.ktc_w = ktc_weight
        self.fc_w  = fc_weight

    def compute(
        self,
        ktc_normalized: float | None,
        fc_normalized:  float | None,
    ) -> MarketResult:
        if ktc_normalized is not None and fc_normalized is not None:
            market_price  = self.ktc_w * ktc_normalized + self.fc_w * fc_normalized
            max_val       = max(ktc_normalized, fc_normalized, 1.0)
            sentiment_gap = (ktc_normalized - fc_normalized) / max_val
            sources = "both"
        elif ktc_normalized is not None:
            market_price, sentiment_gap, sources = ktc_normalized, 0.0, "ktc_only"
        elif fc_normalized is not None:
            market_price, sentiment_gap, sources = fc_normalized, 0.0, "fc_only"
        else:
            return MarketResult(0.0, None, None, 0.0, "none")

        return MarketResult(
            market_price   = market_price,
            ktc_normalized = ktc_normalized,
            fc_normalized  = fc_normalized,
            sentiment_gap  = round(sentiment_gap, 4),
            data_sources   = sources,
        )


# ---------------------------------------------------------------------------
# Intrinsic model
# ---------------------------------------------------------------------------


class IntrinsicModel:
    """3-year present-value model for dynasty intrinsic worth.

    Formula (per year t):
        PV_t = age_mult(age + t) × PEAK_VALUE × survival(pos, age, t) × role(rank_pct, t)
               ─────────────────────────────────────────────────────────────────────────────
                                      (1 + discount_rate) ^ t

    intrinsic_raw = Σ PV_t   (t = 1 … horizon)

    Raw values are uncalibrated (arbitrary scale).  Portfolio-level calibration
    happens in ``build_valuation_results`` so the final intrinsic_value lives on
    the same ~10 000-point scale as market prices.
    """

    def __init__(
        self,
        age_mult_fn,                        # Callable: (position, age, method) → float
        horizon:  int   = INTRINSIC_HORIZON,
        discount: float = INTRINSIC_DISCOUNT_RATE,
    ) -> None:
        self._age_mult = age_mult_fn
        self.horizon   = horizon
        self.discount  = discount

    def compute(
        self,
        position:          str,
        age:               float,
        peak_age:          int,
        position_rank_pct: float,
        n_sims:            int = N_SIMULATIONS,
    ) -> IntrinsicResult:
        peak_val = POSITION_PEAK_INTRINSIC.get(position, 9_000.0)

        # --- Deterministic contributions per year (for explainability) ---
        year_contribs: dict[int, float] = {}
        det_pv = 0.0
        for t in range(1, self.horizon + 1):
            future_am = self._age_mult(position, age + t)
            v_t = future_am * peak_val
            s_t = survival_probability(position, age, peak_age, t)
            r_t = role_persistence(position_rank_pct, t)
            disc = (1.0 + self.discount) ** t
            contrib = v_t * s_t * r_t / disc
            year_contribs[t] = round(contrib, 1)
            det_pv += contrib

        # --- Monte Carlo simulation for uncertainty bands (vectorised) ---
        sim_pvs = np.zeros(n_sims)
        for t in range(1, self.horizon + 1):
            future_am = self._age_mult(position, age + t)
            s_t = survival_probability(position, age, peak_age, t)
            r_t = role_persistence(position_rank_pct, t)
            disc = (1.0 + self.discount) ** t
            # Noise grows with projection horizon
            am_noise   = np.random.normal(0.0, 0.04 * math.sqrt(t), n_sims)
            surv_noise = np.random.normal(0.0, 0.03, n_sims)
            eff_am   = np.maximum(0.01, future_am + am_noise)
            eff_surv = np.clip(s_t + surv_noise, 0.0, 1.0)
            sim_pvs += eff_am * peak_val * eff_surv * r_t / disc

        p10 = float(np.percentile(sim_pvs, 10))
        p50 = float(np.percentile(sim_pvs, 50))
        p90 = float(np.percentile(sim_pvs, 90))
        p15 = float(np.percentile(sim_pvs, 15))
        p80 = float(np.percentile(sim_pvs, 80))

        return IntrinsicResult(
            raw_pv                    = det_pv,
            year_contributions        = year_contribs,
            p10                       = p10,
            p50                       = p50,
            p90                       = p90,
            bust_probability          = round(float(np.mean(sim_pvs < p15)), 3),
            elite_outcome_probability = round(float(np.mean(sim_pvs > p80)), 3),
        )


# ---------------------------------------------------------------------------
# League settings & scarcity model
# ---------------------------------------------------------------------------


@dataclass
class LeagueSettings:
    """Dynasty league configuration for replacement-level calculations.

    These values drive the ScarcityModel; if unavailable they fall back
    to 12-team half-PPR 1QB defaults so the model degrades gracefully.
    """
    num_teams:  int   = 12
    qb_slots:   int   = 1
    rb_slots:   int   = 2
    wr_slots:   int   = 2
    te_slots:   int   = 1
    flex_slots: int   = 2
    superflex:  bool  = False
    te_premium: float = 0.0

    @property
    def replacement_rank(self) -> dict[str, int]:
        """First player rank outside typical starting slots = replacement level."""
        t = self.num_teams
        return {
            "QB": (self.qb_slots + (1 if self.superflex else 0)) * t + 1,
            "RB": (self.rb_slots + max(1, self.flex_slots // 2)) * t + 1,
            "WR": (self.wr_slots + self.flex_slots) * t + 1,
            "TE": self.te_slots * t + 1,
        }

    @classmethod
    def from_meta(cls, meta: dict) -> "LeagueSettings":
        """Construct from Sleeper league metadata dict."""
        slots = meta.get("starter_slots", {})
        return cls(
            num_teams  = int(meta.get("num_teams", 12)),
            qb_slots   = int(slots.get("QB", 1)),
            rb_slots   = int(slots.get("RB", 2)),
            wr_slots   = int(slots.get("WR", 2)),
            te_slots   = int(slots.get("TE", 1)),
            flex_slots = int(slots.get("FLEX", 0) + slots.get("SUPER_FLEX", 0)),
            superflex  = bool(meta.get("is_superflex", False)),
            te_premium = float(meta.get("te_premium", 0.0)),
        )


class ScarcityModel:
    """Replacement-level scarcity premium.

    Replaces static tier boosts (e.g. 'top-5 QB +8 %') with a continuous,
    league-configurable gradient.  Players below replacement level get no
    premium.  Players above it get a premium that scales linearly from 0 %
    at the replacement boundary to ``_SCARCITY_PREMIUMS[pos]`` at rank 1.
    """

    def __init__(self, settings: LeagueSettings) -> None:
        self.settings = settings

    def multiplier(self, position: str, rank: int) -> float:
        """Scarcity premium multiplier.  rank=1 is best, rank=N is worst."""
        rep     = self.settings.replacement_rank.get(position, 30)
        premium = _SCARCITY_PREMIUMS.get(position, 0.05)
        if rank >= rep:
            return 1.0
        t = 1.0 - (rank - 1) / max(rep - 1, 1)   # 1.0 at rank=1, 0.0 at rank=rep
        return round(1.0 + premium * t, 4)


# ---------------------------------------------------------------------------
# Portfolio-level orchestration
# ---------------------------------------------------------------------------


def build_valuation_results(
    players:        list[dict],
    age_mult_fn,
    league_settings: LeagueSettings,
    n_sims:         int = N_SIMULATIONS,
) -> dict[str, ValuationResult]:
    """Compute ValuationResult for every player with portfolio-level calibration.

    Calibration approach
    --------------------
    IntrinsicModel outputs ``raw_pv`` on an arbitrary scale (large PV sums).
    We normalise these to the market composite scale by matching the 85th
    percentile of raw_pv to the 85th percentile of market_price across the
    full portfolio.  This ensures spreads are meaningful on a ~10 000-point axis
    without anchoring the model to market pricing at the individual level.

    Args:
        players: List of dicts, each requiring:
            id, position, age (optional), peak_age, position_rank_pct,
            position_rank, ktc_normalized (optional), fc_normalized (optional).
        age_mult_fn:     Callable(position, age) → float  (existing age_multiplier).
        league_settings: LeagueSettings for scarcity.
        n_sims:          MC simulations per player.

    Returns:
        Dict mapping player_id → ValuationResult.
    """
    market_model   = MarketComposite()
    intrinsic_model = IntrinsicModel(age_mult_fn)
    scarcity_model  = ScarcityModel(league_settings)

    # Pass 1 — raw computation
    raw: dict[str, tuple[MarketResult, IntrinsicResult, float]] = {}
    raw_pvs:       list[float] = []
    market_prices: list[float] = []

    for p in players:
        pid  = p["id"]
        pos  = p["position"]
        age  = p.get("age") or float(p.get("peak_age", 26))
        peak = int(p.get("peak_age", 26))
        rank_pct  = float(p.get("position_rank_pct", 0.5))
        rank      = int(p.get("position_rank", 99))

        mkt = market_model.compute(p.get("ktc_normalized"), p.get("fc_normalized"))
        if mkt.data_sources == "none":
            continue

        intr = intrinsic_model.compute(pos, age, peak, rank_pct, n_sims)
        sc   = scarcity_model.multiplier(pos, rank)

        raw[pid] = (mkt, intr, sc)
        raw_pvs.append(intr.p50)
        market_prices.append(mkt.market_price)

    if not raw_pvs:
        return {}

    # Calibration: align p85 of raw_pv to p85 of market_price
    p85_raw    = float(np.percentile(raw_pvs, 85))
    p85_market = float(np.percentile(market_prices, 85))
    scale      = p85_market / max(p85_raw, 1.0)

    # Pass 2 — scale, apply scarcity, compute spreads
    results: dict[str, ValuationResult] = {}
    for pid, (mkt, intr, sc) in raw.items():
        iv   = intr.p50 * scale * sc
        ci_l = intr.p10 * scale * sc
        ci_h = intr.p90 * scale * sc

        spread     = iv - mkt.market_price
        spread_pct = (spread / max(mkt.market_price, 1.0)) * 100.0

        band_width = (ci_h - ci_l) / max(iv, 1.0)
        if band_width > 0.8:
            uncertainty = "high"
        elif band_width > 0.4:
            uncertainty = "moderate"
        else:
            uncertainty = "low"

        results[pid] = ValuationResult(
            market_price    = round(mkt.market_price, 1),
            intrinsic_value = round(iv, 1),
            spread          = round(spread, 1),
            spread_pct      = round(spread_pct, 2),
            confidence_low  = round(ci_l, 1),
            confidence_high = round(ci_h, 1),
            uncertainty_label = uncertainty,
            bust_prob       = intr.bust_probability,
            elite_prob      = intr.elite_outcome_probability,
            sentiment_gap   = mkt.sentiment_gap,
            buy_signal      = spread_pct >= BUY_SPREAD_THRESHOLD_PCT,
            sell_signal     = spread_pct <= SELL_SPREAD_THRESHOLD_PCT,
            scarcity_mult   = sc,
            data_sources    = mkt.data_sources,
        )

    return results
