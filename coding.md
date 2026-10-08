# Project guidelines

Project-specific architecture notes and conventions. General rules (English-only
code and docs, Conventional Commits, branch model) apply as usual. This file
records only what is specific to this repository.

## Architecture

```
CoolerControl daemon ──gRPC over a Unix socket──▶ zalman_cc_plugin.service ──▶ zalman_lcd.LcdClient ──▶ /dev/ttyACM0
```

- `zalman_cc_plugin/service.py` implements `DeviceService` from
  `proto/coolercontrol/device_service/v1/device_service.proto`. It is a thin
  adapter and holds no rendering or protocol logic.
- `zalman_cc_plugin/__main__.py` parses `--socket`, maps `CC_LOG` to Python log
  levels, and runs a single-worker gRPC server, so LCD commands never interleave
  on the serial port.
- The panel protocol lives in the separate driver repository
  ([zalman-Alpha2-DS-LCD-Linux](https://github.com/droltr/zalman-Alpha2-DS-LCD-Linux)).
  Driver fixes go there, not here.

## Decisions

| Decision | Reason |
|---|---|
| Python, not the Rust template | Reuses the existing Python driver as-is. |
| `privileged = true` | `/dev/ttyACM0` is `root:dialout`. Running as root avoids shipping a udev rule. Revisit if a narrow udev rule is added. |
| Install under `/var/lib/coolercontrol/plugins/zalman-lcd` only, with a private venv | `/usr` is read-only on image-based distros (Bazzite, Silverblue). |
| `chcon -t bin_t run.sh` | SELinux denies `init_t` executing `var_lib_t` files. The label is removed together with the folder. |
| Orientation is inverted (`(360 - deg) % 360`) | CoolerControl uses clockwise angles; the driver (PIL) rotates counter-clockwise. Verified on hardware. |
| `none` mode blanks the panel | CoolerControl always offers `None` in addition to the plugin's modes. |
| Generated stubs are committed (`zalman_cc_plugin/gen/`) | Installation needs no `grpcio-tools`. Regenerate with the command in `proto/SOURCE`; never edit them by hand. |

## Conventions

- **File names:** the general rule is kebab-case, but Python modules and packages
  must be importable and therefore use snake_case (`zalman_cc_plugin`,
  `test_client.py`, future `tests/test_*.py`). Shell scripts and docs stay
  kebab-case.
- **Style:** `ruff format` and `ruff check` (configured in `pyproject.toml`, 100-char
  lines, `gen/` excluded). Type hints are required on all functions.
- **Logging:** use `logging`, never `print`, in the service. Never log tokens or
  image contents. Errors returned to CoolerControl must also be logged.
- **Deletion:** do not hard-delete files during development. Move them to
  `.deleted/` with a `_YYYYMMDD_HHMMSS` suffix (git-ignored).
- **Versioning:** keep `zalman_cc_plugin/__init__.py`, `manifest.toml` and
  `CHANGELOG.md` in sync. Tag releases `vX.Y.Z` on `main`; pre-release builds use
  `vX.Y.Z-test-<feature>`.
- **Branches:** `main` (released), `develop` (integration), `feature/*`, `fix/*`.
  Merge through pull requests into `develop`.

## Known external issues

- CoolerControl ≤ 5.0.1 tags plugin LCD modes as `None`, so its UI resets the
  channel instead of applying an image. Use the REST API or CoolerDash.
- CoolerDash ≤ 3.3.5 treats unknown LCDs larger than 240 px as circular and
  penalises `ServicePlugin` devices. It needs a Zalman display profile and
  `device_detection.allowlist = "zalman"`.
