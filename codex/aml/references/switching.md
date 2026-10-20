# Switch prep — Claude Code ↔ Codex

aml's plan and record files (`intent.md`·`spec.md`·`task.md`·`progress.md`·`REVIEW.md`) have the same shape in both tools, so moving a project to the other tool **doesn't need a new plan.** Only two things differ between the tools.

| | Claude Code | Codex |
|---|---|---|
| Project guide file (read automatically every session) | `CLAUDE.md` | `AGENTS.md` |
| Rule card location | `.claude/skills/` | `.agents/skills/` |

So you only create that one file, **and only if** the tool you're moving to doesn't have its guide file.

## Steps

1. **Check the current state.** Look at whether `spec.md`·`task.md`·`progress.md` exist, whether "How to check" in the original tool's guide file (`CLAUDE.md` or `AGENTS.md`) has the run and test commands, and how many rule cards the original tool has.
2. **Ask for only the guide file the new tool is missing.** In the tool you're moving to, say this.
   - Moving to Codex: "Leave spec.md·task.md·progress.md as they are, and create only AGENTS.md in aml's AGENTS template shape, carrying over what's in CLAUDE.md (especially How to check). Don't change any other file."
   - Moving to Claude Code: "Leave spec.md·task.md·progress.md as they are, and create only CLAUDE.md in aml's CLAUDE template shape, carrying over what's in AGENTS.md (especially How to check). Don't change any other file."
3. **Check.** `$aml:doctor` in Codex, `/aml:doctor` in Claude Code. If it says the guide file exists and there are tasks left, you're ready.
4. **Carry on.** `$aml:go` in Codex, `/aml:go` in Claude Code. Checked tasks and past records stay as they are, and work continues from the first unchecked task.

## What not to do

- **Don't plan anew.** After moving, don't start over with `$aml:new` (`/aml:new`) or rewrite `spec.md`·`task.md`. The check marks and records would be lost.
- **Don't overwrite an existing guide file.** If the tool you're moving to already has its guide file, leave it. If the two guide files differ (especially the run and test commands), don't fix them; tell the user what differs and ask which is right.
- **Keep using `REVIEW.md` as is.** Both tools read the same file. Don't create a new one or overwrite it.
- **Don't move rule cards automatically.** The new tool doesn't read the original tool's rule cards. The user checks which rules should still be kept, and only those are written anew with the new tool's rule step (`$aml:rule` / `/aml:rule`).
- **Don't use both tools at the same time.** Finish a task in one tool (including the commit) before moving to the other. If both tools change `task.md` at the same time, one side's changes can be overwritten.

## Differences to know

- **Safety net**: the Claude Code edition has an AML hook that blocks hard-to-undo things (committing secret keys, changing test files while fixing, force push · hard reset). This version has no AML-specific blocking hook. Codex's permission, sandbox, and approval settings apply depending on your environment, and don't guarantee the same blocking as the Claude edition's AML hook.
- **Independent check**: the Claude Code edition calls a separate checking helper (verifier) at the end. The Codex edition self-checks by default, and writes "independent check" only when it actually handed the check to someone else.
- **Usage lines**: even when both tools' usage lines are mixed in `progress.md`, the progress summary (`$aml:status` / `/aml:status`) adds them up together. If Codex can't read usage reliably, `Usage: no record` is left.
