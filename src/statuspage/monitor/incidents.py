"""Incident detection and uptime maths.

The project root is on sys.path at runtime (wsgi.py inserts it, and the app is
started from this directory), so the application modules are imported flat:
`from models import ...`, not `from .models import ...` - the latter would look
for the non-existent package `monitor.models`.
"""

from datetime import datetime, timedelta


def detect(monitor, ok):
    """Open an incident after `monitor.retries` consecutive failures, close it on recovery."""
    from ..models import Check, Incident, db

    recent = (
        Check.query.filter_by(monitor_id=monitor.id)
        .order_by(Check.id.desc())
        .limit(monitor.retries + 1)
        .all()
    )
    open_inc = Incident.query.filter_by(monitor_id=monitor.id, resolved_at=None).first()
    if not ok and len(recent) >= monitor.retries and all(not c.ok for c in recent):
        if not open_inc:
            db.session.add(
                Incident(
                    monitor_id=monitor.id,
                    severity="down",
                    message="%d consecutive failures" % len(recent),
                )
            )
            db.session.commit()
    elif ok and open_inc:
        open_inc.resolved_at = datetime.utcnow()
        db.session.commit()


def uptime_pct(monitor_id, days=30):
    """Share of successful checks over the window, or 100.0 when there is no data."""
    from ..models import Check

    since = datetime.utcnow() - timedelta(days=days)
    checks = Check.query.filter(Check.monitor_id == monitor_id, Check.at >= since).all()
    if not checks:
        return 100.0
    return round(sum(1 for c in checks if c.ok) / len(checks) * 100, 2)
