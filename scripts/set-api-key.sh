#!/usr/bin/env bash
# Save your OpenAI API key once, so you never have to export it again.
#
#   bash scripts/set-api-key.sh            # paste the key (input is hidden)
#   bash scripts/set-api-key.sh --remove   # delete the saved key
#
# The key is stored in ~/.fluidian/openai.env (readable only by you), outside the
# project folder, so it cannot end up in a zip or on GitHub. New terminals load it
# automatically through a line added to ~/.bashrc.
set -eu

DIR="$HOME/.fluidian"
FILE="$DIR/openai.env"
RC="$HOME/.bashrc"
MARK="# fluidian: load OpenAI key"

if [ "${1:-}" = "--remove" ]; then
  rm -f "$FILE"
  if [ -f "$RC" ]; then
    sed -i "/$MARK/d; \#fluidian/openai.env#d" "$RC"
  fi
  echo "Saved key removed."
  exit 0
fi

printf 'Paste your OpenAI API key (it starts with sk-), then press Enter. Input is hidden: '
IFS= read -rs KEY || true
echo
KEY="$(printf '%s' "${KEY:-}" | tr -d '[:space:]')"

case "$KEY" in
  sk-*) ;;
  *) echo "That does not look like an OpenAI key (it should start with sk-). Nothing was saved."; exit 1 ;;
esac

umask 077
mkdir -p "$DIR"
chmod 700 "$DIR"
printf 'export OPENAI_API_KEY=%q\n' "$KEY" > "$FILE"
chmod 600 "$FILE"

touch "$RC"
if ! grep -qF "$MARK" "$RC"; then
  printf '\n%s\n[ -f "%s" ] && . "%s"\n' "$MARK" "$FILE" "$FILE" >> "$RC"
fi

echo "Saved. Key ends in ...${KEY: -4} and loads in every new terminal."
echo "Check that it works:  ./fluidian doctor --live"
