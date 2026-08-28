"""Heuristic attack-family detectors — the families a substring marker list cannot express.

**Seam note.** Like :mod:`harness.safety.normalize`, this is a *local stand-in* for Azure AI
Content Safety **Prompt Shields**. The Lesson-1 guardrail (`guardrails.INJECTION_MARKERS`)
matches a handful of exact override phrasings; this module adds four broader families that a
single substring can't capture — **indirect / retrieved-content injection**, **authority / role
escalation**, **role-play / jailbreak personas**, and **AI-disclosure suppression** — each as an
ordered list of compiled regexes run over the :func:`~harness.safety.normalize.normalize`-folded
text, so a homoglyph or zero-width disguise can't bypass them.

:func:`detect_attacks` returns every match; :func:`worst` returns the single highest-severity one
(indirect > authority > role-play > disclosure).

**State the leak.** These are hand-written regexes, not an ML classifier. They are anchored on
adversarial *intent* (a directive verb, a request-to-perform framing, an action on a control) so
ordinary phrasing doesn't false-positive — but they catch known shapes, not novel paraphrase.
Managed Prompt Shields remain the production answer. Pure, deterministic, stdlib-only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from harness.safety.normalize import normalize

__all__ = ["Detection", "detect_attacks", "worst"]


@dataclass(frozen=True)
class Detection:
    """One flagged attack: its family ``kind``, a human ``reason``, and the ``span`` matched."""

    kind: str
    reason: str
    span: tuple[int, int]


# (kind, severity, [(regex, reason)]) — higher severity wins in `worst`.
_FAMILIES: tuple[tuple[str, int, tuple[tuple[str, str], ...]], ...] = (
    (
        "indirect_injection",
        4,
        (
            (r"when you (read|process|see) this", "payload embedded in retrieved content"),
            # Require a directive verb after "(assistant|ai|model) should/must" so benign phrasing
            # ("which model should I choose?") doesn't read as the model being directed.
            (
                r"(assistant|ai|model|bot) (should|must) (now )?(ignore|disregard|forget|append"
                r"|reveal|expose|leak|obey|follow|comply|treat|output|print|skip)",
                "content directing the model",
            ),
            (
                r"(tell|tells|telling|instruct|instructs|instructing|direct|directs|directing)"
                r" the (assistant|ai|model|bot|system)",
                "third-party content directing the model",
            ),
            (
                r"(append|reveal|expose|leak|print|include) [^.]{0,30}system prompt",
                "system-prompt exfiltration via retrieved content",
            ),
            (r"^\s*system\s*:", "inline system-role spoofing"),
            (r"ignore the (document|text|content) above", "retrieved-content override"),
            (r"</?(system|instructions?)>", "instruction-tag injection"),
            (r"<[^>]{0,20}(override|policy)[^>]{0,20}>", "policy-override tag injection"),
        ),
    ),
    (
        # Claiming authority to relax a control. Anchored on the *action*
        # (authorise/disable/override/self-elevate), not a bare "as the administrator" identity
        # claim, which over-blocks legitimate use.
        "authority_escalation",
        3,
        (
            (r"i authori[sz]e you to", "false self-authorisation"),
            (
                r"(disable|turn off|switch off|deactivate|bypass) the"
                r" .{0,25}(guardrail|gate|control|check|filter|shield)",
                "request to disable a control",
            ),
            (
                r"override the .{0,25}(guardrail|control|policy|filter|limit|restriction)",
                "request to override a control",
            ),
            (
                r"treat (my|me|the user'?s?) .{0,20}as .{0,10}(admin|root|privileged|developer)",
                "role self-elevation",
            ),
        ),
    ),
    (
        "roleplay",
        2,
        (
            (r"pretend (you are|to be|the rules)", "role-play jailbreak"),
            (
                r"pretend .{0,25}(rules|safety|policy|guardrails?|guidelines)"
                r" (were|are|never|do ?n'?t)",
                "role-play suspension of the rules",
            ),
            (r"let'?s play a game", "game-framing jailbreak"),
            # "hypothetical scenario" is deliberately NOT here — it is ordinary language; the
            # jailbreak shape is fictional framing used to smuggle a real how-to.
            (
                r"(fictional|imaginary|make[- ]?believe)"
                r" (script|story|scenario|world|setting|character)",
                "fiction-framing jailbreak",
            ),
            # Request-to-perform framing so an educational question about *detecting* circumvention
            # isn't blocked.
            (
                r"(how (to|do i|can i|would i)|help me|show me|teach me|steps? to|walk me through)"
                r" [^.]{0,25}(bypass|circumvent|evade|defeat|get around|skirt)"
                r" [^.]{0,20}(safety|guardrail|filter|content policy|moderation|restriction)",
                "request to bypass a control",
            ),
            (r"(two|multiple|dual|split) personas?", "multi-persona jailbreak"),
            (r"\bdan\b", "DAN persona jailbreak"),
            (r"developer mode", "developer-mode jailbreak"),
            (r"as an?\s+(unfiltered|uncensored|unrestricted)", "unfiltered-persona jailbreak"),
            (r"you have no (rules|restrictions|guidelines)", "restriction-removal jailbreak"),
        ),
    ),
    (
        "disclosure_suppression",
        1,
        (
            (
                r"do ?n'?t (say|mention|tell|reveal) .{0,20}(you'?re|you are|it'?s) (an? )?ai",
                "AI-disclosure suppression",
            ),
            (
                r"(hide|omit|skip|remove|drop|without|no)\b.{0,30}(disclaimer|disclosure|banner)",
                "disclaimer/disclosure suppression",
            ),
            (r"an ai (generated|wrote|made|produced|created)", "hiding AI authorship"),
            (r"(sign|present|pass) .{0,20}as (a )?human", "human-impersonation request"),
            (r"pretend to be (a )?human", "human-impersonation request"),
        ),
    ),
)

_COMPILED: tuple[tuple[str, int, tuple[tuple[re.Pattern[str], str], ...]], ...] = tuple(
    (kind, sev, tuple((re.compile(rx), reason) for rx, reason in pats))
    for kind, sev, pats in _FAMILIES
)


def detect_attacks(text: str) -> list[Detection]:
    """Return every attack :class:`Detection` in ``text`` (normalised first), in family order."""
    folded = normalize(text)
    out: list[Detection] = []
    for kind, _sev, patterns in _COMPILED:
        for pattern, reason in patterns:
            m = pattern.search(folded)
            if m:
                out.append(Detection(kind=kind, reason=reason, span=m.span()))
    return out


def worst(text: str) -> Detection | None:
    """Return the single highest-severity :class:`Detection`, or ``None`` if the text is clean."""
    sev_by_kind = {kind: sev for kind, sev, _ in _COMPILED}
    detections = detect_attacks(text)
    if not detections:
        return None
    return max(detections, key=lambda d: sev_by_kind[d.kind])
