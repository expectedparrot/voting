# Troubleshooting

Common errors, warning codes, and recovery steps.

## Error Codes

### missing_project
**Message:** No voting project found.
**Cause:** Running a command outside a project directory, or `.voting/meta.json` is missing.
**Fix:** `cd` into the project directory, or run `voting init <name>` to create one.

### invalid_project
**Message:** Missing .voting/meta.json or invalid JSON.
**Cause:** Corrupted project directory or manually edited JSON.
**Fix:** Check that `.voting/meta.json` exists and is valid JSON.

### user_error (NOT_FOUND)
**Message:** File not found: `.voting/<collection>/<id>.json`
**Cause:** Referencing an option, voter, or election that does not exist.
**Fix:** Run `voting option list`, `voting voter list`, or `voting election list` to see valid IDs.

### user_error (ALREADY_EXISTS)
**Message:** Option/Voter/Election already exists: `<id>`
**Cause:** Trying to add an entity with an ID that already exists.
**Fix:** Use a different ID, or use `voting option show <id>` to inspect the existing one.

### user_error (ELECTION_NOT_OPEN)
**Message:** Election is not open for ballots.
**Cause:** Casting ballots on a draft or closed election.
**Fix:** Run `voting election open <election_id>` first.

### user_error (UNKNOWN_METHOD)
**Message:** Unknown voting method.
**Fix:** Run `voting docs show voting-methods` to see all supported method names.

### user_error (NO_OPTIONS)
**Message:** Election has no eligible options.
**Fix:** Run `voting election add-option <election_id> <option_id>` for each option.

## Ballot Warning Codes

Ballot warnings appear in `voting ballot validate` and `voting count run` output. They do not block counting — invalid ballots are skipped.

| Code | Meaning | Fix |
|------|---------|-----|
| `unknown_voter` | Ballot voter_id not in voter registry | Add with `voting voter add` or set `allow_unregistered_voters: true` in meta.json |
| `ineligible_voter` | Voter marked as ineligible | `voting voter set-eligible <id> true` |
| `unknown_option` | Ballot references option not in election | `voting election add-option <election_id> <option_id>` |
| `duplicate_ranked_option` | Same option appears twice in a ranking | Re-cast the ballot with unique option IDs |
| `allocation_over_budget` | Allocated votes exceed configured budget | Check election settings.budget and re-cast |

## Survey Generation Issues

### Generated script fails with `ModuleNotFoundError: edsl`
**Fix:** Install EDSL in your environment: `pip install edsl`

### `voting ballot import` fails with "Results file is for election X, not Y"
**Cause:** The `--election` flag doesn't match the `election_id` baked into the results file.
**Fix:** Use the election ID shown in the error, or regenerate the survey script.

### Import succeeds but ballots show `unknown_voter` warnings
**Cause:** The EDSL agent names (voter IDs in the generated script) don't match registered voter IDs.
**Fix:** Voter IDs in `voting voter add` should match what you used in the generated script. The generated script uses voter IDs from the registry, so this should not happen unless voters were added after the script was generated. Regenerate with `voting survey generate`.

## ID Format Errors

Voter, option, and election IDs must be lowercase alphanumeric with underscores, not starting with a digit.

Valid: `alice`, `voter_1`, `city_council_2026`
Invalid: `Alice`, `voter-1`, `1st_choice`

## JSON Parsing

All commands emit JSON by default. On error:
```json
{
  "command": "...",
  "status": "error",
  "errors": [{"code": "...", "message": "...", "hint": "..."}]
}
```

Parse `errors[0].hint` for the recovery command. Use `--human` for readable error messages.

## Next Steps

- `voting docs show data-model` — understand the .voting/ directory structure
- `voting docs show workflow` — check what phase you are in
