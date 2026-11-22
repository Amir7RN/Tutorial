"""Facts the Humanoid Balance pages assert, checked on ctrlcore/upperbody.py,
and the JavaScript port (app/assets/steplab/ub.js) checked against it under node."""
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ctrlcore import robodyn as rd  # noqa: E402
from ctrlcore import upperbody as ub  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
STEPLAB = ROOT / "app" / "assets" / "steplab"

Q = np.array([0.1, -0.2, 0.5, 0.3])
QD = np.array([0.4, -0.3, 1.2, -0.8])


def close(a, b, atol=1e-8):
    return np.allclose(np.asarray(a, float), np.asarray(b, float), atol=atol)


class EquationsOfMotion(unittest.TestCase):
    """The Jacobian derivation agrees with the Newton-Euler recursion of page 136."""

    def setUp(self):
        self.m = ub.PLANES["sagittal"]
        L = self.m.links
        self.arm = rd.PlanarArm(L=[l.L for l in L], m=[l.m for l in L], r=[l.r for l in L], I=[l.I for l in L])
        # PlanarArm measures angles counter-clockwise from +x; this model clockwise from +y
        phi = self.m.angles(Q)
        phi_arm = np.pi / 2 - phi
        self.q_arm = np.diff(np.concatenate([[0.0], phi_arm]))
        self.qd_arm = -QD

    def test_mass_matrix_matches_newton_euler(self):
        M = self.m.mass_matrix(Q)
        self.assertTrue(close(M, self.arm.mass_matrix(self.q_arm)))
        self.assertTrue(close(M, M.T))
        self.assertTrue(np.all(np.linalg.eigvalsh(M) > 0))

    def test_gravity_and_velocity_product_match_newton_euler(self):
        self.assertTrue(close(self.m.gravity(Q), -self.arm.gravity(self.q_arm)))
        c_arm = self.arm.h(self.q_arm, self.qd_arm) - self.arm.gravity(self.q_arm)
        self.assertTrue(close(self.m.velocity_product(Q, QD), -c_arm))

    def test_velocity_product_is_the_christoffel_form(self):
        """c = C(q, qd) qd with C from the Christoffel symbols of M (page 134)."""
        m = self.m
        eps = 1e-6
        n = m.n
        dM = []
        for k in range(n):
            e = np.zeros(n)
            e[k] = eps
            dM.append((m.mass_matrix(Q + e) - m.mass_matrix(Q - e)) / (2 * eps))
        C = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                C[i, j] = sum(0.5 * (dM[k][i, j] + dM[j][i, k] - dM[i][j, k]) * QD[k] for k in range(n))
        self.assertTrue(close(C @ QD, m.velocity_product(Q, QD), atol=1e-6))

    def test_gravity_is_the_potential_gradient(self):
        m = self.m
        eps = 1e-6
        g = np.zeros(m.n)
        for j in range(m.n):
            e = np.zeros(m.n)
            e[j] = eps
            g[j] = (m.energy(Q + e, QD)[1] - m.energy(Q - e, QD)[1]) / (2 * eps)
        self.assertTrue(close(g, m.gravity(Q), atol=1e-6))

    def test_standing_straight_needs_no_torque_and_leaning_needs_a_backward_one(self):
        m = self.m
        self.assertTrue(close(m.gravity(np.zeros(4)), 0))
        g = m.gravity([0.1, 0, 0, 0])
        self.assertLess(g[0], 0)                       # hold a forward lean: pitch back
        self.assertAlmostEqual(g[0], -m.gravity_moment([0.1, 0, 0, 0]), places=9)

    def test_arms_hang_down_and_positive_shoulder_swings_them_back(self):
        p, c = self.m.points(np.zeros(4))
        self.assertLess(p[3][1], p[2][1])              # elbow below the shoulder
        p2, _ = self.m.points([0, 0, 0.5, 0])
        self.assertLess(p2[3][0], p[3][0])             # elbow moved backward (-x)
        p3, _ = self.m.points([0.1, 0, 0, 0])
        self.assertGreater(p3[1][0], 0)                # a positive ankle angle leans forward

    def test_energy_is_conserved_in_a_free_swing(self):
        """No motors, no stops, no ankle: kinetic + potential energy stays put (RK4, 1 ms)."""
        import dataclasses
        m = ub.Model(tuple(dataclasses.replace(l, lo=-1e9, hi=1e9) for l in ub.SAGITTAL), plane="free")
        q0 = np.array([0.0, 0.3, -0.8, 0.2])
        res = ub.simulate(m, ub.Gains(ankle_k=0, ankle_b=0), ub.Push(force=0), active=[1, 2, 3],
                          q0=q0, T=0.6, controller=ub.passive, fall_deg=90)
        E = [sum(m.energy(q, qd)) for q, qd in zip(res["q"], res["qd"])]
        self.assertGreater(np.degrees(np.abs(res["q"]).max()), 90)       # it really swung
        self.assertLess(max(E) - min(E), 1e-4 * max(1.0, abs(E[0])))

    def test_joint_stops_only_dissipate(self):
        """With the stops in place the same swing loses energy and never leaves the ranges by much."""
        m = self.m
        res = ub.simulate(m, ub.Gains(ankle_k=0, ankle_b=0), ub.Push(force=0), active=[1, 2, 3],
                          q0=np.array([0.0, 0.3, -0.8, 0.2]), T=0.6, controller=ub.passive, fall_deg=90)
        E = [sum(m.energy(q, qd)) for q, qd in zip(res["q"], res["qd"])]
        self.assertLess(E[-1], E[0])
        for j, l in enumerate(m.links):
            if j:
                self.assertLess(res["q"][:, j].max(), l.hi + 0.15)
                self.assertGreater(res["q"][:, j].min(), l.lo - 0.15)


class Momentum(unittest.TestCase):
    def setUp(self):
        self.m = ub.PLANES["sagittal"]

    def test_momentum_matrix_times_qdot_is_the_momentum(self):
        m = self.m
        self.assertTrue(close(m.momentum_matrix(Q) @ QD, m.momentum(Q, QD)))
        self.assertTrue(close(m.momentum_matrix(Q, about=(0, 0)) @ QD, m.momentum(Q, QD, about=(0, 0))))
        k = m.core(Q, QD)
        self.assertTrue(close(k.A_O @ QD, m.momentum(Q, QD, about=(0, 0))))
        self.assertAlmostEqual(float(k.link_H.sum()), k.H_O)
        # linear momentum is m_tot times the COM velocity
        _, vc = m.com(Q, QD)
        self.assertTrue(close(k.h[:2], m.m_tot * vc))

    def test_bias_is_the_derivative_of_A_qdot(self):
        m = self.m
        eps = 1e-6
        num = (m.momentum(Q + eps * QD, QD) - m.momentum(Q - eps * QD, QD)) / (2 * eps)
        self.assertTrue(close(m.momentum_bias(Q, QD), num, atol=1e-5))

    def test_centroidal_A_is_the_mass_matrix_without_the_outer_jacobian(self):
        """Row 3 of A about the ankle, contracted with qd, equals the first row of M qd
        when the chain is straight: both are 'the ankle's share' of the same sum."""
        m = self.m
        q = np.zeros(4)
        A_O = m.momentum_matrix(q, about=(0, 0))
        M = m.mass_matrix(q)
        self.assertTrue(close(A_O[2], M[0]))           # H_ankle = M_0j qd_j when q = 0

    def test_internal_torques_cannot_change_momentum_about_the_pivot(self):
        """g = 0, ankle free: any upper-body torques leave H_O constant."""
        m = ub.Model(ub.SAGITTAL, g=0.0, plane="test")
        rng = np.random.default_rng(1)

        def wild(model, q, qd, gains, active=None):
            return np.array([0.0, *rng.uniform(-8, 8, 3)])

        res = ub.simulate(m, ub.Gains(ankle_k=0, ankle_b=0), ub.Push(force=0), q0=[0.2, 0.1, -0.5, 0.3],
                          T=0.5, controller=wild, fall_deg=180)
        self.assertGreater(np.abs(res["qd"][:, 1:]).max(), 1.0)          # the joints really moved
        self.assertLess(np.ptp(res["H_O"]), 1e-4 * max(1.0, np.abs(res["H_O"]).max()))
        self.assertTrue(res["t"][-1] >= 0.5 - 1e-9)

    def test_the_balance_identity(self):
        """dH_O/dt = tau_ankle + m g x_c + (push moment), along a real trajectory."""
        m = self.m
        g = ub.Gains(ankle_k=200, ankle_b=20)
        push = ub.Push(force=50, t0=0.1, duration=0.2)
        res = ub.simulate(m, g, push, active=[1, 2, 3], T=0.5, dt=5e-4, sample=1, fall_deg=90)
        t, H = res["t"], res["H_O"]
        dH = np.gradient(H, t)
        errs = []
        dt = t[1] - t[0]
        for i in range(5, len(t) - 5, 5):
            if min(abs(t[i] - push.t0), abs(t[i] - push.t0 - push.duration)) < 2.5 * dt:
                continue                                    # a step in the push: no derivative there
            q, qd = res["q"][i], res["qd"][i]
            rhs = res["tau"][i][0] + m.gravity_moment(q)            # the ankle torque actually applied
            if push.t0 <= t[i] < push.t0 + push.duration:
                p, _ = m.points(q)
                rhs += ub.pcross(p[push.point][0], p[push.point][1], push.force, 0.0)
            errs.append(abs(dH[i] - rhs))
            # a numerical derivative straddling a saturation or push edge is allowed to be off
            self.assertLess(abs(dH[i] - rhs), 0.15 * max(1.0, abs(rhs)))
        self.assertLess(np.mean(errs), 0.05)
        self.assertGreater(np.abs(dH).max(), 30)                     # the identity was tested on real motion

    def test_the_arms_count_by_where_they_move_not_by_how_they_spin(self):
        """Swing the hanging arms forward (negative shoulder rate). Their own spin
        is backward, but their mass moves forward one metre above the pivot, so
        their share of H about the ankle is forward (positive). With H_O fixed
        the legs then have to take backward momentum: the legs rotate back."""
        m = self.m
        qd = np.array([0.0, 0.0, -3.0, 0.0])
        lh = m.link_momenta(np.zeros(4), qd)
        self.assertGreater(lh[2], 0)
        self.assertGreater(lh[3], 0)
        # the spin part alone is negative and small
        self.assertLess(m.links[2].I * qd[2], 0)
        self.assertLess(abs(m.links[2].I * qd[2]), 0.1 * lh[2])
        A_O = m.momentum_matrix(np.zeros(4), about=(0, 0))
        self.assertLess(A_O[2, 2], 0)                   # positive shoulder rate = arms back = backward H
        qd0 = -(A_O[2, 2] * qd[2]) / A_O[2, 0]
        self.assertLess(qd0, 0)                         # the legs rotate backward


class Locks(unittest.TestCase):
    def test_locking_deletes_columns(self):
        m = ub.PLANES["sagittal"]
        q = np.array([0.1, -0.2, 0.5, 0.0])
        qd = np.array([0.4, -0.3, 1.2, 0.0])
        L = m.locked(q, qd, [0, 1, 2])
        S = L["S"]
        self.assertTrue(close(L["M"], S.T @ m.mass_matrix(q) @ S))
        self.assertEqual(L["M"].shape, (3, 3))
        self.assertTrue(close(L["A"], m.momentum_matrix(q) @ S))

    def test_an_elbow_locked_straight_is_the_frontal_arm(self):
        """Merging upper arm and forearm by hand gives the FRONTAL arm's m, r, I."""
        sag, fro = ub.PLANES["sagittal"], ub.PLANES["frontal"]
        q = np.array([0.1, -0.2, 0.5, 0.0])
        qd = np.array([0.4, -0.3, 1.2, 0.0])
        L = sag.locked(q, qd, [0, 1, 2])
        self.assertTrue(close(L["M"], fro.mass_matrix(q[:3]), atol=2e-3))
        self.assertTrue(close(L["g"], fro.gravity(q[:3]), atol=2e-3))
        self.assertTrue(close(L["c"], fro.velocity_product(q[:3], qd[:3]), atol=2e-3))

    def test_simulator_holds_locked_joints_exactly(self):
        m = ub.PLANES["sagittal"]
        res = ub.simulate(m, ub.Gains(), ub.Push(force=60), active=[1], T=0.6)
        self.assertTrue(np.all(res["q"][:, 2:] == 0))
        self.assertTrue(np.all(res["qd"][:, 2:] == 0))
        self.assertTrue(np.any(np.abs(res["tau"][:, 2:]) > 0))   # but they carry torque


@unittest.skipIf(shutil.which("node") is None, "node not installed")
class JavaScriptPort(unittest.TestCase):
    SCRIPT = r"""
const UB = require(process.argv[2]);
const m = UB.planes.sagittal, q = [0.1, -0.2, 0.5, 0.3], qd = [0.4, -0.3, 1.2, -0.8];
const k = UB.core(m, q, qd), kO = UB.core(m, q, qd, {about: [0, 0]});
const g = UB.gains(), push = UB.push({force: 70});
const res = UB.simulate(m, UB.gains({law: 'momentum'}), push, [1, 2, 3], {T: 0.6});
const resL = UB.simulate(m, g, push, [1, 2, 3], {T: 1.5});
const lock = UB.locked(m, [0.1, -0.2, 0.5, 0.0], [0.4, -0.3, 1.2, 0.0], [0, 1, 2]);
const xs = [0.05, -0.1, 0.2, -0.3], xds = [0.3, 0.1, -0.5, 0.2];
const lq = UB.controlStep(m, xs, xds, g, [1, 2, 3]);
const cw = UB.controlStep(m, xs, xds, UB.gains({law: 'counterweight'}), [1, 2, 3]);
const mo = UB.controlStep(m, xs, xds, UB.gains({law: 'momentum'}), [1, 2, 3]);
const K = UB.lqrGain(m, g, [1, 2, 3]).K;
console.log(JSON.stringify({M: k.M, g: k.g, c: k.cvec, A: k.A, bias: k.bias, A_O: kO.A, H_O: k.H_O, link_H: k.link_H,
  xc: k.xc, vc: k.vc, lockM: lock.M, lockA: lock.A, lq, cw, mo, K,
  q_end: res.q[res.q.length - 1], H_end: res.H_O[res.H_O.length - 1], n: res.t.length, peak: res.peak_lean_deg,
  peakL: resL.peak_lean_deg, fellL: resL.fell, q_endL: resL.q[resL.q.length - 1]}));
"""

    def test_ub_js_matches_the_python_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = os.path.join(tmp, "t.js")
            with open(script, "w", encoding="utf-8") as f:
                f.write(self.SCRIPT)
            out = subprocess.run(["node", script, str(STEPLAB / "ub.js")], capture_output=True, text=True, timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr)
        o = json.loads(out.stdout)
        m = ub.PLANES["sagittal"]
        k = m.core(Q, QD)
        kO = m.core(Q, QD, about=(0, 0))
        for name, mine in (("M", k.M), ("g", k.g), ("c", k.cvec), ("A", k.A), ("bias", k.bias), ("A_O", kO.A),
                           ("link_H", k.link_H), ("xc", k.xc), ("vc", k.vc)):
            self.assertTrue(close(o[name], mine, atol=1e-9), name)
        self.assertAlmostEqual(o["H_O"], k.H_O)
        L = m.locked([0.1, -0.2, 0.5, 0.0], [0.4, -0.3, 1.2, 0.0], [0, 1, 2])
        self.assertTrue(close(o["lockM"], L["M"]))
        self.assertTrue(close(o["lockA"], L["A"]))
        qs, qds = [0.05, -0.1, 0.2, -0.3], [0.3, 0.1, -0.5, 0.2]
        self.assertTrue(close(o["cw"], ub.control_step(m, qs, qds, ub.Gains(law="counterweight"), active=[1, 2, 3]), atol=1e-7))
        self.assertTrue(close(o["mo"], ub.control_step(m, qs, qds, ub.Gains(law="momentum"), active=[1, 2, 3]), atol=1e-6))
        # the LQR gain comes from an iterated Riccati equation in the browser: within 0.2 %
        K = ub.lqr_gain(m, ub.Gains(), [1, 2, 3])[0]
        self.assertLess(np.abs(np.array(o["K"]) - K).max(), 2e-3 * np.abs(K).max())
        lq = ub.control_step(m, qs, qds, ub.Gains(), active=[1, 2, 3])
        self.assertLess(np.abs(np.array(o["lq"]) - lq).max(), 2e-3 * max(1.0, np.abs(lq).max()))
        res = ub.simulate(m, ub.Gains(law="momentum"), ub.Push(force=70), active=[1, 2, 3], T=0.6)
        self.assertEqual(o["n"], len(res["t"]))
        self.assertTrue(close(o["q_end"], res["q"][-1], atol=1e-6))
        self.assertAlmostEqual(o["H_end"], res["H_O"][-1], places=5)
        self.assertAlmostEqual(o["peak"], res["peak_lean_deg"], places=4)
        resL = ub.simulate(m, ub.Gains(), ub.Push(force=70), active=[1, 2, 3], T=1.5)
        self.assertEqual(o["fellL"], resL["fell"])
        self.assertAlmostEqual(o["peakL"], resL["peak_lean_deg"], delta=0.05)
        self.assertTrue(close(o["q_endL"], resL["q"][-1], atol=2e-3))


class Recovery(unittest.TestCase):
    """The numbers page 169 quotes: the ankle alone falls at 75 N, the upper body stands at 80 N (slow)."""

    def test_the_upper_body_extends_the_recoverable_push(self):
        m = ub.PLANES["sagittal"]
        g = ub.Gains()
        self.assertEqual(g.law, "lqr")
        self.assertAlmostEqual(m.tau_ankle_max(), m.m_tot * 9.81 * 0.10)
        locked_70 = ub.simulate(m, g, ub.Push(force=70), active=[], T=3.0)
        upper_70 = ub.simulate(m, g, ub.Push(force=70), active=[1, 2, 3], T=3.0)
        self.assertFalse(locked_70["fell"])
        self.assertFalse(upper_70["fell"])
        self.assertLess(upper_70["peak_lean_deg"], locked_70["peak_lean_deg"] - 1.0)
        self.assertLess(abs(math.degrees(upper_70["q"][-1][0])), 0.5)          # back upright
        locked_75 = ub.simulate(m, g, ub.Push(force=75), active=[], T=3.0)
        upper_80 = ub.simulate(m, g, ub.Push(force=80), active=[1, 2, 3], T=3.0)
        self.assertTrue(locked_75["fell"])
        self.assertFalse(upper_80["fell"])
        from app.pages.humanoid_balance import RECOVERY_TABLE
        rows = {F: (a, b) for F, a, b in RECOVERY_TABLE}
        self.assertIn("falls", rows[75][0])
        self.assertIn("stands", rows[80][1])
        self.assertIn(f"{locked_70['peak_lean_deg']:.1f}", rows[70][0])
        self.assertIn(f"{upper_70['peak_lean_deg']:.1f}", rows[70][1])

    def test_torques_stay_inside_the_limits(self):
        m = ub.PLANES["sagittal"]
        g = ub.Gains()
        res = ub.simulate(m, g, ub.Push(force=80), active=[1, 2, 3], T=1.0)
        lim = np.array(g.tau_max)
        self.assertTrue(np.all(np.abs(res["tau"][:, 1:]) <= lim[1:] + 1e-9))
        self.assertTrue(np.all(np.abs(res["tau"][:, 0]) <= m.tau_ankle_max() + 1e-9))
        self.assertGreater(np.abs(res["tau"][:, 1]).max(), 20)                 # the waist really worked

    def test_momentum_law_runs_and_box_qp_is_consistent(self):
        m = ub.PLANES["sagittal"]
        g = ub.Gains(law="momentum")
        q, qd = np.array([0.06, 0.0, 0.0, 0.0]), np.array([0.5, 0.0, 0.0, 0.0])
        tau, d = ub.recovery_step(m, q, qd, g, active=[1, 2, 3], detail=True)
        self.assertTrue(np.all(np.abs(tau[1:]) <= np.array(g.tau_max[1:]) + 1e-9))
        # the QP's answer is never worse than clipping the unconstrained answer
        R = np.array([[1.0, 0.0], [0.0, 1.0], [0.3, 0.3]])
        r0 = np.array([-5.0, 2.0, 1.0])
        x, _ = ub.box_qp(R, r0, np.array([-1.0, -1.0]), np.array([1.0, 1.0]))
        unc = np.linalg.lstsq(R, -r0, rcond=None)[0]
        self.assertLessEqual(np.sum((R @ x + r0) ** 2), np.sum((R @ np.clip(unc, -1, 1) + r0) ** 2) + 1e-12)
        self.assertTrue(np.all(np.abs(x) <= 1 + 1e-9))


class Pages(unittest.TestCase):
    """The five pages build offscreen, their labs exist and load only local scripts."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_pages_build_and_are_numbered_after_the_cpp_chapter(self):
        import re
        from app.pages import LESSON_CLASSES
        from app.pages.humanoid_balance import BALANCE_PAGES
        from app import theme
        nums = [c.NUM for c in BALANCE_PAGES]
        self.assertEqual(nums, list(range(nums[0], nums[0] + len(BALANCE_PAGES))))
        self.assertEqual(nums[0], max(c.NUM for c in LESSON_CLASSES if c not in BALANCE_PAGES) + 1)
        self.assertEqual(theme.group_of(BALANCE_PAGES[0].SECTION), "Humanoid Balance")
        for name in ("g1_upper_body.html", "upper_body_lagrange.html", "upper_body_recovery.html",
                     "lqr_torque_flow.html", "riccati_tutor.html", "kalman_encoder.html",
                     "riccati_physical.html", "lqr_bellman.html", "kalman_mirror.html"):
            src = open(STEPLAB / name, encoding="utf-8").read()
            for s in re.findall(r'<script src="([^"]+)"', src):
                self.assertFalse(s.startswith("http"), name)
                self.assertTrue((STEPLAB / s).exists(), f"{name}: {s}")
        for cls in BALANCE_PAGES:
            page = cls()
            self.assertTrue(page.NO_RECAP)
            page.deleteLater()

    def test_lqr_lab_script_parses(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        for name in ("lqr_torque_flow.html", "riccati_tutor.html", "kalman_encoder.html",
                     "riccati_physical.html", "lqr_bellman.html", "kalman_mirror.html"):
            src = (STEPLAB / name).read_text(encoding="utf-8")
            js = src.split("<script>")[1].split("</script>")[0]
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
                f.write("new Function(" + json.dumps(js) + ");")
            try:
                r = subprocess.run([node, f.name], capture_output=True, text=True)
            finally:
                os.unlink(f.name)
            self.assertEqual(r.returncode, 0, f"{name}: {r.stderr}")

    def test_lqr_page_story_matches_the_simulation(self):
        from app.pages.humanoid_balance import LQR_STORY as st, lqr_numbers
        n = lqr_numbers()
        m, g, K = n["m"], n["g"], n["K"]
        # P solves the Riccati equation and gives the same K
        A, B, Q, R, P = n["A"], n["B"], n["Q"], n["R"], n["P"]
        res_care = A.T @ P + P @ A - P @ B @ np.linalg.inv(R) @ B.T @ P + Q
        self.assertLess(np.abs(res_care).max(), 1e-6 * np.abs(P).max())
        np.testing.assert_allclose(np.linalg.inv(R) @ B.T @ P, K, atol=1e-6)
        # the analytic A at standing equals the finite-difference one
        Mi, G = n["Minv"], n["G"]
        np.testing.assert_allclose(A[4:, :4], -Mi @ (G + np.diag([g.ankle_k, 0, 0, 0])), atol=1e-3)
        np.testing.assert_allclose(B[4:], Mi[:, 1:], atol=1e-6)
        r = ub.simulate(m, g, ub.Push(force=70), active=[1, 2, 3], T=1.2, sample=1)
        lk = ub.simulate(m, g, ub.Push(force=70), active=[], T=1.2, sample=1)
        self.assertAlmostEqual(r["peak_lean_deg"], st["peak"], delta=0.05)
        self.assertAlmostEqual(lk["peak_lean_deg"], st["locked_peak"], delta=0.05)
        t = np.array(r["t"]); tau = np.array(r["tau"]); q = np.array(r["q"]); qd = np.array(r["qd"])
        self.assertAlmostEqual(t[np.argmax(np.abs(q[:, 0]))], st["t_peak"], delta=0.01)
        sat = t[np.abs(tau[:, 0]) >= m.tau_ankle_max() - 1e-6]
        self.assertAlmostEqual(sat[0], st["sat"][0], delta=0.01)
        self.assertAlmostEqual(sat[-1], st["sat"][1], delta=0.01)
        self.assertAlmostEqual(t[(t > 0.25) & (tau[:, 1] > 0)][0], st["flip"], delta=0.01)
        i = 250
        x = np.concatenate([q[i], qd[i]])
        np.testing.assert_allclose(-K[0] * x, st["waist_terms_025"], atol=0.06)
        self.assertAlmostEqual(tau[i, 1], st["waist_025"], delta=0.06)
        for i, want in ((250, st["qdd0_025"]), (400, st["qdd0_040"])):
            k = m.core(q[i], qd[i])
            Mi = np.linalg.inv(k.M)
            fp = m.point_jacobian(q[i], 2)[0] * 70 if 200 <= i < 300 else np.zeros(4)
            parts = list(Mi[0] * tau[i]) + [Mi[0] @ -k.g, Mi[0] @ fp]
            total = Mi[0] @ (tau[i] + fp - k.g - k.cvec)
            np.testing.assert_allclose(parts + [total], want, atol=0.01)
        self.assertAlmostEqual(np.degrees(q[400, 0] + q[400, 1]), st["torso_back"], delta=0.1)

    def test_momentum_page_simulation_button(self):
        from app.pages.humanoid_balance import UpperBodyMomentumPage
        page = UpperBodyMomentumPage()
        page.sim_btn.click()
        self.assertIn("recovered", page.sim_out.text())
        self.assertIn("H arms", page.sim_out.text())
        page.deleteLater()


if __name__ == "__main__":
    unittest.main()
