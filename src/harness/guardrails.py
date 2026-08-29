"""Input guardrails for the agent harness.

In production these delegate to Azure AI Content Safety (Prompt Shields) to
detect jailbreak / prompt-injection attempts. For Lesson 1 we run a LOCAL
stand-in so the harness works without Azure — and so you decide the policy.

The raw substring marker list below is a teaching baseline that is trivially
bypassed by unicode look-alikes and spacing tricks. :mod:`harness.safety` closes
that specific gap locally: it re-checks the markers over obfuscation-folded text
and adds heuristic attack-family detectors the markers can't express. It is still
heuristic, not ML — the managed Prompt Shields remain the production answer.
"""
from __future__ import annotations

from dataclasses import dataclass

from harness.safety import is_letter_split, normalize, squash, worst


@dataclass
class GuardrailResult:
    allowed: bool
    reason: str | None = None


# Reject inputs larger than this (rough token/DoS ceiling; tune per model context).
MAX_INPUT_CHARS = 4000

# Common prompt-injection / jailbreak markers. This substring list is a TEACHING
# stand-in only — it is trivially bypassed (unicode look-alikes, spacing tricks).
# Production defense is Azure Content Safety Prompt Shields, which is ML-based and
# evasion-resistant. Keep this list narrow to limit false positives.
INJECTION_MARKERS = (
    "ignore previous instructions",
    "ignore all previous instructions",
    "disregard previous instructions",
    "disregard the above",
    "reveal your instructions",
    "reveal the system prompt",
    "developer mode",
)


def check_input(text: str) -> GuardrailResult:
    """Decide whether user input may reach the agent.

    Policy (reference implementation): a hard-block guard. Reject empty input,
    over-long input, and anything containing a known prompt-injection marker.
    Hard-block is chosen over flag-and-pass because a guard that forwards the
    injection payload to the model provides little real protection — at the cost
    of occasional false positives, which the narrow marker list keeps rare.
    """
    if not text or not text.strip():
        return GuardrailResult(allowed=False, reason="empty input")

    if len(text) > MAX_INPUT_CHARS:
        return GuardrailResult(allowed=False, reason="input too long")

    lowered = text.lower()
    for marker in INJECTION_MARKERS:
        if marker in lowered:
            return GuardrailResult(
                allowed=False, reason=f"possible prompt injection: {marker!r}"
            )

    # Evasion-resistant pass: re-check the same markers over obfuscation-folded text, so a
    # homoglyph/zero-width disguise ("ignorе previous instructions") can't slip past the raw
    # substring check above.
    folded = normalize(text)
    if folded != lowered:
        for marker in INJECTION_MARKERS:
            if marker in folded:
                return GuardrailResult(
                    allowed=False, reason=f"possible prompt injection (obfuscated): {marker!r}"
                )

    # Separator-agnostic pass. `normalize` rejoins a word split by an INVISIBLE character but
    # not one split by a visible separator, so "i g n o r e", "i.g.n.o.r.e" and "i-g-n-o-r-e"
    # all walked straight through. Squashing both sides to alphanumerics closes the family.
    #
    # Gated, because squashing deletes the separator it is aimed at and the full stop ending an
    # ordinary sentence equally: "Please do not ignore. Previous instructions were unclear" was
    # hard-blocked by this pass. `is_letter_split` asks whether the input carries the evasion
    # signature at all, so prose is no longer folded on the chance that it might be an attack.
    if is_letter_split(text):
        squashed = squash(text)
        for marker in INJECTION_MARKERS:
            if squash(marker) in squashed:
                return GuardrailResult(
                    allowed=False, reason=f"possible prompt injection (separated): {marker!r}"
                )

    # Heuristic attack families the flat marker list can't express (indirect injection, authority
    # escalation, role-play/jailbreak, disclosure suppression).
    hit = worst(text)
    if hit is not None:
        return GuardrailResult(allowed=False, reason=f"{hit.kind}: {hit.reason}")

    return GuardrailResult(allowed=True)
