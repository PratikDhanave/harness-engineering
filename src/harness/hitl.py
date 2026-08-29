"""Human-in-the-loop approval gate (Lesson 7).

A sensitive action (issue a refund, delete a table, deploy to prod) must PAUSE
for a human decision before it runs. This is a LOCAL stand-in for the Microsoft
Agent Framework `RequestInfoExecutor` — the executor that suspends a workflow,
emits a request to an external approver, and resumes once the reply arrives.

Durability of the suspension is NOT re-invented here: it is *exactly* the
Lesson 2 checkpoint store. `request_approval` writes an "awaiting approval"
checkpoint (the prompt, a requested-at timestamp, and the deadline all live in
the checkpoint state) and returns without touching the action. The process may
crash, restart, or idle for a week — the pending request is on disk (see
`harness.durable.sqlite_store`), so a resume loses nothing. Suspension here means
one durable row, nothing more.

State the leak: a real `RequestInfoExecutor` also ROUTES the request to a person
(a Teams card, an email, a web form), authenticates *who* is allowed to approve,
and correlates their reply back to the right run. This stand-in does none of
that — the "approver" is simply whoever calls `resume()` in the same process,
with no identity, no notification, and no auth. It teaches the suspend / resume /
deadline shape, not the human-facing plumbing.

Execution is at-least-once, not exactly-once (same guarantee as Lesson 2): on
approval the order is load -> action() -> save-terminal-checkpoint. A crash after
the action runs but before the terminal checkpoint is written leaves the run
`awaiting_approval`, so a re-`resume` will run the action again. The injected
action must therefore be idempotent (or externally deduplicated) — doubly important
here because the action is by definition sensitive.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from harness.durable.checkpoint import Checkpoint, CheckpointStore

# Default approval window, in seconds. Tune per action risk; tests inject their
# own so the deadline never depends on wall-clock time.
DEFAULT_TIMEOUT_SECONDS = 3600.0

# Marker written into checkpoint state while a run is parked at the gate.
STATUS_AWAITING = "awaiting_approval"


@dataclass
class ApprovalPending:
    run_id: str
    prompt: str


@dataclass
class ApprovalOutcome:
    status: str  # one of {"approved", "rejected", "timed_out"}
    detail: str


def request_approval(
    run_id: str,
    prompt: str,
    store: CheckpointStore,
    now: float,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> ApprovalPending:
    """Park a run for human approval before its sensitive action.

    The caller has already done any work leading up to the gate; this only writes
    the "awaiting approval" checkpoint and returns.
    Persists an "awaiting approval" checkpoint holding the prompt, the injected
    `now` as the requested-at time, and the deadline — and returns WITHOUT
    performing the action. `now` is passed in (never read from the clock) so the
    recorded deadline is deterministic in tests.
    """
    store.save(
        Checkpoint(
            run_id=run_id,
            step=0,  # the gate; the caller has finished any pre-action work
            state={
                "status": STATUS_AWAITING,
                "prompt": prompt,
                "requested_at": now,
                "timeout_seconds": timeout_seconds,
                "performed": False,
            },
        )
    )
    return ApprovalPending(run_id=run_id, prompt=prompt)


def resume(
    run_id: str,
    decision: bool,
    store: CheckpointStore,
    now: float,
    *,
    action: Callable[[dict], dict] | None = None,
) -> ApprovalOutcome:
    """Resolve a parked run given a human `decision`.

    - approved (and on time) -> perform/record the action, return "approved".
    - rejected              -> abort, return "rejected"; action NOT performed.
    - past the deadline     -> return "timed_out"; action NOT performed, even if
      the decision was yes. The deadline is checked FIRST against the injected
      `now`, so a late "yes" is void.

    If provided, `action` is the sensitive operation; it receives the pending
    state and returns a dict merged into the recorded checkpoint. The terminal
    outcome is written back to the store, so "the action ran" is itself durable.
    """
    cp = _load_pending(run_id, store)
    requested_at = cp.state["requested_at"]
    timeout_seconds = cp.state["timeout_seconds"]

    if now - requested_at > timeout_seconds:
        overdue = now - requested_at
        _resolve(cp, store, now, status="timed_out", performed=False)
        return ApprovalOutcome(
            "timed_out",
            detail=f"approval deadline exceeded ({overdue:.0f}s > {timeout_seconds:.0f}s)",
        )

    if not decision:
        _resolve(cp, store, now, status="rejected", performed=False)
        return ApprovalOutcome("rejected", detail="human rejected; action not performed")

    update = action(dict(cp.state)) if action is not None else {}
    _resolve(cp, store, now, status="approved", performed=True, extra=update)
    return ApprovalOutcome("approved", detail="human approved; action performed")


def _load_pending(run_id: str, store: CheckpointStore) -> Checkpoint:
    """Load the checkpoint for `run_id`, insisting it is still awaiting approval."""
    cp = store.load(run_id)
    if cp is None or cp.state.get("status") != STATUS_AWAITING:
        raise ValueError(f"no approval awaiting resume for run_id {run_id!r}")
    return cp


def _resolve(
    cp: Checkpoint,
    store: CheckpointStore,
    now: float,
    *,
    status: str,
    performed: bool,
    extra: dict | None = None,
) -> None:
    """Overwrite the pending checkpoint with the terminal outcome (durable)."""
    state = dict(cp.state)
    state.update(extra or {})
    state["status"] = status
    state["performed"] = performed
    state["decided_at"] = now
    store.save(Checkpoint(run_id=cp.run_id, step=cp.step + 1, state=state))
