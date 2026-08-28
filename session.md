# Session Log — harness-engineering-pratice

> A full record of the working session that took this repository from a fresh scaffold
> (only `README.md` + an Azure plan doc) to a **local-first implementation of all 7
> harness-engineering patterns**, with design docs, an adversarial audit, and remediation.
>
> Repo: `PratikDhanave/harness-engineering-pratice` (private) · Language: Python 3.11 · Tooling: `uv` + `pytest`
> Span: 2026-07-06 → 2026-07-11 · Author of all commits: PratikDhanave

---

## 1. Outcome at a glance

| | |
|---|---|
| **Patterns implemented** | 7/7 (Lessons 1–7), local-first, every Azure dependency stubbed behind a seam |
| **Tests** | 59 passing, deterministic, cloud-free (`uv run --extra dev pytest`) |
| **Source** | ~1,460 LOC across `src/harness/` (16 modules) + `tests/` (8 files) |
| **Docs** | `architecture.md` (design), `azure-implementation-plan.md` (blueprint), `lesson-02-durable-execution.md`, `CLAUDE.md`, `README.md` |
| **Multi-agent workflows** | 2 (build Lessons 4–7; adversarial repo audit) — 32 subagents total |
| **Final commit** | `cc7398d` (session log) on `main`, pushed to private `origin`, working tree clean |

---

## 2. The project in one paragraph

A learning project that re-implements the 7 "harness engineering" patterns from the
[Hendrixer/harness-engineering](https://github.com/Hendrixer/harness-engineering) course —
originally taught by hand in TypeScript — on **Azure using Python and managed primitives**
(Azure AI Foundry Agent Service + Microsoft Agent Framework). The engineering philosophy:
**buy the harness from managed services; own the composition.** Because Azure wiring needs a
live account, every capability is first built **local-first** behind a *seam* (a `Protocol` /
injectable callable / rule table) with a local implementation whose docstring names the Azure
service it stands in for and honestly **states where the local stand-in is weaker** ("state the leak").

---

## 3. Chronological narrative

### Phase A — Orient & correct the record
- Ran `/init`. The existing `CLAUDE.md` had inferred **Go** from the `GOPATH`-style directory path.
  Evidence contradicted it: a new `docs/azure-implementation-plan.md` explicitly committed the project
  to **Python + Azure**. Rewrote `CLAUDE.md` to correct the language, point at the plan as source of
  truth, and stop future sessions from re-deriving "this is Go."
- Confirmed the remote (`origin`, private GitHub repo).

### Phase B — First commit + review + hygiene audit
- Committed `CLAUDE.md` + the Azure plan.
- **Self-review** flagged: the message said "Rewrite" but git recorded an *add* (the old CLAUDE.md was
  never tracked); the commit bundled the user-authored plan doc under a Claude co-author trailer.
- **Hygiene audit** found the real gaps: no `.gitignore` (critical before Python generates `.env`/`.venv`),
  no `LICENSE`, stub README.

### Phase C — Advisory pass & "make it directive"
- Consulted the `claude-code-guide` agent on CLAUDE.md best practices. Verdict: CLAUDE.md should be
  **primarily directive but fact-grounded**; for a planning-only repo keep it minimal; `@import` exists
  but isn't free (consumes context), so a plain path reference to the plan is better for context economy.
- Applied: added a `.gitignore` (Python + Azure/`azd`), a directive **"Working rules"** section to
  CLAUDE.md (thin implementations · pin preview versions · keyless-auth-first), expanded the README,
  and amended the first commit's message for accuracy.

### Phase D — Attribution
- On request, stripped the `Co-Authored-By: Claude` trailers from the two unpushed commits via
  `git filter-branch --msg-filter`, then cleaned the `refs/original/` backup + expired reflog so the
  old (trailer-bearing) commits were unreachable. Everything attributed solely to PratikDhanave.
- Verified repo integrity, and **tested `.gitignore` behaviorally** (created real `.env`/`.venv`/
  `__pycache__`/`.azure` and confirmed git ignored them).

### Phase E — Lesson 1 (the agent harness)
- Scaffolded a runnable FastAPI app: `pyproject.toml` (uv, Python 3.11), `src/harness/app.py`
  (`/health` + `/chat`, agent call **stubbed** so it runs with no Azure), `guardrails.py`, and tests.
- Left the **guardrail policy as a deliberate user exercise** (a security-vs-UX decision), marked with
  an `xfail` injection test as the target.
- On request, implemented the reference guardrail (**hard-block** on empty / oversize / injection
  markers), removed the `xfail`, and added tests. Booted `uvicorn` and smoke-tested the endpoints live.

### Phase F — Lesson 2 plan, then Lessons 2 & 3
- Wrote `docs/lesson-02-durable-execution.md` (checkpoint-store seam, resume logic, crash-recovery
  tests as the acceptance spec).
- **Lesson 2 (Durable Execution):** `CheckpointStore` Protocol + `SQLiteCheckpointStore` +
  `run_durably()`; proved recovery with a **subprocess crash-and-resume test**.
- **Lesson 3 (Secure Sandboxing):** `run_code()` in an isolated (`-I`) subprocess with a hard timeout;
  documented that it is *not* a real security boundary (Code Interpreter is).

### Phase G — The distinguished-level architecture doc
- On request ("Google Distinguished Engineer level… other models are going to attack you"), wrote
  `docs/architecture.md`: explicit SLOs (each tied to its *dominating dependency*), C4 views,
  per-capability design, data/consistency model (**at-least-once + idempotency**, not exactly-once),
  STRIDE threat model + prompt-injection defense-in-depth, capacity/latency budgets, a cost-model shape,
  ADRs with rejected alternatives, a risk register, and an **"Anticipated critiques & rebuttals"**
  section engineered to absorb adversarial review. All Mermaid diagrams validated with `mmdc`.

### Phase H — Lessons 4–7 via a build workflow (ultracode)
- With ultracode enabled, ran a **Workflow**: an implement→review pipeline over the 4 remaining lessons
  (8 subagents). Each implementer wrote its module(s) + deterministic tests behind a seam and passed
  its own test file; a reviewer then attacked each for correctness, seam consistency, test rigor, and
  honesty. All four **approved with zero high/medium issues**.
  - **L4 Memory:** `memory/thread.py` (SQLite threads), `knowledge.py` (keyword search ≈ AI Search),
    `summarize.py` (lossy roll-up).
  - **L5 Routing:** `orchestration/router.py` (triage → specialist, injectable rule table).
  - **L6 Supervision:** `orchestration/supervisor.py` (real `ThreadPoolExecutor` fan-out/fan-in, fault isolation).
  - **L7 Human-in-the-loop:** `hitl.py` (built on L2 checkpoints; injected clock for deterministic timeout).
- Applied the reviewers' low-severity findings myself (correctness + honesty): guarded `keep<=0` in
  summarize, disclosed the supervisor's **liveness leak** (a *hanging* worker isn't isolated) and HITL's
  **at-least-once** semantics, and added edge-case tests. Committed each lesson separately; updated docs.

### Phase I — Adversarial repo audit + remediation (ultracode)
- Ran a second **Workflow**: a 5-dimension audit (correctness, security, tests, docs-consistency,
  hygiene) where **every raw finding was adversarially verified** by an independent skeptic prompted to
  *refute* it (24 subagents). The verify phase refuted the noise (disclosed router substring behavior,
  a DoS red herring, a tracked-`.db` false alarm) and down-graded over-severe findings.
- **13 findings survived.** Fixed all of them (see §5) and pushed in 4 grouped commits.

### Phase J — Session log & tooling Q&A
- Wrote this `session.md` and committed it (`cc7398d`).
- Answered CLI questions: `claude --resume` / `--continue` are terminal commands (the session was
  already live); consulted the `claude-code-guide` agent to confirm permission-mode behavior.
  Takeaway: `bypassPermissions` (the `--dangerously-skip-permissions` mode) is **not** reachable via
  Shift+Tab (which cycles Manual → Accept Edits → Plan → Auto); it can be set via `defaultMode` in
  `.claude/settings.json` (applies on reload) or by relaunching with the flag. `/permissions` manages
  allow/ask/deny rules. No settings were changed (bypass disables all prompts — left to the user).

---

## 4. Key decisions & rationale

- **Path-based inference vs. stated intent** → the explicit plan doc wins over the GOPATH location; the
  project is Python, not Go.
- **Buy vs. build the harness** → managed Azure primitives; our code is orchestration + guardrails + glue.
- **Seam pattern everywhere** → a narrow interface (Protocol / callable / table) with a **local impl** for
  offline deterministic tests and an **Azure impl** later. This is what makes local-first + testability real,
  and limits blast radius of the preview-API risk.
- **At-least-once, not exactly-once** → exactly-once across external side-effects is impossible without the
  side-effecting system's cooperation; steps/actions must be idempotent. Stated up front in code and docs.
- **"State the leak"** → where a local stand-in is weaker than Azure, the docstring says so. Overstating a
  fake boundary is worse than admitting it — and it is what survives external review.
- **Attribution** → all commits under the user's name; Claude co-author trailers removed on request.

---

## 5. Audit findings & fixes (all resolved)

| Severity | Finding | Resolution |
|----------|---------|------------|
| 🔴 High | `README.md` front page said "no code yet" — false and self-contradictory | Corrected status header, structure note, Getting Started, caveats |
| 🟠 Med | **Real bug:** sandbox timeout returned `bytes` in a `str`-typed field (undecoded partial output) | Added `_as_text()` decode on the timeout path + regression test; preserved partial stderr |
| 🟠 Med | `lesson-02` plan said "not yet built" + referenced a nonexistent test name | Marked implemented, ticked met criteria, fixed the test name |
| 🟡 Low ×10 | Doc staleness (`architecture.md` status, `pyproject`, `__init__`); N6/N7/§9.1 over-claims; 4 test-coverage gaps; `.gitignore` not covering `.claude/settings.local.json` | All fixed: hedged claims to match code, added boundary/marker/slice/keep tests, repo-local ignore rule |

Refuted by verification (not real issues): router substring false-positives (disclosed, by-design), a
guardrail-DoS claim, a tracked-`.db` risk.

**Net after remediation:** 59 tests pass, all Mermaid diagrams render, zero stale status phrases, docs
and code mutually consistent.

---

## 6. Final repository state

```
harness-engineering-pratice/
├── CLAUDE.md                     # directive guidance (Python, seam convention, working rules)
├── README.md                     # overview + Mermaid diagrams + accurate status
├── session.md                    # this file
├── pyproject.toml  +  uv.lock    # uv, Python 3.11
├── .gitignore  +  .env.example
├── docs/
│   ├── architecture.md               # design doc: SLOs, C4, ADRs, STRIDE, rebuttals
│   ├── azure-implementation-plan.md  # the Azure blueprint (lesson-by-lesson)
│   └── lesson-02-durable-execution.md
├── src/harness/
│   ├── app.py                    # L1 FastAPI: /health, /chat (agent stubbed)
│   ├── guardrails.py             # L1 input guard (Content Safety stand-in)
│   ├── workflow.py + durable/    # L2 run_durably + CheckpointStore + SQLite (Cosmos stand-in)
│   ├── sandbox.py                # L3 isolated-subprocess run_code (Code Interpreter stand-in)
│   ├── memory/                   # L4 thread + knowledge + summarize (threads/AI Search stand-ins)
│   ├── orchestration/router.py   # L5 triage → specialist (handoff stand-in)
│   ├── orchestration/supervisor.py  # L6 parallel fan-out/fan-in (Magentic stand-in)
│   └── hitl.py                   # L7 approval gate on checkpoints (RequestInfoExecutor stand-in)
└── tests/                        # 8 files, 59 tests, deterministic
```

**Commit history (this session):**
```
fdcadfc first commit
9620f82 Add CLAUDE.md and Azure implementation plan
d2b5d86 Add .gitignore, working rules, and README orientation
dcdb3ba Expand README with detailed overview and Mermaid diagrams
c4eaf6f Scaffold Lesson 1: runnable FastAPI harness with guardrails and tests
32153c0 Implement Lesson 1 guardrail: hard-block injection policy
82ee932 Add Lesson 2 (Durable Execution) implementation plan
b3157f5 Implement Lesson 2: durable execution with checkpoint/resume
5eccd4e Implement Lesson 3: secure sandboxing (isolated subprocess + timeout)
310c694 Add detailed architecture.md (design doc with SLOs, ADRs, threat model)
343f508 Implement Lesson 4: advanced memory (threads, knowledge, summarization)
bfb121b Implement Lesson 5: orchestration routing/handoff
c063063 Implement Lesson 6: hierarchical supervision (parallel fan-out/fan-in)
cae9dcc Implement Lesson 7: human-in-the-loop approval gate
85e478b Docs: mark all 7 lessons implemented locally
9ff84f3 Fix sandbox timeout returning bytes in str field; disclose timeout scope
7291ea2 Harden tests for gaps found in audit
cf7226c Docs: correct stale status to reflect all 7 lessons implemented locally
c20f76b gitignore: cover .claude/settings.local.json at repo level
cc7398d Add session.md — full working-session log
9ca94c8 Update session.md: add Phase J (session log + permission-mode Q&A)
```
_(A session log is always one commit behind the commit that saves it — later `session.md`
updates, including this review's fixes, land in subsequent commits.)_

---

## 7. Multi-agent workflows used

1. **Build Lessons 4–7** — `implement → review` pipeline, 8 subagents. Parallel disjoint-file writes
   (shared `__init__.py` pre-created to avoid conflicts); each lesson reviewed as its impl landed.
2. **Repo audit** — 5 auditors → per-finding adversarial `verify` (refute-first), 24 subagents, ~673k
   tokens. Only findings surviving refutation were reported; severities adjusted by verifiers.

Pattern that made both work: **fan out to find/build, then adversarially verify before accepting.**

---

## 8. Conventions for future sessions

- **Add code the same way:** a seam (`Protocol` / callable / table) + a local impl whose docstring names
  the Azure counterpart and states the leak. Match the tone of `durable/` and `guardrails.py`.
- **Tests are deterministic:** no sleeps / randomness / network. Inject clocks and dependencies. Prove
  concurrency with `threading.Barrier`/`Event`, not timing.
- **Run:** `uv run --extra dev pytest` (full) · `uv run uvicorn harness.app:app --reload` (API).
- **Keep docs honest:** when code changes, update `README.md`, `CLAUDE.md`, and `architecture.md` status
  together — doc↔code drift was the dominant audit finding.

---

## 9. Open items / suggested next steps

- **Lesson 2's last acceptance item:** route `/chat` through `run_durably()` behind a flag (only
  unchecked criterion).
- **Azure adapters:** write the `AzureImpl` side of each seam (`cosmos_store.py`, AI Search, Agent
  Service, Content Safety) — needs a live Foundry project + pinned preview SDK versions.
- **External review:** `architecture.md` is ready to be run past other models (Grok/ChatGPT/Gemini);
  feed critiques back for point-by-point defense or revision.
- **Optional:** add a `LICENSE`; consider a linter (`ruff`) config.
