# Repo Glossary — this project's own vocabulary

Definitions of the terms, conventions, and symbols used **inside this repository**: the seam
pattern, the seven lessons, and every store/executor/type they introduce. For the *framework*
angle (how these map to LangGraph primitives) see [`langgraph-glossary.md`](langgraph-glossary.md).

Each entry lists where it lives and, where relevant, the ☁️ **Azure/Agent Framework** service the
local stand-in targets and the ⚠️ **leak** (where the stand-in is honestly weaker).

---

## Conventions (read these first)

### Harness / harness engineering
The **harness** is everything wrapped *around* a model call — context assembly, tools, guardrails,
memory, durability, orchestration, and human approval. "Harness engineering" is the discipline of
building that wrapper well. This repo re-implements 7 such patterns; the model call itself is stubbed.

### Seam pattern
The core convention. A capability is expressed as a `typing.Protocol` (or an injectable
callable/table), and a **local implementation** satisfies it for offline dev/tests. The same
interface later accepts an Azure-backed impl with **no change to the calling code**. Examples:
`CheckpointStore`, `ThreadStore`, `KnowledgeStore`, the `worker` callable, the `rules` table.

### "State the leak"
The honesty rule paired with the seam. Every local stand-in's docstring **names the Azure service it
substitutes for** and spells out exactly where it is weaker (no auth, no vectors, not a real security
boundary, at-least-once not exactly-once, …). A stand-in that hides its weakness is a bug in the docs.

### Lesson (L1–L7)
The 7 build increments, each one course pattern. Framed "Azure provides X / you build Y." Map:

| Lesson | Pattern | Module(s) |
|---|---|---|
| L1 | Input guardrails | `guardrails.py` + `safety/` + `app.py` |
| L2 | Durable execution | `workflow.py` + `durable/` |
| L3 | Secure sandboxing | `sandbox.py` |
| L4 | Memory | `memory/` (`thread`, `knowledge`, `summarize`) |
| L5 | Routing / handoff | `orchestration/router.py` |
| L6 | Supervision / fan-out | `orchestration/supervisor.py` |
| L7 | Human-in-the-loop | `hitl.py` (built on `durable/`) |

---

## L1 — Guardrails & safety (`guardrails.py`, `safety/`)

### Guardrail / `check_input`
The input policy run before anything reaches the model. `check_input` hard-blocks empty input,
oversize input (> `MAX_INPUT_CHARS`, 4000), and prompt-injection markers, returning a
`GuardrailResult(allowed, reason)`.
☁️ Azure AI **Content Safety — Prompt Shields**.

### `INJECTION_MARKERS`
The substring blocklist of jailbreak/injection phrases ("ignore previous instructions", …). A
**teaching baseline** only.
⚠️ Trivially bypassed by unicode look-alikes and spacing tricks on the raw string — which is exactly
what the `safety/` layer exists to close.

### `safety.normalize` / `safety.squash` (obfuscation folding)
`normalize` folds evasion tricks — homoglyphs, zero-width characters, full-width forms, case — into a
canonical form, so the markers are re-checked over *folded* text and are no longer bypassed by
look-alikes. `squash` goes one step further and removes **every** non-alphanumeric character, which
is what catches a marker split by visible separators (`i g n o r e`, `i.g.n.o.r.e`, `i-g-n-o-r-e`).
Being separator-agnostic, it costs nothing to defeat the next separator somebody picks.

### `safety.detectors` (attack-family heuristics)
Heuristic detectors for injection **families** the flat marker list can't express (e.g. instruction
-override, system-prompt exfiltration). Expresses *shapes* of attack, not fixed strings.

### `safety.redteam` (corpus) + scorer / `worst`
A red-team corpus of attack samples plus a scorer; `worst` returns the most severe verdict across the
detectors. Used to regression-test that evasion variants stay blocked.
⚠️ Still **heuristic, not ML** — managed Prompt Shields remain the production answer. Design + threat
model: [`safety-layer.md`](safety-layer.md).

---

## L2 — Durable execution (`workflow.py`, `durable/`)

### `run_durably(run_id, steps, store)`
The durable runner. Executes a list of named `steps` in order, **checkpointing after each**. Re-calling
with the same `run_id` skips completed steps and resumes from the next — the Azure-free equivalent of a
checkpointed Agent Framework workflow.

### Step
A `(name, fn)` pair; `fn(state) -> dict` receives accumulated state and returns updates merged in
(last-write-wins via `state.update`).

### `Checkpoint` / `CheckpointStore`
`Checkpoint(run_id, step, state)` is one snapshot, where `step` = index of the last **completed** step
(resume starts at `step + 1`). `CheckpointStore` is the Protocol seam (`load`/`save`).

### `SQLiteCheckpointStore`
Concrete store — one row per `run_id` in `.harness/checkpoints.db`. Writing to a **file** (not memory)
is what makes recovery survive a process restart.
☁️ Azure **Cosmos DB**.
⚠️ `save()` **upserts** — only the latest checkpoint is kept, so there is no checkpoint history (no
time-travel).

### `run_id`
The identity of one durable run; passing the same value is what triggers resume-from-checkpoint.

---

## L3 — Secure sandbox (`sandbox.py`)

### Sandbox / `SandboxResult`
Runs agent-generated code in an **isolated subprocess** with a hard timeout, returning
`SandboxResult(ok, stdout, stderr, exit_code, timed_out)`.
☁️ Foundry **Code Interpreter** (managed, network-isolated) / ACA Dynamic Sessions.
⚠️ A local subprocess is **not a real security boundary** — shares host FS/network, sets no CPU/memory
limits, and the timeout kills only the direct child (orphans/fork-bombs escape). Teaching stand-in only.

---

## L4 — Memory (`memory/`)

### Thread / `ThreadStore` / `SQLiteThreadStore` / `Message`
Short-term conversation memory. `ThreadStore` (Protocol: `append`/`history`) with an append-only,
insertion-ordered `Message(role, content)` log keyed by `thread_id`. `AUTOINCREMENT seq` gives stable
ordering independent of wall-clock.
☁️ Agent Service **managed threads**.
⚠️ Single local file, no auth/replication, unbounded growth (no server-side trimming).

### Knowledge / `KnowledgeStore` / `InMemoryKnowledgeStore` / `Hit`
Long-term retrieval. `KnowledgeStore` (Protocol: `add`/`search`) returning `Hit(doc_id, text, score)`;
the in-memory impl scores by fraction of distinct query terms overlapping a doc (ties break by `doc_id`).
☁️ **Azure AI Search**.
⚠️ Keyword **overlap** only — no vectors/embeddings/synonyms, so "car" ≠ "automobile". Semantically
relevant docs can score 0.0.

### `summarize_thread`
History roll-up: returns the transcript verbatim if it fits `max_chars`, else keeps the first/last
`keep` turns and drops the middle behind a `[...k earlier turns omitted...]` marker.
⚠️ Deterministic truncation, **not** an LLM recap — no meaning preserved from the dropped middle.
Mitigation: the raw thread stays in the `ThreadStore`, so a bad summary is recoverable.

---

## L5 — Routing (`orchestration/router.py`)

### `Router` / `route` / `RouteDecision`
Intent routing / handoff. `Router.route(request)` returns `RouteDecision(specialist, matched_intent)`
by **first-matching keyword** (case-insensitive substring).
☁️ A triage **agent** (LLM classifier + handoff).
⚠️ A substring table has no notion of meaning — misses synonyms, gameable by word order, carries no
thread context.

### `Specialist` / `DEFAULT_RULES`
`Specialist` is the enum of handoff targets (`BILLING`, `CODE`, `RESEARCH`, `FALLBACK`). `DEFAULT_RULES`
is the injectable trigger-word → specialist table; `FALLBACK` fires when nothing matches.

---

## L6 — Supervision (`orchestration/supervisor.py`)

### `Supervisor` / `run` / `decompose` / `worker`
A manager that splits a task and runs each piece on a `worker` **in parallel** via a `ThreadPoolExecutor`.
`decompose` is a naive splitter (on `;` and newlines); `worker` is the injected sub-agent seam;
`max_workers` bounds concurrency.
☁️ Agent Framework **Magentic / concurrent orchestration**.

### `SubResult` / `Aggregate` — fan-out / fan-in
`run` fans subtasks out and fans results back in **decomposition order, not completion order**
(pre-sized results list slotted by index). `SubResult(subtask, output, error)` isolates a worker
failure into `error`; `Aggregate(results, succeeded, failed)` is the roll-up.
⚠️ Static one-shot fan-out (no re-planning); isolation covers **faults, not liveness** — a hung worker
blocks the batch (`future.result()` has no timeout).

---

## L7 — Human-in-the-loop (`hitl.py`)

### `request_approval` / `ApprovalPending`
Parks a run before a sensitive action: writes an `"awaiting_approval"` checkpoint (prompt, injected
`now` as requested-at, deadline) and returns `ApprovalPending` **without performing the action**. The
durability of the pause *is* the L2 checkpoint store, reused.
☁️ Agent Framework **`RequestInfoExecutor`**.
⚠️ No routing to a person, no approver identity/auth — the "approver" is whoever calls `resume()`.

### `resume` / `ApprovalOutcome`
Resolves a parked run given a human `decision`. Checks the **deadline first** (a late "yes" is void →
`timed_out`); on approve-and-on-time runs the injected `action`, then writes a terminal checkpoint.
Returns `ApprovalOutcome(status, detail)` where status ∈ {approved, rejected, timed_out}.

### At-least-once / idempotency
Execution guarantee (same as L2): a crash after `action()` but before the terminal checkpoint re-runs
the action on resume. The injected action **must be idempotent** — doubly important because it is
sensitive by definition.

### `STATUS_AWAITING` / deadline (`now` injected)
`STATUS_AWAITING = "awaiting_approval"` marks a parked run. `now` is always **passed in**, never read
from the clock, so deadlines are deterministic in tests.

---

## The API & cross-cutting (`app.py`, config)

### FastAPI app / `/health` / `/chat`
`app.py` is the thin orchestration API. `/health` is the liveness probe (used by Azure Container Apps);
`/chat` takes a `ChatRequest(message)` through `check_input` and returns a `ChatResponse(reply, guardrail)`.
☁️ Deployment target: **Azure Container Apps**.

### Keyless auth
Project rule: prefer **Managed Identity + `DefaultAzureCredential`**, fall back to Key Vault only where a
service needs a key. Real secrets never committed (`.env` is gitignored). *(Aspirational — no Azure wired
yet.)*

### `uv`
The toolchain. System Python is 3.9; the project requires 3.11, which `uv` provisions.
`uv run --extra dev pytest` runs the suite.

---

See also: [`langgraph-glossary.md`](langgraph-glossary.md) (framework mapping) ·
[`architecture.md`](architecture.md) (design + SLOs + ADRs) ·
[`azure-implementation-plan.md`](azure-implementation-plan.md) (blueprint) ·
[`safety-layer.md`](safety-layer.md) (threat model)
