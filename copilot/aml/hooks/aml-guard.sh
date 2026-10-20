#!/usr/bin/env bash
# aml-guard.sh — beginner safety net (Copilot CLI preToolUse hook).
#
# Blocks only three things that are hard to undo:
#   1. Secret keys getting into the repository (.env)
#   2. Changing test files while fixing a bug (when .aml/FIXING exists)
#   3. Irreversible commands (force push · hard reset · wiping a folder)
#
# Principles:
#   - Only works in aml projects that have spec.md and task.md. No effect on other repositories.
#   - When it blocks, it says why and what to do instead.
#   - Never gets in the way of work no matter what — if there is no python3 or the input is odd, let it through (exit 0).
#     Copilot blocks the tool if a hook ends with a code other than 0·2 (fail-closed),
#     so at the very bottom everything other than 0 and 2 is turned into 0.
#   - To turn it off, guard: "off" in .aml/config.yaml.
#
# Input (Copilot): {"sessionId", "timestamp", "cwd", "toolName", "toolArgs"}
#   toolArgs can be an object or a JSON string.
# Exit codes: 0 = pass, 2 = block (the reason goes to stderr, and also to stdout as permissionDecisionReason — see the bottom).

set -o pipefail

guard() {
  command -v python3 >/dev/null 2>&1 || return 0

  local INPUT
  INPUT=$(cat 2>/dev/null || echo "")
  [[ -z "$INPUT" ]] && return 0

  # Pull out four things with one python call.
  # line 1 = kind (shell / file / blank), line 2 = cwd, line 3 = files to change (tab-separated), everything after = command
  # (commands can have newlines, so the command goes last.)
  local PARSED
  PARSED=$(printf '%s' "$INPUT" | python3 -c '
import json, re, sys
try:
    d = json.load(sys.stdin)
    name = d.get("toolName") or d.get("tool_name") or ""
    args = d.get("toolArgs", d.get("tool_input"))
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            args = {"command": args}
    if not isinstance(args, dict):
        args = {}
    if name in ("bash", "powershell", "Bash"):
        kind, cmd, paths = "shell", args.get("command") or "", []
    else:
        kind, cmd = "file", ""
        paths = [args.get(k) for k in ("path", "file_path", "filePath") if isinstance(args.get(k), str)]
        # Some tools change several files in one patch — look for "*** Update File: <path>" lines.
        for v in args.values():
            if isinstance(v, str):
                paths += re.findall(r"^\*\*\* (?:Update|Add|Delete) File: (.+)$", v, re.M)
        if not paths:
            kind = ""
    print(kind)
    print(d.get("cwd", "") or "")
    print("\t".join(p.strip() for p in paths))
    print(cmd, end="")
except Exception:
    pass
' 2>/dev/null || echo "")

  [[ -z "$PARSED" ]] && return 0

  local KIND R1 CWD R2 FILES CMD
  KIND="${PARSED%%$'\n'*}"
  R1="${PARSED#*$'\n'}"; [[ "$R1" == "$PARSED" ]] && R1=""
  CWD="${R1%%$'\n'*}"
  R2="${R1#*$'\n'}"; [[ "$R2" == "$R1" ]] && R2=""
  FILES="${R2%%$'\n'*}"
  CMD="${R2#*$'\n'}"; [[ "$CMD" == "$R2" ]] && CMD=""

  [[ -z "$KIND" ]] && return 0

  local ROOT="${CWD:-$PWD}"
  [[ -d "$ROOT" ]] || ROOT="$PWD"

  # Not an aml project: do nothing.
  [[ -f "$ROOT/spec.md" && -f "$ROOT/task.md" ]] || return 0

  # Turned off: do nothing.
  if [[ -f "$ROOT/.aml/config.yaml" ]] \
     && grep -qE '^[[:space:]]*guard:[[:space:]]*"?off"?[[:space:]]*$' "$ROOT/.aml/config.yaml" 2>/dev/null; then
    return 0
  fi

  # ── Guard 2: protect test files while fixing (tools that create or change files) ──
  if [[ "$KIND" == "file" ]]; then
    if [[ -f "$ROOT/.aml/FIXING" && -n "$FILES" ]]; then
      local FILE_PATH
      while IFS= read -r -d $'\t' FILE_PATH || [[ -n "$FILE_PATH" ]]; do
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
            return 2
            ;;
        esac
      done < <(printf '%s' "$FILES")
    fi
    return 0
  fi

  # The remaining guards only apply to shell commands.
  [[ -z "$CMD" ]] && return 0

  # ── Guard 1: keep secret keys out of the repository ────────────────────────
  if echo "$CMD" | grep -qE '(>|>>)[[:space:]]*[^[:space:]]*\.env' \
     || echo "$CMD" | grep -qE 'git[[:space:]]+add[[:space:]][^;&|]*\.env'; then
    cat >&2 <<'MSG'
❌ Blocked by the aml safety net — a secret key could get into the repository.
   Files like .env hold passwords and API keys. Once they get into the repository,
   they stay in the history even if you delete them later.
   → Don't put .env in the repository; list it in .gitignore.
   → If a value needs changing, tell Copilot "put this value in .env" and check it with your own eyes.
MSG
    return 2
  fi

  # ── Guard 3: irreversible commands ─────────────────────────────────────────
  local FORCE_RE='git[[:space:]]+push[^;&|]*--force([[:space:]]|$)'
  local LEASE_RE='git[[:space:]]+push[^;&|]*--force-with-lease'
  if echo "$CMD" | grep -qE "$FORCE_RE" && ! echo "$CMD" | grep -qE "$LEASE_RE"; then
    cat >&2 <<'MSG'
❌ Blocked by the aml safety net — a force push overwrites history that's already been pushed.
   → If you really need it, use --force-with-lease. It stops on its own if it would overwrite someone else's work.
MSG
    return 2
  fi

  if echo "$CMD" | grep -qE 'git[[:space:]]+reset[^;&|]*--hard'; then
    cat >&2 <<'MSG'
❌ Blocked by the aml safety net — a hard reset deletes unsaved work for good.
   → To set it aside for a while: git stash  (bring it back later with git stash pop)
   → To go back to a specific commit: git revert <commit>  (undoes without erasing history)
   → If it really has to be thrown away, the user should run it directly in the terminal.
MSG
    return 2
  fi

  if echo "$CMD" | grep -qE '(^|[[:space:];&|(])rm[[:space:]]+(-[^[:space:]]*[rR][^[:space:]]*[[:space:]]+)+(/|~|\.|\*|\./\*|/\*|\$HOME)([[:space:]]|$)'; then
    cat >&2 <<'MSG'
❌ Blocked by the aml safety net — this command wipes a whole folder, and it can't be undone.
   → Name exactly what to delete (e.g. rm -rf build).
   → If it really has to be deleted like this, the user should run it directly in the terminal.
MSG
    return 2
  fi

  return 0
}

# Write the block reason to stderr, and also to stdout as permissionDecisionReason so Copilot shows it.
REASON=$(guard 2>&1 >/dev/null)
if [[ $? == 2 ]]; then
  printf '%s\n' "$REASON" >&2
  printf '%s' "$REASON" | python3 -c '
import json, sys
print(json.dumps({"permissionDecision": "deny", "permissionDecisionReason": sys.stdin.read().strip()}, ensure_ascii=False))
' 2>/dev/null
  exit 2
fi
exit 0
