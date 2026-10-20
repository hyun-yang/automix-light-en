#!/usr/bin/env bash
# test-templates.sh — checks that the 5 common templates (spec·task·progress·intent·review)
# are identical down to the letter in the Claude and Codex packages, and that no tool-specific notes slipped in.
# Usage (from the repo root): bash codex/tests/test-templates.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_T="$HERE/../../claude-code/aml/templates"
CODEX_T="$HERE/../aml/templates"
COMMON="spec task progress intent review"

fail() { echo "FAIL: $*" >&2; exit 1; }

# 0 if both folders have all common templates with the same content, 1 otherwise
same_templates() {
  local a="$1" b="$2" t
  for t in $COMMON; do
    [ -f "$a/$t.template.md" ] && [ -f "$b/$t.template.md" ] || return 1
    cmp -s "$a/$t.template.md" "$b/$t.template.md" || return 1
  done
}

# A. The common templates of the two real packages are identical
same_templates "$CLAUDE_T" "$CODEX_T" || {
  for t in $COMMON; do diff -u "$CLAUDE_T/$t.template.md" "$CODEX_T/$t.template.md" >&2 || true; done
  fail "A common templates differ between the two packages — change both together"
}
echo "OK: A passed (5 common templates identical)"

# B. The common templates have no tool-specific paths or calls
for t in $COMMON; do
  if grep -nE '/aml:|\$aml[-:]|\.claude/|\.agents/|CLAUDE\.md|AGENTS\.md' "$CODEX_T/$t.template.md" >&2; then
    fail "B $t.template.md has tool-specific notes — move them to commands, skills, or tool-specific templates"
  fi
done
echo "OK: B passed (no tool-specific notes)"

# C. The check really catches things: changing one test copy fails, the original passes
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/a" "$TMP/b"
cp "$CLAUDE_T"/*.template.md "$TMP/a/"; cp "$CODEX_T"/*.template.md "$TMP/b/"
same_templates "$TMP/a" "$TMP/b" || fail "C1 the untouched copies are reported as different"
for t in $COMMON; do
  cp "$TMP/b/$t.template.md" "$TMP/keep"
  echo "a line changed on one side only" >> "$TMP/b/$t.template.md"
  same_templates "$TMP/a" "$TMP/b" && fail "C2 $t was changed on one side only but the check passed"
  mv "$TMP/keep" "$TMP/b/$t.template.md"
done
rm "$TMP/b/spec.template.md"
same_templates "$TMP/a" "$TMP/b" && fail "C3 a file is missing on one side but the check passed"
echo "OK: C passed (changing one side fails)"

# D. Tool-specific templates point to their own paths
grep -q 'AGENTS.md' "$CODEX_T/agents.template.md"        || fail "D agents.template.md does not mention AGENTS.md"
grep -q '.agents/skills/' "$CODEX_T/skill.template.md"   || fail "D Codex skill.template.md does not mention .agents/skills/"
if grep -nE '/aml:|\.claude/|CLAUDE\.md' "$CODEX_T/agents.template.md" "$CODEX_T/skill.template.md" >&2; then
  fail "D Codex-specific templates contain Claude paths or calls"
fi
echo "OK: D passed (tool-specific template paths)"

echo "OK: test-templates passed"
