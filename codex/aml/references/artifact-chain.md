# What each document is for and how to keep it

The documents aml writes are **the standard for the next step's work**. Purpose, requirements, plan, and results are each recorded in their own file.

| File | What it records | Step that uses it |
|---|---|---|
| `intent.md` | Why the app is being built and the problem it solves | Referenced in `$aml:new` when shaping the requirements |
| `spec.md` | The features needed and the done criteria | Checks in `$aml:go`, requirement checks in `$aml:review` |
| `task.md` | Order of work, expected risks, how to check | Build order and plan changes in `$aml:go` |
| `progress.md` | Work done, usage numbers, review results | Progress summary in `$aml:status`, finding repeated mistakes in `$aml:rule` |
| `REVIEW.md` | Code review scope and standards | Checking with consistent standards in `$aml:review` |
| `AGENTS.md` | Project guide, how to run and check, development rules | Read by Codex at the start of every session |
| `.agents/skills/` | This project's rule cards | Pulled out and read by Codex when needed (made by `$aml:rule`) |

If the same content is kept in several files, only some get updated and they drift apart. Depending on what you want to check, treat these files as the standard.

| What to check | Standard document |
|---|---|
| Why the app is being built | `intent.md` |
| When the build counts as done | The done criteria in `spec.md` |
| Current work and whether it's done | Checkboxes in `task.md` |
| Decisions made while building, and why | Notes in `progress.md` |
| What to cover in code review | `REVIEW.md` |
| How to run and check the app | "How to check" in `AGENTS.md` |

## How to keep the documents

1. **Commit the result of each step.** You can see with `git log` what was decided and changed, and when. If needed, you can also undo changes one commit at a time.
2. **When the build plan changes, update the documents too.** If only the code changes and `task.md` stays the same, later work follows the wrong plan. Put plan changes in the same commit as the related code.
3. **Keep earlier records.** Keep earlier plans further down in `intent.md`, check criteria for fixed bugs in `spec.md`, and work results in `progress.md`. Later work can then look up the reasons behind decisions and check whether the same problem came back.

## When used with other tools

If you also record plans in Notion, Jira, or Trello, decide **which side is the standard** when the content differs.

- **The repository is the standard** — the simple way when working alone. Keep the content in the markdown files and leave links to those files in Notion etc.
- **The external tool is the standard** — if the team already uses a tool, treat the content in Notion or Jira as the standard. At the start of a session, bring what's needed into the project documents, and after work, put the results back into the external tool.
- **Keep links between documents** — on both sides, show links to related documents and which one is the standard, so the latest content can be found.

Even after deciding on the standard, you need a routine for copying changes to the other side. When the two differ, check the standard document first.

## When growing into team work

A team can use the same set of documents. In PR reviews, look at `spec.md`, `task.md`, and `REVIEW.md` together to check that the requirements and plan were met.

## When used with the Claude Code edition

`intent.md`·`spec.md`·`task.md`·`progress.md`·`REVIEW.md` have the same shape as in the Claude Code edition, so you can carry on with them as they are. The only differences between the tools are the guide file (`AGENTS.md` ↔ `CLAUDE.md`) and the rule card location (`.agents/skills/` ↔ `.claude/skills/`). For the steps when moving, follow [switch prep](switching.md). Use one tool at a time — if both tools change `task.md` at the same time, one side's changes can be overwritten.
