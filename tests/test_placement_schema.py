"""Tests for placement schema merge."""

import yaml

from aoj_mr_studio.placement_schema import (
    PlacementConfig,
    apply_placement_to_yaml_text,
    placement_from_dict,
)


def test_placement_from_dict_stackable_parent() -> None:
    data = {
        "placement": {
            "surfaceType": 0,
            "providesAnchor": True,
            "anchorTarget": "Top",
        }
    }
    config = placement_from_dict(data)
    assert config.surface_type == 0
    assert config.provides_anchor is True
    assert config.anchor_target == "Top"


def test_apply_placement_object_on_prop() -> None:
    base = "version: 1\nname: Phone\nmodel:\n  file: phone.glb\n"
    config = PlacementConfig(surface_type=5, provides_anchor=False, anchor_target="")
    merged = apply_placement_to_yaml_text(base, config)
    parsed = yaml.safe_load(merged)
    assert parsed["placement"]["surfaceType"] == 5


def test_placement_from_dict_stick_rotation() -> None:
    data = {
        "placement": {
            "surfaceType": 1,
            "allowStickRotation": True,
            "stickRotationAxis": 0,
            "stickRotationSpeed": 120,
        }
    }
    config = placement_from_dict(data)
    assert config.allow_stick_rotation is True
    assert config.stick_rotation_axis == 0
    assert config.stick_rotation_speed == 120.0


def test_apply_placement_stick_rotation() -> None:
    base = "version: 1\nname: Fan\nmodel:\n  file: fan.glb\n"
    config = PlacementConfig(
        surface_type=1,
        allow_stick_rotation=True,
        stick_rotation_axis=0,
        stick_rotation_speed=90.0,
    )
    merged = apply_placement_to_yaml_text(base, config)
    parsed = yaml.safe_load(merged)
    assert parsed["placement"]["allowStickRotation"] is True
    assert parsed["placement"]["stickRotationAxis"] == 0
