from __future__ import annotations

from pathlib import Path

import typer

from voting.commands.common import ctx_project, output
from voting.core.errors import UserError
from voting.core.store import list_entities, read_entity
from voting.surveygen import generate_survey_script

app = typer.Typer(help="Generate EDSL survey scripts for preference elicitation.", no_args_is_help=True, add_completion=False)


@app.command("generate")
def generate(
    ctx: typer.Context,
    election_id: str = typer.Argument(..., help="Election ID to generate a survey for."),
    model: str = typer.Option("claude-opus-4-6", "--model", "-m", help="EDSL model name."),
    output_path: Path | None = typer.Option(None, "--output", "-o", help="Override output path for the script."),
) -> None:
    """Generate a standalone EDSL Python script that elicits voter preferences."""
    project = ctx_project(ctx)

    election = read_entity(project, "elections", election_id)
    ballot_type = election.get("ballot_type", "ranked")

    if ballot_type not in {"ranked", "single_choice", "approval", "score"}:
        raise UserError(
            f"Survey generation does not support ballot_type '{ballot_type}'.",
            {"ballot_type": ballot_type, "supported": ["ranked", "single_choice", "approval", "score"]},
            hint="Change the election ballot type or cast ballots directly.",
        )

    option_ids = election.get("options", [])
    if not option_ids:
        raise UserError(
            "Election has no options.",
            {"election_id": election_id},
            hint=f"Add options with `voting election add-option {election_id} <option_id>`.",
        )

    options = [read_entity(project, "options", oid) for oid in option_ids]
    voters = list_entities(project, "voters")
    if not voters:
        raise UserError(
            "No voters registered.",
            {"election_id": election_id},
            hint="Add voters with `voting voter add <id> <name>` before generating a survey.",
        )

    output_dir = project.path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    results_path = output_dir / f"results_{election_id}.json"
    script_path = output_path or (output_dir / f"survey_{election_id}.py")

    script = generate_survey_script(
        election=election,
        options=options,
        voters=voters,
        output_path=results_path,
        model_name=model,
    )

    script_path.write_text(script, encoding="utf-8")

    output(
        ctx,
        "survey generate",
        {
            "election_id": election_id,
            "ballot_type": ballot_type,
            "options": len(options),
            "voters": len(voters),
            "model": model,
            "script_path": str(script_path),
            "results_path": str(results_path),
        },
        human_message=f"Generated survey script: {script_path}",
        next_steps=[
            f"python {script_path}",
            f"voting ballot import --election {election_id} --from {results_path}",
        ],
    )
