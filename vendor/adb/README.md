# Bundled Android platform-tools (SideQuest-style)

Copy Google's **platform-tools** here before building the `.exe`:

- `adb.exe`
- `AdbWinApi.dll`
- `AdbWinUsbApi.dll`

## Quick setup (Windows)

From the project root:

```powershell
.\scripts\copy-adb.ps1
```

Or download [platform-tools](https://developer.android.com/tools/releases/platform-tools) and copy the files above into this folder.

These binaries are **not** committed to git (see `.gitignore`). Each developer/build machine runs `copy-adb.ps1` once, then `build_exe.ps1`.

## License

ADB is part of the Android SDK Platform-Tools (Google). Distribution of your app bundling `adb.exe` must comply with the [Android SDK license](https://developer.android.com/studio/terms).
