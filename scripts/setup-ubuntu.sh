#!/usr/bin/env bash
# One-step setup for Ubuntu or Debian: prerequisites, every language toolchain,
# then a health check. Run it from the fluidian folder:
#
#   bash scripts/setup-ubuntu.sh
#
# It asks for your password once (sudo). Safe to run again.
set -u
cd "$(dirname "$0")/.." || exit 1

say() { printf '\033[1m==> %s\033[0m\n' "$*"; }

if ! command -v apt-get >/dev/null 2>&1; then
  echo "This setup needs apt (Ubuntu or Debian). Install Python 3.8+ and run ./fluidian doctor instead."
  exit 1
fi

SUDO=""
if [ "$(id -u)" -ne 0 ]; then SUDO="sudo"; fi

say "Step 1 of 3: system prerequisites"
$SUDO apt-get update -qq || echo "    (package index update had problems; continuing)"
DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y -qq \
  python3 curl unzip ca-certificates git build-essential >/dev/null \
  && echo "    done" || echo "    some prerequisites failed; check the messages above"
python3 --version

say "Step 2 of 3: language toolchains (node, go, rust, java, kotlin, c#, c++, ruby, php, dart, elixir, lua, browser)"
bash scripts/install-toolchains.sh

say "Step 3 of 3: health check"
./fluidian doctor || true

echo
say "Setup finished."
echo "Next, add your OpenAI key:   bash scripts/set-api-key.sh"
echo "Then run the tests:          bash scripts/test-all.sh"
