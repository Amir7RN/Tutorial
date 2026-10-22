"""C++ workshop 2 (page 131): grader, reference solution, starter, page."""

import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from ctrlcore import robokin as rk
from ctrlcore import rrpr2_check as r2


def _run(workbook, tmp, args=()):
    harness = os.path.join(tmp, "h.cpp")
    exe = os.path.join(tmp, "h.exe")
    with open(harness, "w", encoding="utf-8") as f:
        f.write(r2.harness_source(workbook))
    r = subprocess.run(r2.compile_command(r2.find_gxx(), harness, exe), capture_output=True, text=True)
    if r.returncode:
        raise AssertionError(r.stdout + r.stderr)
    out = subprocess.run([exe, *args], capture_output=True, text=True, timeout=30).stdout
    return r2.parse_output(out)[0]


class GraderTests(unittest.TestCase):
    def test_references_are_consistent(self):
        q = r2.P1
        Jp = r2.tool_point_jacobian(q)
        # finite-difference check of the tool-point Jacobian
        h = 1e-6
        for i in range(4):
            e = np.zeros(4)
            e[i] = h
            d = (rk.fk_space(r2.M_HOME, r2.S_LIST, q + e)[:3, 3]
                 - rk.fk_space(r2.M_HOME, r2.S_LIST, q - e)[:3, 3]) / (2 * h)
            self.assertTrue(np.allclose(d, Jp[:, i], atol=1e-6))
        self.assertTrue(np.allclose(Jp @ r2.null_motion(q, np.array([0.3, -0.2, 0.5, 1.0])), 0, atol=1e-12))
        qd = np.array([0.5, 0.6, 0.3, 0.8])
        Tsd = rk.fk_body(r2.M_HOME, r2.B_LIST, qd)
        sol = r2.ik_newton(Tsd, qd - 0.2)
        self.assertTrue(np.allclose(rk.fk_body(r2.M_HOME, r2.B_LIST, sol), Tsd, atol=1e-9))

    def test_known_mistake_is_named(self):
        t = next(t for t in r2.TESTS if t.tag == "holdP1")
        self.assertIn("moment", r2.grade(t, t.wrongs[0][0]).why)
        self.assertTrue(r2.grade(t, t.expected).ok)

    def test_blocking_and_solution_blocks(self):
        self.assertEqual(r2.blocking(10, {7: False}), [7, 8, 9])
        for ex in r2.EXERCISES:
            self.assertIn("(", r2.solution_block(ex))


@unittest.skipIf(r2.find_gxx() is None, "no g++")
class CompileTests(unittest.TestCase):
    def test_solution_passes_everything(self):
        with tempfile.TemporaryDirectory() as tmp:
            res = r2.grade_all(_run(r2.SOLUTION, tmp))
            self.assertEqual([r.test.tag for r in res if not r.ok], [])
            qd, g = [0.7, 0.4, 0.25, -0.3], [0.5, 0.3, 0.1, 0.0]
            pose = _run(r2.SOLUTION, tmp, tuple(map(str, qd + g)))
            Tsd = rk.fk_body(r2.M_HOME, r2.B_LIST, qd)
            self.assertTrue(np.allclose(rk.fk_body(r2.M_HOME, r2.B_LIST, pose["pose_ik"]), Tsd, atol=1e-8))
            self.assertTrue(np.allclose(pose["pose_mu"], r2.manip(np.array(g))))

    def test_starter_compiles_and_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            res = r2.grade_all(_run(r2.STARTER, tmp))
            self.assertFalse(any(r.ok for r in res))


class PageTests(unittest.TestCase):
    def test_page_builds_without_compiling(self):
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        from app.pages import RRPRWorkshop2Page, LESSON_CLASSES
        self.assertEqual(LESSON_CLASSES.index(RRPRWorkshop2Page) + 1, 131)
        p = RRPRWorkshop2Page()
        self.assertEqual(len(p.ex_cards), 11)
        self.assertIsNone(p.ws._proc)
        self.assertTrue(p.ws.exe.endswith(("harness2.exe", "harness2")))
        p.close()


if __name__ == "__main__":
    unittest.main()
