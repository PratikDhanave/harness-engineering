"""The generated live-demo payload is a shipped artifact — test it like one.

`scripts/build_live_demo.py` produces `live-payload.js`, which the deck loads to
run real `src/harness/` modules in the browser. Three failure modes here are
silent — the page renders, the buttons simply do nothing, and no console error
is raised:

1. A slide declares `data-demo="x"` with no snippet `x` in the payload.
2. The payload stops being a valid JS object literal.
3. A `{placeholder}` survives into a shipped snippet, so the browser prints it
   literally while the build-time transcript looks perfect.

All three have happened. These tests are cheap, need no network and no browser,
and they run in CI alongside everything else.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

PRES = Path(__file__).resolve().parent.parent / "docs" / "presentation"
PAYLOAD = PRES / "live-payload.js"
SLIDE_JS = PRES / "slide.js"

pytestmark = pytest.mark.skipif(
    not PAYLOAD.exists() or not SLIDE_JS.exists(),
    reason="presentation assets not present",
)


def load_payload() -> dict:
    text = PAYLOAD.read_text()
    m = re.search(r"window\.LIVE_PAYLOAD\s*=\s*(\{.*\});\s*$", text, re.S)
    assert m, "payload is not a `window.LIVE_PAYLOAD = {...};` assignment"
    # strict=False: transcripts legitimately contain control characters.
    return json.loads(m.group(1), strict=False)


def declared_demos() -> set[str]:
    return set(re.findall(r'data-demo="([a-z-]+)"', SLIDE_JS.read_text()))


def test_payload_is_a_valid_object_literal() -> None:
    assert isinstance(load_payload(), dict)


def test_every_slide_panel_has_a_snippet() -> None:
    """A panel with no snippet renders a button that does nothing, silently."""
    p = load_payload()
    snippets = set(p["snippets"])
    missing = sorted(d for d in declared_demos() if d not in snippets and d != "crash")
    assert not missing, f"slides declare {missing} with no snippet in the payload"


def test_crash_panel_has_both_phases() -> None:
    """`crash` is special: one marker, two snippets separated by a page reload."""
    p = load_payload()
    if "crash" in declared_demos():
        assert "crash-start" in p["snippets"]
        assert "crash-resume" in p["snippets"]
        assert p.get("crashKey"), "live.js needs crashKey to find the checkpoint"


def test_every_snippet_has_a_captured_transcript() -> None:
    """Without a fallback the panel has nothing to replay when Pyodide is down."""
    p = load_payload()
    fallbacks = set(p["fallbacks"])
    for name in p["snippets"]:
        if name == "guard":
            assert any(k.startswith("guard:") for k in fallbacks)
        else:
            assert name in fallbacks, f"snippet {name!r} has no captured transcript"


def test_no_transcript_records_a_build_time_failure() -> None:
    p = load_payload()
    broken = [k for k, v in p["fallbacks"].items() if "capture failed" in v]
    assert not broken, f"transcripts captured a failure: {broken}"


def test_guard_snippet_is_browser_ready() -> None:
    """Doubled braces or a lost placeholder only break in the browser."""
    guard = load_payload()["snippets"]["guard"]
    assert "{{" not in guard and "}}" not in guard
    assert "{msg}" in guard, "live.js substitutes {msg}; it must survive the build"


def test_inlined_modules_match_the_repo() -> None:
    """The payload ships copies of src/harness/. Drift means the deck lies."""
    src = Path(__file__).resolve().parent.parent / "src"
    for rel, shipped in load_payload()["files"].items():
        on_disk = src / rel
        assert on_disk.exists(), f"payload ships {rel}, which no longer exists"
        assert shipped == on_disk.read_text(), (
            f"{rel} in live-payload.js differs from src/ — "
            "re-run scripts/build_live_demo.py"
        )
