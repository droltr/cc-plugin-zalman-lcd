#!/usr/bin/env bash
# Remove the plugin and let CoolerControl drop the device.
# Usage: sudo bash uninstall.sh
set -euo pipefail
test "$(id -u)" -eq 0 || { echo "run with sudo" >&2; exit 1; }
rm -rf /var/lib/coolercontrol/plugins/zalman-lcd /var/lib/coolercontrol/plugins/zalman-lcd.new
rm -f /run/coolercontrol-plugin-zalman-lcd.sock
systemctl restart coolercontrold
echo "zalman-lcd plugin removed"
