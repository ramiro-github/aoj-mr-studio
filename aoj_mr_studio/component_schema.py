"""Schema and YAML merge for MR custom object components."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import yaml

from aoj_mr_studio.config import COMPONENT_IDS

FieldKind = Literal["bool", "str", "float", "choice"]


@dataclass(frozen=True)
class FieldSpec:
    key: str
    label: str
    kind: FieldKind
    default: bool | str | float
    choices: tuple[str, ...] = ()


COMPONENT_SCHEMAS: dict[str, tuple[FieldSpec, ...]] = {
    "grab": (
        FieldSpec("twoHands", "twoHands", "bool", False),
        FieldSpec("returnOnRelease", "returnOnRelease", "bool", True),
        FieldSpec("hideHands", "hideHands", "bool", True),
        FieldSpec("target", "target", "str", ""),
        FieldSpec("returnDurationSeconds", "returnDurationSeconds", "float", 0.15),
    ),
    "video": (
        FieldSpec("file", "file", "str", ""),
        FieldSpec("target", "target", "str", ""),
        FieldSpec("loop", "loop", "bool", True),
        FieldSpec("playOnAwake", "playOnAwake", "bool", True),
        FieldSpec("volume", "volume", "float", 1.0),
        FieldSpec("invertX", "invertX", "bool", False),
        FieldSpec("invertY", "invertY", "bool", False),
    ),
    "rotator": (
        FieldSpec("target", "target (GLB child)", "str", ""),
        FieldSpec("axis", "axis", "choice", "y", ("x", "y", "z", "-x", "-y", "-z")),
        FieldSpec("speed", "speed °/s", "float", 180.0),
    ),
    "animator": (
        FieldSpec("clip", "clip (GLB animation)", "str", ""),
        FieldSpec("target", "target (GLB child)", "str", ""),
        FieldSpec("loop", "loop", "bool", True),
        FieldSpec("playOnAwake", "playOnAwake", "bool", True),
        FieldSpec("speed", "speed", "float", 1.0),
    ),
}


def component_rows_from_dict(data: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    rows: list[tuple[str, dict[str, Any]]] = []
    for entry in data.get("components") or []:
        if not isinstance(entry, str):
            continue
        comp_id = entry.lower()
        if comp_id not in COMPONENT_SCHEMAS:
            continue
        block = data.get(comp_id)
        config = block if isinstance(block, dict) else {}
        rows.append((comp_id, dict(config)))
    return rows


def _coerce_value(field: FieldSpec, raw: Any) -> bool | str | float:
    if field.kind == "bool":
        return bool(raw)
    if field.kind == "float":
        try:
            return float(raw)
        except (TypeError, ValueError):
            return float(field.default)
    if field.kind == "choice":
        value = str(raw if raw is not None else field.default)
        return value if value in field.choices else str(field.default)
    return str(raw if raw is not None else "")


def normalize_component_config(comp_id: str, config: dict[str, Any]) -> dict[str, Any]:
    schema = COMPONENT_SCHEMAS[comp_id]
    normalized: dict[str, Any] = {}
    for field in schema:
        raw = config.get(field.key, field.default)
        normalized[field.key] = _coerce_value(field, raw)
    return normalized


def serialize_component_block(comp_id: str, config: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_component_config(comp_id, config)

    if comp_id == "grab":
        block: dict[str, Any] = {
            "twoHands": normalized["twoHands"],
            "returnOnRelease": normalized["returnOnRelease"],
            "hideHands": normalized["hideHands"],
        }
        if normalized["target"]:
            block["target"] = normalized["target"]
        if normalized["returnDurationSeconds"] != 0.15:
            block["returnDurationSeconds"] = normalized["returnDurationSeconds"]
        return block

    if comp_id == "video":
        block = {}
        if normalized["file"]:
            block["file"] = normalized["file"]
        if normalized["target"]:
            block["target"] = normalized["target"]
        block["loop"] = normalized["loop"]
        block["playOnAwake"] = normalized["playOnAwake"]
        if normalized["volume"] != 1.0:
            block["volume"] = normalized["volume"]
        if normalized["invertX"]:
            block["invertX"] = True
        if normalized["invertY"]:
            block["invertY"] = True
        return block

    if comp_id == "rotator":
        block: dict[str, Any] = {
            "target": normalized["target"],
            "axis": normalized["axis"],
            "speed": normalized["speed"],
        }
        return block

    if comp_id == "animator":
        block: dict[str, Any] = {
            "clip": normalized["clip"],
            "loop": normalized["loop"],
            "playOnAwake": normalized["playOnAwake"],
        }
        if normalized["target"]:
            block["target"] = normalized["target"]
        if normalized["speed"] != 1.0:
            block["speed"] = normalized["speed"]
        return block

    return {}


def validate_component_rows(rows: list[tuple[str, dict[str, Any]]]) -> list[str]:
    errors: list[str] = []
    for comp_id, config in rows:
        normalized = normalize_component_config(comp_id, config)
        if comp_id == "rotator" and not str(normalized["target"]).strip():
            errors.append("rotator: target (GLB child name) is required — e.g. Blades")
        if comp_id == "video":
            if not str(normalized["file"]).strip():
                errors.append("video: file is required")
            if not str(normalized["target"]).strip():
                errors.append("video: target (GLB screen mesh) is required")
        if comp_id == "animator" and not str(normalized["clip"]).strip():
            errors.append("animator: clip (GLB animation name) is required")
    return errors


def apply_components_to_yaml_text(
    yaml_text: str,
    rows: list[tuple[str, dict[str, Any]]],
) -> str:
    parsed = yaml.safe_load(yaml_text) if yaml_text.strip() else {}
    if parsed is None:
        parsed = {}
    if not isinstance(parsed, dict):
        raise ValueError("object.yaml root must be a mapping")

    parsed.pop("components", None)
    for comp_id in COMPONENT_IDS:
        parsed.pop(comp_id, None)

    if rows:
        parsed["components"] = [comp_id for comp_id, _config in rows]
        for comp_id, config in rows:
            parsed[comp_id] = serialize_component_block(comp_id, config)

    header = ""
    body = yaml_text
    if body.startswith("#"):
        parts = body.split("\n\n", 1)
        if len(parts) == 2:
            header = parts[0] + "\n\n"
            body = parts[1]

    dumped = yaml.dump(
        parsed,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )
    if not header:
        header = (
            "# Age of Joy — MR custom object (schema v1)\n"
            "# Edited with AOJ MR Studio\n\n"
        )
    return header + dumped
