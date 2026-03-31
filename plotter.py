import os
import matplotlib.pyplot as plt


def plot_series(series, filename="plot.png"):
    """Old single-series plot (kept in case you still want it)."""
    plt.figure(figsize=(8, 4))
    plt.plot(series)
    plt.xlabel("Step")
    plt.ylabel("Price")
    plt.title("Simulated Price Over Time")
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()


def plot_economy(
    prices,
    demands,
    spreads,
    filename: str = "simulation.png",
    title: str = None,
):
    """
    Plot price and demand on the left axis, credit spread on the right axis.
    Automatically opens the saved chart after saving.

    Args:
        prices:   list of price values over time
        demands:  list of demand values over time
        spreads:  list of credit spread values over time
        filename: output PNG filename
        title:    optional chart title — if None, a default title is used
    """
    fig, ax1 = plt.subplots(figsize=(8, 4))

    steps = range(len(prices))

    # Price & demand on left axis
    ax1.plot(steps, prices, label="Price")
    ax1.plot(steps, demands, label="Demand", linestyle="--")
    ax1.set_xlabel("Step")
    ax1.set_ylabel("Price / Demand Index")
    ax1.set_title(title if title else "LLM-Controlled Economic Market Simulation")
    ax1.legend(loc="upper left")

    # Credit spread on right axis
    ax2 = ax1.twinx()
    ax2.plot(steps, spreads, label="Credit Spread", linestyle=":", alpha=0.8)
    ax2.set_ylabel("Credit Spread")
    ax2.legend(loc="upper right")

    fig.tight_layout()
    fig.savefig(filename)
    plt.close(fig)

    # Automatically open the chart in the default image viewer
    os.startfile(os.path.abspath(filename))