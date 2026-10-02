"""
robodyn.py -- dynamics of open chains, trajectories and robot control.

Modern Robotics chapters 8, 9 and 11, for a planar serial arm of revolute
joints so that every number on the pages can be checked by hand:

    PlanarArm.rnea          recursive Newton-Euler inverse dynamics
    PlanarArm.mass_matrix   n RNEA calls with unit accelerations
    PlanarArm.gravity       RNEA with zero velocity and acceleration
    PlanarArm.coriolis_matrix  Christoffel symbols of M(q)
    PlanarArm.forward_dynamics  qdd = M^-1 (tau - c - g)
    PlanarArm.task_space    Lambda, J_bar, mu, p (operational space)
    lagrange_2r             closed-form Lagrangian 2R model, a cross-check

    time scalings           cubic, quintic, trapezoid
    time_optimal_line       bang-bang along a straight joint path, torque limits
    simulate                RK4 / semi-implicit / explicit Euler

Gravity acts along -y. Link i has length L_i, mass m_i at distance r_i from
its joint, and rotational inertia I_i about its centre of mass.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .robokin import planar_jacobian, planar_points, pinv_damped

G0 = 9.81


def _perp(v):
    return np.array([-v[1], v[0]])


def _cross2(a, b) -> float:
    return float(a[0] * b[1] - a[1] * b[0])


@dataclass
class PlanarArm:
    L: list = field(default_factory=lambda: [1.0, 1.0])
    m: list = field(default_factory=lambda: [1.0, 1.0])
    r: list | None = None          # COM distance from joint (default L/2)
    I: list | None = None          # inertia about COM (default m L^2 / 12)
    g: float = G0
    rotor: list | None = None      # reflected rotor inertia N^2 J_m per joint
    friction: list | None = None   # viscous joint friction b_i

    def __post_init__(self):
        n = len(self.L)
        self.L = [float(x) for x in self.L]
        self.m = [float(x) for x in self.m]
        self.r = [L / 2 for L in self.L] if self.r is None else [float(x) for x in self.r]
        self.I = ([m * L * L / 12 for m, L in zip(self.m, self.L)]
                  if self.I is None else [float(x) for x in self.I])
        self.rotor = [0.0] * n if self.rotor is None else [float(x) for x in self.rotor]
        self.friction = [0.0] * n if self.friction is None else [float(x) for x in self.friction]

    @property
    def n(self) -> int:
        return len(self.L)

    # ------------------------------------------------------------------
    # Inverse dynamics: recursive Newton-Euler
    # ------------------------------------------------------------------
    def rnea(self, q, qd, qdd, gravity: bool = True, trace: bool = False,
             f_tip=None):
        """
        Forward pass (base -> tip): angular velocity, angular acceleration
        and linear acceleration of every joint origin and centre of mass.
        Gravity enters as a fictitious upward base acceleration of g.
        Backward pass (tip -> base): force on each link, then the moment
        about its joint, whose z-component is the joint torque.

        f_tip: optional (fx, fy) force the TIP exerts on the environment.
        """
        # Scalar arithmetic on purpose: this runs thousands of times per
        # simulated second, and small numpy arrays cost more than they save.
        n = self.n
        q = [float(v) for v in q]
        qd = [float(v) for v in qd]
        qdd = [float(v) for v in qdd]
        ang = w = al = 0.0
        ux, uy, W, AL = [], [], [], []
        for i in range(n):
            ang += q[i]
            w += qd[i]
            al += qdd[i]
            ux.append(math.cos(ang))
            uy.append(math.sin(ang))
            W.append(w)
            AL.append(al)
        ax, ay = 0.0, (self.g if gravity else 0.0)
        acx, acy, ajx, ajy = [], [], [ax], [ay]
        for i in range(n):
            r, L, w2 = self.r[i], self.L[i], W[i] * W[i]
            acx.append(ax - AL[i] * r * uy[i] - w2 * r * ux[i])
            acy.append(ay + AL[i] * r * ux[i] - w2 * r * uy[i])
            ax = ax - AL[i] * L * uy[i] - w2 * L * ux[i]
            ay = ay + AL[i] * L * ux[i] - w2 * L * uy[i]
            ajx.append(ax)
            ajy.append(ay)
        if f_tip is None:
            fx = fy = 0.0
        else:
            fx, fy = float(f_tip[0]), float(f_tip[1])
        mom = 0.0
        tau = np.zeros(n)
        forces, moments = [None] * n, [None] * n
        for i in range(n - 1, -1, -1):
            m, r, L = self.m[i], self.r[i], self.L[i]
            mx, my = m * acx[i], m * acy[i]
            mom = (mom + L * (ux[i] * fy - uy[i] * fx)
                   + r * (ux[i] * my - uy[i] * mx) + self.I[i] * AL[i])
            fx, fy = fx + mx, fy + my
            tau[i] = mom + self.rotor[i] * qdd[i] + self.friction[i] * qd[i]
            forces[i], moments[i] = (fx, fy), mom
        if trace:
            return tau, dict(omega=np.array(W), alpha=np.array(AL),
                             acc_c=np.column_stack([acx, acy]),
                             acc_j=np.column_stack([ajx, ajy]),
                             force=np.array(forces), moment=np.array(moments))
        return tau

    def gravity(self, q) -> np.ndarray:
        z = np.zeros(self.n)
        return self.rnea(q, z, z)

    def h(self, q, qd) -> np.ndarray:
        """c(q, qd) + g(q) + friction: everything except M qdd."""
        return self.rnea(q, qd, np.zeros(self.n))

    def mass_matrix(self, q) -> np.ndarray:
        n = self.n
        M = np.zeros((n, n))
        z = np.zeros(n)
        for i in range(n):
            e = np.zeros(n)
            e[i] = 1.0
            M[:, i] = self.rnea(q, z, e, gravity=False)
        return M

    def mass_matrix_jacobian(self, q) -> np.ndarray:
        """Same M from  sum m_i Jv_i^T Jv_i + I_i Jw_i^T Jw_i  (a cross-check)."""
        n = self.n
        M = np.diag(self.rotor).astype(float)
        pts = planar_points(self.L, q)
        ang = np.cumsum(q)
        for i in range(n):
            c = pts[i] + self.r[i] * np.array([math.cos(ang[i]), math.sin(ang[i])])
            Jv = np.zeros((2, n))
            for j in range(i + 1):
                d = c - pts[j]
                Jv[:, j] = [-d[1], d[0]]
            Jw = np.zeros(n)
            Jw[:i + 1] = 1.0
            M += self.m[i] * Jv.T @ Jv + self.I[i] * np.outer(Jw, Jw)
        return M

    def dM(self, q, eps: float = 1e-6) -> np.ndarray:
        """dM[k] = dM/dq_k by central differences."""
        q = np.asarray(q, float)
        out = []
        for k in range(self.n):
            e = np.zeros(self.n)
            e[k] = eps
            out.append((self.mass_matrix(q + e) - self.mass_matrix(q - e)) / (2 * eps))
        return np.array(out)

    def coriolis_matrix(self, q, qd) -> np.ndarray:
        """C_ij = sum_k Gamma_ijk qd_k with Christoffel symbols of M."""
        D = self.dM(q)
        n = self.n
        C = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                C[i, j] = sum(0.5 * (D[k][i, j] + D[j][i, k] - D[i][j, k]) * qd[k]
                              for k in range(n))
        return C

    def Mdot(self, q, qd) -> np.ndarray:
        D = self.dM(q)
        return sum(D[k] * qd[k] for k in range(self.n))

    # ------------------------------------------------------------------
    # Forward dynamics
    # ------------------------------------------------------------------
    def forward_dynamics(self, q, qd, tau, f_tip=None) -> np.ndarray:
        M = self.mass_matrix(q)
        h = self.rnea(q, qd, np.zeros(self.n), f_tip=f_tip)
        return np.linalg.solve(M, np.asarray(tau, float) - h)

    def energy(self, q, qd):
        """(kinetic, potential)."""
        qd = np.asarray(qd, float)
        T = 0.5 * qd @ self.mass_matrix(q) @ qd
        pts = planar_points(self.L, q)
        ang = np.cumsum(q)
        V = sum(self.m[i] * self.g * (pts[i][1] + self.r[i] * math.sin(ang[i]))
                for i in range(self.n))
        return float(T), float(V)

    # ------------------------------------------------------------------
    # Task space (operational space)
    # ------------------------------------------------------------------
    def jacobian(self, q) -> np.ndarray:
        return planar_jacobian(self.L, q)

    def Jdot_qd(self, q, qd, eps: float = 1e-6) -> np.ndarray:
        q, qd = np.asarray(q, float), np.asarray(qd, float)
        Jp = planar_jacobian(self.L, q + eps * qd)
        Jm = planar_jacobian(self.L, q - eps * qd)
        return (Jp - Jm) / (2 * eps) @ qd

    def task_space(self, q, qd):
        """
        Lambda = (J M^-1 J^T)^-1      task-space inertia
        J_bar  = M^-1 J^T Lambda      dynamically consistent inverse
        mu     = J_bar^T c - Lambda Jdot qd
        p      = J_bar^T g
        Valid where J has full row rank.
        """
        J = self.jacobian(q)
        M = self.mass_matrix(q)
        Mi = np.linalg.inv(M)
        Lam = np.linalg.inv(J @ Mi @ J.T)
        Jbar = Mi @ J.T @ Lam
        g = self.gravity(q)
        c = self.h(q, qd) - g
        mu = Jbar.T @ c - Lam @ self.Jdot_qd(q, qd)
        p = Jbar.T @ g
        return Lam, Jbar, mu, p

    def tip(self, q) -> np.ndarray:
        return planar_points(self.L, q)[-1]


# ==========================================================================
# Closed-form Lagrangian 2R model, for cross-checking RNEA by hand
# ==========================================================================

def lagrange_2r(arm: PlanarArm, q, qd):
    """
    M = [[a + 2b cos q2, d + b cos q2], [d + b cos q2, d]]
        a = I1 + I2 + m1 r1^2 + m2 (L1^2 + r2^2), b = m2 L1 r2, d = I2 + m2 r2^2
    c = [-b sin q2 (2 qd1 qd2 + qd2^2),  b sin q2 qd1^2]
    g = [(m1 r1 + m2 L1) g cos q1 + m2 r2 g cos(q1+q2),  m2 r2 g cos(q1+q2)]
    """
    L1, _ = arm.L
    m1, m2 = arm.m
    r1, r2 = arm.r
    I1, I2 = arm.I
    g = arm.g
    a = I1 + I2 + m1 * r1 ** 2 + m2 * (L1 ** 2 + r2 ** 2)
    b = m2 * L1 * r2
    d = I2 + m2 * r2 ** 2
    c2, s2 = math.cos(q[1]), math.sin(q[1])
    M = np.array([[a + 2 * b * c2, d + b * c2], [d + b * c2, d]])
    c = np.array([-b * s2 * (2 * qd[0] * qd[1] + qd[1] ** 2), b * s2 * qd[0] ** 2])
    gv = np.array([(m1 * r1 + m2 * L1) * g * math.cos(q[0]) + m2 * r2 * g * math.cos(q[0] + q[1]),
                   m2 * r2 * g * math.cos(q[0] + q[1])])
    return M, c, gv


# ==========================================================================
# Integration
# ==========================================================================

def simulate(arm: PlanarArm, q0, qd0, T: float, dt: float, tau_fn=None,
             method: str = "rk4"):
    """
    tau_fn(t, q, qd) -> tau (default zero: a passive multi-link pendulum).
    method: 'rk4', 'semi' (semi-implicit Euler) or 'euler'.
    """
    q, qd = np.array(q0, float), np.array(qd0, float)
    n = arm.n
    tau_fn = tau_fn or (lambda t, q, qd: np.zeros(n))
    ts = np.arange(0.0, T + 1e-12, dt)
    Q, QD, TAU = [q.copy()], [qd.copy()], []

    def f(t, x):
        qq, vv = x[:n], x[n:]
        tau = tau_fn(t, qq, vv)
        return np.r_[vv, arm.forward_dynamics(qq, vv, tau)], tau

    for t in ts[:-1]:
        x = np.r_[q, qd]
        if method == "rk4":
            k1, tau = f(t, x)
            k2, _ = f(t + dt / 2, x + dt / 2 * k1)
            k3, _ = f(t + dt / 2, x + dt / 2 * k2)
            k4, _ = f(t + dt, x + dt * k3)
            x = x + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
            q, qd = x[:n], x[n:]
        elif method == "semi":
            k1, tau = f(t, x)
            qd = qd + dt * k1[n:]
            q = q + dt * qd
        else:
            k1, tau = f(t, x)
            q, qd = q + dt * qd, qd + dt * k1[n:]
        TAU.append(np.asarray(tau, float))
        Q.append(q.copy())
        QD.append(qd.copy())
    TAU.append(TAU[-1] if TAU else np.zeros(n))
    return ts, np.array(Q), np.array(QD), np.array(TAU)


# ==========================================================================
# Chapter 9 -- time scaling and trajectories
# ==========================================================================

def cubic(t, T):
    """s, sdot, sddot for the cubic with zero end velocities."""
    t = np.clip(np.asarray(t, float), 0, T)
    s = 3 * (t / T) ** 2 - 2 * (t / T) ** 3
    sd = 6 * t / T ** 2 - 6 * t ** 2 / T ** 3
    sdd = 6 / T ** 2 - 12 * t / T ** 3
    return s, sd, sdd


def quintic(t, T):
    """Zero end velocity AND acceleration: no jerk spike at start and stop."""
    t = np.clip(np.asarray(t, float), 0, T)
    x = t / T
    s = 10 * x ** 3 - 15 * x ** 4 + 6 * x ** 5
    sd = (30 * x ** 2 - 60 * x ** 3 + 30 * x ** 4) / T
    sdd = (60 * x - 180 * x ** 2 + 120 * x ** 3) / T ** 2
    return s, sd, sdd


def trapezoid(t, v: float, a: float):
    """
    Trapezoidal velocity profile from s = 0 to 1 with cruise speed v and
    acceleration a (requires v^2/a <= 1). Total time T = (a + v^2)/(v a).
    """
    if v * v / a > 1:
        v = math.sqrt(a)          # triangle profile (bang-bang)
    T = (a + v * v) / (v * a)
    ta = v / a
    t = np.clip(np.asarray(t, float), 0, T)
    s = np.where(t < ta, 0.5 * a * t ** 2,
                 np.where(t < T - ta, v * t - v * v / (2 * a),
                          (2 * a * v * T - 2 * v * v - a * a * (t - T) ** 2) / (2 * a)))
    sd = np.where(t < ta, a * t, np.where(t < T - ta, v, a * (T - t)))
    sdd = np.where(t < ta, a, np.where(t < T - ta, 0.0, -a))
    return s, sd, sdd, T


def time_optimal_line(arm: PlanarArm, q0, q1, tau_max, ns: int = 400):
    """
    Time-optimal time scaling of the straight joint path q(s) = q0 + s (q1-q0).
    Along the path   tau = m(s) sdd + c(s) sd^2 + g(s)   with
        m = M q',  c = (h(q, q') - g(q)) (q'' = 0),  g = g(q).
    Torque limits give  L(s, sd) <= sdd <= U(s, sd).  The velocity limit curve
    is where L = U. One-switch bang-bang: integrate U forward from (0, 0),
    L backward from (1, 0), switch where they meet.
    Returns dict with the two curves, the VLC and the switching point.
    """
    q0, q1 = np.asarray(q0, float), np.asarray(q1, float)
    dq = q1 - q0
    tmax = np.asarray(tau_max, float)

    def coeffs(s):
        q = q0 + s * dq
        m = arm.mass_matrix(q) @ dq
        g = arm.gravity(q)
        c = arm.h(q, dq) - g
        return m, c, g

    def bounds(s, sd):
        m, c, g = coeffs(s)
        lo, hi = -np.inf, np.inf
        for i in range(arm.n):
            if abs(m[i]) < 1e-12:
                continue
            a = (-tmax[i] - c[i] * sd * sd - g[i]) / m[i]
            b = (tmax[i] - c[i] * sd * sd - g[i]) / m[i]
            lo, hi = max(lo, min(a, b)), min(hi, max(a, b))
        return lo, hi

    ss = np.linspace(0, 1, ns)
    # velocity limit curve by bisection on sd
    vlc = []
    for s in ss:
        a, b = 0.0, 1.0
        while bounds(s, b)[0] <= bounds(s, b)[1] and b < 1e3:
            b *= 2
        for _ in range(40):
            mid = 0.5 * (a + b)
            lo, hi = bounds(s, mid)
            a, b = (mid, b) if lo <= hi else (a, mid)
        vlc.append(a)
    vlc = np.array(vlc)

    def integrate(forward: bool):
        ds = 1.0 / (ns - 1)
        sd2 = np.zeros(ns)          # integrate sd^2 in s: d(sd^2)/ds = 2 sdd
        idx = range(ns - 1) if forward else range(ns - 1, 0, -1)
        for k in idx:
            sd = math.sqrt(max(sd2[k], 0.0))
            lo, hi = bounds(ss[k], sd)
            if forward:
                sd2[k + 1] = sd2[k] + 2 * hi * ds
                sd2[k + 1] = min(max(sd2[k + 1], 0.0), vlc[k + 1] ** 2)
            else:
                sd2[k - 1] = sd2[k] - 2 * lo * ds
                sd2[k - 1] = min(max(sd2[k - 1], 0.0), vlc[k - 1] ** 2)
        return np.sqrt(sd2)

    acc = integrate(True)
    dec = integrate(False)
    prof = np.minimum(acc, dec)
    k_sw = int(np.argmax(prof))
    # time = integral ds / sd, guarding the end points
    mids = 0.5 * (prof[1:] + prof[:-1])
    T = float(np.sum((ss[1] - ss[0]) / np.maximum(mids, 1e-6)))
    return dict(s=ss, accel=acc, decel=dec, profile=prof, vlc=vlc,
                switch=float(ss[k_sw]), T=T, bounds=bounds)


# ==========================================================================
# Chapter 11 -- control laws on the arm
# ==========================================================================

def ctc_tau(model: PlanarArm, q, qd, qr, qdr, qddr, Kp, Kd):
    """Computed torque: tau = M_hat (qdd_r + Kd e_dot + Kp e) + h_hat."""
    e, ed = qr - q, qdr - qd
    v = qddr + Kd * ed + Kp * e
    return model.mass_matrix(q) @ v + model.h(q, qd)


def pd_gravity_tau(model: PlanarArm, q, qd, qr, qdr, Kp, Kd):
    """PD plus gravity compensation: no model of M or c is used."""
    return Kp * (qr - q) + Kd * (qdr - qd) + model.gravity(q)


def osc_tau(model: PlanarArm, q, qd, xr, xdr, xddr, Kp, Kd,
            q_post=None, Kp_null: float = 0.0, Kd_null: float = 0.0,
            consistent: bool = True):
    """
    Operational space control with a null-space posture task:
        F    = Lambda (xdd_r + Kd ed + Kp e) + mu + p
        tau0 = Kp_n (q_post - q) - Kd_n qd
        tau  = J^T F + (I - J^T J_bar^T) tau0
    With consistent=False the projector uses the kinematic pseudo-inverse
    J^+ instead of J_bar, which leaks posture torque into the tip.
    """
    J = model.jacobian(q)
    Lam, Jbar, mu, p = model.task_space(q, qd)
    x = model.tip(q)
    xd = J @ qd
    F = Lam @ (xddr + Kd * (xdr - xd) + Kp * (xr - x)) + mu + p
    tau = J.T @ F
    if q_post is not None:
        tau0 = Kp_null * (np.asarray(q_post) - q) - Kd_null * qd
        Jinv = Jbar if consistent else pinv_damped(J)
        N = np.eye(model.n) - J.T @ Jinv.T
        tau = tau + N @ tau0
    return tau


# ==========================================================================
# Constrained dynamics: the tip held on a vertical wall x = x_w
# ==========================================================================

def wall_constrained_step(arm: PlanarArm, q, qd, tau, x_wall: float,
                          dt: float, stab: float = 20.0):
    """
    One semi-implicit step of
        M qdd + h = tau + A^T lam,      A qdd = -Adot qd - 2a phid - a^2 phi
    with phi = x_tip - x_wall and A the x-row of the tip Jacobian (Baumgarte
    stabilisation, gain a = stab). lam is the force the WALL pushes on the
    tip along +x. Returns (q, qd, lam).
    """
    q, qd = np.asarray(q, float), np.asarray(qd, float)
    n = arm.n
    J = arm.jacobian(q)
    A = J[0:1, :]
    Adqd = arm.Jdot_qd(q, qd)[0]
    phi = arm.tip(q)[0] - x_wall
    phid = float((A @ qd)[0])
    M = arm.mass_matrix(q)
    h = arm.h(q, qd)
    K = np.zeros((n + 1, n + 1))
    K[:n, :n] = M
    K[:n, n] = -A[0]
    K[n, :n] = A[0]
    rhs = np.r_[np.asarray(tau, float) - h, -Adqd - 2 * stab * phid - stab ** 2 * phi]
    sol = np.linalg.solve(K, rhs)
    qdd, lam = sol[:n], sol[n]
    qd = qd + dt * qdd
    q = q + dt * qd
    return q, qd, float(lam)
