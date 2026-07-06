# AOJ MR Studio

Desktop tool for **Age of Joy Mixed Reality** — browse Quest MR folders and edit custom object packages (`object.yaml`).

Not an official Curif tool.

---

## For users (download — do not clone)

**Do not clone this repository.** End users only need the pre-built Windows zip from **Releases**.

1. Open **[Latest release](https://github.com/ramiro-github/aoj-mr-studio/releases/latest)**
2. Download **`AOJ-MR-Studio-vX.Y.Z-win64.zip`**
3. Extract the folder **`AOJ MR Studio`**
4. Run **`AOJ MR Studio.exe`**

No Python install required. Keep the **whole extracted folder** (includes bundled `adb/`).

### Requirements

- Windows PC
- Meta Quest: developer mode, USB debugging, Age of Joy run at least once
- USB cable to the PC

---

## Features (current)

- **Startup** — connects to Meta Quest on launch (loading screen), then opens **Home** with the bundled MR user guide (**pt-BR** and **English**), styled text and clickable table of contents
- Browse Quest folders under `/sdcard/Android/data/com.curif.AgeOfJoy/MR/` via **ADB**
- Edit custom object packages (`object.yaml`, Placement, Components) and **Save to Meta Quest**
- **Bundled adb** — no separate platform-tools install for end users

---

## For developers

Clone this repo only if you work on the app. Users should use **Releases**, not `git clone`.

### Requirements

- Python **3.11+**
- Meta Quest: developer mode, USB debugging, Age of Joy run once

For **running from source**, either:

1. Run `scripts/copy-adb.ps1` (bundled adb in `vendor/adb/`), or  
2. Install [platform-tools](https://developer.android.com/tools/releases/platform-tools) and add `adb` to PATH

### Setup

```powershell
cd "C:\Users\ramir\OneDrive\Documents\AOJ MR Studio"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev,build]"
.\scripts\copy-adb.ps1
```

### Run from source

```powershell
python -m aoj_mr_studio
```

Or `run.bat`.

### Build executable locally (Windows)

```powershell
.\build_exe.ps1
```

Output: `dist\AOJ MR Studio\AOJ MR Studio.exe` and `dist\AOJ MR Studio\adb\adb.exe`.

Ship the **entire** `dist\AOJ MR Studio\` folder to users (or publish via Releases below).

### Publish a release (maintainers)

`./scripts/deploy.sh` (Git Bash):

1. Runs tests
2. Bumps `pyproject.toml` version
3. Commits and pushes to `main`
4. Creates tag `vX.Y.Z` and pushes it

GitHub Actions then builds the user-ready zip and publishes it on **Releases** (source code stays on `main`; the `.exe` is **not** committed to git).

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

Workflow: [.github/workflows/release.yml](.github/workflows/release.yml) — Windows, tests, PyInstaller, bundled adb, zip upload.

---

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
