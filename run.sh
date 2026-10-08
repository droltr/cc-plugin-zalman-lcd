#!/usr/bin/env bash
# Started by CoolerControl (systemd unit cc-plugin-zalman-lcd).
set -euo pipefail
dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export PYTHONPATH="$dir/lib"
exec "$dir/venv/bin/python" -P -m zalman_cc_plugin "$@"
