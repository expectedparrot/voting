from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from voting.commands.survey import show, survey_job_path, survey_manifest_path
from voting.core.errors import UserError


class ProjectStub:
    def __init__(self, root: Path):
        self.root = root

    def path(self, *parts: str) -> Path:
        return self.root / ".voting" / Path(*parts)


def test_survey_job_path_uses_jobs_ep_convention(tmp_path: Path) -> None:
    project = ProjectStub(tmp_path)
    assert survey_job_path(project, "city_council") == (
        tmp_path / ".voting" / "output" / "survey_city_council.jobs.ep"
    )


def test_show_reports_missing_generated_survey(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = ProjectStub(tmp_path)
    election_path = project.path("elections", "city_council.json")
    election_path.parent.mkdir(parents=True)
    election_path.write_text('{"id": "city_council"}', encoding="utf-8")
    ctx = SimpleNamespace(obj=SimpleNamespace(project=None, human=True, quiet=False))
    monkeypatch.setattr("voting.commands.survey.ctx_project", lambda _ctx: project)

    with pytest.raises(UserError, match="Generated survey not found") as exc:
        show(ctx, "city_council")

    assert "voting survey generate city_council" in exc.value.hint


def test_show_prints_manifest_summary_for_humans(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    project = ProjectStub(tmp_path)
    election_path = project.path("elections", "city_council.json")
    election_path.parent.mkdir(parents=True)
    election_path.write_text('{"id": "city_council"}', encoding="utf-8")
    manifest_path = survey_manifest_path(project, "city_council")
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(json.dumps({
        "election_id": "city_council",
        "ballot_type": "ranked",
        "model": "gpt-5.5",
        "service": "openai",
        "voter_count": 3,
        "expected_model_calls": 3,
        "job_path": str(survey_job_path(project, "city_council")),
        "question_texts": {"ranking": "Rank the options."},
        "options": [{"id": "alice", "name": "Alice"}],
    }), encoding="utf-8")
    ctx = SimpleNamespace(obj=SimpleNamespace(project=None, human=True, quiet=False))
    monkeypatch.setattr("voting.commands.survey.ctx_project", lambda _ctx: project)

    show(ctx, "city_council")

    out = capsys.readouterr().out
    assert "gpt-5.5" in out
    assert "Rank the options." in out
    assert "alice: Alice" in out
