"""SQLite-backed checkpoint store — local stand-in for Azure Cosmos DB.

One row per run_id; `save()` upserts so only the latest checkpoint is retained.
Writing to a single file (not memory) is what makes recovery survive a process
restart — the whole point of Lesson 2.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from harness.durable.checkpoint import Checkpoint


class SQLiteCheckpointStore:
    def __init__(self, path: str | Path = ".harness/checkpoints.db"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS checkpoints ("
            " run_id TEXT PRIMARY KEY, step INTEGER NOT NULL, state TEXT NOT NULL)"
        )
        self._conn.commit()

    def load(self, run_id: str) -> Checkpoint | None:
        row = self._conn.execute(
            "SELECT step, state FROM checkpoints WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None:
            return None
        return Checkpoint(run_id=run_id, step=row[0], state=json.loads(row[1]))

    def save(self, checkpoint: Checkpoint) -> None:
        self._conn.execute(
            "INSERT INTO checkpoints (run_id, step, state) VALUES (?, ?, ?) "
            "ON CONFLICT(run_id) DO UPDATE SET step=excluded.step, state=excluded.state",
            (checkpoint.run_id, checkpoint.step, json.dumps(checkpoint.state)),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
