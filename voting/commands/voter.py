from __future__ import annotations

import typer

from voting.commands.common import ctx_project, output, parse_json_value
from voting.core.ids import local_iso_now, validate_id
from voting.core.store import list_entities, read_entity, write_entity, write_json

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("add")
def add(
    ctx: typer.Context,
    voter_id: str,
    name: str,
    weight: float = typer.Option(1.0, "--weight"),
) -> None:
    validate_id(voter_id, "voter id")
    data = {
        "id": voter_id,
        "name": name,
        "added_at": local_iso_now(),
        "weight": weight,
        "eligible": True,
        "traits": {},
    }
    write_entity(ctx_project(ctx), "voters", voter_id, data)
    output(
        ctx,
        "voter add",
        data,
        human_message=f"Added voter {voter_id}",
        next_steps=[
            "voting voter set-trait <id> <key> <json_value>",
            "voting election add <id> <name>",
        ],
    )


@app.command("list")
def list_cmd(ctx: typer.Context) -> None:
    output(ctx, "voter list", {"voters": list_entities(ctx_project(ctx), "voters")})


@app.command("show")
def show(ctx: typer.Context, voter_id: str) -> None:
    output(ctx, "voter show", read_entity(ctx_project(ctx), "voters", voter_id))


@app.command("set-trait")
def set_trait(ctx: typer.Context, voter_id: str, key: str, json_value: str) -> None:
    project = ctx_project(ctx)
    data = read_entity(project, "voters", voter_id)
    data.setdefault("traits", {})[key] = parse_json_value(json_value)
    write_json(project.path("voters", f"{voter_id}.json"), data)
    output(ctx, "voter set-trait", data)


@app.command("set-eligible")
def set_eligible(ctx: typer.Context, voter_id: str, eligible: bool) -> None:
    project = ctx_project(ctx)
    data = read_entity(project, "voters", voter_id)
    data["eligible"] = eligible
    write_json(project.path("voters", f"{voter_id}.json"), data)
    output(ctx, "voter set-eligible", data)
