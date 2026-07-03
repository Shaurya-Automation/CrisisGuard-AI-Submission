# Filename: run_automation.py
"""
CrisisGuard-AI :: Master Automation Script

Runs the full Sensor -> Analyst -> Response loop from the command line,
independent of Streamlit. This is the script to run while screen-recording
the demo video: it prints each agent's action to the console step by step.

Usage:
    python run_automation.py --cycles 3 --events 8 --delay 2
"""

import argparse
import time

from agents import AnalystAgent, ContextManager, ResponseAgent, SensorAgent
from alert_system import format_alert, notify
from data_generator import generate_simulated_posts


def run_cycle(context: ContextManager, analyst: AnalystAgent, n_events: int, cycle_num: int) -> None:
    print(f"\n----- CYCLE {cycle_num} -----")

    sensor = SensorAgent(context=context)
    responder = ResponseAgent(context=context, severity_threshold=4)

    print("[SensorAgent] Generating + ingesting simulated social posts...")
    posts = generate_simulated_posts(n=n_events)
    ingested = sensor.ingest_texts(source="simulated_social", texts=[p["text"] for p in posts])
    print(f"[SensorAgent] Ingested {ingested} raw events into context.db")

    print("[AnalystAgent] Scoring pending events for crisis severity...")
    analyzed = analyst.analyze_pending()
    print(f"[AnalystAgent] Analyzed {analyzed} events")

    print("[ResponseAgent] Checking for severity >= 4 events to route...")
    alerts_issued = responder.respond_pending(alert_formatter=format_alert, notifier=notify)
    print(f"[ResponseAgent] Issued {alerts_issued} alert(s)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CrisisGuard-AI automation loop")
    parser.add_argument("--cycles", type=int, default=3, help="Number of simulation cycles")
    parser.add_argument("--events", type=int, default=8, help="Events generated per cycle")
    parser.add_argument("--delay", type=float, default=2.0, help="Seconds to pause between cycles")
    args = parser.parse_args()

    print("=" * 70)
    print("CRISISGUARD-AI :: MULTI-AGENT AUTOMATION RUN")
    print("=" * 70)

    context = ContextManager()
    analyst = AnalystAgent(context=context)

    for i in range(1, args.cycles + 1):
        run_cycle(context, analyst, n_events=args.events, cycle_num=i)
        if i < args.cycles:
            time.sleep(args.delay)

    print("\nAutomation run complete. Launch the dashboard with:")
    print("    streamlit run app.py")


if __name__ == "__main__":
    main()
