from __future__ import annotations

import typer

from voting.commands.common import ctx_project, output
from voting.core.errors import UserError
from voting.core.ids import local_iso_now, validate_id
from voting.core.store import list_entities, read_entity, write_entity, write_json
from voting.core.validate import validate_settings

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("add")
def add(
    ctx: typer.Context,
    election_id: str,
    name: str,
    ballot_type: str = typer.Option("single_choice", "--ballot-type"),
    seats: int = typer.Option(1, "--seats"),
    tie_policy: str = typer.Option("lexicographic", "--tie-policy"),
    budget: float | None = typer.Option(None, "--budget", help="Maximum points per allocated ballot."),
    grade: list[str] | None = typer.Option(None, "--grade", help="Grade label; repeat from worst to best."),
    approval_limit: int | None = typer.Option(None, "--approval-limit", help="Maximum approved options per ballot."),
    description: str = "",
) -> None:
    validate_id(election_id, "election id")
    if seats < 1:
        raise UserError("Seats must be at least 1.", {"seats": seats}, hint="Use --seats with a positive integer.")
    data = {
        "id": election_id,
        "name": name,
        "description": description,
        "created_at": local_iso_now(),
        "ballot_type": ballot_type,
        "seats": seats,
        "status": "draft",
        "options": [],
        "settings": {"tie_policy": tie_policy, "quota": "droop"},
    }
    data["settings"].update({k: v for k, v in {
        "budget": budget, "grade_scale": grade, "approval_limit": approval_limit,
    }.items() if v is not None})
    validate_settings(data)
    write_entity(ctx_project(ctx), "elections", election_id, data)
    output(
        ctx,
        "election add",
        data,
        human_message=f"Added election {election_id}",
        next_steps=[
            f"voting election add-option {election_id} <option_id>",
            f"voting election open {election_id}",
        ],
    )


@app.command("configure")
def configure(
    ctx: typer.Context,
    election_id: str,
    seats: int | None = typer.Option(None, "--seats"),
    tie_policy: str | None = typer.Option(None, "--tie-policy"),
    budget: float | None = typer.Option(None, "--budget"),
    grade: list[str] | None = typer.Option(None, "--grade", help="Repeat labels from worst to best."),
    approval_limit: int | None = typer.Option(None, "--approval-limit"),
    clear_budget: bool = typer.Option(False, "--clear-budget"),
    clear_approval_limit: bool = typer.Option(False, "--clear-approval-limit"),
) -> None:
    """Update seats, budget, grade scale, or approval limit; existing ballots are revalidated at count time."""
    project = ctx_project(ctx)
    data = read_entity(project, "elections", election_id)
    if (clear_budget and budget is not None) or (clear_approval_limit and approval_limit is not None):
        raise UserError("Cannot set and clear the same setting in one command.")
    if seats is not None:
        data["seats"] = seats
    settings = data.setdefault("settings", {})
    settings.update({k: v for k, v in {
        "tie_policy": tie_policy, "budget": budget, "grade_scale": grade,
        "approval_limit": approval_limit,
    }.items() if v is not None})
    if clear_budget:
        settings.pop("budget", None)
    if clear_approval_limit:
        settings.pop("approval_limit", None)
    validate_settings(data)
    write_entity(project, "elections", election_id, data, overwrite=True)
    output(ctx, "election configure", data, next_steps=[f"voting ballot validate {election_id}"])


@app.command("list")
def list_cmd(ctx: typer.Context) -> None:
    output(ctx, "election list", {"elections": list_entities(ctx_project(ctx), "elections")})


@app.command("show")
def show(ctx: typer.Context, election_id: str) -> None:
    project = ctx_project(ctx)
    election = read_entity(project, "elections", election_id)

    def _panel():
        from voting.render import election_panel

        names = {}
        for oid in election.get("options", []):
            try:
                names[oid] = read_entity(project, "options", oid).get("name", "")
            except Exception:
                pass
        return election_panel(election, names)

    output(ctx, "election show", election, human_renderable=_panel)


@app.command("open")
def open_cmd(ctx: typer.Context, election_id: str) -> None:
    data = _set_status(ctx, election_id, "open")
    output(
        ctx,
        "election open",
        data,
        human_message=f"Opened {election_id}",
        next_steps=[
            "voting next",
            f"voting election show {election_id}",
        ],
    )


@app.command("close")
def close(ctx: typer.Context, election_id: str) -> None:
    data = _set_status(ctx, election_id, "closed")
    output(
        ctx,
        "election close",
        data,
        human_message=f"Closed {election_id}",
        next_steps=[f"voting count run {election_id} --method <method>"],
    )


@app.command("add-option")
def add_option(ctx: typer.Context, election_id: str, option_id: str) -> None:
    project = ctx_project(ctx)
    read_entity(project, "options", option_id)
    data = read_entity(project, "elections", election_id)
    if option_id not in data["options"]:
        data["options"].append(option_id)
    write_json(project.path("elections", f"{election_id}.json"), data)
    output(
        ctx,
        "election add-option",
        data,
        next_steps=[f"voting election open {election_id}"],
    )


@app.command("remove-option")
def remove_option(ctx: typer.Context, election_id: str, option_id: str) -> None:
    project = ctx_project(ctx)
    data = read_entity(project, "elections", election_id)
    data["options"] = [item for item in data["options"] if item != option_id]
    write_json(project.path("elections", f"{election_id}.json"), data)
    output(ctx, "election remove-option", data)


def _set_status(ctx: typer.Context, election_id: str, status: str) -> dict:
    project = ctx_project(ctx)
    data = read_entity(project, "elections", election_id)
    data["status"] = status
    data[f"{status}_at"] = local_iso_now()
    write_json(project.path("elections", f"{election_id}.json"), data)
    return data
