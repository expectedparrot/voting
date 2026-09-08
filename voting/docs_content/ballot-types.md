# Ballot Types

Six ballot formats are supported. Choose based on the information you want from voters and the counting methods you plan to use.

## single_choice

Voter picks exactly one option.

```bash
voting ballot cast <election_id> <voter_id> --choice <option_id>
```

Use with: `fptp`, `simple_majority`, `sntv`, `runoff`

## ranked

Voter ranks options in order of preference (most to least preferred).

```bash
voting ballot rank <election_id> <voter_id> opt_a opt_b opt_c
```

Options not listed are treated as unranked (tied last) by most methods. Duplicates are rejected.

Use with: `irv`, `stv`, `borda`, `bucklin`, `ranked_pairs`, `schulze`, `kemeny_young`, `copeland`, `minimax`

FPTP, simple majority, and runoff also accept ranked ballots by extracting first preferences. Ranked-only methods reject single-choice ballots.

## approval

Voter marks any number of options as approved (no ordering). Duplicates are rejected.
Use `voting ballot approve <election_id> <voter_id> --abstain` to approve nothing.
Set a per-ballot limit with `voting election configure <election_id> --approval-limit 2`.

```bash
voting ballot approve <election_id> <voter_id> --option opt_a --option opt_b
```

Use with: `approval`, `block_voting`, `limited_voting`

## score

Voter assigns a numeric score to each option (higher = more preferred). All options can receive any score.

```bash
voting ballot score <election_id> <voter_id> opt_a=8 opt_b=3 opt_c=9
```

Score range is unconstrained by default; the counting method may define its own scale.

Use with: `score` (range voting), `star`

## grade

Voter assigns an ordered grade label to each option. Defaults, worst to best:
`reject`, `poor`, `fair`, `good`, `excellent`. Omitted grades are abstentions for that option.

```bash
voting ballot grade <election_id> <voter_id> opt_a=excellent opt_b=fair opt_c=good
```

Customize with `voting election configure <election_id> --grade F --grade C --grade B --grade A`
(repeat labels from worst to best).

Use with: `majority_judgment`

## allocated

Voter distributes a fixed budget of votes across options (cumulative voting).

```bash
voting ballot allocate <election_id> <voter_id> opt_a=40 opt_b=35 opt_c=25
```

Budget validation is optional: use `voting election configure <election_id> --budget 100`.
Allocations must always be finite and nonnegative; negative amounts cannot offset spending.

Use with: `cumulative`, `quadratic`, `equal_shares`

## Choosing a Ballot Type

| Goal | Recommended ballot type |
|------|------------------------|
| Simplest possible ballot | `single_choice` |
| Capture preference ordering | `ranked` |
| Allow "approve many" | `approval` |
| Capture intensity of preference | `score` |
| Categorical evaluation | `grade` |
| Weighted priority allocation | `allocated` |

## Cross-type Compatibility

Counts enforce ballot-type compatibility, including method aliases:
- FPTP and simple_majority can extract a first choice from ranked ballots
- Approval counting accepts single-choice ballots as one approval each
- Binary score ballots can model approval, but approval ballots are not automatically converted to scores

Always validate after importing: `voting ballot validate <election_id>`

## Survey Collection Support

Both synthetic EDSL generation and hosted Humanize surveys support
`single_choice`, `ranked`, `approval`, and `score`. Humanize jobs are model-free
and collect answers from real people at a respondent URL. `grade` and
`allocated` ballots currently use direct casting or JSON imports (`ballot import --from`).
The JSON importer supports all six ballot types. EDSL Results imports support the four survey ballot types.

## Next Steps

- `voting docs show voting-methods` — which methods pair with which ballot types
- `voting docs show humanize` — publish and email hosted human ballots
- `voting docs show workflow` — the balloting phase in detail
