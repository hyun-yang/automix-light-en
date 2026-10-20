---
name: rule
description: When the same mistake happens twice, set it as a rule — one line in AGENTS.md or a rule card (.agents/skills). Use for "make this a rule", "same mistake again", or "$aml:rule".
---

# $aml:rule — so the same mistake doesn't happen a third time

To make into a rule: the rule the user named (if none, find one in the records and suggest it)

A mistake that people prevent by remembering will happen again someday. Write it in a file and Codex keeps it on its own from the next session on. This skill sets **things that happened twice** as rules — something that happened once isn't a rule yet.

## 1. Decide what to make into a rule

- If the user named a rule, start with that.
- If not, skim `progress.md` for things that came up **two or more times**: notes ("did differently from the plan"), findings in review lines, records of getting stuck. Show up to 3 with evidence (when they happened) and let the user pick.
- If nothing came up twice or more, say so and stop: "Nothing has repeated enough to make a rule yet. Something that happened once may just have been a one-off mistake."

## 2. Decide where it goes

| If it's | Put it in |
|---|---|
| A short line, a habit that only applies to this project | `AGENTS.md` |
| A procedure with an order (3+ steps), or something to use in other projects too | Rule card `.agents/skills/<name>/SKILL.md` |
| Something you can't undo once it happens (deleted for good, money spent, data leaked) | A spoken rule alone isn't enough — see below |

If it's **something you can't undo**, say so honestly: "This version has no AML-specific blocking hook. Codex's permission, sandbox, and approval settings apply depending on your environment, and don't guarantee the same blocking as the Claude edition's AML hook." So put "always ask the user before doing this" in a rule card, and suggest the user look at Codex's approval settings themselves. Don't change user settings files (`~/.codex/config.toml` etc.) before asking. A rule card only makes something "usually kept"; it can't make it "impossible".

If there are **rule cards used in Claude Code** (`.claude/skills/`), don't move them automatically. Ask the user whether each rule should still be kept, and write only those anew into `.agents/skills/` with this skill. Don't delete or change the original cards.

## 3. Write it

- **AGENTS.md** — add one line under "What Codex keeps getting wrong" (to stop a mistake) or "Rules" (to always keep). AGENTS.md is read in full every session, so it **must not go past one page** — if it looks like it will, first ask whether to delete old lines that no longer fit. If there's no AGENTS.md, create it first from the [AGENTS template](../../templates/agents.template.md).
- **Rule card** — create `.agents/skills/<english-name>/SKILL.md` following the [rule card template](../../templates/skill.template.md). The `description` matters more than the body: write specifically **when to pull out this card** (like "Use when creating or changing an API"). That one sentence alone decides whether it gets pulled out. If a card with the same name already exists, don't overwrite it; use another name or ask the user.

## 4. Check it really gets pulled out

Rule cards are read in a new session. Write a situation that needs the rule **twice, in different words**, hand them to the user, and ask them to check in a new Codex session whether the card gets pulled out. If you couldn't check it yourself in this session, write "Pulled out: not checked yet". If it doesn't get pulled out, the `description` is too narrow — rewrite the situation more broadly.

## 5. Record it

Add one line to the latest entry in progress.md:

`- Rule added: run tests before commit (why: same finding twice) → AGENTS.md`

If it's a git repository, commit (`rule: <one line>`). When and why the rule appeared stays on record.
