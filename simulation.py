import random
from typing import Dict, List


def run_simulation(
    interest_rate: float,
    steps: int = 80,
    demand_shock: float = 0.0,
    supply_shock: float = 0.0,
    uncertainty_shock: float = 0.0,
    regulation_shock: float = 0.0,
    fiscal_shock: float = 0.0,
) -> Dict:
    """
    Shock-driven macro/market toy simulation.

    State variables:
        - price: asset/market price
        - demand: aggregate demand / activity index (100 = "normal")
        - credit_spread: proxy for financial stress (higher = tighter conditions)

    Shocks (all pre-processed by the LLM from a natural-language scenario):
        - demand_shock: [-1, +1]  (negative = weak demand, positive = strong demand)
        - supply_shock: [-1, +1]  (negative = supply disruption, positive = supply boost)
        - uncertainty_shock: [0, 1]  (scales volatility / noise)
        - regulation_shock: [0, 1]   (extra tightening in spreads)
        - fiscal_shock: [-1, +1]     (negative = austerity, positive = stimulus)

    Idea:
        - interest_rate and regulation_shock push credit_spreads up/down
        - demand_shock and fiscal_shock shift demand up/down
        - supply_shock and spreads influence the "fundamental" price
        - uncertainty_shock scales how noisy/volatile things are
    """

    # --- Initial conditions ---
    price = 100.0
    demand = 100.0          # 100 = "normal" demand
    credit_spread = 1.5     # in percentage points

    prices: List[float] = []
    demands: List[float] = []
    spreads: List[float] = []

    # --- Model parameters ---
    neutral_rate = 2.0          # "normal" policy rate
    demand_mean = 100.0
    spread_mean = 1.5

    demand_adjustment = 0.08    # speed of demand mean reversion
    spread_adjustment = 0.2     # speed of spread mean reversion
    price_adjustment = 0.18     # speed of price adjustment to fundamental

    # thresholds for regimes
    recession_threshold = 90.0
    overheating_threshold = 110.0

    recession_steps = 0
    overheating_steps = 0

    # Base noise scales, which uncertainty_shock will modify
    base_demand_noise = 1.0
    base_spread_noise = 0.05
    base_price_noise = 1.5

    # Scale noise by (1 + uncertainty_shock)
    demand_noise_scale = base_demand_noise * (1.0 + uncertainty_shock)
    spread_noise_scale = base_spread_noise * (1.0 + uncertainty_shock)
    price_noise_scale = base_price_noise * (1.0 + uncertainty_shock)

    for _ in range(steps):
        # How far away are we from the neutral rate?
        rate_gap = interest_rate - neutral_rate

        # --- Demand dynamics ---
        # Baseline target demand reacts to interest_rate, demand_shock and fiscal_shock.
        demand_target = (
            demand_mean
            - 2.5 * rate_gap           # higher rates -> weaker demand
            + 15.0 * demand_shock      # structural demand impact
            + 10.0 * fiscal_shock      # fiscal stance impact
        )

        demand_drift = demand_adjustment * (demand_target - demand)
        demand_shock_term = random.uniform(-demand_noise_scale, demand_noise_scale)
        demand += demand_drift + demand_shock_term

        demand = max(60.0, min(demand, 140.0))

        # --- Credit spread dynamics ---
        # Spreads are wider when rates are above neutral and when regulation is tight.
        spread_target = max(
            0.3,
            spread_mean + 0.4 * rate_gap + 1.5 * regulation_shock,
        )
        spread_drift = spread_adjustment * (spread_target - credit_spread)
        spread_shock_term = random.uniform(-spread_noise_scale, spread_noise_scale)
        credit_spread += spread_drift + spread_shock_term

        credit_spread = max(0.2, min(credit_spread, 10.0))

        # --- Fundamental price and market price dynamics ---
        # Supply shocks affect the "cost side" of fundamentals:
        # negative supply_shock -> higher costs -> lower fundamentals.
        supply_cost_effect = -8.0 * supply_shock  # if shock < 0, this is positive "cost pain"

        fundamental = (
            100.0
            + 0.5 * (demand - demand_mean)        # demand-driven fundamentals
            - 6.0 * (credit_spread - spread_mean) # spread-driven discounting
            + supply_cost_effect
        )

        # Price moves gradually toward fundamental plus some noise.
        price_drift = price_adjustment * (fundamental - price)
        price_shock_term = random.uniform(-price_noise_scale, price_noise_scale)
        price += price_drift + price_shock_term

        price = max(5.0, min(price, 250.0))

        # --- Record series ---
        prices.append(price)
        demands.append(demand)
        spreads.append(credit_spread)

        # --- Regime counters ---
        if demand < recession_threshold:
            recession_steps += 1
        if demand > overheating_threshold:
            overheating_steps += 1

    # --- Summary stats ---
    avg_price = sum(prices) / len(prices)
    price_volatility = max(prices) - min(prices)
    avg_demand = sum(demands) / len(demands)
    max_spread = max(spreads)
    min_spread = min(spreads)

    return {
        "interest_rate": interest_rate,
        "steps": steps,
        "final_price": price,
        "average_price": avg_price,
        "price_volatility": price_volatility,
        "average_demand": avg_demand,
        "recession_steps": recession_steps,
        "overheating_steps": overheating_steps,
        "max_credit_spread": max_spread,
        "min_credit_spread": min_spread,
        "series_price": prices,
        "series_demand": demands,
        "series_spread": spreads,
    }


if __name__ == "__main__":
    # quick manual test
    res = run_simulation(
        interest_rate=3.0,
        steps=100,
        demand_shock=-0.5,
        supply_shock=-0.3,
        uncertainty_shock=0.7,
        regulation_shock=0.6,
        fiscal_shock=0.2,
    )
    summary = {k: v for k, v in res.items() if not k.startswith("series_")}
    print(summary)
