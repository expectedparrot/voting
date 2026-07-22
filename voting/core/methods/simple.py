from __future__ import annotations

from .common import choose_highest, round_number, sorted_totals


def fptp(election: dict, options: list[str], ballots: list[dict], tie_policy: str) -> dict:
    totals = {option_id: 0.0 for option_id in options}
    for ballot in ballots:
        choice = ballot.get("choice")
        if choice is None and ballot.get("ranking"):
            choice = ballot["ranking"][0]
        if choice in totals:
            totals[choice] += float(ballot.get("weight", 1.0))
    best = max(totals.values(), default=0.0)
    tied = sorted(oid for oid, t in totals.items() if t == best)
    winner = choose_highest(totals, tie_policy)
    warnings = []
    if len(tied) > 1:
        warnings.append({
            "code": "tiebreak_applied",
            "tied_options": tied,
            "score": round_number(best),
            "policy": tie_policy,
            "message": (
                f"Tie between {', '.join(tied)} ({round_number(best)} votes each). "
                f"Winner selected by {tie_policy!r} tiebreak."
            ),
        })
    return {"winners": [winner], "ranking": _ranking(totals), "scores": sorted_totals(totals), "rounds": [], "warnings": warnings}


def simple_majority(election: dict, options: list[str], ballots: list[dict], tie_policy: str) -> dict:
    result = fptp(election, options, ballots, tie_policy)
    total = sum(item["total"] for item in result["scores"])
    threshold = total / 2
    winner_total = result["scores"][0]["total"] if result["scores"] else 0
    met = winner_total > threshold
    result["majority_threshold"] = round_number(threshold)
    result["majority_met"] = met
    if not met:
        result["winners"] = []
    return result


def sntv(election: dict, options: list[str], ballots: list[dict], tie_policy: str) -> dict:
    totals = {option_id: 0.0 for option_id in options}
    for ballot in ballots:
        choice = ballot.get("choice")
        if choice in totals:
            totals[choice] += float(ballot.get("weight", 1.0))
    seats = int(election.get("seats", 1))
    ordered = sorted(totals, key=lambda option_id: (-totals[option_id], option_id))
    winners = ordered[:seats]
    return {"winners": winners, "ranking": _ranking(totals, seats), "scores": sorted_totals(totals), "rounds": []}


def _ranking(totals: dict[str, float], seats: int = 1) -> list[dict]:
    ordered = sorted(totals, key=lambda option_id: (-totals[option_id], option_id))
    return [
        {"option_id": option_id, "rank": idx + 1, "status": "elected" if idx < seats else "defeated", "total": round_number(totals[option_id])}
        for idx, option_id in enumerate(ordered)
    ]
