#!/usr/bin/env python3
"""
Dynasty Fantasy Football Trade Analyzer
========================================
Pulls Sleeper rosters, FantasyCalc + KTC values, builds an age-adjusted
consensus value model, and surfaces trade recommendations where you win
the value exchange.

Usage:
    python fantasy_trade_analyzer.py
    python fantasy_trade_analyzer.py --username YOUR_NAME --season 2025
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime
from difflib import SequenceMatcher
from itertools import combinations
from pathlib import Path

import requests

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

CONFIG = {
    "sleeper_username":    "YOUR_SLEEPER_USERNAME",  # ← override via CLI or prompt
    "season":              "2025",
    "cache_players":       True,      # cache the large Sleeper players call
    "cache_ttl_hours":     24,        # hours before cache expires
    "min_trade_value_gain": 250,      # minimum net gain to surface a trade rec
    "max_players_to_send":  3,        # max players on either side of a trade
    "top_n_trades":         25,       # number of top trade recs to display
}

CACHE_DIR = Path(".fantasy_cache")
CACHE_DIR.mkdir(exist_ok=True)

# Positional age curves  (peak_age, pre-peak slope, post-peak decay rate)
AGE_CURVES = {
    "QB":  {"peak": 28, "pre": 0.030, "post": 0.080},
    "RB":  {"peak": 24, "pre": 0.040, "post": 0.130},
    "WR":  {"peak": 26, "pre": 0.035, "post": 0.090},
    "TE":  {"peak": 27, "pre": 0.030, "post": 0.085},
}

# Fallback pick values if FantasyCalc doesn't return picks  (1QB scale)
FALLBACK_PICK_VALUES_1QB = {
    "Early 1st (2025)": 7200, "Mid 1st (2025)": 5400, "Late 1st (2025)": 3800,
    "Early 1st (2026)": 6200, "Mid 1st (2026)": 4600, "Late 1st (2026)": 3200,
    "Early 1st (2027)": 5000, "Mid 1st (2027)": 3800, "Late 1st (2027)": 2600,
    "Early 2nd (2025)": 2400, "Mid 2nd (2025)": 1900, "Late 2nd (2025)": 1400,
    "Early 2nd (2026)": 2200, "Mid 2nd (2026)": 1700, "Late 2nd (2026)": 1200,
    "Early 3rd (2025)": 900,  "Mid 3rd (2025)": 700,  "Late 3rd (2025)": 500,
}

# ANSI colours
BOLD   = "\033[1m"
GREEN  = "\033[92m"
CYAN   = "\033[96m"
YELLOW = "\033[93m"
RED    = "\033[91m"
DIM    = "\033[2m"
RESET  = "\033[0m"


# ─────────────────────────────────────────────────────────────────────────────
# CACHE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _cache_get(key: str):
    path = CACHE_DIR / f"{key}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        age_h = (time.time() - data["ts"]) / 3600
        if age_h > CONFIG["cache_ttl_hours"]:
            return None
        return data["value"]
    except Exception:
        return None


def _cache_set(key: str, value):
    path = CACHE_DIR / f"{key}.json"
    path.write_text(json.dumps({"ts": time.time(), "value": value}))


# ─────────────────────────────────────────────────────────────────────────────
# HTTP HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _get(url: str, headers=None, retries=3, timeout=20):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            r.raise_for_status()
            return r
        except requests.RequestException as exc:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1A — SLEEPER API
# ─────────────────────────────────────────────────────────────────────────────

SLEEPER_BASE = "https://api.sleeper.app/v1"


def _sleeper(path: str):
    return _get(f"{SLEEPER_BASE}{path}").json()


def fetch_sleeper_data(username: str, season: str) -> dict:
    print(f"\n{BOLD}[Sleeper]{RESET} Fetching data for user: {CYAN}{username}{RESET}")

    user = _sleeper(f"/user/{username}")
    if not user or "user_id" not in user:
        raise ValueError(f"Sleeper user '{username}' not found.")
    user_id = user["user_id"]
    print(f"  User ID: {user_id}")

    leagues = _sleeper(f"/user/{user_id}/leagues/nfl/{season}")
    if not leagues:
        raise ValueError(f"No NFL leagues found for {username} in {season}.")

    dynasty_leagues = [l for l in leagues if l.get("settings", {}).get("type") == 2]
    if not dynasty_leagues:
        raise ValueError("No dynasty leagues found (type == 2). Check the season.")

    # League selection
    if len(dynasty_leagues) > 1:
        print(f"\n  Found {len(dynasty_leagues)} dynasty leagues:")
        for i, lg in enumerate(dynasty_leagues):
            print(f"    [{i}] {lg.get('name', 'Unnamed')}  (ID: {lg['league_id']})")
        try:
            idx = int(input("  Select league [default 0]: ").strip() or "0")
        except (ValueError, EOFError):
            idx = 0
        league = dynasty_leagues[min(idx, len(dynasty_leagues) - 1)]
    else:
        league = dynasty_leagues[0]

    league_id    = league["league_id"]
    settings     = league.get("settings", {})
    scoring      = league.get("scoring_settings", {})
    positions    = league.get("roster_positions", [])

    is_superflex = positions.count("SUPER_FLEX") > 0
    ppr          = float(scoring.get("rec", 0))
    num_teams    = int(settings.get("num_teams", 12))
    te_premium   = float(scoring.get("bonus_rec_te", 0))

    print(f"\n  {BOLD}{league.get('name', 'Unknown League')}{RESET}")
    print(f"  {num_teams} teams | {'Superflex' if is_superflex else '1QB'} | "
          f"PPR={ppr} | TE-prem={te_premium}")

    rosters      = _sleeper(f"/league/{league_id}/rosters")
    users        = _sleeper(f"/league/{league_id}/users")
    traded_picks = _sleeper(f"/league/{league_id}/traded_picks") or []

    user_map = {u["user_id"]: u.get("display_name", "Unknown") for u in (users or [])}
    roster_owner_map = {
        r["roster_id"]: user_map.get(r.get("owner_id"), f"Owner_{r.get('owner_id')}")
        for r in rosters
    }

    my_roster = next((r for r in rosters if r.get("owner_id") == user_id), None)
    if not my_roster:
        raise ValueError("Could not locate your roster in this league.")

    my_picks = [p for p in traded_picks
                if str(p.get("owner_id")) == str(my_roster["roster_id"])]

    # Fetch (or load cached) full NFL player database
    print("  Loading NFL player database …", end="", flush=True)
    all_players = _cache_get("sleeper_players_nfl")
    if all_players is None:
        all_players = _sleeper("/players/nfl")
        if CONFIG["cache_players"]:
            _cache_set("sleeper_players_nfl", all_players)
    print(f" {len(all_players):,} players loaded.")

    return {
        "user_id":           user_id,
        "league_id":         league_id,
        "league_name":       league.get("name", "Unknown"),
        "is_superflex":      is_superflex,
        "ppr":               ppr,
        "num_teams":         num_teams,
        "te_premium":        te_premium,
        "rosters":           rosters,
        "my_roster":         my_roster,
        "my_picks":          my_picks,
        "traded_picks":      traded_picks,
        "user_map":          user_map,
        "roster_owner_map":  roster_owner_map,
        "all_players":       all_players,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1B — FANTASYCALC API
# ─────────────────────────────────────────────────────────────────────────────

def fetch_fantasycalc_values(is_superflex: bool, ppr: float, num_teams: int) -> list:
    print(f"\n{BOLD}[FantasyCalc]{RESET} Fetching dynasty values …", end="", flush=True)
    num_qbs = 2 if is_superflex else 1
    url = (
        "https://api.fantasycalc.com/values/current"
        f"?isDynasty=true&numQbs={num_qbs}&numTeams={num_teams}&ppr={ppr}"
    )
    try:
        data = _get(url).json()
        print(f" {len(data)} records.")
        return data
    except Exception as e:
        print(f"\n  {YELLOW}[WARNING]{RESET} FantasyCalc unavailable: {e}")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1C — KTC (unofficial; graceful fallback)
# ─────────────────────────────────────────────────────────────────────────────

_KTC_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
    "Referer": "https://keeptradecut.com/",
}


def fetch_ktc_values(is_superflex: bool) -> dict:
    """
    Attempt to retrieve KTC dynasty player values.
    KTC's Terms of Service restrict automated access; use for personal research only.
    Falls back gracefully so the tool works even if KTC is unreachable.

    Returns: {player_name: value} or {} on failure.
    """
    print(f"\n{BOLD}[KTC]{RESET} Attempting dynasty values …", end="", flush=True)
    sf = "true" if is_superflex else "false"

    # Known unofficial JSON endpoints (vary by KTC site version)
    endpoints = [
        f"https://keeptradecut.com/dynasty-rankings/json?superFlex={sf}",
        f"https://keeptradecut.com/dynasty-rankings?format=json&superFlex={sf}",
    ]

    for url in endpoints:
        try:
            r = requests.get(url, headers=_KTC_HEADERS, timeout=15)
            if r.status_code == 200:
                ct = r.headers.get("content-type", "")
                if "json" in ct:
                    parsed = _parse_ktc_json(r.json())
                    if parsed:
                        print(f" {len(parsed)} records (JSON endpoint).")
                        return parsed
                # HTML — try to extract embedded JS array
                match = re.search(
                    r'(?:var\s+(?:playerData|rankings|dynastyPlayers)\s*=\s*)(\[.*?\]);',
                    r.text, re.DOTALL
                )
                if match:
                    parsed = _parse_ktc_json(json.loads(match.group(1)))
                    if parsed:
                        print(f" {len(parsed)} records (embedded JS).")
                        return parsed
        except Exception:
            continue

    print(f"\n  {YELLOW}[WARNING]{RESET} KTC unavailable — using FantasyCalc only.")
    return {}


def _parse_ktc_json(data: list) -> dict:
    result = {}
    for item in data:
        try:
            name = (
                item.get("playerName")
                or item.get("name")
                or (item.get("player") or {}).get("name")
                or ""
            )
            value = (
                item.get("value")
                or item.get("superFlexValue")
                or item.get("oneQBValue")
                or item.get("dynastyValue")
                or 0
            )
            if name and value:
                result[name.strip()] = int(value)
        except Exception:
            continue
    return result


# ─────────────────────────────────────────────────────────────────────────────
# NAME NORMALISATION + FUZZY MATCHING
# ─────────────────────────────────────────────────────────────────────────────

def _norm(name: str) -> str:
    if not name:
        return ""
    s = name.lower().strip()
    s = re.sub(r"\s+(jr\.?|sr\.?|ii+|iii|iv|v)$", "", s)
    s = re.sub(r"[''`ʼ]", "", s)
    s = re.sub(r"[^a-z\s\-]", "", s)
    return s.strip()


def _best_match(target: str, candidates: list, threshold=0.82) -> str | None:
    t = _norm(target)
    best_score, best_key = 0.0, None
    for c in candidates:
        score = SequenceMatcher(None, t, _norm(c)).ratio()
        if score > best_score:
            best_score, best_key = score, c
    return best_key if best_score >= threshold else None


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — AGE-CURVE MODEL
# ─────────────────────────────────────────────────────────────────────────────

def age_multiplier(position: str, age) -> float:
    """
    Dynasty age-curve multiplier.
    Young players below their positional peak get a slight premium;
    veterans past peak are discounted using exponential decay.
    """
    try:
        age = float(age)
    except (TypeError, ValueError):
        return 1.0

    curve = AGE_CURVES.get(position.upper(), AGE_CURVES["WR"])
    peak  = curve["peak"]

    if age <= peak:
        years_out = peak - age
        # Slight premium close to peak, small discount for rookies far out
        mult = 1.05 - curve["pre"] * max(0, years_out - 1)
    else:
        years_past = age - peak
        mult = 1.0 * ((1 - curve["post"]) ** years_past)

    return round(max(0.05, min(1.25, mult)), 4)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — BUILD CONSENSUS VALUE MODEL
# ─────────────────────────────────────────────────────────────────────────────

def _value_tier(v: float) -> str:
    if v >= 7000: return "Elite"
    if v >= 5000: return "Star"
    if v >= 3500: return "Starter"
    if v >= 2000: return "Flex"
    if v >= 1000: return "Depth"
    return "Stash"


def build_player_values(
    fc_data: list,
    ktc_data: dict,
    all_players: dict,
    is_superflex: bool,
    ppr: float,
    te_premium: float,
) -> dict:
    """
    Merge FantasyCalc + KTC into a single age-adjusted consensus value dict
    keyed by Sleeper player ID.
    """
    print(f"\n{BOLD}[Model]{RESET} Building consensus value model …", end="", flush=True)

    # ── FantasyCalc lookups ──
    fc_by_sleeper: dict = {}
    fc_by_name:    dict = {}
    for item in fc_data:
        p   = item.get("player", {})
        sid = p.get("sleeperId")
        nm  = p.get("name", "")
        if sid:
            fc_by_sleeper[str(sid)] = item
        if nm:
            fc_by_name[nm] = item

    ktc_names = list(ktc_data.keys())

    players_db: dict = {}
    skipped = 0

    for pid, pdata in all_players.items():
        pos = pdata.get("position", "")
        if pos not in ("QB", "RB", "WR", "TE"):
            continue
        if pdata.get("status") in ("Retired",):
            skipped += 1
            continue

        name = pdata.get("full_name") or pdata.get("search_full_name") or ""
        if not name:
            continue

        age      = pdata.get("age") or 0
        team     = pdata.get("team") or "FA"
        yrs_exp  = pdata.get("years_exp", 0)

        # ── FantasyCalc value ──
        fc_rec = fc_by_sleeper.get(str(pid))
        if fc_rec is None and name:
            matched = _best_match(name, list(fc_by_name.keys()))
            if matched:
                fc_rec = fc_by_name[matched]

        fc_val   = fc_rec.get("value", 0)   if fc_rec else 0
        fc_trend = fc_rec.get("trend30Day", 0) if fc_rec else 0

        # ── KTC value ──
        ktc_val = 0
        if ktc_names and name:
            km = _best_match(name, ktc_names)
            if km:
                ktc_val = ktc_data.get(km, 0)

        if fc_val == 0 and ktc_val == 0:
            continue

        # ── Consensus: FC primary (65%), KTC secondary (35%) ──
        if fc_val > 0 and ktc_val > 0:
            # Normalise KTC to FC scale (both ~0–10 000)
            consensus = 0.65 * fc_val + 0.35 * ktc_val
        elif fc_val > 0:
            consensus = float(fc_val)
        else:
            consensus = float(ktc_val)

        # ── Age-curve adjustment ──
        a_mult = age_multiplier(pos, age)
        adj    = consensus * a_mult

        # ── Positional scarcity bonuses ──
        if pos == "TE":
            adj *= (1.06 + 0.02 * min(te_premium, 2.0))   # TE premium leagues
        if pos == "QB" and is_superflex:
            adj *= 1.12

        players_db[str(pid)] = {
            "id":            str(pid),
            "name":          name,
            "position":      pos,
            "team":          team,
            "age":           age or "?",
            "years_exp":     yrs_exp,
            "fc_value":      round(fc_val),
            "ktc_value":     round(ktc_val),
            "consensus_raw": round(consensus),
            "age_mult":      a_mult,
            "adjusted_value": round(adj),
            "trend_30d":     round(fc_trend),
            "tier":          _value_tier(adj),
        }

    print(f" {len(players_db):,} players valued ({skipped} skipped).")
    return players_db


def build_pick_values(fc_data: list, is_superflex: bool) -> dict:
    """Extract draft-pick values from FantasyCalc; fall back to table if absent."""
    pick_db: dict = {}

    for item in fc_data:
        p    = item.get("player", {})
        name = p.get("name", "")
        pos  = p.get("position", "")
        if pos == "PICK" or re.search(r"\b(pick|round|1st|2nd|3rd)\b", name, re.I):
            val = item.get("value", 0)
            pick_db[name] = {
                "id":             f"pick_{name}",
                "name":           name,
                "position":       "PICK",
                "team":           "PICK",
                "age":            "N/A",
                "adjusted_value": val,
                "fc_value":       val,
                "ktc_value":      0,
                "trend_30d":      item.get("trend30Day", 0),
                "tier":           _value_tier(val),
            }

    # Fall back to hardcoded table (scaled for superflex)
    if not pick_db:
        sf_mult = 1.18 if is_superflex else 1.0
        for name, base_val in FALLBACK_PICK_VALUES_1QB.items():
            val = round(base_val * sf_mult)
            pick_db[name] = {
                "id":             f"pick_{name}",
                "name":           name,
                "position":       "PICK",
                "team":           "PICK",
                "age":            "N/A",
                "adjusted_value": val,
                "fc_value":       val,
                "ktc_value":      0,
                "trend_30d":      0,
                "tier":           _value_tier(val),
            }

    return pick_db


# ─────────────────────────────────────────────────────────────────────────────
# ROSTER BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_roster(
    roster_record: dict,
    player_values: dict,
    roster_owner_map: dict,
    all_players: dict,
) -> dict:
    roster_id  = roster_record["roster_id"]
    owner_name = roster_owner_map.get(roster_id, f"Roster_{roster_id}")
    pids       = roster_record.get("players") or []

    players = []
    for pid in pids:
        if pid in player_values:
            players.append(player_values[pid])
        elif pid in all_players:
            pdata = all_players[pid]
            players.append({
                "id":             pid,
                "name":           pdata.get("full_name", pid),
                "position":       pdata.get("position", "?"),
                "team":           pdata.get("team") or "FA",
                "age":            pdata.get("age", "?"),
                "adjusted_value": 0,
                "fc_value":       0,
                "ktc_value":      0,
                "trend_30d":      0,
                "tier":           "Unranked",
            })

    players.sort(key=lambda p: p.get("adjusted_value", 0), reverse=True)
    total = sum(p.get("adjusted_value", 0) for p in players)

    pos_totals: dict = {}
    for p in players:
        pos = p.get("position", "?")
        pos_totals[pos] = pos_totals.get(pos, 0) + p.get("adjusted_value", 0)

    wins   = roster_record.get("settings", {}).get("wins", 0)
    losses = roster_record.get("settings", {}).get("losses", 0)

    return {
        "roster_id":   roster_id,
        "owner_name":  owner_name,
        "players":     players,
        "total_value": total,
        "pos_totals":  pos_totals,
        "record":      {"wins": wins, "losses": losses},
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — TRADE RECOMMENDATION ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def analyze_trades(
    my_roster:   dict,
    all_rosters: list,
    min_gain:    int = 250,
    max_send:    int = 3,
) -> list:
    """
    Enumerate 1v1, 2v1, 1v2, 2v2, 3v2, 2v3, 3v3 combinations and surface trades
    where I net positive value (>= min_gain) and the opponent receives at least
    75% of what they give up (making the deal plausibly acceptable).
    """
    print(f"\n{BOLD}[Trade Engine]{RESET} Scanning trade space …", end="", flush=True)

    # Only tradeable assets (exclude 0-value stashes for performance)
    my_assets  = [p for p in my_roster["players"]  if p.get("adjusted_value", 0) >= 300]
    recs: list = []

    for opp in all_rosters:
        if opp["roster_id"] == my_roster["roster_id"]:
            continue
        opp_assets = [p for p in opp["players"] if p.get("adjusted_value", 0) >= 300]

        for send_n in range(1, max_send + 1):
            for recv_n in range(1, max_send + 1):
                if send_n + recv_n < 2 or send_n + recv_n > 5:
                    continue

                # Limit search space — top assets only for larger combos
                my_pool  = my_assets[:  (8 if send_n == 1 else 7 if send_n == 2 else 6)]
                opp_pool = opp_assets[: (8 if recv_n == 1 else 7 if recv_n == 2 else 6)]

                for my_side in combinations(my_pool, send_n):
                    my_val = sum(p["adjusted_value"] for p in my_side)

                    for opp_side in combinations(opp_pool, recv_n):
                        opp_val = sum(p["adjusted_value"] for p in opp_side)
                        my_gain = opp_val - my_val

                        if my_gain < min_gain:
                            continue

                        ratio = opp_val / my_val if my_val > 0 else 0
                        # Plausibility filter — don't surface outright robberies
                        if ratio < 0.75:
                            continue

                        recs.append({
                            "opponent":      opp["owner_name"],
                            "send":          list(my_side),
                            "receive":       list(opp_side),
                            "send_value":    round(my_val),
                            "receive_value": round(opp_val),
                            "my_gain":       round(my_gain),
                            "ratio":         round(ratio, 3),
                            "trade_size":    f"{send_n}v{recv_n}",
                        })

    recs.sort(key=lambda x: x["my_gain"], reverse=True)
    print(f" {len(recs):,} scenarios found.")
    return recs


# ─────────────────────────────────────────────────────────────────────────────
# DISPLAY HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _vc(val: float) -> str:
    """Return ANSI colour for a given value."""
    if val >= 7000: return f"{BOLD}{GREEN}"
    if val >= 5000: return GREEN
    if val >= 3500: return CYAN
    if val >= 2000: return YELLOW
    return DIM


def print_roster(roster: dict, label: str = "MY ROSTER") -> None:
    sep = "═" * 64
    print(f"\n{sep}")
    print(f"{BOLD}{label}: {roster['owner_name']}{RESET}  "
          f"W-L: {roster['record']['wins']}-{roster['record']['losses']}  "
          f"Total: {BOLD}{roster['total_value']:,}{RESET}")
    print(f"{'─' * 64}")

    for pos in ("QB", "RB", "WR", "TE"):
        pos_players = [p for p in roster["players"] if p.get("position") == pos]
        if not pos_players:
            continue
        print(f"\n  {BOLD}{pos}{RESET}")
        for p in pos_players[:10]:
            v  = p.get("adjusted_value", 0)
            t  = p.get("trend_30d", 0)
            ts = f"{'↑' if t > 0 else '↓' if t < 0 else '─'}{abs(t)}"
            print(f"    {_vc(v)}{p['name']:<26}{RESET} "
                  f"Age {str(p.get('age', '?')):<4}  {v:>6,}  {DIM}{ts}{RESET}")


def print_league_summary(all_rosters: list) -> None:
    print(f"\n{'═' * 64}")
    print(f"{BOLD}LEAGUE VALUE RANKINGS{RESET}")
    print(f"{'─' * 64}")
    ranked = sorted(all_rosters, key=lambda r: r["total_value"], reverse=True)
    for i, r in enumerate(ranked, 1):
        bar = "█" * min(int(r["total_value"] / 3500), 28)
        print(f"  {i:2}. {r['owner_name']:<24} {r['total_value']:>9,}  {CYAN}{bar}{RESET}")


def print_value_movers(player_values: dict, top_n: int = 8) -> None:
    ranked = [
        p for p in player_values.values()
        if isinstance(p.get("trend_30d"), (int, float)) and p["adjusted_value"] >= 1500
    ]
    risers  = sorted(ranked, key=lambda p: p["trend_30d"], reverse=True)[:top_n]
    fallers = sorted(ranked, key=lambda p: p["trend_30d"])[:top_n]

    print(f"\n{'═' * 64}")
    print(f"{BOLD}30-DAY VALUE MOVERS{RESET}")
    print(f"  {GREEN}Risers{RESET}")
    for p in risers:
        if p["trend_30d"] > 0:
            print(f"    {p['name']:<26} {p['position']:<3}  {GREEN}+{p['trend_30d']:,}{RESET}")
    print(f"  {RED}Fallers{RESET}")
    for p in fallers:
        if p["trend_30d"] < 0:
            print(f"    {p['name']:<26} {p['position']:<3}  {RED}{p['trend_30d']:,}{RESET}")


def print_trade_recommendations(recs: list, top_n: int = 25) -> None:
    print(f"\n{'═' * 64}")
    print(f"{BOLD}TOP TRADE RECOMMENDATIONS  (where you win the value exchange){RESET}")
    print(f"{'─' * 64}")

    if not recs:
        print(f"  {YELLOW}No trades meet the minimum gain threshold.{RESET}")
        print("  Try lowering --min-gain or expanding --max-send.")
        return

    for i, rec in enumerate(recs[:top_n], 1):
        print(f"\n  {BOLD}#{i:<3} vs {rec['opponent']}  [{rec['trade_size']}]  "
              f"{GREEN}+{rec['my_gain']:,}{RESET} net gain{RESET}")
        print(f"  {'─' * 58}")

        print(f"  {RED}YOU SEND{RESET}     (value: {rec['send_value']:,})")
        for p in rec["send"]:
            v = p["adjusted_value"]
            print(f"    {_vc(v)}{p['name']:<28}{RESET}  {p['position']:<4}  {v:>6,}")

        print(f"  {GREEN}YOU RECEIVE{RESET}  (value: {rec['receive_value']:,})")
        for p in rec["receive"]:
            v = p["adjusted_value"]
            print(f"    {_vc(v)}{p['name']:<28}{RESET}  {p['position']:<4}  {v:>6,}")

        pct = int(rec["ratio"] * 100)
        bar = "█" * (pct // 5)
        print(f"  Fairness: {bar:<20} {pct}%  →  net {GREEN}+{rec['my_gain']:,}{RESET}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Dynasty Fantasy Football Trade Analyzer")
    p.add_argument("--username",  default=None, help="Sleeper username")
    p.add_argument("--season",    default=CONFIG["season"], help="NFL season (default: 2025)")
    p.add_argument("--min-gain",  type=int, default=CONFIG["min_trade_value_gain"],
                   help="Minimum value gain to show a trade rec (default: 250)")
    p.add_argument("--max-send",  type=int, default=CONFIG["max_players_to_send"],
                   help="Max players on each trade side (default: 3)")
    p.add_argument("--top",       type=int, default=CONFIG["top_n_trades"],
                   help="Number of trade recs to display (default: 25)")
    p.add_argument("--no-cache",  action="store_true", help="Bypass player cache")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if args.no_cache:
        CONFIG["cache_players"] = False

    print(f"\n{'═' * 64}")
    print(f"{BOLD}  DYNASTY FANTASY FOOTBALL TRADE ANALYZER{RESET}")
    print(f"  Powered by Sleeper  ·  FantasyCalc  ·  KTC")
    print(f"{'═' * 64}")

    username = args.username or CONFIG["sleeper_username"]
    if username == "YOUR_SLEEPER_USERNAME":
        try:
            username = input("\nEnter your Sleeper username: ").strip()
        except (EOFError, KeyboardInterrupt):
            username = ""
        if not username:
            print("No username provided. Exiting.")
            sys.exit(1)

    # ── Collect data ──────────────────────────────────────────────────────────
    sleeper = fetch_sleeper_data(username, args.season)

    fc_data  = fetch_fantasycalc_values(
        is_superflex=sleeper["is_superflex"],
        ppr=sleeper["ppr"],
        num_teams=sleeper["num_teams"],
    )
    ktc_data = fetch_ktc_values(is_superflex=sleeper["is_superflex"])

    # ── Build value model ─────────────────────────────────────────────────────
    player_values = build_player_values(
        fc_data,
        ktc_data,
        sleeper["all_players"],
        is_superflex=sleeper["is_superflex"],
        ppr=sleeper["ppr"],
        te_premium=sleeper["te_premium"],
    )
    pick_values = build_pick_values(fc_data, is_superflex=sleeper["is_superflex"])

    # Merge picks into player_values for unified lookup
    player_values.update({f"pick_{k}": v for k, v in pick_values.items()})

    # ── Build all rosters ────────────────────────────────────────────────────
    all_rosters = [
        build_roster(r, player_values, sleeper["roster_owner_map"], sleeper["all_players"])
        for r in sleeper["rosters"]
    ]
    my_roster_obj = next(
        r for r in all_rosters
        if r["roster_id"] == sleeper["my_roster"]["roster_id"]
    )

    # ── Display ───────────────────────────────────────────────────────────────
    print_roster(my_roster_obj)
    print_league_summary(all_rosters)
    print_value_movers(player_values)

    # ── Trade analysis ───────────────────────────────────────────────────────
    recs = analyze_trades(
        my_roster_obj,
        all_rosters,
        min_gain=args.min_gain,
        max_send=args.max_send,
    )
    print_trade_recommendations(recs, top_n=args.top)

    print(f"\n{'═' * 64}")
    print(f"  Analysis complete — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'═' * 64}\n")


if __name__ == "__main__":
    main()
