# cc-plugin-zalman-lcd

[CoolerControl](https://gitlab.com/coolercontrol/coolercontrol) device service
plugin for the **Zalman ALPHA2 DS** AIO LCD (320×320, USB `0483:5740`,
"HWCX-TECH USB Display", `cdc_acm`).

The screen shows up in CoolerControl as an LCD device. Images, brightness and
orientation can then be set through CoolerControl's REST API, and tools built on
it, such as [CoolerDash](https://github.com/damachine/coolerdash), can draw to it.

The panel itself is driven by
[zalman-Alpha2-DS-LCD-Linux](https://github.com/droltr/zalman-Alpha2-DS-LCD-Linux)
(`zalman_lcd.client.LcdClient`). This plugin is only the gRPC bridge between
CoolerControl and that driver.

## How it works

```
CoolerControl ──gRPC (unix socket)──▶ zalman_cc_plugin ──▶ zalman_lcd ──▶ /dev/ttyACM0
```

- `ListDevices` reports one device with an `lcd` channel: 320×320 and one `image`
  mode with brightness and orientation.
- `Lcd` receives the image that CoolerControl has already processed (a file path),
  plus brightness and orientation, and forwards them to `LcdClient`. Static frames
  go to the device's overlay layer, not to flash.
- `none` blanks the panel. Orientation is clockwise, like the rest of CoolerControl.
- There are no fan, lighting or sensor channels.

## Requirements

- CoolerControl ≥ 5.0 (tested with 5.0.1 on Fedora 44 / Bazzite)
- Python ≥ 3.10 on the host (the installer builds a private venv)
- The driver checked out next to this repo as `../zalman-Alpha2-DS-LCD-Linux`

## Install / uninstall

```bash
sudo bash install.sh && sudo systemctl restart coolercontrold
sudo bash uninstall.sh
```

`install.sh` puts everything into `/var/lib/coolercontrol/plugins/zalman-lcd/`:
the manifest, the launcher, the plugin and driver packages under `lib/`, and a
venv. It does not touch `/usr` or any packages. On SELinux systems it labels only
`run.sh` as `bin_t`, so that systemd may execute it. The plugin runs as root
(`privileged = true`) so it can open the serial port without a udev rule.

## Development

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt grpcio-tools
# run against the real device without CoolerControl:
PYTHONPATH=../zalman-Alpha2-DS-LCD-Linux .venv/bin/python -m zalman_cc_plugin --socket $XDG_RUNTIME_DIR/zl.sock
.venv/bin/python test_client.py $XDG_RUNTIME_DIR/zl.sock some-320x320.png --orientation 90
```

The protos under `proto/` are vendored from
[cc-plugins](https://gitlab.com/coolercontrol/cc-plugins); see `proto/SOURCE`
for the commit and the command that regenerates `zalman_cc_plugin/gen/`.

## Upstream status

What we found in CoolerControl, CoolerDash and the driver, and what we would ask of them: [docs/upstream.md](docs/upstream.md).

## Known issue (CoolerControl 5.0.1)

CoolerControl's UI cannot apply images to plugin LCDs. The daemon tags every
plugin LCD mode as type `None` (`repositories/service_plugin/client.rs`), and the
UI's save button treats `None` as "reset channel". The UI reports success, but
nothing is applied. The REST API is not affected:

```bash
curl -X PUT -H "Authorization: Bearer $TOKEN" \
  -F mode=image -F brightness=80 -F orientation=0 -F 'images[]=@card.png;type=image/png' \
  http://localhost:11987/devices/<device-uid>/settings/lcd/lcd/images
```

## License

GPL-3.0-or-later (the vendored protos and generated code come from cc-plugins,
GPL-3.0). The bundled driver is MIT.
