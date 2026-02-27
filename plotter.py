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
    filename: str = "phaseA_sim.png",
):
    """
    Plot price and demand on the left axis, credit spread on the right axis.
    This gives a more interesting, 'macro-style' chart.
    """
    fig, ax1 = plt.subplots(figsize=(8, 4))

    steps = range(len(prices))

    # Price & demand on left axis
    ax1.plot(steps, prices, label="Price")
    ax1.plot(steps, demands, label="Demand", linestyle="--")
    ax1.set_xlabel("Step")
    ax1.set_ylabel("Price / Demand Index")
    ax1.set_title("Toy Macro-Market Simulation")
    ax1.legend(loc="upper left")

    # Credit spread on right axis
    ax2 = ax1.twinx()
    ax2.plot(steps, spreads, label="Credit Spread", linestyle=":", alpha=0.8)
    ax2.set_ylabel("Credit Spread")

    fig.tight_layout()
    fig.savefig(filename)
    plt.close(fig)
