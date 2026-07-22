from __future__ import annotations

import typer

from voting.commands.common import ctx_project, output
from voting.workflow import phase_state


def command(ctx: typer.Context) -> None:
    """Show current project phase, counts, and recommended next steps."""
    project = ctx_project(ctx)
    state = phase_state(project)
    output(
        ctx,
        "status",
        state,
        next_steps=[step["command"] for step in state["recommended_next_steps"]],
    )
