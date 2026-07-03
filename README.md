CrisisGuard-AI

Multi-agent real-time crisis detection & response system — built for $0.

CrisisGuard-AI ingests text from news/social sources, scores it for crisis
severity using a multi-agent pipeline, and routes high-severity events to
the right authority — all running on free tools with no cloud credits and
no paid APIs.

Built for the Kaggle "AI Agents for Social Good" capstone track.


Why agents?

A single script that scores text is not resilient or extensible. Splitting
the work into independent agents that only talk through a shared context
store means each piece can be tested, swapped, or scaled on its own —
exactly how a real crisis-response pipeline would need to evolve.

Architecture

                 ┌─────────────────────────────────────────┐
                 │           context.db (MCP server)        │
                 │  raw_events | analyzed_events | alerts   │
                 │         context_store (key/value)        │
                 └───────────────▲───────────▲──────────────┘
                                 │           │
        writes raw text         │           │  reads analyzed,
                                 │           │  writes alerts
┌───────────────┐        ┌──────┴─────┐  ┌──┴──────────┐
│  SensorAgent   │        │AnalystAgent│  │ResponseAgent │
│ RSS + simulated│──────► │ keyword +  │─►│ routes to    │
│ social feed    │        │ HF model   │  │ authority    │
└───────────────┘        └────────────┘  └──────────────┘
                                                  │
                                                  ▼
                                        alert_system.py
                                     (console + DB log)
                                                  │
                                                  ▼
                                    app.py — Streamlit dashboard
                                    (live feed, heatmap, alert log)

No agent calls another agent directly. Every agent reads and writes
through ContextManager in agents.py, which acts as the shared
MCP (Model Context Protocol) server — a single SQLite-backed source
of truth (context.db) that all agents synchronize against.

The three agents

AgentFileRoleSensorAgentagents.pyIngests RSS headlines + simulated social posts, sanitizes input, rate-limits ingestionAnalystAgentagents.pyCombines keyword taxonomy + a lazy-loaded Hugging Face sentiment model into a 0–1 crisis score and 1–5 severityResponseAgentagents.pyMatches category → authority, generates the alert, hands it to alert_system.py

Security features


Input sanitisation (sanitize_input) strips HTML/script tags, control
characters, and hard-truncates every piece of text before it reaches the
model or the database.
Rate limiting (RateLimiter) caps ingestion and analysis throughput
per time window, independently for each agent.
No hardcoded secrets — any API key is read via os.environ.get(...)
and defaults to None; the whole system runs at $0 without one.
Defense in depth — a hard keyword match (e.g. "suicide", "shooting")
guarantees Critical-tier severity on its own, so the system doesn't
silently under-react if the ML model is unavailable.


Roadmap

This build intentionally uses only free RSS feeds and simulated data to
stay at $0. A planned future iteration will integrate real-time crisis
data APIs (e.g. live news/social monitoring feeds) in place of the
simulated feed, once a budget for paid API access is available — the
agent boundaries and MCP context store are already designed to support
this swap without any architectural changes.

Tech stack

Python 3.9+, Streamlit, Pandas, Hugging Face transformers
(distilbert-base-uncased-finetuned-sst-2-english), SQLite, feedparser.


Run it locally

bashpip install -r requirements.txt

# Option A: run the CLI automation loop (good for recording a demo)
python run_automation.py --cycles 3 --events 8 --delay 2

# Option B: launch the dashboard
streamlit run app.py

Click "Run Simulation Cycle" in the sidebar to trigger a full
Sensor → Analyst → Response pass and watch the live feed, heatmap, and
alert log populate.

Run the tests

bashpytest test_crisis_system.py -v

Tests use a mock scorer for AnalystAgent so they run instantly offline —
no model download required to verify the logic.

Deploy on Hugging Face Spaces (3 steps)


Create a new Space → SDK: Streamlit → copy every file in this
project into the Space root (no src/ folder, no Dockerfile).
Make sure requirements.txt is present at the root — Spaces installs
it automatically on build.
Spaces will run streamlit run app.py for you. The Hugging Face model
only loads on the first simulation click (lazy-loaded via
st.cache_resource), so the app boots instantly and never times out
on cold start.



Zero budget. Zero paid APIs. Fully reproducible.
