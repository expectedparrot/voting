from __future__ import annotations

import json
from pathlib import Path

import pytest

from voting.core.errors import UserError
from voting.humanize import build_humanize_job, run_ep


@pytest.mark.parametrize(
    ("ballot_type", "question_names"),
    [
        ("ranked", ["ranking"]),
        ("single_choice", ["choice"]),
        ("approval", ["approved"]),
        ("score", ["score_a", "score_b"]),
    ],
)
def test_build_humanize_job(tmp_path: Path, ballot_type: str, question_names: list[str]) -> None:
    pytest.importorskip("edsl")
    from edsl import Jobs

    path = tmp_path / "vote.ep"
    manifest = build_humanize_job(
        {"id": "vote", "name": "Vote", "ballot_type": ballot_type},
        [{"id": "a", "name": "Option A"}, {"id": "b", "name": "Option B"}],
        [{"id": "v1", "name": "Voter One", "traits": {"email": "v1@example.com"}}],
        path,
        email_trait="email",
    )

    if hasattr(Jobs, "git"):
        jobs = Jobs.git.load(manifest["job_path"])
    else:
        jobs = Jobs.load(manifest["job_path"])
    assert manifest["question_names"] == question_names
    assert len(jobs.survey.questions) == len(question_names)
    assert len(jobs.agents) == 1
    assert not jobs.models
    expected_randomized = question_names if ballot_type != "score" else []
    assert jobs.survey.questions_to_randomize == expected_randomized


def test_build_humanize_job_requires_every_email(tmp_path: Path) -> None:
    pytest.importorskip("edsl")
    with pytest.raises(UserError, match="do not have the 'email' email trait") as exc:
        build_humanize_job(
            {"id": "vote", "name": "Vote", "ballot_type": "ranked"},
            [{"id": "a", "name": "Option A"}, {"id": "b", "name": "Option B"}],
            [{"id": "v1", "name": "Voter One", "traits": {}}],
            tmp_path / "vote.ep",
            email_trait="email",
        )
    assert exc.value.details["voter_ids"] == ["v1"]


def test_run_ep_returns_data(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("voting.humanize.shutil.which", lambda _name: "/bin/ep")
    monkeypatch.setattr(
        "voting.humanize.subprocess.run",
        lambda *args, **kwargs: type("Completed", (), {
            "stdout": json.dumps({"status": "ok", "data": {"uuid": "survey-1"}}),
            "stderr": "",
            "returncode": 0,
        })(),
    )
    assert run_ep(["humanize", "status", "survey-1"]) == {"uuid": "survey-1"}
