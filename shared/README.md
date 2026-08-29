# `shared/` — a frozen hand-out copy, not the current deck

**If you want the talk, do not use these files.** They are a point-in-time copy taken on
**21 August 2026** and kept for reference. The deck has moved on substantially since.

| | here in `shared/` | current, in [`docs/presentation/`](../docs/presentation/) |
|---|---|---|
| `harness-engineering.pdf` | **28 pages** | **64 pages** + a separate 54-question quiz handout |
| `slide.js` | 66 KB | 377 KB |
| Last changed | 21 Aug 2026 | current |

Everything the talk is generated from lives in **[`docs/presentation/`](../docs/presentation/)** —
one `SLIDES` array in `slide.js` builds two browser decks, four PowerPoints, three PDFs, two web
versions and the deployable bundle. See
[`docs/presentation/README.md`](../docs/presentation/README.md).

There is a **third** copy of `slide.js` in [`public/`](../public/): the deployed web bundle, which
is generated and has its speaker notes blanked. So, to be unambiguous:

| Copy | What it is | Edit it? |
|---|---|---|
| `docs/presentation/slide.js` | **the single source of the talk** | **yes — this one** |
| `public/slide.js` | generated web bundle, notes blanked | no — rebuilt by `scripts/build_public_site.py` |
| `shared/slide.js` | frozen 21 Aug hand-out | no — kept as a record |

Kept rather than deleted deliberately: a deck that has been handed to people is a record of what
they were given, and overwriting it would destroy that.
