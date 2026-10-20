---
name: status
description: Summarizes progress and numbers (time · tokens · cost) in plain words from spec.md / task.md / progress.md. Read-only. Use for "how far along are we?", "progress", or "/aml:status".
---

# /aml:status — check progress

Read spec.md, task.md, and progress.md in the project root (and intent.md and REVIEW.md if they exist). If none of the three exist, tell the user to start with /aml:new. Don't change anything.

Report (in English, in plain words):

- **How far along** — how many of the done criteria are checked, how many tasks are done, the most recent work in one line
- **Blocked** — if progress.md records something blocking, what it is and the question the user needs to answer
- **Numbers** — see below
- **Next** — /aml:go if tasks are left, try it yourself and then /aml:next if everything is done, /aml:review if it's before a commit

## Numbers

Add one line explaining what each number means. Don't just throw numbers at a beginner.

First, add up the usage lines (`<package>` is two levels up from this SKILL.md. Skip only this step if there is no python3):

```bash
python3 "<package>/scripts/observe.py" summary progress.md
```

Show the output as is, then add what can be counted from the files. Usage lines left by Claude Code·Codex·Copilot are added up together even when mixed. "AI credits" in Copilot lines are usage Copilot recorded itself, so they're added up separately and not mixed with dollar costs. If there's "cost unknown", explain: "These are models whose price couldn't be confirmed, so their cost was counted separately instead of as 0."

- **Done criteria passed** — `- [x]` / total in spec.md. "When this whole list is checked, it's finished."
- **Check type** — the most recent `Check type:` line in progress.md (self-check / independent check).
- **Repeated findings** — show the 3 most recent review lines in progress.md (`- Review: major N · minor M`) side by side. If the major count is going down, say so.
- **Times blocked** — the number of blocked records in progress.md. If you got stuck on the same thing two or more times, suggest /aml:rule.
- **Days so far** — from the oldest date in intent.md to today. "It's been N days since you first thought of this."
- **Rule cards** — the number of `.agents/skills/*/SKILL.md`. Zero just means no rules have been made yet; it isn't wrong.

## Last — offer a quiz

If they want, a **quiz**: about 3 easy questions about what's been built so far, to check the user could explain it to someone else. Keeping up with the flow isn't about reading code; it's about checking you understand.
