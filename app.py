#!/usr/bin/env python3
"""Streamlit web app for Dynasty Future Value Analyzer."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

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
    [data-testid="stSidebar"] { background: #0d0d1a; }
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: #e0e0ff; }
    .block-container { padding-top: 1.5rem; max-width: 1200px; }
    .stTabs [data-baseweb="tab"] {
        font-size: 0.88rem;
        font-weight: 600;
        padding: 8px 16px;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 2px; }
    .trade-block {
        background: #12121e;
        border: 1px solid #2a2a3a;
        border-radius: 10px;
        padding: 1.2rem;
        margin-bottom: 1rem;
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
    season = st.selectbox("Season", ["2025", "2024"])

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
    analyze_btn = st.button("🔍 Analyze My Team", type="primary", use_container_width=True)

# ── session state init ────────────────────────────────────────────────────────
for key in ("leagues", "data", "state", "user_id"):
    if key not in st.session_state:
        st.session_state[key] = None

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
    }


# ── main header ───────────────────────────────────────────────────────────────
st.title("Dynasty Future Value Analyzer")
st.caption(
    f"Powered by Sleeper · FantasyCalc · KTC  |  {datetime.now().strftime('%B %d, %Y')}"
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
            **FFPredict** pulls live dynasty values from **FantasyCalc** and **KeepTradeCut**,
            blends them with age-curve projections, and gives you:

            - 📋 **Roster breakdown** — current & projected player values, tiers, trends
            - 🏆 **League power rankings** — where you stand vs every other team
            - 🔄 **Trade recommendations** — value-positive moves ranked by composite score
            - 📈 **Buy low / Sell high targets** — players to chase or move before value shifts
            - 📉 **Value movers** — biggest 30-day risers and fallers across the whole market
            - 🔮 **Future value projections** — 1, 2, 3, and 5-year outlooks per player
            - 🗺️ **Positional needs heatmap** — color-coded roster gaps for every team
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

st.divider()

# ── tabs ──────────────────────────────────────────────────────────────────────
(
    tab_roster,
    tab_league,
    tab_trades,
    tab_buysell,
    tab_movers,
    tab_future,
    tab_needs,
) = st.tabs([
    "📋 My Roster",
    "🏆 League Rankings",
    "🔄 Trade Recommendations",
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

    players_sorted = sorted(my.players, key=lambda x: x.adjusted_value, reverse=True)
    roster_rows = [
        {
            "#": i,
            "Name": p.name,
            "Pos": p.position,
            "Team": p.team,
            "Age": round(p.age, 1) if p.age else None,
            "Value": int(p.adjusted_value),
            "+1yr": int(p.future_value_1yr),
            "+3yr": int(p.future_value_3yr),
            "+5yr": int(p.future_value_5yr),
            "FVS": round(p.fvs, 1),
            "Tier": p.tier,
            "30d Trend": p.trend_30d,
        }
        for i, p in enumerate(players_sorted, 1)
    ]

    df_roster = pd.DataFrame(roster_rows)

    def _color_tier(val: str) -> str:
        return {
            "Elite": "background-color:#5c4200; color:#FFD700",
            "Star": "background-color:#2a2a2a; color:#C0C0C0",
            "Starter": "background-color:#1a3a1a; color:#4CAF50",
            "Flex": "background-color:#1a253a; color:#64b5f6",
            "Depth": "background-color:#3a2a10; color:#FF9800",
            "Stash": "background-color:#222; color:#9E9E9E",
        }.get(val, "")

    def _color_trend(val: int) -> str:
        if val > 0:
            return "color:#22c55e; font-weight:bold"
        if val < 0:
            return "color:#ef4444; font-weight:bold"
        return ""

    styled_roster = (
        df_roster.style
        .map(_color_tier, subset=["Tier"])
        .map(_color_trend, subset=["30d Trend"])
    )
    st.dataframe(styled_roster, use_container_width=True, hide_index=True)

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
        st.dataframe(pd.DataFrame(pick_rows), use_container_width=True, hide_index=True)

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
    st.dataframe(styled_league, use_container_width=True, hide_index=True)

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

                why = (
                    "Sell aging asset for stronger long-term trajectory."
                    if r.future_value_delta > 0
                    else "Win current value while preserving depth."
                )
                st.caption(f"Why: {why}")
                st.markdown("</div>", unsafe_allow_html=True)
                st.write("")

# ─────────────────────────────────────────────────────────────────────────────
# TAB: BUY / SELL
# ─────────────────────────────────────────────────────────────────────────────
with tab_buysell:
    buy_col, sell_col = st.columns(2)

    with buy_col:
        st.subheader("📈 Buy Low Targets")
        st.caption("Players across the league whose value is likely to rise")
        if buy:
            buy_rows = [
                {
                    "Name": b["name"],
                    "Owner": b.get("owner", "—"),
                    "Score": round(b["score"], 3),
                    "Current": int(b["current"]),
                    "2yr Proj": int(b["future"]),
                }
                for b in buy
            ]
            st.dataframe(pd.DataFrame(buy_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No buy low targets identified.")

    with sell_col:
        st.subheader("📉 Sell High Targets")
        st.caption("Your players who may be near peak value — move before decline")
        if sell:
            sell_rows = [
                {
                    "Name": s["name"],
                    "Score": round(s["score"], 3),
                    "Current": int(s["current"]),
                    "1yr Proj": int(s["future"]),
                }
                for s in sell
            ]
            st.dataframe(pd.DataFrame(sell_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No sell high targets identified.")

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
        st.dataframe(pd.DataFrame(riser_rows), use_container_width=True, hide_index=True)

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
        st.dataframe(pd.DataFrame(faller_rows), use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB: FUTURE PROJECTIONS
# ─────────────────────────────────────────────────────────────────────────────
with tab_future:
    st.subheader("Future Value Projections — Top 25 by FVS")
    st.caption(
        "FVS (Future Value Score) is a 0–100 composite of projected dynasty value across 1, 2, 3, and 5 years."
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
    st.dataframe(styled_proj, use_container_width=True, hide_index=True)

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
    st.dataframe(styled_needs, use_container_width=True, hide_index=True)
