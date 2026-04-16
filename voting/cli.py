from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from voting.commands import ballot, count, election, info, init, option, voter
from voting.core.errors import VotingError

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()


class CliContext:
    def __init__(self, project: Path | None, human: bool, quiet: bool):
        self.project = project
        self.human = human
        self.quiet = quiet


def emit(data: Any = None, warnings: list[dict] | None = None) -> None:
    typer.echo(json.dumps({"data": data, "warnings": warnings or []}, indent=2, sort_keys=True))


@app.callback()
def callback(
    ctx: typer.Context,
    project: Path | None = typer.Option(None, "--project", help="Override project root."),
    human: bool = typer.Option(False, "--human", help="Use human-readable output."),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress non-data human output."),
) -> None:
    ctx.obj = CliContext(project=project, human=human, quiet=quiet)


app.command("init")(init.command)
app.command("info")(info.command)
app.add_typer(election.app, name="election")
app.add_typer(option.app, name="option")
app.add_typer(voter.app, name="voter")
app.add_typer(ballot.app, name="ballot")
app.add_typer(count.app, name="count")


def main() -> None:
    try:
        app()
    except VotingError as exc:
        typer.echo(
            json.dumps({"error": {"code": exc.code, "message": exc.message, "details": exc.details}}, indent=2, sort_keys=True),
            err=True,
        )
        sys.exit(exc.exit_code)
    except Exception as exc:
        typer.echo(
            json.dumps({"error": {"code": "internal_error", "message": str(exc), "details": {}}}, indent=2, sort_keys=True),
            err=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
