#!/usr/bin/env bash
# One-time setup on an Apple Silicon Mac: Android SDK + emulator image + AVD,
# ffmpeg, and the `gui-agent` conda env. Safe to re-run (skips what exists).
#
#   bash scripts/setup_mac.sh
#
# Downloads ~6-8 GB (Android system image, SDK, conda packages).
set -euo pipefail
cd "$(dirname "$0")/.."

SDK="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
IMAGE="system-images;android-33;google_apis;arm64-v8a"   # Pixel 6 / API 33 (Tiramisu), ARM build
AVD="AndroidWorldAvd"

echo "==> Homebrew packages"
brew list ffmpeg >/dev/null 2>&1 || brew install ffmpeg
brew list openjdk@17 >/dev/null 2>&1 || brew install openjdk@17
brew list --cask android-commandlinetools >/dev/null 2>&1 || brew install --cask android-commandlinetools
export JAVA_HOME="$(brew --prefix openjdk@17)/libexec/openjdk.jdk/Contents/Home"

echo "==> Android SDK into $SDK"
mkdir -p "$SDK"
yes | sdkmanager --sdk_root="$SDK" --licenses >/dev/null || true
sdkmanager --sdk_root="$SDK" "cmdline-tools;latest" "platform-tools" "emulator" "platforms;android-33" "$IMAGE"

echo "==> AVD $AVD"
# Use the avdmanager inside $SDK: Homebrew's copy looks in its own SDK root and
# fails with "Package path is not valid. Valid system image paths are: null".
if ! "$SDK/emulator/emulator" -list-avds | grep -qx "$AVD"; then
  echo "no" | "$SDK/cmdline-tools/latest/bin/avdmanager" create avd -n "$AVD" -k "$IMAGE" -d pixel_6
fi
# Without a hardware keyboard, `adb shell monkey` (used by AndroidWorld to launch apps)
# aborts with "SYS_KEYS has no physical keys" during --perform-emulator-setup.
sed -i '' 's/^hw.keyboard=no$/hw.keyboard=yes/' "$HOME/.android/avd/$AVD.avd/config.ini"

echo "==> Third-party code (android_world, gelab-zero)"
if [ -d .git ]; then
  git submodule update --init
else
  # Unpacked from the ZIP (no .git): fetch the same upstream commits the submodules pin.
  fetch_pinned() {
    if [ -n "$(ls -A "$1" 2>/dev/null)" ]; then return; fi
    git init -q "$1"
    git -C "$1" fetch -q --depth 1 "$2" "$3"
    git -C "$1" checkout -q FETCH_HEAD
  }
  fetch_pinned third_party/android_world https://github.com/google-research/android_world \
    2dfc5ca3dc590efe9c72ce768f2b04182f2f75c7
  fetch_pinned third_party/gelab-zero https://github.com/stepfun-ai/gelab-zero \
    7b619f6f67d2b1101021fc453cb27bd48a29e4f2
fi

echo "==> conda env 'gui-agent' (Python 3.11)"
if conda env list | grep -q "^gui-agent "; then
  conda env update -n gui-agent -f environment.yml --prune
else
  conda env create -f environment.yml
fi

[ -f .env ] || cp .env.example .env

cat <<EOF

Done. Next:
  conda activate gui-agent
  bash scripts/setup_model.sh          # GELab-Zero into Ollama (once)
  bash scripts/start_emulator.sh       # in its own terminal
  python scripts/check_setup.py
EOF
