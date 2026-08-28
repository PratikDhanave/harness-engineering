# Lesson 2 — Durable Execution (implementation plan)

> Next increment after Lesson 1 (the agent harness). Blueprint reference:
> [`azure-implementation-plan.md`](azure-implementation-plan.md) §4 Lesson 2.
>
> Status: implemented locally (`workflow.py` + `durable/`, tests in `tests/test_durable.py`).
> The only remaining item is routing `/chat` through `run_durably()` behind a flag.

## Goal

Make an agent run **recoverable**: if the process crashes or hits a rate limit mid-run, restart
and **resume from the last checkpoint** instead of starting over. This is the "durable execution"
pattern — the harness persists progress, not just the final result.

**Pattern learned:** crash / rate-limit recovery via checkpointed state.

## Division of labor

- **Azure provides:** Agent Service threads are already persisted server-side; Microsoft Agent
  Framework **Workflows** support **checkpointing**.
- **We build:** wrap the agent run in a workflow with a **checkpoint store**, and prove recovery.

## Design

Keep Lesson 1's "runs locally without Azure" principle. Introduce a storage seam so the recovery
logic is testable offline and the backend swaps for Azure later — the same pattern as the
`GuardrailResult` seam in Lesson 1.

```
src/harness/
├── durable/
│   ├── checkpoint.py     # CheckpointStore protocol + Checkpoint dataclass
│   ├── sqlite_store.py   # local impl (offline dev + tests) — default
│   └── cosmos_store.py   # Azure impl (deferred until Azure wiring)  [stub]
└── workflow.py           # run_durably(): execute steps, checkpoint after each
```

### The seam

```python
# checkpoint.py  (sketch — not final)
@dataclass
class Checkpoint:
    run_id: str
    step: int
    state: dict

class CheckpointStore(Protocol):
    def load(self, run_id: str) -> Checkpoint | None: ...
    def save(self, cp: Checkpoint) -> None: ...
```

`run_durably(run_id, steps)` loads any existing checkpoint, skips already-completed steps, runs
the rest, and `save()`s after each step. Default store is SQLite (a single file, gitignored).

### Open decision (from the blueprint, to resolve here)

**Checkpoint store backend:** Cosmos DB vs. blob vs. Redis. Decision: **SQLite locally, Cosmos in
Azure** — Cosmos matches the blueprint's cross-cutting choice and gives per-item TTL + partition
by `run_id`. Blob/Redis remain fallbacks if Cosmos cost/latency disappoints.

## How we prove it (the test = the spec)

The blueprint's acceptance criterion is itself a test: *kill mid-run, resume from the last
checkpoint.* Concretely:

1. `test_resume_skips_completed_steps` — run a workflow whose step 2 raises; assert steps 0–1 were
   checkpointed. Re-run with the same `run_id`; assert steps 0–1 do **not** re-execute and the run
   completes.
2. `test_fresh_run_executes_all_steps` — new `run_id` executes every step.
3. `test_checkpoint_survives_process_restart` — spawn a subprocess that dies mid-run, then a second
   process resumes from the SQLite file and finishes.

Use a spy/counter step to assert *which* steps actually ran (not just the final output) — the whole
point is that completed work is skipped.

## Acceptance criteria

- [x] `CheckpointStore` protocol + SQLite implementation
- [x] `run_durably()` checkpoints after each step and resumes from the latest
- [x] Recovery proven by an automated test that kills and resumes a run
- [x] Checkpoint DB file gitignored; no secrets (`.harness/` in `.gitignore`)
- [ ] `/chat` optionally routes through `run_durably()` behind a flag (keeps Lesson 1 green)
- [x] CLAUDE.md + README updated once it lands (per the maintaining rule)

## Out of scope (later lessons)

- Real Agent Framework workflow API + Cosmos wiring (needs Azure; pin preview versions then).
- Human-in-the-loop suspend/resume — that's Lesson 7, built on this checkpoint machinery.
