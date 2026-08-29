"""The agent seam behind /chat: which implementation gets selected, and why.

Everything here is cloud-free and model-free: the FoundryLocalAgent tests inject
a fake framework agent, and the selection tests monkeypatch the class itself —
nothing boots a runtime or downloads a model.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from harness import agents as agents_module
from harness.agents import (
    ENV_AGENT_MODE,
    ENV_LOCAL_ENDPOINT,
    ENV_LOCAL_MODEL,
    FoundryLocalAgent,
    StubAgent,
    make_agent,
)


# --------------------------------------------------------------- selection --
def test_stub_selected_when_env_empty():
    assert isinstance(make_agent({}), StubAgent)


def test_stub_selected_when_mode_is_explicit():
    assert isinstance(make_agent({ENV_AGENT_MODE: "stub"}), StubAgent)


def test_local_mode_threads_its_settings_through(monkeypatch):
    captured: dict = {}

    class _Marker:
        def __init__(self, **kw):
            captured.update(kw)

    monkeypatch.setattr(agents_module, "FoundryLocalAgent", _Marker)
    make_agent(
        {
            ENV_AGENT_MODE: "local",
            ENV_LOCAL_ENDPOINT: "http://127.0.0.1:5273/v1",
            ENV_LOCAL_MODEL: "qwen2.5-0.5b",
        }
    )
    assert captured == {
        "endpoint": "http://127.0.0.1:5273/v1",
        "model": "qwen2.5-0.5b",
    }


def test_local_mode_defaults_to_an_sdk_managed_runtime(monkeypatch):
    captured: dict = {}

    class _Marker:
        def __init__(self, **kw):
            captured.update(kw)

    monkeypatch.setattr(agents_module, "FoundryLocalAgent", _Marker)
    make_agent({ENV_AGENT_MODE: "local"})
    # endpoint None is the signal to boot the bundled runtime in-process
    assert captured["endpoint"] is None
    assert captured["model"] == agents_module.DEFAULT_LOCAL_MODEL


def test_an_unknown_mode_fails_loudly():
    with pytest.raises(ValueError, match="unknown"):
        make_agent({ENV_AGENT_MODE: "nonsense"})


def test_azure_mode_explains_itself_rather_than_breaking_obscurely():
    """The Azure client was dropped; asking for it must say so.

    `agent-framework-azure-ai` has never shipped past 1.0.0rc6 and breaks on the
    current core. Anyone with `HARNESS_AGENT_MODE=azure` in an old .env deserves
    a sentence, not an ImportError from three layers down.
    """
    with pytest.raises(ValueError) as exc:
        make_agent({ENV_AGENT_MODE: "azure"})
    assert "no longer supported" in str(exc.value)
    assert "local" in str(exc.value)


# ------------------------------------------------------------- behaviour ---
@dataclass
class _FakeResponse:
    text: str


class _FakeFrameworkAgent:
    def __init__(self) -> None:
        self.seen: list[str] = []

    async def run(self, message: str) -> _FakeResponse:
        self.seen.append(message)
        return _FakeResponse(text=f"foundry says: {message}")


def test_stub_reply_is_deterministic():
    assert asyncio.run(StubAgent().reply("hello")) == "(stub agent) you said: hello"


def test_foundry_local_agent_delegates_to_framework_run():
    fake = _FakeFrameworkAgent()
    agent = FoundryLocalAgent(framework_agent=fake)
    assert asyncio.run(agent.reply("on-device?")) == "foundry says: on-device?"
    assert fake.seen == ["on-device?"]
    asyncio.run(agent.aclose())  # nothing was booted; must be a no-op


def test_chat_endpoint_uses_the_seam():
    from fastapi.testclient import TestClient

    from harness.app import app, get_agent

    app.dependency_overrides[get_agent] = lambda: FoundryLocalAgent(
        framework_agent=_FakeFrameworkAgent()
    )
    try:
        body = TestClient(app).post("/chat", json={"message": "hi"}).json()
    finally:
        app.dependency_overrides.clear()
    assert body == {"reply": "foundry says: hi", "guardrail": "passed"}
