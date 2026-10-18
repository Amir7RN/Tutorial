"""The C++ RRPR workshop (page 125): grader, reference solution, starter, page."""

import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from ctrlcore import robokin as rk
from ctrlcore import rrpr_check as rc


def _run(workbook, tmp, args=()):
    harness = os.path.join(tmp, "h.cpp")
    exe = os.path.join(tmp, "h.exe")
    with open(harness, "w", encoding="utf-8") as f:
        f.write(rc.harness_source(workbook))
    r = subprocess.run(rc.compile_command(rc.find_gxx(), harness, exe), capture_output=True, text=True)
    if r.returncode:
        raise AssertionError(r.stdout + r.stderr)
    out = subprocess.run([exe, *args], capture_output=True, text=True, timeout=20).stdout
    return rc.parse_output(out)[0]


class GraderTests(unittest.TestCase):
    def test_reference_geometry(self):
        self.assertTrue(np.allclose(rc.S_LIST[:, 1], [0, -1, 0, 1, 0, 0]))
        self.assertTrue(np.allclose(rc.S_LIST[:, 3], [1, 0, 0, 0, 1, 0]))
        # straight up: roll axis lies on the waist axis, columns 1 and 4 coincide
        Js = rk.jacobian_space(rc.S_LIST, [0.2, np.pi / 2, 0.3, 0.1])
        self.assertTrue(np.allclose(Js[:, 0], Js[:, 3]))

    def test_known_mistake_is_named(self):
        t = next(t for t in rc.TESTS if t.tag == "rev0")
        wrong = t.wrongs[0][0]
        self.assertIn("−ω × q", rc.grade(t, wrong).why)
        self.assertTrue(rc.grade(t, t.expected).ok)

    def test_blocking(self):
        self.assertEqual(rc.blocking(7, {1: True, 2: False}), [2, 3, 4, 5, 6])
        self.assertEqual(rc.blocking(1, {}), [])

    def test_solution_blocks_exist(self):
        for ex in rc.EXERCISES:
            self.assertIn("(", rc.solution_block(ex))


@unittest.skipIf(rc.find_gxx() is None, "no g++")
class CompileTests(unittest.TestCase):
    def test_solution_passes_everything(self):
        with tempfile.TemporaryDirectory() as tmp:
            vals = _run(rc.SOLUTION, tmp)
            res = rc.grade_all(vals)
            self.assertEqual([r.test.tag for r in res if not r.ok], [])
            pose = _run(rc.SOLUTION, tmp, ("0.3", "0.5", "0.2", "-0.4"))
            T = rk.fk_space(rc.M_HOME, rc.S_LIST, [0.3, 0.5, 0.2, -0.4])
            self.assertTrue(np.allclose(pose["pose_fkb"].reshape(4, 4), T))

    def test_starter_compiles_and_fails_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            res = rc.grade_all(_run(rc.STARTER, tmp))
            self.assertFalse(any(r.ok for r in res))
            self.assertTrue(all("TODO" in r.why for r in res))


class PageTests(unittest.TestCase):
    def test_page_builds_without_compiling(self):
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        from app.pages import RRPRWorkshopPage, LESSON_CLASSES
        self.assertEqual(LESSON_CLASSES.index(RRPRWorkshopPage) + 1, 125)
        p = RRPRWorkshopPage()
        self.assertEqual(len(p.ex_cards), 10)
        self.assertIsNone(p.ws._proc)
        p.close()


if __name__ == "__main__":
    unittest.main()
