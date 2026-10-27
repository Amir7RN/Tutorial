"""Step labs (app/assets/steplab): files, offline scripts, mr.js vs ctrlcore, page wiring."""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from app.widgets.step_lab import STEPLAB_DIR, STEP_LABS, lab_path

NODE_SCRIPT = r"""
const MR = require(process.argv[2]);
const q = [0.3, 0.5, 0.2, -0.4];
const B = MR.RRPR.S.map(s => MR.mv(MR.adj(MR.invT(MR.RRPR.M)), s));
const arm = MR.arm({L: [1, 0.8], m: [2, 1.5], r: [0.5, 0.4], I: [0.17, 0.08]});
const qq = [0.4, 0.9], qd = [1.2, -0.7];
const lg = MR.logT(MR.fkSpace(MR.RRPR.M, MR.RRPR.S, q)), th = MR.norm(lg.slice(0, 3));
console.log(JSON.stringify({
  T: MR.fkSpace(MR.RRPR.M, MR.RRPR.S, q), Tb: MR.fkBody(MR.RRPR.M, B, q),
  Js: MR.jacSpace(MR.RRPR.S, q), Jb: MR.jacBody(B, q),
  Tlog: MR.expTwist(MR.scl(lg, 1 / th), th),
  tau: MR.rnea(arm, qq, qd, [0.3, -0.5], {ftip: [2, -1]}), M: MR.massMatrix(arm, qq),
  C: MR.coriolis(arm, qq, qd), fd: MR.forwardDyn(arm, qq, qd, [1, 2]),
  P: MR.pinv([[-1, -1, 0], [2, 1, 1]]), eig: MR.eigSym([[5, 3, 2], [3, 2, 1], [2, 1, 1]]).vals,
}));
"""


class FileTests(unittest.TestCase):
    def test_every_lab_exists_and_loads_only_local_scripts(self):
        for name, (html, title) in STEP_LABS.items():
            path = lab_path(html)
            self.assertTrue(os.path.exists(path), f"{name}: {html} missing")
            src = open(path, encoding="utf-8").read()
            for s in re.findall(r'<script src="([^"]+)"', src):
                self.assertFalse(s.startswith("http"), f"{html} loads {s} from the network")
                self.assertTrue(os.path.exists(os.path.join(STEPLAB_DIR, s)), f"{html}: {s} missing")
            self.assertTrue(title)

    def test_labs_are_unique_per_page(self):
        files = [h for h, _ in STEP_LABS.values()]
        self.assertEqual(len(files), len(set(files)))


@unittest.skipIf(shutil.which("node") is None, "node not installed")
class MrJsTests(unittest.TestCase):
    def test_mr_js_matches_ctrlcore(self):
        from ctrlcore import robodyn as rd
        from ctrlcore import robokin as rk
        from ctrlcore import rrpr_check as rc
        with tempfile.TemporaryDirectory() as tmp:
            script = os.path.join(tmp, "t.js")
            with open(script, "w", encoding="utf-8") as f:
                f.write(NODE_SCRIPT)
            out = subprocess.run(["node", script, os.path.join(STEPLAB_DIR, "mr.js")],
                                 capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        o = json.loads(out.stdout)
        q = np.array([0.3, 0.5, 0.2, -0.4])
        T = rk.fk_space(rc.M_HOME, rc.S_LIST, q)
        arm = rd.PlanarArm(L=[1, 0.8], m=[2, 1.5], r=[0.5, 0.4], I=[0.17, 0.08])
        qq, qd = [0.4, 0.9], [1.2, -0.7]
        close = lambda a, b: self.assertTrue(np.allclose(np.array(a, float), np.array(b, float), atol=1e-7))
        close(o["T"], T)
        close(o["Tb"], rk.fk_body(rc.M_HOME, rc.B_LIST, q))
        close(np.array(o["Js"]).T, rk.jacobian_space(rc.S_LIST, q))
        close(np.array(o["Jb"]).T, rk.jacobian_body(rc.B_LIST, q))
        close(o["Tlog"], T)
        close(o["tau"], arm.rnea(qq, qd, [0.3, -0.5], f_tip=[2, -1]))
        close(o["M"], arm.mass_matrix(qq))
        close(o["C"], arm.coriolis_matrix(qq, qd))
        close(o["fd"], arm.forward_dynamics(qq, qd, [1, 2]))
        close(o["P"], np.linalg.pinv([[-1, -1, 0], [2, 1, 1]]))
        close(o["eig"], np.sort(np.linalg.eigvalsh([[5, 3, 2], [3, 2, 1], [2, 1, 1]]))[::-1])


class PageTests(unittest.TestCase):
    def test_pages_show_the_lab_instead_of_the_movie(self):
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: F401
        except ImportError:
            self.skipTest("no Qt WebEngine")
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication
        QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
        app = QApplication.instance() or QApplication([])
        from app.pages import LESSON_CLASSES
        for cls in LESSON_CLASSES:
            if cls.__name__ in ("LagrangePage", "NullSpacePage", "PoEPage"):
                p = cls()
                self.assertTrue(hasattr(p, "step_lab"), cls.__name__)
                self.assertFalse(hasattr(p, "lesson_animation"), cls.__name__)
                p.close()


if __name__ == "__main__":
    unittest.main()
