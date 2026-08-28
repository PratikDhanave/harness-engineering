"""Lesson 6 on the Agent Framework: fan-out, fan-in, and surviving a failure."""
from __future__ import annotations

import pytest

from harness.af.supervise import MAX_WORKERS, decompose, run


def test_splits_on_semicolons_and_newlines():
    assert decompose("a; b\nc") == ["a", "b", "c"]
    assert decompose("  ;  ") == []


def test_every_piece_runs_and_comes_back_in_order():
    agg = run("one; two; three", lambda t: t.upper())
    assert [r.subtask for r in agg.results] == ["one", "two", "three"]
    assert [r.output for r in agg.results] == ["ONE", "TWO", "THREE"]
    assert (agg.succeeded, agg.failed) == (3, 0)


def test_one_failure_does_not_sink_the_batch():
    def worker(t: str) -> str:
        if t == "two":
            raise RuntimeError("supplier site down")
        return t.upper()

    agg = run("one; two; three", worker)
    assert (agg.succeeded, agg.failed) == (2, 1)
    assert agg.results[1].error == "RuntimeError: supplier site down"
    assert agg.results[1].output is None
    assert agg.results[0].output == "ONE", "its neighbours still came back"
    assert agg.results[2].output == "THREE"


def test_results_are_in_decomposition_order_not_completion_order():
    order: list[str] = []

    def worker(t: str) -> str:
        order.append(t)
        return t

    agg = run("first; second; third", worker)
    assert [r.subtask for r in agg.results] == ["first", "second", "third"]


def test_too_many_subtasks_fails_loudly_rather_than_dropping_work():
    task = "; ".join(str(i) for i in range(MAX_WORKERS + 1))
    with pytest.raises(Exception):
        run(task, lambda t: t)
