from __future__ import annotations

from pathlib import Path

import typer

from voting.commands.common import output
from voting.core.ids import local_iso_now, validate_id
from voting.core.project import create_project
from voting.core.store import write_json


def command(
    ctx: typer.Context,
    name: str = typer.Argument(...),
    description: str = typer.Option("", "--description"),
) -> None:
    project_id = validate_id(Path(name).name, "project id")
    project = create_project(Path(name))
    meta = {
        "id": project_id,
        "title": project_id.replace("_", " ").title(),
        "description": description,
        "created_at": local_iso_now(),
        "settings": {"default_tie_policy": "lexicographic", "allow_unregistered_voters": False},
    }
    write_json(project.path("meta.json"), meta)
    output(
        ctx,
        "init",
        {"project": str(project.root), "data_dir": str(project.data_dir), "meta": meta},
        human_message=f"Created {project.data_dir}",
        next_steps=[
            f"voting option add <id> <name>",
            f"voting voter add <id> <name>",
            f"voting election add <id> <name>",
        ],
    )
