"""Docs and CLI must not drift: documented commands exist, and commands are documented."""
from __future__ import annotations

import re
from pathlib import Path

import typer

from voting.cli import app

REPO = Path(__file__).resolve().parents[1]
DOCS = [REPO / "README.md", REPO / "docs" / "index.html"]


def registered_command_paths() -> set[str]:
    root = typer.main.get_command(app)
    paths: set[str] = set()

    def walk(cmd, prefix: list[str]) -> None:
        if hasattr(cmd, "commands") and cmd.commands:
            for name, sub in cmd.commands.items():
                walk(sub, prefix + [name])
        elif prefix:
            paths.add(" ".join(prefix))

    walk(root, [])
    return paths


def documented_invocations(text: str) -> set[str]:
    invocations: list[str] = []
    for block in re.findall(r"```(?:bash|sh|console|text)?\n(.*?)```", text, re.DOTALL):
        for line in block.splitlines():
            stripped = line.strip().lstrip("$ ").strip()
            if stripped.startswith("voting "):
                invocations.append(stripped)
    for span in re.findall(r"`([^`\n]+)`", text):
        if span.strip().startswith("voting "):
            invocations.append(span.strip())
    for block in re.findall(r"<pre[^>]*>(?:<code[^>]*>)?(.*?)(?:</code>)?</pre>", text, re.DOTALL):
        for line in block.splitlines():
            stripped = line.strip().lstrip("$ ").strip()
            if stripped.startswith("voting "):
                invocations.append(stripped)
    found: set[str] = set()
    for invocation in invocations:
        cleaned = re.sub(r"^voting\s+(--\S+\s+)*", "voting ", invocation)
        match = re.match(r"voting\s+([a-z][a-z0-9_-]*)(?:\s+([a-z][a-z0-9_-]*))?", cleaned)
        if match:
            first, second = match.group(1), match.group(2)
            found.add(first if second is None else f"{first} {second}")
    return found


def test_every_documented_command_exists() -> None:
    registered = registered_command_paths()
    groups = {path.split(" ")[0] for path in registered}
    documented: set[str] = set()
    for doc in DOCS:
        if doc.exists():
            documented |= documented_invocations(doc.read_text())
    problems = []
    for doc_path in sorted(documented):
        first = doc_path.split(" ")[0]
        if doc_path in registered or doc_path in groups:
            continue
        if first in groups:
            group_subs = {p.split(" ")[1] for p in registered if p.startswith(first + " ") and " " in p}
            if not group_subs or (" " in doc_path and doc_path.split(" ")[1] in group_subs):
                continue
            if first in registered:
                continue
            problems.append(doc_path)
        elif first in registered:
            continue
        else:
            problems.append(doc_path)
    assert problems == [], "docs reference commands the CLI does not register:\n" + "\n".join(problems)


def test_every_registered_command_is_in_readme_reference() -> None:
    readme = (REPO / "README.md").read_text()
    reference = readme[readme.index("## Command reference"):]
    missing = [
        path for path in sorted(registered_command_paths())
        if f"`voting {path}`" not in reference
    ]
    assert missing == [], "commands missing from the README command reference:\n" + "\n".join(missing)
