"""Paths and constants for Age of Joy MR custom objects."""

from __future__ import annotations

from pathlib import Path

APP_NAME = "AOJ MR Studio"
APP_VERSION = "0.1.0"
YAML_VERSION = 1
OBJECT_YAML_NAME = "object.yaml"

QUEST_PACKAGE = "com.curif.AgeOfJoy"
QUEST_MR_DIR = f"/sdcard/Android/data/{QUEST_PACKAGE}/MR"
QUEST_CUSTOM_OBJECTS = f"{QUEST_MR_DIR}/Custom Objects"
QUEST_MAGAZINES = f"{QUEST_MR_DIR}/Magazines"
QUEST_MAGAZINES_YAML = f"{QUEST_MAGAZINES}/magazines.yaml"

SURFACE_TYPES: dict[int, str] = {
    0: "Floor",
    1: "Wall",
    2: "Ceiling",
    3: "Free3D",
    4: "Table",
    5: "Object (on another prop)",
}

FACING_AXES: dict[int, str] = {
    0: "+Z",
    1: "-Z",
    2: "+X",
    3: "-X",
}

STICK_ROTATION_AXES: dict[int, str] = {
    0: "World yaw",
    1: "World pitch",
    2: "World roll",
}

COLLISION_MODES = ("mesh", "box", "none")
COMPONENT_IDS = ("grab", "video", "rotator", "animator", "light")


def default_local_custom_objects() -> Path:
    return Path.home() / "cabs" / "MR" / "Custom Objects"
