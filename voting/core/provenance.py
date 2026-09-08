"""Small input fingerprints for detecting stale counts, without copying projects."""
from __future__ import annotations

import hashlib
import json
from importlib.metadata import PackageNotFoundError, version

from .ballots import latest_ballots
from .project import Project
from .store import list_entities, read_entity


def input_fingerprint(project: Project, election: dict) -> str:
    options = [read_entity(project, "options", oid) for oid in election.get("options", [])]
    ballots = latest_ballots(project, election["id"])
    voter_ids = {b.get("voter_id") for b in ballots}
    payload = {
        "election": {k: election.get(k) for k in ("ballot_type", "seats", "settings", "options")},
        "options": [{k: o.get(k) for k in ("id", "eligible", "type")} for o in options],
        "voters": [{k: v.get(k) for k in ("id", "eligible")} for v in list_entities(project, "voters")
                   if v["id"] in voter_ids],
        "ballots": ballots,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def package_version() -> str:
    try:
        return version("voting")
    except PackageNotFoundError:
        return "unknown"
