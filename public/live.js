/* live.js — runnable code panels for the Harness Engineering deck.
 *
 * Mounts a "▶ Run" panel into any element carrying
 * data-demo="guard|seam|durable|crash|sandbox|memory|router|hitl|redteam"
 * and executes the REAL modules from src/harness/ as CPython on WebAssembly (Pyodide).
 * The payload (inlined Python sources + build-time transcripts) comes from
 * live-payload.js, which scripts/build_live_demo.py generates. This file is the
 * runtime and is hand-maintained.
 *
 * Used by both surfaces, so there is one implementation:
 *   - the decks (index.html / clearroute.html), where slide.js swaps slides in and
 *     out of the DOM — a MutationObserver re-mounts panels as slides appear;
 *   - live-demo.html, the standalone page.
 *
 * Never dies on stage: if Pyodide can't load, each panel replays the real
 * transcript captured at build time and says so.
 */
(function () {
  "use strict";

  var P = window.LIVE_PAYLOAD;
  if (!P) { console.warn("[live] live-payload.js not loaded"); return; }

  var pyPromise = null;
  var statusListeners = [];
  // True once CPython has actually booted. Used to tell "the runtime never
  // loaded" (replay the transcript) apart from "the runtime loaded and the
  // Python raised" — reporting the second as "offline" hid real errors.
  var pyReady = false;

  function announce(kind, text) {
    statusListeners.forEach(function (fn) { fn(kind, text); });
  }

  function ensurePython() {
    if (pyPromise) return pyPromise;
    pyPromise = (async function () {
      announce("loading", "loading CPython (WebAssembly) — first run only");
      await new Promise(function (resolve, reject) {
        var s = document.createElement("script");
        s.src = P.pyodideBase + "pyodide.js";
        s.onload = resolve;
        s.onerror = function () { reject(new Error("pyodide CDN unreachable")); };
        document.head.appendChild(s);
      });
      var py = await loadPyodide({ indexURL: P.pyodideBase });
      // memory/thread.py and durable/sqlite_store.py import sqlite3, which is a
      // loadable package in Pyodide rather than a builtin. Tolerated if it fails:
      // only the memory panel needs it, and it degrades to its transcript.
      try { await py.loadPackage("sqlite3"); } catch (e) { /* memory panel replays */ }
      ["safety", "durable", "memory", "orchestration"].forEach(function (d) {
        py.FS.mkdirTree("/demo/harness/" + d);
      });
      Object.keys(P.files).forEach(function (path) {
        py.FS.writeFile("/demo/" + path, P.files[path]);
      });
      py.runPython("import sys; sys.path.insert(0, '/demo')");
      var v = py.runPython("import sys; sys.version.split()[0]");
      announce("ready", "CPython " + v + " — running the real harness modules");
      pyReady = true;
      return py;
    })();
    // A FAILED boot must not stay cached. pyPromise is memoised so CPython loads
    // once — but a rejected promise is memoised just as happily, so a single
    // transient CDN blip would disable every panel for the rest of the session
    // and the only cure would be reloading the page, mid-talk. Clearing it means
    // pressing Run again actually retries.
    pyPromise.catch(function () { pyPromise = null; });
    return pyPromise;
  }

  function codeFor(key, input) {
    // Function replacement, not a string: String.replace treats $&, $\', $` and
    // $1 in the REPLACEMENT as special. A pasted attack containing "$&" would
    // otherwise rewrite the snippet instead of being quoted into it.
    if (key === "guard") {
      return P.snippets.guard.replace("{msg}", function () { return JSON.stringify(input); });
    }
    return P.snippets[key];
  }

  function fallbackFor(key, presetLabel) {
    if (key !== "guard") return P.fallbacks[key];
    var k = "guard:" + presetLabel;
    return Object.prototype.hasOwnProperty.call(P.fallbacks, k) ? P.fallbacks[k] : null;
  }

  // ---- checkpoint storage for the real crash demo --------------------------
  // The `crash` panel is the only stateful one: the checkpoint has to outlive
  // the page, because the demo IS destroying the page. P.crashKey is composed
  // by the build from the same constants the Python uses, so these can never
  // drift onto two different keys.
  // Every access is guarded — Safari private mode throws on localStorage rather
  // than returning null, and a demo that throws on stage is worse than one that
  // degrades to its transcript.
  function storageWorks() {
    try {
      localStorage.setItem("__harness_probe", "1");
      localStorage.removeItem("__harness_probe");
      return true;
    } catch (e) { return false; }
  }
  function hasCheckpoint() {
    try { return localStorage.getItem(P.crashKey) !== null; } catch (e) { return false; }
  }
  function clearCheckpoint() {
    try { localStorage.removeItem(P.crashKey); } catch (e) { /* nothing to clear */ }
  }

  function lineNode(line) {
    // VERDICT is the punchline — give it a banner instead of a log line.
    if (/^VERDICT:/.test(line)) {
      var v = document.createElement("div");
      var body = line.replace(/^VERDICT:\s*/, "");
      v.className = "live-verdict "
        + (/BLOCKED|clean sweep|ran ONCE|never ran again|caught, not merged/i.test(body)
          ? "good" : "warn");
      v.textContent = body;
      return v;
    }
    var span = document.createElement("span");
    if (/^\(\d\)/.test(line)) span.className = "beat";          // act heading
    else if (/skipped |ran step|none —|recovered|outlived|read back|conforms|identical across/.test(line)) span.className = "ok";
    else if (/CRASH|caught it|REJECTED|U\+[0-9A-F]{4}/.test(line)) span.className = "no";
    span.textContent = line + "\n";
    return span;
  }

  // Reveal beat by beat. Instant output reads as a log dump; staged output reads
  // as a demo, and gives the room a second to follow each act. Click to skip.
  function reveal(el, text) {
    // A second run while the first is still staging would interleave two line
    // streams into one element. Finish any reveal already in flight first.
    if (el.__liveFinish) el.__liveFinish();
    el.textContent = "";
    var lines = text.split("\n");
    var step = Math.max(14, Math.min(70, Math.round(900 / Math.max(1, lines.length))));
    var i = 0, timer = null;

    function finish() {
      if (timer) { clearInterval(timer); timer = null; }
      while (i < lines.length) { el.appendChild(lineNode(lines[i])); i++; }
      el.scrollTop = el.scrollHeight;
      el.classList.remove("revealing");
      el.__liveFinish = null;
      el.removeEventListener("click", finish);
    }
    el.__liveFinish = finish;
    el.classList.add("revealing");
    el.addEventListener("click", finish);

    timer = setInterval(function () {
      if (i >= lines.length) { finish(); return; }
      el.appendChild(lineNode(lines[i]));
      i++;
      el.scrollTop = el.scrollHeight;
    }, step);
    return finish;
  }

  function mount(host) {
    if (host.dataset.liveMounted === "1") return;
    host.dataset.liveMounted = "1";

    var demo = host.dataset.demo;
    // web-talk.html sets data-live-inline: it is a scrolling document with room
    // for the panel, so the deck's overlay treatment is not wanted there.
    var compact = host.hasAttribute("data-compact")
      && !document.documentElement.hasAttribute("data-live-inline");
    var showCode = host.hasAttribute("data-code");

    var panel = document.createElement("div");
    panel.className = "live-panel" + (compact ? " compact" : "");

    // `crash` has no snippet of its own — it is two, split by a page reload —
    // so fall back to the phase that runs first.
    var codePre = null;
    if (showCode && (P.snippets[demo] || P.snippets[demo + "-start"])) {
      codePre = document.createElement("pre");
      codePre.className = "live-code";
      codePre.textContent = P.snippets[demo] || P.snippets[demo + "-start"];
      panel.appendChild(codePre);
    }

    var input = null;
    var activePreset = null;

    if (demo === "guard") {
      var chips = document.createElement("div");
      chips.className = "live-chips";
      P.presets.forEach(function (p, idx) {
        var b = document.createElement("button");
        b.className = "live-chip";
        b.type = "button";
        b.textContent = p.label;
        b.addEventListener("click", function () {
          input.value = p.text;
          activePreset = p.label;
          Array.prototype.forEach.call(chips.children, function (c) {
            c.classList.toggle("on", c === b);
          });
        });
        chips.appendChild(b);
        if (idx === (P.presets.length > 1 ? 1 : 0)) { activePreset = p.label; b.classList.add("on"); }
      });
      panel.appendChild(chips);

      input = document.createElement("textarea");
      input.className = "live-input";
      input.spellcheck = false;
      input.rows = compact ? 1 : 2;
      // Default to the injection preset when present, else whatever exists.
      input.value = (P.presets[1] || P.presets[0] || { text: "" }).text;
      input.addEventListener("input", function () {
        activePreset = null;
        Array.prototype.forEach.call(chips.children, function (c) { c.classList.remove("on"); });
      });
      panel.appendChild(input);
    }

    // ---- crash demo: phase banner ------------------------------------------
    // This panel is stateful across page loads, so it has to say which half of
    // the story it is in before the speaker presses anything.
    var isCrash = demo === "crash";
    var banner = null;
    if (isCrash) {
      banner = document.createElement("div");
      banner.className = "live-phase";
      panel.appendChild(banner);
    }

    var row = document.createElement("div");
    row.className = "live-row";
    var btn = document.createElement("button");
    btn.className = "live-run";
    btn.type = "button";
    btn.textContent = host.dataset.label || "▶ Run";
    row.appendChild(btn);
    var status = document.createElement("span");
    status.className = "live-status";
    row.appendChild(status);

    var reset = null;
    if (isCrash) {
      reset = document.createElement("button");
      reset.className = "live-reset";
      reset.type = "button";
      reset.textContent = "reset";
      reset.title = "Discard the checkpoint and arm the demo again";
      row.appendChild(reset);
    }
    panel.appendChild(row);

    var out = document.createElement("pre");
    out.className = "live-out";
    panel.appendChild(out);

    // The call-to-action after a successful first half. The reload is the demo,
    // so it gets a prompt the back row can read — not a line in the log.
    var cta = null;
    if (isCrash) {
      cta = document.createElement("div");
      cta.className = "live-cta";
      panel.appendChild(cta);
    }

    // Which snippet the button runs. Fixed for every other panel; for `crash`
    // it is decided by whether a checkpoint is sitting in localStorage.
    function demoKey() {
      if (!isCrash) return demo;
      return hasCheckpoint() ? "crash-resume" : "crash-start";
    }

    function checkpointStep() {
      try { return JSON.parse(localStorage.getItem(P.crashKey)).step; }
      catch (e) { return null; }
    }

    function syncPhase() {
      if (!isCrash) return;
      var armed = !hasCheckpoint();
      cta.className = "live-cta";
      cta.textContent = "";
      out.className = "live-out";
      out.textContent = "";
      btn.disabled = false;
      if (!storageWorks()) {
        banner.className = "live-phase blocked";
        banner.textContent =
          "localStorage is unavailable in this browser, so nothing can outlive a "
          + "reload here. The button replays the transcript captured at build time.";
        btn.textContent = "▶ Replay the crash";
        reset.style.display = "none";
        return;
      }
      reset.style.display = armed ? "none" : "";
      if (armed) {
        banner.className = "live-phase armed";
        banner.textContent = "No checkpoint stored. The run has not started.";
        btn.textContent = "▶ Start the run";
      } else {
        var s = checkpointStep();
        banner.className = "live-phase recovered";
        banner.textContent = "⟲ A checkpoint survived the reload — run banquet-42"
          + (s === null ? "" : ", last completed step " + (s + 1));
        btn.textContent = "▶ Resume the run";
      }
    }
    syncPhase();

    statusListeners.push(function (kind, text) {
      status.textContent = text;
      status.className = "live-status " + kind;
    });

    async function go() {
      // Freeze the phase for this run: crash-start WRITES the checkpoint, so
      // re-deriving the key afterwards would report the wrong half of the story.
      var key = demoKey();
      // Show exactly what is about to run: the guard panel substitutes the
      // presenter's message, and the crash panel swaps snippet between phases.
      if (codePre) codePre.textContent = codeFor(key, input ? input.value : "");
      out.classList.add("shown");
      out.textContent = "running…";
      btn.disabled = true;
      var ok = false;
      try {
        var py = await ensurePython();
        var buf = "";
        py.setStdout({ batched: function (s) { buf += s + "\n"; } });
        await py.runPythonAsync(codeFor(key, input ? input.value : ""));
        reveal(out, buf.replace(/\n$/, ""));
        ok = true;
      } catch (err) {
        var canned = fallbackFor(key, activePreset);
        var tag = document.createElement("div");
        tag.className = "live-replay";
        var rest = document.createElement("div");
        out.textContent = "";

        if (pyReady) {
          // CPython is up, so this is the demo's own Python raising — NOT a
          // connectivity problem. Reporting it as "offline" sent us hunting for
          // a network fault while the real traceback sat unread.
          announce("error", "the demo raised — this is a Python error, not a network one");
          tag.textContent = "PYTHON ERROR · the runtime is fine; this demo threw";
          out.appendChild(tag);
          out.appendChild(rest);
          reveal(rest, String((err && err.message) || err));
        } else {
          announce("offline", "offline — replaying the build-time transcript · press Run again to retry");
          tag.textContent = canned !== null
            ? "OFFLINE REPLAY · real output, captured at build time"
            : "OFFLINE · no transcript for hand-typed input";
          out.appendChild(tag);
          out.appendChild(rest);
          reveal(rest, canned !== null
            ? canned
            : "This input was typed live, so there is no pre-captured transcript.\n"
              + "Pick a preset above to replay a real one, or reconnect.");
        }
      } finally {
        btn.disabled = false;
      }

      if (!isCrash) return;

      if (!ok) {
        // Replayed, not executed — so no checkpoint was written and a reload
        // would find nothing. Say so rather than inviting a reload that fails.
        cta.className = "live-cta note";
        cta.textContent = "Replay only — CPython did not load, so no checkpoint "
          + "was actually written. The reload step needs a live run.";
        return;
      }

      if (key === "crash-start") {
        // The point of the whole panel. Lock the button so the next thing that
        // happens is the reload.
        btn.disabled = true;
        reset.style.display = "";
        cta.className = "live-cta go";
        cta.innerHTML =
          '<strong>Now reload the page — <kbd>⌘R</kbd> / <kbd>F5</kbd></strong>'
          + '<span>The Pyodide interpreter, every Python object, and this panel are '
          + 'destroyed. The deck comes back to this slide and the checkpoint is '
          + 'still there.</span>';
      } else {
        cta.className = "live-cta done";
        cta.textContent = "Run complete. Press reset to arm it again for the next "
          + "rehearsal.";
      }
    }

    btn.addEventListener("click", go);
    if (reset) {
      reset.addEventListener("click", function () {
        clearCheckpoint();
        syncPhase();
        announce("ready", "checkpoint discarded — demo armed");
      });
    }
    if (input) {
      input.addEventListener("keydown", function (e) {
        if ((e.metaKey || e.ctrlKey) && e.key === "Enter") { e.preventDefault(); go(); }
      });
    }

    if (!compact) { host.appendChild(panel); return; }

    // In-deck: a slide is a fixed-height canvas that is usually already full, so
    // the panel must not reflow it. Park it in an overlay behind a small trigger;
    // the slide looks exactly as designed until the speaker asks for the demo.
    var overlay = document.createElement("div");
    overlay.className = "live-overlay";
    var sheet = document.createElement("div");
    sheet.className = "live-sheet";
    var close = document.createElement("button");
    close.className = "live-close";
    close.type = "button";
    close.setAttribute("aria-label", "Close demo");
    close.textContent = "✕";
    sheet.appendChild(close);
    sheet.appendChild(panel);
    overlay.appendChild(sheet);

    var trigger = document.createElement("button");
    trigger.className = "live-trigger";
    trigger.type = "button";
    trigger.textContent = host.dataset.label || "▶ Run";

    function open() {
      overlay.classList.add("open");
      if (input) input.focus();
    }
    function shut() { overlay.classList.remove("open"); }

    trigger.addEventListener("click", open);
    close.addEventListener("click", shut);
    overlay.addEventListener("click", function (e) { if (e.target === overlay) shut(); });

    // `r` opens the demo on the current slide, Esc closes it. Both are ignored
    // while typing, and `r` is not used by the deck engine.
    document.addEventListener("keydown", function (e) {
      if (!host.isConnected || !host.closest(".slide.active")) return;
      var typing = /^(INPUT|TEXTAREA)$/.test((e.target && e.target.tagName) || "");
      if (e.key === "Escape") { shut(); return; }
      if (typing || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "r" || e.key === "R") { e.preventDefault(); open(); }
    });

    host.appendChild(trigger);
    host.appendChild(overlay);

    // Coming back from the reload, the speaker should not have to remember a
    // keystroke in front of the room: if a checkpoint is waiting and this is the
    // slide on screen, open straight into the resume half. Deferred a tick so
    // the deck has applied `.active` from the hash first.
    if (isCrash && hasCheckpoint()) {
      setTimeout(function () {
        if (host.isConnected && host.closest(".slide.active")) open();
      }, 0);
    }
  }

  var mounting = false;
  function mountAll(root) {
    // mount() appends into #deck, which the observer watches — so a naive
    // mountAll re-enters itself on every panel it creates. The liveMounted flag
    // made that terminate, but it still re-walked the tree once per insertion.
    if (mounting) return;
    mounting = true;
    try {
      (root || document).querySelectorAll("[data-demo]").forEach(mount);
    } finally {
      mounting = false;
    }
  }

  function start() {
    mountAll(document);
    // The decks re-render slides into #deck on every navigation, so panels have
    // to be (re)mounted as slides enter the DOM.
    var deck = document.getElementById("deck");
    if (deck && window.MutationObserver) {
      new MutationObserver(function () { mountAll(deck); }).observe(deck, {
        childList: true, subtree: true
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
