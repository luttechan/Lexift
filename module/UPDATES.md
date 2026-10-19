# Updates

- Repository: `luttechan/KanaShift`
- Release tags: `v0.7.7`, `v0.7.8`, `v0.7.10`
- Published stable releases only; drafts and prereleases excluded
- Manual checks: Settings, About, tray menu
- Automatic check: 8 seconds after normal startup; one notification per new version
- Network requests run outside the UI thread
- Network and archive work run in a separate process; update windows are modeless
- Global keyboard hooks run in a separate process, isolated from UI/font initialization
- Login startup skips construction of the main window until it is opened

## Release build

1. Set `VERSION` in `module/app.py`.
2. Run `build_windows.bat`.
3. Publish the matching GitHub tag, for example `v0.7.7`.
4. Upload `release/KanaShift-0.7.7-Windows-x64.zip` and its `.sha256` file.

The ZIP root contains `KanaShift/KanaShift.exe` and `KanaShift/module/`.
Runtime libraries, fonts, `KanaShiftUpdater.exe`, and `update-manifest.json`
are inside `module/`.
Publish this generated ZIP, without changing its contents.
GitHub's asset SHA-256 digest is used to verify downloads. The manifest verifies
the version, architecture, file list, and every extracted file's SHA-256.
The `.sha256` file is also provided for manual verification.

## Installation

The user confirms download and installation. A copy of the updater runs outside
the installation directory and waits for KanaShift to exit. It replaces the
complete managed runtime, including `module`, then restarts KanaShift.
The old runtime is restored if replacement or startup confirmation fails.
If restoration itself is blocked, the backup path is shown for manual recovery.
User preferences and other files outside the managed runtime are preserved.
The installation directory must be writable by the current user; the updater
does not request administrator rights.

Automatic installation is supported by the packaged Windows application.
Source launches can check versions and open the release page.
ZIP files without the update manifest are not eligible for automatic installation.
GitHub's automatically generated source-code ZIP is not a portable update package.

The 0.7.6 release cannot update itself automatically: it has no updater.
Install 0.7.7 once; subsequent compatible releases can use the in-app updater.

The new updater also accepts older `_internal` packages. Runtime migration and
rollback replace the complete old layout; obsolete root helpers and manifests
are removed only after a successful replacement.

## Source layout

- Root: `launch.pyw`, launch/install/build scripts, README, license
- `module/`: Python modules, fonts, icon, requirements, tests, build tools
- `dist/KanaShift/`: portable Windows application
- `release/`: release ZIP and SHA-256
- Existing `.venv/`: source Python environment, retained in place
