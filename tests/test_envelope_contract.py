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
