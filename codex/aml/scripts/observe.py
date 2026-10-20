#!/usr/bin/env python3
"""observe.py — aml (Codex edition) measuring script. Uses only the Python standard library.

  task-start --label L          task start: stamps the start time and saves the current session's cumulative usage in .aml/
  task-done  --since T --label L [--feature F] [--note N]
                                task end: prints the current session's span usage as one "Usage: …" line
  summary    <progress.md>      adds up the usage lines in progress.md (Claude/Codex lines may be mixed)
  check                         says in one line whether the current session's usage can be read (for $aml:doctor)

Rules (references/telemetry.md):
  - The session is picked only by the CODEX_THREAD_ID Codex passes (or --session). Never another session in the same folder.
  - Span usage = cumulative at the end − cumulative at the start. If the start value is unknown, don't use the whole-session value; 'no record'.
  - Input tokens include cache reads, and output tokens include reasoning tokens — don't add them again.
  - Cost is calculated only for models with confirmed prices. The rest are 'cost unknown' (never counted as 0).
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
          "output_tokens", "reasoning_output_tokens", "total_tokens")

# Price per model (USD / million tokens): (input, cached input, output).
# Only add models whose source and check date are written in references/telemetry.md. No prices are confirmed yet.
PRICING: dict[str, tuple[float, float, float]] = {}

START_FILE = Path(".aml") / "codex-measure-start.json"

# The lowest Codex version whose token-number relations were checked against real logs (references/telemetry.md).
# Older logs (0.136 and below) meant different things, e.g. reasoning tokens sat outside the output.
MIN_VERSION = (0, 144, 0)


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


# ── Find the session ──────────────────────────────────────────────────────

def sessions_dir() -> Path:
    home = os.environ.get("CODEX_HOME") or str(Path.home() / ".codex")
    return Path(home) / "sessions"


def current_session_id(explicit: str | None = None) -> str:
    sid = explicit or os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID")
    if not sid:
        raise NoRecord("the current session id is unknown")
    return sid.strip()


def find_session_file(sid: str) -> Path:
    root = sessions_dir()
    if not root.is_dir():
        raise NoRecord("there is no Codex session log folder")
    hits = sorted(root.rglob(f"rollout-*{sid}.jsonl"))
    if len(hits) != 1:
        raise NoRecord("couldn't find the current session's log file" if not hits
                       else "there are several log files with the same session id")
    return hits[0]


def version_tuple(v) -> tuple[int, ...] | None:
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)", v or "")
    return tuple(int(x) for x in m.groups()) if m else None


def consistent(u: dict) -> bool:
    """input ⊇ cache read, output ⊇ reasoning, total = input + output — only calculate when these hold."""
    return (u["cached_input_tokens"] <= u["input_tokens"]
            and u["reasoning_output_tokens"] <= u["output_tokens"]
            and u["total_tokens"] == u["input_tokens"] + u["output_tokens"])


def read_events(path: Path, sid: str) -> list[tuple[datetime, str, dict]]:
    """Returns a list of (time, model, cumulative usage) from the session file, in time order."""
    events: list[tuple[datetime, str, dict]] = []
    meta_ok = False
    version = None
    model = "?"
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            kind = obj.get("type")
            body = obj.get("payload") or {}
            if not isinstance(body, dict):
                continue
            if kind == "session_meta":
                meta_ok = (body.get("id") or body.get("session_id")) == sid
                version = version_tuple(body.get("cli_version"))
            elif kind == "turn_context":
                model = body.get("model") or "?"
            elif kind == "event_msg" and body.get("type") == "token_count":
                info = body.get("info") or {}
                tot = info.get("total_token_usage")
                ts = parse_ts(obj.get("timestamp"))
                if not isinstance(tot, dict) or ts is None:
                    continue
                try:
                    usage = {k: int(tot.get(k) or 0) for k in FIELDS}
                except (TypeError, ValueError):
                    continue
                events.append((ts, model, usage))
    if not meta_ok:
        raise NoRecord("the session log format is unknown")
    if version is None or version < MIN_VERSION:
        raise NoRecord("the log is from an unchecked Codex version")
    return events


# ── Span usage ────────────────────────────────────────────────────────────

def interval_usage(events, since: datetime, end: datetime,
                   baseline: dict | None = None) -> dict[str, dict]:
    """Adds up, per model, how much grew from the cumulative value just before since (or baseline) until end.

    The same cumulative value recorded again (a duplicate) passes as 0, and if the cumulative value
    goes down, the counter is treated as having started over and the new value is added as is."""
    prev = None
    for ts, _model, usage in events:
        if ts <= since:
            prev = usage
    if prev is None:
        prev = baseline
    if prev is None:
        raise NoRecord("there is no cumulative value at the span start")
    if not consistent(prev):
        raise NoRecord("the token numbers don't relate as expected")
    per: dict[str, dict] = {}
    for ts, model, usage in events:
        if ts <= since or ts > end:
            continue
        if not consistent(usage):
            raise NoRecord("the token numbers don't relate as expected")
        if usage["total_tokens"] < prev["total_tokens"]:
            inc = dict(usage)                      # cumulative reset — counting again from 0
        else:
            inc = {k: max(0, usage[k] - prev[k]) for k in FIELDS}
        prev = usage
        if not inc["total_tokens"]:
            continue                               # duplicate event
        tot = per.setdefault(model, {k: 0 for k in FIELDS})
        for k in FIELDS:
            tot[k] += inc[k]
    return per


def cost_usd(model: str, tok: dict, pricing: dict | None = None) -> float | None:
    """Only for models with known prices. input = uncached input + cache read (the cache is inside the input)."""
    table = PRICING if pricing is None else pricing
    price = table.get(model.strip().lower())
    if price is None or tok.get("cache_write_input_tokens"):
        return None                                # the cache write price hasn't been confirmed
    inp, cached, out = price
    fresh = max(0, tok["input_tokens"] - tok["cached_input_tokens"])
    return (fresh / 1e6 * inp + tok["cached_input_tokens"] / 1e6 * cached
            + tok["output_tokens"] / 1e6 * out)


def measure_line(dur_secs: int, per: dict[str, dict], pricing: dict | None = None) -> str:
    """Same shape as the Claude edition's usage line. 'in' is uncached input, 'cache read' is separate."""
    if not per:
        return f"Usage: {humanize_dur(dur_secs)} · no token record"
    items = sorted(per.items())
    costs = [cost_usd(m, t, pricing) for m, t in items]

    def fresh(t):
        return max(0, t["input_tokens"] - t["cached_input_tokens"])

    if len(items) == 1:
        m, t = items[0]
        line = (f"Usage: {m} · {humanize_dur(dur_secs)}"
                f" · tokens in {humanize(fresh(t))} / out {humanize(t['output_tokens'])}"
                f" (cache read {humanize(t['cached_input_tokens'])})")
    else:
        parts = [f"{m}(in {humanize(fresh(t))}/out {humanize(t['output_tokens'])})"
                 for m, t in items]
        line = f"Usage: {humanize_dur(dur_secs)} · " + " + ".join(parts)
    known = [c for c in costs if c is not None]
    if known and len(known) == len(costs):
        line += f" · est. cost {fmt_usd(sum(known))}"
    elif known:
        line += f" · est. cost {fmt_usd(sum(known))} (some cost unknown)"
    else:
        line += " · cost unknown"
    return line


# ── Progress log summary (adds up the usage lines in progress.md) ──────────────

# The time is one whole " · " piece: "1h 3m", "4m 49s" or "37s" (see humanize_dur)
_DUR = re.compile(r"(?:(\d+)h (\d+)m|(\d+)m (\d+)s|(\d+)s)")
_COST = re.compile(r"est\. cost\s*\$([0-9]+(?:\.[0-9]+)?)")
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
    cost = 0.0
    have_cost = False
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
    if no_cost:
        out += f"\nTasks with cost unknown: {no_cost} (models whose price couldn't be confirmed — not counted as 0)"
    if untracked:
        out += f"\nTasks without usage: {untracked}"
    return out


# ── Commands ──────────────────────────────────────────────────────────────

def cmd_task_start(args) -> None:
    start = now_utc().astimezone()
    print(f"Start: {start.isoformat(timespec='seconds')}")
    try:
        sid = current_session_id(args.session)
        events = read_events(find_session_file(sid), sid)
    except (NoRecord, OSError) as exc:
        print(f"Measuring setup: skipped ({exc})", file=sys.stderr)
        return
    snap = {"label": args.label, "session": sid, "since": start.isoformat(),
            "usage": events[-1][2] if events else None}
    try:
        START_FILE.parent.mkdir(parents=True, exist_ok=True)
        START_FILE.write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        print(f"Measuring setup: couldn't save the start value ({exc})", file=sys.stderr)


def load_baseline(label: str, sid: str) -> dict | None:
    try:
        snap = json.loads(START_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if snap.get("label") != label or snap.get("session") != sid:
        return None
    usage = snap.get("usage")
    return usage if isinstance(usage, dict) and all(k in usage for k in FIELDS) else None


def task_done_line(since_s: str, label: str, session: str | None = None,
                   end: datetime | None = None) -> str:
    since = parse_ts(since_s)
    if since is None:
        return "Usage: no record (couldn't read the --since time)"
    end = end or now_utc()
    dur = max(0, int((end - since).total_seconds()))
    try:
        sid = current_session_id(session)
        events = read_events(find_session_file(sid), sid)
        per = interval_usage(events, since, end, load_baseline(label, sid))
    except NoRecord as exc:
        return f"Usage: no record ({exc})"
    except OSError as exc:
        return f"Usage: no record (couldn't read the session log: {exc.__class__.__name__})"
    return measure_line(dur, per)


def cmd_task_done(args) -> None:
    print(task_done_line(args.since, args.label, args.session))
    try:
        START_FILE.unlink()
    except OSError:
        pass


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
    print("Usage: the current session's usage can be read (cost is calculated only for models with confirmed prices)")


def main() -> None:
    ap = argparse.ArgumentParser(prog="observe.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ts = sub.add_parser("task-start", help="task start — save the start time and starting cumulative value")
    ts.add_argument("--label", default="task")
    ts.add_argument("--session")
    td = sub.add_parser("task-done", help="task end — print the usage line")
    td.add_argument("--since", required=True)
    td.add_argument("--label", default="task")
    td.add_argument("--feature")
    td.add_argument("--note")
    td.add_argument("--session")
    sm = sub.add_parser("summary", help="add up the usage lines in progress.md (for $aml:status)")
    sm.add_argument("path")
    ck = sub.add_parser("check", help="whether usage can be read (for $aml:doctor)")
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
