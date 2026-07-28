from __future__ import annotations

import json
import os
import sys

import typer

ENVELOPE_SCHEMA_VERSION = "1.0"

_COMMAND_GROUPS = {"election", "option", "voter", "ballot", "count", "docs", "survey", "plot"}


def canonical_command(argv: list[str] | None = None) -> str:
    """Derive `group sub` (or a flat command) from the actual invocation."""
    raw = argv if argv is not None else sys.argv[1:]
    words = [arg for arg in raw if not arg.startswith("-")]
    if not words:
        return ""
    depth = 2 if words[0] in _COMMAND_GROUPS and len(words) > 1 else 1
    return " ".join(words[:depth])


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
        "schema_version": ENVELOPE_SCHEMA_VERSION,
        "command": command,
        "status": "ok",
        "argv": ["voting", *sys.argv[1:]],
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
        "schema_version": ENVELOPE_SCHEMA_VERSION,
        "command": command or canonical_command(),
        "status": "error",
        "argv": ["voting", *sys.argv[1:]],
        "data": {},
        "warnings": [],
        "errors": [err_dict],
        "next_steps": [],
    }
    typer.echo(json.dumps(payload, indent=2))
    raise typer.Exit(exit_code)
