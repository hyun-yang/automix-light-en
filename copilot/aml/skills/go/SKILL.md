---
name: go
description: Builds and checks task.md in order and records it in progress.md. When everything is done, runs an independent check (the verifier agent; self-check if it can't be called), checks the done criteria, and reviews. Use when carrying out a plan already made, like "build it", "carry on", or "/aml:go".
---

# /aml:go — build

`<package>` is two levels up (`../../`) from the folder this SKILL.md is in.

Read spec.md, task.md, progress.md (latest entries), and AGENTS.md in the project root. If intent.md and rule cards (`.agents/skills/*/SKILL.md`) exist, read those too. If spec.md or task.md is missing, tell the user to start with /aml:new and stop. If things look off, mention that /aml:doctor can check the setup.

**If there's no AGENTS.md and only CLAUDE.md**, the project was started in Claude Code. Don't write a new plan; first follow [switch prep](../../references/switching.md) — tell the user in one line "I'll create only the Copilot guide file (AGENTS.md) and leave everything else as it is", then create AGENTS.md carrying over How to check (run and test commands) from CLAUDE.md, and carry on. Don't change CLAUDE.md.

Before starting, check whether `.aml/FIXING` is left over. If it is, a bug fix was interrupted last time — tell the user in one line, delete it, and carry on.

The person you are working with is a beginner. Write all reports and records in **English**, in words someone who doesn't know programming understands.

## Task loop

Go through the unchecked tasks in task.md in order:

1. **Check the plan** — first look at `Files / Risk / Proof` for the section the task belongs to.
   - If Risk is "low" and there is a way to prove it (a test, or a screen to look at), say in one line: "You can leave this one to me — I'll build it all the way through without checking in at each step, then show you the result."
   - If a risk is written down, take that part one step at a time, and say what you're going to do before touching anything.

2. **Build** — when you start, leave a measuring start point:

   `python3 "<package>/scripts/observe.py" task-start --label "<task number and name>"`

   Remember the printed `Start: <time>` (you use it as `--since` in step 4). If there's no python3 or it fails, just note the time with `date -Is` and carry on. Build using the "Decisions" and references (mockups, screenshots) in spec.md and the rule cards as your map.
   - **If the task is fixing a bug, write a failing test first.** Write a test that reproduces the problem, confirm it really fails, create the `.aml/FIXING` file (`mkdir -p .aml && touch .aml/FIXING`), then fix **only the code** until it passes. Once it passes, `rm .aml/FIXING`. Don't change test files while fixing — that wouldn't make the bug go away, it would make the check go away. If you try to change a test file while fixing, the aml safety-net hook blocks it. If it gets blocked, look at the code again, not the test. If something forces you to change a test file, stop and ask the user.
   - **If the task has a screen, match it by eye.** Build → run it or take a screenshot → compare with the references (the chosen mockup) in spec.md → refine. If you have no tool to see the screen, write "Screen check: not done" and tell the user how to look at it themselves.
   - **If the build drifts from the plan, fix task.md on the spot.** Update the Files / Risk / Proof lines to match reality and add a word on why they changed. Never leave the plan and reality out of step.

3. **Check** — run the commands under "How to check" in AGENTS.md exactly as written and show their output as is. If there are no tests, actually run it and confirm it works. Match it against the related "Done criteria" items in spec.md. **If a test fails, fix the code, not the test.**

4. **Record** — check the task off in task.md and add an entry at the top of progress.md: Done / Checked / **Notes** (what you did differently from the plan and why — beginners read this instead of the code) / **usage line** / Next. Get the usage line with one call:

   `python3 "<package>/scripts/observe.py" task-done --since <start time> --label "<task number and name>" --feature "<spec.md title>" --note "<one-line check result>"`

   Paste the printed "Usage: …" line as is — leave it exactly in the format the script produced. If usage can't be read reliably, the script prints `Usage: no record (…)`; paste that as is too and carry on. If the call itself fails (no python3, etc.), write `Usage: no record` and carry on. **Never stop the work because of measuring.** For the detailed rules, see the [measuring guide](../../references/telemetry.md).

5. **Commit** — if it's a git repository, commit each time a task is done (e.g. `feat: 1.2 add-card dialog`). That way you can undo in these units. If it isn't a git repository, quietly skip this.

If the same problem isn't solved after 3 tries, stop: record where you got stuck in progress.md, explain the situation in plain words, and ask the user.

## When everything is done

1. **Independent check** — follow the [checking guide](../../references/verification.md). Call the `verifier` agent that comes with this plugin as a subagent and hand it the check. It checks by actually running things in a fresh context, so the builder's assumptions don't creep in. Hand it: the project location, the "Done criteria" list from spec.md (as is), the "How to check" commands from AGENTS.md, and one line on what was built this time — don't hand over the conclusion "it's done". Write "independent check" only when you actually called it and the result came back. If it can't be called or fails, set aside the conclusions you built up, check again yourself with the same list, and write "self-check". Never write that you did something you didn't. If anything is "not working", fix it and check again (at most 2 times).
2. **Tick the done criteria** — actually check the "Done criteria" items in spec.md one by one and tick them off. Don't tick items you couldn't check; leave the reason.
3. **Review** — read REVIEW.md and go over the work once now, the same way as /aml:review (bugs · safety · promises kept). If a major finding comes up, fix it and start again from 2. Add a one-line result to progress.md. Also write how it was checked: `- Check type: independent check (verifier agent)` or `- Check type: self-check (<why verifier couldn't be called>)`.
4. **Final commit** — if it's a git repository, commit.
5. **Final report** — what was built, how to check it yourself (how to run it), what couldn't be checked, and this pointer: "Try it yourself, then run /aml:next — I'll turn what you noticed while using it into the next tasks." If they want to check their understanding, suggest the quiz in /aml:status.
