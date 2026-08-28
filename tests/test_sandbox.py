from harness.sandbox import run_code


def test_runs_code_and_captures_stdout():
    r = run_code("print(2 + 3)")
    assert r.ok is True
    assert r.stdout.strip() == "5"
    assert r.timed_out is False


def test_captures_error_and_nonzero_exit():
    r = run_code("raise ValueError('boom')")
    assert r.ok is False
    assert "ValueError" in r.stderr
    assert r.exit_code not in (0, None)


def test_timeout_kills_runaway_code():
    r = run_code("while True: pass", timeout=1)
    assert r.timed_out is True
    assert r.ok is False


def test_isolated_interpreter_flag_set():
    # Under `-I`, sys.flags.isolated == 1 — proves the isolation flag is honored.
    r = run_code("import sys; print(sys.flags.isolated)")
    assert r.stdout.strip() == "1"


def test_timeout_with_partial_output_returns_str_stdout():
    # A program that prints and then hangs is killed at the timeout; the captured
    # partial output must be decoded text (str), not raw bytes — otherwise any
    # downstream string op on SandboxResult.stdout would TypeError.
    r = run_code("import sys; print('partial', flush=True)\nwhile True: pass", timeout=1)
    assert r.timed_out is True
    assert isinstance(r.stdout, str)
    assert "partial" in r.stdout
