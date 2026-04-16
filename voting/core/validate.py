from __future__ import annotations

from .errors import ValidationError


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
