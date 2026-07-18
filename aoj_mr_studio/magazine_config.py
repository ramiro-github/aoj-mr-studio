"""Quest magazine shelf activation configuration (magazines.yaml)."""

from __future__ import annotations

from pathlib import Path

import yaml

from aoj_mr_studio.adb_sync import (
    AdbResult,
    RemoteEntry,
    pull_remote_file,
    push_remote_file,
    remote_file_exists,
)
from aoj_mr_studio.config import QUEST_MAGAZINES_YAML

MAGAZINE_SHELF_LIMIT = 9
MAGAZINES_YAML_NAME = "magazines.yaml"


def magazine_folder_names(entries: list[RemoteEntry]) -> list[str]:
    return sorted(
        (entry.name for entry in entries if entry.is_dir),
        key=str.casefold,
    )


def magazine_activation_map(entries: list[RemoteEntry]) -> dict[str, bool]:
    """Map magazine folders to shelf activation, enabling at most nine."""
    names = magazine_folder_names(entries)
    return {
        name: index < MAGAZINE_SHELF_LIMIT
        for index, name in enumerate(names)
    }


def dump_activation_map(activation: dict[str, bool]) -> str:
    return yaml.safe_dump(
        activation,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )


def magazine_config_text(entries: list[RemoteEntry]) -> str:
    return dump_activation_map(magazine_activation_map(entries))


def active_magazine_count(activation: dict[str, bool]) -> int:
    return sum(1 for enabled in activation.values() if enabled)


def sync_activation_with_folders(
    activation: dict[str, bool],
    entries: list[RemoteEntry],
) -> dict[str, bool]:
    """Keep only existing folders and add missing ones as inactive."""
    names = magazine_folder_names(entries)
    synced: dict[str, bool] = {}
    for name in names:
        synced[name] = bool(activation.get(name, False))

    # Cap at shelf limit if the YAML somehow has more than nine active.
    if active_magazine_count(synced) > MAGAZINE_SHELF_LIMIT:
        enabled = 0
        for name in names:
            if synced[name]:
                enabled += 1
                if enabled > MAGAZINE_SHELF_LIMIT:
                    synced[name] = False
    return synced


def local_magazines_yaml_path(cache_root: Path) -> Path:
    return cache_root / "magazines" / MAGAZINES_YAML_NAME


def ensure_magazines_yaml(
    entries: list[RemoteEntry],
    cache_root: Path,
) -> tuple[AdbResult, bool]:
    """Create magazines.yaml when absent. Returns (result, created)."""
    exists_result, exists = remote_file_exists(QUEST_MAGAZINES_YAML)
    if not exists_result.ok:
        return exists_result, False
    if exists:
        return AdbResult(True, "magazines.yaml already exists"), False

    result = save_magazines_yaml(magazine_activation_map(entries), cache_root)
    return result, result.ok


def load_magazines_yaml(
    entries: list[RemoteEntry],
    cache_root: Path,
) -> tuple[AdbResult, dict[str, bool]]:
    """Pull magazines.yaml and sync it with the current folder list."""
    ensure_result, _created = ensure_magazines_yaml(entries, cache_root)
    if not ensure_result.ok:
        return ensure_result, {}

    local_yaml = local_magazines_yaml_path(cache_root)
    pull = pull_remote_file(QUEST_MAGAZINES_YAML, local_yaml)
    if not pull.ok:
        return pull, {}

    try:
        parsed = yaml.safe_load(local_yaml.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return AdbResult(False, f"Invalid magazines.yaml: {exc}"), {}

    if not isinstance(parsed, dict):
        return AdbResult(False, "magazines.yaml must be a mapping of name: true/false"), {}

    activation = {
        str(name): bool(enabled)
        for name, enabled in parsed.items()
        if str(name) != MAGAZINES_YAML_NAME
    }
    return AdbResult(True, "Loaded magazines.yaml"), sync_activation_with_folders(
        activation,
        entries,
    )


def save_magazines_yaml(
    activation: dict[str, bool],
    cache_root: Path,
) -> AdbResult:
    local_yaml = local_magazines_yaml_path(cache_root)
    local_yaml.parent.mkdir(parents=True, exist_ok=True)
    local_yaml.write_text(dump_activation_map(activation), encoding="utf-8")
    push = push_remote_file(local_yaml, QUEST_MAGAZINES_YAML)
    if not push.ok:
        return push
    return AdbResult(True, "Saved magazines.yaml to Meta Quest.")
