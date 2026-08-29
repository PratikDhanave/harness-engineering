"""Guardrails as Agent Framework middleware (Lesson 1).

`harness.guardrails.check_input` is the policy. This is where the platform puts
it: an `AgentMiddleware` wrapped round the agent, so the check runs on the way
in and a blocked message **never reaches the model at all** — the middleware
simply does not call `call_next()`, and sets the reply itself.

That is the property worth testing, and the reason middleware is the right
place for this rather than an `if` at the top of your endpoint: every path into
the agent goes through the pipeline, including the ones you add later and
forget about.

`EchoChatClient` exists so all of this runs with no cloud, no key and no
network — the workshop's whole first lesson is exercisable offline, and the
suite stays cloud-free.

State the leak: `check_input` is a heuristic stand-in for Content Safety Prompt
Shields (see `harness/safety/`), and this middleware only guards the way IN.
Output filtering is a second middleware nobody has written yet.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from agent_framework import (
    Agent,
    AgentContext,
    AgentMiddleware,
    AgentResponse,
    BaseChatClient,
    ChatResponse,
    Message,
)

from harness.guardrails import check_input

BLOCKED_PREFIX = "I can't help with that"


class EchoChatClient(BaseChatClient):
    """A chat client that answers without a model. Cloud-free by construction.

    It records what it was asked, so a test can assert the thing that matters:
    that a blocked message never got this far.
    """

    def __init__(self) -> None:
        super().__init__()
        self.seen: list[str] = []

    async def _inner_get_response(  # type: ignore[override]
        self, *, messages: Sequence[Message], stream: bool, options: Mapping[str, Any], **kwargs: Any
    ) -> ChatResponse:
        text = " ".join(m.text for m in messages if getattr(m, "text", None))
        self.seen.append(text)
        return ChatResponse(messages=Message("assistant", [f"echo: {text}"]))


class GuardrailMiddleware(AgentMiddleware):
    """Runs the input policy before the model, and refuses in its place."""

    def __init__(self) -> None:
        self.blocked: list[str] = []

    async def process(self, context: AgentContext, call_next) -> None:
        text = " ".join(
            m.text for m in (context.messages or []) if getattr(m, "text", None)
        )
        verdict = check_input(text)
        if not verdict.allowed:
            self.blocked.append(verdict.reason or "blocked")
            context.result = AgentResponse(
                messages=Message("assistant", [f"{BLOCKED_PREFIX} — {verdict.reason}"])
            )
            return  # call_next is NOT called: the model never sees this
        await call_next()


def build_guarded_agent(chat_client: BaseChatClient | None = None) -> tuple[Agent, EchoChatClient, GuardrailMiddleware]:
    """An Agent with the guardrail in its middleware pipeline."""
    client = chat_client or EchoChatClient()
    guard = GuardrailMiddleware()
    agent = Agent(
        client,
        "You are the harness demo agent. Answer briefly.",
        middleware=[guard],
    )
    return agent, client, guard
