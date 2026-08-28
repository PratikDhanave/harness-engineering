"""Secure sandboxing (Lesson 3).

Runs agent-generated code in an isolated SUBPROCESS with a hard timeout. This is
a TEACHING stand-in for the Azure AI Foundry Code Interpreter tool (a managed,
network-isolated sandbox). A local subprocess is NOT a real security boundary —
it shares the host filesystem and, absent extra sandboxing, the network. Use it
to learn the shape of "run untrusted code safely"; use Code Interpreter or ACA
Dynamic Sessions for anything real.

Scope of the timeout (state the leak): it kills only the DIRECT child process and
sets no CPU/memory/process limits. Code that spawns its own descendants can leave
orphans running past the deadline, and a fork/memory bomb is not contained — one
more reason this is a teaching stand-in, not real isolation.
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass

DEFAULT_TIMEOUT_SECONDS = 5.0


@dataclass
class SandboxResult:
    ok: bool
    stdout: str
    stderr: str
    exit_code: int | None
    timed_out: bool


def _as_text(value: object) -> str:
    """Coerce captured subprocess output (str, bytes, or None) to str.

    On the timeout path the partial output captured on the exception is not
    decoded even under `text=True`, so it can arrive as bytes.
    """
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value


def run_code(code: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> SandboxResult:
    """Execute `code` as a Python script in an isolated subprocess.

    - Isolated interpreter (`-I`): ignores PYTHONPATH / user site-packages / env.
    - Hard timeout: a runaway or infinite loop is killed (timed_out=True) instead
      of hanging the harness.
    """
    try:
        proc = subprocess.run(
            [sys.executable, "-I", "-c", code],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        # Decode any partial output so stdout/stderr stay `str` (the dataclass
        # contract) on the timeout path too, and keep a partial traceback if one
        # was emitted just before the process hung.
        partial_err = _as_text(exc.stderr)
        return SandboxResult(
            ok=False,
            stdout=_as_text(exc.stdout),
            stderr="timed out" + (f"\n{partial_err}" if partial_err else ""),
            exit_code=None,
            timed_out=True,
        )
    return SandboxResult(
        ok=proc.returncode == 0,
        stdout=proc.stdout,
        stderr=proc.stderr,
        exit_code=proc.returncode,
        timed_out=False,
    )
