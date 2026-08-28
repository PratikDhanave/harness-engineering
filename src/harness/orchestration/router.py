"""Intent routing / handoff — local stand-in for Microsoft Agent Framework triage.

In production a *triage AGENT* (an LLM) reads the request, classifies the user's
intent, and hands the conversation off to a specialist agent while carrying the
whole thread context along. That agent generalizes: it understands paraphrase,
typos, and mixed intents, and it can ask a clarifying question.

For Lesson 5 we run a LOCAL, deterministic stand-in: a keyword rule table that
maps trigger words to a specialist. This is the honest leak — a substring table
has no notion of meaning. It misses synonyms it was never given ("won't build"
never matches "compile"), it can be gamed by word order, and it carries no thread
context. Its virtue is that it is fast, offline, and fully testable, which is
exactly what we want while wiring the harness together.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Specialist(str, Enum):
    """The agents a request can be handed off to.

    Subclassing ``str`` keeps the values plain strings, so a ``RouteDecision``
    round-trips through JSON / logs without special handling.
    """

    BILLING = "billing"
    CODE = "code"
    RESEARCH = "research"
    FALLBACK = "fallback"  # no rule matched — a human/general agent takes it


@dataclass
class RouteDecision:
    specialist: str
    matched_intent: str | None  # the keyword that fired, or None on fallback


# Default rule table: trigger keyword -> specialist. Keywords are matched
# case-insensitively as substrings, so keep them lowercase here. This is
# deliberately small and readable; extend it by injecting your own table.
DEFAULT_RULES: dict[str, Specialist] = {
    "invoice": Specialist.BILLING,
    "refund": Specialist.BILLING,
    "charge": Specialist.BILLING,
    "bug": Specialist.CODE,
    "error": Specialist.CODE,
    "stack trace": Specialist.CODE,
    "compile": Specialist.CODE,
    "paper": Specialist.RESEARCH,
    "study": Specialist.RESEARCH,
    "cite": Specialist.RESEARCH,
    "research": Specialist.RESEARCH,
}


class Router:
    """Route a request to a specialist by first-matching keyword.

    The rule table is injectable so tests can supply a tiny fixed table and
    callers can extend the domain vocabulary without editing this module — the
    same reason the checkpoint store is a seam in Lesson 2.
    """

    def __init__(self, rules: dict[str, Specialist] | None = None) -> None:
        # Copy so a caller mutating their dict later can't change our behavior.
        self.rules = dict(rules) if rules is not None else dict(DEFAULT_RULES)

    def route(self, request: str) -> RouteDecision:
        """Return the specialist for ``request``, or FALLBACK if nothing matches.

        Case-insensitive substring match. The first keyword (in table order) that
        appears in the request wins; there is no scoring or tie-breaking — a real
        triage agent would weigh the whole message instead of stopping at the
        first hit.
        """
        lowered = request.lower()
        for keyword, specialist in self.rules.items():
            if keyword in lowered:
                return RouteDecision(
                    specialist=specialist.value, matched_intent=keyword
                )
        return RouteDecision(specialist=Specialist.FALLBACK.value, matched_intent=None)
