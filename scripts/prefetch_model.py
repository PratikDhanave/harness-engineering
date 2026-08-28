#!/usr/bin/env python3
"""Download and load the on-device model now, instead of on the first /chat.

Same code path `HARNESS_AGENT_MODE=local` takes — catalog, download if needed,
load, serve — so afterwards the first real request is instant. Run it before a
workshop rather than during one.

    uv run python3 scripts/prefetch_model.py [model-alias]
"""
from __future__ import annotations

import os
import sys

from harness.agents import DEFAULT_LOCAL_MODEL, ENV_LOCAL_MODEL, _boot_foundry_local


def main() -> int:
    alias = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.environ.get(ENV_LOCAL_MODEL) or DEFAULT_LOCAL_MODEL
    )
    print(f"model: {alias}")
    print("downloading if needed — this is the slow part, once per machine ...")
    endpoint, model_id, manager = _boot_foundry_local(alias)
    print(f"ready: {model_id} serving at {endpoint}")
    try:
        manager.stop_web_service()
    except Exception:  # nothing to clean up if it never started one
        pass
    print("cached. `make run-local` will now answer straight away.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
