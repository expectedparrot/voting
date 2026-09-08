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
        "Create an election: `voting election add <id> <name> --ballot-type <type>`",
        "Add options to the election: `voting election add-option <election_id> <option_id>`",
        "Open the election: `voting election open <election_id>`",
    ],
    Phase.BALLOTING: [
        "Cast ballots directly:  `voting ballot rank|cast|approve|score <election_id> <voter_id> ...`",
        "Or generate a survey:   `voting survey generate <election_id>` → `ep run` the .jobs.ep → `voting ballot import --from-results`",
        "Validate ballots:       `voting ballot validate <election_id>`",
    ],
    Phase.COUNTING: [
        "Run a counting method: `voting count run <election_id> --method <method>`",
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
        {"label": "Create election", "command": "voting election add <id> <name> --ballot-type single_choice"},
        {"label": "Browse methods", "command": "voting docs show voting-methods"},
    ],
    Phase.BALLOTING: [
        {"label": "Cast ranked ballot", "command": "voting ballot rank <election_id> <voter_id> <opt1> <opt2>"},
        {"label": "Generate EDSL survey", "command": "voting survey generate <election_id>"},
    ],
    Phase.COUNTING: [
        {"label": "Count the ballots", "command": "voting count run <election_id> --method <method>"},
    ],
    Phase.DONE: [
        {"label": "View results", "command": "voting count list"},
        {"label": "Compare another method", "command": "voting count run <election_id> --method <method>"},
    ],
}


def infer_phase(project: Project) -> Phase:
    return phase_state(project)["phase"]


def _counts(project: Project) -> dict:
    return {name: len(list(project.path(name).glob("*.json")))
            for name in ("options", "voters", "elections", "ballots", "results")}


def _election_state(project: Project, election: dict, results: list[dict]) -> dict:
    from voting.commands.count import prepare_count
    from voting.core.ballots import latest_ballots
    from voting.core.errors import VotingError
    from voting.core.provenance import input_fingerprint
    from voting.core.store import read_entity
    from voting.core.validate import eligible_options

    eid = election["id"]
    ballots = latest_ballots(project, eid)
    latest_results = {}
    for result in results:
        if result.get("election_id") == eid:
            latest_results[result["method"]] = result
    fingerprint = input_fingerprint(project, election)
    current = [r["id"] for r in latest_results.values()
               if r.get("provenance", {}).get("input_fingerprint") == fingerprint]
    stale = [r["id"] for r in latest_results.values() if r["id"] not in current]
    options = eligible_options(election, [read_entity(project, "options", oid) for oid in election.get("options", [])])
    invalid = []
    if not options:
        phase = Phase.ELECTIONS
        step = {"label": f"Add eligible options to {eid}",
                "command": f"voting election add-option {eid} <option_id>"}
    elif election.get("seats", 1) > len(options):
        phase = Phase.ELECTIONS
        step = {"label": f"Reduce seats or add eligible options to {eid}",
                "command": f"voting election configure {eid} --seats {len(options)}"}
    else:
        try:
            prepared = prepare_count(project, eid, None)
            invalid = prepared["warnings"]
        except VotingError as exc:
            return {"election_id": eid, "phase": Phase.ELECTIONS, "status": election.get("status"),
                    "error": str(exc), "recommended_next_steps": [
                        {"label": f"Review settings for {eid}", "command": f"voting election show {eid}"}]}
        if current:
            phase = Phase.DONE
            step = {"label": f"Review current results for {eid}", "command": f"voting count show {current[-1]}"}
        elif prepared["ballots"] or election.get("status") == "closed":
            phase = Phase.COUNTING
            step = {"label": f"Recount changed inputs for {eid}" if stale else f"Count ballots for {eid}",
                    "command": f"voting count compare {eid}"}
        elif election.get("status") == "draft":
            phase = Phase.ELECTIONS
            step = {"label": f"Open {eid} for ballots", "command": f"voting election open {eid}"}
        else:
            phase = Phase.BALLOTING
            bt = election.get("ballot_type", "single_choice")
            cast = {
                "single_choice": f"cast {eid} <voter_id> --choice <option_id>",
                "ranked": f"rank {eid} <voter_id> <opt1> <opt2>",
                "approval": f"approve {eid} <voter_id> --option <option_id>",
                "score": f"score {eid} <voter_id> <option_id>=5",
                "grade": f"grade {eid} <voter_id> <option_id>=" + (election.get("settings", {}).get("grade_scale") or ["good"])[-1],
                "allocated": f"allocate {eid} <voter_id> <option_id>=10",
            }[bt]
            step = {"label": f"Collect {bt} ballots for {eid}", "command": f"voting ballot {cast}"}
    steps = [step]
    if invalid:
        steps.insert(0, {"label": f"Review {len(invalid)} invalid ballots for {eid}",
                         "command": f"voting ballot validate {eid}"})
    return {"election_id": eid, "phase": phase, "status": election.get("status"),
            "ballots": len(ballots), "invalid_ballots": len(invalid),
            "current_result_ids": current, "stale_result_ids": stale,
            "recommended_next_steps": steps}


def phase_state(project: Project) -> dict:
    from voting.core.store import list_entities, list_records

    exists = project.path("meta.json").exists()
    counts = _counts(project)
    states = []
    if not exists:
        phase = Phase.INIT
        steps = NEXT_STEP_COMMANDS[phase]
    elif not counts["options"] or (not counts["elections"] and not counts["voters"]):
        phase = Phase.SETUP
        steps = [step for step, missing in zip(NEXT_STEP_COMMANDS[phase],
                 (not counts["options"], not counts["voters"])) if missing]
    elif not counts["elections"]:
        phase = Phase.ELECTIONS
        steps = NEXT_STEP_COMMANDS[phase]
    else:
        results = [record for _, record in list_records(project, "results")]
        states = [_election_state(project, e, results) for e in list_entities(project, "elections")]
        priority = {Phase.ELECTIONS: 0, Phase.BALLOTING: 1, Phase.COUNTING: 2, Phase.DONE: 3}
        states.sort(key=lambda state: (priority[state["phase"]], state["election_id"]))
        phase = states[0]["phase"]
        steps = [step for state in states if state["phase"] != Phase.DONE
                 for step in state["recommended_next_steps"]]
        if not steps:
            steps = [step for state in states for step in state["recommended_next_steps"]]
    return {"phase": phase, "project_exists": exists, "counts": counts,
            "elections": states, "checklist": CHECKLISTS.get(phase, []),
            "recommended_next_steps": steps}
