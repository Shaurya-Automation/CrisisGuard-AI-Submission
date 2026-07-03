# CrisisGuard-AI — 5-Minute Demo Video Script

Word-for-word script. Timings are approximate — adjust pacing as needed,
but keep total runtime under 5 minutes.

---

### [0:00–0:30] Hook + Problem

> "Crisis signals show up in text long before anyone official notices —
> a fire spreading, someone in danger, a server getting breached. But
> most monitoring tools either rely purely on keywords and miss context,
> or rely purely on an ML model that can go down or be wrong at the worst
> possible moment. I built CrisisGuard-AI to fix that — for zero dollars."

### [0:30–1:15] Why Agents? (Unique Value)

> "Instead of one script doing everything, CrisisGuard-AI splits the work
> across three independent agents: a Sensor Agent that ingests text, an
> Analyst Agent that scores it for crisis severity, and a Response Agent
> that routes alerts to the right authority. None of these agents talk to
> each other directly. They all read and write through a single shared
> context store — that's the MCP pattern: a Model Context Protocol server
> that mediates state between independent agents, backed here by SQLite."

*(Cue: show the architecture diagram from README.md on screen — Sensor →
context.db → Analyst → context.db → Response.)*

### [1:15–2:00] Architecture Walkthrough

> "Here's `agents.py`. The Sensor Agent pulls from RSS feeds and a
> simulated social feed, sanitizing every piece of text and rate-limiting
> ingestion. The Analyst Agent combines a crisis-keyword taxonomy with a
> Hugging Face sentiment model to produce a severity score from 1 to 5.
> And notice this design choice —" *(point to `CRISIS_KEYWORDS` weights)*
> "— keyword matches alone are enough to hit Critical severity. That's
> deliberate: the system should never silently under-react just because
> the ML model is slow or unavailable."

*(Cue: scroll through `agents.py`, highlighting `ContextManager`,
`SensorAgent`, `AnalystAgent`, `ResponseAgent` class definitions.)*

### [2:00–2:30] Security Features

> "Every piece of external text goes through input sanitisation before it
> touches the model or the database. Every agent is rate-limited. And
> there are no hardcoded API keys anywhere — any future key is read from
> an environment variable and defaults to `None`, so the whole system
> runs at zero cost by design."

### [2:30–4:15] Live Demo

> "Let's run it. I'll launch the dashboard with `streamlit run app.py`."

*(Cue: show terminal, run the command, dashboard loads instantly.)*

> "Notice the app loads immediately — the ML model hasn't loaded yet,
> it's lazy. I'll click 'Run Simulation Cycle' in the sidebar."

*(Cue: click the button, wait for spinner.)*

> "The Sensor Agent just generated and ingested simulated posts. The
> Analyst Agent scored each one. And look — the Response Agent already
> triggered alerts for the Critical-severity events. Here's the live
> feed table with severity flags, the severity heatmap by category, and
> the alert log showing exactly which authority each event was routed
> to — Fire & Disaster Response, Cybercrime Cell, Mental Health Crisis
> Helpline, or Police."

*(Cue: scroll through the dashboard — live feed table, severity
heatmap, alert log. Optionally: a 3D globe / hotspot visualization here
if using Antigravity for extra visual polish.)*

> "I'll run it again to show it handles a fresh batch consistently."

*(Cue: click 'Run Simulation Cycle' a second time, show new rows
appearing.)*

### [4:15–4:45] Build Process

> "Everything here is Python-native — Streamlit for the dashboard,
> Hugging Face Transformers for sentiment scoring, SQLite for the shared
> MCP context, and `feedparser` for real RSS ingestion. All tested with
> an 11-test pytest suite that runs offline using a mock scorer, so the
> agent logic is verified independently of the ML model."

*(Cue: run `pytest test_crisis_system.py -v`, show all tests passing.)*

### [4:45–5:00] Close

> "CrisisGuard-AI: three agents, one shared context, zero budget, and a
> design that stays safe even when the ML model can't be trusted alone.
> Thanks for watching."

---

**Production notes:**
- Record the dashboard demo first — it's the most visually convincing segment.
- Keep the terminal font large enough to read on a recorded screen.
- If using Antigravity for the hotspot globe, insert it as a cutaway during
  the 2:30–4:15 demo segment rather than replacing the real dashboard footage.
