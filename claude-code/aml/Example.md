# A full walkthrough with a to-do app

An example of planning a simple to-do app with aml, building and checking it, then improving what you found while using it. The conversation and usage numbers below are examples for explanation; real runs will differ.

## The commands

On top of the 4 original commands, 3 commands for review, planning improvements, and development rules were added, for 7 in total.

| Kind | Commands |
|---|---|
| Original commands | `/aml:new`, `/aml:go`, `/aml:status`, `/aml:doctor` |
| Added in v0.6.0 | `/aml:review`, `/aml:next`, `/aml:rule` |

The basic order is to plan with `/aml:new` and build with `/aml:go`. When `/aml:go` finishes, it also runs a review automatically. Use the other commands when you need them.

## Step 0: pre-start check (optional)

```text
/aml:doctor
```

In an empty folder, it says `spec.md`, `task.md`, and `progress.md` are missing and suggests running `/aml:new`. When starting for the first time, you can skip this check and go straight to `/aml:new`.

## Step 1: shaping the idea and planning the work

```text
/aml:new "an app to write down and check off to-dos, as a single HTML file I open in the browser"
```

Claude goes in this order.

1. **Project setup** — if it isn't a Git repository, it initializes one with a `main` branch. If `CLAUDE.md` and `REVIEW.md` don't exist, it creates them, and keeps existing files.
2. **Recording the purpose** — before starting the questions, it writes your words into `intent.md` and commits with `intent: to-do app`.
3. **Checking the requirements** — it lists things that need deciding, like what happens to finished to-dos, due dates, reordering, and saving data. Then it asks about 5 questions with options, and has you pick the screen from 3–4 mockups.
4. **Writing the plan** — `spec.md` gets the done criteria and expected problems; `task.md` gets the files, risk, and how to check for each task. It also creates `progress.md`, has you review the plan, then commits with `plan: to-do app`.

`intent.md` ends up with something like this.

```text
- What's not working: I write them on sticky notes and keep losing them.
- What good looks like: when I open my laptop, I'd like to see today's to-dos.
- Still unknown: I'm not sure what features need deciding.
```

Here's an example of `task.md`. The "Proof" line says how to check the task was really finished.

```markdown
## 1. Screen and saving

- Files: todo.html
- Risk: low
- Proof: after adding 3 to-dos in the browser, the list stays after a refresh.

- [ ] 1.1 list screen and add dialog
- [ ] 1.2 mark done and delete
- [ ] 1.3 save in the browser (stays after refresh)
```

## Step 2: building and checking

```text
/aml:go
```

Each task goes **check the plan → build → check → record → commit**.

For example, "1.1 list screen and add dialog" goes like this.

```text
says the risk is low and there's a set way to check it
  → builds the screen, then checks it works in the browser
  → records the result and usage in progress.md
     - Usage: claude-opus-4-8 · 3m 11s · tokens in 8.2k / out 2.4k · est. cost $0.19
  → commits feat: 1.1 list screen and add dialog
```

The other tasks go the same way. When all tasks are done, it wraps up like this.

1. **Separate check** — the `verifier` agent runs things itself to check the done criteria are met.
2. **Ticking the done criteria** — criteria that passed are changed from `- [ ]` to `- [x]` in `spec.md`.
3. **Code review** — checks bugs, security problems, and whether requirements are met against `REVIEW.md`, and reports the result like "major 0 · minor 2".
4. **Final commit** — wraps up, and suggests using the app yourself and then running `/aml:next`.

## Step 3: sorting out improvements after use

```text
/aml:next
```

Claude asks whether the app behaved as you expected, what felt awkward or odd, and whether you need any more features.

| What you said | How it's handled |
|---|---|
| "Long titles get cut off." | A small fix, so a task is added to `task.md`. |
| "I'd like to see them on a calendar too." | A new feature, so it's written at the top of `intent.md` and planned with `/aml:new`. |
| "I'll add reminders later." | The reason for not building it this time is recorded in `intent.md` or `progress.md`. |

The added fix is carried out with this command.

```text
/aml:go
```

When fixing a bug, a test or check that reproduces the problem is prepared first. While the `.aml/FIXING` file (marking that a fix is in progress) exists, the blocking hook stops test files from being changed.

The fixed bug is also kept in the done criteria in `spec.md`, so later work checks it again.

```markdown
- [x] long titles don't get cut off (fixed 2026-09-06)
```

## Commands to use when needed

```text
/aml:review          # check changes once more before committing
/aml:review all      # check all the code, including existing code
/aml:rule            # turn repeated findings or mistakes into development rules
/aml:status          # see progress and numbers, and an understanding quiz if you like
/aml:doctor          # check readiness or settings problems
```

For example, if `/aml:rule` finds in `progress.md` that "forgot to check it saved" happened twice, it adds a prevention rule under "What Claude keeps getting wrong" in `CLAUDE.md`. If it's a procedure with several steps, it's written as a rule card in `.claude/skills/<name>/SKILL.md`.

## The whole flow

```text
/aml:new → /aml:go → use it yourself → /aml:next
  plan     build & check                 sort out improvements
                                         ├ small fix → /aml:go
                                         └ new feature / change of direction → /aml:new
```

At any point you can see progress with `/aml:status`, and run checks with `/aml:review` or `/aml:doctor`. When planning the next feature, you carry on with the existing documents and development rules.
