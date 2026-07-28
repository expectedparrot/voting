from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from voting.commands import agent_bootstrap, ballot, count, election, info, init, option, voter
from voting.commands import docs_cmd, meta, status, survey
from voting.core.errors import VotingError
from voting.output import ENVELOPE_SCHEMA_VERSION, canonical_command

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()


class CliContext:
    def __init__(self, project: Path | None, human: bool, quiet: bool):
        self.project = project
        self.human = human
        self.quiet = quiet


@app.callback()
def callback(
    ctx: typer.Context,
    project: Optional[Path] = typer.Option(None, "--project", help="Override project root."),
    human: bool = typer.Option(False, "--human", help="Use human-readable output."),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress non-data human output."),
) -> None:
    ctx.obj = CliContext(project=project, human=human, quiet=quiet)


app.command("init")(init.command)
app.command("agent-bootstrap")(agent_bootstrap.command)
app.command("info")(info.command)
app.command("status")(status.command)
app.command("version")(meta.version_command)
app.command("capabilities")(meta.capabilities_command)
app.command("next")(meta.next_command)
app.add_typer(election.app, name="election")
app.add_typer(option.app, name="option")
app.add_typer(voter.app, name="voter")
app.add_typer(ballot.app, name="ballot")
app.add_typer(count.app, name="count")
app.add_typer(docs_cmd.app, name="docs")
app.add_typer(survey.app, name="survey")


def main() -> None:
    try:
        app()
    except VotingError as exc:
        payload = {
            "schema_version": ENVELOPE_SCHEMA_VERSION,
            "command": canonical_command(),
            "argv": ["voting", *sys.argv[1:]],
            "status": "error",
            "data": {},
            "warnings": [],
            "errors": [{"code": exc.code, "message": str(exc), "context": exc.details, "hint": exc.hint}],
            "next_steps": [],
        }
        typer.echo(json.dumps(payload, indent=2))
        sys.exit(exc.exit_code)
    except SystemExit:
        raise
    except Exception as exc:
        payload = {
            "schema_version": ENVELOPE_SCHEMA_VERSION,
            "command": canonical_command(),
            "argv": ["voting", *sys.argv[1:]],
            "status": "error",
            "data": {},
            "warnings": [],
            "errors": [{"code": "internal_error", "message": str(exc), "context": {}, "hint": ""}],
            "next_steps": [],
        }
        typer.echo(json.dumps(payload, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
