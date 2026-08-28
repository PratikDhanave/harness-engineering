import subprocess
import sys

from harness.durable.sqlite_store import SQLiteCheckpointStore
from harness.workflow import run_durably


def _store(tmp_path):
    return SQLiteCheckpointStore(tmp_path / "cp.db")


def test_fresh_run_executes_all_steps(tmp_path):
    ran = []
    steps = [
        ("a", lambda s: ran.append("a") or {"a": 1}),
        ("b", lambda s: ran.append("b") or {"b": 2}),
    ]
    state = run_durably("run1", steps, _store(tmp_path))
    assert ran == ["a", "b"]
    assert state == {"a": 1, "b": 2}


def test_resume_skips_completed_steps(tmp_path):
    store = _store(tmp_path)
    ran = []

    def boom(_s):
        raise RuntimeError("crash in step c")

    steps_crash = [
        ("a", lambda s: ran.append("a") or {"a": 1}),
        ("b", lambda s: ran.append("b") or {"b": 2}),
        ("c", boom),
    ]
    try:
        run_durably("run2", steps_crash, store)
    except RuntimeError:
        pass
    assert ran == ["a", "b"]  # a and b completed + checkpointed before the crash

    # Re-run with a working step c; a and b must NOT run again.
    ran.clear()
    steps_fixed = [
        ("a", lambda s: ran.append("a") or {"a": 1}),
        ("b", lambda s: ran.append("b") or {"b": 2}),
        ("c", lambda s: ran.append("c") or {"c": 3}),
    ]
    state = run_durably("run2", steps_fixed, store)
    assert ran == ["c"]  # only the previously-failed step re-runs
    assert state == {"a": 1, "b": 2, "c": 3}


def test_checkpoint_survives_process_restart(tmp_path):
    db = str(tmp_path / "cp.db")
    # Child process: completes step a (checkpointed), then dies at step b.
    child = (
        "import sys;"
        "from harness.durable.sqlite_store import SQLiteCheckpointStore;"
        "from harness.workflow import run_durably;"
        "store=SQLiteCheckpointStore(sys.argv[1]);"
        "steps=[('a',lambda s:{'a':1}),('b',lambda s:sys.exit(3))];"
        "run_durably('r',steps,store)"
    )
    r = subprocess.run([sys.executable, "-c", child, db])
    assert r.returncode == 3

    # This process resumes from the on-disk checkpoint: step a must be skipped.
    ran = []
    steps = [
        ("a", lambda s: ran.append("a") or {"a": 1}),
        ("b", lambda s: ran.append("b") or {"b": 2}),
    ]
    state = run_durably("r", steps, SQLiteCheckpointStore(db))
    assert ran == ["b"]
    assert state == {"a": 1, "b": 2}
