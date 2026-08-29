"""Repeatable validation for the docs & diagram pack.

Fast, dependency-free structural checks (fences, in-page anchors, Excalidraw JSON,
no HTML-escape artifacts) run always. The heavier Mermaid render check shells out
to `mmdc` and is opt-in (set HARNESS_RENDER_MERMAID=1) so the default suite stays
fast and cloud/CLI-free.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"

MD_FILES = sorted([*REPO.glob("*.md"), *DOCS.glob("*.md")])
EXCALIDRAW_FILES = sorted(DOCS.glob("*.excalidraw"))
MERMAID_DOCS = [DOCS / "diagrams.md", DOCS / "architecture.md", REPO / "README.md"]


def gh_slug(heading: str) -> str:
    """Approximate GitHub's heading-to-anchor slugger."""
    s = heading.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    return s.replace(" ", "-")


@pytest.mark.parametrize("path", MD_FILES, ids=lambda p: p.name)
def test_code_fences_balanced(path):
    n = len(re.findall(r"^```", path.read_text(), re.M))
    assert n % 2 == 0, f"unbalanced ``` fences in {path.name} ({n} found)"


@pytest.mark.parametrize("path", MD_FILES, ids=lambda p: p.name)
def test_in_page_anchors_resolve(path):
    text = path.read_text()
    headings = {gh_slug(h) for h in re.findall(r"^#{2,6}\s+(.+)$", text, re.M)}
    links = re.findall(r"\]\(#([\w-]+)\)", text)
    broken = sorted(set(l for l in links if l not in headings))
    assert not broken, f"broken in-page anchors in {path.name}: {broken}"


def test_diagrams_md_has_no_html_escape_artifacts():
    # After HTML-unescaping, Mermaid must use <, >, & — not &lt;/&gt;/&amp; which
    # would render as literal text on GitHub.
    text = (DOCS / "diagrams.md").read_text()
    for artifact in ("&lt;", "&gt;", "&amp;"):
        assert artifact not in text, f"residual {artifact!r} in diagrams.md"


@pytest.mark.parametrize("path", EXCALIDRAW_FILES, ids=lambda p: p.name)
def test_excalidraw_is_valid(path):
    doc = json.loads(path.read_text())  # raises on malformed JSON
    assert doc["type"] == "excalidraw"
    assert doc["version"] == 2
    assert isinstance(doc["elements"], list) and doc["elements"], "no elements"
    required = {"id", "type", "x", "y", "width", "height", "seed",
                "version", "versionNonce", "isDeleted"}
    for el in doc["elements"]:
        missing = required - el.keys()
        assert not missing, f"{path.name}: element {el.get('id')} missing {missing}"


@pytest.mark.skipif(
    shutil.which("mmdc") is None or os.environ.get("HARNESS_RENDER_MERMAID") != "1",
    reason="opt-in: set HARNESS_RENDER_MERMAID=1 with mermaid-cli (mmdc) installed",
)
@pytest.mark.parametrize("path", MERMAID_DOCS, ids=lambda p: p.name)
def test_mermaid_blocks_render(path, tmp_path):
    blocks = re.findall(r"```mermaid\n(.*?)```", path.read_text(), re.S)
    assert blocks, f"no mermaid blocks found in {path.name}"
    for i, block in enumerate(blocks):
        src = tmp_path / f"{path.stem}_{i}.mmd"
        src.write_text(block)
        result = subprocess.run(
            ["mmdc", "-i", str(src), "-o", str(tmp_path / f"{path.stem}_{i}.svg")],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, (
            f"{path.name} mermaid block {i} failed to render:\n{result.stderr[:400]}"
        )
