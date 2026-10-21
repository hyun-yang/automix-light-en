#!/usr/bin/env python3
"""observe.py — automix-light's only script (observation only, standard library only).

When a task is done, /aml:go calls it like this:
  observe.py task-done --since <ISO8601> --label "<task>" \
      [--feature "<feature name>"] [--note "<check result>"] [--dry-run]
→ Adds up per-model token usage for the span (start → now) from the session logs
  (~/.claude/projects/<encoded cwd>/*.jsonl) and prints the one "Usage: …" line for progress.md to stdout.
→ If langfuse in .aml/config.yaml is "on", it also sends the same data to Langfuse
  (keys are read from environment variables only).

Fixed rule: fully fail-open — any failure while running leaves just one warning line and exit code 0.
Observation must never block the build. (Only argparse usage errors exit with 2.)
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USAGE_FIELDS = ("input_tokens", "output_tokens",
                "cache_creation_input_tokens", "cache_read_input_tokens")

DEFAULT_HOST = "https://cloud.langfuse.com"

# Price per model family (USD/MTok, input/output) — same table as am's pricing.py.
PRICING = {"opus": (5.0, 25.0), "fable": (10.0, 50.0),
           "sonnet": (3.0, 15.0), "haiku": (1.0, 5.0)}
CACHE_WRITE_MULT = 1.25   # cache write ≈ 1.25× the input price
CACHE_READ_MULT = 0.10    # cache read ≈ 0.1× the input price


# ── Time / formatting helpers ─────────────────────────────────────────────────

def parse_ts(ts) -> datetime | None:
    if not ts:
        return None
    s = str(ts).strip().replace("Z", "+00:00")
    s = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", s)   # BSD date's +1000 → +10:00
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return (dt.astimezone(timezone.utc)
            .isoformat(timespec="milliseconds").replace("+00:00", "Z"))


def humanize(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1e6:.1f}M"
    if n >= 10_000:
        return f"{round(n / 1000)}k"
    if n >= 1_000:
        return f"{n / 1000:.1f}k"
    return str(n)


def humanize_dur(secs: int) -> str:
    if secs >= 3600:
        return f"{secs // 3600}h {secs % 3600 // 60}m"
    if secs >= 60:
        return f"{secs // 60}m {secs % 60}s"
    return f"{secs}s"


# ── Find session logs + add up (a trimmed copy of am's task-metrics.py) ────────────

def projects_root() -> Path:
    return Path(os.environ.get("AML_CLAUDE_PROJECTS_DIR")
                or os.path.expanduser("~/.claude/projects"))


def _dir_cwd(d: Path) -> str | None:
    """The realpath cwd written in this log folder (None if there is none)."""
    for f in sorted(d.glob("*.jsonl")):
        try:
            with f.open(encoding="utf-8") as fh:
                for i, line in enumerate(fh):
                    if i > 20:
                        break
                    if '"cwd"' not in line:
                        continue
                    try:
                        c = json.loads(line).get("cwd")
                    except Exception:
                        continue
                    if c:
                        return os.path.realpath(c)
        except OSError:
            continue
    return None


def transcript_dir() -> Path | None:
    """The log folder for the current cwd. The encoding (`[^A-Za-z0-9] → -`) loses information,
    so check against the cwd written in the folder, and if it doesn't match or is missing, scan all folders."""
    root = projects_root()
    if not root.is_dir():
        return None
    cwd = os.path.realpath(os.getcwd())
    enc = re.sub(r"[^A-Za-z0-9]", "-", cwd)
    cand = root / enc
    if cand.is_dir():
        dc = _dir_cwd(cand)
        if dc is None or dc == cwd:
            return cand
    for d in sorted(root.iterdir()):
        if not d.is_dir() or d == cand:
            continue
        if _dir_cwd(d) == cwd:
            return d
    return None


def sum_by_model(start: datetime, end: datetime) -> dict[str, dict] | None:
    """Adds up assistant usage within the span [start, end] per model.
    None if no logs are found (the usage line comes out as 'Usage: no record')."""
    d = transcript_dir()
    if d is None:
        return None
    per: dict[str, dict] = {}
    start_epoch = start.timestamp()
    for f in d.rglob("*.jsonl"):
        try:
            if f.stat().st_mtime < start_epoch - 2:   # skip files that ended before the span
                continue
            fh = f.open(encoding="utf-8")
        except OSError:
            continue
        with fh:
            for line in fh:
                if '"usage"' not in line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("type") != "assistant":
                    continue
                ts = parse_ts(rec.get("timestamp"))
                if ts is not None and ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts is None or ts < start or ts > end:
                    continue
                msg = rec.get("message") or {}
                usage = msg.get("usage") or {}
                model = msg.get("model") or "?"   # records without a model go under "?" (left out of the cost)
                tot = per.setdefault(model, {k: 0 for k in USAGE_FIELDS})
                for k in USAGE_FIELDS:
                    tot[k] += usage.get(k, 0) or 0
    return per


# ── Cost ────────────────────────────────────────────────────────────────────

def cost_usd(model: str, tok: dict) -> float | None:
    m = model.strip().lower()
    price = next((p for key, p in PRICING.items() if key == m or key in m), None)
    if price is None:
        return None
    inp, out = price
    return (tok["input_tokens"] / 1e6 * inp
            + tok["output_tokens"] / 1e6 * out
            + tok["cache_creation_input_tokens"] / 1e6 * inp * CACHE_WRITE_MULT
            + tok["cache_read_input_tokens"] / 1e6 * inp * CACHE_READ_MULT)


def fmt_usd(c: float) -> str:
    return f"${c:.4f}" if c < 0.01 else f"${c:.2f}"


# ── Build the usage line ────────────────────────────────────────────────────

def measure_line(dur_secs: int, per: dict[str, dict] | None) -> str:
    if per is None:
        return "Usage: no record (couldn't find the session logs)"
    if not per:
        return f"Usage: {humanize_dur(dur_secs)} · no token record"
    items = sorted(per.items())
    costs = [cost_usd(m, t) for m, t in items]
    known = [c for c in costs if c is not None]
    total = sum(known) if known else None
    if len(items) == 1:
        m, t = items[0]
        line = (f"Usage: {m} · {humanize_dur(dur_secs)}"
                f" · tokens in {humanize(t['input_tokens'])} / out {humanize(t['output_tokens'])}"
                f" (cache read {humanize(t['cache_read_input_tokens'])}"
                f" / write {humanize(t['cache_creation_input_tokens'])})")
    else:
        parts = [f"{m}(in {humanize(t['input_tokens'])}/out {humanize(t['output_tokens'])})"
                 for m, t in items]
        line = f"Usage: {humanize_dur(dur_secs)} · " + " + ".join(parts)
    if total is not None:
        line += f" · est. cost {fmt_usd(total)}"
    return line


# ── Langfuse (optional, off by default — off if there is no .aml/config.yaml) ─────

def config_get(key: str) -> str | None:
    """Reads a key from .aml/config.yaml by the first matching line (am's get_config way).
    The file is documented as two flat keys (langfuse/langfuse_host),
    and even with nesting or duplicates, the first line found in the file wins."""
    p = Path(".aml/config.yaml")
    if not p.is_file():
        return None
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            m = re.match(rf'\s*{key}:\s*["\']?([^"\'#\n]*)', line)
            if m:
                return m.group(1).strip() or None
    except (OSError, UnicodeDecodeError):
        return None
    return None


def langfuse_on() -> bool:
    return (config_get("langfuse") or "off").lower() == "on"


def resolve_creds() -> tuple[str | None, str | None, str]:
    public = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret = os.environ.get("LANGFUSE_SECRET_KEY")
    host = (os.environ.get("LANGFUSE_HOST") or config_get("langfuse_host")
            or DEFAULT_HOST).rstrip("/")
    return public, secret, host


def slug(s: str) -> str:
    s = re.sub(r"[^0-9a-z]+", "-", s.lower()).strip("-")
    return s or "task"


def build_batch(label: str, feature: str | None, note: str | None,
                since: datetime, end: datetime, dur_secs: int,
                per: dict[str, dict] | None) -> list[dict]:
    """One task → a Langfuse ingestion batch. The id is made deterministically from label+since."""
    tid = f"aml-{slug(label)}-{re.sub(r'[^0-9]', '', iso(since))[:14]}"
    items = sorted((per or {}).items())
    summary: dict = {"duration_sec": dur_secs, "models": dict(items)}
    known = [c for c in (cost_usd(m, t) for m, t in items) if c is not None]
    if known:
        summary["est_cost_usd"] = round(sum(known), 4)
    if note:
        summary["verify"] = note
    batch: list[dict] = []

    def envelope(etype: str, body: dict) -> None:
        batch.append({"id": f"{body['id']}-{etype}", "type": etype,
                      "timestamp": iso(end), "body": body})

    envelope("trace-create", {
        "id": tid, "name": f"aml:{label}",
        "sessionId": feature or Path.cwd().name,
        "timestamp": iso(since), "tags": ["aml"],
        "metadata": {"label": label, "cwd": Path.cwd().name},
        "input": label, "output": summary})
    for i, (m, t) in enumerate(items):
        envelope("generation-create", {
            "id": f"{tid}-gen{i}", "traceId": tid, "name": "task",
            "startTime": iso(since), "endTime": iso(end), "model": m,
            "usageDetails": {
                "input": t["input_tokens"], "output": t["output_tokens"],
                "cache_creation_input_tokens": t["cache_creation_input_tokens"],
                "cache_read_input_tokens": t["cache_read_input_tokens"]},
            "output": summary})
    if note:
        envelope("event-create", {
            "id": f"{tid}-verify", "traceId": tid, "name": "verify",
            "startTime": iso(end), "metadata": {"note": note}})
    return batch


def post(host: str, public: str, secret: str, batch: list[dict]) -> int | None:
    data = json.dumps({"batch": batch}).encode("utf-8")
    auth = base64.b64encode(f"{public}:{secret}".encode()).decode()
    req = urllib.request.Request(
        f"{host}/api/public/ingestion", data=data, method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": f"Basic {auth}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status
    except Exception as exc:  # noqa: BLE001 — best-effort send
        print(f"langfuse: send failed ({exc}) — carrying on", file=sys.stderr)
        return None


# ── Progress log summary (adds up the usage lines in progress.md) ──────────────

# The time is one whole " · " piece: "1h 3m", "4m 49s" or "37s" (see humanize_dur)
_DUR = re.compile(r"(?:(\d+)h (\d+)m|(\d+)m (\d+)s|(\d+)s)")
_COST = re.compile(r"est\. cost\s*\$([0-9]+(?:\.[0-9]+)?)")
_TOK_IN = re.compile(r"\bin\s*([0-9]+(?:\.[0-9]+)?)([kM]?)")
_TOK_OUT = re.compile(r"\bout\s*([0-9]+(?:\.[0-9]+)?)([kM]?)")
_MODEL_MULTI = re.compile(r"([A-Za-z][A-Za-z0-9._-]*)\(in ")
_MODEL_ONE = re.compile(r"^([A-Za-z][A-Za-z0-9._-]*)\s+·")


def unhumanize(num: str, unit: str) -> int:
    """Undoes humanize()'s notation (12.3k, 1.4M) — the notation is rounded, so this is approximate."""
    v = float(num)
    if unit == "k":
        v *= 1_000
    elif unit == "M":
        v *= 1_000_000
    return int(round(v))


def summarize_progress(text: str) -> str:
    """Picks only the 'Usage:' lines out of all of progress.md and adds them up (skips template notes)."""
    tasks = untracked = secs = tok_in = tok_out = 0
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
        parts.append(f"est. cost total {fmt_usd(cost)}")
    out = " · ".join(parts)
    if models:
        ranked = sorted(models.items(), key=lambda kv: (-kv[1], kv[0]))
        out += "\nModels: " + " · ".join(f"{m} ×{n}" for m, n in ranked)
    if untracked:
        out += f"\nTasks without usage: {untracked}"
    return out


# ── Commands ──────────────────────────────────────────────────────────────

def cmd_task_done(args) -> None:
    since = parse_ts(args.since)
    if since is None:
        print("Usage: no record (couldn't read the --since time)")
        return
    if since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    end = now_utc()
    dur = max(0, int((end - since).total_seconds()))
    per = sum_by_model(since, end)
    print(measure_line(dur, per))
    if not langfuse_on():
        return
    batch = build_batch(args.label, args.feature, args.note, since, end, dur, per)
    if args.dry_run:
        print(json.dumps({"batch": batch}, ensure_ascii=False))
        return
    public, secret, host = resolve_creds()
    if not public or not secret:
        print("langfuse: it's on, but LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY are missing, "
              "so sending is skipped", file=sys.stderr)
        return
    status = post(host, public, secret, batch)
    if status is not None:
        print(f"langfuse: sent (HTTP {status})", file=sys.stderr)


def cmd_summary(args) -> None:
    path = Path(args.path)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        print(f"Summary: couldn't read {path}")
        return
    print(summarize_progress(text))


def cmd_ping() -> None:
    public, secret, host = resolve_creds()
    if not public or not secret:
        print("Warning: LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY are missing — "
              "set them as shell environment variables (never put them in a settings file).")
        return
    ts = iso(now_utc())
    batch = [{"id": "aml-ping-trace-create", "type": "trace-create", "timestamp": ts,
              "body": {"id": "aml-ping", "name": "aml:ping",
                       "timestamp": ts, "tags": ["aml", "ping"]}}]
    status = post(host, public, secret, batch)
    if status is None:
        print(f"Warning: couldn't connect to Langfuse ({host}) — check the address and keys.")
    else:
        # The success message leaves out the host — so a self-hosted address doesn't
        # leak into the conversation log (the failure warning keeps it for debugging).
        print(f"OK: Langfuse connection confirmed (HTTP {status})")


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="observe.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    td = sub.add_parser("task-done", help="task finished — print the usage line (+ send to langfuse)")
    td.add_argument("--since", required=True, help="task start time (ISO8601)")
    td.add_argument("--label", required=True, help="task number and name")
    td.add_argument("--feature", default=None, help="feature name (Langfuse sessionId)")
    td.add_argument("--note", default=None, help="one-line check result")
    td.add_argument("--dry-run", action="store_true", help="print the batch JSON instead of sending")
    sm = sub.add_parser("summary", help="add up the usage lines in progress.md (for /aml:status)")
    sm.add_argument("path", nargs="?", default="progress.md", help="path to progress.md")
    sub.add_parser("ping", help="check the Langfuse connection (for /aml:doctor)")
    args = ap.parse_args()
    if args.cmd == "task-done":
        cmd_task_done(args)
    elif args.cmd == "summary":
        cmd_summary(args)
    else:
        cmd_ping()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — observation must never block the build
        print(f"Usage: no record ({exc})")
        sys.exit(0)
