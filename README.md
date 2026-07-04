# PM Portfolio Agent

An AI assistant that lets non-technical business stakeholders — PMs, directors, execs — ask plain-English questions about a project portfolio and get real, data-backed answers. No SQL, no dashboard training required.

Built with the Anthropic API (Claude, tool use) and Streamlit.

> "Which projects are at risk this sprint?"
> "Who's overallocated next month?"
> "Which at-risk projects also have an overallocated team member?"

The agent reasons over the underlying data, decides which lookups it needs, chains them if the question requires it, and returns a clear, business-readable answer — along with a transparent trace of exactly what it checked.

---

## Why this project exists

Most portfolio dashboards show data. Business users still have to interpret it themselves — cross-referencing a risk report against a resource allocation sheet to answer a question like "is our most at-risk project also short-staffed?"

This project flips that: the AI does the cross-referencing, and gives you the answer in plain language, with the underlying data available if you want to verify it.

It's a companion piece to my [smart meter anomaly detection agent](https://github.com/anub1591/smart-meter-anomaly-agent) — same architecture (Claude API + tool use + Streamlit), applied to a business/PM use case instead of a technical one, to show both sides of where AI meets business operations.

---

## What it does

- **Risk detection** — flags projects that are at-risk or delayed, with the specific reason (budget overrun, declining sprint velocity, blocked stories)
- **Capacity checks** — identifies team members who are overallocated across projects in a given month
- **Budget variance** — planned vs. actual spend, by project
- **Project lookups** — full status pull for any project, by name or ID
- **Multi-step reasoning** — combines the above when a question needs it (e.g. "which at-risk projects also have an overallocated person on them")
- **Transparent reasoning trace** — every answer includes an expandable section showing exactly which tools were called and what data came back

---

## Tech stack

- **Claude (Anthropic API)** — tool use / function calling for reasoning and orchestration
- **Python** — `pandas` for data access
- **Streamlit** — chat-based frontend

---

## Architecture

```
User question (plain English)
        │
        ▼
   agent.py  ── Claude decides which tool(s) to call
        │
        ▼
   tools.py  ── reads projects.csv / allocations.csv, returns structured data
        │
        ▼
   Claude synthesizes a final answer from the tool results
        │
        ▼
   app.py (Streamlit) ── displays the answer + reasoning trace
```

Data model:
- **`projects.csv`** — 10 projects with status, budget (planned/actual), sprint velocity (last 3 sprints), blocked stories, and risk notes
- **`allocations.csv`** — team members mapped to projects with allocation % by month, enabling cross-project capacity checks

Both are synthetic datasets, deliberately constructed with realistic patterns (budget overruns, declining velocity, overallocated team members) so the agent has genuine signal to reason over.

---

## Example interaction

**Q: Which at-risk projects also have an overallocated team member?**

> 4 out of 6 at-risk/delayed projects have at least one overallocated team member. Priya Nair is the most critical case — she's at 140% allocation in July across three projects, all three of which are already flagged at risk...

*(Full reasoning trace showing the two tool calls and underlying data available in the app.)*

---

## Running it locally

```bash
git clone https://github.com/anub1591/pm-portfolio-agent.git
cd pm-portfolio-agent
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here
streamlit run app.py
```

Or run the agent directly from the command line without the UI:
```bash
python3 agent.py
```

---

## Project structure

```
pm-portfolio-agent/
├── app.py              # Streamlit chat interface
├── agent.py             # Orchestration loop (Claude + tool use)
├── tools.py              # Data access functions
├── projects.csv          # Synthetic project portfolio data
├── allocations.csv       # Synthetic team allocation data
└── requirements.txt
```

---

## About

Built by [Anubhav Rastogi](https://anubhav-rastogi.com) — BI/Analytics professional exploring where AI agents meet business operations and project management.
