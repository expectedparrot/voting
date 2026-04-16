from __future__ import annotations

from .project import Project
from .store import list_records


def latest_ballots(project: Project, election_id: str) -> list[dict]:
    latest: dict[str, tuple[str, dict]] = {}
    for rid, ballot in list_records(project, "ballots"):
        if ballot.get("election_id") != election_id:
            continue
        voter_id = ballot.get("voter_id")
        marker = (ballot.get("recorded_at") or "", rid)
        previous = latest.get(voter_id)
        if previous is None or marker > (previous[1].get("recorded_at") or "", previous[0]):
            latest[voter_id] = (rid, ballot)
    return [ballot for _, ballot in sorted(latest.values(), key=lambda item: item[0])]


def first_active_choice(ranking: list[str], active: set[str]) -> str | None:
    for option_id in ranking:
        if option_id in active:
            return option_id
    return None
