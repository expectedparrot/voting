# Data Model

All state lives in the `.voting/` hidden directory inside the project root.

## Directory Layout

```
<project_root>/
└── .voting/
    ├── meta.json          # project metadata
    ├── elections/         # one JSON file per election
    ├── options/           # one JSON file per option
    ├── voters/            # one JSON file per voter
    ├── ballots/           # one JSON file per ballot record (append-only)
    ├── results/           # one JSON file per count run
    ├── output/            # generated survey scripts and results files
    ├── policies/          # (reserved)
    ├── sessions/          # (reserved)
    └── reports/           # (reserved)
```

## meta.json

```json
{
  "id": "my_election",
  "title": "My Election",
  "description": "",
  "created_at": "2026-04-21T10:00:00",
  "settings": {
    "default_tie_policy": "lexicographic",
    "allow_unregistered_voters": false
  }
}
```

## options/<id>.json

```json
{
  "id": "alice",
  "name": "Alice Nguyen",
  "type": "candidate",
  "description": "",
  "added_at": "2026-04-21T10:01:00",
  "eligible": true,
  "metadata": {}
}
```

Types: `candidate`, `proposal`, `reference`, `write_in`

## voters/<id>.json

```json
{
  "id": "voter_1",
  "name": "Voter One",
  "added_at": "2026-04-21T10:02:00",
  "weight": 1.0,
  "eligible": true,
  "traits": {
    "persona": "Progressive urban planner who prioritizes transit"
  }
}
```

Traits are arbitrary key/value pairs. The `persona` trait is used by `voting survey generate` to build EDSL agent descriptions.

## elections/<id>.json

```json
{
  "id": "city_council",
  "name": "City Council Race",
  "description": "",
  "created_at": "2026-04-21T10:03:00",
  "method": "irv",
  "ballot_type": "ranked",
  "seats": 1,
  "status": "open",
  "open_at": "2026-04-21T10:04:00",
  "options": ["alice", "bob", "carol"],
  "settings": {
    "tie_policy": "lexicographic",
    "quota": "droop"
  }
}
```

Status values: `draft`, `open`, `closed`

## ballots/<timestamp>_<voter>_<election>.json

Ballot records are append-only. If a voter casts multiple times, the latest supersedes earlier ones for counting, but all are preserved on disk.

**Ranked ballot:**
```json
{
  "id": "20260421T100500_voter_1_city_council",
  "election_id": "city_council",
  "voter_id": "voter_1",
  "ballot_type": "ranked",
  "ranking": ["bob", "alice", "carol"],
  "recorded_at": "2026-04-21T10:05:00",
  "weight": 1.0,
  "metadata": {}
}
```

**Single-choice ballot:**
```json
{ ..., "ballot_type": "single_choice", "choice": "alice" }
```

**Approval ballot:**
```json
{ ..., "ballot_type": "approval", "approved": ["alice", "carol"] }
```

**Score ballot:**
```json
{ ..., "ballot_type": "score", "scores": {"alice": 8, "bob": 5, "carol": 9} }
```

**Grade ballot:**
```json
{ ..., "ballot_type": "grade", "grades": {"alice": "A", "bob": "C", "carol": "B"} }
```

**Allocated ballot:**
```json
{ ..., "ballot_type": "allocated", "allocations": {"alice": 40, "bob": 35, "carol": 25} }
```

## results/<timestamp>_<election>_<method>.json

```json
{
  "id": "20260421T110000_city_council_irv",
  "election_id": "city_council",
  "method": "irv",
  "created_at": "2026-04-21T11:00:00",
  "settings": { "seats": 1, "tie_policy": "lexicographic" },
  "winners": ["alice"],
  "ranking": ["alice", "carol", "bob"],
  "summary": {
    "valid_ballots": 50,
    "invalid_ballots": 2,
    "total_valid_weight": 50.0,
    "exhausted_weight": 0.0
  },
  "rounds": [...],
  "warnings": []
}
```

## output/ (survey generation)

`voting survey generate` writes two files here:

- `survey_<election_id>.py` — the generated EDSL script (inspect before running)
- `results_<election_id>.json` — written by the script after running; ingested by `voting ballot import`

The results file format:
```json
{
  "voting_version": "0.1.0",
  "election_id": "city_council",
  "ballot_type": "ranked",
  "generated_at": "2026-04-21T12:00:00Z",
  "rows": [
    {
      "voter_id": "voter_1",
      "voter_name": "Voter One",
      "answer": { "ranking": ["alice", "carol", "bob"] }
    }
  ]
}
```

## Next Steps

- `voting docs show troubleshooting` — common errors and fixes
- `voting docs show workflow` — phase reference
