"""Load and save object.yaml for a Quest package folder."""

from __future__ import annotations

from pathlib import Path

import yaml

from aoj_mr_studio.adb_sync import (
    pull_remote_file,
    push_remote_file,
    remote_file_exists,
    list_remote_dir,
)
from aoj_mr_studio.config import OBJECT_YAML_NAME
from aoj_mr_studio.yaml_model import ObjectDefinition, save_object_yaml


def remote_yaml_path(package_remote_path: str) -> str:
    base = package_remote_path.rstrip("/")
    return f"{base}/{OBJECT_YAML_NAME}"


def local_cache_path(cache_root: Path, package_name: str) -> Path:
    return cache_root / package_name


def local_yaml_path(cache_root: Path, package_name: str) -> Path:
    return local_cache_path(cache_root, package_name) / OBJECT_YAML_NAME


def first_glb_in_package(package_remote_path: str) -> str | None:
    _result, entries = list_remote_dir(package_remote_path)
    for entry in entries:
        if not entry.is_dir and entry.name.lower().endswith(".glb"):
            return entry.name
    return None


def pull_package_yaml(
    package_remote_path: str,
    package_name: str,
    cache_root: Path,
) -> tuple[bool, str, str]:
    """Return (exists_on_quest, yaml_text, status_message)."""
    remote_yaml = remote_yaml_path(package_remote_path)
    local_yaml = local_yaml_path(cache_root, package_name)

    exists_result, exists = remote_file_exists(remote_yaml)
    if not exists_result.ok:
        return False, "", exists_result.message

    if not exists:
        return False, "", f"No {OBJECT_YAML_NAME} on Quest — create one below."

    pull = pull_remote_file(remote_yaml, local_yaml)
    if not pull.ok:
        return True, "", pull.message

    text = local_yaml.read_text(encoding="utf-8")
    return True, text, f"Loaded {OBJECT_YAML_NAME} from Quest."


def default_yaml_text(
    package_name: str,
    cache_root: Path,
    model_file: str | None = None,
) -> str:
    definition = ObjectDefinition.default_for_package(package_name)
    if model_file:
        definition.model_file = model_file

    package_dir = local_cache_path(cache_root, package_name)
    package_dir.mkdir(parents=True, exist_ok=True)
    save_object_yaml(package_dir, definition)
    return local_yaml_path(cache_root, package_name).read_text(encoding="utf-8")


def save_yaml_to_quest(
    package_remote_path: str,
    package_name: str,
    cache_root: Path,
    yaml_text: str,
) -> tuple[bool, str]:
    try:
        parsed = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        return False, f"Invalid YAML: {exc}"

    if parsed is not None and not isinstance(parsed, dict):
        return False, f"{OBJECT_YAML_NAME} must be a YAML mapping at the root."

    local_dir = local_cache_path(cache_root, package_name)
    local_dir.mkdir(parents=True, exist_ok=True)
    local_yaml = local_yaml_path(cache_root, package_name)
    local_yaml.write_text(yaml_text if yaml_text.endswith("\n") else yaml_text + "\n", encoding="utf-8")

    remote_yaml = remote_yaml_path(package_remote_path)
    push = push_remote_file(local_yaml, remote_yaml)
    if not push.ok:
        return False, push.message

    return True, f"Saved {OBJECT_YAML_NAME} to Quest."


def ensure_default_yaml_on_quest(
    package_remote_path: str,
    package_name: str,
    cache_root: Path,
    model_file: str,
) -> tuple[bool, bool, str]:
    """Create default object.yaml on Quest when missing. Returns (ok, created, message)."""
    remote_yaml = remote_yaml_path(package_remote_path)
    exists_result, exists = remote_file_exists(remote_yaml)
    if not exists_result.ok:
        return False, False, exists_result.message

    if exists:
        return True, False, f"{OBJECT_YAML_NAME} already on Quest."

    yaml_text = default_yaml_text(package_name, cache_root, model_file=model_file)
    ok, message = save_yaml_to_quest(package_remote_path, package_name, cache_root, yaml_text)
    if not ok:
        return False, False, message

    return True, True, f"Created default {OBJECT_YAML_NAME} with model.file: {model_file}"
