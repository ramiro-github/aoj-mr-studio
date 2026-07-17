"""Schema and YAML merge for MR custom object components."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import yaml

from aoj_mr_studio.config import COMPONENT_IDS

FieldKind = Literal["bool", "str", "float", "choice", "color"]


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
    "light": (
        FieldSpec("target", "target (GLB child)", "str", ""),
        FieldSpec("type", "type", "choice", "point", ("point", "spot")),
        FieldSpec("intensity", "intensity", "float", 2.0),
        FieldSpec("range", "range m", "float", 4.0),
        FieldSpec("color", "color", "color", "#ffffff"),
        FieldSpec("spotAngle", "spotAngle °", "float", 60.0),
        FieldSpec("innerSpotAngle", "innerSpotAngle °", "float", 30.0),
        FieldSpec("shadows", "shadows", "bool", False),
    ),
}


def rgb_floats_to_hex(r: float, g: float, b: float) -> str:
    def channel(value: float) -> int:
        try:
            return max(0, min(255, int(round(float(value) * 255.0))))
        except (TypeError, ValueError):
            return 255

    return f"#{channel(r):02x}{channel(g):02x}{channel(b):02x}"


def hex_to_rgb_floats(value: str) -> tuple[float, float, float]:
    hex_value = str(value or "").strip().lstrip("#")
    if len(hex_value) != 6:
        return 1.0, 1.0, 1.0
    try:
        return (
            int(hex_value[0:2], 16) / 255.0,
            int(hex_value[2:4], 16) / 255.0,
            int(hex_value[4:6], 16) / 255.0,
        )
    except ValueError:
        return 1.0, 1.0, 1.0


def normalize_hex_color(value: Any, default: str = "#ffffff") -> str:
    if isinstance(value, dict):
        return rgb_floats_to_hex(
            float(value.get("r", 1.0)),
            float(value.get("g", 1.0)),
            float(value.get("b", 1.0)),
        )
    text = str(value if value is not None else default).strip()
    if not text:
        return default
    if not text.startswith("#"):
        text = f"#{text}"
    if len(text) != 7:
        return default
    try:
        int(text[1:], 16)
    except ValueError:
        return default
    return text.lower()


def is_valid_hex_color(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    if not text.startswith("#"):
        text = f"#{text}"
    if len(text) != 7:
        return False
    try:
        int(text[1:], 16)
    except ValueError:
        return False
    return True


def _expand_light_config(config: dict[str, Any]) -> dict[str, Any]:
    """Map YAML color: {r,g,b} (or legacy colorR/G/B) into a #rrggbb editor field."""
    expanded = dict(config)
    color = config.get("color")
    if isinstance(color, dict):
        expanded["color"] = rgb_floats_to_hex(
            float(color.get("r", 1.0)),
            float(color.get("g", 1.0)),
            float(color.get("b", 1.0)),
        )
    elif "colorR" in config or "colorG" in config or "colorB" in config:
        expanded["color"] = rgb_floats_to_hex(
            float(config.get("colorR", 1.0)),
            float(config.get("colorG", 1.0)),
            float(config.get("colorB", 1.0)),
        )
    elif color is not None:
        expanded["color"] = normalize_hex_color(color)
    return expanded


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
        if comp_id == "light":
            config = _expand_light_config(config)
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
    if field.kind == "color":
        return normalize_hex_color(raw, str(field.default))
    return str(raw if raw is not None else "")


def normalize_component_config(comp_id: str, config: dict[str, Any]) -> dict[str, Any]:
    schema = COMPONENT_SCHEMAS[comp_id]
    if comp_id == "light":
        config = _expand_light_config(config)
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

    if comp_id == "light":
        color_r, color_g, color_b = hex_to_rgb_floats(str(normalized["color"]))
        block: dict[str, Any] = {
            "type": normalized["type"],
            "intensity": normalized["intensity"],
            "range": normalized["range"],
            "color": {
                "r": round(color_r, 4),
                "g": round(color_g, 4),
                "b": round(color_b, 4),
            },
            "shadows": normalized["shadows"],
        }
        if normalized["target"]:
            block["target"] = normalized["target"]
        if normalized["type"] == "spot":
            block["spotAngle"] = normalized["spotAngle"]
            block["innerSpotAngle"] = normalized["innerSpotAngle"]
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
        if comp_id == "light":
            light_type = str(normalized["type"]).strip().lower()
            if light_type not in ("point", "spot"):
                errors.append("light: type must be point or spot")
            raw_color = config.get("color", normalized["color"])
            if isinstance(raw_color, str) and raw_color.strip() and not is_valid_hex_color(raw_color):
                errors.append("light: color must be a valid #rrggbb hex value")
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
