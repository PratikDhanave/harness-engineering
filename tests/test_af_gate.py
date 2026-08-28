"""Lesson 7 on the Agent Framework: the run stops and waits for a person.

Same three outcomes as `test_hitl.py` asserts for the local gate, re-asserted
against the framework's own request/response ports.
"""
from __future__ import annotations

import pytest

from harness.af.gate import APPROVED, REJECTED, TIMED_OUT, ask_then_act


def _spy():
    calls: list[str] = []

    def action() -> str:
        calls.append("did it")
        return "refunded 900"

    return calls, action


def test_approved_in_time_performs_the_action():
    calls, action = _spy()
    out = ask_then_act("refund 900?", action, approve=True, now=0.0, decided_at=5.0)
    assert out.status == APPROVED
    assert out.detail == "refunded 900"
    assert calls == ["did it"]


def test_rejected_never_performs_the_action():
    calls, action = _spy()
    out = ask_then_act("refund 900?", action, approve=False, now=0.0, decided_at=5.0)
    assert out.status == REJECTED
    assert calls == [], "a refused action must not happen"


def test_a_late_yes_is_void():
    calls, action = _spy()
    out = ask_then_act(
        "refund 900?", action, approve=True, now=0.0, decided_at=61.0,
        timeout_seconds=60.0,
    )
    assert out.status == TIMED_OUT
    assert calls == [], "an answer after the deadline must not act"


def test_deadline_is_checked_before_the_decision():
    """A deadline that only bites on 'no' is not a deadline."""
    calls, action = _spy()
    late_yes = ask_then_act("x", action, approve=True, decided_at=999.0,
                            timeout_seconds=1.0)
    late_no = ask_then_act("x", action, approve=False, decided_at=999.0,
                           timeout_seconds=1.0)
    assert late_yes.status == TIMED_OUT
    assert late_no.status == TIMED_OUT
    assert calls == []


def test_exactly_on_the_deadline_still_counts():
    calls, action = _spy()
    out = ask_then_act("x", action, approve=True, now=0.0, decided_at=60.0,
                       timeout_seconds=60.0)
    assert out.status == APPROVED, "the boundary is inclusive"
    assert calls == ["did it"]
