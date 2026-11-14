"""Run: python agent-workflow/scripts/test_workflow.py (stdlib only)."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import workflow


SCRIPT = Path(__file__).with_name("workflow.py")


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="workflow-中文-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / ".superpowers/sdd/run/state.json"
        self.spec = self.root / "spec.json"
        self.put("input.txt", "input")

    def put(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def task(self, name="a", **changes):
        task = dict(id=name, title=name, owns=[name], depends=[],
                    acceptance=["Real output passes review"], inputs=["input.txt"],
                    checks=[[sys.executable, "-c", "print('checked')"]])
        task.update(changes)
        return task

    def cli(self, command, *args, ok=True):
        result = subprocess.run([sys.executable, str(SCRIPT), command, str(self.state),
                                 *map(str, args)], capture_output=True, text=True,
                                encoding="utf-8", timeout=15)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def init(self, tasks=None, ok=True):
        self.spec.write_text(json.dumps(dict(goal="测试 goal", tasks=tasks or [self.task()]),
                                        ensure_ascii=False), encoding="utf-8")
        return self.cli("init", "--root", self.root, "--spec", self.spec, ok=ok)

    def load(self):
        return json.loads(self.state.read_text(encoding="utf-8"))

    def submitted(self, name="a", agent="worker"):
        self.cli("start", name, "--agent", agent)
        self.put(name + "/out.txt", "output")
        self.cli("submit", name, "--artifact", name + "/out.txt")

    def reviewed(self, name="a", verdict="pass"):
        report = self.put("reviews/" + name + ".md", "Inspected real output; " + verdict)
        self.cli("review", name, "--agent", "reviewer", "--report",
                 report.relative_to(self.root), "--verdict", verdict)

    def verified(self, name="a"):
        self.submitted(name)
        self.cli("check", name)
        self.reviewed(name)
        self.cli("verify", name)

    def test_lifecycle_reload_and_atomic_rejection(self):
        self.init()
        original = self.state.read_bytes()
        self.cli("init", "--root", self.root, "--spec", self.spec, ok=False)
        self.assertEqual(self.state.read_bytes(), original)
        self.submitted()
        self.cli("verify", "a", ok=False)
        self.cli("check", "a")
        self.reviewed()
        self.cli("verify", "a")
        self.cli("finish")
        status = json.loads(self.cli("status").stdout)
        self.assertFalse(status["tasks"]["a"]["stale"])
        self.assertEqual(self.load()["tasks"]["a"]["status"], "verified")
        self.assertGreater(len(self.load()["events"]), 5)

    def test_invalid_specs(self):
        cases = [[], [self.task(), self.task()], [self.task(depends=["missing"])],
                 [self.task(depends=["b"]), self.task("b", depends=["a"])],
                 [self.task(acceptance=[])], [self.task(checks=[])],
                 [self.task(owns=["../outside"])], [self.task(owns=[str(self.root / "a")])],
                 [self.task(owns=["a", "a/../a"])], [self.task(timeout=0)],
                 [self.task(checks=["echo wrong shape"])], [self.task(max_attempts=0)]]
        for tasks in cases:
            with self.subTest(tasks=tasks):
                self.spec.write_text(json.dumps(dict(goal="goal", tasks=tasks)), encoding="utf-8")
                self.cli("init", "--root", self.root, "--spec", self.spec, ok=False)
                self.assertFalse(self.state.exists())
        self.spec.write_text("[]", encoding="utf-8")
        result = self.cli("init", "--root", self.root, "--spec", self.spec, ok=False)
        self.assertNotIn("Traceback", result.stderr)

    def test_parallel_overlap_aliases_and_artifact_boundary(self):
        self.init([self.task(), self.task("b", owns=["a/../a/sub"]), self.task("c")])
        self.cli("start", "a", "--agent", "w1")
        self.cli("start", "b", "--agent", "w2", ok=False)
        self.cli("start", "c", "--agent", "w3")
        self.put("a/out.txt", "output")
        self.cli("submit", "a", "--artifact", "a/missing.txt", ok=False)
        self.cli("submit", "a", "--artifact", "input.txt", ok=False)
        self.cli("submit", "a", "--artifact", "a", ok=False)
        self.cli("submit", "a", "--artifact", "a/out.txt", "--artifact", "a/./out.txt", ok=False)
        self.cli("submit", "a", "--artifact", "a/./out.txt")
        self.cli("start", "b", "--agent", "w2", ok=False)

    def test_case_alias(self):
        self.init([self.task(), self.task("b", owns=["A/sub"])])
        self.cli("start", "a", "--agent", "w")
        self.cli("start", "b", "--agent", "w2", ok=False)

    def test_symlink_escape(self):
        self.init()
        self.cli("start", "a", "--agent", "w")
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        try:
            os.symlink(outside.name, self.root / "a", target_is_directory=True)
        except OSError as error:
            self.skipTest("Windows symlink privilege unavailable: " + str(error))
        Path(outside.name, "out.txt").write_text("outside", encoding="utf-8")
        self.cli("submit", "a", "--artifact", "a/out.txt", ok=False)

    def test_self_review_missing_report_and_fail_requires_new_attempt(self):
        self.init()
        self.submitted()
        self.put("review.md", "review")
        self.cli("review", "a", "--agent", "WORKER", "--report", "review.md", "--verdict", "pass", ok=False)
        self.cli("review", "a", "--agent", "r", "--report", "missing.md", "--verdict", "pass", ok=False)
        self.put("empty.md", " \n")
        self.cli("review", "a", "--agent", "r", "--report", "empty.md", "--verdict", "pass", ok=False)
        self.reviewed(verdict="fail")
        original_report = (self.root / "reviews/a.md").read_text(encoding="utf-8")
        self.cli("review", "a", "--agent", "r", "--report", "review.md", "--verdict", "pass", ok=False)
        self.submitted(agent="worker2")
        self.cli("check", "a")
        self.reviewed()
        self.cli("verify", "a")
        self.assertEqual(len(self.load()["tasks"]["a"]["attempts"]), 2)
        self.assertEqual(self.load()["tasks"]["a"]["attempts"][0]["reviews"][0].get("report_text"), original_report)

    def test_each_freshness_boundary(self):
        for target in ("input.txt", "a/out.txt", "reviews/a.md", "spec.json", "log"):
            with self.subTest(target=target):
                # Independent roots retain each stale state as evidence until cleanup.
                if self.state.exists():
                    self.state = self.state.with_name(self.state.stem + "x.json")
                self.init()
                self.verified()
                if target == "log":
                    log = self.load()["tasks"]["a"]["attempts"][-1]["check_runs"][-1]["results"][0]["log"]
                    Path(log).write_text("forged old success", encoding="utf-8")
                else:
                    with (self.root / target).open("a", encoding="utf-8") as handle:
                        handle.write("changed")
                self.cli("verify", "a", ok=False)
                self.cli("finish", ok=False)
                self.assertTrue(json.loads(self.cli("status").stdout)["tasks"]["a"]["stale"])

    def test_dependency_recursive_freshness(self):
        self.init([self.task(), self.task("b", depends=["a"]), self.task("c", depends=["b"])])
        self.cli("start", "b", "--agent", "w", ok=False)
        self.verified("a")
        self.verified("b")
        self.verified("c")
        self.cli("finish")
        self.put("a/out.txt", "changed upstream")
        self.cli("verify", "c", ok=False)
        self.cli("finish", ok=False)
        self.cli("repair", "c", "--reason", "upstream changed")
        self.cli("start", "c", "--agent", "w", ok=False)

    def test_failed_command_timeout_and_mutation_keep_logs(self):
        commands = [("import sys; print('failed'); sys.exit(7)", 2),
                    ("import time; print('started', flush=True); time.sleep(3)", .1),
                    ("from pathlib import Path; Path('a/out.txt').write_text('changed')", 2)]
        for code, timeout in commands:
            with self.subTest(code=code):
                if self.state.exists():
                    self.state = self.state.with_name(self.state.stem + "x.json")
                self.init([self.task(checks=[[sys.executable, "-c", code]], timeout=timeout)])
                self.submitted()
                self.cli("check", "a", ok=False)
                task = self.load()["tasks"]["a"]
                self.assertEqual(task["status"], "repair")
                run = task["attempts"][-1]["check_runs"][-1]
                self.assertFalse(run["passed"])
                self.assertTrue(Path(run["results"][0]["log"]).is_file())
                if "sys.exit" in code:
                    self.assertEqual(run["results"][0]["returncode"], 7)
                if "time.sleep" in code:
                    self.assertTrue(run["results"][0]["timed_out"])
                    self.assertIsInstance(run["results"][0]["returncode"], int)
                self.cli("verify", "a", ok=False)
                self.cli("check", "a", ok=False)

    def test_check_after_review_detects_mutation(self):
        self.init([self.task(checks=[[sys.executable, "-c", "from pathlib import Path; Path('a/out.txt').write_text('new')"]])])
        self.submitted()
        self.reviewed()
        self.cli("check", "a", ok=False)
        self.cli("verify", "a", ok=False)

    def test_budget_wait_resume_and_inspection(self):
        self.init([self.task(validation="inspection", checks=[], max_attempts=2)])
        self.cli("start", "a", "--agent", "w")
        self.cli("wait", "a", "--reason", "unknown request result", "--external-id", "req-1")
        self.cli("start", "a", "--agent", "w", ok=False)
        self.cli("finish", ok=False)
        self.cli("repair", "a", "--reason", "bypass waiting", ok=False)
        self.cli("resume", "a", "--resolution", "looked up req-1: finished")
        self.put("a/out.txt", "output")
        self.cli("submit", "a", "--artifact", "a/out.txt")
        self.reviewed()
        self.cli("verify", "a")
        self.cli("repair", "a", "--reason", "new finding")
        self.submitted(agent="w")
        self.reviewed(verdict="fail")
        before = self.state.read_bytes()
        self.cli("start", "a", "--agent", "w", ok=False)
        self.assertEqual(self.state.read_bytes(), before)
        self.assertEqual(len(self.load()["tasks"]["a"]["attempts"]), 2)

    def test_atomic_write_failure_preserves_state(self):
        self.init()
        old = self.state.read_bytes()
        with patch.object(workflow.os, "replace", side_effect=OSError("simulated disk failure")):
            with self.assertRaises(OSError):
                workflow.save(self.state, dict(broken=True))
        self.assertEqual(self.state.read_bytes(), old)
        self.assertEqual(list(self.state.parent.glob("*.tmp")), [])

    def test_directory_input_added_file_and_review_status_staleness(self):
        self.put("config/first", "first")
        self.init([self.task(inputs=["config"])])
        self.submitted()
        self.cli("check", "a")
        self.reviewed()
        self.put("reviews/a.md", "changed review")
        self.assertTrue(json.loads(self.cli("status").stdout)["tasks"]["a"]["stale"])
        self.cli("verify", "a", ok=False)
        self.put("config/second", "second")
        self.cli("check", "a", ok=False)

    def test_argv_is_literal_and_every_predeclared_check_runs(self):
        self.init([self.task(checks=[[sys.executable, "-c", "import sys; print(sys.argv[1])", "a & echo bad"],
                                      [sys.executable, "-c", "print('second')"]])])
        self.submitted()
        self.cli("check", "a")
        results = self.load()["tasks"]["a"]["attempts"][-1]["check_runs"][-1]["results"]
        self.assertEqual(len(results), 2)
        self.assertIn("a & echo bad", Path(results[0]["log"]).read_text(encoding="utf-8"))
        self.assertIn("second", Path(results[1]["log"]).read_text(encoding="utf-8"))

    def test_start_input_baseline_survives_wait_and_requires_new_attempt(self):
        for waiting in (False, True):
            with self.subTest(waiting=waiting):
                if self.state.exists():
                    self.state = self.state.with_name(self.state.stem + "x.json")
                self.put("input.txt", "v1")
                self.init([self.task(validation="inspection", checks=[])])
                self.cli("start", "a", "--agent", "worker")
                self.put("a/out.txt", (self.root / "input.txt").read_text(encoding="utf-8"))
                if waiting:
                    self.cli("wait", "a", "--reason", "result unknown", "--external-id", "req-1")
                self.put("input.txt", "v2")
                if waiting:
                    self.cli("resume", "a", "--resolution", "queried req-1: finished")
                old = self.state.read_bytes()
                self.cli("submit", "a", "--artifact", "a/out.txt", ok=False)
                self.assertEqual(self.state.read_bytes(), old)
                self.assertTrue(json.loads(self.cli("status").stdout)["tasks"]["a"]["stale"])
                self.cli("verify", "a", ok=False)
                self.cli("finish", ok=False)
                self.cli("repair", "a", "--reason", "input changed; rebuild from v2")
                self.cli("start", "a", "--agent", "worker")
                self.put("a/out.txt", (self.root / "input.txt").read_text(encoding="utf-8"))
                self.cli("submit", "a", "--artifact", "a/out.txt")
                self.reviewed()
                self.cli("verify", "a")
                self.cli("finish")
                attempts = self.load()["tasks"]["a"]["attempts"]
                self.assertNotEqual(attempts[0]["baseline"], attempts[1]["baseline"])

    def test_running_dependency_reverification_invalidates_start_baseline(self):
        self.init([self.task(validation="inspection", checks=[]),
                   self.task("b", depends=["a"], validation="inspection", checks=[])])
        self.verified("a")
        self.cli("start", "b", "--agent", "worker")
        self.put("b/out.txt", "derived from upstream attempt 1")
        self.cli("repair", "a", "--reason", "independent review requires new upstream attempt")
        self.verified("a")  # Same bytes, new proof: the old downstream execution still cannot be rebound.
        self.cli("submit", "b", "--artifact", "b/out.txt", ok=False)
        self.cli("repair", "b", "--reason", "use new dependency proof")
        self.verified("b")
        self.cli("finish")

    def test_running_spec_change_rejects_submit(self):
        self.init()
        self.cli("start", "a", "--agent", "worker")
        self.put("a/out.txt", "output")
        with self.spec.open("a", encoding="utf-8") as target:
            target.write("\n")
        self.cli("submit", "a", "--artifact", "a/out.txt", ok=False)

    def test_inputs_cannot_intersect_mutable_owns(self):
        for inputs in (["a"], ["a/sub"], ["A"], ["a/../a"]):
            with self.subTest(inputs=inputs):
                self.init([self.task(inputs=inputs)], ok=False)
                self.assertFalse(self.state.exists())
        self.init([self.task(owns=["source/file.py"], inputs=["source"])], ok=False)
        self.assertFalse(self.state.exists())

    def test_inputs_cannot_contain_ledger_or_logs(self):
        ledger = self.state.relative_to(self.root).as_posix()
        for inputs in ([ledger], [ledger + "/inside"], [str(Path(ledger).parent)],
                       [ledger + ".logs"], [ledger + ".logs/nested.log"]):
            with self.subTest(inputs=inputs):
                self.init([self.task(inputs=inputs)], ok=False)
                self.assertFalse(self.state.exists())

    def test_existing_code_in_owns_is_editable_without_immutable_overlap(self):
        self.put("source/app.py", "old implementation")
        self.init([self.task(owns=["source/app.py"], validation="inspection", checks=[])])
        self.cli("start", "a", "--agent", "worker")
        self.put("source/app.py", "new implementation")
        self.cli("submit", "a", "--artifact", "source/app.py")
        self.reviewed()
        self.cli("verify", "a")
        self.cli("finish")

    def test_legacy_attempt_missing_baseline_requires_repair_preserves_review(self):
        self.init([self.task(validation="inspection", checks=[])])
        self.verified()
        state = self.load()
        original = state["tasks"]["a"]["attempts"][0]
        original.pop("baseline", None)
        self.state.write_text(json.dumps(state), encoding="utf-8")
        old = self.state.read_bytes()
        result = self.cli("verify", "a", ok=False)
        self.assertIn("baseline", result.stderr)
        self.assertEqual(self.state.read_bytes(), old)
        self.cli("finish", ok=False)
        self.cli("repair", "a", "--reason", "legacy attempt needs new execution baseline")
        self.verified()
        self.cli("finish")
        self.assertEqual(self.load()["tasks"]["a"]["attempts"][0], original)


if __name__ == "__main__":
    unittest.main(verbosity=2)
