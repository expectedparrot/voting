from __future__ import annotations

import typer

from voting.commands.common import ctx_project, output
from voting.core.errors import UserError
from voting.core.ids import local_iso_now, validate_id
from voting.core.store import append_record, list_records, read_entity, read_json
from voting.core.validate import validate_unique

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("cast")
def cast(ctx: typer.Context, election_id: str, voter_id: str, choice: str = typer.Option(..., "--choice")) -> None:
    data = _base(ctx, election_id, voter_id, "single_choice")
    data["choice"] = choice
    rid, _ = append_record(ctx_project(ctx), "ballots", [voter_id, election_id], data)
    output(ctx, {"id": rid, **data}, human_message=f"Recorded ballot {rid}")


@app.command("rank")
def rank(ctx: typer.Context, election_id: str, voter_id: str, option_ids: list[str] = typer.Argument(...)) -> None:
    ranking = list(option_ids)
    if not ranking:
        raise UserError("Ranking cannot be empty.")
    validate_unique(ranking, "ranked option")
    data = _base(ctx, election_id, voter_id, "ranked")
    data["ranking"] = ranking
    rid, _ = append_record(ctx_project(ctx), "ballots", [voter_id, election_id], data)
    output(ctx, {"id": rid, **data}, human_message=f"Recorded ballot {rid}")


@app.command("approve")
def approve(ctx: typer.Context, election_id: str, voter_id: str, option: list[str] = typer.Option(..., "--option")) -> None:
    if not option:
        raise UserError("At least one --option is required.")
    validate_unique(option, "approved option")
    data = _base(ctx, election_id, voter_id, "approval")
    data["approved"] = option
    rid, _ = append_record(ctx_project(ctx), "ballots", [voter_id, election_id], data)
    output(ctx, {"id": rid, **data}, human_message=f"Recorded ballot {rid}")


@app.command("score")
def score(ctx: typer.Context, election_id: str, voter_id: str, pairs: list[str] = typer.Argument(...)) -> None:
    data = _base(ctx, election_id, voter_id, "score")
    data["scores"] = {key: float(value) for key, value in [_split_pair(pair) for pair in pairs]}
    rid, _ = append_record(ctx_project(ctx), "ballots", [voter_id, election_id], data)
    output(ctx, {"id": rid, **data}, human_message=f"Recorded ballot {rid}")


@app.command("grade")
def grade(ctx: typer.Context, election_id: str, voter_id: str, pairs: list[str] = typer.Argument(...)) -> None:
    data = _base(ctx, election_id, voter_id, "grade")
    data["grades"] = dict(_split_pair(pair) for pair in pairs)
    rid, _ = append_record(ctx_project(ctx), "ballots", [voter_id, election_id], data)
    output(ctx, {"id": rid, **data}, human_message=f"Recorded ballot {rid}")


@app.command("allocate")
def allocate(ctx: typer.Context, election_id: str, voter_id: str, pairs: list[str] = typer.Argument(...)) -> None:
    data = _base(ctx, election_id, voter_id, "allocated")
    data["allocations"] = {key: float(value) for key, value in [_split_pair(pair) for pair in pairs]}
    rid, _ = append_record(ctx_project(ctx), "ballots", [voter_id, election_id], data)
    output(ctx, {"id": rid, **data}, human_message=f"Recorded ballot {rid}")


@app.command("list")
def list_cmd(ctx: typer.Context, election: str | None = typer.Option(None, "--election"), voter: str | None = typer.Option(None, "--voter")) -> None:
    records = [record for _, record in list_records(ctx_project(ctx), "ballots")]
    if election:
        records = [record for record in records if record.get("election_id") == election]
    if voter:
        records = [record for record in records if record.get("voter_id") == voter]
    output(ctx, records)


@app.command("show")
def show(ctx: typer.Context, ballot_record_id: str) -> None:
    project = ctx_project(ctx)
    output(ctx, read_json(project.path("ballots", f"{ballot_record_id}.json")))


@app.command("validate")
def validate_cmd(ctx: typer.Context, election_id: str) -> None:
    from voting.commands.count import prepare_count

    prepared = prepare_count(ctx_project(ctx), election_id, None)
    output(ctx, {"valid_ballots": len(prepared["ballots"]), "warnings": prepared["warnings"]})


def _base(ctx: typer.Context, election_id: str, voter_id: str, ballot_type: str) -> dict:
    project = ctx_project(ctx)
    election = read_entity(project, "elections", election_id)
    if election.get("status") not in {"open", "draft"}:
        raise UserError("Election is not open for ballots.", {"election_id": election_id, "status": election.get("status")})
    voter = read_entity(project, "voters", voter_id)
    validate_id(election_id, "election id")
    validate_id(voter_id, "voter id")
    return {
        "election_id": election_id,
        "voter_id": voter_id,
        "ballot_type": ballot_type,
        "recorded_at": local_iso_now(),
        "weight": float(voter.get("weight", 1.0)),
        "metadata": {},
    }


def _split_pair(pair: str) -> tuple[str, str]:
    if "=" not in pair:
        raise UserError("Expected KEY=VALUE.", {"value": pair})
    key, value = pair.split("=", 1)
    return key, value
