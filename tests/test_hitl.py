import pytest

from harness.durable.sqlite_store import SQLiteCheckpointStore
from harness.hitl import (
    STATUS_AWAITING,
    ApprovalPending,
    request_approval,
    resume,
)


def _store(tmp_path):
    return SQLiteCheckpointStore(tmp_path / "hitl.db")


def _recording_action(log):
    """A sensitive action that records the fact it ran and returns state."""

    def action(state):
        log.append("performed")
        return {"refund_id": "rf_1"}

    return action


def test_gate_parks_without_performing_the_action(tmp_path):
    store = _store(tmp_path)
    pending = request_approval("r1", "Refund $500?", store, now=100.0, timeout_seconds=60.0)

    assert isinstance(pending, ApprovalPending)
    assert pending.run_id == "r1"
    assert pending.prompt == "Refund $500?"
    # The checkpoint is parked; nothing performed yet.
    cp = store.load("r1")
    assert cp.state["status"] == STATUS_AWAITING
    assert cp.state["performed"] is False


def test_approve_within_deadline_performs_and_records_action(tmp_path):
    store = _store(tmp_path)
    log = []
    request_approval("r2", "Refund $500?", store, now=100.0, timeout_seconds=60.0)

    outcome = resume("r2", True, store, now=130.0, action=_recording_action(log))

    assert outcome.status == "approved"
    assert log == ["performed"]  # the action actually ran
    # ...and the fact it ran is durable in the checkpoint.
    cp = store.load("r2")
    assert cp.state["status"] == "approved"
    assert cp.state["performed"] is True
    assert cp.state["refund_id"] == "rf_1"


def test_reject_does_not_perform_action(tmp_path):
    store = _store(tmp_path)
    log = []
    request_approval("r3", "Delete production DB?", store, now=0.0, timeout_seconds=60.0)

    outcome = resume("r3", False, store, now=5.0, action=_recording_action(log))

    assert outcome.status == "rejected"
    assert log == []  # action NOT recorded
    assert store.load("r3").state["performed"] is False


def test_resume_after_deadline_times_out(tmp_path):
    store = _store(tmp_path)
    log = []
    request_approval("r4", "Deploy to prod?", store, now=1000.0, timeout_seconds=60.0)

    # Decision is YES, but we advance the injected clock past the deadline.
    outcome = resume("r4", True, store, now=1000.0 + 61.0, action=_recording_action(log))

    assert outcome.status == "timed_out"
    assert log == []  # a late "yes" is void; action NOT recorded
    assert store.load("r4").state["performed"] is False


def test_pending_state_survives_a_fresh_store_on_same_file(tmp_path):
    db = tmp_path / "hitl.db"
    # Park the approval, then drop the store object entirely (simulate a crash).
    first = SQLiteCheckpointStore(db)
    request_approval("r5", "Wire $1M?", first, now=42.0, timeout_seconds=3600.0)
    first.close()

    # A brand-new store on the SAME file must still see the pending request.
    second = SQLiteCheckpointStore(db)
    parked = second.load("r5")
    assert parked.state["status"] == STATUS_AWAITING
    assert parked.state["prompt"] == "Wire $1M?"
    assert parked.state["requested_at"] == 42.0

    # And resuming against the fresh store works — suspension lost nothing.
    log = []
    outcome = resume("r5", True, second, now=100.0, action=_recording_action(log))
    assert outcome.status == "approved"
    assert log == ["performed"]


def test_resume_exactly_at_deadline_is_still_approved(tmp_path):
    # now - requested_at == timeout_seconds exactly: the deadline check is strict
    # ('>'), so the boundary is on time, not timed out.
    store = _store(tmp_path)
    log = []
    request_approval("rb", "Refund?", store, now=100.0, timeout_seconds=60.0)
    outcome = resume("rb", True, store, now=160.0, action=_recording_action(log))
    assert outcome.status == "approved"
    assert log == ["performed"]


def test_second_resume_after_resolution_raises(tmp_path):
    # Once resolved, the run is no longer awaiting; resuming again is an error,
    # not a silent replay of the sensitive action.
    store = _store(tmp_path)
    request_approval("rc", "Refund?", store, now=0.0, timeout_seconds=60.0)
    resume("rc", True, store, now=1.0)
    with pytest.raises(ValueError):
        resume("rc", True, store, now=2.0)


def test_resume_unknown_run_id_raises(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(ValueError):
        resume("never-parked", True, store, now=1.0)
