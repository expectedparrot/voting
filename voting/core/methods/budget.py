"""Budget-allocation methods: quadratic voting and the Method of Equal Shares.

Both consume `allocated` ballots (each voter distributes a budget of points
over options) and support multi-winner selection via seats. They answer two
different questions:

- quadratic: approximate *utility maximization*. Effective support is the
  square root of points spent, so the marginal price of influence rises with
  intensity and proportional-to-utility allocation is the rational strategy
  (Lalley-Weyl). A voter who dumps everything on one option gets sqrt(budget),
  not budget.
- equal_shares: *proportional representation* (Peters-Skowron MES). Every
  voter controls an equal share of a virtual budget regardless of how many
  points they allocated; allocations only steer how that fixed share is
  spent. A cohesive group of n/k voters can always afford one of the k seats.
"""
from __future__ import annotations

import math

from .common import round_number, sorted_totals


def _ranking(order: list[str], winners: list[str], totals: dict[str, float], key: str) -> list[dict]:
    return [
        {"option_id": option_id, "rank": idx + 1,
         "status": "elected" if option_id in winners else "defeated",
         key: round_number(totals.get(option_id, 0.0))}
        for idx, option_id in enumerate(order)
    ]


def quadratic(election: dict, options: list[str], ballots: list[dict], tie_policy: str) -> dict:
    support = {option_id: 0.0 for option_id in options}
    raw_points = {option_id: 0.0 for option_id in options}
    for ballot in ballots:
        weight = float(ballot.get("weight", 1.0))
        for option_id, points in (ballot.get("allocations") or {}).items():
            points = float(points)
            if option_id in support and points > 0:
                support[option_id] += weight * math.sqrt(points)
                raw_points[option_id] += weight * points
    seats = int(election.get("seats", 1))
    order = sorted(support, key=lambda option_id: (-support[option_id], option_id))
    winners = order[:seats]
    return {
        "winners": winners,
        "ranking": _ranking(order, winners, support, "support"),
        "scores": sorted_totals(support),
        "raw_points": sorted_totals(raw_points),
        "rounds": [],
    }


def equal_shares(election: dict, options: list[str], ballots: list[dict], tie_policy: str) -> dict:
    """Method of Equal Shares over cardinal utilities (unit-cost candidates).

    Each voter's budget is seats * weight / total_weight, so the electorate
    can afford exactly `seats` candidates. A candidate is elected at the
    lowest price-per-utility rho with sum_i min(budget_i, rho * u_i) = cost 1;
    supporters pay proportionally to stated utility, capped by budget. Seats
    MES cannot fill (no candidate remains affordable) are completed
    utilitarian-style from remaining point totals, and marked as such.
    """
    seats = int(election.get("seats", 1))
    voters = []
    total_weight = 0.0
    utility_totals = {option_id: 0.0 for option_id in options}
    for ballot in ballots:
        weight = float(ballot.get("weight", 1.0))
        utilities = {
            option_id: float(points)
            for option_id, points in (ballot.get("allocations") or {}).items()
            if option_id in utility_totals and float(points) > 0
        }
        total_weight += weight
        for option_id, points in utilities.items():
            utility_totals[option_id] += weight * points
        if utilities:
            voters.append({"weight": weight, "utilities": utilities, "budget": 0.0})
    if total_weight > 0:
        for voter in voters:
            voter["budget"] = seats * voter["weight"] / total_weight

    epsilon = 1e-9
    elected: list[str] = []
    rounds: list[dict] = []

    def cheapest_rho(option_id: str) -> float | None:
        """Minimal rho with sum_i min(budget_i, rho * u_i) = 1, or None if unaffordable."""
        supporters = [
            (voter["budget"], voter["utilities"][option_id])
            for voter in voters if voter["utilities"].get(option_id, 0.0) > 0
        ]
        if sum(budget for budget, _ in supporters) < 1.0 - epsilon:
            return None
        supporters.sort(key=lambda item: item[0] / item[1])  # by cap threshold budget/utility
        capped_budget = 0.0
        uncapped_utility = sum(utility for _, utility in supporters)
        for budget, utility in supporters:
            rho = (1.0 - capped_budget) / uncapped_utility
            if rho * utility <= budget + epsilon:
                return rho
            capped_budget += budget
            uncapped_utility -= utility
        return None  # unreachable when affordable

    while len(elected) < seats:
        best: tuple[float, str] | None = None
        for option_id in options:
            if option_id in elected:
                continue
            rho = cheapest_rho(option_id)
            if rho is None:
                continue
            if best is None or rho < best[0] - epsilon or (abs(rho - best[0]) <= epsilon and option_id < best[1]):
                best = (rho, option_id)
        if best is None:
            break
        rho, option_id = best
        payers = 0
        for voter in voters:
            utility = voter["utilities"].get(option_id, 0.0)
            if utility > 0:
                payment = min(voter["budget"], rho * utility)
                voter["budget"] -= payment
                payers += 1
        elected.append(option_id)
        rounds.append({
            "round": len(elected),
            "elected": option_id,
            "price_per_utility": round_number(rho),
            "supporters_charged": payers,
        })

    completed: list[str] = []
    if len(elected) < seats:
        remaining = sorted(
            (option_id for option_id in options if option_id not in elected),
            key=lambda option_id: (-utility_totals[option_id], option_id),
        )
        for option_id in remaining[: seats - len(elected)]:
            elected.append(option_id)
            completed.append(option_id)
            rounds.append({
                "round": len(elected),
                "elected": option_id,
                "completion": "utilitarian",
            })

    unelected = sorted(
        (option_id for option_id in options if option_id not in elected),
        key=lambda option_id: (-utility_totals[option_id], option_id),
    )
    order = elected + unelected
    return {
        "winners": elected,
        "ranking": _ranking(order, elected, utility_totals, "points"),
        "scores": sorted_totals(utility_totals),
        "rounds": rounds,
        "completed_seats": completed,
        "budget": {"candidate_cost": 1.0, "total_budget": round_number(seats)},
    }
