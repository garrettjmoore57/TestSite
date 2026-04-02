"""
Custom 0–100 dynasty score for FFPredict.

This is a separate, easy-to-read layer from the intrinsic PV / FVS model.
Weights follow: age > usage trend > team context > draft capital, with injury drag.

Plain English: we blend “how good is his career stage”, “is market heat rising or falling”,
“is the NFL situation decent”, “was he premium draft capital”, and “is he hurt”.
"""

from __future__ import annotations

import numpy as np

# Subjective but stable: good QB / play-calling / surrounding talent proxy.
_STRONG_OFFENSE_TEAMS: frozenset[str] = frozenset({
    "PHI", "KC", "BUF", "DET", "BAL", "DAL", "GB", "HOU", "CIN", "ATL",
    "TB", "LAR", "SF", "LAC", "MIA", "DEN",
})
_WEAK_OFFENSE_TEAMS: frozenset[str] = frozenset({
    "NYG", "NE", "TEN", "CLE", "LV", "CAR", "ARI", "NYJ", "NO", "CHI",
})


def _clip(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return float(max(lo, min(hi, x)))


def _age_subscore(position: str, age: float | None) -> float:
    if age is None:
        return 52.0

    if position == "RB":
        if age < 25:
            return _clip(78 + (25 - age) * 3.5)
        if age <= 28:
            return _clip(72 - (age - 25) * 6)
        return _clip(48 - (age - 28) * 10)

    if position == "QB":
        if age < 25:
            return _clip(65 + (25 - age) * 2)
        if age <= 34:
            return _clip(72 - max(0, age - 28) * 2.2)
        return _clip(35 - (age - 34) * 8)

    if position in {"WR", "TE"}:
        cliff = 30
        if age < 25:
            return _clip(74 + (25 - age) * 2.5)
        if age <= cliff:
            return _clip(70 - (age - 25) * 3.5)
        return _clip(42 - (age - cliff) * 9)

    return 55.0


def _usage_trend_subscore(adjusted_value: float, trend_30d: int) -> float:
    base = 52.0
    denom = max(adjusted_value, 1.0)
    momentum_pct = (trend_30d / denom) * 100.0
    return _clip(base + np.tanh(momentum_pct / 8.0) * 38.0)


def _team_subscore(team: str | None) -> float:
    t = (team or "").upper()
    if t in _STRONG_OFFENSE_TEAMS:
        return 72.0
    if t in _WEAK_OFFENSE_TEAMS:
        return 38.0
    if t in {"", "FA"}:
        return 45.0
    return 55.0


def _draft_capital_subscore(years_exp: int, draft_round: int | None) -> float:
    if years_exp >= 4:
        return 54.0
    if draft_round is None:
        return 50.0 if years_exp <= 1 else 54.0
    if draft_round == 1:
        return 86.0
    if draft_round == 2:
        return 72.0
    if draft_round == 3:
        return 62.0
    return 52.0


def _injury_subscore(injury_status: str | None) -> float:
    if not injury_status:
        return 92.0
    key = str(injury_status).upper()
    if key in {"IR", "PUP", "SUSP"}:
        return 22.0
    if key in {"O", "OUT"}:
        return 28.0
    if key in {"D", "DOUBTFUL"}:
        return 40.0
    if key in {"Q", "QUESTIONABLE"}:
        return 58.0
    return 78.0


def compute_custom_dynasty_score(
    position: str,
    age: float | None,
    years_exp: int,
    adjusted_value: float,
    trend_30d: int,
    team: str,
    injury_status: str | None,
    draft_round: int | None,
) -> float:
    """Return a single 0–100 score for dynasty desirability (custom ruleset)."""
    w_age, w_usage, w_team, w_draft, w_inj = 0.40, 0.28, 0.14, 0.10, 0.08
    a = _age_subscore(position, age)
    u = _usage_trend_subscore(adjusted_value, trend_30d)
    tm = _team_subscore(team)
    d = _draft_capital_subscore(years_exp, draft_round)
    inj = _injury_subscore(injury_status)
    raw = w_age * a + w_usage * u + w_team * tm + w_draft * d + w_inj * inj
    return round(_clip(raw), 1)


def roster_action_label(
    buy_signal: bool,
    sell_signal: bool,
    custom_dynasty_score: float,
    trend_30d: int,
) -> str:
    """BUY / HOLD / SELL for UI badges (combines model spread + custom score)."""
    if buy_signal:
        return "BUY"
    if sell_signal:
        return "SELL"
    if custom_dynasty_score >= 68 and trend_30d <= 0:
        return "BUY"
    if custom_dynasty_score <= 40 and trend_30d >= 0:
        return "SELL"
    return "HOLD"


def projection_curve_label(adjusted_value: float, future_value_2yr: float) -> str:
    """Plain-English 2-year trajectory vs today’s market price."""
    if adjusted_value <= 0:
        return "—"
    ch = future_value_2yr / max(adjusted_value, 1.0)
    if ch >= 1.08:
        return "↑ Rising (2yr)"
    if ch <= 0.92:
        return "↓ Fading (2yr)"
    return "→ Flat (2yr)"


def apply_custom_scores_to_player_values(
    player_values: dict,
    all_players: dict[str, dict],
) -> None:
    """Set ``custom_dynasty_score`` on each PlayerValue in-place."""
    for pid, pv in player_values.items():
        meta = all_players.get(pid, {})
        dr = meta.get("draft_round")
        try:
            dr_int = int(dr) if dr is not None else None
        except (TypeError, ValueError):
            dr_int = None
        pv.custom_dynasty_score = compute_custom_dynasty_score(
            pv.position,
            pv.age,
            pv.years_exp,
            pv.adjusted_value,
            pv.trend_30d,
            pv.team,
            pv.injury_status,
            dr_int,
        )
