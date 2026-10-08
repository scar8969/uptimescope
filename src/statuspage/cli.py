#!/usr/bin/env python3
"""statuspage command line client.

```
python cli.py status
python cli.py add --name api --target https://example.com --type http
python cli.py checks 1
python cli.py resolve 2
python cli.py monitors
```

The network commands use `urllib` from the standard library only, so this file
imports and prints `--help` even before `pip install -r requirements.txt`.
`monitors` reads the SQLite file directly and therefore needs Flask-SQLAlchemy;
it fails with a one-line message when that is missing instead of a traceback.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from . import paths

BASE = os.environ.get("STATUSPAGE_URL", "http://127.0.0.1:8000")

def _request(method, path, body=None):
    """Issue one request and return (status, parsed-or-text body)."""
    url = BASE.rstrip("/") + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8", "replace")
            status = resp.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        status = exc.code
    except urllib.error.URLError as exc:
        return None, str(exc.reason)
    try:
        return status, json.loads(raw)
    except ValueError:
        return status, raw

def _print(status, payload):
    if status is None:
        print("could not reach %s: %s" % (BASE, payload), file=sys.stderr)
        return 1
    body = json.dumps(payload, indent=2, sort_keys=True) if not isinstance(payload, str) else payload
    print("HTTP %s" % status)
    print(body)
    return 0 if status < 400 else 1

def cmd_status(args):
    return _print(*_request("GET", "/api/status"))

def cmd_add(args):
    body = {"name": args.name, "target": args.target, "type": args.type,
            "interval": args.interval, "retries": args.retries}
    return _print(*_request("POST", "/api/admin/monitors", body))

def cmd_checks(args):
    return _print(*_request("GET", "/api/admin/monitors/%d/checks" % args.monitor_id))

def cmd_resolve(args):
    return _print(*_request("POST", "/api/admin/incidents/%d/resolve" % args.incident_id))

def cmd_monitors(args):
    """Read the monitors straight out of the database the app writes to."""
    root = str(paths.PROJECT_ROOT)
    try:
        os.environ.setdefault("PYTHONPATH", root)
        if root not in sys.path:
            sys.path.insert(0, root)
        from flask import Flask
        from .models import Check, Monitor, db
    except ImportError as exc:
        print("monitors needs Flask-SQLAlchemy (%s)." % exc, file=sys.stderr)
        print("Run: pip install -r requirements.txt", file=sys.stderr)
        return 2
    instance = str(paths.INSTANCE_DIR)
    paths.ensure_runtime_dirs()
    app = Flask(__name__, instance_path=instance)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + str(paths.INSTANCE_DIR / "statuspage.db")
    db.init_app(app)
    with app.app_context():
        rows = Monitor.query.order_by(Monitor.name).all()
        if not rows:
            print("no monitors configured")
            return 0
        print("%-4s %-20s %-6s %-34s %8s %7s %s" % ("id", "name", "type", "target", "interval", "checks", "active"))
        for m in rows:
            n = Check.query.filter_by(monitor_id=m.id).count()
            print("%-4d %-20s %-6s %-34s %8ds %7d %s"
                  % (m.id, m.name, m.type, m.target, m.interval, n, "yes" if m.active else "no"))
    return 0

def build_parser():
    ap = argparse.ArgumentParser(
        prog="statuspage",
        description="Query and administer a running statuspage instance.",
        epilog="Set STATUSPAGE_URL to point at a different host (default http://127.0.0.1:8000).")
    sub = ap.add_subparsers(dest="command")

    s = sub.add_parser("status", help="public status: every monitor and its uptime")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("add", help="register a monitor")
    s.add_argument("--name", required=True, help="display name, e.g. api")
    s.add_argument("--target", required=True, help="URL (http), host:port (tcp) or hostname (ssl)")
    s.add_argument("--type", default="http", choices=("http", "tcp", "ssl"))
    s.add_argument("--interval", type=int, default=60, help="seconds between checks (default 60)")
    s.add_argument("--retries", type=int, default=2, help="failures before an incident opens (default 2)")
    s.set_defaults(func=cmd_add)

    s = sub.add_parser("checks", help="last 100 checks for a monitor")
    s.add_argument("monitor_id", type=int)
    s.set_defaults(func=cmd_checks)

    s = sub.add_parser("resolve", help="mark an incident resolved")
    s.add_argument("incident_id", type=int)
    s.set_defaults(func=cmd_resolve)

    s = sub.add_parser("monitors", help="list monitors from the local database")
    s.set_defaults(func=cmd_monitors)

    return ap

def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) is None:
        parser.print_help()
        return 0
    return args.func(args)
