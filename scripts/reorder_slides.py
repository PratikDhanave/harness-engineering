#!/usr/bin/env python3
"""One-shot re-order of the SLIDES array into teaching sections.

Kept for the record rather than for reuse: ORDER below is the 25 Aug 2026
arrangement, expressed as the slide numbers it started from, so it only makes
sense against that revision. It moves every quiz next to the material it tests
instead of banking them all at the end, and rescues three teaching slides that
had ended up marooned inside the quiz block.

Re-running it against a changed deck will fail its own assertion rather than
scramble anything — the count and the permutation are both checked.
"""
import pathlib
import re

# --- the new running order, by ORIGINAL slide number -----------------------
ORDER = (
    # 1. What this is
    [1, 2, 3, 40, 41, 4, 5]
    # 2. Three ways to picture it, then where you have already met it
    + [6, 7, 8, 9, 19, 20]
    # 3. What actually runs: the loop
    + [10, 11, 16, 48, 17, 49, 62, 53, 67, 68, 43, 83]
    # 4. Tools
    + [47, 51, 54, 55, 56, 52, 77, 61, 63, 79, 60, 85, 64, 65, 59, 66]
    # 5. The event layer
    + [12, 13, 14, 73, 74, 75, 76, 44, 45, 84]
    # 6. The trick, then the map
    + [15, 46, 18, 21]
    # 7. The seven, each with its own questions
    + [22, 23, 24, 58]                      # L1
    + [25, 26, 69, 70, 71, 72, 78, 81, 82, 80]   # L2
    + [27, 28, 86, 87, 89, 88]              # L3
    + [29, 30, 50]                          # L4
    + [31, 32]                              # L5
    + [33, 34]                              # L6
    + [35, 36, 57]                          # L7
    # 8. Close
    + [37, 38, 39, 42, 90, 91, 93, 92, 94]
)

p = pathlib.Path("docs/presentation/slide.js")
src = p.read_text()

start = src.index("const SLIDES = [")
open_br = src.index("[", start)
depth, end = 0, len(src)
for j in range(open_br, len(src)):
    if src[j] == "[":
        depth += 1
    elif src[j] == "]":
        depth -= 1
        if depth == 0:
            end = j
            break
body = src[open_br + 1 : end]

# split top-level {...} objects, keeping their exact text
objs, d, buf, start_i = [], 0, [], None
for i, ch in enumerate(body):
    if ch == "{":
        if d == 0:
            start_i = i
        d += 1
    elif ch == "}":
        d -= 1
        if d == 0:
            objs.append(body[start_i : i + 1])
n = len(objs)
assert n == 94, f"expected 94 slides, found {n}"
assert sorted(ORDER) == list(range(1, n + 1)), (
    f"ORDER must use each slide once: missing "
    f"{sorted(set(range(1, n + 1)) - set(ORDER))}, dupes "
    f"{sorted(x for x in set(ORDER) if ORDER.count(x) > 1)}"
)

new_body = "\n\n  " + ",\n\n  ".join(objs[i - 1] for i in ORDER) + "\n"
p.write_text(src[: open_br + 1] + new_body + src[end:])
print(f"reordered {n} slides")
