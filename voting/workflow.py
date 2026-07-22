from __future__ import annotations

from enum import Enum
from pathlib import Path

from voting.core.project import Project


class Phase(str, Enum):
    INIT = "init"
    SETUP = "setup"
    ELECTIONS = "elections"
    BALLOTING = "balloting"
    COUNTING = "counting"
    DONE = "done"


CHECKLISTS: dict[str, list[str]] = {
    Phase.INIT: [
        "Create a project: `voting init <name>`",
    ],
    Phase.SETUP: [
        "Add options (candidates/proposals): `voting option add <id> <name>`",
        "Add voters: `voting voter add <id> <name>`",
        "Optionally set voter traits for survey generation: `voting voter set-trait <id> <key> <value>`",
    ],
    Phase.ELECTIONS: [
        "Create an election: `voting election add <id> <name> --method <method> --ballot-type <type>`",
        "Add options to the election: `voting election add-option <election_id> <option_id>`",
        "Open the election: `voting election open <election_id>`",
    ],
    Phase.BALLOTING: [
        "Cast ballots directly:  `voting ballot rank|cast|approve|score <election_id> <voter_id> ...`",
        "Or generate a survey:   `voting survey generate <election_id>` → run the script → `voting ballot import`",
        "Validate ballots:       `voting ballot validate <election_id>`",
    ],
    Phase.COUNTING: [
        "Run a counting method: `voting count run <election_id>`",
        "Run multiple methods for comparison: `voting count run <election_id> --method <method>`",
    ],
    Phase.DONE: [
        "Review results: `voting count list` and `voting count show <result_id>`",
        "Run additional methods for comparison: `voting count run <election_id> --method <method>`",
    ],
}

NEXT_STEP_COMMANDS: dict[str, list[dict]] = {
    Phase.INIT: [
        {"label": "Create project", "command": "voting init <name>"},
    ],
    Phase.SETUP: [
        {"label": "Add first option", "command": "voting option add <id> <name>"},
        {"label": "Add first voter", "command": "voting voter add <id> <name>"},
    ],
    Phase.ELECTIONS: [
        {"label": "Create election", "command": "voting election add <id> <name> --method fptp --ballot-type single_choice"},
        {"label": "Browse methods", "command": "voting docs show voting-methods"},
    ],
    Phase.BALLOTING: [
        {"label": "Cast ranked ballot", "command": "voting ballot rank <election_id> <voter_id> <opt1> <opt2>"},
        {"label": "Generate EDSL survey", "command": "voting survey generate <election_id>"},
    ],
    Phase.COUNTING: [
        {"label": "Count with election's default method", "command": "voting count run <election_id>"},
    ],
    Phase.DONE: [
        {"label": "View results", "command": "voting count list"},
        {"label": "Compare another method", "command": "voting count run <election_id> --method <method>"},
    ],
}


def infer_phase(project: Project) -> Phase:
    if not project.path("meta.json").exists():
        return Phase.INIT

    options = list(project.path("options").glob("*.json"))
    voters = list(project.path("voters").glob("*.json"))
    if not options or not voters:
        return Phase.SETUP

    elections_dir = project.path("elections")
    open_elections = []
    all_elections = list(elections_dir.glob("*.json")) if elections_dir.exists() else []
    for ep in all_elections:
        try:
            import json
            data = json.loads(ep.read_text(encoding="utf-8"))
            if data.get("status") == "open":
                open_elections.append(data)
        except Exception:
            pass

    if not open_elections:
        return Phase.ELECTIONS

    ballots = list(project.path("ballots").glob("*.json"))
    if not ballots:
        return Phase.BALLOTING

    results = list(project.path("results").glob("*.json"))
    if not results:
        return Phase.COUNTING

    return Phase.DONE


def _counts(project: Project) -> dict:
    def _count(subdir: str) -> int:
        d = project.path(subdir)
        return len(list(d.glob("*.json"))) if d.exists() else 0

    return {
        "options": _count("options"),
        "voters": _count("voters"),
        "elections": _count("elections"),
        "ballots": _count("ballots"),
        "results": _count("results"),
    }


def phase_state(project: Project) -> dict:
    phase = infer_phase(project)
    counts = _counts(project)
    return {
        "phase": phase,
        "project_exists": project.path("meta.json").exists(),
        "counts": counts,
        "checklist": CHECKLISTS.get(phase, []),
        "recommended_next_steps": NEXT_STEP_COMMANDS.get(phase, []),
    }
