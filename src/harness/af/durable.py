"""Durable execution on the Agent Framework (Lesson 2).

The same contract as `harness.workflow.run_durably` — a list of named steps,
checkpointed as they go, resumable by id — but the checkpointing is the
framework's rather than ours: a `WorkflowBuilder` chain of one executor per
step, with `FileCheckpointStorage` behind it.

Two differences from the local runner worth knowing, both verified:

- The framework keys checkpoints by *workflow name*, so `run_id` becomes the
  workflow's name. A resumed run must rebuild an identical graph under that
  same name or it will not find its own checkpoints.
- Recovery is **at-least-once**, exactly as ours is. A step that started and
  died is re-run on resume; only steps that *completed* are skipped. Steps must
  therefore be safe to run twice — the same rule, enforced by the same physics.
"""
from __future__ import annotations

from harness.af import run_sync
from typing import Callable

from agent_framework import (
    Executor,
    FileCheckpointStorage,
    WorkflowBuilder,
    WorkflowContext,
    handler,
)

Step = tuple[str, Callable[[dict], dict]]


class _StepExecutor(Executor):
    """One named step. Takes the accumulated state, returns it updated."""

    def __init__(self, name: str, fn: Callable[[dict], dict], last: bool) -> None:
        super().__init__(id=name)
        self._fn = fn
        self._last = last

    @handler
    async def run(self, state: dict, ctx: WorkflowContext[dict, dict]) -> None:
        update = self._fn(state) or {}
        merged = {**state, **update}
        if self._last:
            await ctx.yield_output(merged)
        else:
            await ctx.send_message(merged)


def _build(run_id: str, steps: list[Step], storage: FileCheckpointStorage):
    if not steps:
        raise ValueError("run_durably needs at least one step")
    execs = [
        _StepExecutor(name, fn, last=(i == len(steps) - 1))
        for i, (name, fn) in enumerate(steps)
    ]
    b = WorkflowBuilder(name=run_id, start_executor=execs[0], checkpoint_storage=storage)
    for a, c in zip(execs, execs[1:]):
        b.add_edge(a, c)
    return b.build()


async def run_durably_async(
    run_id: str, steps: list[Step], checkpoint_dir: str, state: dict | None = None
) -> dict:
    """Run `steps` under a checkpointed Agent Framework workflow.

    Called again with the same `run_id` and an existing checkpoint, it resumes
    from that checkpoint instead of starting over.
    """
    storage = FileCheckpointStorage(checkpoint_dir)
    wf = _build(run_id, steps, storage)
    latest = await storage.get_latest(workflow_name=run_id)
    if latest is None:
        result = await wf.run(dict(state or {}))
    else:
        result = await wf.run(
            checkpoint_id=latest.checkpoint_id, checkpoint_storage=storage
        )
    for ev in reversed(list(result)):
        if getattr(ev, "type", None) == "output":
            return ev.data
    return {}


def run_durably(
    run_id: str, steps: list[Step], checkpoint_dir: str, state: dict | None = None
) -> dict:
    """Blocking wrapper, so this reads like `harness.workflow.run_durably`."""
    return run_sync(run_durably_async(run_id, steps, checkpoint_dir, state), "run_durably_async")
