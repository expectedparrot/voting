from __future__ import annotations

import json
import os
from pathlib import Path

from typer.testing import CliRunner

from voting.cli import app

runner = CliRunner()


def invoke(args: list[str], cwd: Path) -> dict:
    previous = os.getcwd()
    os.chdir(cwd)
    try:
        result = runner.invoke(app, args)
    finally:
        os.chdir(previous)
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)["data"]


def init_project(tmp_path: Path, name: str = "scenario") -> Path:
    invoke(["init", name], tmp_path)
    return tmp_path / name


def add_options(project: Path, *option_ids: str) -> None:
    for option_id in option_ids:
        invoke(["option", "add", option_id, option_id.title()], project)


def add_voters(project: Path, count: int) -> list[str]:
    voter_ids = [f"v{i}" for i in range(1, count + 1)]
    for voter_id in voter_ids:
        invoke(["voter", "add", voter_id, voter_id.upper()], project)
    return voter_ids


def add_election(project: Path, election_id: str, method: str, ballot_type: str, options: list[str], seats: int = 1) -> None:
    invoke(["election", "add", election_id, election_id.title(), "--method", method, "--ballot-type", ballot_type, "--seats", str(seats)], project)
    for option_id in options:
        invoke(["election", "add-option", election_id, option_id], project)
    invoke(["election", "open", election_id], project)


def count(project: Path, election_id: str, method: str) -> dict:
    return invoke(["count", "run", election_id, "--method", method], project)


def test_ranked_neighborhood_methods(tmp_path: Path) -> None:
    project = init_project(tmp_path, "neighborhood_vote")
    options = ["park", "library", "bike_lanes"]
    add_options(project, *options)
    voters = add_voters(project, 5)
    add_election(project, "neighborhood_projects", "stv", "ranked", options)
    rankings = [
        ["park", "library", "bike_lanes"],
        ["library", "park", "bike_lanes"],
        ["bike_lanes", "park", "library"],
        ["park", "bike_lanes", "library"],
        ["library", "bike_lanes", "park"],
    ]
    for voter_id, ranking in zip(voters, rankings, strict=True):
        invoke(["ballot", "rank", "neighborhood_projects", voter_id, *ranking], project)

    assert count(project, "neighborhood_projects", "fptp")["winners"] == ["library"]
    borda = count(project, "neighborhood_projects", "borda")
    assert borda["winners"] == ["park"]
    assert {item["option_id"]: item["total"] for item in borda["scores"]} == {"park": 6.0, "library": 5.0, "bike_lanes": 4.0}
    assert count(project, "neighborhood_projects", "irv")["winners"] == ["park"]
    assert count(project, "neighborhood_projects", "stv")["winners"] == ["park"]


def test_approval_block_limited_sntv(tmp_path: Path) -> None:
    project = init_project(tmp_path, "committee_vote")
    options = ["music", "food", "art", "sports"]
    add_options(project, *options)
    voters = add_voters(project, 5)
    add_election(project, "festival_committee", "approval", "approval", options, seats=2)
    approvals = [["music", "food"], ["music", "art"], ["food", "art"], ["music", "sports"], ["art", "sports"]]
    for voter_id, approved in zip(voters, approvals, strict=True):
        args = ["ballot", "approve", "festival_committee", voter_id]
        for option_id in approved:
            args.extend(["--option", option_id])
        invoke(args, project)
    assert count(project, "festival_committee", "approval")["winners"] == ["art", "music"]
    assert count(project, "festival_committee", "block_voting")["winners"] == ["art", "music"]

    project2 = init_project(tmp_path, "board_vote")
    options2 = ["ada", "ben", "cy", "dia"]
    add_options(project2, *options2)
    voters2 = add_voters(project2, 5)
    add_election(project2, "park_board", "sntv", "single_choice", options2, seats=2)
    for voter_id, choice in zip(voters2, ["ada", "ada", "ben", "cy", "dia"], strict=True):
        invoke(["ballot", "cast", "park_board", voter_id, "--choice", choice], project2)
    assert count(project2, "park_board", "sntv")["winners"] == ["ada", "ben"]


def test_score_star_and_cumulative(tmp_path: Path) -> None:
    project = init_project(tmp_path, "score_vote")
    options = ["alpha", "beta", "gamma"]
    add_options(project, *options)
    voters = add_voters(project, 5)
    add_election(project, "software_vendor", "score", "score", options)
    scores = [(5, 4, 0), (5, 3, 0), (0, 5, 4), (0, 5, 3), (3, 2, 5)]
    for voter_id, row in zip(voters, scores, strict=True):
        invoke(["ballot", "score", "software_vendor", voter_id, f"alpha={row[0]}", f"beta={row[1]}", f"gamma={row[2]}"], project)
    assert count(project, "software_vendor", "score")["winners"] == ["beta"]
    assert count(project, "software_vendor", "star")["winners"] == ["alpha"]

    project2 = init_project(tmp_path, "budget_vote")
    options2 = ["lighting", "trees", "sidewalks", "murals"]
    add_options(project2, *options2)
    voters2 = add_voters(project2, 5)
    add_election(project2, "capital_budget", "cumulative", "allocated", options2, seats=2)
    rows = [["lighting=5"], ["lighting=3", "trees=2"], ["trees=5"], ["sidewalks=5"], ["sidewalks=3", "murals=2"]]
    for voter_id, row in zip(voters2, rows, strict=True):
        invoke(["ballot", "allocate", "capital_budget", voter_id, *row], project2)
    assert count(project2, "capital_budget", "cumulative")["winners"] == ["lighting", "sidewalks"]


def test_condorcet_stv_majority_judgment_bucklin_runoff(tmp_path: Path) -> None:
    project = init_project(tmp_path, "ranked_suite")
    options = ["alpha", "beta", "gamma"]
    add_options(project, *options)
    voters = add_voters(project, 7)
    add_election(project, "policy_package", "condorcet_copeland", "ranked", options)
    rankings = [["alpha", "beta", "gamma"]] * 3 + [["beta", "gamma", "alpha"]] * 2 + [["gamma", "beta", "alpha"]] * 2
    for voter_id, ranking in zip(voters, rankings, strict=True):
        invoke(["ballot", "rank", "policy_package", voter_id, *ranking], project)
    assert count(project, "policy_package", "condorcet_copeland")["winners"] == ["beta"]
    assert count(project, "policy_package", "condorcet_minimax")["winners"] == ["beta"]

    project2 = init_project(tmp_path, "cycle_vote")
    add_options(project2, *options)
    voters2 = add_voters(project2, 7)
    add_election(project2, "platform_cycle", "ranked_pairs", "ranked", options)
    rankings2 = [["alpha", "beta", "gamma"]] * 3 + [["beta", "gamma", "alpha"]] * 2 + [["gamma", "alpha", "beta"]] * 2
    for voter_id, ranking in zip(voters2, rankings2, strict=True):
        invoke(["ballot", "rank", "platform_cycle", voter_id, *ranking], project2)
    assert count(project2, "platform_cycle", "ranked_pairs")["winners"] == ["alpha"]
    assert count(project2, "platform_cycle", "schulze")["winners"] == ["alpha"]

    project3 = init_project(tmp_path, "club_vote")
    options3 = ["ada", "ben", "cy"]
    add_options(project3, *options3)
    voters3 = add_voters(project3, 5)
    add_election(project3, "club_president", "bucklin", "ranked", options3)
    rankings3 = [["ada", "ben", "cy"], ["ben", "ada", "cy"], ["cy", "ben", "ada"], ["ben", "cy", "ada"], ["cy", "ada", "ben"]]
    for voter_id, ranking in zip(voters3, rankings3, strict=True):
        invoke(["ballot", "rank", "club_president", voter_id, *ranking], project3)
    assert count(project3, "club_president", "bucklin")["winners"] == ["ben"]
    assert count(project3, "club_president", "runoff")["winners"] == ["ben"]

    project4 = init_project(tmp_path, "grade_vote")
    options4 = ["park", "library", "transit"]
    add_options(project4, *options4)
    voters4 = add_voters(project4, 5)
    add_election(project4, "site_selection_grade", "majority_judgment", "grade", options4)
    grades = [("excellent", "good", "excellent"), ("good", "good", "fair"), ("good", "fair", "fair"), ("fair", "fair", "poor"), ("fair", "poor", "reject")]
    for voter_id, row in zip(voters4, grades, strict=True):
        invoke(["ballot", "grade", "site_selection_grade", voter_id, f"park={row[0]}", f"library={row[1]}", f"transit={row[2]}"], project4)
    assert count(project4, "site_selection_grade", "majority_judgment")["winners"] == ["park"]

    project5 = init_project(tmp_path, "stv_vote")
    options5 = ["ada", "ben", "cy", "dia"]
    add_options(project5, *options5)
    voters5 = add_voters(project5, 7)
    add_election(project5, "council_stv", "stv", "ranked", options5, seats=2)
    rankings5 = [["ada", "ben", "cy", "dia"]] * 3 + [["ben", "ada", "cy", "dia"]] * 2 + [["cy", "ben", "ada", "dia"], ["dia", "cy", "ben", "ada"]]
    for voter_id, ranking in zip(voters5, rankings5, strict=True):
        invoke(["ballot", "rank", "council_stv", voter_id, *ranking], project5)
    assert count(project5, "council_stv", "stv")["winners"] == ["ada", "ben"]
