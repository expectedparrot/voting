from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from voting.commands.common import ctx_project, output
from voting.core.errors import UserError
from voting.core.ids import local_iso_now, validate_id
from voting.core.store import append_record, list_records, read_entity, read_json
from voting.core.validate import validate_unique

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("cast")
def cast(
    ctx: typer.Context,
    election_id: str,
    voter_id: str,
    choice: str = typer.Option(..., "--choice"),
) -> None:
    data = _base(ctx, election_id, voter_id, "single_choice")
    data["choice"] = choice
    rid, _ = append_record(ctx_project(ctx), "ballots", [voter_id, election_id], data)
    output(
        ctx,
        "ballot cast",
        {"id": rid, **data},
        human_message=f"Recorded ballot {rid}",
        next_steps=[f"voting ballot validate {election_id}", f"voting count run {election_id}"],
    )


@app.command("rank")
def rank(
    ctx: typer.Context,
    election_id: str,
    voter_id: str,
    option_ids: list[str] = typer.Argument(...),
) -> None:
    ranking = list(option_ids)
    if not ranking:
        raise UserError("Ranking cannot be empty.", hint="Provide option IDs as positional arguments.")
    validate_unique(ranking, "ranked option")
    data = _base(ctx, election_id, voter_id, "ranked")
    data["ranking"] = ranking
    rid, _ = append_record(ctx_project(ctx), "ballots", [voter_id, election_id], data)
    output(
        ctx,
        "ballot rank",
        {"id": rid, **data},
        human_message=f"Recorded ballot {rid}",
        next_steps=[f"voting ballot validate {election_id}", f"voting count run {election_id}"],
    )


@app.command("approve")
def approve(
    ctx: typer.Context,
    election_id: str,
    voter_id: str,
    option: list[str] = typer.Option(..., "--option"),
) -> None:
    if not option:
        raise UserError("At least one --option is required.", hint="Pass --option <id> for each approved option.")
    validate_unique(option, "approved option")
    data = _base(ctx, election_id, voter_id, "approval")
    data["approved"] = option
    rid, _ = append_record(ctx_project(ctx), "ballots", [voter_id, election_id], data)
    output(
        ctx,
        "ballot approve",
        {"id": rid, **data},
        human_message=f"Recorded ballot {rid}",
        next_steps=[f"voting ballot validate {election_id}", f"voting count run {election_id}"],
    )


@app.command("score")
def score(
    ctx: typer.Context,
    election_id: str,
    voter_id: str,
    pairs: list[str] = typer.Argument(...),
) -> None:
    data = _base(ctx, election_id, voter_id, "score")
    data["scores"] = {key: float(value) for key, value in [_split_pair(pair) for pair in pairs]}
    rid, _ = append_record(ctx_project(ctx), "ballots", [voter_id, election_id], data)
    output(
        ctx,
        "ballot score",
        {"id": rid, **data},
        human_message=f"Recorded ballot {rid}",
        next_steps=[f"voting ballot validate {election_id}", f"voting count run {election_id}"],
    )


@app.command("grade")
def grade(
    ctx: typer.Context,
    election_id: str,
    voter_id: str,
    pairs: list[str] = typer.Argument(...),
) -> None:
    data = _base(ctx, election_id, voter_id, "grade")
    data["grades"] = dict(_split_pair(pair) for pair in pairs)
    rid, _ = append_record(ctx_project(ctx), "ballots", [voter_id, election_id], data)
    output(
        ctx,
        "ballot grade",
        {"id": rid, **data},
        human_message=f"Recorded ballot {rid}",
        next_steps=[f"voting ballot validate {election_id}", f"voting count run {election_id}"],
    )


@app.command("allocate")
def allocate(
    ctx: typer.Context,
    election_id: str,
    voter_id: str,
    pairs: list[str] = typer.Argument(...),
) -> None:
    data = _base(ctx, election_id, voter_id, "allocated")
    data["allocations"] = {key: float(value) for key, value in [_split_pair(pair) for pair in pairs]}
    rid, _ = append_record(ctx_project(ctx), "ballots", [voter_id, election_id], data)
    output(
        ctx,
        "ballot allocate",
        {"id": rid, **data},
        human_message=f"Recorded ballot {rid}",
        next_steps=[f"voting ballot validate {election_id}", f"voting count run {election_id}"],
    )


@app.command("list")
def list_cmd(
    ctx: typer.Context,
    election: Optional[str] = typer.Option(None, "--election"),
    voter: Optional[str] = typer.Option(None, "--voter"),
) -> None:
    records = [record for _, record in list_records(ctx_project(ctx), "ballots")]
    if election:
        records = [r for r in records if r.get("election_id") == election]
    if voter:
        records = [r for r in records if r.get("voter_id") == voter]
    output(ctx, "ballot list", {"ballots": records})


@app.command("show")
def show(ctx: typer.Context, ballot_record_id: str) -> None:
    project = ctx_project(ctx)
    output(ctx, "ballot show", read_json(project.path("ballots", f"{ballot_record_id}.json")))


@app.command("validate")
def validate_cmd(ctx: typer.Context, election_id: str) -> None:
    from voting.commands.count import prepare_count

    prepared = prepare_count(ctx_project(ctx), election_id, None)
    output(
        ctx,
        "ballot validate",
        {"valid_ballots": len(prepared["ballots"]), "warnings": prepared["warnings"]},
        next_steps=[f"voting count run {election_id}"],
    )


@app.command("import")
def import_ballots(
    ctx: typer.Context,
    election_id: str = typer.Option(..., "--election", help="Election ID to import ballots into."),
    from_file: Path = typer.Option(..., "--from", help="Path to results file written by a generated survey script."),
) -> None:
    """Import ballots from a file generated by `voting survey generate`."""
    project = ctx_project(ctx)

    if not from_file.exists():
        raise UserError(
            f"Results file not found: {from_file}",
            {"path": str(from_file)},
            hint="Run the generated survey script first, then re-run this command.",
        )

    try:
        results = json.loads(from_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise UserError(f"Invalid JSON in results file: {exc}", {"path": str(from_file)}) from exc

    file_election_id = results.get("election_id")
    if file_election_id and file_election_id != election_id:
        raise UserError(
            f"Results file is for election '{file_election_id}', not '{election_id}'.",
            {"file_election_id": file_election_id, "requested_election_id": election_id},
            hint="Check --election matches the election_id in the results file.",
        )

    ballot_type = results.get("ballot_type")
    rows = results.get("rows", [])

    election = read_entity(project, "elections", election_id)
    if election.get("status") not in {"open", "draft"}:
        raise UserError(
            "Election is not open for ballots.",
            {"election_id": election_id, "status": election.get("status")},
            hint=f"Run `voting election open {election_id}` first.",
        )

    voters_by_id = {}
    try:
        from voting.core.store import list_entities
        voters_by_id = {v["id"]: v for v in list_entities(project, "voters")}
    except Exception:
        pass

    from voting.core.ballots import latest_ballots as _latest_ballots
    existing_voter_ids = {b["voter_id"] for b in _latest_ballots(project, election_id)}

    cast_count = 0
    skipped: list[dict] = []
    warnings_list: list[dict] = []

    for row in rows:
        voter_id = row.get("voter_id")
        if not voter_id:
            skipped.append({"row": row, "reason": "missing voter_id"})
            continue

        answer = row.get("answer", {})
        voter = voters_by_id.get(voter_id)
        weight = float(voter.get("weight", 1.0)) if voter else 1.0
        if voter is None:
            warnings_list.append({"code": "unregistered_voter", "voter_id": voter_id})
        if voter_id in existing_voter_ids:
            warnings_list.append({"code": "ballot_overwritten", "voter_id": voter_id, "message": f"Existing ballot for voter '{voter_id}' replaced by this import."})

        record: dict = {
            "election_id": election_id,
            "voter_id": voter_id,
            "ballot_type": ballot_type,
            "recorded_at": local_iso_now(),
            "weight": weight,
            "metadata": {"source": "import", "import_file": str(from_file)},
        }

        try:
            if ballot_type == "ranked":
                ranking = answer.get("ranking", [])
                if not ranking:
                    skipped.append({"voter_id": voter_id, "reason": "empty ranking"})
                    continue
                record["ranking"] = ranking
            elif ballot_type == "single_choice":
                choice = answer.get("choice")
                if not choice:
                    skipped.append({"voter_id": voter_id, "reason": "missing choice"})
                    continue
                record["choice"] = choice
            elif ballot_type == "approval":
                approved = answer.get("approved", [])
                if not approved:
                    skipped.append({"voter_id": voter_id, "reason": "empty approved list"})
                    continue
                record["approved"] = approved
            elif ballot_type == "score":
                scores = answer.get("scores", {})
                if not scores:
                    skipped.append({"voter_id": voter_id, "reason": "empty scores"})
                    continue
                record["scores"] = {k: float(v) for k, v in scores.items()}
            elif ballot_type == "grade":
                grades = answer.get("grades", {})
                if not grades:
                    skipped.append({"voter_id": voter_id, "reason": "empty grades"})
                    continue
                record["grades"] = grades
            else:
                skipped.append({"voter_id": voter_id, "reason": f"unsupported ballot_type: {ballot_type}"})
                continue

            append_record(project, "ballots", [voter_id, election_id], record)
            cast_count += 1
        except Exception as exc:
            skipped.append({"voter_id": voter_id, "reason": str(exc)})

    output(
        ctx,
        "ballot import",
        {
            "election_id": election_id,
            "cast": cast_count,
            "skipped": len(skipped),
            "skipped_detail": skipped,
            "source_file": str(from_file),
        },
        warnings=warnings_list or None,
        next_steps=[f"voting count run {election_id}"],
    )


def _base(ctx: typer.Context, election_id: str, voter_id: str, ballot_type: str) -> dict:
    project = ctx_project(ctx)
    election = read_entity(project, "elections", election_id)
    if election.get("status") not in {"open", "draft"}:
        raise UserError(
            "Election is not open for ballots.",
            {"election_id": election_id, "status": election.get("status")},
            hint=f"Run `voting election open {election_id}` first.",
        )
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
        raise UserError("Expected KEY=VALUE.", {"value": pair}, hint="Format: option_id=score, e.g. alice=8")
    key, value = pair.split("=", 1)
    return key, value
