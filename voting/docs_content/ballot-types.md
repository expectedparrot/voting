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

Use with: `irv`, `stv`, `borda`, `bucklin`, `ranked_pairs`, `schulze`, `kemeny_young`, `copeland`, `minimax`, `majority_judgment`

Many ranked-ballot methods also accept single-choice ballots by extracting the first choice.

## approval

Voter marks any number of options as approved (no ordering).

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

Voter assigns a letter grade to each option.

```bash
voting ballot grade <election_id> <voter_id> opt_a=A opt_b=C opt_c=B
```

Use with: `majority_judgment`

## allocated

Voter distributes a fixed budget of votes across options (cumulative voting).

```bash
voting ballot allocate <election_id> <voter_id> opt_a=40 opt_b=35 opt_c=25
```

Budget validation is optional — set `budget` in election settings to enforce it.

Use with: `cumulative`

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

Some methods handle ballot types they weren't designed for:
- FPTP and simple_majority can extract a first choice from ranked ballots
- Score voting degrades gracefully to approval if scores are 0/1

Always validate after importing: `voting ballot validate <election_id>`

## Next Steps

- `voting docs show voting-methods` — which methods pair with which ballot types
- `voting docs show workflow` — the balloting phase in detail
