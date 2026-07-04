"""
tools.py — Data-access functions for the PM Portfolio Agent.

These are the "tools" exposed to Claude via the Anthropic tool-use API.
Each function reads from the local CSVs and returns clean, structured
data (list of dicts) that Claude can reason over and summarize for
a business user.

Expected folder structure:
    pm-portfolio-agent/
        data/
            projects.csv
            allocations.csv
        tools.py
        agent.py
        app.py
"""

import pandas as pd
import os

DATA_DIR = os.path.dirname(__file__)
PROJECTS_PATH = os.path.join(DATA_DIR, "projects.csv")
ALLOCATIONS_PATH = os.path.join(DATA_DIR, "allocations.csv")


def _load_projects():
    return pd.read_csv(PROJECTS_PATH)


def _load_allocations():
    return pd.read_csv(ALLOCATIONS_PATH)


def get_at_risk_projects():
    """
    Returns all projects with status 'At Risk' or 'Delayed', along with
    the reason (budget variance %, velocity trend, blocked stories).

    Returns:
        list[dict]: one entry per at-risk/delayed project.
    """
    df = _load_projects()
    flagged = df[df["status"].isin(["At Risk", "Delayed"])].copy()

    flagged["budget_variance_pct"] = round(
        (flagged["budget_actual"] - flagged["budget_planned"])
        / flagged["budget_planned"] * 100, 1
    )
    flagged["velocity_trend"] = flagged.apply(
        lambda r: "declining" if r["sprint_velocity_3"] < r["sprint_velocity_1"] else "stable/improving",
        axis=1
    )

    results = []
    for _, r in flagged.iterrows():
        results.append({
            "project_id": r["project_id"],
            "project_name": r["project_name"],
            "status": r["status"],
            "percent_complete": int(r["percent_complete"]),
            "budget_variance_pct": r["budget_variance_pct"],
            "velocity_trend": r["velocity_trend"],
            "sprint_velocity_last3": [r["sprint_velocity_1"], r["sprint_velocity_2"], r["sprint_velocity_3"]],
            "blocked_stories": int(r["blocked_stories"]),
            "risk_notes": r["risk_notes"],
        })
    return results


def check_resource_allocation(person: str = None, month: str = None):
    """
    Sums each person's allocation_pct across all their projects for a
    given month, and flags anyone over 100%.

    Args:
        person (str, optional): filter to a specific person (case-insensitive, partial match ok).
        month (str, optional): filter to a specific month, format 'YYYY-MM' (e.g. '2026-08').
                                If omitted, all months are included.

    Returns:
        list[dict]: one entry per person (per month if month spans multiple),
                    with total allocation and per-project breakdown.
    """
    df = _load_allocations()

    if month:
        df = df[df["month"] == month]
    if person:
        df = df[df["person_name"].str.contains(person, case=False, na=False)]

    results = []
    for (name, mo), group in df.groupby(["person_name", "month"]):
        total = int(group["allocation_pct"].sum())
        results.append({
            "person_name": name,
            "month": mo,
            "total_allocation_pct": total,
            "overallocated": total > 100,
            "projects": [
                {
                    "project_id": row["project_id"],
                    "role": row["role"],
                    "allocation_pct": int(row["allocation_pct"]),
                }
                for _, row in group.iterrows()
            ],
        })

    # Most useful when overallocation is the point of the question —
    # surface the worst offenders first.
    results.sort(key=lambda x: x["total_allocation_pct"], reverse=True)
    return results


def check_budget_variance(project_id: str = None):
    """
    Returns planned vs. actual budget for one project or all projects,
    with variance amount and percentage.

    Args:
        project_id (str, optional): e.g. 'P01'. If omitted, returns all projects.

    Returns:
        list[dict]: one entry per project.
    """
    df = _load_projects()
    if project_id:
        df = df[df["project_id"].str.upper() == project_id.upper()]

    results = []
    for _, r in df.iterrows():
        variance = r["budget_actual"] - r["budget_planned"]
        variance_pct = round(variance / r["budget_planned"] * 100, 1)
        results.append({
            "project_id": r["project_id"],
            "project_name": r["project_name"],
            "budget_planned": int(r["budget_planned"]),
            "budget_actual": int(r["budget_actual"]),
            "variance_amount": int(variance),
            "variance_pct": variance_pct,
            "over_budget": variance > 0,
        })
    return results


def get_project_summary(project_id: str):
    """
    Full detail pull for a single project, including its current
    resource allocations. Accepts either the project ID (e.g. 'P01')
    or the project name (full or partial, e.g. 'Fraud Detection').

    Args:
        project_id (str): project ID or project name.

    Returns:
        dict: full project detail, or an error message if not found.
    """
    df = _load_projects()

    # Try exact ID match first, then fall back to partial name match.
    row = df[df["project_id"].str.upper() == project_id.upper()]
    if row.empty:
        row = df[df["project_name"].str.contains(project_id, case=False, na=False)]
    if row.empty:
        return {"error": f"No project found matching '{project_id}'"}
    if len(row) > 1:
        matches = ", ".join(f"{r['project_id']} ({r['project_name']})" for _, r in row.iterrows())
        return {"error": f"Multiple projects match '{project_id}': {matches}. Please specify the exact ID."}

    r = row.iloc[0]

    resolved_id = r["project_id"]
    alloc_df = _load_allocations()
    project_allocations = alloc_df[alloc_df["project_id"].str.upper() == resolved_id.upper()]
    team = [
        {
            "person_name": a["person_name"],
            "role": a["role"],
            "allocation_pct": int(a["allocation_pct"]),
            "month": a["month"],
        }
        for _, a in project_allocations.iterrows()
    ]

    return {
        "project_id": r["project_id"],
        "project_name": r["project_name"],
        "status": r["status"],
        "start_date": r["start_date"],
        "end_date": r["end_date"],
        "percent_complete": int(r["percent_complete"]),
        "budget_planned": int(r["budget_planned"]),
        "budget_actual": int(r["budget_actual"]),
        "sprint_velocity_last3": [int(r["sprint_velocity_1"]), int(r["sprint_velocity_2"]), int(r["sprint_velocity_3"])],
        "blocked_stories": int(r["blocked_stories"]),
        "risk_notes": r["risk_notes"],
        "team": team,
    }


if __name__ == "__main__":
    # Quick manual sanity check — run `python tools.py` to eyeball outputs.
    import json
    print("=== At-risk projects ===")
    print(json.dumps(get_at_risk_projects(), indent=2))

    print("\n=== Overallocated people, August 2026 ===")
    print(json.dumps(check_resource_allocation(month="2026-08"), indent=2))

    print("\n=== Budget variance, all projects ===")
    print(json.dumps(check_budget_variance(), indent=2))

    print("\n=== Project summary: P01 ===")
    print(json.dumps(get_project_summary("P01"), indent=2))
