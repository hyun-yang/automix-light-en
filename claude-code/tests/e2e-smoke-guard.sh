#!/usr/bin/env bash
# e2e-smoke-guard.sh — checks the aml safety net (hooks/aml-guard.sh)
#
# The hook blocks only three things, does nothing outside aml projects,
# and must fail open (let things through) no matter what. Tested without calling Claude.

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

# run <description> <expected exit code> <tool_name> <cwd> <file_path> <command>
run() {
  local desc="$1" want="$2" tool="$3" cwd="$4" fp="$5" cmd="$6"
  local json out code
  json=$(TOOL="$tool" CWD="$cwd" FP="$fp" CMD="$cmd" python3 -c '
import json, os
print(json.dumps({
    "tool_name": os.environ["TOOL"],
    "cwd": os.environ["CWD"],
    "tool_input": {"file_path": os.environ["FP"], "command": os.environ["CMD"]},
}))')
  out=$(printf '%s' "$json" | bash "$GUARD" 2>&1); code=$?
  if [[ "$code" != "$want" ]]; then
    echo "FAIL: $desc — expected exit code $want, got $code" >&2
    echo "      output: $out" >&2
    exit 1
  fi
  # If it blocked, the reason and what to do must both be there.
  if [[ "$want" == "2" ]]; then
    echo "$out" | grep -q "Blocked by the aml safety net" || { echo "FAIL: $desc — no reason for the block" >&2; exit 1; }
    echo "$out" | grep -q "→" || { echo "FAIL: $desc — no next step (→)" >&2; exit 1; }
  fi
}

FORCE_PUSH='git push --force origin main'
LEASE_PUSH='git push --force-with-lease origin main'

# ── A. Scope: only works in aml projects ─────────────────────────────────────
run "A1 .env redirect in a non-aml folder"  0 Bash "$PLAIN" "" 'echo KEY=1 >> .env'
run "A2 force push in a non-aml folder"     0 Bash "$PLAIN" "" "$FORCE_PUSH"
run "A3 ordinary command in an aml folder"  0 Bash "$TMP"   "" 'ls -la'
echo "OK: A passed (scope)"

# ── B. Guard 1 — secret keys ─────────────────────────────────────────────────
run "B1 overwrite .env"          2 Bash "$TMP" "" 'echo KEY=1 > .env'
run "B2 append to .env"          2 Bash "$TMP" "" 'echo KEY=1 >> .env.local'
run "B3 git add .env"            2 Bash "$TMP" "" 'git add .env'
run "B4 ordinary redirect"       0 Bash "$TMP" "" 'echo hi > out.txt'
run "B5 reading .env passes"     0 Bash "$TMP" "" 'cat .env'
echo "OK: B passed (secret keys)"

# ── C. Guard 3 — irreversible commands ───────────────────────────────────────
run "C1 force push"                   2 Bash "$TMP" "" "$FORCE_PUSH"
run "C2 --force-with-lease passes"    0 Bash "$TMP" "" "$LEASE_PUSH"
run "C3 hard reset"                   2 Bash "$TMP" "" 'git reset --hard HEAD~1'
run "C4 wipe everything (home)"       2 Bash "$TMP" "" 'rm -rf ~'
run "C5 wipe everything (this folder)" 2 Bash "$TMP" "" 'rm -rf .'
run "C6 delete with a clear target"   0 Bash "$TMP" "" 'rm -rf build'
run "C7 ordinary push"                0 Bash "$TMP" "" 'git push origin main'
echo "OK: C passed (irreversible commands)"

# ── D. Guard 2 — protect test files while fixing ─────────────────────────────
run "D1 without the marker, test files pass" 0 Edit "$TMP" "$TMP/tests/test_app.py" ""
mkdir -p "$TMP/.aml" && touch "$TMP/.aml/FIXING"
run "D2 test file while fixing"          2 Edit  "$TMP" "$TMP/tests/test_app.py" ""
run "D3 spec file while fixing"          2 Write "$TMP" "$TMP/src/app.spec.ts"   ""
run "D4 source file while fixing passes" 0 Edit  "$TMP" "$TMP/src/app.py"        ""
run "D5 Bash while fixing isn't this guard's business" 0 Bash "$TMP" "" 'ls tests/'
rm -f "$TMP/.aml/FIXING"
run "D6 removing the marker lets it through again" 0 Edit "$TMP" "$TMP/tests/test_app.py" ""
echo "OK: D passed (test file protection)"

# ── E. Turning off + fail-open ───────────────────────────────────────────────
printf 'guard: "off"\n' > "$TMP/.aml/config.yaml"
run "E1 guard off — secret key passes"  0 Bash "$TMP" "" 'echo KEY=1 >> .env'
run "E2 guard off — force push passes"  0 Bash "$TMP" "" "$FORCE_PUSH"
printf 'guard: "on"\n' > "$TMP/.aml/config.yaml"
run "E3 guard on — blocks again"        2 Bash "$TMP" "" 'echo KEY=1 >> .env'
rm -f "$TMP/.aml/config.yaml"

# Broken input / empty input / unknown tool → pass
out=$(printf 'not json at all' | bash "$GUARD" 2>&1); code=$?
[[ "$code" == "0" ]] || { echo "FAIL: E4 broken JSON must pass (exit code $code)" >&2; exit 1; }
out=$(printf '' | bash "$GUARD" 2>&1); code=$?
[[ "$code" == "0" ]] || { echo "FAIL: E5 empty input must pass (exit code $code)" >&2; exit 1; }
run "E6 unknown tool passes" 0 WebFetch "$TMP" "" ""
echo "OK: E passed (turning off + fail-open)"

# ── F. Plugin wiring ─────────────────────────────────────────────────────────
PJ="$HERE/../aml/.claude-plugin/plugin.json"
python3 - "$PJ" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
hooks = d.get("hooks", {}).get("PreToolUse", [])
assert hooks, "plugin.json has no PreToolUse hook"
entry = hooks[0]
assert "Edit" in entry.get("matcher", "") and "Bash" in entry.get("matcher", ""), \
    "matcher must include both Bash and Edit: %r" % entry.get("matcher")
cmd = entry["hooks"][0]["command"]
assert "aml-guard.sh" in cmd and "CLAUDE_PLUGIN_ROOT" in cmd, \
    "hook command must point to ${CLAUDE_PLUGIN_ROOT}/hooks/aml-guard.sh: %r" % cmd
PY
[[ $? == 0 ]] || exit 1
echo "OK: F passed (plugin wiring)"

echo "OK: e2e-smoke-guard passed"
