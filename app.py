# Filename: app.py
"""
CrisisGuard-AI :: Streamlit Dashboard

Root-level entry point for Hugging Face Spaces (Streamlit SDK).
Run with:  streamlit run app.py

Design notes for HF Spaces reliability:
- The Hugging Face `transformers` model is NEVER loaded at import time.
  It is wrapped in `st.cache_resource` and only instantiated the first
  time a simulation cycle actually needs it, so the app boots instantly
  and never times out on Spaces cold start.
- All state lives in context.db (SQLite) via ContextManager, so the
  dashboard just re-reads the DB on every interaction — no in-memory
  globals that would break on Streamlit's rerun model.
"""

import pandas as pd
import streamlit as st

from agents import AnalystAgent, ContextManager, ResponseAgent, SensorAgent
from alert_system import format_alert, notify
from data_generator import generate_simulated_posts

st.set_page_config(page_title="CrisisGuard-AI", page_icon="🚨", layout="wide")


@st.cache_resource(show_spinner=False)
def get_context() -> ContextManager:
    return ContextManager()


@st.cache_resource(show_spinner="Loading crisis detection model (first run only)...")
def get_analyst(_context: ContextManager) -> AnalystAgent:
    # Model itself is still lazy-loaded inside AnalystAgent on first
    # detect_crisis() call — this cache just avoids re-instantiating
    # the agent object across reruns.
    return AnalystAgent(context=_context)


def run_simulation_cycle(context: ContextManager, analyst: AnalystAgent, n_events: int) -> dict:
    sensor = SensorAgent(context=context)
    responder = ResponseAgent(context=context, severity_threshold=4)

    posts = generate_simulated_posts(n=n_events)
    ingested = sensor.ingest_texts(source="simulated_social", texts=[p["text"] for p in posts])
    analyzed = analyst.analyze_pending()
    alerts_issued = responder.respond_pending(alert_formatter=format_alert, notifier=notify)

    return {"ingested": ingested, "analyzed": analyzed, "alerts": alerts_issued}


def severity_color(severity: int) -> str:
    return {1: "🟢", 2: "🟢", 3: "🟡", 4: "🔴", 5: "🔴"}.get(severity, "⚪")


# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------
st.sidebar.title("🚨 CrisisGuard-AI")
st.sidebar.caption("Multi-agent crisis detection & response — $0 budget build")

n_events = st.sidebar.slider("Events per simulation cycle", 5, 30, 10)
run_clicked = st.sidebar.button("▶️ Run Simulation Cycle", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.markdown("**Agents in this system**")
st.sidebar.markdown(
    "- 📡 **SensorAgent** — ingests posts\n"
    "- 🧠 **AnalystAgent** — scores crisis severity\n"
    "- 📣 **ResponseAgent** — routes alerts to authorities\n"
    "- 🗄️ **ContextManager** — shared MCP-style state (SQLite)"
)

context = get_context()
analyst = get_analyst(context)

if run_clicked:
    with st.spinner("Running Sensor → Analyst → Response cycle..."):
        result = run_simulation_cycle(context, analyst, n_events)
    st.sidebar.success(
        f"Ingested {result['ingested']} | Analyzed {result['analyzed']} | "
        f"Alerts {result['alerts']}"
    )

# ---------------------------------------------------------------------------
# System status indicator
# ---------------------------------------------------------------------------
last_run = context.get_context("analyst_last_run")
status_col, title_col = st.columns([1, 6])
with status_col:
    if last_run:
        st.markdown("### 🟢")
    else:
        st.markdown("### 🔴")
with title_col:
    st.title("CrisisGuard-AI Live Dashboard")
    if last_run:
        st.caption(f"System status: ONLINE — last analysis run at {last_run}")
    else:
        st.caption("System status: IDLE — click 'Run Simulation Cycle' in the sidebar to start")

# ---------------------------------------------------------------------------
# Live feed table
# ---------------------------------------------------------------------------
events = context.all_analyzed_events(limit=100)
st.subheader("📋 Live Crisis Feed")
if events:
    df = pd.DataFrame(events)[["id", "created_at", "category", "severity", "label", "crisis_score", "text", "status"]]
    df.insert(1, "flag", df["severity"].apply(severity_color))
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No events analyzed yet. Run a simulation cycle from the sidebar.")

# ---------------------------------------------------------------------------
# Severity heatmap (category x severity counts)
# ---------------------------------------------------------------------------
st.subheader("🌡️ Severity Heatmap")
if events:
    df_all = pd.DataFrame(events)
    pivot = (
        df_all.groupby(["category", "severity"]).size().unstack(fill_value=0).sort_index()
    )
    st.bar_chart(pivot)
else:
    st.info("Heatmap will populate after the first simulation cycle.")

# ---------------------------------------------------------------------------
# Alert log
# ---------------------------------------------------------------------------
st.subheader("📣 Alert Log (Severity ≥ 4)")
alerts = context.all_alerts(limit=100)
if alerts:
    adf = pd.DataFrame(alerts)[["id", "created_at", "category", "severity", "authority", "message"]]
    st.dataframe(adf, use_container_width=True, hide_index=True)
else:
    st.info("No alerts triggered yet.")

st.markdown("---")
st.caption(
    "CrisisGuard-AI · Multi-Agent System with MCP-style shared context (SQLite) · "
    "Built for the Kaggle 'AI Agents for Social Good' capstone track."
)
