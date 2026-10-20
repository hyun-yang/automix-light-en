<!-- Headings and notes are examples — keep the structure, write the content in English.
     Keep it to one page — Copilot reads it start to finish every session,
     so old content left lying around pushes out what actually matters. -->
# AGENTS.md — <project name>

<!-- Copilot reads this file automatically every time (Codex reads the same file). Write what to know and what to keep in this project. -->

## What this project builds

<One or two sentences — taken from "Why" in spec.md.>

## What it's built with

- Language/framework: <what was decided in the interview>
- Folder layout: <one or two lines on what is where. If nothing yet, "Nothing yet">

## How to check

<!-- For each command, also write "what it looks like when it works". That way Copilot can judge on its own. -->

- Run: `<command>` → <when it works, it looks like this>
- Test: `<command, or "None yet">` → <when it works, it looks like this>

Before saying a task is done, actually run the above and paste the output.
If a test fails, **fix the code, not the test** — never delete or skip a test.

## Where the map is

- `intent.md` — why we decided to build this in the first place (newest at the top)
- `spec.md` — what we're building and the done criteria (this list is the real standard)
- `task.md` — tasks in order + a plan per section (Files / Risk / Proof)
- `progress.md` — log of what was done (newest at the top)
- `REVIEW.md` — what to look at when reviewing
- `.agents/skills/` — this project's rule cards

Build with `/aml:go`, check with `/aml:review`, see progress with `/aml:status`, start the next round with `/aml:next`. (In Codex, call them like `$aml:go`.)

## Rules

- The user is a beginner — explain and write records in English, in plain words.
- Don't change the "Decisions" in spec.md on your own. If one needs to change, ask first.
- <add project rules here>

## What the AI keeps getting wrong

<!-- When the same mistake happens twice, add one line here (/aml:rule adds it for you).
     Lines here stop that mistake from the next session on. -->

- <None yet>
