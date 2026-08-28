# Requirements

What you need on a machine to run this repo. Everything was verified on the
versions below, not copied from a template.

## The short version

**Two things to install: `git` and `uv`.** That is the whole list. `uv` fetches
its own Python and every dependency, including the on-device model runtime.

```bash
git clone <repo> && cd harness-engineering

./scripts/install.sh          # macOS / Linux
.\scripts\install.ps1         # Windows
```

That installs `uv` if you do not have it, provisions Python, installs
everything, and runs the tests. Safe to re-run.

Once, before a workshop rather than during one, to avoid a 2-3 GB wait on the
first `/chat`:

```bash
uv run python3 scripts/prefetch_model.py
```

No Azure. No API key. No account. No Docker. Nothing runs in the cloud.

## Prerequisites

| | Version | Why | Check |
|---|---|---|---|
| **git** | any | clone the repo | `git --version` |
| **uv** | ≥ 0.5 | provisions Python + all deps | `uv --version` |

Install `uv`: `curl -LsSf https://astral.sh/uv/install.sh \| sh` (macOS/Linux) or
`powershell -c "irm https://astral.sh/uv/install.ps1 \| iex"` (Windows).

**You do not install Python yourself.** The project needs **≥ 3.11** and `uv`
downloads a matching interpreter — which matters, because the system Python on
macOS is often 3.9 and would fail. CI runs the same way on 3.11.

## What gets installed for you

Declared in `pyproject.toml`; `uv sync` resolves them.

| Package | Role |
|---|---|
| `agent-framework-core` ≥1.15 | the Agent Framework: workflows, checkpointing, middleware, sessions, edge groups |
| `agent-framework-openai` ≥1.14 | the chat client that talks to the local model |
| `agent-framework-orchestrations` ≥1.1 | handoff / concurrent / Magentic builders |
| `foundry-local-sdk` ==1.2.4 | **the on-device model runtime** — pulls `foundry-local-core` and ONNX Runtime as ordinary pip packages |
| `fastapi`, `uvicorn`, `pydantic` | the `/chat` HTTP layer |

`pytest` and `pytest-asyncio` come with `--extra dev`.

## Disk and network

| | |
|---|---|
| Dependencies | **~193 MB** across 46 packages — `foundry-local-core` alone is 105 MB |
| Model, first `/chat` in local mode | **~2–3 GB** for the default `phi-4-mini`, downloaded once |
| Network | needed for `uv sync` and for the model download. **Nothing else** — the tests, the demos and `af_tour.py` all run offline |

## Running the model on-device

Nothing extra to install: there is **no separate Foundry Local application and no
CLI** — the SDK boots the runtime in-process (catalog → download if needed →
load → serve), and the Agent Framework talks to it over a local
OpenAI-compatible endpoint.

```bash
cp .env.example .env
# HARNESS_AGENT_MODE=local
make run-local        # then POST http://127.0.0.1:8000/chat
```

Two things that surprise people:

- **The first `/chat` downloads the model and is slow by design.** Do it before a
  workshop, not during one.
- **Nothing auto-loads `.env`.** Only `--env-file .env` does, which `make run-local`
  passes for you. Set the variable by hand and you must export it yourself.

Set `FOUNDRY_LOCAL_ENDPOINT` only if you are pointing at a Foundry Local server
you run yourself; then the SDK does no lifecycle management at all.

## Platforms

The ONNX Runtime dependency resolves per platform — CUDA builds on Linux x86_64,
plain builds on Linux aarch64, and the core build on macOS and Windows. Verified
here on **macOS (Apple silicon), Python 3.13.14**. CI runs Linux on Python 3.11.

## Optional, only for rebuilding the slides

Not needed to run the code:

- **Google Chrome** — renders the deck to PDF
- **`python-pptx`** — pulled in on demand by `uv run --with python-pptx …`
- **`poppler`** (`pdfinfo`, `pdftoppm`) — used to verify no slide is clipped
