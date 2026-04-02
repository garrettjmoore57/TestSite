#!/usr/bin/env python3
"""Streamlit web app for Dynasty Future Value Analyzer."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import streamlit as st

# ── page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="FFPredict | Dynasty Analyzer",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── import core logic from original script ────────────────────────────────────
from dynasty_custom_score import (  # noqa: E402
    apply_custom_scores_to_player_values,
    projection_curve_label,
    roster_action_label,
)
from fantasy_trade_analyzer import (  # noqa: E402
    CONFIG,
    CacheManager,
    FantasyCalcClient,
    FutureValueProjector,
    HttpClient,
    KTCClient,
    NameResolver,
    RosterAnalyzer,
    SleeperClient,
    TradeEngine,
    ValueEngine,
    _grade,
    build_pick_values,
    compute_fvs_tier,
)

# ── custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    :root {
      --ff-bg: #0b0b0c;
      --ff-panel: #141416;
      --ff-orange: #ff6a00;
      --ff-orange-dim: #cc5500;
      --ff-text: #f4f4f5;
      --ff-muted: #a1a1aa;
    }
    .stApp { background: var(--ff-bg); color: var(--ff-text); }
    [data-testid="stSidebar"] {
      background: linear-gradient(180deg, #0e0e10 0%, #0a0a0b 100%);
      border-right: 1px solid #222;
    }
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: var(--ff-orange); }
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] label { color: var(--ff-muted); }
    .block-container { padding-top: 1.25rem; max-width: 1280px; }
    h1, h2, h3 { color: var(--ff-text) !important; letter-spacing: -0.02em; }
    div[data-testid="stDecoration"] { background: var(--ff-orange); }
    .stTabs [data-baseweb="tab"] {
        font-size: 0.85rem;
        font-weight: 700;
        padding: 10px 14px;
        color: var(--ff-muted);
    }
    .stTabs [aria-selected="true"] { color: var(--ff-orange) !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 4px; background: var(--ff-panel); border-radius: 8px; padding: 4px; }
    .trade-block {
        background: var(--ff-panel);
        border: 1px solid #2a2a2e;
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        box-shadow: 0 8px 24px rgba(0,0,0,0.35);
    }
    @media (max-width: 768px) {
      .block-container { padding-left: 1rem !important; padding-right: 1rem !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏈 FFPredict")
    st.caption("Dynasty Future Value Analyzer")
    st.divider()

    st.markdown("### League Settings")
    username = st.text_input("Sleeper Username", placeholder="your_sleeper_username")
    season = st.selectbox("Season", ["2026", "2025", "2024"])

    st.divider()
    st.markdown("### Analysis Settings")
    min_gain = st.slider(
        "Min Value Gain",
        min_value=0,
        max_value=1000,
        value=250,
        step=50,
        help="Minimum value gain required to surface a trade suggestion",
    )
    max_send = st.slider("Max Assets to Send", 1, 4, 3)
    top_n = st.slider("Top N Trades", 5, 50, 25, 5)
    age_method = st.selectbox(
        "Age Curve Method",
        ["gompertz", "exponential", "logistic"],
        help="Gompertz models the asymmetric NFL career arc best",
    )
    clear_cache = st.checkbox(
        "Force fresh data",
        help="Clears the HTTP cache and re-fetches everything from source APIs",
    )

    st.divider()
    analyze_btn = st.button("🔍 Analyze My Team", type="primary", width="stretch")

# ── session state init ────────────────────────────────────────────────────────
for key in ("leagues", "data", "state", "user_id"):
    if key not in st.session_state:
        st.session_state[key] = None


def _trim_fc_history_for_sparkline(raw: list[dict], days: int = 28, max_points: int = 10) -> list[dict]:
    """Turn FantasyCalc daily history into a short series for charts (~last month)."""
    if not raw:
        return []
    rows: list[dict[str, float | str]] = []
    for x in raw:
        d_raw, v = x.get("date"), x.get("value")
        if d_raw is None or v is None:
            continue
        ds = str(d_raw)[:10]
        try:
            rows.append({"date": ds, "value": float(v)})
        except (TypeError, ValueError):
            continue
    rows.sort(key=lambda r: str(r["date"]))
    cutoff = (datetime.now(UTC) - timedelta(days=days)).date().isoformat()
    rows = [r for r in rows if str(r["date"]) >= cutoff]
    if len(rows) > max_points:
        step = max(1, len(rows) // max_points)
        rows = rows[::step]
    return rows[-max_points:]


# ── analysis helper ───────────────────────────────────────────────────────────

def do_analysis(
    uname: str,
    user_id: str,
    ssn: str,
    league: dict,
    min_g: float,
    max_s: int,
    top: int,
    method: str,
) -> dict:
    """Run the full analysis pipeline and return a results dict."""
    CONFIG["age_curve_method"] = method

    cache = CacheManager(ttl_hours=CONFIG["cache_ttl_hours"])
    http = HttpClient(cache=cache)
    resolver = NameResolver()
    source_status = {"sleeper": True, "fantasycalc": True, "ktc": True}

    sleeper = SleeperClient(http, cache)
    meta = sleeper.get_league_metadata(league)

    rosters = sleeper.get_rosters(meta["league_id"])
    users_raw = http.get(
        f"https://api.sleeper.app/v1/league/{meta['league_id']}/users",
        source_name="Sleeper",
    )
    owner_map = {
        int(r["roster_id"]): next(
            (u.get("display_name", "Unknown") for u in users_raw if u.get("user_id") == r.get("owner_id")),
            f"Roster {r['roster_id']}",
        )
        for r in rosters
    }

    traded_picks = sleeper.get_traded_picks(meta["league_id"])
    draft_picks = sleeper.get_draft_picks(meta["league_id"])
    all_players = sleeper.get_all_players(cache)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fc_client = FantasyCalcClient(http, cache)
        ktc_client = KTCClient(http, cache)
        fc_fut = pool.submit(fc_client.fetch_values, meta["is_superflex"], meta["ppr"], meta["num_teams"])
        ktc_fut = pool.submit(ktc_client.fetch_values, meta["is_superflex"])
        try:
            fc_data = fc_fut.result()
        except Exception:
            source_status["fantasycalc"] = False
            fc_data = []
        try:
            ktc_data = ktc_fut.result()
        except Exception:
            source_status["ktc"] = False
            ktc_data = []

    ve = ValueEngine(resolver, fc_data, ktc_data, all_players, meta)
    player_values = ve.build_consensus()
    pick_values = build_pick_values(fc_data, meta, traded_picks, draft_picks)

    projector = FutureValueProjector(method, [1, 2, 3, 5])
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

    avg_val = float(np.mean([r.total_value for r in profiles])) if profiles else 1.0
    avg_fvs = float(np.mean([r.total_fvs for r in profiles])) if profiles else 1.0

    for rp in profiles:
        g, reason, window, ws = _grade(rp, avg_val, avg_fvs)
        rp.roster_grade, rp.grade_reasoning, rp.window, rp.window_score = g, reason, window, ws

    for i, rp in enumerate(sorted(profiles, key=lambda x: x.total_fvs, reverse=True), 1):
        rp.fvs_rank = i

    # Match by owner_id (user_id), not display name — the two differ for many users
    my_roster_id = next(
        (int(r["roster_id"]) for r in rosters if r.get("owner_id") == user_id),
        None,
    )
    my = next(
        (rp for rp in profiles if rp.roster_id == my_roster_id),
        profiles[0],
    )

    # Rules-based 0–100 dynasty score (age, trend, team, draft capital, injury)
    apply_custom_scores_to_player_values(player_values, all_players)

    sparklines: dict[str, list[dict]] = {}
    fc_hist = FantasyCalcClient(http, cache)

    def _fetch_spark(pid: str) -> tuple[str, list[dict]]:
        hist = fc_hist.fetch_historical_trend_cached(pid)
        return pid, _trim_fc_history_for_sparkline(hist)

    roster_ids = [p.id for p in my.players]
    if roster_ids:
        with ThreadPoolExecutor(max_workers=min(8, len(roster_ids))) as spark_pool:
            for pid, series in spark_pool.map(_fetch_spark, roster_ids):
                if series:
                    sparklines[pid] = series

    ns = argparse.Namespace(max_send=max_s, min_gain=min_g, top=top)
    engine = TradeEngine(my, profiles, ns)
    recs = engine.generate_recommendations()
    buy, sell = engine.compute_buy_sell_targets()

    return {
        "meta": meta,
        "my": my,
        "profiles": profiles,
        "recs": recs,
        "buy": buy,
        "sell": sell,
        "player_values": player_values,
        "source_status": source_status,
        "all_players": all_players,
        "rosters": rosters,
        "sparklines": sparklines,
    }


# ── main header ───────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='margin-bottom:0.2rem;'>FFPredict <span style='color:#ff6a00;'>Dynasty</span> Lab</h1>",
    unsafe_allow_html=True,
)
st.caption(
    f"Market data: KTC (sentiment) · FantasyCalc (executed) · **DScore** = custom 0–100 dynasty rules  |  "
    f"{datetime.now().strftime('%B %d, %Y')}"
)

# ── step 1: fetch leagues when "Analyze" clicked ──────────────────────────────
if analyze_btn:
    if not username.strip():
        st.warning("Please enter your Sleeper username in the sidebar.")
        st.stop()

    st.session_state.data = None

    if clear_cache:
        CacheManager().clear()
        st.toast("Cache cleared — fetching fresh data.", icon="🗑️")

    with st.spinner("Looking up your Sleeper leagues…"):
        try:
            _cache = CacheManager()
            _http = HttpClient(cache=_cache)
            _sleeper = SleeperClient(_http, _cache)
            _user = _sleeper.get_user(username.strip())
            _leagues = _sleeper.get_leagues(_user["user_id"], season)
            st.session_state.leagues = _leagues
            st.session_state.user_id = _user["user_id"]
        except Exception as exc:
            st.error(f"Could not load leagues: {exc}")
            st.stop()

    if not st.session_state.leagues:
        st.warning(
            "No dynasty leagues found. "
            "Check your username and make sure you have dynasty leagues in the selected season."
        )
        st.stop()

    # Auto-run immediately when only one league exists
    if len(st.session_state.leagues) == 1:
        with st.spinner("Running analysis — this may take 20–40 s on first run…"):
            try:
                st.session_state.data = do_analysis(
                    username.strip(), st.session_state.user_id, season,
                    st.session_state.leagues[0], min_gain, max_send, top_n, age_method,
                )
            except Exception as exc:
                st.error(f"Analysis failed: {exc}")
                st.stop()

# ── step 2: league picker (multiple leagues) ──────────────────────────────────
if st.session_state.leagues and len(st.session_state.leagues) > 1 and not st.session_state.data:
    leagues = st.session_state.leagues
    league_names = [lg.get("name", f"League {i + 1}") for i, lg in enumerate(leagues)]
    chosen = st.selectbox("Select your dynasty league:", league_names)
    league_idx = league_names.index(chosen)

    if st.button("Run Analysis on Selected League", type="primary"):
        with st.spinner("Running analysis — this may take 20–40 s on first run…"):
            try:
                st.session_state.data = do_analysis(
                    username.strip(), st.session_state.user_id, season,
                    leagues[league_idx], min_gain, max_send, top_n, age_method,
                )
            except Exception as exc:
                st.error(f"Analysis failed: {exc}")
                st.stop()

# ── no data yet: show intro ───────────────────────────────────────────────────
if not st.session_state.data:
    st.info(
        "Enter your **Sleeper username** in the sidebar and click **Analyze My Team** to get started.",
        icon="👈",
    )
    with st.expander("What does this app do?"):
        st.markdown(
            """
            **FFPredict** is a model-vs-market decision engine for dynasty fantasy football.

            It separates two things most tools blend together:

            | Layer | What it is |
            |---|---|
            | **Market Price** | What KTC + FantasyCalc say a player trades for right now |
            | **Intrinsic Value** | What a 3-year present-value model says the player is actually worth |

            **The spread between them** — intrinsic minus market — is your edge signal:
            - 📈 **Positive spread** → model thinks the market is underpricing the player (buy candidate)
            - 📉 **Negative spread** → model thinks the market is overpricing the player (sell candidate)

            #### Data sources
            - **KTC (KeepTradeCut)** — community sentiment: what people *say* players are worth
            - **FantasyCalc** — executed prices: what people actually *pay* in completed trades

            Neither source is treated as ground truth. Both feed the market layer only.
            KTC vs FC disagreement is surfaced as a context signal, not used to boost or penalise scores.

            #### Intrinsic model
            Uses a 3-year present-value formula:
            ```
            V = Σ  age_mult(age+t) × survival(pos, age, t) × role_persistence(rank, t)
                    ─────────────────────────────────────────────────────────────────
                                        (1 + 12 %)^t
            ```
            - Age curves follow Gompertz career-arc fitting by position
            - Survival probability accounts for position and age relative to peak
            - Role persistence reflects current rank in position
            - Uncertainty bands come from Monte Carlo simulation

            #### Outputs
            - 📋 Roster breakdown with Market Price / Intrinsic Value / Spread per player
            - 🏆 League power rankings
            - 🔄 Trade recommendations ranked by composite score
            - 📈 Buy / Sell targets based on model-vs-market spread
            - 📉 30-day value movers
            - 🔮 1, 2, 3, 5-year forward projections
            - 🗺️ Positional needs heatmap
            """
        )
    st.stop()

# ── render results ────────────────────────────────────────────────────────────
data = st.session_state.data
meta = data["meta"]
my = data["my"]
profiles = data["profiles"]
recs = data["recs"]
buy = data["buy"]
sell = data["sell"]
player_values = data["player_values"]
source_status = data["source_status"]
sparklines = data.get("sparklines") or {}
league_rosters = data.get("rosters") or []

# ── top summary bar ───────────────────────────────────────────────────────────
st.subheader(f"📊 {meta['league_name']}")

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Roster Grade", my.roster_grade)
c2.metric("Total Value", f"{my.total_value:,.0f}")
c3.metric("FVS Score", f"{my.total_fvs:.1f}")
c4.metric("Avg Starter Age", f"{my.avg_age_starters:.1f}")
c5.metric("Window", my.window)
c6.metric("Teams", meta["num_teams"])

src_icons = " · ".join(
    f"{'✅' if ok else '⚠️'} {name.upper()}" for name, ok in source_status.items()
)
league_flags = []
if meta.get("is_superflex"):
    league_flags.append("Superflex")
if meta.get("is_2qb"):
    league_flags.append("2QB")
ppr_label = {1.0: "Full PPR", 0.5: "Half PPR", 0.0: "Standard"}.get(meta.get("ppr", 1.0), "PPR")
league_flags.append(ppr_label)
st.caption(f"Data: {src_icons}  |  Format: {' · '.join(league_flags)}")

# Show warning if KTC is unavailable
if not source_status.get("ktc"):
    st.warning(
        "⚠️ **KTC data unavailable** (network issue, rate-limited, or site blocked).  "
        "Market prices are using **FantasyCalc only**. Intrinsic model unaffected.  "
        "Try again in 24h or check your internet connection.",
        icon="⚠️",
    )

st.divider()

# ── tabs ──────────────────────────────────────────────────────────────────────
(
    tab_roster,
    tab_trade_compare,
    tab_waiver,
    tab_league,
    tab_trades,
    tab_buysell,
    tab_movers,
    tab_future,
    tab_needs,
) = st.tabs([
    "📋 Dashboard",
    "⚖️ Trade Analyzer",
    "💎 Waiver Gems",
    "🏆 League Rankings",
    "🔄 Trade Ideas",
    "📈 Buy / Sell",
    "📉 Value Movers",
    "🔮 Future Projections",
    "🗺️ Positional Needs",
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB: MY ROSTER
# ─────────────────────────────────────────────────────────────────────────────
with tab_roster:
    st.subheader(f"Roster: {my.owner_name}")

    r1, r2, r3, r4, r5 = st.columns(5)
    r1.metric("QB Value", f"{my.qb_value:,.0f}")
    r2.metric("RB Value", f"{my.rb_value:,.0f}")
    r3.metric("WR Value", f"{my.wr_value:,.0f}")
    r4.metric("TE Value", f"{my.te_value:,.0f}")
    r5.metric("Pick Value", f"{my.pick_value:,.0f}")

    st.caption(
        "**DScore** = our 0–100 dynasty score (age, usage trend, team, rookie draft round, injury).  "
        "**Market** = KTC + FantasyCalc.  **Intrinsic** = 3-yr PV model.  "
        "**Action** = BUY / HOLD / SELL from model spread + DScore heuristics."
    )

    players_sorted = sorted(
        my.players,
        key=lambda x: (x.custom_dynasty_score, x.adjusted_value),
        reverse=True,
    )

    roster_rows = [
        {
            "#": i,
            "Name": p.name,
            "Pos": p.position,
            "Team": p.team,
            "Age": round(p.age, 1) if p.age else None,
            "DScore": round(p.custom_dynasty_score, 1),
            "Action": roster_action_label(p.buy_signal, p.sell_signal, p.custom_dynasty_score, p.trend_30d),
            "Market": int(p.adjusted_value),
            "Intrinsic": int(p.intrinsic_value) if p.intrinsic_value else "—",
            "Spread %": f"{p.spread_pct:+.1f}%" if p.spread_pct else "—",
            "+1yr": int(p.future_value_1yr),
            "+2yr": int(p.future_value_2yr),
            "+3yr": int(p.future_value_3yr),
            "FVS": round(p.fvs, 1),
            "Tier": p.tier,
            "30d": p.trend_30d,
        }
        for i, p in enumerate(players_sorted, 1)
    ]

    df_roster = pd.DataFrame(roster_rows)

    def _color_tier(val: str) -> str:
        return {
            "Elite": "background-color:#5c2e00; color:#ffb547",
            "Star": "background-color:#2a2a2a; color:#e4e4e7",
            "Starter": "background-color:#1a3a1a; color:#86efac",
            "Flex": "background-color:#1a253a; color:#93c5fd",
            "Depth": "background-color:#3a2a10; color:#fdba74",
            "Stash": "background-color:#27272a; color:#a1a1aa",
        }.get(val, "")

    def _color_trend(val: int) -> str:
        if val > 0:
            return "color:#4ade80; font-weight:bold"
        if val < 0:
            return "color:#f87171; font-weight:bold"
        return ""

    def _color_action_cell(val: str) -> str:
        if val == "BUY":
            return "background-color:#14532d; color:#86efac; font-weight:700"
        if val == "SELL":
            return "background-color:#450a0a; color:#fca5a5; font-weight:700"
        return "background-color:#3f3f0f; color:#facc15; font-weight:600"

    styled_roster = (
        df_roster.style
        .map(_color_tier, subset=["Tier"])
        .map(_color_trend, subset=["30d"])
        .map(_color_action_cell, subset=["Action"])
    )
    st.dataframe(styled_roster, width="stretch", hide_index=True)

    st.subheader("4-week value trends (FantasyCalc)")
    st.caption("Short sparklines from recent market clears — scroll in each chart on mobile.")
    if not sparklines:
        st.info("Charts load after analysis fetches history (one request per roster player, cached).", icon="📈")
    else:
        n = len(players_sorted)
        for row_start in range(0, n, 2):
            c_left, c_right = st.columns(2)
            for col, idx in zip([c_left, c_right], [row_start, row_start + 1]):
                if idx >= n:
                    break
                pl = players_sorted[idx]
                ser = sparklines.get(pl.id, [])
                with col:
                    st.markdown(f"**{pl.name}** · {pl.position} · DScore {pl.custom_dynasty_score:.0f}")
                    if ser:
                        sdf = pd.DataFrame(ser)
                        st.line_chart(sdf.set_index("date"), height=120)
                    else:
                        st.caption("No recent history")

    if my.picks:
        st.subheader("Draft Picks")
        pick_rows = [
            {
                "Pick": p.name,
                "Year": p.year,
                "Round": p.round,
                "Tier": p.tier,
                "Value": int(p.adjusted_value),
                "Expected EV": int(p.expected_ev),
            }
            for p in sorted(my.picks, key=lambda x: x.adjusted_value, reverse=True)
        ]
        st.dataframe(pd.DataFrame(pick_rows), width="stretch", hide_index=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB: TRADE ANALYZER (side-by-side packages)
# ─────────────────────────────────────────────────────────────────────────────
with tab_trade_compare:
    st.subheader("Trade Analyzer")
    st.caption(
        "Pick players on each side (names must match the app’s player list).  "
        "We compare **DScore**, **market** totals, and **future** columns (+1 / +2 / +3 years)."
    )
    by_name = {pv.name: pv for pv in player_values.values()}
    all_names = sorted(by_name.keys())
    side_a = st.multiselect("Your side (2–4 players)", all_names, max_selections=4)
    side_b = st.multiselect("Their side (2–4 players)", all_names, max_selections=4)

    if st.button("Compare trade", type="primary"):
        if len(side_a) < 2 or len(side_b) < 2:
            st.warning("Choose at least **two** players on **each** side (per your workflow).")
        elif set(side_a) & set(side_b):
            st.warning("A player cannot appear on both sides.")
        else:
            pa = [by_name[n] for n in side_a]
            pb = [by_name[n] for n in side_b]

            def _pack_rows(players: list, label: str) -> list[dict]:
                out = []
                for p in players:
                    out.append({
                        "Side": label,
                        "Name": p.name,
                        "Pos": p.position,
                        "Age": round(p.age, 1) if p.age else None,
                        "DScore": round(p.custom_dynasty_score, 1),
                        "Market": int(p.adjusted_value),
                        "2yr curve": projection_curve_label(p.adjusted_value, p.future_value_2yr),
                        "+1yr": int(p.future_value_1yr),
                        "+2yr": int(p.future_value_2yr),
                        "+3yr": int(p.future_value_3yr),
                    })
                return out

            left_df = pd.DataFrame(_pack_rows(pa, "You"))
            right_df = pd.DataFrame(_pack_rows(pb, "Them"))
            c_a, c_b = st.columns(2)
            with c_a:
                st.markdown("**You send**")
                st.dataframe(left_df, width="stretch", hide_index=True)
            with c_b:
                st.markdown("**You receive**")
                st.dataframe(right_df, width="stretch", hide_index=True)

            sum_mkt_a = sum(p.adjusted_value for p in pa)
            sum_mkt_b = sum(p.adjusted_value for p in pb)
            sum_ds_a = sum(p.custom_dynasty_score for p in pa)
            sum_ds_b = sum(p.custom_dynasty_score for p in pb)
            sum_2_a = sum(p.future_value_2yr for p in pa)
            sum_2_b = sum(p.future_value_2yr for p in pb)
            delta_mkt = sum_mkt_b - sum_mkt_a
            delta_ds = sum_ds_b - sum_ds_a
            delta_2 = sum_2_b - sum_2_a
            pct = 100.0 * delta_mkt / max(sum_mkt_a, 1.0)

            st.divider()
            verdict_box = st.container()
            with verdict_box:
                if abs(delta_mkt) < 150 and abs(delta_ds) < 8:
                    verdict = "**Even-ish trade** on both market and DScore — preference comes down to roster construction."
                    winner = "Toss-up"
                elif delta_mkt > 0 and delta_ds >= 0:
                    verdict = "**You win on paper** on current market and DScore totals — nice upside if the market is efficient."
                    winner = "You"
                elif delta_mkt < 0 and delta_ds <= 0:
                    verdict = "**They win on paper** on market and DScore — be sure you are buying a narrative the model does not see."
                    winner = "Them"
                elif delta_mkt > 0 > delta_ds:
                    verdict = "**You gain market now** but give up DScore — classic stars-for-youth / win-now tilt."
                    winner = "You (market) / Them (DScore)"
                else:
                    verdict = "**You sacrifice some market** but gain DScore — rebuild / futures tilt."
                    winner = "Them (market) / You (DScore)"

                st.markdown(f"### Verdict: {winner}")
                st.markdown(verdict)
                st.metric("Market surplus (receive − send)", f"{delta_mkt:+,.0f} pts", f"{pct:+.1f}% vs your outgoing")
                st.caption(
                    f"DScore delta (receive − send): **{delta_ds:+.1f}**  ·  "
                    f"+2yr projected market delta: **{delta_2:+,.0f}**"
                )

# ─────────────────────────────────────────────────────────────────────────────
# TAB: WAIVER GEMS (unrostered in this league)
# ─────────────────────────────────────────────────────────────────────────────
with tab_waiver:
    st.subheader("Waiver wire gems")
    st.caption("Players valued in this league’s market who are **not** on any roster (including taxi/IR).")
    rostered_ids: set[str] = set()
    for r in league_rosters:
        for key in ("players", "taxi", "reserve"):
            for pid in r.get(key) or []:
                rostered_ids.add(str(pid))
    min_w = st.slider("Minimum market value to show", 200, 4000, 500, 50)
    gems = [pv for pid, pv in player_values.items() if pid not in rostered_ids and pv.adjusted_value >= min_w]
    gems.sort(key=lambda x: (x.custom_dynasty_score, x.adjusted_value), reverse=True)
    if not gems:
        st.info("No unrostered players met that threshold — lower the minimum or check league rosters.")
    else:
        gem_rows = [
            {
                "Name": g.name,
                "Pos": g.position,
                "Team": g.team,
                "Age": round(g.age, 1) if g.age else None,
                "DScore": round(g.custom_dynasty_score, 1),
                "Market": int(g.adjusted_value),
                "+1yr": int(g.future_value_1yr),
                "+2yr": int(g.future_value_2yr),
                "+3yr": int(g.future_value_3yr),
                "2yr curve": projection_curve_label(g.adjusted_value, g.future_value_2yr),
            }
            for g in gems[:80]
        ]
        st.dataframe(pd.DataFrame(gem_rows), width="stretch", hide_index=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB: LEAGUE RANKINGS
# ─────────────────────────────────────────────────────────────────────────────
with tab_league:
    st.subheader("League Power Rankings")

    ranked = sorted(profiles, key=lambda x: x.total_value, reverse=True)
    league_rows = [
        {
            "Rank": i,
            "Owner": r.owner_name,
            "Grade": r.roster_grade,
            "Total Value": int(r.total_value),
            "FVS": round(r.total_fvs, 1),
            "FVS Rank": r.fvs_rank,
            "Avg Age": round(r.avg_age_starters, 1),
            "Window": r.window,
            "Pick Value": int(r.pick_value),
        }
        for i, r in enumerate(ranked, 1)
    ]
    df_league = pd.DataFrame(league_rows)

    def _highlight_me(row: pd.Series) -> list[str]:
        return (
            ["background-color:#1a2a4a"] * len(row)
            if row["Owner"] == my.owner_name
            else [""] * len(row)
        )

    def _color_grade(val: str) -> str:
        return {
            "A+": "background-color:#145a32; color:white",
            "A": "background-color:#1e8449; color:white",
            "B+": "background-color:#7d6608; color:white",
            "B": "background-color:#9a7d0a; color:white",
            "C+": "background-color:#6e2222; color:white",
            "C": "background-color:#4a1515; color:white",
            "D": "background-color:#2c3e50; color:white",
        }.get(val, "")

    styled_league = (
        df_league.style
        .apply(_highlight_me, axis=1)
        .map(_color_grade, subset=["Grade"])
    )
    st.dataframe(styled_league, width="stretch", hide_index=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB: TRADE RECOMMENDATIONS
# ─────────────────────────────────────────────────────────────────────────────
with tab_trades:
    st.subheader(f"Top {len(recs)} Trade Recommendations")

    if not recs:
        st.info(
            "No trades surfaced with current settings. "
            "Try lowering the **Min Value Gain** slider in the sidebar.",
            icon="💡",
        )
    else:
        for i, r in enumerate(recs, 1):
            with st.container():
                st.markdown(
                    f"<div class='trade-block'>",
                    unsafe_allow_html=True,
                )
                hdr, gain_col = st.columns([5, 1])
                hdr.markdown(f"**#{i} &nbsp;·&nbsp; vs {r.opponent}**")
                gain_col.metric("Value Gain", f"+{r.raw_value_gain:,.0f}")

                send_col, recv_col, stats_col = st.columns([2, 2, 1])

                with send_col:
                    st.markdown("🔴 **YOU SEND**")
                    for p in r.send_assets:
                        st.markdown(
                            f"&nbsp;&nbsp;**{p.name}** ({p.position})  \n"
                            f"&nbsp;&nbsp;Value: {p.adjusted_value:,.0f} · FVS: {p.fvs:.1f}"
                        )

                with recv_col:
                    st.markdown("🟢 **YOU RECEIVE**")
                    for p in r.receive_assets:
                        st.markdown(
                            f"&nbsp;&nbsp;**{p.name}** ({p.position})  \n"
                            f"&nbsp;&nbsp;Value: {p.adjusted_value:,.0f} · FVS: {p.fvs:.1f}"
                        )

                with stats_col:
                    st.metric("Plausibility", f"{r.plausibility_score * 100:.0f}%")
                    st.metric("FVS Delta", f"{r.future_value_delta:+.1f}")
                    st.metric("Need-Adj Gain", f"+{r.need_adjusted_gain:,.0f}")

                # Build a model-aware reason string
                send_sell_signals  = [p for p in r.send_assets    if p.sell_signal]
                recv_buy_signals   = [p for p in r.receive_assets  if p.buy_signal]
                if send_sell_signals and recv_buy_signals:
                    why = (
                        f"Sell model-overvalued asset(s) "
                        f"({', '.join(p.name for p in send_sell_signals)}) "
                        f"for model-undervalued asset(s) "
                        f"({', '.join(p.name for p in recv_buy_signals)})."
                    )
                elif r.future_value_delta > 0:
                    why = "Exchange for stronger long-term trajectory (higher FVS received)."
                else:
                    why = "Win current market value while preserving roster depth."
                st.caption(f"Why: {why}")
                st.markdown("</div>", unsafe_allow_html=True)
                st.write("")

# ─────────────────────────────────────────────────────────────────────────────
# TAB: BUY / SELL
# ─────────────────────────────────────────────────────────────────────────────
with tab_buysell:
    st.caption(
        "Signals are driven by **model-vs-market spread**, not KTC-vs-FC disagreement.  "
        "**Buy** = intrinsic value > market price by ≥ 8 % AND market trending down (entry point).  "
        "**Sell** = market price > intrinsic value by ≥ 8 % AND market trending up (exit point)."
    )
    buy_col, sell_col = st.columns(2)

    with buy_col:
        st.subheader("🔵 Buy Candidates")
        st.caption("Model thinks market is underpricing these players")
        if buy:
            buy_rows = [
                {
                    "Name":       b["name"],
                    "Owner":      b.get("owner", "—"),
                    "Spread %":   f"+{b['spread_pct']:.1f}%",
                    "Market":     int(b["current"]),
                    "Intrinsic":  int(b["intrinsic"]),
                    "Confidence": b.get("uncertainty", "—"),
                }
                for b in buy
            ]
            st.dataframe(pd.DataFrame(buy_rows), width="stretch", hide_index=True)
        else:
            st.info(
                "No buy candidates found at current threshold (≥ +8 % spread).  "
                "Try lower **Min Value Gain** or check back when market prices shift.",
                icon="💡",
            )

    with sell_col:
        st.subheader("🔴 Sell Candidates")
        st.caption("Model thinks the market is overpricing these players on your roster")
        if sell:
            sell_rows = [
                {
                    "Name":       s["name"],
                    "Spread %":   f"{s['spread_pct']:.1f}%",
                    "Market":     int(s["current"]),
                    "Intrinsic":  int(s["intrinsic"]),
                    "Confidence": s.get("uncertainty", "—"),
                }
                for s in sell
            ]
            st.dataframe(pd.DataFrame(sell_rows), width="stretch", hide_index=True)
        else:
            st.info("No sell candidates on your roster at current threshold.", icon="💡")

# ─────────────────────────────────────────────────────────────────────────────
# TAB: VALUE MOVERS
# ─────────────────────────────────────────────────────────────────────────────
with tab_movers:
    all_vals = list(player_values.values())
    risers = sorted(all_vals, key=lambda x: x.trend_30d, reverse=True)[:15]
    fallers = sorted(all_vals, key=lambda x: x.trend_30d)[:15]

    up_col, dn_col = st.columns(2)

    with up_col:
        st.subheader("🟢 Biggest Risers (30d)")
        riser_rows = [
            {
                "Name": p.name,
                "Pos": p.position,
                "Team": p.team,
                "Value": int(p.adjusted_value),
                "+30d": f"+{p.trend_30d}",
                "Momentum": f"{(p.trend_30d / max(p.adjusted_value, 1)) * 100:.2f}%",
            }
            for p in risers
        ]
        st.dataframe(pd.DataFrame(riser_rows), width="stretch", hide_index=True)

    with dn_col:
        st.subheader("🔴 Biggest Fallers (30d)")
        faller_rows = [
            {
                "Name": p.name,
                "Pos": p.position,
                "Team": p.team,
                "Value": int(p.adjusted_value),
                "30d": str(p.trend_30d),
                "Momentum": f"{(p.trend_30d / max(p.adjusted_value, 1)) * 100:.2f}%",
            }
            for p in fallers
        ]
        st.dataframe(pd.DataFrame(faller_rows), width="stretch", hide_index=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB: FUTURE PROJECTIONS
# ─────────────────────────────────────────────────────────────────────────────
with tab_future:
    st.subheader("Future Value Projections — Top 25 by FVS")
    st.caption(
        "**FVS** (Future Value Score) is a 0–100 league-relative score based on projected market-price trajectory "
        "over 1, 2, 3, and 5 years.  Higher = better long-term hold.  "
        "Use **Spread %** in the Roster tab for the model-vs-market signal."
    )

    top_players = sorted(my.players, key=lambda x: x.fvs, reverse=True)[:25]
    proj_rows = [
        {
            "Name": p.name,
            "Pos": p.position,
            "Age": round(p.age, 1) if p.age else None,
            "Current": int(p.adjusted_value),
            "+1yr": int(p.future_value_1yr),
            "+2yr": int(p.future_value_2yr),
            "+3yr": int(p.future_value_3yr),
            "+5yr": int(p.future_value_5yr),
            "FVS": round(p.fvs, 1),
            "FVS Tier": p.fvs_tier,
            "Trend": "↑" if p.future_value_3yr > p.adjusted_value else "↓",
        }
        for p in top_players
    ]
    df_proj = pd.DataFrame(proj_rows)

    def _color_fvs_tier(val: str) -> str:
        return {
            "Elite": "background-color:#5c4200; color:#FFD700",
            "Rising": "background-color:#1a3a1a; color:#4CAF50",
            "Stable": "background-color:#1a253a; color:#64b5f6",
            "Declining": "background-color:#3a2a10; color:#FF9800",
            "Fading": "background-color:#2a0a0a; color:#ef4444",
        }.get(val, "")

    def _color_arrow(val: str) -> str:
        return "color:#22c55e; font-weight:bold" if val == "↑" else "color:#ef4444; font-weight:bold"

    styled_proj = (
        df_proj.style
        .map(_color_fvs_tier, subset=["FVS Tier"])
        .map(_color_arrow, subset=["Trend"])
    )
    st.dataframe(styled_proj, width="stretch", hide_index=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB: POSITIONAL NEEDS HEATMAP
# ─────────────────────────────────────────────────────────────────────────────
with tab_needs:
    st.subheader("Positional Need Heatmap — All Teams")
    st.caption("0.0 = deep / no need  |  1.0 = critical need.  Green < 0.3 · Yellow < 0.6 · Red ≥ 0.6")

    need_rows = [
        {
            "Team": r.owner_name,
            "QB": round(r.positional_needs.get("QB", 0.5), 2),
            "RB": round(r.positional_needs.get("RB", 0.5), 2),
            "WR": round(r.positional_needs.get("WR", 0.5), 2),
            "TE": round(r.positional_needs.get("TE", 0.5), 2),
        }
        for r in sorted(profiles, key=lambda x: x.total_value, reverse=True)
    ]
    df_needs = pd.DataFrame(need_rows)

    def _color_need(val: float) -> str:
        if val < 0.3:
            return "background-color:#1a472a; color:white"
        if val < 0.6:
            return "background-color:#7d6608; color:white"
        return "background-color:#641e16; color:white"

    def _highlight_my_team(row: pd.Series) -> list[str]:
        return (
            ["background-color:#1a2a4a"] * len(row)
            if row["Team"] == my.owner_name
            else [""] * len(row)
        )

    styled_needs = (
        df_needs.style
        .apply(_highlight_my_team, axis=1)
        .map(_color_need, subset=["QB", "RB", "WR", "TE"])
        .format({"QB": "{:.2f}", "RB": "{:.2f}", "WR": "{:.2f}", "TE": "{:.2f}"})
    )
    st.dataframe(styled_needs, width="stretch", hide_index=True)
