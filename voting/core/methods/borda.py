from __future__ import annotations

from .common import sorted_totals


def borda(election: dict, options: list[str], ballots: list[dict], tie_policy: str) -> dict:
    totals = {option_id: 0.0 for option_id in options}
    n = len(options)
    for ballot in ballots:
        weight = float(ballot.get("weight", 1.0))
        for idx, option_id in enumerate(ballot.get("ranking") or []):
            if option_id in totals:
                totals[option_id] += (n - idx - 1) * weight
    ordered = sorted(totals, key=lambda option_id: (-totals[option_id], option_id))
    return {
        "winners": [ordered[0]] if ordered else [],
        "ranking": [{"option_id": option_id, "rank": idx + 1, "status": "elected" if idx == 0 else "defeated", "score": round(totals[option_id], 6)} for idx, option_id in enumerate(ordered)],
        "scores": sorted_totals(totals),
        "rounds": [],
    }
