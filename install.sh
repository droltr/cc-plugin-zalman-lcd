#!/usr/bin/env bash
# Install (or update) the plugin into CoolerControl's plugin directory.
# Everything lands in one folder; uninstall.sh removes it again.
# Usage: sudo bash install.sh
set -euo pipefail

src=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
driver="$src/../zalman-Alpha2-DS-LCD-Linux/zalman_lcd"
target=/var/lib/coolercontrol/plugins/zalman-lcd
stage="$target.new"

test "$(id -u)" -eq 0 || { echo "run with sudo" >&2; exit 1; }
test -d "$driver"

rm -rf "$stage"
mkdir -p "$stage/lib"
cp "$src/manifest.toml" "$src/run.sh" "$src/requirements.txt" "$stage/"
cp -r "$src/zalman_cc_plugin" "$driver" "$stage/lib/"
find "$stage/lib" -name __pycache__ -prune -exec rm -rf {} +
/usr/bin/python3 -m venv "$stage/venv"
"$stage/venv/bin/pip" install --quiet --disable-pip-version-check -r "$stage/requirements.txt"
chmod 0755 "$stage/run.sh"

rm -rf "$target"
mv "$stage" "$target"
# SELinux: systemd (init_t) may not execute var_lib_t files; label only the
# launcher like a regular program. The label goes away with the folder.
if command -v selinuxenabled >/dev/null && selinuxenabled; then
    chcon -t bin_t "$target/run.sh"
fi
echo "Installed to $target"
echo "Activate with: sudo systemctl restart coolercontrold"
