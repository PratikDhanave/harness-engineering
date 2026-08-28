"""The deck promises every lesson shows code AND runs. Hold it to that.

Two failure modes here are silent. A slide can lose its code sample to an export
(the print box is `overflow: hidden`, so anything too tall just is not in the
PDF — that removed four code blocks once, with no error), and a lesson can lose
its runnable panel to a refactor while the slide still claims one.

Neither needs a browser or a network to check.
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

import pytest

PRES = Path(__file__).resolve().parent.parent / "docs" / "presentation"
SLIDE_JS = PRES / "slide.js"
PPTX = PRES / "harness-engineering.pptx"

pytestmark = pytest.mark.skipif(not SLIDE_JS.exists(), reason="deck not present")

LESSONS = ("L1", "L2", "L3", "L4", "L5", "L6", "L7")


def slides() -> list[tuple[str, str]]:
    """(title, html) per slide, in deck order."""
    out = []
    for block in re.split(r"\n  \{\n    html: `", SLIDE_JS.read_text())[1:]:
        html = block.split("`,\n    notes:")[0]
        m = re.search(r"<h2>(.*?)</h2>", html, re.S)
        title = re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""
        out.append((re.sub(r"\s+", " ", title), html))
    return out


def lesson_of(title: str) -> str | None:
    m = re.match(r"(L[1-7])", title)
    return m.group(1) if m else None


def test_every_lesson_slide_shows_code() -> None:
    missing = [t for t, html in slides() if lesson_of(t) and "<pre" not in html]
    assert not missing, f"lesson slides with no code sample: {missing}"


def test_all_seven_lessons_have_a_runnable_panel() -> None:
    """Panels are per-lesson, not per-slide: L1 splits across two slides."""
    covered = {
        lesson_of(t)
        for t, html in slides()
        if lesson_of(t) and 'data-demo="' in html
    }
    assert covered == set(LESSONS), f"lessons without a panel: {sorted(set(LESSONS) - covered)}"


def test_every_panel_shows_the_code_it_runs() -> None:
    for title, html in slides():
        for m in re.finditer(r"<div data-demo=\"[a-z-]+\"([^>]*)>", html):
            assert "data-code" in m.group(1), (
                f"panel on {title!r} does not show its source; add data-code"
            )


@pytest.mark.skipif(not PPTX.exists(), reason="pptx not built")
def test_pptx_kept_every_code_sample() -> None:
    """An export that silently drops content is the failure this guards."""
    z = zipfile.ZipFile(PPTX)
    text = " ".join(
        re.sub(r"<[^>]+>", " ", z.read(n).decode("utf8"))
        for n in sorted(z.namelist())
        if n.startswith("ppt/slides/slide") and n.endswith(".xml")
    )
    text = re.sub(r"\s+", " ", text)
    for title, html in slides():
        if not lesson_of(title):
            continue
        for pre in re.findall(r"<pre[^>]*>(.*?)</pre>", html, re.S):
            body = re.sub(r"<[^>]+>", "", pre)
            # first real code line, ignoring the leading comment
            lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
            code = next((ln for ln in lines if not ln.startswith("#")), None)
            if not code:
                continue
            probe = re.sub(r"\s+", " ", code.split("#")[0].strip())[:40]
            assert probe in text, f"{title}: code sample missing from the .pptx — {probe!r}"


def test_animation_does_not_survive_into_the_handout() -> None:
    """The engine hides arrowheads with an INLINE style during the draw.

    Inline styles beat any print rule, and `marker-end: revert` reverts to the
    user-agent value (none), not to the element's own marker-end attribute — so
    the first attempt at this printed every diagram arrow as a headless line.
    Only clearing the inline styles gives the attribute back. Guard both halves.
    """
    js = SLIDE_JS.read_text(encoding="utf-8")
    assert "function finaliseFigures()" in js
    assert 'addEventListener("beforeprint", finaliseFigures)' in js
    # the media-query fallback, because headless printing may not fire beforeprint
    assert 'matchMedia("print")' in js
    for prop in ("markerEnd", "strokeDasharray", "strokeDashoffset", "opacity"):
        assert f'n.style.{prop} = ""' in js, f"finaliseFigures must clear {prop}"

    css = (PRES / "slide.css").read_text(encoding="utf-8")
    assert "marker-end: revert" not in css, "revert reverts to none; it caused the bug"
