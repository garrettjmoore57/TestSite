# FFPredict

A model-vs-market decision engine for dynasty fantasy football.

---

## What the app does

FFPredict estimates the **intrinsic dynasty value** of every player in your league, compares it to what the market currently prices them at, and surfaces where the two diverge.

When your model says a player is worth 7 200 and the market prices them at 5 500, that 1 700-point spread is your edge — a potential buy.  When the market prices someone at 6 800 and the model says 4 900, that is a sell signal.

The goal is not to average two popular sources.  It is to tell you when the market is wrong.

---

## Why it is different

Most dynasty tools blend KTC and FantasyCalc into a single number and call it a value.  That produces a weighted average of community opinion — not an independent estimate of intrinsic worth.

FFPredict treats market data as one input layer and builds a separate intrinsic model:

| Layer | What it is |
|---|---|
| **Market Price** | KTC + FantasyCalc composite — what players actually trade for |
| **Intrinsic Value** | Forward-looking present-value model — what the player is likely worth |
| **Spread** | Intrinsic − Market — your actionable signal |

KTC and FantasyCalc are described correctly:
- **KTC** = community sentiment.  What dynasty managers *say* a player is worth.
- **FantasyCalc** = executed market price.  What managers actually *pay* in real trades.

Neither is used to imply player performance.  Neither is the model itself.

---

## Core model layers

### 1 · Market price composite

```
market_price = 0.50 × KTC_normalised + 0.50 × FantasyCalc_normalised
```

Both sources are normalised to a common 10 000-point scale using their 90th percentile as a reference.  The 50/50 split is configurable.  KTC vs FC disagreement is surfaced as a context signal (`sentiment_gap`) but does **not** directly inflate or deflate the score — the old ±4 %/−8 % bonuses are gone.

### 2 · Intrinsic value model

A 3-year present-value formula:

```
V = Σ  age_mult(age + t) × PEAK_VALUE × survival(pos, age, t) × role(rank, t)
        ────────────────────────────────────────────────────────────────────────
                              (1 + 12 %)^t
```

| Component | What it captures |
|---|---|
| `age_mult` | Gompertz career arc by position (QB peaks 28, RB 24, WR 26, TE 27) |
| `PEAK_VALUE` | Position-specific intrinsic anchor (calibrated to ~10 000-point scale) |
| `survival` | P(player still active at year t), adjusted for age relative to peak |
| `role` | P(still a starter at year t), based on current position rank |
| `discount rate` | 12 % annual time discount — future production is worth less today |

Raw PV values are portfolio-calibrated so intrinsic and market prices live on the same scale and spreads are directly comparable.

### 3 · Uncertainty

Each player's intrinsic value comes with a confidence band from Monte Carlo simulation (150 runs per player).  Uncertainty grows with projection horizon.  Outputs:

- p10 / p50 / p90 intrinsic value
- Uncertainty label: low / moderate / high
- Bust probability and elite-outcome probability

### 4 · Scarcity

Replacement-level value-over-replacement, computed from your actual league settings (roster size, starting slots, superflex).  Replaces static tier boosts like "top-5 QB +8 %."  Players below replacement level receive no premium; players above it receive a continuously scaled premium.

### 5 · Picks and rookies

Draft picks use historical hit/bust rates by pick tier.  Younger players naturally have wider confidence bands.  No flat rookie contract bonus is applied to current market price.

---

## Output interpretation

| Column | Meaning |
|---|---|
| **Market** | Adjusted composite of KTC + FC, including league-format multipliers |
| **Intrinsic** | 3-year PV model estimate (portfolio-calibrated) |
| **Spread %** | (Intrinsic − Market) / Market × 100 |
| **Signal** | 🔵 Buy (spread ≥ +8 %) · 🔴 Sell (spread ≤ −8 %) · — Hold |
| **FVS** | 0–100 league-relative future value score (trajectory signal) |

### Reading the spread

- **+10 %**: Model estimates the player is worth ~10 % more than the market. Buy candidate — especially when the market price is trending down.
- **−12 %**: Market is pricing the player ~12 % above the model estimate. Sell candidate — especially when the market price is near its peak.
- **Near 0 %**: Model and market agree. Hold unless other factors apply.

Uncertainty matters.  A +10 % spread with "high uncertainty" is less actionable than +10 % with "low uncertainty."

---

## Example workflow

1. Run the app with your Sleeper username.
2. Open the **My Roster** tab.  Sort by **Spread %**.
3. Large positive spread = model thinks the player is underpriced.  Consider buying more at market price.
4. Large negative spread = market overpricing.  Consider selling while market is high.
5. Open **Buy / Sell** for league-wide opportunities: buy candidates are on opponents' rosters; sell candidates are on yours.
6. Use **Trade Recommendations** to find specific trade proposals where you move overvalued assets and receive undervalued ones.

---

## Developer notes

### Setup

```bash
git clone https://github.com/garrettjmoore57/FFPredict.git
cd FFPredict
pip install -r requirements.txt
streamlit run app.py
```

### Key files

| File | Purpose |
|---|---|
| `valuation_engine.py` | Layered valuation model: market composite, intrinsic PV, scarcity |
| `fantasy_trade_analyzer.py` | Data fetching (Sleeper, KTC, FC), value computation, trade engine |
| `app.py` | Streamlit UI |

### Configuration

Central constants live at the top of each file:

- `valuation_engine.py`: `INTRINSIC_DISCOUNT_RATE`, `MARKET_KTC_WEIGHT`, spread thresholds, scarcity premiums
- `fantasy_trade_analyzer.py` → `CONFIG`: league format multipliers, cache TTL, trade engine settings

### Data sources

| Source | What it is | Cache |
|---|---|---|
| **Sleeper** | Roster, league settings, player metadata | 24 h |
| **KTC** | Community dynasty trade values | 24 h |
| **FantasyCalc** | Trade-derived executed prices, 30-day trends | 24 h |

If KTC is unavailable, the market composite falls back to FantasyCalc only.  The UI flags this.

### Extending the model

- **Better survival probabilities**: Replace `_SURVIVAL_BASE` in `valuation_engine.py` with empirical career-length data.
- **League-specific discount rate**: Pass a custom `discount` argument to `IntrinsicModel`.
- **Roster simulation**: `RosterAnalyzer` profiles are ready for Monte Carlo team-level simulation; add a `SimulationEngine` class that aggregates player-level distributions into roster outcome distributions.
- **Target share / snap %**: Layer real production data into the intrinsic model by extending the `IntrinsicResult` inputs.

### Known limitations

- KTC and FantasyCalc don't provide raw contract or salary data; the model can't explicitly factor in rookie salary scale.
- Survival probabilities are position-wide, not player-specific.  Injury history is not tracked across seasons.
- The 3-year horizon is deliberately conservative.  5-year projections would require wider uncertainty bands and more speculative survival assumptions.

---

## Disclaimer

FFPredict provides data-driven insights for dynasty decision support.  It is not investment advice.  Dynasty trades involve subjective factors (team context, league dynamics, personal risk tolerance) that any model only partially captures.
