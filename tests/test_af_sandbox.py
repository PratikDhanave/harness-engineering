"""Lesson 3: the one seam with no in-process framework implementation."""
from __future__ import annotations

from harness.af.guard import EchoChatClient
from harness.af.sandbox import code_interpreter_available, run_code, why_not_local


def test_a_local_client_cannot_offer_a_managed_sandbox():
    assert code_interpreter_available(EchoChatClient()) is False
    assert "hosted" in why_not_local()


def test_the_local_stand_in_still_runs_code():
    r = run_code("print(6 * 7)")
    assert r.ok and r.stdout.strip() == "42"


def test_and_still_stops_a_runaway():
    r = run_code("while True: pass", timeout=0.5)
    assert r.timed_out and not r.ok
