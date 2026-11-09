#!/usr/bin/env python3
"""Render the Google-format deck (docs/presentation/slide.js) as a native .pptx.

The deck's source of truth is the `SLIDES` array in slide.js — this script parses
that array and rebuilds each slide with real PowerPoint shapes, so the .pptx is a
replica of `harness-engineering.pdf` rather than a tracing of it. Text stays
editable; the six inline-SVG diagrams are rasterised with headless Chrome and
embedded as pictures (they are artwork, not text).

Geometry matches the deck's @media print block: 13.333in x 7.5in (960x540pt),
1in side padding, 0.55in top/bottom. Palette matches slide.css :root exactly.

Usage:  uv run --with python-pptx python3 scripts/deck_to_pptx.py
Output: docs/presentation/harness-engineering.pptx
"""
from __future__ import annotations

import base64
import html as htmllib
import math
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

REPO = Path(__file__).resolve().parent.parent
PRES = REPO / "docs" / "presentation"
SLIDE_JS = PRES / "slide.js"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# Sanity floor for the JS parse. The deck only grows; fewer than this
# means slide.js broke the brace/backtick parser.
MIN_SLIDES = 15


def _installed(*names: str) -> str | None:
    """First font family actually present on this machine (PPTX has no fallback list)."""
    import glob, os
    have = set()
    for d in ("/System/Library/Fonts", "/Library/Fonts", "/System/Library/Fonts/Supplemental",
              os.path.expanduser("~/Library/Fonts")):
        for f in glob.glob(d + "/*"):
            have.add(os.path.basename(f).lower())
    for n in names:
        key = n.split()[0].lower().replace("-", "")
        if any(key in h for h in have):
            return n
    return None


# ---------------------------------------------------------------- themes ----
# Google theme = the deck's own slide.css :root.  ClearRoute theme = the house
# palette read off harness-engineering-clearroute.pptx (navy #1A202C, mint
# #00E8AF, card #2E3A4A, body #E6EAF2) at the house 1440x828pt canvas.
THEMES = {
    "google": {
        "out": "harness-engineering.pptx",
        "bg": 0xFFFFFF, "card": 0xFFFFFF, "on_accent": 0xFFFFFF,
        "ink": 0x202124, "ink_soft": 0x3C4043, "muted": 0x5F6368,
        "accent": 0x4285F4, "accent_dk": 0x1A73E8, "good": 0x188038, "warn": 0xB06000,
        "panel": 0xF1F3F4, "line": 0xE8EAED, "line2": 0xDADCE0,
        "good_bg": 0xE6F4EA, "good_bd": 0xCEEAD6, "warn_bg": 0xFEF7E0, "warn_bd": 0xFEEFC3,
        "code_c": 0x8A94A8,
        "sans": "Helvetica Neue", "mono": "Menlo",
        "w_in": 13.333, "h_in": 7.5, "pad_x": 1.0, "pad_y": 0.55, "scale": 1.0,
        "svg_bg": "#ffffff", "svg_map": {},
    },
    "clearroute": {
        "out": "harness-engineering-clearroute-talk.pptx",
        # White paper, ClearRoute mint. Mint is bright, so it fills badges/rules
        # while text and code take the deeper house green — same accent /
        # accent_dk split the Google theme makes.
        "bg": 0xFFFFFF, "card": 0xFFFFFF, "on_accent": 0xFFFFFF,
        "ink": 0x121A24, "ink_soft": 0x37414F, "muted": 0x6E788A,
        "accent": 0x009167, "accent_dk": 0x009167, "good": 0x009167, "warn": 0xB06000,
        "panel": 0xF2F7F5, "line": 0xE6EAF0, "line2": 0xD6DDE6,
        "good_bg": 0xE6FAF4, "good_bd": 0xA8EBD6, "warn_bg": 0xFEF7E0, "warn_bd": 0xFEEFC3,
        "code_c": 0x7B8794,
        # Typography matches the Google deck on purpose — only the palette is
        # ClearRoute. (Swap to "Gotham" here to use the house face instead.)
        "sans": _installed("Google Sans", "Product Sans", "Roboto", "Helvetica Neue") or "Helvetica Neue",
        "mono": _installed("Menlo", "Consolas", "Courier New") or "Courier New",
        "w_in": 13.333, "h_in": 7.5, "pad_x": 1.0, "pad_y": 0.55, "scale": 1.0,
        "svg_bg": "#ffffff",
        # The diagrams are already drawn for white paper — only the Google blues
        # move to the ClearRoute greens.
        "svg_map": {
            "#4285f4": "#009167", "#1a73e8": "#009167", "#188038": "#009167",
            "#e8f0fe": "#E6FAF4", "#e6f4ea": "#E6FAF4",
            "#c9ddfc": "#A8EBD6", "#ceead6": "#A8EBD6",
        },
    },
    "devfest": {
        "out": "harness-engineering-devfest.pptx",
        # DevFest 2026 template ("[External] DevFest 2026 - Presentation
        # Template"): Google Sans Bold headlines, Roboto Mono Light subheads,
        # Black 02 ink (#1e1e1e), the Google 500s as accents with the
        # template's pastel/halftone pairs for good/warn fills, off-white
        # (#f0f0f0) panels on white paper. Font NAMES are forced rather than
        # probed: the .pptx is destined for Google Slides, where Google Sans
        # and Roboto Mono exist even when this machine lacks them.
        "bg": 0xFFFFFF, "card": 0xFFFFFF, "on_accent": 0xFFFFFF,
        "ink": 0x1E1E1E, "ink_soft": 0x3C4043, "muted": 0x5F6368,
        "accent": 0x4285F4, "accent_dk": 0x1A73E8, "good": 0x34A853, "warn": 0xB06000,
        "panel": 0xF0F0F0, "line": 0xE8EAED, "line2": 0xDADCE0,
        "good_bg": 0xCCF6C5, "good_bd": 0x5CDB6D, "warn_bg": 0xFFE7A5, "warn_bd": 0xFFD427,
        "code_c": 0x8A94A8,
        "sans": "Google Sans", "mono": "Roboto Mono",
        "subhead_mono": True,  # DevFest subheads are Roboto Mono
        "w_in": 13.333, "h_in": 7.5, "pad_x": 1.0, "pad_y": 0.55, "scale": 1.0,
        "svg_bg": "#ffffff", "svg_map": {},
    },
}

THEME: dict = {}
OUT = PRES / "harness-engineering.pptx"
SZ: dict = {}
_BASE_SZ = {
    "h1": 63.4, "h2": 31.5, "h3": 16.5, "p": 18.0, "small": 12.75,
    "li": 18.75, "kicker": 13.5, "sub": 21.0, "meta": 13.5,
    "card_h3": 16.5, "card_p": 14.25, "tag": 11.25, "duo_h3": 15.75,
    "td": 14.25, "th": 11.7, "pre": 12.9,
}


def _c(v: int) -> RGBColor:
    return RGBColor((v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF)


def apply_theme(name: str) -> None:
    """Bind the palette/geometry globals the renderer reads."""
    global THEME, OUT, SZ
    global INK, INK_SOFT, MUTED, ACCENT, ACCENT_DK, GOOD, WARN, PANEL, LINE, LINE2
    global GOOD_BG, GOOD_BD, WARN_BG, WARN_BD, CODE_C, BG, CARD, ON_ACCENT, WHITE
    global SANS, MONO, SLIDE_W, SLIDE_H, PAD_X, PAD_Y, CONTENT_W, AVAIL_IN

    t = THEMES[name]
    THEME = t
    OUT = PRES / t["out"]
    INK, INK_SOFT, MUTED = _c(t["ink"]), _c(t["ink_soft"]), _c(t["muted"])
    ACCENT, ACCENT_DK = _c(t["accent"]), _c(t["accent_dk"])
    GOOD, WARN = _c(t["good"]), _c(t["warn"])
    PANEL, LINE, LINE2 = _c(t["panel"]), _c(t["line"] & 0xFFFFFF), _c(t["line2"])
    GOOD_BG, GOOD_BD = _c(t["good_bg"]), _c(t["good_bd"])
    WARN_BG, WARN_BD = _c(t["warn_bg"]), _c(t["warn_bd"])
    CODE_C = _c(t["code_c"])
    BG, CARD, ON_ACCENT = _c(t["bg"]), _c(t["card"]), _c(t["on_accent"])
    WHITE = BG
    SANS, MONO = t["sans"], t["mono"]
    SLIDE_W, SLIDE_H = Inches(t["w_in"]), Inches(t["h_in"])
    PAD_X, PAD_Y = Inches(t["pad_x"]), Inches(t["pad_y"])
    CONTENT_W = Inches(t["w_in"] - 2 * t["pad_x"])
    AVAIL_IN = t["h_in"] - 2 * t["pad_y"]
    SZ = {k: v * t["scale"] for k, v in _BASE_SZ.items()}


apply_theme("google")


# ------------------------------------------------------------ slide model ----
@dataclass
class Run:
    text: str
    bold: bool = False
    italic: bool = False
    mono: bool = False
    color: RGBColor | None = None
    boxed: bool = False  # inline <code> chip


@dataclass
class Block:
    kind: str
    runs: list[Run] = field(default_factory=list)
    items: list = field(default_factory=list)
    cls: str = ""
    extra: dict = field(default_factory=dict)


def _rgb(el_class: str) -> RGBColor | None:
    if "accent-2" in el_class:
        return GOOD
    if "accent" in el_class:
        return ACCENT
    return None


class Inline(HTMLParser):
    """Flatten inline markup into styled runs."""

    def __init__(self, preserve: bool = False):
        super().__init__(convert_charrefs=True)
        self.preserve = preserve
        self.runs: list[Run] = []
        self.bold = 0
        self.italic = 0
        self.mono = 0
        self.color: list[RGBColor] = []
        self.boxed = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class", "")
        if tag in ("b", "strong"):
            self.bold += 1
        elif tag in ("i", "em"):
            self.italic += 1
        elif tag == "code":
            self.mono += 1
            self.boxed += 1
            self.color.append(ACCENT_DK)
        elif tag == "span":
            if "pill" in cls:
                self.mono += 1
                self.color.append(WARN if " w" in f" {cls}" or "pill w" in cls else GOOD)
                self.bold += 1
            elif "cmd" in cls:
                self.mono += 1
                self.color.append(GOOD)
                self.bold += 1
            elif cls.strip() == "c":
                self.mono += 1
                self.color.append(CODE_C)
            elif "k" in cls.split():
                self.mono += 1
                self.color.append(ACCENT_DK)
            elif "num" in cls:
                self.mono += 1
                self.color.append(WHITE)
                self.bold += 1
            else:
                c = _rgb(cls)
                if c:
                    self.color.append(c)

    def handle_endtag(self, tag):
        if tag in ("b", "strong"):
            self.bold = max(0, self.bold - 1)
        elif tag in ("i", "em"):
            self.italic = max(0, self.italic - 1)
        elif tag == "code":
            self.mono = max(0, self.mono - 1)
            self.boxed = max(0, self.boxed - 1)
            if self.color:
                self.color.pop()
        elif tag == "span":
            if self.color:
                self.color.pop()
            self.mono = max(0, self.mono - 1)
            self.bold = max(0, self.bold - 1)

    def handle_data(self, data):
        # <pre> is whitespace-significant: keep indentation exactly as authored.
        text = data if self.preserve else re.sub(r"\s+", " ", data)
        if not text:
            return
        self.runs.append(
            Run(
                text,
                bold=self.bold > 0,
                italic=self.italic > 0,
                mono=self.mono > 0,
                color=self.color[-1] if self.color else None,
                boxed=self.boxed > 0,
            )
        )


def inline_runs(fragment: str, preserve: bool = False) -> list[Run]:
    p = Inline(preserve=preserve)
    p.feed(fragment)
    if preserve:
        return [r for r in p.runs if r.text]
    runs = [r for r in p.runs if r.text.strip() or r.text == " "]
    if runs:
        runs[0].text = runs[0].text.lstrip()
        runs[-1].text = runs[-1].text.rstrip()
    return [r for r in runs if r.text]


def _inner(tag: str, s: str) -> list[str]:
    """Return inner HTML of each top-level <tag> in s."""
    out, i = [], 0
    pat = re.compile(rf"<{tag}\b[^>]*>", re.S)
    while True:
        m = pat.search(s, i)
        if not m:
            return out
        depth, j = 1, m.end()
        open_re = re.compile(rf"<{tag}\b", re.S)
        close_re = re.compile(rf"</{tag}>", re.S)
        while depth and j < len(s):
            no = open_re.search(s, j)
            nc = close_re.search(s, j)
            if not nc:
                break
            if no and no.start() < nc.start():
                depth += 1
                j = no.end()
            else:
                depth -= 1
                j = nc.end()
                if depth == 0:
                    out.append(s[m.end() : nc.start()])
        i = j


def _inner_with_tag(tag: str, s: str) -> list[tuple[str, str]]:
    """Like _inner, but also returns each element's opening tag (for its class)."""
    out, i = [], 0
    pat = re.compile(rf"<{tag}\b[^>]*>", re.S)
    open_re = re.compile(rf"<{tag}\b", re.S)
    close_re = re.compile(rf"</{tag}>", re.S)
    while True:
        m = pat.search(s, i)
        if not m:
            return out
        depth, j = 1, m.end()
        while depth and j < len(s):
            no, nc = open_re.search(s, j), close_re.search(s, j)
            if not nc:
                return out
            if no and no.start() < nc.start():
                depth += 1
                j = no.end()
            else:
                depth -= 1
                j = nc.end()
                if depth == 0:
                    out.append((s[m.end() : nc.start()], m.group(0)))
        i = j


def _attr(tag_html: str, name: str) -> str:
    m = re.search(rf'{name}="([^"]*)"', tag_html)
    return m.group(1) if m else ""


def parse_slide(html: str, svg_png: dict[int, Path], idx: int) -> list[Block]:
    """Turn one slide's HTML into an ordered list of layout blocks."""
    blocks: list[Block] = []
    # Walk top-level elements in document order.
    pos = 0
    top = re.compile(
        r'<(h1|h2|h3|p|ul|table|pre|div|img)\b([^>]*)>', re.S)
    while True:
        m = top.search(html, pos)
        if not m:
            break
        tag, attrs = m.group(1), m.group(2)
        cls = _attr(attrs, "class")
        # <img> is void — it has no closing tag, so it must be handled before
        # the depth-matching loop below, which would run to end-of-slide
        # looking for a </img> and swallow every block after it.
        if tag == "img":
            pos = m.end()
            if "logo" in cls:
                # Straight decode — the circular mask that portrait_png bakes
                # in would crop a wordmark to a disc.
                png = plain_png(_attr(attrs, "src"))
                if png:
                    blocks.append(
                        Block("image", extra={"path": png, "w_in": 1.95,
                                              "h_in": 0.35, "align": "left"}),
                    )
                continue
            if "portrait" in cls:
                png = portrait_png(_attr(attrs, "src"))
                if png:
                    blocks.append(
                        Block(
                            "image",
                            extra={"path": png, "w_in": 1.42, "h_in": 1.42, "align": "left"},
                        )
                    )
            continue
        # find matching close
        depth, j = 1, m.end()
        o = re.compile(rf"<{tag}\b", re.S)
        c = re.compile(rf"</{tag}>", re.S)
        while depth and j < len(html):
            no, nc = o.search(html, j), c.search(html, j)
            if not nc:
                j = len(html)
                break
            if no and no.start() < nc.start():
                depth += 1
                j = no.end()
            else:
                depth -= 1
                j = nc.end()
        inner = html[m.end() : max(m.end(), j - len(f"</{tag}>"))]
        pos = j

        # A row of co-author portraits. python-pptx cannot lay images out
        # side by side inside a block, so the row is composited into ONE
        # picture here and emitted as a single image block.
        if tag == "div" and "portraits" in cls:
            pngs = [
                q for q in (
                    portrait_png(_attr(a, "src"))
                    for a in re.findall(r"<img\b([^>]*)>", inner, re.S)
                ) if q
            ]
            if pngs:
                row = portrait_row(pngs)
                blocks.append(
                    Block(
                        "image",
                        extra={"path": row, "w_in": 1.42 * len(pngs) + 0.16 * (len(pngs) - 1),
                               "h_in": 1.42, "align": "left"},
                    )
                )
            pos = j
            continue
        if tag == "div" and "diagram" in cls:
            png = svg_png.get(idx)
            if png:
                blocks.append(Block("image", extra={"path": png}))
            continue
        if tag == "div" and "kicker" in cls:
            blocks.append(Block("kicker", runs=inline_runs(inner)))
            continue
        if tag == "div" and cls.strip() == "sub":
            blocks.append(Block("sub", runs=inline_runs(inner)))
            continue
        if tag == "div" and "meta" in cls:
            blocks.append(Block("meta", runs=inline_runs(inner)))
            continue
        if tag == "div" and ("cols" in cls or "duo" in cls):
            # Columns hold arbitrary content (cards, lists, code) — parse recursively.
            cols = []
            for col_html, col_open in _inner_with_tag("div", inner):
                ccls = _attr(col_open, "class")
                tagm = re.search(r'<span class="tag"[^>]*>(.*?)</span>', col_html, re.S)
                cols.append(
                    {
                        "cls": ccls,
                        "tag": inline_runs(tagm.group(1)) if tagm else [],
                        "blocks": parse_slide(
                            re.sub(r'<span class="tag"[^>]*>.*?</span>', "", col_html, flags=re.S),
                            svg_png, idx,
                        ),
                    }
                )
            blocks.append(
                Block(
                    "duo" if "duo" in cls else "cols",
                    items=cols,
                    cls=cls,
                    extra={"n": 3 if "three" in cls else 2},  # CSS grid: 1fr 1fr (or three)
                )
            )
            continue
        if tag in ("h1", "h2", "h3"):
            numm = re.search(r'<span class="num">(.*?)</span>', inner, re.S)
            body = re.sub(r'<span class="num">.*?</span>', "", inner, flags=re.S)
            blocks.append(
                Block(
                    tag,
                    runs=inline_runs(body),
                    cls=cls,
                    extra={"num": htmllib.unescape(numm.group(1)).strip() if numm else ""},
                )
            )
            continue
        if tag == "p":
            blocks.append(Block("p", runs=inline_runs(inner), cls=cls))
            continue
        if tag == "ul":
            # A quiz marks its answer with <li class="right">. On screen that is
            # revealed by CSS, which this parser never sees — so carry the flag
            # through, or the .pptx ships a quiz with no answer on it.
            items, right = [], set()
            for i, (li, li_open) in enumerate(_inner_with_tag("li", inner)):
                if "right" in _attr(li_open, "class").split():
                    right.add(i)
                items.append(inline_runs(li))
            blocks.append(Block("ul", items=items, cls=cls, extra={"right": right}))
            continue
        if tag == "pre":
            txt = re.sub(r"<[^>]+>", "", inner)
            lines = htmllib.unescape(txt).strip("\n").split("\n")
            # keep span colouring per line
            # Parse the whole block once so a <span> spanning a line break keeps
            # its colour on the continuation line, then split runs on newlines.
            flat = inline_runs(inner.strip("\n"), preserve=True)
            lines: list[list[Run]] = [[]]
            for r in flat:
                for k, part in enumerate(r.text.split("\n")):
                    if k:
                        lines.append([])
                    if part:
                        lines[-1].append(Run(part, r.bold, r.italic, r.mono, r.color, r.boxed))
            styled = [ln or [Run(" ")] for ln in lines]
            blocks.append(Block("pre", items=styled, extra={"plain": lines}))
            continue
        if tag == "table":
            rows = []
            for tr in _inner("tr", inner):
                cells = []
                for cm in re.finditer(r"<(th|td)([^>]*)>(.*?)</\1>", tr, re.S):
                    body = cm.group(3)
                    pm = re.search(r'<span class="pill( w)?"', body)
                    cells.append(
                        {
                            "head": cm.group(1) == "th",
                            "cls": _attr(cm.group(2), "class"),
                            "runs": inline_runs(body),
                            "pill": ("w" if pm.group(1) else "y") if pm else "",
                        }
                    )
                if cells:
                    rows.append(cells)
            blocks.append(Block("table", items=rows))
            continue
    return blocks


# ------------------------------------------------------------- measuring ----
# Helvetica-ish average advance widths as a fraction of font size.
def _wrap_lines(runs: list[Run], size_pt: float, width_in: float) -> int:
    text = "".join(r.text for r in runs)
    if not text.strip():
        return 1
    avg = 0.50 * size_pt
    cpl = max(8, int((width_in * 72) / avg))
    words, line, lines = text.split(), 0, 1
    for w in words:
        add = len(w) + (1 if line else 0)
        if line + add > cpl:
            lines += 1
            line = len(w)
        else:
            line += add
    return lines


CARD_PAD = 0.229  # CSS .card padding clamp(15px,2vw,22px)
COL_GAP = 0.42
MONO_ADV = 0.60  # Menlo advance width as a fraction of font size


def _rows(items: list, n: int) -> list[list]:
    return [items[i : i + n] for i in range(0, len(items), n)] or [[]]


def pre_font(b: Block, width_in: float) -> float:
    """Shrink a code block's type until its longest line fits (CSS would scroll)."""
    longest = max((sum(len(r.text) for r in ln) for ln in b.items), default=1)
    usable = max(1.0, width_in - 0.48)
    fits = usable * 72 / max(1, longest * MONO_ADV)
    return max(7.5, min(SZ["pre"], fits))


def block_height(b: Block, width_in: float, in_card: bool = False) -> float:
    """Estimated height in inches."""
    if b.kind == "image":
        return b.extra.get("h_in", 3.2)
    if b.kind in ("cols", "duo"):
        n = b.extra.get("n", 2)
        cw = (width_in - COL_GAP * (n - 1)) / n
        pad = 2 * CARD_PAD if any("card" in c["cls"].split() for c in b.items) else 0.06
        total = 0.0
        for row in _rows(b.items, n):  # CSS grid wraps: 4 cards in 2 cols = 2 rows
            tallest = 0.0
            for c in row:
                card = "card" in c["cls"].split()
                inner_w = cw - (2 * CARD_PAD if card else (0.20 if b.kind == "duo" else 0))
                hh = 0.30 if c["tag"] else 0.0
                hh += sum(block_height(cb, inner_w, card) for cb in c["blocks"])
                tallest = max(tallest, hh)
            total += tallest + pad + 0.12
        return total
    if b.kind == "h1":
        return _wrap_lines(b.runs, SZ["h1"], width_in) * SZ["h1"] * 1.05 / 72 + 0.16
    if b.kind == "h2":
        return _wrap_lines(b.runs, SZ["h2"], width_in) * SZ["h2"] * 1.12 / 72 + 0.20
    if b.kind == "kicker":
        return SZ["kicker"] * 1.6 / 72 + 0.18
    if b.kind == "sub":
        return _wrap_lines(b.runs, SZ["sub"], min(width_in, 8.2)) * SZ["sub"] * 1.35 / 72 + 0.10
    if b.kind == "meta":
        # CSS: margin-top 2.1em + border-top + padding-top 1.1em + one line
        return 0.394 + 0.206 + SZ["meta"] * 1.6 / 72
    if b.kind == "h3":
        s = SZ["card_h3"] if in_card else SZ["h3"]
        return _wrap_lines(b.runs, s, width_in) * s * 1.3 / 72 + 0.10
    if b.kind == "p":
        s = SZ["card_p"] if in_card else (SZ["small"] if "small" in b.cls else SZ["p"])
        w = width_in if in_card else min(width_in, 10.4)
        return _wrap_lines(b.runs, s, w) * s * (1.45 if in_card else 1.5) / 72 + (0.08 if in_card else 0.11)
    if b.kind == "ul":
        s = SZ["card_p"] if in_card else SZ["li"]
        h = 0.0
        for it in b.items:
            h += _wrap_lines(it, s, width_in - 0.42) * s * 1.42 / 72 + 0.15
        return h + 0.05
    if b.kind == "table":
        return len(b.items) * (SZ["td"] * 1.5 / 72 + 0.115) + 0.10
    if b.kind == "pre":
        return len(b.items) * pre_font(b, width_in) * 1.55 / 72 + 0.42
    return 0.3


# -------------------------------------------------------------- rendering ----
def add_runs(tf_para, runs: list[Run], size: float, color: RGBColor, *, bold=False):
    first = True
    for r in runs:
        run = tf_para.runs[0] if (first and tf_para.runs) else tf_para.add_run()
        first = False
        run.text = r.text
        f = run.font
        f.size = Pt(size)
        f.name = MONO if r.mono else SANS
        f.bold = bold or r.bold
        f.italic = r.italic
        f.color.rgb = r.color or color


def textbox(slide, x, y, w, h):
    tb = slide.shapes.add_textbox(Emu(int(x)), Emu(int(y)), Emu(int(w)), Emu(int(h)))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    return tb, tf


def rounded(slide, x, y, w, h, fill, border, radius=0.16):
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Emu(int(x)), Emu(int(y)), Emu(int(w)), Emu(int(h)))
    sh.adjustments[0] = radius
    if fill is None:
        sh.fill.background()
    else:
        sh.fill.solid()
        sh.fill.fore_color.rgb = fill
    if border is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = border
        sh.line.width = Pt(1)
    sh.shadow.inherit = False
    return sh


def draw_block(s, b: Block, x: int, y: int, w: int, scale: float, in_card: bool = False) -> None:
    """Draw one block at (x, y) within width w (all EMU). Columns recurse."""
    h = int(block_height(b, w / 914400, in_card) * scale * 914400)

    if b.kind == "image":
        pic_w = min(w, int(Inches(b.extra.get("w_in", 10.6))))
        # Diagrams are centred in the content column; the title-slide portrait
        # sits above a left-aligned kicker and must hang off the same margin.
        px = x if b.extra.get("align") == "left" else int(x + (w - pic_w) / 2)
        s.shapes.add_picture(str(b.extra["path"]), Emu(px), Emu(y), width=Emu(pic_w))
    elif b.kind == "kicker":
        bar = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Emu(x), Emu(y + int(Inches(0.07))), Inches(0.31), Inches(0.031))
        bar.adjustments[0] = 0.5
        bar.fill.solid(); bar.fill.fore_color.rgb = ACCENT
        bar.line.fill.background(); bar.shadow.inherit = False
        _, tf = textbox(s, x + int(Inches(0.46)), y, w, h)
        add_runs(tf.paragraphs[0], b.runs, SZ["kicker"], ACCENT_DK, bold=True)
        if THEME.get("subhead_mono"):
            for r in tf.paragraphs[0].runs:
                r.font.name = MONO
    elif b.kind == "h1":
        _, tf = textbox(s, x, y, w, h)
        p = tf.paragraphs[0]
        add_runs(p, b.runs, SZ["h1"] * scale, INK)
        for r in p.runs:
            r.font.bold = False
        p.line_spacing = 1.02
    elif b.kind == "sub":
        _, tf = textbox(s, x, y, min(w, int(Inches(8.6))), h)
        add_runs(tf.paragraphs[0], b.runs, SZ["sub"] * scale, MUTED)
        tf.paragraphs[0].line_spacing = 1.32
        if THEME.get("subhead_mono"):
            for r in tf.paragraphs[0].runs:
                r.font.name = MONO
    elif b.kind == "meta":
        rule_y = y + int(Inches(0.394))
        ln = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Emu(x), Emu(rule_y), Inches(5.6), Emu(9525))
        ln.fill.solid(); ln.fill.fore_color.rgb = LINE
        ln.line.fill.background(); ln.shadow.inherit = False
        _, tf = textbox(s, x, rule_y + int(Inches(0.206)), w, int(Inches(0.32)))
        add_runs(tf.paragraphs[0], b.runs, SZ["meta"], INK_SOFT)
        for r in tf.paragraphs[0].runs:
            r.font.name = MONO
    elif b.kind in ("h2", "h3"):
        xoff = 0
        if b.extra.get("num"):
            badge = rounded(s, x, y, int(Inches(0.62)), int(Inches(0.42)), ACCENT, None, radius=0.22)
            btf = badge.text_frame
            btf.margin_left = btf.margin_right = btf.margin_top = btf.margin_bottom = 0
            btf.word_wrap = False
            bp = btf.paragraphs[0]
            bp.alignment = PP_ALIGN.CENTER
            br = bp.add_run(); br.text = b.extra["num"]
            br.font.size = Pt(SZ["h2"] * 0.5 * scale); br.font.name = MONO
            br.font.bold = True; br.font.color.rgb = ON_ACCENT
            btf.vertical_anchor = MSO_ANCHOR.MIDDLE
            xoff = int(Inches(0.78))
        _, tf = textbox(s, x + xoff, y, w - xoff, h)
        if b.kind == "h2":
            sz, col, bold = SZ["h2"], INK, False
        else:
            sz = SZ["card_h3"] if in_card else SZ["h3"]
            col = _rgb(b.cls) or (INK if not in_card else INK)
            bold = in_card
        add_runs(tf.paragraphs[0], b.runs, sz * scale, col, bold=bold)
        tf.paragraphs[0].line_spacing = 1.12
    elif b.kind == "p":
        small = "small" in b.cls
        sz = (SZ["card_p"] if in_card else (SZ["small"] if small else SZ["p"])) * scale
        col = MUTED if (small or "lead" in b.cls) else INK_SOFT
        _, tf = textbox(s, x, y, w if in_card else min(w, int(Inches(10.6))), h)
        add_runs(tf.paragraphs[0], b.runs, sz, col)
        tf.paragraphs[0].line_spacing = 1.42 if in_card else 1.45
    elif b.kind == "ul":
        base = SZ["card_p"] if in_card else SZ["li"]
        iy = y
        right = b.extra.get("right", set())
        for i, it in enumerate(b.items):
            ok = i in right
            ih = int((_wrap_lines(it, base, w / 914400 - 0.42) * base * 1.42 / 72 + 0.15) * scale * 914400)
            dot = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Emu(x), Emu(iy + int(Inches(0.13))), Inches(0.135), Inches(0.135))
            dot.adjustments[0] = 0.18
            dot.fill.solid(); dot.fill.fore_color.rgb = GOOD if ok else ACCENT
            dot.line.fill.background(); dot.shadow.inherit = False
            _, tf = textbox(s, x + int(Inches(0.36)), iy, w - int(Inches(0.36)), ih)
            runs = list(it) + [Run(" \u2713", bold=True, color=GOOD)] if ok else it
            add_runs(tf.paragraphs[0], runs, base * scale, INK if ok else INK_SOFT, bold=ok)
            tf.paragraphs[0].line_spacing = 1.40
            iy += ih
    elif b.kind in ("cols", "duo"):
        n = b.extra.get("n", 2)
        gap = int(Inches(COL_GAP))
        cw = int((w - gap * (n - 1)) / n)
        pad = 2 * CARD_PAD if any("card" in c["cls"].split() for c in b.items) else 0.06
        ry = y
        for row in _rows(b.items, n):
            tallest = 0.0
            for c in row:
                card = "card" in c["cls"].split()
                iw = cw / 914400 - (2 * CARD_PAD if card else (0.20 if b.kind == "duo" else 0))
                hh = 0.30 if c["tag"] else 0.0
                hh += sum(block_height(cb, iw, card) for cb in c["blocks"])
                tallest = max(tallest, hh)
            row_h = int((tallest + pad) * scale * 914400)
            for i, c in enumerate(row):
                cx = x + i * (cw + gap)
                card = "card" in c["cls"].split()
                if card:
                    rounded(s, cx, ry, cw, row_h, CARD, LINE)
                    inner_x = cx + int(Inches(CARD_PAD))
                    inner_w = cw - 2 * int(Inches(CARD_PAD))
                    iy = ry + int(Inches(CARD_PAD * 0.8))
                elif b.kind == "duo":
                    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Emu(cx), Emu(ry), Inches(0.042), Emu(row_h))
                    bar.fill.solid()
                    bar.fill.fore_color.rgb = GOOD if "b" in c["cls"].split() else ACCENT
                    bar.line.fill.background(); bar.shadow.inherit = False
                    inner_x, inner_w, iy = cx + int(Inches(0.20)), cw - int(Inches(0.20)), ry
                else:
                    inner_x, inner_w, iy = cx, cw, ry
                if c["tag"]:
                    _, tf = textbox(s, inner_x, iy, inner_w, int(Inches(0.26)))
                    add_runs(tf.paragraphs[0], c["tag"], SZ["tag"], ACCENT_DK, bold=True)
                    iy += int(Inches(0.30))
                for cb in c["blocks"]:
                    ch = int(block_height(cb, inner_w / 914400, card) * scale * 914400)
                    if cb.kind == "h3" and b.kind == "duo":
                        _, tf = textbox(s, inner_x, iy, inner_w, ch)
                        add_runs(tf.paragraphs[0], cb.runs, SZ["duo_h3"] * scale,
                                 _rgb(cb.cls) or ACCENT_DK, bold=True)
                    else:
                        draw_block(s, cb, inner_x, iy, inner_w, scale, card)
                    iy += ch
            ry += row_h + int(Inches(0.12) * scale)
    elif b.kind == "table":
        ry = y
        rh = int((SZ["td"] * 1.5 / 72 + 0.115) * scale * 914400)
        for row in b.items:
            head = row[0]["head"]
            # Column widths are per-arity. Without the 4-column case the first
            # three ate the whole content width and the fourth began at the
            # right edge — rendering it off-slide with no error.
            if len(row) == 2:
                widths = [int(Inches(0.75)), w - int(Inches(0.75))]
            elif len(row) == 3:
                widths = [int(Inches(0.75)), w - int(Inches(0.75)) - int(Inches(4.3)), int(Inches(4.3))]
            elif len(row) == 4:
                lead = int(Inches(0.55)), int(Inches(1.30))
                rest = w - sum(lead)
                widths = [*lead, rest // 2, rest - rest // 2]
            else:
                each = w // len(row)
                widths = [each] * (len(row) - 1) + [w - each * (len(row) - 1)]
            cx = x
            for ci, cell in enumerate(row):
                cwid = widths[ci] if ci < len(widths) else int(Inches(2.0))
                if cell.get("pill"):
                    txt = "".join(r.text for r in cell["runs"])
                    pw = int(Inches(0.16)) * 2 + int(len(txt) * SZ["td"] * 0.60 * 12700)
                    warn = cell["pill"] == "w"
                    rounded(s, cx, ry + int(Inches(0.04)), pw, int(Inches(0.30)),
                            WARN_BG if warn else GOOD_BG, WARN_BD if warn else GOOD_BD, radius=0.5)
                    _, tf = textbox(s, cx + int(Inches(0.16)), ry + int(Inches(0.09)), pw, int(Inches(0.24)))
                    add_runs(tf.paragraphs[0], cell["runs"], SZ["td"] * 0.86 * scale, WARN if warn else GOOD, bold=True)
                    for r in tf.paragraphs[0].runs:
                        r.font.name = MONO
                    cx += cwid
                    continue
                _, tf = textbox(s, cx, ry + int(Inches(0.06)), cwid - int(Inches(0.12)), rh)
                sz = (SZ["th"] if head else SZ["td"]) * scale
                col = MUTED if head else (ACCENT if "n" in cell["cls"].split() else INK_SOFT)
                add_runs(tf.paragraphs[0], cell["runs"], sz, col, bold=head or "n" in cell["cls"].split())
                if head:
                    for r in tf.paragraphs[0].runs:
                        r.text = r.text.upper()
                cx += cwid
            sep = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Emu(x), Emu(ry + rh), Emu(w), Emu(9525))
            sep.fill.solid(); sep.fill.fore_color.rgb = LINE
            sep.line.fill.background(); sep.shadow.inherit = False
            ry += rh
    elif b.kind == "pre":
        rounded(s, x, y, w, h, CARD, LINE2, radius=0.10)
        fs = pre_font(b, w / 914400)
        ly = y + int(Inches(0.18))
        lh = int(fs * 1.55 / 72 * scale * 914400)
        for line in b.items:
            _, tf = textbox(s, x + int(Inches(0.24)), ly, w - int(Inches(0.48)), lh)
            tf.word_wrap = False  # CSS `pre` overflows rather than wrapping
            pr = tf.paragraphs[0]
            add_runs(pr, line, fs * scale, INK)
            for r in pr.runs:
                r.font.name = MONO
            ly += lh


def render(prs, blocks: list[Block], notes: str, is_title: bool, is_section: bool):
    blank = prs.slide_layouts[6]
    s = prs.slides.add_slide(blank)
    bg = s.background.fill
    bg.solid()
    bg.fore_color.rgb = BG

    W = int(CONTENT_W)
    total = sum(block_height(b, CONTENT_W.inches) for b in blocks)
    avail = AVAIL_IN
    scale = min(1.0, avail / total) if total else 1.0
    y = int(PAD_Y) + int((avail - min(total, avail)) / 2 * 914400)

    if not is_title:
        rule = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, PAD_X, PAD_Y, Inches(0.458), Inches(0.042))
        rule.adjustments[0] = 0.5
        rule.fill.solid()
        rule.fill.fore_color.rgb = ACCENT
        rule.line.fill.background()
        rule.shadow.inherit = False
        y = max(y, int(PAD_Y) + int(Inches(0.36)))

    for b in blocks:
        draw_block(s, b, int(PAD_X), y, W, scale)
        y += int(block_height(b, CONTENT_W.inches) * scale * 914400)

    if notes:
        s.notes_slide.notes_text_frame.text = notes
    return s


# ------------------------------------------------------------------ svg ------
def portrait_png(src: str) -> Path | None:
    """Decode the inlined portrait data: URI into a circular PNG for the deck.

    The photo lives as a base64 data: URI inside slide.js so that every HTML
    surface is self-contained. python-pptx cannot embed a data: URI, and it
    cannot round a picture either, so the circle is baked into an alpha mask
    here — matching `.title .portrait { border-radius: 50% }` in slide.css.
    """
    m = re.match(r"data:image/(?:jpeg|png);base64,(.+)$", src.strip(), re.S)
    if not m:
        return None
    from io import BytesIO

    from PIL import Image, ImageDraw  # ships with python-pptx

    im = Image.open(BytesIO(base64.b64decode(m.group(1)))).convert("RGBA")
    side = min(im.size)
    im = im.crop((0, 0, side, side))
    # Mask at 4x and downsample, so the circle's edge is smooth rather than
    # a visible staircase at projector size.
    mask = Image.new("L", (side * 4, side * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, side * 4 - 1, side * 4 - 1), fill=255)
    im.putalpha(mask.resize((side, side), Image.LANCZOS))
    out = Path(tempfile.mkdtemp(prefix="deck-portrait-")) / "portrait.png"
    im.save(out)
    return out


def plain_png(src: str) -> Path | None:
    """Decode an inlined data: URI as-is. python-pptx cannot embed a data: URI."""
    m = re.match(r"data:image/(?:jpeg|png);base64,(.+)$", src.strip(), re.S)
    if not m:
        return None
    out = Path(tempfile.mkdtemp(prefix="deck-img-")) / "img.png"
    out.write_bytes(base64.b64decode(m.group(1)))
    return out


def portrait_row(pngs: list[Path]) -> Path:
    """Composite already-circular portraits into one wide transparent strip.

    A block in this renderer is a row of its own, so two separate image blocks
    would stack vertically. Compositing keeps the co-authors side by side and
    matches `.title .portraits { display: flex }` in slide.css.
    """
    from PIL import Image

    ims = [Image.open(q).convert("RGBA") for q in pngs]
    side = max(i.width for i in ims)
    ims = [i.resize((side, side), Image.LANCZOS) for i in ims]
    gap = int(side * 0.11)
    out = Image.new("RGBA", (side * len(ims) + gap * (len(ims) - 1), side), (0, 0, 0, 0))
    for k, i in enumerate(ims):
        out.paste(i, (k * (side + gap), 0), i)
    q = Path(tempfile.mkdtemp(prefix="deck-portraits-")) / "portraits.png"
    out.save(q)
    return q


def rasterise_svgs(slides) -> dict[int, Path]:
    out: dict[int, Path] = {}
    tmp = Path(tempfile.mkdtemp(prefix="deck-svg-"))
    for i, sl in enumerate(slides, 1):
        # Match the class ATTRIBUTE, not a literal string: parse_slide accepts
        # any class containing "diagram", so a literal match here silently
        # skipped `class="diagram wide"` and dropped the figure from the deck.
        m = re.search(r'<div class="[^"]*\bdiagram\b[^"]*">(.*?)</div>', sl["html"], re.S)
        if not m:
            continue
        svg = m.group(1).strip()
        vb = re.search(r'viewBox="([\d.\s-]+)"', svg)
        if vb:
            _, _, vw, vh = [float(v) for v in vb.group(1).split()]
        else:
            vw, vh = 960.0, 420.0
        width = 2200
        height = int(width * vh / vw)
        svg_fit = re.sub(r"<svg\b", '<svg preserveAspectRatio="xMidYMid meet"', svg, count=1)
        # Re-theme the diagram: the SVGs hardcode the Google hexes.
        for src_hex, dst_hex in THEME.get("svg_map", {}).items():
            # Trailing guard so "#fff" never eats the front of "#ffffff".
            svg_fit = re.sub(re.escape(src_hex) + r"(?![0-9a-fA-F])", dst_hex, svg_fit, flags=re.I)
        svg_fit = re.sub(r"font-family:[^;}]+", f"font-family:'{SANS}',sans-serif", svg_fit)
        page = tmp / f"d{i}.html"
        page.write_text(
            "<!doctype html><meta charset='utf-8'><style>"
            f"html,body{{margin:0;padding:0;background:{THEME['svg_bg']};}}"
            f"body{{width:{width}px;}}"
            "svg{display:block;width:100%;height:auto;}"
            f"</style><body>{svg_fit}</body>"
        )
        png = tmp / f"d{i}.png"
        subprocess.run(
            [CHROME, "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
             f"--screenshot={png}", f"--window-size={width},{height}",
             f"file://{page}"],
            capture_output=True, timeout=90,
        )
        if png.exists():
            out[i] = png
            slides[i - 1]["_img_h_in"] = (10.6 * vh / vw)
    return out


# ----------------------------------------------------------------- driver ----
def extract_slides():
    src = SLIDE_JS.read_text()
    i = src.index("const SLIDES = [")
    i = src.index("[", i)
    depth, end = 0, len(src)
    for j in range(i, len(src)):
        if src[j] == "[":
            depth += 1
        elif src[j] == "]":
            depth -= 1
            if depth == 0:
                end = j
                break
    body = src[i + 1 : end]
    objs, d, cur = [], 0, ""
    for ch in body:
        if ch == "{":
            d += 1
            if d == 1:
                cur = ""
                continue
        if ch == "}":
            d -= 1
            if d == 0:
                objs.append(cur)
                continue
        if d >= 1:
            cur += ch
    slides = []
    for o in objs:
        hm = re.search(r"html:\s*`(.*?)`", o, re.S)
        cm = re.search(r'cls:\s*"([^"]*)"', o)
        nm = re.search(r'notes:\s*"((?:[^"\\]|\\.)*)"', o, re.S)
        notes = nm.group(1).replace('\\"', '"').replace("\\n", "\n") if nm else ""
        slides.append({"html": hm.group(1) if hm else "", "cls": cm.group(1) if cm else "", "notes": notes})
    return slides


def main():
    theme = "google"
    # The quizzes ship as their own handout, so a build selects one view of the
    # deck. The SLIDES array in slide.js stays the whole thing either way —
    # this mirrors window.DECK_FILTER in the browser engine.
    view = "noquiz"
    for a in sys.argv[1:]:
        if a.startswith("--theme="):
            theme = a.split("=", 1)[1]
        elif a.startswith("--filter="):
            view = a.split("=", 1)[1]
        elif a in THEMES:
            theme = a
    global OUT
    if view not in ("all", "quiz", "noquiz"):
        print(f"unknown filter {view!r}; choose from all, quiz, noquiz")
        return 2
    if theme not in THEMES:
        print(f"unknown theme {theme!r}; choose from {', '.join(THEMES)}")
        return 2
    apply_theme(theme)
    print(f"theme: {theme}  (sans={SANS}, mono={MONO})")

    slides = extract_slides()
    # A parse failure must not silently overwrite a good deck. SLIDES is
    # brace-counted out of a JS file, so one stray brace or backtick in a slide
    # can drop the count to zero — and main() previously returned None on that
    # path, so sys.exit(main()) reported success after clobbering the artifact.
    if len(slides) < MIN_SLIDES:
        print(f"BUILD ERROR: parsed {len(slides)} slides, expected >= {MIN_SLIDES}. "
              f"Refusing to overwrite {OUT.name}. Check slide.js for an "
              "unbalanced brace or a stray backtick.")
        return 1
    print(f"parsed {len(slides)} slides from slide.js")
    if view != "all":
        is_quiz = lambda sl: '<ul class="quiz">' in sl["html"]
        slides = [sl for sl in slides if (is_quiz(sl) if view == "quiz" else not is_quiz(sl))]
        if view == "quiz":
            OUT = OUT.with_name(OUT.stem + "-quiz" + OUT.suffix)
        print(f"filter {view}: {len(slides)} slides -> {OUT.name}")
        if not slides:
            print("BUILD ERROR: filter left no slides.")
            return 1
    svgs = rasterise_svgs(slides)
    print(f"rasterised {len(svgs)} inline SVG diagrams")

    prs = Presentation()
    prs.slide_width, prs.slide_height = SLIDE_W, SLIDE_H

    for i, sl in enumerate(slides, 1):
        blocks = parse_slide(sl["html"], svgs, i)
        for b in blocks:
            if b.kind == "image" and "_img_h_in" in sl:
                b.extra["h_in"] = sl["_img_h_in"] + 0.15
        render(prs, blocks, sl["notes"], sl["cls"] == "title", sl["cls"] == "section-slide")

    prs.save(OUT)
    print(f"wrote {OUT.relative_to(REPO)}  ({OUT.stat().st_size/1024:.0f} KB, {len(slides)} slides)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
