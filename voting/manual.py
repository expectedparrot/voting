"""Build the packaged LaTeX manual by executing its local command listings."""
from __future__ import annotations

from collections import defaultdict
from importlib import resources
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

from voting.core.errors import UserError
from voting.core.provenance import package_version


CHAPTERS = [
    "01-decision.tex", "02-project.tex", "03-ranked.tex", "04-pairwise.tex",
    "05-committees.tex", "06-cardinal.tex", "07-credits.tex",
    "08-practice.tex", "09-reference.tex",
]
LOCAL_COMMANDS = {
    ("init",), ("status",), ("next",), ("option", "add"), ("voter", "add"),
    ("election", "add"), ("election", "add-option"), ("election", "open"),
    ("election", "close"), ("election", "configure"),
    ("ballot", "rank"), ("ballot", "cast"), ("ballot", "approve"),
    ("ballot", "score"), ("ballot", "grade"), ("ballot", "allocate"),
    ("ballot", "validate"), ("ballot", "list"),
    ("count", "run"), ("count", "compare"), ("count", "list"),
}


def tex_escape(value: object) -> str:
    replacements = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
                    "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
                    "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(replacements.get(c, c) for c in str(value))


def listing_commands(root: Path) -> list[dict]:
    """Only marked listings run; fielding and illustrative snippets never do."""
    commands = []
    for chapter in CHAPTERS:
        source = (root / chapter).read_text(encoding="utf-8")
        for match in re.finditer(r"\\begin\{lstlisting\}\[style=(votingrun|votingerror)\](.*?)\\end\{lstlisting\}", source, re.S):
            for line in match[2].splitlines():
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                argv = shlex.split(line)
                if not argv or argv[0] != "voting" or not any(tuple(argv[1:1 + len(p)]) == p for p in LOCAL_COMMANDS):
                    raise UserError("Manual executable listings must contain allowed local voting commands.", {"chapter": chapter, "line": line})
                commands.append({"chapter": chapter, "display": line, "argv": argv,
                                 "expected_error": match[1] == "votingerror"})
    return commands


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def run_example(root: Path) -> tuple[list[dict], list[dict]]:
    commands = listing_commands(root)
    env = os.environ.copy()
    # Resolve this checkout/package even after entering the isolated example.
    env["PYTHONPATH"] = str(Path(__file__).resolve().parent.parent) + os.pathsep + env.get("PYTHONPATH", "")
    transcript = []
    cwd = root
    for command in commands:
        completed = subprocess.run([sys.executable, "-m", "voting", *command["argv"][1:]],
                                   cwd=cwd, env=env, capture_output=True, text=True, timeout=60)
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise UserError("Manual command returned non-JSON output.", {"command": command["display"], "stderr": completed.stderr[-2000:]}) from exc
        entry = {**command, "returncode": completed.returncode, "envelope": payload}
        transcript.append(entry)
        _write_json(root / "commands.json", transcript)
        success = completed.returncode == 0 and payload.get("status") == "ok"
        expected_failure = completed.returncode != 0 and payload.get("status") == "error"
        if not (expected_failure if command["expected_error"] else success):
            raise UserError("Manual command did not produce its expected outcome.", entry)
        if command["argv"][1] == "init":
            cwd = root / "study"
    results = [json.loads(p.read_text()) for p in sorted((cwd / ".voting" / "results").glob("*.json"))]
    _write_json(root / "results.json", results)
    generated = root / "generated"
    generated.mkdir()
    lines = ["# Start in the exported manual directory; use a fresh directory to replay."]
    for command in commands:
        if command["expected_error"]:
            lines.append("# Expected validation error (the following command exits nonzero).")
        lines.append(command["display"])
        if command["argv"][1] == "init":
            lines.append("cd study")
    (generated / "commands.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    generate_tables(root, results, transcript)
    return results, transcript


def generate_tables(root: Path, results: list[dict], transcript: list[dict]) -> None:
    from voting.commands.count import METHODS

    directory = root / "generated"
    by_key = {(r["election_id"], r["method"], r["settings"]["seats"]): r for r in results}
    names = {"library": "Library", "shelters": "Shelters", "trees": "Trees", "playground": "Playground", "garden": "Garden"}
    label = lambda oid: names.get(oid, oid)
    winners = lambda r: ", ".join(label(oid) for oid in r["winners"]) or "No winner"

    def table(name, headers, rows, widths=None):
        spec = widths or ("l" * len(headers))
        lines = [r"\begin{longtable}{" + spec + "}", r"\toprule",
                 " & ".join(tex_escape(h) for h in headers) + r" \\\midrule\endhead"]
        lines += [" & ".join(tex_escape(v) for v in row) + r" \\" for row in rows]
        lines += [r"\bottomrule", r"\end{longtable}"]
        (directory / f"{name}.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def numeric(value, places=3):
        return f"{value:,.{places}f}".rstrip("0").rstrip(".") if isinstance(value, (int, float)) else value

    def tally(r):
        return {row["option_id"]: row["total"] for row in r["scores"]}

    def outcome_table(name, election, seats):
        selected = [r for (eid, _, k), r in by_key.items() if eid == election and k == seats]
        table(name, ["Method", "Winner(s)"], [(r["method"], winners(r)) for r in selected], r"p{.40\linewidth}p{.50\linewidth}")

    for name, eid, seats in [("ranked-methods", "ranked", 1), ("approval-methods", "approvals", 1),
                             ("limited-methods", "limited", 3), ("credit-methods", "credits", 2),
                             ("representation-methods", "representation", 3), ("cycle-methods", "cycle", 1)]:
        outcome_table(name, eid, seats)
    order = list("library shelters trees playground".split())
    plurality = tally(by_key["ranked", "fptp", 1])
    borda = tally(by_key["ranked", "borda", 1])
    table("ranked-totals", ["Project", "First choices", "Borda points"],
          [(label(oid), numeric(plurality[oid]), numeric(borda[oid])) for oid in order])
    for filename, key in [("irv-rounds", ("ranked", "irv", 1)), ("stv-rounds", ("ranked", "stv", 2))]:
        r = by_key[key]
        rows = []
        for i, rnd in enumerate(r["rounds"], 1):
            totals = {row["option_id"]: row["total"] for row in rnd["totals"]}
            elected = rnd.get("elected")
            if isinstance(elected, str):
                elected = [elected]
            action = "Elect " + ", ".join(label(oid) for oid in elected) if elected else "Drop " + label(rnd["eliminated"])
            rows.append([i, *[numeric(totals[oid]) if oid in totals else "--" for oid in order], action])
        table(filename, ["Round", "L", "S", "T", "P", "Action"], rows, r"r r r r r p{.30\linewidth}")
    matrix = {(p["a"], p["b"]): p["a_over_b"] for p in by_key["ranked", "schulze", 1]["pairwise"]}
    matrix.update({(p["b"], p["a"]): p["b_over_a"] for p in by_key["ranked", "schulze", 1]["pairwise"]})
    table("pairwise", ["Row over column", "L", "S", "T", "P"],
          [(label(a), *["--" if a == b else numeric(matrix[a, b]) for b in order]) for a in order])
    score = by_key["scores", "score", 1]
    table("score-totals", ["Project", "Total score", "Mean score"],
          [(label(r["option_id"]), numeric(r["score"]), numeric(r["average"])) for r in score["ranking"]])
    grades = by_key["grades", "majority_judgment", 1]
    table("grade-totals", ["Rank", "Project", "Majority grade"],
          [(r["rank"], label(r["option_id"]), r["median"]) for r in grades["ranking"]])
    for name, eid in [("star-runoff", "scores"), ("star-reversal", "star_demo")]:
        r = by_key[eid, "star", 1]
        sc = tally(by_key[eid, "score", 1])
        table(name, ["Finalist", "Score total", "Runoff support", "Outcome"],
              [(label(row["option_id"]), numeric(sc[row["option_id"]]), numeric(row["total"]),
                "Elected" if row["option_id"] in r["winners"] else "Defeated") for row in r["runoff"]["totals"]])
    raw = tally(by_key["credits", "cumulative", 2])
    quadratic = tally(by_key["credits", "quadratic", 2])
    table("credit-totals", ["Project", "Credits spent", "Effective quadratic votes"],
          [(label(oid), numeric(raw[oid]), numeric(quadratic[oid])) for oid in raw])
    mes = by_key["representation", "equal_shares", 3]
    table("mes-rounds", ["Round", "Elected", "Price per utility", "Completion"],
          [(r["round"], label(r["elected"]), numeric(r.get("price_per_utility", "--"), 6), r.get("completion", "No")) for r in mes["rounds"]])
    table("all-results", ["Election", "Method", "Seats", "Winner(s)"],
          [(eid, method, k, winners(r)) for (eid, method, k), r in by_key.items()],
          r"p{.21\linewidth}p{.27\linewidth}r p{.34\linewidth}")
    aliases = defaultdict(list)
    for name, function in METHODS.items():
        aliases[function.__name__].append(name)
    table("aliases", ["Algorithm", "Accepted names"], sorted((name, ", ".join(values)) for name, values in aliases.items()),
          r"p{.27\linewidth}p{.63\linewidth}")
    failures = [(entry["display"], entry["envelope"]["errors"][0]["message"])
                for entry in transcript if entry["expected_error"]]
    table("validation", ["Rejected command", "Reason"], failures, r"p{.51\linewidth}p{.39\linewidth}")
    revision_states = []
    for entry in transcript:
        if entry["argv"][1:] == ["status"]:
            state = next(e for e in entry["envelope"]["data"]["elections"] if e["election_id"] == "revision")
            revision_states.append((len(revision_states) + 1, state["status"], state["phase"],
                                    len(state["current_result_ids"]), len(state["stale_result_ids"])))
    table("revision-history", ["Check", "Election status", "Phase", "Current", "Stale"], revision_states)
    coordinates = " ".join(f"({letter},{plurality[oid]})" for letter, oid in zip("LSTP", order))
    (directory / "first-choice-plot.tex").write_text(
        r"\begin{tikzpicture}\begin{axis}[ybar,width=.85\linewidth,height=5cm,ymin=0,ymax=50,"
        r"symbolic x coords={L,S,T,P},xtick=data,ylabel={Weighted first choices},nodes near coords,"
        r"bar width=22pt,axis lines=left,grid=major]"
        + r"\addplot[fill=VotingGreen!70,draw=VotingGreen] coordinates {" + coordinates
        + r"};\end{axis}\end{tikzpicture}" + "\n", encoding="utf-8")


def build_manual(output_dir: Path, *, pdf: bool = False, sources_only: bool = False) -> dict:
    from voting.commands.count import METHODS
    root = output_dir.resolve()
    if root.exists():
        raise UserError("Manual output directory already exists; choose a new directory.", {"path": str(root)})
    if pdf and not shutil.which("pdflatex"):
        raise UserError("PDF compilation requires pdflatex; omit --pdf to export LaTeX and the example.")
    root.mkdir(parents=True)
    for resource in resources.files("voting").joinpath("manual_content").iterdir():
        if resource.is_file():
            (root / resource.name).write_bytes(resource.read_bytes())
    (root / "version.tex").write_text(
        r"\newcommand{\VotingVersion}{" + tex_escape(package_version()) + "}\n"
        + r"\newcommand{\MethodNameCount}{" + str(len(METHODS)) + "}\n"
        + r"\newcommand{\AlgorithmCount}{" + str(len(set(METHODS.values()))) + "}\n", encoding="utf-8")
    results, commands = ([], []) if sources_only else run_example(root)
    if pdf:
        for _ in range(3):
            compiled = subprocess.run(["pdflatex", "-no-shell-escape", "-interaction=nonstopmode", "-halt-on-error", "manual.tex"],
                                      cwd=root, capture_output=True, text=True, timeout=180)
            if compiled.returncode:
                raise UserError("LaTeX compilation failed; inspect manual.log.", {"directory": str(root), "tail": compiled.stdout[-2500:]})
    manifest = {"schema": "voting-manual-v1", "voting_version": package_version(),
                "example_kind": "fictional teaching profiles", "example_executed": not sources_only,
                "command_count": len(commands), "result_count": len(results),
                "expected_validation_errors": sum(c["expected_error"] for c in commands),
                "sources": CHAPTERS}
    _write_json(root / "build-manifest.json", manifest)
    return {"directory": str(root), "latex": str(root / "manual.tex"),
            "pdf": str(root / "manual.pdf") if pdf else None,
            "manifest": str(root / "build-manifest.json"), **manifest}
