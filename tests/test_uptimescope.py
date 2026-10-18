"""B2 statuspage — tests. Run: pytest test_uptimescope.py"""

import threading

import pytest

flask_ok = True
try:
    import flask_sqlalchemy
except ImportError:
    flask_ok = False
from http.server import BaseHTTPRequestHandler, HTTPServer


class OkServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *a):
        pass


@pytest.fixture(scope="module")
def server():
    srv = HTTPServer(("127.0.0.1", 0), OkServer)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv.server_address[1]
    srv.shutdown()


def test_check_http_ok(server):
    from statuspage.monitor.checks import check_http

    ok, ms = check_http(f"http://127.0.0.1:{server}/")
    assert ok and ms >= 0


def test_check_http_down():
    from statuspage.monitor.checks import check_http

    ok, _ = check_http("http://127.0.0.1:1/", timeout=1)
    assert not ok


def test_check_tcp_ok(server):
    from statuspage.monitor.checks import check_tcp

    ok, _ = check_tcp("127.0.0.1", server)
    assert ok


def test_check_tcp_down():
    from statuspage.monitor.checks import check_tcp

    ok, _ = check_tcp("127.0.0.1", 1, timeout=1)
    assert not ok


@pytest.mark.skipif(not flask_ok, reason="flask-sqlalchemy not installed")
def test_uptime_pct_empty():
    from statuspage.monitor.incidents import uptime_pct

    assert uptime_pct(999) == 100.0
