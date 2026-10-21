# automix-light — Claude Code edition

This is aml for Claude Code. With 7 commands (`/aml:new` · `/aml:go` · `/aml:review` · `/aml:next` · `/aml:rule` · `/aml:status` · `/aml:doctor`) you can go from planning through building, checking, and recording, to improving after use. Each command is explained in [`aml/README.md`](aml/README.md).

## Install

On **Ubuntu or macOS**, run these commands in a terminal:

```bash
git clone https://github.com/hyun-yang/automix-light-en.git
cd automix-light-en
bash claude-code/install.sh   # copies to ~/.claude-marketplaces/automix-light-en
```

Then type these in Claude Code.

```text
/plugin marketplace add ~/.claude-marketplaces/automix-light-en
/plugin install aml@automix-light-en
```

On **Windows 11**, install [Git for Windows](https://git-scm.com/download/win) and [Python 3](https://www.python.org/downloads/windows/) first. Open Windows Terminal (PowerShell), then run:

```powershell
git clone https://github.com/hyun-yang/automix-light-en.git
cd automix-light-en
powershell -ExecutionPolicy Bypass -File claude-code\install.ps1
```

Copy the `/plugin marketplace add C:/Users/.../.claude-marketplaces/automix-light-en` command printed by the installer into Claude Code, then run `/plugin install aml@automix-light-en`. The execution-policy option applies only to this invocation. See the [Windows 11 guide](../README.md#install-on-windows-11) for prerequisite and troubleshooting details.

When the 7 `/aml:` commands show up in `/help`, the install is done.

Install either this English edition or the Korean edition ([automix-light](https://github.com/hyun-yang/automix-light)), not both — they use the same command names (`/aml:go` etc.).

## Tests

```bash
bash claude-code/tests/e2e-smoke-guard.sh     # blocking risky actions: 6 groups of cases
bash claude-code/tests/e2e-smoke-observe.sh   # usage records and install result
```

These tests are for repository contributors. On Windows, use Git Bash to run them; it is not needed for the normal install. Some tests assume Linux paths, so see the [test notes](../README.md#tests).

## Moving a project from Codex to Claude Code

`intent.md`·`spec.md`·`task.md`·`progress.md`·`REVIEW.md` have the same format in both tools, so you can use them as they are. Only the project guide file (`AGENTS.md` for Codex, `CLAUDE.md` for Claude Code) and the rule card location (`.agents/skills/` ↔ `.claude/skills/`) differ.

1. Check that the project folder has `spec.md`·`task.md`·`progress.md`, and that "How to check" in `AGENTS.md` has the run and test commands.
2. **Only if there is no** `CLAUDE.md`, ask Claude Code: "Leave spec.md·task.md·progress.md as they are, and create only CLAUDE.md in aml's CLAUDE template format, carrying over what's in AGENTS.md (especially How to check). Don't change any other file."
3. Check with `/aml:doctor`.
4. Carry on with `/aml:go`. Leave the done marks on tasks and the existing records as they are.

Things to watch when switching:

- Don't start over with `/aml:new`. The done marks on tasks and the records would be lost.
- If `CLAUDE.md` already exists, don't overwrite it. If its run and test commands differ from `AGENTS.md`, check which is right and fix it yourself.
- `REVIEW.md` is shared by both tools, so don't create a new one.
- Claude Code doesn't read rule cards in `.agents/skills/`. Rewrite only the rules you want to keep applying with `/aml:rule`.
- Don't use both tools at the same time. Commit before switching.

The Claude Code edition has an AML hook (`aml/hooks/aml-guard.sh`) that blocks actions that are hard to undo. The Codex edition doesn't have this hook. For the other direction (Claude Code → Codex), see the [Codex edition guide](../codex/README.md#moving-a-project-from-claude-code-to-codex).
