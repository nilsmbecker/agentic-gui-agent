#!/usr/bin/env bash
# Start the AndroidWorld emulator. Keep this terminal open while running tasks.
#   bash scripts/start_emulator.sh            # with window
#   bash scripts/start_emulator.sh -no-window # headless
# -grpc 8554 is required by AndroidWorld (accessibility forwarding).
set -euo pipefail
SDK="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
exec "$SDK/emulator/emulator" -avd AndroidWorldAvd -no-snapshot -grpc 8554 "$@"
