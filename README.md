# NEW_AI_CAR_SCANER

Evidence-driven automotive diagnostic platform with a shared FastAPI backend, deterministic diagnostic rules, evidence-based hypotheses, optional AI/RAG assistance, vehicle simulation, and native client applications.

[Release notes](RELEASE_NOTES.md)

## Ecosystem foundation (development)

This repository retains the source ecosystem foundation work and starts the requested ecosystem
without replacing the native UI or shared diagnostic engine. Audit, baseline,
interactive architecture, API/migration/security design and a phased roadmap
are in [docs](docs/CURRENT_SYSTEM_AUDIT.md). The first backend account/ownership/
workshop-consent milestone is opt-in (`AI_CAR_ECOSYSTEM_ENABLED`, default off).
Native login screens, authenticated diagnostic adapters, scheduling, notification
providers, marketplace and admin tools remain later milestones.

[Implementation status](docs/IMPLEMENTATION_REPORT.md) ·
[Interactive architecture](docs/architecture/interactive_architecture.html) ·
[Rollout / local smoke test](docs/DEPLOYMENT_GUIDE.md).

## C++ OBD connection milestone

Optional C++20 TCP socket transport is integrated behind the existing Wi-Fi
interface, with bounded reads, deadlines and read-only command validation.
See [build, activation and platform limits](native/obd/README.md).
The original native UI and icons are retained. This is a staged development
repository, not a completed production ecosystem.

## Supported clients

- **Desktop:** Python + PySide6 workstation (finalbuild/apps/desktop).
- **Android:** native Kotlin + Jetpack Compose app (finalbuild/apps/mobile-android).
- **iOS:** native Swift + SwiftUI app (finalbuild/apps/mobile-ios).

The repository uses native client implementations. The browser/PWA client and its static Render deployment have been removed. The legacy Flutter client sources and their build scaffolding have been removed.

## Setup after cloning

```bash
python runner.py setup --accept-android-licenses --run
```

The Windows runner prepares `.venv`, Backend/Desktop dependencies, local AI and
Android tools/APK. Missing model/SDK downloads can total several GB. Existing
assets can be supplied with `--model` and `--llama-dir`. Use a second terminal
with an emulator running: `python runner.py android`.
[Runner commands, recovery and prerequisites](finalbuild/docs/building/LOCAL_RUNNER.md).

## Windows installer

Build the download-and-install wizard locally with `python installer.py`
(requires Inno Setup 6.3+ on Windows). It bundles a pinned Git source snapshot (including private repos),
installs Desktop/Backend, offers optional Local AI and Desktop shortcuts, and
registers a Windows uninstaller.
[Installer build, distribution and removal](finalbuild/docs/building/WINDOWS_INSTALLER.md).
The Desktop-styled wizard supports downloaded or existing local GGUF models.
[Shared JSON environment configuration](finalbuild/docs/building/ENVIRONMENT_CONFIG.md)
controls Desktop, Backend and runner settings.

## Build all native apps

One entrypoint: `python build.py`. Run `python build.py --check` to verify native
toolchains. On Windows, build locally with `python build.py --targets desktop android`.
For Android + iOS, run `python build.py --targets android ios --with-tests` on
macOS with the required toolchains. Desktop EXE packaging requires Windows;
iOS requires macOS/Xcode. Builds run locally; no CI/CD dispatch is configured.
[Full instructions, prerequisites and artifacts](finalbuild/docs/building/BUILD_ALL.md).

iOS output is an unsigned Simulator app; iPhone/App Store distribution requires
Apple signing configuration. Local Windows/Linux runs cannot compile iOS.

## Real OBD and shared vehicle data

[Protocol audit and support matrix](finalbuild/docs/obd/REAL_OBD_AUDIT.md) ·
[Backend/native bridge setup and APIs](finalbuild/docs/obd/SETUP_AND_API.md).

## Quick start

See [Windows setup](finalbuild/START_HERE_WINDOWS.md) for the local desktop/AI runtime and [project overview](finalbuild/README.md) for backend setup, tests, and architecture.

## Shared client behavior

The three native clients share the backend vehicle catalog and DiagnosticSession API. Language codes are English (en), Russian (ru), and Armenian (hy); theme modes are dark/light; diagnostic result values are PASS/FAIL/INCOMPLETE. See [the machine-readable client contract](finalbuild/config/client_contract.json) and [platform feature contract](finalbuild/PLATFORM_FEATURE_PARITY.md).

## Architecture and quality reports

- [Architecture documentation](finalbuild/docs/README.md)
- [Platform feature contract](finalbuild/PLATFORM_FEATURE_PARITY.md)
- [Historical quality report](report.md)

The results in report.md are tied to the specific commits and CI runs named in that report; they must not be interpreted as validation of later commits unless a matching run is linked.

## Safe local cleanup

`python clean.py` previews disposable Python/test/lint caches; run
`python clean.py --apply` to remove that list. Tracked files, native build outputs,
test reports, models, environments and SDKs are preserved.

[Current native functionality](finalbuild/docs/reviews/native-parity-implementation-2026-10-27.md)
· [Latest Desktop Save/analyze fix](finalbuild/docs/reviews/desktop-save-analyze-fix-2026-10-27.md).
