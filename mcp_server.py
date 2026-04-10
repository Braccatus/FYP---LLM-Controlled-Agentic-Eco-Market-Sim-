"""
MCP Server for the LLM-Controlled Economic Market Simulation.

Tools exposed to the agent:

Python macro simulation tools:
- run_and_plot:              Runs the macro simulation AND generates a plot in one call.
                             PRIMARY tool for macro-level economic scenarios.
- run_macro_simulation:      Runs the macro simulation only, returns compact summary.
- run_and_average:           Runs the macro simulation N times and returns averaged results.

NetLogo agent-based simulation tools:
- run_netlogo_wealth:        Runs the NetLogo Wealth Distribution model and returns
                             inequality statistics (Gini coefficient, class distribution).
                             Use this when the scenario involves wealth inequality,
                             resource distribution, or agent-level behaviour.
- run_netlogo_wealth_plot:   Same as above but also generates a plot of results.

Design note:
    The agent has two complementary simulation backends:
    1. Python simulation — macro-level price, demand, credit spread dynamics
    2. NetLogo simulation — agent-level wealth distribution and inequality
    The agent should use both when a scenario calls for both macro and micro analysis.
"""
from __future__ import annotations

import os
from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

from simulation import run_simulation
from plotter import plot_economy
from netlogo_bridge import run_wealth_distribution
from netlogo_plotter import plot_wealth_distribution

mcp = FastMCP("toy-macro-market-sim")


# ── Primary Tool ──────────────────────────────────────────────────────────────

@mcp.tool()
def run_and_plot(
    interest_rate: float,
    steps: int = 100,
    demand_shock: float = 0.0,
    supply_shock: float = 0.0,
    uncertainty_shock: float = 0.0,
    regulation_shock: float = 0.0,
    fiscal_shock: float = 0.0,
    filename: str = "simulation.png",
) -> Dict[str, Any]:
    """
    PRIMARY TOOL. Run the economic simulation and generate a plot in one step.

    This tool:
    1. Runs the shock-driven macro simulation with the given parameters.
    2. Saves a chart (price, demand, credit spread over time) to a PNG file.
    3. Returns a compact summary of results — no large arrays.

    Use this tool first for any economic scenario.

    Parameters:
        interest_rate:      Policy interest rate in percent (e.g. 3.0 = 3%)
        steps:              Number of simulation time steps (50–300)
        demand_shock:       -1 (very weak demand) to +1 (very strong demand)
        supply_shock:       -1 (severe supply disruption) to +1 (strong supply boost)
        uncertainty_shock:  0 (stable/predictable) to 1 (extremely uncertain)
        regulation_shock:   0 (no change) to 1 (very strong regulatory tightening)
        fiscal_shock:       -1 (severe austerity) to +1 (strong fiscal stimulus)
        filename:           Name of the PNG file to save the chart to

    Returns:
        A summary dict with: interest_rate, steps, final_price, average_price,
        price_volatility, average_demand, recession_steps, overheating_steps,
        max_credit_spread, min_credit_spread, plot_saved_to.
    """
    # Run the simulation
    results = run_simulation(
        interest_rate=interest_rate,
        steps=steps,
        demand_shock=demand_shock,
        supply_shock=supply_shock,
        uncertainty_shock=uncertainty_shock,
        regulation_shock=regulation_shock,
        fiscal_shock=fiscal_shock,
    )

    # Derive a human-readable title from the filename
    base = os.path.splitext(os.path.basename(filename))[0]
    title = base.replace("_", " ").title()

    # Generate multi-sector plot
    from plotter import plot_multisector
    plot_multisector(
        sector_series=results["sector_series"],
        market_avg_series=results["series_market_avg"],
        demand_series=results["series_demand"],
        spread_series=results["series_spread"],
        filename=filename,
        title=title,
    )

    # Return compact summary — drop large series arrays
    summary = {
        "interest_rate":           results["interest_rate"],
        "steps":                   results["steps"],
        "average_demand":          results["average_demand"],
        "recession_steps":         results["recession_steps"],
        "overheating_steps":       results["overheating_steps"],
        "max_credit_spread":       results["max_credit_spread"],
        "min_credit_spread":       results["min_credit_spread"],
        "market_average_final":    results["market_average_final"],
        "market_average_price":    results["market_average_price"],
        "market_price_volatility": results["market_price_volatility"],
        "sector_summary":          results["sector_summary"],
        "plot_saved_to":           os.path.abspath(filename),
    }

    return summary


# ── Secondary Tool: Simulation Only (no plot) ─────────────────────────────────

@mcp.tool()
def run_macro_simulation(
    interest_rate: float,
    steps: int = 100,
    demand_shock: float = 0.0,
    supply_shock: float = 0.0,
    uncertainty_shock: float = 0.0,
    regulation_shock: float = 0.0,
    fiscal_shock: float = 0.0,
) -> Dict[str, Any]:
    """
    Run the economic simulation and return a compact summary (no plot generated).

    Use this tool when you want to run multiple simulations quickly for comparison
    or averaging, without generating a chart each time.

    Parameters:
        interest_rate:      Policy interest rate in percent (e.g. 3.0 = 3%)
        steps:              Number of simulation time steps (50–300)
        demand_shock:       -1 (very weak demand) to +1 (very strong demand)
        supply_shock:       -1 (severe supply disruption) to +1 (strong supply boost)
        uncertainty_shock:  0 (stable/predictable) to 1 (extremely uncertain)
        regulation_shock:   0 (no change) to 1 (very strong regulatory tightening)
        fiscal_shock:       -1 (severe austerity) to +1 (strong fiscal stimulus)

    Returns:
        A compact summary dict (no series arrays).
    """
    results = run_simulation(
        interest_rate=interest_rate,
        steps=steps,
        demand_shock=demand_shock,
        supply_shock=supply_shock,
        uncertainty_shock=uncertainty_shock,
        regulation_shock=regulation_shock,
        fiscal_shock=fiscal_shock,
    )

    return {
        "interest_rate":           results["interest_rate"],
        "steps":                   results["steps"],
        "average_demand":          results["average_demand"],
        "recession_steps":         results["recession_steps"],
        "overheating_steps":       results["overheating_steps"],
        "max_credit_spread":       results["max_credit_spread"],
        "min_credit_spread":       results["min_credit_spread"],
        "market_average_final":    results["market_average_final"],
        "market_average_price":    results["market_average_price"],
        "market_price_volatility": results["market_price_volatility"],
        "sector_summary":          results["sector_summary"],
    }


# ── Advanced Tool: Average Multiple Runs ─────────────────────────────────────

@mcp.tool()
def run_and_average(
    interest_rate: float,
    n_runs: int = 5,
    steps: int = 100,
    demand_shock: float = 0.0,
    supply_shock: float = 0.0,
    uncertainty_shock: float = 0.0,
    regulation_shock: float = 0.0,
    fiscal_shock: float = 0.0,
    filename: str = "averaged_simulation.png",
) -> Dict[str, Any]:
    """
    Run the simulation N times and return averaged results, plus a plot.

    Use this tool when uncertainty_shock is high (> 0.5) or when you want
    more reliable results by averaging out random noise across multiple runs.

    Parameters:
        interest_rate:      Policy interest rate in percent
        n_runs:             Number of simulation runs to average (2–10 recommended)
        steps:              Number of simulation time steps (50–300)
        demand_shock:       -1 to +1
        supply_shock:       -1 to +1
        uncertainty_shock:  0 to 1
        regulation_shock:   0 to 1
        fiscal_shock:       -1 to +1
        filename:           Name of the PNG file to save the averaged chart to

    Returns:
        Averaged summary statistics across all runs, plus plot_saved_to.
    """
    n_runs = max(2, min(n_runs, 10))  # clamp between 2 and 10

    all_results = []
    all_prices = []
    all_demands = []
    all_spreads = []

    for _ in range(n_runs):
        r = run_simulation(
            interest_rate=interest_rate,
            steps=steps,
            demand_shock=demand_shock,
            supply_shock=supply_shock,
            uncertainty_shock=uncertainty_shock,
            regulation_shock=regulation_shock,
            fiscal_shock=fiscal_shock,
        )
        all_results.append(r)
        all_prices.append(r["series_price"])
        all_demands.append(r["series_demand"])
        all_spreads.append(r["series_spread"])

    # Average the series for plotting
    avg_prices  = [sum(run[i] for run in all_prices)  / n_runs for i in range(steps)]
    avg_demands = [sum(run[i] for run in all_demands) / n_runs for i in range(steps)]
    avg_spreads = [sum(run[i] for run in all_spreads) / n_runs for i in range(steps)]

    # Derive a human-readable title from the filename
    base = os.path.splitext(os.path.basename(filename))[0]
    title = base.replace("_", " ").title() + f" (Averaged {n_runs} Runs)"

    # Plot the averaged series
    plot_economy(avg_prices, avg_demands, avg_spreads, filename=filename, title=title)

    # Average the scalar summary stats
    keys = ["final_price", "average_price", "price_volatility",
            "average_demand", "recession_steps", "overheating_steps",
            "max_credit_spread", "min_credit_spread"]

    averaged_summary = {
        key: sum(r[key] for r in all_results) / n_runs
        for key in keys
    }

    averaged_summary["interest_rate"]   = interest_rate
    averaged_summary["steps"]           = steps
    averaged_summary["n_runs"]          = n_runs
    averaged_summary["plot_saved_to"]   = os.path.abspath(filename)

    return averaged_summary


# ── NetLogo Tool: Wealth Distribution (no plot) ──────────────────────────────

@mcp.tool()
def run_netlogo_wealth(
    num_people: int = 250,
    max_vision: int = 5,
    metabolism_max: int = 15,
    percent_best_land: int = 10,
    life_expectancy_min: int = 1,
    life_expectancy_max: int = 83,
    grain_growth_interval: int = 1,
    num_grain_grown: int = 4,
    steps: int = 100,
    tax_rate: float = 0.0,
    redistribution_rate: float = 0.0,
    welfare_boost: float = 0.0,
    policy_description: str = "",
) -> Dict[str, Any]:
    """
    Run the NetLogo Wealth Distribution agent-based model (single run, no plot).
    Use run_netlogo_wealth_multiple for statistically meaningful results.

    STANDARD PARAMETER MAPPING:
        num_people (10-500):        Population size.
        max_vision (1-10):          Market information access. Lower = restricted markets.
        metabolism_max (1-25):      Cost of living. Higher = inflation/high living costs.
        percent_best_land (1-25):   Economic productivity. Lower = poor infrastructure.
        life_expectancy_max (20-100): Productive lifespan effects.
        num_grain_grown (1-10):     Welfare generosity. Lower = welfare cuts.
        steps (50-300):             Simulation length.

    POLICY INJECTION PARAMETERS — inject behavioural rules into the model:
        tax_rate (0-50):            % of wealth taken from upper class (rich) agents
                                    each tick. Use for progressive taxation scenarios.
                                    Example: tax_rate=30 for extreme wealth tax.
        redistribution_rate (0-100): % of collected tax given back to poor agents.
                                    Use with tax_rate for redistribution policies.
                                    Example: redistribution_rate=80 for generous redistribution.
        welfare_boost (0-10):       Flat grain bonus given to every poor agent each tick.
                                    Use for direct welfare payment scenarios.
                                    Example: welfare_boost=3 for direct payments to poor.
        policy_description:         Brief description of the policy being applied.

    Returns: final_gini, average_gini, max_gini, min_gini,
             low_class_final, mid_class_final, up_class_final,
             policy_active, tax_rate, redistribution_rate, welfare_boost
    """
    results = run_wealth_distribution(
        num_people=num_people,
        max_vision=max_vision,
        metabolism_max=metabolism_max,
        percent_best_land=percent_best_land,
        life_expectancy_min=life_expectancy_min,
        life_expectancy_max=life_expectancy_max,
        grain_growth_interval=grain_growth_interval,
        num_grain_grown=num_grain_grown,
        steps=steps,
        tax_rate=tax_rate,
        redistribution_rate=redistribution_rate,
        welfare_boost=welfare_boost,
        policy_description=policy_description,
    )
    return {k: v for k, v in results.items() if not k.endswith("_history")}


# ── NetLogo Tool: Multiple Runs with Variance Analysis ───────────────────────

@mcp.tool()
def run_netlogo_wealth_multiple(
    num_people: int = 250,
    max_vision: int = 5,
    metabolism_max: int = 15,
    percent_best_land: int = 10,
    life_expectancy_min: int = 1,
    life_expectancy_max: int = 83,
    grain_growth_interval: int = 1,
    num_grain_grown: int = 4,
    steps: int = 100,
    n_runs: int = 3,
    filename: str = "netlogo_wealth.png",
    tax_rate: float = 0.0,
    redistribution_rate: float = 0.0,
    welfare_boost: float = 0.0,
    policy_description: str = "",
) -> Dict[str, Any]:
    """
    PRIMARY NETLOGO TOOL. Run the Wealth Distribution model N times and return
    averaged results plus variance analysis. Generates a plot.

    Running multiple times accounts for the randomness in agent behaviour —
    each run produces slightly different outcomes. Averaging gives statistically
    more reliable results and variance shows how stable the outcome is.

    STANDARD PARAMETER MAPPING:
        num_grain_grown:      welfare generosity (higher = more generous)
        percent_best_land:    economic productivity / infrastructure quality
        metabolism_max:       cost of living / inflation pressure
        max_vision:           market information access / transparency
        life_expectancy_max:  productive lifespan / retirement age effects
        n_runs:               use 3 for standard, 5 for high-uncertainty scenarios

    POLICY INJECTION — use these to directly modify agent behaviour rules:
        tax_rate (0-50):          % wealth removed from upper class agents each tick.
                                  Use for wealth tax / progressive taxation scenarios.
        redistribution_rate (0-100): % of tax revenue redistributed to poor agents.
                                  Use with tax_rate for redistribution policies.
        welfare_boost (0-10):     Flat grain bonus to every poor agent each tick.
                                  Use for direct welfare payment scenarios.
        policy_description:       Brief description of the policy injected.

    WHEN TO USE POLICY PARAMETERS:
        - "extreme tax on the rich" → tax_rate=30-40, redistribution_rate=80-100
        - "universal basic income" → welfare_boost=3-5
        - "wealth redistribution programme" → tax_rate=20, redistribution_rate=100
        - "no policy intervention" → leave all at 0 (default)

    Returns:
        mean_final_gini, std_final_gini, mean_average_gini,
        mean_low_class, mean_mid_class, mean_up_class,
        n_runs, policy_active, plot_saved_to
    """
    import math

    n_runs = max(2, min(int(n_runs), 5))

    all_final_gini   = []
    all_average_gini = []
    all_low          = []
    all_mid          = []
    all_up           = []
    all_gini_history = []
    all_low_history  = []
    all_mid_history  = []
    all_up_history   = []

    for run_num in range(n_runs):
        r = run_wealth_distribution(
            num_people=num_people,
            max_vision=max_vision,
            metabolism_max=metabolism_max,
            percent_best_land=percent_best_land,
            life_expectancy_min=life_expectancy_min,
            life_expectancy_max=life_expectancy_max,
            grain_growth_interval=grain_growth_interval,
            num_grain_grown=num_grain_grown,
            steps=steps,
            tax_rate=tax_rate,
            redistribution_rate=redistribution_rate,
            welfare_boost=welfare_boost,
            policy_description=policy_description,
        )
        all_final_gini.append(r["final_gini"])
        all_average_gini.append(r["average_gini"])
        all_low.append(r["low_class_final"])
        all_mid.append(r["mid_class_final"])
        all_up.append(r["up_class_final"])
        all_gini_history.append(r["gini_history"])
        all_low_history.append(r["low_class_history"])
        all_mid_history.append(r["mid_class_history"])
        all_up_history.append(r["up_class_history"])

    # Average the time series
    avg_gini = [sum(run[i] for run in all_gini_history) / n_runs for i in range(steps)]
    avg_low  = [sum(run[i] for run in all_low_history)  / n_runs for i in range(steps)]
    avg_mid  = [sum(run[i] for run in all_mid_history)  / n_runs for i in range(steps)]
    avg_up   = [sum(run[i] for run in all_up_history)   / n_runs for i in range(steps)]

    # Compute statistics
    mean_final_gini   = round(sum(all_final_gini) / n_runs, 4)
    mean_average_gini = round(sum(all_average_gini) / n_runs, 4)
    mean_low          = round(sum(all_low) / n_runs, 1)
    mean_mid          = round(sum(all_mid) / n_runs, 1)
    mean_up           = round(sum(all_up)  / n_runs, 1)

    # Standard deviation of final Gini across runs
    variance = sum((g - mean_final_gini) ** 2 for g in all_final_gini) / n_runs
    std_final_gini = round(math.sqrt(variance), 4)

    # Generate plot of averaged results
    base  = os.path.splitext(os.path.basename(filename))[0]
    title = base.replace("_", " ").title() + f" (Averaged {n_runs} Runs)"

    plot_wealth_distribution(
        gini_history=avg_gini,
        low_history=avg_low,
        mid_history=avg_mid,
        up_history=avg_up,
        filename=filename,
        title=title,
    )

    return {
        "n_runs":             n_runs,
        "steps":              steps,
        "mean_final_gini":    mean_final_gini,
        "std_final_gini":     std_final_gini,
        "mean_average_gini":  mean_average_gini,
        "mean_low_class":     mean_low,
        "mean_mid_class":     mean_mid,
        "mean_up_class":      mean_up,
        "all_final_gini":     all_final_gini,
        "parameters": {
            "num_people":            num_people,
            "max_vision":            max_vision,
            "metabolism_max":        metabolism_max,
            "percent_best_land":     percent_best_land,
            "life_expectancy_min":   life_expectancy_min,
            "life_expectancy_max":   life_expectancy_max,
            "grain_growth_interval": grain_growth_interval,
            "num_grain_grown":       num_grain_grown,
        },
        "policy_active":       tax_rate > 0 or redistribution_rate > 0 or welfare_boost > 0,
        "tax_rate":            tax_rate,
        "redistribution_rate": redistribution_rate,
        "welfare_boost":       welfare_boost,
        "policy_description":  policy_description,
        "plot_saved_to":       os.path.abspath(filename),
    }





# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")