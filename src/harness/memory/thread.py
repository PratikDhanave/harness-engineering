"""Short-term conversation memory — the per-conversation thread (Lesson 4).

The `ThreadStore` protocol is the swap point: a local SQLite store for offline
dev/tests, and (later) Azure AI Agent Service *managed threads* — same interface,
so agent code appends turns and replays history without knowing which backs it.

An append-only row-per-turn table is what makes the transcript survive a process
restart, and reading back in insertion order is what makes the replayed history
faithful to what the user and agent actually said.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class Message:
    role: str  # e.g. "user" / "assistant" / "system"
    content: str


class ThreadStore(Protocol):
    def append(self, thread_id: str, role: str, content: str) -> None: ...

    def history(self, thread_id: str) -> list[Message]: ...


class SQLiteThreadStore:
    """SQLite-backed thread store — local stand-in for Agent Service managed threads.

    Where this is weaker than the managed service (state the leak): Azure threads
    are a multi-tenant, replicated, access-controlled service with server-side
    trimming/summarization built in. This is a single local file with no auth, no
    replication, and unbounded growth — every turn is retained forever until you
    prune it yourself. Good enough to develop and test the *shape* of memory.
    """

    def __init__(self, path: str | Path = ".harness/threads.db"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        # AUTOINCREMENT `seq` gives a stable insertion order that is independent of
        # wall-clock time, so two turns appended in the same millisecond still read
        # back in the order they were written.
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS messages ("
            " seq INTEGER PRIMARY KEY AUTOINCREMENT,"
            " thread_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL)"
        )
        self._conn.commit()

    def append(self, thread_id: str, role: str, content: str) -> None:
        self._conn.execute(
            "INSERT INTO messages (thread_id, role, content) VALUES (?, ?, ?)",
            (thread_id, role, content),
        )
        self._conn.commit()

    def history(self, thread_id: str) -> list[Message]:
        rows = self._conn.execute(
            "SELECT role, content FROM messages WHERE thread_id = ? ORDER BY seq",
            (thread_id,),
        ).fetchall()
        return [Message(role=role, content=content) for role, content in rows]

    def close(self) -> None:
        self._conn.close()
