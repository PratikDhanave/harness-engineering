"""Obfuscation-folding normaliser — a pre-pass so trivial disguises of an attack phrase can't
slip past the guardrail's literal markers.

**Seam note.** In production, jailbreak/prompt-injection detection is Azure AI Content Safety
**Prompt Shields** — an ML classifier that is evasion-resistant by design. This module is a
*local stand-in that closes one specific, cheap gap* in the Lesson-1 marker list
(`guardrails.INJECTION_MARKERS`): an adversary hides ``ignore previous instructions`` behind
homoglyphs (Cyrillic ``а`` for Latin ``a``), zero-width joiners (``ig​nore``), full-width
characters (``ｉｇｎｏｒｅ``), or separators between the letters (``i g n o r e``,
``i.g.n.o.r.e``, ``i-g-n-o-r-e``), and the raw substring check misses it.
:func:`normalize` folds all of these to a canonical lower-case ASCII form so the marker match
sees the *intent* rather than the exact bytes.

**State the leak.** This is still substring/heuristic matching, not classification. It defeats
the common mechanical evasions above; it does **not** defeat paraphrase, translation, or novel
phrasings — that is what the managed Prompt Shields are for. Pure stdlib, deterministic, and
idempotent (``normalize(normalize(x)) == normalize(x)``).
"""

from __future__ import annotations

import re
import unicodedata

__all__ = ["fold_homoglyphs", "is_letter_split", "normalize", "squash"]

# Confusable letters NFKC does NOT fold (Cyrillic/Greek look-alikes → Latin).
_HOMOGLYPHS = {
    "а": "a",
    "е": "e",
    "о": "o",
    "р": "p",
    "с": "c",
    "у": "y",
    "х": "x",
    "к": "k",
    "м": "m",
    "н": "h",
    "т": "t",
    "в": "b",
    "і": "i",
    "ѕ": "s",
    "ј": "j",
    "ο": "o",
    "α": "a",
    "ε": "e",
    "ρ": "p",
    "ν": "v",
    "τ": "t",
    "ι": "i",
}
_HOMOGLYPH_TABLE = str.maketrans(_HOMOGLYPHS)

_WHITESPACE = re.compile(r"\s+")


def _strip_invisible(text: str) -> str:
    """Remove Unicode format chars (Cf: zero-width, soft hyphen, bidi marks) and non-spacing
    marks (Mn: combining accents) — invisible splitters an attacker inserts to break a word."""
    return "".join(c for c in text if unicodedata.category(c) not in ("Cf", "Mn"))


def fold_homoglyphs(text: str) -> str:
    """Map Cyrillic/Greek confusable letters to their Latin look-alikes."""
    return text.translate(_HOMOGLYPH_TABLE)


def normalize(text: str) -> str:
    """Return ``text`` folded to a canonical lower-case ASCII-ish form for marker matching.

    Order matters: strip zero-width chars first so a split word rejoins, NFKC-normalise (handles
    full-width / compatibility forms), then **lower-case before folding** so an UPPER-case
    confusable (Cyrillic ``І``/``О``) collapses to its lower-case form first and is caught by the
    lower-case-only homoglyph table — folding before lower-casing would leave it un-folded and
    let ``ІGNОRЕ PRЕVІОUS`` bypass the marker check. A final fold + whitespace collapse makes the
    result stable and idempotent, so callers can normalise once and match safely.
    """
    text = _strip_invisible(text)
    text = unicodedata.normalize("NFKC", text)
    text = text.lower()
    text = fold_homoglyphs(text)
    text = unicodedata.normalize("NFKC", text)  # NFKC can re-expand a few folded compat chars
    text = fold_homoglyphs(text)
    return _WHITESPACE.sub(" ", text).strip()


_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def squash(text: str) -> str:
    """Return ``text`` normalised and then stripped of every non-alphanumeric character.

    :func:`normalize` collapses runs of whitespace but cannot rejoin a word an attacker has
    split *between* its letters — ``i g n o r e``, ``i.g.n.o.r.e`` and ``i-g-n-o-r-e`` all
    survived it, which meant three one-keystroke evasions walked past a guard whose whole
    purpose is to resist exactly that. Removing the separators entirely is separator-agnostic,
    so it costs nothing to defeat the next one somebody invents.

    Callers must squash the *marker* too, then substring-match.

    **State the leak.** An earlier version of this docstring claimed the cost was theoretical —
    that squashing "could in principle" join words it did not mean to, but that with phrases this
    long it had not happened. It had. ``"Please do not ignore. Previous instructions were
    unclear"`` squashes to ``…ignorepreviousinstructions…`` and was hard-blocked, and so was
    ``"I will ignore previous. Instructions follow below."`` Both are things a person actually
    writes. The sentence-ending full stop is exactly the separator this function is designed to
    delete, and it cannot tell that one apart from the full stops in ``i.g.n.o.r.e``.

    So squashing is no longer applied to arbitrary text. :func:`is_letter_split` gates it, and
    only input that *carries the evasion signature* — a run of single characters held apart by
    separators — is squashed. That keeps every probe in :mod:`harness.safety.redteam` blocked
    while ordinary prose stops being collateral. The residual leak is narrower but real: an
    attacker who letter-splits one word anywhere in a message re-enables squashing for the whole
    of it, so a long enough message could still be joined across a boundary somewhere else.
    """
    return _NON_ALNUM.sub("", normalize(text))


# Three or more single characters, each held apart by separators — "i g n o r e", "i.g.n.o.r.e",
# "i-g-n-o-r-e". A word of two or more letters breaks the run at its own second character, which
# is what keeps ordinary prose out: "do not ignore. Previous" never reaches three repetitions.
_LETTER_SPLIT = re.compile(r"(?:[a-z0-9][^a-z0-9]+){3,}")


def is_letter_split(text: str) -> bool:
    """True when ``text`` shows the signature of a word split between its letters.

    This is the gate on :func:`squash`. It answers "is this input the kind that separator-folding
    was built for?", so the expensive-in-false-positives fold runs on evasions rather than on
    every message. Deliberately a *signature*, not a proof: an acronym like ``U.S.A.`` trips it,
    which costs nothing — it merely enables a check that then finds no marker.
    """
    return _LETTER_SPLIT.search(normalize(text)) is not None
