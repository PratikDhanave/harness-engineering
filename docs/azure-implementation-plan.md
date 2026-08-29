# Azure Implementation Plan — Harness Engineering (Managed, Python)

> A plan for building the 7 harness patterns in **pure Python** on a **managed agent platform**
> (Microsoft Agent Framework + Azure AI Foundry Agent Service).
>
> Status: the local-first implementation of all 7 patterns exists (see `src/harness/` +
> [`architecture.md`](architecture.md)). This document is the blueprint for the **Azure-managed**
> re-implementation, which is not built yet.

---

## 1. Goals & philosophy

Building a harness by hand means owning that infrastructure forever. So: **let the managed
platform supply the harness, and spend the effort on orchestration, guardrails, and
observability.** Every one of the 7 patterns still gets built — as *configuration and
orchestration* on managed primitives rather than from-scratch infrastructure.

Two layers do all the work:

| Layer | What it is | Provides |
|-------|-----------|----------|
| **Azure AI Foundry — Agent Service** | Managed agents, threads, and tools | The *agents themselves*: model calls, persisted memory (threads), sandboxed code execution, built-in tools |
| **Microsoft Agent Framework** (Python `agent-framework`) | Orchestration SDK; unified successor to Semantic Kernel + AutoGen | The *harness around agents*: middleware/guardrails, durable checkpointed workflows, multi-agent orchestration, human-in-the-loop |

> **Preview note:** Microsoft Agent Framework is in public preview and its API surface changes.
> Pin versions and re-verify against current docs before each lesson. Azure AI Foundry Agent Service
> tool availability (e.g. Code Interpreter) can vary by region and model — check region support early.

---

## 2. Azure services and their roles

| Service | Role in this project |
|---------|----------------------|
| **Azure AI Foundry** (hub + project) | The workspace that hosts models, agents, connections, and tracing |
| **Azure AI Foundry — Agent Service** | Runs agents with managed threads + tools (Code Interpreter, File Search, Function, OpenAPI, Azure AI Search grounding) |
| **Azure OpenAI** model deployment (GPT-4o / GPT-4.1) | The reasoning model, deployed inside the Foundry project |
| **Azure AI Content Safety** (Prompt Shields + content filters) | Guardrails: jailbreak / prompt-injection detection, output filtering |
| **Azure Container Apps** | Hosts *our* Python orchestration API (FastAPI) that drives the agents; scale-to-zero |
| **Azure Cosmos DB** | Custom durable state / workflow checkpoints beyond what threads persist |
| **Azure AI Search** | Long-term semantic memory / RAG, exposed to agents as a knowledge tool |
| **Azure Key Vault** | Secrets (only where keyless auth isn't possible) |
| **Microsoft Entra ID + Managed Identity** | Keyless auth from our app to Foundry/OpenAI/Cosmos (`DefaultAzureCredential`) |
| **Application Insights / Azure Monitor** | Observability — the "Harness Inspector" equivalent (OpenTelemetry traces of agent runs) |
| **Azure Static Web Apps** *(optional)* | Host a UI to watch runs, if we want the Inspector experience |

---

## 3. Reference architecture

```
        ┌────────────────────────────────────────────────────────────┐
 User ─►│  Azure Container Apps — Python API (FastAPI)                 │
  / UI  │  Microsoft Agent Framework: middleware · workflows · orch.   │
        └───────┬───────────────────────────────┬─────────────────────┘
                │                                │
      guardrails│                                │ orchestrates
                ▼                                ▼
   ┌─────────────────────┐        ┌──────────────────────────────────────┐
   │ Azure AI Content    │        │  Azure AI Foundry — Agent Service     │
   │ Safety (Prompt      │        │  • agents (triage + specialists)      │
   │ Shields)            │        │  • managed threads (memory)           │
   └─────────────────────┘        │  • tools: Code Interpreter (sandbox), │
                                   │    File Search, Function, AI Search   │
                                   └───────┬───────────────┬──────────────┘
                                           ▼               ▼
                                  ┌────────────────┐ ┌────────────────┐
                                  │ Azure OpenAI   │ │ Azure AI Search│
                                  │ (GPT-4o/4.1)   │ │ (long-term mem)│
                                  └────────────────┘ └────────────────┘

  Durable state / checkpoints ► Azure Cosmos DB
  Cross-cutting ► Entra Managed Identity (keyless) · Key Vault · App Insights + OpenTelemetry
```

---

## 4. Lesson-by-lesson build plan

Each lesson = one increment. "You build" = the code/config you write; "Azure provides" = what you get for free.

### Lesson 1 — The Agent Harness
- **Azure provides:** A `ChatAgent` backed by Agent Service; model call + tool loop handled.
- **You build:** Create the Foundry project + model deployment; define one agent with instructions and 1–2 function tools; add **Agent Framework middleware** for guardrails (call **Content Safety Prompt Shields** on input, filter output) and for logging every step.
- **Pattern learned:** context + tools + guardrails as middleware around the model.

### Lesson 2 — Durable Execution
- **Azure provides:** Threads are already persisted server-side; Agent Framework **Workflows** support **checkpointing**.
- **You build:** Wrap the agent run in an Agent Framework workflow with a **checkpoint store** (Cosmos DB or blob). Prove recovery: kill the process mid-run, restart, resume from the last checkpoint instead of restarting.
- **Pattern learned:** crash / rate-limit recovery via checkpointed state.

### Lesson 3 — Secure Sandboxing
- **Azure provides:** The Agent Service **Code Interpreter tool** — a managed, isolated sandbox with timeouts. **No sandbox infra to build.**
- **You build:** Attach the Code Interpreter tool to an agent; give it a task requiring generated code; observe isolated execution. Optionally compare with ACA Dynamic Sessions if you want a custom sandbox.
- **Pattern learned:** running untrusted, agent-generated code safely.

### Lesson 4 — Advanced Memory
- **Azure provides:** **Managed threads** (short-term conversation memory) + **File Search / Azure AI Search tool** (long-term semantic memory).
- **You build:** Persist a thread across sessions; add an Azure AI Search index as a knowledge tool; implement a summarization step (an LLM call) that rolls up long threads into a compact context.
- **Pattern learned:** context hydration from state stores + summarization.

### Lesson 5 — Orchestration (Routing & Handoffs)
- **Azure provides:** Agent Framework **handoff orchestration** pattern; Foundry **connected agents**.
- **You build:** A triage agent that routes intent to specialist agents (e.g. "billing", "code", "research") via handoff. Define the handoff rules and specialist instructions.
- **Pattern learned:** intent routing between triage and specialists.

### Lesson 6 — Hierarchical Supervision
- **Azure provides:** Agent Framework **Magentic** and **concurrent** orchestration (a manager coordinating parallel sub-agents); workflow fan-out/fan-in.
- **You build:** A supervisor that decomposes a task, dispatches sub-agents in parallel, and aggregates results.
- **Pattern learned:** supervisor-led parallel sub-agent coordination.

### Lesson 7 — Human-in-the-Loop
- **Azure provides:** Agent Framework workflow **request/response ports** (`RequestInfoExecutor`) + checkpointing to **suspend and resume**; Foundry function-tool approval gates.
- **You build:** A workflow that pauses before a sensitive action, emits an approval request, checkpoints, and resumes on human response (with a timeout). Approval UI can be a simple endpoint or **Logic Apps** (Teams/Outlook approval connector).
- **Pattern learned:** suspend/resume for extended approval workflows.

---

## 5. Cross-cutting concerns

- **Identity (keyless first):** Use **Managed Identity** + `DefaultAzureCredential`; grant the app RBAC roles on Foundry / OpenAI / Cosmos / Search. Fall back to Key Vault only where a service requires a key.
- **Observability = the Inspector:** Agent Framework emits **OpenTelemetry**. Wire it to **Application Insights**; use Foundry tracing to inspect each agent's steps, tool calls, and token usage. This replaces the course's React "Harness Inspector."
- **Infrastructure as code:** Author with **Bicep**, or bootstrap with the **Azure Developer CLI (`azd`)** for one-command provision + deploy.
- **Environments:** dev / prod resource groups; ACA scales to zero to keep dev cheap.

---

## 6. Proposed repository structure

```
harness-engineering-pratice/
├── docs/
│   └── azure-implementation-plan.md   # this file
├── infra/                             # Bicep / azd IaC
│   ├── main.bicep
│   └── modules/                       # foundry, openai, cosmos, search, aca, monitoring
├── src/
│   └── harness/
│       ├── agents/                    # agent definitions per lesson
│       ├── middleware/                # guardrails, logging (lesson 1)
│       ├── workflows/                 # durable / HITL workflows (lessons 2, 6, 7)
│       ├── orchestration/             # routing / handoff / supervision (lessons 5, 6)
│       ├── memory/                    # threads + search + summarization (lesson 4)
│       └── app.py                     # FastAPI entrypoint
├── lessons/
│   └── 01..07/                        # notes + runnable example per lesson
├── pyproject.toml                     # deps: agent-framework, azure-ai-*, azure-identity, fastapi
└── .env.example                       # non-secret config (endpoints, deployment names)
```

---

## 7. Provisioning checklist (high level, no IaC yet)

1. Create an **Azure AI Foundry** hub + project.
2. Deploy a **GPT-4o / GPT-4.1** model in the project.
3. Enable **Agent Service**; confirm **Code Interpreter** tool availability in your region.
4. Create **Azure AI Content Safety**, **Cosmos DB**, and **Azure AI Search** resources.
5. Create the **Container Apps** environment + **App Insights**.
6. Assign **Managed Identity** RBAC roles across the above (keyless).
7. Capture endpoints + deployment names into `.env.example`.

---

## 8. Open decisions (revisit before coding)

- **UI or headless?** Skip a UI and rely on Foundry tracing + App Insights, or build a small Static Web App inspector?
- **Checkpoint store for durable/HITL:** Cosmos DB vs. blob vs. Redis — decide in Lesson 2.
- **Long-term memory backend:** Azure AI Search vs. Cosmos DB vector vs. pgvector — decide in Lesson 4.
- **Repo language note:** this repo sits under a Go `GOPATH` path, but is built in **Python** (`CLAUDE.md` reflects this).
