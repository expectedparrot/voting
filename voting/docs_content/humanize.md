# Humanize Surveys

Humanize turns a voting election into a hosted web survey for real people. It
uses EDSL's `ep humanize` commands for remote creation, URLs, respondent email
delivery, and response retrieval. The generated EDSL Jobs package contains no
language model.

Humanize currently supports `ranked`, `single_choice`, `approval`, and `score`
ballots. Grade and allocated ballots should be cast or imported directly.

## Install the Integration

```bash
pip install -e '.[humanize]'
ep --help
```

The `ep` CLI uses its normal Expected Parrot credentials and active profile.
Voting does not copy credentials into project state.

## Create a Shareable Survey

The election must contain at least two eligible options.

```bash
voting survey humanize <election_id>
voting survey publish <election_id>
```

Choice order is randomized independently for each respondent by default, which
reduces starting-order effects. Use `--no-randomize-options` only when the
display order is substantively meaningful or must remain fixed.

`humanize` writes a model-free EDSL Jobs package, a Humanize schema, and a
manifest under `.voting/output/`. `publish` delegates to `ep humanize create`,
saves the returned deployment metadata, and prints:

- `respondent_url` — the link to send to voters
- `admin_url` — the dashboard for monitoring the survey
- `uuid` — the stable Humanize survey identifier

The equivalent lower-level command is included in the JSON `next_steps` from
`voting survey humanize`, so the package can also be reviewed and published
with `ep` directly.

## Email Unique Voting Links

Email delivery requires registered voters and an email trait on every voter.
Trait values are JSON values, so quote string addresses as shown:

```bash
voting voter set-trait voter_1 email '"voter1@example.com"'
voting voter set-trait voter_2 email '"voter2@example.com"'

voting survey humanize <election_id> --email-trait email
voting survey publish <election_id>
voting survey email <election_id> \
  --name "Voting invitation" \
  --subject "Please cast your vote"
```

The generated job contains an EDSL AgentList keyed by voter ID. Its delivery
map tells Humanize which trait contains the email address. `survey email`
creates an immediate Expected Parrot delivery using the built-in respondent
invitation template and returns a delivery UUID for tracking.

Do not commit personal email addresses or deployment files to a public
repository. Obtain appropriate consent and follow the applicable privacy,
retention, and unsubscribe requirements for the electorate.

## Retrieve Responses

```bash
voting survey responses <election_id>
```

This asks `ep humanize responses` for the published survey's responses and
writes `.voting/output/humanize_responses_<election_id>.ep`. The artifact is an
EDSL Results package suitable for inspection and downstream conversion into
validated voting ballots.

Use the admin URL or the lower-level EDSL commands for status and delivery
diagnostics:

```bash
ep humanize status <human_survey_uuid>
ep humanize respondents <human_survey_uuid>
ep humanize deliveries list <human_survey_uuid>
ep humanize deliveries tasks <human_survey_uuid> <delivery_uuid>
```

## Generated Files

| File | Purpose |
|------|---------|
| `humanize_<election_id>.ep` | Model-free EDSL Jobs package |
| `humanize_<election_id>.json` | Voting-to-EDSL manifest |
| `humanize_schema_<election_id>.json` | Required-question presentation schema |
| `humanize_delivery_<election_id>.json` | Email trait mapping, when requested |
| `humanize_deployment_<election_id>.json` | Saved UUID and hosted URLs |
| `humanize_responses_<election_id>.ep` | Downloaded EDSL Results package |

Regenerate the job whenever election wording, options, voters, or email traits
change. Publishing again creates a new remote Humanize survey; it does not
silently mutate the prior deployment.

## Humanize vs. Synthetic EDSL

| Goal | Command |
|------|---------|
| Ask AI personas to simulate preferences | `voting survey generate` |
| Inspect the generated AI script | `voting --human survey show` |
| Ask real people through a web survey | `voting survey humanize` + `publish` |
| Send unique email invitations | `voting survey email` |
| Download human responses | `voting survey responses` |

Always label synthetic and human evidence separately in the final analysis.

## Next Steps

- `voting docs show workflow` — see all three preference paths in context
- `voting docs show data-model` — inspect local Humanize artifacts
- `voting docs show troubleshooting` — diagnose EDSL, publishing, and delivery failures
