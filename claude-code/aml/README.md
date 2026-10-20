# automix-light (aml) — English edition

> A Claude Code plugin for people building their first app. A light, English version of automix that guides you from planning through building, checking, and improving after use.

automix (am) supports plan verification, code review, team work, reusable development patterns, and integration with external monitoring tools. automix-light keeps the parts you need when building your first app on your own.

v0.6.0 is based on Anthropic's [AI-Native SDLC playbook](https://claude.com/blog/the-ai-native-sdlc-playbook), **with the development process simplified so someone building an app alone can follow it.** The core idea is to write down the result of each step as a document, and to work from that document in the next step. aml writes these documents in plain English that beginners can follow.

| Step | What gets recorded |
|---|---|
| Planning (`intent.md`) | Why the app is being built and the problem it solves |
| Requirements (`spec.md`) | Features needed, done criteria, expected problems |
| Task plan (`task.md`) | Order of work, files to change, expected risks, how to check |
| Build and check (code + `progress.md`) | What was built, check results, time taken and cost |
| Code review | Bugs, security problems, whether requirements are met |
| Improving after use | Small fixes go into `task.md`; new features or changes of direction go into `intent.md` |

- **7 commands** — the basic flow is `/aml:new` → `/aml:go` → `/aml:review` → `/aml:next`. As needed, write development rules with `/aml:rule`, check progress with `/aml:status`, and check readiness with `/aml:doctor`.
- **Markdown first** — command definitions, templates, and work results are kept as English markdown documents. The only running code is the usage-recording script (`scripts/observe.py`, Python standard library only) and the blocking hook (`hooks/aml-guard.sh`).
- **Blocking risky actions** — blocks committing sensitive files, changing test files while fixing a bug, force pushes, and other risky actions, and explains why and what to do instead.
- **A separate checking agent** — when the build is done, the `verifier` agent runs things itself to check the done criteria are met.

The design draws on the principles of "A Field Guide to Fable": keep prompts short, pass on the context of the work and not just the constraints, and find what's uncertain before starting. When building your first app, even knowing what needs deciding can feel overwhelming. So aml doesn't jump into building; it starts by sorting out the requirements through questions and answers.

## Install

Run the install script from the folder where you downloaded the repository.

```bash
cd automix-light-en
bash claude-code/install.sh   # copies to ~/.claude-marketplaces/automix-light-en
```

Then type these in Claude Code.

```text
/plugin marketplace add ~/.claude-marketplaces/automix-light-en
/plugin install aml@automix-light-en
```

When the 7 commands below, such as `/aml:new` and `/aml:go`, show up in `/help`, the install is done.

## How it flows

### 1. `/aml:new "describe the app you want in one line"`

First it gets the project's basic setup ready. If `CLAUDE.md` (the project guide Claude Code reads automatically every session) and `REVIEW.md` (the code review checklist) don't exist, it creates them. **Files that already exist are not changed.** If it isn't a Git repository, it initializes one and sets the default branch to `main`.

Next it records why you're building the app in **`intent.md`**. It keeps your original words before refining the requirements through questions and answers, so you can always look back at what you first had in mind.

When shaping the requirements, it asks from four angles.

| Kind | What to find out | How it goes |
|---|---|---|
| KK: what you already know | Requirements you described clearly | Writes down what you said as is. |
| UU: what you haven't thought of yet | More things that need deciding to build the app | First shows an example list: "people usually decide these things". |
| KU: what needs deciding | Things you know matter but haven't decided | Asks questions with options. You can also ask for a recommendation. |
| UK: taste that's hard to put into words | The feel and layout of the screens you want | Shows 3–4 different mockups and lets you pick. |

From this it writes `spec.md` and `task.md` and asks you to review them. `spec.md` holds the done criteria and expected problems; `task.md` holds the files, risks, and how to check for each section of work. In the documents these are called **"Concerns"** and **"Files / Risk / Proof"**.

### 2. `/aml:go`

Builds the tasks in `task.md` in order. Each task goes like this.

1. **Check the plan** — if the risk is "low" and there's a set way to check it, it tells you the task can be left to run on its own.
2. **Build** — a bug fix **starts by writing a failing test that reproduces the problem**. Screen work is compared with the mockup two or three times. If the plan changes, `task.md` is updated too.
3. **Check** — runs the commands under "How to check" in `CLAUDE.md` and shows the results.
4. **Record** — writes the work done, check results, notes, usage, and the next task at the top of `progress.md`.
5. **Commit** — commits each time a task is finished.

When all tasks are done, it wraps up with a separate check by `verifier`, checking the done criteria, a code review, and a final commit, in that order.

**Usage** is recorded as one line per task, like this. The numbers below are just an example of the format.

```text
- Usage: claude-opus-4-8 · 4m 32s · tokens in 12.3k / out 4.1k (cache read 88k / write 2.1k) · est. cost $0.42
```

It shows the model used, time taken, input and output tokens, and estimated cost. Tokens are the units a model processes text in. The cost is an estimate from the public price list, so it may differ from what you're actually billed. If there's no `python3`, it shows `Usage: no record` and the build carries on.

### 3. `/aml:review`

Before committing, it checks **bugs, security problems, and whether requirements are met** against `REVIEW.md`. In the review checklist these are called "Bugs", "Safety", and "Promises kept". The requirements check also covers whether the done criteria in `spec.md` and the plan in `task.md` were followed.

Findings are split into "major" and "minor", and up to 5 minor findings are reported. **It doesn't change code during the review.** Any fixes are done with `/aml:go`.

Running `/aml:review all` checks all the code, including existing code.

### 4. `/aml:next`

Brings the problems and wanted features you found while using the finished app into the next work. Small fixes go into `task.md`; new features or changes of direction go into `intent.md`.

After a bug is fixed, an item that checks the same problem hasn't come back is added to the done criteria in `spec.md`. Later builds are checked against it too.

### 5. `/aml:rule`

When the same mistake happens **twice**, a rule to prevent it is written down. A simple caution becomes one line in `CLAUDE.md`; a procedure with several steps becomes a rule card (`.claude/skills/<name>/SKILL.md`). Claude refers to rule cards in later sessions when doing related work.

### 6. `/aml:status`

Summarizes progress and anything blocking the work, and shows the done-criteria pass rate, repeated review findings, and total time and cost. If you like, a **quiz** checks how well you understand the app you built.

### 7. `/aml:doctor`

Checks the project's state before starting work or when something goes wrong. It doesn't change files.

- ❌ **Fix before working** — if `spec.md`, `task.md`, or `progress.md` is missing, or there are no done-criteria or task checkboxes, it points you to `/aml:new`.
- ⚠️ **For your information** — checks whether `CLAUDE.md`, `intent.md`, and `REVIEW.md` exist, whether the bug-fix marker file (`.aml/FIXING`) is left over, the blocking feature, whether Git and `python3` are installed, whether a check was run after settings changed, and the Langfuse settings.

## Blocking risky actions

The blocking hook works in folders that have `spec.md` and `task.md`, and is on by default.

| Blocked action | Why |
|---|---|
| Committing a `.env` file | Passwords and API keys can stay in the Git history even after the file is deleted. |
| Changing test files while fixing a bug | Changing a test to make it pass may leave the real bug unfixed. |
| Force push, hard reset, mass file deletion | Work or history can disappear and be hard to recover. |

To turn it off, set `guard: "off"` in `.aml/config.yaml`. For how it works in detail and how to add project-specific blocking rules, see [Handing work over and blocking risky actions](references/autonomy-and-guardrails.md).

## Langfuse integration (optional)

[Langfuse](https://langfuse.com) is a tool for viewing LLM work numbers on a dashboard. When connected, the model, token usage, time taken, and check result for each task are sent, so you can see the work flow per feature on the web. **It's off by default**, and local usage recording works without it.

1. Get a public key and a secret key from a Langfuse project (cloud or self-hosted).
2. Set the keys **only as environment variables**. Don't put them in a settings file.
   ```bash
   export LANGFUSE_PUBLIC_KEY=pk-...
   export LANGFUSE_SECRET_KEY=sk-...
   export LANGFUSE_HOST=https://cloud.langfuse.com   # use your own address if self-hosted
   ```
3. Create `.aml/config.yaml` in the project root.
   ```yaml
   langfuse: "on"        # "off" or no settings file means nothing is sent (default)
   langfuse_host: ""     # empty uses LANGFUSE_HOST; without that env var too, cloud.langfuse.com
   guard: "on"           # blocking feature: on by default, "off" to turn it off
   ```
4. Check the connection with `/aml:doctor`. When it shows "OK: Langfuse connection confirmed", the setup is done.

If sending fails because of a network error or a wrong key, it leaves a warning and the build carries on.

## Example

```text
/aml:new "a kanban-style to-do app, in a single HTML file"
  → Git setup (default branch main) + CLAUDE.md + REVIEW.md created
  → intent.md: "I want to do what I used to do with sticky notes on my laptop"
  → things to decide: number of columns, due dates, what happens to done cards, drag to move, etc.
  → 5 questions with options → 4 mockups → picks number 3
  → spec.md + task.md + progress.md created, review requested

/aml:go
  → 1.1 board screen → check → usage recorded → commit
  → 1.2 add-card dialog → same steps
  → verifier check → all 7 done criteria met → review → final commit

/aml:review
  → no major security problems / 2 minor findings → results reported

/aml:next
  → "it gets slow with lots of cards" → fix added to task.md
  → "a calendar view would be nice" → new feature written up in intent.md → /aml:new
```

## Reference docs

- [What each document is for and how to keep it](references/artifact-chain.md) — why to record with files and commits, how to use it alongside Notion or Jira
- [Handing work over and blocking risky actions](references/autonomy-and-guardrails.md) — when it's fine to let it run, adding project-specific blocking rules
- [Growing the project and working as a team](references/next-steps.md) — parallel work, CI, regular checks, team rules, Slack, dashboards
- [Full walkthrough](Example.md) — a to-do app from planning through building, checking, and improving

## When to move to automix (am)

If you keep developing several features and need a separate check step (goal), several agents working together, sharing development patterns across projects, budget caps, or an undo command, consider automix (am). The basic flow — plan → task plan → build and check — is the same, so you can carry on with what you learned in aml. am's Langfuse integration (`/am:observe`) uses the same environment variables.
