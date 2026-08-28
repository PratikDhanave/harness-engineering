#!/usr/bin/env python3
"""Author-time generator for the deck's seven before/after pattern pictures.

Each one is a "you are here" strip of all seven patterns over a matched pair of
panels: the same situation without the pattern and with it. `big_map()` draws
the whole system on one slide; the strip is that map, compressed.

**This does not run at build time, and nothing calls it automatically.** It
prints SVG that is pasted INLINE into `docs/presentation/slide.js`, because
slide.js has to stay a single literal source that `deck_to_pptx.py` and
`build_web_talk.py` can both read as plain text — a `${...}` in a slide would
reach them unexpanded.

So: edit the wording below, run this, and paste the result over the matching
`<svg>` in slide.js. Do not expect a rebuild to pick up a change made here.

    uv run python3 scripts/build_pattern_diagrams.py out.json

Colours are the Google palette by hex, matching the deck's other diagrams;
`deck_to_pptx.py --theme=clearroute` remaps them for the .pptx via its
`svg_map`. The ClearRoute *browser* deck does not remap them, so these read
blue there — same as every other diagram in the deck.
"""

FONT = "<style>text{font-family:'Google Sans','Product Sans',Roboto,system-ui,sans-serif}</style>"

# The seven, in the order the deck teaches them, with the one-word verb a
# student can hold in their head.
STEPS = ["1 Check", "2 Survive", "3 Isolate", "4 Remember", "5 Route", "6 Split up", "7 Ask"]

ACCENT, ACCENT_DK = "#4285f4", "#1a73e8"
GOOD, GOOD_BG, GOOD_BD = "#188038", "#e6f4ea", "#ceead6"
WARN, WARN_BG, WARN_BD = "#b06000", "#fef7e0", "#f9ab00"
INK, MUTED, LINE = "#202124", "#5f6368", "#dadce0"
TINT = "#e8f0fe"


def strip(active: int) -> str:
    """The 'you are here' band: the same seven chips on every pattern slide."""
    out = []
    w, gap = 124, 12
    x0 = 10
    for i, label in enumerate(STEPS):
        x = x0 + i * (w + gap)
        on = (i + 1) == active
        fill = ACCENT if on else "#ffffff"
        stroke = ACCENT if on else LINE
        colour = "#ffffff" if on else MUTED
        weight = "600" if on else "500"
        out.append(
            f'<rect x="{x}" y="0" width="{w}" height="30" rx="8" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="1.4"/>'
            f'<text x="{x + w / 2:.0f}" y="20" text-anchor="middle" font-size="13.5" '
            f'font-weight="{weight}" fill="{colour}">{label}</text>'
        )
    return "".join(out)


def _panel(n: int, side: str, x: int, heading: str, rows: list[str], outcome: str) -> str:
    """One half of a before/after picture: a heading, stacked steps, a verdict."""
    bad = side == "bad"
    bg, bd = (WARN_BG, WARN_BD) if bad else (GOOD_BG, GOOD_BD)
    key = WARN if bad else GOOD
    arrow = f"p{n}{'b' if bad else 'g'}"
    out = [
        f'<rect x="{x}" y="46" width="452" height="252" rx="12" fill="{bg}" '
        f'stroke="{bd}" stroke-width="1.6"/>',
        f'<text x="{x + 22}" y="74" font-size="16" font-weight="600" fill="{key}">{heading}</text>',
    ]
    # Three rows is the norm; four is supported so the memory slide can show all
    # four kinds a harness handles. Both fill the same 252-high panel.
    n = len(rows)
    h, gap = (40, 16) if n <= 3 else (34, 10)
    top = 90 if n <= 3 else 84
    ys = [top + i * (h + gap) for i in range(n)]
    for i, row in enumerate(rows):
        y = ys[i]
        out.append(
            f'<rect x="{x + 24}" y="{y}" width="404" height="{h}" rx="9" fill="#ffffff" '
            f'stroke="{bd}" stroke-width="1.3"/>'
            f'<text x="{x + 226}" y="{y + h / 2 + 5.5:.0f}" text-anchor="middle" '
            f'font-size="{15.5 if n <= 3 else 14}" fill="{INK}">{row}</text>'
        )
        if i < n - 1:
            out.append(
                f'<line x1="{x + 226}" y1="{y + h}" x2="{x + 226}" y2="{y + h + gap - 2}" '
                f'stroke="{key}" stroke-width="1.6" marker-end="url(#{arrow})"/>'
            )
    out.append(
        f'<text x="{x + 226}" y="{278}" text-anchor="middle" font-size="16" '
        f'font-weight="600" fill="{key}">{outcome}</text>'
    )
    return "".join(out)


def pattern(n: int, bad_rows, bad_out, good_rows, good_out, label: str) -> str:
    """Full pattern picture: the 'you are here' strip over a before/after pair."""
    defs = (
        f'<defs>'
        f'<marker id="p{n}b" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="6" '
        f'markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{WARN}"/></marker>'
        f'<marker id="p{n}g" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="6" '
        f'markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{GOOD}"/></marker>'
        f'</defs>'
    )
    return (
        f'<svg viewBox="0 0 960 306" role="img" aria-label="{label}">{FONT}{defs}'
        + strip(n)
        + _panel(n, "bad", 10, "Without it", bad_rows, bad_out)
        + _panel(n, "good", 498, "With it", good_rows, good_out)
        + "</svg>"
    )


PATTERNS = {
    1: dict(
        label="Without a check the model obeys hostile text; with one the model is never called",
        bad_rows=["Someone types: ignore your instructions",
                  "Straight to the model",
                  "The model does what the text said"],
        bad_out="You find out from the transcript",
        good_rows=["Someone types: ignore your instructions",
                   "Read it first — does this look like an attack?",
                   "Blocked. The model is never called"],
        good_out="Nothing reached the model",
    ),
    2: dict(
        label="Without save points a crash restarts the job; with them it carries on",
        bad_rows=["Step 1 done · Step 2 done", "Step 3 crashes", "Start again from step 1"],
        bad_out="The first two steps are paid for twice",
        good_rows=["Step 1 done · Step 2 done — both saved",
                   "Step 3 crashes",
                   "Come back, read the save, run step 3"],
        good_out="The work was remembered, not redone",
    ),
    3: dict(
        label="Without isolation model-written code runs in your app; with it the code is boxed and timed",
        bad_rows=["The model writes some code",
                  "Your app runs it, in your app",
                  "It loops forever, or reads your files"],
        bad_out="Its reach is your reach",
        good_rows=["The model writes some code",
                   "Run it somewhere else, with a stopwatch",
                   "Out of time — stopped, nothing else touched"],
        good_out="Its reach is the box",
    ),
    4: dict(
        label="Without memory every message starts from nothing; with it the agent keeps three kinds",
        bad_rows=["I bought this last Tuesday", "Which order do you mean?", "The one I just told you about"],
        bad_out="Every message starts from nothing",
        good_rows=["Short-term — what we just said",
                   "Long-term — what it learned before",
                   "Scratch pad — working notes, this task only",
                   "Facts — what the company knows"],
        good_out="Four kinds, four lifetimes",
    ),
    5: dict(
        label="Without routing one agent handles everything badly; with it a sorter picks a specialist",
        bad_rows=["One agent. Every kind of question.",
                  "Its instructions grow to cover all of them",
                  "It is mediocre at all of them"],
        bad_out="A jack of all trades",
        good_rows=["Read the request. What kind is it?",
                   "Billing · Code · Research",
                   "Hand it to the one that fits"],
        good_out="Each specialist stays small and sharp",
    ),
    6: dict(
        label="Without splitting one failure loses the whole job; with it the rest still lands",
        bad_rows=["One big job, done end to end", "The middle part fails", "The whole thing fails"],
        bad_out="One bad part loses all of it",
        good_rows=["Split it into three pieces",
                   "Run them side by side",
                   "One fails — keep the other two"],
        good_out="2 done, 1 failed. You still have work",
    ),
    7: dict(
        label="Without a human gate the agent refunds on its own; with one it waits for a person",
        bad_rows=["The agent decides to refund 40 pounds",
                  "It refunds 40 pounds",
                  "You read about it afterwards"],
        bad_out="Nobody said yes",
        good_rows=["The agent wants to refund 40 pounds",
                   "It stops and saves where it got to",
                   "A person says yes — then it acts"],
        good_out="And a yes that arrives too late does not count",
    ),
}


def agent_equation() -> str:
    """LLM + harness = agent. The definition the rest of the talk rests on."""
    d = []
    def box(x, w, title, sub, key=False):
        fill, stroke = (TINT, ACCENT) if key else ("#ffffff", LINE)
        return (f'<rect x="{x}" y="40" width="{w}" height="104" rx="13" fill="{fill}" '
                f'stroke="{stroke}" stroke-width="1.8"/>'
                f'<text x="{x + w / 2:.0f}" y="82" text-anchor="middle" font-size="21" '
                f'font-weight="600" fill="{INK}">{title}</text>'
                f'<text x="{x + w / 2:.0f}" y="110" text-anchor="middle" font-size="14" '
                f'fill="{MUTED}">{sub}</text>')

    def sign(x, ch):
        return (f'<text x="{x}" y="103" text-anchor="middle" font-size="34" '
                f'font-weight="600" fill="{MUTED}">{ch}</text>')

    d.append(box(14, 250, "An LLM", "answers, then forgets"))
    d.append(sign(292, "+"))
    d.append(box(320, 280, "A harness", "the seven things in this talk"))
    d.append(sign(628, "="))
    d.append(box(656, 290, "An agent", "does real work, safely", key=True))

    # the negative case, said as plainly as the positive one
    d.append(f'<rect x="14" y="172" width="932" height="52" rx="11" fill="{WARN_BG}" '
             f'stroke="{WARN_BD}" stroke-width="1.6"/>')
    d.append(f'<text x="480" y="204" text-anchor="middle" font-size="16" fill="{WARN}">'
             f'Take the harness away and you do not have a worse agent. You have a model, '
             f'answering one question at a time.</text>')
    return (f'<svg viewBox="0 0 960 236" role="img" aria-label="An LLM plus a harness '
            f'equals an agent">{FONT}' + "".join(d) + "</svg>")


def big_map() -> str:
    """The whole system on one slide. The strip is the compact re-run of this."""
    d = []
    a = (
        '<defs><marker id="mapa" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" '
        f'markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{MUTED}"/></marker>'
        '</defs>'
    )

    def box(x, y, w, h, title, sub="", key=False, rx=11):
        fill, stroke = (TINT, ACCENT) if key else ("#ffffff", LINE)
        s = (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
             f'stroke="{stroke}" stroke-width="1.6"/>')
        ty = y + h / 2 - 2 if sub else y + h / 2 + 6
        s += (f'<text x="{x + w / 2:.0f}" y="{ty:.0f}" text-anchor="middle" font-size="15" '
              f'fill="{INK}">{title}</text>')
        if sub:
            s += (f'<text x="{x + w / 2:.0f}" y="{y + h / 2 + 17:.0f}" text-anchor="middle" '
                  f'font-size="12" fill="{MUTED}">{sub}</text>')
        return s

    def arr(x1, y1, x2, y2, dash=False):
        da = ' stroke-dasharray="6 4"' if dash else ""
        return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{MUTED}" '
                f'stroke-width="1.6"{da} marker-end="url(#mapa)"/>')

    # top band — the request's journey in
    d.append(box(14, 18, 132, 46, "A request"))
    d.append(arr(146, 41, 186, 41))
    d.append(box(188, 18, 176, 46, "1 · Check it", key=True))
    d.append(arr(364, 41, 404, 41))
    d.append(box(406, 18, 176, 46, "5 · Route it", key=True))
    d.append(arr(582, 41, 622, 41))
    d.append(box(624, 18, 200, 46, "6 · Split it up", key=True))
    d.append(arr(724, 64, 620, 122))

    # middle band — the agent, flanked by memory and the sandbox
    d.append(box(14, 122, 216, 96, "4 · Remember", "recent · facts · summary", key=True))
    d.append(box(262, 122, 356, 96, "The agent", "the model, plus its tools"))
    d.append(box(650, 122, 296, 96, "3 · Isolate its tools", "run code in a box, on a clock", key=True))
    d.append(arr(230, 170, 260, 170))
    d.append(arr(618, 170, 648, 170))
    d.append(arr(440, 218, 440, 252))

    # bottom band — the way out
    d.append(box(262, 254, 356, 62, "7 · Ask a person", "before anything risky", key=True))
    d.append(box(668, 254, 148, 62, "Answer"))
    d.append(arr(618, 285, 666, 285))

    # and one band underneath, because saving as you go is not a step in the
    # flow — it wraps every step above it. Dashed, to read as an enclosure.
    d.append(f'<rect x="14" y="336" width="932" height="48" rx="11" fill="#ffffff" '
             f'stroke="{ACCENT}" stroke-width="1.6" stroke-dasharray="7 5"/>')
    d.append(f'<text x="480" y="359" text-anchor="middle" font-size="15" fill="{INK}">'
             f'2 · Survive a crash</text>')
    d.append(f'<text x="480" y="376" text-anchor="middle" font-size="12" fill="{MUTED}">'
             f'wrapped around all of it — every step saved as you go, so a crash carries on '
             f'instead of starting over</text>')

    return (f'<svg viewBox="0 0 960 396" role="img" aria-label="Where each of the seven '
            f'patterns sits around an agent">{FONT}{a}' + "".join(d) + "</svg>")


if __name__ == "__main__":
    import json, sys
    out = {"map": big_map(), "eq": agent_equation()}
    for n, cfg in PATTERNS.items():
        out[f"p{n}"] = pattern(n, cfg["bad_rows"], cfg["bad_out"],
                               cfg["good_rows"], cfg["good_out"], cfg["label"])
    json.dump(out, open(sys.argv[1], "w"))
    print("wrote", sys.argv[1], {k: len(v) for k, v in out.items()})
