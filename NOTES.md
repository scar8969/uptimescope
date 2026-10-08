== curl ==
# GET  /api/status
# POST /api/admin/monitors  {"name":"api","type":"http","target":"https://…","interval":60}
# GET  /api/admin/monitors/1/checks
# POST /api/admin/incidents/4/resolve

== session plan ==
# Session 1: checks (http/tcp/ssl vs local servers) → tests
# Session 2: scheduler + incidents + uptime% → tests
# Session 3: alerts + public status page → screenshots
# Session 4: admin + README → CI/Docker/Pages → tag
