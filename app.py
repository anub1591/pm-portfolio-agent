"""
app.py — Streamlit frontend for the PM Portfolio Agent.

A business-user-facing chat interface. Ask plain-English questions
about project risk, budget, and team allocation; the agent reasons
over real data and shows its work.

Run with: streamlit run app.py
Requires: ANTHROPIC_API_KEY set as an environment variable, or
entered in the sidebar if running locally without it set.
"""

import streamlit as st
import os
from agent import ask_agent

st.set_page_config(
    page_title="PM Portfolio Agent",
    page_icon="📊",
    layout="wide",
)

# ---------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------
with st.sidebar:
    st.title("📊 PM Portfolio Agent")
    st.caption("Ask about project risk, budget, or team capacity — in plain English, no SQL or dashboard required.")

    # Allow entering the key here if it's not already set as an env var —
    # useful for anyone testing this without setting up their own .env.
    if not os.environ.get("ANTHROPIC_API_KEY"):
        key_input = st.text_input("Anthropic API Key", type="password")
        if key_input:
            os.environ["ANTHROPIC_API_KEY"] = key_input

    st.divider()
    st.subheader("Try asking:")

    example_questions = [
        "Which projects are at risk this sprint?",
        "Who's overallocated in August?",
        "Give me a status update on the Fraud Detection ML Model.",
        "What's the budget variance on the Legacy System Decommission project?",
        "Which at-risk projects also have an overallocated team member?",
    ]

    for q in example_questions:
        if st.button(q, use_container_width=True):
            st.session_state["pending_question"] = q

    st.divider()
    st.caption("Built with the Anthropic API (tool use) + a synthetic portfolio dataset. "
               "The agent decides which data to pull based on your question — nothing is hardcoded per question.")

# ---------------------------------------------------------------
# Chat state
# ---------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state["messages"] = []

st.title("Project Portfolio Assistant")
st.caption("Ask a question below, or pick one from the sidebar.")

# Render existing chat history
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("trace"):
            with st.expander("🔍 What the agent checked"):
                for step in msg["trace"]:
                    st.markdown(f"**Tool called:** `{step['tool']}`")
                    if step["input"]:
                        st.markdown(f"**With:** `{step['input']}`")
                    st.json(step["result"])

# ---------------------------------------------------------------
# Handle new input — either typed or from a sidebar button
# ---------------------------------------------------------------
typed_question = st.chat_input("Ask about your project portfolio...")
question = typed_question or st.session_state.pop("pending_question", None)

if question:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.error("Please enter your Anthropic API key in the sidebar first.")
    else:
        st.session_state["messages"].append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Checking the data..."):
                try:
                    result = ask_agent(question)
                    answer = result["answer"]
                    trace = result["trace"]
                except Exception as e:
                    answer = f"Something went wrong: {e}"
                    trace = []

            st.markdown(answer)
            if trace:
                with st.expander("🔍 What the agent checked"):
                    for step in trace:
                        st.markdown(f"**Tool called:** `{step['tool']}`")
                        if step["input"]:
                            st.markdown(f"**With:** `{step['input']}`")
                        st.json(step["result"])

        st.session_state["messages"].append({"role": "assistant", "content": answer, "trace": trace})
