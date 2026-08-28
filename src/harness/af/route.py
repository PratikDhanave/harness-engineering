"""Routing on the Agent Framework (Lesson 5).

`harness.orchestration.router` decides a specialist with a keyword table and
returns the decision. Here the decision *is* the graph: a switch-case edge
group sends the request down exactly one branch, and the branch that runs is
the specialist. Nothing downstream has to ask who won.

Why not `HandoffBuilder`? It is installed and available — but it takes real
`Agent`s and the handoff decision is made *by a model*: one agent decides it is
the wrong one for this and passes the conversation on. That is a different
pattern from a deterministic table, and it would make this lesson need a model
to run at all. When the routing rule is "does this text contain 'refund'", the
honest primitive is a switch, and a switch-case edge group is exactly that.

State the leak: the same one the local router has. A keyword table has no idea
what a word means, so "the project won't build" misses a rule that only knows
"compile". A real triage step is a model deciding, and it belongs behind this
same seam.
"""
from __future__ import annotations

from harness.af import run_sync
from dataclasses import dataclass

from agent_framework import (
    Case,
    Default,
    Executor,
    WorkflowBuilder,
    WorkflowContext,
    handler,
)

BILLING, CODE, RESEARCH, FALLBACK = "billing", "code", "research", "fallback"

DEFAULT_RULES: dict[str, str] = {
    "refund": BILLING, "invoice": BILLING, "charge": BILLING,
    "compile": CODE, "stack trace": CODE, "exception": CODE,
    "compare": RESEARCH, "find out": RESEARCH, "who is": RESEARCH,
}


@dataclass
class Routed:
    specialist: str
    matched: str | None
    answer: str


def _matches(rules: dict[str, str], specialist: str):
    def predicate(request: object) -> bool:
        text = str(request).lower()
        return any(word in text for word in rules if rules[word] == specialist)
    return predicate


class _Intake(Executor):
    @handler
    async def take(self, request: str, ctx: WorkflowContext[str]) -> None:
        await ctx.send_message(request)


class _Specialist(Executor):
    def __init__(self, name: str, rules: dict[str, str]) -> None:
        super().__init__(id=name)
        self._name = name
        self._rules = rules

    @handler
    async def handle(self, request: str, ctx: WorkflowContext[Routed, Routed]) -> None:
        text = request.lower()
        hit = next((w for w, s in self._rules.items() if s == self._name and w in text), None)
        await ctx.yield_output(
            Routed(self._name, hit, f"[{self._name}] {request}")
        )


def build_router(rules: dict[str, str] | None = None):
    rules = dict(rules or DEFAULT_RULES)
    intake = _Intake(id="intake")
    specialists = {
        n: _Specialist(n, rules) for n in (BILLING, CODE, RESEARCH, FALLBACK)
    }
    cases: list[Case | Default] = [
        Case(condition=_matches(rules, n), target=specialists[n])
        for n in (BILLING, CODE, RESEARCH)
    ]
    cases.append(Default(target=specialists[FALLBACK]))
    return (
        WorkflowBuilder(name="triage", start_executor=intake)
        .add_switch_case_edge_group(intake, cases)
        .build()
    )


async def route_async(request: str, rules: dict[str, str] | None = None) -> Routed:
    events = await build_router(rules).run(request)
    for ev in reversed(list(events)):
        if getattr(ev, "type", None) == "output":
            return ev.data
    raise RuntimeError("the router produced no decision")


def route(request: str, rules: dict[str, str] | None = None) -> Routed:
    return run_sync(route_async(request, rules), "route_async")
