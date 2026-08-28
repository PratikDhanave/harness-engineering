"""Suite-wide isolation: the tests must be deterministic on ANY machine.

A developer shell that exports the Foundry env vars must not flip the suite
onto a real on-device model — clear them for every test, and reset the app's
cached agent so no test inherits another's selection.
"""
from __future__ import annotations

import pytest

from harness.agents import ENV_AGENT_MODE, ENV_LOCAL_ENDPOINT, ENV_LOCAL_MODEL
from harness.app import get_agent


@pytest.fixture(autouse=True)
def _cloud_free(monkeypatch):
    for var in (ENV_AGENT_MODE, ENV_LOCAL_ENDPOINT, ENV_LOCAL_MODEL):
        monkeypatch.delenv(var, raising=False)
    get_agent.cache_clear()
    yield
    get_agent.cache_clear()
