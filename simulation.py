"""
simulation.py — Multi-sector shock-driven economic simulation.

Each sector has its own sensitivity profile — meaning each shock affects
different sectors differently. For example:
    - Supply shocks hit commodities hard but barely affect tech
    - Regulation shocks hit crypto hard but barely affect healthcare
    - Uncertainty shocks hit tech and crypto hardest
    - Fiscal shocks hit healthcare and infrastructure more
    - Interest rate rises hit financials and housing hardest

The simulation runs the core equations for each sector independently,
then computes a market average across all sectors.

Sectors modelled:
    - Commodities
    - Technology
    - Healthcare
    - Crypto
    - Financials
"""

import random
from typing import Dict, List


# ── Sector sensitivity profiles ───────────────────────────────────────────────
# Each value represents how sensitive a sector is to each shock type.
# 1.0 = average sensitivity, >1.0 = more sensitive, <1.0 = less sensitive

SECTOR_PROFILES = {
    "Commodities": {
        "interest_rate":   0.8,   # moderately sensitive to rates
        "demand_shock":    1.2,   # highly driven by demand
        "supply_shock":    2.0,   # most sensitive to supply disruptions
        "uncertainty":     0.8,   # less volatile than financial assets
        "regulation":      0.5,   # less regulated
        "fiscal":          0.9,   # moderate fiscal sensitivity
    },
    "Technology": {
        "interest_rate":   1.2,   # rate sensitive (growth stocks discounted)
        "demand_shock":    1.0,   # average demand sensitivity
        "supply_shock":    0.6,   # less affected by physical supply shocks
        "uncertainty":     1.8,   # very sensitive to uncertainty
        "regulation":      1.2,   # increasingly regulated
        "fiscal":          0.8,   # less dependent on government spending
    },
    "Healthcare": {
        "interest_rate":   0.6,   # less rate sensitive (defensive sector)
        "demand_shock":    0.5,   # demand is relatively inelastic
        "supply_shock":    0.7,   # moderate supply sensitivity
        "uncertainty":     0.4,   # defensive — less volatile in uncertainty
        "regulation":      1.5,   # highly regulated
        "fiscal":          1.8,   # very dependent on government spending
    },
    "Crypto": {
        "interest_rate":   1.5,   # very rate sensitive
        "demand_shock":    1.3,   # sentiment-driven demand
        "supply_shock":    0.3,   # not affected by physical supply
        "uncertainty":     2.5,   # most sensitive to uncertainty
        "regulation":      2.0,   # most sensitive to regulation
        "fiscal":          0.6,   # less fiscal sensitivity
    },
    "Financials": {
        "interest_rate":   1.8,   # most sensitive to interest rates
        "demand_shock":    1.0,   # average demand sensitivity
        "supply_shock":    0.5,   # less affected by supply shocks
        "uncertainty":     1.5,   # sensitive to uncertainty/risk
        "regulation":      1.8,   # highly regulated
        "fiscal":          1.0,   # average fiscal sensitivity
    },
}


# ── Single sector simulation ──────────────────────────────────────────────────

def _run_sector(
    sector_name: str,
    profile: Dict,
    interest_rate: float,
    steps: int,
    demand_shock: float,
    supply_shock: float,
    uncertainty_shock: float,
    regulation_shock: float,
    fiscal_shock: float,
) -> List[float]:
    """
    Run the simulation for a single sector using its sensitivity profile.
    Returns the price series for that sector.
    """
    price = 100.0
    demand = 100.0
    credit_spread = 1.5

    neutral_rate  = 2.0
    demand_mean   = 100.0
    spread_mean   = 1.5

    demand_adjustment = 0.08
    spread_adjustment = 0.2
    price_adjustment  = 0.18

    # Apply sector sensitivity to noise scaling
    base_noise = 1.5 * profile["uncertainty"]
    noise_scale = base_noise * (1.0 + uncertainty_shock)

    prices = []

    for _ in range(steps):
        rate_gap = interest_rate - neutral_rate

        # Demand dynamics with sector sensitivity
        demand_target = (
            demand_mean
            - 2.5 * rate_gap           * profile["interest_rate"]
            + 15.0 * demand_shock      * profile["demand_shock"]
            + 10.0 * fiscal_shock      * profile["fiscal"]
        )

        demand_drift = demand_adjustment * (demand_target - demand)
        demand += demand_drift + random.uniform(-noise_scale * 0.7, noise_scale * 0.7)
        demand = max(60.0, min(demand, 140.0))

        # Credit spread dynamics with sector sensitivity
        spread_target = max(
            0.3,
            spread_mean
            + 0.4  * rate_gap          * profile["interest_rate"]
            + 1.5  * regulation_shock  * profile["regulation"],
        )
        spread_drift = spread_adjustment * (spread_target - credit_spread)
        credit_spread += spread_drift + random.uniform(-0.05, 0.05)
        credit_spread = max(0.2, min(credit_spread, 10.0))

        # Fundamental price with sector-specific supply sensitivity
        supply_cost_effect = -8.0 * supply_shock * profile["supply_shock"]

        fundamental = (
            100.0
            + 0.5 * (demand - demand_mean)
            - 6.0 * (credit_spread - spread_mean)
            + supply_cost_effect
        )

        price_drift = price_adjustment * (fundamental - price)
        price += price_drift + random.uniform(-noise_scale, noise_scale)
        price = max(5.0, min(price, 250.0))

        prices.append(price)

    return prices


# ── Main simulation function ──────────────────────────────────────────────────

def run_simulation(
    interest_rate: float,
    steps: int = 100,
    demand_shock: float = 0.0,
    supply_shock: float = 0.0,
    uncertainty_shock: float = 0.0,
    regulation_shock: float = 0.0,
    fiscal_shock: float = 0.0,
) -> Dict:
    """
    Multi-sector shock-driven economic simulation.

    Runs the simulation for each sector independently using sector-specific
    sensitivity profiles, then computes aggregate demand, credit spread,
    and a market average price across all sectors.

    Returns per-sector price series plus aggregate demand and credit spread.
    """

    # Run each sector
    sector_series = {}
    for sector_name, profile in SECTOR_PROFILES.items():
        sector_series[sector_name] = _run_sector(
            sector_name=sector_name,
            profile=profile,
            interest_rate=interest_rate,
            steps=steps,
            demand_shock=demand_shock,
            supply_shock=supply_shock,
            uncertainty_shock=uncertainty_shock,
            regulation_shock=regulation_shock,
            fiscal_shock=fiscal_shock,
        )

    # Compute market average price at each step
    market_avg_series = [
        sum(sector_series[s][i] for s in SECTOR_PROFILES) / len(SECTOR_PROFILES)
        for i in range(steps)
    ]

    # Run aggregate demand and credit spread (used for recession detection)
    neutral_rate      = 2.0
    demand_mean       = 100.0
    spread_mean       = 1.5
    demand_adjustment = 0.08
    spread_adjustment = 0.2
    noise_scale       = 1.0 * (1.0 + uncertainty_shock)

    demand        = 100.0
    credit_spread = 1.5
    demands       = []
    spreads       = []
    recession_steps    = 0
    overheating_steps  = 0

    for _ in range(steps):
        rate_gap = interest_rate - neutral_rate

        demand_target = (
            demand_mean
            - 2.5  * rate_gap
            + 15.0 * demand_shock
            + 10.0 * fiscal_shock
        )
        demand += demand_adjustment * (demand_target - demand)
        demand += random.uniform(-noise_scale, noise_scale)
        demand = max(60.0, min(demand, 140.0))

        spread_target = max(
            0.3,
            spread_mean + 0.4 * rate_gap + 1.5 * regulation_shock,
        )
        credit_spread += spread_adjustment * (spread_target - credit_spread)
        credit_spread += random.uniform(-0.05, 0.05)
        credit_spread = max(0.2, min(credit_spread, 10.0))

        demands.append(demand)
        spreads.append(credit_spread)

        if demand < 90.0:
            recession_steps += 1
        if demand > 110.0:
            overheating_steps += 1

    # Summary statistics per sector
    sector_summary = {}
    for sector, prices in sector_series.items():
        sector_summary[sector] = {
            "final_price":     round(prices[-1], 4),
            "average_price":   round(sum(prices) / len(prices), 4),
            "price_volatility": round(max(prices) - min(prices), 4),
        }

    return {
        # Parameters
        "interest_rate":      interest_rate,
        "steps":              steps,

        # Aggregate stats
        "average_demand":     round(sum(demands) / len(demands), 4),
        "recession_steps":    recession_steps,
        "overheating_steps":  overheating_steps,
        "max_credit_spread":  round(max(spreads), 4),
        "min_credit_spread":  round(min(spreads), 4),

        # Market average price
        "market_average_final":    round(market_avg_series[-1], 4),
        "market_average_price":    round(sum(market_avg_series) / len(market_avg_series), 4),
        "market_price_volatility": round(max(market_avg_series) - min(market_avg_series), 4),

        # Per sector summary
        "sector_summary":     sector_summary,

        # Time series
        "series_demand":      demands,
        "series_spread":      spreads,
        "series_market_avg":  market_avg_series,
        "sector_series":      sector_series,
    }


# ── Quick test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    res = run_simulation(
        interest_rate=3.0,
        steps=100,
        demand_shock=-0.5,
        supply_shock=-0.3,
        uncertainty_shock=0.7,
        regulation_shock=0.6,
        fiscal_shock=0.2,
    )

    print("=== SECTOR SUMMARY ===")
    for sector, stats in res["sector_summary"].items():
        print(f"  {sector:12}: final={stats['final_price']:.1f}  "
              f"avg={stats['average_price']:.1f}  "
              f"volatility={stats['price_volatility']:.1f}")

    print(f"\n  {'Market Avg':12}: final={res['market_average_final']:.1f}  "
          f"avg={res['market_average_price']:.1f}")
    print(f"\n  Avg Demand:     {res['average_demand']:.1f}")
    print(f"  Recession Steps: {res['recession_steps']}")
    print(f"  Max Credit Spread: {res['max_credit_spread']:.3f}")