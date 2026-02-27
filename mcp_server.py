"""
MCP Server for your toy macro-market simulation.

Exposes your existing Python functions as MCP tools:
- run_simulation(...)
- plot_economy_from_run(...)

Run:
  python mcp_server.py

This server uses stdio transport (most common for local MCP usage).
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from simulation import run_simulation
from plotter import plot_economy

print("MCP SERVER STARTED")

mcp = FastMCP("toy-macro-market-sim")


@mcp.tool()
def run_macro_simulation(
    interest_rate: float,
    steps: int = 80,
    demand_shock: float = 0.0,
    supply_shock: float = 0.0,
    uncertainty_shock: float = 0.0,
    regulation_shock: float = 0.0,
    fiscal_shock: float = 0.0,
) -> Dict[str, Any]:
    """
    Run the simulation and return the full results dict (including series_* arrays).
    """
    return run_simulation(
        interest_rate=interest_rate,
        steps=steps,
        demand_shock=demand_shock,
        supply_shock=supply_shock,
        uncertainty_shock=uncertainty_shock,
        regulation_shock=regulation_shock,
        fiscal_shock=fiscal_shock,
    )


@mcp.tool()
def plot_economy_from_run(
    run: Dict[str, Any],
    filename: str = "phaseA_sim.png",
) -> Dict[str, Any]:
    """
    Create the standard macro-style plot from a simulation run dict.

    Expects run to contain:
      - series_price
      - series_demand
      - series_spread

    Returns metadata about the saved plot.
    """
    plot_economy(
        run["series_price"],
        run["series_demand"],
        run["series_spread"],
        filename=filename,
    )
    return {"saved_to": filename}


@mcp.tool()
def summarize_run(run: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return a compact summary (drops full series_* arrays).
    Useful for follow-up Q&A without stuffing the context window.
    """
    return {k: v for k, v in run.items() if not k.startswith("series_")}


if __name__ == "__main__":
    # stdio transport = MCP client launches this as a subprocess and talks over stdin/stdout
    mcp.run(transport="stdio")
