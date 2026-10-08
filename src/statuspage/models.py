from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Monitor(db.Model):
    __tablename__ = "monitors"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), default="")
    type = db.Column(db.String(8), default="http")  # http|tcp|ssl
    target = db.Column(db.String(256), default="")
    interval = db.Column(db.Integer, default=60)
    retries = db.Column(db.Integer, default=2)
    active = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Check(db.Model):
    __tablename__ = "checks"
    id = db.Column(db.Integer, primary_key=True)
    monitor_id = db.Column(db.Integer, db.ForeignKey("monitors.id"), index=True)
    ok = db.Column(db.Integer, default=1)
    ms = db.Column(db.Integer, default=0)
    detail = db.Column(db.String(256), default="")
    at = db.Column(db.DateTime, default=datetime.utcnow)

class Incident(db.Model):
    __tablename__ = "incidents"
    id = db.Column(db.Integer, primary_key=True)
    monitor_id = db.Column(db.Integer, db.ForeignKey("monitors.id"))
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    severity = db.Column(db.String(16), default="down")  # degraded|down
    message = db.Column(db.String(256), default="")
