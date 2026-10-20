---
name: next
description: After building, take what came up while using it into the next round — small things into task.md, big things into a new intent.md. Use for "I tried it", "what should I do next?", or "/aml:next".
---

# /aml:next — one more round

Building and stopping is only half the job. Things become truly usable **after you use them and fix them**. This skill turns what the user noticed while using it into the next tasks.

Read intent.md (if it exists), spec.md, task.md, and progress.md in the project root. If spec.md is missing, tell the user to start with /aml:new and stop.

## 1. So far, in one line

Summarize in a line or two of plain words how many of the done criteria are checked, and what was done last.

## 2. Hear how using it went

Ask one at a time and wait for the answer. Add examples so it's easy for a beginner to answer.

1. **Did it work well?** — things that behaved the way you expected
2. **Anything that didn't work or felt odd?** — clicked and nothing happened, slow, confusing, text cut off… anything
3. **Anything you wish it had?** — things you missed while using it

"Nothing really" is an answer too. In that case, dig a little more into question 3.

## 3. Sort what came up

| If it's | Do this |
|---|---|
| A small problem that can be fixed now | Add it to `task.md` as a new task. Make a new section and fill in the three lines **Files / Risk / Proof** → when done, point to /aml:go |
| A new feature or a big change of direction | Write a new intent at the top of `intent.md` with today's date (in the user's own words, filling in the fields of the [intent template](../../templates/intent.template.md)) → point to /aml:new |
| Not doing it now | Leave one line with the reason under "Not this time" in intent.md or in progress.md |

At the end, show in one go what went where.

## 4. Keep fixed problems on the checklist for good

If any **bugs were fixed** this round, add each as one line (with the date) to the "Done criteria" in `spec.md`:

`- [x] Saving with an empty title doesn't freeze the app (fixed 2026-09-10)`

From now on, /aml:go re-checks this whole list every time it finishes. If something fixed once breaks again because of something built later, it gets caught then — the longer this list grows, the safer you are.

## 5. Now and then, look at the whole thing

If the last full check was about a month ago or there hasn't been one, suggest: "Shall we check 'all' with /aml:review and go over all the code now? Not just the new things — we look for anything risky in what was built before."

## 6. Wrap up

If it's a git repository, commit the changed files (`next: <one line>`). Then say in one line what to do next — /aml:go if tasks were added, /aml:new if a new intent was written.
