# Voting Methods

35 method names and aliases across six categories. Reuse stored ballots with compatible methods after the fact. Methods enforce ballot format and seat-count compatibility.

## Quick Selection Guide

| Goal | Recommended method |
|------|--------------------|
| Simplest single-winner | `fptp` |
| Eliminate vote-splitting | `irv` |
| Reward broad support | `borda` |
| Find the pairwise winner | `schulze` or `ranked_pairs` |
| Approve multiple, pick best | `approval` |
| Capture preference intensity | `score` or `star` |
| Multi-seat proportional | `stv` |
| Multi-seat bloc | `block_voting` |

## Plurality / Single-Choice Methods

### fptp (First Past the Post)
Most first-choice votes wins. Simple, familiar, prone to vote-splitting with 3+ options.

### simple_majority
Winner needs >50% of first-choice votes; no winner declared if no majority.

### sntv (Single Non-Transferable Vote)
Multi-seat: voters cast one vote each; top N candidates by vote count win N seats.

## Ranked Methods

### irv (Instant Runoff Voting)
Eliminate the last-place candidate each round, transfer their votes to the next ranked choice. Prevents vote-splitting; requires full ranking for best results.

### borda
Each option receives points based on its position in every ballot (last = 0, second-to-last = 1, ...). Rewards options with broad moderate support over polarizing favorites.

### stv (Single Transferable Vote)
Multi-seat proportional method using ranked ballots and the Droop quota. The standard for multi-member proportional representation.

### bucklin
Voters rank options; first check if any gets majority first-choice, then add second choices, etc. until a majority is reached.

### runoff (Two-Round)
If no option gets majority in round 1, top two advance to a simulated runoff.

### majority_judgment
Requires grade ballots. Uses the lower weighted median grade; fractional weights are preserved. Tied medians are resolved by repeatedly removing a median grade from tied distributions, then lexicographically if still identical. Decimal weights are represented as integer units without expanding voter lists. Omitted grades are abstentions for that option.

Default labels are reject, poor, fair, good, excellent; configure another ordered scale with `election configure --grade` (worst to best). See [Balinski and Laraki (2007)](https://www.rangevoting.org/BalinskiLarakiPNASpdf.pdf) for the median-removal rule.

## Approval / Block Methods

### approval
Each approved option gets one vote; most approvals wins. Simple, expressive, no ranking required.

### block_voting
Multi-seat: voters can approve up to N options; top N by approval count win N seats. Ballots exceeding N (or a stricter configured approval limit) make this method incompatible with that dataset.

### limited_voting
Multi-seat: voters get fewer votes than seats available. Configure `--approval-limit` below `--seats`; the default counting limit is seats minus one. Requires at least two seats and rejects datasets containing ballots over the limit.

## Score / Range Methods

### score (Range Voting)
Weighted score totals determine the winner. Omitted scores contribute zero to totals; the reported average uses only voters who scored that option. Scores must be finite; there is no default range restriction.

### star (Score Then Automatic Runoff)
Score round selects top two candidates; runoff round picks the one preferred by more voters. Combines expressiveness with majority preference.

## Condorcet Methods

A Condorcet winner beats every other option head-to-head. All five methods below identify and elect the Condorcet winner when one exists; they differ in how they handle Condorcet cycles.

### copeland
Each option scores 1 for each pairwise win, 0.5 for each tie, and 0 for each loss. Ties in the final score use lexicographic order.

### minimax
Minimize the maximum pairwise defeat. Favors options that, at their worst, lose narrowly.

### ranked_pairs (Tideman)
Lock in pairwise wins from largest to smallest margin, skipping any that would create a cycle. Satisfies many fairness criteria.

### schulze (Beatpath)
Winner is the option with the strongest path of pairwise wins through the tournament graph. Widely used in practice (Debian, Wikimedia, many organizations).

### kemeny_young
Find the ranking that disagrees least with all pairwise preferences. Enumerates every permutation. `count run` and `count compare` limit this to nine eligible options by default. Default comparisons skip it above the limit and explain why; explicitly requesting it requires `--allow-expensive` above the limit. Even 12 options require 479 million permutations.

## Other Methods

### cumulative
Multi-seat: voters distribute a fixed vote budget; raw points are summed. Allows strategic concentration (rational voters dump their budget); good for minority representation research.

### quadratic (alias: qv)
Budget allocation with square-root scoring: a voter's effective support for an option is sqrt(points spent), so the marginal price of influence rises with intensity and allocating in proportion to true utility is the rational strategy. The closest practical approximation to utility-maximizing selection under a forced budget. Deterministic; supports seats for top-K.

### equal_shares (alias: mes)
Method of Equal Shares (Peters-Skowron) over allocated points as cardinal utilities. Every voter controls an equal share of a virtual budget — allocations steer how the share is spent, never how large it is — and a cohesive group of n/k voters can always afford one of k seats. Choose this when the top-K should *represent* the group (proportionality) rather than maximize summed points; seats MES cannot fill are completed utilitarian-style and marked `completed_seats` in the result.

## Settings and comparisons

Only lexicographic tie-breaking is supported; unknown policies are rejected.
Single-winner methods reject multiple seats. Seats must be positive and cannot
exceed eligible options. Default comparisons skip methods that cannot honor
the election's seats or approval limits, returning `methods_skipped` reasons.
Explicit method lists are checked in full before saving any results.
A count with no valid ballots declares no winner.

## Method Comparison Tips

The main value of this tool is running the same ballots through multiple methods:

```bash
voting count run my_election --method irv
voting count run my_election --method borda
voting count run my_election --method schulze
voting count compare my_election
voting count list --election my_election
```

When methods agree, the winner has robust support. When they disagree, it reveals how ballot aggregation rules affect outcomes — the interesting case for research.

## Next Steps

- `voting docs show ballot-types` — which ballot types pair with which methods
- `voting docs show workflow` — how to run multi-method comparisons
