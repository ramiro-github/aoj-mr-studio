"""Load, edit, validate, and save object.yaml (schema v1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from aoj_mr_studio.config import OBJECT_YAML_NAME, YAML_VERSION


@dataclass
class Vector3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Vector3:
        if not data:
            return cls()
        return cls(
            x=float(data.get("x", 0)),
            y=float(data.get("y", 0)),
            z=float(data.get("z", 0)),
        )

    def to_dict(self) -> dict[str, float]:
        if self.x == 0 and self.y == 0 and self.z == 0:
            return {}
        return {"x": self.x, "y": self.y, "z": self.z}


@dataclass
class ObjectDefinition:
    version: int = YAML_VERSION
    name: str = ""
    display_name: str = ""
    author: str = ""
    model_file: str = ""
    model_scale: float = 1.0
    model_offset: Vector3 = field(default_factory=Vector3)
    model_rotation: Vector3 = field(default_factory=Vector3)
    surface_type: int = 0
    facing_axis: int = 0
    allow_stick_rotation: bool = False
    stick_rotation_axis: int = 0
    stick_rotation_speed: float = 90.0
    provides_anchor: bool = False
    anchor_target: str = ""
    collision_mode: str = "mesh"
    collision_convex: bool = True
    audio_file: str = ""
    audio_loop: bool = True
    audio_volume: float = 1.0
    audio_play_on_awake: bool = True
    audio_distance_min: float = 0.5
    audio_distance_max: float = 4.0
    components: list[str] = field(default_factory=list)
    grab_two_hands: bool = False
    grab_return_on_release: bool = True
    grab_hide_hands: bool = True
    grab_target: str = ""
    grab_return_duration: float = 0.15
    video_file: str = ""
    video_target: str = ""
    video_loop: bool = True
    video_play_on_awake: bool = True
    video_volume: float = 1.0
    rotator_target: str = ""
    rotator_axis: str = "y"
    rotator_speed: float = 180.0
    animator_clip: str = ""
    animator_target: str = ""
    animator_loop: bool = True
    animator_play_on_awake: bool = True
    animator_speed: float = 1.0

    @classmethod
    def default_for_package(cls, package_name: str) -> ObjectDefinition:
        slug = package_name.lower().replace(" ", "_")
        return cls(
            name=package_name,
            display_name=package_name,
            model_file=f"{slug}.glb",
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any], package_name: str = "") -> ObjectDefinition:
        model = data.get("model") or {}
        placement = data.get("placement") or {}
        collision = data.get("collision") or {}
        audio = data.get("audio") or {}
        distance = audio.get("distance") or {}
        grab = data.get("grab") or {}
        video = data.get("video") or {}
        rotator = data.get("rotator") or {}
        animator = data.get("animator") or {}
        raw_components = data.get("components") or []

        components: list[str] = []
        for entry in raw_components:
            if isinstance(entry, str):
                components.append(entry.lower())

        return cls(
            version=int(data.get("version", YAML_VERSION)),
            name=str(data.get("name") or package_name),
            display_name=str(data.get("displayName") or ""),
            author=str(data.get("author") or ""),
            model_file=str(model.get("file") or ""),
            model_scale=float(model.get("scale", 1.0) or 1.0),
            model_offset=Vector3.from_dict(model.get("offset")),
            model_rotation=Vector3.from_dict(model.get("rotation")),
            surface_type=int(placement.get("surfaceType", 0)),
            facing_axis=int(placement.get("facingAxis", 0)),
            allow_stick_rotation=bool(placement.get("allowStickRotation", False)),
            stick_rotation_axis=int(placement.get("stickRotationAxis", 0)),
            stick_rotation_speed=float(placement.get("stickRotationSpeed", 90)),
            provides_anchor=bool(placement.get("providesAnchor", False)),
            anchor_target=str(placement.get("anchorTarget") or ""),
            collision_mode=str(collision.get("mode") or "mesh"),
            collision_convex=bool(collision.get("convex", True)),
            audio_file=str(audio.get("file") or ""),
            audio_loop=bool(audio.get("loop", True)),
            audio_volume=float(audio.get("volume", 1.0)),
            audio_play_on_awake=bool(audio.get("playOnAwake", True)),
            audio_distance_min=float(distance.get("min", 0.5)),
            audio_distance_max=float(distance.get("max", 4.0)),
            components=components,
            grab_two_hands=bool(grab.get("twoHands", False)),
            grab_return_on_release=bool(grab.get("returnOnRelease", True)),
            grab_hide_hands=bool(grab.get("hideHands", True)),
            grab_target=str(grab.get("target") or ""),
            grab_return_duration=float(grab.get("returnDurationSeconds", 0.15)),
            video_file=str(video.get("file") or ""),
            video_target=str(video.get("target") or ""),
            video_loop=bool(video.get("loop", True)),
            video_play_on_awake=bool(video.get("playOnAwake", True)),
            video_volume=float(video.get("volume", 1.0)),
            rotator_target=str(rotator.get("target") or ""),
            rotator_axis=str(rotator.get("axis") or "y"),
            rotator_speed=float(rotator.get("speed", 180)),
            animator_clip=str(animator.get("clip") or ""),
            animator_target=str(animator.get("target") or ""),
            animator_loop=bool(animator.get("loop", True)),
            animator_play_on_awake=bool(animator.get("playOnAwake", True)),
            animator_speed=float(animator.get("speed", 1.0)),
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "version": self.version,
            "name": self.name,
        }
        if self.display_name:
            data["displayName"] = self.display_name
        if self.author:
            data["author"] = self.author

        model: dict[str, Any] = {"file": self.model_file}
        if self.model_scale != 1.0:
            model["scale"] = self.model_scale
        offset = self.model_offset.to_dict()
        if offset:
            model["offset"] = offset
        rotation = self.model_rotation.to_dict()
        if rotation:
            model["rotation"] = rotation
        data["model"] = model

        placement: dict[str, Any] = {
            "surfaceType": self.surface_type,
            "facingAxis": self.facing_axis,
        }
        if self.allow_stick_rotation:
            placement["allowStickRotation"] = True
            placement["stickRotationAxis"] = self.stick_rotation_axis
            if self.stick_rotation_speed != 90.0:
                placement["stickRotationSpeed"] = self.stick_rotation_speed
        if self.provides_anchor:
            placement["providesAnchor"] = True
        if self.anchor_target:
            placement["anchorTarget"] = self.anchor_target
        data["placement"] = placement

        if self.collision_mode != "mesh" or not self.collision_convex:
            data["collision"] = {
                "mode": self.collision_mode,
                "convex": self.collision_convex,
            }

        if self.audio_file:
            audio: dict[str, Any] = {
                "file": self.audio_file,
                "loop": self.audio_loop,
                "volume": self.audio_volume,
                "playOnAwake": self.audio_play_on_awake,
            }
            if self.audio_distance_min != 0.5 or self.audio_distance_max != 4.0:
                audio["distance"] = {
                    "min": self.audio_distance_min,
                    "max": self.audio_distance_max,
                }
            data["audio"] = audio

        if self.components:
            data["components"] = list(self.components)

        if "grab" in self.components:
            grab: dict[str, Any] = {
                "twoHands": self.grab_two_hands,
                "returnOnRelease": self.grab_return_on_release,
                "hideHands": self.grab_hide_hands,
            }
            if self.grab_target:
                grab["target"] = self.grab_target
            if self.grab_return_duration != 0.15:
                grab["returnDurationSeconds"] = self.grab_return_duration
            data["grab"] = grab

        if "video" in self.components:
            data["video"] = {
                "file": self.video_file,
                "target": self.video_target,
                "loop": self.video_loop,
                "playOnAwake": self.video_play_on_awake,
                "volume": self.video_volume,
            }

        if "rotator" in self.components:
            rotator: dict[str, Any] = {
                "target": self.rotator_target,
                "axis": self.rotator_axis,
                "speed": self.rotator_speed,
            }
            data["rotator"] = rotator

        if "animator" in self.components:
            animator: dict[str, Any] = {
                "clip": self.animator_clip,
                "loop": self.animator_loop,
                "playOnAwake": self.animator_play_on_awake,
            }
            if self.animator_target:
                animator["target"] = self.animator_target
            if self.animator_speed != 1.0:
                animator["speed"] = self.animator_speed
            data["animator"] = animator

        return data

    def validate(self, package_dir: Path) -> list[str]:
        errors: list[str] = []
        if not self.name.strip():
            errors.append("name is required")
        if not self.model_file.strip():
            errors.append("model.file is required")
        elif not (package_dir / self.model_file).is_file():
            errors.append(f"model file not found: {self.model_file}")

        if self.surface_type not in range(6):
            errors.append(f"surfaceType must be 0–5, got {self.surface_type}")

        if self.collision_mode not in ("mesh", "box", "none"):
            errors.append(f"collision.mode must be mesh|box|none, got {self.collision_mode}")

        for component in self.components:
            if component not in ("grab", "video", "rotator", "animator"):
                errors.append(f"unknown component: {component}")

        if "video" in self.components:
            if not self.video_file:
                errors.append("video.file is required when video component is enabled")
            if not self.video_target:
                errors.append("video.target is required when video component is enabled")
            elif self.video_file and not (package_dir / self.video_file).is_file():
                errors.append(f"video file not found: {self.video_file}")

        if "rotator" in self.components and not self.rotator_target:
            errors.append("rotator.target is required when rotator component is enabled")

        if "animator" in self.components and not self.animator_clip:
            errors.append("animator.clip is required when animator component is enabled")

        if self.audio_file and not (package_dir / self.audio_file).is_file():
            errors.append(f"audio file not found: {self.audio_file}")

        return errors


def load_object_yaml(package_dir: Path) -> ObjectDefinition:
    yaml_path = package_dir / OBJECT_YAML_NAME
    if not yaml_path.is_file():
        return ObjectDefinition.default_for_package(package_dir.name)

    with yaml_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    if not isinstance(raw, dict):
        raise ValueError(f"{yaml_path}: expected YAML mapping at root")

    return ObjectDefinition.from_dict(raw, package_name=package_dir.name)


def save_object_yaml(package_dir: Path, definition: ObjectDefinition) -> None:
    package_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = package_dir / OBJECT_YAML_NAME
    payload = definition.to_dict()
    header = (
        "# Age of Joy — MR custom object (schema v1)\n"
        "# Edited with AOJ MR Studio\n\n"
    )
    body = yaml.dump(
        payload,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )
    yaml_path.write_text(header + body, encoding="utf-8")
