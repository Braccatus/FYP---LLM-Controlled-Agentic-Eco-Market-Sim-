"""
netlogo_bridge.py — Bridge between Python and the NetLogo Wealth Distribution model.

APPROACH: NetLogo Headless with embedded BehaviorSpace experiment.
    1. Reads the Wealth Distribution model file (which contains a saved
       BehaviorSpace experiment called 'wealth_sim')
    2. Creates a temporary copy with the parameter values updated
    3. Runs NetLogo headless on the temporary copy
    4. Parses the CSV output and returns structured results

Model: Wealth Distribution (saved in project folder with wealth_sim experiment)
"""

import os
import re
import csv
import subprocess
import tempfile
import time
from typing import Dict, Any

# ── Constants ─────────────────────────────────────────────────────────────────

NETLOGO_HEADLESS = r"C:\Program Files\NetLogo 7.0.2\netlogo-headless.bat"

# Model saved in project folder with wealth_sim experiment embedded
MODEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "Wealth Distribution.nlogox",
)

TIMEOUT_SECONDS = 180


# ── Model file parameter patcher ──────────────────────────────────────────────

def _patch_model_parameters(
    model_content: str,
    num_people: int,
    max_vision: int,
    metabolism_max: int,
    percent_best_land: int,
    life_expectancy_min: int,
    life_expectancy_max: int,
    grain_growth_interval: int,
    num_grain_grown: int,
    steps: int,
) -> str:
    """
    Update the enumeratedValueSet values in the model's BehaviorSpace experiment.
    Also updates the timeLimit steps.
    """
    params = {
        "num-people":            num_people,
        "max-vision":            max_vision,
        "metabolism-max":        metabolism_max,
        "percent-best-land":     percent_best_land,
        "life-expectancy-min":   life_expectancy_min,
        "life-expectancy-max":   life_expectancy_max,
        "grain-growth-interval": grain_growth_interval,
        "num-grain-grown":       num_grain_grown,
    }

    for param, value in params.items():
        # Match the enumeratedValueSet block for this parameter and update value
        pattern = (
            rf'(<enumeratedValueSet variable="{re.escape(param)}">\s*'
            rf'<value value=")([^"]*)("></value>\s*</enumeratedValueSet>)'
        )
        replacement = rf'\g<1>{value}\g<3>'
        model_content = re.sub(pattern, replacement, model_content)

    # Update timeLimit steps
    model_content = re.sub(
        r'<timeLimit steps="[^"]*"></timeLimit>',
        f'<timeLimit steps="{steps}"></timeLimit>',
        model_content,
    )

    return model_content


# ── CSV Parser ────────────────────────────────────────────────────────────────

def _parse_csv(csv_path: str) -> Dict[str, Any]:
    """
    Parse the BehaviorSpace table CSV output.
    Returns time series for gini and class counts.
    """
    gini_history      = []
    low_class_history = []
    mid_class_history = []
    up_class_history  = []

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    # Find header row containing gini-index-reserve
    header_idx = None
    for i, row in enumerate(rows):
        if any("gini-index-reserve" in cell for cell in row):
            header_idx = i
            break

    if header_idx is None:
        raise ValueError("Could not find header row in CSV output")

    headers = rows[header_idx]

    # Find column indices
    gini_col = next(i for i, h in enumerate(headers) if "gini-index-reserve" in h)
    low_col  = next(i for i, h in enumerate(headers) if "color = red" in h)
    mid_col  = next(i for i, h in enumerate(headers) if "color = green" in h)
    up_col   = next(i for i, h in enumerate(headers) if "color = blue" in h)

    for row in rows[header_idx + 1:]:
        if len(row) <= max(gini_col, low_col, mid_col, up_col):
            continue
        try:
            gini_history.append(float(row[gini_col]))
            low_class_history.append(int(float(row[low_col])))
            mid_class_history.append(int(float(row[mid_col])))
            up_class_history.append(int(float(row[up_col])))
        except (ValueError, IndexError):
            continue

    return {
        "gini_history":      gini_history,
        "low_class_history": low_class_history,
        "mid_class_history": mid_class_history,
        "up_class_history":  up_class_history,
    }


# ── Main simulation function ──────────────────────────────────────────────────

def run_wealth_distribution(
    num_people: int = 250,
    max_vision: int = 5,
    metabolism_max: int = 15,
    percent_best_land: int = 10,
    life_expectancy_min: int = 1,
    life_expectancy_max: int = 83,
    grain_growth_interval: int = 1,
    num_grain_grown: int = 4,
    steps: int = 100,
) -> Dict[str, Any]:
    """
    Run the Wealth Distribution NetLogo model via headless BehaviorSpace.

    Creates a temporary patched copy of the model with the given parameters,
    runs NetLogo headless, parses the CSV and returns structured results.
    """
    # Clamp parameters to safe ranges
    num_people            = max(10,  min(int(num_people),            500))
    max_vision            = max(1,   min(int(max_vision),            10))
    metabolism_max        = max(1,   min(int(metabolism_max),        25))
    percent_best_land     = max(1,   min(int(percent_best_land),     25))
    life_expectancy_min   = max(1,   min(int(life_expectancy_min),   10))
    life_expectancy_max   = max(20,  min(int(life_expectancy_max),   100))
    grain_growth_interval = max(1,   min(int(grain_growth_interval), 10))
    num_grain_grown       = max(1,   min(int(num_grain_grown),       10))
    steps                 = max(50,  min(int(steps),                 300))

    if life_expectancy_min >= life_expectancy_max:
        life_expectancy_min = life_expectancy_max - 1

    # Read the model file
    with open(MODEL_PATH, "r", encoding="utf-8") as f:
        model_content = f.read()

    # Patch the parameters
    patched_content = _patch_model_parameters(
        model_content,
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

    with tempfile.TemporaryDirectory() as tmpdir:
        # Write patched model to temp file
        temp_model = os.path.join(tmpdir, "wealth_sim.nlogox")
        csv_path   = os.path.join(tmpdir, "results.csv")

        with open(temp_model, "w", encoding="utf-8") as f:
            f.write(patched_content)

        # Run NetLogo headless
        cmd = (
            f'"{NETLOGO_HEADLESS}" --model "{temp_model}" '
            f'--experiment wealth_sim --table "{csv_path}" --threads 1'
        )

        print(f"[NetLogo] Running {steps} steps...")
        start_time = time.time()

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            shell=True,
        )

        elapsed = round(time.time() - start_time, 1)
        print(f"[NetLogo] Completed in {elapsed}s")

        if result.returncode != 0:
            raise RuntimeError(f"NetLogo headless failed:\n{result.stderr}")

        series = _parse_csv(csv_path)

    gini_history      = series["gini_history"]
    low_class_history = series["low_class_history"]
    mid_class_history = series["mid_class_history"]
    up_class_history  = series["up_class_history"]

    if not gini_history:
        raise ValueError("No simulation data returned from NetLogo")

    final_gini   = gini_history[-1]
    average_gini = sum(gini_history) / len(gini_history)
    max_gini     = max(gini_history)
    min_gini     = min(gini_history)

    return {
        "num_people":            num_people,
        "max_vision":            max_vision,
        "metabolism_max":        metabolism_max,
        "percent_best_land":     percent_best_land,
        "life_expectancy_min":   life_expectancy_min,
        "life_expectancy_max":   life_expectancy_max,
        "grain_growth_interval": grain_growth_interval,
        "num_grain_grown":       num_grain_grown,
        "steps":                 steps,
        "final_gini":            round(final_gini,   4),
        "average_gini":          round(average_gini, 4),
        "max_gini":              round(max_gini,     4),
        "min_gini":              round(min_gini,     4),
        "low_class_final":       low_class_history[-1],
        "mid_class_final":       mid_class_history[-1],
        "up_class_final":        up_class_history[-1],
        "gini_history":          gini_history,
        "low_class_history":     low_class_history,
        "mid_class_history":     mid_class_history,
        "up_class_history":      up_class_history,
    }


# ── Quick test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Testing NetLogo headless bridge...")
    print("Running Wealth Distribution model (100 steps)\n")

    results = run_wealth_distribution(
        num_people=250,
        metabolism_max=15,
        percent_best_land=10,
        steps=100,
    )

    summary = {k: v for k, v in results.items() if not k.endswith("_history")}
    print("=== RESULTS ===")
    for key, value in summary.items():
        print(f"  {key}: {value}")

    print(f"\nGini at step 50: {results['gini_history'][49]:.2f}")
    print(f"Low class at end: {results['low_class_final']}")
    print(f"Mid class at end: {results['mid_class_final']}")
    print(f"Up class at end:  {results['up_class_final']}")