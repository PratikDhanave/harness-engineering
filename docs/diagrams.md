# Diagram Pack — harness-engineering-pratice

> A consistent set of diagrams for the managed agent harness. Every diagram uses one shared
> component glossary, so the views describe the *same* system. All Mermaid blocks are validated
> with `mmdc` and render natively on GitHub. For an editable hand-drawn version of the
> architecture, open [`architecture.excalidraw`](architecture.excalidraw) at excalidraw.com.


## Contents

- [C4 architecture views](#c4-architecture-views)
- [Message sequence diagrams](#message-sequence-diagrams)
- [State & lifecycle diagrams](#state--lifecycle-diagrams)
- [Class / seam diagrams](#class--seam-diagrams)
- [Data model & mapping](#data-model--mapping)
- [Deployment & data flow](#deployment--data-flow)


## C4 architecture views

### C4 L1 — System Context

```mermaid
flowchart TB
    User(["User / UI"])
    Approver(["Approver<br/>(human-in-the-loop)"])

    subgraph SYS["System boundary — our software"]
        API["FastAPI API (ACA)<br/>orchestrates managed agents,<br/>runs guardrails + durable workflows"]
    end

    subgraph AZURE["Azure managed platform (keyless)"]
        CS["Content Safety<br/>(Prompt Shields)"]
        AS["Agent Service<br/>(agents · threads · tools)"]
        AOAI["Azure OpenAI<br/>(GPT-4o/4.1)"]
        SEARCH["Azure AI Search"]
        COSMOS[("Cosmos DB")]
        MI["Managed Identity<br/>(keyless)"]
    end

    APPI["App Insights<br/>(OpenTelemetry)"]

    User -->|"chat / task request"| API
    API -->|"input guard (input-only, inline in /chat)"| CS
    API -->|"run agents"| AS
    AS -->|"model calls"| AOAI
    AS -->|"knowledge / RAG"| SEARCH
    API -->|"checkpoints (at-least-once)"| COSMOS
    API -.->|"pause for approval"| Approver
    Approver -.->|"approve / reject"| API
    API -.->|"traces + metrics"| APPI
    AS -.->|"traces"| APPI
    MI -.->|"tokens (no keys)"| API

    classDef person fill:#08427b,stroke:#052e56,color:#fff
    classDef sysbox fill:#1168bd,stroke:#0b4884,color:#fff
    classDef azure fill:#0f6cbd,stroke:#0a4d87,color:#fff
    classDef obs fill:#6b6b6b,stroke:#444,color:#fff
    class User,Approver person
    class API sysbox
    class CS,AS,AOAI,SEARCH,COSMOS,MI azure
    class APPI obs
```

_System context: the User (and an Approver for HITL) interact with our FastAPI API (ACA), which is the only component we build; every downstream capability — Content Safety, Agent Service, Azure OpenAI, AI Search, Cosmos DB, App Insights, Managed Identity — is an Azure managed service._

### C4 L2 — Container

```mermaid
flowchart TB
    User(["User / UI"])
    Approver(["Approver<br/>(human-in-the-loop)"])

    subgraph ACA["Azure Container Apps — FastAPI API (ACA)"]
        direction TB
        HTTP["HTTP surface<br/>/chat · /health"]
        MW["Agent Framework middleware<br/>guardrails · logging · tracing"]
        WF["Durable workflow<br/>run_durably + CheckpointStore"]
        ORCH["Orchestrator<br/>Router · Supervisor · HITL"]
        HTTP --> MW --> ORCH
        MW --> WF
        ORCH --> WF
    end

    subgraph AZURE["Azure managed services"]
        CS["Content Safety<br/>(Prompt Shields)"]
        AS["Agent Service<br/>(agents · threads · tools)"]
        AOAI["Azure OpenAI<br/>(GPT-4o/4.1)"]
        SEARCH["Azure AI Search"]
        COSMOS[("Cosmos DB")]
    end

    APPI["App Insights<br/>(OpenTelemetry)"]
    MI["Managed Identity<br/>(keyless)"]

    User -->|"request"| HTTP
    MW -->|"input guard (input-only)"| CS
    ORCH -->|"run agents · threads · tools"| AS
    AS -->|"model calls"| AOAI
    AS -->|"grounding / RAG"| SEARCH
    WF -->|"save/load checkpoints<br/>(at-least-once)"| COSMOS
    ORCH -.->|"suspend for approval"| Approver
    Approver -.->|"resume (deadline checked first)"| ORCH
    MW -.->|"traces + metrics"| APPI
    MI -.->|"tokens, no keys"| ACA

    classDef person fill:#08427b,stroke:#052e56,color:#fff
    classDef comp fill:#1168bd,stroke:#0b4884,color:#fff
    classDef azure fill:#0f6cbd,stroke:#0a4d87,color:#fff
    classDef obs fill:#6b6b6b,stroke:#444,color:#fff
    class User,Approver person
    class HTTP,MW,WF,ORCH comp
    class CS,AS,AOAI,SEARCH,COSMOS azure
    class APPI obs
    class MI obs
```

_Container view: inside the ACA boundary the FastAPI HTTP surface fronts the Agent Framework middleware, the durable workflow, and the orchestrator; the middleware runs the input-only guard against Content Safety, the orchestrator drives Agent Service (which calls Azure OpenAI and AI Search), the workflow persists at-least-once checkpoints to Cosmos DB, and Managed Identity supplies keyless tokens._

### C4 L3 — Component (orchestration service)

```mermaid
flowchart TB
    IN(["User / UI request"])
    APPR(["Approver"])

    subgraph ORCHSVC["Orchestration service (components = local seam modules)"]
        direction TB

        subgraph L1["L1 harness"]
            G["guardrails.check_input -> GuardrailResult<br/>input-only guard, inline in /chat"]
        end
        subgraph L5["L5 routing"]
            R["orchestration.Router.route -> RouteDecision<br/>triage intent to a specialist"]
        end
        subgraph L6["L6 supervision"]
            S["orchestration.Supervisor.run -> Aggregate<br/>fan-out sub-tasks, fan-in results"]
        end
        subgraph L3["L3 sandbox"]
            SB["sandbox.run_code -> SandboxResult<br/>isolated child; timeout kills direct child only"]
        end
        subgraph L4["L4 memory"]
            TH["memory.ThreadStore / SQLiteThreadStore<br/>short-term thread history"]
            KN["memory.KnowledgeStore / InMemoryKnowledgeStore<br/>long-term retrieval"]
            SUM["memory.summarize_thread<br/>compress thread context"]
        end
        subgraph L2["L2 durable execution"]
            WF["workflow.run_durably +<br/>durable.CheckpointStore [Protocol] /<br/>SQLiteCheckpointStore (at-least-once)"]
        end
        subgraph L7["L7 HITL"]
            H["hitl.request_approval / hitl.resume<br/>-> ApprovalPending / ApprovalOutcome<br/>deadline checked first"]
        end
    end

    subgraph MANAGED["Azure service each seam stands in for"]
        CS["Content Safety<br/>(Prompt Shields)"]
        ASH["Agent Service handoff/triage<br/>(Agent Framework)"]
        ASM["Magentic / concurrent<br/>orchestration"]
        ASC["Agent Service<br/>Code Interpreter"]
        AST["Agent Service<br/>managed threads"]
        SEARCH["Azure AI Search"]
        AOAI["Azure OpenAI<br/>summarization"]
        COSMOS[("Cosmos DB")]
        RIE["RequestInfoExecutor"]
    end

    IN --> G
    G -->|"allowed"| R
    R -->|"complex task"| S
    R -->|"simple task"| H
    S --> SB
    S --> TH
    S --> KN
    TH --> SUM
    KN --> SUM
    R -.->|"parked on gate"| H
    H -.->|"suspend"| APPR
    APPR -.->|"resume"| H

    G -. stands in for .-> CS
    R -. stands in for .-> ASH
    S -. stands in for .-> ASM
    SB -. stands in for .-> ASC
    TH -. stands in for .-> AST
    KN -. stands in for .-> SEARCH
    SUM -. stands in for .-> AOAI
    WF -. stands in for .-> COSMOS
    H -. stands in for .-> RIE

    G --> WF
    S --> WF
    H --> WF

    classDef person fill:#08427b,stroke:#052e56,color:#fff
    classDef seam fill:#1168bd,stroke:#0b4884,color:#fff
    classDef azure fill:#0f6cbd,stroke:#0a4d87,color:#fff
    class IN,APPR person
    class G,R,S,SB,TH,KN,SUM,WF,H seam
    class CS,ASH,ASM,ASC,AST,SEARCH,AOAI,COSMOS,RIE azure
```

_Component view of the orchestration service: each L1–L7 local seam module (grouped by lesson) is shown with its exact signature and responsibility, wired into the request flow (guard -> route -> supervise/sandbox/memory/HITL over a durable workflow) and mapped by a dashed 'stands in for' edge to the Azure service it will later be swapped for._


## Message sequence diagrams

### /chat request lifecycle (guard → agent tool-loop → trace)

```mermaid
sequenceDiagram
    autonumber
    actor U as User / UI
    participant API as FastAPI API (ACA)
    participant MW as Agent Framework middleware
    participant CS as Content Safety (Prompt Shields)
    participant AS as Agent Service (agents · threads · tools)
    participant AOAI as Azure OpenAI (GPT-4o/4.1)
    participant SR as Azure AI Search
    participant AI as App Insights (OpenTelemetry)

    U->>API: POST /chat {message}
    API->>MW: enter middleware (guardrails · logging · tracing)
    MW->>AI: start span (trace request)
    Note over API,CS: input guard runs inline in /chat (input-only)
    MW->>CS: guardrails.check_input(message) -> GuardrailResult
    alt result.allowed == false (BLOCK)
        CS-->>MW: allowed=false, reason
        MW->>AI: span event: guardrail.blocked
        MW-->>API: blocked
        API-->>U: 200 {reply: "Request blocked by guardrail.", guardrail: reason}
    else result.allowed == true (PASS)
        CS-->>MW: allowed=true
        MW->>AS: run(thread, message)
        loop tool-loop until no tool calls
            AS->>AOAI: chat.completions (messages + tool schema)
            AOAI-->>AS: tool_call(s)
            AS->>SR: execute tool (retrieve)
            SR-->>AS: tool result
            AS->>AOAI: chat.completions (append tool results)
            AOAI-->>AS: assistant message / final
        end
        AS-->>MW: final reply
        MW->>AI: end span (latency, tokens)
        MW-->>API: reply
        API-->>U: 200 {reply, guardrail: "passed"}
    end
```

_A /chat request flows through the inline input guard (Content Safety) before the Agent Service runs an Azure OpenAI tool-loop, with spans emitted to App Insights and an alt branch showing a guardrail BLOCK short-circuiting the agent call._

### Durable execution — crash mid-run and at-least-once resume

```mermaid
sequenceDiagram
    autonumber
    participant C as Caller
    participant W as workflow.run_durably
    participant S as SQLiteCheckpointStore (Cosmos DB)
    participant F as step fn(state)

    rect rgb(245, 233, 233)
    Note over C,S: Attempt 1 — crashes mid-run
    C->>W: run_durably(run_id, steps, store)
    W->>S: load(run_id)
    S-->>W: None (no checkpoint)
    Note over W: start = 0, state = {}
    W->>F: steps[0].fn(state)
    F-->>W: update0
    W->>S: save(Checkpoint step=0, state)
    S-->>W: ok
    W->>F: steps[1].fn(state)
    F-->>W: update1
    Note over W,S: CRASH — fn(1) ran, but save(step=1) not yet written
    W--xS: save(step=1) never happens
    end

    rect rgb(233, 245, 235)
    Note over C,S: Attempt 2 — restart with same run_id
    C->>W: run_durably(run_id, steps, store)
    W->>S: load(run_id)
    S-->>W: Checkpoint(step=0, state)
    Note over W: start = cp.step + 1 = 1 (resume after last completed)
    W->>F: steps[1].fn(state) RE-RUN
    Note right of F: at-least-once — step 1 executes AGAIN (not exactly-once)
    F-->>W: update1
    W->>S: save(Checkpoint step=1, state)
    W->>F: steps[2].fn(state)
    F-->>W: update2
    W->>S: save(Checkpoint step=2, state)
    W-->>C: final state
    end
```

_run_durably saves a checkpoint after each step; a crash between fn(1) and its save leaves step 1 uncommitted, so the restart resumes from step.step+1 and re-runs step 1 — illustrating at-least-once, not exactly-once, execution._

### HITL — park a checkpoint, then resume with deadline-checked-first

```mermaid
sequenceDiagram
    autonumber
    participant C as Caller
    participant H as hitl (request_approval / resume)
    participant S as SQLiteCheckpointStore (Cosmos DB)
    participant A as action (sensitive · idempotent)

    Note over C,S: Park the run at the gate
    C->>H: request_approval(run_id, prompt, store, now, timeout_seconds)
    H->>S: save(Checkpoint step=0, status=awaiting_approval, requested_at=now, timeout_seconds)
    S-->>H: ok
    H-->>C: ApprovalPending(run_id, prompt)
    Note over S: durable awaiting_approval row — may idle / crash / restart

    Note over C,A: Later — a human decision arrives
    C->>H: resume(run_id, decision, store, now, action)
    H->>S: load(run_id) (must still be awaiting_approval)
    S-->>H: Checkpoint(requested_at, timeout_seconds)

    alt now - requested_at > timeout_seconds (DEADLINE checked FIRST)
        H->>S: save terminal status=timed_out, performed=false
        H-->>C: ApprovalOutcome("timed_out") — a late "yes" is void
    else decision == false (reject)
        H->>S: save terminal status=rejected, performed=false
        H-->>C: ApprovalOutcome("rejected") — action NOT performed
    else decision == true and on time (approve)
        H->>A: action(pending state)
        A-->>H: update (merged into checkpoint)
        H->>S: save terminal status=approved, performed=true
        H-->>C: ApprovalOutcome("approved") — action performed
    end
```

_request_approval persists a single awaiting_approval checkpoint and returns without acting; resume loads it and checks the deadline FIRST (a late yes times out), then handles reject vs approve, running the sensitive action only on an approved, on-time decision._

### Routing handoff — Router.route classifies then hands off with context

```mermaid
sequenceDiagram
    autonumber
    actor U as User / UI
    participant API as FastAPI API (ACA)
    participant R as orchestration.Router.route
    participant AS as Agent Service (agents · threads · tools)
    participant SP as Specialist (billing / code / research)
    participant AOAI as Azure OpenAI (GPT-4o/4.1)

    U->>API: POST /chat {message}
    API->>R: route(request)
    Note over R: case-insensitive substring scan of DEFAULT_RULES,<br/>first keyword in table order wins
    alt a keyword matches
        R-->>API: RouteDecision(specialist, matched_intent=keyword)
    else no keyword matches
        R-->>API: RouteDecision(specialist="fallback", matched_intent=None)
    end
    API->>AS: handoff to specialist (carry thread context)
    Note over API,AS: whole thread context travels with the handoff
    AS->>SP: run specialist agent with context
    SP->>AOAI: chat.completions (specialist prompt + carried context)
    AOAI-->>SP: answer
    SP-->>AS: specialist reply
    AS-->>API: reply
    API-->>U: 200 {reply}
```

_Router.route does a first-match keyword scan to produce a RouteDecision (or fallback), then the API hands the conversation off to the chosen specialist agent, carrying the full thread context along for the specialist's Azure OpenAI call._

### Supervision — parallel fan-out, fault-isolated fan-in

```mermaid
sequenceDiagram
    autonumber
    participant C as Caller
    participant SV as orchestration.Supervisor.run
    participant P as ThreadPoolExecutor (max_workers)
    participant W1 as worker (subtask 0)
    participant W2 as worker (subtask 1)
    participant W3 as worker (subtask 2)

    C->>SV: run(task)
    SV->>SV: decompose(task) -> [s0, s1, s2] (split on semicolons and newlines)
    Note over SV: pre-size results[] by index — output order = decomposition order

    par fan-out (parallel dispatch)
        SV->>P: submit(worker, s0)
        P->>W1: worker(s0)
        W1-->>P: output0
    and
        SV->>P: submit(worker, s1)
        P->>W2: worker(s1)
        W2--xP: raises Exception
    and
        SV->>P: submit(worker, s2)
        P->>W3: worker(s2)
        W3-->>P: output2
    end

    Note over SV,P: fan-in — collect each future by its original index
    P-->>SV: future0.result() -> SubResult(output0, error=None)
    Note right of SV: worker 1 raised -> ISOLATED into<br/>SubResult(output=None, error=str(exc)),<br/>one failure does NOT sink the batch
    P-->>SV: future1 -> SubResult(output=None, error=exc)
    P-->>SV: future2.result() -> SubResult(output2, error=None)
    SV-->>C: Aggregate(results in decomposition order, succeeded=2, failed=1)
```

_Supervisor.run decomposes the task, fans the subtasks out across a bounded thread pool, and fans results back in by original index — a worker that raises is isolated into its SubResult.error without sinking the batch, and output order stays independent of completion order._


## State & lifecycle diagrams

### Durable run lifecycle (workflow.run_durably + CheckpointStore)

```mermaid
---
title: Durable run lifecycle (workflow.run_durably + CheckpointStore, Cosmos DB stand-in)
---
stateDiagram-v2
    [*] --> Loading : run_durably(run_id, steps, store)

    state "Loading checkpoint" as Loading
    state "Running step i" as Running
    state "Checkpointed step i" as Checkpointed
    state "Aborted" as Aborted
    state "Done" as Done

    Loading --> Running : resume after last completed step (start = cp.step+1)
    Loading --> Aborted : CheckpointStore unavailable — load failed

    Running --> Checkpointed : fn(state) ok then store.save(Checkpoint)
    Running --> Crashed : process dies mid-step
    Running --> Aborted : CheckpointStore unavailable — save failed

    Checkpointed --> Running : more steps remain (i+1)
    Checkpointed --> Done : all steps complete then return state

    Crashed --> Loading : re-invoke same run_id (resume-after-crash)

    Done --> [*]
    Aborted --> [*]

    note right of Checkpointed
        Cosmos DB stand-in: SQLiteCheckpointStore
        upserts one row per run_id (latest checkpoint wins).
    end note
    note right of Crashed
        At-least-once, not exactly-once:
        a step whose save never landed
        is executed again on resume.
    end note
```

_Lesson 2 durable execution: run_durably checkpoints after each step so a crash resumes from cp.step+1, while a load/save failure on the CheckpointStore (Cosmos DB stand-in) aborts the run — recovery is at-least-once, not exactly-once._

### HITL approval state machine (hitl.request_approval / hitl.resume)

```mermaid
---
title: HITL approval state machine (hitl.request_approval / hitl.resume, RequestInfoExecutor stand-in)
---
stateDiagram-v2
    [*] --> Running : caller does pre-gate work

    state "Running" as Running
    state "AwaitingApproval" as AwaitingApproval
    state "Performing action" as Performing
    state "Approved" as Approved
    state "Rejected" as Rejected
    state "TimedOut" as TimedOut
    state deadline_check <<choice>>

    Running --> AwaitingApproval : request_approval writes awaiting_approval checkpoint (performed=False)

    AwaitingApproval --> deadline_check : resume(decision, now) — deadline checked FIRST
    deadline_check --> TimedOut : now minus requested_at over timeout (late yes is void)
    deadline_check --> Rejected : on time and decision is false (action NOT performed)
    deadline_check --> Performing : on time and decision is true

    Performing --> Approved : action(state) then write terminal checkpoint (performed=True)
    Performing --> AwaitingApproval : crash before terminal checkpoint (replay window)

    Approved --> [*]
    Rejected --> [*]
    TimedOut --> [*]

    note right of Performing
        At-least-once replay window: the action ran but the
        terminal save never landed, so the run is still
        awaiting_approval and re-resume replays the action.
        The sensitive action must be idempotent.
    end note
```

_Lesson 7 human-in-the-loop: request_approval parks the run as awaiting_approval, and resume checks the deadline FIRST (a late yes is void) before branching to Approved / Rejected / TimedOut — a crash between action and terminal checkpoint reopens the at-least-once replay window._

### Single agent run in the harness (input-guarded model/tool loop)

```mermaid
---
title: Single agent run in the harness (input-guarded then model/tool loop, blocked path)
---
stateDiagram-v2
    [*] --> InputGuard : POST /chat with message

    state "Input guard — inline, input-only (guardrails.check_input)" as InputGuard
    state "Blocked" as Blocked
    state "Done" as Done

    InputGuard --> Blocked : GuardrailResult.allowed=false (empty / too long / injection marker)
    InputGuard --> AgentLoop : allowed=true then forward to agent

    state "Agent loop (Azure OpenAI stand-in)" as AgentLoop {
        [*] --> Model
        state "Model turn" as Model
        state "Tool call" as Tool
        state "Tool timed out" as ToolTimeout
        state "Final message" as Final

        Model --> Tool : model requests a tool
        Model --> Final : final message with no tool call
        Tool --> Model : SandboxResult fed back
        Tool --> ToolTimeout : sandbox.run_code hard timeout (kills direct child only)
        ToolTimeout --> Model : SandboxResult timed_out=True fed back
        Final --> [*]
    }

    AgentLoop --> Done : ChatResponse(reply, guardrail=passed)
    Blocked --> Done : ChatResponse(guardrail=reason)
    Done --> [*]

    note right of InputGuard
        Runs inline in /chat before the model.
        Input-only: there is no output guard on the reply.
    end note
```

_Lesson 1 harness: /chat runs guardrails.check_input inline (input-only) before the agent; a blocked verdict short-circuits to a guardrail response, while an allowed request enters the model/tool loop where sandbox.run_code timeouts (killing only the direct child) feed a SandboxResult back until a final message ends the run._


## Class / seam diagrams

### Storage seam #1 — CheckpointStore (durable execution + HITL persistence)

```mermaid
classDiagram
    direction LR

    class CheckpointStore {
        <<Protocol>>
        +load(run_id) Checkpoint_or_None
        +save(checkpoint) None
    }
    class SQLiteCheckpointStore {
        <<Local -- SQLite file>>
        +load(run_id) Checkpoint_or_None
        +save(checkpoint) None
        +close() None
    }
    class CosmosCheckpointStore {
        <<Planned -- Cosmos DB>>
        +load(run_id) Checkpoint_or_None
        +save(checkpoint) None
    }
    class Checkpoint {
        <<dataclass>>
        +str run_id
        +int step
        +dict state
    }

    SQLiteCheckpointStore ..|> CheckpointStore : realizes (current)
    CosmosCheckpointStore ..|> CheckpointStore : realizes (planned)
    CheckpointStore ..> Checkpoint : load/save

    class run_durably {
        <<L2 -- workflow.run_durably>>
        +run_durably(run_id, steps, store) dict
    }
    class hitl {
        <<L7 -- request_approval / resume>>
        +request_approval(run_id, prompt, store, now) ApprovalPending
        +resume(run_id, decision, store, now, action) ApprovalOutcome
    }
    run_durably ..> CheckpointStore : depends on (seam)
    hitl ..> CheckpointStore : durable suspend (same seam)

    note for CheckpointStore "One Protocol, two backends.\nat-least-once: save is upsert of latest\ncheckpoint; a crash re-runs the last step."
```

_The CheckpointStore Protocol is one swap point realized by the current SQLiteCheckpointStore and a planned CosmosCheckpointStore (Cosmos DB); both L2 run_durably and L7 hitl ride the same seam, and its at-least-once upsert semantics are why a crash re-runs the last step._

### Storage seams #2 — ThreadStore + KnowledgeStore (memory)

```mermaid
classDiagram
    direction LR

    class ThreadStore {
        <<Protocol>>
        +append(thread_id, role, content) None
        +history(thread_id) list~Message~
    }
    class SQLiteThreadStore {
        <<Local -- SQLite append-only>>
        +append(thread_id, role, content) None
        +history(thread_id) list~Message~
        +close() None
    }
    class AgentServiceThreadStore {
        <<Planned -- Agent Service managed threads>>
        +append(thread_id, role, content) None
        +history(thread_id) list~Message~
    }
    class Message {
        <<dataclass>>
        +str role
        +str content
    }

    SQLiteThreadStore ..|> ThreadStore : realizes (current)
    AgentServiceThreadStore ..|> ThreadStore : realizes (planned)
    ThreadStore ..> Message : returns

    class KnowledgeStore {
        <<Protocol>>
        +add(doc_id, text) None
        +search(query, k) list~Hit~
    }
    class InMemoryKnowledgeStore {
        <<Local -- keyword overlap>>
        +add(doc_id, text) None
        +search(query, k) list~Hit~
    }
    class AzureSearchKnowledgeStore {
        <<Planned -- Azure AI Search>>
        +add(doc_id, text) None
        +search(query, k) list~Hit~
    }
    class Hit {
        <<dataclass>>
        +str doc_id
        +str text
        +float score
    }

    InMemoryKnowledgeStore ..|> KnowledgeStore : realizes (current)
    AzureSearchKnowledgeStore ..|> KnowledgeStore : realizes (planned)
    KnowledgeStore ..> Hit : returns

    class summarize_thread {
        <<L4 -- memory.summarize_thread>>
        +summarize_thread(messages, max_chars, keep) str
    }
    summarize_thread ..> Message : reads (Azure OpenAI in prod)
```

_The two L4 memory Protocols repeat the same seam pattern — ThreadStore (SQLiteThreadStore now, Agent Service managed threads planned) yields Message, KnowledgeStore (InMemoryKnowledgeStore now, Azure AI Search planned) yields Hit — while summarize_thread consumes Message history (Azure OpenAI summarization in production)._

### Behavioral seams — callables/interfaces and their result dataclasses

```mermaid
classDiagram
    direction LR

    class check_input {
        <<L1 callable -- Content Safety Prompt Shields>>
        +check_input(text) GuardrailResult
    }
    class GuardrailResult {
        <<dataclass>>
        +bool allowed
        +str reason
    }
    check_input ..> GuardrailResult : returns (input-only, inline in /chat)

    class run_code {
        <<L3 callable -- Agent Service Code Interpreter>>
        +run_code(code, timeout) SandboxResult
    }
    class SandboxResult {
        <<dataclass>>
        +bool ok
        +str stdout
        +str stderr
        +int exit_code
        +bool timed_out
    }
    run_code ..> SandboxResult : returns (timeout kills direct child only)

    class Router {
        <<L5 -- Agent Framework handoff/triage>>
        +route(request) RouteDecision
    }
    class RouteDecision {
        <<dataclass>>
        +str specialist
        +str matched_intent
    }
    Router ..> RouteDecision : returns

    class Supervisor {
        <<L6 -- Magentic / concurrent orchestration>>
        +decompose(task) list~str~
        +run(task) Aggregate
    }
    class Worker {
        <<seam -- Callable str to str>>
    }
    class Aggregate {
        <<dataclass>>
        +list~SubResult~ results
        +int succeeded
        +int failed
    }
    class SubResult {
        <<dataclass>>
        +str subtask
        +str output
        +str error
    }
    Supervisor ..> Aggregate : returns (decomposition order)
    Aggregate *-- SubResult : contains
    Supervisor o-- Worker : injected sub-agent

    class hitl {
        <<L7 -- RequestInfoExecutor>>
        +request_approval(...) ApprovalPending
        +resume(..., decision, action) ApprovalOutcome
    }
    class ApprovalPending {
        <<dataclass>>
        +str run_id
        +str prompt
    }
    class ApprovalOutcome {
        <<dataclass>>
        +str status
        +str detail
    }
    hitl ..> ApprovalPending : parks (awaiting_approval)
    hitl ..> ApprovalOutcome : resolves (deadline checked first)
```

_The behavioral seams as callables/interfaces mapped to their Azure counterparts and value dataclasses: check_input->GuardrailResult (Prompt Shields, input-only inline in /chat), run_code->SandboxResult (Code Interpreter, timeout kills only the direct child), Router->RouteDecision (Agent Framework triage), Supervisor->Aggregate composed of SubResult with an injected Worker (Magentic), and hitl->ApprovalPending/ApprovalOutcome (RequestInfoExecutor, deadline checked first)._


## Data model & mapping

### Persisted local schemas (checkpoints & threads)

```mermaid
erDiagram
    RUN ||--o| CHECKPOINTS : "latest row only (upsert)"
    THREAD ||--o{ MESSAGES : "append-only turns"
    RUN {
        string run_id PK "one durable workflow.run_durably run"
    }
    CHECKPOINTS {
        string run_id PK "= RUN.run_id · SQLiteCheckpointStore"
        int step "index of last COMPLETED step"
        string state "JSON snapshot of workflow state"
    }
    THREAD {
        string thread_id PK "one conversation transcript"
    }
    MESSAGES {
        int seq PK "AUTOINCREMENT insertion order"
        string thread_id FK "-> THREAD · SQLiteThreadStore"
        string role "user / assistant / system"
        string content "turn text"
    }
```

_The two persisted SQLite schemas: one checkpoints row per RUN (upsert keeps only the latest step/state), and an append-only threads table (messages.db) where each MESSAGES row is one turn of a THREAD ordered by AUTOINCREMENT seq._

### Local store to Azure counterpart mapping

```mermaid
flowchart LR
    subgraph LOCAL["Local seams (current code)"]
        direction TB
        L3["workflow.run_durably + durable.CheckpointStore [Protocol] / SQLiteCheckpointStore<br/>checkpoints table: run_id PK, step, state"]
        L2["memory.ThreadStore/SQLiteThreadStore<br/>threads table: seq PK, thread_id, role, content"]
        L1["memory.KnowledgeStore/InMemoryKnowledgeStore<br/>in-memory keyword index (not persisted)"]
    end
    subgraph AZURE["Azure managed (target)"]
        direction TB
        A3["Cosmos DB"]
        A2["Agent Service (agents · threads · tools)"]
        A1["Azure AI Search"]
    end
    L3 -->|"same Protocol · at-least-once checkpoints"| A3
    L2 -->|"same interface · managed threads"| A2
    L1 -->|"same interface · vector + semantic ranking"| A1
```

_Each local storage seam is a Protocol swap-point pairing one-to-one with its Azure counterpart: SQLite checkpoints to Cosmos DB, SQLite threads to Agent Service managed threads, and the in-memory knowledge index to Azure AI Search._


## Deployment & data flow

### Azure deployment topology — ACA-hosted harness (keyless + OTel)

```mermaid
flowchart LR
    User["User / UI"]

    subgraph ACA["Azure Container Apps · scale-to-zero"]
        direction TB
        API["FastAPI API (ACA)"]
        MW["Agent Framework middleware<br/>guardrails · logging · tracing"]
        API --> MW
    end

    subgraph Foundry["Azure AI Foundry project"]
        AGS["Agent Service (agents · threads · tools)"]
        OAI["Azure OpenAI (GPT-4o/4.1)"]
    end

    CS["Content Safety (Prompt Shields)"]
    SRCH[("Azure AI Search")]
    COS[("Cosmos DB")]
    AI["App Insights (OpenTelemetry)"]
    MI(["Managed Identity (keyless)"])

    User -->|HTTPS| API
    MW -->|input · output screen| CS
    MW -->|orchestrate · run agents| AGS
    AGS -->|reason| OAI
    AGS -->|grounding tool| SRCH
    MW -->|checkpoints · HITL state| COS

    MW -.->|OTel| AI
    AGS -.->|OTel| AI

    MI -.->|token| API
    MI -.->|token| AGS
    MI -.->|token| OAI
    MI -.->|token| CS
    MI -.->|token| COS
    MI -.->|token| SRCH

    linkStyle 7,8 stroke:#8250df,stroke-width:1.6px,stroke-dasharray:2 4
    linkStyle 9,10,11,12,13,14 stroke:#1a7f37,stroke-width:1.6px,stroke-dasharray:8 4

    classDef app fill:#dbeafe,stroke:#1d4ed8,color:#0b2447;
    classDef managed fill:#e6f4ea,stroke:#1a7f37,color:#0b2447;
    classDef store fill:#fff4e5,stroke:#b26a00,color:#3d2600;
    classDef obs fill:#f3e8ff,stroke:#8250df,color:#2a0a45;
    classDef ident fill:#fde2e4,stroke:#b4232c,color:#450a0d;
    classDef ext fill:#eef2f6,stroke:#5b6b7b,color:#1f2933;

    class API,MW app;
    class AGS,OAI,CS,SRCH managed;
    class COS store;
    class AI obs;
    class MI ident;
    class User ext;
```

_Scale-to-zero ACA hosts the FastAPI app plus Agent Framework middleware, wired to Foundry Agent Service, Azure OpenAI, Content Safety, Cosmos DB, and AI Search, with Managed Identity issuing keyless tokens (green dashed) and every hop emitting OpenTelemetry traces to App Insights (purple dotted)._

### End-to-end data flow — one guarded, memory-augmented, durable request

```mermaid
flowchart TB
    U["User / UI"]
    API["FastAPI API (ACA)"]
    MW["Agent Framework middleware<br/>guardrails · logging · tracing"]
    CS["Content Safety (Prompt Shields)"]
    GATE{"GuardrailResult<br/>allowed?"}
    WF["workflow.run_durably<br/>durable step loop"]
    COS[("Cosmos DB")]
    AGS["Agent Service (agents · threads · tools)"]
    SRCH["Azure AI Search"]
    OAI["Azure OpenAI (GPT-4o/4.1)"]
    AI["App Insights (OpenTelemetry)"]
    SEM["at-least-once on resume<br/>steps must be idempotent"]

    U -->|1 · POST /chat| API
    API --> MW
    MW -->|2 · guardrails.check_input| CS
    CS --> GATE
    GATE -->|blocked · short-circuit reply| U
    GATE -->|allowed| WF

    WF <-->|3 · CheckpointStore save before next step · load| COS
    WF -->|4 · run agent · ThreadStore history| AGS
    AGS -->|5 · KnowledgeStore.search k| SRCH
    SRCH -->|grounding hits| AGS
    AGS -->|6 · generate| OAI
    OAI -->|completion| AGS
    AGS -->|7 · summarize_thread if over budget| OAI
    AGS -->|8 · result · append turn| WF
    WF -->|9 · final checkpoint| COS
    WF -->|10 · reply| API
    API -->|11 · reply + guardrail| U

    WF -.- SEM
    MW -.->|OTel| AI
    WF -.->|OTel| AI
    AGS -.->|OTel| AI

    classDef app fill:#dbeafe,stroke:#1d4ed8,color:#0b2447;
    classDef managed fill:#e6f4ea,stroke:#1a7f37,color:#0b2447;
    classDef store fill:#fff4e5,stroke:#b26a00,color:#3d2600;
    classDef obs fill:#f3e8ff,stroke:#8250df,color:#2a0a45;
    classDef ext fill:#eef2f6,stroke:#5b6b7b,color:#1f2933;
    classDef gate fill:#fff9c4,stroke:#b59f00,color:#3d3600;
    classDef note fill:#f1f5f9,stroke:#94a3b8,color:#334155,font-style:italic;

    class API,MW,WF app;
    class AGS,OAI,CS,SRCH managed;
    class COS store;
    class AI obs;
    class U ext;
    class GATE gate;
    class SEM note;
```

_A single request flows input-first through guardrails.check_input to Content Safety (block short-circuits), then into the durable workflow.run_durably loop that checkpoints to Cosmos before each step, hydrates short-term ThreadStore history and long-term KnowledgeStore.search hits, calls Azure OpenAI (with optional summarize_thread), and returns — every hop traced to App Insights, with at-least-once idempotent semantics on resume._


---

## Editable source

- [`architecture.excalidraw`](architecture.excalidraw) — hand-drawn, draggable architecture canvas (open in excalidraw.com or the VS Code Excalidraw extension).
- Mermaid sources above are the version-controlled diagrams; edit them inline and GitHub re-renders.

