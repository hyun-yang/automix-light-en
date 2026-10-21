# aml — Copilot CLI edition package

A plugin that helps beginners go from planning through building, checking, and recording, in English. For Windows 11 and other installation steps, see the repository's `copilot/README.md`.

## Skills

| Skill | What it does |
|---|---|
| `/aml:new` | Writes `intent.md`·`spec.md`·`task.md`·`progress.md` through questions and answers (doesn't build) |
| `/aml:go` | Builds and checks the tasks in `task.md` in order and records the results in `progress.md` |
| `/aml:review` | Checks bugs, security problems, and whether requirements are met before committing (doesn't change code) |
| `/aml:next` | Turns problems and wanted features found while using it into next tasks or a new plan |
| `/aml:rule` | When the same mistake happens twice, writes a prevention rule into `AGENTS.md` or a rule card (`.agents/skills/`) |
| `/aml:status` | Summarizes progress and time · tokens · AI credits |
| `/aml:doctor` | Checks readiness before starting work (doesn't change files) |

Copilot has built-in commands like `/new`·`/review`, so always type `aml:` in front when running aml skills.

## Folders

- `plugin.json` — plugin settings (where the skills, agents, and hooks are)
- `skills/` — the 7 skills
- `agents/verifier.agent.md` — the agent in charge of independent checks (called when `/aml:go` finishes)
- `hooks.json` · `hooks/aml-guard.sh` — the safety-net hook (blocks three kinds of hard-to-undo actions)
- `templates/` — 5 common templates (spec · task · progress · intent · review, same content as the other editions) and the Copilot-only `agents.template.md` · `skill.template.md`
- `references/` — [switch prep](references/switching.md) · [checking the done criteria](references/verification.md) · [measuring rules](references/telemetry.md) · [what each document is for](references/artifact-chain.md)
- `scripts/observe.py` — usage recording and summary (Python standard library only)

## Blocking risky actions

The aml safety-net hook blocks committing `.env`, changing test files while fixing a bug (`.aml/FIXING`), and force push · hard reset · mass file deletion. It only works in aml projects that have `spec.md` and `task.md`, and if something goes wrong inside the hook, it doesn't block the action. If the hook runs past its time limit, Copilot doesn't block the action either, so have the user check hard-to-undo actions once more too.
