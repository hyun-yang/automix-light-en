---
description: Pre-start check — checks the files and done criteria, the safety net, git/Python, and Langfuse settings. Read-only.
allowed-tools: Read, Bash, Glob, Grep
---

# /aml:doctor — pre-start check

Check the following in order from the project root and report in plain English. **Don't change anything.**

## Blocking items — if one fails, show ❌ and how to fix it

1. Do spec.md / task.md / progress.md all exist? → if not: "Start with /aml:new"
2. Does the "Done criteria" in spec.md have at least one checkbox (`- [ ]` or `- [x]`)?
3. Does task.md have at least one task checkbox?

## Info-only items — don't block, show ⚠️

4. Does **CLAUDE.md** exist? — if not: "Claude has to work out what this project is from scratch every time. Running /aml:new will create it for you". If it does, check its length too — over 120 lines: "It's gone past one page. Try tidying up lines that no longer fit with /aml:rule".
5. Does **intent.md** exist? — if not: "There's no record of why you decided to build this. It gets created the next time you run /aml:new or /aml:next" (not a problem right now).
6. Does **REVIEW.md** exist? — if not: "There's no review checklist. The first time you run /aml:review it gets created for you".
7. Is **`.aml/FIXING`** left over? — if so ⚠️: "A marker saying a bug is being fixed is still there. While it's there, test files can't be changed. If the fix is finished, remove it with `rm .aml/FIXING`."
8. **Safety net (hook)** status — report one of three.
   - No working Python → ⚠️ "The safety net isn't working (no working Python). It can't block secret keys or irreversible commands."
   - `guard: "off"` in `.aml/config.yaml` → ⚠️ "You've turned the safety net off."
   - Otherwise → ✅ "Safety net on — blocks secret keys · test files while fixing · irreversible commands."
9. Is it a **git** repository (`git rev-parse --is-inside-work-tree`)? — if not: "/aml:new sets up git and sets the default branch to main — with it, mistakes are easy to undo"
10. Is **Python** working? Try `python3 -c "import sys"`, then `python -c "import sys"`, then `py -3 -c "import sys"`. The first successful command is the one to use for measuring and the safety net (including `-3` for `py -3`). Checking PATH alone can mistake the Windows Store shortcut for Python. If none works: "No usage line (model · time · tokens · cost) will be left in progress.md"
11. **Rule cards** — count `.claude/skills/*/SKILL.md` and report it (zero is fine). If there are any, list just the names on one line.
12. **Checked after changing settings?** — if the most recent change to CLAUDE.md · REVIEW.md · rule cards is later than the last entry in progress.md, ⚠️: "The settings that guide Claude changed and there hasn't been a full check since. Go over the done criteria once more with `/aml:go` or `/aml:review`." (When settings change, results can change too.)
13. **Langfuse** status — report one of three. **Langfuse never blocks anything.**
    - No `.aml/config.yaml`, or `langfuse:` isn't "on" → "Langfuse sending: off (default)". How to turn it on is under "Langfuse integration (optional)" in the README.
    - "on" but the LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY environment variables are missing → ⚠️ "It's on, but sending is skipped because there are no keys" + how to set the keys (never print key values — only present/missing).
    - "on" and the keys are there → check the connection with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/observe.py" ping`, replacing `python3` with the working Python command from step 10, and pass on the OK/Warning result as is.

## Report format

One line per item with ✅/❌/⚠️. At the end, one line on what to do next — /aml:new if files are missing, /aml:go if tasks are left, /aml:next if everything is done, and "You can start right away" if there are no problems.
