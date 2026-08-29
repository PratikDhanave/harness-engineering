"""FastAPI orchestration API — Lesson 1: the agent harness.

This is the thin API layer that drives the agent behind /chat through the
`harness.agents` seam: a real Microsoft Agent Framework agent over Foundry Local
when `HARNESS_AGENT_MODE=local`, or the deterministic local stub otherwise — so
the harness runs end-to-end with no cloud either way. The pattern being learned is unchanged: context +
tools + GUARDRAILS wrapped as middleware around the model.

Run locally:  uv run uvicorn harness.app:app --reload
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from harness.agents import ReplyAgent, make_agent
from harness.guardrails import check_input

logger = logging.getLogger("harness")


@lru_cache(maxsize=1)
def get_agent() -> ReplyAgent:
    """Build the process's reply agent lazily, on first /chat.

    Importing this module must never touch Azure: a shell that happens to have
    the Foundry env vars set should not construct credentials or clients at
    import (or during test collection). Tests override this dependency via
    `app.dependency_overrides[get_agent]`.
    """
    return make_agent()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    if get_agent.cache_info().currsize:  # only if a /chat ever built one
        await get_agent().aclose()


app = FastAPI(title="Harness Engineering API", version="0.1.0", lifespan=lifespan)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    guardrail: str


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe — used by Azure Container Apps and local smoke checks."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest, agent: Annotated[ReplyAgent, Depends(get_agent)]
) -> ChatResponse:
    # --- input guardrail (local stand-in for Content Safety Prompt Shields) ---
    result = check_input(req.message)
    logger.info("guardrail: allowed=%s reason=%s", result.allowed, result.reason)
    if not result.allowed:
        return ChatResponse(
            reply="Request blocked by guardrail.",
            guardrail=result.reason or "blocked",
        )

    # --- agent call (via the harness.agents seam: Foundry when configured) ---
    reply = await agent.reply(req.message)
    return ChatResponse(reply=reply, guardrail="passed")
