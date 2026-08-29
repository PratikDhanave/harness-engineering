"""Checkpoint model + storage seam for durable execution.

The `CheckpointStore` protocol is the swap point: a local SQLite store for offline
dev/tests, and (later) an Azure Cosmos DB store — same interface, no change to the
workflow logic in `harness.workflow`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class Checkpoint:
    run_id: str
    step: int  # index of the last COMPLETED step
    state: dict


class CheckpointStore(Protocol):
    def load(self, run_id: str) -> Checkpoint | None: ...

    def save(self, checkpoint: Checkpoint) -> None: ...
