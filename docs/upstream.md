# Upstream notes

This plugin sits between three projects we do not control. This page records,
for each of them, what we found, what we would ask, how sure we are, and whether
it is time to ask. It is written for the maintainers of those projects as much
as for us. If you maintain one of them and landed here: thank you, and feedback
is welcome in this repository's issues.

Status as of 2026-10-09, tested on one machine: Bazzite 44 (Fedora 44, SELinux
enforcing), CoolerControl 5.0.1, CoolerDash 3.3.5, one Zalman ALPHA2 DS unit.

---

## 1. CoolerControl — plugin LCD modes are typed `None`, so the UI cannot apply them

Tracked here as [#1](https://github.com/droltr/cc-plugin-zalman-lcd/issues/1).

### What we found
A device-service plugin that reports an LCD channel (`ChannelInfo.lcd_info` with
an `image` mode) shows up correctly in the UI. However, pressing **save** on its LCD
page reports *"Settings successfully updated and applied to the device"* while
nothing is sent to the plugin and no LCD setting is stored.

- `coolercontrold/daemon/src/repositories/service_plugin/client.rs`: every plugin
  LCD mode is mapped with `type_: LcdModeType::None`. Plugin lighting modes in the
  same function use `LightingModeType::Custom`.
- `coolercontrol-ui/src/views/LcdView.vue`, `saveLCDSetting()`: if
  `selectedLcdMode.type === LcdModeType.NONE`, the UI calls
  `saveDaemonDeviceSettingReset()` and returns. It never saves the chosen mode.

The REST API path is unaffected: `PUT /devices/{uid}/settings/{channel}/lcd/images`
(multipart) and `PUT …/lcd` (JSON) reach the plugin's `Lcd` RPC, and the setting is
persisted and re-applied on restart.

### What we would ask
Map plugin LCD modes to `LcdModeType::Custom` (or another non-`None` type) in
`service_plugin/client.rs`. That looks like a one-word change, and the UI would
then behave as it does for liquidctl LCDs.

### How sure we are
High. We reproduced the behaviour, read both code paths, and confirmed that the API
works. The same code is still present on `main` (checked 2026-10-09). We have not
built a patched daemon to prove the fix end to end.

### Timing
Ready to report now. It is a self-contained bug and does not depend on this
plugin's maturity.

### Minor, same area
The cc-plugins `manifest.toml` comment says the default device socket is
`/run/coolercontrol-plugin-{SERVICE_ID}.sock`, while the README and the code
(`service_manifest.rs`, `get_address`) use `/tmp/{id}.sock`. This plugin sets
`address` explicitly, so it is not affected.

---

## 2. CoolerDash — square panel treated as circular; ServicePlugin LCDs filtered out

Tracked here as [#5](https://github.com/droltr/cc-plugin-zalman-lcd/issues/5).

### What we found
1. `is_circular_display_device()` treats any LCD without a profile and larger than
   240 px as circular. The Zalman panel is a 320×320 square, so the layout is drawn
   inside a circle with empty corners. No configuration option overrides this.
2. `score_lcd_candidate()` gives `ServicePlugin` devices −40, commented
   *"CC v4.3.0: plugins are never LCD hw"*. Since CoolerControl 5, device-service
   plugins can expose LCD channels. In `strict` and `balanced` modes the panel is
   therefore rejected unless it is allowlisted.

### What we do locally
- One entry in `display_profiles[]` (`src/device/profile.c`):
  ```c
  {"Zalman ALPHA2 DS", 0x0483, 0x5740, 320, 320,
   DISPLAY_SHAPE_RECTANGULAR, 1.0, 0.5, 0.5,
   DISPLAY_TRANSPORT_IMAGE_UPLOAD, 0x00, 0,
   "zalman", "alpha2", NULL},
  ```
  It matches by name, because CoolerControl reports no USB IDs for plugin devices.
- `config.json`: `"device_detection": { "allowlist": "zalman" }`.

With both, CoolerDash logs `Zalman ALPHA2 LCD (320x320 pixel, unscaled (rectangular))`,
and the dashboard fills the panel.

### What we would ask
1. Accept the profile above, via a device confirmation issue using their template
   and `coolerdash --hardware-report --test-lcd`.
2. Reconsider the `ServicePlugin` penalty, for example by only penalising
   ServicePlugin devices that expose no `lcd_info`. Alternatively, document the allowlist.
3. Optionally, add a config option to force the display shape.

### More fixes found on 2026-10-09 (fork branch `zalman-alpha2-profile`)

Both changes are in [droltr/coolerdash](https://github.com/droltr/coolerdash/tree/zalman-alpha2-profile),
verified on this machine.

- **CPU fan RPM source** (`2298b5f`): the RPM under CPU (Split and Circle) is hard-wired to the first
  Liquidctl RPM sensor, so it stays empty when the AIO is wired to motherboard fan headers.
  New `display.cpu_rpm_sensor` (`"device_uid:sensor name"`, e.g. a motherboard `fan1 RPM`) with a
  selector in the plugin page; empty keeps the old behaviour.
- **Integrated plus discrete GPU** (`f76355e`): with an iGPU (AMD Raphael `amdgpu`) listed before the
  discrete card, the legacy `gpu` slot showed the iGPU temperature, load and power, while the RPM came
  from the discrete card. Fix: prefer the GPU that reports fan RPM for all GPU values; fall back to the
  first GPU.

### How sure we are
- Profile: fairly high for this panel, but it is one unit on one machine.
  `0x0483:0x5740` is a generic STMicroelectronics CDC ID, so the name tokens matter
  more than the IDs.
- Scoring: the code and comment are unambiguous. Whether the author wants to change
  the heuristic is their call.

### Timing
Slightly early. We would rather report after the robustness tests in
[#4](https://github.com/droltr/cc-plugin-zalman-lcd/issues/4) (long run, replug,
suspend), so the device confirmation can say "stable". The scoring question can
be asked any time.

---

## 3. Zalman driver — fork and original

The panel protocol and driver are by **bl3xand**
([original](https://github.com/bl3xand/zalman-Alpha2-DS-LCD-Linux), MIT). This plugin uses the fork
[droltr/zalman-Alpha2-DS-LCD-Linux](https://github.com/droltr/zalman-Alpha2-DS-LCD-Linux),
which adds:

- `zalman_lcd/client.py` and `media.py`: an embedded client (`LcdClient`) for host
  applications. It holds one persistent serial connection, sends static frames to
  the overlay layer rather than to flash, and has no daemon thread.
- A `find_tty()` fallback for when the USB address changes after a reconnect, with
  a regression test (incident of 2026-09-13).

### Open on our side first
As of 2026-10-09 the fork's GitHub copy is **behind** the local checkout. The
`client.py` bridge commit is not pushed, and the `find_tty()` fix is not committed.
This must be fixed before the driver can be pinned
([#3](https://github.com/droltr/cc-plugin-zalman-lcd/issues/3)) or offered upstream.

### What we would ask bl3xand
Whether they want the embedded client and the replug fallback in the original
project, so that integrations like this one can depend on it directly.

### Timing
Early. First push the fork, tag it, and pin it here.

---

## 4. liquidctl — nothing to ask

The previous approach added a Zalman driver to liquidctl and patched coolercontrold
to recognise it. The plugin approach makes both unnecessary, and the panel is a CDC
serial device rather than a HID cooler, which is not liquidctl's usual scope. We
have no request for liquidctl.

---

## Order we intend to follow

1. Push and tag the driver fork; pin it here (#3).
2. Report the CoolerControl UI bug (#1).
3. After the robustness tests (#4): CoolerDash device confirmation and the scoring question (#5).
4. With v1.0.0: ask CoolerControl to list this plugin (#6).
