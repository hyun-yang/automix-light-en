#!/usr/bin/env bash
# install.sh — copies the automix-light-en marketplace to a fixed path
# and prints the /plugin commands to run inside Claude Code.
#
# Usage (from the repo root):
#   $ cd automix-light-en
#   $ bash claude-code/install.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${AUTOMIX_LIGHT_MARKETPLACE_DIR:-$HOME/.claude-marketplaces/automix-light-en}"

echo "automix-light-en installer"
echo "─────────────────────────────────────────────────"
echo "From: $SCRIPT_DIR"
echo "To:   $TARGET"
echo

# 1. Check this is the marketplace root
if [[ ! -f "$SCRIPT_DIR/.claude-plugin/marketplace.json" ]]; then
  echo "Error: $SCRIPT_DIR/.claude-plugin/marketplace.json not found." >&2
  echo "       Run the repository's claude-code/install.sh as is (e.g. bash claude-code/install.sh)." >&2
  exit 1
fi

# 2. Check the JSON files (only if python3 is available)
if command -v python3 >/dev/null 2>&1; then
  python3 -c "import json; json.load(open('$SCRIPT_DIR/.claude-plugin/marketplace.json'))" \
    || { echo "Error: marketplace.json is not valid JSON" >&2; exit 1; }
  python3 -c "import json; json.load(open('$SCRIPT_DIR/aml/.claude-plugin/plugin.json'))" \
    || { echo "Error: plugin.json is not valid JSON" >&2; exit 1; }
fi

# 3. Copy to the fixed path (back up any existing install)
#    Move only what the marketplace needs — .git/.venv/.idea are not copied.
mkdir -p "$(dirname "$TARGET")"
if [[ -d "$TARGET" ]]; then
  echo "Backing up the existing install to ${TARGET}.bak"
  rm -rf "${TARGET}.bak"
  mv "$TARGET" "${TARGET}.bak"
fi
mkdir -p "$TARGET"
cp -r "$SCRIPT_DIR/.claude-plugin" "$SCRIPT_DIR/aml" "$TARGET/"

# 4. Next steps
cat <<MSG
✓ Copied: $TARGET

Next — run these inside Claude Code:

  1. Add the marketplace:
     /plugin marketplace add $TARGET

  2. Install the plugin:
     /plugin install aml@automix-light-en

  3. Check:
     /help                  # you're set if /aml:new, /aml:go, /aml:review, /aml:next show up

MSG
