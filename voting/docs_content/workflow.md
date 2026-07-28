# Workflow & Phases

The `voting` workflow has six phases inferred from what exists on disk — no metadata to drift.

## Phases

| Phase | Condition | Key command |
|-------|-----------|-------------|
| `init` | No `.voting/` project | `voting init <name>` |
| `setup` | Project exists, no options or voters | `voting option add`, `voting voter add` |
| `elections` | Options+voters ready, no open election | `voting election add` + `voting election open` |
| `balloting` | Open election exists, no ballots | Direct ballot, synthetic survey, or Humanize survey |
| `counting` | Ballots recorded, no results | `voting count run <election_id>` |
| `done` | Results exist | `voting count list` / `voting count show` |

Check current phase at any time:
```bash
voting status
```

## Phase: setup

Register all options and voters before creating elections. The `persona` trait
powers synthetic EDSL agents; an email trait enables Humanize invitations.

```bash
voting option add <id> <name> [--type candidate|proposal|reference|write_in]
voting voter add <id> <name> [--weight 1.0]
voting voter set-trait <id> persona '"Description of this voter as an AI agent persona"'
voting voter set-trait <id> email '"person@example.com"'
```

## Phase: elections

Create one or more elections, each with a method and ballot type. The method can be changed before counting — it does not need to match the ballot type strictly (many methods handle cross-type ballots gracefully). Add all options to each election, then open it.

```bash
voting election add <id> <name> --method fptp --ballot-type single_choice
voting election add-option <election_id> <option_id>  # repeat per option
voting election open <election_id>
```

For multi-method comparison, create multiple elections with different methods but the same options:
```bash
voting election add e_irv    "Race (IRV)"    --method irv    --ballot-type ranked
voting election add e_borda  "Race (Borda)"  --method borda  --ballot-type ranked
voting election add e_condorcet "Race (Schulze)" --method schulze --ballot-type ranked
```

## Phase: balloting

Two paths:

### Direct ballot casting

Use when you already have preferences or are generating them programmatically.

```bash
voting ballot rank    <election_id> <voter_id> opt1 opt2 opt3
voting ballot cast    <election_id> <voter_id> --choice opt_id
voting ballot approve <election_id> <voter_id> --option opt1 --option opt2
voting ballot score   <election_id> <voter_id> opt1=8 opt2=5 opt3=9
```

### Synthetic survey-generated ballots (EDSL path)

Use when you want AI agents to elicit preferences. Voter traits become agent personas.

```bash
# Step 1: build an EDSL Jobs package (survey + voter agents + model; no execution)
voting survey generate <election_id> [--model gpt-5.5 --service openai]

# Step 2: inspect the job
voting --human survey show <election_id>

# Step 3: execute it externally (requires edsl and credentials)
ep run --jobs .voting/output/survey_<election_id>.jobs.ep \
    --output .voting/output/survey_<election_id>.results.ep

# Step 4: import results as ballots
voting ballot import --election <election_id> \
    --from-results .voting/output/survey_<election_id>.results.ep
```

The Jobs package bakes in your project's options and voters. Voters with `persona` traits produce richer agent responses.

### Hosted ballots for real people (Humanize path)

Generate a model-free EDSL Jobs package, then publish it through the `ep` CLI:

```bash
pip install -e '.[humanize]'
voting survey humanize <election_id>
voting survey publish <election_id>
```

`publish` saves the Humanize UUID and URLs under `.voting/output/` and returns
the respondent and admin URLs. Retrieve responses later with:

```bash
voting survey responses <election_id>
```

For email delivery, every voter must have the selected trait:

```bash
voting voter set-trait <voter_id> email '"person@example.com"'
voting survey humanize <election_id> --email-trait email
voting survey publish <election_id>
voting survey email <election_id> --name "Voting invitation"
```

The Humanize job contains no model. Without `--email-trait`, share the returned
respondent URL directly. With it, Humanize creates tracked respondents and sends
unique links through Expected Parrot's delivery system.

Validate before counting:
```bash
voting ballot validate <election_id>
```

## Phase: counting

Run any method at any time. Results are saved as records; running again with a different method does not overwrite previous results.

```bash
voting count run <election_id>
voting count run <election_id> --method borda
voting count run <election_id> --method schulze
```

## Phase: done

Results exist. Review and compare:

```bash
voting count list
voting count list --election <election_id>
voting count show <result_id>
```

You can always run more methods — the `done` phase is not terminal.

## Next Steps

- `voting docs show voting-methods` — which method to use when
- `voting docs show ballot-types` — ballot format reference
