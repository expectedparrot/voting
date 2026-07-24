# voting — election-method modeling and ballot analysis CLI
<!-- id: voting/voting -->

voting models social-choice problems with options, voters, elections, ballots, and counting methods across plurality, ranked, approval, score, grade, allocation, Condorcet, and multi-winner families. The agent uses it to help the user define the electorate and ballot format, cast or import ballots, compare counting methods, inspect winners/rankings, generate synthetic preference studies, and publish Humanize surveys for real voters.

## Copy and paste into Codex or Claude Code

```text
Set up voting and help me model and run an election.

Install the current voting and EDSL `main` branches from GitHub. If `uv` is not
installed, first run `python -m pip install --upgrade uv`. Then install voting
as a managed tool, including the EDSL executable used for generated and hosted
surveys:

uv tool install --upgrade --force \
  --with-executables-from "edsl @ git+https://github.com/expectedparrot/edsl.git@main" \
  "voting[humanize] @ git+https://github.com/expectedparrot/voting.git@main"

Verify that both command-line tools are available:

voting --help
ep --help

Ask me for a project name and a short description of the decision, candidates
or proposals, voters, and whether I need a single winner, ranking, or multiple
winners. Then run `voting init <project_name> --description "<description>"`,
enter the new project directory, and run `voting status`.

Treat voting's JSON output as the source of truth. Follow each command's
`next_steps`, using `voting status` whenever the next action is unclear. Before
counting, confirm the election method and ballot type with me, add eligible
options, open the election, collect or import ballots, and validate them. Use
`voting docs show voting-methods` when helping me choose a method. Do not invent
preferences or silently resolve substantive ties or data errors.

Only if I ask to generate an AI survey or publish a Humanize survey, run
`ep auth status`. If authentication is missing, run `ep auth login` and follow
its login flow; let the EDSL CLI create and manage the repository-local `.env`.
Never display, copy, or commit API keys. Then run `ep profiles current` to
inspect the redacted configuration and `ep check` to verify connectivity.
```

Local ballot entry, validation, and counting do not require EDSL
authentication. The `humanize` extra and `ep` setup are included above so the
agent can also generate or publish surveys when requested.

## When to use this
<!-- id: voting/when-to-use -->

- The user needs to choose winners or rankings from ballots, voter preferences, or simulated electorates.
- The question is about election rules, voting methods, social choice, or preference aggregation.
- The user wants to compare methods such as plurality, approval, score, STAR, IRV, Condorcet, STV, or majority judgment.
- Options and voters can be represented explicitly, even if ballots are synthetic or imported later.

## When this is a stretch (and how to adapt)
<!-- id: voting/when-stretch -->

- The decision is criteria scoring by a committee rather than ballots. Use [mcda](#mcda/mcda), or convert criteria judgments into ballots only if social choice is the point.
- The user has survey preferences but no ballot format. Use `voting survey generate` for synthetic agents or `voting survey humanize` for a hosted human ballot.
- The user wants strategic scenario planning. Use [kahn](#kahn/kahn) for scenarios and voting only if stakeholders vote on options.
- The election is legally binding or security-critical. Use voting for analysis and method comparison, not as an election administration or audit system.
- The electorate is hypothetical. Model voters and ballots transparently, and report that results are scenario-based.

## Decision rule for the calling agent
<!-- id: voting/decision-rule -->

Before dispatching to voting, confirm:

1. The objects being selected are candidates, proposals, projects, vendors, or other options.
2. Preferences are represented as ballots, rankings, approvals, scores, grades, allocations, or generated survey responses.
3. The user cares about a voting/counting rule or comparison across rules.
4. The result should be a winner, ranking, seat allocation, or method-comparison artifact.

If yes to all four, voting is the right method.

## Inputs and elicitation
<!-- id: voting/inputs -->

### Options
<!-- id: voting/inputs-options -->

What it is: the candidates, proposals, projects, or alternatives that can win.

How the agent elicits this:
- Ask what the options are and whether any are ineligible or reference-only.
- Ask whether options need traits or descriptions for survey generation.
- Use stable IDs separate from display names.

Default to suggest: include all viable options and mark withdrawn/ineligible options explicitly rather than deleting history.

Fallback: if options are still being developed, use [mcda](#mcda/mcda) or [kahn](#kahn/kahn) first to clarify the option set.

### Voters and electorate
<!-- id: voting/inputs-voters -->

What it is: the voters, voter weights, eligibility, and optional traits for analysis or simulation.

How the agent elicits this:
- Ask whether voters are real participants, stakeholder groups, synthetic personas, or anonymous ballots.
- Ask whether all voters have equal weight.
- Ask whether eligibility changes by election or option.

Default to suggest: equal-weight voters unless the user has a defensible weighting scheme.

Fallback: for anonymous ballots, create aggregate or synthetic voter IDs sufficient to store ballots without personal data.

### Election method and ballot type
<!-- id: voting/inputs-election-method -->

What it is: the counting rule, number of seats, ballot format, tie policy, and eligible options.

How the agent elicits this:
- Ask whether the user needs a single winner, ranking, multi-winner result, allocation, or method comparison.
- Match ballot format to method: ranked for IRV/Condorcet/STV, approval for approval/block voting, scores for score/STAR, grades for majority judgment.
- Ask whether tie policy matters for reporting.

Default to suggest: compare at least one simple method and one richer preference method when the user is evaluating a rule.

Fallback: if users already supplied a ballot format, choose methods compatible with that ballot rather than forcing recoding.

### Ballots
<!-- id: voting/inputs-ballots -->

What it is: the recorded voter preferences for an election.

How the agent elicits this:
- Ask whether ballots are already available or need to be generated through a survey.
- Ask whether incomplete ballots are valid and how to handle abstentions.
- Ask whether ballots should be validated before counting.

Default to suggest: validate ballots before every count run, especially after method or eligibility changes.

Fallback: if ballots are missing, use `voting survey generate` for synthetic preferences or `voting survey humanize` for real respondents.

## Outputs
<!-- id: voting/outputs -->

voting produces:

- `.voting/` project state with options, voters, elections, ballots, counts, and generated survey artifacts.
- Election results with winners, rankings, seat allocations, pairwise matrices, score summaries, or method-specific diagnostics.
- Saved count snapshots under project results state.
- Status output with current phase, counts, and recommended next steps.
- Generated EDSL scripts for synthetic agents and model-free Humanize jobs for hosted human ballots.

## Workflow
<!-- id: voting/workflow -->

Canonical sequence:

1. `voting init` — create the project.
2. `voting option ...` — add candidates/proposals/options.
3. `voting voter ...` — add voters, weights, traits, or eligibility.
4. `voting election ...` — create an election with method, ballot type, seats, and tie policy.
5. `voting election add-option ...` — attach eligible options.
6. `voting ballot ...` — cast, rank, approve, score, grade, allocate, import, list, and validate ballots.
7. `voting count run` — count the election with the configured method.
8. `voting count show` or `voting count list` — inspect saved results.
9. Repeat count runs with alternative methods for method comparison.
10. `voting survey ...` — generate EDSL scripts when ballots need to be elicited.

For a hosted survey that humans can open in a browser, generate a model-free
EDSL Humanize job and publish it through the `ep` CLI:

```bash
voting survey humanize ranked_pref
voting survey publish ranked_pref
```

The publish response includes the respondent and admin URLs. To send unique
links by email, first store an email trait for every registered voter, then
include that trait when building the job:

```bash
voting voter set-trait v1 email '"v1@example.com"'
voting survey humanize ranked_pref --email-trait email
voting survey publish ranked_pref
voting survey email ranked_pref --name "Voting invitation"
```

Humanize support requires the optional dependency: `pip install -e '.[humanize]'`.

Use `voting status` to recover phase and next actions.

## Worked examples
<!-- id: voting/examples -->

### Comparing approval and ranked methods
<!-- id: voting/example-method-comparison -->

User: "We have five project proposals and want to know whether approval voting changes the winner compared with ranked choice."

Agent: "Voting is the right tool. I’ll register the proposals as options, add voters or anonymous voter IDs, create one approval election and one ranked election, validate ballots for each format, then compare count results."

User: "Ballots are in CSV, but we can start with three test voters."

Agent: "I’ll create a small project and cast test ballots first so we verify formats before import."

```bash
voting init project_vote
voting option add park --name "Park renovation"
voting option add library --name "Library hours"
voting voter add v1
voting voter add v2
voting election add approval_round --method approval --ballot-type approval
voting election add ranked_round --method irv --ballot-type ranked
voting ballot approve approval_round v1 park library
voting ballot rank ranked_round v1 library park
voting ballot validate approval_round
voting count run approval_round
voting count run ranked_round
```

Output: saved count results for both methods that can be compared in the report.

### Generating a preference survey
<!-- id: voting/example-survey-generation -->

```bash
voting option add a "Option A"
voting option add b "Option B"
voting election add ranked_pref "Ranked preference" --method copeland --ballot-type ranked
voting election add-option ranked_pref a
voting election add-option ranked_pref b
voting survey generate ranked_pref
voting --human survey show ranked_pref
```

Output: an inspectable EDSL script for collecting compatible synthetic ranked ballots. For real voters, run `voting survey humanize ranked_pref` followed by `voting survey publish ranked_pref`.

## Quick command reference
<!-- id: voting/commands -->

For full options, run `voting <subcommand> --help`.

| Command | Purpose |
|---|---|
| `voting init` / `info` | Initialize or summarize a project. |
| `voting status` | Show phase, counts, and next steps. |
| `voting option ...` | Manage candidates, proposals, or options. |
| `voting voter ...` | Manage voters, traits, weights, and eligibility. |
| `voting election ...` | Manage elections, methods, seats, options, and tie policy. |
| `voting ballot ...` | Cast, import, list, show, and validate ballots. |
| `voting count run/list/show` | Run and inspect election counts. |
| `voting survey generate/show` | Generate and inspect model-based EDSL preference scripts. |
| `voting survey humanize/publish/email/responses` | Create, distribute, and retrieve hosted human surveys. |
| `voting docs` | Read built-in method and Humanize guidance. |

## Common pitfalls
<!-- id: voting/pitfalls -->

- Ballot type must match the counting method; approval ballots cannot be counted as ranked ballots without recoding assumptions.
- Method comparisons are only meaningful on the same electorate and option eligibility set.
- Weighted voters can dominate results; document any non-equal weights.
- Multi-winner methods need seat count and quota/tie details specified before interpretation.
- This package analyzes voting rules; it is not an election-security, identity, or legal-audit system.

## Cross-references
<!-- id: voting/xrefs -->

- Upstream: [oneheart](#oneheart/oneheart) or EDSL surveys can generate simulated voter preferences; [saldana](#saldana/saldana) can create persona panels for synthetic electorates.
- Adjacent methods: [mcda](#mcda/mcda) for criteria-based decisions; [green](#green/green) for conjoint preference estimation.
- Reporting: [gutenberg](#gutenberg/gutenberg), [herndon](#herndon/herndon), and [sonesta](#sonesta/sonesta) can package election results.

## State contract
<!-- id: voting/state -->

`.voting/` stores options, voters, elections, ballots, count results, status projections, and generated survey artifacts. Ballots and count snapshots are append-only analysis records; rerun counts after method, eligibility, or ballot changes.

## JSON output and error codes
<!-- id: voting/json -->

voting uses structured output unless `--human` is requested. Common recoverable errors include invalid IDs, missing elections/options/voters, incompatible ballot type and method, ineligible options, malformed ballots, and count precondition failures.
