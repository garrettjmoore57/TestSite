# FFPredict

A comprehensive dynasty fantasy football analyzer powered by live KTC (KeepTradeCut) and FantasyCalc data, with intelligent trade evaluation, roster grading, and future value projections.

## What It Does

FFPredict is a tool for serious dynasty fantasy football players who want to make data-driven trade decisions. It fetches live player valuations from two sources—**KTC** (community dynasty trade values) and **FantasyCalc** (real-world performance signals)—blends them intelligently, and provides:

- **Trade Analyzer**: Evaluate proposed trades with clear value gains/losses
- **Roster Grading**: See how your team stacks up against others in the league
- **Power Rankings**: Visualize league standings by roster strength
- **Buy/Sell Targets**: Identify undervalued (buy) and overvalued (sell) players
- **Draft Pick Valuation**: Assess trade value of future draft capital
- **Future Value Score (FVS)**: Project player value over 1, 2, 3, and 5-year horizons

## How Player Values Work

FFPredict uses a two-source blending system tailored to dynasty fantasy football:

### Value Sources

| Source | Role | Weight |
|--------|------|--------|
| **KTC (KeepTradeCut)** | Primary dynasty trade value—what the community says players are worth in trades | **65%** |
| **FantasyCalc** | Real-world performance signal—recent production and trend momentum | **35%** |

### Directional Disagreement Handling

When the two sources disagree by more than 35%, FFPredict applies logic based on *which way* they disagree:

- **When FantasyCalc > KTC** (by >35%): Player is performing better than the dynasty community values them. This is a **buy signal**—the player gets a small boost (+4%) to reflect undervaluation.
  - *Example*: A WR posting elite production numbers (FC: 8500) but the community hasn't caught up (KTC: 5200).

- **When KTC > FantasyCalc** (by >35%): The dynasty community is overvaluing this player relative to real-world results. This is a **sell signal**—the value gets a penalty (-8%) to temper hype.
  - *Example*: A high-pedigree player with low recent production (KTC: 6000, FC: 3800).

When sources agree (disagree ≤35%), consensus is a straight weighted blend: **0.65 × KTC + 0.35 × FC**.

### Additional Value Adjustments

On top of the KTC/FC blend, FFPredict applies:

1. **Age Curves** (Gompertz model by default)
   - Each position has a peak age and decay profile
   - QB peaks at 28, RB at 24, WR at 26, TE at 27
   - Captures the upside of youth and the decline with age

2. **Positional Scarcity Premiums**
   - Elite players at each position get a boost (harder to replace)
   - QB top 5 +8%, RB top 10 +5%, WR top 12 +2%, TE top 5 +12%

3. **TE Premium**: Tight ends get a baseline 6% boost, plus up to +3.75% based on league settings

4. **Superflex QB Premium**: QBs get +14% value in superflex leagues

5. **Rookie Contract Bonus**: Players with ≤3 years of experience get +5%

6. **Veteran Penalty**: Players 3+ years past their position peak see declining value (floors at 45% of adjusted value)

7. **Injury Adjustment**: IR/O = 88%, Q = 97%, D = 91% of base value

### Normalization

Both KTC and FantasyCalc values are normalized to a common 10,000-point scale using each source's 90th percentile value. This ensures fair comparison even though the raw value ranges may differ.

## Key Features

### Trade Analyzer
Input two rosters (you and a trading partner) and get an instant breakdown:
- Projected value of assets each side is sending
- Value gain/loss for each side
- Risk assessment based on age, injury, and trend volatility
- Depth impact (how it affects your team depth at each position)

### Roster Grading
Submit your league's rosters (via Sleeper username) and get:
- Individual roster grades (A-F) by tier strength
- Power ranking across all teams
- Bench depth analysis
- Positional balance scorecard

### Buy/Sell Targets
FFPredict surfaces:
- **Undervalued** players (FC signal strongly bullish vs. KTC)
- **Overvalued** players (KTC hype vs. weak FC signal)
- **Declining** players (negative 30-day trend momentum)
- **Rising** players (positive 30-day trend momentum)

### Future Value Score (FVS)
A composite 0–100 score blending projected values across multiple years:
- **1-year**: 20% weight (current contention window)
- **2-year**: 25% weight
- **3-year**: 30% weight
- **5-year**: 25% weight (long-term dynasty asset quality)

Higher FVS = better long-term hold. Great for identifying dynasty studs vs. one-year wonders.

## Setup & Installation

### Requirements
- Python 3.11+
- pip package manager

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/garrettjmoore57/FFPredict.git
   cd FFPredict
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up configuration (optional)**
   - If using the Sleeper roster pull, provide your Sleeper username:
     ```bash
     export SLEEPER_USERNAME="your_username"
     ```
   - Or pass it when prompted by the app

## Running the App

### Web UI (Streamlit)
```bash
streamlit run app.py
```
Then open your browser to `http://localhost:8501`. Use the sidebar to:
- Select league and league type (1QB, Superflex, etc.)
- Choose number of teams and scoring format (PPR, Half-PPR, Standard)
- Upload league data or pull from Sleeper
- Switch between Trade Analyzer, Power Rankings, and Buy/Sell targets

### CLI
```bash
python fantasy_trade_analyzer.py
```
Launches an interactive CLI prompt where you can:
- Query individual player values
- Evaluate trades
- Print roster summaries
- Export data to JSON

## Configuration

FFPredict uses sensible defaults, but you can tweak behavior by editing the `CONFIG` dict in `fantasy_trade_analyzer.py`:

```python
CONFIG = {
    "fc_weight": 0.35,              # FantasyCalc weight in consensus (default 35%)
    "ktc_weight": 0.65,             # KTC weight in consensus (default 65%)
    "age_curve_method": "gompertz", # age curve shape (gompertz, exponential, logistic)
    "superflex_qb_premium": 1.14,   # QB value boost in superflex (default 1.14x)
    "te_premium_base": 1.06,        # TE baseline premium (default 1.06x)
    "positional_scarcity_enabled": True,  # apply elite tier boosts
    "rookie_contract_bonus": 0.05,  # rookie contract value boost (default 5%)
    "veteran_contract_penalty": 0.03, # per-year value decay for vets past peak
    "pick_year_discount_rate": 0.88, # discount future draft picks by year
}
```

## Data Sources

### KeepTradeCut (KTC)
- **URL**: `https://keeptradecut.com/dynasty-rankings`
- **What**: Community-driven 1v1 trade value database
- **How it's fetched**: JSON API + HTML scrape fallback (with browser User-Agent)
- **Cached**: 24 hours (disk cache at `.fantasy_cache/`)
- **Includes**: Superflex-adjusted values, 7-day trend data

### FantasyCalc
- **URL**: `https://api.fantasycalc.com/values/current`
- **What**: Crowdsourced dynasty values based on real league trades + player production
- **How it's fetched**: JSON API
- **Cached**: 24 hours
- **Includes**: 1-day, 7-day, 30-day trend momentum, age, team, draft picks

### Caching
Both data sources are cached locally in `.fantasy_cache/` to avoid repeated network calls. Cache TTL is configurable in `CONFIG["cache_ttl_hours"]` (default 24). Delete `.fantasy_cache/` to force a fresh pull.

## Tier System

FFPredict assigns each player a tier based on adjusted value:

| Tier | Value Range | Role |
|------|-------------|------|
| **Elite** | ≥9000 | Perennial starter, generational talent |
| **Star** | 7000–8999 | Reliably excellent, contender-level |
| **Starter** | 4500–6999 | Core starter, depth on most teams |
| **Flex** | 2500–4499 | Flex-worthy or team's WR3/RB3 |
| **Depth** | 1000–2499 | Depth piece, lottery ticket |
| **Stash** | <1000 | Upside play, rarely starts |

## Future Value Score (FVS)

FFPredict uses age curves and Monte Carlo simulation to project each player's value across 1, 2, 3, and 5-year horizons. The FVS combines these into a single 0–100 score:

```
FVS = 0.20 × (1yr value percentile) 
    + 0.25 × (2yr value percentile)
    + 0.30 × (3yr value percentile)
    + 0.25 × (5yr value percentile)
```

**Use cases:**
- **High FVS (75+)**: Dynasty studs; long-term holds
- **Medium FVS (50–74)**: Mixed window; good value near contention window
- **Low FVS (<50)**: Short-term asset; sell if you're rebuilding

## Trade Analyzer Details

When you input a proposed trade, FFPredict:

1. **Sums asset values** for each side (players + picks)
2. **Calculates value delta** (what's being given up vs. received)
3. **Flags massive disagreements** between KTC and FC for either side (uncertainty)
4. **Assesses positional impact** (does the trade leave you thin at a position?)
5. **Considers future outlook** (is the incoming player entering decline while outgoing asset is rising?)

The verdict is color-coded:
- 🟢 **Green** (gain ≥250 value): Trade favors you
- 🟡 **Yellow** (gain/loss ±249): Fairly even
- 🔴 **Red** (loss ≥250 value): Trade favors your opponent

## Example Scenarios

### Scenario 1: Undervalued Performer
```
Player: Austin Ekeler
KTC Value: 3,200
FantasyCalc Value: 5,100 (59% higher!)
Status: Disagreement > 35% → +4% boost applied
Result: Adjusted value rises to ~3,400
Signal: BUY — real production exceeds dynasty valuation
```

### Scenario 2: Overhyped Name
```
Player: A 29-year-old WR entering decline
KTC Value: 5,800 (community still backing the name)
FantasyCalc Value: 3,100 (recent performance down)
Status: Disagreement > 35% → -8% penalty applied
Result: Adjusted value drops to ~5,200
Signal: SELL — name value exceeding real production
```

### Scenario 3: Consensus Agreement
```
Player: Justin Jefferson (WR, age 25, elite production)
KTC Value: 8,900
FantasyCalc Value: 9,200 (only 3% higher)
Status: Disagreement ≤ 35% → standard 65/35 blend
Result: Adjusted value = 0.65 × 8,900 + 0.35 × 9,200 = 9,015
Signal: HOLD — sources agree, elite tier
```

## Troubleshooting

### "KTC scrape failed, falling back to FantasyCalc only"
This means the KTC scraping strategy failed (site structure change, network issue, or IP blocking). FFPredict automatically degrades to 100% FantasyCalc weighting. Fix: Wait 24+ hours (cache expires), or check if keeptradecut.com is accessible.

### Missing players in the valuation table
FFPredict only shows players that have KTC *or* FantasyCalc data. If a player isn't listed:
- They may be too new (rookie not yet valued by both sources)
- They may be inactive/retired
- Name matching failed (rare, but can happen with unique names or slight misspellings)

### Values seem off
- Verify league type (1QB vs. Superflex) is set correctly
- Check that scoring format (PPR, Half-PPR, Standard) matches your league
- Confirm no IDP (individual defensive player) leagues are being analyzed (FFPredict supports skill positions only)

## Contributing

Found a bug or have an idea? Open an issue on GitHub or submit a pull request!

## License

MIT License — see LICENSE file.

## Disclaimer

FFPredict provides data-driven insights but is not investment advice. Dynasty trades involve subjective factors (team needs, rebuild timeline, risk tolerance) that algorithms can't capture. Always do your own diligence and consider your league's context.

---

**Built with ❤️ for dynasty fantasy football nerds.**
