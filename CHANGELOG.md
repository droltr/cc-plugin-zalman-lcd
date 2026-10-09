# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.2] - 2026-10-09

### Fixed
- `manifest.toml` homepage URL now points to this repository (it pointed to the driver).

### Changed
- Type hints for all gRPC handlers; ruff configuration in `pyproject.toml`.

### Added
- Project docs: `CHANGELOG.md`, `coding.md`, `.claudeignore`, `docs/upstream.md`.

## [0.1.1] - 2026-10-09

### Fixed
- Orientation now rotates clockwise, matching CoolerControl (the driver rotates
  counter-clockwise, so the angle is inverted before it is passed on).
- Selecting the `none` LCD mode blanks the panel instead of returning an error.

## 0.1.0 - 2026-10-09 (not tagged; superseded by 0.1.1 before the first commit)

### Added
- CoolerControl device service exposing the Zalman ALPHA2 DS LCD (320×320) as an
  LCD channel with an `image` mode, brightness and orientation.
- `install.sh` / `uninstall.sh` keeping everything under
  `/var/lib/coolercontrol/plugins/zalman-lcd`, including the SELinux label for the launcher.
- `test_client.py` to exercise a running service without CoolerControl.

Verified on Bazzite 44 with CoolerControl 5.0.1 and CoolerDash 3.3.5.

[Unreleased]: https://github.com/droltr/cc-plugin-zalman-lcd/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/droltr/cc-plugin-zalman-lcd/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/droltr/cc-plugin-zalman-lcd/releases/tag/v0.1.1
