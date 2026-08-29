"""The human gate on the Agent Framework (Lesson 7).

`harness.hitl` parks a run by writing an "awaiting_approval" checkpoint and
resumes when someone calls `resume()`. The framework has a first-class version
of that shape: an executor calls `ctx.request_info(...)`, the workflow stops and
emits a request, and the run is continued later by handing the answer back —
`wf.run(responses={request_id: answer})`.

The same three outcomes as ours, and for the same reasons:

    approved   the action runs, then the run finishes
    rejected   the action never runs
    timed_out  the deadline passed before the answer arrived, so a late yes
               is void — checked BEFORE the decision is read, because a
               deadline that only applies to "no" is not a deadline

`now` is injected rather than read from the clock, so a test can be exact about
a late answer without sleeping.
"""
# NOTE: no `from __future__ import annotations` in this module, deliberately.
# It would make every annotation a *string* at runtime, and the framework's
# response_handler validator calls get_origin() on the raw annotation without
# resolving it — so a correct WorkflowContext[...] is rejected with a message
# that quotes the very type it wanted. @handler resolves strings;
# @response_handler does not.
from harness.af import run_sync
from dataclasses import dataclass
from typing import Any, Callable

from agent_framework import (
    Executor,
    WorkflowBuilder,
    WorkflowContext,
    handler,
    response_handler,
)

APPROVED = "approved"
REJECTED = "rejected"
TIMED_OUT = "timed_out"


@dataclass
class ApprovalRequest:
    """What the person is being asked. This is what reaches the outside world."""

    prompt: str
    requested_at: float
    deadline: float


@dataclass
class ApprovalReply:
    """What comes back. `decided_at` is injected, never read from the clock."""

    approved: bool
    decided_at: float


@dataclass
class GateOutcome:
    status: str
    detail: str


class _Gate(Executor):
    def __init__(self, action: Callable[[], str], timeout_seconds: float, now: float):
        super().__init__(id="human_gate")
        self._action = action
        self._timeout = timeout_seconds
        self._now = now

    @handler
    async def ask(self, prompt: str, ctx: WorkflowContext) -> None:
        await ctx.request_info(
            ApprovalRequest(
                prompt=prompt,
                requested_at=self._now,
                deadline=self._now + self._timeout,
            ),
            ApprovalReply,
        )

    @response_handler
    async def decided(
        self,
        original_request: ApprovalRequest,
        reply: ApprovalReply,
        ctx: WorkflowContext[Any, GateOutcome],
    ) -> None:
        # Deadline first. A late "yes" is void, and checking the decision first
        # would quietly make that untrue.
        if reply.decided_at > original_request.deadline:
            await ctx.yield_output(
                GateOutcome(TIMED_OUT, "the deadline passed before an answer arrived")
            )
            return
        if not reply.approved:
            await ctx.yield_output(GateOutcome(REJECTED, "a person said no"))
            return
        await ctx.yield_output(GateOutcome(APPROVED, self._action()))


async def ask_then_act_async(
    prompt: str,
    action: Callable[[], str],
    *,
    approve: bool,
    now: float = 0.0,
    decided_at: float = 1.0,
    timeout_seconds: float = 60.0,
) -> GateOutcome:
    """Run the gate to a decision and return the outcome.

    Split into two `run` calls on purpose: the first stops at the request with
    the action NOT performed, and only the second — carrying a human's answer —
    can let it happen.
    """
    gate = _Gate(action, timeout_seconds, now)
    wf = WorkflowBuilder(name="human-gate", start_executor=gate).build()

    events = await wf.run(prompt)
    pending = [e for e in events if getattr(e, "type", None) == "request_info"]
    if not pending:
        raise RuntimeError("the gate did not stop to ask anybody")
    request_id = pending[0].request_id

    events = await wf.run(
        responses={request_id: ApprovalReply(approved=approve, decided_at=decided_at)}
    )
    for ev in reversed(list(events)):
        if getattr(ev, "type", None) == "output":
            return ev.data
    raise RuntimeError("the gate never reached an outcome")


def ask_then_act(prompt: str, action: Callable[[], str], **kw: object) -> GateOutcome:
    return run_sync(ask_then_act_async(prompt, action, **kw), "ask_then_act_async")
