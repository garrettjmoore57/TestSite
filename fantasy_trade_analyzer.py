#!/usr/bin/env python3
"""Dynasty Future Value Analyzer.

Single-file production script for Sleeper + FantasyCalc + KTC dynasty analysis.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time
import traceback
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

import numpy as np
import requests
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.prompt import Prompt
from rich.table import Table
from rich.traceback import install

install(show_locals=False)
console = Console()

CONFIG: dict[str, Any] = {
    "sleeper_username": "",
    "season": "2025",
    "cache_ttl_hours": 24,
    "cache_players": True,
    "min_trade_value_gain": 250,
    "max_players_to_send": 3,
    "top_n_trades": 25,
    "fc_weight": 0.60,
    "ktc_weight": 0.40,
    "age_curve_method": "gompertz",
    "projection_years": [1, 2, 3, 5],
    "positional_scarcity_enabled": True,
    "need_weight": 0.25,
    "trend_window_days": 30,
    "min_asset_value_for_trade": 300,
    "max_trade_complexity": 3,
    "superflex_qb_premium": 1.14,
    "te_premium_base": 1.06,
    "pick_year_discount_rate": 0.88,
    "rookie_contract_bonus": 0.05,
    "veteran_contract_penalty": 0.03,
}

AGE_CURVES = {
    "QB": {"peak": 28, "plateau_start": 25, "plateau_end": 31, "pre_slope": 0.028, "post_decay": 0.075, "gompertz_b": 12.0, "gompertz_c": 0.35},
    "RB": {"peak": 24, "plateau_start": 22, "plateau_end": 26, "pre_slope": 0.042, "post_decay": 0.145, "gompertz_b": 8.0, "gompertz_c": 0.55},
    "WR": {"peak": 26, "plateau_start": 23, "plateau_end": 29, "pre_slope": 0.033, "post_decay": 0.088, "gompertz_b": 10.0, "gompertz_c": 0.42},
    "TE": {"peak": 27, "plateau_start": 24, "plateau_end": 30, "pre_slope": 0.030, "post_decay": 0.092, "gompertz_b": 9.5, "gompertz_c": 0.40},
}

POSITION_SCARCITY = {
    "QB": {"elite_cutoff": 5, "starter_cutoff": 20, "scarcity_mult": 1.08},
    "RB": {"elite_cutoff": 10, "starter_cutoff": 40, "scarcity_mult": 1.05},
    "WR": {"elite_cutoff": 12, "starter_cutoff": 50, "scarcity_mult": 1.02},
    "TE": {"elite_cutoff": 5, "starter_cutoff": 15, "scarcity_mult": 1.12},
}

DRAFT_PICK_REGRESSION = {
    "1.01-1.03": {"hit_rate": 0.72, "bust_rate": 0.08, "avg_peak_val": 8200, "avg_peak_age": 24},
    "1.04-1.06": {"hit_rate": 0.58, "bust_rate": 0.14, "avg_peak_val": 6800, "avg_peak_age": 24},
    "1.07-1.09": {"hit_rate": 0.46, "bust_rate": 0.22, "avg_peak_val": 5600, "avg_peak_age": 25},
    "1.10-1.12": {"hit_rate": 0.34, "bust_rate": 0.30, "avg_peak_val": 4500, "avg_peak_age": 25},
    "2.01-2.04": {"hit_rate": 0.22, "bust_rate": 0.42, "avg_peak_val": 3200, "avg_peak_age": 25},
    "2.05-2.08": {"hit_rate": 0.16, "bust_rate": 0.50, "avg_peak_val": 2400, "avg_peak_age": 26},
    "2.09-2.12": {"hit_rate": 0.11, "bust_rate": 0.58, "avg_peak_val": 1900, "avg_peak_age": 26},
    "3.01-3.12": {"hit_rate": 0.07, "bust_rate": 0.68, "avg_peak_val": 1200, "avg_peak_age": 26},
}

FALLBACK_PICK_VALUES_1QB = {
    "2025 Early 1st": 7200,
    "2025 Mid 1st": 5600,
    "2025 Late 1st": 4200,
    "2025 Early 2nd": 2500,
    "2025 Mid 2nd": 1900,
    "2025 Late 2nd": 1400,
    "2026 Early 1st": 6200,
    "2026 Mid 1st": 4900,
    "2026 Late 1st": 3600,
    "2027 Early 1st": 5300,
    "2027 Mid 1st": 4200,
    "2027 Late 1st": 3100,
}


@dataclass
class DataSourceError(Exception):
    """Represents a fetch failure from an external source.

    Args:
        source_name: Source label.
        url: URL that failed.
        status_code: Last known HTTP status.
    """

    source_name: str
    url: str
    status_code: int | None = None


@dataclass
class PlayerValue:
    id: str
    name: str
    position: str
    team: str
    age: float | None
    years_exp: int
    fc_value: float | None
    ktc_value: float | None
    fc_normalized: float | None
    ktc_normalized: float | None
    source_disagreement_pct: float
    consensus_raw: float
    age_mult: float
    injury_status: str | None
    adjusted_value: float
    tier: str
    trend_30d: int
    trend_7d: int
    future_value_1yr: float = 0.0
    future_value_2yr: float = 0.0
    future_value_3yr: float = 0.0
    future_value_5yr: float = 0.0
    fvs: float = 0.0
    fvs_tier: str = ""
    confidence_low: float = 0.0
    confidence_high: float = 0.0


@dataclass
class PickValue:
    name: str
    year: int
    round: int
    tier: str
    base_value: float
    time_discounted_value: float
    expected_ev: float
    years_until_used: int
    confidence_band_pct: float
    adjusted_value: float = 0.0


@dataclass
class RosterProfile:
    roster_id: int
    owner_name: str
    players: list[PlayerValue] = field(default_factory=list)
    picks: list[PickValue] = field(default_factory=list)
    total_value: float = 0.0
    starter_value: float = 0.0
    bench_depth_value: float = 0.0
    pick_value: float = 0.0
    qb_value: float = 0.0
    qb_players: list[PlayerValue] = field(default_factory=list)
    rb_value: float = 0.0
    rb_players: list[PlayerValue] = field(default_factory=list)
    wr_value: float = 0.0
    wr_players: list[PlayerValue] = field(default_factory=list)
    te_value: float = 0.0
    te_players: list[PlayerValue] = field(default_factory=list)
    avg_age: float = 0.0
    avg_age_starters: float = 0.0
    total_fvs: float = 0.0
    fvs_rank: int = 0
    window: str = ""
    window_score: float = 0.0
    positional_needs: dict[str, float] = field(default_factory=dict)
    positional_surplus: dict[str, float] = field(default_factory=dict)
    record: dict[str, int] = field(default_factory=dict)
    roster_grade: str = ""
    grade_reasoning: str = ""


@dataclass
class TradeScore:
    opponent: str
    send_assets: list[PlayerValue]
    receive_assets: list[PlayerValue]
    raw_value_gain: float
    need_adjusted_gain: float
    future_value_delta: float
    plausibility_score: float
    composite_score: float


class CacheManager:
    """Disk cache helper.

    Args:
        ttl_hours: Cache TTL in hours.
        enabled: Whether cache is enabled.
    """

    def __init__(self, ttl_hours: int = 24, enabled: bool = True) -> None:
        self.ttl_hours = ttl_hours
        self.enabled = enabled
        self.cache_dir = Path(".fantasy_cache")
        self.cache_dir.mkdir(exist_ok=True)

    def _path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def get(self, key: str) -> Optional[Any]:
        """Read value from cache if not expired.

        Args:
            key: Cache key.

        Returns:
            Cached value or None.

        Raises:
            None.
        """

        if not self.enabled:
            return None
        path = self._path(key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text())
            age_hours = (time.time() - payload["ts"]) / 3600
            if age_hours > self.ttl_hours:
                return None
            return payload["value"]
        except Exception:
            return None

    def set(self, key: str, value: Any) -> None:
        """Atomically write cache value.

        Args:
            key: Cache key.
            value: Arbitrary JSON-serializable payload.

        Returns:
            None.

        Raises:
            OSError: If filesystem write fails.
        """

        if not self.enabled:
            return
        path = self._path(key)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"ts": time.time(), "value": value}, default=str))
        os.replace(tmp, path)

    def clear(self) -> None:
        """Delete cache files.

        Args:
            None.

        Returns:
            None.

        Raises:
            None.
        """

        files = list(self.cache_dir.glob("*.json"))
        for f in files:
            f.unlink(missing_ok=True)
        console.print(f"[yellow]Cleared {len(files)} cache files.[/yellow]")

    def stats(self) -> dict[str, float]:
        """Return cache statistics.

        Args:
            None.

        Returns:
            Summary dictionary.

        Raises:
            None.
        """

        files = list(self.cache_dir.glob("*.json"))
        if not files:
            return {"total_files": 0, "total_size_kb": 0, "oldest_entry_hours": 0, "newest_entry_hours": 0}
        now = time.time()
        ages = [(now - f.stat().st_mtime) / 3600 for f in files]
        size_kb = sum(f.stat().st_size for f in files) / 1024
        return {
            "total_files": len(files),
            "total_size_kb": round(size_kb, 2),
            "oldest_entry_hours": round(max(ages), 2),
            "newest_entry_hours": round(min(ages), 2),
        }


class HttpClient:
    """HTTP wrapper with retries and mock support."""

    def __init__(self, verbose: bool = False, mock_mode: bool = False, cache: CacheManager | None = None) -> None:
        self.verbose = verbose
        self.mock_mode = mock_mode
        self.cache = cache or CacheManager()

    def get(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        retries: int = 3,
        timeout: int = 20,
        allow_non_json: bool = False,
        source_name: str = "unknown",
    ) -> dict | list | str:
        """Execute GET with retry logic.

        Args:
            url: Endpoint URL.
            headers: Optional headers.
            params: Query params.
            retries: Number of retry attempts.
            timeout: Request timeout seconds.
            allow_non_json: Return raw body if not JSON.
            source_name: Friendly data source name.

        Returns:
            Parsed JSON payload or raw string.

        Raises:
            DataSourceError: If all attempts fail.
        """

        mock_key = f"mock_{hashlib.sha256((url + json.dumps(params or {}, sort_keys=True)).encode()).hexdigest()}"
        mock_path = Path(".fantasy_cache") / f"{mock_key}.json"
        if self.mock_mode:
            if mock_path.exists():
                return json.loads(mock_path.read_text())
            raise DataSourceError(source_name, url, None)

        for attempt in range(retries):
            start = time.perf_counter()
            try:
                r = requests.get(url, headers=headers, params=params, timeout=timeout)
                elapsed_ms = int((time.perf_counter() - start) * 1000)
                if self.verbose:
                    console.log(f"[blue]HTTP[/blue] {url} status={r.status_code} {elapsed_ms}ms attempt={attempt+1}")
                if r.status_code == 429:
                    retry_after = int(r.headers.get("Retry-After", "10"))
                    time.sleep(retry_after)
                    continue
                if r.status_code != 200:
                    if attempt < retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    raise DataSourceError(source_name, url, r.status_code)
                ctype = r.headers.get("Content-Type", "")
                if "application/json" in ctype or (not allow_non_json):
                    return r.json()
                return r.text
            except requests.Timeout:
                console.print(f"[yellow][{source_name}] timeout for {url}; using fallback.[/yellow]")
                return {} if not allow_non_json else ""
            except requests.RequestException:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise DataSourceError(source_name, url, None)
        raise DataSourceError(source_name, url, None)


class NameResolver:
    """Cross-source player name resolver."""

    def __init__(self) -> None:
        self.resolution_log: list[dict[str, Any]] = []

    def normalize(self, name: str) -> str:
        """Normalize player names across sources.

        Args:
            name: Raw name.

        Returns:
            Normalized name.

        Raises:
            None.
        """

        s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii").lower().strip()
        s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b\.?", "", s)
        s = re.sub(r"['\-.]", "", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def _jaro_winkler(self, s1: str, s2: str) -> float:
        if s1 == s2:
            return 1.0
        if not s1 or not s2:
            return 0.0
        max_dist = max(len(s1), len(s2)) // 2 - 1
        s1_matches = [False] * len(s1)
        s2_matches = [False] * len(s2)
        m = 0
        for i, ch in enumerate(s1):
            start = max(0, i - max_dist)
            end = min(i + max_dist + 1, len(s2))
            for j in range(start, end):
                if s2_matches[j] or s2[j] != ch:
                    continue
                s1_matches[i] = s2_matches[j] = True
                m += 1
                break
        if m == 0:
            return 0.0
        t = 0
        k = 0
        for i in range(len(s1)):
            if not s1_matches[i]:
                continue
            while not s2_matches[k]:
                k += 1
            if s1[i] != s2[k]:
                t += 1
            k += 1
        t /= 2
        jaro = (m / len(s1) + m / len(s2) + (m - t) / m) / 3
        prefix = 0
        for a, b in zip(s1, s2):
            if a == b and prefix < 4:
                prefix += 1
            else:
                break
        return jaro + 0.1 * prefix * (1 - jaro)

    def resolve_with_confidence(self, target_name: str, candidates: dict[str, Any], threshold: float = 0.84) -> tuple[Optional[str], float]:
        """Resolve name and score.

        Args:
            target_name: Target player name.
            candidates: Candidate name map.
            threshold: Matching threshold.

        Returns:
            Tuple of candidate key and confidence score.

        Raises:
            None.
        """

        target = self.normalize(target_name)
        normalized = {self.normalize(k): k for k in candidates.keys()}
        if target in normalized:
            return normalized[target], 1.0
        bits = target.split()
        if len(bits) == 2:
            inv = f"{bits[1]} {bits[0]}"
            if inv in normalized:
                return normalized[inv], 0.96
        best_name, best_score = None, 0.0
        for cand_norm, original in normalized.items():
            sc = self._jaro_winkler(target, cand_norm)
            if sc > best_score:
                best_name, best_score = original, sc
        if best_score >= threshold:
            return best_name, best_score
        if bits:
            initial = f"{bits[0][0]} {bits[-1]}"
            for cand_norm, original in normalized.items():
                cbits = cand_norm.split()
                if cbits and f"{cbits[0][0]} {cbits[-1]}" == initial:
                    return original, 0.85
        return None, best_score

    def resolve(self, target_name: str, candidates: dict[str, Any], threshold: float = 0.84) -> Optional[str]:
        """Resolve a name.

        Args:
            target_name: Player name.
            candidates: Candidate map.
            threshold: Similarity threshold.

        Returns:
            Matched name or None.

        Raises:
            None.
        """

        matched, score = self.resolve_with_confidence(target_name, candidates, threshold)
        self.resolution_log.append({"source": "resolve", "target": target_name, "resolved": matched, "score": round(score, 4), "method": "multi-stage"})
        return matched


def age_multiplier(position: str, age: float | None, method: str = "gompertz") -> float:
    """Compute age-based dynasty value multiplier.

    Args:
        position: Position key.
        age: Player age.
        method: Curve method.

    Returns:
        Multiplier in bounded range.

    Raises:
        None.
    """

    if age is None:
        return 1.0
    curve = AGE_CURVES.get(position, AGE_CURVES["WR"])
    peak = curve["peak"]
    if method == "exponential":
        if age <= peak:
            mult = 1.05 - curve["pre_slope"] * max(0, peak - age - 1)
        else:
            mult = (1 - curve["post_decay"]) ** (age - peak)
        return float(max(0.05, min(1.25, mult)))
    if method == "logistic":
        k = 0.33
        base = 1 / (1 + math.exp(k * (age - peak)))
        return float(max(0.05, min(1.25, 0.15 + base * 1.0)))
    # Gompertz is preferred because NFL value paths show asymmetric rise-then-fall behavior better than symmetric curves.
    b, c = curve["gompertz_b"], curve["gompertz_c"]
    span = max(curve["plateau_end"] - curve["plateau_start"], 1e-6)
    rel = (age - curve["plateau_start"]) / span
    rel_peak = (peak - curve["plateau_start"]) / span
    g_age = math.exp(-b * math.exp(-c * rel))
    g_peak = math.exp(-b * math.exp(-c * rel_peak))
    if age <= peak:
        scaled = 0.55 + 0.65 * (g_age / max(g_peak, 1e-9))
    else:
        scaled = 1.10 * ((1 - curve["post_decay"]) ** (age - peak))
    return float(max(0.05, min(1.25, scaled)))


class SleeperClient:
    BASE = "https://api.sleeper.app/v1"

    def __init__(self, http: HttpClient, cache: CacheManager):
        self.http = http
        self.cache = cache

    def get_user(self, username: str) -> dict:
        data = self.http.get(f"{self.BASE}/user/{username}", source_name="Sleeper")
        if not isinstance(data, dict) or "user_id" not in data:
            raise ValueError(f"Sleeper user '{username}' not found.")
        return data

    def get_leagues(self, user_id: str, season: str) -> list[dict]:
        data = self.http.get(f"{self.BASE}/user/{user_id}/leagues/nfl/{season}", source_name="Sleeper")
        return [x for x in data if x.get("settings", {}).get("type") == 2] if isinstance(data, list) else []

    def select_league(self, leagues: list[dict]) -> dict:
        if len(leagues) == 1:
            return leagues[0]
        tbl = Table(title="Select Dynasty League")
        for c in ["Index", "League Name", "Teams", "Scoring", "Superflex"]:
            tbl.add_column(c)
        for i, lg in enumerate(leagues):
            rp = lg.get("roster_positions", [])
            tbl.add_row(str(i), lg.get("name", "Unnamed"), str(lg.get("settings", {}).get("num_teams", "?")), f"PPR {lg.get('scoring_settings', {}).get('rec', 0)}", "Yes" if "SUPER_FLEX" in rp else "No")
        console.print(tbl)
        idx = int(Prompt.ask("League index", default="0"))
        return leagues[max(0, min(idx, len(leagues) - 1))]

    def get_league_metadata(self, league: dict) -> dict:
        rp = league.get("roster_positions", [])
        starter_slots: dict[str, int] = {}
        for p in rp:
            starter_slots[p] = starter_slots.get(p, 0) + 1
        return {
            "league_id": league["league_id"],
            "league_name": league.get("name", "Unknown"),
            "season": str(league.get("season", CONFIG["season"])),
            "num_teams": int(league.get("settings", {}).get("num_teams", 12)),
            "is_superflex": "SUPER_FLEX" in rp,
            "is_2qb": rp.count("QB") > 1,
            "ppr": float(league.get("scoring_settings", {}).get("rec", 0)),
            "te_premium": float(league.get("scoring_settings", {}).get("bonus_rec_te", 0)),
            "taxi_slots": int(league.get("settings", {}).get("taxi_slots", 0)),
            "ir_slots": int(league.get("settings", {}).get("reserve_slots", 0)),
            "roster_positions": rp,
            "starter_slots": starter_slots,
            "total_starter_count": len(rp),
        }

    def get_rosters(self, league_id: str) -> list[dict]:
        rosters = self.http.get(f"{self.BASE}/league/{league_id}/rosters", source_name="Sleeper")
        return [{**r, "taxi": r.get("taxi", []), "reserve": r.get("reserve", [])} for r in rosters] if isinstance(rosters, list) else []

    def get_traded_picks(self, league_id: str) -> list[dict]:
        data = self.http.get(f"{self.BASE}/league/{league_id}/traded_picks", source_name="Sleeper")
        return data if isinstance(data, list) else []

    def get_draft_picks(self, league_id: str) -> list[dict]:
        drafts = self.http.get(f"{self.BASE}/league/{league_id}/drafts", source_name="Sleeper")
        out: list[dict] = []
        if not isinstance(drafts, list):
            return out
        for d in drafts:
            picks = self.http.get(f"{self.BASE}/draft/{d.get('draft_id')}/picks", source_name="Sleeper")
            if isinstance(picks, list):
                out.extend(picks)
        return out

    def get_player_age_precise(self, player: dict) -> float | None:
        b = player.get("birth_date")
        if not b:
            return None
        try:
            born = datetime.fromisoformat(b).replace(tzinfo=UTC)
            return (datetime.now(UTC) - born).days / 365.25
        except Exception:
            return None

    def get_all_players(self, cache_manager: CacheManager) -> dict[str, dict]:
        key = "sleeper_players_nfl_v2"
        cached = cache_manager.get(key)
        if cached is not None:
            return cached
        players = self.http.get(f"{self.BASE}/players/nfl", source_name="Sleeper")
        out: dict[str, dict] = {}
        for pid, p in (players or {}).items():
            pos = p.get("position")
            if pos not in {"QB", "RB", "WR", "TE"}:
                continue
            status = p.get("status", "Active")
            if status in {"Retired"}:
                continue
            age = p.get("age") or self.get_player_age_precise(p)
            rec = {
                "id": str(pid), "full_name": p.get("full_name") or p.get("first_name", "") + " " + p.get("last_name", ""), "position": pos,
                "team": p.get("team") or "FA", "age": age, "birth_date": p.get("birth_date"), "years_exp": int(p.get("years_exp") or 0),
                "college": p.get("college"), "draft_pick": p.get("search_rank"), "draft_year": p.get("draft_year"), "injury_status": p.get("injury_status"),
                "status": status, "depth_chart_order": p.get("depth_chart_order"),
                "search_full_name": re.sub(r"\s+", "", (p.get("full_name") or "").lower()),
            }
            out[str(pid)] = rec
        cache_manager.set(key, out)
        return out


class FantasyCalcClient:
    def __init__(self, http: HttpClient, cache: CacheManager):
        self.http = http
        self.cache = cache
        self.fc_by_sleeper_id: dict[str, dict] = {}
        self.fc_by_normalized_name: dict[str, dict] = {}
        self.pick_values: dict[str, int] = {}
        self.resolver = NameResolver()

    def fetch_values(self, is_superflex: bool, ppr: float, num_teams: int) -> list[dict]:
        num_qbs = 2 if is_superflex else 1
        key = f"fc_dynasty_{num_qbs}_{num_teams}_{ppr}"
        cached = self.cache.get(key)
        if cached:
            data = cached
        else:
            url = "https://api.fantasycalc.com/values/current"
            data = self.http.get(url, params={"isDynasty": "true", "numQbs": num_qbs, "numTeams": num_teams, "ppr": ppr}, source_name="FantasyCalc")
            self.cache.set(key, data)
        parsed: list[dict] = []
        for r in data if isinstance(data, list) else []:
            name = r.get("playerName") or r.get("name") or r.get("assetName", "")
            rec = {
                "sleeper_id": str(r.get("player", {}).get("sleeperId") or r.get("sleeper_id") or "") or None,
                "name": name,
                "position": r.get("position") or r.get("player", {}).get("position") or "PICK",
                "team": r.get("team") or r.get("player", {}).get("team"),
                "age": r.get("age") or r.get("player", {}).get("age"),
                "value": int(r.get("value") or 0),
                "trend_1day": int(r.get("valueChange", {}).get("day", 0)),
                "trend_7day": int(r.get("valueChange", {}).get("week", 0)),
                "trend_30day": int(r.get("valueChange", {}).get("month", 0)),
                "overallRank": r.get("overallRank"),
                "positionRank": r.get("positionRank"),
                "is_pick": bool("pick" in name.lower() or r.get("isPick") is True),
                "pick_details": name if "pick" in name.lower() or re.search(r"\b[123](st|nd|rd)\b", name.lower()) else None,
            }
            parsed.append(rec)
            if rec["sleeper_id"]:
                self.fc_by_sleeper_id[rec["sleeper_id"]] = rec
            self.fc_by_normalized_name[self.resolver.normalize(name)] = rec
            if rec["is_pick"]:
                self.pick_values[name] = rec["value"]
        return parsed

    def fetch_historical_trend(self, player_sleeper_id: str) -> list[dict]:
        try:
            url = f"https://api.fantasycalc.com/values/history?sleeperId={player_sleeper_id}&days=90"
            data = self.http.get(url, source_name="FantasyCalc")
            return [{"date": x.get("date"), "value": x.get("value")} for x in data] if isinstance(data, list) else []
        except Exception:
            return []


class KTCClient:
    def __init__(self, http: HttpClient, cache: CacheManager):
        self.http = http
        self.cache = cache
        self.ktc_by_normalized_name: dict[str, dict] = {}
        self.resolver = NameResolver()

    def _parse(self, data: Any, sf: bool) -> list[dict]:
        out: list[dict] = []
        if isinstance(data, dict):
            if "players" in data:
                data = data["players"]
            elif "data" in data:
                data = data["data"]
        for r in data if isinstance(data, list) else []:
            sfv = int(r.get("superFlex") or r.get("superFlexValue") or r.get("value") or 0)
            oq = int(r.get("oneQB") or r.get("oneQbValue") or sfv)
            rec = {
                "name": r.get("name") or r.get("playerName", ""),
                "position": r.get("position", ""),
                "team": r.get("team"),
                "value": sfv if sf else oq,
                "superFlex_value": sfv,
                "oneQB_value": oq,
                "age": r.get("age"),
                "rank": r.get("rank"),
                "trend_7day": r.get("trend_7day"),
            }
            if rec["name"]:
                out.append(rec)
                self.ktc_by_normalized_name[self.resolver.normalize(rec["name"])] = rec
        return out

    def fetch_values(self, is_superflex: bool) -> list[dict]:
        sf = "true" if is_superflex else "false"
        key = f"ktc_{sf}"
        cached = self.cache.get(key)
        if cached:
            return self._parse(cached, is_superflex)
        urls = [
            f"https://keeptradecut.com/dynasty-rankings/json?superFlex={sf}&format=json",
            f"https://keeptradecut.com/dynasty-rankings?format=json&superFlex={sf}",
        ]
        for u in urls:
            try:
                data = self.http.get(u, source_name="KTC", allow_non_json=False)
                parsed = self._parse(data, is_superflex)
                if parsed:
                    self.cache.set(key, data)
                    return parsed
            except Exception:
                continue
        try:
            html = self.http.get(
                "https://keeptradecut.com/dynasty-rankings",
                source_name="KTC",
                allow_non_json=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.119 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Referer": "https://www.google.com/",
                },
            )
            patterns = [r"var\s+(?:playerData|rankings|dynastyRankings|ktcData)\s*=\s*(\[.*?\]);"]
            for pat in patterns:
                m = re.search(pat, html, re.DOTALL)
                if m:
                    data = json.loads(m.group(1))
                    parsed = self._parse(data, is_superflex)
                    if parsed:
                        self.cache.set(key, data)
                        return parsed
        except Exception:
            pass
        console.print("[yellow][KTC] All scraping strategies failed. Proceeding with FantasyCalc-only values (KTC weight redistributed to FC).[/yellow]")
        CONFIG["fc_weight"], CONFIG["ktc_weight"] = 1.0, 0.0
        return []


class FutureValueProjector:
    POSITION_DECAY_OVERLAY = {
        "RB": {1: 0.97, 2: 0.93, 3: 0.87, 5: 0.72},
        "WR": {1: 0.98, 2: 0.95, 3: 0.91, 5: 0.80},
        "QB": {1: 0.99, 2: 0.97, 3: 0.94, 5: 0.84},
        "TE": {1: 0.98, 2: 0.95, 3: 0.90, 5: 0.78},
    }

    def __init__(self, method: str, projection_years: list[int]):
        self.method = method
        self.projection_years = projection_years

    def project_player(self, player: dict | PlayerValue, current_value: float, years_ahead: int) -> dict[str, float]:
        pos = player["position"] if isinstance(player, dict) else player.position
        age = player.get("age") if isinstance(player, dict) else player.age
        years_exp = int(player.get("years_exp", 0) if isinstance(player, dict) else player.years_exp)
        trend_30d = float(player.get("trend_30d", 0) if isinstance(player, dict) else player.trend_30d)
        age_mult_now = age_multiplier(pos, age, self.method)
        age_mult_future = age_multiplier(pos, None if age is None else age + years_ahead, self.method)
        momentum_factor = 1 + (trend_30d / max(current_value, 1)) * math.exp(-0.4 * years_ahead)
        decay_map = self.POSITION_DECAY_OVERLAY.get(pos, {})
        if years_ahead in decay_map:
            positional_decay = decay_map[years_ahead]
        else:
            keys = sorted(decay_map.keys())
            if not keys:
                positional_decay = 0.9
            elif years_ahead > keys[-1]:
                positional_decay = decay_map[keys[-1]] * (0.95 ** (years_ahead - keys[-1]))
            else:
                hi = next(k for k in keys if k > years_ahead)
                lo = max(k for k in keys if k < hi)
                frac = (years_ahead - lo) / (hi - lo)
                positional_decay = decay_map[lo] + frac * (decay_map[hi] - decay_map[lo])
        dev_bonus = max(0.0, 0.08 - 0.026 * years_exp)
        projected = current_value * (age_mult_future / max(age_mult_now, 1e-6)) * momentum_factor * positional_decay * (1 + dev_bonus)
        sims = []
        for _ in range(200):
            am = np.random.normal(age_mult_future / max(age_mult_now, 1e-6), 0.04)
            mf = np.random.normal(momentum_factor, 0.06)
            db = np.random.normal(dev_bonus, 0.02)
            sims.append(max(0.0, current_value * am * mf * positional_decay * (1 + db)))
        mean = float(np.mean(sims))
        std = float(np.std(sims))
        within = sum(abs(x - mean) <= 0.2 * mean for x in sims) / len(sims)
        return {
            "projected_value": max(0.0, projected),
            "confidence_low": max(0.0, mean - std),
            "confidence_high": mean + std,
            "confidence_pct": within * 100,
        }

    def project_pick(self, pick_name: str, current_value: float, years_until_used: int) -> dict[str, float]:
        time_discount = CONFIG["pick_year_discount_rate"] ** years_until_used
        tier_regression = max(0.65, 1.0 - 0.05 * years_until_used)
        projected = current_value * time_discount * tier_regression
        lookup = "2.05-2.08"
        if "early 1" in pick_name.lower():
            lookup = "1.01-1.03"
        elif "mid 1" in pick_name.lower():
            lookup = "1.04-1.06"
        elif "late 1" in pick_name.lower():
            lookup = "1.10-1.12"
        t = DRAFT_PICK_REGRESSION[lookup]
        ev = t["hit_rate"] * t["avg_peak_val"] + (1 - t["hit_rate"] - t["bust_rate"]) * t["avg_peak_val"] * 0.45 + t["bust_rate"] * t["avg_peak_val"] * 0.05
        return {"projected_trade_value": projected, "expected_dynasty_value": ev}

    def compute_future_value_score(self, projections: dict[int, dict[str, float]], scale_vals: list[float]) -> float:
        weights = {1: 0.20, 2: 0.25, 3: 0.30, 5: 0.25}
        raw = sum(weights[y] * projections[y]["projected_value"] for y in [1, 2, 3, 5] if y in projections)
        p5, p95 = np.percentile(scale_vals, [5, 95]) if scale_vals else (0, 1)
        return float(np.clip((raw - p5) / max(p95 - p5, 1) * 100, 0, 100))


class ValueEngine:
    def __init__(self, resolver: NameResolver, fc_data: list[dict], ktc_data: list[dict], all_players: dict[str, dict], league_meta: dict):
        self.resolver = resolver
        self.fc_data = fc_data
        self.ktc_data = ktc_data
        self.all_players = all_players
        self.meta = league_meta

    def _tier(self, v: float) -> str:
        if v >= 9000:
            return "Elite"
        if v >= 7000:
            return "Star"
        if v >= 4500:
            return "Starter"
        if v >= 2500:
            return "Flex"
        if v >= 1000:
            return "Depth"
        return "Stash"

    def build_consensus(self) -> dict[str, PlayerValue]:
        fc_by_id = {x["sleeper_id"]: x for x in self.fc_data if x.get("sleeper_id")}
        fc_by_name = {self.resolver.normalize(x["name"]): x for x in self.fc_data if x.get("name")}
        ktc_by_name = {self.resolver.normalize(x["name"]): x for x in self.ktc_data if x.get("name")}
        fc_p90 = np.percentile([x["value"] for x in self.fc_data if x.get("value", 0) > 0], 90) if self.fc_data else 10000
        ktc_p90 = np.percentile([x["value"] for x in self.ktc_data if x.get("value", 0) > 0], 90) if self.ktc_data else 10000
        out: dict[str, PlayerValue] = {}
        temp_by_pos: dict[str, list[tuple[str, float]]] = {"QB": [], "RB": [], "WR": [], "TE": []}
        for pid, p in self.all_players.items():
            fc = fc_by_id.get(pid)
            if fc is None:
                m = self.resolver.resolve(p["full_name"], fc_by_name)
                fc = fc_by_name.get(self.resolver.normalize(m)) if m else None
            m2 = self.resolver.resolve(p["full_name"], ktc_by_name)
            ktc = ktc_by_name.get(self.resolver.normalize(m2)) if m2 else None
            if not fc and not ktc:
                continue
            fc_raw = float(fc["value"]) if fc else None
            ktc_raw = float(ktc["value"]) if ktc else None
            fcn = fc_raw * (10000 / max(fc_p90, 1)) if fc_raw is not None else None
            ktcn = ktc_raw * (10000 / max(ktc_p90, 1)) if ktc_raw is not None else None
            if fcn is not None and ktcn is not None:
                consensus = CONFIG["fc_weight"] * fcn + CONFIG["ktc_weight"] * ktcn
            else:
                consensus = fcn if fcn is not None else ktcn
            if consensus is None:
                continue
            disagreement = 0.0
            if fcn and ktcn:
                disagreement = abs(fcn - ktcn) / max(fcn, ktcn)
                if disagreement > 0.35:
                    consensus *= 0.92
            age = p.get("age")
            am = age_multiplier(p["position"], age, CONFIG["age_curve_method"])
            val = consensus * am
            if p["position"] == "TE":
                val *= CONFIG["te_premium_base"] + 0.015 * min(self.meta["te_premium"], 2.5)
            if p["position"] == "QB" and self.meta["is_superflex"]:
                val *= CONFIG["superflex_qb_premium"]
            if p.get("years_exp", 0) <= 3 and p.get("draft_year"):
                val *= 1 + CONFIG["rookie_contract_bonus"]
            peak = AGE_CURVES[p["position"]]["peak"]
            if age and age > peak + 3:
                val *= max(0.45, 1 - CONFIG["veteran_contract_penalty"] * (age - peak - 3))
            inj = p.get("injury_status")
            val *= {"IR": 0.88, "O": 0.88, "Q": 0.97, "D": 0.91}.get(inj, 1.0)
            pv = PlayerValue(
                id=pid,
                name=p["full_name"],
                position=p["position"],
                team=p.get("team", "FA"),
                age=age,
                years_exp=int(p.get("years_exp", 0)),
                fc_value=fc_raw,
                ktc_value=ktc_raw,
                fc_normalized=fcn,
                ktc_normalized=ktcn,
                source_disagreement_pct=disagreement * 100,
                consensus_raw=consensus,
                age_mult=am,
                injury_status=inj,
                adjusted_value=val,
                tier=self._tier(val),
                trend_30d=int(fc.get("trend_30day", 0) if fc else 0),
                trend_7d=int(fc.get("trend_7day", 0) if fc else 0),
            )
            out[pid] = pv
            temp_by_pos[p["position"]].append((pid, val))
        for pos, arr in temp_by_pos.items():
            arr.sort(key=lambda x: x[1], reverse=True)
            for idx, (pid, _) in enumerate(arr, start=1):
                if CONFIG["positional_scarcity_enabled"]:
                    sc = POSITION_SCARCITY[pos]
                    mult = sc["scarcity_mult"] if idx <= sc["elite_cutoff"] else (1 + (sc["scarcity_mult"] - 1) * 0.5 if idx <= sc["starter_cutoff"] else 1.0)
                    out[pid].adjusted_value *= mult
                    out[pid].tier = self._tier(out[pid].adjusted_value)
        return out


def build_pick_values(fc_data: list[dict], league_meta: dict, traded_picks: list[dict], draft_history: list[dict]) -> dict[str, PickValue]:
    out: dict[str, PickValue] = {}
    cur_year = datetime.now(UTC).year
    picks = [x for x in fc_data if x.get("is_pick")]
    for p in picks:
        nm = p.get("pick_details") or p["name"]
        year_m = re.search(r"(20\d{2})", nm)
        round_m = re.search(r"([123])(st|nd|rd)", nm.lower())
        tier = "Mid"
        if "early" in nm.lower():
            tier = "Early"
        elif "late" in nm.lower():
            tier = "Late"
        py = int(year_m.group(1)) if year_m else cur_year
        pr = int(round_m.group(1)) if round_m else 2
        years = max(0, py - cur_year)
        base = float(p.get("value", 0))
        tdv = base * (CONFIG["pick_year_discount_rate"] ** years)
        lookup = f"1.04-1.06"
        if pr == 1 and tier == "Early":
            lookup = "1.01-1.03"
        elif pr == 1 and tier == "Late":
            lookup = "1.10-1.12"
        elif pr == 2 and tier == "Early":
            lookup = "2.01-2.04"
        elif pr == 2 and tier == "Late":
            lookup = "2.09-2.12"
        elif pr == 3:
            lookup = "3.01-3.12"
        t = DRAFT_PICK_REGRESSION[lookup]
        ev = t["hit_rate"] * t["avg_peak_val"] + (1 - t["hit_rate"] - t["bust_rate"]) * t["avg_peak_val"] * 0.40 + t["bust_rate"] * 200
        pv = PickValue(nm, py, pr, tier, base, tdv, ev, years, 0.15 * years, tdv)
        out[nm] = pv
    if not out:
        scale = 1.18 if league_meta["is_superflex"] else 1.0
        for nm, val in FALLBACK_PICK_VALUES_1QB.items():
            year = int(re.search(r"20\d{2}", nm).group(0))
            round_v = int(re.search(r"([123])st|([23])nd|([23])rd", nm.lower()).group(1) or 2)
            years = max(0, year - cur_year)
            tdv = val * scale * (CONFIG["pick_year_discount_rate"] ** years)
            out[nm] = PickValue(nm, year, round_v, "Mid", val * scale, tdv, tdv * 1.05, years, 0.15 * years, tdv)
    return out


class RosterAnalyzer:
    def __init__(self, player_values: dict[str, PlayerValue], league_meta: dict, owner_map: dict[int, str]):
        self.player_values = player_values
        self.meta = league_meta
        self.owner_map = owner_map

    def analyze_roster(self, roster_record: dict, pick_values: dict[str, PickValue]) -> RosterProfile:
        r = RosterProfile(roster_id=int(roster_record["roster_id"]), owner_name=self.owner_map.get(int(roster_record["roster_id"]), f"Roster {roster_record['roster_id']}"))
        pids = roster_record.get("players") or []
        r.players = [self.player_values[p] for p in pids if p in self.player_values]
        for pos in ["QB", "RB", "WR", "TE"]:
            plist = sorted([p for p in r.players if p.position == pos], key=lambda x: x.adjusted_value, reverse=True)
            setattr(r, f"{pos.lower()}_players", plist)
            setattr(r, f"{pos.lower()}_value", sum(p.adjusted_value for p in plist))
        starter_slots = {"QB": self.meta["starter_slots"].get("QB", 1), "RB": self.meta["starter_slots"].get("RB", 2), "WR": self.meta["starter_slots"].get("WR", 2), "TE": self.meta["starter_slots"].get("TE", 1)}
        starters = []
        for pos, c in starter_slots.items():
            starters.extend(sorted([p for p in r.players if p.position == pos], key=lambda x: x.adjusted_value, reverse=True)[:c])
        r.starter_value = sum(p.adjusted_value for p in starters)
        r.total_value = sum(p.adjusted_value for p in r.players)
        r.bench_depth_value = max(0.0, r.total_value - r.starter_value)
        r.total_fvs = sum(p.fvs for p in r.players)
        ages = [p.age for p in r.players if p.age is not None]
        vals = [p.adjusted_value for p in r.players if p.age is not None]
        r.avg_age = float(np.average(ages, weights=vals)) if ages else 0.0
        s_ages = [p.age for p in starters if p.age is not None]
        s_vals = [p.adjusted_value for p in starters if p.age is not None]
        r.avg_age_starters = float(np.average(s_ages, weights=s_vals)) if s_ages else 0.0
        r.pick_value = 0.0
        for p in pick_values.values():
            if str(roster_record["roster_id"]) in p.name:
                r.picks.append(p)
                r.pick_value += p.time_discounted_value
        r.total_value += r.pick_value
        for pos in ["QB", "RB", "WR", "TE"]:
            arr = sorted([p for p in r.players if p.position == pos], key=lambda x: x.adjusted_value, reverse=True)
            depth_score = len(arr) / max(starter_slots[pos] * 2, 1)
            starter_val = sum(p.adjusted_value for p in arr[: starter_slots[pos]])
            starter_fvs = sum(p.fvs for p in arr[: starter_slots[pos]])
            value_score = starter_val / max(8000 * starter_slots[pos], 1)
            future_score = starter_fvs / max(70 * starter_slots[pos], 1)
            need = max(0.0, min(1.0, 1.0 - (0.33 * depth_score + 0.34 * value_score + 0.33 * future_score)))
            r.positional_needs[pos] = round(need, 3)
            r.positional_surplus[pos] = round(max(0.0, 0.7 - need), 3)
        return r


class TradeEngine:
    def __init__(self, my_roster: RosterProfile, all_rosters: list[RosterProfile], args: argparse.Namespace):
        self.my = my_roster
        self.all = [r for r in all_rosters if r.roster_id != my_roster.roster_id]
        self.args = args

    def detect_need_mismatch(self, mine: RosterProfile, opp: RosterProfile) -> tuple[list[str], list[str]]:
        give = [p for p, s in mine.positional_surplus.items() if s > 0.25 and opp.positional_needs.get(p, 0) > 0.5]
        want = [p for p, s in mine.positional_needs.items() if s > 0.5 and opp.positional_surplus.get(p, 0) > 0.2]
        return give, want

    def compute_plausibility(self, my_send: list[PlayerValue], their_receive: list[PlayerValue], opponent_roster: RosterProfile) -> float:
        send_val = sum(p.adjusted_value for p in my_send)
        rec_val = sum(p.adjusted_value for p in their_receive)
        value_ratio = rec_val / max(send_val, 1)
        if value_ratio < 0.75:
            return 0.0
        need_fulfillment = float(np.mean([opponent_roster.positional_needs.get(p.position, 0.5) for p in their_receive])) if their_receive else 0.5
        return round(min(1.0, 0.60 * min(value_ratio, 1.15) + 0.40 * need_fulfillment), 3)

    def generate_recommendations(self) -> list[TradeScore]:
        recs: list[TradeScore] = []
        mine = [p for p in sorted(self.my.players, key=lambda x: x.adjusted_value, reverse=True) if p.adjusted_value >= CONFIG["min_asset_value_for_trade"]][:15]
        sizes = [(1, 1), (1, 2), (2, 1), (2, 2), (1, 3), (3, 1), (2, 3), (3, 2), (3, 3)]
        for opp in self.all:
            give_pos, want_pos = self.detect_need_mismatch(self.my, opp)
            opp_assets = [p for p in sorted(opp.players, key=lambda x: x.adjusted_value, reverse=True) if p.adjusted_value >= CONFIG["min_asset_value_for_trade"]][:15]
            for a, b in sizes:
                if a > self.args.max_send or b > self.args.max_send:
                    continue
                my_pool = mine[:15 if (a == 1 and b == 1) else 8]
                opp_pool = opp_assets[:15 if (a == 1 and b == 1) else 8]
                for send in itertools.combinations(my_pool, a):
                    send_val = sum(x.adjusted_value for x in send)
                    if a == b == 1 and send[0].position not in give_pos and give_pos:
                        continue
                    for receive in itertools.combinations(opp_pool, b):
                        if a == b == 1 and receive[0].position not in want_pos and want_pos:
                            continue
                        rec_val = sum(x.adjusted_value for x in receive)
                        ratio = rec_val / max(send_val, 1)
                        if not (0.65 <= ratio <= 1.50):
                            continue
                        upper_bound = sum(sorted([x.adjusted_value for x in opp_pool], reverse=True)[:b]) - send_val
                        if upper_bound < self.args.min_gain:
                            continue
                        raw_gain = rec_val - send_val
                        if raw_gain < self.args.min_gain:
                            continue
                        need_gain = sum(x.adjusted_value * (1 + 0.20 * (self.my.positional_needs.get(x.position, 0.5) - 0.5)) for x in receive) - send_val
                        fvs_delta = sum(x.fvs for x in receive) - sum(x.fvs for x in send)
                        plaus = self.compute_plausibility(list(send), list(receive), opp)
                        if plaus <= 0:
                            continue
                        n_raw = np.tanh(raw_gain / 3000)
                        n_fvs = np.tanh(fvs_delta / 120)
                        comp = 0.45 * n_raw + 0.30 * n_fvs + 0.25 * plaus
                        recs.append(TradeScore(opp.owner_name, list(send), list(receive), raw_gain, need_gain, fvs_delta, plaus, comp))
        recs.sort(key=lambda x: x.composite_score, reverse=True)
        seen = set()
        dedup = []
        for r in recs:
            key = (max(r.send_assets, key=lambda x: x.adjusted_value).id, max(r.receive_assets, key=lambda x: x.adjusted_value).id)
            if key in seen:
                continue
            seen.add(key)
            dedup.append(r)
            if len(dedup) >= self.args.top:
                break
        return dedup

    def compute_buy_sell_targets(self) -> tuple[list[dict], list[dict]]:
        sell = []
        for p in self.my.players:
            if p.adjusted_value <= 0:
                continue
            score = (p.adjusted_value - p.future_value_1yr) / p.adjusted_value
            if score > 0.12 and p.trend_30d >= 0:
                sell.append({"name": p.name, "score": score, "current": p.adjusted_value, "future": p.future_value_1yr})
        buy = []
        for opp in self.all:
            for p in opp.players:
                if p.adjusted_value <= 0:
                    continue
                score = (p.future_value_2yr - p.adjusted_value) / p.adjusted_value
                if score > 0.15 and p.trend_30d < 0:
                    buy.append({"name": p.name, "owner": opp.owner_name, "score": score, "current": p.adjusted_value, "future": p.future_value_2yr})
        buy.sort(key=lambda x: x["score"], reverse=True)
        sell.sort(key=lambda x: x["score"], reverse=True)
        return buy[:8], sell[:8]


class Display:
    def print_header(self, league_name: str) -> None:
        console.print(Panel.fit(f"[bold cyan]DYNASTY FUTURE VALUE ANALYZER[/bold cyan]\n[dim]Generated {datetime.now().isoformat()}[/dim]\n{league_name}"))

    def print_roster(self, roster_profile: RosterProfile) -> None:
        t = Table(title=f"Roster: {roster_profile.owner_name}")
        for c in ["Rank", "Name", "Pos", "Team", "Age", "Current", "1Y", "3Y", "FVS", "Tier"]:
            t.add_column(c)
        players = sorted(roster_profile.players, key=lambda x: x.adjusted_value, reverse=True)
        for i, p in enumerate(players, 1):
            t.add_row(str(i), p.name, p.position, p.team, f"{p.age:.1f}" if p.age else "-", f"{p.adjusted_value:,.0f}", f"{p.future_value_1yr:,.0f}", f"{p.future_value_3yr:,.0f}", f"{p.fvs:.1f}", p.tier)
        console.print(t)
        console.print(Panel(f"Total {roster_profile.total_value:,.0f} | Grade {roster_profile.roster_grade} | Window {roster_profile.window} | Avg age {roster_profile.avg_age_starters:.1f}"))

    def print_league_rankings(self, all_rosters: list[RosterProfile], mine: str) -> None:
        t = Table(title="League Rankings")
        for c in ["Rank", "Owner", "Total", "FVS", "Avg Age", "Window"]:
            t.add_column(c)
        for i, r in enumerate(sorted(all_rosters, key=lambda x: x.total_value, reverse=True), 1):
            style = "bold cyan" if r.owner_name == mine else ""
            t.add_row(str(i), f"[{style}]{r.owner_name}[/{style}]" if style else r.owner_name, f"{r.total_value:,.0f}", f"{r.total_fvs:,.1f}", f"{r.avg_age_starters:.1f}", r.window)
        console.print(t)

    def print_future_value_projections(self, my_roster: RosterProfile) -> None:
        t = Table(title="Future Value Projections")
        for c in ["Player", "+1", "+2", "+3", "+5", "Conf"]:
            t.add_column(c)
        top = sorted(my_roster.players, key=lambda x: x.fvs, reverse=True)[:20]
        for p in top:
            arrow = "🟢↑" if p.future_value_3yr > p.adjusted_value else "🔴↓"
            t.add_row(p.name, f"{p.future_value_1yr:,.0f}", f"{p.future_value_2yr:,.0f}", f"{p.future_value_3yr:,.0f} {arrow}", f"{p.future_value_5yr:,.0f}", f"{max(0.0,min(100.0,(p.confidence_high-p.confidence_low)/max(p.adjusted_value,1)*100)):.0f}%")
        console.print(t)

    def print_value_movers(self, player_values: dict[str, PlayerValue]) -> None:
        vals = list(player_values.values())
        risers = sorted(vals, key=lambda x: x.trend_30d, reverse=True)[:10]
        fallers = sorted(vals, key=lambda x: x.trend_30d)[:10]
        pr = Table(title="Risers")
        pf = Table(title="Fallers")
        for tb in [pr, pf]:
            tb.add_column("Name")
            tb.add_column("Trend")
            tb.add_column("Momentum")
        for p in risers:
            pr.add_row(p.name, f"↑ {p.trend_30d:+d}", f"{(p.trend_30d/max(p.adjusted_value,1))*100:.2f}%")
        for p in fallers:
            pf.add_row(p.name, f"↓ {p.trend_30d:+d}", f"{(p.trend_30d/max(p.adjusted_value,1))*100:.2f}%")
        console.print(Columns([pr, pf]))

    def print_buy_sell_targets(self, buy_low: list[dict], sell_high: list[dict]) -> None:
        bs = Table(title="Buy Low")
        ss = Table(title="Sell High")
        for tb in [bs, ss]:
            tb.add_column("Name")
            tb.add_column("Owner")
            tb.add_column("Score")
            tb.add_column("Current")
            tb.add_column("Future")
        for b in buy_low:
            bs.add_row(b["name"], b.get("owner", "-"), f"{b['score']:.2f}", f"{b['current']:,.0f}", f"{b['future']:,.0f}")
        for s in sell_high:
            ss.add_row(s["name"], "Me", f"{s['score']:.2f}", f"{s['current']:,.0f}", f"{s['future']:,.0f}")
        console.print(Columns([bs, ss]))

    def print_trade_recommendations(self, recs: list[TradeScore], top_n: int) -> None:
        for i, r in enumerate(recs[:top_n], 1):
            left = "\n".join([f"{p.name} ({p.position}) {p.adjusted_value:,.0f} FVS:{p.fvs:.1f}" for p in r.send_assets])
            right = "\n".join([f"{p.name} ({p.position}) {p.adjusted_value:,.0f} FVS:{p.fvs:.1f}" for p in r.receive_assets])
            why = "Sell aging asset for stronger long-term trajectory." if r.future_value_delta > 0 else "Win current value while preserving depth."
            panel = Panel(Columns([Panel(left, title="YOU SEND", border_style="red"), Panel(right, title="YOU RECEIVE", border_style="green")]), title=f"#{i} vs {r.opponent} | +{r.raw_value_gain:,.0f} | plausibility {r.plausibility_score*100:.0f}%\nWHY: {why}")
            console.print(panel)

    def print_positional_needs_heatmap(self, all_rosters: list[RosterProfile]) -> None:
        t = Table(title="Positional Need Heatmap")
        t.add_column("Team")
        for p in ["QB", "RB", "WR", "TE"]:
            t.add_column(p)
        for r in all_rosters:
            vals = []
            for p in ["QB", "RB", "WR", "TE"]:
                n = r.positional_needs.get(p, 0.5)
                color = "green" if n < 0.3 else "yellow" if n < 0.6 else "red"
                vals.append(f"[{color}]{n:.2f}[/{color}]")
            t.add_row(r.owner_name, *vals)
        console.print(t)


def compute_fvs_tier(v: float) -> str:
    if v >= 85:
        return "Elite"
    if v >= 70:
        return "Rising"
    if v >= 55:
        return "Stable"
    if v >= 40:
        return "Declining"
    return "Fading"


def export_analysis(my_roster: RosterProfile, all_rosters: list[RosterProfile], trade_recs: list[TradeScore], buy_low: list[dict], sell_high: list[dict], player_values: dict[str, PlayerValue], resolver: NameResolver, meta: dict, username: str, source_status: dict[str, bool]) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    file = f"dynasty_analysis_{ts}.json"
    risers = sorted(player_values.values(), key=lambda x: x.trend_30d, reverse=True)[:15]
    fallers = sorted(player_values.values(), key=lambda x: x.trend_30d)[:15]
    payload = {
        "meta": {
            "generated_at": datetime.now(UTC).isoformat(),
            "username": username,
            "league_name": meta["league_name"],
            "season": meta["season"],
            "league_id": meta["league_id"],
            "is_superflex": meta["is_superflex"],
            "ppr": meta["ppr"],
            "data_sources": source_status,
        },
        "my_roster": {
            "grade": my_roster.roster_grade,
            "window": my_roster.window,
            "total_value": my_roster.total_value,
            "total_fvs": my_roster.total_fvs,
            "avg_age_starters": my_roster.avg_age_starters,
            "players": [asdict(x) for x in my_roster.players],
        },
        "league_rankings": [{"owner": r.owner_name, "total_value": r.total_value, "total_fvs": r.total_fvs, "grade": r.roster_grade, "window": r.window} for r in all_rosters],
        "trade_recommendations": [asdict(x) for x in trade_recs],
        "buy_low_targets": buy_low,
        "sell_high_targets": sell_high,
        "name_resolution_log": resolver.resolution_log,
        "value_movers_30d": {"risers": [asdict(x) for x in risers], "fallers": [asdict(x) for x in fallers]},
    }
    Path(file).write_text(json.dumps(payload, indent=2, default=str))
    return file


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--username")
    p.add_argument("--season", default="2025")
    p.add_argument("--min-gain", type=float, default=250)
    p.add_argument("--max-send", type=int, default=3)
    p.add_argument("--top", type=int, default=25)
    p.add_argument("--no-cache", action="store_true")
    p.add_argument("--clear-cache", action="store_true")
    p.add_argument("--export", action="store_true")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--mock", action="store_true")
    p.add_argument("--age-method", choices=["exponential", "gompertz", "logistic"], default="gompertz")
    p.add_argument("--projection-years", default="1,2,3,5")
    p.add_argument("--self-test", action="store_true")
    return p.parse_args()


def _grade(roster: RosterProfile, avg_val: float, avg_fvs: float) -> tuple[str, str, str, float]:
    val = roster.total_value / max(avg_val, 1)
    fvs = roster.total_fvs / max(avg_fvs, 1)
    pos_bal = 1 - float(np.mean(list(roster.positional_needs.values())))
    starter_bench = roster.starter_value / max(roster.total_value, 1)
    picks = roster.pick_value / max(avg_val * 0.2, 1)
    score = 100 * (0.30 * val + 0.25 * fvs + 0.20 * pos_bal + 0.15 * starter_bench + 0.10 * picks)
    if score >= 95:
        grade = "A+"
    elif score >= 88:
        grade = "A"
    elif score >= 81:
        grade = "B+"
    elif score >= 73:
        grade = "B"
    elif score >= 66:
        grade = "C+"
    elif score >= 58:
        grade = "C"
    else:
        grade = "D"
    window_score = 100 * (0.40 * val + 0.35 * (1 - (roster.avg_age_starters - 22) / 18) + 0.25 * fvs)
    if val > 1.1 and roster.avg_age_starters < 26.5 and fvs > 1.0:
        window = "Championship Window"
    elif val > 1.0:
        window = "Contender"
    elif fvs > 1.0 and roster.avg_age_starters < 25.0:
        window = "Rebuilding"
    else:
        window = "Full Rebuild"
    return grade, f"Composite score {score:.1f} driven by value/future balance.", window, window_score


def run_self_test() -> int:
    res = []
    res.append(("RB peak", age_multiplier("RB", 24, "gompertz") >= age_multiplier("RB", 28, "gompertz")))
    res.append(("QB near-peak", age_multiplier("QB", 28, "gompertz") >= age_multiplier("QB", 22, "gompertz")))
    pr = FutureValueProjector("gompertz", [1, 2, 3, 5])
    mock_wr = {"position": "WR", "age": 26, "years_exp": 4, "trend_30d": 50}
    mock_rb = {"position": "RB", "age": 21, "years_exp": 1, "trend_30d": 20}
    res.append(("WR decline", pr.project_player(mock_wr, 5000, 3)["projected_value"] < 5000))
    res.append(("RB horizon", pr.project_player(mock_rb, 4000, 2)["projected_value"] > pr.project_player(mock_rb, 4000, 4)["projected_value"]))
    resolver = NameResolver()
    res.append(("Suffix match", resolver.resolve("Patrick Mahomes", {"Patrick Mahomes II": 9000}) == "Patrick Mahomes II"))
    te = TradeEngine(RosterProfile(1, "me"), [RosterProfile(2, "opp")], argparse.Namespace(max_send=3, min_gain=250, top=10))
    p1 = PlayerValue("1", "A", "RB", "X", 25, 3, None, None, None, None, 0, 0, 1, None, 1000, "", 0, 0)
    p2 = PlayerValue("2", "B", "WR", "Y", 25, 3, None, None, None, None, 0, 0, 1, None, 600, "", 0, 0)
    res.append(("Plausibility floor", te.compute_plausibility([p1], [p2], RosterProfile(2, "opp")) == 0.0))
    ok = True
    for n, p in res:
        console.print(f"{'[green]PASS[/green]' if p else '[red]FAIL[/red]'} {n}")
        ok &= p
    return 0 if ok else 1


def main() -> int:
    args = parse_args()
    CONFIG["age_curve_method"] = args.age_method
    proj_years = [int(x.strip()) for x in args.projection_years.split(",") if x.strip()]
    cache = CacheManager(ttl_hours=CONFIG["cache_ttl_hours"], enabled=not args.no_cache)
    if args.clear_cache:
        cache.clear()
        return 0
    if args.self_test:
        return run_self_test()
    username = args.username or Prompt.ask("Sleeper username")
    http = HttpClient(verbose=args.verbose, mock_mode=args.mock, cache=cache)
    resolver = NameResolver()
    source_status = {"sleeper": True, "fantasycalc": True, "ktc": True}
    sleeper = SleeperClient(http, cache)
    user = sleeper.get_user(username)
    leagues = sleeper.get_leagues(user["user_id"], args.season)
    if not leagues:
        raise ValueError("No dynasty leagues found.")
    league = sleeper.select_league(leagues)
    meta = sleeper.get_league_metadata(league)
    rosters = sleeper.get_rosters(meta["league_id"])
    users = http.get(f"https://api.sleeper.app/v1/league/{meta['league_id']}/users", source_name="Sleeper")
    owner_map = {int(r["roster_id"]): next((u.get("display_name", "Unknown") for u in users if u.get("user_id") == r.get("owner_id")), f"Roster {r['roster_id']}") for r in rosters}
    traded_picks = sleeper.get_traded_picks(meta["league_id"])
    draft_picks = sleeper.get_draft_picks(meta["league_id"])
    all_players = sleeper.get_all_players(cache)
    with ThreadPoolExecutor(max_workers=2) as pool:
        fc_future = pool.submit(FantasyCalcClient(http, cache).fetch_values, meta["is_superflex"], meta["ppr"], meta["num_teams"])
        ktc_future = pool.submit(KTCClient(http, cache).fetch_values, meta["is_superflex"])
        try:
            fc_data = fc_future.result()
        except Exception:
            source_status["fantasycalc"] = False
            fc_data = []
        try:
            ktc_data = ktc_future.result()
        except Exception:
            source_status["ktc"] = False
            ktc_data = []
    ve = ValueEngine(resolver, fc_data, ktc_data, all_players, meta)
    player_values = ve.build_consensus()
    pick_values = build_pick_values(fc_data, meta, traded_picks, draft_picks)
    projector = FutureValueProjector(args.age_method, proj_years)
    scale_vals = [p.adjusted_value for p in player_values.values()] or [1]
    for p in player_values.values():
        projs = {y: projector.project_player(p, p.adjusted_value, y) for y in [1, 2, 3, 5]}
        p.future_value_1yr = projs[1]["projected_value"]
        p.future_value_2yr = projs[2]["projected_value"]
        p.future_value_3yr = projs[3]["projected_value"]
        p.future_value_5yr = projs[5]["projected_value"]
        p.fvs = projector.compute_future_value_score(projs, scale_vals)
        p.fvs_tier = compute_fvs_tier(p.fvs)
        p.confidence_low = projs[1]["confidence_low"]
        p.confidence_high = projs[1]["confidence_high"]
    analyzer = RosterAnalyzer(player_values, meta, owner_map)
    profiles = [analyzer.analyze_roster(r, pick_values) for r in rosters]
    avg_val = float(np.mean([r.total_value for r in profiles])) if profiles else 1
    avg_fvs = float(np.mean([r.total_fvs for r in profiles])) if profiles else 1
    for rp in profiles:
        g, reason, window, ws = _grade(rp, avg_val, avg_fvs)
        rp.roster_grade, rp.grade_reasoning, rp.window, rp.window_score = g, reason, window, ws
    for i, rp in enumerate(sorted(profiles, key=lambda x: x.total_fvs, reverse=True), 1):
        rp.fvs_rank = i
    my = next((r for r in profiles if r.owner_name.lower() == username.lower()), profiles[0])
    args.min_gain = args.min_gain
    trade_engine = TradeEngine(my, profiles, args)
    recs = trade_engine.generate_recommendations()
    buy, sell = trade_engine.compute_buy_sell_targets()
    d = Display()
    d.print_header(meta["league_name"])
    d.print_roster(my)
    d.print_future_value_projections(my)
    d.print_league_rankings(profiles, my.owner_name)
    d.print_positional_needs_heatmap(profiles)
    d.print_value_movers(player_values)
    d.print_buy_sell_targets(buy, sell)
    d.print_trade_recommendations(recs, args.top)
    if args.export:
        path = export_analysis(my, profiles, recs, buy, sell, player_values, resolver, meta, username, source_status)
        console.print(f"[green]Exported analysis to {path}[/green]")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        console.print("[yellow]Exiting gracefully.[/yellow]")
        raise SystemExit(0)
    except DataSourceError as exc:
        console.print(f"[yellow]Data source issue: {exc.source_name} {exc.url} status={exc.status_code}[/yellow]")
        raise SystemExit(0)
    except Exception:
        console.print("[red]Unhandled exception:[/red]")
        console.print(traceback.format_exc())
        raise SystemExit(1)
