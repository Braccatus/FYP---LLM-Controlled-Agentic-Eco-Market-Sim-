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
    steps: int = 200,
) -> Dict[str, Any]:
    """
    Run the NetLogo Wealth Distribution agent-based model.

    Use this tool when the scenario involves:
    - Wealth inequality or redistribution
    - Effects of policy on different income classes
    - Resource scarcity or abundance
    - Agent-level economic behaviour and emergence

    How parameters map to economic scenarios:
        percent_best_land:    Higher = more productive economy / better infrastructure
        num_grain_grown:      Higher = more generous welfare / resource availability
        metabolism_max:       Higher = higher cost of living / consumption
        num_people:           Population size
        max_vision:           Agent awareness / market information access
        life_expectancy_max:  Higher = longer productive lifespans

    Returns:
        final_gini:       Gini coefficient at end (0=equal, 100=totally unequal)
        average_gini:     Average Gini over the simulation
        max_gini:         Peak inequality reached
        min_gini:         Lowest inequality reached
        low_class_final:  Number of agents in low wealth class at end
        mid_class_final:  Number of agents in middle wealth class at end
        up_class_final:   Number of agents in upper wealth class at end
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
    )

    # Return compact summary only
    return {k: v for k, v in results.items() if not k.endswith("_history")}


# ── NetLogo Tool: Wealth Distribution with Plot ───────────────────────────────

@mcp.tool()
def run_netlogo_wealth_plot(
    num_people: int = 250,
    max_vision: int = 5,
    metabolism_max: int = 15,
    percent_best_land: int = 10,
    life_expectancy_min: int = 1,
    life_expectancy_max: int = 83,
    grain_growth_interval: int = 1,
    num_grain_grown: int = 4,
    steps: int = 200,
    filename: str = "netlogo_wealth.png",
) -> Dict[str, Any]:
    """
    Run the NetLogo Wealth Distribution model AND generate a plot.

    Use this as the PRIMARY NetLogo tool. Generates a chart showing:
    - Gini coefficient over time
    - Low / mid / upper class agent counts over time

    Same parameters as run_netlogo_wealth, plus:
        filename: Name of the PNG file to save the chart to

    Returns compact summary plus plot_saved_to path.
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
    )

    # Generate plot
    base = os.path.splitext(os.path.basename(filename))[0]
    title = base.replace("_", " ").title()

    plot_wealth_distribution(
        gini_history=results["gini_history"],
        low_history=results["low_class_history"],
        mid_history=results["mid_class_history"],
        up_history=results["up_class_history"],
        filename=filename,
        title=title,
    )

    summary = {k: v for k, v in results.items() if not k.endswith("_history")}
    summary["plot_saved_to"] = os.path.abspath(filename)

    return summary


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")