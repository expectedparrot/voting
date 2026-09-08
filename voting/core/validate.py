from __future__ import annotations

import math

from .errors import ValidationError

BALLOT_TYPES = {"single_choice", "ranked", "approval", "score", "grade", "allocated"}
GRADE_SCALE = ["reject", "poor", "fair", "good", "excellent"]


def finite_number(value: object) -> bool:
    try:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    except OverflowError:
        return False


def validate_weight(weight: object) -> None:
    if not finite_number(weight) or weight <= 0:
        raise ValidationError("Weight must be a finite positive number.")


def validate_settings(election: dict) -> None:
    if not isinstance(election.get("ballot_type"), str) or election["ballot_type"] not in BALLOT_TYPES:
        raise ValidationError("Unknown ballot type.", {"supported": sorted(BALLOT_TYPES)})
    seats = election.get("seats", 1)
    if type(seats) is not int or seats < 1:
        raise ValidationError("Seats must be a positive integer.")
    settings = election.get("settings") or {}
    if not isinstance(settings, dict):
        raise ValidationError("Election settings must be an object.")
    if settings.get("tie_policy", "lexicographic") != "lexicographic":
        raise ValidationError("Only the lexicographic tie policy is supported.")
    budget = settings.get("budget")
    if budget is not None and (not finite_number(budget) or budget < 0):
        raise ValidationError("Budget must be a finite nonnegative number.")
    limit = settings.get("approval_limit")
    if limit is not None and (type(limit) is not int or limit < 1):
        raise ValidationError("Approval limit must be a positive integer.")
    scale = settings.get("grade_scale", GRADE_SCALE)
    if (not isinstance(scale, list) or len(scale) < 2
            or any(not isinstance(g, str) or not g.strip() for g in scale)
            or len(set(scale)) != len(scale)):
        raise ValidationError("Grade scale must contain at least two distinct labels, worst to best.")


def ballot_issue(ballot: dict, options: list[str], election: dict) -> dict | None:
    """Validate the same ballot schema at entry, import, and count time."""
    def issue(code: str, **details) -> dict:
        return {"code": code, "ballot_id": ballot.get("id"), **details}

    ballot_type = ballot.get("ballot_type")
    if not isinstance(ballot_type, str) or ballot_type not in BALLOT_TYPES or ballot_type != election.get("ballot_type"):
        return issue("ballot_type_mismatch", expected=election.get("ballot_type"), actual=ballot_type)
    weight = ballot.get("weight", 1.0)
    if not finite_number(weight) or weight <= 0:
        return issue("invalid_weight")
    field = {"single_choice": "choice", "ranked": "ranking", "approval": "approved",
             "score": "scores", "grade": "grades", "allocated": "allocations"}[ballot_type]
    value = ballot.get(field)
    if ballot_type == "single_choice":
        values = [value]
    elif ballot_type in {"ranked", "approval"}:
        if not isinstance(value, list):
            return issue("invalid_ballot_shape", field=field)
        values = value
    else:
        if not isinstance(value, dict):
            return issue("invalid_ballot_shape", field=field)
        values = list(value)
    if any(not isinstance(v, str) for v in values):
        return issue("invalid_option_id")
    if not values and ballot_type != "approval":
        return issue("empty_ballot")
    if len(values) != len(set(values)):
        return issue("duplicate_ranked_option" if ballot_type == "ranked" else "duplicate_approved_option")
    unknown = [v for v in values if v not in options]
    if unknown:
        return issue("unknown_option", options=unknown)
    settings = election.get("settings") or {}
    if ballot_type in {"score", "allocated"}:
        if any(not finite_number(v) for v in value.values()):
            return issue("invalid_numeric_value")
    if ballot_type == "allocated":
        if any(v < 0 for v in value.values()):
            return issue("negative_allocation")
        total = sum(value.values())
        budget = settings.get("budget")
        if not finite_number(total):
            return issue("invalid_numeric_value")
        if budget is not None and total > budget:
            return issue("allocation_over_budget", total=total, budget=budget)
    if ballot_type == "approval":
        limit = settings.get("approval_limit")
        if limit is not None and len(values) > limit:
            return issue("approval_over_limit", limit=limit)
    if ballot_type == "grade":
        scale = settings.get("grade_scale", GRADE_SCALE)
        if any(not isinstance(g, str) or g not in scale for g in value.values()):
            return issue("unknown_grade", grade_scale=scale)
    return None


def eligible_options(election: dict, options: list[dict]) -> list[str]:
    option_map = {option["id"]: option for option in options}
    ids = election.get("options") or sorted(option_map)
    result = []
    for option_id in ids:
        option = option_map.get(option_id)
        if option and option.get("eligible", True) and option.get("type") != "reference":
            result.append(option_id)
    return result


def validate_unique(values: list[str], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValidationError(f"Duplicate {label}.", {"values": values})
