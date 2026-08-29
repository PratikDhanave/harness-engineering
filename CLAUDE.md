# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current state

**All 7 lessons are implemented locally** — each is a runnable, fully unit-tested module. Every
Azure dependency is **stubbed behind a seam** (Protocol/interface + local impl), so the whole suite
runs with no cloud setup or network. **Lesson 1 has its real Agent Framework side in two
modes**: `agents.py` defines the `ReplyAgent` seam behind `/chat`, selected by
`HARNESS_AGENT_MODE` — `stub` (default, no model at all) or `local`
(`FoundryLocalAgent` — a real Agent Framework `Agent` over an `OpenAIChatClient` pointed at
Foundry Local; needs **no** config: with `FOUNDRY_LOCAL_ENDPOINT` unset, the pinned
`foundry-local-sdk` boots the bundled runtime in-process — catalog → download-if-needed → load →
serve — for the alias in `FOUNDRY_LOCAL_MODEL`, default `phi-4-mini`; set the endpoint instead to
use a runtime you manage). Explicit modes fail loud on missing settings.

**There is no `azure` mode.** It was removed on 26 Aug 2026 and
`HARNESS_AGENT_MODE=azure` now raises with an explanation. `agent-framework-azure-ai` never
shipped past `1.0.0rc6`, and its open-ended `core>=1.0.0rc6` requirement pinned the whole stack
to the release candidates — which in turn blocked `agent-framework-orchestrations`. Dropping it
moved everything to current stable: `agent-framework-core>=1.15`, `-openai>=1.14`,
`-orchestrations>=1.1`. Do not reintroduce the azure-ai package without checking that it has
shipped a release compatible with a current core. **All seven lessons now also exist on the Agent Framework**
under `src/harness/af/`, each behind the same seam as its hand-written twin — six of them run
with no cloud at all (see `docs/agent-framework-map.md`, and `scripts/af_tour.py` to watch them).
Lesson 3 is the exception: Code Interpreter is a *hosted* tool, so there is nothing to build
locally. `docs/azure-implementation-plan.md` and `docs/architecture.md` remain the source of
truth for the managed shape.

Module → pattern map:
- `guardrails.py` + `agents.py` (L1), `workflow.py` + `durable/` (L2), `sandbox.py` (L3),
  `memory/` (L4: thread/knowledge/summarize), `orchestration/router.py` (L5),
  `orchestration/supervisor.py` (L6), `hitl.py` (L7, built on `durable/`).
- `safety/` augments L1: an evasion-resistant local stand-in for Content Safety Prompt Shields
  (`normalize` obfuscation-folding + heuristic attack-family `detectors` + a `redteam` corpus +
  scorer). `guardrails.check_input` re-checks its markers over folded text and runs the detectors,
  so the "trivially bypassed" marker list resists homoglyph/zero-width evasion. Still heuristic,
  not ML — states the leak. Design + threat model: `docs/safety-layer.md`.

The **seam pattern is the core convention**: a `typing.Protocol` (or injectable callable/table) with
a local implementation whose docstring names the Azure service it stands in for and honestly states
where the local stand-in is weaker ("state the leak"). Match this when adding code.

Two glossaries cross-reference the concepts: `docs/glossary.md` defines this repo's own vocabulary
(seam pattern, "state the leak", the 7 lessons and every store/executor/type they introduce), and
`docs/langgraph-glossary.md` maps every LangGraph primitive to the matching harness pattern, the repo
module that stands in for it, and the Agent Framework/Azure target (e.g. LangGraph checkpointer ↔
`durable/`, `interrupt()` ↔ `hitl.py`, `Send` fan-out ↔ `orchestration/supervisor.py`).

Before adding commands or architecture claims to this file, confirm them against real files.

## Commands

Tooling is `uv` (system Python is 3.9; the project requires ≥3.11 — `uv` provisions its own).
A `Makefile` wraps the common flows: `make install / model / test / run / run-local / demo /
clean` (the demo — `scripts/demo.sh` — boots the API and shows guardrail blocks incl. a homoglyph
and a letter-split case, then durable crash-resume; `clean` drops `.harness/` and `.pytest_cache`).

```bash
uv run --extra dev pytest              # run the test suite
uv run --extra dev pytest tests/test_guardrails.py::test_normal_input_allowed   # single test
uv run uvicorn harness.app:app --reload   # run the API locally (http://127.0.0.1:8000)
uv run uvicorn harness.app:app --reload --env-file .env   # /chat via the real Agent Framework
                                          # (HARNESS_AGENT_MODE=local is self-contained — the
                                          # bundled foundry-local-sdk boots the runtime and the
                                          # FIRST /chat downloads the model (~2–3 GB). There is no
                                          # azure mode any more; nothing auto-loads .env, the flag does)
```

Source layout: `src/harness/` (package `harness`), tests in `tests/`. `app.py` is the FastAPI
entrypoint (only `/health` and `/chat` are wired — `/chat` runs `guardrails.check_input` then the
`harness.agents` seam: a stub reply by default, a Microsoft Agent Framework agent when the two
Azure env vars are set; the other six lessons are standalone modules exercised only by their
tests — in both their local and their `harness/af/` Agent Framework forms — not mounted on the
API yet). `guardrails.py` holds the input-guardrail policy (hard-block on empty,
oversize, and prompt-injection markers — a local stand-in for Content Safety Prompt Shields). No
linter yet.

Two test-isolation conventions to preserve when touching the API: the agent is built **lazily**
by `app.get_agent` (an `lru_cache`d FastAPI dependency), so importing `app` never constructs
credentials or clients — tests swap it via `app.dependency_overrides[get_agent]`; and
`tests/conftest.py` autouse-clears all five agent env vars plus the cache, so a dev shell that
exports Foundry settings can't flip the suite onto a cloud/on-device path. Nothing auto-loads
`.env` — only the `--env-file` flag does (`.env.example` documents every variable).

**Every lesson slide shows the code it runs.** Slides 11-18 each carry a `<pre class="tight">`
sample (a compact variant added so a code block fits under a diagram and bullets without
overflowing), and every in-deck panel is marked `data-code`, so opening it shows the *exact*
snippet about to execute — the guard panel with the presenter's typed message substituted in, the
crash panel with whichever phase is next.

**A specificity bug hid a whole line of vertical budget.** `small, .small { font-size: ... }`
loses to `.slide p`, so every `<p class="small">` in the deck rendered at *full* paragraph size —
greyer, but not smaller. Fixed 24 Aug 2026 with an explicit `.slide p.small`. It is called out
because it is the exact shape of bug this deck keeps producing: no error, no visible breakage,
just silently less room on a page that clips without saying so.

**Checking that on screen is not enough.** The print box is a fixed 13.333x7.5in with
`overflow: hidden`, so content too tall is silently clipped — no error, it simply is not in the
PDF. Adding the code samples dropped four of them (L1, L2, L6, L7) from `harness-engineering.pdf`
while the browser showed no overflow at all, because screen slides are viewport-sized and print
slides are not. A separate trap sits underneath it: `<pre>` at a tight `line-height` shaved the
*underscores* off `run_durably(run_id, ...)` in the PDF and left every other character intact, so
the line looked almost right. Print-specific rules in `@media print` fix both — and
`tests/test_deck.py` now asserts every lesson slide carries a code sample, that all seven lessons
have a panel, that every panel is `data-code`, and that **the .pptx still contains each sample**,
which is the export check that would have caught it.

**Docs are part of the test suite.** `tests/test_docs.py` globs the `.md` files at the repo root
and in `docs/`, plus every `docs/*.excalidraw` — balanced code fences, resolvable in-page anchors,
valid Excalidraw JSON, no HTML-escape artifacts in `diagrams.md`. So editing docs can turn the
suite red, and **dropping any new `.md` at the root enrolls it automatically** (that is how
`session.md`, a historical log of the build session, and `harness-engineering-medium.md`, an
article draft, are covered). The globs do not recurse into subdirectories of `docs/`, so nothing
under `docs/presentation/` or `docs/diagrams/` is tested. The heavier
Mermaid render check is opt-in: `HARNESS_RENDER_MERMAID=1 uv run --extra dev pytest` (needs the
`mmdc` mermaid-cli on PATH); it's skipped by default, which is why a green run shows a few skips
(currently 187 passed, 3 skipped).

Untested asset directories, so you can tell generated output from source: `docs/diagrams/` holds
the README's archify repo map (typed `*.architecture.json` source + self-contained interactive
HTML + light/dark PNGs), and `docs/presentation/` holds the decks plus five more archify diagrams
in the same JSON→HTML→PNG triplet form. Regenerate a triplet rather than hand-editing the HTML
or PNG. **Nothing under `docs/presentation/` is covered by the suite** — `test_docs.py`'s globs
are `*.md` at the root and `docs/*.md`, and they do not recurse.

### Presentation: one source, many surfaces

`docs/presentation/README.md` is the full record. The load-bearing fact: **`slide.js`'s `SLIDES`
array is the single source of the talk.** Edit it and every surface below updates. Everything
except `slide.*`, `clearroute.css`, `live.js`/`live.css` and `talk-overview.html` is **generated —
never hand-edit it**, the next build overwrites you.

**The speaker portrait on slide 1 is a base64 `data:` URI inlined in `slide.js`.** There is no
asset file to copy, so `file://`, the `public/` bundle and the web-talks all carry it with no
extra plumbing. Two places consume it rather than holding a second copy: `deck_to_pptx.py`
(`portrait_png()` decodes the URI and bakes the circle into an alpha mask, because python-pptx
can embed neither a `data:` URI nor a rounded picture), and `build_web_talk.py` (whose masthead
restates slide 1 in its own markup, so it lifts the `<img>` out of the slide). Re-crop by
regenerating the base64 in place — do not add a file next to it.

| Surface | Built by | Notes |
|---|---|---|
| Google browser deck | `index.html` + `slide.css` + `slide.js` | White, Google Blue `#4285F4`, no red. `--print-to-pdf` → `harness-engineering.pdf`, 65 slides @960×540 (the quizzes build separately) |
| ClearRoute browser deck | `clearroute.html` + `clearroute.css` | A *skin* over slide.css — white paper, mint `#00E8AF` fills, deeper green `#009167` for text. `--print-to-pdf` → `harness-engineering-clearroute-talk.pdf`, 65 slides — **not** the preserved 24-slide `harness-engineering-clearroute.pdf` |
| Two `.pptx` builds | `scripts/deck_to_pptx.py [--theme=clearroute]` | Native editable text; the 6 inline-SVG diagrams are rasterised via headless Chrome |
| Live-code demo page | `scripts/build_live_demo.py` | `live-demo.html` + `live-payload.js` |
| The talk on the web | `scripts/build_web_talk.py [--theme=clearroute]` | `web-talk.html` (google) / `web-talk-clearroute.html` — paged like the deck, `s` toggles long-form reading, notes shown. **One output per theme**; they shared a filename until 21 Aug, so whichever build ran last silently overwrote the other |

```bash
uv run --with python-pptx python3 scripts/deck_to_pptx.py [--theme=clearroute]
uv run python3 scripts/build_live_demo.py      # after ANY change to guardrails/safety/workflow
uv run python3 scripts/build_web_talk.py [--theme=clearroute]
```

**Slides 4, 5 and 6 are three alternates of one idea, not a sequence.** The same seven patterns
as an operating system (engineers), a restaurant kitchen (mixed / client), and a flight deck
(risk, assurance, regulator). 5 and 6 deliberately share the *same* SVG geometry so the repeated
shape reads as "same seven, any domain". The speaker picks one for the room; the deck carries all
three so it can be re-aimed without a rewrite. Each one's speaker note says so, and each states a
different leak (ring 0 is hardware / a kitchen's controls assume a sanctionable actor / aviation
bought its record with an accident corpus we do not have). Do not "deduplicate" them into one.

**Never delete, overwrite, or merge one deck into another** (explicit user instruction). That
covers the preserved `harness-engineering-clearroute.pptx`/`.pdf` (24 slides @1440×828, the
house deck-builder output, Gotham — not generated here) and the `talk-overview` companion, a
5-page A4 narrative cut of the same story.

**Diagrams build rather than appear, and the timings are one system.** Parts fade in over
`.72s` across a `1.15s` stagger *budget* (a budget, not a per-element step — a per-element step
makes a 43-part figure take three times as long as a 13-part one). Arrows then draw with
`stroke-dashoffset` over `.95s` starting at `1.10s`, i.e. after the last box lands at ~`1.25s`;
a line drawn between two boxes that are still fading in reads as a glitch. Whole build ~3s.
Slowed from ~1.7s on 27 Aug 2026 because it finished before the room looked up. `a` replays it.

**The arrowhead is a presentation *attribute*, and that is a trap.** The engine hides it with an
inline `marker-end` while the line travels. Inline styles beat any print rule, and
`marker-end: revert` reverts to the *user-agent* value — `none` — not to the element's own
attribute. A print guard written that way silently printed **every diagram arrow as a headless
line**. The fix is `finaliseFigures()`, which clears the inline styles on `beforeprint` plus a
`matchMedia("print")` fallback (headless printing does not always fire `beforeprint`).
`tests/test_deck.py` guards both halves. Two earlier cuts of this same animation also failed
silently: one hid the whole arrow during the draw, so it drew under an invisible mask and popped
in complete; another restored the heads on a `setTimeout`, which fired from a *previous* visit to
the slide. Verify animation by rendering frames (`--virtual-time-budget=N --screenshot`) and
**looking at them** — every one of these bugs read as correct in `getComputedStyle`.

### Live code in the browser

`live.js` runs the **real modules** from `src/harness/` as CPython on WebAssembly (Pyodide), so
the guardrail that blocks a homoglyph on a slide is the same `check_input` the suite exercises.
`build_live_demo.py` inlines those sources into `live-payload.js` (so it works from `file://`
with no server) **and captures each demo's output by running it against local CPython** — if the
Pyodide CDN is unreachable, the panel replays that real transcript and labels itself. Panels
cover **all seven lessons**, via `data-demo` markers in `slide.js`; the `.pptx` parser
skips unknown `<div>`s, so they are invisible to it. Measured slide positions — **re-derive rather
than trusting this table**; it has been wrong twice. They move whenever a slide is inserted, a
stale `// 7 —` comment in `slide.js` already caused one wrong report, and the numbers below sat
unrevised through the quiz expansion, which put every one of them out by 14 or more.

Two numberings exist and they are not interchangeable. `SLIDES` currently holds **119** entries;
the presented deck is the **65** that survive the `noquiz` filter (`'<ul class="quiz">' in html`),
and that is what the PDFs and both `.pptx` paginate. The table below is the *presented* numbering.
Derive both with:

```bash
uv run python3 -c "
import re; h=re.findall(r'\n    html: \`(.*?)\`,\n', open('docs/presentation/slide.js').read(), re.S)
nq=[x for x in h if '<ul class=\"quiz\">' not in x]; print(len(h),'array /',len(nq),'presented')
[print(j, d.group(1)) for j,x in enumerate(nq,1) if (d:=re.search(r'data-demo=\"([^\"]+)\"',x))]"
```

Match the builder's own count (`parsed N slides` / `filter noquiz: N slides`) before believing a
number — a quick regex that segments on the *whole* slide object rather than its `html` field
misclassifies a slide whose **speaker note** quotes `<ul class="quiz">`, and silently undercounts.

| Slide | Demo | What it runs |
|---|---|---|
| 25 | `seam` | three backends, one workflow, a widened seam rejected |
| 30 | `guard` | L1 — the homoglyph the naive scan waves through |
| 32 | `crash` | L2 — checkpoint, real page reload, resume |
| 34 | `sandbox` | L3 — the browser refuses to spawn a process |
| 37 | `memory` | L4 — thread (real sqlite3) · knowledge · summarise |
| 41 | `router` | L5 — routes three, misses a paraphrase |
| 44 | `supervisor` | L6 — fan-out, one sub-agent fails, the batch survives |
| 47 | `hitl` | L7 — approve · reject · a late yes is void |
| 51 | `redteam` | the red-team corpus scored |

**Each lesson is two slides: concept, then example.** The concept slide carries the
before/after diagram, one line of small print and a 2-4 line signature; the **example slide**
carries a fuller worked excerpt of the code that actually runs, plus the runnable panel.

**The deck is pitched at students (24 Aug 2026) — plain language, and the diagram is the body
of the slide.** The seven patterns and the slide order are unchanged; the wording is. Jargon
that a first-year would not have met is gone from the slides and lives only in the speaker
notes: seam, Protocol, middleware, invariant, fan-out/fan-in, idempotent, homoglyph, RAG. The
patterns are named as verbs — check, survive, isolate, remember, route, split up, ask — and the
old names survive in `docs/` and in the code. **Do not quietly re-raise the register**; if a
slide needs a term, gloss it on the slide or leave it in the notes.

**An eighteen-slide recap closes the talk (24 Aug 2026): thirty multiple-choice quizzes then two
click-to-reveal card slides.** The author chose to keep the quiz bank *in the deck* rather than
split it into a companion artifact, and to include the Vercel AI SDK questions. Two consequences
to hold on to:

- **The AI SDK slide must keep its framing line.** This project does **not** use the AI SDK; the
  slide is there because a module-per-provider is the seam pattern in another ecosystem. Without
  that sentence the deck starts to read as a TypeScript-course port, which the framing rule
  above forbids.
- **Slide 11, "How the harness talks to itself", describes what this repo does NOT build** — the
  agent loop as a `runtime` file, an `emit` bus, a WebSocket transport, shared event definitions.
  Our API is request/response and the tool loop is rented. The slide says so in its small print;
  keep that, or the deck claims an event layer that does not exist.
- **"Runtime" is now overloaded on purpose.** Slide 4 onward uses it for the whole harness; the
  loop quiz notes many codebases use it for the one file holding the agent loop. Both slides
  name the clash rather than pretending it away. They are *progressive enhancement*, and the reason matters —
the correct answer is marked in the **HTML source** (`<li class="right">`, `<p class="a">`),
never injected by script. So:

- **On screen** CSS hides it until a click; `slide.js`'s engine has one delegated listener
  (`.card.qa` toggles `.open`, `.quiz li` adds `.picked` and `.answered`).
- **In the PDF** an `@media print` block reveals it, because a handout has nobody to click it.
- **In the .pptx** `deck_to_pptx.py` reads the HTML and never sees CSS, so it had to be taught
  the flag explicitly: `ul` parsing now keeps which `<li>` is `right` and renders it bold with
  a green bullet and a ✓. Without that the .pptx shipped a quiz with no answer on it.

Verified in a real browser, not by inspection — a headless probe clicks a wrong option and
asserts the computed backgrounds actually change. Do that again if you touch the markup;
"the class is in the file" is not evidence the click works.

**The pair that defines the terms comes before anything else** (24 Aug 2026) — *an agent is a
model plus a harness*, then the six things a harness actually provides. Without a harness you
have one-off, transactional inference calls — ask, answer, forget. Everything after those two
slides is an answer to "so what goes in the harness", so do not reorder them behind the
analogy slides. They were slides 2 and 3 when that was written; the front of the deck has grown
since, and they are now 7 and 8.

**Slide 6, "The words we will use", is a reference card, not a teaching slide** (29 Aug 2026).
Ten rows: *harness* and *durable execution* defined, then the seven patterns in the same verb
phrasings the rest of the deck uses, so the vocabulary never shifts under a student. It sits
*before* the definitional pair on purpose — the room gets the words on arrival and can come back
to one page rather than hunting. Two things to preserve:

- **The seven rows must stay verbatim identical to the names used elsewhere** (slide 17's "You
  already use all seven", and each lesson's own title). The whole value is that they match; a
  reworded row here silently teaches two names for one thing.
- **It has no vertical budget left.** It fills the print box almost exactly, and the first cut
  overflowed *upward* — the `h2` rose into the accent rule that `@media print` pins at `0.55in`,
  and that collision was the only visible symptom. `table.lessons.gloss` gives the name column a
  `15em` floor so two rows do not wrap to a second line each; without it the page is over. If you
  add a row, take a line out somewhere else, then re-render page 6 and **look at it**.

**L4 shows four kinds of memory, and the repo builds three.** The diagram names short-term,
long-term, scratch pad and facts because that is what a harness handles; `memory/` implements
thread, knowledge and summarise, and there is **no scratch pad**. The slide says so. If a
scratch-pad store lands, update the slide's small print — do not let the picture drift into a
claim. (The before/after panel helper takes 3 or 4 rows and keeps the same panel height; four
rows switch to a tighter row size automatically.)

Three diagram jobs came in with that rewrite, all from
`scripts/build_pattern_diagrams.py` (author-time only — it does **not** run at build time; you
paste its SVG into `slide.js` by hand, because a `${...}` in a slide would reach the .pptx
parser unexpanded):

- **One big map, slide 10** — the whole system on one page, request in at top left, answer out
  at bottom right, every pattern in place.
- **A "you are here" strip** — the same seven chips with the current one lit, baked into the
  *top of each pattern's SVG* rather than added as a second element. That is deliberate:
  `rasterise_svgs` takes **one diagram per slide** (`svg_png[idx]`), so a separate strip would
  be dropped from both .pptx builds without erroring.
- **A before/after pair** — the same situation without the pattern and with it, side by side.
  This is what a student actually takes away, so it gets the vertical budget: the concept
  slides' bullet lists were cut to a single line of small print to pay for it.

**What Pyodide can and cannot do** — measured, not assumed, because it decides what is demoable:

- `sqlite3` is **not** a builtin; it is a loadable package. `live.js` calls
  `loadPackage("sqlite3")` at startup, which is what lets `memory/thread.py` run unmodified.
- **No threads.** `ThreadPoolExecutor` imports and then raises `RuntimeError: can't start new
  thread`. `supervisor.py` therefore takes an **injectable `executor_factory`** (keyword-only,
  defaulting to `ThreadPoolExecutor`) — a second seam alongside `worker`, added 21 Aug 2026 so
  Lesson 6 could run in a browser at all. The panel injects a synchronous executor and **says
  what that gives up**: fault isolation and decomposition-order output are real, the parallelism
  is not. Never let that demo imply otherwise.
- **No subprocess.** `subprocess` imports and `run()` raises `OSError`. That is *why* L3 has a
  panel: it calls the real `run_code`, gets refused, and the refusal is the lesson —
  `sandbox.py`'s own docstring admits a subprocess is not a security boundary, and the browser
  is one that actually enforces it. The snippet is written to read correctly in both
  environments, because the build-time capture runs where subprocess *does* work.

**Slide 7's `seam` panel runs the convention the slide describes.** The slide claims you can
swap local for Azure without touching the workflow logic; that is falsifiable, so the panel runs
it — three `CheckpointStore` implementations (dict, localStorage standing in for Cosmos, and an
audit wrapper proving the seam composes), the same `run_durably` from `src/harness/` over all
three, identical results, then a fourth implementation that adds a `tenant` argument and is
rejected. The conformance check compares parameter names **exactly**, which is stricter than
structural typing on purpose: it is `SEALED_DRAFT_PARAMS` in miniature, and name-pinning is what
stops a seam widening one reasonable-looking argument at a time. The build fails if the three
results are not identical or if the widened one is not rejected — so the slide cannot keep
claiming this after it stops being true.

**The `crash` panel is the only stateful one, and the only demo that is performed rather
than depicted.** The other panels simulate their failure inside one process. This one checkpoints
to the browser's `localStorage` through a `BrowserCheckpointStore` — the same `CheckpointStore`
Protocol as the SQLite and Cosmos stores, so the real `run_durably` runs unmodified — and then the
speaker **actually reloads the page**, destroying the Pyodide interpreter and every Python object
in it. It is two snippets (`crash-start` / `crash-resume`), not one with a branch, because what
separates them is a real page load. Consequences worth knowing before touching it:

- **The localStorage key is a cross-language contract.** Python composes it from `KEY_PREFIX` +
  `RUN_ID` in `CRASH_PRELUDE`; `live.js` reads and clears the same key to decide which phase to
  show. It is emitted once as `payload.crashKey` and asserted against the prelude at build time —
  do not retype it in either language.
- **The build proves the demo's claim.** `build_live_demo.py` captures the pair as a genuine
  two-process sequence (run start, keep only the stored bytes, run resume in a fresh namespace)
  and then fails the build if the resume re-executed step-1/step-2, if `ran` isn't empty, or if
  the run didn't finish. The panel asserts "the work was not redone" on stage; these checks are
  what stop that from silently becoming false. Match the *side-effect marker*, not the step name —
  the first cut of that guard matched the word "step-1" inside a narration line and failed a
  correct build.
- **It degrades rather than lies.** `localStorage` throws (not returns null) in Safari private
  mode, so every access is wrapped; with storage unavailable, or Pyodide offline, the panel says
  so and replays the transcript instead of inviting a reload that would prove nothing.

Four traps this code has already fallen into — all of them fail *silently* and look fine:

- **Broken generated JS kills the whole `<script>`.** An unquoted value renders a perfect-looking
  page whose buttons do nothing, with no console error. Both build scripts now fail loudly if a
  generated JS global isn't a valid literal.
- **Two paths to the same demo can disagree.** The browser runs `payload.snippets`; the fallbacks
  come from Python `.format()`. Ship the raw template and the live run prints a literal
  `{r.reason}` while the captured transcript looks correct — i.e. it only breaks on stage.
- **Skins must load *after* `live.css`.** The `--live-*` colour tokens are overridden at equal
  specificity, so source order decides. Link the skin first and panels silently stay blue in a
  mint deck.
- **A slides-only rebuild silently disarms a deployment that had demos.**
  `build_public_site.py` defaults to slides-only, so running it bare overwrites `public/` and
  drops `live.js`/`live-payload.js`. Nothing errors; the next `vercel deploy` just quietly ships a
  deck whose panels are gone. The live site currently runs **`--with-demos`** — check what the
  deployment actually serves (`curl -o /dev/null -w '%{http_code}' <url>/live-payload.js`) before
  rebuilding the bundle.

### Deploying the published deck

Live at **https://harness-engineering-talk.vercel.app** (Vercel project
`harness-engineering-talk`, team `clearroute`). Production is public; previews are team-only
via `ssoProtection: preview`.

**Do not run `vercel deploy` from inside `public/`.** It has failed 4/4 times — the CLI either
hangs at status `UNKNOWN` for 25+ minutes on nine static files, or dies with `fetch failed`,
while the identical bundle deploys in seconds from outside the repo. The difference is that
`public/` sits inside a git repository, which is itself nested in a ~525-repo workspace; the
CLI's git detection is what stalls. Copy the bundle somewhere outside any repo — **including
`.vercel/`, or the deploy silently creates a *new* project** (that is how a stray project named
`public` came to exist) and **excluding `.env.local`** — then deploy from there:

```bash
D=$(mktemp -d)                      # must not be inside a git repo
cp public/{index.html,live-demo.html,live-payload.js,live.css,live.js,robots.txt,slide.css,slide.js,vercel.json} "$D/"
cp -r public/.vercel "$D/.vercel"; cp public/.vercelignore "$D/"
cd "$D" && npx vercel deploy --prod --yes
```

Then verify against the URL rather than trusting the CLI — it has reported failure on a
deployment that succeeded, and success on one that never went live:

```bash
curl -s <url>/slide.js | grep -o 'notes: "[^"]' | wc -l   # MUST be 0 — presenter-only, not for readers
```

Durable-execution and HITL tests write checkpoints to a local `.harness/` SQLite store (gitignored)
— the local stand-in for the Cosmos DB checkpoint store.

CI is a single GitHub Actions job (`.github/workflows/ci.yml`, on push to `main` + every PR):
`astral-sh/setup-uv@v5` on Python 3.11, then `uv run --extra dev pytest -q`. **No secrets and no
cloud** — that is a property to preserve, and it is why every Azure dependency sits behind a seam.
Since docs are part of the suite, a docs-only edit can fail CI.

## What this project is

A learning project that builds the **7 "harness engineering" patterns** in **pure Python** on the
**Microsoft Agent Framework** and **Azure AI Foundry**.

**Framing rule for anything audience-facing** (deck, article, talk-overview, README): present this
as pure Python on the Microsoft Agent Framework. Do **not** frame it as a port of a TypeScript
course, and do not use the "change the altitude, not the syllabus" line — that framing was removed
on 21 Aug 2026 at the author's request. A factual provenance citation stays in
`docs/architecture.md`'s reference list; that is a citation, not a frame.

The full blueprint lives in `docs/azure-implementation-plan.md`; **read it first** when starting
any implementation work. It is the source of truth for architecture and the lesson-by-lesson plan.

Remaining work is the **Roadmap table in `README.md`** — 12 items, each one a seam with a local
implementation and no managed one. It replaced a project board on a private account that returned
404 for everyone else once this repo went public. Check it before proposing "what's next".

## Language note (important)

Despite living under a Go `GOPATH`-style path (`.../go/src/github.com/...`), this project is
**Python, not Go**. The directory location is incidental. Do not scaffold Go tooling. The
toolchain is Python + `uv` + `pytest` (confirmed — see Commands above).

## Intended architecture (from the plan)

The design deliberately offloads the "harness" to managed Azure services and spends effort on
orchestration, guardrails, and observability rather than from-scratch infrastructure. Two layers
do the work:

- **Azure AI Foundry — Agent Service** provides the *agents*: model calls + tool loop, managed
  threads (memory), and sandboxed tools (Code Interpreter, File Search, Function, AI Search).
- **Microsoft Agent Framework** (Python `agent-framework`) provides the *harness around agents*:
  middleware/guardrails, durable checkpointed workflows, multi-agent orchestration, and
  human-in-the-loop.

Our own code is a **FastAPI orchestration API** (planned for Azure Container Apps) that drives
these agents. The 7 course patterns map to 7 build increments ("lessons") — see section 4 of the
plan. Each lesson is framed as "Azure provides X / you build Y," so keep implementations thin:
prefer managed primitives over hand-rolled infrastructure.

## Working rules

Decisions already made — follow these unless the user says otherwise:

- **Keep implementations thin.** Prefer managed Azure primitives (Agent Service tools, managed
  threads, Content Safety, Agent Framework workflows) over hand-rolled infrastructure. If a lesson
  can be solved by configuring a managed service, don't build it from scratch.
- **Pin preview versions.** Microsoft Agent Framework is public preview with a shifting API. Pin
  exact versions in `pyproject.toml` and re-verify APIs against current docs before each lesson.
- **Keyless auth first.** Use Managed Identity + `DefaultAzureCredential`; fall back to Key Vault
  only where a service requires a key. Never commit real secrets — `.env` is gitignored. Note the
  azure path needs the **async** credential (`azure.identity.aio`): a sync one constructs fine and
  then fails at the first token fetch.
- **Explicit modes fail loud.** A mode the operator asked for must never be silently swapped for
  another (a `.env` flow that quietly answered from the stub is exactly the bug this rule came
  from). Auto-detect only applies when `HARNESS_AGENT_MODE` is unset.
- **This repo is handed out at workshops.** The confidentiality notice was removed on 26 Aug 2026 when it became teaching material, and the demo examples were made domain-neutral at the same time — no client terminology in tracked files. Speaker notes are **presenter-only, not secret** — that is the settled position, and the repo
  used to contradict itself about it. They are stripped from the published *web bundle* (blanked,
  not deleted, so the array shape holds) because a reader of the site is not the presenter. They
  ship in full in `docs/presentation/slide.js`, which is public. If that ever needs to change, the
  strip has to move into the deck source, not just the bundle.

## Maintaining this file

Local code has landed (all 7 lessons, tested), and all 7 now have Agent Framework
implementations in `harness/af/` as well; `agents.py` remains the only path that reaches a
real cloud. Keep the two states distinct here — describe what's runnable today under "Current state"/"Commands", and keep the
managed/Azure design in `docs/architecture.md` and `docs/azure-implementation-plan.md` rather than
duplicating it into this file. When you wire a lesson to Azure, update the "Current state" map and
add the real build/deploy commands. Confirm every command and architecture claim against the actual
files before writing it (this file's module map and commands were verified against the tree).

**`live-payload.js` contains an inlined copy of `src/harness/`.** Editing `guardrails.py`,
`safety/` or `workflow.py` leaves the browser demos running the *old* code, and nothing fails —
the suite is green and the page still works. Re-run `scripts/build_live_demo.py` as part of any
such change.
