"""CRUD for custom object package folders."""

from __future__ import annotations

import shutil
from pathlib import Path

from aoj_mr_studio.config import OBJECT_YAML_NAME
from aoj_mr_studio.yaml_model import ObjectDefinition, load_object_yaml, save_object_yaml


def list_packages(root: Path) -> list[str]:
    if not root.is_dir():
        return []

    names: list[str] = []
    for entry in sorted(root.iterdir(), key=lambda path: path.name.lower()):
        if entry.is_dir() and not entry.name.startswith("."):
            names.append(entry.name)
    return names


def package_dir(root: Path, package_name: str) -> Path:
    return root / package_name


def create_package(root: Path, package_name: str) -> Path:
    name = package_name.strip()
    if not name:
        raise ValueError("package name is required")

    target = package_dir(root, name)
    if target.exists():
        raise FileExistsError(f"package already exists: {name}")

    target.mkdir(parents=True)
    definition = ObjectDefinition.default_for_package(name)
    save_object_yaml(target, definition)
    return target


def delete_package(root: Path, package_name: str) -> None:
    target = package_dir(root, package_name)
    if not target.is_dir():
        raise FileNotFoundError(f"package not found: {package_name}")
    shutil.rmtree(target)


def package_has_yaml(root: Path, package_name: str) -> bool:
    return (package_dir(root, package_name) / OBJECT_YAML_NAME).is_file()


def list_glb_files(package_path: Path) -> list[str]:
    if not package_path.is_dir():
        return []
    return sorted(path.name for path in package_path.glob("*.glb"))
