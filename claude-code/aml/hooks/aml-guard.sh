#!/usr/bin/env bash
# aml-guard.sh — beginner safety net (PreToolUse hook).
#
# Blocks only three things that are hard to undo:
#   1. Secret keys getting into the repository (.env)
#   2. Changing test files while fixing a bug (when .aml/FIXING exists)
#   3. Irreversible commands (force push · hard reset · wiping a folder)
#
# Principles:
#   - Only works in aml projects that have spec.md and task.md. No effect on other repositories.
#   - When it blocks, it says why and what to do instead.
#   - Never gets in the way of work no matter what — if there is no working Python or the input is odd, let it through (exit 0).
#   - To turn it off, guard: "off" in .aml/config.yaml.
#
# Exit codes: 0 = pass, 2 = block (the message goes to Claude through stderr).

set -uo pipefail

PY=()
for candidate in "python3" "python" "py -3"; do
  if $candidate -c "import sys" >/dev/null 2>&1; then
    read -r -a PY <<<"$candidate"
    break
  fi
done
(( ${#PY[@]} )) || exit 0

INPUT=$(cat 2>/dev/null || echo "")
[[ -z "$INPUT" ]] && exit 0

# Pull out four things with one python call.
# line 1 = tool_name, line 2 = cwd, line 3 = file_path, everything after = command
# (tool names and paths have no newlines, but commands can, so the command goes last.)
PARSED=$(printf '%s' "$INPUT" | "${PY[@]}" -c '
import json, sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
try:
    d = json.load(sys.stdin)
    inp = d.get("tool_input") or {}
    if not isinstance(inp, dict):
        inp = {}
    print(d.get("tool_name", "") or "")
    print(d.get("cwd", "") or "")
    print(inp.get("file_path") or inp.get("notebook_path") or "")
    print(inp.get("command", "") or "", end="")
except Exception:
    pass
' 2>/dev/null || echo "")

[[ -z "$PARSED" ]] && exit 0

TOOL_NAME="${PARSED%%$'\n'*}"
R1="${PARSED#*$'\n'}"; [[ "$R1" == "$PARSED" ]] && R1=""
CWD="${R1%%$'\n'*}"
R2="${R1#*$'\n'}"; [[ "$R2" == "$R1" ]] && R2=""
FILE_PATH="${R2%%$'\n'*}"
CMD="${R2#*$'\n'}"; [[ "$CMD" == "$R2" ]] && CMD=""

[[ -z "$TOOL_NAME" ]] && exit 0

ROOT="${CWD:-$PWD}"
[[ -d "$ROOT" ]] || ROOT="$PWD"

# Not an aml project: do nothing.
[[ -f "$ROOT/spec.md" && -f "$ROOT/task.md" ]] || exit 0

# Turned off: do nothing.
if [[ -f "$ROOT/.aml/config.yaml" ]] \
   && grep -qE '^[[:space:]]*guard:[[:space:]]*"?off"?[[:space:]]*$' "$ROOT/.aml/config.yaml" 2>/dev/null; then
  exit 0
fi

# ── Guard 2: protect test files while fixing (Edit/Write family) ─────────────
if [[ "$TOOL_NAME" == "Edit" || "$TOOL_NAME" == "Write" || "$TOOL_NAME" == "NotebookEdit" ]]; then
  if [[ -f "$ROOT/.aml/FIXING" && -n "$FILE_PATH" ]]; then
    case "$FILE_PATH" in
      */tests/*|*/test/*|*/__tests__/*|tests/*|test/*|__tests__/*|\
      *test_*.py|*_test.py|*_test.go|*_test.rb|*_spec.rb|*_test.dart|\
      *.test.js|*.test.jsx|*.test.ts|*.test.tsx|\
      *.spec.js|*.spec.jsx|*.spec.ts|*.spec.tsx|*.spec.dart|*Test.java|*Tests.cs)
        cat >&2 <<'MSG'
❌ Blocked by the aml safety net — a bug is being fixed right now (.aml/FIXING).
   Changing a test file doesn't make the bug go away; it makes the check that catches the bug go away.
   → Leave the test as it is and fix the code until it passes.
   → Only if the test itself is written wrong: remove the marker with rm .aml/FIXING and try again.
MSG
        exit 2
        ;;
    esac
  fi
  exit 0
fi

# The remaining guards only apply to Bash commands.
[[ "$TOOL_NAME" == "Bash" ]] || exit 0
[[ -z "$CMD" ]] && exit 0

# ── Guard 1: keep secret keys out of the repository ──────────────────────────
if echo "$CMD" | grep -qE '(>|>>)[[:space:]]*[^[:space:]]*\.env' \
   || echo "$CMD" | grep -qE 'git[[:space:]]+add[[:space:]][^;&|]*\.env'; then
  cat >&2 <<'MSG'
❌ Blocked by the aml safety net — a secret key could get into the repository.
   Files like .env hold passwords and API keys. Once they get into the repository,
   they stay in the history even if you delete them later.
   → Don't put .env in the repository; list it in .gitignore.
   → If a value needs changing, tell Claude "put this value in .env" and check it with your own eyes.
MSG
  exit 2
fi

# ── Guard 3: irreversible commands ───────────────────────────────────────────
FORCE_RE='git[[:space:]]+push[^;&|]*--force([[:space:]]|$)'
LEASE_RE='git[[:space:]]+push[^;&|]*--force-with-lease'
if echo "$CMD" | grep -qE "$FORCE_RE" && ! echo "$CMD" | grep -qE "$LEASE_RE"; then
  cat >&2 <<'MSG'
❌ Blocked by the aml safety net — a force push overwrites history that's already been pushed.
   → If you really need it, use --force-with-lease. It stops on its own if it would overwrite someone else's work.
MSG
  exit 2
fi

if echo "$CMD" | grep -qE 'git[[:space:]]+reset[^;&|]*--hard'; then
  cat >&2 <<'MSG'
❌ Blocked by the aml safety net — a hard reset deletes unsaved work for good.
   → To set it aside for a while: git stash  (bring it back later with git stash pop)
   → To go back to a specific commit: git revert <commit>  (undoes without erasing history)
   → If it really has to be thrown away, the user should run it directly in the terminal.
MSG
  exit 2
fi

if echo "$CMD" | grep -qE '(^|[[:space:];&|(])rm[[:space:]]+(-[^[:space:]]*[rR][^[:space:]]*[[:space:]]+)+(/|~|\.|\*|\./\*|/\*|\$HOME)([[:space:]]|$)'; then
  cat >&2 <<'MSG'
❌ Blocked by the aml safety net — this command wipes a whole folder, and it can't be undone.
   → Name exactly what to delete (e.g. rm -rf build).
   → If it really has to be deleted like this, the user should run it directly in the terminal.
MSG
  exit 2
fi

exit 0
