"""Append-only local audit events, hash-chained for tamper detection, without payloads."""

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


class AuditLog:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with sqlite3.connect(path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY, body TEXT NOT NULL,
                previous TEXT NOT NULL, digest TEXT NOT NULL)""")

    def record(self, action: str, outcome: str, feature: str = "") -> None:
        body = json.dumps(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "action": action,
                "outcome": outcome,
                "feature": feature,
            },
            sort_keys=True,
        )
        with sqlite3.connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT digest FROM events ORDER BY id DESC LIMIT 1").fetchone()
            previous = row[0] if row else "0" * 64
            digest = hashlib.sha256((previous + body).encode()).hexdigest()
            db.execute(
                "INSERT INTO events(body, previous, digest) VALUES (?, ?, ?)",
                (body, previous, digest),
            )

    def events(self) -> list[dict]:
        with sqlite3.connect(self.path) as db:
            rows = db.execute("SELECT body, previous, digest FROM events ORDER BY id").fetchall()
        previous = "0" * 64
        result = []
        for body, prior, digest in rows:
            if prior != previous or hashlib.sha256((prior + body).encode()).hexdigest() != digest:
                raise ValueError("Audit chain verification failed")
            result.append(json.loads(body))
            previous = digest
        return result
