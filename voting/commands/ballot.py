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
        next_steps=[f"voting ballot validate {election_id}", f"voting count run {election_id} --method <method>"],
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
        next_steps=[f"voting ballot validate {election_id}", f"voting count run {election_id} --method <method>"],
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
        next_steps=[f"voting ballot validate {election_id}", f"voting count run {election_id} --method <method>"],
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
        next_steps=[f"voting ballot validate {election_id}", f"voting count run {election_id} --method <method>"],
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
        next_steps=[f"voting ballot validate {election_id}", f"voting count run {election_id} --method <method>"],
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
        next_steps=[f"voting ballot validate {election_id}", f"voting count run {election_id} --method <method>"],
    )


@app.command("list")
def list_cmd(
    ctx: typer.Context,
    election: Optional[str] = typer.Option(None, "--election"),
    voter: Optional[str] = typer.Option(None, "--voter"),
    latest: bool = typer.Option(False, "--latest", help="Show only each voter's latest ballot (the ones a count would use) instead of the full append-only record."),
) -> None:
    project = ctx_project(ctx)
    if latest:
        if not election:
            raise UserError(
                "--latest requires --election.",
                hint="Latest-ballot resolution is per election; pass --election <id>.",
            )
        from voting.core.ballots import latest_ballots

        records = latest_ballots(project, election)
    else:
        records = [record for _, record in list_records(project, "ballots")]
        if election:
            records = [r for r in records if r.get("election_id") == election]
    if voter:
        records = [r for r in records if r.get("voter_id") == voter]

    def _table():
        from voting.render import ballots_table

        return ballots_table(records)

    output(ctx, "ballot list", {"ballots": records}, human_renderable=_table)


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
        next_steps=[f"voting count run {election_id} --method <method>"],
    )


def _rows_from_edsl_results(results_dict: dict, election: dict, options: list[dict]) -> tuple[list[dict], list[dict]]:
    """Convert EDSL Results rows into import rows, mapping option labels to ids.

    Fail-closed: a label that matches no option name or id itemizes the row
    instead of guessing.
    """
    label_to_id: dict[str, str] = {}
    for option in options:
        label_to_id[option["id"]] = option["id"]
        if option.get("name"):
            label_to_id[option["name"]] = option["id"]
    ballot_type = election.get("ballot_type", "ranked")
    rows: list[dict] = []
    issues: list[dict] = []
    for result in results_dict.get("data", []):
        agent = result.get("agent", {}) or {}
        respondent = str(agent.get("name") or agent.get("traits", {}).get("voter_id") or "").strip()
        answer = result.get("answer", {}) or {}
        if not respondent:
            issues.append({"reason": "missing agent name (voter_id)", "answer_keys": sorted(answer)})
            continue
        # Store ids must match ^[a-zA-Z_][a-zA-Z0-9_]*$; anonymous Humanize
        # respondents arrive as hyphenated UUIDs. Sanitize deterministically
        # and keep the original as provenance on the ballot.
        voter_id = respondent.replace("-", "_")
        if not voter_id[0].isalpha() and voter_id[0] != "_":
            voter_id = f"r_{voter_id}"
        try:
            if ballot_type == "ranked":
                raw = answer.get("ranking")
                if isinstance(raw, dict):
                    ordered = [label for label, rank in sorted(raw.items(), key=lambda item: item[1])]
                elif isinstance(raw, list):
                    ordered = list(raw)
                else:
                    issues.append({"voter_id": voter_id, "reason": "no ranking answer"})
                    continue
                # QuestionRank sometimes answers with integer positions into
                # question_options (which follow the election's option order).
                if ordered and all(isinstance(item, int) for item in ordered):
                    if any(index < 0 or index >= len(options) for index in ordered):
                        issues.append({"voter_id": voter_id, "reason": "ranking index out of range", "labels": ordered})
                        continue
                    ordered = [options[index]["id"] for index in ordered]
                unknown = [label for label in ordered if label not in label_to_id]
                if unknown:
                    issues.append({"voter_id": voter_id, "reason": "unknown option labels", "labels": unknown})
                    continue
                rows.append({"voter_id": voter_id, "answer": {"ranking": [label_to_id[label] for label in ordered]}, "respondent": respondent})
            elif ballot_type == "single_choice":
                label = answer.get("choice")
                if label not in label_to_id:
                    issues.append({"voter_id": voter_id, "reason": "unknown option label", "labels": [label]})
                    continue
                rows.append({"voter_id": voter_id, "answer": {"choice": label_to_id[label]}, "respondent": respondent})
            elif ballot_type == "approval":
                labels = answer.get("approved") or answer.get("approval") or []
                unknown = [label for label in labels if label not in label_to_id]
                if unknown:
                    issues.append({"voter_id": voter_id, "reason": "unknown option labels", "labels": unknown})
                    continue
                rows.append({"voter_id": voter_id, "answer": {"approved": [label_to_id[label] for label in labels]}, "respondent": respondent})
            elif ballot_type == "score":
                raw = answer.get("scores") or answer.get("score") or {}
                if not raw:
                    # Score surveys ask one QuestionLinearScale per option,
                    # named score_<option_id>.
                    raw = {
                        key[len("score_"):]: value
                        for key, value in answer.items()
                        if key.startswith("score_") and isinstance(value, (int, float))
                    }
                unknown = [label for label in raw if label not in label_to_id]
                if unknown:
                    issues.append({"voter_id": voter_id, "reason": "unknown option labels", "labels": unknown})
                    continue
                rows.append({"voter_id": voter_id, "answer": {"scores": {label_to_id[label]: value for label, value in raw.items()}}, "respondent": respondent})
            else:
                issues.append({"voter_id": voter_id, "reason": f"unsupported ballot_type for Results import: {ballot_type}"})
        except Exception as exc:  # pragma: no cover - defensive
            issues.append({"voter_id": voter_id, "reason": str(exc)})
    return rows, issues


@app.command("import")
def import_ballots(
    ctx: typer.Context,
    election_id: str = typer.Option(..., "--election", help="Election ID to import ballots into."),
    from_file: Optional[Path] = typer.Option(None, "--from", help="Path to a ballots JSON file ({election_id, ballot_type, rows})."),
    from_results: Optional[Path] = typer.Option(None, "--from-results", help="Path to an EDSL Results .ep package (e.g. downloaded Humanize responses)."),
    from_coop: Optional[str] = typer.Option(None, "--from-coop", help="Coop UUID of an EDSL Results object to pull (network read; requires EDSL auth)."),
    register_voters: bool = typer.Option(False, "--register-voters", help="Register unknown respondents as voters (weight 1.0) instead of importing their ballots as unregistered."),
) -> None:
    """Import ballots from a ballots JSON file or an EDSL Results object."""
    project = ctx_project(ctx)
    sources = [value for value in (from_file, from_results, from_coop) if value]
    if len(sources) != 1:
        raise UserError(
            "Provide exactly one of --from, --from-results, or --from-coop.",
            hint="--from reads a ballots JSON file; --from-results reads a local Results .ep; --from-coop pulls a Results object by UUID.",
        )

    election = read_entity(project, "elections", election_id)
    conversion_issues: list[dict] = []
    if from_file is not None:
        if not from_file.exists():
            raise UserError(
                f"Results file not found: {from_file}",
                {"path": str(from_file)},
                hint="Check the path, or use --from-results for an EDSL Results .ep package.",
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
        source_display = str(from_file)
    else:
        try:
            from edsl import Results
        except ImportError as exc:
            raise UserError(
                "EDSL is required to import from a Results object.",
                hint="Install the optional dependency (`pip install edsl`) and retry.",
            ) from exc
        if from_results is not None:
            if not from_results.exists():
                raise UserError(f"Results package not found: {from_results}", {"path": str(from_results)})
            try:
                results_obj = Results.git.load(str(from_results))
            except Exception as exc:
                raise UserError(
                    f"Could not load EDSL Results package: {from_results}",
                    hint="Expected a .ep package saved by EDSL (e.g. from `voting survey responses`).",
                ) from exc
            source_display = str(from_results)
        else:
            try:
                results_obj = Results.pull(from_coop)
            except Exception as exc:
                raise UserError(
                    f"Could not pull Results object {from_coop} from Coop.",
                    hint="Check EDSL authentication (`ep profiles current`) and that the object is yours.",
                ) from exc
            source_display = f"coop:{from_coop}"
        options = [read_entity(project, "options", oid) for oid in election.get("options", [])]
        ballot_type = election.get("ballot_type", "ranked")
        rows, conversion_issues = _rows_from_edsl_results(results_obj.to_dict(), election, options)

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
        if voter is None and register_voters:
            from voting.core.store import write_entity

            voter = {
                "id": voter_id,
                "name": row.get("respondent") or voter_id,
                "added_at": local_iso_now(),
                "weight": 1.0,
                "eligible": True,
                "traits": {},
                "metadata": {"source": "ballot import --register-voters"},
            }
            write_entity(project, "voters", voter_id, voter)
            voters_by_id[voter_id] = voter
            weight = 1.0
            warnings_list.append({"code": "voter_registered", "voter_id": voter_id})
        elif voter is None:
            warnings_list.append({
                "code": "unregistered_voter",
                "voter_id": voter_id,
                "message": "Ballot recorded but will not count until the voter is registered (or re-import with --register-voters).",
            })
        if voter_id in existing_voter_ids:
            warnings_list.append({"code": "ballot_overwritten", "voter_id": voter_id, "message": f"Existing ballot for voter '{voter_id}' replaced by this import."})

        record: dict = {
            "election_id": election_id,
            "voter_id": voter_id,
            "ballot_type": ballot_type,
            "recorded_at": local_iso_now(),
            "weight": weight,
            "metadata": {
                "source": "import",
                "import_file": source_display,
                **({"respondent": row["respondent"]} if row.get("respondent") and row["respondent"] != voter_id else {}),
            },
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
            "skipped": len(skipped) + len(conversion_issues),
            "skipped_detail": skipped + conversion_issues,
            "source_file": source_display,
        },
        warnings=warnings_list or None,
        next_steps=[f"voting count run {election_id} --method <method>"],
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
