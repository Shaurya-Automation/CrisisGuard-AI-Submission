# Filename: alert_system.py
"""
CrisisGuard-AI :: Alert System

Formats and delivers alerts produced by the ResponseAgent. In this
zero-budget build, "delivery" means: log to the shared context.db
(so the dashboard can display it) and print a formatted banner to the
console (standing in for an SMS/webhook call to real authorities).

No paid SMS/email API is used or required, keeping this at $0 cost.
"""

from datetime import datetime, timezone


def format_alert(event: dict, authority: str) -> str:
    """
    Build a human-readable alert message from an analyzed_event row
    and the authority it was routed to.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    severity_bar = "!" * event["severity"]
    excerpt = event["text"][:160]
    return (
        f"[{timestamp}] SEVERITY {event['severity']}/5 {severity_bar} "
        f"| CATEGORY: {event['category']} | ROUTED TO: {authority}\n"
        f"    \"{excerpt}\""
    )


def notify_console(message: str) -> None:
    """Print a formatted alert banner to the console."""
    border = "=" * 70
    print(border)
    print("CRISISGUARD-AI :: ALERT TRIGGERED")
    print(message)
    print(border)


def notify(message: str) -> None:
    """Public entry point used by ResponseAgent — currently console-only."""
    notify_console(message)
