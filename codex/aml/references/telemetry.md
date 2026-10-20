# Measuring — how the Codex edition's usage line is made

$aml:go leaves one usage line in `progress.md` per task. The numbers come from `scripts/observe.py` reading Codex's session logs. Measuring **never blocks the work** — whenever anything is uncertain, it doesn't make numbers up and leaves `Usage: no record (reason)` instead.

```text
Usage: gpt-6-astra · 4m 12s · tokens in 12.3k / out 2.1k (cache read 85.0k) · cost unknown
```

## How to call it

```bash
python3 "<package>/scripts/observe.py" task-start --label "1.2 add-card dialog"
#  → Start: 2026-10-17T06:00:00+10:00      (use this time as --since below)
python3 "<package>/scripts/observe.py" task-done --since 2026-10-17T06:00:00+10:00 --label "1.2 add-card dialog"
python3 "<package>/scripts/observe.py" summary progress.md     # $aml:status
python3 "<package>/scripts/observe.py" check                   # $aml:doctor
```

## Which session it reads

- It picks **only the current session** by the session id Codex passes when running a command (`CODEX_THREAD_ID`, or `CODEX_SESSION_ID` if that's missing). You can also give it directly with `--session <id>`.
- The log file is `rollout-*-<session id>.jsonl` under `$CODEX_HOME/sessions/` (default `~/.codex/sessions/`). It's read only if the id in the file's `session_meta` matches.
- If the session id is unknown, it **doesn't pick some other session opened in the same folder (cwd) instead.** That would mix in other work from the same project. In that case it's `no record`.

## How the span is cut

- The log file's `token_count` events hold the **cumulative** usage since the session started (`total_token_usage`).
- Span usage = (cumulative at the end) − (cumulative just before the start time). Only events after the start time and before now are counted.
- If there's no event just before the start time, it uses the start value `task-start` saved in `.aml/codex-measure-start.json` (only for the same task name and the same session). If neither exists, it **doesn't use the whole-session value instead**; it's `no record`.
- An event that records the same cumulative value twice (a duplicate) adds 0, so it isn't counted.
- If the cumulative value goes down, the counter is treated as having started over, and the new cumulative value is added as is (never subtracted as a negative).
- If a new session was opened partway through a task (the session changed), the earlier session's usage isn't stitched on — the start value can't be found, so it's `no record`.
- The model is taken from the `turn_context.model` just before each event. If the model changes within the span, it's written per model.

## How the token numbers relate (never count twice)

The numbers in Codex's logs contain one another. Checked on 2026-10-17 against real logs on this computer — all of about 19,500 events from codex-cli 0.144.1 to 0.163.0 kept the relations below, while logs from 0.133.0 to 0.136.0 mostly didn't (reasoning tokens were outside the output).

| Name in the log | Meaning | Relation |
|---|---|---|
| `input_tokens` | All input | **includes** cache reads |
| `cached_input_tokens` | Input read from cache, out of that | at most `input_tokens` |
| `output_tokens` | All output | **includes** reasoning tokens |
| `reasoning_output_tokens` | Reasoning, out of that | at most `output_tokens` |
| `total_tokens` | Everything | equals `input_tokens + output_tokens` |

In the usage line, **"in" is uncached input** (`input_tokens − cached_input_tokens`), and **"cache read" is written separately**. This matches the meaning of the Claude edition's usage line, so when both tools' lines are mixed, the summary adds like with like. Reasoning tokens are already inside the output, so they aren't added again.

## Cost

Cost is calculated **only for models whose prices and token meanings have been confirmed**.

Formula: `(uncached input × input price) + (cache read × cached input price) + (output × output price)`, prices in dollars per million tokens. If there are cache write tokens (`cache_write_input_tokens`) and their price hasn't been confirmed, that model isn't calculated.

| Model | Input | Cached input | Output | Source | Checked on |
|---|---|---|---|---|---|
| (none yet) | | | | | |

There are no confirmed prices yet, so all of the Codex edition's usage lines say `cost unknown`. On a subscription plan, tokens may not cost money one by one anyway. When adding prices, confirm them from the official price list and change this table and `PRICING` in `observe.py` together. The cost of an unknown model is **never written as 0** — 0 reads as "free".

## Summary ($aml:status)

`summary` reads all the usage lines in `progress.md` and shows the number of tasks · total time taken · tokens (approx.) · total known cost. Tokens in the usage lines are rounded like `12.3k`, so the totals are **approximate** too. Tasks with unknown cost and tasks without usage are counted separately. Claude edition and Codex edition lines can be mixed.

## Supported format

Only session logs from codex-cli **0.144.0 or later** (`session_meta` · `turn_context` · `event_msg/token_count`) are read. Older versions, logs with an unknown version, logs without `session_meta`, and logs where even one number in the span breaks the relations in the table above are not guessed at; they're `no record`. Sending to Langfuse isn't in the first Codex edition.
