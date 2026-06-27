"""Parse and merge placement block in object.yaml."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yaml

from aoj_mr_studio.config import SURFACE_TYPES


@dataclass
class PlacementConfig:
    surface_type: int = 0
    provides_anchor: bool = False
    anchor_target: str = ""
    allow_stick_rotation: bool = False
    stick_rotation_axis: int = 0
    stick_rotation_speed: float = 90.0


def placement_from_dict(data: dict[str, Any]) -> PlacementConfig:
    placement = data.get("placement") or {}
    if not isinstance(placement, dict):
        placement = {}

    surface_type = int(placement.get("surfaceType", 0))
    if surface_type not in SURFACE_TYPES:
        surface_type = 0

    return PlacementConfig(
        surface_type=surface_type,
        provides_anchor=bool(placement.get("providesAnchor", False)),
        anchor_target=str(placement.get("anchorTarget") or ""),
        allow_stick_rotation=bool(placement.get("allowStickRotation", False)),
        stick_rotation_axis=int(placement.get("stickRotationAxis", 0)),
        stick_rotation_speed=float(placement.get("stickRotationSpeed", 90) or 90),
    )


def serialize_placement(config: PlacementConfig) -> dict[str, Any]:
    placement: dict[str, Any] = {
        "surfaceType": config.surface_type,
        "facingAxis": 0,
    }
    if config.provides_anchor:
        placement["providesAnchor"] = True
    if config.anchor_target.strip():
        placement["anchorTarget"] = config.anchor_target.strip()
    if config.allow_stick_rotation:
        placement["allowStickRotation"] = True
        placement["stickRotationAxis"] = config.stick_rotation_axis
        if config.stick_rotation_speed != 90.0:
            placement["stickRotationSpeed"] = config.stick_rotation_speed
    return placement


def apply_placement_to_yaml_text(yaml_text: str, config: PlacementConfig) -> str:
    parsed = yaml.safe_load(yaml_text) if yaml_text.strip() else {}
    if parsed is None:
        parsed = {}
    if not isinstance(parsed, dict):
        raise ValueError("object.yaml root must be a mapping")

    parsed["placement"] = serialize_placement(config)

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
