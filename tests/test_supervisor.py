import threading

from harness.orchestration.supervisor import Aggregate, Supervisor, SubResult


def test_decompose_splits_on_delimiters_and_defaults_to_single():
    sup = Supervisor(worker=lambda s: s)
    assert sup.decompose("a; b; c") == ["a", "b", "c"]
    assert sup.decompose("a\nb\nc") == ["a", "b", "c"]
    assert sup.decompose("a; b\nc") == ["a", "b", "c"]
    # No delimiter -> the whole task is one subtask.
    assert sup.decompose("just one task") == ["just one task"]


def test_fan_out_aggregates_all_results_in_order():
    sup = Supervisor(worker=lambda s: f"done:{s}")
    agg = sup.run("a; b; c; d")

    assert isinstance(agg, Aggregate)
    assert [r.subtask for r in agg.results] == ["a", "b", "c", "d"]
    assert [r.output for r in agg.results] == ["done:a", "done:b", "done:c", "done:d"]
    assert all(r.error is None for r in agg.results)
    assert (agg.succeeded, agg.failed) == (4, 0)


def test_order_preserved_regardless_of_completion_order():
    # Later subtasks are gated so they can only finish AFTER earlier ones are
    # released — completion order is deliberately the reverse of submission order.
    gates = {"a": threading.Event(), "b": threading.Event(), "c": threading.Event()}

    def worker(subtask: str) -> str:
        gates[subtask].wait(timeout=5)
        # Release the earlier-lettered subtask once this later one has finished
        # waiting, forcing completions to interleave out of submission order.
        if subtask == "c":
            gates["b"].set()
        if subtask == "b":
            gates["a"].set()
        return subtask.upper()

    gates["c"].set()  # unblock the LAST subtask first
    agg = Supervisor(worker=worker, max_workers=3).run("a; b; c")

    # Results still come back in decomposition order, not completion order.
    assert [r.subtask for r in agg.results] == ["a", "b", "c"]
    assert [r.output for r in agg.results] == ["A", "B", "C"]
    assert (agg.succeeded, agg.failed) == (3, 0)


def test_one_failing_worker_is_isolated():
    def worker(subtask: str) -> str:
        if subtask == "boom":
            raise ValueError("kaboom")
        return f"ok:{subtask}"

    agg = Supervisor(worker=worker).run("a; boom; c")

    by_subtask = {r.subtask: r for r in agg.results}
    assert by_subtask["a"].output == "ok:a" and by_subtask["a"].error is None
    assert by_subtask["c"].output == "ok:c" and by_subtask["c"].error is None

    failed = by_subtask["boom"]
    assert failed.output is None
    assert failed.error == "kaboom"  # exception captured, not raised

    # Ordering and counts are unaffected by the isolated failure.
    assert [r.subtask for r in agg.results] == ["a", "boom", "c"]
    assert (agg.succeeded, agg.failed) == (2, 1)


def test_runs_truly_in_parallel_via_barrier_without_sleeps():
    # A Barrier(n) only releases once ALL n workers have arrived. If the fan-out
    # were serial, worker #1 would wait alone and hit the timeout -> BrokenBarrier
    # -> an error result. So "all succeeded" is proof the workers ran concurrently.
    # No sleeps: the barrier itself is the synchronisation, and the small timeout
    # bounds the test instead of hanging forever if parallelism regresses.
    n = 4
    barrier = threading.Barrier(n, timeout=5)

    def worker(subtask: str) -> str:
        barrier.wait()  # blocks until all n workers rendezvous here
        return f"through:{subtask}"

    task = "; ".join(f"t{i}" for i in range(n))
    agg = Supervisor(worker=worker, max_workers=n).run(task)

    assert (agg.succeeded, agg.failed) == (n, 0)
    assert [r.output for r in agg.results] == [f"through:t{i}" for i in range(n)]
    assert all(isinstance(r, SubResult) for r in agg.results)


def test_injected_executor_preserves_isolation_and_order():
    """The executor is a seam so the module runs where threads do not exist.

    Pyodide raises `RuntimeError: can't start new thread`, which would otherwise
    put Lesson 6 out of reach of the browser entirely. A synchronous executor
    gives up parallelism — and must give up nothing else.
    """

    class SyncFuture:
        def __init__(self, fn, arg):
            try:
                self._value, self._error = fn(arg), None
            except Exception as exc:  # captured, re-raised from result()
                self._value, self._error = None, exc

        def result(self):
            if self._error is not None:
                raise self._error
            return self._value

    class SyncExecutor:
        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def submit(self, fn, arg):
            return SyncFuture(fn, arg)

    def worker(subtask: str) -> str:
        if subtask == "boom":
            raise RuntimeError("sub-agent failed")
        return f"done:{subtask}"

    agg = Supervisor(worker=worker, executor_factory=SyncExecutor).run("a; boom; c")

    assert [r.subtask for r in agg.results] == ["a", "boom", "c"]
    assert agg.succeeded == 2 and agg.failed == 1
    assert agg.results[0].output == "done:a"
    assert agg.results[1].output is None
    assert "sub-agent failed" in agg.results[1].error
    assert agg.results[2].output == "done:c"
