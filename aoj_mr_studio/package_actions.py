"""Create packages and upload GLB models to Quest."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from aoj_mr_studio.adb_sync import (
    AdbResult,
    create_remote_dir,
    push_remote_file,
    remote_dir_exists,
    remote_file_exists,
)
from aoj_mr_studio.config import QUEST_CUSTOM_OBJECTS

_INVALID_PACKAGE_CHARS = re.compile(r'[\\/:*?"<>|]')


@dataclass
class PushModelResult:
    ok: bool
    message: str
    file_name: str = ""
    replaced: bool = False


def validate_package_name(name: str) -> str | None:
    cleaned = name.strip()
    if not cleaned:
        return "Package name is required."
    if cleaned in (".", ".."):
        return "Invalid package name."
    if _INVALID_PACKAGE_CHARS.search(cleaned):
        return 'Package name cannot contain \\ / : * ? " < > |'
    return None


def remote_package_path(package_name: str) -> str:
    return f"{QUEST_CUSTOM_OBJECTS.rstrip('/')}/{package_name.strip()}"


def create_quest_package(package_name: str) -> AdbResult:
    error = validate_package_name(package_name)
    if error:
        return AdbResult(False, error)

    remote = remote_package_path(package_name)
    exists_result, exists = remote_dir_exists(remote)
    if not exists_result.ok:
        return exists_result
    if exists:
        return AdbResult(False, f"Package folder already exists: {package_name}")

    return create_remote_dir(remote)


def push_model_to_package(package_name: str, local_glb: Path) -> PushModelResult:
    error = validate_package_name(package_name)
    if error:
        return PushModelResult(False, error)

    if not local_glb.is_file():
        return PushModelResult(False, f"File not found: {local_glb}")

    if local_glb.suffix.lower() != ".glb":
        return PushModelResult(False, "Model must be a .glb file")

    remote_dir = remote_package_path(package_name)
    exists_result, exists = remote_dir_exists(remote_dir)
    if not exists_result.ok:
        return PushModelResult(False, exists_result.message)
    if not exists:
        return PushModelResult(False, f"Package folder not found on Quest: {package_name}")

    glb_name = local_glb.name
    remote_file = f"{remote_dir}/{glb_name}"
    file_exists_result, already_on_quest = remote_file_exists(remote_file)
    if not file_exists_result.ok:
        return PushModelResult(False, file_exists_result.message)

    push = push_remote_file(local_glb, remote_file)
    if not push.ok:
        return PushModelResult(False, push.message, file_name=glb_name, replaced=already_on_quest)

    if already_on_quest:
        message = f"Replaced {glb_name} on Quest."
    else:
        message = f"Uploaded {glb_name} to Quest."

    return PushModelResult(True, message, file_name=glb_name, replaced=already_on_quest)
