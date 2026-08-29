"""Hierarchical supervision (Lesson 6): a manager fanning work out to sub-agents.

Local stand-in for Microsoft Agent Framework's Magentic / concurrent orchestration,
where a manager LLM decomposes a task, dispatches the pieces to parallel sub-agents,
and gathers their results. Here the "sub-agent" is an injected callable so the
fan-out/fan-in plumbing — parallel dispatch, per-subtask fault isolation, and
stable result ordering — is what gets exercised and tested, with no LLM or network.

State the leak: real supervision is adaptive. The Magentic manager re-plans based on
sub-agent output, retries, and reasons about partial failure. This stand-in is a
one-shot static fan-out: `decompose` is a dumb string split and there is no re-planning
or cross-subtask coordination. What it faithfully models is the concurrency contract —
one worker raising must NOT sink the others, and completion order must NOT leak into
the aggregated result order. Note the isolation covers *faults*, not *liveness*: a
worker that raises is contained, but a worker that hangs forever will block the batch
(`future.result()` is called without a timeout) — cancellation/timeout is part of a
real orchestrator's contract and is deliberately out of scope for this stand-in.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable


@dataclass
class SubResult:
    subtask: str
    output: str | None  # set on success, None when the worker raised
    error: str | None  # set to the isolated exception text, None on success


@dataclass
class Aggregate:
    results: list[SubResult]  # in decomposition order, NOT completion order
    succeeded: int
    failed: int


class Supervisor:
    """A manager that splits a task and runs each piece on a worker in parallel.

    The `worker` is the seam: inject a real LLM sub-agent call in production, or a
    plain function in tests. `max_workers` bounds the thread pool the same way a
    managed orchestrator bounds concurrent sub-agent invocations.
    """

    def __init__(
        self,
        worker: Callable[[str], str],
        max_workers: int = 4,
        *,
        executor_factory: Callable[[], object] | None = None,
    ):
        """`executor_factory` is the second seam, alongside `worker`.

        It returns a context manager exposing `submit(fn, arg) -> future`, i.e.
        the slice of `concurrent.futures.Executor` this class actually uses.
        Defaults to a `ThreadPoolExecutor` bounded by `max_workers`.

        It exists because threads are not universally available: CPython on
        WebAssembly (Pyodide) raises `RuntimeError: can't start new thread`, so
        without this seam the module cannot run in a browser at all. Injecting a
        synchronous executor keeps the two behaviours this class actually
        guarantees — fault isolation and decomposition-order output — testable
        anywhere.

        State the leak: a synchronous executor gives up the one thing the
        default is for. Fan-out becomes sequential, so wall-clock no longer
        overlaps and a worker that blocks stalls everything after it. Use it to
        exercise the contract, never to claim parallelism.
        """
        self.worker = worker
        self.max_workers = max_workers
        self.executor_factory = executor_factory

    def decompose(self, task: str) -> list[str]:
        """Split a task into subtasks deterministically.

        A deliberately naive planner: break on ";" and newlines, trim whitespace,
        drop empties. If nothing splits out, the whole task is a single subtask.
        A real manager would use an LLM to plan; this keeps decomposition pure and
        reproducible so the concurrency behaviour is what the tests pin down.
        """
        pieces = [
            part.strip()
            for chunk in task.split("\n")
            for part in chunk.split(";")
            if part.strip()
        ]
        return pieces or [task]

    def run(self, task: str) -> Aggregate:
        """Decompose, fan out to the worker in parallel, then fan in the results.

        Each subtask runs on its own thread-pool slot. A worker that raises is
        ISOLATED into that subtask's `SubResult.error` — the exception never
        escapes `run`, so a single bad sub-agent cannot fail the whole batch.
        Results are collected back in decomposition order regardless of which
        worker finished first.
        """
        subtasks = self.decompose(task)

        # Pre-size the results list so we can slot each outcome by its original
        # index — this is what keeps output order independent of completion order.
        results: list[SubResult | None] = [None] * len(subtasks)

        make_pool = self.executor_factory or (
            lambda: ThreadPoolExecutor(max_workers=self.max_workers)
        )
        with make_pool() as pool:
            futures = {
                pool.submit(self.worker, subtask): index
                for index, subtask in enumerate(subtasks)
            }
            for future, index in futures.items():
                subtask = subtasks[index]
                try:
                    output = future.result()
                    results[index] = SubResult(
                        subtask=subtask, output=output, error=None
                    )
                except Exception as exc:  # isolate: one failure must not sink the rest
                    results[index] = SubResult(
                        subtask=subtask, output=None, error=str(exc)
                    )

        ordered = [r for r in results if r is not None]
        succeeded = sum(1 for r in ordered if r.error is None)
        failed = len(ordered) - succeeded
        return Aggregate(results=ordered, succeeded=succeeded, failed=failed)
