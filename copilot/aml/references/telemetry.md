# Measuring — how the Copilot edition's usage line is made

/aml:go leaves one usage line in `progress.md` per task. The numbers come from `scripts/observe.py` reading Copilot CLI's session logs. Measuring **never blocks the work** — whenever anything is uncertain, it doesn't make numbers up and leaves `Usage: no record (reason)` instead.

```text
Usage: gpt-6-luna · 3m 27s · tokens in 6 / out 189 (cache read 24.8k / write 6.0k) · cost unknown · AI credits 0.11
```

## How to call it

Try `python3 -c "import sys"`, then `python -c "import sys"`, then `py -3 -c "import sys"`. Replace `python3` in the examples with the first command that succeeds, including `-3` if using `py -3`. A Windows Store shortcut can exist on PATH without working.

```bash
python3 "<package>/scripts/observe.py" task-start --label "1.2 add-card dialog"
#  → Start: 2026-10-19T18:00:00+10:00      (use this time as --since below)
python3 "<package>/scripts/observe.py" task-done --since 2026-10-19T18:00:00+10:00 --label "1.2 add-card dialog"
python3 "<package>/scripts/observe.py" summary progress.md     # /aml:status
python3 "<package>/scripts/observe.py" check                   # /aml:doctor
```

`<package>` is two levels up from the folder the skill file (SKILL.md) is in.

## Which session it reads

- It picks **only the current session** by the session id Copilot passes when running a shell command (`COPILOT_AGENT_SESSION_ID`). You can also give it directly with `--session <id>`.
- The log file is `$COPILOT_HOME/session-state/<session id>/events.jsonl` (default `~/.copilot/session-state/…`). It's read only if the id in the file's `session.start` matches.
- If the session id is unknown, it **doesn't pick some other session opened in the same folder instead.** That would mix in other work from the same project. In that case it's `no record`.
- The session log also holds the conversation, but this script only reads the usage numbers and sends nothing anywhere.

## How the span is cut

- Every time Copilot calls a model, it leaves **the amount used in that one call** as a `session.usage_record` line. Span usage = all `session.usage_record` after the start time up to now, added together.
- If the same record (the same `usageId`) appears twice, it's counted once.
- If a new session was opened partway through a task (the session start time is later than the task start), the amount used in the earlier session can't be known, so it **isn't stitched on**; it's `no record`.
- The model is taken from the `model` written in each record. If the model changes within the span, it's written per model. In Copilot's "auto" mode, the log keeps the name of the model actually used.

## How the token numbers relate (never count twice)

Checked on 2026-10-19 against 7 real logs from Copilot CLI 1.0.98 — all 7 kept the relations below exactly, and the usage line numbers matched `Tokens ↑ … (… cached, … written) • ↓ …` · `AI Credits …` shown at the end of Copilot's screen.

| Name in the log | Meaning | Relation |
|---|---|---|
| `inputTokens` | All input | cache reads and cache writes are **included** |
| `cacheReadTokens` | Input read from cache, out of that | |
| `cacheWriteTokens` | Input newly written to cache, out of that | |
| `input` in `copilotUsage.tokenDetails` | Uncached input | equals `inputTokens − cacheReadTokens − cacheWriteTokens` |
| `outputTokens` | All output | |
| `reasoningTokens` | Reasoning, out of that | at most `outputTokens` |
| `copilotUsage.totalNanoAiu` | Usage as Copilot calculated it | divided by one billion, the AI credits on screen |

In the usage line, **"in" is uncached input**, and **"cache read / write" are written separately**. This matches the meaning of the Claude edition's usage line, so when all three tools' lines are mixed, the summary adds like with like. If even one of the relations above doesn't hold, it doesn't guess; it's `no record`.

## Cost and AI credits

- **Dollar cost** is calculated only for models whose prices and token meanings have been confirmed. There are no confirmed prices yet, so all of the Copilot edition's usage lines say `cost unknown`. With a Copilot subscription, tokens may not cost money one by one anyway. The cost of an unknown model is **never written as 0** — 0 reads as "free".
- **AI credits** are the usage Copilot wrote into the log itself, carried over as is (not an estimate). They're in a different unit from dollars, so they're written separately, not combined. If even one record in the span has no credits, that line doesn't show credits.

| Model | Input | Cached input | Output | Source | Checked on |
|---|---|---|---|---|---|
| (none yet) | | | | | |

When adding prices, confirm them from the official price list and change this table and `PRICING` in `observe.py` together.

## Summary (/aml:status)

`summary` reads all the usage lines in `progress.md` and shows the number of tasks · total time taken · tokens (approx.) · total known dollar cost · total AI credits. Tokens in the usage lines are rounded like `12.3k`, so the totals are **approximate** too. Tasks with unknown cost and tasks without usage are counted separately. Claude edition and Codex edition lines can be mixed.

## Known limits

- Only logs from Copilot CLI **1.0.98 or later** (`session.start` · `session.usage_record`) are read. Older versions and logs with an unknown version are `no record`.
- Whether the usage of subagents like the checking helper (verifier) is recorded in the same session log hasn't been checked yet. If it's recorded separately, that much is missing from the usage line.
- Sending to Langfuse isn't in the first Copilot edition.
