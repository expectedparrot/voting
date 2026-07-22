# Workflow & Phases

The `voting` workflow has six phases inferred from what exists on disk — no metadata to drift.

## Phases

| Phase | Condition | Key command |
|-------|-----------|-------------|
| `init` | No `.voting/` project | `voting init <name>` |
| `setup` | Project exists, no options or voters | `voting option add`, `voting voter add` |
| `elections` | Options+voters ready, no open election | `voting election add` + `voting election open` |
| `balloting` | Open election exists, no ballots | Direct ballot or `voting survey generate` |
| `counting` | Ballots recorded, no results | `voting count run <election_id>` |
| `done` | Results exist | `voting count list` / `voting count show` |

Check current phase at any time:
```bash
voting status
```

## Phase: setup

Register all options and voters before creating elections. Voter traits power EDSL survey generation later.

```bash
voting option add <id> <name> [--type candidate|proposal|reference|write_in]
voting voter add <id> <name> [--weight 1.0]
voting voter set-trait <id> persona '"Description of this voter as an AI agent persona"'
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

### Survey-generated ballots (EDSL path)

Use when you want AI agents to elicit preferences. Voter traits become agent personas.

```bash
# Step 1: generate a runnable Python script
voting survey generate <election_id> [--model claude-opus-4-6]

# Step 2: inspect and optionally edit the script
cat .voting/output/survey_<election_id>.py

# Step 3: run it (requires edsl installed in your environment)
python .voting/output/survey_<election_id>.py

# Step 4: import results as ballots
voting ballot import --election <election_id> \
    --from .voting/output/results_<election_id>.json
```

The generated script bakes in your project's options and voters. Voters with `persona` traits produce richer agent responses.

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
