import os
import pyNetLogo

NETLOGO_HOME = r"C:\Program Files\NetLogo 6.4.0"  # Windows example

MODEL_PATH = os.path.join(
    NETLOGO_HOME,
    "models",
    "Sample Models",
    "Biology",
    "Wolf Sheep Predation.nlogo",
)

# optional: if pyNetLogo can't find Java, you can pass jvm_path=...
# NETLOGO = pyNetLogo.NetLogoLink(gui=False, jvm_path="path/to/java")
NETLOGO = pyNetLogo.NetLogoLink(gui=False)  # headless NetLogo instance


def load_model():
    """Load the Wolf Sheep Predation model into NetLogo."""
    NETLOGO.load_model(MODEL_PATH)


def run_once(steps: int = 100, sheep_init: int = 80, wolves_init: int = 50) -> dict:
    """
    Run a single simulation and return some basic stats.
    You can adapt this later to economic models.
    """
    load_model()

    # Set some parameters (these names come from the NetLogo model's sliders)
    NETLOGO.command(f"set initial-number-sheep {sheep_init}")
    NETLOGO.command(f"set initial-number-wolves {wolves_init}")

    # Setup and advance the model
    NETLOGO.command("setup")
    NETLOGO.repeat_command("go", steps)

    # Get some reporters (again, from the NetLogo model)
    sheep_count = NETLOGO.report("count sheep")
    wolf_count = NETLOGO.report("count wolves")
    grass_pct = NETLOGO.report("count patches with [pcolor = green] / count patches")

    return {
        "sheep": sheep_count,
        "wolves": wolf_count,
        "grass_fraction": grass_pct,
    }


def close():
    """Cleanly close the NetLogo instance when you're done."""
    NETLOGO.kill_workspace()