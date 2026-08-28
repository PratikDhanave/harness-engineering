"""The agent seam (Lesson 1): who produces the assistant reply behind /chat.

`ReplyAgent` is the swap point between the FastAPI harness and the model. Two
implementations, selected by `HARNESS_AGENT_MODE`:

- `stub` → `StubAgent` — deterministic local echo, no model at all. The default,
  so the API and the whole test suite run with no runtime and no network.
- `local` → `FoundryLocalAgent` — a real Microsoft Agent Framework `Agent` over
  **Foundry Local**'s OpenAI-compatible server, so the model runs on the machine
  in front of you. With `FOUNDRY_LOCAL_ENDPOINT` set, that running server is used
  as-is; without it, the pinned `foundry-local-sdk` boots the bundled runtime
  in-process (catalog → download-if-needed → load → serve). Optional
  `FOUNDRY_LOCAL_MODEL` picks the alias (default `phi-4-mini`).

There was a third mode, `azure`, on Foundry Agent Service. It was removed on
26 Aug 2026: `agent-framework-azure-ai` has never shipped past `1.0.0rc6` and
breaks against any core newer than that, which pinned the whole stack and kept
`agent-framework-orchestrations` out of reach. Asking for it now raises and says
so, rather than failing obscurely at import.

State the leak: `StubAgent` exercises none of the real failure modes.
`FoundryLocalAgent`'s SDK-managed path downloads the model on the FIRST /chat
(one-time, ~2–3 GB for the default) — that request is slow by design; the
explicit-endpoint path does no lifecycle management at all.
"""
from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Protocol

ENV_AGENT_MODE = "HARNESS_AGENT_MODE"  # "stub" | "local" | unset
ENV_LOCAL_ENDPOINT = "FOUNDRY_LOCAL_ENDPOINT"
ENV_LOCAL_MODEL = "FOUNDRY_LOCAL_MODEL"

DEFAULT_LOCAL_MODEL = "phi-4-mini"

AGENT_NAME = "harness-chat"
AGENT_INSTRUCTIONS = (
    "You are the harness-engineering demo agent. Answer briefly and honestly; "
    "if you are unsure, say so."
)


class ReplyAgent(Protocol):
    async def reply(self, message: str) -> str: ...

    async def aclose(self) -> None: ...


class StubAgent:
    """Local stand-in: echoes the message so the harness runs end-to-end offline."""

    async def reply(self, message: str) -> str:
        return f"(stub agent) you said: {message}"

    async def aclose(self) -> None:  # nothing to release
        return None


class FoundryLocalAgent:
    """Microsoft Agent Framework agent over Foundry Local (on-device models).

    Same `Agent` on top, different chat client underneath: the pinned trio's
    `OpenAIChatClient` pointed at Foundry Local's OpenAI-compatible server.
    Two ways to get that server:

    - `endpoint` given → use it as-is (a runtime you manage yourself).
    - `endpoint` omitted → the pinned `foundry-local-sdk` (which bundles the
      runtime — no separate install) boots everything in-process: resolve the
      model alias from the catalog, download it if not cached (one-time,
      ~2–3 GB for the default), load it, and start the web service.
    """

    def __init__(
        self,
        framework_agent=None,
        *,
        endpoint: str | None = None,
        model: str = DEFAULT_LOCAL_MODEL,
    ) -> None:
        self._manager = None
        if framework_agent is None:
            from agent_framework import Agent
            from agent_framework_openai import OpenAIChatClient

            model_id = model
            if endpoint is None:
                endpoint, model_id, self._manager = _boot_foundry_local(model)
            client = OpenAIChatClient(
                model=model_id,
                base_url=endpoint,
                api_key="not-needed",  # Foundry Local ignores the key
            )
            framework_agent = Agent(
                client, instructions=AGENT_INSTRUCTIONS, name=AGENT_NAME
            )
        self._agent = framework_agent

    async def reply(self, message: str) -> str:
        response = await self._agent.run(message)
        return response.text

    async def aclose(self) -> None:
        if self._manager is not None:
            self._manager.stop_web_service()


def _boot_foundry_local(alias: str):
    """SDK-managed runtime: catalog → download-if-needed → load → web service.

    Returns (endpoint, concrete model id, manager). Synchronous and potentially
    slow on first use (model download) — called once per process from the lazy
    agent construction, never at import.
    """
    from foundry_local_sdk import Configuration, FoundryLocalManager

    FoundryLocalManager.initialize(Configuration(app_name="harness"))
    manager = FoundryLocalManager.instance
    model = manager.catalog.get_model(alias)
    if model is None:
        raise ValueError(f"Foundry Local has no model for alias {alias!r}")
    if not model.is_cached:
        model.download()
    if not model.is_loaded:
        model.load()
    manager.start_web_service()
    urls = manager.urls
    url = (urls[0] if isinstance(urls, (list, tuple)) else urls).rstrip("/")
    return (url if url.endswith("/v1") else f"{url}/v1", model.id, manager)


def make_agent(env: Mapping[str, str] = os.environ) -> ReplyAgent:
    """Build the reply agent for this process from `env` (and only `env`).

    Two modes. `stub` is the default and needs nothing; `local` is a real Agent
    Framework agent against an on-device model. An explicit mode is never
    quietly swapped for another.
    """
    mode = env.get(ENV_AGENT_MODE, "").strip().lower()

    if mode in ("", "stub"):
        return StubAgent()
    if mode == "local":
        return FoundryLocalAgent(
            endpoint=env.get(ENV_LOCAL_ENDPOINT) or None,  # None → SDK-managed
            model=env.get(ENV_LOCAL_MODEL) or DEFAULT_LOCAL_MODEL,
        )
    if mode == "azure":
        raise ValueError(
            f"{ENV_AGENT_MODE}=azure is no longer supported: the Azure Foundry "
            "client has never shipped past 1.0.0rc6 and breaks on the current "
            "core, so this repo runs on Foundry Local. Use HARNESS_AGENT_MODE=local."
        )
    raise ValueError(f"unknown {ENV_AGENT_MODE}={mode!r} — use 'stub' or 'local'")
