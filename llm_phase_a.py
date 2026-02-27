import json
from typing import Dict, Any

from mirascope import llm
from simulation import run_simulation
from plotter import plot_economy

PRESET_SCENARIOS = {
    "1": "The central bank raises interest rates by 2 percentage points to fight high inflation.",
    "2": "The central bank cuts interest rates to near zero after a recession to stimulate growth.",
    "3": "A sudden energy price shock increases production costs for firms across the economy.",
    "4": "A housing boom driven by cheap credit causes rapid increases in house prices.",
    "5": "The government announces large-scale infrastructure spending financed by borrowing.",
    "6": "Consumer confidence falls sharply after a financial crisis, reducing household spending.",
    "7": "A new technology sector bubble forms as investors pour money into unprofitable startups.",
    "8": "The government implements austerity measures, cutting public spending to reduce debt.",
}


def get_user_scenario() -> str:
    print("How would you like to provide the scenario?\n")
    print("  1) Type my own scenario")
    print("  2) Choose from preset examples\n")

    mode = input("> ").strip()

    if mode == "2":
        print("\nPreset scenarios:")
        for key, text in PRESET_SCENARIOS.items():
            print(f"  {key}) {text}")
        choice = input("\nSelect a preset number (or press Enter to go back):\n> ").strip()

        if choice in PRESET_SCENARIOS:
            scenario = PRESET_SCENARIOS[choice]
            print(f"\nYou selected:\n{scenario}\n")
            return scenario
        else:
            print("\nInvalid choice or empty input – switching to custom scenario.\n")

    # Fallback: custom scenario
    scenario = input("Describe an economic scenario in your own words:\n> ")
    return scenario


# 1) Ask the LLM to convert a text scenario into numeric parameters
@llm.call(provider="openai", model="gpt-4.1-mini")
def choose_parameters(description: str) -> str:
    return f"""
You are configuring a toy macro/market simulation using a small set of generic shocks.

Given the scenario description, choose values for:

- interest_rate: a float in percent, typically between 0 and 10.
- demand_shock: a float between -1 and +1
    - -1 = very negative demand shock (strong drop in spending/activity)
    -  0 = neutral
    - +1 = very positive demand shock (strong boost to demand)
- supply_shock: a float between -1 and +1
    - -1 = severe supply disruption (shortages, bottlenecks)
    -  0 = neutral
    - +1 = strong positive supply shock (productivity, extra capacity)
- uncertainty_shock: a float between 0 and 1
    - 0 = environment feels very stable and predictable
    - 1 = extremely uncertain and risky
- regulation_shock: a float between 0 and 1
    - 0 = no relevant regulatory change
    - 1 = very strong regulatory tightening
- fiscal_shock: a float between -1 and +1
    - -1 = severe austerity (spending cuts, tax hikes)
    -  0 = neutral fiscal stance
    - +1 = strong stimulus (spending increases, tax cuts)
- steps: an integer between 50 and 300 (how many time steps the simulation runs)

Respond ONLY with a single valid JSON object with this exact structure
and field names (no comments, no extra keys, no explanations):

{{
  "interest_rate": 1.5,
  "demand_shock": -0.2,
  "supply_shock": 0.0,
  "uncertainty_shock": 0.4,
  "regulation_shock": 0.3,
  "fiscal_shock": 0.1,
  "steps": 150
}}

Fill in the values appropriately for this scenario:

Scenario:
{description}
"""


# 2) LLM: results -> explanation, with tutor style
@llm.call(provider="openai", model="gpt-4.1-mini")
def explain_results(
    description: str,
    results: Dict[str, Any],
    tutor_style: str,
) -> str:
    return f"""
You are acting as a {tutor_style} explaining the outcome of a toy macro/market simulation
to a university student.

The simulation includes three main variables over time:
- price: a market/asset price
- demand: an index of aggregate demand / economic activity (100 = 'normal')
- credit_spread: a proxy for financial stress (higher = tighter financial conditions)

The mechanics:
- Higher interest_rate tends to lower demand and increase credit_spread relative to normal.
- A 'fundamental' price is computed from demand and credit_spread.
- The market price moves gradually toward this fundamental value plus some noise.

The results dict includes summary statistics:
- interest_rate, steps
- final_price, average_price, price_volatility
- average_demand
- recession_steps (how many steps demand was below a "weak demand" threshold)
- overheating_steps (how many steps demand was above a "strong demand" threshold)
- max_credit_spread, min_credit_spread

The results dict also includes a "shocks" object with:
- demand_shock
- supply_shock
- uncertainty_shock
- regulation_shock
- fiscal_shock

These shocks summarise how the scenario was interpreted. Use them to explain the 
economic meaning of the scenario (e.g., negative demand shock means weak consumer 
activity). If the simulation does not explicitly include all shocks numerically, 
still discuss their conceptual impact.

Your job:
1. Briefly restate the scenario in your own words.
2. Explain how the interest_rate likely affected demand, credit spreads, and price dynamics.
3. Interpret the summary statistics, especially price_volatility, average_demand,
   recession_steps, and max_credit_spread.
4. Provide an interpretation from the perspective of a {tutor_style}
   (policy implications, portfolio implications, or social implications).
5. Keep it concise but clear (2–4 short paragraphs).

Scenario:
{description}

Simulation results (Python dict):
{results}
"""


def run_scenario(description: str, tutor_style: str):
    # --- Ask LLM for parameters ---
    param_response = choose_parameters(description)
    params_text = getattr(param_response, "content", str(param_response))
    print("\n--- Raw LLM parameter JSON ---")
    print(params_text)

        # Clean up LLM output in case it wrapped JSON in ``` fences
    raw = params_text.strip()

    # If the model returns a markdown code block, strip the fences
    if raw.startswith("```"):
        # Remove leading/trailing fences
        raw = raw.strip("`")
        # Sometimes it starts with 'json\n{...'
        if raw.lower().startswith("json"):
            raw = raw[4:]  # drop 'json'
        raw = raw.strip()

    # Extract just the JSON object between the first '{' and last '}'
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"Could not find JSON object in LLM output:\n{params_text}")

    json_str = raw[start:end]

    # Now parse
    params = json.loads(json_str)

    interest_rate = float(params["interest_rate"])
    steps = int(params["steps"])


    # Extract shock parameters (with safe defaults if something is missing)
    shocks = {
        "demand_shock": float(params.get("demand_shock", 0.0)),
        "supply_shock": float(params.get("supply_shock", 0.0)),
        "uncertainty_shock": float(params.get("uncertainty_shock", 0.0)),
        "regulation_shock": float(params.get("regulation_shock", 0.0)),
        "fiscal_shock": float(params.get("fiscal_shock", 0.0)),
    }

    # --- Run simulation ---
    sim_results = run_simulation(
        interest_rate=interest_rate,
        steps=steps,
        demand_shock=shocks["demand_shock"],
        supply_shock=shocks["supply_shock"],
        uncertainty_shock=shocks["uncertainty_shock"],
        regulation_shock=shocks["regulation_shock"],
        fiscal_shock=shocks["fiscal_shock"],
    )

    # Attach shocks to results so the LLM can talk about them
    sim_results_with_shocks = dict(sim_results)
    sim_results_with_shocks["shocks"] = shocks

    # --- Plot time series ---
    plot_economy(
        sim_results["series_price"],
        sim_results["series_demand"],
        sim_results["series_spread"],
        filename="phaseA_sim.png",
    )
    print("\nPlot saved as phaseA_sim.png")

    # --- Ask LLM to explain with chosen tutor style ---
    explanation_response = explain_results(description, sim_results_with_shocks, tutor_style)
    explanation_text = getattr(explanation_response, "content", str(explanation_response))

    # --- Print nice summary ---
    print("\n=== PARAMETERS USED ===")
    print({"interest_rate": interest_rate, "steps": steps})

    print("\n=== SIMULATION SUMMARY (without full series) ===")
    summary = {k: v for k, v in sim_results_with_shocks.items() if not k.startswith("series_")}
    print(summary)

    print("\n=== LLM EXPLANATION ({}) ===".format(tutor_style))
    print(explanation_text)

    # --- Conversational follow-up loop ---
    while True:
        print("\nAsk a follow-up question about the scenario.")
        print("Type 'new' to run a new scenario, or 'quit' to exit.")
        user_q = input("> ").strip()

        if user_q.lower() in ["quit", "exit"]:
            print("Goodbye!")
            break

        if user_q.lower() == "new":
            print("\nReturning to main menu...\n")
            return  # exits run_scenario and returns to __main__

        # Generate follow-up answer
        follow_resp = follow_up_answer(
            description,
            summary,   # use the summary, not full series
            tutor_style,
            user_q,
        )
        follow_text = getattr(follow_resp, "content", str(follow_resp))

        print("\n=== FOLLOW-UP RESPONSE ===")
        print(follow_text)


@llm.call(provider="openai", model="gpt-4.1-mini")
def follow_up_answer(
    scenario: str,
    results: Dict[str, Any],
    tutor_style: str,
    question: str,
) -> str:
    return f"""
You are continuing a conversation as a {tutor_style}.

The user previously ran a simulation based on this scenario:
"{scenario}"

The results summary is:
{results}

The user now asks a follow-up question:
"{question}"

Your response should:
- Stay consistent with the earlier simulation outcome
- Use the chosen perspective: {tutor_style}
- Be concise but helpful (1–3 paragraphs max)
- Provide additional insight grounded in the data above
- If the question asks about changing parameters (e.g. lower interest rate),
  answer conceptually (do NOT re-run the simulation)

Answer the user's follow-up question now.
"""


if __name__ == "__main__":
    # Step 1: scenario (custom or preset)
    scenario = get_user_scenario()

    # Step 2: choose tutor style
    print("\nChoose explanation style:")
    print("  1) economist")
    print("  2) investor")
    print("  3) sociologist")
    choice = input("> ").strip()

    style_map = {
        "1": "economist",
        "2": "investment advisor",
        "3": "sociologist",
    }
    tutor_style = style_map.get(choice, "economist")

    run_scenario(scenario, tutor_style)
