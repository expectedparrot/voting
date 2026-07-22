# Getting Started

Step-by-step guide from project creation through your first count.

## 1. Create a Project

```bash
voting init my_election
cd my_election
```

This creates `my_election/.voting/` with subdirectories for elections, options, voters, ballots, and results.

## 2. Register Options

Options are the candidates, proposals, or choices voters will choose from.

```bash
voting option add alice "Alice Nguyen" --type candidate
voting option add bob   "Bob Okafor"   --type candidate
voting option add carol "Carol Reyes"  --type candidate
```

Option IDs must be lowercase alphanumeric with underscores. Types: `candidate`, `proposal`, `reference`, `write_in`.

## 3. Register Voters

```bash
voting voter add voter_1 "Voter One"
voting voter add voter_2 "Voter Two"
voting voter add voter_3 "Voter Three"
```

Voters can have traits (used by EDSL survey generation):
```bash
voting voter set-trait voter_1 persona '"Progressive urban planner who prioritizes transit"'
```

## 4. Create and Open an Election

```bash
voting election add city_council "City Council Race" \
    --method irv \
    --ballot-type ranked

voting election add-option city_council alice
voting election add-option city_council bob
voting election add-option city_council carol

voting election open city_council
```

## 5. Cast Ballots (Direct Path)

```bash
voting ballot rank city_council voter_1 bob alice carol
voting ballot rank city_council voter_2 alice carol bob
voting ballot rank city_council voter_3 carol bob alice
```

## 5. Cast Ballots (Survey Path)

If you want EDSL AI agents to supply preferences instead:

```bash
voting survey generate city_council
# Inspect the generated script:
voting --human survey show city_council

# Run it (requires edsl to be installed):
python .voting/output/survey_city_council.py

# Import the results as ballots:
voting ballot import --election city_council \
    --from .voting/output/results_city_council.json
```

## 5. Collect Ballots from Humans (Hosted Path)

Generate a model-free EDSL Jobs package and publish it as a Humanize web survey:

```bash
pip install -e '.[humanize]'
voting survey humanize city_council
voting survey publish city_council
```

The publish output contains a `respondent_url` to share and an `admin_url` for
monitoring. Download submitted responses as an EDSL Results package with:

```bash
voting survey responses city_council
```

To email unique links, first give every registered voter an email trait:

```bash
voting voter set-trait voter_1 email '"voter1@example.com"'
# Repeat for every registered voter.
voting survey humanize city_council --email-trait email
voting survey publish city_council
voting survey email city_council --name "City council ballot"
```

## 6. Count the Results

```bash
voting count run city_council
```

Compare additional methods:
```bash
voting count run city_council --method borda
voting count run city_council --method condorcet_copeland
```

## 7. Review Results

```bash
voting count list
voting count show <result_id>
```

Use `--human` for readable output (it's a top-level flag, place it before the subcommand):
```bash
voting --human count run city_council
```

## Next Steps

- `voting docs show voting-methods` — choose the right method for your scenario
- `voting docs show ballot-types` — understand ballot format differences
- `voting docs show workflow` — full phase reference
