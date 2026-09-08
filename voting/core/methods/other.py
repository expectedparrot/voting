from __future__ import annotations

from .common import round_number, sorted_totals


def cumulative(election: dict, options: list[str], ballots: list[dict], tie_policy: str) -> dict:
    totals = {option_id: 0.0 for option_id in options}
    for ballot in ballots:
        weight = float(ballot.get("weight", 1.0))
        for option_id, votes in (ballot.get("allocations") or {}).items():
            if option_id in totals:
                totals[option_id] += float(votes) * weight
    seats = int(election.get("seats", 1))
    order = sorted(totals, key=lambda option_id: (-totals[option_id], option_id))
    winners = order[:seats]
    return {"winners": winners, "ranking": _ranking(order, winners, totals, "votes"), "scores": sorted_totals(totals), "rounds": []}


def bucklin(election: dict, options: list[str], ballots: list[dict], tie_policy: str) -> dict:
    total_weight = sum(float(ballot.get("weight", 1.0)) for ballot in ballots)
    majority = total_weight / 2
    rounds = []
    previous = {option_id: 0.0 for option_id in options}
    for depth in range(1, len(options) + 1):
        totals = {option_id: 0.0 for option_id in options}
        for ballot in ballots:
            weight = float(ballot.get("weight", 1.0))
            for option_id in (ballot.get("ranking") or [])[:depth]:
                if option_id in totals:
                    totals[option_id] += weight
        round_data = {"depth": depth, "totals": sorted_totals(totals), "majority_threshold": round_number(majority)}
        contenders = [option_id for option_id, total in totals.items() if total > majority]
        if contenders:
            contenders.sort(key=lambda option_id: (-totals[option_id], -previous[option_id], option_id))
            winner = contenders[0]
            round_data["elected"] = winner
            rounds.append(round_data)
            order = [winner] + sorted((oid for oid in options if oid != winner), key=lambda oid: (-totals[oid], oid))
            return {"winners": [winner], "ranking": _ranking(order, [winner], totals, "support"), "scores": sorted_totals(totals), "rounds": rounds}
        rounds.append(round_data)
        previous = totals
    order = sorted(options, key=lambda option_id: (-previous[option_id], option_id))
    return {"winners": order[:1], "ranking": _ranking(order, order[:1], previous, "support"), "scores": sorted_totals(previous), "rounds": rounds}


def runoff(election: dict, options: list[str], ballots: list[dict], tie_policy: str) -> dict:
    first = {option_id: 0.0 for option_id in options}
    for ballot in ballots:
        choice = ballot.get("choice") or ((ballot.get("ranking") or [None])[0])
        if choice in first:
            first[choice] += float(ballot.get("weight", 1.0))
    finalists = sorted(options, key=lambda option_id: (-first[option_id], option_id))[:2]
    runoff_totals = {option_id: 0.0 for option_id in finalists}
    no_preference = 0.0
    for ballot in ballots:
        ranking = ballot.get("ranking") or []
        weight = float(ballot.get("weight", 1.0))
        chosen = None
        for option_id in ranking:
            if option_id in runoff_totals:
                chosen = option_id
                break
        if chosen is None:
            choice = ballot.get("choice")
            chosen = choice if choice in runoff_totals else None
        if chosen:
            runoff_totals[chosen] += weight
        else:
            no_preference += weight
    winner = sorted(runoff_totals, key=lambda option_id: (-runoff_totals[option_id], option_id))[0]
    return {
        "winners": [winner],
        "ranking": _ranking(sorted(options, key=lambda option_id: (-runoff_totals.get(option_id, 0.0), option_id)), [winner], {option_id: runoff_totals.get(option_id, 0.0) for option_id in options}, "votes"),
        "scores": sorted_totals(runoff_totals),
        "rounds": [{"round": 1, "totals": sorted_totals(first), "finalists": finalists}, {"round": 2, "totals": sorted_totals(runoff_totals), "no_preference": round_number(no_preference)}],
    }


def majority_judgment(election: dict, options: list[str], ballots: list[dict], tie_policy: str) -> dict:
    """Lower weighted median, with repeated median removal to resolve grade ties.

    Decimal weights are represented as integer units in grade histograms;
    neither fractional votes nor large weights require expanding voter lists.
    Omitted grades are abstentions for that option.
    """
    from fractions import Fraction
    from functools import cmp_to_key
    from math import lcm
    from voting.core.validate import GRADE_SCALE

    scale = election.get("settings", {}).get("grade_scale") or GRADE_SCALE
    grade_index = {grade: idx for idx, grade in enumerate(scale)}
    weights = [Fraction(str(b.get("weight", 1.0))) for b in ballots]
    unit = lcm(*(w.denominator for w in weights)) if weights else 1
    distributions = {oid: [0] * len(scale) for oid in options}
    for ballot, weight in zip(ballots, weights):
        count = int(weight * unit)
        for oid, grade in (ballot.get("grades") or {}).items():
            if oid in distributions and grade in grade_index:
                distributions[oid][grade_index[grade]] += count

    def median(counts):
        total = sum(counts)
        if not total:
            return -1
        cumulative = 0
        for grade, count in enumerate(counts):
            cumulative += count
            if 2 * cumulative >= total:
                return grade
        return -1

    def until_change(counts, grade):
        below = sum(counts[:grade])
        above = sum(counts[grade + 1:])
        middle = counts[grade]
        return min(middle, middle + above - below, middle + below - above + 1)

    def compare(a, b):
        left, right = list(distributions[a]), list(distributions[b])
        while True:
            lm, rm = median(left), median(right)
            if lm != rm:
                return -1 if lm > rm else 1
            if lm < 0 or left == right:
                return (a > b) - (a < b)
            # Skip identical median-removal steps until one median changes.
            remove = min(until_change(left, lm), until_change(right, rm))
            left[lm] -= remove
            right[rm] -= remove

    medians = {oid: median(counts) for oid, counts in distributions.items()}
    order = sorted(options, key=cmp_to_key(compare))
    winner = order[0] if order else None
    return {
        "winners": [winner] if winner else [],
        "ranking": [{"option_id": oid, "rank": idx + 1,
                     "status": "elected" if oid == winner else "defeated",
                     "median": scale[medians[oid]] if medians[oid] >= 0 else None}
                    for idx, oid in enumerate(order)],
        "scores": [{"option_id": oid, "median": scale[medians[oid]] if medians[oid] >= 0 else None}
                   for oid in order],
        "rounds": [],
    }


def _ranking(order: list[str], winners: list[str], totals: dict[str, float], key: str) -> list[dict]:
    return [{"option_id": option_id, "rank": idx + 1, "status": "elected" if option_id in winners else "defeated", key: round_number(totals.get(option_id, 0.0))} for idx, option_id in enumerate(order)]
