#!/usr/bin/env python3
"""Export the quiz slides from slide.js as JSON.

    uv run python3 scripts/export_quiz.py [out.json]

slide.js stays the single source: this reads the same SLIDES array the decks
render, keeps only the multiple-choice slides, and writes them structured. Run
it again after editing a quiz and the JSON follows.

`speaker_note` is the presenter script. It is deliberately stripped from the
published web bundle, so think before putting this file somewhere public.
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

PRES = Path(__file__).resolve().parents[1] / "docs" / "presentation"
SRC = PRES / "slide.js"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else PRES / "harness-engineering-quiz.json"


def text(fragment: str) -> str:
    """Strip tags, unescape entities, collapse whitespace."""
    s = re.sub(r"<[^>]+>", "", fragment)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).replace(" ", " ").strip()


def slides() -> list[dict]:
    src = SRC.read_text()
    body = src[src.index("const SLIDES = [") :]
    body = body[body.index("[") : body.index("\n];") + 2]
    out, depth, start = [], 0, None
    for i, ch in enumerate(body):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                out.append(body[start : i + 1])
    return out


def main() -> int:
    quizzes = []
    for n, raw in enumerate(slides(), 1):
        hm = re.search(r"html:\s*`(.*?)`,\s*\n\s*notes:", raw, re.S)
        if not hm or '<ul class="quiz">' not in hm.group(1):
            continue
        h = hm.group(1)
        nm = re.search(r'notes:\s*"(.*?)"\s*$', raw.rstrip().rstrip("}").rstrip(), re.S)

        options = []
        for li, attrs in re.findall(r"<li(\s[^>]*)?>(.*?)</li>", h, re.S) and [
            (m.group(2), m.group(1) or "") for m in re.finditer(r"<li(\s[^>]*)?>(.*?)</li>", h, re.S)
        ]:
            label = text(li)
            # options are written "1 &nbsp; the answer" — split the leading number off
            m = re.match(r"^(\d+)\s+(.*)$", label)
            options.append(
                {
                    "n": int(m.group(1)) if m else len(options) + 1,
                    "text": m.group(2) if m else label,
                    "correct": 'class="right"' in attrs,
                }
            )

        quizzes.append(
            {
                "id": f"q{len(quizzes) + 1:02d}",
                "deck_slide": n,
                "title": text(re.search(r"<h2>(.*?)</h2>", h, re.S).group(1)),
                "question": text(re.search(r'<p class="lead">(.*?)</p>', h, re.S).group(1)),
                "options": options,
                "answer": next((o["n"] for o in options if o["correct"]), None),
                "explanation": text(
                    (re.search(r'<p class="small">(.*?)</p>', h, re.S) or re.match("", "")).group(1)
                )
                if re.search(r'<p class="small">(.*?)</p>', h, re.S)
                else "",
                "speaker_note": (nm.group(1) if nm else "").replace('\\"', '"'),
            }
        )

    bad = [q["id"] for q in quizzes if q["answer"] is None or len(q["options"]) < 2]
    if bad:
        print(f"BUILD ERROR: {len(bad)} quizzes without exactly one marked answer: {bad}")
        return 1

    OUT.write_text(json.dumps({"count": len(quizzes), "quizzes": quizzes}, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(Path.cwd())}  ({len(quizzes)} quizzes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
