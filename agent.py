"""
agent.py  —  Agentic LLM loop for the LLM-Controlled Economic Market Simulation

Architecture:
    User (natural language)
        ↓
    OpenAI GPT-4 Agent  ←─────────────────────────┐
        ↓                                          │
    Decides which tool to call                     │
        ↓                                          │
    MCP Client calls tool on mcp_server.py         │
        ↓                                          │
    Tool result returned to agent ─────────────────┘
        ↓  (when agent is satisfied)
    Final explanation printed to user

The agent autonomously decides:
    - Which tools to call (run_macro_simulation, plot_economy_from_run, summarize_run)
    - In what order to call them
    - How many times to run simulations (e.g. multiple runs to average out noise)
    - When it has enough information to produce a final response
"""

import asyncio
import json
import os
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI


# ── Configuration ────────────────────────────────────────────────────────────

# Path to your mcp_server.py — update this if needed
MCP_SERVER_PATH = os.path.join(os.path.dirname(__file__), "mcp_server.py")

# OpenAI model to use as the agent brain
AGENT_MODEL = "gpt-4o-mini"

# Maximum number of tool-calling rounds before forcing a final answer
# This prevents infinite loops if the agent gets stuck
MAX_ROUNDS = 10

# System prompt — this defines the agent's behaviour and goals
SYSTEM_PROMPT = """
You are an autonomous economic analysis agent. Your job is to help users understand
economic scenarios by running simulations and interpreting the results.

You have access to TWO complementary simulation backends:

── MACRO SIMULATION TOOLS (Python) ──
These model aggregate economic dynamics: price, demand, credit spread.

- run_and_plot (PRIMARY MACRO TOOL): Runs the macro simulation AND generates a chart.
  Always use this first for any new scenario.

- run_macro_simulation: Macro simulation only, no chart. Use for quick comparisons.

- run_and_average: Runs macro simulation N times and averages results plus a plot.
  Use when uncertainty_shock > 0.5 to reduce noise.

── AGENT-BASED SIMULATION TOOLS (NetLogo) ──
These model individual agent behaviour and wealth inequality emergence.

- run_netlogo_wealth_plot (PRIMARY NETLOGO TOOL): Runs the NetLogo Wealth Distribution
  model AND generates a chart showing Gini index and class distribution over time.
  Use this when the scenario involves inequality, welfare, taxation, or resource policy.

- run_netlogo_wealth: Same as above but no chart. Use for quick NetLogo runs.

── YOUR WORKFLOW ──
1. Always start with run_and_plot for macro-level analysis.
2. If the scenario involves inequality, welfare, or resource distribution,
   ALSO call run_netlogo_wealth_plot for agent-level analysis.
3. Interpret BOTH sets of results together in your final response.
4. If uncertainty is high, use run_and_average for more stable macro results.

── MACRO PARAMETER GUIDANCE ──
- interest_rate: float in percent, typically 0–10
- demand_shock: -1 (very weak demand) to +1 (very strong demand)
- supply_shock: -1 (severe disruption) to +1 (strong boost)
- uncertainty_shock: 0 (stable) to 1 (extremely uncertain)
- regulation_shock: 0 (no change) to 1 (very strong tightening)
- fiscal_shock: -1 (severe austerity) to +1 (strong stimulus)
- steps: integer 50–300

── NETLOGO PARAMETER GUIDANCE ──
- percent_best_land: 1–25 (higher = more productive economy / better infrastructure)
- num_grain_grown: 1–10 (higher = more generous welfare / resource availability)
- metabolism_max: 1–25 (higher = higher cost of living)
- num_people: 10–500 (population size)
- steps: always use 50 for NetLogo — it is slow to initialise

Be autonomous. Infer all parameters from the scenario — never ask the user.
Think step by step. After each tool call reflect on results before deciding what to do next.
Always provide a clear, insightful final explanation covering both simulations where relevant.
"""


# ── MCP Tool Helpers ──────────────────────────────────────────────────────────

async def get_tools_from_mcp(session: ClientSession) -> list[dict]:
    """
    Fetches the list of available tools from the MCP server and converts
    them into the format OpenAI expects for function/tool calling.
    """
    tools_response = await session.list_tools()
    openai_tools = []

    for tool in tools_response.tools:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema,
            },
        })

    return openai_tools


async def call_mcp_tool(session: ClientSession, tool_name: str, tool_args: dict) -> Any:
    """
    Calls a specific tool on the MCP server and returns the result.
    Handles both text and structured results.
    """
    print(f"\n  [Tool Call] → {tool_name}")
    print(f"  [Arguments] → {json.dumps(tool_args, indent=2)}")

    result = await session.call_tool(tool_name, tool_args)

    # MCP returns a list of content blocks — extract text content
    content_blocks = result.content
    if not content_blocks:
        return {}

    # If there's a single text block that looks like JSON, parse it
    if len(content_blocks) == 1 and hasattr(content_blocks[0], "text"):
        raw = content_blocks[0].text
        try:
            parsed = json.loads(raw)
            # Print each key-value pair on its own line so nothing gets truncated
            print("  [Tool Result] →")
            for key, value in parsed.items():
                if isinstance(value, float):
                    print(f"    {key}: {value:.4f}")
                else:
                    print(f"    {key}: {value}")
            return parsed
        except (json.JSONDecodeError, TypeError):
            print(f"  [Tool Result] → {raw}")
            return raw

    return content_blocks


# ── Agentic Loop ──────────────────────────────────────────────────────────────

async def run_agent(scenario: str):
    """
    Main agentic loop.

    1. Connects to the MCP server via stdio
    2. Fetches available tools
    3. Runs the OpenAI agent in a loop:
       - Agent decides which tool to call
       - Tool is executed on the MCP server
       - Result is fed back to the agent
       - Repeat until agent produces a final text response

    Returns:
        simulation_summary: the compact results dict from the last tool call
        conversation_history: list of user/assistant messages for follow-up context
    """

    # Server parameters tell the MCP client how to launch your mcp_server.py
    server_params = StdioServerParameters(
        command="python",
        args=[MCP_SERVER_PATH],
    )

    print("\n" + "="*60)
    print("  AGENTIC LLM — ECONOMIC MARKET SIMULATION")
    print("="*60)
    print(f"\nScenario: {scenario}\n")
    print("Connecting to MCP server...")

    # Track the last simulation summary for follow-up context
    simulation_summary = {}

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:

            # Initialise the MCP session
            await session.initialize()
            print("MCP server connected.\n")

            # Fetch tools from MCP server in OpenAI format
            tools = await get_tools_from_mcp(session)
            print(f"Tools available: {[t['function']['name'] for t in tools]}\n")

            # Initialise the conversation with the system prompt and user scenario
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": scenario},
            ]

            client = OpenAI()  # uses OPENAI_API_KEY from environment

            # ── Agentic loop ──────────────────────────────────────────────
            for round_num in range(MAX_ROUNDS):
                print(f"--- Agent Round {round_num + 1} ---")

                # On the first round, force the agent to call a tool.
                # On subsequent rounds, let it decide freely — it may call
                # another tool or produce its final response.
                tool_choice = "required" if round_num == 0 else "auto"

                # Call the OpenAI model
                response = client.chat.completions.create(
                    model=AGENT_MODEL,
                    messages=messages,
                    tools=tools,
                    tool_choice=tool_choice,
                )

                message = response.choices[0].message

                # Add the assistant's response to the conversation history
                messages.append(message)

                # ── Case 1: Agent wants to call one or more tools ──
                if message.tool_calls:
                    for tool_call in message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)

                        # Execute the tool on the MCP server
                        tool_result = await call_mcp_tool(session, tool_name, tool_args)

                        # Store the simulation summary for follow-up context
                        if isinstance(tool_result, dict):
                            simulation_summary = tool_result

                        # Feed the result back into the conversation
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(tool_result),
                        })

                # ── Case 2: Agent has finished and produced a final response ──
                elif message.content:
                    print("\n" + "="*60)
                    print("  AGENT FINAL RESPONSE")
                    print("="*60)
                    print(message.content)
                    print("="*60)

                    # Build clean conversation history for follow-up use
                    # (only user/assistant text messages, no tool call messages)
                    followup_history = [
                        {"role": "assistant", "content": message.content}
                    ]
                    return simulation_summary, followup_history

            # If we hit MAX_ROUNDS without a final response
            print("\n[Warning] Agent reached maximum rounds without a final response.")
            return simulation_summary, []


# ── Follow-up Answer (no tools, uses stored context) ─────────────────────────

def answer_followup(
    scenario: str,
    simulation_summary: dict,
    conversation_history: list,
    question: str,
) -> str:
    """
    Answers a follow-up question using the stored simulation summary and
    conversation history. Does NOT re-run the simulation or reconnect to MCP.
    This is a lightweight single OpenAI call.
    """
    client = OpenAI()

    # Build a focused context message for the follow-up
    context = (
        f"The user previously described this economic scenario:\n{scenario}\n\n"
        f"The simulation produced these results:\n{json.dumps(simulation_summary, indent=2)}\n\n"
        f"You already provided an explanation of these results. "
        f"Now answer the user's follow-up question concisely and insightfully, "
        f"staying consistent with the simulation results above. "
        f"Do NOT re-run the simulation."
    )

    messages = (
        [{"role": "system", "content": context}]
        + conversation_history
        + [{"role": "user", "content": question}]
    )

    response = client.chat.completions.create(
        model=AGENT_MODEL,
        messages=messages,
    )

    return response.choices[0].message.content


# ── Follow-up Conversation Loop ───────────────────────────────────────────────

async def conversation_loop(scenario: str):
    """
    Runs the agent for the initial scenario, then allows the user to
    ask follow-up questions using stored context — no re-running the simulation.
    """
    # Run the main agent and get back the summary + conversation history
    simulation_summary, conversation_history = await run_agent(scenario)

    print("\n\nYou can now ask follow-up questions.")
    print("Type 'new' to run a new scenario, or 'quit' to exit.\n")

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue
        if user_input.lower() in ["quit", "exit"]:
            print("Goodbye!")
            break
        if user_input.lower() == "new":
            new_scenario = input("\nDescribe a new economic scenario:\n> ").strip()
            simulation_summary, conversation_history = await run_agent(new_scenario)
            scenario = new_scenario
        else:
            # Answer using stored context — no MCP reconnection, no tool calls
            print("\n" + "="*60)
            print("  FOLLOW-UP RESPONSE")
            print("="*60)
            answer = answer_followup(
                scenario,
                simulation_summary,
                conversation_history,
                user_input,
            )
            print(answer)
            print("="*60 + "\n")

            # Add this exchange to history so future follow-ups have full context
            conversation_history.append({"role": "user", "content": user_input})
            conversation_history.append({"role": "assistant", "content": answer})


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\nLLM-Controlled Economic Market Simulation — Agentic Mode")
    print("-" * 55)
    scenario = input("Describe an economic scenario:\n> ").strip()

    if not scenario:
        scenario = "The central bank raises interest rates by 3 percentage points to combat high inflation."

    asyncio.run(conversation_loop(scenario))