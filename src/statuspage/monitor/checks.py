import socket
import ssl
import time
import urllib.request

from ..clock import utcnow


def check_http(url, timeout=10.0):
    s = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status < 500, (time.perf_counter() - s) * 1000
    except Exception:
        return False, (time.perf_counter() - s) * 1000


def check_tcp(host, port, timeout=5.0):
    s = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout):
            return True, (time.perf_counter() - s) * 1000
    except Exception:
        return False, (time.perf_counter() - s) * 1000


def check_ssl(host, port=443, timeout=5.0):
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as tls:
                cert = tls.getpeercert() or {}
                from datetime import datetime

                not_after = datetime.strptime(str(cert["notAfter"]), "%b %d %H:%M:%S %Y %Z")
                days = (not_after - utcnow()).days
                return days > 0, days
    except Exception:
        return False, 0
