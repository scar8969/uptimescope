<p align="center">
  <img src="docs/assets/screens/root.png" alt="uptimescope running" width="900">
</p>

<h1 align="center">uptimescope</h1>

<p align="center"><b>Uptime monitoring with a public status page that tells the truth.</b></p>

<p align="center">
  <a href="https://github.com/scar8969/uptimescope/actions/workflows/ci.yml"><img src="https://github.com/scar8969/uptimescope/actions/workflows/ci.yml/badge.svg" alt="ci"></a> <a href="#quality-gates"><img src="https://img.shields.io/badge/tests-25%20passed-2ea44f" alt="tests: 25 passed"></a> <a href="#quality-gates"><img src="https://img.shields.io/badge/coverage-60.0%-yellow" alt="coverage: 60.0%"></a> <a href="#api"><img src="https://img.shields.io/badge/routes-8%20live-0969da" alt="routes: 8 live"></a> <a href="#requirements"><img src="https://img.shields.io/badge/python-3.11%2B-3776ab" alt="python: 3.11+"></a> <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-2ea44f" alt="license: MIT"></a>
</p>

uptimescope probes the endpoints you list on an interval, stores every check, opens an incident when a probe starts failing, and serves a public page with the uptime percentage and the incident history.

---

**Contents** &nbsp;·&nbsp; [Why](#why-this-exists) &nbsp;·&nbsp; [What it does](#what-it-does) &nbsp;·&nbsp; [Quickstart](#quickstart) &nbsp;·&nbsp; [Screenshots](#screenshots) &nbsp;·&nbsp; [API](#api) &nbsp;·&nbsp; [CLI](#cli) &nbsp;·&nbsp; [Configuration](#configuration) &nbsp;·&nbsp; [Measured](#measured-not-estimated) &nbsp;·&nbsp; [How a request flows](#how-a-request-flows) &nbsp;·&nbsp; [Architecture](#architecture) &nbsp;·&nbsp; [Quality gates](#quality-gates) &nbsp;·&nbsp; [Development](#development) &nbsp;·&nbsp; [Deploy](#deploy) &nbsp;·&nbsp; [Limits](#limits-stated-rather-than-hidden)

## Why this exists

A status page is only worth reading if it is generated from the same checks that trigger alerts. This one stores each probe result, computes uptime from those rows, and shows the last 30 checks per monitor as a strip — no hand-edited banner.

## What it does

| Capability | How it works |
| --- | --- |
| **Background scheduler** | A poller thread runs the probes on an interval; disabling it is one environment variable. |
| **Check history** | Every probe result is a row with status, latency and timestamp. |
| **Incidents** | An incident opens after the monitor's retry budget of consecutive failures and closes on the first success; resolving one is an explicit action with a timestamp. |
| **Public page and JSON** | The same data renders as HTML for humans and GET /api/status for machines. |
| **Admin page** | Add monitors and resolve incidents without touching the API. |

## Quickstart

```sh
git clone https://github.com/scar8969/uptimescope.git
cd uptimescope
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python wsgi.py                                 # http://127.0.0.1:8000
```

It is up when this answers:

```sh
curl -s http://127.0.0.1:8000/
```

## Screenshots

Captured from the running service with headless Chromium at 1440×900, one image per page, committed under [`docs/assets/screens/`](docs/assets/screens/).

<table>
<tr>
<td width="50%"><img src="docs/assets/screens/admin.png" alt="/admin" width="100%"><br><sub><code>/admin</code> &middot; 38.4 KB</sub></td>
<td width="50%"><img src="docs/assets/screens/healthz.png" alt="/healthz" width="100%"><br><sub><code>/healthz</code> &middot; 8.3 KB</sub></td>
</tr>
</table>

<table>
<tr>
<td width="50%"><img src="docs/assets/screens/livez.png" alt="/livez" width="100%"><br><sub><code>/livez</code> &middot; 7.3 KB</sub></td>
<td width="50%"><img src="docs/assets/screens/metrics.png" alt="/metrics" width="100%"><br><sub><code>/metrics</code> &middot; 14.8 KB</sub></td>
</tr>
</table>

<table>
<tr>
<td width="50%"><img src="docs/assets/screens/readyz.png" alt="/readyz" width="100%"><br><sub><code>/readyz</code> &middot; 7.7 KB</sub></td>
<td width="50%"><img src="docs/assets/screens/version.png" alt="/version" width="100%"><br><sub><code>/version</code> &middot; 26.0 KB</sub></td>
</tr>
</table>

## API

Every route below is declared in [`openapi/uptimescope.yaml`](openapi/uptimescope.yaml) and exercised by the live probe recorded in [`docs/EVIDENCE.md`](docs/EVIDENCE.md).

| Method | Path | What it does |
| --- | --- | --- |
| `GET` | `/` | public status page (HTML) |
| `GET` | `/admin` | admin page (HTML) - add monitors, resolve incidents |
| `GET` | `/api/status` | public status as JSON |
| `POST` | `/api/admin/monitors` | add monitor |
| `GET` | `/api/admin/monitors/<int:mid>/checks` | last 100 checks for a monitor |
| `POST` | `/api/admin/incidents/<int:iid>/resolve` | resolve an incident |

## CLI

The same operations without an HTTP client. Installed as `uptimescope`, and runnable from a checkout with no install:

```sh
python -m statuspage.cli --help
```

```text
usage: statuspage [-h] {status,add,checks,resolve,monitors} ...

Query and administer a running statuspage instance.

positional arguments:
  {status,add,checks,resolve,monitors}
    status              public status: every monitor and its uptime
    add                 register a monitor
    checks              last 100 checks for a monitor
    resolve             mark an incident resolved
    monitors            list monitors from the local database

options:
  -h, --help            show this help message and exit

Set STATUSPAGE_URL to point at a different host (default http://127.0.0.1:8000).
```

## Configuration

Environment only — there is no config file. Copy `.env.example` to `.env` and edit; `APP_ENV=production` refuses to start without `SECRET_KEY`.

| Variable | Default | Meaning |
| --- | --- | --- |
| `APP_ENV` | `development` | development \| staging \| production; production enforces the secret. |
| `SECRET_KEY` | `change-me-in-production` | Session/CSRF signing key. Required when APP_ENV=production. |
| `HOST` | `0.0.0.0` | Interface the dev server binds. |
| `PORT` | `8000` | Port the dev server and the container listen on. |
| `DEBUG` | `false` | Flask debug mode. Never true in production. |
| `MAX_CONTENT_LENGTH` | `8388608` | Largest accepted request body, in bytes. |
| `DATA_DIR` | `(empty)` | Where uploaded and generated files live. |
| `INSTANCE_DIR` | `(empty)` | Where the SQLite file and instance state live. |
| `LOG_DIR` | `(empty)` | Where rotated log files are written, if file logging is on. |
| `LOG_LEVEL` | `INFO` | DEBUG \| INFO \| WARNING \| ERROR. |
| `LOG_JSON` | `true` | true emits one JSON object per line; false is human-readable. |
| `REQUEST_ID_HEADER` | `X-Request-ID` | Header echoed on every response and stamped on every log line. |
| `CHECK_INTERVAL` | `30` | Seconds between scheduler passes. |
| `MONITOR_SCHEDULER` | `on` | Set to off to run the web app without the background poller. |
| `STATUSPAGE_URL` | `http://127.0.0.1:8000` | Base URL the CLI talks to. |

## Measured, not estimated

Produced on this checkout by `pytest --cov` and by booting `wsgi.py` and issuing one real GET per documented path. The commands are recorded in [`docs/EVIDENCE.md`](docs/EVIDENCE.md).

| Signal | Value |
| --- | --- |
| Tests | **25 / 25 passed** (3.8 s, exit 0) |
| Line coverage | **60.0%** — 486 of 761 statements |
| Source | 16 files / 1,646 lines |
| Test code | 4 files / 264 lines |
| Documented paths | 6 in the spec, 4 GET |
| Live probe | 9 GET requests to the booted app, **8 answered 200** |
| Median latency | **7.8 ms** (single uncached request, dev server) |
| Slowest / fastest | 47.5 ms `/` / 4.9 ms `/metrics` |
| Bytes served | 11.9 KB across 9 responses |
| Screenshots | 7 captured |

## How a request flows

```text
client
  │  HTTP
  ▼
wsgi.py ──▶ statuspage/app.py:get_app()
                │  reads config once (statuspage/config.py)
                │  registers the `monitor` blueprint
                ▼
           route handler
             ├──▶ statuspage/models.py        tables, via Flask-SQLAlchemy
             ├──▶ statuspage/errors.py        raises typed errors → one JSON envelope
             └──▶ statuspage/observability.py JSON log line + X-Request-ID
```

Every response carries `X-Request-ID`, and the matching log line is written once at the end of the request with the status and duration, so a report of "it failed" is one `grep` away from the traceback.

## Architecture

```
uptimescope/
├── src/statuspage/
│   ├── http.py                         379  HTTP plumbing for statuspage: correlation ids, acces
│   ├── config.py                       173  Environment-driven configuration for statuspage
│   ├── cli.py                          169  statuspage command line client
│   ├── observability.py                169  Structured logging and request correlation for statu
│   ├── _app.py                         133  Flask application: the public status page plus the J
│   ├── app.py                          119  Application factory for statuspage
│   ├── monitor/api.py                  110  JSON API for the status page and the admin UI
│   ├── errors.py                       108  Typed application errors and their HTTP mapping for 
│   ├── monitor/scheduler.py             92  Polling scheduler: every `interval` seconds, check e
│   ├── paths.py                         52  Filesystem layout for statuspage
│   ├── monitor/incidents.py             47  Incident detection and uptime maths
│   ├── models.py                        38  
├── openapi/uptimescope.yaml               the contract of record
├── schema/uptimescope.sql                 the DDL
├── tests/                       the suite that has to stay green
├── docs/EVIDENCE.md             the recorded live route walk
├── Dockerfile                   multi-stage build
└── wsgi.py                      entry point
```

The package keeps one shape across the service: `config.py` reads the environment once, `observability.py` emits structured JSON logs carrying a request id, `errors.py` turns exceptions into a single JSON envelope, `models.py` holds the tables, and the `monitor/` package holds the routes.

## Quality gates

| Gate | Command | Threshold |
| --- | --- | --- |
| Suite | `pytest -q` | all green |
| Coverage | `pytest --cov` | floor in `pyproject.toml`, set below the measured value |
| Lint | `ruff check src tests` | zero findings |
| Format | `ruff format --check src tests` | zero reformats |
| Types | `mypy src` | zero errors |
| Security | `bandit -c pyproject.toml -r src` | reviewed skip list, no unreviewed finding |
| Live routes | boot `wsgi.py`, one GET per documented path | no 5xx, no undocumented guard |

CI runs the first six on Python 3.11, 3.12 and 3.13 on every push to `main`, plus a container build — [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Development

```sh
pip install -e ".[dev]"
python -m pytest -q                      # the suite
python -m pytest --cov                   # with the coverage floor
python -m ruff check src tests           # lint
python -m ruff format --check src tests  # formatting
python -m mypy src                       # types
python -m bandit -c pyproject.toml -r src  # security
pre-commit install                       # the same checks on commit
```

Dependabot opens grouped PRs for the dev tooling weekly and for actions and the base image monthly.

## Deploy

```sh
docker build -t uptimescope .
docker run --rm -p 8000:8000 --env-file .env.example uptimescope
```

A `docker-compose.yml` is included for a local run with a volume for the SQLite file. The image runs as a non-root user and serves through gunicorn.

## Limits, stated rather than hidden

- Probes run from the host the service runs on, so they measure that vantage point only.
- Uptime is computed from stored checks, so a window with no checks reports 100% rather than unknown.

## License

MIT — see [LICENSE](LICENSE).
