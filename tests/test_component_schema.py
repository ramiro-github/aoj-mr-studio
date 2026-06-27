"""Tests for component schema merge."""

from aoj_mr_studio.component_schema import (
    apply_components_to_yaml_text,
    component_rows_from_dict,
    serialize_component_block,
)

import yaml


def test_component_rows_from_dict() -> None:
    data = {
        "components": ["grab", "rotator"],
        "grab": {"twoHands": True},
        "rotator": {"target": "Blades", "axis": "y", "speed": 90},
    }
    rows = component_rows_from_dict(data)
    assert rows[0][0] == "grab"
    assert rows[0][1]["twoHands"] is True
    assert rows[1][0] == "rotator"
    assert rows[1][1]["target"] == "Blades"


def test_apply_components_to_yaml_text() -> None:
    base = "version: 1\nname: Leon\nmodel:\n  file: leon.glb\n"
    rows = [
        (
            "grab",
            {
                "twoHands": False,
                "returnOnRelease": True,
                "hideHands": True,
                "target": "",
                "returnDurationSeconds": 0.15,
            },
        ),
    ]
    merged = apply_components_to_yaml_text(base, rows)
    parsed = yaml.safe_load(merged)
    assert parsed["components"] == ["grab"]
    assert parsed["grab"]["returnOnRelease"] is True
    assert parsed["model"]["file"] == "leon.glb"


def test_validate_rotator_requires_target() -> None:
    from aoj_mr_studio.component_schema import validate_component_rows

    errors = validate_component_rows([("rotator", {"target": "", "axis": "y", "speed": 180})])
    assert any("rotator" in error for error in errors)


def test_serialize_rotator_includes_target() -> None:
    block = serialize_component_block(
        "rotator",
        {"target": "Blades", "axis": "y", "speed": 180},
    )
    assert block["target"] == "Blades"
    assert block["axis"] == "y"

    block = serialize_component_block(
        "video",
        {
            "file": "screen.mp4",
            "target": "Screen",
            "loop": True,
            "playOnAwake": True,
            "volume": 1.0,
            "invertX": True,
            "invertY": False,
        },
    )
    assert block["invertX"] is True
    assert "invertY" not in block


def test_validate_animator_requires_clip() -> None:
    from aoj_mr_studio.component_schema import validate_component_rows

    errors = validate_component_rows(
        [("animator", {"clip": "", "target": "Character", "loop": True, "playOnAwake": True, "speed": 1.0})]
    )
    assert any("animator" in error for error in errors)


def test_serialize_animator() -> None:
    block = serialize_component_block(
        "animator",
        {
            "clip": "Walk",
            "target": "Character",
            "loop": True,
            "playOnAwake": True,
            "speed": 1.0,
        },
    )
    assert block["clip"] == "Walk"
    assert block["target"] == "Character"
    assert "speed" not in block
