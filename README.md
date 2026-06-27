# AOJ MR Studio

Desktop tool for **Age of Joy Mixed Reality** — browse Quest MR folders and (future) edit custom object packages (`object.yaml`).

Not an official Curif tool.

## Features (current)

- Browse Quest folders under `/sdcard/Android/data/com.curif.AgeOfJoy/MR/` via **ADB**
- **Bundled adb** support (SideQuest-style) — no separate platform-tools install for end users

## Requirements (development)

- Python **3.11+**
- Meta Quest: developer mode, USB debugging, Age of Joy run once

For **running from source**, either:

1. Run `scripts/copy-adb.ps1` (bundled adb in `vendor/adb/`), or  
2. Install [platform-tools](https://developer.android.com/tools/releases/platform-tools) and add `adb` to PATH

## Setup

```powershell
cd "C:\Users\ramir\OneDrive\Documents\AOJ MR Studio"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
.\scripts\copy-adb.ps1
```

## Run

```powershell
python -m aoj_mr_studio
```

Or `run.bat`.

## Build executable (Windows)

Bundles **adb.exe** + DLLs next to the app (like SideQuest):

```powershell
.\build_exe.ps1
```

Output: `dist\AOJ MR Studio\AOJ MR Studio.exe` and `dist\AOJ MR Studio\adb\adb.exe`.

Ship the **entire** `dist\AOJ MR Studio\` folder to users.

## Quest paths

| Where | Path |
|-------|------|
| MR root | `/sdcard/Android/data/com.curif.AgeOfJoy/MR/` |
| Custom objects | `.../MR/Custom Objects/` |
| PC mirror | `%UserProfile%\cabs\MR\Custom Objects\` |

Schema: [CUSTOM_OBJECT_YAML.md](https://github.com/curif/AgeOfJoy-2022.1/blob/0.5.0/Assets/ramiro/CUSTOM_OBJECT_YAML.md)

## Tests

```powershell
pytest
```

## License

MIT — see [LICENSE](LICENSE). Bundled `adb.exe` is subject to the [Android SDK terms](https://developer.android.com/studio/terms).
