from __future__ import annotations

from .common import sorted_totals


def approval(election: dict, options: list[str], ballots: list[dict], tie_policy: str) -> dict:
    return _approval_like(election, options, ballots)


def block_voting(election: dict, options: list[str], ballots: list[dict], tie_policy: str) -> dict:
    return _approval_like(election, options, ballots)


def limited_voting(election: dict, options: list[str], ballots: list[dict], tie_policy: str) -> dict:
    return _approval_like(election, options, ballots)


def _approval_like(election: dict, options: list[str], ballots: list[dict]) -> dict:
    totals = {option_id: 0.0 for option_id in options}
    for ballot in ballots:
        weight = float(ballot.get("weight", 1.0))
        approved = ballot.get("approved")
        if approved is None and ballot.get("choice"):
            approved = [ballot["choice"]]
        for option_id in approved or []:
            if option_id in totals:
                totals[option_id] += weight
    seats = int(election.get("seats", 1))
    ordered = sorted(totals, key=lambda option_id: (-totals[option_id], option_id))
    winners = ordered[:seats]
    return {
        "winners": winners,
        "ranking": [{"option_id": option_id, "rank": idx + 1, "status": "elected" if option_id in winners else "defeated", "approvals": round(totals[option_id], 6)} for idx, option_id in enumerate(ordered)],
        "scores": sorted_totals(totals),
        "rounds": [],
    }
