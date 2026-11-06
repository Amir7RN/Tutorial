"""C++ course (cpp/learn): every reference solution passes, every starter does not.

Compiles each exercise with the real g++ (skipped when no compiler is found):
  * solution files  -> every check passes (mutation exercises: catches every mutant)
  * starter files   -> compiles when it should, and is NOT already passing
"""

import os
import re
import shutil
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ctrlcore import cpp_course as cc

GXX = cc.find_gxx()


def _grade(ex, files):
    tmp = tempfile.mkdtemp(prefix=f"cpp_{ex.id}_")
    try:
        src = cc.write_sources(ex, files, os.path.join(tmp, "src"))
        steps = cc.plan(ex, src, "check", build=os.path.join(tmp, "build"))
        rep = cc.Report()
        import subprocess
        for step in steps:
            c = subprocess.run(step.compile, capture_output=True, text=True, errors="replace")
            if c.returncode != 0:
                rep.compiled = False
                rep.compile_log = c.stdout + c.stderr
                return rep
            r = subprocess.run([step.exe], capture_output=True, text=True, timeout=30, errors="replace")
            cc.grade_step(step, r.returncode, r.stdout, rep)
        rep.results += cc.check_rules(ex, src)
        return rep
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


class Metadata(unittest.TestCase):
    def test_every_exercise_has_files_task_and_hints(self):
        for ex in cc.EXERCISES.values():
            self.assertTrue(cc.starter_files(ex), ex.id)
            self.assertTrue(os.path.isdir(os.path.join(cc.EXERCISES_DIR, ex.id, "solution")), ex.id)
            if not ex.mutants:
                self.assertTrue(os.path.exists(os.path.join(cc.EXERCISES_DIR, ex.id, "test", "test_main.cpp")), ex.id)
            self.assertGreater(len(ex.task), 80, ex.id)
            self.assertTrue(ex.hints, ex.id)
            for name, path in cc.given_files(ex).items():
                self.assertTrue(os.path.exists(path), f"{ex.id}: given {name}")

    def test_project_scheduler_copy_matches_the_v2_solution(self):
        a = cc._read(os.path.join(cc.PROJECT_DIR, "scheduler.hpp"))
        b = cc._read(os.path.join(cc.EXERCISES_DIR, "p2_sched", "solution", "scheduler.hpp"))
        self.assertEqual(a, b)

    def test_result_parser(self):
        res, done, other = cc.parse_results("PASS a\nFAIL b c | got 1, expected 2\nhello\nDONE\n")
        self.assertEqual([(r.ok, r.name, r.why) for r in res],
                         [(True, "a", ""), (False, "b c", "got 1, expected 2")])
        self.assertTrue(done)
        self.assertEqual(other, "hello")

    def test_diagnostics_parser(self):
        log = ("C:/x/work/s0/pid.hpp:5:7: error: redefinition of 'class Pid'\n"
               "ld.exe: test_main.o: undefined reference to `Pid::update(double)'\n")
        d = cc.diagnostics(log)
        self.assertEqual(d[0][:2], ("pid.hpp", 5))
        self.assertEqual(d[-1][3], "link")


@unittest.skipIf(GXX is None, "g++ not installed")
class Builds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        exs = list(cc.EXERCISES.values())
        with ThreadPoolExecutor(max_workers=6) as pool:
            sol = list(pool.map(lambda e: _grade(e, cc.solution_files(e)), exs))
            sta = list(pool.map(lambda e: _grade(e, cc.starter_files(e)), exs))
        cls.solutions = dict(zip([e.id for e in exs], sol))
        cls.starters = dict(zip([e.id for e in exs], sta))

    def test_every_solution_passes(self):
        for ex_id, rep in self.solutions.items():
            with self.subTest(ex=ex_id):
                self.assertTrue(rep.compiled, rep.compile_log[:1500])
                bad = [f"{r.name}: {r.why}" for r in rep.results if not r.ok]
                self.assertFalse(bad, bad)
                self.assertTrue(rep.passed)

    def test_every_starter_is_not_yet_passing(self):
        for ex_id, rep in self.starters.items():
            ex = cc.EXERCISES[ex_id]
            with self.subTest(ex=ex_id):
                self.assertEqual(rep.compiled, ex.starter_compiles, rep.compile_log[:1500])
                self.assertFalse(rep.passed)

    def test_compile_error_exercises_fail_for_the_taught_reason(self):
        expect = {"s0_header": r"redefinition of 'class Pid'",
                  "s0_linker": r"multiple definition of",
                  "s2_const": r"passing 'const JointState'|discards qualifiers"}
        for ex_id, pattern in expect.items():
            with self.subTest(ex=ex_id):
                self.assertRegex(self.starters[ex_id].compile_log, pattern)


if __name__ == "__main__":
    unittest.main()
