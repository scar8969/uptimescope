-- ● statuspage schema
CREATE TABLE monitors(id INTEGER PRIMARY KEY, name TEXT, type TEXT DEFAULT 'http', target TEXT, interval INTEGER DEFAULT 60, retries INTEGER DEFAULT 2, active INTEGER DEFAULT 1, created_at DATETIME);
CREATE TABLE checks(id INTEGER PRIMARY KEY, monitor_id INTEGER REFERENCES monitors(id), ok INTEGER DEFAULT 1, ms INTEGER DEFAULT 0, detail TEXT, at DATETIME);
CREATE TABLE incidents(id INTEGER PRIMARY KEY, monitor_id INTEGER REFERENCES monitors(id), started_at DATETIME, resolved_at DATETIME, severity TEXT DEFAULT 'down', message TEXT);
