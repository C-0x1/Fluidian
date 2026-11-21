#!/usr/bin/env bash
# Install the language toolchains used by the SDK conformance suite on Ubuntu or Debian.
#
#   scripts/install-toolchains.sh            # everything
#   scripts/install-toolchains.sh go rust    # only the named languages
#   scripts/install-toolchains.sh --check    # report what is installed, change nothing
#
# The framework itself needs only Python 3.  Every toolchain here is optional:
# `./fluidian test` skips the SDKs whose toolchain is missing and says so.
# The script is best-effort by design: a language that cannot be installed is
# reported at the end and does not stop the others.
set -u

ALL="node typescript go rust java kotlin csharp cpp ruby php dart elixir lua browser"
WANT="${*:-$ALL}"
CHECK=0
if [ "${1:-}" = "--check" ]; then CHECK=1; WANT="$ALL"; fi
if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'; exit 0; fi

ARCH="$(dpkg --print-architecture 2>/dev/null || uname -m)"
case "$ARCH" in x86_64) ARCH=amd64 ;; aarch64) ARCH=arm64 ;; esac
SUDO=""
if [ "$(id -u)" -ne 0 ]; then SUDO="sudo"; fi
FAILED=""
APT_READY=0

say()  { printf '\033[1m==> %s\033[0m\n' "$*"; }
note() { printf '    %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }
fail() { FAILED="$FAILED $1"; note "could not install $1 — $2"; }

apt_install() {
  if ! have apt-get; then return 1; fi
  if [ "$APT_READY" -eq 0 ]; then $SUDO apt-get update -qq || true; APT_READY=1; fi
  DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y -qq --no-install-recommends "$@" >/dev/null
}

node_major() { node --version 2>/dev/null | sed 's/^v//; s/\..*//'; }

install_node() {
  if have node && [ "$(node_major)" -ge 18 ] 2>/dev/null; then return 0; fi
  apt_install nodejs npm || true
  if have node && [ "$(node_major)" -ge 18 ] 2>/dev/null; then return 0; fi
  note "the distribution's Node.js is older than 18; adding the NodeSource repository"
  apt_install curl ca-certificates || return 1
  curl -fsSL https://deb.nodesource.com/setup_22.x | $SUDO -E bash - >/dev/null 2>&1 || return 1
  apt_install nodejs
}

install_typescript() {
  have tsc && return 0
  install_node || return 1
  have npm || apt_install npm || return 1
  $SUDO npm install --global --silent typescript
}

install_dart() {
  have dart && return 0
  local arch url dir
  case "$ARCH" in amd64) arch=x64 ;; arm64) arch=arm64 ;; *) return 1 ;; esac
  url="https://storage.googleapis.com/dart-archive/channels/stable/release/latest/sdk/dartsdk-linux-${arch}-release.zip"
  dir="$HOME/.fluidian/toolchains"
  apt_install curl unzip ca-certificates || return 1
  mkdir -p "$dir" && curl -fsSL "$url" -o "$dir/dart.zip" && unzip -q -o "$dir/dart.zip" -d "$dir" && rm -f "$dir/dart.zip" || return 1
  note "Dart was unpacked to $dir/dart-sdk (the test runner looks there; add $dir/dart-sdk/bin to PATH to use it yourself)"
}

install_csharp() {
  have dotnet && return 0
  apt_install dotnet-sdk-8.0 && return 0
  note "dotnet-sdk-8.0 is not in this distribution's repositories; using Microsoft's install script"
  apt_install curl ca-certificates libicu-dev || return 1
  curl -fsSL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh && bash /tmp/dotnet-install.sh --channel 8.0 --install-dir "$HOME/.dotnet" >/dev/null
}

install_browser() {
  for name in google-chrome chromium chromium-browser; do have "$name" && return 0; done
  apt_install chromium || apt_install chromium-browser
}

install_one() {
  case "$1" in
    node)       install_node ;;
    typescript) install_typescript ;;
    go)         have go      || apt_install golang-go ;;
    rust)       have cargo   || apt_install cargo rustc ;;
    java)       have javac   || apt_install default-jdk-headless ;;
    kotlin)     have kotlinc || { have javac || apt_install default-jdk-headless; apt_install kotlin; } ;;
    csharp)     install_csharp ;;
    cpp)        have g++     || apt_install g++ ;;
    ruby)       have ruby    || apt_install ruby ;;
    php)        have php     || apt_install php-cli ;;
    dart)       install_dart ;;
    elixir)     have elixir  || apt_install elixir ;;
    lua)        have lua5.4  || have lua5.3 || have lua || apt_install lua5.4 ;;
    browser)    install_browser ;;
    *)          note "unknown toolchain: $1"; return 1 ;;
  esac
}

probe() {
  case "$1" in
    node) have node && node --version ;;        typescript) have tsc && tsc --version ;;
    go) have go && go version | cut -d' ' -f3 ;; rust) have cargo && cargo --version | cut -d' ' -f2 ;;
    java) have javac && javac -version 2>&1 | tail -1 ;;   kotlin) have kotlinc && echo installed ;;
    csharp) { have dotnet || [ -x "$HOME/.dotnet/dotnet" ]; } && echo installed ;;
    cpp) have g++ && g++ -dumpversion ;;         ruby) have ruby && ruby -e 'print RUBY_VERSION' ;;
    php) have php && php -r 'echo PHP_VERSION;' ;;
    dart) { have dart || [ -x "$HOME/.fluidian/toolchains/dart-sdk/bin/dart" ]; } && echo installed ;;
    elixir) have elixir && echo installed ;;     lua) { have lua5.4 || have lua5.3 || have lua; } && echo installed ;;
    browser) { have google-chrome || have chromium || have chromium-browser; } && echo installed ;;
  esac
}

say "Fluidian toolchains ($ARCH)"
have python3 && note "python      $(python3 --version 2>&1 | cut -d' ' -f2)  (required; already present)"
for lang in $WANT; do
  if [ "$CHECK" -eq 0 ] && [ -z "$(probe "$lang")" ]; then
    say "Installing $lang"
    install_one "$lang" || fail "$lang" "see the messages above; install it manually or skip this SDK"
  fi
  status="$(probe "$lang")"
  printf '    %-11s %s\n' "$lang" "${status:-missing}"
done

if [ -n "$FAILED" ]; then
  say "Finished with gaps:$FAILED"
  note "The framework works without them; the matching SDK tests will be skipped."
  exit 0
fi
say "Done. Run ./fluidian doctor to confirm, then ./fluidian test."
