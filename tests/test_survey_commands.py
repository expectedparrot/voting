from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from voting.commands.survey import show, survey_script_path
from voting.core.errors import UserError


class ProjectStub:
    def __init__(self, root: Path):
        self.root = root

    def path(self, *parts: str) -> Path:
        return self.root / ".voting" / Path(*parts)


def test_survey_script_path_uses_generated_script_convention(tmp_path: Path) -> None:
    project = ProjectStub(tmp_path)
    assert survey_script_path(project, "city_council") == (
        tmp_path / ".voting" / "output" / "survey_city_council.py"
    )


def test_show_reports_missing_generated_script(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = ProjectStub(tmp_path)
    election_path = project.path("elections", "city_council.json")
    election_path.parent.mkdir(parents=True)
    election_path.write_text('{"id": "city_council"}', encoding="utf-8")
    ctx = SimpleNamespace(obj=SimpleNamespace(project=None, human=True, quiet=False))
    monkeypatch.setattr("voting.commands.survey.ctx_project", lambda _ctx: project)

    with pytest.raises(UserError, match="Generated survey script not found") as exc:
        show(ctx, "city_council")

    assert "voting survey generate city_council" in exc.value.hint


def test_show_prints_generated_script_for_humans(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    project = ProjectStub(tmp_path)
    election_path = project.path("elections", "city_council.json")
    election_path.parent.mkdir(parents=True)
    election_path.write_text('{"id": "city_council"}', encoding="utf-8")
    script_path = survey_script_path(project, "city_council")
    script_path.parent.mkdir(parents=True)
    script_path.write_text('print("survey plan")\n', encoding="utf-8")
    ctx = SimpleNamespace(obj=SimpleNamespace(project=None, human=True, quiet=False))
    monkeypatch.setattr("voting.commands.survey.ctx_project", lambda _ctx: project)

    show(ctx, "city_council")

    assert capsys.readouterr().out == 'print("survey plan")\n\n'
