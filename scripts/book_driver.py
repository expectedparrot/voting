#!/usr/bin/env python3
"""Run the tutorial's worked example and capture every envelope.

The worked run recreates the "Classic book preference" election and imports
the real production Results object (18 human respondents ranking eight
classic novels via an Expected Parrot Humanize survey), then counts the same
ballots under many methods. Nothing is fixtured: the ballots are real human
rankings pulled from Coop.

Requirements to regenerate:
- dev install of this repo plus edsl
- production Expected Parrot credentials in ~/.env
  (EXPECTED_PARROT_API_KEY, no EXPECTED_PARROT_URL override)

Usage (from the repo root):

    python scripts/book_driver.py    # rerun the worked run, refresh captures
    python scripts/build_index.py    # render docs/index.html from captures
"""
from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TUTORIAL = REPO / "build" / "tutorial"
WORK = TUTORIAL / "classic_books"
CAPTURES = TUTORIAL / "captures"

RESULTS_UUID = "917f9e19-d477-43cf-bdf0-664a1592400f"

BOOKS = [
    ("great_gatsby", "The Great Gatsby — Fitzgerald"),
    ("mockingbird", "To Kill a Mockingbird — Harper Lee"),
    ("nineteen_eighty_four", "1984 — Orwell"),
    ("catcher_rye", "The Catcher in the Rye — Salinger"),
    ("lord_flies", "Lord of the Flies — Golding"),
    ("mice_men", "Of Mice and Men — Steinbeck"),
    ("animal_farm", "Animal Farm — Orwell"),
    ("scarlet_letter", "The Scarlet Letter — Hawthorne"),
]

METHODS = ["borda", "irv", "schulze", "copeland", "kemeny_young", "bucklin", "fptp"]


def parrot_env() -> dict[str, str]:
    """Subprocess env with production Expected Parrot credentials from ~/.env."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO)
    env.pop("EXPECTED_PARROT_URL", None)  # production default
    env_file = Path.home() / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("EXPECTED_PARROT_API_KEY="):
                env["EXPECTED_PARROT_API_KEY"] = line.split("=", 1)[1].strip().strip('"')
    return env


def voting(*args: str, capture: str | None = None, cwd: Path | None = None,
           human: bool = False, expect_fail: bool = False) -> dict:
    argv = [sys.executable, "-m", "voting"] + (["--human"] if human else []) + list(args)
    completed = subprocess.run(argv, cwd=cwd or WORK, env=parrot_env(), text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if expect_fail:
        assert completed.returncode != 0, f"expected failure: {args}\n{completed.stdout}"
    else:
        assert completed.returncode == 0, f"failed: {args}\n{completed.stdout}\n{completed.stderr}"
    if human:
        if capture:
            (CAPTURES / f"{capture}.txt").write_text(
                "$ voting --human " + shlex.join(args) + "\n" + completed.stdout
            )
        return {}
    payload = json.loads(completed.stdout)
    if capture:
        (CAPTURES / f"{capture}.json").write_text(json.dumps({
            "argv_display": "voting " + shlex.join(args),
            "payload": payload,
        }, indent=2, ensure_ascii=False))
    return payload


def main() -> None:
    if TUTORIAL.exists():
        shutil.rmtree(TUTORIAL)
    CAPTURES.mkdir(parents=True)

    voting("version", capture="01-version", cwd=TUTORIAL)
    voting("init", "classic_books", capture="02-init", cwd=TUTORIAL)
    voting("next", capture="03-next")

    # ── Options and the election ──────────────────────────────────────────
    voting("option", "add", BOOKS[0][0], BOOKS[0][1], capture="04-option-add")
    for option_id, name in BOOKS[1:]:
        voting("option", "add", option_id, name)
    voting("election", "add", "book_preference", "Classic book preference",
           "--method", "borda", "--ballot-type", "ranked", capture="05-election-add")
    for option_id, _ in BOOKS:
        voting("election", "add-option", "book_preference", option_id)
    voting("election", "open", "book_preference", capture="06-election-open")
    voting("election", "show", "book_preference", capture="06h-election", human=True)

    # ── The hosted Humanize survey (build is local; publishing happened once) ─
    voting("survey", "humanize", "book_preference", capture="07-humanize")

    # ── Real ballots: pull the production Results object and import ────────
    # First without registration: ballots record, but none can count —
    # the fail-closed state the tutorial teaches readers to check for.
    first = voting("ballot", "import", "--election", "book_preference",
                   "--from-coop", RESULTS_UUID, capture="08a-import-unregistered")
    assert first["data"]["cast"] > 0
    unvalidated = voting("ballot", "validate", "book_preference",
                         capture="08b-validate-unregistered")
    assert unvalidated["data"]["valid_ballots"] == 0
    imported = voting("ballot", "import", "--election", "book_preference",
                      "--from-coop", RESULTS_UUID, "--register-voters",
                      capture="08-import")
    assert imported["data"]["cast"] > 0, "no ballots imported"
    assert imported["data"]["skipped"] == 0, imported["data"]
    voting("ballot", "validate", "book_preference", capture="09-validate")
    voting("ballot", "list", "--election", "book_preference", capture="10-ballots", human=True)
    voting("status", capture="11-status")

    # ── Count the same ballots under many methods ─────────────────────────
    validated = voting("ballot", "validate", "book_preference")
    assert validated["data"].get("valid_ballots") == imported["data"]["cast"], validated["data"]
    voting("count", "run", "book_preference", capture="12-count-borda")
    for method in METHODS[1:]:
        voting("count", "run", "book_preference", "--method", method,
               capture=f"13-count-{method}")
    voting("count", "list", capture="14-count-list")
    voting("count", "list", capture="14h-count-list", human=True)
    voting("next", capture="15-next-final")

    print("captures:", len(list(CAPTURES.iterdir())))


if __name__ == "__main__":
    main()
