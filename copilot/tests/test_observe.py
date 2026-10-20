"""test_observe.py — checks the measuring and summary numbers of the Copilot edition's observe.py (standard library only).

Usage (from the repo root): python3 copilot/tests/test_observe.py
Builds fake session logs with set numbers and checks the span usage and summary match the expected values exactly.
The log shape was copied from a real events.jsonl of Copilot CLI 1.0.98 on 2026-10-19, with only the numbers changed.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True   # don't leave __pycache__ in the package folder (it would be copied on install)
HERE = Path(__file__).resolve().parent
OBSERVE = HERE.parent / "aml" / "scripts" / "observe.py"
spec = importlib.util.spec_from_file_location("observe", OBSERVE)
ob = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ob)

SID = "aaaaaaaa-0000-4000-8000-000000000001"
OTHER = "bbbbbbbb-0000-4000-8000-000000000002"

_n = 0


def rec(ts, model, fresh, cr, cw, out, reasoning=0, nano=None, uid=None, details=True):
    """One usage_record line. input = uncached input + cache read + cache write (the same relation as real logs)."""
    global _n
    _n += 1
    u = {"model": model, "inputTokens": fresh + cr + cw, "outputTokens": out,
         "cacheReadTokens": cr, "cacheWriteTokens": cw, "reasoningTokens": reasoning, "cost": 1.0,
         "accounting": {"sourceSessionId": SID, "sequence": _n, "usageId": uid or f"u{_n}"}}
    cu = {}
    if details:
        cu["tokenDetails"] = [{"tokenType": "input", "tokenCount": fresh},
                              {"tokenType": "cache_read", "tokenCount": cr},
                              {"tokenType": "cache_write", "tokenCount": cw},
                              {"tokenType": "output", "tokenCount": out}]
    if nano is not None:
        cu["totalNanoAiu"] = nano
    u["copilotUsage"] = cu
    return {"type": "session.usage_record", "data": {"usage": u}, "id": f"e{_n}", "timestamp": ts}


def start(sid, version="1.0.98", at="2026-10-19T00:00:00.000Z"):
    return {"type": "session.start", "id": "s0", "timestamp": at,
            "data": {"sessionId": sid, "version": 1, "producer": "copilot-agent",
                     "copilotVersion": version, "startTime": at}}


def write_session(home: Path, sid: str, rows, with_start=True, version="1.0.98",
                  at="2026-10-19T00:00:00.000Z"):
    d = home / "session-state" / sid
    d.mkdir(parents=True, exist_ok=True)
    lines = ([start(sid, version, at)] if with_start else []) + rows
    (d / "events.jsonl").write_text("\n".join(json.dumps(r) for r in lines) + "\n", encoding="utf-8")


SINCE = "2026-10-19T00:10:00+00:00"
END = datetime(2026, 10, 19, 0, 20, tzinfo=timezone.utc)   # a 10-minute span

# Inside the span: (uncached input 2000 + 400, cache read 1000 + 600, write 300 + 0, output 300 + 200, reasoning 50)
# AI credits 0.12 + 0.10 = 0.22
BASE_ROWS = [
    rec("2026-10-19T00:05:00.000Z", "gpt-test", 9000, 0, 0, 900, nano=500_000_000),      # before the start — must be left out
    rec("2026-10-19T00:12:00.000Z", "gpt-test", 2000, 1000, 300, 300, 50, nano=120_000_000, uid="dup"),
    rec("2026-10-19T00:12:00.000Z", "gpt-test", 2000, 1000, 300, 300, 50, nano=120_000_000, uid="dup"),  # duplicate
    rec("2026-10-19T00:15:00.000Z", "gpt-test", 400, 600, 0, 200, nano=100_000_000),
    rec("2026-10-19T00:25:00.000Z", "gpt-test", 7000, 0, 0, 700, nano=900_000_000),      # after the end — must be left out
]
BASE_LINE = "Usage: gpt-test · 10m 0s · tokens in 2.4k / out 500 (cache read 1.6k / write 300) · cost unknown · AI credits 0.22"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "copilot-home"
        self.proj = Path(self.tmp.name) / "proj"
        self.proj.mkdir()
        self._old = {k: os.environ.get(k) for k in ("COPILOT_HOME", "COPILOT_AGENT_SESSION_ID")}
        os.environ.update({"COPILOT_HOME": str(self.home), "COPILOT_AGENT_SESSION_ID": SID})
        self._cwd = os.getcwd()
        os.chdir(self.proj)

    def tearDown(self):
        os.chdir(self._cwd)
        for k, v in self._old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.tmp.cleanup()

    def per(self):
        sid = ob.current_session_id()
        st, records = ob.read_events(ob.find_session_file(sid), sid)
        return ob.interval_usage(st, records, ob.parse_ts(SINCE), END)


class TestInterval(Base):
    def test_known_sum_and_duplicates(self):
        write_session(self.home, SID, BASE_ROWS)
        per = self.per()
        self.assertEqual(list(per), ["gpt-test"])
        t = per["gpt-test"]
        self.assertEqual((t["input_tokens"], t["cached_input_tokens"], t["cache_write_input_tokens"],
                          t["output_tokens"], t["reasoning_output_tokens"], t["nano_aiu"]),
                         (2400, 1600, 300, 500, 50, 220_000_000))

    def test_line_does_not_double_count_cache(self):
        write_session(self.home, SID, BASE_ROWS)
        self.assertEqual(ob.task_done_line(SINCE, end=END), BASE_LINE)

    def test_other_session_is_ignored(self):
        write_session(self.home, SID, BASE_ROWS)
        write_session(self.home, OTHER, [rec("2026-10-19T00:11:00.000Z", "gpt-other", 90000, 0, 0, 9000)])
        self.assertEqual(ob.task_done_line(SINCE, end=END), BASE_LINE)

    def test_no_session_id_means_no_record(self):
        write_session(self.home, SID, BASE_ROWS)
        os.environ.pop("COPILOT_AGENT_SESSION_ID")
        self.assertEqual(ob.task_done_line(SINCE, end=END), "Usage: no record (the current session id is unknown)")

    def test_session_started_mid_task_is_no_record(self):
        write_session(self.home, SID, BASE_ROWS[3:4], at="2026-10-19T00:14:00.000Z")
        self.assertEqual(ob.task_done_line(SINCE, end=END), "Usage: no record (the session changed partway through the task)")

    def test_no_sessions_dir(self):
        self.assertEqual(ob.task_done_line(SINCE, end=END), "Usage: no record (there is no Copilot session log folder)")

    def test_session_file_missing(self):
        write_session(self.home, OTHER, BASE_ROWS)
        self.assertEqual(ob.task_done_line(SINCE, end=END), "Usage: no record (couldn't find the current session's log file)")

    def test_unknown_format(self):
        write_session(self.home, SID, BASE_ROWS, with_start=False)
        self.assertEqual(ob.task_done_line(SINCE, end=END), "Usage: no record (the session log format is unknown)")

    def test_old_version_is_not_guessed(self):
        write_session(self.home, SID, BASE_ROWS, version="1.0.90")
        self.assertEqual(ob.task_done_line(SINCE, end=END),
                         "Usage: no record (the log is from an unchecked Copilot CLI version)")

    def test_inconsistent_numbers_are_not_guessed(self):
        bad = rec("2026-10-19T00:12:00.000Z", "gpt-test", 100, 0, 0, 10)
        bad["data"]["usage"]["copilotUsage"]["tokenDetails"][0]["tokenCount"] = 99   # input total doesn't add up
        write_session(self.home, SID, [bad])
        self.assertEqual(ob.task_done_line(SINCE, end=END), "Usage: no record (the token numbers don't relate as expected)")
        neg = rec("2026-10-19T00:12:00.000Z", "gpt-test", 0, 500, 0, 10, details=False)
        neg["data"]["usage"]["inputTokens"] = 100                                    # cache bigger than input
        write_session(self.home, SID, [neg])
        self.assertIn("no record", ob.task_done_line(SINCE, end=END))

    def test_no_usage_in_interval_is_not_zero_cost(self):
        write_session(self.home, SID, BASE_ROWS[:1])
        self.assertEqual(ob.task_done_line(SINCE, end=END), "Usage: 10m 0s · no token record")

    def test_missing_credit_is_not_written_as_zero(self):
        write_session(self.home, SID, [rec("2026-10-19T00:12:00.000Z", "gpt-test", 2000, 0, 0, 300)])
        self.assertEqual(ob.task_done_line(SINCE, end=END),
                         "Usage: gpt-test · 10m 0s · tokens in 2.0k / out 300 (cache read 0 / write 0) · cost unknown")

    def test_multi_model(self):
        rows = [rec("2026-10-19T00:12:00.000Z", "gpt-a", 500, 500, 0, 100, nano=10_000_000),
                rec("2026-10-19T00:14:00.000Z", "gpt-b", 3000, 0, 0, 300, nano=20_000_000)]
        write_session(self.home, SID, rows)
        self.assertEqual(ob.task_done_line(SINCE, end=END),
                         "Usage: 10m 0s · gpt-a(in 500/out 100) + gpt-b(in 3.0k/out 300) · cost unknown · AI credits 0.03")


class TestCost(unittest.TestCase):
    TOK = {"input_tokens": 2_000_000, "cached_input_tokens": 1_000_000, "cache_write_input_tokens": 0,
           "output_tokens": 500_000, "reasoning_output_tokens": 200_000, "nano_aiu": None}

    def test_known_price_counts_cache_once(self):
        # uncached input 2M × $2 + cache 1M × $0.5 + output 0.5M × $8 (reasoning is inside the output)
        self.assertAlmostEqual(ob.cost_usd("gpt-test", self.TOK, {"gpt-test": (2.0, 0.5, 8.0)}), 8.5)

    def test_unknown_model_has_no_cost(self):
        self.assertIsNone(ob.cost_usd("gpt-unknown", self.TOK, {"gpt-test": (2.0, 0.5, 8.0)}))

    def test_cache_write_without_price_is_not_guessed(self):
        tok = dict(self.TOK, cache_write_input_tokens=10)
        self.assertIsNone(ob.cost_usd("gpt-test", tok, {"gpt-test": (2.0, 0.5, 8.0)}))


class TestSummary(unittest.TestCase):
    PROGRESS = """# Progress log
- <observe.py output as is — the one `Usage: …` line: model · time taken · tokens · est. cost. If it fails, `Usage: no record`>
- Usage: claude-opus-5-5 · 4m 16s · tokens in 74 / out 65k (cache read 5.9M / write 105k) · est. cost $5.23
- Usage: gpt-codex · 10m 0s · tokens in 2.4k / out 500 (cache read 1.6k) · cost unknown
- Usage: gpt-test · 10m 0s · tokens in 2.4k / out 500 (cache read 1.6k / write 300) · cost unknown · AI credits 0.22
- Usage: 1m 30s · gpt-a(in 500/out 100) + gpt-b(in 3.0k/out 300) · cost unknown · AI credits 0.03
- Usage: no record (the current session id is unknown)
"""

    def test_mixed_claude_codex_copilot_lines(self):
        self.assertEqual(ob.summarize_progress(self.PROGRESS), "\n".join([
            "Summary: 5 tasks · total 25m 46s · tokens approx. in 8.4k / out 66.4k · known cost total $5.23",
            "Models: claude-opus-5-5 ×1 · gpt-a ×1 · gpt-b ×1 · gpt-codex ×1 · gpt-test ×1",
            "AI credits total: 0.25 (usage Copilot recorded — counted separately from dollar cost)",
            "Tasks with cost unknown: 3 (models whose price couldn't be confirmed — not counted as 0)",
            "Tasks without usage: 1"]))

    def test_empty(self):
        self.assertEqual(ob.summarize_progress("# Progress log\n"), "Summary: no usage lines yet")


class TestCli(Base):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-B", str(OBSERVE), *args], cwd=self.proj,
                              env=dict(os.environ), capture_output=True, text=True)

    def test_start_then_done_round_trip(self):
        write_session(self.home, SID, BASE_ROWS[:1])
        r = self.run_cli("task-start", "--label", "1.1 test")
        self.assertEqual(r.returncode, 0)
        self.assertTrue(r.stdout.startswith("Start: "), r.stdout)
        self.assertEqual(r.stderr, "")                    # no warning when the log can be read
        r = self.run_cli("task-done", "--since", r.stdout.split("Start: ")[1].strip(), "--label", "1.1 test")
        self.assertEqual(r.returncode, 0)
        self.assertIn("no token record", r.stdout)      # no tokens used after the start (not shown as 0 cost)
        self.assertFalse((self.proj / ".aml").exists())   # leaves nothing in the project

    def test_bad_input_never_fails(self):
        os.environ.pop("COPILOT_AGENT_SESSION_ID")
        for args in (("task-done", "--since", "yesterday"), ("task-done", "--since", SINCE),
                     ("task-start",), ("check",), ("summary", "no-such-file.md")):
            r = self.run_cli(*args)
            self.assertEqual(r.returncode, 0, (args, r.stderr))
        self.assertIn("no record", self.run_cli("task-done", "--since", SINCE).stdout)
        self.assertIn("no record", self.run_cli("check").stdout)

    def test_real_shape_from_copilot_1_0_98(self):
        # the numbers of a real 2026-10-19 log as is (input 15264 = 7968 + cache 7296, AI credits 0.175752)
        write_session(self.home, SID, [rec("2026-10-19T00:12:00.000Z", "mai-code-1.1-flash",
                                           7968, 7296, 0, 15, nano=175_752_000)])
        self.assertEqual(ob.task_done_line(SINCE, end=END),
                         "Usage: mai-code-1.1-flash · 10m 0s · tokens in 8.0k / out 15 (cache read 7.3k / write 0) · cost unknown · AI credits 0.18")


if __name__ == "__main__":
    unittest.main(verbosity=1)
