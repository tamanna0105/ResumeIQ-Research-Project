import json
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


DATABASE_PATH = Path(os.getenv("RESUMEIQ_DB_PATH", str(Path(tempfile.gettempdir()) / "resumeiq_experiments.sqlite3")))


def _connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute(
        "CREATE TABLE IF NOT EXISTS experiment_runs ("
        "id TEXT PRIMARY KEY, created_at TEXT NOT NULL, metrics_json TEXT NOT NULL)"
    )
    return connection


def record_experiment(metrics: dict) -> str:
    """Store aggregate research metrics only; never store resume or job text."""
    experiment_id = str(uuid4())
    with _connect() as connection:
        connection.execute(
            "INSERT INTO experiment_runs (id, created_at, metrics_json) VALUES (?, ?, ?)",
            (experiment_id, datetime.now(timezone.utc).isoformat(), json.dumps(metrics)),
        )
    return experiment_id


def list_experiments(limit: int = 20) -> list[dict]:
    with _connect() as connection:
        rows = connection.execute(
            "SELECT id, created_at, metrics_json FROM experiment_runs ORDER BY created_at DESC LIMIT ?",
            (max(1, min(limit, 100)),),
        ).fetchall()
    return [{"id": row[0], "created_at": row[1], **json.loads(row[2])} for row in rows]