# CrisisGuard-AI

**Multi-agent real-time crisis detection & response system — built for $0.**

CrisisGuard-AI ingests text from news/social sources, scores it for crisis
severity using a multi-agent pipeline, and routes high-severity events to
the right authority — all running on free tools with no cloud credits and
no paid APIs.

Built for the Kaggle **"AI Agents for Social Good"** capstone track.

---

## Problem

Crisis signals — a fire spreading through a building, someone expressing
suicidal intent online, a company's servers being breached — often show
up in text long before any official channel reports them. Most
monitoring tools either lean purely on keyword matching, and drown in
false positives, or lean entirely on an ML model that can be slow,
wrong, or unavailable at the exact moment it matters most. Neither is
resilient enough on its own, and most robust crisis-monitoring stacks
assume budgets an individual builder simply doesn't have.

## Solution

CrisisGuard-AI treats crisis detection as three independently testable
agents — Sensor, Analyst, Response — coordinated through a single
shared context store, and runs entirely on free tools. Its core design
decision is defense in depth: a hard keyword match (e.g. "fire",
"suicide", "shooting") alone guarantees Critical-tier severity, and the
ML sentiment model only ever adds signal on top of that baseline — so
the system never silently under-reacts just because the model is slow
to load or uncertain about a borderline case.

## Why agents?

A single script that scores text is not resilient or extensible. Splitting
the work into independent agents that only talk through a shared context
store means each piece can be tested, swapped, or scaled on its own —
exactly how a real crisis-response pipeline would need to evolve.

## Architecture

```
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
```

No agent calls another agent directly. Every agent reads and writes
through `ContextManager` in `agents.py`, which acts as the shared
**MCP (Model Context Protocol) server** — a single SQLite-backed source
of truth (`context.db`) that all agents synchronize against.

## The three agents

| Agent | File | Role |
|---|---|---|
| `SensorAgent` | `agents.py` | Ingests RSS headlines + simulated social posts, sanitizes input, rate-limits ingestion |
| `AnalystAgent` | `agents.py` | Combines keyword taxonomy + a lazy-loaded Hugging Face sentiment model into a 0–1 crisis score and 1–5 severity |
| `ResponseAgent` | `agents.py` | Matches category → authority, generates the alert, hands it to `alert_system.py` |

## Security features

- **Input sanitisation** (`sanitize_input`) strips HTML/script tags, control
  characters, and hard-truncates every piece of text before it reaches the
  model or the database.
- **Rate limiting** (`RateLimiter`) caps ingestion and analysis throughput
  per time window, independently for each agent.
- **No hardcoded secrets** — any API key is read via `os.environ.get(...)`
  and defaults to `None`; the whole system runs at $0 without one.
- **Defense in depth** — a hard keyword match (e.g. "suicide", "shooting")
  guarantees Critical-tier severity on its own, so the system doesn't
  silently under-react if the ML model is unavailable.

## Roadmap

This build intentionally uses only free RSS feeds and simulated data to
stay at $0. A planned future iteration will integrate real-time crisis
data APIs (e.g. live news/social monitoring feeds) in place of the
simulated feed, once a budget for paid API access is available — the
agent boundaries and MCP context store are already designed to support
this swap without any architectural changes.

## Tech stack

Python 3.10+, Streamlit, Pandas, Hugging Face `transformers`
(`distilbert-base-uncased-finetuned-sst-2-english`), SQLite, `feedparser`.

---

## Setup & Installation

```bash
git clone https://github.com/<your-username>/CrisisGuard-AI-Submission.git
cd CrisisGuard-AI-Submission
pip install -r requirements.txt
```

## Run it locally

```bash
# Option A: run the CLI automation loop (good for recording a demo)
python run_automation.py --cycles 3 --events 8 --delay 2

# Option B: launch the dashboard
streamlit run app.py
```

Click **"Run Simulation Cycle"** in the sidebar to trigger a full
Sensor → Analyst → Response pass and watch the live feed, heatmap, and
alert log populate.

## Run the tests

```bash
pytest test_crisis_system.py -v
```

Tests use a mock scorer for `AnalystAgent` so they run instantly offline —
no model download required to verify the logic.

## Deploy on Hugging Face Spaces (3 steps)

1. Create a new Space → SDK: **Streamlit** → copy every file in this
   project into the Space **root** (no `src/` folder, no Dockerfile).
2. Make sure `requirements.txt` is present at the root — Spaces installs
   it automatically on build.
3. Spaces will run `streamlit run app.py` for you. The Hugging Face model
   only loads on the first simulation click (lazy-loaded via
   `st.cache_resource`), so the app boots instantly and never times out
   on cold start.

## Screenshots

Can be seen as indivisual files, they will be labelled as the following:
1. Dashboard image 1.png
2. Dashboard image 2.png
3. Alerts (also visisble on dashboard).png [shown in bash]

---

## 👥 Team & Roles

**CrisisGuard-AI** was engineered by a core technical architect and a strategic product lead, combining rigorous engineering with high-impact social good strategy.

### **Shaurya (Technical Lead & Architect)**
*Lead Developer | Python Engineer | Security Specialist*

*   **Core System Architecture:** Solely designed and implemented the **Multi-Agent System (MAS)** using a custom **Model Context Protocol (MCP)** pattern. Engineered the stateful communication layer using SQLite to ensure agent independence and data integrity.
*   **Security & Robustness:** Built the entire security framework from scratch, including **input sanitization pipelines**, **rate-limiting logic**, and **environment-based secret management** to guarantee zero-cost, secure operation without hardcoded keys.
*   **Full-Stack Implementation:** Developed the entire Python codebase (`agents.py`, `alert_system.py`), the **Streamlit dashboard** for real-time visualization, and the **11-test `pytest` suite** using mock scorers to validate logic offline.
*   **Deployment Strategy:** Orchestrated the deployment pipeline to **Hugging Face Spaces**, ensuring the ML models and agents run seamlessly in a serverless environment.
*   **Technical Ownership:** Responsible for 100% of the code logic, database schema, and performance optimization, ensuring the system remains accurate even when ML models are uncertain.

### **Rama Kruthi (Product Lead & Strategy)**
*System Designer | Impact Strategist | Demo Lead*

*   **Crisis Logic & Taxonomy:** Defined the crisis detection taxonomy and the "Safety-First" scoring logic that prioritizes keyword certainty over ML latency.
*   **Social Impact Framework:** Mapped specific crisis categories (Fire, Cybercrime, Mental Health) to real-world authority routing protocols, ensuring the system solves a tangible real-world problem.
*   **Narrative & Demo:** Led the project storytelling, crafting the "Zero Budget, High Reliability" value proposition and directing the live demonstration to showcase system resilience.
*   **Research & Validation:** Conducted initial feasibility research on crisis signal detection patterns to validate the need for a hybrid keyword+ML approach.


---

*Zero budget. Zero paid APIs. Fully reproducible.*
