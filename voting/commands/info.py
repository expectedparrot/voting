from __future__ import annotations

import typer

from voting.commands.common import ctx_project, output
from voting.core.store import list_entities, read_json


def command(ctx: typer.Context) -> None:
    project = ctx_project(ctx)
    data = {
        "project": str(project.root),
        "data_dir": str(project.data_dir),
        "meta": read_json(project.path("meta.json")),
        "counts": {
            "elections": len(list_entities(project, "elections")),
            "options": len(list_entities(project, "options")),
            "voters": len(list_entities(project, "voters")),
        },
    }
    output(ctx, "info", data, next_steps=["voting status"])
