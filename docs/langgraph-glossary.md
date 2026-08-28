# LangGraph Glossary — every concept, mapped to this repo

A reference glossary of **LangGraph** concepts, each defined on its own terms and then
cross-referenced to the matching **harness-engineering pattern**, the **module in this repo**
that stands in for it, and the **Microsoft Agent Framework / Azure** primitive it targets.

> **Why this doc exists.** This project ([README](../README.md)) hand-rolls the same agent-harness
> primitives that LangGraph ships as a framework — but behind explicit *seams* (a `typing.Protocol`
> + a local impl that "states the leak"). LangGraph is the *other* dominant way to assemble these
> primitives, so learning its vocabulary alongside the repo's modules teaches the same ideas twice,
> from two angles. This repo does **not** use LangGraph; the mappings are conceptual analogies, not
> imports.

**Legend for the callouts under each term:**

- 🧩 **In this repo** — the file/function here that plays the same role (with the lesson number).
- ☁️ **Prod target** — the Microsoft Agent Framework / Azure primitive the repo module stands in for.
- ⚠️ **Leak** — where the repo's stand-in is genuinely weaker than the LangGraph/managed version.

---

## At-a-glance mapping table

| LangGraph concept | Harness pattern | This repo | MS Agent Framework / Azure |
|---|---|---|---|
| `StateGraph` / graph compile | Workflow assembly | `workflow.py` (linear step list) | Agent Framework `Workflow` |
| State schema + reducers | Accumulated run state | `state: dict` in `run_durably` | Workflow shared state |
| Node | Unit of work | step `(name, fn)`; supervisor `worker` | Executor |
| Conditional edge / routing | Intent handoff (L5) | `orchestration/router.py` | Triage agent |
| `Send` fan-out (map-reduce) | Supervision (L6) | `orchestration/supervisor.py` | Magentic / concurrent orch. |
| Checkpointer (`BaseCheckpointSaver`) | Durable execution (L2) | `durable/checkpoint.py` + `sqlite_store.py` | Cosmos DB checkpoint store |
| Thread / `thread_id` | Run + conversation identity | `run_id`; `thread_id` in `memory/thread.py` | Agent Service managed threads |
| Short-term memory | Conversation memory (L4) | `memory/thread.py` | Managed threads |
| Store (`BaseStore`) long-term memory | Knowledge retrieval (L4) | `memory/knowledge.py` | Azure AI Search |
| Message trimming / summarization | History roll-up (L4) | `memory/summarize.py` | Azure OpenAI summarize call |
| `interrupt()` / breakpoints | Human-in-the-loop (L7) | `hitl.py` | `RequestInfoExecutor` |
| `Command(resume=...)` | Resume a paused run | `hitl.resume(decision)` | HITL reply correlation |
| Pre/post model hook / guardrail | Input guardrails (L1) | `guardrails.py` + `safety/` | Content Safety Prompt Shields |
| `ToolNode` / tool (Code Interpreter) | Secure sandbox (L3) | `sandbox.py` | Foundry Code Interpreter / ACA |
| `@entrypoint` / `@task` (Functional API) | Durable function | `run_durably` + step fns | Checkpointed workflow |
| Platform / Server / Studio / Assistants | Deployment surface | *(no local equiv)* | Azure Container Apps |

---

## 1. Core graph model

### StateGraph
The central builder in LangGraph: a directed graph whose **nodes** are functions and whose **edges**
define control flow. You declare a state schema, `add_node(...)`, wire `add_edge(...)`, then
`compile()` it into a runnable. It is the "harness shape" made explicit as a graph.

> 🧩 **In this repo:** `workflow.py` — `run_durably(run_id, steps, store)` is a *degenerate* StateGraph:
> a **linear list** of `(name, fn)` steps instead of a branching graph. There is no builder object; the
> "graph" is just the list order.
> ☁️ **Prod target:** an Agent Framework `Workflow` (executors + edges).
> ⚠️ **Leak:** no branching, cycles, or parallelism in `workflow.py` — routing (L5) and fan-out (L6)
> live in *separate* modules rather than as edges of one graph.

### State (schema)
A typed, shared object (usually a `TypedDict`) that every node reads from and writes to. Each field
is a **channel**; the schema declares the fields and how updates to them are combined (see *Reducers*).

> 🧩 **In this repo:** the plain `state: dict` threaded through `run_durably`, and the
> `Checkpoint.state` dict in `durable/checkpoint.py`. Untyped, single-object, last-write-wins.

### Node
A function `(state) -> partial_state_update`. It receives the current state and returns a dict of the
channels it wants to update. Nodes are the only place work happens.

> 🧩 **In this repo:** a workflow step `fn(state) -> dict` in `workflow.py`, and each `worker(subtask)`
> in `orchestration/supervisor.py`. Both return a value that gets merged/collected — exactly the node
> contract.

### Edge
A directed connection between nodes declaring "after A, go to B." A **normal edge** is unconditional.
Special sentinels `START` and `END` mark where execution enters and leaves the graph.

> 🧩 **In this repo:** *implicit* — the order of the `steps` list in `run_durably` is the edge set.
> `range(start, len(steps))` is the sole "A → B → C" wiring.

### Conditional edge
`add_conditional_edges(source, router_fn, mapping)` — a function inspects the state and **returns the
name of the next node**, so control flow branches at runtime. This is how LangGraph does routing and
loops (e.g. "tools or END?").

> 🧩 **In this repo:** `orchestration/router.py` — `Router.route(request) -> RouteDecision` picks a
> `Specialist` by first-matching keyword. That's a conditional edge whose routing function is a
> keyword table instead of an LLM.
> ⚠️ **Leak:** a substring table has no notion of meaning — it misses synonyms and carries no context
> (the module says so). A real triage/conditional-edge fn can read the whole message.

### START / END
Reserved virtual nodes. `START` is the entry; an edge to `END` terminates that branch. Replaces the
older `set_entry_point` / `set_finish_point`.

> 🧩 **In this repo:** `start = cp.step + 1` (entry, possibly mid-list after a resume) and the loop
> falling off `len(steps)` (END) in `run_durably`.

### compile()
Turns the mutable `StateGraph` builder into an immutable, runnable `Pregel` object. This is where you
attach a `checkpointer=`, a `store=`, and static `interrupt_before=/interrupt_after=` breakpoints.

> ⚠️ **Leak:** no compile step here — `run_durably` is called directly with its `store` argument.
> The checkpointer is passed at *call* time, not *compile* time.

### Runnable / `invoke` / `stream` / `batch` / `ainvoke`
A compiled graph implements the LangChain **Runnable** interface: `invoke(input, config)` runs once,
`stream(...)` yields intermediate output, `batch(...)` runs many inputs, and the `a*` variants are
async.

> 🧩 **In this repo:** `POST /chat` in `app.py` is an `invoke`-shaped call (one input → one output).
> ⚠️ **Leak:** no `stream`/`batch`/async surface — the harness is synchronous request/response.

### MessageGraph (deprecated)
An older builder whose entire state was just a list of messages. Superseded by `StateGraph` +
`MessagesState`. Listed for completeness; don't reach for it in new code.

### Multiple schemas — input / output / private state
A graph can declare separate `input_schema` and `output_schema` (so callers see a narrow contract) and
carry extra *internal* channels that nodes pass between themselves but never expose:
`StateGraph(state, input_schema=..., output_schema=..., context_schema=...)`.

> ⚠️ **Leak:** no repo equiv — `run_durably` uses one open `dict` for input, internal, and output alike.

### Conditional entry point
`add_conditional_edges(START, router_fn)` — branch on the *very first* step, so the entry node itself is
chosen at runtime rather than fixed.

> 🧩 **In this repo:** `Router.route` picking the first specialist is the nearest shape; there's no fixed entry node.

### Parallel branches (fan-out / fan-in via edges)
Edges from one node to several others make them run **in the same super-step** (parallel); edges
converging back fan them in, their writes merged by the target channels' reducers. Graph-native
parallelism, distinct from `Send`.

> 🧩 **In this repo:** `Supervisor` fans out with threads, not edges; `workflow.py` has no parallel branches.

### Deferred node (`defer=True`)
A node marked `defer=True` waits until **all** other pending paths into it finish before running — used
for map-reduce aggregation so the reducer sees every branch.

> ⚠️ **Leak:** no repo equiv.

---

## 2. State, channels & reducers

### Channel
The storage cell behind one state field. LangGraph has channel *types*: `LastValue` (keep newest —
the default), `Topic` (a fan-in list), `BinaryOperatorAggregate` (fold with an operator), etc. The
channel type **is** the reducer.

> 🧩 **In this repo:** each key of the `state` dict is effectively a `LastValue` channel — `state.update(update)`
> overwrites prior values.

### Reducer
A function `(current, update) -> new` attached to a channel via `Annotated[type, reducer]`. It decides
how a node's partial write **merges** into existing state (append? overwrite? add?). Without a reducer,
the default is overwrite.

> 🧩 **In this repo:** `state.update(update)` in `run_durably` is a hard-coded last-write-wins reducer
> for every field. `memory/summarize.py` is a *manual* reducer over message history (fold long history
> into a shorter string).

### `add_messages`
The built-in reducer for conversation state: given a list of existing messages and new ones, it
**appends** while de-duplicating/updating by message `id`. It's what makes chat history accumulate
correctly across nodes.

> 🧩 **In this repo:** `SQLiteThreadStore.append(...)` in `memory/thread.py` — an append-only,
> insertion-ordered message log. Same "grow the transcript, never clobber" semantics, backed by a
> table instead of a channel.

### `MessagesState`
A prebuilt state schema with a single `messages` field already annotated with `add_messages`. Most
chat agents subclass it.

> 🧩 **In this repo:** the `Message(role, content)` dataclass + `SQLiteThreadStore.history()` play the
> `MessagesState` role.

### Annotated state / `TypedDict`
State schemas are `TypedDict`s whose fields carry their reducer via `Annotated[type, reducer]`
(e.g. `Annotated[list, add_messages]`). A field with no annotation is a plain overwrite channel.

> 🧩 **In this repo:** the untyped `state` dict is the "no annotation, overwrite" case for every field.

### Channel types (`LastValue`, `Topic`, `BinaryOperatorAggregate`, `EphemeralValue`)
The built-in channel kinds behind reducers: `LastValue` (newest wins — the default), `Topic`
(accumulate a list, optional de-dupe), `BinaryOperatorAggregate` (fold with an operator like `add`),
`EphemeralValue` (visible only for the next step, then cleared).

> 🧩 **In this repo:** every `state` key behaves as `LastValue`; the append-only `ThreadStore` echoes `Topic`.

---

## 3. Execution model (Pregel)

### Pregel / super-step / BSP
LangGraph's runtime is modeled on Google's **Pregel** / Bulk Synchronous Parallel algorithm. Execution
proceeds in **super-steps**: in each step, all currently-active nodes run (possibly in parallel), their
writes are applied to channels, and then the next set of nodes activates. A checkpoint is saved *between*
super-steps.

> 🧩 **In this repo:** the `for index in range(start, len(steps))` loop in `run_durably` is a
> single-node-per-super-step Pregel: run one step, apply its update, **save a checkpoint**, advance.
> ⚠️ **Leak:** one node per step, strictly sequential — no parallel activation within a super-step.

### `Send` (map-reduce / fan-out)
`Send(node_name, per_item_state)` lets a node dispatch **N parallel copies** of a downstream node, each
with its own slice of state — LangGraph's map-reduce primitive. The results fan back in via a reducer.

> 🧩 **In this repo:** `Supervisor.run(task)` in `orchestration/supervisor.py` — `decompose` splits the
> task and a `ThreadPoolExecutor` fans each subtask out to a `worker`, then fans results **back in
> decomposition order** (not completion order). This is the clearest `Send` analog in the codebase.
> ⚠️ **Leak:** static one-shot fan-out with no re-planning; a hung worker blocks the batch (no timeout).

### `RunnableConfig` / `configurable`
The per-run config object passed as the second arg to `invoke`. `config["configurable"]` carries
runtime values — most importantly `thread_id` (which checkpoint thread to use), plus any user-defined
knobs. `recursion_limit` also lives here.

> 🧩 **In this repo:** the **injected arguments** are the config seam — `store`, `now`, and the `rules`
> table are passed in rather than read from globals, so tests can supply deterministic values (the same
> reason `hitl` takes `now` instead of reading the clock).

### `recursion_limit`
A safety cap (default 25) on how many super-steps a single run may take before LangGraph raises
`GraphRecursionError` — prevents infinite loops in cyclic graphs.

> ⚠️ **Leak:** no equivalent here — `run_durably` is acyclic and finite by construction, so there's
> nothing to bound. `Supervisor.max_workers` bounds *concurrency*, which is a different thing.

### Streaming modes
`stream(..., stream_mode=...)` supports `"values"` (full state after each step), `"updates"` (just the
diffs), `"messages"` (token-by-token LLM output), `"custom"` (user-emitted data), and `"debug"`.

> ⚠️ **Leak:** not implemented — `app.py` returns a single JSON body. Streaming is a candidate for a
> later increment.

### Durability mode
Controls *when* checkpoints are written: newer LangGraph exposes `durability="sync"` (write before the
next step — safest), `"async"` (write in the background), or `"exit"` (only at the end — fastest, least
safe). Older API: `checkpoint_during=True/False`.

> 🧩 **In this repo:** `run_durably` is effectively `durability="sync"` — `store.save(...)` runs
> synchronously **after each step** before advancing, which is what guarantees resume-after-crash.

### Runtime & `context_schema` (static run context)
Newer LangGraph separates **static context** (user id, db handles, model choice — constant for a run)
from mutable state. You declare `context_schema` and pass `context=...` to `invoke`; nodes read it via a
`Runtime` object (`get_runtime`) instead of `config["configurable"]`.

> 🧩 **In this repo:** the injected `store` / `rules` / `worker` *are* static context, passed as arguments.

### `StreamWriter` / custom streaming (`get_stream_writer`)
A node can emit arbitrary progress data mid-execution by writing to a `StreamWriter`; the caller sees it
under `stream_mode="custom"`. Used for token-independent progress ("fetched 3/10 docs").

> ⚠️ **Leak:** no repo equiv — the harness returns one final body.

### Config extras — `tags` / `metadata` / `run_name` / `callbacks`
`RunnableConfig` also carries `tags` and `metadata` (filtering/observability in LangSmith), `run_name`
(a friendly label), and `callbacks` (tracing/event hooks).

> ⚠️ **Leak:** no repo equiv — observability is out of scope for the local stand-ins.

### `GraphRecursionError`
Raised when a run exceeds `recursion_limit` super-steps — the guard against infinite cycles.

> ⚠️ **Leak:** no repo equiv (the runner is acyclic and finite).

---

## 4. Persistence & checkpointing

### Checkpointer (`BaseCheckpointSaver`)
The pluggable persistence backend. After each super-step LangGraph serializes the full channel state
into a **checkpoint** and hands it to the checkpointer to store, keyed by `thread_id`. Supplying one at
`compile(checkpointer=...)` is what turns a stateless graph into a durable, resumable one.

> 🧩 **In this repo:** `durable/checkpoint.py` — the `CheckpointStore` **Protocol** (`load`/`save`) is
> the exact `BaseCheckpointSaver` seam. `SQLiteCheckpointStore` in `sqlite_store.py` is a concrete impl.
> ☁️ **Prod target:** an Azure Cosmos DB checkpoint store (same Protocol, no change to `workflow.py`).

### Checkpoint
A single immutable snapshot: the channel values, the next nodes to run, and metadata (step number,
timestamp, parent checkpoint). A thread is a *sequence* of these.

> 🧩 **In this repo:** the `Checkpoint(run_id, step, state)` dataclass. `step` = index of the last
> **completed** step, so resume starts at `step + 1`.
> ⚠️ **Leak:** `SQLiteCheckpointStore.save()` **upserts one row per `run_id`** — only the *latest*
> checkpoint is kept. There is no chain of prior checkpoints, so there is **no history and no
> time-travel** (see below).

### Thread / `thread_id`
The identifier that groups all checkpoints of one conversation/run. Pass the same `thread_id` in config
and LangGraph resumes exactly where that thread left off; use a new one for a fresh run.

> 🧩 **In this repo:** two names for this idea — `run_id` in `durable/`/`hitl.py` (the *run* thread) and
> `thread_id` in `memory/thread.py` (the *conversation* thread). Passing the same id is what makes
> `run_durably` skip completed steps.

### State snapshot — `get_state` / `get_state_history`
`graph.get_state(config)` returns the latest `StateSnapshot` for a thread; `get_state_history(config)`
walks **all** past checkpoints newest-first. These power inspection, resuming, and time-travel.

> 🧩 **In this repo:** `store.load(run_id)` == `get_state` (latest only).
> ⚠️ **Leak:** there is **no `get_state_history`** — the upsert store discards past checkpoints.

### `update_state` / time travel
Because the checkpoint chain is preserved, you can rewind to an *earlier* checkpoint and resume from
there, optionally `graph.update_state(config, values)` to edit the state before resuming — "fork the
timeline." This is the basis of debugging and of some HITL edits.

> ⚠️ **Leak:** **not supported** here — only the newest checkpoint survives the upsert, so you can
> resume the *current* run but cannot travel back to a prior step. An honest structural difference worth
> knowing before you reach for it.

### In-tree savers — `MemorySaver`, `SqliteSaver`, `PostgresSaver`
Concrete checkpointers: `MemorySaver` (in-process, non-durable — tests/demos), `SqliteSaver`
(single-file, local dev), `PostgresSaver` (production). Same `BaseCheckpointSaver` interface.

> 🧩 **In this repo:** `SQLiteCheckpointStore` is the `SqliteSaver` analog — a single `.harness/checkpoints.db`
> file, which is precisely what makes recovery survive a process restart.

### `checkpoint_ns` (namespace)
A checkpoint namespace that scopes checkpoints to a particular (sub)graph, so a subgraph's state doesn't
collide with its parent's. Empty for the root graph.

> ⚠️ **Leak:** no repo equiv — a flat single-graph store.

### `checkpoint_id`
The unique id of one checkpoint within a thread. Passing a specific `checkpoint_id` in config is how you
**resume from / travel to** an exact past point.

> ⚠️ **Leak:** the repo keys only by `run_id` (one row), so there's no per-checkpoint id to target.

### `StateSnapshot`
What `get_state` returns: `.values` (channel values), `.next` (nodes queued next), `.config` (its
checkpoint id), `.metadata`, `.created_at`, `.parent_config`, and `.tasks` (pending/failed tasks,
including interrupts).

> 🧩 **In this repo:** `Checkpoint(run_id, step, state)` is a minimal `StateSnapshot` — `state` ≈ `.values`, `step` ≈ position.

### Serializer (`JsonPlusSerializer`) / encryption
Checkpointers serialize state through a pluggable serde (default `JsonPlusSerializer`, which handles
messages, datetimes, etc.), optionally encrypted at rest.

> 🧩 **In this repo:** `SQLiteCheckpointStore` uses plain `json.dumps/loads` — same idea, no rich types or encryption.

### TTL
Checkpointers and the Store can expire entries after a time-to-live, bounding storage growth.

> ⚠️ **Leak:** no repo equiv — checkpoints/threads grow until pruned by hand.

---

## 5. Memory

LangGraph splits memory into **short-term** (within a thread, via the checkpointer) and **long-term**
(across threads, via the *Store*). This repo's Lesson 4 mirrors the split across three files.

### Short-term memory
The conversation state persisted by the checkpointer under a `thread_id` — the running message history
the agent replays each turn. It lives and dies with the thread.

> 🧩 **In this repo:** `memory/thread.py` — `SQLiteThreadStore.append/history`, an append-only
> row-per-turn transcript replayed in insertion order.
> ☁️ **Prod target:** Agent Service **managed threads**.
> ⚠️ **Leak:** single local file, no auth/replication, unbounded growth (no server-side trimming).

### Long-term memory — the Store (`BaseStore`)
A separate, cross-thread key-value store (`InMemoryStore`, `PostgresStore`) organized by **namespaces**
(tuples like `(user_id, "memories")`). It can be given an **index** for *semantic search* over stored
items, so an agent recalls facts from earlier, unrelated conversations. Supplied at `compile(store=...)`.

> 🧩 **In this repo:** `memory/knowledge.py` — `KnowledgeStore` Protocol + `InMemoryKnowledgeStore`
> (`add`/`search`), a keyword-overlap index.
> ☁️ **Prod target:** **Azure AI Search**.
> ⚠️ **Leak:** keyword *overlap* only — no vectors/embeddings/synonyms, so "car" ≠ "automobile". A real
> Store with an index does semantic ranking; documents that would rank well semantically can score 0.0 here.

### Message trimming / summarization
Long threads blow the context window. LangGraph offers `trim_messages` (drop by token budget) and the
summarization pattern (an LLM condenses old turns into a running summary, often in a `pre_model_hook`).

> 🧩 **In this repo:** `memory/summarize.py` — `summarize_thread(messages, max_chars, keep)` keeps the
> first/last `keep` turns and drops the middle behind a `[...k earlier turns omitted...]` marker.
> ⚠️ **Leak:** deterministic truncation, not an LLM recap — it preserves no meaning from the dropped
> middle. Mitigation: the raw thread stays in the `ThreadStore`, so a bad summary is always recoverable.

### Memory types — semantic / episodic / procedural
A taxonomy LangGraph's memory docs use: **semantic** (facts), **episodic** (past experiences/examples),
**procedural** (how-to / instructions, often the system prompt). All live in the Store; the type is about
*what* you keep, not a different API.

> 🧩 **In this repo:** `KnowledgeStore` holds semantic/episodic facts; a procedural prompt would be repo config.

### Semantic search in the Store (`index` / `embed` / `fields`)
Configure the Store with an embeddings `index` so `store.search(namespace, query=...)` does vector
similarity, not just key lookup — the managed version of what `InMemoryKnowledgeStore` approximates.

> ⚠️ **Leak:** the repo's search is keyword overlap, not embeddings — the exact "state the leak" in `memory/knowledge.py`.

### Namespace
A tuple key (e.g. `(user_id, "memories")`) that partitions the Store, scoping long-term memory per user
or per purpose.

> ⚠️ **Leak:** no repo equiv — `InMemoryKnowledgeStore` is a single flat namespace.

---

## 6. Human-in-the-loop (HITL)

### `interrupt()`
The dynamic HITL primitive: calling `interrupt(payload)` inside a node **pauses the graph**, persists a
checkpoint, and surfaces `payload` to the caller for a human to act on. Requires a checkpointer (the
pause has to be durable).

> 🧩 **In this repo:** `hitl.request_approval(run_id, prompt, store, now, ...)` — writes an
> `"awaiting_approval"` checkpoint holding the prompt + deadline and **returns without performing the
> action**. The durability of the pause *is* the Lesson 2 checkpoint store, reused verbatim.
> ☁️ **Prod target:** Agent Framework `RequestInfoExecutor`.

### `Command(resume=...)`
How you answer an interrupt: re-invoke the graph with `Command(resume=human_value)` and the paused node
continues, its `interrupt()` call now *returning* that value. `Command` can also carry `goto=` (jump to
a node) and `update=` (patch state).

> 🧩 **In this repo:** `hitl.resume(run_id, decision, store, now, action=...)` — loads the pending
> checkpoint, and on an approved-and-on-time decision runs the injected `action`, then writes a terminal
> checkpoint. `decision` is the `resume` value.
> ⚠️ **Leak:** at-least-once, not exactly-once — a crash after `action()` but before the terminal
> checkpoint re-runs the action on resume, so the action **must be idempotent** (the module says so).

### Breakpoints — `interrupt_before` / `interrupt_after`
*Static* pause points set at compile time: "always stop before node X." Unlike dynamic `interrupt()`,
they don't need code inside the node — useful for approval gates and step-through debugging.

> 🧩 **In this repo:** the approval gate in `hitl.py` is conceptually an `interrupt_before` on the
> sensitive action — the action never runs until a human resumes.

### Approval deadline / timeout
Not a core LangGraph API, but a common HITL requirement layered on top: if no human responds in time,
fail closed.

> 🧩 **In this repo:** `resume` checks `now - requested_at > timeout_seconds` **first**, so a late "yes"
> is void (`timed_out`). `now` is injected, never read from the clock, so the deadline is deterministic
> in tests.

### `Interrupt` object & resume map
When a graph pauses, `get_state().tasks[...].interrupts` holds `Interrupt` objects (each with a `value`
shown to the human and an `id`). With multiple concurrent interrupts you resume by passing
`Command(resume={interrupt_id: value})` — a map, not a single value.

> 🧩 **In this repo:** `ApprovalPending` is the single-interrupt case; there's no multi-interrupt map.

### `NodeInterrupt` (legacy)
The older way to pause: raise `NodeInterrupt(value)` from inside a node. Superseded by the `interrupt()`
function. Listed for completeness.

### Double-texting / interrupt-handling modes
When a new input arrives while a run is still going, the Platform offers strategies: `reject`, `enqueue`,
`interrupt` (stop current, start new), or `rollback` (undo current, start new).

> ⚠️ **Leak:** no repo equiv — a synchronous single-request handler.

### Review-a-tool-call pattern
The canonical HITL recipe: interrupt **before** a tool node, show the proposed tool call to a human, and
resume with approve / edit-args / reject.

> 🧩 **In this repo:** `request_approval` + `resume(decision, action=...)` is exactly this, minus arg-editing.

---

## 7. Multi-agent architectures

### Supervisor architecture
A **supervisor** agent decides which specialist sub-agent handles each step and routes control to it,
gathering results. Packaged as `langgraph-supervisor`. Sub-agents are themselves graphs.

> 🧩 **In this repo:** two halves — `orchestration/router.py` (the *triage*/routing decision, L5) and
> `orchestration/supervisor.py` (the *fan-out manager*, L6).
> ☁️ **Prod target:** Agent Framework Magentic / concurrent orchestration.

### Swarm / handoffs
In the **swarm** pattern (`langgraph-swarm`) there is no central manager: agents **hand off** to each
other directly via *handoff tools* — a tool call returns a `Command(goto="other_agent")`, transferring
control and (optionally) state.

> 🧩 **In this repo:** `Router.route(...)` returning a `Specialist` is a one-step handoff: it names the
> agent that should take the conversation.
> ⚠️ **Leak:** the handoff carries **no thread context** and can't be initiated *by* a specialist
> mid-conversation — it's a front-door classifier, not peer-to-peer transfer.

### Subgraph
A compiled graph used **as a node** inside a parent graph. Enables composition, team hierarchies, and
independent state schemas (with a mapping between parent and child state).

> 🧩 **In this repo:** the `worker: Callable[[str], str]` injected into `Supervisor` is the subgraph
> seam — in production it's a full sub-agent invocation; in tests it's a plain function.

### Network / hierarchical topologies
Beyond supervisor/swarm, agents can be wired as arbitrary graphs (any agent can call any other) or in
tiers (a top supervisor over team-supervisors over workers).

> 🧩 **In this repo:** `Supervisor` is a single flat tier (manager → workers). Hierarchy would nest a
> `Supervisor` as a `worker`.

### Handoff via `Command` / `Command.PARENT`
Agents transfer control by returning `Command(goto="agent_b", update=...)`. From inside a subgraph,
`Command(graph=Command.PARENT, goto=...)` navigates in the **parent** graph — the mechanism behind swarm
handoffs and supervisor routing.

> 🧩 **In this repo:** `RouteDecision` naming a `Specialist` is a value-level handoff; there's no shared graph to `goto`.

### `langgraph-supervisor` / `langgraph-swarm` (packages)
Prebuilt libraries: `langgraph-supervisor` wires a manager-over-workers topology; `langgraph-swarm` wires
peer agents with handoff tools. Both compile down to a `StateGraph`.

> 🧩 **In this repo:** `orchestration/supervisor.py` (manager) and `router.py` (front-door handoff) are the hand-rolled analogs.

### Agent-as-tool
An alternative to handoffs: wrap a sub-agent as a **tool** the parent agent calls, getting its result
back inline rather than transferring control.

> 🧩 **In this repo:** the injected `worker` callable in `Supervisor` is a sub-agent invoked as a plain call — the agent-as-tool shape.

---

## 8. Prebuilt agents & tools

### `create_react_agent`
The batteries-included **ReAct** agent constructor: give it a model and a list of tools and it builds a
graph that loops *reason → call tool → observe → repeat* until the model answers. The fastest path to a
working tool-using agent.

> 🧩 **In this repo:** `app.py`'s `/chat` is the *harness around* such an agent — for Lesson 1 the model
> call itself is stubbed, and the emphasis is the guardrail middleware wrapping it (context + tools +
> **guardrails**).

### Tool / `ToolNode` / `tools_condition`
A **tool** is a function the model may call. `ToolNode` is the prebuilt node that executes whichever
tools the model requested; `tools_condition` is the prebuilt conditional edge that routes to `ToolNode`
if there are tool calls, else to `END`.

> 🧩 **In this repo:** `sandbox.py` is a **tool** — it runs agent-generated code in an isolated
> subprocess with a hard timeout.
> ☁️ **Prod target:** Foundry **Code Interpreter** (managed, network-isolated sandbox) / ACA Dynamic Sessions.
> ⚠️ **Leak:** a local subprocess is **not a security boundary** — it shares the host FS/network, sets
> no CPU/memory limits, and only kills the direct child (orphans/fork-bombs escape). Teaching stand-in only.

### `pre_model_hook` / `post_model_hook`
Optional functions `create_react_agent` runs *before* the model (e.g. trim/summarize history, **input
guardrails**) and *after* it (e.g. output validation, redaction).

> 🧩 **In this repo:** `guardrails.check_input` is a `pre_model_hook` — it hard-blocks empty/oversize
> input and prompt-injection markers before anything reaches the model.
> ☁️ **Prod target:** Azure AI **Content Safety Prompt Shields**.
> ⚠️ **Leak:** the raw substring marker list is trivially bypassed; `safety/` (normalize + heuristic
> detectors + redteam corpus) closes homoglyph/zero-width evasion but is still heuristic, not ML.

### `InjectedState` / `InjectedStore`
Annotations that let a tool receive the graph's state or the long-term Store **without** the model
seeing/filling those arguments — the runtime injects them.

> 🧩 **In this repo:** conceptually the dependency-injection seam everywhere — `store`, `rules`, `worker`
> are injected by the caller, not supplied by a model.

### `create_agent` vs `create_react_agent`
The same prebuilt ReAct agent — `create_react_agent` (`langgraph.prebuilt`) is being renamed/streamlined
to `create_agent` in LangChain 1.0's agent package. Both names refer to the tool-loop agent.

### `AgentState`
The default state schema for prebuilt agents — a `MessagesState` plus `remaining_steps` (a budget so the
loop can stop before `recursion_limit`).

> 🧩 **In this repo:** no equiv; the loop/budget is implicit in the stubbed `/chat`.

### Structured output (`response_format`)
Passing `response_format=SomeSchema` makes the agent return a validated typed object (via a final
structured-output step) instead of free text.

> 🧩 **In this repo:** the Pydantic `ChatResponse` on the API boundary is a related "typed output" idea, not model-enforced.

### `ToolNode` error handling (`handle_tool_errors`)
`ToolNode` can catch a tool exception and feed the error back to the model as a `ToolMessage` (so it can
retry) instead of crashing the run.

> 🧩 **In this repo:** `sandbox.py` returns errors in `SandboxResult.stderr`/`exit_code` rather than raising — same "surface, don't crash" instinct.

### `ValidationNode`
A prebuilt node that validates tool-call arguments against a schema before execution.

> 🧩 **In this repo:** `guardrails.check_input` validates *input* the same way — fail closed before proceeding.

### Agent middleware
LangChain 1.0 agents accept **middleware** (before/after model, before/after tools) — e.g. summarization,
HITL, guardrail middleware — the extensible version of `pre_model_hook`/`post_model_hook`.

> 🧩 **In this repo:** `check_input` is before-model middleware; `safety/` is its evasion-resistant extension.

---

## 9. Functional API

### `@entrypoint`
The functional (non-graph) way to build durable workflows: decorate a normal function with
`@entrypoint(checkpointer=...)` and it becomes a resumable, checkpointed unit you call like any
function. State is just the function's locals + return value.

> 🧩 **In this repo:** `run_durably(run_id, steps, store)` is exactly an `@entrypoint`-style durable
> function — no graph object, just a checkpointed procedure that resumes by `run_id`.

### `@task`
A unit of work inside an `@entrypoint`, called like `future = my_task(...)`. Results are checkpointed,
so on resume completed tasks aren't re-run. Tasks can run concurrently.

> 🧩 **In this repo:** each `(name, fn)` step is a `@task` — its result is folded into `state` and a
> checkpoint is saved, so a resumed run skips it.

### `entrypoint.final`
A way for an entrypoint to return a value to the caller while persisting a *different* value as the
saved state — separating "what the caller sees" from "what resume restores."

> ⚠️ **Leak:** no equivalent — `run_durably` returns and checkpoints the same `state` dict.

### `previous` / entrypoint state
An `@entrypoint` with a checkpointer receives its **last return value** as `previous`, so a durable
function accumulates state across invocations without a graph.

> 🧩 **In this repo:** `run_durably` reloads prior `state` from the checkpoint on resume — the same "carry state across calls" idea.

### `StreamWriter` (functional)
Functional `@task`s / entrypoints can also stream custom progress via an injected `StreamWriter`.

> ⚠️ **Leak:** no repo equiv.

---

## 10. Reliability & performance

### `RetryPolicy`
Per-node `retry_policy=RetryPolicy(...)` — automatically retries a node on failure with backoff,
configurable by exception type and attempt count.

> ⚠️ **Leak:** not implemented — a step/worker that raises is **not** retried. The `supervisor` *isolates*
> a failure into `SubResult.error` instead of retrying; `run_durably` propagates it.

### `CachePolicy`
Per-node `cache_policy=CachePolicy(...)` — memoizes a node's output keyed by its input so repeated calls
with the same input skip recomputation.

> 🧩 **In this repo:** a weak echo — `InMemoryKnowledgeStore` precomputes each doc's term set on `add`
> so `search` doesn't re-tokenize. Not a general node cache.

### Fault isolation
Not a single API but a property: one node/branch failing shouldn't necessarily sink the whole run
(handled via retries, conditional edges to error handlers, or `Send` fan-out where each item is independent).

> 🧩 **In this repo:** `Supervisor.run` **isolates** each worker — an exception becomes that subtask's
> `SubResult.error` and never escapes `run`, so one bad sub-agent can't fail the batch.
> ⚠️ **Leak:** isolation covers *faults*, not *liveness* — a worker that **hangs** blocks the batch
> (`future.result()` has no timeout).

### Node cache
With a cache on compile plus a per-node `cache_policy`, LangGraph memoizes a node's output by an input
key (and optional TTL), skipping recomputation on identical inputs.

> 🧩 **In this repo:** `InMemoryKnowledgeStore` precomputing term sets is a narrow echo; there's no general node cache.

### Serde / deserialization safety
Because checkpointed state is serialized and later trusted, the serializer boundary is also a security
boundary — don't deserialize untrusted checkpoints blindly.

> 🧩 **In this repo:** `SQLiteCheckpointStore` round-trips via `json` (data-only), sidestepping code-execution deserialization risk.

---

## 11. LangGraph Platform (deployment)

These have **no local equivalent** in this repo — the deployment target here is Azure Container Apps
driving Agent Framework, not LangGraph Platform. Listed for completeness.

### LangGraph Server / Platform / Cloud
The managed (or self-hosted) runtime that serves compiled graphs over HTTP: persistent threads, a task
queue, horizontal scaling, and the checkpointer/Store wired to managed Postgres/Redis.

> ☁️ **Prod analog here:** a **FastAPI** app on **Azure Container Apps** (`app.py` is the seed) with
> Cosmos DB / AI Search as the managed backends.

### Assistants
A versioned *configuration* of a graph (its prompt, model, tools, config) that the Platform stores and
serves — you can update an assistant's config without redeploying code.

> ☁️ **Prod analog here:** an Agent Service **agent** definition.

### Threads API / cron / webhooks
Platform HTTP surface: create/read/resume **threads**, schedule **cron** runs, and register **webhooks**
for run completion.

> ☁️ **Prod analog here:** your own FastAPI routes + Azure Container Apps jobs / Event Grid.

### Deployment options
LangGraph Platform ships several models: **Cloud SaaS**, **Self-Hosted Data Plane** (control plane in
cloud, runtime in your VPC), **Standalone Container** (fully self-managed), and **BYOC**.

> ☁️ **Prod analog here:** Azure **Container Apps** hosting the FastAPI app.

### `langgraph.json`
The project config file the CLI reads — declares graphs (`"graphs": {...}`), dependencies, env, and auth.

> 🧩 **Analog here:** `pyproject.toml` + `app.py`'s `app` object.

### LangGraph CLI (`langgraph dev` / `build` / `up`)
Runs the server locally (`dev`, with Studio), builds a Docker image (`build`), or launches the stack (`up`).

> 🧩 **Analog here:** `uv run uvicorn harness.app:app --reload`.

### Custom auth (`@auth`)
Platform hook to authenticate requests and authorize access to threads/assistants/store resources per user.

> 🧩 **Analog here:** none yet; the project rule is Managed Identity + `DefaultAzureCredential` at the Azure layer.

### Run
One execution of an assistant on a thread (queued, streamable, cancelable). A thread holds many runs.

> 🧩 **Analog here:** one `run_id` execution of `run_durably`.

### LangSmith — tracing & evaluations
The observability/eval platform LangGraph integrates with: it traces every node/LLM call and runs offline
evals / regression gates.

> 🧩 **Analog here:** the `make ci`-style pytest gate (and offline eval gates in sibling projects); OpenTelemetry is the planned Azure path.

### `RemoteGraph`
A client wrapper that makes a deployed graph callable as if local (same `invoke`/`stream` interface).

> 🧩 **Analog here:** an HTTP client against the FastAPI API.

### LangGraph Studio / CLI
**Studio** is the visual debugger (inspect state per super-step, edit-and-resume, replay). The **CLI**
(`langgraph dev` / `build` / `up`) runs the server locally and packages it.

> 🧩 **In this repo:** the analog of Studio's step inspection is reading the checkpoint row + the test
> suite (`uv run --extra dev pytest`); there is no visual debugger.

### SDK (`get_client` / `RemoteGraph`)
Client libraries (Python/JS) to call a deployed graph, or treat a remote graph as if it were local
(`RemoteGraph`).

> ☁️ **Prod analog here:** an HTTP client against the FastAPI orchestration API.

---

## Summary: the one idea

LangGraph packages the harness as a **graph + checkpointer + store + interrupts**. This repo takes the
same primitives apart and rebuilds each behind a `typing.Protocol` seam, with a local impl that names
the Azure service it stands in for and **states exactly where it's weaker**. Learn the LangGraph name,
then open the mapped module here to see the primitive with its lid off.

- Durable execution / checkpointer → [`durable/`](../src/harness/durable) + [`workflow.py`](../src/harness/workflow.py)
- Memory (short-term / Store / summarize) → [`memory/`](../src/harness/memory)
- Routing & supervision (`Send`, conditional edges) → [`orchestration/`](../src/harness/orchestration)
- HITL (`interrupt` / `Command`) → [`hitl.py`](../src/harness/hitl.py)
- Guardrails (`pre_model_hook`) & tools (`ToolNode`) → [`guardrails.py`](../src/harness/guardrails.py) + [`safety/`](../src/harness/safety) + [`sandbox.py`](../src/harness/sandbox.py)

See also: [`architecture.md`](architecture.md) · [`azure-implementation-plan.md`](azure-implementation-plan.md) · [`safety-layer.md`](safety-layer.md)
