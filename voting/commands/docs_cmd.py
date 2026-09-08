from __future__ import annotations

from pathlib import Path

import typer

from voting.commands.common import output
from voting.core.errors import UserError
from voting.docs import DOCS, load_doc, search_docs

app = typer.Typer(help="Read built-in documentation.", no_args_is_help=True, add_completion=False)


@app.command("manual")
def manual(
    ctx: typer.Context,
    output_dir: Path = typer.Option(..., "--output-dir", help="New directory for the book and isolated example."),
    pdf: bool = typer.Option(False, "--pdf", help="Compile the exported LaTeX with pdflatex."),
    sources_only: bool = typer.Option(False, "--sources-only", help="Export sources without executing examples."),
) -> None:
    """Build the LaTeX textbook and run its local worked examples."""
    from voting.manual import build_manual

    data = build_manual(output_dir, pdf=pdf, sources_only=sources_only)
    output(ctx, "docs manual", data, human_message=f"Manual written to {data['directory']}")


@app.command("list")
def docs_list(ctx: typer.Context) -> None:
    """List all available documentation topics."""
    topics = [{"topic": k, "title": v["title"], "summary": v["summary"]} for k, v in DOCS.items()]
    output(ctx, "docs list", {"topics": topics})


@app.command("show")
def docs_show(ctx: typer.Context, topic: str) -> None:
    """Show the full text of a documentation topic."""
    if topic not in DOCS:
        raise UserError(
            f"No doc '{topic}'.",
            {"topic": topic, "available": list(DOCS.keys())},
            hint="Run `voting docs list` to see available topics.",
        )
    text = load_doc(topic)
    output(ctx, "docs show", {"topic": topic, "title": DOCS[topic]["title"], "markdown": text})


@app.command("search")
def docs_search(ctx: typer.Context, query: str) -> None:
    """Search documentation by keyword."""
    matches = search_docs(query)
    output(ctx, "docs search", {"query": query, "matches": matches})
