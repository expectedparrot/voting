from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from voting.core.errors import UserError


SUPPORTED_BALLOT_TYPES = {"ranked", "single_choice", "approval", "score"}


def build_humanize_job(
    election: dict,
    options: list[dict],
    voters: list[dict],
    output_path: Path,
    *,
    email_trait: str | None = None,
    randomize_options: bool = True,
) -> dict:
    """Build a model-free EDSL Jobs package suitable for `ep humanize create`."""
    try:
        from edsl import Agent, AgentList, Jobs, Survey
        from edsl.questions import (
            QuestionCheckBox,
            QuestionLinearScale,
            QuestionMultipleChoice,
            QuestionRank,
        )
    except ImportError as exc:
        raise UserError(
            "EDSL is required to build a Humanize job.",
            hint="Install the optional dependency with `pip install -e '.[humanize]'`.",
        ) from exc

    ballot_type = election.get("ballot_type", "ranked")
    if ballot_type not in SUPPORTED_BALLOT_TYPES:
        raise UserError(
            f"Humanize does not support ballot_type '{ballot_type}'.",
            {"ballot_type": ballot_type, "supported": sorted(SUPPORTED_BALLOT_TYPES)},
            hint="Use ranked, single_choice, approval, or score ballots.",
        )
    if len(options) < 2:
        raise UserError(
            "A Humanize voting survey requires at least two options.",
            {"option_count": len(options)},
            hint="Add another eligible option to the election.",
        )
    if email_trait:
        if not voters:
            raise UserError(
                "Email delivery requires at least one registered voter.",
                hint="Add voters and their email traits before generating the Humanize job.",
            )
        missing = [voter["id"] for voter in voters if not voter.get("traits", {}).get(email_trait)]
        if missing:
            raise UserError(
                f"Some voters do not have the '{email_trait}' email trait.",
                {"email_trait": email_trait, "voter_ids": missing},
                hint=f"Set it with `voting voter set-trait <voter_id> {email_trait} '\"name@example.com\"'`.",
            )

    labels = [option["name"] for option in options]
    election_name = election.get("name") or election["id"]
    description = election.get("description") or ""
    context = f"\n\n{description}" if description else ""
    questions = []
    if ballot_type == "ranked":
        questions.append(QuestionRank(
            question_name="ranking",
            question_text=f"{election_name}{context}\n\nRank the options from most to least preferred.",
            question_options=labels,
            num_selections=len(labels),
            include_comment=False,
        ))
    elif ballot_type == "single_choice":
        questions.append(QuestionMultipleChoice(
            question_name="choice",
            question_text=f"{election_name}{context}\n\nWhich option do you most prefer?",
            question_options=labels,
            include_comment=False,
        ))
    elif ballot_type == "approval":
        questions.append(QuestionCheckBox(
            question_name="approved",
            question_text=f"{election_name}{context}\n\nSelect every option you approve of.",
            question_options=labels,
            min_selections=0,
            max_selections=len(labels),
            include_comment=False,
        ))
    else:
        questions.extend(
            QuestionLinearScale(
                question_name=f"score_{option['id']}",
                question_text=f"{election_name}{context}\n\nHow much do you support {option['name']}?",
                question_options=list(range(11)),
                option_labels={0: "Strongly oppose", 5: "Neutral", 10: "Strongly support"},
                include_comment=False,
            )
            for option in options
        )

    randomized_questions = (
        [question.question_name for question in questions]
        if randomize_options and ballot_type in {"ranked", "single_choice", "approval"}
        else []
    )
    survey = Survey(questions, questions_to_randomize=randomized_questions)
    agents = None
    if email_trait:
        agents = AgentList([
            Agent(name=voter["id"], traits={**voter.get("traits", {}), "voter_id": voter["id"]})
            for voter in voters
        ])

    jobs = Jobs(survey=survey, agents=agents) if agents is not None else Jobs(survey=survey)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        git_accessor = jobs.git
    except (AttributeError, ValueError):
        git_accessor = None
    if git_accessor is not None:
        git_accessor.save(output_path)
        saved_path = output_path
    else:
        jobs.save(str(output_path), compress=False)
        saved_path = output_path if output_path.exists() else Path(f"{output_path}.json")

    manifest = {
        "election_id": election["id"],
        "ballot_type": ballot_type,
        "options": [{"id": option["id"], "name": option["name"]} for option in options],
        "question_names": [question.question_name for question in questions],
        "email_trait": email_trait,
        "voter_count": len(voters) if email_trait else 0,
        "randomize_options": bool(randomized_questions),
        "job_path": str(saved_path),
    }
    return manifest


def run_ep(args: list[str]) -> dict[str, Any]:
    executable = shutil.which("ep")
    if not executable:
        raise UserError("The ep CLI was not found.", hint="Install EDSL and confirm `ep --help` works.")
    completed = subprocess.run(
        [executable, *args],
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise UserError(
            "The ep CLI returned non-JSON output.",
            {"returncode": completed.returncode, "stderr": completed.stderr.strip()},
            hint="Run the equivalent ep command directly for diagnostic output.",
        ) from exc
    if completed.returncode != 0 or payload.get("status") != "ok":
        raise UserError(
            "The ep CLI command failed.",
            {"returncode": completed.returncode, "ep": payload},
            hint=payload.get("error", {}).get("message", "Check your Expected Parrot credentials and input files."),
        )
    return payload.get("data", payload)
