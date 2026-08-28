#!/usr/bin/env python3
"""Author-time generator for three flow diagrams in the deck.

`loop()` draws the agent loop with both its exits, `event()` draws an event
going to the log before the listeners, and `kitchen()` draws the kitchen
analogy as a labelled room.

Like `build_pattern_diagrams.py`, this is **author-time only** — it prints SVG
that gets pasted INLINE into `docs/presentation/slide.js`. Nothing calls it
during a build, because slide.js has to stay a literal source that
`deck_to_pptx.py` and `build_web_talk.py` can read as plain text.

    uv run python3 scripts/build_flow_diagrams.py out.json
"""
import json, sys

FONT = "<style>text{font-family:'Google Sans','Product Sans',Roboto,system-ui,sans-serif}</style>"
ACCENT, TINT = "#4285f4", "#e8f0fe"
GOOD, GOOD_BG, GOOD_BD = "#188038", "#e6f4ea", "#ceead6"
WARN, WARN_BG, WARN_BD = "#b06000", "#fef7e0", "#f9ab00"
INK, MUTED, LINE = "#202124", "#5f6368", "#dadce0"


def mk(name, colour=MUTED):
    return (f'<marker id="{name}" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" '
            f'markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" '
            f'fill="{colour}"/></marker>')


def box(x, y, w, h, title, sub="", fill="#ffffff", stroke=LINE, ts=16, rx=11):
    s = (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
         f'stroke="{stroke}" stroke-width="1.7"/>')
    cy = y + h / 2 - (9 if sub else -6)
    s += (f'<text x="{x + w / 2:.0f}" y="{cy + 6:.0f}" text-anchor="middle" font-size="{ts}" '
          f'font-weight="600" fill="{INK}">{title}</text>')
    if sub:
        s += (f'<text x="{x + w / 2:.0f}" y="{y + h / 2 + 16:.0f}" text-anchor="middle" '
              f'font-size="12.5" fill="{MUTED}">{sub}</text>')
    return s


def line(x1, y1, x2, y2, m="a", colour=MUTED, dash=False, w=1.8):
    d = ' stroke-dasharray="6 4"' if dash else ""
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{colour}" '
            f'stroke-width="{w}"{d} marker-end="url(#{m})"/>')


def label(x, y, t, size=13, colour=INK, anchor="middle", weight="400"):
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" '
            f'font-weight="{weight}" fill="{colour}">{t}</text>')


# ---------------------------------------------------------------- the loop --
def loop():
    d = [f'<defs>{mk("la")}{mk("lg", GOOD)}{mk("lw", WARN)}</defs>']
    d.append(box(40, 96, 250, 92, "The model", "decides what to do next", TINT, ACCENT))
    d.append(box(430, 96, 250, 92, "Your code", "runs the tool it asked for"))
    # out and back
    d.append(f'<path d="M290 122 C 350 108, 370 108, 428 118" fill="none" stroke="{MUTED}" stroke-width="1.8" marker-end="url(#la)"/>')
    d.append(label(359, 100, "&#8220;call this tool&#8221;", 13))
    d.append(f'<path d="M428 166 C 370 178, 350 178, 292 166" fill="none" stroke="{MUTED}" stroke-width="1.8" stroke-dasharray="6 4" marker-end="url(#la)"/>')
    d.append(label(359, 197, "the result goes back", 13))
    d.append(label(359, 216, "one lap = one turn", 12, MUTED))
    # good exit
    d.append(box(740, 40, 200, 74, "The answer", "no tools needed", GOOD_BG, GOOD))
    d.append(f'<path d="M680 118 C 706 96, 714 80, 738 74" fill="none" stroke="{GOOD}" stroke-width="2" marker-end="url(#lg)"/>')
    d.append(label(742, 132, "asks for nothing &#8594; done", 13, GOOD, "start", "600"))
    # bad exit
    d.append(box(740, 190, 200, 74, "Stopped", "cap hit, or it threw", WARN_BG, WARN_BD))
    d.append(f'<path d="M680 170 C 706 196, 714 214, 738 224" fill="none" stroke="{WARN}" stroke-width="2" stroke-dasharray="6 4" marker-end="url(#lw)"/>')
    d.append(label(742, 284, "out of laps &#8594; unfinished", 13, WARN, "start", "600"))
    return (f'<svg viewBox="0 0 960 300" role="img" aria-label="The agent loop: the model asks '
            f'for a tool, your code runs it, the result goes back; it leaves either with an '
            f'answer or by running out">{FONT}' + "".join(d) + "</svg>")


# ----------------------------------------------------------- an event, e2e --
def event():
    d = [f'<defs>{mk("ea")}{mk("eg", GOOD)}</defs>']
    d.append(box(14, 92, 190, 76, "Something", "happened"))
    d.append(line(204, 130, 246, 130, "ea"))
    d.append(box(248, 92, 214, 76, "1 &#183; Write it down", "numbered, in order", TINT, ACCENT))
    d.append(line(462, 130, 516, 130, "ea", GOOD, w=2.2))
    d.append(label(489, 116, "only then", 11.5, GOOD, "middle", "600"))
    d.append(box(518, 92, 186, 76, "2 &#183; Tell everyone", "", GOOD_BG, GOOD))
    for t, y in [("a screen", 8), ("the audit log", 76), ("another agent", 144)]:
        d.append(box(770, y, 176, 54, t, "", "#ffffff", LINE, ts=14))
        d.append(f'<path d="M704 130 C 734 130, 740 {y + 27}, 768 {y + 27}" fill="none" '
                 f'stroke="{MUTED}" stroke-width="1.5" marker-end="url(#ea)"/>')
    d.append(f'<rect x="14" y="216" width="932" height="46" rx="10" fill="{WARN_BG}" '
             f'stroke="{WARN_BD}" stroke-width="1.6"/>')
    d.append(label(480, 245, "Do it the other way round and a failed write leaves everyone "
                             "believing something that never happened.", 14.5, WARN, "middle", "600"))
    return (f'<svg viewBox="0 0 960 274" role="img" aria-label="An event is written to the '
            f'numbered log first, and only then sent to the listeners">{FONT}'
            + "".join(d) + "</svg>")


# ------------------------------------------------------------- the kitchen --
def kitchen():
    d = [f'<defs>{mk("ka")}</defs>']

    def station(x, y, w, h, n, title, sub):
        s = box(x, y, w, h, title, sub, TINT, ACCENT, ts=14.5)
        s += (f'<circle cx="{x + 17}" cy="{y + 17}" r="13" fill="{ACCENT}"/>'
              f'<text x="{x + 17}" y="{y + 22}" text-anchor="middle" font-size="13.5" '
              f'font-weight="700" fill="#ffffff">{n}</text>')
        return s

    d.append(box(14, 20, 170, 74, "Deliveries", "what arrives"))
    d.append(line(184, 57, 218, 57, "ka"))
    d.append(station(220, 20, 210, 74, "1", "Check the crate", "before anything is used"))
    d.append(line(430, 57, 464, 57, "ka"))
    d.append(station(466, 20, 220, 74, "5", "Which section?", "grill &#183; pastry &#183; salad"))
    d.append(line(686, 57, 720, 74, "ka"))
    d.append(station(722, 20, 224, 74, "6", "The head chef", "watches every station"))

    d.append(station(14, 122, 210, 78, "3", "Its own board", "raw chicken, own knife"))
    d.append(station(248, 122, 230, 78, "4", "The ticket rail", "and the recipe book"))
    d.append(station(502, 122, 216, 78, "2", "The order ticket", "survives a cook walking out"))
    d.append(station(742, 122, 204, 78, "7", "The pass", "nothing leaves unchecked"))

    d.append(f'<rect x="14" y="224" width="932" height="46" rx="10" fill="{GOOD_BG}" '
             f'stroke="{GOOD_BD}" stroke-width="1.6"/>')
    d.append(label(480, 253, "A professional kitchen is all seven patterns, running since long "
                             "before anyone had a model to wrap.", 14.5, GOOD, "middle", "600"))
    return (f'<svg viewBox="0 0 960 282" role="img" aria-label="A kitchen with each station '
            f'labelled by the pattern it matches">{FONT}' + "".join(d) + "</svg>")


if __name__ == "__main__":
    json.dump({"loop": loop(), "event": event(), "kitchen": kitchen()}, open(sys.argv[1], "w"))
    print("wrote", sys.argv[1])
