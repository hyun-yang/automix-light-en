# automix-light (aml) — English edition

> A Claude Code · Codex · Copilot CLI plugin for people building their first app. A light, English version of automix that guides you from planning through building, checking, and improving after use.
>
> The Korean edition lives at [hyun-yang/automix-light](https://github.com/hyun-yang/automix-light).

Based on Anthropic's [AI-Native SDLC playbook](https://claude.com/blog/the-ai-native-sdlc-playbook), **with the development process simplified so someone building an app alone can follow it.** The core idea is to write down the result of each step as a document, and to work from that document in the next step.

You shape the idea, plan the build, build the app, and check it. Problems and wanted features you find while using the finished app go into the next round of work.

| Step | What gets recorded |
|---|---|
| Planning (`intent.md`) | Why the app is being built and the problem it solves |
| Requirements (`spec.md`) | Features needed and the done criteria |
| Task plan (`task.md`) | Order of work, files to change, expected risks, how to check |
| Build and check (code + `progress.md`) | What was built, check results, time taken and cost |
| Code review | Bugs, security problems, whether requirements are met |
| Improving after use | Small fixes go into `task.md`; new features or changes of direction go into `intent.md` |

Command definitions, templates, and work results are all markdown files. The only running code is the usage-recording script (`observe.py`, Python standard library only) and the blocking hook of the Claude Code and Copilot CLI editions (`aml-guard.sh`).

## Which tool do you use?

The same workflow works in all three tools. Follow the install guide for the tool you use.

| Tool | Install and guide | Install commands (from the repo root) |
|---|---|---|
| Claude Code | [`claude-code/README.md`](claude-code/README.md) | `bash claude-code/install.sh` |
| Codex | [`codex/README.md`](codex/README.md) | `codex plugin marketplace add "$PWD/codex"` → `codex plugin add aml@automix-light-en` |
| GitHub Copilot CLI | [`copilot/README.md`](copilot/README.md) | `copilot plugin marketplace add "$PWD/copilot"` → `copilot plugin install aml@automix-light-en` |

```bash
git clone https://github.com/hyun-yang/automix-light-en.git
cd automix-light-en
```

**Install either this English edition or the Korean edition, not both, in the same tool.** They use the same command names (`/aml:go`, `$aml:go`), so it would be hard to tell which one runs.

## Commands

| What it does | Claude Code | Codex | Copilot CLI |
|---|---|---|---|
| Shapes the idea through questions and answers and creates `intent.md`, `spec.md`, `task.md`, `progress.md` | `/aml:new "one-line idea"` | `$aml:new` | `/aml:new` |
| Builds and checks the tasks in `task.md` in order, records the results, and commits per task | `/aml:go` | `$aml:go` | `/aml:go` |
| Checks bugs, security problems, and whether requirements are met before committing (doesn't change code) | `/aml:review` | `$aml:review` | `/aml:review` |
| Turns problems and wanted features found while using the app into next tasks or a new plan | `/aml:next` | `$aml:next` | `/aml:next` |
| Writes development rules that prevent repeated mistakes | `/aml:rule` | `$aml:rule` | `/aml:rule` |
| Shows progress, done-criteria pass rate, and total time and cost | `/aml:status` | `$aml:status` | `/aml:status` |
| Checks you're ready to start work (doesn't change files) | `/aml:doctor` | `$aml:doctor` | `/aml:doctor` |

The plan and record files (`intent.md`·`spec.md`·`task.md`·`progress.md`·`REVIEW.md`) have the same format in all three tools, so you can move a project in progress to another tool and carry on. Only the project guide file (`CLAUDE.md` ↔ `AGENTS.md`) and the rule card location (`.claude/skills/` ↔ `.agents/skills/`) differ, and Codex and Copilot CLI both use `AGENTS.md` and `.agents/skills/`. The switching steps are in each folder's README. Use one tool at a time.

## Differences between editions

| | Claude Code edition | Codex edition | Copilot CLI edition |
|---|---|---|---|
| Blocking risky actions | The AML hook blocks committing `.env`, changing test files while fixing a bug, and force push · hard reset | This version has no AML-specific blocking hook. Codex's permission, sandbox, and approval settings apply depending on your environment, and don't guarantee the same blocking as the Claude edition's AML hook | The AML hook blocks the same three kinds of actions as the Claude Code edition and shows why. If the hook runs past its time limit (10 seconds), Copilot doesn't block the action |
| Final check | A separate checking agent (`verifier`) runs things itself to check | Self-check by default. Recorded as "independent check" only when the check was actually handed to a separate agent | Calls the checking agent (`verifier`), and records "independent check" only when it was actually called |
| Usage numbers | Model, time taken, tokens, est. cost. Sending to [Langfuse](https://langfuse.com) is optional and **off by default** | Model, time taken, tokens. Shows `Usage: no record` when the numbers can't be confirmed. Models without a confirmed price show "cost unknown". No Langfuse sending | Model, time taken, tokens, and the AI credits Copilot recorded. `Usage: no record` when the numbers can't be confirmed. Dollar cost shows "cost unknown". No Langfuse sending |

## Repository layout

```text
README.md                           this document — pick a tool
claude-code/                        Claude Code edition
  .claude-plugin/marketplace.json   marketplace settings
  aml/                              plugin (commands · agents · hooks · scripts · templates · references)
  install.sh                        marketplace install script
  tests/                            basic behavior tests
codex/                              Codex edition
  .agents/plugins/marketplace.json  marketplace settings
  aml/                              plugin (skills · scripts · templates · references)
  tests/                            template match · measuring · package structure checks
copilot/                            GitHub Copilot CLI edition
  .github/plugin/marketplace.json   marketplace settings
  aml/                              plugin (skills · agents · hooks · scripts · templates · references)
  tests/                            template match · safety net · measuring · package structure checks
```

The three `aml/` folders don't refer to each other. The 5 common templates (spec · task · progress · intent · review) are included with identical content in all three editions, and `codex/tests/test-templates.sh` and `copilot/tests/test-templates.sh` check that they match.

## Tests

```bash
bash claude-code/tests/e2e-smoke-guard.sh     # blocking risky actions: 6 groups of cases
bash claude-code/tests/e2e-smoke-observe.sh   # usage records and install result
bash codex/tests/test-templates.sh            # whether the common templates match across two editions
python3 codex/tests/test_observe.py           # Codex measuring and summary numbers
bash codex/tests/test-package.sh              # Codex package structure (with the codex command, also an isolated install)
bash copilot/tests/test-templates.sh          # whether the common templates match across three editions
bash copilot/tests/test-guard.sh              # Copilot edition blocking of risky actions
python3 copilot/tests/test_observe.py         # Copilot measuring and summary numbers
bash copilot/tests/test-package.sh            # Copilot package structure (with the copilot command, also an isolated install)
```

## More

- [`claude-code/aml/README.md`](claude-code/aml/README.md) — what each command does, how planning questions work, Langfuse setup
- [`claude-code/aml/Example.md`](claude-code/aml/Example.md) — a full walkthrough from planning through building, checking, and improving
- [`claude-code/aml/references/`](claude-code/aml/references/) — how the documents connect step to step, adding blocking rules, growing the project
- [`codex/aml/references/`](codex/aml/references/) — the Codex edition's switch prep, checking the done criteria, measuring rules
- [`copilot/aml/references/`](copilot/aml/references/) — the Copilot CLI edition's switch prep, checking the done criteria, measuring rules

## License

[MIT](LICENSE)
