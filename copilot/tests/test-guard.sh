#!/usr/bin/env bash
# test-guard.sh — checks the Copilot edition's aml safety net (hooks/aml-guard.sh)
#
# The hook blocks only three things, does nothing outside aml projects,
# and must end only with 0 (pass) or 2 (block) no matter what — Copilot treats any other code as "block".
# Tested without calling Copilot, by imitating the shape of Copilot's preToolUse input.
# Usage (from the repo root): bash copilot/tests/test-guard.sh

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GUARD="$HERE/../aml/hooks/aml-guard.sh"
[[ -f "$GUARD" ]] || { echo "FAIL: hook file not found: $GUARD" >&2; exit 1; }
bash -n "$GUARD" || { echo "FAIL: hook shell syntax error" >&2; exit 1; }

TMP="$(mktemp -d)"
PLAIN="$(mktemp -d)"        # a folder that isn't an aml project
trap 'rm -rf "$TMP" "$PLAIN"' EXIT

printf '# spec\n' > "$TMP/spec.md"
printf '# task\n' > "$TMP/task.md"

# check <description> <expected exit code> <input JSON>
check() {
  local desc="$1" want="$2" json="$3" out code
  # Run the hook from an empty folder, so the result is the same even if the test runs inside an aml project.
  out=$(cd "$PLAIN" && printf '%s' "$json" | bash "$GUARD" 2>&1); code=$?
  if [[ "$code" != "$want" ]]; then
    echo "FAIL: $desc — expected exit code $want, got $code" >&2
    echo "      output: $out" >&2
    exit 1
  fi
  # If it blocked, the reason and what to do must both be there.
  if [[ "$want" == "2" ]]; then
    echo "$out" | grep -q "Blocked by the aml safety net" || { echo "FAIL: $desc — no reason for the block" >&2; exit 1; }
    echo "$out" | grep -q "→" || { echo "FAIL: $desc — no next step (→)" >&2; exit 1; }
    # Copilot shows permissionDecisionReason on stdout as the block reason (stderr isn't shown).
    stdout=$(cd "$PLAIN" && printf '%s' "$json" | bash "$GUARD" 2>/dev/null)
    printf '%s' "$stdout" | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d.get("permissionDecision") == "deny"
r = d.get("permissionDecisionReason", "")
assert "Blocked by the aml safety net" in r and "→" in r
' 2>/dev/null || { echo "FAIL: $desc — no block reason (permissionDecisionReason) on stdout: $stdout" >&2; exit 1; }
  fi
}

# sh <description> <expected> <cwd> <command>        — the bash tool
sh_() {
  local json
  json=$(CWD="$3" CMD="$4" python3 -c '
import json, os
print(json.dumps({"sessionId": "s1", "timestamp": 1, "cwd": os.environ["CWD"],
                  "toolName": "bash", "toolArgs": {"command": os.environ["CMD"], "description": "x"}}))')
  check "$1" "$2" "$json"
}

# file <description> <expected> <tool> <cwd> <path>   — tools that create or change files
file_() {
  local json
  json=$(TOOL="$3" CWD="$4" FP="$5" python3 -c '
import json, os
print(json.dumps({"sessionId": "s1", "timestamp": 1, "cwd": os.environ["CWD"],
                  "toolName": os.environ["TOOL"], "toolArgs": {"path": os.environ["FP"], "new_str": "x"}}))')
  check "$1" "$2" "$json"
}

FORCE_PUSH='git push --force origin main'
LEASE_PUSH='git push --force-with-lease origin main'

# ── A. Scope: only works in aml projects ─────────────────────────────────────
sh_ "A1 .env redirect in a non-aml folder"  0 "$PLAIN" 'echo KEY=1 >> .env'
sh_ "A2 force push in a non-aml folder"     0 "$PLAIN" "$FORCE_PUSH"
sh_ "A3 ordinary command in an aml folder"  0 "$TMP"   'ls -la'
echo "OK: A passed (scope)"

# ── B. Guard 1 — secret keys ─────────────────────────────────────────────────
sh_ "B1 overwrite .env"       2 "$TMP" 'echo KEY=1 > .env'
sh_ "B2 append to .env"       2 "$TMP" 'echo KEY=1 >> .env.local'
sh_ "B3 git add .env"         2 "$TMP" 'git add .env'
sh_ "B4 ordinary redirect"    0 "$TMP" 'echo hi > out.txt'
sh_ "B5 reading .env passes"  0 "$TMP" 'cat .env'
echo "OK: B passed (secret keys)"

# ── C. Guard 3 — irreversible commands ───────────────────────────────────────
sh_ "C1 force push"                  2 "$TMP" "$FORCE_PUSH"
sh_ "C2 --force-with-lease passes"  0 "$TMP" "$LEASE_PUSH"
sh_ "C3 hard reset"                  2 "$TMP" 'git reset --hard HEAD~1'
sh_ "C4 wipe everything (home)"      2 "$TMP" 'rm -rf ~'
sh_ "C5 wipe everything (this folder)" 2 "$TMP" 'rm -rf .'
sh_ "C6 delete with a clear target"  0 "$TMP" 'rm -rf build'
sh_ "C7 ordinary push"               0 "$TMP" 'git push origin main'
sh_ "C8 hard reset inside a multi-line command" 2 "$TMP" $'git status\ngit reset --hard'
echo "OK: C passed (irreversible commands)"

# ── D. Guard 2 — protect test files while fixing ─────────────────────────────
file_ "D1 without the marker, test files pass" 0 edit "$TMP" "$TMP/tests/test_app.py"
mkdir -p "$TMP/.aml" && touch "$TMP/.aml/FIXING"
file_ "D2 test file while fixing (edit)"    2 edit   "$TMP" "$TMP/tests/test_app.py"
file_ "D3 test file while fixing (create)"  2 create "$TMP" "$TMP/src/app.spec.ts"
file_ "D4 name ending in _test.py while fixing"  2 edit   "$TMP" "$TMP/src/app_test.py"
file_ "D5 source file while fixing passes"  0 edit   "$TMP" "$TMP/src/app.py"
sh_   "D6 bash while fixing isn't this guard's business" 0 "$TMP" 'ls tests/'
PATCH=$'*** Begin Patch\n*** Update File: src/app.py\n@@\n-a\n+b\n*** Update File: tests/test_app.py\n@@\n-a\n+b\n*** End Patch'
json=$(CWD="$TMP" P="$PATCH" python3 -c '
import json, os
print(json.dumps({"sessionId": "s1", "timestamp": 1, "cwd": os.environ["CWD"],
                  "toolName": "apply_patch", "toolArgs": {"input": os.environ["P"]}}))')
check "D7 test file inside a patch while fixing" 2 "$json"
rm -f "$TMP/.aml/FIXING"
file_ "D8 removing the marker lets it through again"  0 edit "$TMP" "$TMP/tests/test_app.py"
echo "OK: D passed (test file protection)"

# ── E. Turning off + ending only with 0·2 ────────────────────────────────────
printf 'guard: "off"\n' > "$TMP/.aml/config.yaml"
sh_ "E1 guard off — secret key passes"  0 "$TMP" 'echo KEY=1 >> .env'
sh_ "E2 guard off — force push passes" 0 "$TMP" "$FORCE_PUSH"
printf 'guard: "on"\n' > "$TMP/.aml/config.yaml"
sh_ "E3 guard on — blocks again"       2 "$TMP" 'echo KEY=1 >> .env'
rm -f "$TMP/.aml/config.yaml"

check "E4 broken JSON passes"        0 'not json at all'
check "E5 empty input passes"        0 ''
check "E6 unknown tool passes"       0 "{\"cwd\": \"$TMP\", \"toolName\": \"web_fetch\", \"toolArgs\": {\"url\": \"https://x\"}}"
check "E7 toolArgs is a JSON string" 2 "{\"cwd\": \"$TMP\", \"toolName\": \"bash\", \"toolArgs\": \"{\\\"command\\\": \\\"git reset --hard\\\"}\"}"
check "E8 toolArgs is missing"       0 "{\"cwd\": \"$TMP\", \"toolName\": \"bash\"}"
check "E9 cwd doesn't exist"         0 '{"cwd": "/no/such/folder", "toolName": "bash", "toolArgs": {"command": "git reset --hard"}}'
# No python3 means pass (take only python3 out of PATH, keep bash)
NOPY="$(mktemp -d)"; ln -s "$(command -v bash)" "$NOPY/bash"
out=$(printf '{"cwd": "%s", "toolName": "bash", "toolArgs": {"command": "git reset --hard"}}' "$TMP" | PATH="$NOPY" "$NOPY/bash" "$GUARD" 2>&1); code=$?
rm -rf "$NOPY"
[[ "$code" == "0" ]] || { echo "FAIL: E10 must pass when there is no python3 (exit code $code)" >&2; exit 1; }
echo "OK: E passed (turning off + ends only with 0·2)"

# ── F. Plugin wiring ─────────────────────────────────────────────────────────
python3 - "$HERE/../aml" <<'PY'
import json, os, sys
root = sys.argv[1]
pj = json.load(open(os.path.join(root, "plugin.json")))
assert pj.get("hooks") == "hooks.json", "hooks in plugin.json must point to hooks.json: %r" % pj.get("hooks")
hj = json.load(open(os.path.join(root, "hooks.json")))
assert hj.get("version") == 1, "version in hooks.json must be 1"
entries = hj.get("hooks", {}).get("preToolUse", [])
assert entries, "hooks.json has no preToolUse hook"
cmd = entries[0].get("bash", "")
assert "${PLUGIN_ROOT}/hooks/aml-guard.sh" in cmd, "hook command must point to ${PLUGIN_ROOT}/hooks/aml-guard.sh: %r" % cmd
assert 0 < entries[0].get("timeoutSec", 30) <= 30, "timeoutSec looks wrong"
PY
[[ $? == 0 ]] || exit 1
echo "OK: F passed (plugin wiring)"

echo "OK: test-guard passed"
