/* slide.js — the Harness Engineering deck: content + a tiny dependency-free engine.
 *
 * Open ./index.html in any browser (works from file://, no server/build needed).
 * Navigate: ← → / Space / PageUp-Down · Home/End · click ‹ › · o overview · s notes · f fullscreen.
 *
 * Every fact here is drawn from this repo (CLAUDE.md, README.md, docs/, src/harness/**, tests/**).
 * To edit the talk, edit the SLIDES array below — each entry is { html, notes }.
 */

const SLIDES = [
  // 1 — TITLE
  {
    html: `
      <div class="kicker">Azure · Python · Microsoft Agent Framework</div>
      <h1>Harness Engineering</h1>
      <div class="sub">Seven patterns for putting an AI agent into production — re-built in Python on managed Azure primitives.</div>
      <div class="meta">A local-first practice project &nbsp;·&nbsp; all 7 lessons implemented &amp; tested</div>
    `,
    cls: "title",
    notes: "One-line hook: an LLM on its own is not a product. The 'harness' is everything you wrap around the model to make it safe, durable, and useful in production. This deck walks the seven patterns and how each maps onto a managed Azure service."
  },

  // 2 — TWO MEANINGS
  {
    html: `
      <h2>First: which "harness"?</h2>
      <p class="lead">The term is overloaded. Two different things share the name — this project is the first one.</p>
      <div class="cols">
        <div class="card">
          <span class="tag">This project</span>
          <h3 class="accent">Runtime harness</h3>
          <p>The scaffolding wrapped <b>around a deployed agent</b>: guardrails, memory, tools, orchestration, human-in-the-loop. Built here in <b>Python on the Microsoft Agent Framework</b>.</p>
        </div>
        <div class="card">
          <span class="tag">Not this project</span>
          <h3 class="accent-2">Dev-time harness</h3>
          <p>OpenAI's "humans steer, agents execute" — the environment &amp; feedback loops that let <b>coding agents write your software</b>. Same words, different layer.</p>
        </div>
      </div>
      <p class="small">We're building the harness an agent runs <i>inside</i>, not the harness a team builds software <i>with</i>. <b>From here on we'll call it the runtime</b> — same thing, no collision.</p>
    `,
    notes: "Pre-empt the confusion. If someone in the audience read OpenAI's 'harness engineering' post, clarify up front that this is the runtime meaning. Both are about 'scaffolding around agents' — but one is production runtime, the other is a development methodology."
  },

  // 3 — THE THESIS
  {
    html: `
      <h2>The thesis</h2>
      <p>Seven runtime patterns, built in <b>pure Python</b> on the <b>Microsoft Agent Framework</b>:</p>
      <ul class="big">
        <li><b>Agent Framework gives you the harness</b> — middleware, checkpointed workflows, multi-agent orchestration, human-in-the-loop.</li>
        <li><b>Azure AI Foundry gives you the agents</b> — the model call, the tool loop, managed threads, sandboxed tools.</li>
        <li>You write the <b>orchestration, the guardrails and the observability</b> — not the plumbing underneath them.</li>
      </ul>
      <p class="small">Working rule throughout: <span class="k">keep implementations thin</span>. If a pattern can be solved by configuring a managed primitive, don't hand-roll it.</p>
    `,
    notes: "The core design decision, and the one line to land: this is pure Python on the Microsoft Agent Framework. Two layers do the work — Agent Framework is the harness AROUND agents (middleware, durable workflows, orchestration, HITL), Foundry Agent Service is the agents themselves (model call, tool loop, managed threads, sandboxed tools). The payoff is less infrastructure code and more attention on the interesting agent problems. Every pattern that follows is framed the same way: the platform provides X, you build Y."
  },

  // 4 — THE MENTAL MODEL
  {
    html: `
      <h2>An operating system for your agent</h2>
      <p class="lead">If the model is a <b>process</b>, the runtime is the <b>OS</b>.</p>
      <table class="lessons">
        <tr><th>#</th><th>Pattern</th><th>What it is, in OS terms</th></tr>
        <tr><td class="n">1</td><td>Guardrails</td><td>syscall validation — <code>seccomp</code></td></tr>
        <tr><td class="n">2</td><td>Durable execution</td><td>journaling · checkpoint / restore</td></tr>
        <tr><td class="n">3</td><td>Sandboxing</td><td>process isolation · namespaces</td></tr>
        <tr><td class="n">4</td><td>Memory</td><td>RAM · disk · paging</td></tr>
        <tr><td class="n">5</td><td>Orchestration</td><td>the scheduler</td></tr>
        <tr><td class="n">6</td><td>Supervision</td><td>a process supervision tree</td></tr>
        <tr><td class="n">7</td><td>Human-in-the-loop</td><td><code>sudo</code></td></tr>
      </table>
      <p class="small">Nobody writes their own scheduler any more. <b>Azure gives you the OS; you write the program.</b> One honest gap: ring 0 is enforced by <i>hardware</i> — this boundary is software. <span class="k">state the leak</span>.</p>
    `,
    notes: "The mental model for the whole talk, and the ENGINEERING cut of it — PICK ONE of slides 4/5/6 for the room (4 engineers · 5 mixed or client · 6 risk/assurance/regulator); they are alternates, not a sequence. The model is untrusted code, so it gets a process, not the run of the machine — and every pattern coming up is something an OS already does. Two to land hard: L1 is syscall validation (the kernel distrusts userspace for exactly the reason we distrust model output), and L7 is sudo — a privileged action stops and asks a human. Say the caveat out loud: ring 0 is hardware-enforced, ours is convention. Overselling isolation is the one thing this talk must not do. ALTERNATE FRAME for a risk/assurance/client room — same seven, as controls: 1 pre-trade risk check (rejected before it reaches the market) · 2 the ledger, append-only, replay never redo · 3 segregation of duties, whatever acts cannot also settle · 4 the book of record · 5 routing to the right desk · 6 the desk head owning the aggregate · 7 four-eyes / maker-checker above a threshold. This one is not a metaphor for the architecture, it IS the architecture: I5 append-only audit is a ledger, I3 human gate is maker-checker. Its leak is sharper than ring 0: controls assume an actor who can be sanctioned, and a model cannot be — so every control must be PREVENTIVE, not detective. 'We'll catch it in review' is not a control when the thing under review generated a thousand outputs overnight."
  },

  // 5 — THE SAME SEVEN, PLAIN LANGUAGE
  {
    html: `
      <h2>Or: the same seven, without the jargon</h2>
      <p class="lead">If the model is the <b>cook</b>, the runtime is the <b>kitchen around them</b>.</p>
      <div class="diagram wide trace"><svg viewBox="0 0 960 300" role="img" aria-label="A restaurant kitchen: the seven harness patterns as a kitchen">
<style>text{font-family:'Google Sans','Product Sans',Roboto,system-ui,sans-serif}</style>
<defs>
  <marker id="k-ah" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M0 0L10 5L0 10z" fill="#5f6368"/>
  </marker>
</defs>

<!-- 1 · deliveries in -->
<rect x="14" y="112" width="132" height="60" rx="10" fill="#fff" stroke="#dadce0" stroke-width="1.5"/>
<text x="80" y="138" text-anchor="middle" font-size="15" fill="#202124">Deliveries</text>
<text x="80" y="157" text-anchor="middle" font-size="11.5" fill="#5f6368">whatever turns up</text>

<line x1="146" y1="142" x2="184" y2="142" stroke="#5f6368" stroke-width="1.5" marker-end="url(#k-ah)"/>

<rect x="186" y="106" width="150" height="72" rx="11" fill="#fef7e0" stroke="#f9ab00" stroke-width="1.8"/>
<text x="261" y="132" text-anchor="middle" font-size="15" fill="#202124">Check at the door</text>
<text x="261" y="151" text-anchor="middle" font-size="11.5" fill="#5f6368">spoiled stock turned away</text>
<circle cx="188" cy="108" r="9" fill="#f9ab00"/><text x="188" y="112" text-anchor="middle" font-size="11" font-weight="700" fill="#fff">1</text>

<line x1="336" y1="142" x2="374" y2="142" stroke="#5f6368" stroke-width="1.5" marker-end="url(#k-ah)"/>

<!-- 3 · separate boards -->
<rect x="376" y="100" width="146" height="84" rx="11" fill="#fff" stroke="#4285f4" stroke-width="1.7"/>
<text x="449" y="126" text-anchor="middle" font-size="15" fill="#202124">Separate boards</text>
<text x="449" y="145" text-anchor="middle" font-size="11.5" fill="#5f6368">raw never touches</text>
<text x="449" y="161" text-anchor="middle" font-size="11.5" fill="#5f6368">the salad board</text>
<circle cx="378" cy="102" r="9" fill="#4285f4"/><text x="378" y="106" text-anchor="middle" font-size="11" font-weight="700" fill="#fff">3</text>

<line x1="522" y1="142" x2="560" y2="142" stroke="#5f6368" stroke-width="1.5" marker-end="url(#k-ah)"/>

<!-- 5 · the pass -->
<rect x="562" y="112" width="104" height="60" rx="10" fill="#e8f0fe" stroke="#4285f4" stroke-width="1.8"/>
<text x="614" y="138" text-anchor="middle" font-size="15" fill="#202124">The pass</text>
<text x="614" y="157" text-anchor="middle" font-size="11.5" fill="#5f6368">sends the order</text>
<circle cx="564" cy="114" r="9" fill="#4285f4"/><text x="564" y="118" text-anchor="middle" font-size="11" font-weight="700" fill="#fff">5</text>

<!-- 6 · stations -->
<line x1="666" y1="132" x2="706" y2="96"  stroke="#5f6368" stroke-width="1.4" marker-end="url(#k-ah)"/>
<line x1="666" y1="142" x2="706" y2="142" stroke="#5f6368" stroke-width="1.4" marker-end="url(#k-ah)"/>
<line x1="666" y1="152" x2="706" y2="188" stroke="#5f6368" stroke-width="1.4" marker-end="url(#k-ah)"/>
<rect x="708" y="74"  width="104" height="42" rx="8" fill="#fff" stroke="#dadce0" stroke-width="1.4"/>
<text x="760" y="100" text-anchor="middle" font-size="13.5" fill="#202124">Grill</text>
<rect x="708" y="122" width="104" height="42" rx="8" fill="#fff" stroke="#dadce0" stroke-width="1.4"/>
<text x="760" y="148" text-anchor="middle" font-size="13.5" fill="#202124">Salad</text>
<rect x="708" y="170" width="104" height="42" rx="8" fill="#fff" stroke="#dadce0" stroke-width="1.4"/>
<text x="760" y="196" text-anchor="middle" font-size="13.5" fill="#202124">Pastry</text>
<rect x="700" y="64" width="120" height="158" rx="12" fill="none" stroke="#9aa0a6" stroke-width="1.2" stroke-dasharray="5 4"/>
<text x="760" y="240" text-anchor="middle" font-size="11.5" fill="#5f6368">head chef splits the banquet</text>
<circle cx="700" cy="64" r="9" fill="#4285f4"/><text x="700" y="68" text-anchor="middle" font-size="11" font-weight="700" fill="#fff">6</text>

<!-- 7 · head chef gate -->
<line x1="820" y1="142" x2="856" y2="142" stroke="#5f6368" stroke-width="1.5" marker-end="url(#k-ah)"/>
<rect x="858" y="106" width="88" height="72" rx="11" fill="#e6f4ea" stroke="#188038" stroke-width="1.8"/>
<text x="902" y="132" text-anchor="middle" font-size="14" fill="#202124">Head chef</text>
<text x="902" y="150" text-anchor="middle" font-size="11.5" fill="#5f6368">nothing leaves</text>
<text x="902" y="165" text-anchor="middle" font-size="11.5" fill="#5f6368">unseen</text>
<circle cx="860" cy="108" r="9" fill="#188038"/><text x="860" y="112" text-anchor="middle" font-size="11" font-weight="700" fill="#fff">7</text>

<!-- 2 · ticket rail (above) -->
<rect x="186" y="20" width="480" height="46" rx="9" fill="#fff" stroke="#4285f4" stroke-width="1.6" stroke-dasharray="6 4"/>
<text x="426" y="41" text-anchor="middle" font-size="14" fill="#202124">Ticket rail — every order written down</text>
<text x="426" y="57" text-anchor="middle" font-size="11.5" fill="#5f6368">drop a pan and you pick up from the tickets; you don't re-cook the starters</text>
<circle cx="188" cy="22" r="9" fill="#4285f4"/><text x="188" y="26" text-anchor="middle" font-size="11" font-weight="700" fill="#fff">2</text>
<line x1="614" y1="66" x2="614" y2="106" stroke="#4285f4" stroke-width="1.3" stroke-dasharray="4 3" marker-end="url(#k-ah)"/>

<!-- 4 · memory (below) -->
<rect x="186" y="236" width="480" height="46" rx="9" fill="#f1f3f4" stroke="#dadce0" stroke-width="1.4"/>
<text x="426" y="257" text-anchor="middle" font-size="14" fill="#202124">This table's ticket · the recipe book · the prep list</text>
<text x="426" y="273" text-anchor="middle" font-size="11.5" fill="#5f6368">right now · everything we know · what we boiled down before service</text>
<circle cx="188" cy="238" r="9" fill="#5f6368"/><text x="188" y="242" text-anchor="middle" font-size="11" font-weight="700" fill="#fff">4</text>
<line x1="449" y1="236" x2="449" y2="188" stroke="#9aa0a6" stroke-width="1.3" stroke-dasharray="4 3" marker-end="url(#k-ah)"/>
<circle class="tracer" r="7" fill="#4285f4" stroke="#fff" stroke-width="2" opacity="0"/>
</svg></div>
      <p class="small">Nobody builds a kitchen from scratch to open a restaurant. <b>Azure gives you the kitchen; you decide the menu.</b></p>
    `,
    notes: "The plain-language pass. PICK ONE of slides 4/5/6 for the room in front of you — engineers get the OS, a mixed or client room gets the kitchen, a risk/assurance/regulator room gets the flight deck. They are alternates, not a sequence; showing all three is three minutes of metaphor before any content. Two to point at: the ticket rail IS durable execution (written down, survives the disaster, nobody re-cooks the starters), and the pass is a human gate everyone has physically watched happen. Say the leak out loud — it is the same point as ring 0, but a non-technical room actually feels it."
  },

  // 6 — THE SAME SEVEN, FOR A SAFETY-CRITICAL ROOM
  {
    html: `
      <h2>Or: the same seven, on a flight deck</h2>
      <p class="lead">If the model is the <b>autopilot</b>, the runtime is the <b>aircraft around it</b>.</p>
      <div class="diagram wide trace"><svg viewBox="0 0 960 300" role="img" aria-label="A flight deck: the seven harness patterns as commercial aviation safety practice">
<style>text{font-family:'Google Sans','Product Sans',Roboto,system-ui,sans-serif}</style>
<defs>
  <marker id="f-ah" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M0 0L10 5L0 10z" fill="#5f6368"/>
  </marker>
</defs>

<!-- flight plan in -->
<rect x="14" y="112" width="132" height="60" rx="10" fill="#fff" stroke="#dadce0" stroke-width="1.5"/>
<text x="80" y="138" text-anchor="middle" font-size="15" fill="#202124">Flight plan</text>
<text x="80" y="157" text-anchor="middle" font-size="11.5" fill="#5f6368">whatever is filed</text>

<line x1="146" y1="142" x2="184" y2="142" stroke="#5f6368" stroke-width="1.5" marker-end="url(#f-ah)"/>

<!-- 1 · pre-flight checklist -->
<rect x="186" y="106" width="150" height="72" rx="11" fill="#fef7e0" stroke="#f9ab00" stroke-width="1.8"/>
<text x="261" y="132" text-anchor="middle" font-size="15" fill="#202124">Pre-flight checklist</text>
<text x="261" y="151" text-anchor="middle" font-size="11.5" fill="#5f6368">nothing taxis until it passes</text>
<circle cx="188" cy="108" r="9" fill="#f9ab00"/><text x="188" y="112" text-anchor="middle" font-size="11" font-weight="700" fill="#fff">1</text>

<line x1="336" y1="142" x2="374" y2="142" stroke="#5f6368" stroke-width="1.5" marker-end="url(#f-ah)"/>

<!-- 3 · envelope protection -->
<rect x="376" y="100" width="146" height="84" rx="11" fill="#fff" stroke="#4285f4" stroke-width="1.7"/>
<text x="449" y="126" text-anchor="middle" font-size="15" fill="#202124">Envelope protection</text>
<text x="449" y="145" text-anchor="middle" font-size="11.5" fill="#5f6368">the aircraft refuses</text>
<text x="449" y="161" text-anchor="middle" font-size="11.5" fill="#5f6368">what is out of limits</text>
<circle cx="378" cy="102" r="9" fill="#4285f4"/><text x="378" y="106" text-anchor="middle" font-size="11" font-weight="700" fill="#fff">3</text>

<line x1="522" y1="142" x2="560" y2="142" stroke="#5f6368" stroke-width="1.5" marker-end="url(#f-ah)"/>

<!-- 5 · air traffic control -->
<rect x="562" y="112" width="104" height="60" rx="10" fill="#e8f0fe" stroke="#4285f4" stroke-width="1.8"/>
<text x="614" y="138" text-anchor="middle" font-size="15" fill="#202124">ATC</text>
<text x="614" y="157" text-anchor="middle" font-size="11.5" fill="#5f6368">assigns the route</text>
<circle cx="564" cy="114" r="9" fill="#4285f4"/><text x="564" y="118" text-anchor="middle" font-size="11" font-weight="700" fill="#fff">5</text>

<!-- 6 · crew stations -->
<line x1="666" y1="132" x2="706" y2="96"  stroke="#5f6368" stroke-width="1.4" marker-end="url(#f-ah)"/>
<line x1="666" y1="142" x2="706" y2="142" stroke="#5f6368" stroke-width="1.4" marker-end="url(#f-ah)"/>
<line x1="666" y1="152" x2="706" y2="188" stroke="#5f6368" stroke-width="1.4" marker-end="url(#f-ah)"/>
<rect x="708" y="74"  width="104" height="42" rx="8" fill="#fff" stroke="#dadce0" stroke-width="1.4"/>
<text x="760" y="100" text-anchor="middle" font-size="13.5" fill="#202124">Pilot flying</text>
<rect x="708" y="122" width="104" height="42" rx="8" fill="#fff" stroke="#dadce0" stroke-width="1.4"/>
<text x="760" y="148" text-anchor="middle" font-size="13.5" fill="#202124">Monitoring</text>
<rect x="708" y="170" width="104" height="42" rx="8" fill="#fff" stroke="#dadce0" stroke-width="1.4"/>
<text x="760" y="196" text-anchor="middle" font-size="13.5" fill="#202124">Cabin crew</text>
<rect x="700" y="64" width="120" height="158" rx="12" fill="none" stroke="#9aa0a6" stroke-width="1.2" stroke-dasharray="5 4"/>
<text x="760" y="240" text-anchor="middle" font-size="11.5" fill="#5f6368">the captain divides the work</text>
<circle cx="700" cy="64" r="9" fill="#4285f4"/><text x="700" y="68" text-anchor="middle" font-size="11" font-weight="700" fill="#fff">6</text>

<!-- 7 · captain's authority -->
<line x1="820" y1="142" x2="856" y2="142" stroke="#5f6368" stroke-width="1.5" marker-end="url(#f-ah)"/>
<rect x="858" y="106" width="88" height="72" rx="11" fill="#e6f4ea" stroke="#188038" stroke-width="1.8"/>
<text x="902" y="132" text-anchor="middle" font-size="14" fill="#202124">Captain</text>
<text x="902" y="150" text-anchor="middle" font-size="11.5" fill="#5f6368">nothing leaves</text>
<text x="902" y="165" text-anchor="middle" font-size="11.5" fill="#5f6368">unsigned</text>
<circle cx="860" cy="108" r="9" fill="#188038"/><text x="860" y="112" text-anchor="middle" font-size="11" font-weight="700" fill="#fff">7</text>

<!-- 2 · flight data recorder (above) -->
<rect x="186" y="20" width="480" height="46" rx="9" fill="#fff" stroke="#4285f4" stroke-width="1.6" stroke-dasharray="6 4"/>
<text x="426" y="41" text-anchor="middle" font-size="14" fill="#202124">Flight data recorder — every action written down</text>
<text x="426" y="57" text-anchor="middle" font-size="11.5" fill="#5f6368">after an incident you replay the tape; you do not fly the leg again to find out</text>
<circle cx="188" cy="22" r="9" fill="#4285f4"/><text x="188" y="26" text-anchor="middle" font-size="11" font-weight="700" fill="#fff">2</text>
<line x1="614" y1="66" x2="614" y2="106" stroke="#4285f4" stroke-width="1.3" stroke-dasharray="4 3" marker-end="url(#f-ah)"/>

<!-- 4 · memory (below) -->
<rect x="186" y="236" width="480" height="46" rx="9" fill="#f1f3f4" stroke="#dadce0" stroke-width="1.4"/>
<text x="426" y="257" text-anchor="middle" font-size="14" fill="#202124">The instruments · the charts · the briefing</text>
<text x="426" y="273" text-anchor="middle" font-size="11.5" fill="#5f6368">right now · everything known · what was agreed before departure</text>
<circle cx="188" cy="238" r="9" fill="#5f6368"/><text x="188" y="242" text-anchor="middle" font-size="11" font-weight="700" fill="#fff">4</text>
<line x1="449" y1="236" x2="449" y2="188" stroke="#9aa0a6" stroke-width="1.3" stroke-dasharray="4 3" marker-end="url(#f-ah)"/>
<circle class="tracer" r="7" fill="#4285f4" stroke="#fff" stroke-width="2" opacity="0"/>
</svg></div>
      <p class="small">Nobody builds an airframe to run an airline. <b>Azure gives you the aircraft; you fly the route.</b> The honest gap: aviation earned this from <i>decades of mandatory accident reporting</i>. We have no such corpus — <span class="k">state the leak</span>.</p>
    `,
    notes: "The third alternate frame — for a risk, assurance or regulator room. PICK ONE of slides 4/5/6; do not run them as a sequence. Deliberately the SAME diagram geometry as slide 5, so if you do show both, the shape repeating is the point: same seven, any domain. The mapping to land is 3 — envelope protection is not a rule in a manual, the flight computer physically refuses the input. That is the whole architectural argument in one image: a boundary you enforce in the machine, not in a policy document. If you are in a client room, this is the slide where the sealed parameter list makes sense — the drafting function's signature IS the envelope. Also strong: 2, the flight data recorder is an append-only audit log and every regulator in the room already trusts that idea. And 7, the captain's authority survives full automation — the autopilot flies, the captain is still accountable. The leak is the sharpest of the three and you must say it: aviation's safety record was bought with decades of investigations feeding back into design, mandatory reporting, and a blame-free incident culture. There is no equivalent corpus for agents. We are borrowing the shape of a mature safety system without the evidence base that made it work."
  },

  // 5 — TWO LAYERS
  {
    html: `
      <h2>Two layers do the work</h2>
      <div class="duo">
        <div class="p">
          <h3>Azure provides — the agents</h3>
          <p><b>AI Foundry · Agent Service.</b> Model calls + the tool loop, managed <b>threads</b> (memory), and sandboxed tools: Code Interpreter, File Search, Function, AI Search.</p>
        </div>
        <div class="p b">
          <h3>You build — the harness around them</h3>
          <p><b>Microsoft Agent Framework.</b> Middleware/guardrails, durable checkpointed workflows, multi-agent orchestration, and human-in-the-loop.</p>
        </div>
      </div>
      <p class="small">Our own code is a thin <b>FastAPI orchestration API</b> (destined for Azure Container Apps) that drives these agents. <span class="pill w">Agent Framework is public preview — pin versions</span></p>
    `,
    notes: "Agent Service = the agents themselves. Agent Framework = the harness around agents (successor to Semantic Kernel + AutoGen). Our FastAPI app is the glue. Note the preview caveat: the Agent Framework API shifts, so we pin exact versions per lesson."
  },

  // 6 — ARCHITECTURE
  {
    html: `
      <h2>Architecture</h2>
      <div class="diagram"><svg viewBox="0 0 960 356" role="img" aria-label="Your FastAPI code drives Azure-managed agent services">
<style>text{font-family:'Google Sans','Product Sans',Roboto,system-ui,sans-serif}</style>
<defs><marker id="ah1" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#5f6368"/></marker></defs>
<rect x="400" y="6" width="160" height="40" rx="9" fill="#fff" stroke="#dadce0" stroke-width="1.5"/>
<text x="480" y="31" text-anchor="middle" font-size="16" fill="#202124">User / UI</text>
<line x1="480" y1="46" x2="480" y2="70" stroke="#5f6368" stroke-width="1.5" marker-end="url(#ah1)"/>
<rect x="54" y="72" width="612" height="92" rx="12" fill="#e8f0fe" stroke="#4285f4" stroke-width="1.5"/>
<text x="70" y="93" font-size="13" font-weight="600" fill="#1a73e8">Your code · FastAPI on Azure Container Apps</text>
<rect x="70" y="100" width="580" height="52" rx="8" fill="#fff" stroke="#c9ddfc" stroke-width="1.2"/>
<text x="360" y="131" text-anchor="middle" font-size="15" fill="#202124">Microsoft Agent Framework — middleware · workflows · orchestration</text>
<rect x="700" y="84" width="206" height="68" rx="10" fill="#fef7e0" stroke="#f9ab00" stroke-width="1.5"/>
<text x="803" y="112" text-anchor="middle" font-size="15" fill="#202124">Content Safety</text>
<text x="803" y="132" text-anchor="middle" font-size="12.5" fill="#5f6368">Prompt Shields (in / out)</text>
<line x1="666" y1="118" x2="700" y2="118" stroke="#5f6368" stroke-width="1.5" marker-end="url(#ah1)" marker-start="url(#ah1)"/>
<line x1="360" y1="164" x2="360" y2="194" stroke="#5f6368" stroke-width="1.5" marker-end="url(#ah1)"/>
<rect x="54" y="196" width="852" height="150" rx="12" fill="#f8f9fa" stroke="#9aa0a6" stroke-width="1.4" stroke-dasharray="6 5"/>
<text x="70" y="218" font-size="13" font-weight="600" fill="#5f6368">Managed by Azure AI Foundry</text>
<rect x="68" y="232" width="196" height="98" rx="9" fill="#fff" stroke="#4285f4" stroke-width="1.5"/>
<text x="166" y="276" text-anchor="middle" font-size="15" fill="#202124">Agent Service</text>
<text x="166" y="298" text-anchor="middle" font-size="12.5" fill="#5f6368">agents · threads · tools</text>
<rect x="284" y="232" width="196" height="98" rx="9" fill="#fff" stroke="#dadce0" stroke-width="1.5"/>
<text x="382" y="276" text-anchor="middle" font-size="15" fill="#202124">Azure OpenAI</text>
<text x="382" y="298" text-anchor="middle" font-size="12.5" fill="#5f6368">GPT-4o / 4.1</text>
<rect x="500" y="232" width="196" height="98" rx="9" fill="#fff" stroke="#dadce0" stroke-width="1.5"/>
<text x="598" y="276" text-anchor="middle" font-size="15" fill="#202124">Azure AI Search</text>
<text x="598" y="298" text-anchor="middle" font-size="12.5" fill="#5f6368">long-term memory</text>
<rect x="716" y="232" width="190" height="98" rx="9" fill="#fff" stroke="#dadce0" stroke-width="1.5"/>
<text x="811" y="276" text-anchor="middle" font-size="15" fill="#202124">Cosmos DB</text>
<text x="811" y="298" text-anchor="middle" font-size="12.5" fill="#5f6368">checkpoints</text>
<line x1="264" y1="281" x2="284" y2="281" stroke="#5f6368" stroke-width="1.5" marker-end="url(#ah1)"/>
</svg></div>
      <p class="small">You host only the API; everything in the dashed band is managed by Azure. Cross-cutting: App Insights (OpenTelemetry traces) · Entra Managed Identity (keyless, <code>DefaultAzureCredential</code>).</p>
    `,
    notes: "Walk top to bottom. The API is the only thing we host; everything under it is managed. Observability (App Insights + Foundry tracing) is the 'is it actually working' signal — it is the 'is it actually working' signal you would otherwise hand-build as an inspector UI. Auth is keyless by default."
  },

  // 7 — THE SEAM PATTERN
  {
    html: `
      <h2>The one convention: the <span class="accent">seam pattern</span></h2>
      <p>Every Azure dependency is stubbed behind a seam, so the whole suite runs with <b>no cloud and no network</b>.</p>
      <ul class="big">
        <li>A <code>typing.Protocol</code> (or injectable callable/table) = the swap point.</li>
        <li>A <b>local implementation</b> whose docstring <b>names the Azure service</b> it stands in for.</li>
        <li>It honestly documents where the local stand-in is weaker — <b>"state the leak."</b></li>
      </ul>
      <pre><span class="c"># durable/checkpoint.py — same interface, local SQLite today, Cosmos DB later</span>
class CheckpointStore(Protocol):
    def load(self, run_id: str) -> Checkpoint | None: ...
    def save(self, checkpoint: Checkpoint) -> None: ...</pre>
      <p class="small">Swap local → Azure without touching the workflow logic. <b>Match this pattern when adding code.</b></p>
      <div data-demo="seam" data-compact data-code data-label="▶ Prove it — swap the backend"></div>
    `,
    notes: "This is THE thing to remember from the codebase. Protocol boundary + local impl + honest docstring. 'State the leak' means the stand-in never pretends to be as strong as the managed service — it says exactly where it's weaker. This is what makes the repo runnable offline yet ready to wire to Azure. || LIVE DEMO — the slide makes a falsifiable claim ('swap the backend without touching the workflow'), so run it rather than asserting it. Press r. Four beats: (1) three implementations of the one Protocol, all conforming — a dict, localStorage standing in for Cosmos, and an audit wrapper; (2) the SAME run_durably from src/harness/ over all three, identical results; (3) the audit wrapper's call log, proving a decorator is just another implementation — that is I5; (4) someone adds a 'tenant' argument and the boundary check REJECTS it. Land beat 4 hardest: this is the SEALED_DRAFT_PARAMS rule, and the check compares parameter names exactly, which is stricter than structural typing on purpose. A new capability means a new precomputed field upstream, never a new parameter. If asked why so strict: a seam widens one harmless-looking argument at a time, and each one is individually reasonable."
  },

  // 8 — 7 LESSONS OVERVIEW
  {
    html: `
      <h2>The seven lessons</h2>
      <table class="lessons">
        <tr><th>#</th><th>Pattern</th><th>You build (local module)</th><th></th></tr>
        <tr><td class="n">1</td><td>Agent Harness</td><td><code>guardrails.py</code> + <code>app.py</code></td><td><span class="pill">local ✓</span></td></tr>
        <tr><td class="n">2</td><td>Durable Execution</td><td><code>workflow.py</code> + <code>durable/</code></td><td><span class="pill">local ✓</span></td></tr>
        <tr><td class="n">3</td><td>Secure Sandboxing</td><td><code>sandbox.py</code></td><td><span class="pill">local ✓</span></td></tr>
        <tr><td class="n">4</td><td>Advanced Memory</td><td><code>memory/</code> (thread·knowledge·summarize)</td><td><span class="pill">local ✓</span></td></tr>
        <tr><td class="n">5</td><td>Orchestration</td><td><code>orchestration/router.py</code></td><td><span class="pill">local ✓</span></td></tr>
        <tr><td class="n">6</td><td>Hierarchical Supervision</td><td><code>orchestration/supervisor.py</code></td><td><span class="pill">local ✓</span></td></tr>
        <tr><td class="n">7</td><td>Human-in-the-Loop</td><td><code>hitl.py</code> (on <code>durable/</code>)</td><td><span class="pill">local ✓</span></td></tr>
      </table>
      <p class="small">"local ✓" = runnable + unit-tested with Azure stubbed behind a seam. Azure-wired impls are the next increment.</p>
    `,
    notes: "The map for the rest of the talk — one slide per lesson coming up. Emphasize all seven are DONE locally and green. The Azure wiring is deliberately future work; the point of the exercise is to learn the patterns first, offline."
  },

  // 9 — L1 GUARDRAILS
  {
    html: `
      <h2><span class="num">L1</span>Agent Harness</h2>
      <p class="lead">Guardrails wrap the model as middleware — with a tool loop in the middle.</p>
      <div class="diagram"><svg viewBox="0 0 960 358" role="img" aria-label="Request sequence: guardrail then agent tool loop then response">
<style>text{font-family:'Google Sans','Product Sans',Roboto,system-ui,sans-serif}</style>
<defs><marker id="ah2" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#5f6368"/></marker></defs>
<g font-size="13.5" fill="#202124" text-anchor="middle">
<rect x="30" y="4" width="120" height="32" rx="8" fill="#fff" stroke="#dadce0" stroke-width="1.4"/><text x="90" y="25">User</text>
<rect x="200" y="4" width="160" height="32" rx="8" fill="#e8f0fe" stroke="#4285f4" stroke-width="1.4"/><text x="280" y="25">API · Guardrails</text>
<rect x="420" y="4" width="120" height="32" rx="8" fill="#fff" stroke="#4285f4" stroke-width="1.4"/><text x="480" y="25">Agent</text>
<rect x="620" y="4" width="120" height="32" rx="8" fill="#fff" stroke="#dadce0" stroke-width="1.4"/><text x="680" y="25">Model</text>
<rect x="805" y="4" width="130" height="32" rx="8" fill="#fff" stroke="#dadce0" stroke-width="1.4"/><text x="870" y="25">Tool (sandbox)</text>
</g>
<g stroke="#e8eaed" stroke-width="1.5" stroke-dasharray="4 4">
<line x1="90" y1="36" x2="90" y2="346"/><line x1="280" y1="36" x2="280" y2="346"/><line x1="480" y1="36" x2="480" y2="346"/><line x1="680" y1="36" x2="680" y2="346"/><line x1="870" y1="36" x2="870" y2="346"/>
</g>
<g font-size="12" fill="#3c4043" text-anchor="middle">
<line x1="90" y1="66" x2="278" y2="66" stroke="#5f6368" stroke-width="1.5" marker-end="url(#ah2)"/><text x="184" y="60">request</text>
<rect x="284" y="80" width="152" height="22" rx="6" fill="#fef7e0" stroke="#f9ab00" stroke-width="1.3"/><text x="360" y="95">① guardrail (input)</text>
<line x1="280" y1="124" x2="478" y2="124" stroke="#5f6368" stroke-width="1.5" marker-end="url(#ah2)"/><text x="380" y="118">run agent</text>
<rect x="432" y="140" width="470" height="150" rx="9" fill="none" stroke="#9aa0a6" stroke-width="1.2" stroke-dasharray="5 4"/><text x="470" y="156" font-size="11" fill="#5f6368" text-anchor="start">tool loop ×N</text>
<line x1="480" y1="184" x2="678" y2="184" stroke="#5f6368" stroke-width="1.5" marker-end="url(#ah2)"/><text x="580" y="178">prompt</text>
<line x1="680" y1="212" x2="482" y2="212" stroke="#5f6368" stroke-width="1.5" stroke-dasharray="6 4" marker-end="url(#ah2)"/><text x="580" y="206">tool call</text>
<line x1="480" y1="242" x2="868" y2="242" stroke="#5f6368" stroke-width="1.5" marker-end="url(#ah2)"/><text x="675" y="236">execute (isolated)</text>
<line x1="870" y1="270" x2="482" y2="270" stroke="#5f6368" stroke-width="1.5" stroke-dasharray="6 4" marker-end="url(#ah2)"/><text x="675" y="264">result</text>
<line x1="480" y1="312" x2="282" y2="312" stroke="#5f6368" stroke-width="1.5" stroke-dasharray="6 4" marker-end="url(#ah2)"/><text x="380" y="306">final answer</text>
<line x1="280" y1="340" x2="92" y2="340" stroke="#5f6368" stroke-width="1.5" stroke-dasharray="6 4" marker-end="url(#ah2)"/><text x="184" y="334">response</text>
</g>
</svg></div>
      <ul class="big">
        <li><code>guardrails.check_input</code> blocks empty, oversize &amp; injection markers before the model — a <b>Content Safety Prompt Shields</b> stand-in.</li>
        <li>Only <code>/health</code> and <code>/chat</code> are wired today; the other six lessons are standalone modules.</li>
      </ul>
      <pre class="tight"><span class="c"># app.py — the guardrail runs BEFORE the model, as middleware</span>
verdict = check_input(user_message)
if not verdict.allowed:
    return Blocked(verdict.reason)      <span class="c"># the model is never called</span></pre>
    `,
    notes: "Lesson 1 is the frame for everything: the model in the middle, guardrails on the way in (and, in production, out). The agent call is a stub locally — the pattern being learned is the middleware wrap, not the model itself."
  },

  // 10 — SAFETY LAYER
  {
    html: `
      <h2><span class="num">L1+</span>Evasion-resistant safety layer</h2>
      <p>A naive marker list is trivially bypassed. <code>safety/</code> hardens it into a real Prompt-Shields stand-in.</p>
      <div class="cols">
        <div class="card"><h3><code>normalize</code></h3><p>Folds obfuscation — homoglyphs, zero-width chars, spacing — before matching.</p></div>
        <div class="card"><h3><code>detectors</code></h3><p>Heuristic <b>attack-family</b> detectors run over the folded text.</p></div>
        <div class="card"><h3><code>redteam</code></h3><p>A corpus of attacks + a scorer to measure the layer against itself.</p></div>
        <div class="card"><h3>state the leak</h3><p>Still <b>heuristic, not ML</b> — the docstring says so. No false confidence.</p></div>
      </div>
      <p class="small">Threat model: <code>docs/safety-layer.md</code>.</p>
      <pre class="tight"><span class="c"># safety/ — fold the disguise, THEN match</span>
folded = normalize(msg)        <span class="c"># homoglyphs · zero-width · spacing</span>
verdict = check_input(msg)     <span class="c"># markers re-checked over folded text</span></pre>
    `,
    notes: "This is the repo's most 'productiony' bit. The insight: attackers evade keyword filters with unicode tricks, so you normalize FIRST, then match. Red-team corpus + scorer means the defense is measurable. And it honestly labels itself heuristic — the real thing is Azure Content Safety."
  },

  // L1 — EXAMPLE
  {
    html: `
      <h2><span class="num">L1</span>Guardrails — the example</h2>
      <p class="lead">The same <code>check_input</code> the test suite exercises, on a disguised attack.</p>
      <pre><span class="c"># the naive check most demos ship — a substring scan</span>
naive = next((m for m in INJECTION_MARKERS if m in msg.lower()), None)
<span class="c">#   -> None. it sails straight through.</span>

<span class="c"># look at what is actually in the string</span>
<span class="c">#   pos  5   U+0435   CYRILLIC SMALL LETTER IE</span>

folded  = normalize(msg)      <span class="c"># fold the disguise</span>
verdict = check_input(msg)    <span class="c"># then match again</span>
<span class="c">#   -> BLOCKED: possible prompt injection (obfuscated)</span></pre>
      <div data-demo="guard" data-compact data-code data-label="▶ Run this example"></div>
    `,
    notes: "The worked example for L1. Beat two is the one that earns it — on a projector the two strings are identical, so the room has to take your word that anything is wrong right up until the codepoint appears. Type an attack from the floor if someone offers one; if it gets through, say so, because slide 12 already states the layer is heuristic."
  },

  // 11 — L2 DURABLE
  {
    html: `
      <h2><span class="num">L2</span>Durable Execution</h2>
      <p class="lead">A run must <b>survive a crash</b> — resume from the last checkpoint instead of restarting.</p>
      <div class="diagram"><svg viewBox="0 0 960 176" role="img" aria-label="State machine: Running checkpoints, resumes after a crash, then completes">
<style>text{font-family:'Google Sans','Product Sans',Roboto,system-ui,sans-serif}</style>
<defs><marker id="ah3" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#5f6368"/></marker></defs>
<circle cx="52" cy="77" r="7" fill="#5f6368"/>
<line x1="59" y1="77" x2="110" y2="77" stroke="#5f6368" stroke-width="1.5" marker-end="url(#ah3)"/>
<rect x="112" y="44" width="200" height="66" rx="12" fill="#e8f0fe" stroke="#4285f4" stroke-width="1.6"/>
<text x="212" y="84" text-anchor="middle" font-size="17" fill="#202124">Running</text>
<rect x="402" y="44" width="214" height="66" rx="12" fill="#fff" stroke="#4285f4" stroke-width="1.6"/>
<text x="509" y="78" text-anchor="middle" font-size="16" fill="#202124">Checkpointed</text>
<text x="509" y="97" text-anchor="middle" font-size="12" fill="#5f6368">state persisted</text>
<rect x="706" y="44" width="176" height="66" rx="12" fill="#e6f4ea" stroke="#188038" stroke-width="1.6"/>
<text x="794" y="84" text-anchor="middle" font-size="17" fill="#202124">Done</text>
<line x1="312" y1="62" x2="400" y2="62" stroke="#5f6368" stroke-width="1.5" marker-end="url(#ah3)"/>
<text x="356" y="55" text-anchor="middle" font-size="12" fill="#3c4043">save each step</text>
<line x1="400" y1="96" x2="314" y2="96" stroke="#5f6368" stroke-width="1.5" stroke-dasharray="6 4" marker-end="url(#ah3)"/>
<text x="356" y="130" text-anchor="middle" font-size="12" fill="#b06000">resume after crash / rate-limit</text>
<line x1="616" y1="77" x2="704" y2="77" stroke="#5f6368" stroke-width="1.5" marker-end="url(#ah3)"/>
<text x="660" y="70" text-anchor="middle" font-size="12" fill="#3c4043">complete</text>
</svg></div>
      <ul class="big">
        <li><code>workflow.py</code> runs steps; <code>durable/</code> persists a <b>Checkpoint(run_id, step, state)</b> after each.</li>
        <li>Local <b>SQLite</b> today → <b>Cosmos DB</b> later → <b>localStorage</b> in this browser. Same interface; <code>run_durably</code> never knows.</li>
      </ul>
      <pre class="tight"><span class="c"># workflow.py — checkpoint after every step; resume skips completed work</span>
state = run_durably(run_id, steps, store)</pre>
    `,
    notes: "Checkpoint after each step, keyed by run_id + step index. On restart, load the last checkpoint and continue. The seam: CheckpointStore Protocol. Local = SQLite in .harness/, prod = Cosmos DB. There's an actual test that kills the run mid-way and asserts it resumes. || LIVE DEMO — this one is not a simulation, so run it in this order: press r, press 'Start the run'. Steps 1 and 2 execute and print a real side effect; step 3 hits a rate limit and the run dies. Then SAY 'watch — I'm going to destroy everything' and actually reload the page (Cmd-R). The Pyodide interpreter and every Python object in it are gone. The deck comes back to this slide from the hash and the panel re-opens itself in resume mode. Press 'Resume the run': `ran` is empty — brand new interpreter — but the checkpoint came back out of localStorage, so steps 1 and 2 do NOT re-run and their results are still in the final state. The line to land: the work was not redone, it was remembered. Press 'reset' before you rehearse it again. If the venue blocks localStorage or the Pyodide CDN, the panel says so and replays the build-time transcript instead — don't reload in that case, it proves nothing."
  },

  // L2 — EXAMPLE
  {
    html: `
      <h2><span class="num">L2</span>Durable execution — the example</h2>
      <p class="lead">A real crash, a real page reload, and a resume that skips completed work.</p>
      <pre><span class="c"># same CheckpointStore Protocol as SQLite and Cosmos</span>
store = BrowserCheckpointStore(js.localStorage)

run_durably("banquet-42", STEPS, store)
<span class="c">#   ran step-1 · ran step-2 · CRASH: rate limited</span>

<span class="c"># --- reload the page. the interpreter and every object in it die ---</span>

run_durably("banquet-42", STEPS, store)   <span class="c"># same run id</span>
<span class="c">#   ran step-3 · ran step-4</span>
<span class="c">#   step-1 and step-2 never ran again</span></pre>
      <div data-demo="crash" data-compact data-code data-label="▶ Run this example"></div>
    `,
    notes: "The worked example for L2, and the one demo that is performed rather than depicted. Run the first half, then SAY 'watch — I am going to destroy everything' and actually reload. The deck returns to this slide from the hash and the panel re-opens itself in resume mode. Land: the work was not redone, it was remembered."
  },

  // 12 — L3 SANDBOX
  {
    html: `
      <h2><span class="num">L3</span>Secure Sandboxing</h2>
      <p>Agent-generated code can't run in your process. <code>sandbox.py</code> isolates it.</p>
      <ul class="big">
        <li>Executes in an <b>isolated subprocess</b> with a hard <b>timeout</b>.</li>
        <li>Local stand-in for the Agent Service <b>Code Interpreter</b> tool.</li>
        <li>State the leak: a subprocess is <i>not</i> a real sandbox — the managed tool gives true isolation, network controls, and resource limits.</li>
      </ul>
      <p class="small">The pattern that matters: never <code>exec()</code> untrusted output in-process — put a boundary (and a clock) around it.</p>
      <pre class="tight"><span class="c"># sandbox.py — isolated subprocess, hard timeout</span>
r = run_code(model_written_code, timeout=5.0)
r.ok, r.timed_out, r.stdout</pre>
    `,
    notes: "The lesson isn't 'we built a perfect sandbox' — it's 'code from a model is untrusted; isolate it and bound it in time.' Locally that's a subprocess + timeout. In prod it's Code Interpreter, which is a genuinely hardened sandbox. The docstring states that gap plainly."
  },

  // L3 — EXAMPLE
  {
    html: `
      <h2><span class="num">L3</span>Sandboxing — the example</h2>
      <p class="lead">A subprocess with a clock — and a runtime that refuses outright.</p>
      <pre>r = run_code("print('hello from inside the sandbox')")
r.ok, r.exit_code, r.stdout

r = run_code("while True: pass", timeout=1.0)
r.timed_out          <span class="c"># True — contained by the clock</span>

<span class="c"># but run the same call in this browser:</span>
<span class="c">#   OSError — the runtime refuses to spawn a process at all</span>
<span class="c">#   a real boundary refuses; a teaching stand-in only pretends</span></pre>
      <div data-demo="sandbox" data-compact data-code data-label="▶ Run this example"></div>
    `,
    notes: "The worked example for L3, and the only demo whose interesting result is a failure. Locally the subprocess runs and the timeout contains a runaway. In the browser it is refused outright — and that refusal is the lesson, because sandbox.py's own docstring admits a subprocess is not a security boundary. This is the argument for Code Interpreter in one line."
  },

  // 13 — L4 MEMORY
  {
    html: `
      <h2><span class="num">L4</span>Advanced Memory</h2>
      <p>Three memory shapes, three stand-ins — under <code>memory/</code>.</p>
      <div class="cols three">
        <div class="card"><span class="tag">short-term</span><h3><code>thread</code></h3><p>Per-conversation history. Stands in for Agent Service <b>managed threads</b>.</p></div>
        <div class="card"><span class="tag">long-term</span><h3><code>knowledge</code></h3><p>Retrievable facts. Stands in for <b>Azure AI Search</b> (RAG).</p></div>
        <div class="card"><span class="tag">compaction</span><h3><code>summarize</code></h3><p>Condense history to fit the context window.</p></div>
      </div>
      <p class="small">Short-term = the conversation; long-term = a knowledge store the agent can query; summarization = keep both affordable within the token budget.</p>
      <pre class="tight"><span class="c"># three memories, three lifetimes</span>
threads.append(tid, "user", msg)      <span class="c"># the turn</span>
kb.search("duplicate charge", k=2)    <span class="c"># the corpus</span>
summarize_thread(history, max_chars=500)  <span class="c"># the context budget</span></pre>
    `,
    notes: "Memory isn't one thing. Thread = recent turns (managed threads). Knowledge = durable retrievable facts (AI Search / RAG). Summarize = compress older turns so you don't blow the context window. Together they're 'advanced memory'."
  },

  // L4 — EXAMPLE
  {
    html: `
      <h2><span class="num">L4</span>Memory — the example</h2>
      <p class="lead">Three memories, three lifetimes — running on real SQLite in the browser.</p>
      <pre>threads = SQLiteThreadStore(":memory:")
threads.append("t-1", "user", "my invoice is wrong")
threads.history("t-1")                     <span class="c"># the turn</span>

kb = InMemoryKnowledgeStore()
kb.add("refunds", "Duplicate charges are refunded in five days.")
kb.search("duplicate charge refund", k=2)  <span class="c"># the corpus</span>

summarize_thread(history, max_chars=120, keep=1)
<span class="c">#   user: my invoice is wrong</span>
<span class="c">#   [...4 earlier turns omitted...]</span></pre>
      <div data-demo="memory" data-compact data-code data-label="▶ Run this example"></div>
    `,
    notes: "The worked example for L4. All three memories are real here — thread is actual sqlite3 loaded into the browser, not a dict pretending. The line to land is the last one: the raw thread stays in the store because summarising is lossy, so the summary is never the only copy."
  },

  // 14 — L5 ROUTING
  {
    html: `
      <h2><span class="num">L5</span>Orchestration — routing &amp; handoff</h2>
      <p class="lead">A <b>triage agent</b> classifies intent and hands off to the right specialist.</p>
      <div class="diagram"><svg viewBox="0 0 960 220" role="img" aria-label="Triage agent routes intent to one specialist, which answers">
<style>text{font-family:'Google Sans','Product Sans',Roboto,system-ui,sans-serif}</style>
<defs><marker id="ah5" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#4285f4"/></marker><marker id="ah5g" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#9aa0a6"/></marker></defs>
<rect x="60" y="80" width="180" height="66" rx="11" fill="#e8f0fe" stroke="#4285f4" stroke-width="1.6"/>
<text x="150" y="109" text-anchor="middle" font-size="16" fill="#202124">Triage agent</text>
<text x="150" y="129" text-anchor="middle" font-size="12" fill="#5f6368">classifies intent</text>
<rect x="430" y="26" width="200" height="48" rx="9" fill="#fff" stroke="#dadce0" stroke-width="1.5"/><text x="530" y="55" text-anchor="middle" font-size="15" fill="#5f6368">Billing</text>
<rect x="430" y="89" width="200" height="48" rx="9" fill="#e8f0fe" stroke="#4285f4" stroke-width="1.8"/><text x="530" y="118" text-anchor="middle" font-size="15" fill="#202124">Code</text>
<rect x="430" y="152" width="200" height="48" rx="9" fill="#fff" stroke="#dadce0" stroke-width="1.5"/><text x="530" y="181" text-anchor="middle" font-size="15" fill="#5f6368">Research</text>
<path d="M240 106 C 340 90, 350 55, 428 50" fill="none" stroke="#9aa0a6" stroke-width="1.4" marker-end="url(#ah5g)"/>
<path d="M240 113 C 340 113, 350 113, 428 113" fill="none" stroke="#4285f4" stroke-width="2" marker-end="url(#ah5)"/>
<path d="M240 120 C 340 136, 350 171, 428 176" fill="none" stroke="#9aa0a6" stroke-width="1.4" marker-end="url(#ah5g)"/>
<rect x="760" y="80" width="150" height="66" rx="11" fill="#fff" stroke="#4285f4" stroke-width="1.5"/>
<text x="835" y="118" text-anchor="middle" font-size="16" fill="#202124">Response</text>
<path d="M630 113 C 690 113, 700 113, 758 113" fill="none" stroke="#4285f4" stroke-width="2" marker-end="url(#ah5)"/>
<text x="335" y="16" text-anchor="middle" font-size="12" fill="#5f6368">route by intent → one specialist</text>
</svg></div>
      <ul class="big">
        <li><code>orchestration/router.py</code> — intent → specialist, the Agent Framework <b>handoff</b> pattern.</li>
        <li>One entry point, many specialists; each specialist stays focused and small.</li>
      </ul>
      <pre class="tight"><span class="c"># orchestration/router.py — intent → specialist</span>
Router().route("refund my invoice")
<span class="c"># RouteDecision(specialist='billing', matched_intent='invoice')</span></pre>
    `,
    notes: "Single-agent is limiting. Routing = a cheap classifier agent picks the specialist. Keeps each specialist's prompt/tools narrow and reliable. This is the Agent Framework handoff pattern; locally it's a routing table."
  },

  // L5 — EXAMPLE
  {
    html: `
      <h2><span class="num">L5</span>Routing — the example</h2>
      <p class="lead">Three requests routed, one paraphrase missed — and the leak that causes it.</p>
      <pre>Router().route("I need a refund on my invoice")
<span class="c">#   RouteDecision(specialist='billing', matched_intent='invoice')</span>

Router().route("the project won't build any more")
<span class="c">#   RouteDecision(specialist='fallback', matched_intent=None)</span>
<span class="c">#   a human reads that as a CODE problem instantly.</span>
<span class="c">#   'compile' is in the table; "won't build" is not.</span>

Router({"won't build": Specialist.CODE}).route(...)
<span class="c">#   patched in one line — the treadmill a triage agent removes</span></pre>
      <div data-demo="router" data-compact data-code data-label="▶ Run this example"></div>
    `,
    notes: "The worked example for L5. Beat two matters most: fallback is a routing decision, not a crash, but a substring table has no notion of meaning. Then patch it in one line and note that you have just signed up to maintain that table forever — which is exactly what a real triage agent takes off you."
  },

  // 15 — L6 SUPERVISION
  {
    html: `
      <h2><span class="num">L6</span>Hierarchical Supervision</h2>
      <p>Routing escalated: a <b>supervisor</b> decomposes a task, fans out, and aggregates.</p>
      <div class="diagram"><svg viewBox="0 0 960 226" role="img" aria-label="Supervisor fans a task out to parallel sub-agents and aggregates their results">
<style>text{font-family:'Google Sans','Product Sans',Roboto,system-ui,sans-serif}</style>
<defs><marker id="ah6" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#4285f4"/></marker></defs>
<rect x="60" y="80" width="180" height="66" rx="11" fill="#e8f0fe" stroke="#4285f4" stroke-width="1.6"/>
<text x="150" y="118" text-anchor="middle" font-size="16" fill="#202124">Supervisor</text>
<rect x="420" y="30" width="180" height="48" rx="9" fill="#fff" stroke="#4285f4" stroke-width="1.5"/><text x="510" y="59" text-anchor="middle" font-size="15" fill="#202124">sub-agent A</text>
<rect x="420" y="89" width="180" height="48" rx="9" fill="#fff" stroke="#4285f4" stroke-width="1.5"/><text x="510" y="118" text-anchor="middle" font-size="15" fill="#202124">sub-agent B</text>
<rect x="420" y="148" width="180" height="48" rx="9" fill="#fff" stroke="#4285f4" stroke-width="1.5"/><text x="510" y="177" text-anchor="middle" font-size="15" fill="#202124">sub-agent C</text>
<path d="M240 106 C 320 96, 340 55, 418 54" fill="none" stroke="#4285f4" stroke-width="1.7" marker-end="url(#ah6)"/>
<path d="M240 113 C 320 113, 340 113, 418 113" fill="none" stroke="#4285f4" stroke-width="1.7" marker-end="url(#ah6)"/>
<path d="M240 120 C 320 130, 340 171, 418 172" fill="none" stroke="#4285f4" stroke-width="1.7" marker-end="url(#ah6)"/>
<rect x="736" y="80" width="176" height="66" rx="11" fill="#e8f0fe" stroke="#4285f4" stroke-width="1.6"/>
<text x="824" y="118" text-anchor="middle" font-size="16" fill="#202124">Aggregate</text>
<path d="M600 54 C 678 55, 700 96, 734 106" fill="none" stroke="#4285f4" stroke-width="1.7" marker-end="url(#ah6)"/>
<path d="M600 113 C 678 113, 700 113, 734 113" fill="none" stroke="#4285f4" stroke-width="1.7" marker-end="url(#ah6)"/>
<path d="M600 172 C 678 171, 700 130, 734 120" fill="none" stroke="#4285f4" stroke-width="1.7" marker-end="url(#ah6)"/>
<text x="510" y="18" text-anchor="middle" font-size="12" fill="#5f6368">run in parallel</text>
</svg></div>
      <ul class="big">
        <li><code>orchestration/supervisor.py</code> — parallel <b>fan-out / fan-in</b>.</li>
        <li>Maps to Agent Framework <b>Magentic / concurrent</b> orchestration.</li>
      </ul>
      <pre class="tight"><span class="c"># orchestration/supervisor.py — fan-out / fan-in</span>
agg = Supervisor(worker=sub_agent).run("a; b; c")
agg.succeeded, agg.failed   <span class="c"># one failure never sinks the batch</span></pre>
      <p class="small">Routing picks <i>one</i> agent; supervision runs <i>many</i> in parallel and merges their results.</p>
    `,
    notes: "The step up from routing: don't just pick one specialist, break the task into pieces, dispatch them concurrently, and combine. That's the supervisor/orchestrator pattern (Magentic in Agent Framework). Locally: parallel fan-out, fan-in aggregation."
  },

  // L6 — EXAMPLE
  {
    html: `
      <h2><span class="num">L6</span>Supervision — the example</h2>
      <p class="lead">Fan out, one sub-agent fails, and the batch survives in a stable order.</p>
      <pre>sup = Supervisor(worker=sub_agent, executor_factory=SyncExecutor)
agg = sup.run("summarise the outage; check pricing; draft the note")

for r in agg.results:      <span class="c"># decomposition order, not completion</span>
    r.subtask, r.output, r.error

agg.succeeded, agg.failed  <span class="c"># 2, 1</span>
<span class="c">#   one sub-agent raised; the exception never escaped run()</span>
<span class="c">#   executor_factory is a seam: this browser has no threads,</span>
<span class="c">#   so the isolation is real and the parallelism is not</span></pre>
      <div data-demo="supervisor" data-compact data-code data-label="▶ Run this example"></div>
    `,
    notes: "The worked example for L6. Two guarantees hold — a failing sub-agent is isolated into its own result, and output order follows decomposition rather than completion. Say the leak plainly: threads are unavailable here so the fan-out ran sequentially, which is why the executor is an injectable seam at all."
  },

  // 16 — L7 HITL
  {
    html: `
      <h2><span class="num">L7</span>Human-in-the-Loop</h2>
      <p class="lead">Pause before a sensitive action, wait for a human, then resume — built on L2's checkpoints.</p>
      <div class="diagram"><svg viewBox="0 0 960 216" role="img" aria-label="Running pauses at Awaiting approval, then resumes to Done or is rejected on deadline">
<style>text{font-family:'Google Sans','Product Sans',Roboto,system-ui,sans-serif}</style>
<defs><marker id="ah7" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#5f6368"/></marker></defs>
<rect x="70" y="92" width="180" height="64" rx="12" fill="#e8f0fe" stroke="#4285f4" stroke-width="1.6"/>
<text x="160" y="130" text-anchor="middle" font-size="16" fill="#202124">Running</text>
<rect x="360" y="92" width="222" height="64" rx="12" fill="#fef7e0" stroke="#f9ab00" stroke-width="1.7"/>
<text x="471" y="120" text-anchor="middle" font-size="16" fill="#202124">Awaiting approval</text>
<text x="471" y="139" text-anchor="middle" font-size="11.5" fill="#5f6368">= persisted checkpoint</text>
<rect x="700" y="34" width="200" height="58" rx="12" fill="#e6f4ea" stroke="#188038" stroke-width="1.6"/>
<text x="800" y="69" text-anchor="middle" font-size="15.5" fill="#202124">Resume → Done</text>
<rect x="700" y="150" width="200" height="58" rx="12" fill="#fff" stroke="#dadce0" stroke-width="1.6"/>
<text x="800" y="185" text-anchor="middle" font-size="15.5" fill="#5f6368">Rejected / timeout</text>
<line x1="250" y1="124" x2="358" y2="124" stroke="#5f6368" stroke-width="1.5" marker-end="url(#ah7)"/>
<text x="304" y="116" text-anchor="middle" font-size="12" fill="#3c4043">sensitive action</text>
<path d="M582 112 C 650 96, 660 66, 698 64" fill="none" stroke="#188038" stroke-width="1.6" marker-end="url(#ah7)"/>
<text x="648" y="88" text-anchor="middle" font-size="12" fill="#188038">human approves</text>
<path d="M582 136 C 650 156, 660 176, 698 178" fill="none" stroke="#5f6368" stroke-width="1.5" stroke-dasharray="6 4" marker-end="url(#ah7)"/>
<text x="650" y="172" text-anchor="middle" font-size="12" fill="#b06000">reject / deadline</text>
</svg></div>
      <ul class="big">
        <li><code>hitl.py</code> — checkpointed <b>suspend / resume</b> with a <b>deadline</b> (reject on timeout).</li>
        <li>Reuses the durable store: a paused run is just a persisted checkpoint waiting on input.</li>
      </ul>
      <pre class="tight"><span class="c"># hitl.py — suspend, then resume against a deadline</span>
request_approval(run_id, prompt, store, now=t0, timeout_seconds=60)
resume(run_id, decision=True, store=store, now=t1, action=refund)</pre>
    `,
    notes: "LIVE DEMO — four beats and the fourth is the one nobody expects. A refund reaches the gate and does NOT run; a human approves in time and it fires; a human rejects and it does not; then a human approves TWO HOURS LATE and the gate returns timed_out. The deadline is checked BEFORE the decision, against an injected clock, so a late yes is void. Close on the count: three requests, one refund. || HITL falls out of durable execution almost for free: suspend = checkpoint + wait, resume = load + continue. Add a deadline so it doesn't wait forever. This is where the 'survive a crash' machinery pays off twice."
  },

  // L7 — EXAMPLE
  {
    html: `
      <h2><span class="num">L7</span>Human-in-the-loop — the example</h2>
      <p class="lead">Approve, reject, and the one nobody expects — a yes that arrives too late.</p>
      <pre>request_approval(run_id, "Refund 40.00 GBP", store,
                 now=0.0, timeout_seconds=60.0)
<span class="c">#   status=awaiting_approval   performed=False</span>

resume(run_id, True,  store, now=10.0,   action=issue_refund)
<span class="c">#   approved — action performed</span>
resume(run_id, False, store, now=10.0,   action=issue_refund)
<span class="c">#   rejected — action NOT performed</span>
resume(run_id, True,  store, now=7200.0, action=issue_refund)
<span class="c">#   timed_out — the deadline is checked BEFORE the decision</span></pre>
      <div data-demo="hitl" data-compact data-code data-label="▶ Run this example"></div>
    `,
    notes: "The worked example for L7, and beat four is the one nobody expects. Three requests, one refund. The deadline is checked before the decision against an injected clock, so a late yes is void — which is what stops an approval queue quietly authorising last week's refunds."
  },

  // 17 — DOCS AS TESTS
  {
    html: `
      <h2>The docs are part of the test suite</h2>
      <p>Knowledge lives in the repo and is <b>mechanically validated</b> — stale docs turn the suite red.</p>
      <ul class="big">
        <li><code>tests/test_docs.py</code> checks every <code>.md</code> / <code>.excalidraw</code>: balanced fences, resolvable anchors, valid Excalidraw JSON, no HTML-escape artifacts.</li>
        <li>Heavier Mermaid render is opt-in: <code>HARNESS_RENDER_MERMAID=1</code> (needs <code>mmdc</code>).</li>
        <li>Two glossaries cross-reference concepts — including a full <b>LangGraph → this repo → Azure</b> map.</li>
      </ul>
      <p class="small">A small echo of "repository as system of record": if an agent (or teammate) can't see it in-context, it doesn't exist.</p>
      <div data-demo="redteam" data-compact data-code data-label="▶ Score the red-team corpus"></div>
    `,
    notes: "Nice detail for an engineering audience: documentation is tested like code. This keeps the design docs honest as the code moves. The LangGraph glossary maps every LangGraph primitive to the repo module that stands in for it and the Azure target."
  },

  // 18 — STATUS + RUN IT
  {
    html: `
      <h2>Status &amp; how to run it</h2>
      <div class="cols">
        <div>
          <ul class="big">
            <li><span class="pill">7 / 7 lessons</span> implemented locally &amp; tested.</li>
            <li>Suite is deterministic and cloud-free.</li>
            <li><span class="pill w">Azure wiring pending</span> — the next increment.</li>
          </ul>
        </div>
        <div>
          <pre><span class="c"># run the full suite (no cloud needed)</span>
<span class="cmd">uv run --extra dev pytest</span>

<span class="c"># one test</span>
<span class="cmd">uv run --extra dev pytest \\
  tests/test_guardrails.py::test_normal_input_allowed</span>

<span class="c"># the API locally</span>
<span class="cmd">uv run uvicorn harness.app:app --reload</span>
<span class="cmd">curl localhost:8000/health</span></pre>
        </div>
      </div>
      <p class="small">Tooling is <code>uv</code> (provisions Python ≥3.11). Despite the Go-style path, this project is <b>Python</b>.</p>
    `,
    notes: "Live demo moment if you want one: run pytest (fast, all green), then curl /health, then POST a prompt-injection string to /chat and show the guardrail block it. Reminder: uv provisions the right Python; don't be fooled by the GOPATH-style directory — it's Python."
  },

  // 19 — TAKEAWAYS
  {
    html: `
      <h2>Takeaways</h2>
      <ul class="big">
        <li><b>Thin over managed.</b> The runtime is mostly configuration on Azure primitives, not from-scratch infrastructure.</li>
        <li><b>The seam pattern + "state the leak"</b> let you build and test offline, then swap to Azure without touching logic.</li>
        <li><b>The seven patterns are the vocabulary</b> of production agents: guard, persist, sandbox, remember, route, supervise, ask a human.</li>
      </ul>
      <p class="lead" style="margin-top:1em">Questions?</p>
      <p class="small">Design: <code>docs/architecture.md</code> · Plan: <code>docs/azure-implementation-plan.md</code> · Concepts: <code>docs/glossary.md</code>, <code>docs/langgraph-glossary.md</code></p>
    `,
    cls: "section-slide",
    notes: "Land the three points and open for questions. If asked 'why not just LangGraph?' — point at the langgraph-glossary: this repo maps each LangGraph primitive to a managed Azure equivalent, the bet being that managed services carry the operational load."
  }
];

/* ------------------------------------------------------------------ engine */
(function () {
  const deck = document.getElementById("deck");
  const bar = document.getElementById("progress-bar");
  const counter = document.getElementById("counter");
  const notesEl = document.createElement("div");
  notesEl.id = "notes";
  document.body.appendChild(notesEl);

  // build slides
  SLIDES.forEach((s, i) => {
    const el = document.createElement("section");
    el.className = "slide" + (s.cls ? " " + s.cls : "");
    el.dataset.n = (i + 1);
    el.innerHTML = s.html;
    el.addEventListener("click", () => {
      if (document.body.classList.contains("overview")) { go(i); toggleOverview(false); }
    });
    deck.appendChild(el);
  });
  const slides = Array.from(document.querySelectorAll(".slide"));
  const N = slides.length;

  let cur = clampIndexFromHash();
  let notesOn = false;

  function clampIndexFromHash() {
    const h = parseInt((location.hash || "").replace("#", ""), 10);
    return isNaN(h) ? 0 : Math.max(0, Math.min(N - 1, h - 1));
  }

  function render() {
    slides.forEach((el, i) => el.classList.toggle("active", i === cur));
    bar.style.width = (N > 1 ? (cur / (N - 1)) * 100 : 100) + "%";
    counter.textContent = (cur + 1) + " / " + N;
    const note = SLIDES[cur].notes || "";
    notesEl.innerHTML = '<span class="lbl">Speaker notes — ' + (cur + 1) + "/" + N + "</span>" + note;
    if (history.replaceState) history.replaceState(null, "", "#" + (cur + 1));
    else location.hash = cur + 1;
  }

  function go(i) { cur = Math.max(0, Math.min(N - 1, i)); render(); }
  function next() { if (cur < N - 1) go(cur + 1); }
  function prev() { if (cur > 0) go(cur - 1); }

  function toggleOverview(force) {
    const on = force === undefined ? !document.body.classList.contains("overview") : force;
    document.body.classList.toggle("overview", on);
  }
  function toggleNotes() { notesOn = !notesOn; notesEl.classList.toggle("show", notesOn); }
  function toggleFullscreen() {
    if (!document.fullscreenElement) { (document.documentElement.requestFullscreen || function(){})(); }
    else if (document.exitFullscreen) { document.exitFullscreen(); }
  }

  document.getElementById("next").addEventListener("click", next);
  document.getElementById("prev").addEventListener("click", prev);

  document.addEventListener("keydown", (e) => {
    switch (e.key) {
      case "ArrowRight": case " ": case "PageDown": case "l": case "j": next(); e.preventDefault(); break;
      case "ArrowLeft": case "PageUp": case "h": case "k": prev(); e.preventDefault(); break;
      case "Home": go(0); break;
      case "End": go(N - 1); break;
      case "o": case "Escape": toggleOverview(e.key === "Escape" ? false : undefined); break;
      case "s": case "n": toggleNotes(); break;
      case "f": toggleFullscreen(); break;
      default:
        if (/^[0-9]$/.test(e.key)) { const t = e.key === "0" ? 9 : parseInt(e.key, 10) - 1; if (t < N) go(t); }
    }
  });

  window.addEventListener("hashchange", () => { const i = clampIndexFromHash(); if (i !== cur) go(i); });

  render();
})();
