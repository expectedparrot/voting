# Overview

The `voting` package is a JSON-first CLI for building voting scenarios, recording ballots, and comparing multiple election methods against the same underlying data.

## What It Does

- Create local voting projects with a `.voting/` hidden directory
- Register options (candidates, proposals, etc.) and voters
- Cast ballots in six formats: single choice, ranked, approval, score, grade, allocated
- Run any of 28 counting methods against the same set of ballots
- Compare how outcomes change across methods — the core value of the tool

## When to Use It

Use `voting` when you want to answer: *"How would this group decide under different voting rules?"*

Good use cases:
- Comparing IRV vs. Condorcet methods on the same panel preferences
- Eliciting AI agent preferences via EDSL and running multi-method analysis
- Publishing Humanize web ballots for real voters, with optional email invitations
- Exploring how ballot type affects outcomes for different group compositions
- Building voting scenarios for research, education, or design

## Three Paths to Preferences

**Direct ballot casting** — you already have preferences or are generating them programmatically:
```
voting ballot rank <election_id> <voter_id> opt_a opt_b opt_c
```

**Survey generation** — use EDSL AI agents to elicit preferences:
```
voting survey generate <election_id>   # generates a runnable Python script
voting --human survey show <election_id>
python .voting/output/survey_<id>.py  # runs EDSL survey, saves results
voting ballot import --election <id> --from .voting/output/results_<id>.json
```

**Humanize web survey** — collect preferences from real people at a hosted URL:
```
voting survey humanize <election_id>
voting survey publish <election_id>    # returns respondent_url and admin_url
voting survey responses <election_id>  # downloads an EDSL Results package
```

For unique email invitations, add an email trait to every voter, generate with
`--email-trait email`, publish, and run `voting survey email <election_id>`.

The synthetic script and Humanize paths require EDSL. Install the supported
optional integration with `pip install -e '.[humanize]'`. Humanize jobs contain
no language model; they are answered by people.

## Key Design Principles

- **JSON default, `--human` opt-in.** All output is machine-readable by default. Pass `--human` or set `VOTING_HUMAN_OUTPUT=true` for readable output.
- **Append-only ballots.** Ballots are never overwritten; if a voter casts again, the latest ballot supersedes earlier ones for counting. History is preserved.
- **Phase-aware.** Run `voting status` at any time to see what phase the project is in and what to do next.
- **Method-agnostic storage.** Ballots are stored once; any method can be applied after the fact.

## Next Steps

- `voting docs show getting-started` — step-by-step first workflow
- `voting docs show workflow` — phase reference
- `voting docs show voting-methods` — choose the right counting method
