---
name: review
description: Pre-commit check — goes over bugs · safety · promises kept using REVIEW.md. Does not change code. Use for "review this", "is it OK to commit?", "check everything", or "$aml:review".
---

# $aml:review — one pass before committing

Scope: the scope the user named (if none, uncommitted changes)

When you look at your own code, you miss things. This skill takes a fixed checklist (REVIEW.md) and looks at the same things with the same eyes every time.

**This skill does not change code.** It only finds things and reports them — fixing is $aml:go's job, and deciding what to fix is the user's. This skill writes to exactly two things: REVIEW.md (creating it the first time, if missing) and the one review line in progress.md.

## 1. Get the checklist ready

If `REVIEW.md` doesn't exist, copy the [review template](../../templates/review.template.md) as is into the project root and say in one line: "I created the review checklist (REVIEW.md) — feel free to edit any item you don't like." If it already exists, **never overwrite it.**

## 2. Decide the scope

- No scope named: uncommitted changes (`git diff`, `git diff --cached`, and `git status -s -uall` for new files)
- "all": go over the whole project's code (a regular check, about once a month. For a big project, start with the folders tied to the key features in spec.md)
- Any other scope is read as a git range (`HEAD~3..HEAD`, etc.)
- If there's nothing to look at (no changes), say so and stop. If it isn't a git repository, ask the user which files were recently created or changed.

## 3. Read the standards

`REVIEW.md` (what to look at), `spec.md` (done criteria · decisions · concerns), `task.md` (plan per section), `AGENTS.md`, rule cards (`.agents/skills/*/SKILL.md`).

## 4. Go over it in three passes

Follow the passes written in REVIEW.md. By default there are three.

1. **Bugs** — things that don't work, missed cases (empty values, cancel, double click, lost internet, very long input)
2. **Safety** — passwords or API keys written into the code, other people's data leaking onto the screen or into logs, places that trust user input as is
3. **Promises kept** — places that differ from the done criteria or decisions in spec.md, places that drifted from the plan in task.md without the plan being updated, whether the risks written under "Concerns" were actually handled

Write each finding like this:

```
[major·bug] todo.html:42 — Saving with an empty title turns the screen white.
   Why: nothing filters out empty values, so the next line stops.
   How: before saving, check whether the title is empty, and if so show a message.
```

- **Major**: breaks behavior · leaks data · goes against what spec.md decided
- **Minor**: everything else. List **only up to 5** and leave the rest as a count: "N more".
- Don't look at anything listed under "What not to look at" in REVIEW.md at all.
- If you're not sure, write "needs checking" and say how to check. Don't raise a guess to major.

## 5. Find repeated findings

Skim the past review lines in progress.md, and mark any finding type that is **showing up for the second time**. If there is one, suggest: "This is the second time for the same finding — if you make a rule with $aml:rule, this mistake won't happen again."

## 6. Record and wrap up

Add one line to the most recent entry in progress.md:

`- Review: major 2 · minor 4 (repeated: tests not run before commit)`

Then wrap up:

- If there's something major: "It would be best to fix the N major ones first. Fix them with $aml:go, then run $aml:review again."
- If not: "It's fine to commit now." (If everything is built, also suggest $aml:next.)
