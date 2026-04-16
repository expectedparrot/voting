from __future__ import annotations

from collections import defaultdict
from itertools import permutations
from typing import Iterable


def round_number(value: float) -> float:
    return round(float(value), 6)


def sorted_totals(totals: dict[str, float], reverse: bool = True) -> list[dict]:
    return [
        {"option_id": option_id, "total": round_number(total)}
        for option_id, total in sorted(totals.items(), key=lambda item: (-item[1], item[0]) if reverse else (item[1], item[0]))
    ]


def choose_highest(totals: dict[str, float], tie_policy: str = "lexicographic") -> str:
    best = max(totals.values())
    tied = [option_id for option_id, total in totals.items() if total == best]
    return break_tie(tied, tie_policy)


def choose_lowest(totals: dict[str, float], tie_policy: str = "lexicographic") -> str:
    worst = min(totals.values())
    tied = [option_id for option_id, total in totals.items() if total == worst]
    return break_tie(tied, tie_policy)


def break_tie(option_ids: Iterable[str], tie_policy: str = "lexicographic") -> str:
    items = sorted(option_ids)
    if not items:
        raise ValueError("Cannot break an empty tie.")
    return items[0]


def rankings_from_ballots(ballots: list[dict]) -> list[tuple[list[str], float]]:
    return [(list(ballot.get("ranking") or []), float(ballot.get("weight", 1.0))) for ballot in ballots]


def pairwise_matrix(options: list[str], ballots: list[dict]) -> dict[str, dict[str, float]]:
    matrix = {a: {b: 0.0 for b in options if b != a} for a in options}
    for ranking, weight in rankings_from_ballots(ballots):
        positions = {option_id: idx for idx, option_id in enumerate(ranking)}
        for a in options:
            for b in options:
                if a == b:
                    continue
                a_pos = positions.get(a)
                b_pos = positions.get(b)
                if a_pos is None and b_pos is None:
                    continue
                if b_pos is None or (a_pos is not None and a_pos < b_pos):
                    matrix[a][b] += weight
    return matrix


def pairwise_wins(options: list[str], matrix: dict[str, dict[str, float]]) -> list[dict]:
    wins = []
    for a in options:
        for b in options:
            if a >= b:
                continue
            avb = matrix[a][b]
            bva = matrix[b][a]
            if avb == bva:
                winner = None
                loser = None
            elif avb > bva:
                winner = a
                loser = b
            else:
                winner = b
                loser = a
            wins.append({"a": a, "b": b, "a_over_b": round_number(avb), "b_over_a": round_number(bva), "winner": winner, "loser": loser, "margin": round_number(abs(avb - bva))})
    return wins


def would_create_cycle(edges: set[tuple[str, str]], new_edge: tuple[str, str]) -> bool:
    start, end = new_edge
    graph: dict[str, list[str]] = defaultdict(list)
    for a, b in [*edges, new_edge]:
        graph[a].append(b)
    stack = [end]
    seen = set()
    while stack:
        node = stack.pop()
        if node == start:
            return True
        if node in seen:
            continue
        seen.add(node)
        stack.extend(graph[node])
    return False


def rank_from_edges(options: list[str], edges: set[tuple[str, str]]) -> list[str]:
    scores = {option_id: 0 for option_id in options}
    for winner, loser in edges:
        scores[winner] += 1
        scores[loser] -= 1
    return sorted(options, key=lambda option_id: (-scores[option_id], option_id))


def kemeny_best(options: list[str], matrix: dict[str, dict[str, float]]) -> tuple[list[str], float]:
    best_order: tuple[str, ...] | None = None
    best_score = -1.0
    for order in permutations(options):
        score = 0.0
        for i, a in enumerate(order):
            for b in order[i + 1 :]:
                score += matrix[a][b]
        if score > best_score or (score == best_score and list(order) < list(best_order or ())):
            best_score = score
            best_order = order
    return list(best_order or []), best_score
