---
name: doctor
description: Pre-start check — checks the plan files and done criteria, the project guide (AGENTS.md), switch prep, the safety-net notice, and git/python3. Read-only. Use for "check things", "are we ready?", or "$aml:doctor".
---

# $aml:doctor — pre-start check

Check the following in order from the project root and report in plain English. **Don't change anything** — don't create, change, or delete files. If you see something to fix, only say how.

## Blocking items — if one fails, show ❌ and how to fix it

1. Do spec.md / task.md / progress.md all exist? → if not: "Start with $aml:new"
2. Does the "Done criteria" in spec.md have at least one checkbox (`- [ ]` or `- [x]`)?
3. Does task.md have at least one task checkbox?

## Info-only items — don't block, show ⚠️

4. Does **AGENTS.md** exist? — report one of three.
   - If it does, ✅. Over 120 lines: ⚠️ "It's gone past one page. Try tidying up lines that no longer fit with $aml:rule".
   - If it doesn't but **CLAUDE.md does**: ⚠️ "This looks like a project started in Claude Code. There's no Codex guide file (AGENTS.md) yet — create only AGENTS.md following the [switch prep](../../references/switching.md) steps and you can carry on with the existing plan as is. Don't plan anew."
   - If neither exists: ⚠️ "Codex has to work out what this project is from scratch every time. Running $aml:new will create it for you".
5. Does **intent.md** exist? — if not: "There's no record of why you decided to build this. It gets created the next time you run $aml:new or $aml:next" (not a problem right now).
6. Does **REVIEW.md** exist? — if not: "There's no review checklist. The first time you run $aml:review it gets created for you".
7. Is **`.aml/FIXING`** left over? — if so ⚠️: "A marker saying a bug is being fixed is still there. While fixing, the promise is not to change test files (the Codex edition doesn't block this automatically). If the fix is finished, remove it with `rm .aml/FIXING`."
8. **Safety net** — always report this exact sentence with ⚠️:
   "This version has no AML-specific blocking hook. Codex's permission, sandbox, and approval settings apply depending on your environment, and don't guarantee the same blocking as the Claude edition's AML hook."
   If you haven't actually checked Codex's permission and sandbox settings just now, don't say "it's on" or "you're protected". Add that hard-to-undo things like committing secret keys, force pushes, and hard resets need a person to check them.
9. Is it a **git** repository (`git rev-parse --is-inside-work-tree`)? — if not: "$aml:new sets up git and sets the default branch to main — with it, mistakes are easy to undo"
10. Is **python3** available (`command -v python3`)? — if not: "No usage line (model · time · tokens · cost) will be left in progress.md. The work carries on as normal"
11. **Rule cards** — count `.agents/skills/*/SKILL.md` and report it (zero is fine). If there are any, list just the names on one line. If cards exist only in `.claude/skills/`: ⚠️ "Codex doesn't read Claude Code rule cards automatically. If there are rules you want to keep, rewrite them into `.agents/skills/` with $aml:rule."
12. **Checked after changing settings?** — if the most recent change to AGENTS.md · REVIEW.md · rule cards is later than the last entry in progress.md, ⚠️: "The settings that guide Codex changed and there hasn't been a full check since. Go over the done criteria once more with $aml:go or $aml:review."
13. **Usage measuring** — run `python3 "<package>/scripts/observe.py" check` and pass on the one line it prints as is (`<package>` is two levels up from this SKILL.md). Not being able to measure doesn't block anything. Say in one line that sending to Langfuse isn't in the first Codex edition.

## Report format

One line per item with ✅/❌/⚠️. At the end, one line on what to do next — $aml:new if files are missing, switch prep if only AGENTS.md is missing, $aml:go if tasks are left, $aml:next if everything is done, and "You can start right away" if there are no problems.
