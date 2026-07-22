# Voting Methods

28 counting methods across six categories. All take the same stored ballots — run any combination after the fact.

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
Voters grade each option (A–F). Winner is the option with the highest median grade. Resistant to strategic voting; requires grade ballots.

## Approval / Block Methods

### approval
Each approved option gets one vote; most approvals wins. Simple, expressive, no ranking required.

### block_voting
Multi-seat: voters can approve up to N options; top N by approval count win N seats. Can produce unbalanced results.

### limited_voting
Multi-seat: voters get fewer votes than seats available, encouraging minority representation.

## Score / Range Methods

### score (Range Voting)
Average score across all voters; highest average wins. Fully expressive but vulnerable to strategic min/max scoring.

### star (Score Then Automatic Runoff)
Score round selects top two candidates; runoff round picks the one preferred by more voters. Combines expressiveness with majority preference.

## Condorcet Methods

A Condorcet winner beats every other option head-to-head. All five methods below identify and elect the Condorcet winner when one exists; they differ in how they handle Condorcet cycles.

### copeland
Each option scores +1 for each pairwise win, -1 for each loss. Simple, intuitive; ties are common.

### minimax
Minimize the maximum pairwise defeat. Favors options that, at their worst, lose narrowly.

### ranked_pairs (Tideman)
Lock in pairwise wins from largest to smallest margin, skipping any that would create a cycle. Satisfies many fairness criteria.

### schulze (Beatpath)
Winner is the option with the strongest path of pairwise wins through the tournament graph. Widely used in practice (Debian, Wikimedia, many organizations).

### kemeny_young
Find the ranking that disagrees least with all pairwise preferences. Computationally expensive for >7 options but theoretically optimal.

## Other Methods

### cumulative
Multi-seat: voters distribute a fixed vote budget. Allows strategic concentration; good for minority representation research.

## Method Comparison Tips

The main value of this tool is running the same ballots through multiple methods:

```bash
voting count run my_election --method irv
voting count run my_election --method borda
voting count run my_election --method schulze
voting count run my_election --method approval
voting count list --election my_election
```

When methods agree, the winner has robust support. When they disagree, it reveals how ballot aggregation rules affect outcomes — the interesting case for research.

## Next Steps

- `voting docs show ballot-types` — which ballot types pair with which methods
- `voting docs show workflow` — how to run multi-method comparisons
