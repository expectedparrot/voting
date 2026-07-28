from __future__ import annotations

import typer
from typing import Optional

from voting.commands.common import ctx_project, output
from voting.core.ballots import latest_ballots
from voting.core.errors import UserError
from voting.core.ids import local_iso_now
from voting.core.methods.approval import approval, block_voting, limited_voting
from voting.core.methods.borda import borda
from voting.core.methods.condorcet import copeland, kemeny_young, minimax, ranked_pairs, schulze
from voting.core.methods.irv import irv
from voting.core.methods.other import bucklin, cumulative, majority_judgment, runoff
from voting.core.methods.score import score, star
from voting.core.methods.simple import fptp, simple_majority, sntv
from voting.core.methods.stv import stv
from voting.core.project import Project
from voting.core.store import append_record, list_records, read_entity, read_json
from voting.core.validate import eligible_options

app = typer.Typer(no_args_is_help=True, add_completion=False)

METHODS = {
    "fptp": fptp,
    "first_past_the_post": fptp,
    "simple_majority": simple_majority,
    "borda": borda,
    "irv": irv,
    "stv": stv,
    "single_transferable_vote": stv,
    "approval": approval,
    "score": score,
    "range": score,
    "range_voting": score,
    "star": star,
    "condorcet_copeland": copeland,
    "copeland": copeland,
    "condorcet_minimax": minimax,
    "minimax": minimax,
    "ranked_pairs": ranked_pairs,
    "tideman": ranked_pairs,
    "schulze": schulze,
    "beatpath": schulze,
    "kemeny_young": kemeny_young,
    "kemeny": kemeny_young,
    "block_voting": block_voting,
    "plurality_at_large": block_voting,
    "limited_voting": limited_voting,
    "sntv": sntv,
    "cumulative": cumulative,
    "runoff": runoff,
    "two_round": runoff,
    "bucklin": bucklin,
    "majority_judgment": majority_judgment,
}


@app.command("run")
def run(
    ctx: typer.Context,
    election_id: str,
    method: str = typer.Option(..., "--method", help="Counting method to apply (a count is a lens on the ballots; elections do not fix one)."),
    seats: Optional[int] = typer.Option(None, "--seats"),
    tie_policy: Optional[str] = typer.Option(None, "--tie-policy"),
) -> None:
    project = ctx_project(ctx)
    prepared = prepare_count(project, election_id, method)
    election = dict(prepared["election"])
    if seats is not None:
        election["seats"] = seats
    selected_method = prepared["method"]
    selected_tie_policy = tie_policy or election.get("settings", {}).get("tie_policy", "lexicographic")
    counter = METHODS[selected_method]
    method_result = counter(election, prepared["options"], prepared["ballots"], selected_tie_policy)
    method_warnings = method_result.pop("warnings", [])
    result = {
        "election_id": election_id,
        "method": selected_method,
        "created_at": local_iso_now(),
        "settings": {
            "seats": election.get("seats", 1),
            "tie_policy": selected_tie_policy,
            **(election.get("settings") or {}),
        },
        "winners": method_result.get("winners", []),
        "ranking": method_result.get("ranking", []),
        "summary": {
            "valid_ballots": len(prepared["ballots"]),
            "invalid_ballots": len(prepared["warnings"]),
            "total_valid_weight": round(sum(float(b.get("weight", 1.0)) for b in prepared["ballots"]), 6),
            "exhausted_weight": method_result.get("exhausted_weight", 0.0),
        },
        **{k: v for k, v in method_result.items() if k not in {"winners", "ranking"}},
        "warnings": prepared["warnings"] + method_warnings,
    }
    rid, _ = append_record(project, "results", [election_id, selected_method], result)
    result["id"] = rid
    def _run_table():
        from voting.render import count_result_table

        return count_result_table(result)

    output(
        ctx,
        "count run",
        result,
        next_steps=[f"voting count show {rid}", "voting count list"],
        human_renderable=_run_table,
    )


@app.command("list")
def list_cmd(
    ctx: typer.Context,
    election: Optional[str] = typer.Option(None, "--election"),
) -> None:
    records = [record for _, record in list_records(ctx_project(ctx), "results")]
    if election:
        records = [r for r in records if r.get("election_id") == election]

    def _table():
        from voting.render import count_list_table

        return count_list_table(records)

    output(ctx, "count list", {"results": records}, human_renderable=_table)


@app.command("show")
def show(ctx: typer.Context, result_id: str) -> None:
    project = ctx_project(ctx)
    result = read_json(project.path("results", f"{result_id}.json"))

    def _table():
        from voting.render import count_result_table

        return count_result_table(result)

    output(ctx, "count show", result, human_renderable=_table)


def prepare_count(project: Project, election_id: str, method: str | None) -> dict:
    """Resolve options, voters, and countable ballots.

    method=None is the validation-only path (ballot checks without counting);
    counting always names its method explicitly — elections do not carry one.
    """
    election = read_entity(project, "elections", election_id)
    selected_method = method
    if selected_method is not None and selected_method not in METHODS:
        raise UserError(
            "Unknown voting method.",
            {"method": selected_method, "known": sorted(METHODS)},
            hint="Run `voting docs show voting-methods` to see all supported methods.",
        )
    options = eligible_options(
        election,
        [read_entity(project, "options", oid) for oid in election.get("options", [])],
    )
    if not options:
        raise UserError(
            "Election has no eligible options.",
            {"election_id": election_id},
            hint=f"Add options with `voting election add-option {election_id} <option_id>`.",
        )
    voters = {v["id"]: v for v in _safe_list_voters(project)}
    ballots = []
    warnings = []
    for ballot in latest_ballots(project, election_id):
        warning = _ballot_warning(ballot, options, voters, election)
        if warning:
            warnings.append(warning)
        else:
            ballots.append(ballot)
    return {"election": election, "method": selected_method, "options": options, "ballots": ballots, "warnings": warnings}


def _safe_list_voters(project: Project) -> list[dict]:
    from voting.core.store import list_entities
    return list_entities(project, "voters")


def _ballot_warning(ballot: dict, options: list[str], voters: dict[str, dict], election: dict) -> dict | None:
    voter_id = ballot.get("voter_id")
    voter = voters.get(voter_id)
    if voter is None:
        return {"code": "unknown_voter", "ballot_id": ballot.get("id"), "voter_id": voter_id}
    if not voter.get("eligible", True):
        return {"code": "ineligible_voter", "ballot_id": ballot.get("id"), "voter_id": voter_id}
    option_set = set(options)
    ballot_type = ballot.get("ballot_type")
    values: list[str] = []
    if ballot_type == "single_choice":
        values = [ballot.get("choice")]
    elif ballot_type == "ranked":
        values = list(ballot.get("ranking") or [])
        if len(values) != len(set(values)):
            return {"code": "duplicate_ranked_option", "ballot_id": ballot.get("id")}
    elif ballot_type == "approval":
        values = list(ballot.get("approved") or [])
    elif ballot_type == "score":
        values = list((ballot.get("scores") or {}).keys())
    elif ballot_type == "grade":
        values = list((ballot.get("grades") or {}).keys())
    elif ballot_type == "allocated":
        values = list((ballot.get("allocations") or {}).keys())
    unknown = [v for v in values if v not in option_set]
    if unknown:
        return {"code": "unknown_option", "ballot_id": ballot.get("id"), "options": unknown}
    if ballot_type == "allocated":
        budget = election.get("settings", {}).get("budget")
        total = sum(float(v) for v in (ballot.get("allocations") or {}).values())
        if budget is not None and total > float(budget):
            return {"code": "allocation_over_budget", "ballot_id": ballot.get("id"), "total": total, "budget": budget}
    return None
