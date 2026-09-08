"""Keep the textbook's worked calculations tied to its executable listings."""
from __future__ import annotations

import json
from math import sqrt
import re

import pytest
from typer.testing import CliRunner

from voting.cli import app
from voting.commands.count import METHODS
from voting.core.errors import UserError
from voting.manual import CHAPTERS, build_manual, listing_commands


@pytest.fixture(scope="module")
def book(tmp_path_factory):
    root = tmp_path_factory.mktemp("textbook") / "book"
    manifest = build_manual(root)
    results = json.loads((root / "results.json").read_text())
    commands = json.loads((root / "commands.json").read_text())
    by_key = {(r["election_id"], r["method"], r["settings"]["seats"]): r for r in results}
    return root, manifest, results, commands, by_key


def totals(result):
    return {r["option_id"]: r["total"] for r in result["scores"]}


def test_book_executes_all_algorithms_and_generates_every_exhibit(book):
    root, manifest, results, commands, _ = book
    assert manifest["command_count"] == len(listing_commands(root)) == len(commands)
    assert manifest["result_count"] == len(results)
    assert {METHODS[r["method"]] for r in results} == set(METHODS.values())
    for chapter in CHAPTERS:
        for exhibit in re.findall(r"\\generated\{([^}]+)\}", (root / chapter).read_text()):
            assert (root / "generated" / f"{exhibit}.tex").is_file(), exhibit
    assert (root / "generated" / "all-results.tex").is_file()
    assert "cd study" in (root / "generated" / "commands.txt").read_text()
    assert not any(c["argv"][1] == "survey" for c in commands)


def test_ranked_worked_calculations(book):
    by_key = book[4]
    expected = {"fptp": ["library"], "simple_majority": [], "borda": ["shelters"],
                "irv": ["shelters"], "bucklin": ["trees"], "runoff": ["shelters"],
                "copeland": ["trees"], "minimax": ["trees"], "ranked_pairs": ["trees"],
                "schulze": ["trees"], "kemeny_young": ["trees"]}
    for method, winners in expected.items():
        assert by_key["ranked", method, 1]["winners"] == winners
    assert totals(by_key["ranked", "borda", 1]) == {
        "library": 126, "shelters": 184, "trees": 176, "playground": 114}
    irv = by_key["ranked", "irv", 1]
    assert [r.get("eliminated") for r in irv["rounds"]] == ["playground", "trees", None]
    assert totals(irv)["shelters"] == 58
    pairwise = by_key["ranked", "schulze", 1]["pairwise"]
    tree_support = {r["b"] if r["a"] == "trees" else r["a"]:
                    r["a_over_b"] if r["a"] == "trees" else r["b_over_a"]
                    for r in pairwise if "trees" in (r["a"], r["b"])}
    assert tree_support == {"library": 58, "shelters": 59, "playground": 59}
    stv = by_key["ranked", "stv", 2]
    assert stv["quota"] == 34
    assert stv["winners"] == ["library", "shelters"]
    assert next(r["total"] for r in stv["rounds"][1]["totals"] if r["option_id"] == "trees") == 25


def test_cardinal_and_committee_worked_calculations(book):
    by_key = book[4]
    assert totals(by_key["approvals", "approval", 1]) == {
        "library": 42, "shelters": 58, "trees": 85, "playground": 41}
    assert totals(by_key["scores", "score", 1]) == {
        "library": 420, "shelters": 585, "trees": 669, "playground": 357}
    assert by_key["star_demo", "score", 1]["winners"] == ["shelters"]
    star = by_key["star_demo", "star", 1]
    assert star["winners"] == ["library"]
    assert {r["option_id"]: r["total"] for r in star["runoff"]["totals"]} == {"library": 3, "shelters": 2}
    assert by_key["credits", "cumulative", 2]["winners"] == ["shelters", "library"]
    qv = by_key["credits", "quadratic", 2]
    assert qv["winners"] == ["shelters", "trees"]
    assert totals(qv) == pytest.approx({"library": 10, "shelters": 15, "trees": 6 + sqrt(51)})
    mes = by_key["credits", "equal_shares", 2]
    assert mes["rounds"][0]["price_per_utility"] == pytest.approx(1 / 113, abs=1e-6)
    assert mes["completed_seats"] == ["library"]
    assert by_key["representation", "cumulative", 3]["winners"] == ["library", "shelters", "trees"]
    representative = by_key["representation", "equal_shares", 3]
    assert representative["winners"] == ["library", "shelters", "garden"]
    assert representative["completed_seats"] == []


def test_validation_and_revision_walkthrough(book):
    _, manifest, results, commands, _ = book
    failures = [c for c in commands if c["expected_error"]]
    assert manifest["expected_validation_errors"] == len(failures) == 4
    assert all(c["returncode"] != 0 and c["envelope"]["errors"][0]["code"] == "validation_error" for c in failures)
    assert [c["envelope"]["errors"][0]["message"] for c in failures[:3]] == [
        "allocation_over_budget", "negative_allocation", "unknown_grade"]
    states = [next(e for e in c["envelope"]["data"]["elections"] if e["election_id"] == "revision")
              for c in commands if c["argv"][1:] == ["status"]]
    assert [s["phase"] for s in states] == ["done", "counting", "done"]
    assert len(states[1]["stale_result_ids"]) == 1
    assert states[2]["status"] == "closed"
    revisions = [r for r in results if r["election_id"] == "revision"]
    assert [r["winners"] for r in revisions] == [["library"], ["shelters"]]
    assert len(set(revisions[0]["provenance"]["ballot_ids"]) ^ set(revisions[1]["provenance"]["ballot_ids"])) == 2


def test_source_export_works_without_a_project_or_running_commands(tmp_path, monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("Sources-only export must not execute commands")

    monkeypatch.setattr("voting.manual.subprocess.run", unexpected)
    root = tmp_path / "sources"
    result = CliRunner().invoke(app, ["docs", "manual", "--output-dir", str(root), "--sources-only"])
    assert result.exit_code == 0, result.exception
    data = json.loads(result.stdout)["data"]
    assert data["example_executed"] is False
    assert data["command_count"] == data["result_count"] == 0
    assert not (root / "study").exists()
    assert not (root / "results.json").exists()
    assert all((root / name).is_file() for name in [*CHAPTERS, "manual.tex", "references.tex", "version.tex"])


def test_export_preserves_existing_directory(tmp_path):
    sentinel = tmp_path / "existing.txt"
    sentinel.write_text("Keep this")
    with pytest.raises(UserError, match="already exists"):
        build_manual(tmp_path, sources_only=True)
    assert sentinel.read_text() == "Keep this"
    assert list(tmp_path.iterdir()) == [sentinel]


def test_only_marked_local_listings_can_execute(tmp_path):
    for chapter in CHAPTERS:
        (tmp_path / chapter).write_text("")
    chapter = tmp_path / CHAPTERS[0]
    chapter.write_text("\\begin{lstlisting}\nep run --jobs external.ep\n\\end{lstlisting}")
    assert listing_commands(tmp_path) == []
    chapter.write_text("\\begin{lstlisting}[style=votingrun]\nvoting survey publish ranked\n\\end{lstlisting}")
    with pytest.raises(UserError, match="allowed local voting commands"):
        listing_commands(tmp_path)
