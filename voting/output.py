from __future__ import annotations

import json
import os

import typer


def should_emit_json(human_flag: bool) -> bool:
    if human_flag:
        return False
    return os.getenv("VOTING_HUMAN_OUTPUT", "").lower() != "true"


def finish(
    command: str,
    data: dict,
    warnings: list | None = None,
    next_steps: list | None = None,
) -> None:
    payload = {
        "command": command,
        "status": "ok",
        "data": data,
        "warnings": warnings or [],
        "errors": [],
        "next_steps": next_steps or [],
    }
    typer.echo(json.dumps(payload, indent=2))


def fail(command: str, error: Exception) -> None:
    from voting.core.errors import VotingError

    if isinstance(error, VotingError):
        err_dict = {
            "code": error.code,
            "message": str(error),
            "context": error.details,
            "hint": error.hint,
        }
        exit_code = error.exit_code
    else:
        err_dict = {
            "code": "internal_error",
            "message": str(error),
            "context": {},
            "hint": "",
        }
        exit_code = 1

    payload = {
        "command": command,
        "status": "error",
        "data": {},
        "warnings": [],
        "errors": [err_dict],
        "next_steps": [],
    }
    typer.echo(json.dumps(payload, indent=2))
    raise typer.Exit(exit_code)
