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
        ("election", "add", "drink", "Best drink", "--ballot-type", "single_choice"),
        ("election", "add-option", "drink", "tea"),
        ("election", "add-option", "drink", "coffee"),
        ("election", "open", "drink"),
        ("ballot", "cast", "drink", "v1", "--choice", "tea"),
        ("ballot", "cast", "drink", "v2", "--choice", "coffee"),
        ("ballot", "validate", "drink"),
        ("count", "run", "drink", "--method", "fptp"),
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
        ("election", "add", "favorite", "Favorite book", "--ballot-type", "ranked"),
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

    counted = run_voting("count", "run", "favorite", "--method", "irv", cwd=cwd)
    assert counted.returncode == 0
    count_payload = json.loads(counted.stdout)
    assert count_payload["status"] == "ok"


def test_option_import_bulk_loads_and_attaches(tmp_path: Path) -> None:
    assert run_voting("init", "bulk", cwd=tmp_path).returncode == 0
    cwd = tmp_path / "bulk"
    assert run_voting("election", "add", "books", "Books", "--ballot-type", "ranked", cwd=cwd).returncode == 0
    spec = tmp_path / "options.json"
    spec.write_text(json.dumps([
        {"id": "gatsby", "name": "The Great Gatsby"},
        {"id": "orwell", "name": "1984"},
        {"id": "mockingbird", "name": "To Kill a Mockingbird"},
    ]))
    imported = run_voting("option", "import", "--from", str(spec), "--election", "books", cwd=cwd)
    assert imported.returncode == 0, imported.stdout + imported.stderr
    payload = json.loads(imported.stdout)
    assert payload["data"]["imported"] == 3
    assert payload["data"]["attached"] == ["gatsby", "orwell", "mockingbird"]

    shown = run_voting("election", "show", "books", cwd=cwd)
    assert json.loads(shown.stdout)["data"]["options"] == ["gatsby", "orwell", "mockingbird"]

    # a duplicate id in the file fails before anything is written
    spec2 = tmp_path / "options2.json"
    spec2.write_text(json.dumps([{"id": "new_one", "name": "New"}, {"id": "gatsby", "name": "Dupe"}]))
    failed = run_voting("option", "import", "--from", str(spec2), cwd=cwd)
    assert failed.returncode != 0
    listed = run_voting("option", "list", cwd=cwd)
    assert len(json.loads(listed.stdout)["data"]["options"]) == 3  # new_one not half-imported


def test_human_mode_renders_rich_tables(tmp_path: Path) -> None:
    assert run_voting("init", "pretty", cwd=tmp_path).returncode == 0
    cwd = tmp_path / "pretty"
    for step in [
        ("option", "add", "tea", "Tea"),
        ("option", "add", "coffee", "Coffee"),
        ("voter", "add", "v1", "Voter One"),
        ("election", "add", "drink", "Best drink", "--ballot-type", "ranked"),
        ("election", "add-option", "drink", "tea"),
        ("election", "add-option", "drink", "coffee"),
        ("election", "open", "drink"),
        ("ballot", "rank", "drink", "v1", "tea", "coffee"),
        ("count", "run", "drink", "--method", "borda"),
    ]:
        assert run_voting(*step, cwd=cwd).returncode == 0, step

    # recast: the log keeps both records; --latest resolves to one per voter
    assert run_voting("ballot", "rank", "drink", "v1", "coffee", "tea", cwd=cwd).returncode == 0
    all_records = json.loads(run_voting("ballot", "list", "--election", "drink", cwd=cwd).stdout)
    assert len(all_records["data"]["ballots"]) == 2
    latest = json.loads(run_voting("ballot", "list", "--election", "drink", "--latest", cwd=cwd).stdout)
    assert len(latest["data"]["ballots"]) == 1
    assert latest["data"]["ballots"][0]["ranking"] == ["coffee", "tea"]

    shown = run_voting("--human", "election", "show", "drink", cwd=cwd)
    assert shown.returncode == 0, shown.stderr
    assert "{" not in shown.stdout  # a panel, not a JSON dump
    assert "tea — Tea" in shown.stdout

    ballots = run_voting("--human", "ballot", "list", "--election", "drink", cwd=cwd)
    assert "coffee > tea" in ballots.stdout

    counts = run_voting("--human", "count", "list", cwd=cwd)
    assert "borda" in counts.stdout
    assert "winner" in counts.stdout.lower() or "tea" in counts.stdout


def test_count_compare_runs_all_compatible_methods(tmp_path: Path) -> None:
    assert run_voting("init", "cmp", cwd=tmp_path).returncode == 0
    cwd = tmp_path / "cmp"
    for step in [
        ("option", "add", "tea", "Tea"),
        ("option", "add", "coffee", "Coffee"),
        ("voter", "add", "v1", "One"), ("voter", "add", "v2", "Two"), ("voter", "add", "v3", "Three"),
        ("election", "add", "drink", "Best drink", "--ballot-type", "ranked"),
        ("election", "add-option", "drink", "tea"),
        ("election", "add-option", "drink", "coffee"),
        ("election", "open", "drink"),
        ("ballot", "rank", "drink", "v1", "tea", "coffee"),
        ("ballot", "rank", "drink", "v2", "tea", "coffee"),
        ("ballot", "rank", "drink", "v3", "coffee", "tea"),
    ]:
        assert run_voting(*step, cwd=cwd).returncode == 0, step

    compared = run_voting("count", "compare", "drink", cwd=cwd)
    assert compared.returncode == 0, compared.stdout + compared.stderr
    data = json.loads(compared.stdout)["data"]
    assert set(data["methods_run"]) == {
        "borda", "irv", "stv", "schulze", "copeland", "minimax", "ranked_pairs",
        "kemeny_young", "bucklin", "runoff", "fptp", "simple_majority",
    }
    # 2/3 first preferences IS a majority here, so every method decides — tea.
    assert data["no_winner"] == []
    assert data["unanimous_winners"] == ["tea"]
    # every run was saved as a normal result record
    listed = json.loads(run_voting("count", "list", cwd=cwd).stdout)["data"]["results"]
    assert len(listed) == len(data["methods_run"])

    # --method restricts (and unknown names fail closed)
    two = json.loads(run_voting("count", "compare", "drink", "--method", "borda",
                                "--method", "fptp", cwd=cwd).stdout)["data"]
    assert two["methods_run"] == ["borda", "fptp"]
    bad = run_voting("count", "compare", "drink", "--method", "vibes", cwd=cwd)
    assert bad.returncode == 1
    assert json.loads(bad.stdout)["errors"][0]["context"]["methods"] == ["vibes"]


def test_plot_commands_write_svgs(tmp_path: Path) -> None:
    assert run_voting("init", "plots", cwd=tmp_path).returncode == 0
    cwd = tmp_path / "plots"
    for step in [
        ("option", "add", "tea", "Tea"),
        ("option", "add", "coffee", "Coffee"),
        ("option", "add", "milk", "Milk"),
        ("voter", "add", "v1", "One"), ("voter", "add", "v2", "Two"), ("voter", "add", "v3", "Three"),
        ("election", "add", "drink", "Best drink", "--ballot-type", "ranked"),
        ("election", "add-option", "drink", "tea"),
        ("election", "add-option", "drink", "coffee"),
        ("election", "add-option", "drink", "milk"),
        ("election", "open", "drink"),
        ("ballot", "rank", "drink", "v1", "tea", "coffee", "milk"),
        ("ballot", "rank", "drink", "v2", "tea", "milk", "coffee"),
        ("ballot", "rank", "drink", "v3", "coffee", "tea", "milk"),
    ]:
        assert run_voting(*step, cwd=cwd).returncode == 0, step
    borda = json.loads(run_voting("count", "run", "drink", "--method", "borda", cwd=cwd).stdout)["data"]
    schulze = json.loads(run_voting("count", "run", "drink", "--method", "schulze", cwd=cwd).stdout)["data"]

    for args in [
        ("plot", "scores", borda["id"]),
        ("plot", "ranks", "drink"),
        ("plot", "pairwise", schulze["id"]),
        ("plot", "methods", "--election", "drink"),
    ]:
        completed = run_voting(*args, cwd=cwd)
        assert completed.returncode == 0, (args, completed.stdout, completed.stderr)
        payload = json.loads(completed.stdout)
        svg_path = Path(payload["data"]["path"])
        assert svg_path.exists(), args
        content = svg_path.read_text()
        assert content.startswith("<svg"), args
        assert "Tea" in content or "tea" in content, args

    # pairwise on a non-Condorcet result fails with guidance, not a stack trace
    failed = run_voting("plot", "pairwise", borda["id"], cwd=cwd)
    assert failed.returncode == 1
    assert json.loads(failed.stdout)["errors"][0]["hint"]


def test_survey_generate_emits_executable_jobs_package(tmp_path: Path) -> None:
    steps = [
        ("init", "books"),
        ("option", "add", "gatsby", "The Great Gatsby"),
        ("option", "add", "orwell", "1984"),
        ("voter", "add", "v1", "Voter One"),
        ("voter", "add", "v2", "Voter Two"),
        ("election", "add", "favorite", "Favorite book", "--ballot-type", "ranked"),
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
        ("election", "add", "favorite", "Favorite book", "--ballot-type", "ranked"),
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
