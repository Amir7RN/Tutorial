"""Facts the Robot Mechanics pages assert: kinematics, dynamics, planning, control."""
import math
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ctrlcore import robokin as rk  # noqa: E402
from ctrlcore import robodyn as rd  # noqa: E402


class ConfigurationSpaceTests(unittest.TestCase):
    def test_grubler_classic_mechanisms(self):
        self.assertEqual(rk.grubler(4, [1] * 4, 3), 1)          # four-bar
        self.assertEqual(rk.grubler(5, [1] * 5, 3), 2)          # five-bar
        # Stewart platform: 14 links, 6 U (2), 6 P (1), 6 S (3)
        self.assertEqual(rk.grubler(14, [2] * 6 + [1] * 6 + [3] * 6, 6), 6)
        self.assertEqual(rk.grubler(7, [1] * 6, 6), 6)          # 6R open chain

    def test_four_bar_closes(self):
        A, B = rk.four_bar(0.7, 1.0, 2.5, 2.0, 3.0)
        self.assertAlmostEqual(np.linalg.norm(B - A), 2.5)
        self.assertAlmostEqual(np.linalg.norm(B - np.array([3.0, 0])), 2.0)


class RigidBodyTests(unittest.TestCase):
    def test_rotation_exp_log_round_trip(self):
        for wt in ([0.3, -0.2, 0.9], [0, 0, 2.5], [1, 1, 0]):
            R = rk.rot_exp(wt)
            self.assertTrue(np.allclose(R @ R.T, np.eye(3)))
            self.assertAlmostEqual(np.linalg.det(R), 1.0)
            self.assertTrue(np.allclose(rk.rot_log(R), wt))

    def test_se3_exp_log_round_trip(self):
        S = rk.screw_axis([0.2, -0.4, 0.1], [0, 0.6, 0.8], h=0.3)
        T = rk.exp6(S, 1.1)
        S2, th = rk.log6(T)
        self.assertTrue(np.allclose(rk.exp6(S2, th), T))

    def test_adjoint_maps_twists(self):
        T = rk.exp6(rk.screw_axis([1, 0, 0], [0, 0, 1]), 0.6)
        V_b = np.array([0.1, 0.2, 0.3, 1, 2, 3])
        lhs = rk.twist_hat(rk.adjoint(T) @ V_b)
        self.assertTrue(np.allclose(lhs, T @ rk.twist_hat(V_b) @ rk.inv_T(T)))


class KinematicsTests(unittest.TestCase):
    L = [1.0, 0.8, 0.5]

    def test_poe_matches_planar_trig(self):
        S, M = rk.planar_screws(self.L)
        q = [0.4, -0.9, 1.3]
        T = rk.fk_space(M, S, q)
        self.assertTrue(np.allclose(T[:2, 3], rk.planar_points(self.L, q)[-1]))
        B = rk.adjoint(rk.inv_T(M)) @ S
        self.assertTrue(np.allclose(rk.fk_body(M, B, q), T))

    def test_jacobians_agree(self):
        S, M = rk.planar_screws(self.L)
        q = np.array([0.4, -0.9, 1.3])
        Js = rk.jacobian_space(S, q)
        B = rk.adjoint(rk.inv_T(M)) @ S
        Jb = rk.jacobian_body(B, q)
        T = rk.fk_space(M, S, q)
        self.assertTrue(np.allclose(rk.adjoint(T) @ Jb, Js))
        # finite difference of the tip
        eps = 1e-6
        Jfd = np.column_stack([(rk.planar_points(self.L, q + eps * e)[-1]
                                - rk.planar_points(self.L, q - eps * e)[-1]) / (2 * eps)
                               for e in np.eye(3)])
        self.assertTrue(np.allclose(rk.planar_jacobian(self.L, q), Jfd, atol=1e-6))

    def test_singularity_of_straight_2r(self):
        J = rk.planar_jacobian([1, 1], [0.3, 0.0])
        self.assertLess(abs(np.linalg.det(J)), 1e-12)
        self.assertAlmostEqual(np.linalg.det(rk.planar_jacobian([1, 1], [0.3, 0.5])),
                               math.sin(0.5))

    def test_statics_power_balance(self):
        q = np.array([0.2, 0.9, -0.4])
        J = rk.planar_jacobian(self.L, q)
        F = np.array([3.0, -2.0])
        qd = np.array([0.5, -1.0, 2.0])
        self.assertAlmostEqual((J.T @ F) @ qd, F @ (J @ qd))

    def test_ik_analytic_and_newton(self):
        for elbow in (1, -1):
            q = rk.ik_2r(1.0, 0.7, 0.9, 0.8, elbow)
            self.assertTrue(np.allclose(rk.planar_points([1, .7], q)[-1], [0.9, 0.8]))
        self.assertIsNone(rk.ik_2r(1, 1, 2.5, 0))
        q, _, errs = rk.ik_newton(self.L, [1.2, 0.9], [0.1, 0.5, 0.5])
        self.assertLess(errs[-1], 1e-6)
        self.assertTrue(np.allclose(rk.planar_points(self.L, q)[-1], [1.2, 0.9]))

    def test_null_space_motion_holds_the_tip(self):
        q = np.array([0.3, 0.8, -0.6])
        J = rk.planar_jacobian(self.L, q)
        N = rk.null_projector(J)
        self.assertTrue(np.allclose(J @ N, 0))
        self.assertTrue(np.allclose(N @ N, N))
        self.assertEqual(np.linalg.matrix_rank(N, tol=1e-9), 1)


class DynamicsTests(unittest.TestCase):
    arm = rd.PlanarArm(L=[1.0, 0.8], m=[2.0, 1.5], r=[0.45, 0.35], I=[0.2, 0.1])

    def test_rnea_matches_lagrange(self):
        q, qd, qdd = np.array([0.4, 1.1]), np.array([-0.7, 1.9]), np.array([0.3, -2.0])
        M, c, g = rd.lagrange_2r(self.arm, q, qd)
        self.assertTrue(np.allclose(self.arm.mass_matrix(q), M))
        self.assertTrue(np.allclose(self.arm.gravity(q), g))
        self.assertTrue(np.allclose(self.arm.rnea(q, qd, qdd), M @ qdd + c + g))

    def test_mass_matrix_properties(self):
        arm3 = rd.PlanarArm(L=[1, .8, .5], m=[2, 1.5, .8])
        q, qd = np.array([0.3, -1.0, 0.6]), np.array([1.0, -0.5, 2.0])
        M = arm3.mass_matrix(q)
        self.assertTrue(np.allclose(M, M.T))
        self.assertGreater(np.linalg.eigvalsh(M).min(), 0)
        self.assertTrue(np.allclose(M, arm3.mass_matrix_jacobian(q)))
        C = arm3.coriolis_matrix(q, qd)
        self.assertTrue(np.allclose(C @ qd, arm3.h(q, qd) - arm3.gravity(q), atol=1e-6))
        S = arm3.Mdot(q, qd) - 2 * C
        self.assertTrue(np.allclose(S, -S.T, atol=1e-6))

    def test_forward_inverse_round_trip_and_energy(self):
        q, qd, tau = np.array([0.4, 1.1]), np.array([-0.7, 1.9]), np.array([3.0, -1.0])
        qdd = self.arm.forward_dynamics(q, qd, tau)
        self.assertTrue(np.allclose(self.arm.rnea(q, qd, qdd), tau))
        ts, Q, QD, _ = rd.simulate(self.arm, [0.5, 0.5], [0, 0], 2.0, 0.002)
        E = [sum(self.arm.energy(a, b)) for a, b in zip(Q, QD)]
        self.assertLess(max(E) - min(E), 1e-4)

    def test_task_space_inertia_and_consistency(self):
        q, qd = np.array([0.4, 1.1]), np.array([-0.7, 1.9])
        Lam, Jbar, mu, p = self.arm.task_space(q, qd)
        J = self.arm.jacobian(q)
        self.assertTrue(np.allclose(J @ Jbar, np.eye(2)))
        M = self.arm.mass_matrix(q)
        self.assertTrue(np.allclose(np.linalg.inv(J).T @ M @ np.linalg.inv(J), Lam))

    def test_time_scalings_hit_end_conditions(self):
        for fn in (rd.cubic, rd.quintic):
            s, sd, sdd = fn(np.array([0.0, 2.0]), 2.0)
            self.assertTrue(np.allclose(s, [0, 1]))
            self.assertTrue(np.allclose(sd, [0, 0]))
        s, sd, sdd = rd.quintic(np.array([0.0, 2.0]), 2.0)
        self.assertTrue(np.allclose(sdd, [0, 0]))
        s, sd, sdd, T = rd.trapezoid(np.array([0.0, 0.5, 100.0]), 0.8, 2.0)
        self.assertAlmostEqual(float(s[-1]), 1.0)
        self.assertAlmostEqual(T, (2.0 + 0.64) / 1.6)

    def test_time_optimal_respects_limits(self):
        res = rd.time_optimal_line(self.arm, [-1.0, 0.5], [1.0, -0.5], [40, 15], ns=200)
        self.assertGreater(res["T"], 0)
        self.assertTrue(np.all(res["profile"] <= res["vlc"] + 1e-9))
        self.assertAlmostEqual(res["profile"][0], 0)
        self.assertAlmostEqual(res["profile"][-1], 0)


class ControlTests(unittest.TestCase):
    def test_ctc_tracks_with_exact_model(self):
        arm = rd.PlanarArm(L=[1, .8], m=[2, 1.5])
        Kp, Kd = np.array([100., 100.]), np.array([20., 20.])

        def tau(t, q, qd):
            qr = np.array([math.sin(t), math.cos(t)])
            return rd.ctc_tau(arm, q, qd, qr, np.array([math.cos(t), -math.sin(t)]),
                              -qr, Kp, Kd)
        ts, Q, _, _ = rd.simulate(arm, [0.0, 1.0], [1.0, 0.0], 1.0, 0.002, tau)
        ref = np.column_stack([np.sin(ts), np.cos(ts)])
        self.assertLess(np.abs(Q - ref).max(), 1e-4)

    def test_null_space_torque_does_not_disturb_tip(self):
        arm = rd.PlanarArm(L=[1, .8, .5], m=[2, 1.5, .8])
        q, qd = np.array([0.3, 0.8, -0.6]), np.array([0.2, -0.1, 0.3])
        _, Jbar, _, _ = arm.task_space(q, qd)
        J = arm.jacobian(q)
        N = np.eye(3) - J.T @ Jbar.T
        tau0 = np.array([1.0, -2.0, 0.5])
        # tip acceleration caused by a null-space torque is zero
        dxdd = J @ np.linalg.solve(arm.mass_matrix(q), N @ tau0)
        self.assertTrue(np.allclose(dxdd, 0, atol=1e-9))
        Np = np.eye(3) - J.T @ rk.pinv_damped(J).T
        self.assertGreater(np.linalg.norm(J @ np.linalg.solve(arm.mass_matrix(q), Np @ tau0)), 1e-3)


class PlanningGraspMobileTests(unittest.TestCase):
    def test_astar_finds_collision_free_path(self):
        L = [1.0, 0.8]
        obs = [(1.0, 0.9, 0.3), (-0.5, 1.2, 0.3)]
        G = rk.cspace_grid_2r(L, obs, n=60)
        free = np.argwhere(~G)
        path = rk.astar(G, tuple(free[0]), tuple(free[len(free) // 2]))
        self.assertIsNotNone(path)
        self.assertFalse(any(G[p] for p in path))

    def test_force_closure(self):
        sq = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        normals = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        self.assertFalse(rk.force_closure_planar(rk.contact_wrenches_planar(sq, normals, 0.0)))
        self.assertTrue(rk.force_closure_planar(rk.contact_wrenches_planar(sq, normals, 0.3)))
        two = rk.contact_wrenches_planar([(1, 0), (-1, 0)], [(-1, 0), (1, 0)], 0.5)
        self.assertTrue(rk.force_closure_planar(two))
        self.assertFalse(rk.force_closure_planar(
            rk.contact_wrenches_planar([(1, 0), (-1, 0)], [(-1, 0), (1, 0)], 0.0)))

    def test_diff_drive_cannot_slide(self):
        s = np.array([0.0, 0.0, 0.3])
        s2 = rk.diff_drive_step(s, 2.0, 3.0, 0.05, 0.2, 0.01)
        d = s2[:2] - s[:2]
        self.assertAlmostEqual(-math.sin(0.3) * d[0] + math.cos(0.3) * d[1], 0.0)


if __name__ == "__main__":
    unittest.main()
