#!/usr/bin/env bash
# Run every Fluidian test and print one clear result. Run it from the fluidian folder:
#
#   bash scripts/test-all.sh           # everything, including browser checks if Chrome is installed
#   bash scripts/test-all.sh --quick   # engine and runtime only, takes seconds
set -u
cd "$(dirname "$0")/.." || exit 1

ARGS=""
if [ "${1:-}" = "--quick" ]; then
  ARGS="--quick"
elif command -v google-chrome >/dev/null 2>&1 || command -v chromium >/dev/null 2>&1 || command -v chromium-browser >/dev/null 2>&1; then
  ARGS="--browser"
else
  echo "Chrome not found, so browser checks are skipped. Run setup again to install it."
fi

./fluidian test $ARGS
status=$?
echo
if [ "$status" -eq 0 ]; then
  echo "RESULT: ALL TESTS PASSED"
else
  echo "RESULT: SOME TESTS FAILED. The lines marked FAIL above say which ones, and why."
fi
exit "$status"
