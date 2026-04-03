"""
plotter.py — Multi-sector economic simulation visualiser.

Generates a two-panel chart:
  - Top panel:    Per-sector price indices + market average
  - Bottom panel: Aggregate demand and credit spread
"""

import os
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np


# Consistent colours per sector
SECTOR_COLORS = {
    "Commodities": "#f4a300",   # amber
    "Technology":  "#1a73e8",   # blue
    "Healthcare":  "#34a853",   # green
    "Crypto":      "#9c27b0",   # purple
    "Financials":  "#e53935",   # red
}


def plot_economy(
    prices,
    demands,
    spreads,
    filename: str = "simulation.png",
    title: str = None,
):
    """
    Legacy single-price plot — kept for backward compatibility.
    Redirects to the multi-sector plotter with a single 'Market' series.
    """
    sector_series  = {"Market": prices}
    market_avg     = prices
    plot_multisector(
        sector_series=sector_series,
        market_avg_series=market_avg,
        demand_series=demands,
        spread_series=spreads,
        filename=filename,
        title=title,
    )


def plot_multisector(
    sector_series: dict,
    market_avg_series: list,
    demand_series: list,
    spread_series: list,
    filename: str = "simulation.png",
    title: str = None,
):
    """
    Plot per-sector price indices, market average, demand and credit spread.

    Top panel:    One line per sector + bold market average line
    Bottom panel: Aggregate demand (left axis) + credit spread (right axis)

    Args:
        sector_series:      dict of {sector_name: [price_per_step]}
        market_avg_series:  list of market average prices per step
        demand_series:      list of demand values per step
        spread_series:      list of credit spread values per step
        filename:           output PNG path
        title:              chart title
    """
    steps = range(len(market_avg_series))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)

    # ── Top panel: sector prices ──
    for sector, prices in sector_series.items():
        color = SECTOR_COLORS.get(sector, "#888888")
        ax1.plot(steps, prices, label=sector, color=color,
                 linewidth=1.2, alpha=0.8)

    # Market average as bold black line
    ax1.plot(steps, market_avg_series, label="Market Average",
             color="black", linewidth=2.0, linestyle="--")

    ax1.axhline(y=100, color="gray", linewidth=0.8, linestyle=":", alpha=0.6)
    ax1.set_ylabel("Price Index (Base = 100)")
    ax1.set_title(title if title else "LLM-Controlled Economic Market Simulation")
    ax1.legend(loc="upper right", fontsize=8, ncol=2)
    ax1.grid(True, alpha=0.2)

    # ── Bottom panel: demand + credit spread ──
    ax2.plot(steps, demand_series, label="Aggregate Demand",
             color="#1a73e8", linewidth=1.5)
    ax2.axhline(y=100, color="gray", linewidth=0.8, linestyle=":", alpha=0.6)
    ax2.set_ylabel("Demand Index")
    ax2.set_xlabel("Step")
    ax2.grid(True, alpha=0.2)

    ax3 = ax2.twinx()
    ax3.plot(steps, spread_series, label="Credit Spread",
             color="#e53935", linewidth=1.2, linestyle=":")
    ax3.set_ylabel("Credit Spread (%)")

    # Combined legend for bottom panel
    lines2, labels2 = ax2.get_legend_handles_labels()
    lines3, labels3 = ax3.get_legend_handles_labels()
    ax2.legend(lines2 + lines3, labels2 + labels3,
               loc="upper right", fontsize=8)

    fig.tight_layout()
    fig.savefig(filename, dpi=150)
    plt.close(fig)

    # Auto-open the chart
    os.startfile(os.path.abspath(filename))


def plot_series(series, filename="plot.png"):
    """Old single-series plot — kept for compatibility."""
    plt.figure(figsize=(8, 4))
    plt.plot(series)
    plt.xlabel("Step")
    plt.ylabel("Price")
    plt.title("Simulated Price Over Time")
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()
    os.startfile(os.path.abspath(filename))