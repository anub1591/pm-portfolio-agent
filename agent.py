"""
agent.py — Orchestration loop for the PM Portfolio Agent.

Takes a plain-English business question, lets Claude decide which
tool(s) in tools.py to call, executes them, and returns a reasoned
final answer. Also returns the reasoning trace so the frontend can
show "what the agent checked" — this is the differentiator, don't
strip it out in app.py.

Requires: ANTHROPIC_API_KEY environment variable set.
"""

import os
import json
import anthropic
from tools import (
    get_at_risk_projects,
    check_resource_allocation,
    check_budget_variance,
    get_project_summary,
)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

MODEL = "claude-sonnet-4-6"

# ---------------------------------------------------------------
# Tool definitions Claude sees. Keep descriptions concrete — Claude
# picks tools based on these, so vague descriptions = wrong tool calls.
# ---------------------------------------------------------------
TOOLS = [
    {
        "name": "get_at_risk_projects",
        "description": "Returns all projects currently flagged 'At Risk' or 'Delayed', with budget variance, sprint velocity trend, blocked story count, and a human-written risk note for each. Use this for any question about which projects are struggling, at risk, delayed, or need attention.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "check_resource_allocation",
        "description": "Returns each person's total allocation percentage across all their assigned projects for a given month, flagging anyone over 100% (overallocated). Use this for any question about who's overallocated, over capacity, spread thin, or available/free next month.",
        "input_schema": {
            "type": "object",
            "properties": {
                "person": {"type": "string", "description": "Optional. Filter to a specific person's name (partial match ok)."},
                "month": {"type": "string", "description": "Optional. Format YYYY-MM, e.g. '2026-08'. If omitted, returns all months."},
            },
            "required": [],
        },
    },
    {
        "name": "check_budget_variance",
        "description": "Returns planned vs. actual budget, variance amount, and variance percentage for one project or all projects. Use this for any question about budget, cost overrun, spend, or whether a project is over/under budget.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Optional. e.g. 'P01'. If omitted, returns all projects."},
            },
            "required": [],
        },
    },
    {
        "name": "get_project_summary",
        "description": "Returns full detail for a single named project: status, dates, budget, velocity, blockers, and current team roster. Use this when the user asks about one specific project by name or ID, or wants a general status update on it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Required. Either the project ID (e.g. 'P01') or the project's name, full or partial (e.g. 'Fraud Detection'). Do not guess an ID if you only have a name — pass the name text directly, this tool will resolve it."},
            },
            "required": ["project_id"],
        },
    },
]

TOOL_FUNCTIONS = {
    "get_at_risk_projects": lambda **kwargs: get_at_risk_projects(),
    "check_resource_allocation": lambda **kwargs: check_resource_allocation(**kwargs),
    "check_budget_variance": lambda **kwargs: check_budget_variance(**kwargs),
    "get_project_summary": lambda **kwargs: get_project_summary(**kwargs),
}

SYSTEM_PROMPT = """You are a portfolio management assistant for business stakeholders \
(PMs, directors, execs) who are NOT technical and don't know SQL or Tableau. \
They ask plain-English questions about project health, budget, and team capacity.

Use the tools available to look up real data before answering — never guess or \
make up numbers. If a question needs more than one tool (e.g. "which at-risk \
projects also have an overallocated team member"), call multiple tools and \
combine the results yourself.

When you answer:
- Lead with the direct answer, not a summary of what you did.
- Use specific numbers and project/person names from the tool results.
- Keep it business-readable — no jargon, no code, no raw JSON.
- If nothing matches (e.g. no one is overallocated), say so plainly.
"""


def ask_agent(question: str, verbose: bool = True):
    """
    Runs the full tool-use loop for a single question.

    Args:
        question (str): the user's plain-English question.
        verbose (bool): if True, also returns the reasoning trace
                         (which tools were called, with what args,
                         and what they returned) for display in the UI.

    Returns:
        dict: {"answer": str, "trace": list[dict]}
    """
    messages = [{"role": "user", "content": question}]
    trace = []

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # If Claude didn't ask for a tool, we're done — extract final text.
        if response.stop_reason != "tool_use":
            final_text = "".join(
                block.text for block in response.content if block.type == "text"
            )
            return {"answer": final_text, "trace": trace}

        # Otherwise, run every requested tool call and feed results back.
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            tool_name = block.name
            tool_input = block.input or {}
            fn = TOOL_FUNCTIONS.get(tool_name)

            try:
                result = fn(**tool_input) if fn else {"error": f"Unknown tool: {tool_name}"}
            except Exception as e:
                result = {"error": str(e)}

            trace.append({
                "tool": tool_name,
                "input": tool_input,
                "result": result,
            })

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result),
            })

        messages.append({"role": "user", "content": tool_results})


if __name__ == "__main__":
    # Quick manual test — run `python agent.py` with ANTHROPIC_API_KEY set.
    test_questions = [
        "Which projects are at risk this sprint?",
        "Who's overallocated in August?",
        "Give me a status update on the Fraud Detection ML Model project.",
    ]
    for q in test_questions:
        print(f"\nQ: {q}")
        result = ask_agent(q)
        print(f"A: {result['answer']}")
        print(f"(tools called: {[t['tool'] for t in result['trace']]})")
