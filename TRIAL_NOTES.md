# Trial Run Notes — NYU IOMS Rename Scenario

Observed during: 2026-04-21
Session: 12-voter ranked ballot, 6 options, 6 counting methods via EDSL survey path.

---

## Bugs in generated survey scripts

### 1. `name` included as a trait key (AgentNameError)

The `build_agents()` function in the generated script passes `"name": v["name"]` inside the
`traits` dict, but EDSL's `Agent` class reserves `name` as a top-level attribute and raises
`AgentNameError` if it appears as a trait key.

**Fix:** Remove `"name"` from the traits dict in the generator. The voter's display name is
already available via the `Agent(name=v["id"], ...)` argument; it doesn't need to be repeated
as a trait.

```python
# Wrong (generated):
Agent(name=v["id"], traits={"name": v["name"], **v.get("traits", {})})

# Correct:
Agent(name=v["id"], traits=v.get("traits", {}))
```

---

### 2. `options` vs `question_options` in `QuestionRank` (QuestionInitializationError)

The generated script calls `QuestionRank(..., options=option_names)` but the correct EDSL
parameter name is `question_options`.

**Fix:** Change the generator template to emit `question_options=` for `QuestionRank`.

```python
# Wrong (generated):
QuestionRank(..., options=option_names)

# Correct:
QuestionRank(..., question_options=option_names)
```

---

### 3. `QuestionRank` returns integer indices, not option name strings

The generated script builds `OPTION_MAP = {o["name"]: o["id"] for o in OPTIONS}` and then
does `OPTION_MAP.get(name, name)` for each element in the returned ranking. But EDSL's
`QuestionRank` returns a list of **integer indices** (positions in `question_options`), not
the option name strings. The mapping lookup always fails, leaving every ballot with a list
of bare integers that the importer rejects as invalid option IDs.

**Fix:** The generator must use index-based lookup instead of name-based lookup:

```python
# Wrong (generated):
ranked_names = item.get("ranking") or []
ranked_ids = [OPTION_MAP.get(name, name) for name in ranked_names]

# Correct:
ranked_indices = item.get("ranking") or []
ranked_ids = [option_ids[i] for i in ranked_indices]
# where option_ids = [o["id"] for o in OPTIONS]
```

Alternatively, inspect the EDSL result schema more carefully — if a future version returns
names instead of indices, the generator should detect and handle both forms.

---

## Documentation / CLI inconsistencies

### 4. `--human` flag documented but not available on `voting count run`

The `agent-start` brief says:

> Use `--human` for readable output (not parseable by scripts).

And the getting-started guide shows:

```bash
voting count run city_council --human
```

But `voting count run` does not accept `--human` — it errors with "No such option". Either
add the flag to `count run`, or remove it from all examples that reference this subcommand.
The flag may work on other subcommands; if so, document which ones support it.

---

## Workflow / UX observations

### 5. FPTP tiebreak is silent and surprising

In this trial, `ioms` and `tech_mgmt` both had 3 first-place votes. FPTP declared `ioms` the
winner via lexicographic tiebreak without any warning in the output. A user reading just the
winner field would not know a tie occurred. The `summary` or `warnings` field should flag
ties and explain which tiebreak rule was applied.

### 6. `ballot import` does not overwrite — duplicate ballots accumulate silently

When I re-ran `ballot import` after fixing the results JSON, the command reported `cast: 12,
skipped: 0` but did not warn that the same voter IDs had already cast ballots. Depending on
implementation, this could mean ballots were doubled. Worth verifying that re-import either
(a) replaces existing ballots for the same voter+election pair, or (b) rejects duplicates
with a clear warning. Silent accumulation would corrupt counts.

### 7. The survey path should note the index-return behavior in generated script comments

Even after fixing the generator, it would be helpful to add a comment in the generated
script explaining that `QuestionRank` returns indices and showing how the conversion works.
This makes the script inspectable and correctable by users before running it.

---

## What worked well

- The overall workflow (init → options → voters → election → survey → import → count) is
  clean and easy to follow.
- Voter traits/personas are correctly passed to EDSL agents and produce differentiated,
  realistic preferences — the OR faculty ranked `ioms` first, the junior analytics faculty
  ranked change-names first, exactly as expected.
- Multi-method comparison is seamless: running 6 methods on the same ballots is a one-liner
  loop and the results accumulate without overwriting each other.
- The pairwise tables from Schulze/Copeland/ranked_pairs are rich and analytically useful.
