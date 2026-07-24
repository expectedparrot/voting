from __future__ import annotations

import json
import os
from pathlib import Path

from typer.testing import CliRunner

from voting.cli import app


runner = CliRunner()


def invoke(args: list[str], cwd: Path):
    previous = os.getcwd()
    os.chdir(cwd)
    try:
        return runner.invoke(app, args)
    finally:
        os.chdir(previous)


def test_agent_bootstrap_guides_a_fresh_agent(tmp_path: Path) -> None:
    result = invoke(["agent-bootstrap"], tmp_path)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["data"]["state"]["phase"] == "init"
    assert payload["data"]["agent_guide"].startswith("# Getting Started")
    assert payload["next_steps"] == ["voting init <name>"]


def test_agent_bootstrap_uses_current_project_state(tmp_path: Path) -> None:
    init_result = invoke(["init", "team_vote"], tmp_path)
    assert init_result.exit_code == 0, init_result.output

    result = invoke(["agent-bootstrap"], tmp_path / "team_vote")

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["data"]["state"]["phase"] == "setup"
    assert "voting option add <id> <name>" in payload["next_steps"]
    assert "voting voter add <id> <name>" in payload["next_steps"]


def test_agent_bootstrap_has_readable_human_output(tmp_path: Path) -> None:
    result = invoke(["--human", "agent-bootstrap"], tmp_path)

    assert result.exit_code == 0, result.output
    assert "Current phase: init" in result.stdout
    assert "voting init <name>" in result.stdout
