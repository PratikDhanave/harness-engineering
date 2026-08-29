"""Managed agent harness on Azure — practice project.

All 7 harness-engineering patterns are implemented locally, each behind a seam
that stands in for its Azure counterpart: guardrails (L1), durable execution (L2),
sandboxing (L3), memory (L4), routing (L5), supervision (L6), and human-in-the-loop
(L7). The Lesson 1 agent call is stubbed and the input guardrail runs inline in the
FastAPI app; Azure wiring is future work.
"""

__version__ = "0.1.0"
