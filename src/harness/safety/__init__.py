"""Adversarial safety layer — an evasion-resistant local stand-in for Content Safety Prompt Shields.

This hardens the Lesson-1 guardrail (`harness.guardrails`), whose substring marker list is, by its
own admission, "trivially bypassed (unicode look-alikes, spacing tricks)". Three thin, stdlib-only
pieces, each honest about where the local stand-in is weaker than the managed ML service:

- :mod:`~harness.safety.normalize` — folds homoglyph / zero-width / full-width disguises, and
  squashes separators, so the marker match sees intent, not bytes.
- :mod:`~harness.safety.detectors` — heuristic attack-family detectors (indirect injection,
  authority escalation, role-play/jailbreak, disclosure suppression) the marker list can't express.
- :mod:`~harness.safety.redteam` — a small standing adversarial corpus + scorer, so the block rate
  is a tracked regression metric.
"""

from __future__ import annotations

from harness.safety.detectors import Detection, detect_attacks, worst
from harness.safety.normalize import normalize, squash
from harness.safety.redteam import CORPUS, Probe, Result, score

__all__ = [
    "CORPUS",
    "Detection",
    "Probe",
    "Result",
    "detect_attacks",
    "normalize",
    "score",
    "squash",
    "worst",
]
