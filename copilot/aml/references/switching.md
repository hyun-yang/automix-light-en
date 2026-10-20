# Switch prep — Claude Code · Codex ↔ Copilot CLI

aml's plan and record files (`intent.md`·`spec.md`·`task.md`·`progress.md`·`REVIEW.md`) have the same shape in all three tools, so moving a project to another tool **doesn't need a new plan.** Only two things differ between the tools.

| | Claude Code | Codex | Copilot CLI |
|---|---|---|---|
| Project guide file (read automatically every session) | `CLAUDE.md` | `AGENTS.md` | `AGENTS.md` (also reads `CLAUDE.md`) |
| Where aml makes rule cards | `.claude/skills/` | `.agents/skills/` | `.agents/skills/` (also reads cards in `.claude/skills/`·`.github/skills/`) |
| How to call | `/aml:go` | `$aml:go` | `/aml:go` |

So you only create that one file, **and only if** the tool you're moving to doesn't have its guide file.

## By direction

| From → to | What to do |
|---|---|
| Codex → Copilot | Nothing. They share `AGENTS.md` and `.agents/skills/`. Go straight to `/aml:go` |
| Claude Code → Copilot | Create only `AGENTS.md` (steps below). Copilot reads the rule cards (`.claude/skills/`) too, so don't move them |
| Copilot → Codex | Nothing. Go straight to `$aml:go` |
| Copilot → Claude Code | Create only `CLAUDE.md` (steps below). Claude Code doesn't read rule cards made in Copilot (`.agents/skills/`), so rewrite only the ones to keep with Claude Code's `/aml:rule` |

## Steps (when the guide file is missing)

1. **Check the current state.** Look at whether `spec.md`·`task.md`·`progress.md` exist, and whether "How to check" in the original tool's guide file (`CLAUDE.md` or `AGENTS.md`) has the run and test commands.
2. **Ask for only the guide file the new tool is missing.** In the tool you're moving to, say this.
   - Moving to Copilot: "Leave spec.md·task.md·progress.md as they are, and create only AGENTS.md in aml's AGENTS template shape, carrying over what's in CLAUDE.md (especially How to check). Don't change any other file."
   - Moving to Claude Code: "Leave spec.md·task.md·progress.md as they are, and create only CLAUDE.md in aml's CLAUDE template shape, carrying over what's in AGENTS.md (especially How to check). Don't change any other file."
3. **Check.** `/aml:doctor` in Copilot, and `/aml:doctor` in Claude Code too. If it says the guide file exists and there are tasks left, you're ready.
4. **Carry on.** `/aml:go`. Checked tasks and past records stay as they are, and work continues from the first unchecked task.

## What not to do

- **Don't plan anew.** After moving, don't start over with `/aml:new` or rewrite `spec.md`·`task.md`. The check marks and records would be lost.
- **Don't overwrite an existing guide file.** If the tool you're moving to already has its guide file, leave it. If `CLAUDE.md` and `AGENTS.md` differ (especially the run and test commands), don't fix them; tell the user what differs and ask which is right. Copilot reads both, so if they differ it gets confused.
- **Keep using `REVIEW.md` as is.** All three tools read the same file. Don't create a new one or overwrite it.
- **Don't use several tools at the same time.** Finish a task in one tool (including the commit) before moving to another. If two tools change `task.md` at the same time, one side's changes can be overwritten.

## Differences to know

- **Safety net**: the Claude Code and Copilot editions have an aml hook that blocks hard-to-undo things (committing secret keys, changing test files while fixing, force push · hard reset). If a hook times out, Copilot lets the action through instead of blocking it. The Codex edition has no aml-specific blocking hook.
- **Independent check**: the Claude Code and Copilot editions call a separate checking helper (verifier) at the end. The Copilot edition writes "independent check" only when it actually called it, and "self-check" if it couldn't.
- **Usage lines**: even when all three tools' usage lines are mixed in `progress.md`, the progress summary (`/aml:status`) adds them up together. If Copilot can't read usage reliably, `Usage: no record` is left.
