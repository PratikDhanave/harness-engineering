#!/usr/bin/env python3
"""Build the web version of the talk: slides + runnable code on one page.

`docs/presentation/web-talk.html` is the talk as something you can send someone.
Same 19 slides (parsed from slide.js — one source of truth), laid out as a
scrolling page in the live-demo.html style, with the speaker notes promoted to
visible commentary and the three runnable panels embedded inline.

Why generate instead of restyling the deck: slide.js ships content *and* a
navigation engine that shows one slide at a time and binds keys. Reusing it here
would mean fighting that engine (`o` for overview would wreck a scrolling
layout). Parsing the content out is cleaner and leaves the deck untouched.

Reuses the deck's own stylesheets for components (cards, tables, code, diagrams),
so a change to slide.css lands here too.

    uv run python3 scripts/build_web_talk.py
"""
from __future__ import annotations

import html as htmllib
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PRES = REPO / "docs" / "presentation"
SLIDE_JS = PRES / "slide.js"
# One file per theme. A single output meant `--theme=clearroute` silently
# overwrote the Google build (and vice versa) — the two could never coexist,
# and whichever ran last won with no warning.
OUT_BY_THEME = {
    "google": PRES / "web-talk.html",
    "clearroute": PRES / "web-talk-clearroute.html",
}


def extract_slides() -> list[dict]:
    """Pull {html, cls, notes} out of the SLIDES array in slide.js."""
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
        slides.append({
            "html": hm.group(1) if hm else "",
            "cls": cm.group(1) if cm else "",
            "notes": notes,
        })
    return slides


def title_of(html: str) -> str:
    m = re.search(r"<h[12][^>]*>(.*?)</h[12]>", html, re.S)
    if not m:
        return "Introduction"
    t = re.sub(r'<span class="num">.*?</span>', "", m.group(1), flags=re.S)
    return htmllib.unescape(re.sub(r"<[^>]+>", "", t)).strip()


SKINS = {
    "google": "",  # slide.css is already the Google palette
    "clearroute": '<link rel="stylesheet" href="clearroute.css" />\n',
}


def main() -> int:
    theme = "google"
    for a in sys.argv[1:]:
        if a.startswith("--theme="):
            theme = a.split("=", 1)[1]
        elif a in SKINS:
            theme = a
    if theme not in SKINS:
        print(f"unknown theme {theme!r}; choose from {', '.join(SKINS)}")
        return 2

    slides = extract_slides()
    # The quizzes are a separate handout now, so the web talk carries the talk.
    # slide.js still holds every slide; this mirrors window.DECK_FILTER.
    slides = [sl for sl in slides if '<ul class="quiz">' not in sl["html"]]
    if not slides:
        print("no slides parsed from slide.js")
        return 1

    sections, toc = [], []
    for n, s in enumerate(slides, 1):
        # Panels are inline here, not the deck's overlay — a scrolling page has room.
        body = s["html"].replace(" data-compact", "")
        title = title_of(s["html"])
        anchor = f"s{n}"
        if n > 1:
            toc.append(f'<li><a href="#{anchor}"><span class="n">{n:02d}</span>{htmllib.escape(title)}</a></li>')

        note = ""
        if s["notes"]:
            note = (
                '<aside class="note"><h4>Speaker&#39;s note</h4><p>'
                + htmllib.escape(s["notes"]).replace("\n\n", "</p><p>")
                + "</p></aside>"
            )
        if s["cls"] == "title":
            continue  # the masthead already is this slide
        sections.append(
            f'<section class="sec nav" id="{anchor}">\n'
            f'  <div class="marker">{n:02d} / {len(slides)}</div>\n'
            f'  <div class="slide">{body}</div>\n'
            f"  {note}\n"
            f"</section>"
        )

    # The masthead restates slide 1 in this page's own markup, so the portrait
    # is lifted out of the slide rather than pasted here — slide.js stays the
    # one place the image lives.
    # The speakers moved off the title slide onto their own, so look across
    # the opening slides rather than assuming slide 1 carries the faces.
    pm = next(
        (r for r in (re.search(r'<div class="portraits[^"]*">.*?</div>', sl["html"], re.S)
                     for sl in slides[:3]) if r),
        None,
    )
    html = PAGE.replace("{{PORTRAIT}}", f"    {pm.group(0)}" if pm else "")
    html = html.replace("{{SKIN}}", SKINS[theme])
    html = html.replace("{{TOC}}", "\n".join(toc))
    html = html.replace("{{SECTIONS}}", "\n\n".join(sections))
    html = html.replace("{{COUNT}}", str(len(slides)))
    html = html.replace("{{DEMOS}}", str(html.count("data-demo=")))
    OUT = OUT_BY_THEME[theme]
    OUT.write_text(html)

    print(f"wrote {OUT.relative_to(REPO)}  ({OUT.stat().st_size/1024:.0f} KB, {theme} palette)")
    print(f"  {len(slides)} slides, {sum(1 for s in slides if s['notes'])} with speaker notes")
    print(f"  {html.count('data-demo=')} runnable panels inline")
    return 0


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Harness Engineering — the talk, on the web</title>
<meta name="description" content="Seven patterns for putting an AI agent into production, with the real code running in your browser." />
<!-- Component styles (cards, tables, code, diagrams) come from the deck's own
     stylesheets, so editing slide.css updates this page too. slide.css alone is
     the Google palette; clearroute.css (when present) skins it to the house
     colours. web-talk overrides only the deck's fixed-slide layout. -->
<link rel="stylesheet" href="slide.css" />
<link rel="stylesheet" href="live.css" />
{{SKIN}}
<style>
  /* --- undo the deck's fixed-canvas layout, become a document -------------- */
  html, body { height: auto; overflow: visible; }
  body { background: var(--bg); color: var(--ink); }
  /* The deck paints .slide as a fixed, centred, hidden-unless-active canvas.
     Keep the class (so component rules like `.slide h2 .num` still match) and
     undo just the layout — the same trick slide.css's @media print block uses. */
  .sec .slide {
    position: static; inset: auto; display: block;
    padding: 0; animation: none; overflow: visible; height: auto;
  }
  .sec .slide::before { display: none; }   /* the deck's accent rule */

  .page { max-width: 1180px; margin: 0 auto; padding: 0 clamp(20px, 5vw, 56px) 90px; }

  /* --- masthead ----------------------------------------------------------- */
  .masthead { padding: clamp(48px, 9vh, 96px) 0 clamp(30px, 5vh, 52px); }
  .masthead .portraits { display: flex; gap: .6em; margin: 0 0 1.1em; }
  .masthead .portrait { width: clamp(84px,10vw,132px); height: clamp(84px,10vw,132px);
    border-radius: 50%; object-fit: cover; display: block;
    border: 3px solid var(--accent); box-shadow: 0 5px 20px rgba(16,24,40,.16); }
  .masthead .kicker { display:flex; align-items:center; gap:.7em; color: var(--accent-dk);
    font: 600 clamp(13px,1.4vw,17px)/1 var(--sans); margin-bottom: 1.1em; }
  .masthead .kicker::before { content:""; width:30px; height:3px; background: var(--accent); border-radius:2px; }
  .masthead h1 { font-size: clamp(34px, 5.4vw, 68px); font-weight: 500; letter-spacing: -.022em;
    line-height: 1.04; margin: 0 0 .3em; max-width: 17ch; }
  .masthead .sub { font-size: clamp(17px, 2vw, 24px); color: var(--muted); max-width: 60ch; margin: 0 0 1.3em; }
  .masthead .meta { font: 500 clamp(12px,1.3vw,15px)/1.6 var(--mono); color: var(--ink-soft);
    border-top: 1px solid var(--line); padding-top: 1.1em; display: inline-block; }

  /* --- contents ----------------------------------------------------------- */
  .toc { border: 1px solid var(--line); border-radius: 14px; padding: 20px 24px 22px; margin: 8px 0 46px; }
  .toc h2 { margin: 0 0 .7em; font: 700 12.5px/1 var(--sans); letter-spacing: .09em;
    text-transform: uppercase; color: var(--muted); }
  .toc ol { list-style: none; margin: 0; padding: 0; columns: 2; column-gap: 40px; }
  .toc li { margin: 0 0 7px; break-inside: avoid; }
  .toc a { color: var(--ink-soft); text-decoration: none; font-size: 15px; display: flex; gap: .8em; }
  .toc a:hover { color: var(--accent-dk); }
  .toc .n { font: 700 12.5px/1.5 var(--mono); color: var(--accent-dk); opacity: .8; }
  @media (max-width: 720px) { .toc ol { columns: 1; } }

  /* --- sections ----------------------------------------------------------- */
  .sec { position: relative; padding: clamp(26px,4vh,46px) 0 clamp(30px,5vh,54px);
         border-top: 1px solid var(--line); scroll-margin-top: 16px; }
  .sec.title { display: none; }               /* the masthead already says this */
  .sec .marker { font: 700 12px/1 var(--mono); color: var(--accent-dk);
                 letter-spacing: .1em; opacity: .75; margin-bottom: 1.1em; }

  /* The slide markup assumes a centred fixed canvas; here it is just a block. */
  
  .sec .slide h2 { font-size: clamp(24px, 3vw, 38px); margin: 0 0 .5em; }
  .sec .slide h2 .num { font-size: .5em; }
  .sec .slide p, .sec .slide li { max-width: 74ch; }
  .sec .slide .diagram { margin: 1.1em 0 .6em; }
  .sec .slide .diagram svg { max-height: none; }
  .sec .slide table.lessons { font-size: clamp(13px, 1.25vw, 16px); }

  /* --- speaker note, promoted to visible commentary ----------------------- */
  .note { margin: 1.5em 0 0; padding: 15px 18px 16px; border-radius: 12px;
          background: var(--panel); border: 1px solid var(--line); max-width: 82ch; }
  .note h4 { margin: 0 0 .5em; font: 700 11px/1 var(--mono); letter-spacing: .16em;
             text-transform: uppercase; color: var(--accent-dk); }
  .note p { margin: 0 0 .6em; color: var(--ink-soft); font-size: 15.5px; max-width: none; }
  .note p:last-child { margin-bottom: 0; }

  /* --- run-the-code callout ----------------------------------------------- */
  [data-demo] { display: block; margin-top: 1.5em; padding: 16px 18px 18px;
                border: 1px solid var(--live-tint-bd); border-radius: 12px;
                background: var(--live-tint); }
  [data-demo]::before { content: "Run it yourself"; display: block; margin-bottom: .7em;
                        font: 700 11px/1 var(--mono); letter-spacing: .16em;
                        text-transform: uppercase; color: var(--live-key); }

  footer { border-top: 1px solid var(--line); margin-top: 40px; padding-top: 22px;
           color: var(--muted); font-size: 14px; }
  footer a { color: var(--accent-dk); }

  /* --- reading progress --------------------------------------------------- */
  #bar { position: fixed; top: 0; left: 0; height: 3px; width: 0;
         background: var(--accent); z-index: 50; transition: width .15s ease; }

  /* --- paged mode (default): one section at a time, next/next ------------- */
  body.paged .sec { display: none; border-top: 0; padding-top: clamp(20px,3vh,34px); }
  body.paged .sec.on { display: block; animation: fade .28s ease; }
  body.paged .page { padding-bottom: 96px; min-height: 100vh; }
  body.paged .sec.cover .masthead { padding-top: clamp(24px,6vh,64px); }
  @keyframes fade { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }

  /* Scroll mode keeps the long-form reading view. */
  body.scrolling #chrome .step { display: none; }
  /* The colophon belongs to the document, not to every slide. */
  body.paged footer { display: none; }

  /* Sections can be taller than the viewport, so the fixed chrome floats over
     content — give it a surface of its own or it collides with the text. */
  #chrome { position: fixed; right: clamp(14px,2vw,26px); bottom: clamp(14px,2vh,22px);
            display: flex; align-items: center; gap: 9px; z-index: 60;
            font: 600 13px/1 var(--mono); color: var(--muted);
            background: var(--bg); border: 1px solid var(--line);
            border-radius: 12px; padding: 7px 9px; box-shadow: var(--shadow-md); }
  #chrome button { cursor: pointer; background: var(--bg); color: var(--ink-soft);
    border: 1px solid var(--line-2); border-radius: 9px; height: 34px; min-width: 34px;
    padding: 0 10px; font: 600 14px/1 var(--sans); box-shadow: var(--shadow-sm); }
  #chrome button:hover { border-color: var(--accent-dk); color: var(--accent-dk); }
  #count { min-width: 62px; text-align: center; }
  #chrome #mode { font: 600 11.5px/1 var(--mono); letter-spacing: .04em;
                  min-width: 74px; padding: 0 13px; }
  #hint { position: fixed; left: clamp(14px,2vw,26px); bottom: clamp(16px,2vh,24px);
          z-index: 60; color: var(--muted); font: 500 12px/1 var(--mono);
          background: var(--bg); border: 1px solid var(--line);
          border-radius: 999px; padding: 8px 13px; box-shadow: var(--shadow-sm);
          transition: opacity .4s ease; }
  #hint.gone { opacity: 0; pointer-events: none; }
  #hint b { color: var(--accent-dk); }
  @media (max-width: 640px) { #hint { display: none; } }

  @media print {
    #bar { display: none; }
    .sec { break-inside: avoid; }
  }
</style>
</head>
<body>
<div id="bar"></div>

<div class="page">

  <section class="sec nav cover" id="s0">
  <header class="masthead">
{{PORTRAIT}}
    <div class="kicker">Azure · Python · seven patterns</div>
    <h1>Harness Engineering with Microsoft Agent Framework</h1>
    <p class="sub">Seven patterns for putting an AI agent into production — re-built in Python
    on managed Azure primitives. This is the talk, in full, with the real code running in your
    browser.</p>
    <div class="meta">{{COUNT}} sections &nbsp;·&nbsp; {{DEMOS}} runnable demos &nbsp;·&nbsp; all 7 lessons implemented &amp; tested</div>
  </header>

  <nav class="toc">
    <h2>Contents</h2>
    <ol>{{TOC}}</ol>
  </nav>
  </section>

{{SECTIONS}}

  <footer>
    <p>The three green panels run the <strong>real modules</strong> from <code>src/harness/</code>
    as CPython compiled to WebAssembly — the same <code>check_input</code> the test suite
    exercises. If the Pyodide CDN is unreachable, each panel replays a transcript captured at
    build time and says so.</p>
    <p>Generated from <code>slide.js</code> by <code>scripts/build_web_talk.py</code> — the deck,
    the two PowerPoint builds and this page all come from that one source. Slide-by-slide
    version: <a href="clearroute.html">clearroute.html</a> · <a href="index.html">index.html</a>.</p>
  </footer>
</div>

<nav id="chrome">
  <button id="mode" title="Switch between slide-by-slide and long-form reading">scroll</button>
  <button class="step" id="prev" title="Previous (←)">‹</button>
  <span class="step" id="count">1 / 1</span>
  <button class="step" id="next" title="Next (→)">›</button>
</nav>
<div id="hint">← → navigate &nbsp;·&nbsp; <b>s</b> scroll view &nbsp;·&nbsp; <b>f</b> fullscreen</div>

<script>
  // Panels render inline on this page rather than behind the deck's overlay.
  document.documentElement.setAttribute("data-live-inline", "1");
</script>
<script src="live-payload.js"></script>
<script src="live.js"></script>
<script>
(function () {
  var body = document.body;
  var secs = [].slice.call(document.querySelectorAll(".sec.nav"));
  var bar = document.getElementById("bar");
  var count = document.getElementById("count");
  var cur = 0;

  function paged() { return body.classList.contains("paged"); }

  function show(i, push) {
    cur = Math.max(0, Math.min(secs.length - 1, i));
    secs.forEach(function (s, k) { s.classList.toggle("on", k === cur); });
    count.textContent = (cur + 1) + " / " + secs.length;
    bar.style.width = (secs.length > 1 ? (cur / (secs.length - 1)) * 100 : 100) + "%";
    if (paged()) scrollTo(0, 0);
    if (push !== false && secs[cur].id) history.replaceState(null, "", "#" + secs[cur].id);
  }

  function setMode(toPaged) {
    body.classList.toggle("paged", toPaged);
    body.classList.toggle("scrolling", !toPaged);
    document.getElementById("mode").textContent = toPaged ? "scroll" : "slides";
    if (toPaged) show(cur);
    else {
      secs.forEach(function (s) { s.classList.add("on"); });
      bar.style.width = "0%";
      var t = secs[cur]; if (t) t.scrollIntoView();
    }
  }

  // Deep link: #s9 opens that slide in paged mode, jumps to it in scroll mode.
  var want = secs.findIndex(function (s) { return "#" + s.id === location.hash; });
  setMode(true);
  show(want > 0 ? want : 0, false);

  // The hint is orientation, not chrome — retire it once they are moving, so it
  // stops floating over tall slides (it can land on a panel's Run button).
  var hint = document.getElementById("hint");
  var retire = function () { hint.classList.add("gone"); };
  setTimeout(retire, 7000);
  ["keydown", "click"].forEach(function (ev) {
    addEventListener(ev, retire, { once: true });
  });

  document.getElementById("next").onclick = function () { show(cur + 1); };
  document.getElementById("prev").onclick = function () { show(cur - 1); };
  document.getElementById("mode").onclick = function () { setMode(!paged()); };

  // The live panels contain a textarea — never steal keys while typing in one.
  addEventListener("keydown", function (e) {
    if (/^(INPUT|TEXTAREA)$/.test((e.target && e.target.tagName) || "")) return;
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    var k = e.key;
    if (paged() && (k === "ArrowRight" || k === "PageDown" || k === " ")) { e.preventDefault(); show(cur + 1); }
    else if (paged() && (k === "ArrowLeft" || k === "PageUp")) { e.preventDefault(); show(cur - 1); }
    else if (paged() && k === "Home") { e.preventDefault(); show(0); }
    else if (paged() && k === "End") { e.preventDefault(); show(secs.length - 1); }
    else if (k === "s" || k === "S") { e.preventDefault(); setMode(!paged()); }
    else if (k === "f" || k === "F") {
      e.preventDefault();
      if (document.fullscreenElement) document.exitFullscreen();
      else document.documentElement.requestFullscreen && document.documentElement.requestFullscreen();
    }
  });

  // Contents links should page to the slide, not just jump the scrollbar.
  document.querySelectorAll(".toc a").forEach(function (a) {
    a.addEventListener("click", function (e) {
      var i = secs.findIndex(function (s) { return "#" + s.id === a.getAttribute("href"); });
      if (i >= 0 && paged()) { e.preventDefault(); show(i); }
    });
  });

  addEventListener("scroll", function () {
    if (paged()) return;
    var h = document.documentElement.scrollHeight - innerHeight;
    bar.style.width = (h > 0 ? (scrollY / h) * 100 : 0) + "%";
  }, { passive: true });
})();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    sys.exit(main())
