import json
import urllib.request


def alert(channel, monitor, incident):
    try:
        payload = json.dumps(
            {
                "text": f"⚠ {monitor.name} {incident.severity} since {incident.started_at.isoformat()}"
            }
        ).encode()
        req = urllib.request.Request(
            channel, data=payload, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10):
            pass
    except Exception:
        pass
