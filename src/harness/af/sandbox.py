"""Sandboxing on the Agent Framework (Lesson 3) — and why this one is different.

Every other lesson has an in-process Agent Framework implementation next to its
local one. This lesson cannot, and the reason is the lesson.

Isolation is not a library feature. `harness/sandbox.py` runs generated code in
a subprocess, and its own docstring admits that is not a security boundary: it
shares the filesystem and the network, caps neither memory nor CPU, and the
timeout reaches only the direct child. No amount of local Python fixes that,
because the thing you need is *a different machine*, administered by somebody
whose job it is.

So the framework's answer is a **hosted tool**. `agent_framework` declares the
capability — `SupportsCodeInterpreterTool` — and the implementation lives in
the service: Azure AI Foundry's Code Interpreter, or Container Apps dynamic
sessions. Attaching it is a line of configuration; what you are buying is
somebody else's isolation.

`code_interpreter_available()` reports whether the configured chat client can
actually offer it, so a workshop can show the honest answer — "not from here"
— rather than pretending.
"""

from typing import Any

from agent_framework import SupportsCodeInterpreterTool

from harness.sandbox import SandboxResult, run_code  # the local stand-in

__all__ = ["SandboxResult", "run_code", "code_interpreter_available", "why_not_local"]

WHY_NOT_LOCAL = (
    "Code Interpreter is a hosted tool: the isolation is another machine, which "
    "is the whole point of it. There is no in-process equivalent, so the local "
    "stand-in stays a subprocess and is honest about not being a boundary."
)


def code_interpreter_available(chat_client: Any) -> bool:
    """Can this client offer a managed sandbox? Cloud clients can; local ones cannot."""
    return isinstance(chat_client, SupportsCodeInterpreterTool)


def why_not_local() -> str:
    return WHY_NOT_LOCAL
