"""Rich renderables for --human output.

JSON mode never touches this module; stdout purity is preserved because these
renderers only run when the user opts into --human presentation.
"""
from __future__ import annotations


def print_human(renderable) -> None:
    from rich.console import Console

    Console(width=100).print(renderable)


def election_panel(election: dict, option_names: dict[str, str] | None = None):
    from rich.panel import Panel
    from rich.table import Table

    table = Table(show_header=False, box=None, pad_edge=False)
    table.add_column(style="bold green")
    table.add_column()
    table.add_row("Name", election.get("name") or election["id"])
    if election.get("description"):
        table.add_row("Description", election["description"])
    table.add_row("Method", election.get("method", ""))
    table.add_row("Ballot type", election.get("ballot_type", ""))
    table.add_row("Status", election.get("status", ""))
    table.add_row("Seats", str(election.get("seats", 1)))
    names = option_names or {}
    options = election.get("options", [])
    table.add_row(
        f"Options ({len(options)})",
        "\n".join(f"{oid}" + (f" — {names[oid]}" if oid in names else "") for oid in options) or "(none)",
    )
    return Panel(table, title=f"Election: {election['id']}", border_style="green", expand=False)


def options_table(options: list[dict]):
    from rich.table import Table

    table = Table(title=f"Options ({len(options)})", border_style="green")
    table.add_column("id", style="bold")
    table.add_column("name")
    table.add_column("type")
    table.add_column("eligible")
    for option in options:
        table.add_row(option["id"], option.get("name", ""), option.get("type", ""),
                      "yes" if option.get("eligible", True) else "no")
    return table


def voters_table(voters: list[dict]):
    from rich.table import Table

    table = Table(title=f"Voters ({len(voters)})", border_style="green")
    table.add_column("id", style="bold")
    table.add_column("name")
    table.add_column("weight", justify="right")
    table.add_column("eligible")
    for voter in voters:
        table.add_row(voter["id"], voter.get("name", ""), str(voter.get("weight", 1.0)),
                      "yes" if voter.get("eligible", True) else "no")
    return table


def _ballot_choice(ballot: dict) -> str:
    if ballot.get("ranking") is not None:
        return " > ".join(ballot["ranking"])
    if ballot.get("choice") is not None:
        return str(ballot["choice"])
    if ballot.get("approved") is not None:
        return ", ".join(ballot["approved"])
    if ballot.get("scores") is not None:
        return "  ".join(f"{k}={v:g}" for k, v in ballot["scores"].items())
    if ballot.get("grades") is not None:
        return "  ".join(f"{k}={v}" for k, v in ballot["grades"].items())
    return ""


def ballots_table(ballots: list[dict]):
    from rich.table import Table

    table = Table(title=f"Ballots ({len(ballots)})", border_style="green")
    table.add_column("voter", style="bold", no_wrap=True)
    table.add_column("ballot", overflow="fold")
    table.add_column("recorded", no_wrap=True)
    for ballot in ballots:
        table.add_row(ballot.get("voter_id", ""), _ballot_choice(ballot),
                      (ballot.get("recorded_at") or "").replace("T", " "))
    return table


def count_result_table(result: dict):
    from rich.table import Table

    table = Table(
        title=f"{result.get('method', '')} count — {result.get('election_id', '')}",
        caption=f"winner: {', '.join(result.get('winners', []))}",
        border_style="green",
    )
    table.add_column("rank", justify="right")
    table.add_column("option", style="bold")
    table.add_column("score", justify="right")
    table.add_column("status")
    for row in result.get("ranking", []):
        score = row.get("score")
        table.add_row(
            str(row.get("rank", "")), row.get("option_id", ""),
            "" if score is None else f"{score:g}",
            row.get("status", ""),
        )
    return table


def count_list_table(results: list[dict]):
    from rich.table import Table

    table = Table(title=f"Count runs ({len(results)})", border_style="green")
    table.add_column("method", style="bold")
    table.add_column("winner(s)")
    table.add_column("runner-up")
    table.add_column("created", no_wrap=True)
    for result in results:
        ranking = result.get("ranking", [])
        runner_up = next((r["option_id"] for r in ranking if r.get("rank") == 2), "")
        table.add_row(
            result.get("method", ""),
            ", ".join(result.get("winners", [])),
            runner_up,
            (result.get("created_at") or "").replace("T", " "),
        )
    return table
