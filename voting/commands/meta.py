"""Discoverability commands: version, capabilities, next."""
from __future__ import annotations

from pathlib import Path

import typer

from voting.commands.common import ctx_project, output
from voting.output import ENVELOPE_SCHEMA_VERSION


def version_command(ctx: typer.Context) -> None:
    """Report the installed build and envelope schema version."""
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as package_version

    try:
        installed = package_version("voting")
    except PackageNotFoundError:
        installed = "unknown"
    output(
        ctx,
        "version",
        {
            "version": installed,
            "package_path": str(Path(__file__).resolve().parents[1]),
            "envelope_schema_version": ENVELOPE_SCHEMA_VERSION,
        },
        human_message=f"voting {installed} (envelope schema {ENVELOPE_SCHEMA_VERSION})",
    )


def capabilities_command(ctx: typer.Context) -> None:
    """Describe the agent-facing output contract and external-action surface."""
    output(
        ctx,
        "capabilities",
        {
            "envelope_schema_version": ENVELOPE_SCHEMA_VERSION,
            "output_contract": (
                "Every command prints one JSON envelope "
                "{schema_version, command, status, argv, data, warnings, errors, next_steps} "
                "to stdout by default; --human is an opt-in presentation mode."
            ),
            "execution_boundary": (
                "voting never executes model calls. `survey generate` writes elicitation "
                "artifacts that the user runs externally; counting and analysis are local."
            ),
            "external_service_actions": {
                "survey publish": "Creates a hosted Humanize survey via the ep CLI (outward-facing).",
                "survey email": "Sends invitation emails to configured voters via the ep CLI (outward-facing).",
                "survey responses": "Downloads Humanize responses via the ep CLI (network read).",
            },
            "workflow_commands": ["voting status", "voting next", "voting docs list"],
        },
    )


def next_command(ctx: typer.Context) -> None:
    """Return the single highest-priority next action from project state."""
    from voting.core.errors import ProjectNotFound
    from voting.workflow import phase_state

    try:
        project = ctx_project(ctx)
    except ProjectNotFound:
        output(
            ctx,
            "next",
            {"phase": "init", "recommendation": "voting init <name>",
             "reason": "No voting project found here."},
            next_steps=["voting init <name>"],
        )
        return
    state = phase_state(project)
    steps = state["recommended_next_steps"]
    top = steps[0] if steps else None
    output(
        ctx,
        "next",
        {
            "phase": state["phase"],
            "counts": state["counts"],
            "recommendation": top["command"] if top else None,
            "reason": top["label"] if top else None,
            "checklist": state["checklist"],
        },
        next_steps=[step["command"] for step in steps],
    )
