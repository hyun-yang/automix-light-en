#!/usr/bin/env bash
# test-package.sh — checks the structure of the Codex edition aml package.
#   A. names and descriptions of the 7 skills   B. every link inside the package points inside the package
#   C. resources and the measuring script work even when only the package is copied (no sibling folders)
#   D. (if codex is available) installing into an isolated CODEX_HOME puts 7 skills in the cache
#   E. no old name forms (aml-go, $aml:aml-go, etc.) left in docs or skills
# Usage (from the repo root): bash codex/tests/test-package.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODEX_DIR="$(cd "$HERE/.." && pwd)"
PKG="$CODEX_DIR/aml"
SKILLS="new go review next rule status doctor"

fail() { echo "FAIL: $*" >&2; exit 1; }

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

# Takes one package folder and checks its structure (used the same way on the original and the copy)
check_package() {
  local pkg="$1" s n
  python3 - "$pkg" <<'PY' || exit 1
import json, re, sys
from pathlib import Path
pkg = Path(sys.argv[1]).resolve()
def fail(msg):
    print("FAIL: " + msg, file=sys.stderr); sys.exit(1)
m = json.loads((pkg / ".codex-plugin" / "plugin.json").read_text())
if m.get("name") != "aml" or m.get("skills") != "./skills/":
    fail("plugin.json name/skills differ")
for p in pkg.rglob("*.md"):
    for t, _ in re.findall(r"\]\(([^)#\s]+)(#[^)]*)?\)", p.read_text()):
        if t.startswith(("http://", "https://")):
            continue
        tp = (p.parent / t).resolve()
        if not tp.exists():
            fail(f"link {t} in {p.relative_to(pkg)} doesn't exist")
        if pkg not in tp.parents and tp != pkg:
            fail(f"link {t} in {p.relative_to(pkg)} points outside the package")
PY
  for s in $SKILLS; do
    [ -f "$pkg/skills/$s/SKILL.md" ] || fail "A skill missing: $s"
    n="$(sed -n 's/^name: //p' "$pkg/skills/$s/SKILL.md" | head -1)"
    [ "$n" = "$s" ] || fail "A name of $s is '$n'"
    grep -q '^description: .\{20,\}' "$pkg/skills/$s/SKILL.md" || fail "A description of $s is empty or too short"
    if grep -n 'CLAUDE_PLUGIN_ROOT\|/aml:' "$pkg/skills/$s/SKILL.md" | grep -v 'Claude Code' >&2; then
      fail "A $s has Claude edition paths or calls"
    fi
  done
  [ "$(find "$pkg/skills" -name SKILL.md | wc -l)" -eq 7 ] || fail "A there aren't 7 skills"
  for f in templates/agents.template.md templates/skill.template.md references/switching.md \
           references/verification.md references/telemetry.md scripts/observe.py; do
    [ -f "$pkg/$f" ] || fail "C resource missing: $f"
  done
}

check_package "$PKG"
echo "OK: A·B passed (7 skills, links stay inside the package)"

# C. Copy only the package — without sibling folders (claude-code/, codex/tests)
cp -r "$PKG" "$TMP/aml"
check_package "$TMP/aml"
mkdir -p "$TMP/proj"
printf '# Progress log\n- Usage: gpt-test · 1m 0s · tokens in 10 / out 5 (cache read 0) · cost unknown\n' > "$TMP/proj/progress.md"
OUT="$(cd "$TMP/proj" && python3 "$TMP/aml/scripts/observe.py" summary progress.md)"
echo "$OUT" | grep -q '^Summary: 1 task ' || fail "C copy summary: $OUT"
OUT="$(cd "$TMP/proj" && env -u CODEX_THREAD_ID -u CODEX_SESSION_ID python3 "$TMP/aml/scripts/observe.py" task-done --since 2026-10-17T00:00:00Z --label x)"
[ "${OUT#Usage: no record}" != "$OUT" ] || fail "C copy task-done: $OUT"
echo "OK: C passed (works with only the package copied)"

# D. Isolated install with the real Codex CLI (skipped if missing — never touches the real ~/.codex)
if command -v codex >/dev/null 2>&1; then
  export CODEX_HOME="$TMP/codex-home"; mkdir -p "$CODEX_HOME"
  codex plugin marketplace add "$CODEX_DIR" >/dev/null 2>&1 || fail "D couldn't add the marketplace"
  codex plugin add aml@automix-light-en >/dev/null 2>&1 || fail "D couldn't install the plugin"
  codex plugin list 2>/dev/null | grep -q 'aml@automix-light-en *installed, enabled' || fail "D aml not in the install list"
  CACHE="$(find "$CODEX_HOME/plugins/cache" -mindepth 3 -maxdepth 3 -type d | head -1)"
  [ "$(find "$CACHE/skills" -name SKILL.md | wc -l)" -eq 7 ] || fail "D the installed copy doesn't have 7 skills"
  check_package "$CACHE"
  # Without calling the model, pull out only the skill list Codex will see — plugin skills show up like aml:go
  mkdir -p "$TMP/empty" && (cd "$TMP/empty" && codex debug prompt-input "check" >"$TMP/prompt.json" 2>/dev/null) \
    || fail "D codex debug prompt-input failed"
  for s in $SKILLS; do
    grep -q -- "- aml:$s: " "$TMP/prompt.json" || fail "D aml:$s is not in Codex's skill list"
  done
  grep -q -- "- aml:aml-" "$TMP/prompt.json" && fail "D Codex's skill list has the old name aml:aml-*"
  echo "OK: D passed (7 skills in the isolated install, 7 like aml:go in Codex's list)"
else
  echo "Skipped: D (no codex command)"
fi

# E. Old name forms — progress records are a record of their time, so they aren't checked
OLD='aml-(new|go|review|next|rule|status|doctor)([^a-z0-9-]|$)'
if grep -rnIE "$OLD" "$PKG" "$CODEX_DIR/README.md" "$CODEX_DIR/../README.md" >&2; then
  fail "E old name forms are left — change them to the \$aml:go form"
fi
echo "OK: E passed (no old name forms)"

echo "OK: test-package passed"
