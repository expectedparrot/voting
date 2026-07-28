#!/usr/bin/env python3
"""Render voting's docs/index.html from the captured worked run.

Reads the envelopes written by scripts/book_driver.py (run that first) and
writes the full tutorial page. All prose lives here; all outputs come from
the captures — real production data, no fixtures.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORK = REPO / "build" / "tutorial" / "classic_books"
CAPTURES = REPO / "build" / "tutorial" / "captures"
OUT = REPO / "docs" / "index.html"


def clean(obj):
    if isinstance(obj, str):
        return (
            obj.replace(str(WORK) + "/", "")
            .replace(str(WORK), ".")
            .replace(str(REPO), "~/voting")
        )
    if isinstance(obj, list):
        return [clean(item) for item in obj]
    if isinstance(obj, dict):
        return {clean(key): clean(value) for key, value in obj.items()}
    return obj

TRUNCATE = {
    "08-import": 3,
    "08a-import-unregistered": 2,
    "08b-validate-unregistered": 3,
    "09-validate": 2,
    "14-count-list": 3,
}


def load(name: str) -> dict:
    return json.loads((CAPTURES / f"{name}.json").read_text())


def _trim(value, depth=0):
    if isinstance(value, list):
        keep = 3 if depth <= 1 else 2
        if len(value) > keep:
            return [_trim(v, depth + 1) for v in value[:keep]] + [
                f"… {len(value) - keep} further entries elided …"
            ]
        return [_trim(v, depth + 1) for v in value]
    if isinstance(value, dict):
        return {k: _trim(v, depth + 1) for k, v in value.items()}
    return value


def render_payload(name: str) -> str:
    payload = clean(load(name)["payload"])
    if name in TRUNCATE and isinstance(payload.get("data"), dict):
        payload["data"] = _trim(payload["data"])
    return json.dumps(payload, indent=2, ensure_ascii=False)


def cap(name: str, label: str = "Show command output") -> str:
    body = html.escape(render_payload(name))
    return (
        f'<details class="output"><summary>{label}</summary>'
        f"<pre><code>{body}</code></pre></details>"
    )


def cmd(display: str) -> str:
    return f'<pre class="command"><code>{html.escape(display)}</code></pre>'


def cmdcap(display: str, name: str) -> str:
    return cmd(display) + "\n    " + cap(name)


def cmdcap_auto(name: str) -> str:
    return cmdcap(load(name)["argv_display"], name)


def hcap(name: str, caption: str) -> str:
    text = (CAPTURES / f"{name}.txt").read_text()
    body = html.escape(text.rstrip())
    return (
        f'<figure class="human"><pre class="human"><code>{body}</code></pre>'
        f"<figcaption>{caption}</figcaption></figure>"
    )


# Facts from the captured run, extracted so prose can never drift from data.
IMPORT = load("08-import")["payload"]["data"]
BORDA = load("12-count-borda")["payload"]["data"]
IRV = load("13-count-irv")["payload"]["data"]
FPTP = load("13-count-fptp")["payload"]["data"]
N_BALLOTS = IMPORT["cast"]
BORDA_SCORES = sorted(BORDA["scores"], key=lambda s: -s["total"])
FPTP_TOTALS = sorted(FPTP["scores"], key=lambda s: -s["total"]) if FPTP.get("scores") else []
WINNER = BORDA["winners"][0]
assert all(load(f"13-count-{m}")["payload"]["data"]["winners"] == [WINNER]
           for m in ["irv", "schulze", "copeland", "kemeny_young", "bucklin", "fptp"]), \
    "prose assumes a unanimous winner; the data changed"

T: list[str] = []
add = T.append

add("""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="A worked, evidence-first tutorial: counting real human ballots under seven voting methods.">
  <title>Expected Parrot | Counting Real Ballots with voting</title>
  <style>
    :root{--green:#2e6b4f;--dark:#214d35;--light:#eef5f0;--amber:#b66b13;--ink:#1d211e;--muted:#5b665e;--rule:#dde5de;--code:#152019;--serif:Georgia,'Times New Roman',serif;--sans:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;--mono:'SF Mono',SFMono-Regular,ui-monospace,Menlo,Consolas,monospace;--measure:760px}
    *{box-sizing:border-box}html{scroll-behavior:smooth}
    body{margin:0;color:var(--ink);background:#fff;font:16px/1.62 var(--sans)}
    nav{position:fixed;top:0;bottom:0;left:0;width:310px;overflow-y:auto;padding:26px 26px 40px;color:#dfe9e2;background:var(--dark)}
    nav .brand{display:block;margin-bottom:20px;padding:12px 14px;color:var(--dark);background:#fff;border-radius:8px;text-decoration:none}
    nav .brand strong{display:block;font:700 19px var(--serif)}
    nav .brand small{color:#5b665e;font-size:11px;letter-spacing:.1em;text-transform:uppercase}
    nav .book{margin-bottom:20px;font:600 24px/1.25 var(--serif);color:#fff}
    nav .part{margin:18px 0 6px;font-size:11px;font-weight:800;letter-spacing:.14em;text-transform:uppercase;color:#9fc0ac}
    nav a.item{display:block;padding:4px 0;color:#dfe9e2;font-size:14px;text-decoration:none}
    nav a.item:hover{color:#fff}
    nav .small{margin-top:22px;color:#9fc0ac;font-size:12px}
    main{margin-left:310px}
    article{max-width:880px;padding:46px 56px 90px}
    .eyebrow{color:var(--green);font-size:12px;font-weight:800;letter-spacing:.13em;text-transform:uppercase}
    h1,h2,h3{font-family:var(--serif);font-weight:600;line-height:1.3}
    h1{max-width:780px;margin:14px 0 20px;font-size:clamp(38px,5vw,54px);letter-spacing:-.02em}
    h2{margin:78px 0 22px;padding:12px 0 8px;color:var(--green);font-size:31px;border-top:1px solid var(--rule);border-bottom:1px solid var(--rule)}
    h3{margin:40px 0 13px;font-size:22px}
    .dek{max-width:740px;color:var(--muted);font-size:20px;line-height:1.5}
    p,ul,ol,table,pre,.callout,figure,details.output{max-width:var(--measure)}
    a{color:var(--green)}
    code{padding:.14em .35em;background:#f0f3f0;border-radius:4px;font:88% var(--mono)}
    pre{position:relative;overflow:auto;margin:18px 0 26px;padding:20px 22px;color:#d8e3db;background:var(--code);border-radius:8px;font:13px/1.55 var(--mono)}
    pre code{padding:0;color:inherit;background:none}
    pre.command{border-left:4px solid var(--green);background:#18231d}
    .syntax-program{color:#7ddc9e;font-weight:700}.syntax-option{color:#e8b86d}.syntax-string{color:#b9d8ff}
    details.output{margin:-14px 0 26px}
    details.output summary{color:var(--green);font-size:13px;font-weight:700;cursor:pointer}
    details.output[open] summary{margin-bottom:8px}
    details.output pre{margin:0;white-space:pre-wrap;overflow-wrap:anywhere;max-height:480px;overflow:auto}
    figure{margin:30px 0 36px;padding:0;border:0}
    figure.human pre.human{margin:0 0 8px;color:var(--ink);background:#fbfdfb;border:1px solid var(--rule);border-left:4px solid #9fd3b2;overflow:auto}
    figcaption{color:var(--muted);font-size:13px}
    .callout{margin:24px 0;padding:18px 22px;background:linear-gradient(135deg,#f9fbf9,var(--light));border-left:4px solid var(--green);border-radius:0 8px 8px 0}
    .callout.warn{background:#fff7e9;border-color:var(--amber)}
    table{width:100%;margin:20px 0 28px;border-collapse:collapse;font-size:14px}
    th,td{padding:10px 12px;text-align:left;vertical-align:top;border-bottom:1px solid var(--rule)}
    th{color:#fff;background:var(--green)}
    tbody tr:nth-child(even){background:#f7f9f7}
    footer{margin-top:85px;padding-top:28px;color:var(--muted);border-top:3px solid var(--green);font-size:13px}
    @media(max-width:960px){nav{position:static;width:auto}main{margin-left:0}article{padding:28px 22px 70px}}
  </style>
</head>
<body>
<nav aria-label="Tutorial contents">
  <a class="brand" href="https://www.expectedparrot.com/"><strong>Expected Parrot</strong><small>Open-source research tools</small></a>
  <div class="book">Counting Real Ballots<br>with voting</div>
  <div class="part">Foundations</div>
  <a class="item" href="#question">1. The question and the data</a>
  <a class="item" href="#install">2. Installation and contract</a>
  <div class="part">Worked run</div>
  <a class="item" href="#setup">3. Set up the election</a>
  <a class="item" href="#survey">4. The hosted human survey</a>
  <a class="item" href="#ballots">5. Real ballots, fail-closed</a>
  <a class="item" href="#methods">6. Seven methods, one answer</a>
  <div class="part">Practice</div>
  <a class="item" href="#practice">7. Where everything lives</a>
  <div class="small">Every output on this page is a real captured envelope; the ballots are 18 real human responses from a production Expected Parrot Humanize survey.</div>
</nav>
<main><article>
  <div class="eyebrow">Expected Parrot · a practical, evidence-first tutorial</div>
  <h1>Counting real ballots under seven voting methods</h1>
  <p class="dek">Eighteen people ranked eight classic novels in a hosted survey. This tutorial rebuilds that election from scratch, imports their real ballots from production, and asks whether the winner depends on how you count.</p>
""")

add(f"""
  <section id="question">
    <h2><span class="chapter">01</span> The question and the data</h2>
    <p>Different voting methods can elect different winners from the same ballots — that is the entire reason this tool exists. Plurality rewards first-place strength; Borda rewards broad support; Condorcet methods reward head-to-head dominance; IRV rewards surviving eliminations. <code>voting</code> stores one set of inputs — options, voters, ballots — and lets any of 28 method names and aliases count them, so the comparison is always apples to apples.</p>
    <p>The worked example is real: an Expected Parrot <em>Humanize</em> survey titled "Classic book preference" asked respondents to rank eight classic novels. Eighteen people completed it. Their full rankings live in a production EDSL <code>Results</code> object, and this page imports them — actual human preferences, not synthetic data.</p>
    <div class="callout"><strong>If you follow along, expect small differences.</strong> Every command output on this page is a real captured envelope from one worked run. Ballot and result ids are generated per run, and timestamps will differ. The one step you cannot reproduce byte-for-byte is the data itself: the production Results object belongs to its owner's account, so substitute your own survey results (or cast ballots directly with <code>voting ballot rank</code>). Everything else — every command and the shape of every output — is what you will see. Outputs are JSON envelopes by default; add <code>--human</code> for a readable rendering.</div>
  </section>

  <section id="install">
    <h2><span class="chapter">02</span> Installation and the output contract</h2>
    {cmd("pip install git+https://github.com/expectedparrot/voting.git")}
    <p>Every command prints exactly one JSON envelope to stdout — <code>schema_version</code>, <code>command</code>, <code>status</code>, <code>argv</code>, <code>data</code>, <code>warnings</code>, <code>errors</code>, <code>next_steps</code> — with failures as structured errors and nonzero exits. <code>voting capabilities</code> states the contract machine-readably, and <code>voting next</code> always knows the next valid step:</p>
    {cmdcap_auto("01-version")}
  </section>

  <section id="setup">
    <h2><span class="chapter">03</span> Set up the election</h2>
    <p>A project is a directory with a <code>.voting/</code> store of small JSON entity files — inspectable with nothing but <code>cat</code>. Create it, and let <code>next</code> confirm where you are:</p>
    {cmdcap_auto("02-init")}
    {cmd("cd classic_books")}
    {cmdcap_auto("03-next")}
    <p>Register the eight books as options. The display names matter: when ballots arrive from a survey, answers reference options by these exact labels, and the importer maps labels back to ids fail-closed — an unknown label skips the row and tells you, it never guesses:</p>
    {cmdcap_auto("04-option-add")}
    <p>The other seven follow the same shape. Then define the election — ranked ballots, Borda as the default counting method (any method can be run against the stored ballots later) — attach the options, and open it:</p>
    {cmdcap_auto("05-election-add")}
    {cmdcap_auto("06-election-open")}
    {hcap("06h-election", "The election as a person reads it: eight options, ranked ballots, Borda default, open for ballots.")}
  </section>

  <section id="survey">
    <h2><span class="chapter">04</span> The hosted human survey</h2>
    <p><code>voting survey humanize</code> packages the election as a model-free EDSL job for Expected Parrot's Humanize platform — a web survey real people answer. The build is local and writes every artifact (job package, manifest, response schema):</p>
    {cmdcap_auto("07-humanize")}
    <div class="callout"><strong>Publishing happened once, for real.</strong> <code>voting survey publish</code> creates the hosted survey through the ep CLI, <code>voting survey email</code> sends invitation links, and <code>voting survey responses</code> downloads the answers — all outward-facing service actions, declared as such in <code>voting capabilities</code>. This tutorial's survey was published from the original project and left open; eighteen people responded. This page does not republish it — the next chapter pulls the responses that run collected.</div>
  </section>

  <section id="ballots">
    <h2><span class="chapter">05</span> Real ballots, fail-closed</h2>
    <p>The eighteen responses live in a production EDSL <code>Results</code> object. <code>ballot import</code> can read a local <code>.ep</code> package (<code>--from-results</code>) or pull one by UUID (<code>--from-coop</code>, a network read using your EDSL credentials). Watch what happens on a first, naive import:</p>
    {cmdcap_auto("08a-import-unregistered")}
    <p>All {N_BALLOTS} ballots recorded — with a warning per ballot: the respondents are anonymous survey takers, not registered voters. And the system is fail-closed about exactly that:</p>
    {cmdcap_auto("08b-validate-unregistered")}
    <p><strong>Zero valid ballots.</strong> Recorded is not the same as countable: a ballot from an unregistered voter is preserved but excluded from every count until you decide it belongs. This is the check to run before believing any result — a count over invalid ballots will happily report a "winner" that is nothing but a tiebreak among zeros. The deliberate fix is <code>--register-voters</code>, which registers each unknown respondent as a weight-1.0 voter (keeping the original respondent id as provenance on the ballot) and replaces the earlier ballots:</p>
    {cmdcap_auto("08-import")}
    {cmdcap_auto("09-validate")}
    <p>Eighteen registered voters, eighteen valid ballots. Here is what actually came back from real people — each row one respondent's full ranking:</p>
    {hcap("10-ballots", "The imported ballots: eighteen anonymous respondents, each with a complete ranking of the eight books, imported at weight 1.0.")}
    {cmdcap_auto("11-status")}
  </section>

  <section id="methods">
    <h2><span class="chapter">06</span> Seven methods, one answer</h2>
    <p>Now the point of the exercise. The same eighteen ballots, counted seven ways — the election's default first:</p>
    {cmdcap_auto("12-count-borda")}
    <p>Borda gives <em>{html.escape(BORDA_SCORES[0]["option_id"])}</em> {BORDA_SCORES[0]["total"]:.0f} points against {html.escape(BORDA_SCORES[1]["option_id"])}'s {BORDA_SCORES[1]["total"]:.0f}. Then the rest — instant-runoff, two Condorcet methods, Kemeny–Young, Bucklin, and bare plurality on first preferences:</p>
    {cmdcap_auto("13-count-irv")}
    {cmdcap_auto("13-count-schulze")}
    {cmdcap_auto("13-count-copeland")}
    {cmdcap_auto("13-count-kemeny_young")}
    {cmdcap_auto("13-count-bucklin")}
    {cmdcap_auto("13-count-fptp")}
    {cmdcap_auto("14-count-list")}
    {hcap("14h-count-list", "Every saved count, side by side: seven methods, one winner.")}
    <p><strong>All seven agree: <em>1984</em> wins.</strong> That unanimity is itself the finding. Orwell's novel holds {FPTP_TOTALS[0]["total"]:.0f} of {N_BALLOTS} first preferences, the top Borda score, and — as Schulze, Copeland, and Kemeny–Young confirm — beats every rival head-to-head. When a candidate dominates like this, the choice of method cannot change the outcome; method choice matters exactly when support is fragmented, and these ballots are not fragmented at the top. (Beneath the winner the orderings do shuffle — compare the full <code>ranking</code> arrays across the envelopes above.)</p>
    <div class="callout"><strong>What this page cannot claim.</strong> Eighteen self-selected respondents are a poll of those eighteen people, not of readers in general. The demonstration is methodological — one auditable dataset, many counting rules, disclosed outputs — not a literary verdict.</div>
  </section>

  <section id="practice">
    <h2><span class="chapter">07</span> Where everything lives</h2>
    <p>Every entity is a JSON file under <code>.voting/</code>: options, voters, ballots (append-only records; re-imports warn <code>ballot_overwritten</code>), and one saved result per count, so comparisons never overwrite each other. <code>next</code> closes the loop:</p>
    {cmdcap_auto("15-next-final")}
    <table><thead><tr><th>Need</th><th>Command family</th></tr></thead><tbody>
      <tr><td>Discover the workflow</td><td><code>version</code>, <code>capabilities</code>, <code>status</code>, <code>next</code>, <code>docs list</code></td></tr>
      <tr><td>Define the electorate</td><td><code>option add</code>, <code>voter add</code>, <code>election add|add-option|open</code></td></tr>
      <tr><td>Collect ballots</td><td><code>ballot rank|cast|approve|score</code>, <code>survey generate</code>, <code>survey humanize|publish|email|responses</code></td></tr>
      <tr><td>Import and audit</td><td><code>ballot import --from|--from-results|--from-coop [--register-voters]</code>, <code>ballot validate</code>, <code>ballot list</code></td></tr>
      <tr><td>Count and compare</td><td><code>count run [--method]</code>, <code>count list</code>, <code>count show</code></td></tr>
    </tbody></table>
    <p>Exact options and defaults belong to <code>voting &lt;command&gt; --help</code>; the README's generated command reference lists all 46 commands and is enforced against the CLI by <code>tests/test_contract_sync.py</code>.</p>
  </section>

  <footer>
    <p><strong>voting</strong> is an open-source Expected Parrot research tool, released under the MIT License. Source and issue tracking on <a href="https://github.com/expectedparrot/voting">GitHub</a>. The ballots shown are real responses to a hosted Humanize survey, identified only by anonymous respondent ids; regenerate this page with <code>scripts/book_driver.py</code> and <code>scripts/build_index.py</code>.</p>
  </footer>
</article></main>
<script>
  document.querySelectorAll("details.output").forEach(d=>{{const s=d.querySelector("summary");d.addEventListener("toggle",()=>{{s.textContent=d.open?"Hide command output":"Show command output"}})}});
  document.querySelectorAll("pre.command code").forEach(code=>{{
    let t=code.textContent;
    if(!/^(?:voting|pip|cd|ep)\\b/.test(t.trim()))return;
    code.innerHTML=t.replace(/(--[\\w-]+)|("[^"]*")|^(voting|pip|cd|ep)\\b/gm,(m,opt,str,prog)=>prog?`<span class="syntax-program">${{prog}}</span>`:opt?`<span class="syntax-option">${{opt}}</span>`:`<span class="syntax-string">${{str}}</span>`);
  }});
</script>
</body>
</html>
""")

OUT.write_text("".join(T))
print(f"wrote {OUT} {OUT.stat().st_size} bytes")
