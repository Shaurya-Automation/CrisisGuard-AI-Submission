# Filename: test_crisis_system.py
"""
CrisisGuard-AI :: Test Suite

Uses a mock scorer function for AnalystAgent so these tests run fast and
offline (no Hugging Face model download required). The keyword-based
severity logic and MCP context store are tested directly against real
SQLite, since that's cheap and deterministic.

Run with:
    pytest test_crisis_system.py -v
"""

import os
import tempfile

import pytest

from agents import (
    AnalystAgent,
    ContextManager,
    RateLimiter,
    ResponseAgent,
    SensorAgent,
    sanitize_input,
)
from alert_system import format_alert


def mock_scorer_neutral(text: str) -> float:
    """Pretend every text is emotionally neutral (0.0 negative intensity)."""
    return 0.0


def mock_scorer_negative(text: str) -> float:
    """Pretend every text is strongly negative (1.0 negative intensity)."""
    return 1.0


@pytest.fixture
def context(tmp_path):
    db_path = os.path.join(tmp_path, "test_context.db")
    return ContextManager(db_path=db_path)


# ---------------------------------------------------------------------------
# Security: input sanitisation
# ---------------------------------------------------------------------------
def test_sanitize_input_strips_script_tags():
    dirty = "<script>alert('x')</script>Fire in the building!"
    clean = sanitize_input(dirty)
    assert "<script>" not in clean
    assert "Fire in the building!" in clean


def test_sanitize_input_truncates_long_text():
    long_text = "a" * 1000
    clean = sanitize_input(long_text)
    assert len(clean) <= 500


def test_rate_limiter_blocks_after_max_calls():
    limiter = RateLimiter(max_calls=2, period_seconds=60)
    assert limiter.allow() is True
    assert limiter.allow() is True
    assert limiter.allow() is False  # third call within window is blocked


# ---------------------------------------------------------------------------
# AnalystAgent: crisis detection (Safe / Warning / Critical)
# ---------------------------------------------------------------------------
def test_detect_crisis_safe_text(context):
    analyst = AnalystAgent(context=context, scorer=mock_scorer_neutral)
    result = analyst.detect_crisis("Just passed my exam, feeling great today!")
    assert result.label == "Safe"
    assert result.severity <= 2


def test_detect_crisis_warning_text(context):
    analyst = AnalystAgent(context=context, scorer=mock_scorer_negative)
    result = analyst.detect_crisis("I've been feeling so alone lately, it's hard.")
    assert result.severity >= 3


def test_detect_crisis_critical_text(context):
    analyst = AnalystAgent(context=context, scorer=mock_scorer_negative)
    result = analyst.detect_crisis("Fire spreading fast in the building, need help now!")
    assert result.label == "Critical"
    assert result.severity == 5
    assert result.category == "Fire/Disaster"


def test_detect_crisis_mental_health_category(context):
    analyst = AnalystAgent(context=context, scorer=mock_scorer_negative)
    result = analyst.detect_crisis("I want to end it all, I can't take this anymore.")
    assert result.category == "Mental Health"
    assert result.severity >= 4


# ---------------------------------------------------------------------------
# ContextManager (MCP store)
# ---------------------------------------------------------------------------
def test_context_manager_raw_event_roundtrip(context):
    raw_id = context.add_raw_event(source="test", text="Cyberattack on bank server")
    pending = context.get_pending_raw_events()
    assert any(e["id"] == raw_id for e in pending)

    context.mark_raw_processed(raw_id)
    pending_after = context.get_pending_raw_events()
    assert not any(e["id"] == raw_id for e in pending_after)


def test_context_manager_key_value_store(context):
    context.set_context("sensor_last_run", "2026-01-01T00:00:00")
    assert context.get_context("sensor_last_run") == "2026-01-01T00:00:00"
    assert context.get_context("missing_key", default="fallback") == "fallback"


# ---------------------------------------------------------------------------
# Full pipeline: Sensor -> Analyst -> Response
# ---------------------------------------------------------------------------
def test_full_pipeline_generates_alert_for_critical_event(context):
    sensor = SensorAgent(context=context)
    analyst = AnalystAgent(context=context, scorer=mock_scorer_negative)
    responder = ResponseAgent(context=context, severity_threshold=4)

    sensor.ingest_texts(
        source="test",
        texts=["Explosion reported near the market, people are running."],
    )
    analyzed_count = analyst.analyze_pending()
    assert analyzed_count == 1

    captured = []
    alerts_issued = responder.respond_pending(
        alert_formatter=format_alert, notifier=captured.append
    )
    assert alerts_issued == 1
    assert len(captured) == 1
    assert "SEVERITY" in captured[0]


def test_full_pipeline_no_alert_for_safe_event(context):
    sensor = SensorAgent(context=context)
    analyst = AnalystAgent(context=context, scorer=mock_scorer_neutral)
    responder = ResponseAgent(context=context, severity_threshold=4)

    sensor.ingest_texts(source="test", texts=["Had a great cup of coffee this morning."])
    analyst.analyze_pending()

    alerts_issued = responder.respond_pending(alert_formatter=format_alert, notifier=lambda m: None)
    assert alerts_issued == 0
