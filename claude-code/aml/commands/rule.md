---
description: When the same mistake happens twice, set it as a rule — one line in CLAUDE.md or a rule card (.claude/skills).
argument-hint: "[the rule in one line — empty means find one in the records and suggest it]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion
---

# /aml:rule — so the same mistake doesn't happen a third time

To make into a rule: $ARGUMENTS

A mistake that people prevent by remembering will happen again someday. Write it in a file and Claude keeps it on its own from the next session on. This command sets **things that happened twice** as rules — something that happened once isn't a rule yet.

## 1. Decide what to make into a rule

- If there's an argument, start with that.
- If not, skim `progress.md` for things that came up **two or more times**: notes ("did differently from the plan"), findings in review lines, records of getting stuck. Show up to 3 with evidence (when they happened) and let the user pick.
- If nothing came up twice or more, say so and stop: "Nothing has repeated enough to make a rule yet. Something that happened once may just have been a one-off mistake."

## 2. Decide where it goes

| If it's | Put it in |
|---|---|
| A short line, a habit that only applies to this project | `CLAUDE.md` |
| A procedure with an order (3+ steps), or something to use in other projects too | Rule card `.claude/skills/<name>/SKILL.md` |
| Something you can't undo once it happens (deleted for good, money spent, data leaked) | A spoken rule alone isn't enough — see below |

If it's **something you can't undo**: first check whether it's one of the three things the aml safety net already blocks (secret keys · test files while fixing · irreversible commands). If it isn't, look at `${CLAUDE_PLUGIN_ROOT}/references/autonomy-and-guardrails.md` and explain how to add a safety net to the project directly. A rule card makes something "usually kept"; a safety net makes it "impossible" — they do different jobs.

## 3. Write it

- **CLAUDE.md** — add one line under "What Claude keeps getting wrong" (to stop a mistake) or "Rules" (to always keep). CLAUDE.md is read in full every session, so it **must not go past one page** — if it looks like it will, first ask whether to delete old lines that no longer fit.
- **Rule card** — create `.claude/skills/<english-name>/SKILL.md` following `${CLAUDE_PLUGIN_ROOT}/templates/skill.template.md`. The `description` matters more than the body: write specifically **when to pull out this card** (like "Use when creating or changing an API"). That one sentence alone decides whether it gets pulled out.

## 4. Check it really gets pulled out

If you made a rule card, ask about a situation that needs the rule **twice, in different words**, and see whether the card actually gets pulled out. If not, the `description` is too narrow — rewrite the situation more broadly. Tell the user the result in one line.

## 5. Record it

Add one line to the latest entry in progress.md:

`- Rule added: run tests before commit (why: same finding twice) → CLAUDE.md`

If it's a git repository, commit (`rule: <one line>`). When and why the rule appeared stays on record.
