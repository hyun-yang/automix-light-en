"""test_observe.py — checks the measuring and summary numbers of the Codex edition's observe.py (standard library only).

Usage (from the repo root): python3 codex/tests/test_observe.py
Builds fake session logs with set numbers and checks the span usage and summary match the expected values exactly.
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

SID = "01aaaaaa-0000-7000-8000-000000000001"
OTHER = "01bbbbbb-0000-7000-8000-000000000002"
CWD = "/work/project"


def usage(inp, cached, out, reasoning=0, cache_write=0):
    return {"input_tokens": inp, "cached_input_tokens": cached,
            "cache_write_input_tokens": cache_write, "output_tokens": out,
            "reasoning_output_tokens": reasoning, "total_tokens": inp + out}


def tc(ts, u):
    return {"timestamp": ts, "type": "event_msg",
            "payload": {"type": "token_count", "info": {"total_token_usage": u, "last_token_usage": u}}}


def ctx(ts, model):
    return {"timestamp": ts, "type": "turn_context", "payload": {"cwd": CWD, "model": model}}


def meta(sid, version="0.163.0"):
    return {"timestamp": "2026-10-17T00:00:00Z", "type": "session_meta",
            "payload": {"id": sid, "session_id": sid, "cwd": CWD, "cli_version": version}}


def write_session(home: Path, sid: str, rows, with_meta=True, version="0.163.0"):
    d = home / "sessions" / "2026" / "10" / "17"
    d.mkdir(parents=True, exist_ok=True)
    lines = ([meta(sid, version)] if with_meta else []) + rows
    (d / f"rollout-2026-10-17T00-00-00-{sid}.jsonl").write_text(
        "\n".join(json.dumps(r) for r in lines) + "\n", encoding="utf-8")


SINCE = "2026-10-17T00:10:00+00:00"
END = datetime(2026, 10, 17, 0, 20, tzinfo=timezone.utc)   # a 10-minute span

# Base session: cumulative before start (1000/400/100) → end (5000/2000/600, reasoning 200)
# Growth in the span: input 4000 (cache 1600 → uncached input 2400) / output 500
BASE_ROWS = [
    ctx("2026-10-17T00:01:00Z", "gpt-test"),
    tc("2026-10-17T00:05:00Z", usage(1000, 400, 100)),
    tc("2026-10-17T00:12:00Z", usage(3000, 1000, 300)),
    tc("2026-10-17T00:12:00Z", usage(3000, 1000, 300)),      # duplicate event
    tc("2026-10-17T00:15:00Z", usage(5000, 2000, 600, 200)),
    tc("2026-10-17T00:25:00Z", usage(9000, 3000, 900)),      # after the span end — must be left out
]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "codex-home"
        self.proj = Path(self.tmp.name) / "proj"
        self.proj.mkdir()
        self.env = {"CODEX_HOME": str(self.home), "CODEX_THREAD_ID": SID}
        self._old = {k: os.environ.get(k) for k in ("CODEX_HOME", "CODEX_THREAD_ID", "CODEX_SESSION_ID")}
        os.environ.update(self.env)
        os.environ.pop("CODEX_SESSION_ID", None)
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
        events = ob.read_events(ob.find_session_file(sid), sid)
        return ob.interval_usage(events, ob.parse_ts(SINCE), END, ob.load_baseline("t", sid))


class TestInterval(Base):
    def test_known_difference_and_duplicates(self):
        write_session(self.home, SID, BASE_ROWS)
        per = self.per()
        self.assertEqual(list(per), ["gpt-test"])
        t = per["gpt-test"]
        self.assertEqual((t["input_tokens"], t["cached_input_tokens"], t["output_tokens"],
                          t["reasoning_output_tokens"], t["total_tokens"]),
                         (4000, 1600, 500, 200, 4500))

    def test_line_does_not_double_count_cache(self):
        write_session(self.home, SID, BASE_ROWS)
        line = ob.task_done_line(SINCE, "t", end=END)
        self.assertEqual(line, "Usage: gpt-test · 10m 0s · tokens in 2.4k / out 500 (cache read 1.6k) · cost unknown")

    def test_other_session_same_cwd_is_ignored(self):
        write_session(self.home, SID, BASE_ROWS)
        write_session(self.home, OTHER, [ctx("2026-10-17T00:01:00Z", "gpt-other"),
                                         tc("2026-10-17T00:11:00Z", usage(90000, 0, 9000))])
        self.assertEqual(ob.task_done_line(SINCE, "t", end=END),
                         "Usage: gpt-test · 10m 0s · tokens in 2.4k / out 500 (cache read 1.6k) · cost unknown")

    def test_no_session_id_means_no_record_even_with_same_cwd(self):
        write_session(self.home, SID, BASE_ROWS)
        os.environ.pop("CODEX_THREAD_ID")
        self.assertEqual(ob.task_done_line(SINCE, "t", end=END),
                         "Usage: no record (the current session id is unknown)")

    def test_counter_reset(self):
        rows = [ctx("2026-10-17T00:01:00Z", "gpt-test"),
                tc("2026-10-17T00:05:00Z", usage(1000, 0, 100)),
                tc("2026-10-17T00:12:00Z", usage(3000, 0, 300)),   # +2000/+200
                tc("2026-10-17T00:14:00Z", usage(500, 0, 50)),     # reset → +500/+50
                tc("2026-10-17T00:16:00Z", usage(800, 0, 80))]     # +300/+30
        write_session(self.home, SID, rows)
        t = self.per()["gpt-test"]
        self.assertEqual((t["input_tokens"], t["output_tokens"]), (2800, 280))

    def test_missing_start_value_is_no_record(self):
        rows = [ctx("2026-10-17T00:01:00Z", "gpt-test"),
                tc("2026-10-17T00:12:00Z", usage(3000, 0, 300))]   # no cumulative value before the start
        write_session(self.home, SID, rows)
        self.assertEqual(ob.task_done_line(SINCE, "t", end=END),
                         "Usage: no record (there is no cumulative value at the span start)")

    def test_missing_start_value_uses_snapshot(self):
        rows = [ctx("2026-10-17T00:01:00Z", "gpt-test"),
                tc("2026-10-17T00:12:00Z", usage(3000, 0, 300))]
        write_session(self.home, SID, rows)
        (self.proj / ".aml").mkdir()
        (self.proj / ".aml" / "codex-measure-start.json").write_text(json.dumps(
            {"label": "t", "session": SID, "since": SINCE, "usage": usage(1000, 0, 100)}))
        t = self.per()["gpt-test"]
        self.assertEqual((t["input_tokens"], t["output_tokens"]), (2000, 200))

    def test_snapshot_from_other_session_is_not_used(self):
        rows = [ctx("2026-10-17T00:01:00Z", "gpt-test"),
                tc("2026-10-17T00:12:00Z", usage(3000, 0, 300))]
        write_session(self.home, SID, rows)
        (self.proj / ".aml").mkdir()
        (self.proj / ".aml" / "codex-measure-start.json").write_text(json.dumps(
            {"label": "t", "session": OTHER, "since": SINCE, "usage": usage(1000, 0, 100)}))
        self.assertIn("no record", ob.task_done_line(SINCE, "t", end=END))

    def test_no_sessions_dir(self):
        self.assertEqual(ob.task_done_line(SINCE, "t", end=END),
                         "Usage: no record (there is no Codex session log folder)")

    def test_unknown_format(self):
        write_session(self.home, SID, BASE_ROWS, with_meta=False)
        self.assertEqual(ob.task_done_line(SINCE, "t", end=END),
                         "Usage: no record (the session log format is unknown)")

    def test_old_version_is_not_guessed(self):
        write_session(self.home, SID, BASE_ROWS, version="0.135.0")
        self.assertEqual(ob.task_done_line(SINCE, "t", end=END),
                         "Usage: no record (the log is from an unchecked Codex version)")

    def test_inconsistent_numbers_are_not_guessed(self):
        # a log like the 0.135 days, where reasoning is bigger than output and cache bigger than input
        odd = {"input_tokens": 2521, "cached_input_tokens": 3968, "cache_write_input_tokens": 0,
               "output_tokens": 395, "reasoning_output_tokens": 13843, "total_tokens": 16759}
        rows = BASE_ROWS[:2] + [tc("2026-10-17T00:12:00Z", odd)]
        write_session(self.home, SID, rows)
        self.assertEqual(ob.task_done_line(SINCE, "t", end=END),
                         "Usage: no record (the token numbers don't relate as expected)")

    def test_no_usage_in_interval_is_not_zero_cost(self):
        rows = [ctx("2026-10-17T00:01:00Z", "gpt-test"),
                tc("2026-10-17T00:05:00Z", usage(1000, 0, 100))]
        write_session(self.home, SID, rows)
        self.assertEqual(ob.task_done_line(SINCE, "t", end=END), "Usage: 10m 0s · no token record")

    def test_multi_model(self):
        rows = [ctx("2026-10-17T00:01:00Z", "gpt-a"),
                tc("2026-10-17T00:05:00Z", usage(1000, 0, 100)),
                tc("2026-10-17T00:12:00Z", usage(2000, 500, 200)),   # gpt-a +1000(cache 500)/+100
                ctx("2026-10-17T00:13:00Z", "gpt-b"),
                tc("2026-10-17T00:14:00Z", usage(5000, 500, 500))]   # gpt-b +3000/+300
        write_session(self.home, SID, rows)
        self.assertEqual(ob.task_done_line(SINCE, "t", end=END),
                         "Usage: 10m 0s · gpt-a(in 500/out 100) + gpt-b(in 3.0k/out 300) · cost unknown")


class TestCost(unittest.TestCase):
    TOK = {"input_tokens": 3_000_000, "cached_input_tokens": 1_000_000,
           "cache_write_input_tokens": 0, "output_tokens": 500_000,
           "reasoning_output_tokens": 200_000, "total_tokens": 3_500_000}

    def test_known_price_counts_cache_once(self):
        # uncached input 2M × $2 + cache 1M × $0.5 + output 0.5M × $8 (reasoning is inside the output)
        c = ob.cost_usd("gpt-test", self.TOK, {"gpt-test": (2.0, 0.5, 8.0)})
        self.assertAlmostEqual(c, 4.0 + 0.5 + 4.0)

    def test_unknown_model_has_no_cost(self):
        self.assertIsNone(ob.cost_usd("gpt-unknown", self.TOK, {"gpt-test": (2.0, 0.5, 8.0)}))

    def test_cache_write_without_price_is_not_guessed(self):
        tok = dict(self.TOK, cache_write_input_tokens=10)
        self.assertIsNone(ob.cost_usd("gpt-test", tok, {"gpt-test": (2.0, 0.5, 8.0)}))

    def test_partial_cost_is_marked(self):
        per = {"gpt-test": self.TOK, "gpt-unknown": self.TOK}
        line = ob.measure_line(60, per, {"gpt-test": (2.0, 0.5, 8.0)})
        self.assertTrue(line.endswith("· est. cost $8.50 (some cost unknown)"), line)


class TestSummary(unittest.TestCase):
    PROGRESS = """# Progress log
- <observe.py output as is — the one `Usage: …` line: model · time taken · tokens · est. cost. If it fails, `Usage: no record`>
- Usage: claude-opus-5-5 · 4m 16s · tokens in 74 / out 65k (cache read 5.9M / write 105k) · est. cost $5.23
- Usage: gpt-test · 10m 0s · tokens in 2.4k / out 500 (cache read 1.6k) · cost unknown
- Usage: 1m 30s · gpt-a(in 500/out 100) + gpt-b(in 3.0k/out 300) · est. cost $0.50 (some cost unknown)
- Usage: no record (the current session id is unknown)
- Usage: no record
"""

    def test_mixed_claude_codex_lines(self):
        self.assertEqual(ob.summarize_progress(self.PROGRESS), "\n".join([
            "Summary: 5 tasks · total 15m 46s · tokens approx. in 6.0k / out 65.9k · known cost total $5.73",
            "Models: claude-opus-5-5 ×1 · gpt-a ×1 · gpt-b ×1 · gpt-test ×1",
            "Tasks with cost unknown: 2 (models whose price couldn't be confirmed — not counted as 0)",
            "Tasks without usage: 2"]))

    def test_empty(self):
        self.assertEqual(ob.summarize_progress("# Progress log\n"), "Summary: no usage lines yet")


class TestCli(Base):
    def run_cli(self, *args):
        env = dict(os.environ)
        return subprocess.run([sys.executable, str(OBSERVE), *args], cwd=self.proj, env=env,
                              capture_output=True, text=True)

    def test_start_then_done_round_trip(self):
        write_session(self.home, SID, [ctx("2026-10-17T00:01:00Z", "gpt-test"),
                                       tc("2026-10-17T00:05:00Z", usage(1000, 0, 100))])
        r = self.run_cli("task-start", "--label", "1.1 test")
        self.assertEqual(r.returncode, 0)
        self.assertTrue(r.stdout.startswith("Start: "), r.stdout)
        self.assertTrue((self.proj / ".aml" / "codex-measure-start.json").exists())
        r = self.run_cli("task-done", "--since", r.stdout.split("Start: ")[1].strip(), "--label", "1.1 test")
        self.assertEqual(r.returncode, 0)
        self.assertTrue(r.stdout.startswith("Usage: "), r.stdout)
        self.assertIn("no token record", r.stdout)      # no tokens used after the start (not shown as 0 cost)
        self.assertFalse((self.proj / ".aml" / "codex-measure-start.json").exists())

    def test_bad_input_never_fails(self):
        os.environ.pop("CODEX_THREAD_ID")
        for args in (("task-done", "--since", "yesterday"), ("task-done", "--since", SINCE),
                     ("task-start",), ("check",), ("summary", "no-such-file.md")):
            r = self.run_cli(*args)
            self.assertEqual(r.returncode, 0, (args, r.stderr))
        self.assertIn("no record", self.run_cli("task-done", "--since", SINCE).stdout)
        self.assertIn("no record", self.run_cli("check").stdout)


if __name__ == "__main__":
    unittest.main(verbosity=1)
