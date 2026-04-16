# Voting CLI Specification

`voting` is a JSON-first command-line tool for defining elections, registering options and
voters, recording ballots, and running multiple voting methods against the same stored
inputs.

The tool is intentionally structured like `/Users/jjhorton/tools/mcda`: a Typer-based CLI,
project-local hidden data directory, small JSON entity files, structured JSON output,
structured JSON errors, and focused vertical-slice tests.

---

## Goals

- Create a local voting project that can hold one or more elections.
- Register options, voters, and ballots with reproducible audit trails.
- Support a broad suite of voting methods from the same project data, including
  plurality, majority, ranked, transferable, approval, score, Condorcet, grade, runoff,
  and allocation-based methods.
- Keep the CLI scriptable by returning JSON by default.
- Provide concise human output when requested with `--human`.
- Make election assumptions explicit: seats, ballot type, tie policy, exhausted ballots,
  invalid ballots, and winner eligibility.

## Non-Goals For V1

- Cryptographic election security.
- Anonymous ballot mixing.
- Networked or multi-user persistence.
- Legal compliance for governmental elections.
- GUI or web UI.
- Party-list proportional representation systems. The target scope is candidate/option
  voting, including practical multi-seat STV.

---

## Installation And Entrypoint

The package should use a minimal `pyproject.toml` similar to `mcda`.

```toml
[project]
name = "voting"
version = "0.1.0"
description = "JSON-first CLI for voting scenarios"
requires-python = ">=3.11"
dependencies = [
  "rich",
  "typer",
]

[project.optional-dependencies]
dev = ["pytest"]

[project.scripts]
voting = "voting.cli:main"
```

Local usage:

```bash
pip install -e .
voting --help
python -m voting.cli --help
```

---

## Project Layout

A voting project is a normal directory containing `.voting/meta.json`. Commands find the
project by walking upward from the current directory, or by using `--project <path>`.

```text
budget_vote/
  .voting/
    meta.json
    elections/
    options/
    voters/
    ballots/
    policies/
    sessions/
    results/
    reports/
```

Initial v1 subdirectories:

| Directory | Purpose |
| --- | --- |
| `elections/` | Election definitions and method defaults. |
| `options/` | Choices that can appear on ballots. |
| `voters/` | Registered voters, delegates, groups, or synthetic agents. |
| `ballots/` | Timestamped ballot records. |
| `policies/` | Reusable tie-breaking and validation policies. |
| `sessions/` | Optional live voting sessions. |
| `results/` | Analysis output snapshots. |
| `reports/` | Future human-readable summaries. |

`meta.json`:

```json
{
  "id": "budget_vote",
  "title": "Budget Vote",
  "description": "Choose a neighborhood project.",
  "created_at": "2026-04-16T09:30:00",
  "settings": {
    "default_tie_policy": "lexicographic",
    "allow_unregistered_voters": false
  }
}
```

---

## Output Contract

Commands return JSON by default:

```json
{
  "data": {},
  "warnings": []
}
```

Human output is opt-in:

```bash
voting --human election list
```

Errors are structured JSON on stderr:

```json
{
  "error": {
    "code": "user_error",
    "message": "Election already exists: neighborhood_projects",
    "details": {
      "id": "neighborhood_projects"
    }
  }
}
```

Suggested error classes mirror `mcda`:

| Class | Code | Exit | Meaning |
| --- | --- | ---: | --- |
| `ProjectNotFound` | `missing_project` | 2 | No `.voting/meta.json` found. |
| `InvalidProject` | `invalid_project` | 2 | Bad project structure or invalid JSON. |
| `UserError` | `user_error` | 1 | Bad command input or duplicate IDs. |
| `ValidationError` | `validation_error` | 3 | Election, ballot, or method validation failed. |
| `AnalysisError` | `analysis_error` | 4 | Counting cannot complete. |

---

## IDs

IDs are file-safe identifiers:

```text
^[a-zA-Z_][a-zA-Z0-9_]*$
```

Examples:

```text
alice
option_a
neighborhood_projects
```

Non-examples:

```text
2026_vote
option-a
Option A
```

---

## Core Concepts

### Elections

An election defines the counting context. It can select a default method, ballot type,
number of seats, option eligibility, and tie policy.

```json
{
  "id": "neighborhood_projects",
  "name": "Neighborhood Projects",
  "description": "Choose which project receives funding.",
  "created_at": "2026-04-16T09:30:00",
  "method": "single_transferable_vote",
  "ballot_type": "ranked",
  "seats": 1,
  "status": "draft",
  "options": ["park", "library", "bike_lanes"],
  "settings": {
    "tie_policy": "lexicographic",
    "quota": "droop",
    "exhausted_ballots": "exclude_from_active_total"
  }
}
```

Statuses:

| Status | Meaning |
| --- | --- |
| `draft` | Options, voters, and settings can still change. |
| `open` | Ballots can be recorded. |
| `closed` | Ballots are locked for counting. |
| `archived` | Historical record; no mutation except reports/results. |

### Options

Options are choices that may appear on ballots. They may be candidates, proposals,
projects, parties, or reference options.

```json
{
  "id": "park",
  "name": "Pocket Park",
  "type": "candidate",
  "description": "Build a small public park.",
  "added_at": "2026-04-16T09:31:00",
  "eligible": true,
  "metadata": {}
}
```

Option types for v1:

| Type | Meaning |
| --- | --- |
| `candidate` | Eligible to win. |
| `proposal` | Eligible to win; semantic alias useful for non-person choices. |
| `reference` | May appear in comparisons but is excluded from default winner lists. |
| `write_in` | Captured from ballots when write-ins are allowed. |

### Voters

Voters are optional for simple simulations but required when `allow_unregistered_voters`
is false.

```json
{
  "id": "alice",
  "name": "Alice Rivera",
  "added_at": "2026-04-16T09:32:00",
  "weight": 1.0,
  "eligible": true,
  "traits": {
    "group": "residents"
  }
}
```

`weight` supports weighted voting and synthetic scenarios. The default is `1.0`.

### Ballots

Ballots are append-only records. A later ballot from the same voter can supersede an
earlier ballot if the election policy allows updates.

Ranked ballot:

```json
{
  "id": "20260416T133000000000Z_ab12cd34_alice_neighborhood_projects",
  "election_id": "neighborhood_projects",
  "voter_id": "alice",
  "ballot_type": "ranked",
  "recorded_at": "2026-04-16T09:33:00",
  "weight": 1.0,
  "ranking": ["park", "library", "bike_lanes"],
  "metadata": {}
}
```

Plurality ballot:

```json
{
  "id": "20260416T133100000000Z_ef56ab78_bob_neighborhood_projects",
  "election_id": "neighborhood_projects",
  "voter_id": "bob",
  "ballot_type": "single_choice",
  "recorded_at": "2026-04-16T09:34:00",
  "weight": 1.0,
  "choice": "library",
  "metadata": {}
}
```

Borda score ballot:

```json
{
  "id": "20260416T133200000000Z_gh90ab12_carol_neighborhood_projects",
  "election_id": "neighborhood_projects",
  "voter_id": "carol",
  "ballot_type": "ranked",
  "recorded_at": "2026-04-16T09:35:00",
  "weight": 1.0,
  "ranking": ["bike_lanes", "park", "library"],
  "metadata": {}
}
```

Approval ballot:

```json
{
  "id": "20260416T133300000000Z_ij34ab56_dana_neighborhood_projects",
  "election_id": "neighborhood_projects",
  "voter_id": "dana",
  "ballot_type": "approval",
  "recorded_at": "2026-04-16T09:36:00",
  "weight": 1.0,
  "approved": ["park", "bike_lanes"],
  "metadata": {}
}
```

Score ballot:

```json
{
  "id": "20260416T133400000000Z_kl78ab90_eli_neighborhood_projects",
  "election_id": "neighborhood_projects",
  "voter_id": "eli",
  "ballot_type": "score",
  "recorded_at": "2026-04-16T09:37:00",
  "weight": 1.0,
  "scores": {
    "park": 5,
    "library": 3,
    "bike_lanes": 4
  },
  "scale": {
    "min": 0,
    "max": 5
  },
  "metadata": {}
}
```

Grade ballot:

```json
{
  "id": "20260416T133500000000Z_mn12ab34_fran_neighborhood_projects",
  "election_id": "neighborhood_projects",
  "voter_id": "fran",
  "ballot_type": "grade",
  "recorded_at": "2026-04-16T09:38:00",
  "weight": 1.0,
  "grades": {
    "park": "excellent",
    "library": "good",
    "bike_lanes": "fair"
  },
  "scale": ["reject", "poor", "fair", "good", "excellent"],
  "metadata": {}
}
```

Allocated ballot:

```json
{
  "id": "20260416T133600000000Z_op56ab78_gus_neighborhood_projects",
  "election_id": "neighborhood_projects",
  "voter_id": "gus",
  "ballot_type": "allocated",
  "recorded_at": "2026-04-16T09:39:00",
  "weight": 1.0,
  "allocations": {
    "park": 3,
    "library": 0,
    "bike_lanes": 2
  },
  "budget": 5,
  "metadata": {}
}
```

Ballot types:

| Type | Supports |
| --- | --- |
| `single_choice` | FPTP, simple majority, runoff, SNTV. |
| `ranked` | Borda, IRV, STV, Condorcet methods, Bucklin. |
| `approval` | Approval, block voting, limited voting. |
| `score` | Score/range voting and STAR. |
| `grade` | Majority judgment and related highest-median rules. |
| `allocated` | Cumulative voting. |

---

## Supported Voting Methods

The tool should implement all methods below. Each method returns the same top-level result
shape, with method-specific details nested under `rounds`, `scores`, `transfers`,
`pairwise`, or `allocations`.

### First Past The Post

Alias: `fptp`.

Input ballot type: `single_choice`; ranked ballots may be treated as first-choice ballots
when `--coerce-ranked` is set.

Counting rule:

- Sum ballot weights by selected option.
- Highest total wins.
- Ties are resolved by the election tie policy.

### Simple Majority

Input ballot type: `single_choice` for exactly two eligible options, or yes/no proposal
ballots represented as options such as `yes` and `no`.

Counting rule:

- Sum ballot weights by option.
- A winner requires more than 50% of non-abstaining valid ballot weight.
- If no option exceeds 50%, return no winner unless `--fallback fptp` is requested.

### Borda Count

Input ballot type: `ranked`.

Default scoring:

- For `n` eligible options, first place receives `n - 1`, second receives `n - 2`, and
  so on.
- Unranked options receive `0` by default.
- Weighted ballots multiply awarded points by ballot weight.

Settings:

| Setting | Default | Meaning |
| --- | --- | --- |
| `unranked` | `zero` | Other supported value: `average_remaining`. |
| `score_base` | `zero_based` | Other supported value: `one_based`. |

### Instant Runoff Voting

Alias: `irv`.

Input ballot type: `ranked`.

Counting rule:

- Count first active preference on each ballot.
- If an option has more than 50% of active non-exhausted ballot weight, it wins.
- Otherwise eliminate the lowest active option.
- Transfer each eliminated option's ballots to the next ranked active option.
- Repeat until a majority winner exists or one option remains.

### Single Transferable Vote

Alias: `stv`.

Input ballot type: `ranked`.

Primary v1 target:

- Supports one or more seats.
- Uses the Droop quota by default.
- Uses fractional surplus transfers.
- Eliminates the lowest candidate when no surplus can be transferred.
- Tracks exhausted ballots and inactive candidates per round.

Default quota:

```text
floor(valid_ballot_weight / (seats + 1)) + 1
```

For one-seat elections, STV should produce behavior equivalent to IRV when the same
transfer and tie policies are used.

### Approval Voting

Input ballot type: `approval`.

Counting rule:

- Sum ballot weights once for each approved option.
- Highest total wins in a single-seat election.
- In a multi-seat election, the top `seats` options win unless a different approval
  variant is selected.

### Score Voting

Aliases: `range`, `range_voting`.

Input ballot type: `score`.

Counting rule:

- Validate each score against the election scale.
- Sum or average weighted scores by option.
- Highest score wins.

Default setting:

| Setting | Default | Meaning |
| --- | --- | --- |
| `aggregation` | `sum` | Other supported value: `mean`. |

### STAR Voting

Input ballot type: `score`.

STAR means Score Then Automatic Runoff.

Counting rule:

- Sum weighted scores by option.
- Select the top two score finalists.
- For each ballot, give one runoff vote to the finalist scored higher on that ballot.
- The finalist preferred by more ballot weight wins.
- Equal finalist scores on a ballot count as no runoff preference by default.

### Condorcet Methods

Input ballot type: `ranked`.

Condorcet methods use a pairwise preference matrix. For every pair of options, count how
much ballot weight ranks one above the other. A Condorcet winner beats every other option
head-to-head.

Supported Condorcet-family methods:

| Method | Alias | Rule |
| --- | --- | --- |
| `condorcet_copeland` | `copeland` | Score each option by pairwise wins, losses, and ties. |
| `condorcet_minimax` | `minimax` | Elect the option whose worst pairwise defeat is least severe. |
| `ranked_pairs` | `tideman` | Lock pairwise victories from strongest to weakest without creating cycles. |
| `schulze` | `beatpath` | Elect by strongest paths through the pairwise graph. |
| `kemeny_young` | `kemeny` | Find the ranking with maximum pairwise agreement. Planned for small elections due to cost. |

The first implementation should build reusable pairwise matrix machinery, then layer
Copeland and Minimax on top before adding Ranked Pairs and Schulze.

### Block Voting

Aliases: `plurality_at_large`, `bloc`.

Input ballot type: `approval`.

Counting rule:

- Voters may approve up to `seats` options.
- Sum approvals by option.
- Top `seats` options win.

### Limited Voting

Input ballot type: `approval`.

Counting rule:

- Voters may approve up to a configured limit.
- The approval limit is less than the number of seats.
- Top `seats` options win.

### Single Non-Transferable Vote

Alias: `sntv`.

Input ballot type: `single_choice`.

Counting rule:

- Each voter selects one option.
- Top `seats` options by total weight win.

### Cumulative Voting

Input ballot type: `allocated`.

Counting rule:

- Each voter has a vote budget.
- The voter may allocate votes across options, including stacking multiple votes on one
  option.
- Allocations must be non-negative and cannot exceed the budget.
- Top `seats` options by allocated total win.

### Two-Round Runoff

Aliases: `runoff`, `two_round`.

Input ballot type: `single_choice`, with optional simulation from ranked ballots.

Counting rule:

- If an option has a simple majority in round one, it wins.
- Otherwise the top two options advance to a runoff.
- With ranked ballots, simulate the runoff by each ballot's preference between finalists.
- With single-choice ballots only, return the runoff finalists and mark the result as
  requiring another ballot unless explicit runoff ballots are supplied.

### Bucklin Voting

Input ballot type: `ranked`.

Counting rule:

- Count first-choice support.
- If no option has a majority, count first and second choices together.
- Continue adding ranking depths until an option has majority support.
- Ties at the winning depth are resolved by total support at that depth, previous-depth
  support, then the election tie policy.

### Majority Judgment

Input ballot type: `grade`.

Counting rule:

- Voters grade each option on an ordered scale.
- Each option's primary score is its median grade.
- Ties are resolved by comparing grade distributions around the median.

Related highest-median methods can share the same grade ballot representation.

---

## Result Shape

All analysis commands should write a result JSON file under `.voting/results/` and return
the same data in the CLI response.

```json
{
  "id": "20260416T134000000000Z_ab12cd34_neighborhood_projects_stv",
  "election_id": "neighborhood_projects",
  "method": "single_transferable_vote",
  "created_at": "2026-04-16T09:40:00",
  "settings": {
    "seats": 1,
    "tie_policy": "lexicographic",
    "quota": "droop"
  },
  "winners": ["park"],
  "ranking": [
    {"option_id": "park", "rank": 1, "status": "elected"},
    {"option_id": "library", "rank": 2, "status": "eliminated"},
    {"option_id": "bike_lanes", "rank": 3, "status": "eliminated"}
  ],
  "summary": {
    "valid_ballots": 5,
    "invalid_ballots": 0,
    "total_valid_weight": 5.0,
    "exhausted_weight": 0.0
  },
  "rounds": [],
  "warnings": []
}
```

Method-specific expectations:

| Method | Required details |
| --- | --- |
| `fptp` | Final vote totals. |
| `simple_majority` | Vote totals, majority threshold, whether threshold was met. |
| `borda` | Per-option scores and optional per-ballot contributions. |
| `irv` | Round totals, eliminated option per round, transfer summary. |
| `stv` | Quota, round totals, elected/eliminated options, surplus transfers, exhausted weight. |
| `approval` | Approval totals and approval rate per option. |
| `score` | Score totals, score averages, and score scale. |
| `star` | Score totals, finalists, runoff preferences, and runoff winner. |
| `condorcet_*` | Pairwise matrix, Condorcet winner if any, method-specific ranking. |
| `block_voting` | Approval totals, seat count, and elected set. |
| `limited_voting` | Approval totals, approval limit, seat count, and elected set. |
| `sntv` | Final vote totals and elected set. |
| `cumulative` | Allocation totals, budget validation summary, and elected set. |
| `runoff` | First-round totals, finalists, runoff totals or required next step. |
| `bucklin` | Per-depth support totals and winning depth. |
| `majority_judgment` | Median grades and tie-resolution distribution. |

---

## CLI Commands

### Project

```bash
voting init <name> [--description TEXT]
voting info
```

### Elections

```bash
voting election add <election_id> <name> \
  [--method METHOD] \
  [--ballot-type TYPE] \
  [--seats N] \
  [--tie-policy POLICY] \
  [--description TEXT]

voting election list
voting election show <election_id>
voting election open <election_id>
voting election close <election_id>
voting election set-method <election_id> <method>
voting election add-option <election_id> <option_id>
voting election remove-option <election_id> <option_id>
```

### Options

```bash
voting option add <option_id> <name> [--type candidate] [--description TEXT]
voting option list [--type all]
voting option show <option_id>
voting option set-eligible <option_id> <true|false>
```

### Voters

```bash
voting voter add <voter_id> <name> [--weight FLOAT]
voting voter list
voting voter show <voter_id>
voting voter set-trait <voter_id> <key> <json_value>
voting voter set-eligible <voter_id> <true|false>
```

### Ballots

```bash
voting ballot cast <election_id> <voter_id> --choice <option_id>
voting ballot rank <election_id> <voter_id> <option_id>...
voting ballot approve <election_id> <voter_id> --option <option_id> [--option <option_id> ...]
voting ballot score <election_id> <voter_id> <option_id>=<score>...
voting ballot grade <election_id> <voter_id> <option_id>=<grade>...
voting ballot allocate <election_id> <voter_id> <option_id>=<votes>...
voting ballot list [--election <election_id>] [--voter <voter_id>]
voting ballot show <ballot_record_id>
voting ballot validate <election_id>
```

`ballot cast` creates `single_choice` ballots.

`ballot rank` creates `ranked` ballots.

`ballot approve` creates `approval` ballots.

`ballot score` creates `score` ballots.

`ballot grade` creates `grade` ballots.

`ballot allocate` creates `allocated` ballots.

### Analysis

```bash
voting count run <election_id> [--method METHOD] [--seats N] [--tie-policy POLICY]
voting count show <result_id>
voting count list [--election <election_id>]
```

Methods accepted by `count run`:

```text
fptp
simple_majority
borda
irv
stv
first_past_the_post
single_transferable_vote
approval
score
range
star
condorcet_copeland
copeland
condorcet_minimax
minimax
ranked_pairs
tideman
schulze
beatpath
kemeny_young
kemeny
block_voting
plurality_at_large
limited_voting
sntv
cumulative
runoff
two_round
bucklin
majority_judgment
```

---

## Policy Decisions

### Ballot Updates

Default: one active ballot per voter per election. If a voter casts again, the latest
ballot supersedes previous ballots. Prior ballot records remain in `ballots/`.

The effective ballot set is computed by taking the latest valid ballot for each
`(election_id, voter_id)` pair.

### Invalid Ballots

Invalid ballots are excluded from counting and listed in result warnings/details.

Examples:

- Unknown voter when registration is required.
- Ineligible voter.
- Unknown option.
- Option not included in the election.
- Duplicate ranked option.
- Empty ranking.
- Single-choice ballot with no choice.
- Score outside the election score scale.
- Unknown grade outside the election grade scale.
- Approval count above a block or limited voting cap.
- Allocated votes above the election budget.

### Abstentions

V1 should represent abstention as no ballot. Explicit abstention records can be added
later if needed.

### Ties

Tie policies:

| Policy | Meaning |
| --- | --- |
| `lexicographic` | Sort tied option IDs alphabetically. Deterministic and easy to test. |
| `random_seeded` | Use a provided seed for reproducible random tie-breaking. |
| `manual` | Fail with a tie detail requiring explicit resolution. |

V1 default: `lexicographic`.

### Numeric Precision

Use Python `float` for v1 and round display output to a consistent precision in result
JSON, likely 6 decimal places. If fractional STV transfers become precision-sensitive,
switch counting internals to `decimal.Decimal`.

---

## Internal Module Structure

Mirror the MCDA project shape.

```text
voting/
  __init__.py
  cli.py
  commands/
    __init__.py
    common.py
    init.py
    info.py
    election.py
    option.py
    voter.py
    ballot.py
    count.py
  core/
    __init__.py
    errors.py
    ids.py
    project.py
    store.py
    validate.py
    ballots.py
    methods/
      __init__.py
      fptp.py
      majority.py
      borda.py
      irv.py
      stv.py
      approval.py
      score.py
      star.py
      pairwise.py
      condorcet.py
      block.py
      cumulative.py
      runoff.py
      bucklin.py
      majority_judgment.py
tests/
  test_vertical_slice.py
```

Suggested core responsibilities:

| Module | Responsibility |
| --- | --- |
| `core.project` | `.voting` discovery and project creation. |
| `core.store` | JSON read/write, entity paths, record append/list helpers. |
| `core.ids` | ID validation, timestamps, record IDs. |
| `core.validate` | Election and ballot validation. |
| `core.ballots` | Effective ballot resolution and ballot normalization. |
| `core.methods.*` | Pure counting functions without CLI dependencies. |
| `commands.*` | Typer command wrappers and output formatting. |

---

## Vertical Slice Scenario

This scenario should become the first test fixture.

### Context

Residents choose one neighborhood funding project.

Project:

```text
neighborhood_vote
```

Election:

```text
neighborhood_projects
```

Options:

| ID | Name |
| --- | --- |
| `park` | Pocket Park |
| `library` | Library Hours |
| `bike_lanes` | Bike Lanes |

Voters:

| ID | Name |
| --- | --- |
| `alice` | Alice Rivera |
| `bob` | Bob Chen |
| `carol` | Carol Singh |
| `dana` | Dana Patel |
| `eli` | Eli Morgan |

Ranked ballots:

| Voter | Ranking |
| --- | --- |
| `alice` | `park`, `library`, `bike_lanes` |
| `bob` | `library`, `park`, `bike_lanes` |
| `carol` | `bike_lanes`, `park`, `library` |
| `dana` | `park`, `bike_lanes`, `library` |
| `eli` | `library`, `bike_lanes`, `park` |

Expected first-choice totals:

| Option | Votes |
| --- | ---: |
| `park` | 2 |
| `library` | 2 |
| `bike_lanes` | 1 |

Expected FPTP winner with lexicographic tie policy:

```text
library
```

Expected IRV/STV one-seat behavior:

1. Round 1: `bike_lanes` is eliminated with 1 vote.
2. Carol's ballot transfers to `park`.
3. Round 2: `park` has 3 votes and wins.

Expected Borda scores with zero-based scoring over three options:

| Option | Score |
| --- | ---: |
| `park` | 6 |
| `library` | 5 |
| `bike_lanes` | 4 |

### Target Command Script

```bash
voting init neighborhood_vote --description "Choose one neighborhood funding project."
cd neighborhood_vote

voting option add park "Pocket Park"
voting option add library "Library Hours"
voting option add bike_lanes "Bike Lanes"

voting voter add alice "Alice Rivera"
voting voter add bob "Bob Chen"
voting voter add carol "Carol Singh"
voting voter add dana "Dana Patel"
voting voter add eli "Eli Morgan"

voting election add neighborhood_projects "Neighborhood Projects" \
  --method stv \
  --ballot-type ranked \
  --seats 1

voting election add-option neighborhood_projects park
voting election add-option neighborhood_projects library
voting election add-option neighborhood_projects bike_lanes
voting election open neighborhood_projects

voting ballot rank neighborhood_projects alice park library bike_lanes
voting ballot rank neighborhood_projects bob library park bike_lanes
voting ballot rank neighborhood_projects carol bike_lanes park library
voting ballot rank neighborhood_projects dana park bike_lanes library
voting ballot rank neighborhood_projects eli library bike_lanes park

voting election close neighborhood_projects

voting count run neighborhood_projects --method fptp
voting count run neighborhood_projects --method borda
voting count run neighborhood_projects --method irv
voting count run neighborhood_projects --method stv
```

---

## Test Scenarios

These scenarios are intended to become fixtures under `tests/fixtures/` and runnable demo
scripts under `examples/`. They should be small enough to verify by hand while still
exercising the important behavior of each method family.

### Referendum Majority

Purpose: simple majority, FPTP with two options, and majority threshold reporting.

Election:

```text
community_pool_referendum
```

Options:

| ID | Name |
| --- | --- |
| `yes` | Build Pool |
| `no` | Do Not Build Pool |

Single-choice ballots:

| Choice | Count |
| --- | ---: |
| `yes` | 3 |
| `no` | 2 |

Expected:

| Method | Winner | Notes |
| --- | --- | --- |
| `simple_majority` | `yes` | `yes` has 3 of 5 valid votes, meeting the `> 50%` threshold. |
| `fptp` | `yes` | Same winner, but without the majority-threshold requirement. |

### Ranked Neighborhood Project

Purpose: first vertical slice for FPTP, Borda, IRV, and one-seat STV.

Use the vertical slice scenario above.

Expected:

| Method | Winner | Notes |
| --- | --- | --- |
| `fptp` | `library` | `park` and `library` tie on first choices; lexicographic tie policy selects `library`. |
| `borda` | `park` | Scores: `park=6`, `library=5`, `bike_lanes=4`. |
| `irv` | `park` | `bike_lanes` is eliminated and transfers Carol's ballot to `park`. |
| `stv` | `park` | One-seat STV should match IRV behavior. |

### Approval Committee

Purpose: approval voting and block voting.

Election:

```text
festival_committee
```

Seats:

```text
2
```

Options:

```text
music, food, art, sports
```

Approval ballots:

| Voter | Approved |
| --- | --- |
| `alice` | `music`, `food` |
| `bob` | `music`, `art` |
| `carol` | `food`, `art` |
| `dana` | `music`, `sports` |
| `eli` | `art`, `sports` |

Expected totals:

| Option | Approvals |
| --- | ---: |
| `music` | 3 |
| `art` | 3 |
| `food` | 2 |
| `sports` | 2 |

Expected:

| Method | Winners | Notes |
| --- | --- | --- |
| `approval` | `music`, `art` | Top two approval totals. |
| `block_voting` | `music`, `art` | Each voter approved at most `seats` options. |

### Limited Voting And SNTV

Purpose: limited voting cap validation and single non-transferable vote.

Election:

```text
park_board
```

Seats:

```text
2
```

Options:

```text
ada, ben, cy, dia
```

Single-choice or one-approval ballots:

| Voter | Choice |
| --- | --- |
| `alice` | `ada` |
| `bob` | `ada` |
| `carol` | `ben` |
| `dana` | `cy` |
| `eli` | `dia` |

Expected totals:

| Option | Votes |
| --- | ---: |
| `ada` | 2 |
| `ben` | 1 |
| `cy` | 1 |
| `dia` | 1 |

Expected:

| Method | Winners | Notes |
| --- | --- | --- |
| `limited_voting` | `ada`, `ben` | One approval per voter; tie for second resolved lexicographically. |
| `sntv` | `ada`, `ben` | Same totals using single-choice ballots. |

### Score And STAR

Purpose: demonstrate that score winner and STAR winner can differ.

Election:

```text
software_vendor
```

Score scale:

```text
0..5
```

Options:

```text
alpha, beta, gamma
```

Score ballots:

| Voter | `alpha` | `beta` | `gamma` |
| --- | ---: | ---: | ---: |
| `alice` | 5 | 4 | 0 |
| `bob` | 5 | 3 | 0 |
| `carol` | 0 | 5 | 4 |
| `dana` | 0 | 5 | 3 |
| `eli` | 3 | 2 | 5 |

Expected score totals:

| Option | Score |
| --- | ---: |
| `alpha` | 13 |
| `beta` | 19 |
| `gamma` | 12 |

Expected:

| Method | Winner | Notes |
| --- | --- | --- |
| `score` | `beta` | Highest summed score. |
| `star` | `alpha` | Finalists are `beta` and `alpha`; `alpha` wins the runoff 3 to 2. |

### Condorcet Winner

Purpose: pairwise matrix, Condorcet winner detection, Copeland, and Minimax.

Election:

```text
policy_package
```

Options:

```text
alpha, beta, gamma
```

Ranked ballot groups:

| Count | Ranking |
| ---: | --- |
| 3 | `alpha`, `beta`, `gamma` |
| 2 | `beta`, `gamma`, `alpha` |
| 2 | `gamma`, `beta`, `alpha` |

Expected pairwise results:

| Pair | Winner | Margin |
| --- | --- | ---: |
| `beta` vs `alpha` | `beta` | 4 to 3 |
| `beta` vs `gamma` | `beta` | 5 to 2 |
| `gamma` vs `alpha` | `gamma` | 4 to 3 |

Expected:

| Method | Winner | Notes |
| --- | --- | --- |
| `condorcet_copeland` | `beta` | `beta` wins both pairwise contests. |
| `condorcet_minimax` | `beta` | `beta` has no pairwise defeat. |

### Condorcet Cycle

Purpose: Ranked Pairs and Schulze behavior when there is no Condorcet winner.

Election:

```text
platform_cycle
```

Options:

```text
alpha, beta, gamma
```

Ranked ballot groups:

| Count | Ranking |
| ---: | --- |
| 3 | `alpha`, `beta`, `gamma` |
| 2 | `beta`, `gamma`, `alpha` |
| 2 | `gamma`, `alpha`, `beta` |

Expected pairwise cycle:

| Pair | Winner | Margin |
| --- | --- | ---: |
| `alpha` vs `beta` | `alpha` | 5 to 2 |
| `beta` vs `gamma` | `beta` | 5 to 2 |
| `gamma` vs `alpha` | `gamma` | 4 to 3 |

Expected:

| Method | Winner | Notes |
| --- | --- | --- |
| `ranked_pairs` | `alpha` | Lock `alpha > beta`, lock `beta > gamma`, skip `gamma > alpha`. |
| `schulze` | `alpha` | Strongest paths select `alpha`. |

### Multi-Seat STV

Purpose: Droop quota, elected candidates, elimination, and transfers in a two-seat race.

Election:

```text
council_stv
```

Seats:

```text
2
```

Options:

```text
ada, ben, cy, dia
```

Ranked ballot groups:

| Count | Ranking |
| ---: | --- |
| 3 | `ada`, `ben`, `cy`, `dia` |
| 2 | `ben`, `ada`, `cy`, `dia` |
| 1 | `cy`, `ben`, `ada`, `dia` |
| 1 | `dia`, `cy`, `ben`, `ada` |

Expected:

| Item | Value |
| --- | --- |
| Droop quota | 3 |
| Round 1 elected | `ada` |
| Next elimination | `cy`, by lexicographic tie policy among `cy` and `dia` |
| Transfer effect | `cy` transfers to `ben`, bringing `ben` to quota |
| Winners | `ada`, `ben` |

### Cumulative Budget

Purpose: allocated ballots, vote budgets, and multi-seat cumulative winners.

Election:

```text
capital_budget
```

Seats:

```text
2
```

Vote budget:

```text
5
```

Options:

```text
lighting, trees, sidewalks, murals
```

Allocated ballots:

| Voter | Allocations |
| --- | --- |
| `alice` | `lighting=5` |
| `bob` | `lighting=3`, `trees=2` |
| `carol` | `trees=5` |
| `dana` | `sidewalks=5` |
| `eli` | `sidewalks=3`, `murals=2` |

Expected totals:

| Option | Votes |
| --- | ---: |
| `lighting` | 8 |
| `trees` | 7 |
| `sidewalks` | 8 |
| `murals` | 2 |

Expected:

| Method | Winners | Notes |
| --- | --- | --- |
| `cumulative` | `lighting`, `sidewalks` | Top two allocation totals. |

### Majority Judgment

Purpose: grade ballots, median grade, and grade-distribution tie logic.

Election:

```text
site_selection_grade
```

Grade scale:

```text
reject, poor, fair, good, excellent
```

Options:

```text
park, library, transit
```

Grade ballots:

| Voter | `park` | `library` | `transit` |
| --- | --- | --- | --- |
| `alice` | excellent | good | excellent |
| `bob` | good | good | fair |
| `carol` | good | fair | fair |
| `dana` | fair | fair | poor |
| `eli` | fair | poor | reject |

Expected medians:

| Option | Median |
| --- | --- |
| `park` | good |
| `library` | fair |
| `transit` | fair |

Expected:

| Method | Winner | Notes |
| --- | --- | --- |
| `majority_judgment` | `park` | Highest median grade. |

### Bucklin And Runoff

Purpose: Bucklin depth counting and two-round runoff simulation from ranked ballots.

Election:

```text
club_president
```

Options:

```text
ada, ben, cy
```

Ranked ballots:

| Voter | Ranking |
| --- | --- |
| `alice` | `ada`, `ben`, `cy` |
| `bob` | `ben`, `ada`, `cy` |
| `carol` | `cy`, `ben`, `ada` |
| `dana` | `ben`, `cy`, `ada` |
| `eli` | `cy`, `ada`, `ben` |

Expected first-choice totals:

| Option | Votes |
| --- | ---: |
| `ada` | 1 |
| `ben` | 2 |
| `cy` | 2 |

Expected Bucklin depth-2 totals:

| Option | Votes |
| --- | ---: |
| `ada` | 3 |
| `ben` | 4 |
| `cy` | 3 |

Expected:

| Method | Winner | Notes |
| --- | --- | --- |
| `bucklin` | `ben` | First candidate over majority at depth 2 with the highest depth total. |
| `runoff` | `ben` | Finalists are `ben` and `cy`; `ben` wins the simulated runoff 3 to 2. |

---

## Implementation Order

1. Project skeleton, `pyproject.toml`, CLI shell, structured output/errors.
2. `.voting` project creation and discovery.
3. Option, voter, and election CRUD commands.
4. Ballot recording and validation.
5. FPTP and simple-majority counting.
6. Borda counting.
7. IRV counting.
8. STV one-seat equivalence with IRV, then multi-seat support.
9. Vertical-slice test and README for FPTP, Borda, IRV, and STV.
10. Approval voting, block voting, limited voting, and SNTV.
11. Score/range voting and STAR voting.
12. Pairwise matrix support, then Copeland and Minimax.
13. Ranked Pairs and Schulze.
14. Majority judgment and grade ballots.
15. Cumulative voting and allocated ballots.
16. Bucklin and two-round runoff.
17. Scenario fixtures and examples for every method family above.

The first useful milestone is the vertical slice passing for the ranked neighborhood
project scenario. The full target is all scenarios passing with JSON result snapshots for
every supported method.
