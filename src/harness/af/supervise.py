"""Supervision on the Agent Framework (Lesson 6).

A manager splits a task, the pieces run side by side, and the results come back
together. In `harness.orchestration.supervisor` that is a ThreadPoolExecutor and
a pre-sized results list; here it is the workflow graph itself — `add_fan_out_edges`
to hand the work out, `add_fan_in_edges` to gather it in.

Two properties carried over from the local version, because they are the lesson:

- **One failure does not sink the batch.** A worker that raises records its
  error and still reports, so the other results survive.
- **Results come back in decomposition order**, not completion order, so the
  output is stable and diffable no matter who finished first.

Why not `ConcurrentBuilder`/`MagenticBuilder`? Both are installed. Both are
*agent-shaped*: `ConcurrentBuilder` dispatches an `AgentExecutorRequest` to its
participants, so a worker has to speak the agent message model rather than being
an ordinary callable — verified, not assumed. Our seam takes a plain function,
which is what lets Lesson 6 run with no model at all. Fan-out and fan-in edges
are core workflow features and fit that shape exactly. Reach for the builders
when the workers really are agents.

State the leak: the fan-out is static — the manager decides the split once and
cannot re-plan when a piece comes back badly. That is what Magentic adds.
"""
from __future__ import annotations

from harness.af import run_sync
from dataclasses import dataclass, field

from agent_framework import Executor, WorkflowBuilder, WorkflowContext, handler

MAX_WORKERS = 4


@dataclass
class SubResult:
    subtask: str
    output: str | None = None
    error: str | None = None


@dataclass
class Aggregate:
    results: list[SubResult] = field(default_factory=list)

    @property
    def succeeded(self) -> int:
        return sum(1 for r in self.results if r.error is None)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.error is not None)


def decompose(task: str) -> list[str]:
    """Naive splitter — on `;` then newlines. Same as the local supervisor."""
    parts = [p.strip() for chunk in task.split(";") for p in chunk.splitlines()]
    return [p for p in parts if p]


class _Manager(Executor):
    @handler
    async def split(self, task: str, ctx: WorkflowContext[list[str]]) -> None:
        subtasks = decompose(task)
        if len(subtasks) > MAX_WORKERS:
            raise ValueError(
                f"{len(subtasks)} subtasks but only {MAX_WORKERS} workers; "
                "raise MAX_WORKERS or split the task further upstream"
            )
        await ctx.send_message(subtasks)


class _Worker(Executor):
    """One slot in the pool. Takes the subtask at its own index, if there is one."""

    def __init__(self, index: int, worker) -> None:
        super().__init__(id=f"worker{index}")
        self._index = index
        self._worker = worker

    @handler
    async def work(self, subtasks: list[str], ctx: WorkflowContext[SubResult | None]) -> None:
        if self._index >= len(subtasks):
            await ctx.send_message(None)      # this slot was not needed
            return
        subtask = subtasks[self._index]
        try:
            await ctx.send_message(SubResult(subtask, output=self._worker(subtask)))
        except Exception as exc:              # isolation is the whole point
            await ctx.send_message(SubResult(subtask, error=f"{type(exc).__name__}: {exc}"))


class _Gather(Executor):
    @handler
    async def gather(
        self, results: list[SubResult | None], ctx: WorkflowContext[Aggregate, Aggregate]
    ) -> None:
        # Fan-in hands them over in source order, which is decomposition order,
        # not completion order — so the roll-up is stable.
        await ctx.yield_output(Aggregate([r for r in results if r is not None]))


def build_supervisor(worker):
    manager = _Manager(id="manager")
    workers = [_Worker(i, worker) for i in range(MAX_WORKERS)]
    gather = _Gather(id="gather")
    return (
        WorkflowBuilder(name="supervisor", start_executor=manager)
        .add_fan_out_edges(manager, workers)
        .add_fan_in_edges(workers, gather)
        .build()
    )


async def run_async(task: str, worker) -> Aggregate:
    events = await build_supervisor(worker).run(task)
    for ev in reversed(list(events)):
        if getattr(ev, "type", None) == "output":
            return ev.data
    raise RuntimeError("the supervisor produced no aggregate")


def run(task: str, worker) -> Aggregate:
    return run_sync(run_async(task, worker), "run_async")
