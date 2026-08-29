# The seven lessons on the Microsoft Agent Framework

Each lesson exists twice: `harness/<module>.py` builds it by hand, and
`harness/af/<module>.py` builds it on the framework. Same seam, two sides —
which is the point of the seam.

Run all seven: `uv run python3 scripts/af_tour.py` (no cloud, no key, no network).

| Lesson | Framework primitive | Module | Cloud needed |
|---|---|---|---|
| 1 Check what comes in | `AgentMiddleware` — refuses without calling `call_next()`, so a blocked message never reaches the model | `af/guard.py` | no |
| 2 Survive a crash | `WorkflowBuilder` + `FileCheckpointStorage`, resumed by `run(checkpoint_id=...)` | `af/durable.py` | no |
| 3 Isolate risky code | `SupportsCodeInterpreterTool` — a **hosted** tool; no in-process equivalent exists | `af/sandbox.py` | **yes** (not wired: this repo is local-only) |
| 4 Remember things | `AgentSession` + `InMemoryHistoryProvider`, and a `BaseContextProvider` for retrieval | `af/remember.py` | no |
| 5 Send work to the right place | switch-case edge group — the graph picks the branch | `af/route.py` | no |
| 6 Split work up | `add_fan_out_edges` / `add_fan_in_edges` | `af/supervise.py` | no |
| 7 Ask a person first | `WorkflowContext.request_info()` + `@response_handler` | `af/gate.py` | no |

## Two things found the hard way

**Dropping the Azure client is what unlocked the current stack.**
`agent-framework-azure-ai` has never shipped past `1.0.0rc6` and declares an
open-ended `agent-framework-core>=1.0.0rc6` while importing `BaseContextProvider`,
which core renamed to `ContextProvider`. That one package pinned everything to a
preview and kept `agent-framework-orchestrations` (which needs `core>=1.15`) out
of reach. This repo runs on **Foundry Local**, so the Azure client went, and the
whole stack moved to current stable. `HARNESS_AGENT_MODE=azure` now raises with
that explanation instead of failing three layers down.

**The orchestration builders are agent-shaped, and our seams are not.**
`HandoffBuilder` takes real `Agent`s and the handoff is decided *by a model*;
`ConcurrentBuilder` dispatches an `AgentExecutorRequest` to its participants, so
a worker must speak the agent message model rather than being a plain callable
(verified — it fails graph validation otherwise). Lessons 5 and 6 take ordinary
functions, which is exactly what lets them run with no model. Switch-case and
fan-out/fan-in edge groups are core workflow features and fit that shape. Reach
for the builders when the participants really are agents.

**`@response_handler` does not resolve string annotations.** `af/gate.py`
deliberately omits `from __future__ import annotations`: the validator calls
`get_origin()` on the raw annotation, so with PEP 563 in force a correct
`WorkflowContext[...]` is rejected with a message quoting the very type it
wanted. `@handler` resolves strings; `@response_handler` does not.

## What is still honestly missing

- **Lesson 3 has no local framework path**, and that is the lesson: isolation is
  another machine, not a library. The local subprocess stays, and stays honest
  about not being a security boundary.
- **No scratch-pad memory.** The L4 slide says three of four kinds; so does the code.
- **The fan-out is static.** The manager splits once and cannot re-plan when a
  piece comes back badly — that is what Magentic adds, and taking it would mean
  making the workers agents.
- **Guardrails only guard the way in.** Output filtering would be a second
  middleware, and nobody has written it.
