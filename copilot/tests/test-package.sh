#!/usr/bin/env bash
# test-package.sh — checks the structure of the Copilot edition aml package.
#   A. names and descriptions of the 7 skills, no other edition's notation   B. every link inside the package points inside the package
#   C. resources, the hook, and the measuring script work even when only the package is copied (no sibling folders)
#   D. (if copilot is available) installing into an isolated COPILOT_HOME lists 7 skills — the model is never called
# Usage (from the repo root): bash copilot/tests/test-package.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COPILOT_DIR="$(cd "$HERE/.." && pwd)"
PKG="$COPILOT_DIR/aml"
SKILLS="new go review next rule status doctor"

fail() { echo "FAIL: $*" >&2; exit 1; }

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

# Takes one package folder and checks its structure (used the same way on the original and the copy)
check_package() {
  local pkg="$1" s n f
  python3 - "$pkg" <<'PY' || exit 1
import json, re, sys
from pathlib import Path
pkg = Path(sys.argv[1]).resolve()
def fail(msg):
    print("FAIL: " + msg, file=sys.stderr); sys.exit(1)
m = json.loads((pkg / "plugin.json").read_text())
if (m.get("name"), m.get("skills"), m.get("agents"), m.get("hooks")) != ("aml", "skills/", "agents/", "hooks.json"):
    fail("plugin.json name/skills/agents/hooks differ")
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
    if grep -nE '\$aml[:-]|CLAUDE_PLUGIN_ROOT|CODEX_' "$pkg/skills/$s/SKILL.md" >&2; then
      fail "A $s has another edition's calls or paths — the Copilot edition uses the /aml:go form"
    fi
  done
  [ "$(find "$pkg/skills" -name SKILL.md | wc -l)" -eq 7 ] || fail "A there aren't 7 skills"
  # Phrases easily left over when carrying things over from the Codex edition — the Copilot edition has a hook
  if grep -rnE 'no AML-specific blocking hook|~/\.codex|codex-measure' "$pkg" >&2; then
    fail "A Codex-edition-only phrases are left"
  fi
  for f in hooks.json hooks/aml-guard.sh agents/verifier.agent.md scripts/observe.py \
           templates/agents.template.md templates/skill.template.md \
           references/switching.md references/verification.md references/telemetry.md references/artifact-chain.md; do
    [ -f "$pkg/$f" ] || fail "C resource missing: $f"
  done
  grep -q '^name: verifier$' "$pkg/agents/verifier.agent.md" || fail "C the verifier agent's name differs"
}

# Whether the marketplace file points to the plugin correctly
python3 - "$COPILOT_DIR" <<'PY' || exit 1
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
def fail(msg):
    print("FAIL: " + msg, file=sys.stderr); sys.exit(1)
mk = json.loads((root / ".github" / "plugin" / "marketplace.json").read_text())
pj = json.loads((root / "aml" / "plugin.json").read_text())
if mk.get("name") != "automix-light-en":
    fail("marketplace.json name isn't automix-light-en")
entry = [p for p in mk.get("plugins", []) if p.get("name") == "aml"]
if len(entry) != 1 or entry[0].get("source") != "./aml":
    fail("marketplace.json doesn't point to ./aml")
if entry[0].get("version") != pj.get("version"):
    fail("marketplace.json and plugin.json versions differ")
if (root / ".claude-plugin").exists() or (root / "aml" / ".claude-plugin").exists():
    fail("the Copilot edition has .claude-plugin — it would be confused with the Claude edition")
PY

check_package "$PKG"
echo "OK: A·B passed (7 skills, no other edition's notation, links stay inside the package)"

# C. Copy only the package — without sibling folders (claude-code/, codex/, copilot/tests)
cp -r "$PKG" "$TMP/aml"
check_package "$TMP/aml"
mkdir -p "$TMP/proj"
printf '# Progress log\n- Usage: gpt-test · 1m 0s · tokens in 10 / out 5 (cache read 0 / write 0) · cost unknown · AI credits 0.01\n' > "$TMP/proj/progress.md"
OUT="$(cd "$TMP/proj" && python3 -B "$TMP/aml/scripts/observe.py" summary progress.md)"
echo "$OUT" | grep -q '^Summary: 1 task ' || fail "C copy summary: $OUT"
OUT="$(cd "$TMP/proj" && env -u COPILOT_AGENT_SESSION_ID python3 -B "$TMP/aml/scripts/observe.py" task-done --since 2026-10-19T00:00:00Z --label x)"
[ "${OUT#Usage: no record}" != "$OUT" ] || fail "C copy task-done: $OUT"
printf '# spec\n' > "$TMP/proj/spec.md"; printf '# task\n' > "$TMP/proj/task.md"
set +e
printf '{"cwd": "%s", "toolName": "bash", "toolArgs": {"command": "git push --force"}}' "$TMP/proj" \
  | (cd "$TMP/proj" && bash "$TMP/aml/hooks/aml-guard.sh" >/dev/null 2>&1); code=$?
set -e
[ "$code" = 2 ] || fail "C the copied hook didn't block a force push (exit code $code)"
echo "OK: C passed (works with only the package copied)"

# D. Isolated install with the real Copilot CLI (skipped if missing — never touches the real ~/.copilot)
if command -v copilot >/dev/null 2>&1; then
  export COPILOT_HOME="$TMP/copilot-home"; mkdir -p "$COPILOT_HOME"
  copilot plugin marketplace add "$COPILOT_DIR" >/dev/null 2>&1 || fail "D couldn't add the marketplace"
  copilot plugin install aml@automix-light-en >/dev/null 2>&1 || fail "D couldn't install the plugin"
  copilot plugin list --json 2>/dev/null | python3 -c '
import json, sys
ok = [p for p in json.load(sys.stdin) if p.get("name") == "aml" and p.get("marketplace") == "automix-light-en" and p.get("enabled")]
sys.exit(0 if ok else 1)' || fail "D no enabled aml@automix-light-en in the install list"
  mkdir -p "$TMP/empty"
  (cd "$TMP/empty" && copilot skill list --json 2>/dev/null) | python3 -c '
import json, sys
names = sorted(s["name"] for s in json.load(sys.stdin) if s.get("source") == "plugin" and "/aml/skills/" in s.get("path", ""))
want = sorted("new go review next rule status doctor".split())
if names != want:
    print("FAIL: D the skill list differs: %s" % names, file=sys.stderr); sys.exit(1)' || exit 1
  echo "OK: D passed (7 skills in the isolated install — shown like /aml:go in the conversation)"
else
  echo "Skipped: D (no copilot command)"
fi

echo "OK: test-package passed"
