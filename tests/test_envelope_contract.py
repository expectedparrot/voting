"""Black-box output contract: one JSON envelope on stdout, end to end."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ENVELOPE_KEYS = {"schema_version", "command", "status", "argv", "data", "warnings", "errors", "next_steps"}


def run_voting(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "voting", *args],
        cwd=cwd, text=True, capture_output=True,
        env={"PYTHONPATH": str(REPO), "PATH": "/usr/bin:/bin"},
    )


@pytest.mark.parametrize("argv", [
    ("version",),
    ("capabilities",),
    ("next",),
])
def test_stdout_is_exactly_one_envelope(argv: tuple[str, ...], tmp_path: Path) -> None:
    completed = run_voting(*argv, cwd=tmp_path)
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert ENVELOPE_KEYS <= set(payload)
    assert payload["status"] == "ok"
    assert payload["argv"][0] == "voting"


def test_errors_carry_canonical_command(tmp_path: Path) -> None:
    completed = run_voting("status", cwd=tmp_path)  # no project here
    assert completed.returncode != 0
    payload = json.loads(completed.stdout)
    assert payload["status"] == "error"
    assert payload["command"] == "status"
    assert payload["errors"][0]["code"]


def test_full_election_flow_smoke(tmp_path: Path) -> None:
    steps = [
        ("init", "demo"),
        ("option", "add", "tea", "Tea"),
        ("option", "add", "coffee", "Coffee"),
        ("voter", "add", "v1", "Voter One"),
        ("voter", "add", "v2", "Voter Two"),
        ("election", "add", "drink", "Best drink", "--method", "fptp",
         "--ballot-type", "single_choice"),
        ("election", "add-option", "drink", "tea"),
        ("election", "add-option", "drink", "coffee"),
        ("election", "open", "drink"),
        ("ballot", "cast", "drink", "v1", "--choice", "tea"),
        ("ballot", "cast", "drink", "v2", "--choice", "coffee"),
        ("ballot", "validate", "drink"),
        ("count", "run", "drink"),
    ]
    cwd = tmp_path
    for index, step in enumerate(steps):
        completed = run_voting(*step, cwd=cwd)
        assert completed.returncode == 0, (step, completed.stdout, completed.stderr)
        payload = json.loads(completed.stdout)
        assert payload["status"] == "ok", step
        if index == 0:
            cwd = tmp_path / "demo"
    final = run_voting("next", cwd=cwd)
    assert json.loads(final.stdout)["data"]["phase"] == "done"


def _book_results_ep(path: Path, labels: list[str], rankings: dict[str, list[str]]) -> None:
    import warnings as _warnings

    _warnings.filterwarnings("ignore")
    from edsl import Agent, Model, Results, Scenario, Survey
    from edsl.results import Result

    rows = []
    for voter_id, ordered in rankings.items():
        ranking = {label: ordered.index(label) + 1 for label in ordered}
        rows.append(Result(
            agent=Agent(name=voter_id),
            scenario=Scenario({}),
            model=Model("test"),
            iteration=0,
            answer={"ranking": ranking},
        ))
    Results(survey=Survey([]), data=rows).git.save(str(path))


def test_ballot_import_from_edsl_results(tmp_path: Path) -> None:
    steps = [
        ("init", "books"),
        ("option", "add", "gatsby", "The Great Gatsby"),
        ("option", "add", "orwell", "1984"),
        ("option", "add", "mockingbird", "To Kill a Mockingbird"),
        ("election", "add", "favorite", "Favorite book", "--method", "irv",
         "--ballot-type", "ranked"),
        ("election", "add-option", "favorite", "gatsby"),
        ("election", "add-option", "favorite", "orwell"),
        ("election", "add-option", "favorite", "mockingbird"),
        ("election", "open", "favorite"),
    ]
    cwd = tmp_path
    for index, step in enumerate(steps):
        completed = run_voting(*step, cwd=cwd)
        assert completed.returncode == 0, (step, completed.stdout, completed.stderr)
        if index == 0:
            cwd = tmp_path / "books"

    results_path = tmp_path / "responses.ep"
    _book_results_ep(results_path, ["The Great Gatsby", "1984", "To Kill a Mockingbird"], {
        "r1": ["1984", "The Great Gatsby", "To Kill a Mockingbird"],
        "r2": ["The Great Gatsby", "1984", "To Kill a Mockingbird"],
        "r3": ["1984", "To Kill a Mockingbird", "The Great Gatsby"],
    })

    imported = subprocess.run(
        [sys.executable, "-m", "voting", "ballot", "import", "--election", "favorite",
         "--from-results", str(results_path)],
        cwd=cwd, text=True, capture_output=True,
        env={"PYTHONPATH": str(REPO), "PATH": "/usr/bin:/bin", "HOME": str(tmp_path)},
    )
    assert imported.returncode == 0, imported.stdout + imported.stderr
    payload = json.loads(imported.stdout)
    assert payload["data"]["cast"] == 3
    assert payload["data"]["skipped"] == 0
    # unregistered respondents warn but import (weight 1.0)
    assert any(w["code"] == "unregistered_voter" for w in payload["warnings"])

    counted = run_voting("count", "run", "favorite", cwd=cwd)
    assert counted.returncode == 0
    count_payload = json.loads(counted.stdout)
    assert count_payload["status"] == "ok"


def test_survey_generate_emits_executable_jobs_package(tmp_path: Path) -> None:
    steps = [
        ("init", "books"),
        ("option", "add", "gatsby", "The Great Gatsby"),
        ("option", "add", "orwell", "1984"),
        ("voter", "add", "v1", "Voter One"),
        ("voter", "add", "v2", "Voter Two"),
        ("election", "add", "favorite", "Favorite book", "--method", "borda",
         "--ballot-type", "ranked"),
        ("election", "add-option", "favorite", "gatsby"),
        ("election", "add-option", "favorite", "orwell"),
        ("election", "open", "favorite"),
    ]
    cwd = tmp_path
    for index, step in enumerate(steps):
        completed = run_voting(*step, cwd=cwd)
        assert completed.returncode == 0, (step, completed.stdout, completed.stderr)
        if index == 0:
            cwd = tmp_path / "books"

    generated = subprocess.run(
        [sys.executable, "-m", "voting", "survey", "generate", "favorite"],
        cwd=cwd, text=True, capture_output=True,
        env={"PYTHONPATH": str(REPO), "PATH": "/usr/bin:/bin", "HOME": str(tmp_path)},
    )
    assert generated.returncode == 0, generated.stdout + generated.stderr
    payload = json.loads(generated.stdout)
    data = payload["data"]
    job_path = Path(data["job_path"])
    assert job_path.name == "survey_favorite.jobs.ep"
    assert job_path.exists()
    assert data["expected_model_calls"] == 2  # 2 voters x 1 ranked question
    assert any(step.startswith("ep run --jobs") for step in payload["next_steps"])
    assert any("--from-results" in step for step in payload["next_steps"])

    # The package must carry everything ep run needs: survey, agents, model.
    from edsl import Jobs

    jobs = Jobs.git.load(str(job_path))
    assert sorted(agent.name for agent in jobs.agents) == ["v1", "v2"]
    assert [question.question_name for question in jobs.survey.questions] == ["ranking"]
    assert len(jobs.models) == 1

    shown = subprocess.run(
        [sys.executable, "-m", "voting", "--human", "survey", "show", "favorite"],
        cwd=cwd, text=True, capture_output=True,
        env={"PYTHONPATH": str(REPO), "PATH": "/usr/bin:/bin", "HOME": str(tmp_path)},
    )
    assert shown.returncode == 0, shown.stdout + shown.stderr
    assert "Expected model calls: 2" in shown.stdout


def test_ballot_import_from_results_unknown_label_itemized(tmp_path: Path) -> None:
    steps = [
        ("init", "books2"),
        ("option", "add", "gatsby", "The Great Gatsby"),
        ("election", "add", "favorite", "Favorite book", "--method", "irv",
         "--ballot-type", "ranked"),
        ("election", "add-option", "favorite", "gatsby"),
        ("election", "open", "favorite"),
    ]
    cwd = tmp_path
    for index, step in enumerate(steps):
        completed = run_voting(*step, cwd=cwd)
        assert completed.returncode == 0, (step, completed.stdout)
        if index == 0:
            cwd = tmp_path / "books2"
    results_path = tmp_path / "responses2.ep"
    _book_results_ep(results_path, ["The Great Gatsby"], {
        "r1": ["A Book Nobody Registered"],
    })
    imported = subprocess.run(
        [sys.executable, "-m", "voting", "ballot", "import", "--election", "favorite",
         "--from-results", str(results_path)],
        cwd=cwd, text=True, capture_output=True,
        env={"PYTHONPATH": str(REPO), "PATH": "/usr/bin:/bin", "HOME": str(tmp_path)},
    )
    assert imported.returncode == 0, imported.stdout
    payload = json.loads(imported.stdout)
    assert payload["data"]["cast"] == 0
    assert payload["data"]["skipped"] == 1
    assert payload["data"]["skipped_detail"][0]["reason"] == "unknown option labels"
