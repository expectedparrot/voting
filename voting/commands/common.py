from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

from voting.core.project import Project, find_project
from voting.output import finish


def ctx_project(ctx: typer.Context) -> Project:
    override: Path | None = ctx.obj.project if ctx.obj else None
    return find_project(override=override)


def output(
    ctx: typer.Context,
    command: str,
    data: Any,
    warnings: list[dict] | None = None,
    next_steps: list[str] | None = None,
    human_message: str | None = None,
    human_renderable: Any = None,
) -> None:
    human = ctx.obj.human if ctx.obj else False
    if human:
        if human_renderable is not None:
            from voting.render import print_human

            print_human(human_renderable() if callable(human_renderable) else human_renderable)
        else:
            typer.echo(human_message or json.dumps(data, indent=2, sort_keys=True))
        return
    payload = data if isinstance(data, dict) else {"items": data}
    finish(command, payload, warnings=warnings, next_steps=next_steps)


def parse_json_value(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value
