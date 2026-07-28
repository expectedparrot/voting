from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from voting.commands.common import ctx_project, output
from voting.core.errors import UserError
from voting.core.store import list_entities, read_entity
from voting.humanize import build_humanize_job, build_simulation_job, run_ep

app = typer.Typer(help="Create synthetic or hosted human surveys for preference elicitation.", no_args_is_help=True, add_completion=False)


def survey_job_path(project, election_id: str) -> Path:
    """Return the conventional generated Jobs-package path for an election."""
    return project.path("output", f"survey_{election_id}.jobs.ep")


def survey_manifest_path(project, election_id: str) -> Path:
    return project.path("output", f"survey_{election_id}.json")


def survey_results_path(project, election_id: str) -> Path:
    return project.path("output", f"survey_{election_id}.results.ep")


@app.command("generate")
def generate(
    ctx: typer.Context,
    election_id: str = typer.Argument(..., help="Election ID to generate a survey for."),
    model: str = typer.Option("gpt-5.5", "--model", "-m", help="EDSL model name."),
    service: Optional[str] = typer.Option("openai", "--service", help="EDSL inference service name."),
    output_path: Optional[Path] = typer.Option(None, "--output", "-o", help="Override output path for the Jobs package."),
) -> None:
    """Build an EDSL Jobs package (.jobs.ep) that elicits AI voter preferences via `ep run`."""
    project = ctx_project(ctx)

    election = read_entity(project, "elections", election_id)
    option_ids = election.get("options", [])
    if not option_ids:
        raise UserError(
            "Election has no options.",
            {"election_id": election_id},
            hint=f"Add options with `voting election add-option {election_id} <option_id>`.",
        )

    options = [read_entity(project, "options", oid) for oid in option_ids]
    voters = list_entities(project, "voters")

    job_path = output_path or survey_job_path(project, election_id)
    manifest_path = survey_manifest_path(project, election_id)
    results_path = survey_results_path(project, election_id)

    manifest = build_simulation_job(
        election,
        options,
        voters,
        job_path,
        model_name=model,
        service_name=service,
    )
    manifest["results_path"] = str(results_path)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path)

    output(
        ctx,
        "survey generate",
        manifest,
        human_message=(
            f"Generated Jobs package: {manifest['job_path']}\n"
            f"Expected model calls: {manifest['expected_model_calls']} "
            f"({manifest['voter_count']} voters x {len(manifest['question_names'])} questions)"
        ),
        next_steps=[
            f"voting --human survey show {election_id}",
            f"ep run --jobs {manifest['job_path']} --output {results_path}",
            f"voting ballot import --election {election_id} --from-results {results_path}",
        ],
    )


@app.command("show")
def show(
    ctx: typer.Context,
    election_id: str = typer.Argument(..., help="Election ID whose generated survey should be shown."),
) -> None:
    """Display a generated survey job's manifest for inspection before `ep run`."""
    project = ctx_project(ctx)
    read_entity(project, "elections", election_id)
    manifest_path = survey_manifest_path(project, election_id)
    if not manifest_path.exists():
        raise UserError(
            "Generated survey not found.",
            {"election_id": election_id, "manifest_path": str(manifest_path)},
            hint=f"Run `voting survey generate {election_id}` first.",
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    results_path = manifest.get("results_path") or str(survey_results_path(project, election_id))
    lines = [
        f"Survey job for election: {manifest.get('election_id', election_id)}",
        f"Ballot type: {manifest.get('ballot_type')}",
        f"Model: {manifest.get('model')}" + (f" ({manifest['service']})" if manifest.get("service") else ""),
        f"Voters (agents): {manifest.get('voter_count')}",
        f"Expected model calls: {manifest.get('expected_model_calls')}",
        f"Jobs package: {manifest.get('job_path')}",
        "",
        "Questions:",
    ]
    for name, text in (manifest.get("question_texts") or {}).items():
        lines.append(f"  [{name}] {text}")
    lines += [
        "",
        "Options:",
        *[f"  {option['id']}: {option['name']}" for option in manifest.get("options", [])],
    ]
    output(
        ctx,
        "survey show",
        {"election_id": election_id, "manifest_path": str(manifest_path), **manifest},
        human_message="\n".join(lines),
        next_steps=[
            f"ep run --jobs {manifest.get('job_path')} --output {results_path}",
            f"voting ballot import --election {election_id} --from-results {results_path}",
        ],
    )


@app.command("humanize")
def humanize(
    ctx: typer.Context,
    election_id: str = typer.Argument(..., help="Election ID to package for a Humanize web survey."),
    output_path: Optional[Path] = typer.Option(None, "--output", "-o", help="Override the EDSL Jobs output path."),
    email_trait: Optional[str] = typer.Option(None, "--email-trait", help="Voter trait containing recipient email addresses."),
    randomize_options: bool = typer.Option(True, "--randomize-options/--no-randomize-options", help="Randomize displayed option order for each respondent."),
) -> None:
    """Generate a model-free EDSL job for a Humanize voting survey."""
    project = ctx_project(ctx)
    election = read_entity(project, "elections", election_id)
    option_ids = election.get("options", [])
    if not option_ids:
        raise UserError("Election has no options.", hint=f"Add options to {election_id} before generating a survey.")
    options = [read_entity(project, "options", option_id) for option_id in option_ids]
    voters = list_entities(project, "voters")
    job_path = output_path or project.path("output", f"humanize_{election_id}.ep")
    manifest_path = project.path("output", f"humanize_{election_id}.json")
    schema_path = project.path("output", f"humanize_schema_{election_id}.json")
    delivery_map_path = project.path("output", f"humanize_delivery_{election_id}.json")

    manifest = build_humanize_job(
        election,
        options,
        voters,
        job_path,
        email_trait=email_trait,
        randomize_options=randomize_options,
    )
    schema = {
        "questions": {
            name: {"optional": False}
            for name in manifest["question_names"]
        }
    }
    schema_path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
    manifest.update({"schema_path": str(schema_path)})
    create_command = f"ep humanize create --jobs {manifest['job_path']} --name {json.dumps(election.get('name') or election_id)} --schema {schema_path}"
    if email_trait:
        delivery_map_path.write_text(
            json.dumps({"email": {"col_name": email_trait}}, indent=2) + "\n",
            encoding="utf-8",
        )
        manifest["delivery_map_path"] = str(delivery_map_path)
        create_command += f" --delivery_map {delivery_map_path}"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    output(
        ctx,
        "survey humanize",
        manifest,
        human_message=f"Generated Humanize job: {manifest['job_path']}",
        next_steps=[create_command, f"voting survey publish {election_id}"],
    )


@app.command("publish")
def publish(
    ctx: typer.Context,
    election_id: str = typer.Argument(..., help="Election ID whose Humanize job should be published."),
) -> None:
    """Create a hosted Humanize survey through the ep CLI and save its URLs."""
    project = ctx_project(ctx)
    election = read_entity(project, "elections", election_id)
    manifest_path = project.path("output", f"humanize_{election_id}.json")
    if not manifest_path.exists():
        raise UserError(
            "Humanize job manifest not found.",
            hint=f"Run `voting survey humanize {election_id}` first.",
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    args = [
        "humanize", "create", "--jobs", manifest["job_path"],
        "--name", election.get("name") or election_id,
        "--schema", manifest["schema_path"],
    ]
    if manifest.get("delivery_map_path"):
        args.extend(["--delivery_map", manifest["delivery_map_path"]])
    data = run_ep(args)
    deployment_path = project.path("output", f"humanize_deployment_{election_id}.json")
    deployment_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    output(
        ctx,
        "survey publish",
        {**data, "deployment_path": str(deployment_path)},
        human_message=f"Respondent URL: {data.get('respondent_url')}\nAdmin URL: {data.get('admin_url')}",
        next_steps=[
            f"voting survey responses {election_id}",
            *([f"voting survey email {election_id} --name \"Voting invitation\""] if manifest.get("email_trait") else []),
        ],
    )


def _deployment(project, election_id: str) -> dict:
    path = project.path("output", f"humanize_deployment_{election_id}.json")
    if not path.exists():
        raise UserError("Humanize deployment not found.", hint=f"Run `voting survey publish {election_id}` first.")
    return json.loads(path.read_text(encoding="utf-8"))


@app.command("email")
def email(
    ctx: typer.Context,
    election_id: str = typer.Argument(..., help="Published election survey to email."),
    name: str = typer.Option("Voting invitation", "--name", help="Delivery campaign name."),
    subject: Optional[str] = typer.Option(None, "--subject", help="Optional invitation subject line."),
) -> None:
    """Email unique Humanize voting links to configured voters."""
    project = ctx_project(ctx)
    deployment = _deployment(project, election_id)
    survey_uuid = deployment.get("uuid")
    if not survey_uuid:
        raise UserError("Saved Humanize deployment has no survey UUID.")
    args = [
        "humanize", "deliveries", "create", survey_uuid,
        "--name", name,
        "--respondent-email-template", "respondent_invitation",
    ]
    if subject:
        args.extend(["--subject", subject])
    data = run_ep(args)
    output(ctx, "survey email", data, next_steps=[f"ep humanize deliveries tasks {survey_uuid} {data.get('delivery_uuid', '<delivery_uuid>')}"])


@app.command("responses")
def responses(
    ctx: typer.Context,
    election_id: str = typer.Argument(..., help="Published election survey whose responses should be downloaded."),
    output_path: Optional[Path] = typer.Option(None, "--output", "-o", help="Override the Results output path."),
) -> None:
    """Download Humanize responses as an EDSL Results package."""
    project = ctx_project(ctx)
    deployment = _deployment(project, election_id)
    survey_uuid = deployment.get("uuid")
    if not survey_uuid:
        raise UserError("Saved Humanize deployment has no survey UUID.")
    results_path = output_path or project.path("output", f"humanize_responses_{election_id}.ep")
    data = run_ep(["humanize", "responses", survey_uuid, "--output", str(results_path)])
    output(ctx, "survey responses", {**data, "results_path": str(results_path)})
