# automix-light — Codex edition

This is aml for Codex. With 7 skills you work in the same order as the Claude Code edition (plan → build → check → record → improve after use). All conversation and documents are written in English.

## Install

You need the [Codex CLI](https://developers.openai.com/codex) and Git. To record usage you also need `python3`, but the work carries on without it.

```bash
git clone https://github.com/hyun-yang/automix-light-en.git
cd automix-light-en
codex plugin marketplace add "$PWD/codex"
codex plugin add aml@automix-light-en
codex plugin list            # check that aml@automix-light-en shows installed, enabled
```

When you open Codex fresh and type `$aml`, the install is done if 7 skills show up with the plugin name in front, like `aml:new`. You can call a skill by typing it like `$aml:go`, or by asking in words, like "carry on with the remaining tasks". Codex has its own built-in commands such as `/new`·`/status`·`/review`, so use `$` when running aml skills, like `$aml:status`. The marketplace points to the folder you downloaded, so don't delete or move that folder.

### If the Korean edition is installed

The Korean edition (`aml@automix-light`) uses the same skill names (`aml:go` etc.), so it's hard to tell which one runs. Install only one of them. To remove the Korean edition first:

```bash
codex plugin list                              # check for aml@automix-light
codex plugin remove aml@automix-light          # remove the Korean edition
codex plugin marketplace remove automix-light  # remove its marketplace entry too, then follow the install steps above
```

These commands change `~/.codex/config.toml`, so check your existing settings before running them.

## Skills

| Skill | What it does | Claude Code edition |
|---|---|---|
| `$aml:new` | Writes `intent.md`·`spec.md`·`task.md`·`progress.md` through questions and answers (doesn't build) | `/aml:new` |
| `$aml:go` | Builds and checks the tasks in `task.md` in order, records the results, and commits per task | `/aml:go` |
| `$aml:review` | Checks bugs, security problems, and whether requirements are met before committing (doesn't change code) | `/aml:review` |
| `$aml:next` | Turns problems and wanted features found while using it into next tasks or a new plan | `/aml:next` |
| `$aml:rule` | When the same mistake happens twice, writes a prevention rule into `AGENTS.md` or a rule card (`.agents/skills/`) | `/aml:rule` |
| `$aml:status` | Summarizes progress and time · tokens · cost | `/aml:status` |
| `$aml:doctor` | Checks readiness before starting work (doesn't change files) | `/aml:doctor` |

The project guide file is `AGENTS.md`. Codex reads it automatically every session.

## How it differs from the Claude Code edition (please read)

- **Blocking risky actions** — This version has no AML-specific blocking hook. Codex's permission, sandbox, and approval settings apply depending on your environment, and don't guarantee the same blocking as the Claude edition's AML hook. For committing a `.env` file with secret keys, changing test files while fixing a bug, and force push · hard reset, the skills only give a warning, so check these yourself before they run.
- **Independent check** — the default is a **self-check** done within the same session. "Independent check" is written in `progress.md` only when the check was actually handed to a separate agent.
- **Usage measuring** — it reads the tokens used for the current task from Codex's session logs (`~/.codex/sessions/`) and records usage. If it can't find the current session for sure, or there's no record from when the task started, it shows `Usage: no record`. It never fills in values from another session instead. Cost is calculated only for models whose prices are confirmed; the rest show "cost unknown". For the detailed rules, see the [usage measuring rules](aml/references/telemetry.md).
- **Sending to Langfuse** — not supported in the first Codex edition.

## Moving a project from Claude Code to Codex

Keep using the existing plan and record files, and prepare the Codex project guide file.

1. Check that the project folder has `spec.md`·`task.md`·`progress.md`, and that "How to check" in `CLAUDE.md` has the run and test commands.
2. **Only if there is no** `AGENTS.md`, ask Codex: "Leave spec.md·task.md·progress.md as they are, and create only AGENTS.md in aml's AGENTS template format, carrying over what's in CLAUDE.md (especially How to check). Don't change any other file."
3. Check with `$aml:doctor`.
4. Carry on with `$aml:go`.

If `AGENTS.md` already exists, leave it; if it differs from `CLAUDE.md`, check which is right and fix it yourself. `REVIEW.md` is shared by both tools. Codex doesn't read rule cards in `.claude/skills/`, so rewrite only the rules you want to keep applying with `$aml:rule`. Use one tool at a time, and commit before switching. For details, see the [switch guide](aml/references/switching.md).

For the other direction (Codex → Claude Code), see the [Claude Code edition guide](../claude-code/README.md#moving-a-project-from-codex-to-claude-code).

## Tests (when changing the repository)

```bash
bash codex/tests/test-templates.sh   # whether the 5 common templates match across editions
python3 codex/tests/test_observe.py  # measuring and summary numbers
bash codex/tests/test-package.sh     # package structure (with the codex command, also an isolated install and the skill list)
```
