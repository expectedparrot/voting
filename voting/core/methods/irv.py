from __future__ import annotations

from voting.core.ballots import first_active_choice

from .common import choose_lowest, round_number, sorted_totals


def irv(election: dict, options: list[str], ballots: list[dict], tie_policy: str) -> dict:
    active = set(options)
    rounds = []
    eliminated = []
    while active:
        totals = {option_id: 0.0 for option_id in active}
        exhausted = 0.0
        for ballot in ballots:
            choice = first_active_choice(ballot.get("ranking") or [], active)
            weight = float(ballot.get("weight", 1.0))
            if choice is None:
                exhausted += weight
            else:
                totals[choice] += weight
        active_total = sum(totals.values())
        winner = None
        for option_id, total in totals.items():
            if total > active_total / 2:
                winner = option_id
                break
        round_data = {"totals": sorted_totals(totals), "exhausted_weight": round_number(exhausted)}
        if winner or len(active) == 1:
            winner = winner or sorted(active)[0]
            round_data["elected"] = winner
            rounds.append(round_data)
            return {
                "winners": [winner],
                "ranking": _ranking(winner, eliminated, options),
                "rounds": rounds,
                "scores": sorted_totals({option_id: totals.get(option_id, 0.0) for option_id in options}),
                "exhausted_weight": round_number(exhausted),
            }
        loser = choose_lowest(totals, tie_policy)
        active.remove(loser)
        eliminated.append(loser)
        round_data["eliminated"] = loser
        rounds.append(round_data)
    return {"winners": [], "ranking": [], "rounds": rounds, "scores": []}


def _ranking(winner: str, eliminated: list[str], options: list[str]) -> list[dict]:
    order = [winner] + list(reversed(eliminated)) + [option_id for option_id in options if option_id != winner and option_id not in eliminated]
    return [{"option_id": option_id, "rank": idx + 1, "status": "elected" if idx == 0 else "eliminated"} for idx, option_id in enumerate(order)]
