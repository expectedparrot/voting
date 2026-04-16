from __future__ import annotations

import math

from voting.core.ballots import first_active_choice

from .common import choose_lowest, round_number, sorted_totals


def stv(election: dict, options: list[str], ballots: list[dict], tie_policy: str) -> dict:
    seats = int(election.get("seats", 1))
    if seats == 1:
        from .irv import irv

        result = irv(election, options, ballots, tie_policy)
        result["quota"] = math.floor(sum(float(ballot.get("weight", 1.0)) for ballot in ballots) / 2) + 1
        return result

    total_weight = sum(float(ballot.get("weight", 1.0)) for ballot in ballots)
    quota = math.floor(total_weight / (seats + 1)) + 1
    active = set(options)
    elected: list[str] = []
    eliminated: list[str] = []
    weighted_ballots = [{"ranking": ballot.get("ranking") or [], "weight": float(ballot.get("weight", 1.0))} for ballot in ballots]
    rounds = []

    while active and len(elected) < seats:
        totals = {option_id: 0.0 for option_id in active}
        exhausted = 0.0
        assignments: dict[str, list[dict]] = {option_id: [] for option_id in active}
        for ballot in weighted_ballots:
            choice = first_active_choice(ballot["ranking"], active)
            if choice is None:
                exhausted += ballot["weight"]
            else:
                totals[choice] += ballot["weight"]
                assignments[choice].append(ballot)

        round_data = {"totals": sorted_totals(totals), "exhausted_weight": round_number(exhausted)}
        elected_this_round = [option_id for option_id, total in sorted(totals.items(), key=lambda item: (-item[1], item[0])) if total >= quota]
        if elected_this_round:
            for option_id in elected_this_round:
                if option_id not in elected and len(elected) < seats:
                    elected.append(option_id)
                    active.remove(option_id)
                    surplus = totals[option_id] - quota
                    if surplus > 0 and totals[option_id] > 0:
                        factor = surplus / totals[option_id]
                        for ballot in assignments[option_id]:
                            ballot["weight"] *= factor
                    else:
                        for ballot in assignments[option_id]:
                            ballot["weight"] = 0.0
            round_data["elected"] = elected_this_round
            rounds.append(round_data)
            continue

        if len(active) + len(elected) <= seats:
            elected.extend(sorted(active))
            round_data["elected"] = sorted(active)
            active.clear()
            rounds.append(round_data)
            break

        loser = choose_lowest(totals, tie_policy)
        active.remove(loser)
        eliminated.append(loser)
        round_data["eliminated"] = loser
        rounds.append(round_data)

    ranking_order = elected + list(reversed(eliminated)) + sorted(active)
    return {
        "winners": elected[:seats],
        "ranking": [{"option_id": option_id, "rank": idx + 1, "status": "elected" if option_id in elected[:seats] else "eliminated"} for idx, option_id in enumerate(ranking_order)],
        "rounds": rounds,
        "scores": rounds[-1]["totals"] if rounds else [],
        "quota": quota,
    }
