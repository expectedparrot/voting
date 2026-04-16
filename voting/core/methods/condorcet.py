from __future__ import annotations

from .common import kemeny_best, pairwise_matrix, pairwise_wins, rank_from_edges, round_number, would_create_cycle


def copeland(election: dict, options: list[str], ballots: list[dict], tie_policy: str) -> dict:
    matrix = pairwise_matrix(options, ballots)
    scores = {option_id: 0.0 for option_id in options}
    for item in pairwise_wins(options, matrix):
        if item["winner"] is None:
            scores[item["a"]] += 0.5
            scores[item["b"]] += 0.5
        else:
            scores[item["winner"]] += 1
    return _result(options, matrix, scores)


def minimax(election: dict, options: list[str], ballots: list[dict], tie_policy: str) -> dict:
    matrix = pairwise_matrix(options, ballots)
    scores = {}
    for a in options:
        worst_defeat = 0.0
        for b in options:
            if a == b:
                continue
            defeat = matrix[b][a] - matrix[a][b]
            worst_defeat = max(worst_defeat, defeat)
        scores[a] = -worst_defeat
    return _result(options, matrix, scores)


def ranked_pairs(election: dict, options: list[str], ballots: list[dict], tie_policy: str) -> dict:
    matrix = pairwise_matrix(options, ballots)
    victories = []
    for a in options:
        for b in options:
            if a == b:
                continue
            if matrix[a][b] > matrix[b][a]:
                victories.append((a, b, matrix[a][b] - matrix[b][a], matrix[a][b]))
    victories.sort(key=lambda item: (-item[2], -item[3], item[0], item[1]))
    locked: set[tuple[str, str]] = set()
    skipped = []
    for winner, loser, margin, strength in victories:
        edge = (winner, loser)
        if would_create_cycle(locked, edge):
            skipped.append({"winner": winner, "loser": loser, "margin": round_number(margin)})
        else:
            locked.add(edge)
    ranking = rank_from_edges(options, locked)
    return {"winners": ranking[:1], "ranking": _ranking_from_order(ranking), "pairwise": pairwise_wins(options, matrix), "locked": sorted(locked), "skipped": skipped, "rounds": []}


def schulze(election: dict, options: list[str], ballots: list[dict], tie_policy: str) -> dict:
    matrix = pairwise_matrix(options, ballots)
    strength = {a: {b: 0.0 for b in options if b != a} for a in options}
    for a in options:
        for b in options:
            if a == b:
                continue
            strength[a][b] = matrix[a][b] if matrix[a][b] > matrix[b][a] else 0.0
    for i in options:
        for j in options:
            if i == j:
                continue
            for k in options:
                if i == k or j == k:
                    continue
                strength[j][k] = max(strength[j][k], min(strength[j][i], strength[i][k]))
    wins = {option_id: 0 for option_id in options}
    for a in options:
        for b in options:
            if a != b and strength[a][b] > strength[b][a]:
                wins[a] += 1
    order = sorted(options, key=lambda option_id: (-wins[option_id], option_id))
    return {"winners": order[:1], "ranking": _ranking_from_order(order), "pairwise": pairwise_wins(options, matrix), "path_strengths": strength, "rounds": []}


def kemeny_young(election: dict, options: list[str], ballots: list[dict], tie_policy: str) -> dict:
    matrix = pairwise_matrix(options, ballots)
    order, score = kemeny_best(options, matrix)
    return {"winners": order[:1], "ranking": _ranking_from_order(order), "pairwise": pairwise_wins(options, matrix), "kemeny_score": round_number(score), "rounds": []}


def _result(options: list[str], matrix: dict[str, dict[str, float]], scores: dict[str, float]) -> dict:
    order = sorted(options, key=lambda option_id: (-scores[option_id], option_id))
    return {
        "winners": order[:1],
        "ranking": [{"option_id": option_id, "rank": idx + 1, "status": "elected" if idx == 0 else "defeated", "score": round_number(scores[option_id])} for idx, option_id in enumerate(order)],
        "scores": [{"option_id": option_id, "total": round_number(scores[option_id])} for option_id in order],
        "pairwise": pairwise_wins(options, matrix),
        "rounds": [],
    }


def _ranking_from_order(order: list[str]) -> list[dict]:
    return [{"option_id": option_id, "rank": idx + 1, "status": "elected" if idx == 0 else "defeated"} for idx, option_id in enumerate(order)]
