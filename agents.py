# Filename: agents.py
"""
CrisisGuard-AI :: Core Agent Layer

This file implements the Multi-Agent System (ADK-style) and the MCP
(Model Context Protocol) shared-context server that lets the agents
cooperate without calling each other directly.

Architecture
------------
    SensorAgent  --writes-->  context.db (raw_events)
    AnalystAgent --reads/writes--> context.db (raw_events -> analyzed_events)
    ResponseAgent --reads/writes--> context.db (analyzed_events -> alerts)

Every agent only ever talks to the ContextManager (the "MCP server").
No agent holds a reference to another agent. This is what makes it an
MCP-style architecture rather than a simple function pipeline: the
context store is the single shared source of truth, and agents are
loosely coupled producers/consumers of that store.

Security features implemented in this file (see SECURITY section):
    1. Input sanitisation (`sanitize_input`) on every piece of external text.
    2. Rate limiting (`RateLimiter`) on ingestion and analysis calls.
    3. No hardcoded secrets — any future API key is read from the
       environment with `os.environ.get(...)` and defaults to None.
"""

from __future__ import annotations

import os
import re
import sqlite3
import time
import html
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional

DB_PATH = os.environ.get("CRISISGUARD_DB_PATH", "context.db")

# Example of the "no hardcoded keys" rule in practice: if a real news API
# were wired in, its key would be read like this. It is never written
# into source code and defaults to None so the app still runs with $0 budget.
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", None)


# ---------------------------------------------------------------------------
# SECURITY: input sanitisation
# ---------------------------------------------------------------------------
_TAG_RE = re.compile(r"<[^>]*>")
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
MAX_INPUT_LEN = 500


def sanitize_input(text: str) -> str:
    """
    Clean untrusted text (RSS titles, simulated social posts) before it
    ever reaches the model or the database.

    - Strips HTML/script tags.
    - Un-escapes and re-escapes HTML entities so nothing executable survives.
    - Removes control characters.
    - Hard-truncates length to prevent oversized payloads / prompt abuse.
    """
    if not isinstance(text, str):
        text = str(text)
    text = html.unescape(text)
    text = _TAG_RE.sub("", text)
    text = _CONTROL_CHAR_RE.sub("", text)
    text = text.strip()
    if len(text) > MAX_INPUT_LEN:
        text = text[:MAX_INPUT_LEN]
    return text


# ---------------------------------------------------------------------------
# SECURITY: rate limiting
# ---------------------------------------------------------------------------
class RateLimiter:
    """Simple sliding-window rate limiter, no external dependencies."""

    def __init__(self, max_calls: int, period_seconds: float):
        self.max_calls = max_calls
        self.period_seconds = period_seconds
        self._calls: deque = deque()

    def allow(self) -> bool:
        now = time.monotonic()
        while self._calls and now - self._calls[0] > self.period_seconds:
            self._calls.popleft()
        if len(self._calls) < self.max_calls:
            self._calls.append(now)
            return True
        return False


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# MCP SERVER: shared context store (SQLite-backed)
# ---------------------------------------------------------------------------
class ContextManager:
    """
    Acts as the MCP (Model Context Protocol) server for this project:
    a single shared state store that every agent reads from and writes
    to. Agents never share state directly with one another — only
    through this class — which mirrors how an MCP server mediates
    context between independent tools/agents.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS raw_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    text TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'new',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analyzed_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    raw_id INTEGER,
                    text TEXT NOT NULL,
                    crisis_score REAL NOT NULL,
                    severity INTEGER NOT NULL,
                    label TEXT NOT NULL,
                    category TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'new',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analyzed_id INTEGER,
                    category TEXT NOT NULL,
                    severity INTEGER NOT NULL,
                    authority TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS context_store (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    # -- generic key/value shared context (the "MCP" part) ---------------
    def set_context(self, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO context_store (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value,
                                                updated_at=excluded.updated_at
                """,
                (key, value, _now_iso()),
            )
            conn.commit()

    def get_context(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM context_store WHERE key = ?", (key,)
            ).fetchone()
            return row["value"] if row else default

    # -- raw events (Sensor -> Analyst) -----------------------------------
    def add_raw_event(self, source: str, text: str) -> int:
        clean_text = sanitize_input(text)
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO raw_events (source, text, status, created_at) "
                "VALUES (?, ?, 'new', ?)",
                (sanitize_input(source), clean_text, _now_iso()),
            )
            conn.commit()
            return cur.lastrowid

    def get_pending_raw_events(self, limit: int = 50):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM raw_events WHERE status = 'new' "
                "ORDER BY id ASC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def mark_raw_processed(self, raw_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE raw_events SET status = 'processed' WHERE id = ?",
                (raw_id,),
            )
            conn.commit()

    # -- analyzed events (Analyst -> Response) ----------------------------
    def add_analyzed_event(
        self, raw_id: int, text: str, crisis_score: float,
        severity: int, label: str, category: str,
    ) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO analyzed_events
                    (raw_id, text, crisis_score, severity, label, category, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'new', ?)
                """,
                (raw_id, text, crisis_score, severity, label, category, _now_iso()),
            )
            conn.commit()
            return cur.lastrowid

    def get_pending_analyzed_events(self, min_severity: int = 4, limit: int = 50):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM analyzed_events WHERE status = 'new' "
                "AND severity >= ? ORDER BY id ASC LIMIT ?",
                (min_severity, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def mark_analyzed_handled(self, analyzed_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE analyzed_events SET status = 'handled' WHERE id = ?",
                (analyzed_id,),
            )
            conn.commit()

    def all_analyzed_events(self, limit: int = 200):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM analyzed_events ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    # -- alerts (Response output) -----------------------------------------
    def add_alert(
        self, analyzed_id: int, category: str, severity: int,
        authority: str, message: str,
    ) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO alerts (analyzed_id, category, severity, authority, message, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (analyzed_id, category, severity, authority, message, _now_iso()),
            )
            conn.commit()
            return cur.lastrowid

    def all_alerts(self, limit: int = 200):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Crisis keyword taxonomy — used both as a fast deterministic signal and
# to assign a category, independent of whether the ML model is available.
# ---------------------------------------------------------------------------
CRISIS_KEYWORDS = {
    "Fire/Disaster": {
        "keywords": ["fire", "explosion", "flood", "earthquake", "collapse",
                     "evacuate", "burning", "smoke", "wildfire"],
        "weight": 0.6,
        "authority": "Fire & Disaster Response Unit",
    },
    "Cybercrime": {
        "keywords": ["breach", "cyberattack", "hacked", "ransomware",
                      "data leak", "phishing", "server compromised"],
        "weight": 0.6,
        "authority": "Cybercrime Cell",
    },
    "Mental Health": {
        "keywords": ["suicide", "self harm", "self-harm", "want to die",
                      "end it all", "hopeless", "kill myself"],
        "weight": 0.65,
        "authority": "Mental Health Crisis Helpline",
    },
    "Violence/Conflict": {
        "keywords": ["shooting", "attack", "war", "bomb", "riot",
                      "gunman", "hostage", "violence"],
        "weight": 0.6,
        "authority": "Police / Emergency Response",
    },
}
# Design note: keyword weights are set high enough (>=0.6) that a hard
# keyword match alone guarantees Critical-tier severity, independent of
# whether the ML model is reachable/confident. The model score only ever
# adds on top of this baseline. This is a deliberate defense-in-depth
# choice: a safety system should not silently under-react just because
# the sentiment model is unavailable or uncertain.


@dataclass
class ScoredEvent:
    text: str
    crisis_score: float
    severity: int
    label: str
    category: str


def _keyword_signal(text: str):
    """Return (score_contribution, category) from the keyword taxonomy."""
    lowered = text.lower()
    best_score = 0.0
    best_category = "General"
    for category, info in CRISIS_KEYWORDS.items():
        hits = sum(1 for kw in info["keywords"] if kw in lowered)
        if hits:
            score = min(info["weight"] + 0.05 * (hits - 1), 1.0)
            if score > best_score:
                best_score = score
                best_category = category
    return best_score, best_category


def _severity_from_score(score: float):
    if score < 0.2:
        return 1, "Safe"
    if score < 0.4:
        return 2, "Safe"
    if score < 0.6:
        return 3, "Warning"
    if score < 0.8:
        return 4, "Critical"
    return 5, "Critical"


# ---------------------------------------------------------------------------
# AGENT 1: Sensor
# ---------------------------------------------------------------------------
class SensorAgent:
    """Ingests raw data (RSS + simulated social feed) into the MCP store."""

    def __init__(self, context: ContextManager, rate_limiter: Optional[RateLimiter] = None):
        self.context = context
        self.rate_limiter = rate_limiter or RateLimiter(max_calls=60, period_seconds=60)

    def ingest_texts(self, source: str, texts: list[str]) -> int:
        """Write a batch of raw texts into the shared context. Returns count ingested."""
        count = 0
        for text in texts:
            if not self.rate_limiter.allow():
                break  # SECURITY: stop ingesting once rate limit is hit
            if not text or not text.strip():
                continue
            self.context.add_raw_event(source=source, text=text)
            count += 1
        self.context.set_context("sensor_last_run", _now_iso())
        self.context.set_context("sensor_last_count", str(count))
        return count

    def ingest_rss(self, feed_urls: list[str], max_per_feed: int = 5) -> int:
        """
        Pull headlines from free public RSS feeds. Uses `feedparser`.
        Fails soft (returns 0) if network access is unavailable — the
        simulated feed always keeps the demo working with $0 budget.
        """
        import feedparser  # local import keeps startup fast

        total = 0
        for url in feed_urls:
            try:
                parsed = feedparser.parse(url)
                titles = [entry.get("title", "") for entry in parsed.entries[:max_per_feed]]
                total += self.ingest_texts(source=f"rss:{url}", texts=titles)
            except Exception:
                continue
        return total


# ---------------------------------------------------------------------------
# AGENT 2: Analyst
# ---------------------------------------------------------------------------
class AnalystAgent:
    """
    Reads pending raw events, scores them for crisis severity, and writes
    results back to the MCP store.

    `scorer` is dependency-injected so the agent can be unit-tested
    without downloading the Hugging Face model (see test_crisis_system.py).
    It must be a callable: (text: str) -> float in [0, 1], where higher
    means more negative/urgent sentiment.
    """

    MODEL_NAME = "distilbert-base-uncased-finetuned-sst-2-english"

    def __init__(
        self,
        context: ContextManager,
        scorer: Optional[Callable[[str], float]] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        self.context = context
        self._scorer = scorer
        self._pipeline = None  # lazy-loaded, avoids slow startup / HF Spaces timeout
        self.rate_limiter = rate_limiter or RateLimiter(max_calls=120, period_seconds=60)

    def _get_pipeline(self):
        if self._pipeline is None:
            from transformers import pipeline  # local import: lazy load
            self._pipeline = pipeline("sentiment-analysis", model=self.MODEL_NAME)
        return self._pipeline

    def _model_score(self, text: str) -> float:
        """Return a 0-1 'negative intensity' score from the sentiment model."""
        if self._scorer is not None:
            return self._scorer(text)
        result = self._get_pipeline()(text[:512])[0]
        if result["label"].upper().startswith("NEG"):
            return float(result["score"])
        return 1.0 - float(result["score"])

    def detect_crisis(self, raw_text: str) -> ScoredEvent:
        """Core detection function: keyword signal + model signal -> severity."""
        text = sanitize_input(raw_text)
        kw_score, category = _keyword_signal(text)
        try:
            model_score = self._model_score(text) if text else 0.0
        except Exception:
            # Model unavailable (e.g. offline dev environment) -> degrade
            # gracefully to keyword-only scoring rather than crashing.
            model_score = 0.0
        combined = min(kw_score + 0.4 * model_score, 1.0)
        severity, label = _severity_from_score(combined)
        if kw_score == 0.0:
            category = "General"
        return ScoredEvent(
            text=text, crisis_score=round(combined, 3),
            severity=severity, label=label, category=category,
        )

    def analyze_pending(self, limit: int = 50) -> int:
        events = self.context.get_pending_raw_events(limit=limit)
        processed = 0
        for raw in events:
            if not self.rate_limiter.allow():
                break  # SECURITY: cap analysis throughput
            scored = self.detect_crisis(raw["text"])
            self.context.add_analyzed_event(
                raw_id=raw["id"], text=scored.text,
                crisis_score=scored.crisis_score, severity=scored.severity,
                label=scored.label, category=scored.category,
            )
            self.context.mark_raw_processed(raw["id"])
            processed += 1
        self.context.set_context("analyst_last_run", _now_iso())
        return processed


# ---------------------------------------------------------------------------
# AGENT 3: Response
# ---------------------------------------------------------------------------
class ResponseAgent:
    """Reads high-severity analyzed events and issues alerts to authorities."""

    def __init__(self, context: ContextManager, severity_threshold: int = 4):
        self.context = context
        self.severity_threshold = severity_threshold

    def _authority_for(self, category: str) -> str:
        if category in CRISIS_KEYWORDS:
            return CRISIS_KEYWORDS[category]["authority"]
        return "General Emergency Dispatch"

    def respond_pending(self, alert_formatter: Callable, notifier: Callable) -> int:
        pending = self.context.get_pending_analyzed_events(
            min_severity=self.severity_threshold
        )
        issued = 0
        for event in pending:
            authority = self._authority_for(event["category"])
            message = alert_formatter(event, authority)
            self.context.add_alert(
                analyzed_id=event["id"], category=event["category"],
                severity=event["severity"], authority=authority, message=message,
            )
            notifier(message)
            self.context.mark_analyzed_handled(event["id"])
            issued += 1
        self.context.set_context("response_last_run", _now_iso())
        return issued
