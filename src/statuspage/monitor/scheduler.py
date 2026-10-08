"""Polling scheduler: every `interval` seconds, check each due monitor.

The scheduler owns no data itself.  It reads the monitors the admin API created,
runs the matching probe from `monitor.checks`, stores a Check row, and hands the
result to `monitor.incidents.detect` for incident open/close.  A pass that raises
is logged once and retried on the next tick, so one unreachable target can never
kill the thread.
"""
import sys
import threading
import time

class Scheduler:
    """Background poller.  `app` may be a Flask app; each tick then runs inside
    its application context, which Flask-SQLAlchemy needs for db.session."""

    def __init__(self, app=None, interval=5.0):
        self.app = app
        self.interval = float(interval)
        self._thread = None
        self._stop = threading.Event()
        self._warned = False

    # -- lifecycle ---------------------------------------------------------
    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return self._thread
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="monitor-scheduler",
                                        daemon=True)
        self._thread.start()
        return self._thread

    def stop(self, timeout=5.0):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout)
            self._thread = None

    # -- work --------------------------------------------------------------
    def tick(self):
        """One pass over the active monitors; returns how many were checked."""
        from datetime import datetime, timedelta

        from ..models import Check, Monitor, db
        from .checks import check_http, check_ssl, check_tcp
        from .incidents import detect

        checked = 0
        for m in Monitor.query.filter_by(active=1).all():
            last = Check.query.filter_by(monitor_id=m.id).order_by(Check.id.desc()).first()
            due_after = timedelta(seconds=m.interval or 60)
            if last is not None and last.at and datetime.utcnow() - last.at < due_after:
                continue
            ok, value = self._probe(m, check_http, check_tcp, check_ssl)
            db.session.add(Check(monitor_id=m.id, ok=1 if ok else 0, ms=int(value)))
            db.session.commit()
            detect(m, ok)
            checked += 1
        return checked

    @staticmethod
    def _probe(m, check_http, check_tcp, check_ssl):
        """Run the probe named by monitor.type; never raise on a bad target."""
        target = (m.target or "").strip()
        if not target:
            return False, 0.0
        if m.type == "tcp":
            host, _, raw_port = target.rpartition(":")
            if not host or not raw_port.isdigit():
                return False, 0.0
            return check_tcp(host, int(raw_port))
        if m.type == "ssl":
            return check_ssl(target)
        return check_http(target)

    def _run_tick(self):
        if self.app is None:
            return self.tick()
        with self.app.app_context():
            return self.tick()

    def _loop(self):
        while not self._stop.is_set():
            try:
                self._run_tick()
            except Exception as exc:  # noqa: BLE001 - a tick must never kill the thread
                if not self._warned:
                    self._warned = True
                    print("[scheduler] tick failed: %r" % (exc,), file=sys.stderr)
            self._stop.wait(self.interval)
