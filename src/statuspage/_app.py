"""Flask application: the public status page plus the JSON API.

The app object is built here rather than in the tree root so `wsgi.py` can find
it as `web.app`.  Two things in the constructor matter:

* `template_folder` points at the tree's own `templates/` directory.  A bare
  `Flask(__name__)` would resolve templates relative to this package
  (`web/templates/`), which is not where the pages live.
* `instance_path` points at the tree's `instance/` directory, so the SQLite
  file lands next to the code and survives a `git clean`-free restart.

Nothing is seeded at import time: an empty database renders an honest
"no monitors yet" page instead of inventing rows.
"""
import atexit
import os

from flask import Flask, render_template

from .models import Check, Incident, Monitor, db
from .monitor.api import bp
from .monitor.incidents import uptime_pct
from .monitor.scheduler import Scheduler
from . import paths

paths.ensure_runtime_dirs()

def build_app():
    """Build the application: configuration, database, then routes."""
    app = Flask(__name__,
                template_folder=str(paths.TEMPLATES_DIR),
                instance_path=str(paths.INSTANCE_DIR))
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + str(paths.INSTANCE_DIR / "statuspage.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    # The OpenAPI document only promises JSON, but the shipped admin page posts its
    # forms here, and SQLite takes any thread.
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"connect_args": {"check_same_thread": False}}

    with app.app_context():
        db.create_all()

    app.register_blueprint(bp)

    def latest_checks(monitor_id, limit=30):
        """Most recent checks for a monitor, oldest first, for the uptime strip."""
        rows = (Check.query.filter_by(monitor_id=monitor_id)
                .order_by(Check.id.desc()).limit(limit).all())
        return list(reversed(rows))

    def _stats(monitors, open_incidents):
        up = 0
        for m in monitors:
            if any(i.monitor_id == m.id for i in open_incidents):
                continue
            up += 1
        return {"monitors": len(monitors), "up": up,
                "down": len(monitors) - up, "incidents": len(open_incidents)}

    @app.get("/")
    def index():
        """Public status page: every active monitor, its uptime and recent checks."""
        monitors = Monitor.query.filter_by(active=1).order_by(Monitor.name).all()
        open_incidents = Incident.query.filter_by(resolved_at=None).order_by(Incident.started_at.desc()).all()
        monitor_names = {m.id: m.name for m in monitors}
        return render_template(
            "status.html",
            app_name="statuspage",
            monitors=monitors,
            incidents=open_incidents,
            monitor_names=monitor_names,
            checks={m.id: latest_checks(m.id) for m in monitors},
            uptime={m.id: uptime_pct(m.id, 30) for m in monitors},
            stats=_stats(monitors, open_incidents),
        )

    @app.get("/admin")
    def admin():
        """Admin page: create monitors, inspect their checks, resolve incidents."""
        monitors = Monitor.query.order_by(Monitor.name).all()
        incidents = Incident.query.order_by(Incident.id.desc()).limit(20).all()
        monitor_names = {m.id: m.name for m in monitors}
        return render_template(
            "admin.html",
            app_name="statuspage",
            monitors=monitors,
            incidents=incidents,
            monitor_names=monitor_names,
            open_incident_count=Incident.query.filter_by(resolved_at=None).count(),
            check_counts={m.id: Check.query.filter_by(monitor_id=m.id).count() for m in monitors},
        )

    _scheduler = None

    def start_scheduler(interval=None):
        """Start the background poller once, and stop it when the process exits."""
        global _scheduler
        if _scheduler is not None:
            return _scheduler
        _scheduler = Scheduler(app=app, interval=float(interval or os.environ.get("CHECK_INTERVAL", "30")))
        _scheduler.start()
        atexit.register(_scheduler.stop)
        return _scheduler

    if os.environ.get("MONITOR_SCHEDULER", "on").lower() not in ("0", "off", "false", "no"):
        try:
            start_scheduler()
        except Exception as exc:  # a missing table or a thread-hostile host must not break serving
            print("[app] scheduler not started: %r" % (exc,))

    return app

app = build_app()
