"""History roll-up — compress a long thread so it fits the model context (Lesson 4).

`summarize_thread` is a LOCAL, deterministic stand-in for an LLM summarization call
(the kind you'd normally make against Azure OpenAI / Foundry to condense a long
transcript before replaying it as context).

Where this is weaker than an LLM (state the leak): a real summarizer reads meaning
and writes a faithful prose recap; this just keeps the first and last few turns
verbatim and drops the middle. Summarization is inherently *lossy* — so the raw
thread stays in the `ThreadStore` (see `harness.memory.thread`) and a bad or
misleading summary is always recoverable by replaying the original turns.
"""
from __future__ import annotations

from harness.memory.thread import Message


def _render(messages: list[Message]) -> list[str]:
    return [f"{m.role}: {m.content}" for m in messages]


def summarize_thread(
    messages: list[Message], max_chars: int = 500, keep: int = 2
) -> str:
    """Return the joined history, or a compact roll-up if it is too long.

    If the rendered transcript fits within `max_chars`, it is returned verbatim
    (nothing is lost). Otherwise we keep the first `keep` and last `keep` messages
    and replace everything in between with a "[...k earlier turns omitted...]"
    marker.

    Note the granularity, because the distinction matters elsewhere: this drops
    whole *messages*, not whole *turns*. `Message.role` is an unconstrained string,
    so a thread containing an assistant tool request and its tool result could be
    cut between the two. That is safe **here** and only here, because the output is
    rendered prose for context — never a message list handed back to a model API,
    which rejects an unanswered tool call outright. Anything that reconstructs a
    real message list must compact turn-by-turn instead. The result is not *guaranteed* to be <= max_chars (kept turns could
    themselves be huge), but when the roll-up triggers it is meaningfully shorter
    than the full history — that is the point.

    `keep` must be >= 1; a non-positive value is clamped to 1 (a `keep` of 0 would
    make `lines[-keep:]` select the whole list rather than an empty tail).
    """
    keep = max(1, keep)
    lines = _render(messages)
    full = "\n".join(lines)
    if len(full) <= max_chars:
        return full

    # Not enough turns to have a droppable middle: return the full text unchanged
    # rather than emit a marker that hides nothing.
    if len(messages) <= 2 * keep:
        return full

    head = lines[:keep]
    tail = lines[-keep:]
    omitted = len(messages) - 2 * keep
    marker = f"[...{omitted} earlier turns omitted...]"
    return "\n".join([*head, marker, *tail])
