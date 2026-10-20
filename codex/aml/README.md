# aml — Codex edition package

A plugin that helps beginners go from planning through building, checking, and recording, in English. How to install it and how it differs from the Claude Code edition are in the repository's `codex/README.md`.

## Skills

| Skill | What it does |
|---|---|
| `$aml:new` | Writes `intent.md`·`spec.md`·`task.md`·`progress.md` through questions and answers (doesn't build) |
| `$aml:go` | Builds and checks the tasks in `task.md` in order and records the results in `progress.md` |
| `$aml:review` | Checks bugs, security problems, and whether requirements are met before committing (doesn't change code) |
| `$aml:next` | Turns problems and wanted features found while using it into next tasks or a new plan |
| `$aml:rule` | When the same mistake happens twice, writes a prevention rule into `AGENTS.md` or a rule card (`.agents/skills/`) |
| `$aml:status` | Summarizes progress and time · tokens · cost |
| `$aml:doctor` | Checks readiness before starting work (doesn't change files) |

## Folders

- `skills/` — the 7 skills
- `templates/` — 5 common templates (spec · task · progress · intent · review, same content as the Claude Code edition) and the Codex-only `agents.template.md` · `skill.template.md`
- `references/` — [switch prep](references/switching.md) · [checking the done criteria](references/verification.md) · [measuring rules](references/telemetry.md) · [what each document is for](references/artifact-chain.md)
- `scripts/observe.py` — usage recording and summary (Python standard library only)

## Blocking risky actions

This version has no AML-specific blocking hook. Codex's permission, sandbox, and approval settings apply depending on your environment, and don't guarantee the same blocking as the Claude edition's AML hook.
