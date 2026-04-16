from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .errors import InvalidProject, UserError
from .ids import record_id, validate_id
from .project import Project


def read_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError as exc:
        raise UserError(f"File not found: {path}", {"path": str(path)}) from exc
    except json.JSONDecodeError as exc:
        raise InvalidProject(f"Invalid JSON in {path}: {exc}", {"path": str(path)}) from exc
    if not isinstance(data, dict):
        raise InvalidProject(f"Expected JSON object in {path}.", {"path": str(path)})
    return data


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def entity_path(project: Project, collection: str, entity_id: str) -> Path:
    validate_id(entity_id)
    return project.path(collection, f"{entity_id}.json")


def write_entity(project: Project, collection: str, entity_id: str, data: dict, overwrite: bool = False) -> Path:
    path = entity_path(project, collection, entity_id)
    if path.exists() and not overwrite:
        raise UserError(f"{collection[:-1].title()} already exists: {entity_id}", {"id": entity_id})
    write_json(path, data)
    return path


def read_entity(project: Project, collection: str, entity_id: str) -> dict:
    return read_json(entity_path(project, collection, entity_id))


def list_entities(project: Project, collection: str) -> list[dict]:
    return [read_json(path) for path in sorted(project.path(collection).glob("*.json"))]


def append_record(project: Project, collection: str, descriptor_parts: Iterable[str], data: dict) -> tuple[str, Path]:
    clean_parts = [validate_id(str(part), "descriptor part") for part in descriptor_parts]
    rid = record_id("_".join(clean_parts))
    path = project.path(collection, f"{rid}.json")
    data = {"id": rid, **data}
    write_json(path, data)
    return rid, path


def list_records(project: Project, collection: str) -> list[tuple[str, dict]]:
    return [(path.stem, read_json(path)) for path in sorted(project.path(collection).glob("*.json"))]
