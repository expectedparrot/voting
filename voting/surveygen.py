from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any


def _py(value: Any) -> str:
    return repr(value)


def _header(election: dict, output_path: Path, model_name: str) -> str:
    election_id = election["id"]
    ballot_type = election.get("ballot_type", "ranked")
    return f'''"""Generated EDSL survey for voting election '{election_id}'.

Ballot type: {ballot_type}

This script elicits voter preferences via EDSL and writes results to:
  {output_path}

After a successful run:
  voting ballot import --election {election_id} --from {output_path}
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

MODEL_NAME = {_py(model_name)}
OUTPUT_PATH = Path({_py(str(output_path))})
ELECTION = {_py(election)}

'''


def _write_results_fn(election: dict) -> str:
    election_id = election["id"]
    ballot_type = election.get("ballot_type", "ranked")
    return f'''
def write_results(rows: list[dict]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    envelope = {{
        "voting_version": "0.1.0",
        "election_id": {_py(election_id)},
        "ballot_type": {_py(ballot_type)},
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rows": rows,
    }}
    OUTPUT_PATH.write_text(json.dumps(envelope, indent=2) + "\\n", encoding="utf-8")
    print(f"Wrote {{len(rows)}} ballots to {{OUTPUT_PATH}}")
    print("Next: voting ballot import --election {election_id} --from " + str(OUTPUT_PATH))

'''


def _agents_block(voters: list[dict]) -> str:
    voters_data = [{"id": v["id"], "name": v["name"], "traits": v.get("traits", {})} for v in voters]
    return f'''
VOTERS = {_py(voters_data)}


def build_agents():
    from edsl import Agent, AgentList

    return AgentList([
        Agent(
            name=v["id"],
            traits=v.get("traits", {{}}),
        )
        for v in VOTERS
    ])

'''


def _ranked_body(election: dict, options: list[dict]) -> str:
    options_data = [{"id": o["id"], "name": o["name"]} for o in options]
    election_name = election.get("name", election["id"])
    description = election.get("description", "")
    context_line = f"\\nContext: {description}" if description else ""
    return textwrap.dedent(f'''
    OPTIONS = {_py(options_data)}
    # option_ids preserves the order passed to question_options so index→id conversion works.
    # QuestionRank returns integer indices (positions in question_options), not option name strings.
    option_ids = [o["id"] for o in OPTIONS]
    VOTER_MAP = {{v["id"]: v["name"] for v in VOTERS}}


    def main() -> None:
        from edsl import QuestionRank, Survey, Model

        agents = build_agents()
        option_names = [o["name"] for o in OPTIONS]

        q = QuestionRank(
            question_name="ranking",
            question_text=(
                f"Election: {election_name}.{context_line}\\n\\n"
                "Please rank the following options from most to least preferred."
            ),
            question_options=option_names,
        )

        results = Survey(questions=[q]).by(agents).by(Model(MODEL_NAME)).run()
        raw = results.select("agent.agent_name", "answer.ranking").to_dicts(remove_prefix=True)

        rows = []
        for item in raw:
            voter_id = item["agent_name"]
            # QuestionRank returns a list of integer indices into question_options.
            ranked_indices = item.get("ranking") or []
            ranked_ids = [option_ids[i] for i in ranked_indices]
            rows.append({{
                "voter_id": voter_id,
                "voter_name": VOTER_MAP.get(voter_id, voter_id),
                "answer": {{"ranking": ranked_ids}},
            }})

        write_results(rows)
    ''')


def _single_choice_body(election: dict, options: list[dict]) -> str:
    options_data = [{"id": o["id"], "name": o["name"]} for o in options]
    election_name = election.get("name", election["id"])
    description = election.get("description", "")
    context_line = f"\\nContext: {description}" if description else ""
    return textwrap.dedent(f'''
    OPTIONS = {_py(options_data)}
    OPTION_MAP = {{o["name"]: o["id"] for o in OPTIONS}}
    VOTER_MAP = {{v["id"]: v["name"] for v in VOTERS}}


    def main() -> None:
        from edsl import QuestionMultipleChoice, Survey, Model

        agents = build_agents()
        option_names = [o["name"] for o in OPTIONS]

        q = QuestionMultipleChoice(
            question_name="choice",
            question_text=(
                f"Election: {election_name}.{context_line}\\n\\n"
                "Which one option do you most prefer?"
            ),
            question_options=option_names,
        )

        results = Survey(questions=[q]).by(agents).by(Model(MODEL_NAME)).run()
        raw = results.select("agent.agent_name", "answer.choice").to_dicts(remove_prefix=True)

        rows = []
        for item in raw:
            voter_id = item["agent_name"]
            choice_name = item.get("choice") or ""
            choice_id = OPTION_MAP.get(choice_name, choice_name)
            rows.append({{
                "voter_id": voter_id,
                "voter_name": VOTER_MAP.get(voter_id, voter_id),
                "answer": {{"choice": choice_id}},
            }})

        write_results(rows)
    ''')


def _approval_body(election: dict, options: list[dict]) -> str:
    options_data = [{"id": o["id"], "name": o["name"]} for o in options]
    election_name = election.get("name", election["id"])
    description = election.get("description", "")
    context_line = f"\\nContext: {description}" if description else ""
    return textwrap.dedent(f'''
    OPTIONS = {_py(options_data)}
    OPTION_MAP = {{o["name"]: o["id"] for o in OPTIONS}}
    VOTER_MAP = {{v["id"]: v["name"] for v in VOTERS}}


    def main() -> None:
        from edsl import QuestionCheckbox, Survey, Model

        agents = build_agents()
        option_names = [o["name"] for o in OPTIONS]

        q = QuestionCheckbox(
            question_name="approved",
            question_text=(
                f"Election: {election_name}.{context_line}\\n\\n"
                "Select all options you approve of (you may choose any number)."
            ),
            question_options=option_names,
        )

        results = Survey(questions=[q]).by(agents).by(Model(MODEL_NAME)).run()
        raw = results.select("agent.agent_name", "answer.approved").to_dicts(remove_prefix=True)

        rows = []
        for item in raw:
            voter_id = item["agent_name"]
            approved_names = item.get("approved") or []
            approved_ids = [OPTION_MAP.get(name, name) for name in approved_names]
            rows.append({{
                "voter_id": voter_id,
                "voter_name": VOTER_MAP.get(voter_id, voter_id),
                "answer": {{"approved": approved_ids}},
            }})

        write_results(rows)
    ''')


def _score_body(election: dict, options: list[dict]) -> str:
    options_data = [{"id": o["id"], "name": o["name"]} for o in options]
    election_name = election.get("name", election["id"])
    q_names = [f"score_{o['id']}" for o in options]
    select_cols = '["agent.agent_name"' + "".join(f', "answer.{q}"' for q in q_names) + "]"
    return textwrap.dedent(f'''
    OPTIONS = {_py(options_data)}
    VOTER_MAP = {{v["id"]: v["name"] for v in VOTERS}}


    def main() -> None:
        from edsl import QuestionLinearScale, Survey, Model

        agents = build_agents()

        questions = [
            QuestionLinearScale(
                question_name=f"score_{{o['id']}}",
                question_text=(
                    f"Election: {election_name}.\\n\\n"
                    f"On a scale of 0 to 10, how much do you support {{o['name']}}?\\n"
                    "0 = strongly oppose, 10 = strongly support."
                ),
                question_options=list(range(11)),
                option_labels={{0: "Strongly oppose", 5: "Neutral", 10: "Strongly support"}},
            )
            for o in OPTIONS
        ]

        results = Survey(questions=questions).by(agents).by(Model(MODEL_NAME)).run()
        select_cols = {select_cols}
        raw = results.select(*select_cols).to_dicts(remove_prefix=True)

        rows = []
        for item in raw:
            voter_id = item["agent_name"]
            scores = {{o["id"]: item.get(f"score_{{o['id']}}", 0) for o in OPTIONS}}
            rows.append({{
                "voter_id": voter_id,
                "voter_name": VOTER_MAP.get(voter_id, voter_id),
                "answer": {{"scores": scores}},
            }})

        write_results(rows)
    ''')


def _footer() -> str:
    return '\n\nif __name__ == "__main__":\n    main()\n'


def generate_survey_script(
    election: dict,
    options: list[dict],
    voters: list[dict],
    output_path: Path,
    model_name: str = "claude-opus-4-6",
) -> str:
    ballot_type = election.get("ballot_type", "ranked")

    if ballot_type == "ranked":
        body = _ranked_body(election, options)
    elif ballot_type == "single_choice":
        body = _single_choice_body(election, options)
    elif ballot_type == "approval":
        body = _approval_body(election, options)
    elif ballot_type == "score":
        body = _score_body(election, options)
    else:
        raise ValueError(
            f"Survey generation is not supported for ballot_type '{ballot_type}'. "
            "Supported types: ranked, single_choice, approval, score."
        )

    return (
        _header(election, output_path, model_name)
        + _write_results_fn(election)
        + _agents_block(voters)
        + body
        + _footer()
    )
