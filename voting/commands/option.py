from __future__ import annotations

import typer

from voting.commands.common import ctx_project, output
from voting.core.errors import UserError
from voting.core.ids import local_iso_now, validate_id
from voting.core.store import list_entities, read_entity, write_entity, write_json

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("add")
def add(ctx: typer.Context, option_id: str, name: str, type_: str = typer.Option("candidate", "--type"), description: str = "") -> None:
    if type_ not in {"candidate", "proposal", "reference", "write_in"}:
        raise UserError("Option type must be candidate, proposal, reference, or write_in.", {"type": type_})
    validate_id(option_id, "option id")
    data = {
        "id": option_id,
        "name": name,
        "type": type_,
        "description": description,
        "added_at": local_iso_now(),
        "eligible": True,
        "metadata": {},
    }
    write_entity(ctx_project(ctx), "options", option_id, data)
    output(ctx, data, human_message=f"Added option {option_id}")


@app.command("list")
def list_cmd(ctx: typer.Context, type_: str = typer.Option("all", "--type")) -> None:
    items = list_entities(ctx_project(ctx), "options")
    if type_ != "all":
        items = [item for item in items if item.get("type") == type_]
    output(ctx, items)


@app.command("show")
def show(ctx: typer.Context, option_id: str) -> None:
    output(ctx, read_entity(ctx_project(ctx), "options", option_id))


@app.command("set-eligible")
def set_eligible(ctx: typer.Context, option_id: str, eligible: bool) -> None:
    project = ctx_project(ctx)
    data = read_entity(project, "options", option_id)
    data["eligible"] = eligible
    write_json(project.path("options", f"{option_id}.json"), data)
    output(ctx, data)
