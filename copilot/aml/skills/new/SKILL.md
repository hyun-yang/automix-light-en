---
name: new
description: Turns a one-line idea into intent.md / spec.md / task.md / progress.md through an interview. Does not build anything. Use when turning a new idea into a plan, like "I want to make something new", "plan this for me", or "/aml:new".
---

# /aml:new — draw the map through conversation

The person you are working with is a beginner. They can't read code, but they can answer questions and react to what they see. The goal of this skill is to move the picture in the beginner's head into a few files — building is /aml:go's job. Write the conversation and everything you produce (intent.md·spec.md·task.md·progress.md, down to the template headings) in **English**, in plain words a beginner understands. (Only the usage line the machine adds stays exactly in the format observe.py produces.)

`<package>` is two levels up (`../../`) from the folder this SKILL.md is in. The templates are in `<package>/templates/`.

## 1. Check for work already in progress

If spec.md and task.md exist in the project root and there are unfinished tasks, ask the user whether to continue (point them to /aml:go) or start fresh. If starting fresh, leave a summary of the previous work in progress.md, then write spec.md and task.md anew. Even if continuing, still check the setup in step 2 before moving on.

**If there's a plan made in another tool**: if spec.md·task.md exist, don't plan anew. For a project started in Codex (AGENTS.md exists), say it can carry on with /aml:go as is. For a project started in Claude Code (only CLAUDE.md, no AGENTS.md), point to the [switch prep](../../references/switching.md) steps and follow them as they are — don't rewrite the existing plan.

## 2. Look around and get the setup ready

If there is existing code, skim it and work out the language, framework, and structure. Skip this for an empty project.

Then check the setup — before the interview, before writing any files.

- **AGENTS.md** — only check whether it exists in the project root and remember. **If it exists, never overwrite it.** If not, create it in step 5 from the interview.
- **REVIEW.md** — only check whether it exists. **If it exists, don't overwrite it.** If not, create it from the template in step 5.
- **Rule cards** — if `.agents/skills/*/SKILL.md` exist, read them all. These are rules already decided for this project; treat them as constraints throughout steps 3–5.
- **git** — if this isn't a repository, say so and initialize it right away. If it already is, do nothing (don't rename anyone's branches either).

  ```bash
  git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
    || git init -b main 2>/dev/null \
    || { git init && git symbolic-ref HEAD refs/heads/main; }
  ```

  Tell the user in one line: "I set up git so changes are easy to undo, and set the default branch to main."

## 3. Write down the first words as they are — intent.md

**Before** refining anything through the interview, first write down in the user's own words why they want to build this. It's the original to come back to if you get lost later.

Create `intent.md` in the project root following the [intent template](../../templates/intent.template.md) (if it already exists, add a new entry with today's date **at the top** and leave past entries as they are). How to fill it:

- Don't rewrite the user's sentences. Don't translate them into jargon.
- Don't leave unknown fields blank — write "not known yet". That's exactly what the next step will dig out.
- Ask back only one or two short questions (what's not working, what good looks like). The real questions come in step 4.

If it's a git repository, commit once here: `intent: <one line>`.

## 4. Dig out what's unknown — the interview

A beginner's map has four zones, and each one is drawn out differently.

- **KK (known knowns)** — what the user has already said. Don't ask again; write it down as is.
- **UU (unknown unknowns)** — decisions they haven't even thought of. **Blind-spot sweep**: first show a list of "when building something like this, people usually decide these things". Just seeing the list turns UU into KU.
- **KU (known unknowns)** — things that need deciding but aren't decided yet. Ask **one at a time** without jargon, with options, and wait for the answer. Include an "I'm not sure — recommend one" option in every question; if they pick it, make the choice for them and give the reason.
- **UK (unknown knowns)** — they can't explain it, but they know it when they see it. If screens or design matter and the user can't put their taste into words, make 3–4 screen mockups with completely different feels in one HTML file and let them pick. The chosen mockup becomes a reference (part of the map).

Match the number of questions to the size — about 3 for a small feature, about 7 when it's a new app or a framework choice is involved. Ask questions that could change the structure first.

If you read rule cards in step 2, offer the options that fit those rules first. If a rule and the user's request clash, don't decide on your own — tell them, ask what to do, and record the outcome under "Concerns" in spec.md.

## 5. Write the outputs

Create them in the project root following the templates in `<package>/templates/`.

- **spec.md** — [spec template](../../templates/spec.template.md). Holds the interview results.
  - Write the "Done criteria" as sentences the beginner can check by trying it themselves — this list is what /aml:go checks against, and it becomes a checklist that keeps growing.
  - Put what was decided in the interview in the "Decisions" table, and the chosen mockup, screenshots, or "like the ○○ app" under "References (the map)".
  - Under **"Concerns"**, flag things before building — clashes with rule cards, anything involving other people's data, money, or safety, and requests that can't both be met. If none, "None". Confirm anything written here with the user once more.
- **task.md** — [task template](../../templates/task.template.md). The big tasks to work through in order. One task = one chunk you finish in one go. For each section fill in the three lines **Files / Risk / Proof**. If something isn't known yet, write "not known yet", but fill in Risk and Proof whenever you can — /aml:go reads these two lines to decide "can this be left to me?" and "what will count as done?".
- **progress.md** — if it doesn't exist, create it from the [progress template](../../templates/progress.template.md) and add one "Plan made" entry with today's date.
- **AGENTS.md** — only if step 2 found none, fill it in from the interview answers following the [AGENTS template](../../templates/agents.template.md). Copilot reads this file automatically from the next session on (Codex reads the same file), so keep it short and accurate — **no more than one page**. Under "How to check", write the run and test commands along with **what it looks like when it works**. Don't push for answers to fields the interview didn't cover; leave them as `<not decided yet>`.
- **REVIEW.md** — only if step 2 found none, create it from the [review template](../../templates/review.template.md) as is. If you see something to adjust for the project, touch only a line or two.

## 6. Get it confirmed

Show a plain-words summary of spec.md and get it reviewed. If there are "Concerns", go over those first. If it's a git repository, commit the files you made (`plan: <one line>`). Once confirmed, say: "Run `/aml:go` to start building."
