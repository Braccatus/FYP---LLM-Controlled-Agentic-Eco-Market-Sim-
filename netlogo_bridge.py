"""
netlogo_bridge.py — Bridge between Python and the NetLogo Wealth Distribution model.

APPROACH: NetLogo Headless with embedded BehaviorSpace experiment.
    1. Reads the Wealth Distribution model file
    2. Patches parameter values in the BehaviorSpace experiment
    3. Optionally injects policy code (taxation, redistribution, welfare)
       directly into the model's NetLogo procedures
    4. Runs NetLogo headless on the temporary patched copy
    5. Parses the CSV output and returns structured results

POLICY INJECTION:
    When policy parameters are provided, new NetLogo code is injected into
    the go procedure to simulate policy interventions:
    - tax_rate:           % of wealth taken from upper class (blue) agents each tick
    - redistribution_rate: % of collected tax redistributed to lower class agents
    - welfare_boost:      flat grain bonus given to low class (red) agents each tick
"""

import os
import re
import csv
import subprocess
import tempfile
import time
from typing import Dict, Any, Optional

# ── Constants ─────────────────────────────────────────────────────────────────

NETLOGO_HEADLESS = r"C:\Program Files\NetLogo 7.0.2\netlogo-headless.bat"

MODEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "Wealth Distribution.nlogox",
)

TIMEOUT_SECONDS = 180


# ── Policy code generator ─────────────────────────────────────────────────────

def _generate_policy_procedure(
    tax_rate: float,
    redistribution_rate: float,
    welfare_boost: float,
) -> str:
    """
    Generate a NetLogo procedure that implements policy interventions.

    The procedure:
    1. Taxes upper class (blue) agents by removing tax_rate% of their wealth
    2. Collects total tax revenue across all upper class agents
    3. Redistributes redistribution_rate% of that revenue equally among
       lower class (red) agents
    4. Gives welfare_boost grain directly to every lower class agent

    Returns a string of valid NetLogo code to be injected into the model.
    """
    # Convert percentages to decimals for NetLogo
    tax_decimal   = round(tax_rate / 100.0, 4)
    redis_decimal = round(redistribution_rate / 100.0, 4)
    welfare       = round(welfare_boost, 2)

    procedure = f"""
;; ── Policy interventions (injected by LLM agent) ──────────────────────────
to apply-policy
  ;; Step 1: Tax upper class agents (blue = wealthy)
  let total-tax-collected 0
  ask turtles with [color = blue] [
    let tax-amount floor (wealth * {tax_decimal})
    set wealth (wealth - tax-amount)
    set total-tax-collected (total-tax-collected + tax-amount)
  ]

  ;; Step 2: Redistribute a portion of tax revenue to lower class agents
  let redistribution-pool floor (total-tax-collected * {redis_decimal})
  let num-poor count turtles with [color = red]
  if num-poor > 0 [
    let share-per-agent floor (redistribution-pool / num-poor)
    ask turtles with [color = red] [
      set wealth (wealth + share-per-agent)
    ]
  ]

  ;; Step 3: Direct welfare boost to lower class agents
  if {welfare} > 0 [
    ask turtles with [color = red] [
      set wealth (wealth + {welfare})
    ]
  ]
end
;; ── End policy interventions ───────────────────────────────────────────────
"""
    return procedure


def _inject_policy_into_model(
    model_content: str,
    tax_rate: float,
    redistribution_rate: float,
    welfare_boost: float,
) -> str:
    """
    Inject policy procedures into the model's NetLogo code and add a call
    to apply-policy inside the go procedure.

    Strategy:
    1. Add the apply-policy procedure definition before the copyright comment
    2. Add a call to apply-policy inside the go procedure after harvest
    """
    # Generate the policy procedure code
    policy_code = _generate_policy_procedure(tax_rate, redistribution_rate, welfare_boost)

    # Inject the procedure definition before the copyright comment at end of code
    copyright_marker = "; Copyright 1998 Uri Wilensky."
    if copyright_marker in model_content:
        model_content = model_content.replace(
            copyright_marker,
            policy_code + "\n" + copyright_marker
        )
    else:
        # Fallback: append before closing CDATA tag
        model_content = model_content.replace("]]></code>", policy_code + "\n]]></code>")

    # Add apply-policy call inside the go procedure, after harvest
    # The go procedure contains: ask turtles [ move-eat-age-die ]
    # We add apply-policy after the harvest call and before recolor-turtles
    go_injection_target = "  ask turtles\n    [ move-eat-age-die ]"
    go_with_policy = "  ask turtles\n    [ move-eat-age-die ]\n  apply-policy"

    if go_injection_target in model_content:
        model_content = model_content.replace(go_injection_target, go_with_policy)

    return model_content


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
    Update the enumeratedValueSet values in the BehaviorSpace experiment
    and update the timeLimit steps.
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
    """Parse the BehaviorSpace table CSV output."""
    gini_history      = []
    low_class_history = []
    mid_class_history = []
    up_class_history  = []

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    header_idx = None
    for i, row in enumerate(rows):
        if any("gini-index-reserve" in cell for cell in row):
            header_idx = i
            break

    if header_idx is None:
        raise ValueError("Could not find header row in CSV output")

    headers  = rows[header_idx]
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
    tax_rate: float = 0.0,
    redistribution_rate: float = 0.0,
    welfare_boost: float = 0.0,
    policy_description: str = "",
) -> Dict[str, Any]:
    """
    Run the Wealth Distribution NetLogo model via headless BehaviorSpace.

    Standard parameters configure the simulation environment.
    Policy parameters inject behavioural rules directly into the model code:

    Args:
        tax_rate (0-50):          % of wealth taken from upper class agents each tick.
                                  Use for progressive taxation scenarios.
                                  Example: tax_rate=20 removes 20% from blue agents.
        redistribution_rate (0-100): % of collected tax redistributed to poor agents.
                                  Use with tax_rate for redistribution policies.
                                  Example: redistribution_rate=80 gives 80% of tax
                                  revenue back to red agents equally.
        welfare_boost (0-10):     Flat grain bonus given to every poor agent each tick.
                                  Use for direct welfare payment scenarios.
                                  Example: welfare_boost=3 gives 3 grain to all red agents.
        policy_description:       Human-readable description of the policy applied
                                  (returned in results for agent interpretation).
    """
    # Clamp standard parameters
    num_people            = max(10,  min(int(num_people),            500))
    max_vision            = max(1,   min(int(max_vision),            10))
    metabolism_max        = max(1,   min(int(metabolism_max),        25))
    percent_best_land     = max(1,   min(int(percent_best_land),     25))
    life_expectancy_min   = max(1,   min(int(life_expectancy_min),   10))
    life_expectancy_max   = max(20,  min(int(life_expectancy_max),   100))
    grain_growth_interval = max(1,   min(int(grain_growth_interval), 10))
    num_grain_grown       = max(1,   min(int(num_grain_grown),       10))
    steps                 = max(50,  min(int(steps),                 300))

    # Clamp policy parameters
    tax_rate            = max(0.0,  min(float(tax_rate),            50.0))
    redistribution_rate = max(0.0,  min(float(redistribution_rate), 100.0))
    welfare_boost       = max(0.0,  min(float(welfare_boost),       10.0))

    if life_expectancy_min >= life_expectancy_max:
        life_expectancy_min = life_expectancy_max - 1

    policy_active = tax_rate > 0 or redistribution_rate > 0 or welfare_boost > 0

    # Read the model file
    with open(MODEL_PATH, "r", encoding="utf-8") as f:
        model_content = f.read()

    # Patch standard parameters
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

    # Inject policy code if any policy parameters are set
    if policy_active:
        print(f"[NetLogo] Injecting policy: tax={tax_rate}%, "
              f"redistribution={redistribution_rate}%, welfare_boost={welfare_boost}")
        patched_content = _inject_policy_into_model(
            patched_content,
            tax_rate=tax_rate,
            redistribution_rate=redistribution_rate,
            welfare_boost=welfare_boost,
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_model = os.path.join(tmpdir, "wealth_sim.nlogox")
        csv_path   = os.path.join(tmpdir, "results.csv")

        with open(temp_model, "w", encoding="utf-8") as f:
            f.write(patched_content)

        cmd = (
            f'"{NETLOGO_HEADLESS}" --model "{temp_model}" '
            f'--experiment wealth_sim --table "{csv_path}" --threads 1'
        )

        print(f"[NetLogo] Running {steps} steps...")
        start_time = time.time()

        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=TIMEOUT_SECONDS, shell=True,
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
        "policy_active":         policy_active,
        "tax_rate":              tax_rate,
        "redistribution_rate":   redistribution_rate,
        "welfare_boost":         welfare_boost,
        "policy_description":    policy_description,
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
    print("=" * 50)
    print("Test 1: Baseline (no policy)")
    print("=" * 50)
    r1 = run_wealth_distribution(steps=100)
    print(f"  final_gini: {r1['final_gini']}  "
          f"low: {r1['low_class_final']}  "
          f"mid: {r1['mid_class_final']}  "
          f"up: {r1['up_class_final']}")

    print("\n" + "=" * 50)
    print("Test 2: 30% wealth tax on rich, 80% redistributed to poor")
    print("=" * 50)
    r2 = run_wealth_distribution(
        steps=100,
        tax_rate=30.0,
        redistribution_rate=80.0,
        welfare_boost=2.0,
        policy_description="30% progressive wealth tax with 80% redistribution to low class",
    )
    print(f"  final_gini: {r2['final_gini']}  "
          f"low: {r2['low_class_final']}  "
          f"mid: {r2['mid_class_final']}  "
          f"up: {r2['up_class_final']}")

    print("\nGini comparison:")
    print(f"  Baseline:    {r1['final_gini']}")
    print(f"  With policy: {r2['final_gini']}")
    reduction = r1['final_gini'] - r2['final_gini']
    print(f"  Reduction:   {reduction:.4f} ({'+' if reduction > 0 else ''}{reduction:.1f} points)")