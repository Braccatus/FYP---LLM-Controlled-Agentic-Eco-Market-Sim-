"""
netlogo_plotter.py — Visualisation for NetLogo Wealth Distribution results.

Generates a two-panel chart:
  - Top panel: Gini coefficient over time
  - Bottom panel: Low / mid / upper class agent counts over time
"""

import os
import matplotlib.pyplot as plt


def plot_wealth_distribution(
    gini_history: list,
    low_history: list,
    mid_history: list,
    up_history: list,
    filename: str = "netlogo_wealth.png",
    title: str = None,
):
    """
    Plot Gini index and wealth class distribution over time.
    Automatically opens the chart after saving.

    Args:
        gini_history:   Gini coefficient at each step
        low_history:    Low class agent count at each step
        mid_history:    Mid class agent count at each step
        up_history:     Upper class agent count at each step
        filename:       Output PNG filename
        title:          Optional chart title
    """
    steps = range(len(gini_history))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6), sharex=True)

    # ── Top panel: Gini index ──
    ax1.plot(steps, gini_history, color="purple", linewidth=1.5, label="Gini Index")
    ax1.set_ylabel("Gini Coefficient")
    ax1.set_title(title if title else "NetLogo Wealth Distribution Simulation")
    ax1.legend(loc="upper left")
    ax1.set_ylim(0, 100)
    ax1.grid(True, alpha=0.3)

    # ── Bottom panel: Class counts ──
    ax2.plot(steps, low_history, color="red",   linewidth=1.2, label="Low class")
    ax2.plot(steps, mid_history, color="green", linewidth=1.2, label="Mid class")
    ax2.plot(steps, up_history,  color="blue",  linewidth=1.2, label="Upper class")
    ax2.set_xlabel("Step")
    ax2.set_ylabel("Number of Agents")
    ax2.legend(loc="upper right")
    ax2.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(filename)
    plt.close(fig)

    # Automatically open the chart
    os.startfile(os.path.abspath(filename))