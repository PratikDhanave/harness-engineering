# Presentation assets

Two decks live here, deliberately. **Neither replaces the other — do not delete,
overwrite, or consolidate one into the other.**
### The quizzes are a separate handout

`slide.js` holds every slide — the talk and all 54 multiple-choice quizzes. Each
surface then selects a **view** of it, so nothing is duplicated and adding a
quiz still means editing one file:

| Surface | How it selects |
|---|---|
| `index.html`, `clearroute.html` | `window.DECK_FILTER = "noquiz"` before `slide.js` → the 64-slide talk |
| `quiz.html` | `window.DECK_FILTER = "quiz"` → the 54 quizzes |
| `deck_to_pptx.py` | `--filter=noquiz` (default) or `--filter=quiz`; the quiz build writes to a `-quiz` filename so it cannot overwrite the talk |
| `build_web_talk.py` | filters to the talk |

```bash
uv run python3 scripts/export_quiz.py     # → harness-engineering-quiz.json (54 entries)
```

The JSON carries `question`, `options` (with `correct`), `answer`, `explanation`
and `speaker_note`. It **fails the build** if any quiz does not have exactly one
marked answer. Note the notes are presenter-only — think before putting that
file anywhere public.

**The quiz PDF prints the answers.** `@media print` reveals them, because a
handout has nobody to click. Good as an answer key, not as a blind test.


## Setup — building these from a clean machine

Nothing here is on the repo's dependency list, because none of it is needed to run the
project or its tests. Install only what the surface you are rebuilding requires.

| To rebuild | You need | Check |
|---|---|---|
| Browser decks (`index.html`, `clearroute.html`) | nothing — open the file | `open docs/presentation/index.html` |
| The two PDFs | Google Chrome at the path below | `ls "/Applications/Google Chrome.app"` |
| The two `.pptx` | `python-pptx` **and** Chrome (it rasterises the inline SVG diagrams) | `uv run --with python-pptx python3 -c "import pptx"` |
| `live-payload.js` | nothing beyond the repo's own deps — it runs `src/harness/` under local CPython to capture each transcript | `uv run python3 scripts/build_live_demo.py` |
| The web-talks, `public/` | nothing extra | — |
| Deploying `public/` | `npx vercel` and access to the `clearroute` team | `npx vercel whoami` |

`CHROME` is hardcoded in `scripts/deck_to_pptx.py` as
`/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` — macOS only today. Point it
at your own binary on Linux/Windows; nothing else in the chain is platform-specific.

**Rebuild everything after editing `slide.js`**, in this order — the PDFs read the HTML, and
`public/` copies the finished files:

```bash
uv run --with python-pptx python3 scripts/deck_to_pptx.py
uv run --with python-pptx python3 scripts/deck_to_pptx.py --theme=clearroute
uv run python3 scripts/build_web_talk.py
uv run python3 scripts/build_web_talk.py --theme=clearroute
cd docs/presentation && for d in "index:harness-engineering" "clearroute:harness-engineering-clearroute-talk"; do
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu \
    --no-pdf-header-footer --print-to-pdf="${d#*:}.pdf" "file://$PWD/${d%%:*}.html"
done; cd ../..
uv run python3 scripts/build_public_site.py --with-demos    # NEVER bare — see below
uv run --extra dev pytest tests/test_deck.py tests/test_live_payload.py -q
```

If you touched `guardrails.py`, `safety/`, `workflow.py` or anything else under
`src/harness/` that a panel runs, add `scripts/build_live_demo.py` **first** — the browser
demos hold an inlined copy of that source, and a stale copy fails nothing.

Then check the PDF by **looking at the pages**, not by extracting their text. The print box is
a fixed 13.333x7.5in with `overflow: hidden`, so content that is too tall is silently dropped;
and `pdftotext` has produced false negatives here twice (dropped underscores in one font, split
aligned columns into separate runs). `pdftoppm -f 1 -l 1 -r 90 -png <pdf> /tmp/p` and open it.

## 1. Google-format deck (preserved)

The original talk deck, in the Google visual language: white background, Google Blue
`#4285F4`, Google Green `#188038` for "done" pills, Google Sans stack, no red.

| File | What it is |
|---|---|
| `index.html` | Shell page — hosts the deck engine |
| `slide.js` | **The content**: a `SLIDES` array of `{ html, notes }`, plus the nav engine |
| `slide.css` | The Google palette (`:root` block) and print rules |
| `harness-engineering.pdf` | **Exported deck — 64 slides, 960x540 (16:9)**. The 54 quizzes ship separately as `harness-engineering-quiz.pdf` |
| `harness-engineering.pptx` | **Native PowerPoint replica of the same 64 slides** (generated — see below) |
| `talk-overview.html` → `talk-overview.pdf` | 4-page A4 companion doc, same palette — narrative cut |

Regenerate the PDF with headless Chrome (`--headless --print-to-pdf`); the deck's
`@media print` block gives one 16:9 slide per page. Edit the talk by editing the
`SLIDES` array in `slide.js`, and keep the palette in `slide.css` in sync with the
inline `:root` in `talk-overview.html`.

The companion doc is a **story**, not an abstract: it opens on the four ways a demo
agent dies in production, then resolves each one against the pattern that fixes it
(the seven-pattern table is keyed `failure → pattern → module`), and closes on the
war stories — preview-package drift, the sync/async credential, the silent fallback.
It shares the deck's palette and narrative order. Re-export it the same way:

```bash
cd docs/presentation && "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="talk-overview.pdf" "file://$PWD/talk-overview.html"
```

**This deck is the narrative bar for every other deck**: which-harness disambiguation →
thesis → **the OS mental model** → two layers → architecture → seam pattern with code →
seven-lessons table → one idea per lesson → docs-as-tests → status/how-to-run → takeaways.

Slide 4 is the frame the rest hangs on: *if the model is a process, the runtime is the OS*,
mapping all seven patterns onto syscall validation, journaling, namespaces, paging, the
scheduler, supervision trees and `sudo` — then stating the leak (ring 0 is hardware-enforced;
this boundary is software). The deck says "runtime" from slide 2 onward; "harness" stays as
the name of the discipline.

### The .pptx replica

`harness-engineering.pptx` is a **native PowerPoint build of the Google deck** — same
64 slides, same 960x540 geometry, same palette — produced by
`scripts/deck_to_pptx.py`, which parses the `SLIDES` array directly. It is
generated output: **edit `slide.js` and re-run, never hand-edit the .pptx**, or the
next run overwrites your changes.

```bash
uv run --with python-pptx python3 scripts/deck_to_pptx.py
```

Text is real, editable PowerPoint text; the six inline-SVG diagrams are rasterised
with headless Chrome and embedded as pictures. Speaker notes carry over. Fonts are
Helvetica Neue / Menlo (the macOS end of the deck's CSS font stack) — retarget them
to Arial / Consolas if the deck is going to a Windows machine.

## 2. ClearRoute-format deck (current format for new decks)

`harness-engineering-clearroute.pptx` / `.pdf` — 24 slides, 1440x828, built with the
ClearRoute deck-builder template (dark navy `#212837` + mint `#00E8AF`, Gotham fonts,
rendered via LibreOffice). This is the house format for *new* decks. Gotcha: Gotham
isn't installed locally, so LibreOffice substitutes a serif for "Gotham Medium" —
retarget those runs to "Gotham Bold" before rendering a PDF locally.

## 3. ClearRoute-skinned talk deck — browser + .pptx

The **Google deck's 64 slides in the ClearRoute palette** — white paper, ClearRoute
mint — in two forms.

Mint `#00E8AF` is bright, so it is used for **fills** (the rule, badges, the progress
bar) while **text and code** take the deeper house green `#009167`, which clears
contrast on white. That is the same `--accent` / `--accent-dk` split the Google deck
makes with its two blues. Headings are house navy `#121A24`, cards are white
separated by a hairline rather than a fill.

**Run it in a browser:** open `clearroute.html` (works from `file://`, no server).
Same keys as the light deck: `← →` navigate · `o` overview · `s` notes · `f`
fullscreen · `#N` deep-links a slide.

| File | What it is |
|---|---|
| `clearroute.html` | Shell — loads `slide.css` then `clearroute.css` |
| `clearroute.css` | **The skin**: re-points slide.css's `:root` vars at the ClearRoute palette, patches the few hardcoded Google values, and recolours the inline SVGs |
| `slide.js` | Unchanged — **one copy of the talk**, shared with `index.html` |
| `harness-engineering-clearroute-talk.pptx` | Native PowerPoint, 64 slides, ClearRoute palette (generated) |
| `harness-engineering-clearroute-talk.pdf` | **Exported ClearRoute deck — 64 slides, 960x540.** Distinct from the preserved 24-slide `harness-engineering-clearroute.pdf`, which is house deck-builder output in Gotham and must not be overwritten |
| `web-talk-clearroute.html` | The paged web version, ClearRoute skin |

Because the content and engine stay in `slide.js`, editing the `SLIDES` array
updates the Google deck, the ClearRoute deck, and both .pptx builds at once.

The diagrams hardcode the Google hexes as SVG presentation attributes; a CSS
property always beats a presentation attribute, so `clearroute.css` re-points them
with `[fill="#..."]` / `[stroke="#..."]` selectors — the same mapping the .pptx
generator applies via `svg_map`. Change one, change the other.

Export to PDF the same way as the light deck (`--headless --print-to-pdf`) —
verified at 19 pages, 960x540.

**PowerPoint build:** `harness-engineering-clearroute-talk.pptx`, same generator,
same canvas (960x540), different theme:

```bash
uv run --with python-pptx python3 scripts/deck_to_pptx.py --theme=clearroute
```

This is a *third* deck, not a replacement — deck 1 and deck 2 are both untouched by
it, and the same never-merge rule applies to all three.

Beyond the colour swap, the six inline-SVG diagrams have their Google blues
re-pointed at the ClearRoute greens (`svg_map` in the theme — the SVGs hardcode the
hexes). The rest of each diagram is left alone: they are already drawn for white
paper.

**Typography is deliberately the Google deck's, not Gotham.** Both ClearRoute builds
keep `slide.css`'s `--sans` / `--mono` stack, so the Google and ClearRoute decks
are typographically identical and *only* the palette differs. To switch to the house
face, set `--sans` in `clearroute.css` and the `"sans"` key in the generator's
`clearroute` theme — both are commented at the point of change. (Gotham is not
installed here, so it would fall back anyway; and note the 24-slide deck above sets
most of its body text in Courier New, which this one does not.)

Palette and canvas differ deliberately from deck 2: this is the *talk* deck restyled,
not the house template. The house deck-builder canvas is 1440x828.

## 4. Live code — in the deck, and standalone

Conference-style "run it on stage" — **built into the deck's flow**, and also
available as a standalone page.

**In the deck.** Nine slides carry a runnable panel, covering all seven lessons; the marker lives in
`slide.js` so both decks (and neither .pptx) pick it up automatically:

| Slide | Demo | Trigger |
|---|---|---|
| 11 — The one trick | `seam` — three impls, one workflow, a widened seam rejected | `▶ Prove it — swap the storage` |
| 16 — L1 example | `guard` — editable input, five presets | `▶ Run this example` or press `r` |
| 18 — L2 example | `crash` — checkpoint, **a real page reload**, resume | `▶ Run this example` |
| 20 — L3 example | `sandbox` — the browser **refuses** to spawn a process | `▶ Run this example` |
| 22 — L4 example | `memory` — thread (**real sqlite3**), knowledge, summarise | `▶ Run this example` |
| 24 — L5 example | `router` — routes three, misses one worded differently | `▶ Run this example` |
| 26 — L6 example | `supervisor` — fan-out, one sub-agent fails | `▶ Run this example` |
| 28 — L7 example | `hitl` — approve · reject · **a late yes is void** | `▶ Run this example` |
| 29 — Docs as tests | `redteam` — score the corpus | `▶ Score the attack corpus` |

**Every lesson is two slides: concept, then example.** The concept slide holds the
before/after diagram, one line of small print and a short signature; the example
slide holds a fuller worked excerpt of the code that runs, and the panel.

## The recap section (slides 33-42)

Three multiple-choice quizzes, then two slides of click-to-reveal cards. Built as
progressive enhancement so the same markup works on all three surfaces:

| Surface | How the answer appears |
|---|---|
| Browser | Hidden until clicked. One delegated listener in `slide.js`'s engine |
| PDF | Always shown — `@media print` reveals it, since a handout cannot be clicked |
| `.pptx` | Always shown — `deck_to_pptx.py` keeps the `<li class="right">` flag and renders it bold, green bullet, ✓ |

The answer lives in the **HTML source**, never in script. That is what makes all three
surfaces agree. If you add a question, mark the right option `class="right"` and add the
answer as `<p class="a">` — nothing else is needed.

Check the browser behaviour by actually clicking it. A headless probe that clicks a wrong
option and asserts the computed background changed is what caught this being right; the
class being present in the file proves nothing about whether the listener fired.

## Definitions first (24 Aug 2026)

Slides 2 and 3 answer the two questions a mixed room asks before anything else:

- **What is the relationship between an agent, a model and a harness?** An agent is a
  model *plus* a harness. Without one you have an LLM making one-off, transactional
  calls — ask, answer, forget. The harness is what turns it into something that does a
  job. Diagram: `agent_equation()`.
- **What does a harness actually provide?** Conversation, memory, tools, durable
  execution for long jobs, self-healing and resilience, and a choice of architectures —
  plus input checking and a human gate, which together are the seven patterns.

Keep them ahead of the analogy slides. Everything after is an answer to "so what goes in
the harness", and the analogies only land once the word means something.

**L4 shows four kinds of memory; the repo builds three.** The diagram names short-term,
long-term, scratch pad and facts, because that is what a harness handles. `memory/`
implements thread, knowledge and summarise — there is **no scratch pad**, and the slide
says so out loud. If one lands, update the slide; do not let the picture drift into a claim.

## Pitched at students (24 Aug 2026)

The seven patterns and the slide order did not change. The **wording** did, and the
diagrams became the body of the slide rather than an illustration next to it.

- **Plain language.** Terms a first-year would not have met — seam, Protocol,
  middleware, invariant, fan-out/fan-in, idempotent, homoglyph, RAG — are gone from
  the slides and kept in the speaker notes, where the presenter can reach for them if
  the room turns out to want them. The patterns are named as verbs: check, survive,
  isolate, remember, route, split up, ask. The formal names are unchanged in `docs/`
  and in the code. **Do not quietly put the jargon back.**
- **One big map, slide 10.** The whole system on a page: a request arrives top left,
  an answer leaves bottom right, and every pattern sits where it actually runs.
- **A "you are here" strip** on each pattern slide — the same seven chips with the
  current one lit. It is drawn *inside* that slide's SVG, not added beside it, because
  `rasterise_svgs` takes **one diagram per slide**; a second one would be silently
  dropped from both `.pptx` builds.
- **A before/after pair** on each pattern slide — the same situation without the
  pattern and with it. This is the part a student remembers, so it gets the space:
  the concept slides' bullet lists were cut to a single line of small print to pay
  for it, and the print cap for `.diagram.wide` went from 37vh to 44vh.

The pictures come from `scripts/build_pattern_diagrams.py`. It is an **author-time**
tool: it prints SVG that you paste into `slide.js` by hand. Nothing calls it during a
build, and a change made there does not reach the deck until it is pasted — slide.js
has to stay a single literal source that the `.pptx` parser and the web-talk builder
can both read as plain text.

**L6 needed a source change to be runnable.** Pyodide cannot start threads, so
`supervisor.py` now takes an injectable `executor_factory` (keyword-only,
defaulting to `ThreadPoolExecutor`) — a second seam alongside `worker`. The
panel injects a synchronous executor and states the leak: fault isolation and
output ordering are real, the parallelism is not.

**Every lesson slide also shows its code.** Slides 11-18 carry a compact
`<pre class="tight">` sample, and every panel is `data-code`, so opening one
shows the exact snippet about to run.

Those slide numbers move whenever a slide is inserted — re-derive them from the
`data-demo` markers rather than trusting this table.

**Two of these are performed, not depicted, and that is the point.** Slide 13's
`crash` panel checkpoints to the browser's `localStorage` through a store
implementing the same `CheckpointStore` Protocol as the SQLite and Cosmos ones,
then the speaker **actually reloads the page** — destroying the Pyodide
interpreter and every Python object in it. The resume runs in a new CPython
where `ran` starts empty, yet the completed steps do not re-execute. Slide 7's
`seam` panel runs the claim that slide makes: the same `run_durably` over three
different backends, identical results, then a fourth implementation that adds a
parameter and is **rejected**. Both are checked at build time, so neither slide
can keep claiming something after it stops being true.

**Each demo is told in three beats, not dumped as a log.** "It got blocked" is a
fact; the story is watching the naive check wave the attack through first. The
guard demo runs: (1) the twenty-line substring scan — *nothing matched, it sails
straight through*; (2) the character that made it invisible, printed with its
codepoint (`pos 5  U+0435  CYRILLIC SMALL LETTER IE`) so the room can *see* what
their eyes could not; (3) fold and re-match, then a **VERDICT** banner. Durable
follows the same shape, and prints `skipped step-1 (already checkpointed)`
explicitly rather than leaving the audience to infer it from an absence.

Output is revealed line by line (~0.9s total, click to skip) with a blinking
caret. Instant output reads as a log dump; staged output reads as a demo and
gives the room a beat to follow each act.

A slide is a fixed-height canvas and slide 9 is already full, so the panel does
**not** sit inline — it opens as an overlay over the slide (`Esc` closes). The
slide keeps its designed layout; all you see until you want the demo is a small
pill in the bottom-left. Panels are hidden in `@media print`, so the exported
`harness-engineering.pdf` is unchanged — verified.

**Panel colours follow the palette.** `live.css` defines five tokens —
`--live-tint`, `--live-tint-bd`, `--live-key`, `--live-ok`, `--live-warn` —
defaulting to the Google blues; `clearroute.css` re-points them to mint. Nothing
in `live.css` hardcodes a brand colour, so a new skin re-tints every chip, caret,
verdict and callout by setting those five.

`--live-ok` is deliberately a *light* blue (`#8ab4f8`): it is used on the dark
output block, where `#1a73e8` is unreadable.

**Load order matters.** A skin must be linked *after* `live.css` — the token
overrides have equal specificity, so source order decides. Link it before and
the panels silently stay blue in a mint deck.

Files: `live.js` (runtime, hand-maintained) · `live.css` (styles) ·
`live-payload.js` (**generated** — inlined Python + build-time transcripts).
Removing the two `<script>` lines from a deck shell disables the panels and the
deck still works.

 **Standalone.** `live-demo.html` is the same three panels on one scrollable page,
with the code listings shown. It executes the **real
modules** from `src/harness/` in the browser as CPython compiled to WebAssembly
(Pyodide). The `check_input` that blocks a homoglyph on the projector is the same
function `tests/test_guardrails.py` exercises; nothing is mocked.

```bash
uv run python3 scripts/build_live_demo.py      # regenerate after touching the modules
```

Three panels: **L1** input guardrail (editable — take an attack from the room and
paste it in, five presets incl. homoglyph and zero-width), **L2** durable execution
(crash at step 3, resume, watch completed steps get skipped), **L1+** red-team the
guardrail (scores the standing corpus live).

Two properties that matter when you are standing in front of people:

- **No server.** The Python sources are inlined at build time, so it runs from
  `file://` — verified. (`fetch()` of local files is CORS-blocked anyway, which is
  why inlining rather than fetching is the right call here.)
- **It cannot die on bad conference wifi.** Every panel's output is captured at
  build time by running the demo against local CPython. If Pyodide can't load, the
  page replays that real transcript and labels itself `OFFLINE REPLAY` — honest,
  and the talk keeps moving. Only Pyodide itself (~10 MB, first load) needs network.

Generated output — edit `src/harness/` or the demo snippets in the build script and
re-run; never hand-edit the HTML. The build fails loudly if a generated JS global
isn't a valid literal (an unquoted value silently kills the whole `<script>`, which
is exactly how the first build broke).

## 5. The talk on the web (`web-talk.html`)

The whole talk as one page you can send someone. **Presents slide-by-slide by
default** — `← →` / space / click `‹ ›`, same feel as the deck — with the eight
runnable panels **inline on the slide** rather than behind an overlay, plus the
speaker notes promoted to visible commentary. Same `slide.js` source as
everything else.

Press **`s`** (or the `scroll` button) to flip the same page into long-form
reading view: every section stacked, for someone catching up on their own. `f`
is fullscreen; `#s9` deep-links a slide in either mode, and the contents list
pages straight to a section.

```bash
uv run python3 scripts/build_web_talk.py                      # -> web-talk.html
uv run python3 scripts/build_web_talk.py --theme=clearroute   # -> web-talk-clearroute.html
```

**One output file per theme.** Both wrote to `web-talk.html` until 21 Aug 2026,
so whichever build ran last silently overwrote the other and the two could never
coexist.

`slide.css` on its own **is** the Google palette; `clearroute.css` is a skin
layered over it, so the theme flag simply decides whether that second stylesheet
is linked.

It reuses `slide.css` for components and keeps the deck's own `.slide` class on
each section, overriding only the fixed-canvas layout — the same trick
`slide.css`'s `@media print` block uses. Drop that class and every `.slide h2 …`
rule silently stops applying (the lesson badges render as bare `L1` text glued to
the heading; that is exactly what happened on the first build).

**To host it**, copy these six files to any static host — all paths are relative,
no build step, no server-side anything:

```
web-talk.html   slide.css   clearroute.css   live.css   live.js   live-payload.js
```

Verified working over plain HTTP as well as `file://`. The only network call is
Pyodide's CDN on the first Run; without it the panels replay their build-time
transcripts and say so.

> **Speaker notes never go to the published bundle.** They are presenter-only —
> `build_public_site.py` blanks them, and the deploy check asserts zero remain.

## 6. Diagrams

Five archify diagrams, each as a triplet — typed source JSON, a self-contained
interactive HTML viewer, and a dark PNG for embedding:

`harness-azure` (architecture) · `harness-request` (sequence) · `harness-memory`
(dataflow) · `harness-orchestration` (workflow) · `harness-run-lifecycle` (lifecycle)

Regenerate the triplet rather than hand-editing the HTML or the PNG.

> Nothing in this directory is covered by `tests/test_docs.py` — its globs are
> `*.md` at the repo root and `docs/*.md`, and they do not recurse.
