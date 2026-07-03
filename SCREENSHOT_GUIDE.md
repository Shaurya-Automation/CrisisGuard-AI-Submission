# CrisisGuard-AI — Screenshot Guide

Exactly 3 screenshots for the Kaggle Media Gallery.

## 1. The Dashboard — Live Feed

- Run at least one simulation cycle first so the feed, heatmap, and alert
  log are all populated (empty-state screenshots look unfinished).
- Capture the full page: system status indicator, live crisis feed table
  with severity flags, and the severity heatmap all visible in one shot.
- This is your "hero" image — it should be the first one you attach.

## 2. The Code — Multi-Agent / MCP Structure

- Open `agents.py` in your editor.
- Scroll/frame so `ContextManager`, `SensorAgent`, `AnalystAgent`, and
  `ResponseAgent` class definitions are all visible (or at least their
  class headers + docstrings), showing the MCP pattern clearly.
- A split view showing the `CRISIS_KEYWORDS` taxonomy alongside the
  `ContextManager` class also works well if a single screen can't fit
  all four classes.

## 3. The Alert Trigger — Severity 5

- Run enough simulation cycles that a Severity 5 "Critical" alert
  appears in the Alert Log.
- Capture the Alert Log table with the Severity 5 row visible, ideally
  with the routed authority column showing (e.g. "Mental Health Crisis
  Helpline" or "Fire & Disaster Response Unit").
- Console output from `run_automation.py` showing the
  `CRISISGUARD-AI :: ALERT TRIGGERED` banner is a good alternative if the
  dashboard alert log is hard to frame cleanly.
