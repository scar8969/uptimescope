"""JSON API for the status page and the admin UI.

Every endpoint answers JSON.  The two write endpoints additionally accept an
HTML form post (the admin page posts to them) and then redirect back to /admin,
so the shipped forms work without any JavaScript.  Validation failures are 400s
with an {"error": ...} body - the write endpoints never silently repair input.
"""
import datetime

from flask import Blueprint, jsonify, redirect, request, url_for

from ..models import Check, Incident, Monitor, db
from .incidents import uptime_pct

bp = Blueprint("monitor", __name__)

_TYPES = ("http", "tcp", "ssl")

def _payload():
    """Request body as a dict, from JSON or from an HTML form post."""
    data = request.get_json(force=True, silent=True)
    if isinstance(data, dict):
        return data
    return request.form.to_dict()

def _browser():
    """True when the caller is the admin page rather than an API client.

    A JSON body or an "Accept: application/json" header means API client: the
    answer is JSON.  Anything else - the admin page's form posts included - is
    treated as a browser and redirected back to /admin.
    """
    if request.is_json:
        return False
    return "application/json" not in (request.headers.get("Accept") or "").lower()

def _int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

@bp.get("/api/status")
def status():
    monitors = Monitor.query.filter_by(active=1).all()
    overall = "operational"
    services = []
    for m in monitors:
        last = Check.query.filter_by(monitor_id=m.id).order_by(Check.id.desc()).first()
        open_inc = Incident.query.filter_by(monitor_id=m.id, resolved_at=None).first()
        if open_inc:
            overall = "degraded"
        services.append({"name": m.name, "status": "down" if open_inc else "up",
                         "uptime_30d": uptime_pct(m.id, 30),
                         "last_ms": last.ms if last else None})
    return jsonify({"overall": overall, "services": services})

@bp.post("/api/admin/monitors")
def add_monitor():
    d = _payload()
    name = (d.get("name") or "").strip()
    target = (d.get("target") or "").strip()
    mtype = (d.get("type") or "http").strip().lower()
    if not name or not target:
        return jsonify({"error": "name and target are required"}), 400
    if mtype not in _TYPES:
        return jsonify({"error": "type must be one of " + ", ".join(_TYPES)}), 400
    interval = _int(d.get("interval"), 60)
    retries = _int(d.get("retries"), 2)
    if interval < 5:
        return jsonify({"error": "interval must be at least 5 seconds"}), 400
    if retries < 1:
        return jsonify({"error": "retries must be at least 1"}), 400
    m = Monitor(name=name, type=mtype, target=target, interval=interval, retries=retries)
    db.session.add(m)
    db.session.commit()
    if _browser():
        return redirect(url_for("admin"))
    return jsonify({"id": m.id})

@bp.get("/api/admin/monitors/<int:mid>/checks")
def checks(mid):
    rows = [{"ok": c.ok, "ms": c.ms, "at": c.at.isoformat() if c.at else ""}
            for c in Check.query.filter_by(monitor_id=mid).order_by(Check.id.desc()).limit(100).all()]
    return jsonify({"checks": rows})

@bp.post("/api/admin/incidents/<int:iid>/resolve")
def resolve(iid):
    inc = Incident.query.get_or_404(iid)
    inc.resolved_at = datetime.datetime.utcnow()
    db.session.commit()
    if _browser():
        return redirect(url_for("admin"))
    return jsonify({"status": "resolved"})
