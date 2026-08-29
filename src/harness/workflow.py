"""Durable workflow runner (Lesson 2).

`run_durably` executes a list of named steps in order, checkpointing after each.
If the process dies mid-run, calling it again with the same run_id skips the
already-completed steps and resumes from the next one. This is the local,
Azure-free equivalent of a Microsoft Agent Framework checkpointed workflow.
"""
from __future__ import annotations

from typing import Callable

from harness.durable.checkpoint import Checkpoint, CheckpointStore

# A step is (name, fn); fn receives accumulated state and returns a dict merged in.
Step = tuple[str, Callable[[dict], dict]]


def run_durably(run_id: str, steps: list[Step], store: CheckpointStore) -> dict:
    cp = store.load(run_id)
    start = 0
    state: dict = {}
    if cp is not None:
        start = cp.step + 1  # resume after the last completed step
        state = dict(cp.state)

    for index in range(start, len(steps)):
        _name, fn = steps[index]
        update = fn(state)
        if update:
            state.update(update)
        store.save(Checkpoint(run_id=run_id, step=index, state=state))

    return state
