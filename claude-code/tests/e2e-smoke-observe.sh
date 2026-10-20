#!/usr/bin/env bash
# e2e-smoke-observe.sh — aml observe.py: adding up usage / the usage line / fail-open
# (Part B also checks the Langfuse dry-run.)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OBSERVE="$HERE/../aml/scripts/observe.py"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
fail() { echo "FAIL: $*" >&2; exit 1; }

[ -f "$OBSERVE" ] || fail "observe.py not found: $OBSERVE"

PROJ="$TMP/proj"; mkdir -p "$PROJ"; cd "$PROJ"

# ── Fake session log: one session JSONL under the encoded cwd folder ─────────
ENC="$(python3 -c 'import os,re; print(re.sub(r"[^A-Za-z0-9]","-",os.path.realpath(os.getcwd())))')"
TR="$TMP/projects/$ENC"; mkdir -p "$TR"
cat > "$TR/session.jsonl" <<EOF
{"type":"assistant","timestamp":"2026-07-01T00:00:10Z","cwd":"$PROJ","message":{"model":"claude-opus-4-8","usage":{"input_tokens":1000,"output_tokens":500,"cache_creation_input_tokens":200,"cache_read_input_tokens":8000}}}
{"type":"assistant","timestamp":"2026-07-01T00:01:00Z","message":{"model":"claude-opus-4-8","usage":{"input_tokens":500,"output_tokens":250,"cache_creation_input_tokens":0,"cache_read_input_tokens":2000}}}
{"type":"user","timestamp":"2026-07-01T00:01:30Z","message":{}}
{"type":"assistant","timestamp":"2026-07-01T02:00:00Z","message":{"model":"claude-haiku-4-5","usage":{"input_tokens":100,"output_tokens":50}}}
{"type":"assistant","timestamp":"2020-01-01T00:00:00Z","message":{"model":"claude-opus-4-8","usage":{"input_tokens":99999,"output_tokens":99999}}}
EOF
export AML_CLAUDE_PROJECTS_DIR="$TMP/projects"

# A1. A span with one model (only the haiku record falls inside)
OUT="$(python3 "$OBSERVE" task-done --since 2026-07-01T01:00:00Z --label "1.2 one")"
echo "$OUT" | grep -q '^Usage: claude-haiku-4-5'     || fail "A1 model: $OUT"
echo "$OUT" | grep -q 'tokens in 100 / out 50'       || fail "A1 tokens: $OUT"
echo "$OUT" | grep -q 'est\. cost \$'               || fail "A1 cost: $OUT"

# A2. A span with several models (2 opus + 1 haiku; the 2020 record is outside the span)
OUT="$(python3 "$OBSERVE" task-done --since 2026-07-01T00:00:00Z --label "1.1 several")"
echo "$OUT" | grep -q '^Usage: '                      || fail "A2 prefix: $OUT"
echo "$OUT" | grep -q 'claude-opus-4-8'               || fail "A2 opus: $OUT"
echo "$OUT" | grep -q 'claude-haiku-4-5'              || fail "A2 haiku: $OUT"
echo "$OUT" | grep -q 'in 1.5k'                       || fail "A2 opus input total: $OUT"
echo "$OUT" | grep -q 'est\. cost \$0.03'            || fail "A2 total cost: $OUT"

# A3. fail-open — even with no log folder at all, exit code 0 + "no record"
if ! OUT="$(AML_CLAUDE_PROJECTS_DIR="$TMP/none" python3 "$OBSERVE" task-done --since 2026-07-01T00:00:00Z --label x)"; then
  fail "A3 must exit with code 0"
fi
echo "$OUT" | grep -q 'no record'                     || fail "A3 message: $OUT"

echo "OK: part A passed"

# ── Part B: turning on Langfuse ──────────────────────────────────────────────
# B1. No settings file → off → only the usage line (no batch output even with --dry-run)
OUT="$(python3 "$OBSERVE" task-done --since 2026-07-01T01:00:00Z --label "1.2 one" --dry-run)"
[ "$(printf '%s\n' "$OUT" | wc -l)" -eq 1 ] || fail "B1 when off, only 1 line should come out: $OUT"

# B2. Setting on + --dry-run → the second line is the batch JSON; check its structure
mkdir -p .aml
printf 'langfuse: "on"\nlangfuse_host: ""\n' > .aml/config.yaml
OUT="$(python3 "$OBSERVE" task-done --since 2026-07-01T01:00:00Z --label "1.2 one" \
       --feature "test feature" --note "3 tests passed" --dry-run)"
printf '%s\n' "$OUT" | sed -n '2p' | python3 -c '
import json, sys
b = json.load(sys.stdin)["batch"]
types = sorted(e["type"] for e in b)
assert types == ["event-create", "generation-create", "trace-create"], types
tr = next(e for e in b if e["type"] == "trace-create")
assert tr["body"]["sessionId"] == "test feature", tr["body"]
assert tr["body"]["id"].startswith("aml-"), tr["body"]["id"]
gen = next(e for e in b if e["type"] == "generation-create")
assert gen["body"]["model"] == "claude-haiku-4-5", gen["body"]["model"]
assert gen["body"]["usageDetails"]["input"] == 100, gen["body"]["usageDetails"]
ev = next(e for e in b if e["type"] == "event-create")
assert ev["body"]["metadata"]["note"] == "3 tests passed", ev["body"]
' || fail "B2 batch structure"

# B3. ids are deterministic — running the same since/label twice must give the same set of ids
ids() { printf '%s\n' "$1" | sed -n '2p' | python3 -c 'import json,sys; print(sorted(e["id"] for e in json.load(sys.stdin)["batch"]))'; }
OUT2="$(python3 "$OBSERVE" task-done --since 2026-07-01T01:00:00Z --label "1.2 one" \
        --feature "test feature" --note "3 tests passed" --dry-run)"
[ "$(ids "$OUT")" = "$(ids "$OUT2")" ] || fail "B3 ids must be deterministic"

# B3b. The label stays in the trace id (labels stay distinguishable)
printf '%s\n' "$OUT" | sed -n '2p' | python3 -c '
import json, sys
tr = next(e for e in json.load(sys.stdin)["batch"] if e["type"] == "trace-create")
assert "1-2-one" in tr["body"]["id"], tr["body"]["id"]
' || fail "B3b label slug"

# B3c. Non-ASCII feature names/notes round-trip as is (unicode doesn't break)
OUT="$(python3 "$OBSERVE" task-done --since 2026-07-01T01:00:00Z --label x \
       --feature "café-日本語-🎯" --note "non-ASCII note — é" --dry-run)"
printf '%s\n' "$OUT" | sed -n '2p' | python3 -c '
import json, sys
tr = next(e for e in json.load(sys.stdin)["batch"] if e["type"] == "trace-create")
assert tr["body"]["sessionId"] == "café-日本語-🎯", tr["body"]["sessionId"]
' || fail "B3c non-ASCII round trip"

# B4. on + no keys + not dry-run → skipped-send warning (stderr), exit code 0, usage line on stdout
ERR="$TMP/err"
if ! OUT="$(env -u LANGFUSE_PUBLIC_KEY -u LANGFUSE_SECRET_KEY \
      python3 "$OBSERVE" task-done --since 2026-07-01T01:00:00Z --label x 2>"$ERR")"; then
  fail "B4 must exit with code 0"
fi
echo "$OUT" | grep -q '^Usage: '         || fail "B4 stdout: $OUT"
grep -q 'sending is skipped' "$ERR"      || fail "B4 stderr: $(cat "$ERR")"

# B5. ping — warning when there are no keys, exit code 0
if ! OUT="$(env -u LANGFUSE_PUBLIC_KEY -u LANGFUSE_SECRET_KEY python3 "$OBSERVE" ping)"; then
  fail "B5 must exit with code 0"
fi
echo "$OUT" | grep -q '^Warning:'        || fail "B5: $OUT"

# ── Part C: command md wiring + paths in the installed copy ────────────────
AMLDIR="$HERE/../aml"
grep -q 'scripts/observe.py" task-done --since' "$AMLDIR/commands/go.md" || fail "C1 go.md wiring"
grep -q 'scripts/observe.py" ping' "$AMLDIR/commands/doctor.md"          || fail "C1 doctor.md wiring"
grep -q 'Usage:' "$AMLDIR/templates/progress.template.md"                 || fail "C1 template usage line"

# C3. Setup checks (CLAUDE.md + git) wiring
[ -f "$AMLDIR/templates/claude.template.md" ]                            || fail "C3 CLAUDE template"
grep -q 'claude.template.md' "$AMLDIR/commands/new.md"                   || fail "C3 new.md template wiring"
grep -q 'git init' "$AMLDIR/commands/new.md"                             || fail "C3 new.md git setup"
grep -q 'CLAUDE.md' "$AMLDIR/commands/doctor.md"                         || fail "C3 doctor.md check"

# C4. v0.6.0 artifact chain — all 7 templates and 7 commands exist and point to each other
for t in intent spec task progress claude review skill; do
  [ -f "$AMLDIR/templates/$t.template.md" ]                              || fail "C4 template missing: $t"
done
for c in new go review next rule status doctor; do
  [ -f "$AMLDIR/commands/$c.md" ]                                        || fail "C4 command missing: $c"
done
grep -q 'intent.template.md' "$AMLDIR/commands/new.md"                   || fail "C4 new.md → intent template"
grep -q 'REVIEW.md' "$AMLDIR/commands/new.md"                            || fail "C4 new.md → REVIEW.md"
grep -q '.claude/skills' "$AMLDIR/commands/new.md"                       || fail "C4 new.md → rule cards"
grep -q 'Concerns' "$AMLDIR/templates/spec.template.md"               || fail "C4 spec template Concerns"
grep -q 'Files:' "$AMLDIR/templates/task.template.md"               || fail "C4 task template plan lines"
grep -q 'How to check' "$AMLDIR/templates/claude.template.md"             || fail "C4 claude template How to check"

# C5. Build loop — fixing marker · independent check · review · on to the next round
grep -q '.aml/FIXING' "$AMLDIR/commands/go.md"                           || fail "C5 go.md FIXING"
grep -q 'aml:verifier' "$AMLDIR/commands/go.md"                          || fail "C5 go.md verifier"
grep -q '/aml:review' "$AMLDIR/commands/go.md"                           || fail "C5 go.md → review"
grep -q '/aml:next' "$AMLDIR/commands/go.md"                             || fail "C5 go.md → next"
grep -q 'review.template.md' "$AMLDIR/commands/review.md"                || fail "C5 review.md → template"
grep -q '/aml:rule' "$AMLDIR/commands/review.md"                         || fail "C5 review.md → rule"
grep -q 'skill.template.md' "$AMLDIR/commands/rule.md"                   || fail "C5 rule.md → rule card template"
grep -q 'intent.md' "$AMLDIR/commands/next.md"                           || fail "C5 next.md → intent"
grep -q 'observe.py" summary' "$AMLDIR/commands/status.md"               || fail "C5 status.md → summary"
grep -q 'FIXING' "$AMLDIR/commands/doctor.md"                            || fail "C5 doctor.md FIXING check"
grep -q 'safety net' "$AMLDIR/commands/doctor.md"                            || fail "C5 doctor.md safety net check"

# C6. Helper · safety net · reference docs
[ -f "$AMLDIR/agents/verifier.md" ]                                      || fail "C6 verifier missing"
grep -q '^tools: Read, Bash, Grep, Glob$' "$AMLDIR/agents/verifier.md"   || fail "C6 verifier must be read-only"
[ -x "$AMLDIR/hooks/aml-guard.sh" ]                                      || fail "C6 safety net is not executable"
for r in artifact-chain autonomy-and-guardrails next-steps; do
  [ -f "$AMLDIR/references/$r.md" ]                                      || fail "C6 reference doc missing: $r"
done
grep -q 'autonomy-and-guardrails.md' "$AMLDIR/commands/rule.md"          || fail "C6 rule.md → safety net doc"
grep -q 'next-steps.md' "$AMLDIR/commands/next.md"                       || fail "C6 next.md → next steps doc"

# The installed copy also runs from the same relative path (<plugin root>/scripts/observe.py)
AUTOMIX_LIGHT_MARKETPLACE_DIR="$TMP/stage" bash "$HERE/../install.sh" >/dev/null
OUT="$(env -u LANGFUSE_PUBLIC_KEY -u LANGFUSE_SECRET_KEY python3 "$TMP/stage/aml/scripts/observe.py" task-done --since 2026-07-01T01:00:00Z --label staged 2>/dev/null)"
echo "$OUT" | grep -q '^Usage: '                                         || fail "C2 copy: $OUT"
[ -f "$TMP/stage/aml/templates/claude.template.md" ]                     || fail "C2 copy template"
[ -x "$TMP/stage/aml/hooks/aml-guard.sh" ]                               || fail "C2 copy safety net"
[ -f "$TMP/stage/aml/agents/verifier.md" ]                               || fail "C2 copy verifier"
[ -f "$TMP/stage/aml/references/next-steps.md" ]                         || fail "C2 copy reference doc"

echo "OK: part C passed"

# ── Part D: progress log summary (observe.py summary) ────────────────────────
cat > "$TMP/progress.md" <<'PROG'
# Progress log

## 2026-09-06 — second
- Usage: claude-opus-4-8 · 4m 32s · tokens in 12.3k / out 4.1k (cache read 88k / write 2.1k) · est. cost $0.42
- Review: major 0 · minor 2

## 2026-09-05 — first
- Usage: 1h 3m · claude-opus-4-8(in 5.0k/out 1.2k) + claude-haiku-4-5(in 900/out 300) · est. cost $1.10
- Usage: no record (couldn't find the session logs)
- <observe.py output as is — the one `Usage: …` line: model · time taken · tokens · est. cost>
PROG
OUT="$(python3 "$OBSERVE" summary "$TMP/progress.md")" || fail "D1 exit code"
echo "$OUT" | grep -q '3 tasks'                                          || fail "D1 task count: $OUT"
echo "$OUT" | grep -q 'total 1h 7m'                                      || fail "D1 time taken: $OUT"
echo "$OUT" | grep -q 'est\. cost total \$1.52'                          || fail "D1 cost total: $OUT"
echo "$OUT" | grep -q 'claude-opus-4-8 ×2'                               || fail "D1 model count: $OUT"
echo "$OUT" | grep -q 'Tasks without usage: 1'                           || fail "D1 tasks without usage: $OUT"

# D2. A file with no usage lines / a file that doesn't exist — both exit code 0
printf '# Progress log\n\nNothing here yet.\n' > "$TMP/empty.md"
OUT="$(python3 "$OBSERVE" summary "$TMP/empty.md")" || fail "D2 exit code"
echo "$OUT" | grep -q 'no usage lines yet'                               || fail "D2: $OUT"
OUT="$(python3 "$OBSERVE" summary "$TMP/no-such-file.md")" || fail "D3 exit code (0 even for a missing file)"
echo "$OUT" | grep -q "couldn't read"                                    || fail "D3: $OUT"
echo "OK: part D passed"

echo "OK: e2e-smoke-observe passed"
