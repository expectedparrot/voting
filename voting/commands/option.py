from __future__ import annotations

import json
from pathlib import Path

import typer

from voting.commands.common import ctx_project, output
from voting.core.errors import UserError
from voting.core.ids import local_iso_now, validate_id
from voting.core.store import list_entities, read_entity, write_entity, write_json

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("add")
def add(
    ctx: typer.Context,
    option_id: str,
    name: str,
    type_: str = typer.Option("candidate", "--type"),
    description: str = "",
) -> None:
    if type_ not in {"candidate", "proposal", "reference", "write_in"}:
        raise UserError(
            "Option type must be candidate, proposal, reference, or write_in.",
            {"type": type_},
            hint="Valid types: candidate, proposal, reference, write_in.",
        )
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
    output(
        ctx,
        "option add",
        data,
        human_message=f"Added option {option_id}",
        next_steps=["voting voter add <id> <name>", "voting election add-option <election_id> <option_id>"],
    )


@app.command("list")
def list_cmd(ctx: typer.Context, type_: str = typer.Option("all", "--type")) -> None:
    items = list_entities(ctx_project(ctx), "options")
    if type_ != "all":
        items = [item for item in items if item.get("type") == type_]

    def _table():
        from voting.render import options_table

        return options_table(items)

    output(ctx, "option list", {"options": items}, human_renderable=_table)


@app.command("import")
def import_options(
    ctx: typer.Context,
    from_file: Path = typer.Option(..., "--from", help="JSON file: a list of {id, name, type?, description?} objects (or {\"options\": [...]})."),
    election_id: str = typer.Option(None, "--election", help="Also attach every imported option to this election."),
) -> None:
    """Import many options from a JSON file, optionally attaching them to an election."""
    project = ctx_project(ctx)
    if not from_file.exists():
        raise UserError(f"Options file not found: {from_file}", {"path": str(from_file)})
    try:
        raw = json.loads(from_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise UserError(f"Invalid JSON in options file: {exc}", {"path": str(from_file)}) from exc
    entries = raw.get("options") if isinstance(raw, dict) else raw
    if not isinstance(entries, list) or not entries:
        raise UserError(
            "Options file must contain a non-empty list of options.",
            {"path": str(from_file)},
            hint='Expected [{"id": "alice", "name": "Alice"}, ...] or {"options": [...]}.',
        )

    election = read_entity(project, "elections", election_id) if election_id else None
    existing = {item["id"] for item in list_entities(project, "options")}

    # Validate everything before writing anything, so a bad row can't
    # leave a half-imported file behind.
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or not entry.get("id") or not entry.get("name"):
            raise UserError(
                f"Option entry {index} must be an object with 'id' and 'name'.",
                {"entry": entry},
            )
        validate_id(entry["id"], "option id")
        if entry["id"] in seen:
            raise UserError(f"Duplicate option id in file: {entry['id']}")
        if entry["id"] in existing:
            raise UserError(
                f"Option already exists: {entry['id']}",
                hint="Remove it from the file or use a different id.",
            )
        entry_type = entry.get("type", "candidate")
        if entry_type not in {"candidate", "proposal", "reference", "write_in"}:
            raise UserError(
                f"Option entry {index} has invalid type '{entry_type}'.",
                hint="Valid types: candidate, proposal, reference, write_in.",
            )
        seen.add(entry["id"])

    imported = []
    for entry in entries:
        data = {
            "id": entry["id"],
            "name": entry["name"],
            "type": entry.get("type", "candidate"),
            "description": entry.get("description", ""),
            "added_at": local_iso_now(),
            "eligible": True,
            "metadata": {"source": f"option import {from_file.name}"},
        }
        write_entity(project, "options", entry["id"], data)
        imported.append(data)

    attached = []
    if election is not None:
        election_options = election.get("options", [])
        for entry in entries:
            if entry["id"] not in election_options:
                election_options.append(entry["id"])
                attached.append(entry["id"])
        election["options"] = election_options
        write_entity(project, "elections", election_id, election, overwrite=True)

    next_steps = (
        [f"voting election open {election_id}", f"voting --human election show {election_id}"]
        if election_id
        else ["voting election add <id> <name> --method <method>", "voting election add-option <election_id> <option_id>"]
    )
    output(
        ctx,
        "option import",
        {
            "imported": len(imported),
            "options": [{"id": item["id"], "name": item["name"]} for item in imported],
            "election_id": election_id,
            "attached": attached,
        },
        human_message=f"Imported {len(imported)} options" + (f" and attached them to {election_id}" if election_id else ""),
        next_steps=next_steps,
    )


@app.command("show")
def show(ctx: typer.Context, option_id: str) -> None:
    output(ctx, "option show", read_entity(ctx_project(ctx), "options", option_id))


@app.command("set-eligible")
def set_eligible(ctx: typer.Context, option_id: str, eligible: bool) -> None:
    project = ctx_project(ctx)
    data = read_entity(project, "options", option_id)
    data["eligible"] = eligible
    write_json(project.path("options", f"{option_id}.json"), data)
    output(ctx, "option set-eligible", data)
