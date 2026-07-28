from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from voting.commands.common import ctx_project, output
from voting.core.errors import UserError
from voting.core.store import list_records, read_entity, read_json
from voting import plots

app = typer.Typer(help="Built-in SVG plots of ballots and count results.", no_args_is_help=True, add_completion=False)


def _option_names(project, election: dict) -> dict[str, str]:
    names = {}
    for oid in election.get("options", []):
        try:
            names[oid] = read_entity(project, "options", oid).get("name") or oid
        except Exception:
            names[oid] = oid
    return names


def _result(project, result_id: str) -> dict:
    path = project.path("results", f"{result_id}.json")
    if not path.exists():
        raise UserError(
            f"Count result not found: {result_id}",
            {"result_id": result_id},
            hint="Run `voting count list` to see saved result ids.",
        )
    return read_json(path)


def _write(project, name: str, svg: str, out: Optional[Path]) -> Path:
    path = out or project.path("output", "plots", f"{name}.svg")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding="utf-8")
    return path


def _emit(ctx, command: str, path: Path, data: dict) -> None:
    output(
        ctx,
        command,
        {**data, "path": str(path), "format": "svg"},
        human_message=f"Wrote {path}",
        next_steps=[f"open {path}"],
    )


@app.command("scores")
def scores(
    ctx: typer.Context,
    result_id: str = typer.Argument(..., help="Saved count result id (see `voting count list`)."),
    out: Optional[Path] = typer.Option(None, "--out", help="Override the output .svg path."),
) -> None:
    """Bar chart of a count's per-option totals, winner highlighted."""
    project = ctx_project(ctx)
    result = _result(project, result_id)
    election = read_entity(project, "elections", result["election_id"])
    try:
        svg = plots.scores_svg(result, _option_names(project, election))
    except ValueError as exc:
        raise UserError(str(exc), {"result_id": result_id, "method": result.get("method")}) from exc
    path = _write(project, f"scores_{result_id}", svg, out)
    _emit(ctx, "plot scores", path, {"result_id": result_id, "method": result.get("method")})


@app.command("ranks")
def ranks(
    ctx: typer.Context,
    election_id: str = typer.Argument(..., help="Election whose ballots should be plotted."),
    out: Optional[Path] = typer.Option(None, "--out", help="Override the output .svg path."),
) -> None:
    """Stacked bars of where voters ranked each option (latest ballot per voter)."""
    project = ctx_project(ctx)
    election = read_entity(project, "elections", election_id)
    from voting.core.ballots import latest_ballots

    ballots = latest_ballots(project, election_id)
    try:
        svg = plots.ranks_svg(ballots, [
            {"id": oid, "name": name} for oid, name in _option_names(project, election).items()
        ])
    except ValueError as exc:
        raise UserError(str(exc), {"election_id": election_id},
                        hint="ranks plots need ranked ballots; cast or import some first.") from exc
    path = _write(project, f"ranks_{election_id}", svg, out)
    _emit(ctx, "plot ranks", path, {"election_id": election_id, "ballots": len(ballots)})


@app.command("pairwise")
def pairwise(
    ctx: typer.Context,
    result_id: str = typer.Argument(..., help="Saved count result id from a pairwise method (schulze, copeland, kemeny_young)."),
    out: Optional[Path] = typer.Option(None, "--out", help="Override the output .svg path."),
) -> None:
    """Head-to-head margin matrix from a Condorcet-style count result."""
    project = ctx_project(ctx)
    result = _result(project, result_id)
    election = read_entity(project, "elections", result["election_id"])
    try:
        svg = plots.pairwise_svg(result, _option_names(project, election))
    except ValueError as exc:
        raise UserError(str(exc), {"result_id": result_id, "method": result.get("method")},
                        hint="Run `voting count run <election_id> --method schulze` first.") from exc
    path = _write(project, f"pairwise_{result_id}", svg, out)
    _emit(ctx, "plot pairwise", path, {"result_id": result_id, "method": result.get("method")})


@app.command("methods")
def methods(
    ctx: typer.Context,
    election: Optional[str] = typer.Option(None, "--election", help="Restrict to one election's saved counts."),
    out: Optional[Path] = typer.Option(None, "--out", help="Override the output .svg path."),
) -> None:
    """Grid of finishing positions across every saved count — does the method change the winner?"""
    project = ctx_project(ctx)
    records = [record for _, record in list_records(project, "results")]
    if election:
        records = [r for r in records if r.get("election_id") == election]
    names: dict[str, str] = {}
    for election_id in {r.get("election_id") for r in records if r.get("election_id")}:
        try:
            names.update(_option_names(project, read_entity(project, "elections", election_id)))
        except Exception:
            pass
    try:
        svg = plots.methods_svg(records, names)
    except ValueError as exc:
        raise UserError(str(exc), {"election": election},
                        hint="Run `voting count run <election_id>` (with several --method values) first.") from exc
    path = _write(project, f"methods_{election or 'all'}", svg, out)
    _emit(ctx, "plot methods", path, {
        "election": election,
        "results": len(records),
        "methods": sorted({r.get("method", "?") for r in records}),
    })
