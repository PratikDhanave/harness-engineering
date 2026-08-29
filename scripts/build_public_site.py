#!/usr/bin/env python3
"""Assemble `public/` — exactly what gets published, and nothing else.

`docs/presentation/` is a working directory: it holds the decks, both .pptx
builds, the archify diagram triplets, and `live-payload.js`, which carries an
**inlined copy of src/harness/**. Pointing a host at that folder publishes the
source code along with the slides.

So the deploy target is a bundle we assemble deliberately. Default is
slides-only: the deck, its stylesheet, its content. Nothing else.

    uv run python3 scripts/build_public_site.py                # slides only
    uv run python3 scripts/build_public_site.py --with-demos   # + live code

`--with-demos` re-enables the runnable panels, which requires publishing
`live-payload.js` — i.e. the harness source. That is a deliberate choice, not a
default, and the script says so on every run.
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PRES = REPO / "docs" / "presentation"
OUT = REPO / "public"

# The slides and what they need to render. Nothing here contains repo source.
SLIDES_ONLY = ["index.html", "slide.css", "slide.js", "robots.txt"]

# Adding these publishes src/harness/ (inlined into live-payload.js).
DEMO_EXTRAS = ["live.js", "live.css", "live-payload.js", "live-demo.html"]


def strip_notes(js: str) -> str:
    """Blank every `notes:` string in the deck source.

    slide.js carries the speaker script, and the deck engine renders it on the
    `s` key — so publishing slide.js verbatim publishes the whole speaker
    script to anyone with the URL. The notes carry internal delivery framing
    (audience-swap guidance, invariant IDs, client-room wording); this repo is
    presenter-only. Blank them rather than deleting the key, so the array shape
    and the engine's `SLIDES[cur].notes` read both still work.
    """
    return re.sub(r'notes:\s*"(?:[^"\\]|\\.)*"', 'notes: ""', js)


def strip_live_scripts(html: str) -> str:
    """Drop the live-panel wiring from a deck shell.

    live.js is written to no-op when its payload is absent, but leaving the
    tags in would 404 on every load. The deck itself is unaffected — the panels
    simply do not appear.
    """
    html = re.sub(r'\n\s*<!-- Runnable code panels.*?-->', "", html, flags=re.S)
    html = re.sub(r'\n\s*<script src="live-payload\.js"></script>', "", html)
    html = re.sub(r'\n\s*<script src="live\.js"></script>', "", html)
    html = re.sub(r'\n\s*<link rel="stylesheet" href="live\.css" />', "", html)
    return html


def main() -> int:
    with_demos = "--with-demos" in sys.argv[1:]

    # Rebuild the contents, but never blow away the deploy state. `.vercel/`
    # holds the project link and `.env.local` its OIDC token; deleting them
    # unlinks the bundle, and the next `vercel deploy` silently creates a NEW
    # project named after this folder instead of updating the real one.
    KEEP = {".vercel", ".env.local"}
    OUT.mkdir(parents=True, exist_ok=True)
    for item in OUT.iterdir():
        if item.name in KEEP:
            continue
        shutil.rmtree(item) if item.is_dir() else item.unlink()

    published: list[str] = []
    for name in SLIDES_ONLY + (DEMO_EXTRAS if with_demos else []):
        src = PRES / name
        if not src.exists():
            print(f"missing: {name}")
            return 1
        text = src.read_text()
        if name.endswith(".html") and not with_demos:
            text = strip_live_scripts(text)
        if name == "slide.js":
            text = strip_notes(text)
        (OUT / name).write_text(text)
        published.append(name)

    # Post-conditions. Both of these have already failed silently once: the
    # strip is literal-match and no-ops on any reformat, and slide.js shipped
    # the full speaker script to a public URL.
    idx = (OUT / "index.html").read_text()
    if not with_demos:
        dangling = [r for r in ("live-payload.js", "live.js", "live.css") if r in idx]
        if dangling:
            print(f"BUILD ERROR: slides-only bundle still references {dangling} — "
                  "strip_live_scripts matched nothing (index.html reformatted?)")
            return 1
    # Match a NON-empty notes string; `notes: ""` is the stripped form and must pass.
    survived = re.findall(r'notes:\s*"[^"]', (OUT / "slide.js").read_text())
    if survived:
        print(f"BUILD ERROR: {len(survived)} speaker note(s) survived into the "
              "published slide.js — they would be readable with the `s` key")
        return 1

    # Belt and braces: if the payload ever reaches the bundle by accident, say so.
    leaked = [p.name for p in OUT.iterdir() if p.name == "live-payload.js"]
    if leaked and not with_demos:
        print("BUILD ERROR: live-payload.js in a slides-only bundle")
        return 1

    # Self-deployable: `cd public && npx vercel` uploads ONLY these files.
    # Running the CLI from the repo root would upload the whole repository to
    # Vercel's build infrastructure even though just this folder is served.
    (OUT / "vercel.json").write_text(
        '{\n'
        '  "$schema": "https://openapi.vercel.sh/vercel.json",\n'
        '  "framework": null,\n'
        '  "cleanUrls": true,\n'
        '  "trailingSlash": false,\n'
        '  "headers": [\n'
        '    {\n'
        '      "source": "/(.*)",\n'
        '      "headers": [\n'
        '        { "key": "X-Robots-Tag", "value": "noindex, nofollow, noarchive, nosnippet" },\n'
        '        { "key": "Referrer-Policy", "value": "no-referrer" }\n'
        '      ]\n'
        '    }\n'
        '  ]\n'
        '}\n'
    )
    published.append("vercel.json")

    # Keep Vercel's own state out of the upload. `vercel link` drops .env.local
    # (an OIDC token) and .vercel/ into this folder; shipping them made two
    # deployments hang at status UNKNOWN for 25+ minutes on nine static files,
    # while the same bundle without them went READY in seconds.
    (OUT / ".vercelignore").write_text(
        ".vercel\n"
        ".env.local\n"
        ".gitignore\n"
    )
    published.append(".vercelignore")

    print(f"wrote {OUT.relative_to(REPO)}/  ({len(published)} files)")
    for name in published:
        print(f"  {name}")
    if with_demos:
        print("\n  NOTE: --with-demos publishes live-payload.js, which contains an")
        print("  inlined copy of src/harness/. The slides ship the source with them.")
    else:
        print("\n  Slides only. No repo source is published; the live panels are absent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
