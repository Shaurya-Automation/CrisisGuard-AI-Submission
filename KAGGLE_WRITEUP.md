# CrisisGuard-AI: Multi-Agent Real-Time Crisis Prediction & Response System

*Kaggle Capstone — "AI Agents for Social Good" track*

## Problem Statement

Crisis signals — a fire spreading through a building, a person expressing
suicidal intent online, a company's servers being breached — often surface
in unstructured text long before official channels report them. Existing
monitoring tools tend to fall into one of two traps: they are either
purely keyword-based and drown in false positives, or they depend entirely
on a single ML model whose confidence can be wrong or whose service can be
unavailable at the exact moment it matters most. Neither approach is
resilient enough on its own, and most robust monitoring stacks assume
budgets and infrastructure that an individual builder — a student, a small
NGO, a community responder — simply does not have.

## Solution

CrisisGuard-AI is a multi-agent system that treats crisis detection as a
pipeline of specialized, independently testable agents rather than a
single monolithic script, while keeping the entire stack inside a $0
budget. Three agents — Sensor, Analyst, and Response — cooperate through
a shared SQLite-backed context store that functions as this project's MCP
(Model Context Protocol) server, so each agent can be developed, tested,
and reasoned about in isolation.

The core design decision that makes the system reliable rather than
merely functional is **defense in depth**: crisis keyword matches
(fire, suicide, shooting, breach, etc.) alone are enough to guarantee a
Critical-tier severity score. The Hugging Face sentiment model then adds
additional signal on top of that baseline. This means the system does not
silently under-react if the model is slow to load, temporarily
unavailable, or simply uncertain about a borderline case — a property
that matters far more in a safety-relevant tool than in a typical
sentiment-analysis demo.

## Architecture

**Sensor Agent** — ingests text from two sources: free public RSS feeds
(via `feedparser`) and a simulated social-media feed covering four crisis
categories plus safe/neutral posts, so the demo is fully reproducible
without any live incident occurring. All incoming text is sanitized
(HTML/script stripping, control-character removal, length capping) and
subject to a sliding-window rate limiter before it is written to the
shared context store.

**Analyst Agent** — reads pending raw events and produces a crisis score
in [0, 1] from two combined signals: (1) a keyword taxonomy across four
categories (Fire/Disaster, Cybercrime, Mental Health, Violence/Conflict),
and (2) a lazy-loaded `distilbert-base-uncased-finetuned-sst-2-english`
sentiment pipeline whose negative-intensity score is blended in. The
score maps to a 1–5 severity scale and a Safe/Warning/Critical label. The
model is never loaded at import time — only on first use — so the
dashboard boots instantly, which matters directly for Hugging Face Spaces
cold-start limits.

**Response Agent** — reads analyzed events at or above the alert
threshold (severity ≥ 4), maps each category to a corresponding authority
(Fire & Disaster Response Unit, Cybercrime Cell, Mental Health Crisis
Helpline, Police / Emergency Response), and hands a formatted alert to the
alert system, which logs it to the shared database and prints a console
notification standing in for a real SMS/webhook integration.

**MCP-style context store** (`ContextManager` in `agents.py`) — the
single shared state layer every agent reads and writes through. It holds
three event tables (`raw_events`, `analyzed_events`, `alerts`) plus a
generic key/value `context_store` table used for cross-agent status
signals (e.g. each agent's last-run timestamp). No agent ever imports or
calls another agent directly; all coordination happens through this
shared context, which is what makes the system an MCP-style architecture
rather than a simple function pipeline.

## Technical Implementation

- **Language/stack:** Python 3.9+, Streamlit, Pandas, Hugging Face
  `transformers`, SQLite, `feedparser`, `pydantic`.
- **Code structure:** `agents.py` (agents + MCP context manager),
  `data_generator.py` (simulated feed), `alert_system.py` (alert
  formatting/delivery), `app.py` (dashboard), `run_automation.py` (CLI
  demo loop), `test_crisis_system.py` (pytest suite).
- **Testability:** `AnalystAgent` accepts a dependency-injected scorer
  function, so unit tests validate the full Sensor → Analyst → Response
  pipeline without downloading the ML model — all 11 tests run in well
  under a second.
- **Security:** input sanitisation on every external string, sliding-window
  rate limiting per agent, and no hardcoded credentials anywhere in the
  codebase (any future API key is read from an environment variable and
  defaults to `None`, so the $0-budget constraint is enforced by design,
  not just by convention).

## Impact

Crisis-response tooling is usually built assuming institutional budgets —
paid NLP APIs, dedicated infrastructure, on-call engineering support.
CrisisGuard-AI demonstrates that a resilient, multi-agent, testable crisis
triage pipeline can be built entirely on free tooling and still make a
defensible design trade-off (keyword-first, model-augmented) that a
production safety system would actually want. The same architecture
generalizes directly to real deployments: swap the simulated feed for
live RSS/social APIs, swap the console notifier for a real SMS/webhook
call to local authorities, and the agent boundaries and MCP context store
require no changes.
