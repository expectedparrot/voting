from __future__ import annotations

import json
import random
from functools import cmp_to_key

import pytest
from typer.testing import CliRunner

from voting.cli import app
from voting.core.errors import VotingError
from voting.core.methods.condorcet import ranked_pairs
from voting.core.methods.irv import irv
from voting.core.methods.other import majority_judgment
from voting.core.methods.score import star
from voting.core.validate import ballot_issue


@pytest.fixture
def cli(tmp_path):
    runner = CliRunner()
    root = tmp_path / "project"

    def invoke(*args, ok=True):
        result = runner.invoke(app, ["--project", str(root), *map(str, args)])
        if not ok:
            assert result.exit_code != 0, result.stdout
            assert isinstance(result.exception, VotingError), result.exception
            return result.exception
        assert result.exit_code == 0, (args, result.stdout, result.exception)
        return json.loads(result.stdout)["data"]

    invoke("init", root)
    for oid in "abc":
        invoke("option", "add", oid, oid.upper())
    invoke("voter", "add", "v", "Voter")
    invoke.root = root
    return invoke


def election(cli, ballot_type, eid="e", seats=1):
    cli("election", "add", eid, eid, "--ballot-type", ballot_type, "--seats", seats)
    for oid in "abc":
        cli("election", "add-option", eid, oid)
    cli("election", "open", eid)


def import_rows(cli, tmp_path, rows, ballot_type="approval", **kwargs):
    path = tmp_path / "ballots.json"
    path.write_text(json.dumps({"ballot_type": ballot_type, "rows": rows}))
    return cli("ballot", "import", "--election", "e", "--from", path, **kwargs)


def test_ranked_pairs_respects_every_locked_edge():
    ballots = [{"ranking": list(r), "weight": w} for r, w in
               [("adcb", 2), ("cdba", 1), ("cabd", 3), ("cbda", 2), ("bdac", 4)]]
    result = ranked_pairs({}, list("abcd"), ballots, "lexicographic")
    assert result["winners"] == ["c"]
    positions = {row["option_id"]: row["rank"] for row in result["ranking"]}
    assert all(positions[a] < positions[b] for a, b in result["locked"])


def test_star_ranking_and_winner_agree():
    ballots = [{"scores": dict(zip("abc", scores))} for scores in
               [(5, 4, 0), (5, 3, 0), (0, 5, 4), (0, 5, 3), (3, 2, 5)]]
    result = star({}, list("abc"), ballots, "lexicographic")
    assert result["winners"] == ["a"]
    assert [r["option_id"] for r in result["ranking"]] == list("abc")
    assert [r["status"] for r in result["ranking"]] == ["elected", "defeated", "defeated"]


def test_irv_finalist_precedes_eliminated_candidate():
    result = irv({}, list("abc"), [{"ranking": list(r), "weight": w}
                 for r, w in [("abc", 4), ("bac", 3), ("cab", 2)]], "lexicographic")
    assert [r["option_id"] for r in result["ranking"]] == list("abc")
    assert [r["status"] for r in result["ranking"]] == ["elected", "defeated", "eliminated"]


@pytest.mark.parametrize("bt,payload,settings,code", [
    ("approval", {"approved": ["b", "b"]}, {}, "duplicate_approved_option"),
    ("ranked", {"ranking": ["b", "b"]}, {}, "duplicate_ranked_option"),
    ("ranked", {"ranking": "abc"}, {}, "invalid_ballot_shape"),
    ("ranked", {"ranking": [["a"]]}, {}, "invalid_option_id"),
    ("score", {"scores": {"b": float("nan")}}, {}, "invalid_numeric_value"),
    ("score", {"scores": {"b": float("inf")}}, {}, "invalid_numeric_value"),
    ("score", {"scores": {"b": True}}, {}, "invalid_numeric_value"),
    ("allocated", {"allocations": {"a": 100, "b": -100}}, {"budget": 10}, "negative_allocation"),
    ("allocated", {"allocations": {"a": 11}}, {"budget": 10}, "allocation_over_budget"),
    ("grade", {"grades": {"b": "A"}}, {}, "unknown_grade"),
    ("approval", {"approved": ["a", "b"]}, {"approval_limit": 1}, "approval_over_limit"),
    ("single_choice", {"choice": "missing"}, {}, "unknown_option"),
])
def test_shared_ballot_validation(bt, payload, settings, code):
    issue = ballot_issue({"ballot_type": bt, **payload}, list("abc"),
                         {"ballot_type": bt, "settings": settings})
    assert issue["code"] == code


def test_bad_entry_cannot_replace_valid_ballot(cli):
    election(cli, "ranked")
    cli("ballot", "rank", "e", "v", "b", "a")
    cli("ballot", "cast", "e", "v", "--choice", "a", ok=False)
    cli("ballot", "rank", "e", "v", "missing", ok=False)
    assert cli("ballot", "list", "--election", "e", "--latest")["ballots"][0]["ranking"] == ["b", "a"]
    for method in ("score", "range", "approval", "sntv"):
        cli("count", "run", "e", "--method", method, ok=False)
    cli("count", "compare", "e", "--method", "irv", "--method", "range", ok=False)
    assert cli("count", "list")["results"] == []


def test_import_rejects_duplicates_and_accepts_abstention(cli, tmp_path):
    election(cli, "approval")
    cli("ballot", "approve", "e", "v", "--option", "b")
    bad = import_rows(cli, tmp_path, [{"voter_id": "v", "answer": {"approved": ["b", "b", "b"]}}])
    assert (bad["cast"], bad["skipped"]) == (0, 1)
    assert cli("count", "run", "e", "--method", "approval")["scores"][0]["total"] == 1
    blank = import_rows(cli, tmp_path, [{"voter_id": "v", "answer": {"approved": []}}])
    assert (blank["cast"], blank["skipped"]) == (1, 0)
    assert cli("ballot", "list", "--election", "e", "--latest")["ballots"][0]["approved"] == []
    assert all(s["total"] == 0 for s in cli("count", "run", "e", "--method", "approval")["scores"])
    cli("ballot", "approve", "e", "v", "--abstain")


def test_allocated_import_and_configuration(cli, tmp_path):
    election(cli, "allocated")
    cli("election", "configure", "e", "--budget", 10)
    result = import_rows(cli, tmp_path, [
        {"voter_id": "v", "answer": {"allocations": {"a": 11}}},
        {"voter_id": "v", "answer": {"allocations": {"b": 10}}},
    ], "allocated")
    assert (result["cast"], result["skipped"]) == (1, 1)
    assert cli("count", "run", "e", "--method", "cumulative")["winners"] == ["b"]
    cli("election", "configure", "e", "--clear-budget")
    cli("ballot", "allocate", "e", "v", "b=20")
    cli("ballot", "allocate", "e", "v", "b=NaN", ok=False)
    cli("ballot", "allocate", "e", "v", "b=one", ok=False)
    cli("ballot", "allocate", "e", "v", "b=10", "b=1", ok=False)


@pytest.mark.parametrize("weight", ["0", "-1", "NaN", "inf"])
def test_invalid_voter_weight(cli, weight):
    cli("voter", "add", "bad", "Bad", "--weight", weight, ok=False)
    assert len(cli("voter", "list")["voters"]) == 1


def test_invalid_settings_and_seats(cli):
    cli("election", "add", "bad", "Bad", "--ballot-type", "rnak", ok=False)
    election(cli, "approval")
    for args in [("--seats", "-1"), ("--seats", "0"), ("--seats", "4"), ("--tie-policy", "random")]:
        cli("count", "run", "e", "--method", "approval", *args, ok=False)
    for args in [("--budget", "NaN"), ("--approval-limit", "0"), ("--grade", "A"),
                 ("--grade", "A", "--grade", "A"), ("--tie-policy", "random")]:
        cli("election", "configure", "e", *args, ok=False)
    assert cli("election", "show", "e")["settings"] == {"quota": "droop", "tie_policy": "lexicographic"}


def test_multi_seat_comparison_and_approval_limits(cli):
    election(cli, "approval", seats=2)
    cli("ballot", "approve", "e", "v", "--option", "a", "--option", "b", "--option", "c")
    compared = cli("count", "compare", "e")
    assert compared["methods_run"] == ["approval"]
    assert compared["results"][0]["runner_up"] == "c"
    assert {s["method"] for s in compared["methods_skipped"]} == {"block_voting", "limited_voting"}
    cli("election", "configure", "e", "--approval-limit", 1)
    cli("ballot", "approve", "e", "v", "--option", "a", "--option", "b", ok=False)
    cli("ballot", "approve", "e", "v", "--option", "b")
    assert len(cli("count", "compare", "e")["methods_run"]) == 3


def test_custom_grade_scale_and_count_time_revalidation(cli):
    election(cli, "grade")
    cli("election", "configure", "e", "--grade", "F", "--grade", "B", "--grade", "A")
    cli("ballot", "grade", "e", "v", "a=F", "b=A", "c=B")
    assert cli("count", "run", "e", "--method", "majority_judgment")["winners"] == ["b"]
    cli("election", "configure", "e", "--grade", "poor", "--grade", "good")
    validated = cli("ballot", "validate", "e")
    assert validated["valid_ballots"] == 0
    assert validated["warnings"][0]["code"] == "unknown_grade"
    assert cli("count", "run", "e", "--method", "majority_judgment")["winners"] == []


def test_edsl_missing_approval_is_not_an_abstention():
    from voting.commands.ballot import _rows_from_edsl_results
    results = {"data": [{"agent": {"name": "missing"}, "answer": {}},
                        {"agent": {"name": "blank"}, "answer": {"approved": []}}]}
    rows, issues = _rows_from_edsl_results(results, {"ballot_type": "approval"}, [{"id": "a", "name": "A"}])
    assert [r["voter_id"] for r in rows] == ["blank"]
    assert len(issues) == 1


def test_bad_import_does_not_register_voters(cli, tmp_path):
    election(cli, "allocated")
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"ballot_type": "allocated", "rows": [
        {"voter_id": "new", "answer": {"allocations": {"a": -1}}}]}))
    result = cli("ballot", "import", "--election", "e", "--from", path, "--register-voters")
    assert result["cast"] == 0
    assert [v["id"] for v in cli("voter", "list")["voters"]] == ["v"]


def test_no_valid_ballots_does_not_invent_winner(cli):
    election(cli, "ranked")
    result = cli("count", "run", "e", "--method", "irv")
    assert result["winners"] == []
    assert result["warnings"][0]["code"] == "no_valid_ballots"


def test_kemeny_guard_applies_to_aliases_and_compare(cli, monkeypatch):
    election(cli, "ranked")
    for i in range(7):
        oid = f"x{i}"
        cli("option", "add", oid, oid)
        cli("election", "add-option", "e", oid)
    cli("ballot", "rank", "e", "v", "b", "a")
    def forbidden(*args):
        pytest.fail("expensive enumeration was called without opting in")
    monkeypatch.setattr("voting.core.methods.condorcet.kemeny_best", forbidden)
    result = cli("count", "compare", "e")
    assert "kemeny_young" not in result["methods_run"]
    assert any(r["method"] == "kemeny_young" for r in result["methods_skipped"])
    for name in ["kemeny", "kemeny_young"]:
        cli("count", "run", "e", "--method", name, ok=False)
    monkeypatch.setattr("voting.core.methods.condorcet.kemeny_best", lambda options, matrix: (options, 0))
    cli("count", "run", "e", "--method", "kemeny", "--allow-expensive")


def test_majority_judgment_fractional_weights_and_lower_median():
    ballots = [{"weight": 0.5, "grades": {"a": "reject", "b": "excellent"}}]
    assert majority_judgment({}, list("ab"), ballots, "lexicographic")["winners"] == ["b"]
    ballots = [{"grades": {"a": "reject", "b": "good"}},
               {"grades": {"a": "excellent", "b": "good"}}]
    assert majority_judgment({}, list("ab"), ballots, "lexicographic")["winners"] == ["b"]


def test_majority_judgment_histograms_match_expanded_ballots():
    rng = random.Random(61)
    scale = ["bad", "fair", "good", "great"]
    for _ in range(100):
        ballots = [{"weight": rng.randint(1, 6), "grades": {c: rng.choice(scale) for c in "abc"}}
                   for _ in range(7)]
        expanded = {c: sorted(g for b in ballots for g in [scale.index(b["grades"][c])] * b["weight"])
                    for c in "abc"}
        def compare(a, b):
            left, right = expanded[a][:], expanded[b][:]
            while left and right:
                lm, rm = left.pop((len(left) - 1) // 2), right.pop((len(right) - 1) // 2)
                if lm != rm:
                    return -1 if lm > rm else 1
            return (a > b) - (a < b)
        expected = sorted("abc", key=cmp_to_key(compare))
        result = majority_judgment({"settings": {"grade_scale": scale}}, list("abc"), ballots, "lexicographic")
        assert [r["option_id"] for r in result["ranking"]] == expected


def test_workflow_tracks_elections_and_stale_counts(cli):
    election(cli, "ranked")
    cli("ballot", "rank", "e", "v", "a", "b", "c")
    saved = cli("count", "run", "e", "--method", "irv")
    assert saved["provenance"]["ballot_ids"]
    assert saved["provenance"]["option_ids"] == list("abc")
    cli("election", "close", "e")
    assert cli("status")["phase"] == "done"
    cli("election", "open", "e")
    cli("ballot", "rank", "e", "v", "b", "a", "c")
    state = cli("status")
    assert state["phase"] == "counting"
    assert state["elections"][0]["stale_result_ids"] == [saved["id"]]
    cli("count", "run", "e", "--method", "irv")
    election(cli, "single_choice", "new")
    state = cli("status")
    assert state["phase"] == "balloting"
    assert cli("next")["recommendation"] == "voting ballot cast new <voter_id> --choice <option_id>"
    cli("ballot", "cast", "new", "v", "--choice", "c")
    cli("count", "run", "new", "--method", "fptp")
    cli("election", "configure", "e", "--seats", 2)
    assert cli("status")["phase"] == "counting"
    cli("count", "compare", "e")
    cli("voter", "set-eligible", "v", "false")
    assert cli("status")["phase"] != "done"


@pytest.mark.parametrize("human", [False, True])
def test_surveys_filter_eligibility_and_respect_limits(tmp_path, human):
    from edsl import Jobs
    from voting.humanize import build_humanize_job, build_simulation_job

    e = {"id": "e", "name": "E", "ballot_type": "approval", "options": list("abcd"),
         "settings": {"approval_limit": 1}}
    options = [{"id": "a", "name": "A"}, {"id": "b", "name": "B"},
               {"id": "c", "name": "C", "eligible": False},
               {"id": "d", "name": "D", "type": "reference"}]
    voters = [{"id": "v", "traits": {"email": "v@example.com"}},
              {"id": "excluded", "eligible": False, "traits": {}}]
    path = tmp_path / "survey.ep"
    if human:
        manifest = build_humanize_job(e, options, voters, path, email_trait="email")
    else:
        manifest = build_simulation_job(e, options, voters, path, model_name="test")
    assert [o["id"] for o in manifest["options"]] == ["a", "b"]
    assert manifest["voter_count"] == 1
    jobs = Jobs.git.load(str(path))
    assert [a.name for a in jobs.agents] == ["v"]
    question = jobs.survey.questions[0]
    assert question.question_options == ["A", "B"]
    assert question.max_selections == 1
    assert question.min_selections == 0
