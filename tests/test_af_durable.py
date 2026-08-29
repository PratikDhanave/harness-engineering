"""Lesson 2 on the Agent Framework: a real checkpointed workflow.

These are the same properties `test_workflow.py` asserts about the local
runner, re-asserted against the framework's own checkpointing — because "the
seam swaps cleanly" is only true if both sides behave the same.
"""
from __future__ import annotations

import pytest

from harness.af.durable import run_durably


def test_runs_every_step_in_order(tmp_path):
    ran: list[str] = []

    def step(name):
        def fn(state):
            ran.append(name)
            return {name: True}
        return fn

    out = run_durably("t1", [("a", step("a")), ("b", step("b")), ("c", step("c"))],
                      str(tmp_path))
    assert ran == ["a", "b", "c"]
    assert out == {"a": True, "b": True, "c": True}


def test_resume_does_not_redo_completed_work(tmp_path):
    ran: list[str] = []

    def ok(name):
        def fn(state):
            ran.append(name)
            return {name: True}
        return fn

    def explode(state):
        ran.append("b")
        raise RuntimeError("boom")

    steps_failing = [("a", ok("a")), ("b", explode), ("c", ok("c"))]
    with pytest.raises(Exception):
        run_durably("t2", steps_failing, str(tmp_path))
    assert ran == ["a", "b"], "the run should die inside b"

    ran.clear()
    steps_fixed = [("a", ok("a")), ("b", ok("b")), ("c", ok("c"))]
    out = run_durably("t2", steps_fixed, str(tmp_path))

    # `a` completed before the crash, so it is NOT redone. `b` started and died,
    # so it runs again — at-least-once, the same guarantee the local runner
    # gives, and the reason a step must be safe to run twice.
    assert "a" not in ran, "a completed and must not be redone"
    assert ran == ["b", "c"]
    assert out["a"] is True, "a's result survived in the checkpoint"
    assert out["c"] is True


def test_state_flows_between_steps(tmp_path):
    out = run_durably(
        "t3",
        [("one", lambda s: {"n": 1}), ("two", lambda s: {"n": s["n"] + 41})],
        str(tmp_path),
    )
    assert out["n"] == 42


def test_empty_steps_rejected(tmp_path):
    with pytest.raises(ValueError):
        run_durably("t4", [], str(tmp_path))
