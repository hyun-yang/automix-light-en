#!/usr/bin/env python3
"""observe.py — aml (Copilot CLI edition) measuring script. Uses only the Python standard library.

  task-start --label L          task start: stamps the start time
  task-done  --since T --label L [--feature F] [--note N]
                                task end: prints the current session's span usage as one "Usage: …" line
  summary    <progress.md>      adds up the usage lines in progress.md (Claude/Codex/Copilot lines may be mixed)
  check                         says in one line whether the current session's usage can be read (for /aml:doctor)

Rules (references/telemetry.md):
  - The session is picked only by the COPILOT_AGENT_SESSION_ID Copilot passes to the shell (or --session). Never another session in the same folder.
  - Every time Copilot calls a model it leaves that one call's usage as session.usage_record — span usage is the sum of those records.
  - input tokens = uncached input + cache read + cache write. If this doesn't hold, don't guess; 'no record'.
  - Dollar cost is calculated only for models with confirmed prices. The rest are 'cost unknown' (never counted as 0).
    AI credits that Copilot recorded itself are written separately, not mixed with dollars.
Measuring must never block the build — exit code 0 no matter what (only argparse usage errors exit with 2).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

FIELDS = ("input_tokens", "cached_input_tokens", "cache_write_input_tokens",
          "output_tokens", "reasoning_output_tokens")

# Price per model (USD / million tokens): (input, cached input, output).
# Only add models whose source and check date are written in references/telemetry.md. No prices are confirmed yet.
PRICING: dict[str, tuple[float, float, float]] = {}

# The lowest Copilot CLI version whose token-number relations were checked against real logs (references/telemetry.md).
MIN_VERSION = (1, 0, 98)

NANO = 1_000_000_000   # turns totalNanoAiu into AI credits (same as "AI Credits" on Copilot's screen)


class NoRecord(Exception):
    """Can't measure — the message goes inside the brackets of 'Usage: no record (…)'."""


# ── Time / formatting ─────────────────────────────────────────────────────

def parse_ts(ts) -> datetime | None:
    if not isinstance(ts, str) or not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def humanize(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def humanize_dur(secs: int) -> str:
    h, rem = divmod(max(0, secs), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def fmt_usd(c: float) -> str:
    return f"${c:.4f}" if c < 0.01 else f"${c:.2f}"


def fmt_credit(c: float) -> str:
    return f"{c:.4f}" if c < 0.01 else f"{c:.2f}"


# ── Find the session ──────────────────────────────────────────────────────

def sessions_dir() -> Path:
    home = os.environ.get("COPILOT_HOME") or str(Path.home() / ".copilot")
    return Path(home) / "session-state"


def current_session_id(explicit: str | None = None) -> str:
    sid = explicit or os.environ.get("COPILOT_AGENT_SESSION_ID")
    if not sid:
        raise NoRecord("the current session id is unknown")
    return sid.strip()


def find_session_file(sid: str) -> Path:
    root = sessions_dir()
    if not root.is_dir():
        raise NoRecord("there is no Copilot session log folder")
    path = root / sid / "events.jsonl"
    if "/" in sid or not path.is_file():
        raise NoRecord("couldn't find the current session's log file")
    return path


def version_tuple(v) -> tuple[int, ...] | None:
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)", v or "")
    return tuple(int(x) for x in m.groups()) if m else None


def to_usage(u: dict) -> dict:
    """Turns one usage_record line into numbers for measuring. NoRecord if the numbers don't relate."""
    try:
        inp = int(u["inputTokens"])
        out = int(u["outputTokens"])
        cr = int(u.get("cacheReadTokens") or 0)
        cw = int(u.get("cacheWriteTokens") or 0)
        rs = int(u.get("reasoningTokens") or 0)
    except (KeyError, TypeError, ValueError):
        raise NoRecord("the token numbers don't relate as expected")
    fresh = inp - cr - cw
    details = {}
    for d in (u.get("copilotUsage") or {}).get("tokenDetails") or []:
        if isinstance(d, dict):
            details[d.get("tokenType")] = d.get("tokenCount")
    if (min(inp, out, cr, cw, rs) < 0 or fresh < 0 or rs > out
            or ("input" in details and details["input"] != fresh)):
        raise NoRecord("the token numbers don't relate as expected")
    return {"input_tokens": fresh, "cached_input_tokens": cr, "cache_write_input_tokens": cw,
            "output_tokens": out, "reasoning_output_tokens": rs}


def read_events(path: Path, sid: str):
    """Returns (session start time, [(time, model, dedupe key, raw usage)]) from the session file."""
    start = None
    meta_ok = False
    version = None
    records = []
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            kind = obj.get("type")
            data = obj.get("data") or {}
            if not isinstance(data, dict):
                continue
            if kind == "session.start":
                meta_ok = data.get("sessionId") == sid
                version = version_tuple(data.get("copilotVersion"))
                start = parse_ts(data.get("startTime"))
            elif kind == "session.usage_record":
                u = data.get("usage")
                ts = parse_ts(obj.get("timestamp"))
                if not isinstance(u, dict) or ts is None:
                    continue
                key = (u.get("accounting") or {}).get("usageId") or obj.get("id")
                records.append((ts, u.get("model") or "?", key, u))
    if not meta_ok:
        raise NoRecord("the session log format is unknown")
    if version is None or version < MIN_VERSION:
        raise NoRecord("the log is from an unchecked Copilot CLI version")
    return start, records


# ── Span usage ────────────────────────────────────────────────────────────

def interval_usage(start, records, since: datetime, end: datetime) -> dict[str, dict]:
    """Adds up the usage_records after since until end, per model. The same record appearing twice is counted once.

    If the session started partway through the task, the earlier session's usage can't be known, so 'no record'."""
    if start is None or start > since:
        raise NoRecord("the session changed partway through the task")
    per: dict[str, dict] = {}
    seen = set()
    for ts, model, key, raw in records:
        if ts <= since or ts > end:
            continue
        if key is not None:
            if key in seen:
                continue                           # duplicate record
            seen.add(key)
        u = to_usage(raw)
        tot = per.setdefault(model, dict({k: 0 for k in FIELDS}, nano_aiu=0))
        for k in FIELDS:
            tot[k] += u[k]
        nano = (raw.get("copilotUsage") or {}).get("totalNanoAiu")
        if isinstance(nano, (int, float)) and tot["nano_aiu"] is not None:
            tot["nano_aiu"] += nano
        else:
            tot["nano_aiu"] = None                 # if even one is unknown, don't write that model's credits
    return per


def cost_usd(model: str, tok: dict, pricing: dict | None = None) -> float | None:
    """Only for models with known prices. 'in' is already uncached input."""
    table = PRICING if pricing is None else pricing
    price = table.get(model.strip().lower())
    if price is None or tok.get("cache_write_input_tokens"):
        return None                                # the cache write price hasn't been confirmed
    inp, cached, out = price
    return (tok["input_tokens"] / 1e6 * inp + tok["cached_input_tokens"] / 1e6 * cached
            + tok["output_tokens"] / 1e6 * out)


def measure_line(dur_secs: int, per: dict[str, dict], pricing: dict | None = None) -> str:
    """Same shape as the Claude edition's usage line. 'in' is uncached input, 'cache read / write' are separate."""
    if not per:
        return f"Usage: {humanize_dur(dur_secs)} · no token record"
    items = sorted(per.items())
    costs = [cost_usd(m, t, pricing) for m, t in items]
    if len(items) == 1:
        m, t = items[0]
        line = (f"Usage: {m} · {humanize_dur(dur_secs)}"
                f" · tokens in {humanize(t['input_tokens'])} / out {humanize(t['output_tokens'])}"
                f" (cache read {humanize(t['cached_input_tokens'])}"
                f" / write {humanize(t['cache_write_input_tokens'])})")
    else:
        parts = [f"{m}(in {humanize(t['input_tokens'])}/out {humanize(t['output_tokens'])})"
                 for m, t in items]
        line = f"Usage: {humanize_dur(dur_secs)} · " + " + ".join(parts)
    known = [c for c in costs if c is not None]
    if known and len(known) == len(costs):
        line += f" · est. cost {fmt_usd(sum(known))}"
    elif known:
        line += f" · est. cost {fmt_usd(sum(known))} (some cost unknown)"
    else:
        line += " · cost unknown"
    nanos = [t["nano_aiu"] for _m, t in items]
    if all(n is not None for n in nanos):
        line += f" · AI credits {fmt_credit(sum(nanos) / NANO)}"
    return line


# ── Progress log summary (adds up the usage lines in progress.md) ──────────────

# The time is one whole " · " piece: "1h 3m", "4m 49s" or "37s" (see humanize_dur)
_DUR = re.compile(r"(?:(\d+)h (\d+)m|(\d+)m (\d+)s|(\d+)s)")
_COST = re.compile(r"est\. cost\s*\$([0-9]+(?:\.[0-9]+)?)")
_CREDIT = re.compile(r"AI credits\s*([0-9]+(?:\.[0-9]+)?)")
_TOK_IN = re.compile(r"\bin\s*([0-9]+(?:\.[0-9]+)?)([kM]?)")
_TOK_OUT = re.compile(r"\bout\s*([0-9]+(?:\.[0-9]+)?)([kM]?)")
_MODEL_MULTI = re.compile(r"([A-Za-z][A-Za-z0-9._-]*)\(in ")
_MODEL_ONE = re.compile(r"^([A-Za-z][A-Za-z0-9._-]*)\s+·")


def unhumanize(num: str, unit: str) -> int:
    v = float(num)
    if unit == "k":
        v *= 1_000
    elif unit == "M":
        v *= 1_000_000
    return int(round(v))


def summarize_progress(text: str) -> str:
    tasks = untracked = no_cost = secs = tok_in = tok_out = 0
    cost = credit = 0.0
    have_cost = have_credit = False
    models: dict[str, int] = {}
    for raw in text.splitlines():
        at = raw.find("Usage:")
        if at < 0:
            continue
        line = raw[at + len("Usage:"):].strip()
        if line.startswith("no record"):
            tasks += 1
            untracked += 1
            continue
        dur = next((m for m in (_DUR.fullmatch(p.strip()) for p in line.split(" · ")) if m), None)
        if dur is None:
            continue  # no time taken means it isn't a real usage line (template notes, etc.)
        tasks += 1
        h, hm, m_, ms, s_ = (int(g) if g else 0 for g in dur.groups())
        secs += h * 3600 + hm * 60 + m_ * 60 + ms + s_
        m = _COST.search(line)
        if m:
            cost += float(m.group(1))
            have_cost = True
        m = _CREDIT.search(line)
        if m:
            credit += float(m.group(1))
            have_credit = True
        if "cost unknown" in line:
            no_cost += 1
        for num, unit in _TOK_IN.findall(line):
            tok_in += unhumanize(num, unit)
        for num, unit in _TOK_OUT.findall(line):
            tok_out += unhumanize(num, unit)
        found = _MODEL_MULTI.findall(line)
        if not found:
            one = _MODEL_ONE.match(line)
            found = [one.group(1)] if one else []
        for name in found:
            models[name] = models.get(name, 0) + 1
    if tasks == 0:
        return "Summary: no usage lines yet"
    parts = [f"Summary: {tasks} task{'s' if tasks != 1 else ''}", f"total {humanize_dur(secs)}"]
    if tok_in or tok_out:
        parts.append(f"tokens approx. in {humanize(tok_in)} / out {humanize(tok_out)}")
    if have_cost:
        parts.append(f"known cost total {fmt_usd(cost)}")
    out = " · ".join(parts)
    if models:
        ranked = sorted(models.items(), key=lambda kv: (-kv[1], kv[0]))
        out += "\nModels: " + " · ".join(f"{m} ×{n}" for m, n in ranked)
    if have_credit:
        out += f"\nAI credits total: {fmt_credit(credit)} (usage Copilot recorded — counted separately from dollar cost)"
    if no_cost:
        out += f"\nTasks with cost unknown: {no_cost} (models whose price couldn't be confirmed — not counted as 0)"
    if untracked:
        out += f"\nTasks without usage: {untracked}"
    return out


# ── Commands ──────────────────────────────────────────────────────────────

def task_done_line(since_s: str, session: str | None = None, end: datetime | None = None) -> str:
    since = parse_ts(since_s)
    if since is None:
        return "Usage: no record (couldn't read the --since time)"
    end = end or now_utc()
    dur = max(0, int((end - since).total_seconds()))
    try:
        sid = current_session_id(session)
        start, records = read_events(find_session_file(sid), sid)
        per = interval_usage(start, records, since, end)
    except NoRecord as exc:
        return f"Usage: no record ({exc})"
    except OSError as exc:
        return f"Usage: no record (couldn't read the session log: {exc.__class__.__name__})"
    return measure_line(dur, per)


def cmd_task_start(args) -> None:
    print(f"Start: {now_utc().astimezone().isoformat(timespec='seconds')}")
    try:
        sid = current_session_id(args.session)
        read_events(find_session_file(sid), sid)
    except (NoRecord, OSError) as exc:
        print(f"Measuring setup: usage can't be read, so 'no record' will be left at the end ({exc})", file=sys.stderr)


def cmd_task_done(args) -> None:
    print(task_done_line(args.since, args.session))


def cmd_summary(args) -> None:
    path = Path(args.path)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        print(f"Summary: couldn't read {path}")
        return
    print(summarize_progress(text))


def cmd_check(args) -> None:
    try:
        sid = current_session_id(args.session)
        read_events(find_session_file(sid), sid)
    except (NoRecord, OSError) as exc:
        print(f"Usage: usage can't be read right now, so it will be left as 'Usage: no record' ({exc}). The work carries on as normal")
        return
    print("Usage: the current session's usage can be read (dollar cost only for models with confirmed prices; AI credits as Copilot recorded them)")


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="observe.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ts = sub.add_parser("task-start", help="task start — print the start time")
    ts.add_argument("--label", default="task")
    ts.add_argument("--session")
    td = sub.add_parser("task-done", help="task end — print the usage line")
    td.add_argument("--since", required=True)
    td.add_argument("--label", default="task")
    td.add_argument("--feature")
    td.add_argument("--note")
    td.add_argument("--session")
    sm = sub.add_parser("summary", help="add up the usage lines in progress.md (for /aml:status)")
    sm.add_argument("path")
    ck = sub.add_parser("check", help="whether usage can be read (for /aml:doctor)")
    ck.add_argument("--session")
    args = ap.parse_args()
    handler = {"task-start": cmd_task_start, "task-done": cmd_task_done,
               "summary": cmd_summary, "check": cmd_check}[args.cmd]
    try:
        handler(args)
    except Exception as exc:  # noqa: BLE001 — measuring never blocks the work, no matter what
        if args.cmd == "task-done":
            print(f"Usage: no record ({exc.__class__.__name__})")
        else:
            print(f"Measuring script error: {exc.__class__.__name__}", file=sys.stderr)


if __name__ == "__main__":
    main()
