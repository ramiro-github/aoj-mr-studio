"""Tests for magazine shelf activation configuration."""

from pathlib import Path
from unittest.mock import patch

import yaml

from aoj_mr_studio.adb_sync import AdbResult, RemoteEntry
from aoj_mr_studio.magazine_config import (
    MAGAZINE_SHELF_LIMIT,
    active_magazine_count,
    ensure_magazines_yaml,
    load_magazines_yaml,
    magazine_activation_map,
    magazine_config_text,
    save_magazines_yaml,
    sync_activation_with_folders,
)


def magazine_entries(count: int) -> list[RemoteEntry]:
    return [
        RemoteEntry(name=f"Magazine {number:02d}", is_dir=True)
        for number in range(1, count + 1)
    ]


def test_activation_map_enables_only_first_nine() -> None:
    result = magazine_activation_map(magazine_entries(11))

    assert sum(result.values()) == 9
    assert result["Magazine 09"] is True
    assert result["Magazine 10"] is False


def test_config_text_is_direct_name_boolean_mapping() -> None:
    parsed = yaml.safe_load(magazine_config_text(magazine_entries(2)))
    assert parsed == {"Magazine 01": True, "Magazine 02": True}


def test_sync_adds_missing_folders_as_inactive() -> None:
    synced = sync_activation_with_folders(
        {"Magazine 01": True},
        magazine_entries(3),
    )
    assert synced == {
        "Magazine 01": True,
        "Magazine 02": False,
        "Magazine 03": False,
    }


def test_sync_caps_active_magazines() -> None:
    too_many = {f"Magazine {number:02d}": True for number in range(1, 12)}
    synced = sync_activation_with_folders(too_many, magazine_entries(11))
    assert active_magazine_count(synced) == MAGAZINE_SHELF_LIMIT


def test_ensure_magazines_yaml_creates_missing_file(tmp_path: Path) -> None:
    with (
        patch(
            "aoj_mr_studio.magazine_config.remote_file_exists",
            return_value=(AdbResult(True, ""), False),
        ),
        patch(
            "aoj_mr_studio.magazine_config.push_remote_file",
            return_value=AdbResult(True, "ok"),
        ) as push,
    ):
        result, created = ensure_magazines_yaml(magazine_entries(10), tmp_path)

    assert result.ok is True
    assert created is True
    local_yaml = push.call_args.args[0]
    parsed = yaml.safe_load(local_yaml.read_text(encoding="utf-8"))
    assert sum(parsed.values()) == 9


def test_ensure_magazines_yaml_preserves_existing_file(tmp_path: Path) -> None:
    with (
        patch(
            "aoj_mr_studio.magazine_config.remote_file_exists",
            return_value=(AdbResult(True, ""), True),
        ),
        patch("aoj_mr_studio.magazine_config.push_remote_file") as push,
    ):
        result, created = ensure_magazines_yaml(magazine_entries(2), tmp_path)

    assert result.ok is True
    assert created is False
    push.assert_not_called()


def test_load_magazines_yaml_reads_and_syncs(tmp_path: Path) -> None:
    local = tmp_path / "magazines" / "magazines.yaml"
    local.parent.mkdir(parents=True)
    local.write_text("Magazine 01: true\nMagazine 99: true\n", encoding="utf-8")

    with (
        patch(
            "aoj_mr_studio.magazine_config.remote_file_exists",
            return_value=(AdbResult(True, ""), True),
        ),
        patch(
            "aoj_mr_studio.magazine_config.pull_remote_file",
            return_value=AdbResult(True, "ok"),
        ),
    ):
        result, activation = load_magazines_yaml(magazine_entries(2), tmp_path)

    assert result.ok is True
    assert activation == {"Magazine 01": True, "Magazine 02": False}


def test_save_magazines_yaml_writes_file(tmp_path: Path) -> None:
    with patch(
        "aoj_mr_studio.magazine_config.push_remote_file",
        return_value=AdbResult(True, "ok"),
    ) as push:
        result = save_magazines_yaml({"A": True, "B": False}, tmp_path)

    assert result.ok is True
    local_yaml = push.call_args.args[0]
    assert yaml.safe_load(local_yaml.read_text(encoding="utf-8")) == {"A": True, "B": False}
