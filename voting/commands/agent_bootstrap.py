from __future__ import annotations

from pathlib import Path

import typer

from voting import docs as docs_lib
from voting.commands.common import output
from voting.core.errors import ProjectNotFound
from voting.core.project import Project, find_project
from voting.workflow import phase_state


def _current_or_fresh_project(ctx: typer.Context) -> Project:
    override: Path | None = ctx.obj.project if ctx.obj else None
    try:
        return find_project(override=override)
    except ProjectNotFound:
        if override is not None:
            raise
        return Project(Path.cwd().resolve())


def command(ctx: typer.Context) -> None:
    """Return the agent contract, current state, guide, and next actions."""
    state = phase_state(_current_or_fresh_project(ctx))
    steps = state["recommended_next_steps"]
    data = {
        "role": "Guide the user from election setup through validated results.",
        "rules": [
            "Use voting commands as the source of truth; do not edit .voting JSON directly.",
            "Ask the user for missing decision, option, voter, and ballot information.",
            "Confirm the voting method, ballot type, seats, and tie policy before collecting ballots.",
            "Do not invent voter preferences or silently resolve data errors or substantive ties.",
            "Validate ballots before counting and explain method-comparison assumptions.",
            "Use EDSL authentication only for synthetic or hosted survey workflows.",
            "Run voting agent-bootstrap after material state changes or when the next action is unclear.",
        ],
        "state": state,
        "agent_guide": docs_lib.load_doc("getting-started"),
    }
    human_lines = [
        "Voting agent bootstrap",
        f"Role: {data['role']}",
        f"Current phase: {state['phase'].value}",
        "Next steps:",
        *[f"- {step['label']}: {step['command']}" for step in steps],
    ]
    output(
        ctx,
        "agent-bootstrap",
        data,
        next_steps=[step["command"] for step in steps],
        human_message="\n".join(human_lines),
    )
