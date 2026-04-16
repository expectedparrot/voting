from __future__ import annotations

from .common import sorted_totals


def score(election: dict, options: list[str], ballots: list[dict], tie_policy: str) -> dict:
    totals = {option_id: 0.0 for option_id in options}
    counts = {option_id: 0.0 for option_id in options}
    for ballot in ballots:
        weight = float(ballot.get("weight", 1.0))
        for option_id, value in (ballot.get("scores") or {}).items():
            if option_id in totals:
                totals[option_id] += float(value) * weight
                counts[option_id] += weight
    ordered = sorted(totals, key=lambda option_id: (-totals[option_id], option_id))
    return {
        "winners": [ordered[0]] if ordered else [],
        "ranking": [{"option_id": option_id, "rank": idx + 1, "status": "elected" if idx == 0 else "defeated", "score": round(totals[option_id], 6), "average": round(totals[option_id] / counts[option_id], 6) if counts[option_id] else 0} for idx, option_id in enumerate(ordered)],
        "scores": sorted_totals(totals),
        "rounds": [],
    }


def star(election: dict, options: list[str], ballots: list[dict], tie_policy: str) -> dict:
    base = score(election, options, ballots, tie_policy)
    finalists = [item["option_id"] for item in base["ranking"][:2]]
    runoff = {option_id: 0.0 for option_id in finalists}
    no_preference = 0.0
    if len(finalists) == 2:
        a, b = finalists
        for ballot in ballots:
            scores = ballot.get("scores") or {}
            av = float(scores.get(a, 0))
            bv = float(scores.get(b, 0))
            weight = float(ballot.get("weight", 1.0))
            if av > bv:
                runoff[a] += weight
            elif bv > av:
                runoff[b] += weight
            else:
                no_preference += weight
    winner = sorted(runoff, key=lambda option_id: (-runoff[option_id], option_id))[0] if runoff else None
    base["winners"] = [winner] if winner else []
    base["finalists"] = finalists
    base["runoff"] = {"totals": sorted_totals(runoff), "no_preference": round(no_preference, 6)}
    return base
