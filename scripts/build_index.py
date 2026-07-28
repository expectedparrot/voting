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

# Envelopes shown at full fidelity (the reader should see the complete
# contract at least once). Everything else gets elided for readability —
# the untrimmed captures live in build/tutorial/captures/.
FULL = {"01-version", "02-init", "03-next", "04-election-add", "06-election-open"}


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
        items = list(value.items())
        if depth >= 2 and len(items) > 5:
            trimmed = {k: _trim(v, depth + 1) for k, v in items[:4]}
            trimmed["…"] = f"{len(items) - 4} further keys elided"
            return trimmed
        return {k: _trim(v, depth + 1) for k, v in items}
    return value


def render_payload(name: str) -> str:
    payload = clean(load(name)["payload"])
    if name not in FULL:
        if isinstance(payload.get("data"), dict):
            payload["data"] = _trim(payload["data"])
        if len(payload.get("warnings") or []) > 3:
            n = len(payload["warnings"])
            payload["warnings"] = payload["warnings"][:2] + [
                f"… {n - 2} further warnings elided ({n} total) …"
            ]
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


def svgfig(capture_name: str, caption: str) -> str:
    """Inline the SVG a captured `voting plot ...` command wrote, with its command."""
    payload = load(capture_name)
    svg = Path(payload["payload"]["data"]["path"]).read_text()
    return (
        cmdcap_auto(capture_name)
        + f'\n    <figure class="plot">{svg}<figcaption>{caption}</figcaption></figure>'
    )


def hcap(name: str, caption: str) -> str:
    text = (CAPTURES / f"{name}.txt").read_text()
    body = html.escape(text.rstrip())
    return (
        f'<figure class="human"><pre class="human"><code>{body}</code></pre>'
        f"<figcaption>{caption}</figcaption></figure>"
    )


# Facts from the captured run, extracted so prose can never drift from data.
IMPORT = load("08-import")["payload"]["data"]
COMPARE = load("12-count-compare")["payload"]["data"]
BORDA = load("13-show-borda")["payload"]["data"]
N_BALLOTS = IMPORT["cast"]
BORDA_SCORES = sorted(BORDA["scores"], key=lambda s: -s["total"])
RESULT_IDS = {row["method"]: row["result_id"] for row in COMPARE["results"]}


def _saved_result(method: str) -> dict:
    return json.loads((WORK / ".voting" / "results" / f"{RESULT_IDS[method]}.json").read_text())


FPTP_TOTALS = sorted(_saved_result("fptp")["scores"], key=lambda s: -s["total"])
WINNER = BORDA["winners"][0]
N_METHODS = len(COMPARE["methods_run"])
DECIDED = [row for row in COMPARE["results"] if row["winners"]]
RUNOFF_RUNNER_UP = next(row["runner_up"] for row in COMPARE["results"] if row["method"] == "runoff")
assert COMPARE["unanimous_winners"] == [WINNER], "prose assumes unanimity among deciding methods"
assert COMPARE["no_winner"] == ["simple_majority"], "prose assumes exactly simple_majority declines"
assert all(row["winners"] == [WINNER] for row in DECIDED), "prose assumes every deciding method agrees"
HUMANIZE = load("07-humanize")["payload"]["data"]
STATUS_COUNTS = load("11-status")["payload"]["data"]["counts"]
QUESTION_TEXT = HUMANIZE["question_texts"]["ranking"]
BOOKS_JSON = (WORK / "books.json").read_text().rstrip()
N_COMMANDS = (REPO / "README.md").read_text().count("| `voting ")

T: list[str] = []
add = T.append

add("""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="A worked, evidence-first tutorial: counting real human ballots under twelve voting methods.">
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
    figure.plot{max-width:820px}
    figure.plot svg{width:100%;height:auto;border:1px solid var(--rule);border-radius:8px}
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
  <a class="item" href="#setup">3. Set up the project</a>
  <a class="item" href="#election">4. Define the election</a>
  <a class="item" href="#survey">5. The hosted human survey</a>
  <a class="item" href="#ballots">6. Ballots that don't count (yet)</a>
  <a class="item" href="#methods">7. Every method, one answer</a>
  <div class="part">Practice</div>
  <a class="item" href="#practice">8. Where everything lives</a>
  <div class="small">Every output on this page is a real captured envelope; the ballots are 18 real human responses from a production Expected Parrot Humanize survey.</div>
</nav>
<main><article>
  <div class="eyebrow">Expected Parrot · a practical, evidence-first tutorial</div>
  <h1>Counting real ballots under twelve voting methods</h1>
  <p class="dek">Eighteen people ranked eight classic novels in a hosted survey on Expected Parrot. This tutorial shows how the <code>voting</code> package works with those votes — and how different ways of tallying them do (or don't) change the outcome.</p>
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
    {cmd("uv tool install git+https://github.com/expectedparrot/voting.git")}
    <p>(<code>uv tool</code> gives <code>voting</code> its own isolated environment on your PATH; plain <code>pip install</code> works too.) Confirm the install:</p>
    {cmdcap_auto("01-version")}
    <p>That envelope is the whole interface. Every command prints exactly one JSON envelope to stdout — <code>schema_version</code>, <code>command</code>, <code>status</code>, <code>argv</code>, <code>data</code>, <code>warnings</code>, <code>errors</code>, <code>next_steps</code> — with failures as structured errors and nonzero exits. Add <code>--human</code> to any command for tables meant for people instead. <code>voting capabilities</code> states the contract machine-readably, including which commands touch the outside world:</p>
    {cmdcap_auto("01b-capabilities")}
    <div class="callout">Longer envelopes on this page are elided — lists cut to a few entries, repeated warnings summarized — so the shape stays readable. The first few outputs are shown complete; the full captures live in <code>build/tutorial/captures/</code> when you regenerate the page.</div>
  </section>

  <section id="setup">
    <h2><span class="chapter">03</span> Set up the project</h2>
    <p>Create a project and step into it. All state lives inside the project directory as plain JSON files, so everything the tool does is inspectable and versionable — the layout is covered at the end.</p>
    {cmdcap_auto("02-init")}
    {cmd("cd classic_books")}
    <p><code>voting next</code> is the orientation command: it reports the current phase and the exact commands that make sense now. It exists mostly for AI agents driving the CLI — an agent that only knows how to run <code>voting next</code> can navigate the whole workflow — but it is just as useful when a person comes back to a project cold:</p>
    {cmdcap_auto("03-next")}
  </section>

  <section id="election">
    <h2><span class="chapter">04</span> Define the election</h2>
    <p>An <em>election</em> is the central object here: it names the contest, fixes the <strong>ballot type</strong> (ranked, in this case — voters order all options; other types are single choice, approval, and score), and holds the list of eligible options. Deliberately absent: a counting method. The ballot type determines what voters are asked; <em>how the ballots are counted is a lens you apply afterwards</em> — as many lenses as you like, which is the whole point of chapter 7. An election starts as a draft and only accepts ballots once opened:</p>
    {cmdcap_auto("04-election-add")}
    <p>The eight books load in one step from a JSON file — id plus display name each. The display names matter: when ballots arrive from a survey, answers reference options by these exact labels, and the importer maps labels back to ids. An unknown label skips that row and reports it; nothing is ever silently guessed. (<code>voting option add</code> exists for adding one at a time.)</p>
    <p>Alongside options, a project also keeps a <strong>voter registry</strong> — who may vote, at what weight, with what traits. Ours is deliberately still empty; that becomes the crux of chapter 6.</p>
    <pre class="command"><code>cat books.json</code></pre>
    <details class="output"><summary>Show books.json</summary><pre><code>{html.escape(BOOKS_JSON)}</code></pre></details>
    {cmdcap_auto("05-option-import")}
    <p>Open the election and look at it the way a person would — <code>--human</code> renders tables instead of JSON:</p>
    {cmdcap_auto("06-election-open")}
    {hcap("06h-election", "The election at a glance: eight options, ranked ballots, open for ballots — and no counting method, because that decision belongs to the count.")}
  </section>

  <section id="survey">
    <h2><span class="chapter">05</span> The hosted human survey</h2>
    <p><code>voting survey humanize</code> packages the election for Expected Parrot's Humanize platform — a hosted web survey that real people answer. (Technically it is an EDSL survey job with no AI model attached: the questions are for humans.) The question wording is generated from the election definition itself — name, description, ballot type — and the manifest records it. This election produced exactly one question:</p>
    <div class="callout"><em>{html.escape(QUESTION_TEXT)}</em><br><small>— followed by the eight book titles, in randomized order per respondent.</small></div>
    <p>The build is local and writes every artifact (job package, manifest with the question text, response schema):</p>
    {cmdcap_auto("07-humanize")}
    <div class="callout"><strong>Publishing happened once, for real.</strong> <code>voting survey publish</code> creates the hosted survey through the ep CLI, <code>voting survey email</code> sends invitation links, and <code>voting survey responses</code> downloads the answers — all outward-facing service actions, declared as such in <code>voting capabilities</code>. This tutorial's survey was published from the original project and left open; eighteen people responded. This page does not republish it — the next chapter pulls the responses that survey collected.</div>
  </section>

  <section id="ballots">
    <h2><span class="chapter">06</span> Ballots that don't count (yet)</h2>
    <p>The eighteen responses live in a production EDSL <code>Results</code> object. <code>ballot import</code> can read a local <code>.ep</code> package (<code>--from-results</code>) or pull one by UUID (<code>--from-coop</code>, a network read using your EDSL credentials). Watch what happens on a first, naive import:</p>
    <div class="callout"><strong>Following along without a survey?</strong> This is the one place you cannot use this page's data (the Results object belongs to its owner). Cast a few ballots yourself instead and rejoin at chapter 7 — every count works the same:
<pre class="command"><code>voting voter add v1 'Voter One'
voting ballot rank book_preference v1 nineteen_eighty_four mockingbird great_gatsby</code></pre>
Or run your own survey (<code>voting survey publish</code>) — or have AI personas vote: <code>voting survey generate</code> builds a job you execute with <code>ep run</code> and import with <code>--from-results</code>.</div>
    {cmdcap_auto("08a-import-unregistered")}
    <p>All {N_BALLOTS} ballots recorded — with a warning per ballot: the respondents are anonymous survey takers, not registered voters. When something is off, <code>voting</code>'s policy is to record the problem and refuse to count, rather than guess. Validation makes that concrete:</p>
    {cmdcap_auto("08b-validate-unregistered")}
    <p><strong>Zero valid ballots.</strong> Recorded is not the same as countable: a ballot from an unregistered voter is preserved but excluded from every count until you decide it belongs. This is the check to run before believing any result — a count over invalid ballots will happily report a "winner" that is nothing but a tiebreak among zeros. The deliberate fix is <code>--register-voters</code>, which registers each unknown respondent as a weight-1.0 voter (keeping the original respondent id as provenance on the ballot) and replaces the earlier ballots:</p>
    {cmdcap_auto("08-import")}
    {cmdcap_auto("09-validate")}
    <p>Eighteen registered voters, eighteen valid ballots. Here is what actually came back from real people — one row per respondent, top choices first (<code>--latest</code> shows the ballots a count would use; without it, the append-only record also lists the eighteen superseded ballots from the first import):</p>
    {hcap("10-ballots", "The countable ballots: eighteen anonymous respondents at weight 1.0, top three choices shown; full rankings live in the ballot records and drive every count.")}
    <p>Eighteen full rankings are hard to eyeball. The built-in plots turn them into a picture — <code>voting plot ranks</code> shows, for each book, how many voters placed it first, second, and so on (hover any segment for the exact count):</p>
    {svgfig("11b-plot-ranks", f"Position distributions from the real ballots. {WINNER}'s long dark leading edge is its {FPTP_TOTALS[0]['total']:.0f} first-place votes; books lower down live mostly in the pale right-hand (late-rank) end of the bar.")}
    <p><code>voting status</code> is the project's dashboard. Note the ballot count: {STATUS_COUNTS["ballots"]} records, not {N_BALLOTS} — the superseded first import is still in the append-only log (an audit trail, never silently rewritten), while counting uses each voter's latest ballot. The phase says exactly what remains:</p>
    {cmdcap_auto("11-status")}
  </section>

  <section id="methods">
    <h2><span class="chapter">07</span> Every method, one answer</h2>
    <p>Now the point of the exercise. Counts name their method explicitly (<code>voting count run &lt;id&gt; --method borda</code>) — there is no default, and that is a feature: a "winner" is always a <em>method's</em> winner. But nobody should have to type twelve commands to ask the obvious question. <code>voting count compare</code> counts the same ballots under <strong>every method that can read them</strong> — for ranked ballots, all {N_METHODS} — and saves each result:</p>
    {cmdcap_auto("12-count-compare")}
    {hcap("12h-count-list", f"Twelve methods, side by side. {len(DECIDED)} elect {WINNER}; simple_majority declines.")}
    <p><strong>{len(DECIDED)} of {N_METHODS} methods elect <em>1984</em>. The twelfth refuses to answer</strong> — and its refusal is worth reading. <code>simple_majority</code> requires an outright majority of first preferences; {WINNER} holds {FPTP_TOTALS[0]["total"]:.0f} of {N_BALLOTS}, a plurality but not a majority, so the method reports <code>winners: []</code> with the threshold it applied. Like the unregistered-ballot check in chapter 6, an honest refusal beats a fabricated answer.</p>
    <p>Every comparison run is a full saved record of how its method reasoned. Open a few with <code>count show</code>. Borda first — each ballot position contributes points, so it measures breadth of support:</p>
    {cmdcap_auto("13-show-borda")}
    {hcap("13h-show-borda", "The saved Borda count rendered for people: full ranking, scores, and the winner.")}
    {svgfig("13p-plot-scores", "Borda totals as a picture: the gaps show breadth of support, not just first choices.")}
    <p>Borda gives <em>{html.escape(BORDA_SCORES[0]["option_id"])}</em> {BORDA_SCORES[0]["total"]:.0f} points against {html.escape(BORDA_SCORES[1]["option_id"])}'s {BORDA_SCORES[1]["total"]:.0f}. <strong>Instant-runoff</strong> reasons completely differently — eliminate the weakest option, retry until someone holds a majority — and its <code>rounds</code> array is that elimination story:</p>
    {cmdcap_auto("13-show-irv")}
    <p><strong>Schulze</strong> (a Condorcet method) plays every option against every other; the <code>pairwise</code> matrix holds all 28 head-to-head margins, and <code>voting plot pairwise</code> makes it legible at a glance:</p>
    {cmdcap_auto("13-show-schulze")}
    {svgfig("13p-plot-pairwise", f"Every head-to-head from the real ballots: a cell is the row's margin over the column. {WINNER}'s top row is solid green — it beats all seven rivals directly, which is why all five Condorcet-family methods (schulze, copeland, minimax, ranked_pairs, kemeny_young) must elect it.")}
    <p>The rest tell the same story in different dialects: <strong>copeland</strong> scores those pairings as wins minus losses, <strong>kemeny_young</strong> searches for the ordering that agrees with the most pairwise judgments, <strong>bucklin</strong> keeps adding voters' next choices until someone crosses half, <strong>runoff</strong> stages a two-option finale ({html.escape(WINNER)} vs {html.escape(RUNOFF_RUNNER_UP)}), and <strong>fptp</strong> throws away everything but the first line. Their envelopes are all in <code>count list</code>:</p>
    {cmdcap_auto("14-count-list")}
    <p>And the thesis of this whole page, as one picture — <code>voting plot methods</code> grids every option's finishing position under every saved count:</p>
    {svgfig("14p-plot-methods", "The answer to the tutorial's question. The unbroken dark top row is the finding: no counting method changes the winner (the asterisk marks simple_majority, which ranks but declines to declare). The shuffling in the middle rows is where method choice does matter.")}
    <p><strong>Every method that names a winner names <em>1984</em>.</strong> That unanimity is itself the finding. Orwell's novel holds {FPTP_TOTALS[0]["total"]:.0f} of {N_BALLOTS} first preferences, the top Borda score, and beats every rival head-to-head. When a candidate dominates like this, the choice of method cannot change the outcome; method choice matters exactly when support is fragmented, and these ballots are not fragmented at the top. (Beneath the winner the orderings do shuffle — compare the <code>ranking</code> arrays across the saved results.)</p>
    <div class="callout"><strong>What this page cannot claim.</strong> Eighteen self-selected respondents are a poll of those eighteen people, not of readers in general. The demonstration is methodological — one auditable dataset, many counting rules, disclosed outputs — not a literary verdict.</div>
  </section>

  <section id="practice">
    <h2><span class="chapter">08</span> Where everything lives</h2>
    <p>Every entity the project holds is a small JSON file under the project's <code>.voting/</code> directory: options, voters, ballots (append-only records; re-imports warn <code>ballot_overwritten</code>), and one saved result per count, so comparisons never overwrite each other — all inspectable with nothing but <code>cat</code>. <code>next</code> closes the loop:</p>
    {cmdcap_auto("15-next-final")}
    <table><thead><tr><th>Need</th><th>Command family</th></tr></thead><tbody>
      <tr><td>Discover the workflow</td><td><code>version</code>, <code>capabilities</code>, <code>status</code>, <code>next</code>, <code>docs list</code></td></tr>
      <tr><td>Define the electorate</td><td><code>option add|import</code>, <code>voter add</code>, <code>election add|add-option|open</code></td></tr>
      <tr><td>Collect ballots</td><td><code>ballot rank|cast|approve|score</code>, <code>survey generate</code>, <code>survey humanize|publish|email|responses</code></td></tr>
      <tr><td>Import and audit</td><td><code>ballot import --from|--from-results|--from-coop [--register-voters]</code>, <code>ballot validate</code>, <code>ballot list</code></td></tr>
      <tr><td>Count and compare</td><td><code>count run [--method]</code>, <code>count list</code>, <code>count show</code></td></tr>
    </tbody></table>
    <p>Exact options and defaults belong to <code>voting &lt;command&gt; --help</code>; the README's generated command reference lists all {N_COMMANDS} commands and is enforced against the CLI by <code>tests/test_contract_sync.py</code>.</p>
    <p>That is the whole loop. The natural next step is to run it on a question you actually care about: define your options, publish the survey to the people whose answer matters (or let AI personas vote via <code>survey generate</code> and <code>ep run</code>), and — before believing any winner — check <code>ballot validate</code>, then count it more than one way. If all the methods agree, you have a robust answer. If they disagree, you have something more interesting.</p>
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
