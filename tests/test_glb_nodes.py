"""Tests for GLB node name extraction and package defaults."""

import json
import struct
from pathlib import Path

from aoj_mr_studio.glb_nodes import (
    list_animator_target_candidates,
    read_glb_animation_names,
    read_glb_node_names,
    suggest_animator_clip,
    suggest_animator_target,
    suggest_light_target,
    suggest_rotator_target,
)
from aoj_mr_studio.package_defaults import PackageContext, suggest_component_config


def _write_minimal_glb(
    path: Path,
    node_names: list[str],
    animation_names: list[str] | None = None,
    *,
    animation_payload: list[dict[str, object]] | None = None,
) -> None:
    payload: dict[str, object] = {"nodes": [{"name": name} for name in node_names]}
    if animation_payload is not None:
        payload["animations"] = animation_payload
    elif animation_names:
        payload["animations"] = [{"name": name} for name in animation_names]
    json_chunk = json.dumps(payload).encode("utf-8")
    json_chunk += b" " * ((4 - len(json_chunk) % 4) % 4)
    header = b"glTF" + struct.pack("<II", 2, 12 + 8 + len(json_chunk))
    chunk = struct.pack("<I4s", len(json_chunk), b"JSON") + json_chunk
    path.write_bytes(header + chunk)


def test_read_glb_node_names(tmp_path: Path) -> None:
    glb = tmp_path / "fan.glb"
    _write_minimal_glb(glb, ["Root", "Blades", "Base"])
    assert read_glb_node_names(glb) == ["Root", "Blades", "Base"]


def test_suggest_rotator_target_prefers_blades() -> None:
    assert suggest_rotator_target(["Root", "Blades", "Base"]) == "Blades"


def test_read_glb_animation_names(tmp_path: Path) -> None:
    glb = tmp_path / "character.glb"
    _write_minimal_glb(glb, ["Root", "Character"], ["Idle", "Walk"])
    assert read_glb_animation_names(glb) == ["Idle", "Walk"]


def test_read_glb_animation_names_unnamed_uses_node(tmp_path: Path) -> None:
    glb = tmp_path / "character.glb"
    _write_minimal_glb(
        glb,
        ["Root", "Armature"],
        animation_payload=[{"channels": [{"target": {"node": 1}}]}],
    )
    assert read_glb_animation_names(glb) == ["Armature"]


def test_read_glb_animation_names_unnamed_fallback_index(tmp_path: Path) -> None:
    glb = tmp_path / "prop.glb"
    _write_minimal_glb(glb, ["Root"], animation_payload=[{"channels": []}])
    assert read_glb_animation_names(glb) == ["Animation_0"]


def test_merge_component_config_fills_empty_clip() -> None:
    from aoj_mr_studio.package_defaults import merge_component_config

    merged = merge_component_config(
        "animator",
        {"clip": "", "target": "", "loop": True, "playOnAwake": True, "speed": 1.0},
        {"clip": "Walk", "target": "Character", "loop": True, "playOnAwake": True, "speed": 1.0},
    )
    assert merged["clip"] == "Walk"
    assert merged["target"] == "Character"


def test_merge_component_config_keeps_explicit_clip() -> None:
    from aoj_mr_studio.package_defaults import merge_component_config

    merged = merge_component_config(
        "animator",
        {"clip": "Run", "target": "", "loop": True, "playOnAwake": True, "speed": 1.0},
        {"clip": "Walk", "target": "Character", "loop": True, "playOnAwake": True, "speed": 1.0},
    )
    assert merged["clip"] == "Run"
    assert merged["target"] == "Character"


def test_suggest_animator_clip() -> None:
    assert suggest_animator_clip(["Idle", "Walk"]) == "Idle"
    assert suggest_animator_clip([]) == ""


def test_suggest_animator_target_prefers_armature() -> None:
    nodes = ["Root", "Armature", "Body.001", "mixamorig:Hips", "mixamorig:HeadTop_End"]
    assert suggest_animator_target(nodes) == "Armature"


def test_suggest_animator_target_skips_bones_and_mesh_without_rig_name() -> None:
    nodes = ["Root", "mixamorig:Hips", "mixamorig:HeadTop_End", "Body.001", "Mesh_0"]
    assert suggest_animator_target(nodes) == ""


def test_list_animator_target_candidates_filters_bones_and_mesh() -> None:
    nodes = ["Root", "Armature", "mixamorig:Hips", "Body.001", "Mesh_0"]
    candidates = list_animator_target_candidates(nodes)
    assert candidates == ["Armature"]


def test_suggest_animator_target_from_skinned_glb(tmp_path: Path) -> None:
    glb = tmp_path / "character.glb"
    payload = {
        "nodes": [
            {"name": "Root", "children": [1, 2]},
            {"name": "Armature", "skin": 0, "children": [3]},
            {"name": "Body.001", "mesh": 0},
            {"name": "mixamorig:Hips"},
        ],
        "animations": [{"channels": [{"target": {"node": 3}}]}],
    }
    json_chunk = json.dumps(payload).encode("utf-8")
    json_chunk += b" " * ((4 - len(json_chunk) % 4) % 4)
    header = b"glTF" + struct.pack("<II", 2, 12 + 8 + len(json_chunk))
    chunk = struct.pack("<I4s", len(json_chunk), b"JSON") + json_chunk
    glb.write_bytes(header + chunk)

    node_names = read_glb_node_names(glb)
    assert suggest_animator_target(node_names, glb) == "Armature"


def test_merge_component_config_replaces_bone_target() -> None:
    from aoj_mr_studio.package_defaults import merge_component_config

    merged = merge_component_config(
        "animator",
        {
            "clip": "Walk",
            "target": "mixamorig:HeadTop_End",
            "loop": True,
            "playOnAwake": True,
            "speed": 1.0,
        },
        {"clip": "Walk", "target": "Armature", "loop": True, "playOnAwake": True, "speed": 1.0},
    )
    assert merged["target"] == "Armature"


def test_suggest_component_config_animator(tmp_path: Path) -> None:
    context = PackageContext(
        package_name="Character",
        remote_path="/quest/Custom Objects/Character",
        cache_root=tmp_path,
        glb_node_names=["Root", "Character"],
        glb_animation_names=["Idle", "Walk"],
        model_file="character.glb",
    )
    config = suggest_component_config("animator", context)
    assert config["clip"] == "Idle"
    assert config["target"] == "Character"
    assert config["loop"] is True


def test_suggest_component_config_animator_rigged_character(tmp_path: Path) -> None:
    glb = tmp_path / "character.glb"
    _write_minimal_glb(
        glb,
        ["Root", "Armature", "Body.001", "mixamorig:HeadTop_End"],
        ["Armature|mixamo.com|Layer0"],
    )
    context = PackageContext(
        package_name="Character",
        remote_path="/quest/Custom Objects/Character",
        cache_root=tmp_path,
        glb_node_names=["Root", "Armature", "Body.001", "mixamorig:HeadTop_End"],
        glb_animation_names=["Armature|mixamo.com|Layer0"],
        model_file="character.glb",
        local_glb_path=glb,
    )
    config = suggest_component_config("animator", context)
    assert config["clip"] == "Armature|mixamo.com|Layer0"
    assert config["target"] == "Armature"


def test_suggest_component_config_rotator(tmp_path: Path) -> None:
    context = PackageContext(
        package_name="Fan",
        remote_path="/quest/Custom Objects/Fan",
        cache_root=tmp_path,
        glb_node_names=["Root", "Blades"],
        model_file="fan.glb",
    )
    config = suggest_component_config("rotator", context)
    assert config["target"] == "Blades"
    assert config["axis"] == "y"
    assert config["speed"] == 180.0


def test_suggest_light_target_prefers_bulb() -> None:
    assert suggest_light_target(["Root", "Shade", "Bulb"]) == "Bulb"
    assert suggest_light_target(["Root", "Base"]) == ""


def test_suggest_component_config_light(tmp_path: Path) -> None:
    context = PackageContext(
        package_name="Lamp",
        remote_path="/quest/Custom Objects/Lamp",
        cache_root=tmp_path,
        glb_node_names=["Root", "Bulb", "Shade"],
        model_file="lamp.glb",
    )
    config = suggest_component_config("light", context)
    assert config["target"] == "Bulb"
    assert config["type"] == "point"
    assert config["intensity"] == 2.0
    assert config["range"] == 4.0
    assert config["color"] == "#ffffff"
    assert config["shadows"] is False
