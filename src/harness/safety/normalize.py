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

__all__ = ["fold_homoglyphs", "normalize", "squash"]

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

    Callers must squash the *marker* too, then substring-match. False positives are negligible
    because the markers are long phrases: ``"ignorepreviousinstructions"`` does not occur by
    accident. It is not free of cost — squashing also joins legitimately adjacent words, so a
    marker could in principle match across a word boundary it did not mean to. With phrases this
    long that has not happened, and the corpus in :mod:`harness.safety.redteam` is what would
    show it if it started to.
    """
    return _NON_ALNUM.sub("", normalize(text))
