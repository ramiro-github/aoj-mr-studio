"""ADB pull/push for Quest custom object packages."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from aoj_mr_studio.adb_path import adb_source_label, find_adb
from aoj_mr_studio.config import QUEST_CUSTOM_OBJECTS, QUEST_MR_DIR


@dataclass
class AdbResult:
    ok: bool
    message: str


def quote_shell_path(remote_path: str) -> str:
    """Quote a Quest path for adb shell (paths may contain spaces)."""
    return shlex.quote(remote_path)


def run_adb(*args: str, timeout: float = 120.0) -> AdbResult:
    adb = find_adb()
    if not adb:
        return AdbResult(
            False,
            "adb not found — run scripts/copy-adb.ps1 or install Android platform-tools",
        )

    adb_path = Path(adb)
    try:
        completed = subprocess.run(
            [adb, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="surrogateescape",
            timeout=timeout,
            check=False,
            cwd=str(adb_path.parent) if adb_path.parent.is_dir() else None,
        )
    except subprocess.TimeoutExpired:
        return AdbResult(False, "adb command timed out")
    except OSError as exc:
        return AdbResult(False, f"adb failed: {exc}")

    output = (completed.stdout or "") + (completed.stderr or "")
    output = output.strip()
    if completed.returncode != 0:
        return AdbResult(False, output or f"adb exited with code {completed.returncode}")

    return AdbResult(True, output or "ok")


def run_adb_shell(command: str, timeout: float = 120.0) -> AdbResult:
    """Run one shell command on the device (use for paths with spaces)."""
    return run_adb("shell", command, timeout=timeout)


def check_device_connected() -> AdbResult:
    result = run_adb("devices")
    if not result.ok:
        return result

    lines = [line for line in result.message.splitlines() if line.strip()]
    devices = [
        line.split("\t")[0]
        for line in lines[1:]
        if "\tdevice" in line
    ]
    if not devices:
        return AdbResult(False, "no Quest/device connected (enable USB debugging)")

    label = adb_source_label()
    return AdbResult(True, f"connected: {', '.join(devices)} (adb: {label})")


def pull_custom_objects(local_root: Path) -> AdbResult:
    device = check_device_connected()
    if not device.ok:
        return device

    local_root.mkdir(parents=True, exist_ok=True)
    return run_adb("pull", QUEST_CUSTOM_OBJECTS, str(local_root), timeout=300.0)


def push_custom_objects(local_root: Path) -> AdbResult:
    device = check_device_connected()
    if not device.ok:
        return device

    if not local_root.is_dir():
        return AdbResult(False, f"local folder not found: {local_root}")

    return run_adb("push", str(local_root) + "/", QUEST_CUSTOM_OBJECTS + "/", timeout=300.0)


def push_package(local_root: Path, package_name: str) -> AdbResult:
    device = check_device_connected()
    if not device.ok:
        return device

    package_path = local_root / package_name
    if not package_path.is_dir():
        return AdbResult(False, f"package not found locally: {package_name}")

    remote = f"{QUEST_CUSTOM_OBJECTS}/{package_name}"
    return run_adb("push", str(package_path), remote, timeout=120.0)


def list_remote_packages() -> AdbResult:
    device = check_device_connected()
    if not device.ok:
        return device

    return run_adb_shell(f"ls -1 {quote_shell_path(QUEST_CUSTOM_OBJECTS)}")


@dataclass
class RemoteEntry:
    name: str
    is_dir: bool


def list_remote_dir(remote_path: str) -> tuple[AdbResult, list[RemoteEntry]]:
    """List one Quest folder via adb shell ls -1p (trailing / = directory)."""
    device = check_device_connected()
    if not device.ok:
        return device, []

    result = run_adb_shell(f"ls -1p {quote_shell_path(remote_path)}")
    if not result.ok:
        if "No such file or directory" in result.message:
            return AdbResult(
                False,
                f"Folder not found on Quest:\n{remote_path}\n\n"
                "Run Age of Joy once on the headset so MR folders are created.",
            ), []
        return result, []

    entries: list[RemoteEntry] = []
    for line in result.message.splitlines():
        name = line.strip()
        if not name or name in (".", ".."):
            continue
        is_dir = name.endswith("/")
        if is_dir:
            name = name[:-1]
        entries.append(RemoteEntry(name=name, is_dir=is_dir))

    entries.sort(key=lambda entry: (not entry.is_dir, entry.name.lower()))
    return result, entries


def parent_remote_path(remote_path: str) -> str | None:
    normalized = remote_path.rstrip("/")
    if not normalized or normalized == "/":
        return None
    parent = normalized.rsplit("/", 1)[0]
    return parent or "/"


def remote_file_exists(remote_path: str) -> tuple[AdbResult, bool]:
    device = check_device_connected()
    if not device.ok:
        return device, False

    result = run_adb_shell(f"test -f {quote_shell_path(remote_path)} && echo yes || echo no")
    if not result.ok:
        return result, False
    return result, result.message.strip().endswith("yes")


def pull_remote_file(remote_path: str, local_path: Path) -> AdbResult:
    device = check_device_connected()
    if not device.ok:
        return device

    local_path.parent.mkdir(parents=True, exist_ok=True)
    return run_adb("pull", remote_path, str(local_path), timeout=120.0)


def pull_remote_dir(remote_path: str, local_dir: Path) -> AdbResult:
    """Pull a remote folder into local_dir (creates/overwrites that folder)."""
    device = check_device_connected()
    if not device.ok:
        return device

    if local_dir.exists():
        shutil.rmtree(local_dir)
    local_dir.parent.mkdir(parents=True, exist_ok=True)

    # Pull into the parent so adb creates local_dir with the remote folder name,
    # then rename if needed — or pull directly to local_dir path.
    result = run_adb("pull", remote_path, str(local_dir), timeout=600.0)
    if not result.ok:
        return result
    if not local_dir.is_dir():
        return AdbResult(False, f"pull did not create folder: {local_dir}")
    return result


def push_remote_file(local_path: Path, remote_path: str) -> AdbResult:
    device = check_device_connected()
    if not device.ok:
        return device

    if not local_path.is_file():
        return AdbResult(False, f"local file not found: {local_path}")

    return run_adb("push", str(local_path), remote_path, timeout=120.0)


def push_local_dir(local_dir: Path, remote_parent: str) -> AdbResult:
    """Push a whole local folder into a remote parent folder (one adb call)."""
    device = check_device_connected()
    if not device.ok:
        return device

    if not local_dir.is_dir():
        return AdbResult(False, f"local folder not found: {local_dir}")

    return run_adb("push", str(local_dir), remote_parent.rstrip("/") + "/", timeout=600.0)


def remote_dir_exists(remote_path: str) -> tuple[AdbResult, bool]:
    device = check_device_connected()
    if not device.ok:
        return device, False

    result = run_adb_shell(f"test -d {quote_shell_path(remote_path)} && echo yes || echo no")
    if not result.ok:
        return result, False
    return result, result.message.strip().endswith("yes")


def create_remote_dir(remote_path: str) -> AdbResult:
    device = check_device_connected()
    if not device.ok:
        return device

    return run_adb_shell(f"mkdir -p {quote_shell_path(remote_path)}")


def delete_remote_dir(remote_path: str) -> AdbResult:
    """Recursively delete one remote folder."""
    normalized = remote_path.rstrip("/")
    if not normalized or normalized == "/":
        return AdbResult(False, "refusing to delete the remote root folder")

    device = check_device_connected()
    if not device.ok:
        return device

    return run_adb_shell(f"rm -rf {quote_shell_path(normalized)}")
