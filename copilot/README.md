# automix-light — Copilot CLI edition

This is aml for GitHub Copilot CLI (`copilot`, run in the terminal). With 7 skills you work in the same order as the Claude Code edition (plan → build → check → record → improve after use). All conversation and documents are written in English.

> Install · skill list · safety-net hook · usage records were checked on Copilot CLI **1.0.98** (2026-10-19). Copilot Chat in VS Code isn't supported — it may read the same plugin, but that hasn't been checked.

## Install

You need [GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli) (a Copilot subscription is required) and Git. To record usage and use the safety-net hook you also need a working Python 3 command (`python3`, `python`, or `py -3`). Without one the work still carries on, but usage shows as `no record` and the hook's blocking doesn't work.

```bash
git clone https://github.com/hyun-yang/automix-light-en.git
cd automix-light-en
copilot plugin marketplace add "$PWD/copilot"
copilot plugin install aml@automix-light-en
copilot plugin list            # check it shows aml@automix-light-en (v0.6.0) (enabled)
```

On **Windows 11**, run the commands in Windows Terminal (PowerShell), using `"$PWD\copilot"` instead of `"$PWD/copilot"`. PowerShell expands `$PWD` to a path such as `C:\Users\...\automix-light-en`. The safety-net hook skips a `python3` Microsoft Store shortcut and looks for a working `python` or `py -3`. See the [Windows 11 guide](../README.md#install-on-windows-11) for prerequisites.

The Windows safety-net hook runs Python 3 from Windows PowerShell 5.1 or PowerShell 7. **It does not require Bash to be installed or added to PATH.** Linux/macOS keep the Bash entry point; both entry points use the same Python decisions. Under the existing policy, a missing Python installation or unreadable input allows the tool call, so blocking is not active in those cases.

If `hook errored` is accompanied by `spawn bash ENOENT` in the log, an older Bash-only configuration may still be loaded. Check `copilot plugin list`: if the Live Plugin points to this updated `copilot/` folder, fully quit and restart Copilot. If the plugin is a copied install or points elsewhere, check the marketplace path and reinstall:

```powershell
copilot plugin uninstall aml@automix-light-en
copilot plugin install aml@automix-light-en
```

In the new session, check the AML hook in `/env` and run `/aml:doctor`. A hook appearing in `/env` does not by itself prove it runs successfully. Source edits do not immediately update an existing session or a copied install. If PowerShell blocks npm's `copilot.ps1`, use `copilot.cmd` instead of `copilot`; no computer-wide execution-policy change is required.

For Windows contributor checks, run `python copilot/tests/test_guard_windows.py`. The test passes risky command strings to the hook without executing them. If PowerShell 7 is not installed, that check is skipped and must not be reported as verified.

**Register the `copilot/` folder.** Copilot also reads Claude Code's marketplace file, so if you register the `claude-code/` folder by mistake, the Claude Code edition gets installed instead of the Copilot CLI edition. The marketplace reads the downloaded folder directly, so don't delete or move that folder.

When you open Copilot fresh and type `/aml`, the install is done if 7 skills show up with the plugin name in front, like `/aml:go`. You can call a skill by typing it like `/aml:go`, or by asking in words, like "carry on with the remaining tasks". Copilot has its own built-in commands such as `/new` (new conversation) and `/review` (code review), so always call aml skills with `aml:`, like `/aml:new`.

To check the install in more detail, type `/env` in the Copilot conversation. If **Custom Agents** shows `verifier` and **Hooks** shows `preToolUse: 1 hook (sources: aml)`, the checking agent and the safety-net hook are on.

### If the Korean edition is installed

The Korean edition (`aml@automix-light`) uses the same skill names (`/aml:go` etc.), so it's hard to tell which one runs. Install only one of them. To remove the Korean edition first, run `copilot plugin uninstall aml@automix-light`, then follow the install steps above. This changes your settings under `~/.copilot/`, so check them before running it.

## Skills

| Skill | What it does | Claude Code edition | Codex edition |
|---|---|---|---|
| `/aml:new` | Writes `intent.md`·`spec.md`·`task.md`·`progress.md` through questions and answers (doesn't build) | `/aml:new` | `$aml:new` |
| `/aml:go` | Builds and checks the tasks in `task.md` in order, records the results, and commits per task | `/aml:go` | `$aml:go` |
| `/aml:review` | Checks bugs, security problems, and whether requirements are met before committing (doesn't change code) | `/aml:review` | `$aml:review` |
| `/aml:next` | Turns problems and wanted features found while using it into next tasks or a new plan | `/aml:next` | `$aml:next` |
| `/aml:rule` | When the same mistake happens twice, writes a prevention rule into `AGENTS.md` or a rule card (`.agents/skills/`) | `/aml:rule` | `$aml:rule` |
| `/aml:status` | Summarizes progress and time · tokens · AI credits | `/aml:status` | `$aml:status` |
| `/aml:doctor` | Checks readiness before starting work (doesn't change files) | `/aml:doctor` | `$aml:doctor` |

The project guide file is `AGENTS.md` (the same file as the Codex edition). Copilot reads `AGENTS.md` and `CLAUDE.md` together every session.

## Good to know

- **Blocking risky actions** — like the Claude Code edition, the aml safety-net hook blocks committing `.env`, changing test files while fixing a bug, and force push · hard reset · mass file deletion, and shows why it blocked and what to do on screen. But if the hook runs past its time limit (10 seconds), Copilot doesn't block the action. Have the user check hard-to-undo actions once more too. To turn blocking off, set `guard: "off"` in the project's `.aml/config.yaml`.
- **Independent check** — when `/aml:go` finishes, a separate checking agent (`verifier`) checks whether the done criteria are met. "Independent check" is written in `progress.md` only when the check was actually handed over; if it couldn't be, "self-check" is written.
- **Usage measuring** — reads the tokens and AI credits used for the current task from Copilot's session logs (`~/.copilot/session-state/`). These are numbers Copilot recorded itself, so they match the `Tokens`·`AI Credits` shown at the end of the screen. If it can't find the current session for sure, or the session changed partway through the task, it shows `Usage: no record` and never fills in values from another session. Dollar cost is calculated only for models whose prices are confirmed; the rest show "cost unknown". For the detailed rules, see the [usage measuring rules](aml/references/telemetry.md).
- **Sending to Langfuse** — not supported in the first Copilot edition.

## Moving a project from another tool

The plan and record files have the same format in all three tools, so there's no need to plan anew.

| From → to | What to do |
|---|---|
| Codex → Copilot | Nothing. They share `AGENTS.md` and `.agents/skills/`. Go straight to `/aml:go` |
| Claude Code → Copilot | Create only `AGENTS.md` (steps below). Copilot reads the rule cards in `.claude/skills/` too, so don't move them |
| Copilot → Codex | Nothing. Go straight to `$aml:go` |
| Copilot → Claude Code | Create only `CLAUDE.md`. Follow the same steps in the [Claude Code edition guide](../claude-code/README.md#moving-a-project-from-codex-to-claude-code) |

Moving a project from Claude Code to Copilot:

1. Check that the project folder has `spec.md`·`task.md`·`progress.md`, and that "How to check" in `CLAUDE.md` has the run and test commands.
2. **Only if there is no** `AGENTS.md`, ask Copilot: "Leave spec.md·task.md·progress.md as they are, and create only AGENTS.md in aml's AGENTS template format, carrying over what's in CLAUDE.md (especially How to check). Don't change any other file."
3. Check with `/aml:doctor`.
4. Carry on with `/aml:go`.

If `AGENTS.md` already exists, leave it; if it differs from `CLAUDE.md`, check which is right and fix it yourself. Copilot reads both files together, so if they differ it may follow conflicting instructions. `REVIEW.md` is shared by all three tools. Use one tool at a time, and commit before switching. For details, see the [switch guide](aml/references/switching.md).

## Tests (when changing the repository)

```bash
bash copilot/tests/test-templates.sh   # whether the 5 common templates match across the three editions
bash copilot/tests/test-guard.sh       # the safety-net hook's block/allow behavior with Copilot's input format
python3 copilot/tests/test_observe.py  # measuring and summary numbers
bash copilot/tests/test-package.sh     # package structure (with the copilot command, also an isolated install and the skill list)
```

These tests are for repository contributors. On Windows, use Git Bash for the bash tests and `PYTHONUTF8=1 python` for the Python test if `python3` opens the Microsoft Store. Some tests assume Linux paths; see the [test notes](../README.md#tests).
