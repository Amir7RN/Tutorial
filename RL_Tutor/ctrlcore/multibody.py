"""
multibody.py -- the state-space models the state-feedback, LQR and capstone
pages are built on.

Everything here returns a plain `StateSpace` from linear.py, so the same
place_poles / lqr / simulate_ss machinery applies to all of them. The point
of collecting them in one file is that they form a ladder:

    msd_ss          2 states, 1 input, stable, SISO.  The canonical example.
                    Every symbol in u = -Kx can be pointed at.

    sea_ss          4 states, 1 input, SISO but UNDERACTUATED: one motor and
                    two inertias with a spring between them. This is where
                    pole placement stops being a formality, and where the
                    difference between "collocated" and "non-collocated"
                    output starts to bite.

    lipm_ss         2 states, 1 input, UNSTABLE. The linear inverted pendulum
                    a biped balances on. The input is the centre of pressure,
                    and it is bounded by the length of the foot -- which makes
                    it the cleanest example anywhere of a constraint that no
                    amount of gain can negotiate with.

    two_link_ss     4 states, 2 inputs, MIMO, and its A matrix depends on the
                    configuration. This is the arm. Cross-coupling in the
                    inertia matrix is the thing single-loop design cannot see
                    and full-state design handles without comment.

    leg_ss          6 states, 3 inputs: hip, knee, ankle of one planar leg in
                    stance, linearised. Same structure as the arm, different
                    gravity signs -- and that sign difference is most of why
                    legs and arms feel like different problems.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .linear import StateSpace, ctrb, lqr, obsv, rank

G = 9.81


# ==========================================================================
# 1 -- mass, spring, damper. Two states, and nothing hidden.
# ==========================================================================

def msd_ss(m: float = 1.0, b: float = 0.6, k: float = 20.0) -> StateSpace:
    r"""
    m xddot + b xdot + k x = F

    State x = [position, velocity], input u = F, output y = position.

        A = [[   0,     1  ],      B = [[  0  ],
             [ -k/m, -b/m ]]            [ 1/m ]]

    Read the second row out loud: acceleration equals minus stiffness over
    mass times position, minus damping over mass times velocity, plus force
    over mass. That IS Newton's second law -- the state-space form is not a
    new model, it is f = ma with the second derivative split into two first
    derivatives so that the whole thing becomes one matrix equation.
    """
    A = np.array([[0.0, 1.0], [-k / m, -b / m]])
    B = np.array([[0.0], [1.0 / m]])
    C = np.array([[1.0, 0.0]])
    D = np.array([[0.0]])
    return StateSpace(A, B, C, D)


def msd_natural(m: float, b: float, k: float) -> tuple[float, float]:
    """(wn, zeta) of the open-loop mass-spring-damper."""
    wn = math.sqrt(k / m) if k > 0 else 0.0
    zeta = b / (2.0 * math.sqrt(k * m)) if k > 0 and m > 0 else 0.0
    return wn, zeta


# ==========================================================================
# 2 -- series elastic actuator. Four states, one motor, two inertias.
# ==========================================================================

def sea_ss(j_m: float = 0.02, j_l: float = 0.25, k: float = 400.0,
           b_m: float = 0.05, b_l: float = 0.10) -> StateSpace:
    r"""
    Motor and load joined by a spring:

        J_m thm.. = tau - k (thm - thl) - b_m thm.
        J_l thl.. =       k (thm - thl) - b_l thl.

    State x = [thm, thm., thl, thl.], input u = tau (motor torque), and the
    default output y = thl, the LOAD angle -- which is the one you care about
    and the one your sensor is furthest from.

    Two things make this the interesting example on the state-feedback page:

      * It is UNDERACTUATED in the useful sense: one input, four states. You
        still get to place all four poles, because controllability does not
        require one actuator per state -- it requires that the actuator's
        influence, propagated through the dynamics, reaches every direction.
        The spring is what propagates it.

      * The choice of output decides whether the problem is easy or hard.
        Measuring thm (COLLOCATED -- sensor on the same body as the actuator)
        gives a well-behaved plant. Measuring thl (NON-COLLOCATED) puts the
        flexible mode between actuator and sensor, and that is the classic
        way to make a loop that looks fine on paper and rings on hardware.
    """
    A = np.array([
        [0.0, 1.0, 0.0, 0.0],
        [-k / j_m, -b_m / j_m, k / j_m, 0.0],
        [0.0, 0.0, 0.0, 1.0],
        [k / j_l, 0.0, -k / j_l, -b_l / j_l],
    ])
    B = np.array([[0.0], [1.0 / j_m], [0.0], [0.0]])
    C = np.array([[0.0, 0.0, 1.0, 0.0]])          # load angle
    D = np.array([[0.0]])
    return StateSpace(A, B, C, D)


def sea_output(kind: str = "load") -> np.ndarray:
    """C row for the SEA: which state the sensor actually sees."""
    if kind == "motor":
        return np.array([[1.0, 0.0, 0.0, 0.0]])
    if kind == "deflection":                       # a torque sensor
        return np.array([[1.0, 0.0, -1.0, 0.0]])
    return np.array([[0.0, 0.0, 1.0, 0.0]])


def sea_modes(j_m: float, j_l: float, k: float) -> tuple[float, float]:
    """(resonance, antiresonance) in rad/s -- the two frequencies a SEA has."""
    w_res = math.sqrt(k * (1.0 / j_m + 1.0 / j_l))
    w_anti = math.sqrt(k / j_l)
    return w_res, w_anti


# ==========================================================================
# 3 -- linear inverted pendulum. The biped's balance model.
# ==========================================================================

def lipm_ss(z_com: float = 0.9, g: float = G) -> StateSpace:
    r"""
    The linear inverted pendulum, which is what a biped's whole body reduces
    to when you assume constant centre-of-mass height and no angular momentum
    about the CoM:

        xddot = (g / z) (x - p)

    x is the CoM position, p is the centre of pressure under the foot, and p
    is the INPUT. State [x, xdot], u = p.

        A = [[0, 1], [g/z, 0]]        B = [[0], [-g/z]]

    Its eigenvalues are +-sqrt(g/z): one of them is in the right half plane,
    which is the mathematical statement of "a standing human is falling over
    and catching itself continuously".

    The number that matters more than any gain: u is bounded. The centre of
    pressure cannot leave the support polygon, so |p| <= foot length / 2.
    That is a hard saturation on the ONLY input, and it is why balance is a
    problem about where you can put your feet rather than about controller
    tuning.
    """
    w = g / z_com
    A = np.array([[0.0, 1.0], [w, 0.0]])
    B = np.array([[0.0], [-w]])
    C = np.array([[1.0, 0.0]])
    D = np.array([[0.0]])
    return StateSpace(A, B, C, D)


def lipm_omega(z_com: float = 0.9, g: float = G) -> float:
    """sqrt(g/z) -- the divergence rate, in 1/s. Everything scales with it."""
    return math.sqrt(g / z_com)


def capture_point(x: float, xdot: float, z_com: float = 0.9) -> float:
    """
    The instantaneous capture point, xi = x + xdot / omega.

    This is the single most useful quantity in bipedal balance, and it falls
    straight out of the LIPM: it is the point where you would have to place
    the CoP to bring the CoM to rest. Put another way, it is the unstable
    eigenvector's coordinate -- the one combination of position and velocity
    that grows, isolated from the one that decays.

    If xi lies inside the support polygon you can stop without stepping. If
    it does not, you must step, and the step target IS xi. No amount of ankle
    torque changes that verdict; it is geometry plus one eigenvalue.
    """
    return x + xdot / lipm_omega(z_com)


# ==========================================================================
# 4 -- two-link planar arm, linearised about a configuration
# ==========================================================================

@dataclass
class TwoLink:
    """A planar two-link arm, in the parameters a datasheet would give you."""
    m1: float = 3.0          # kg, upper link
    m2: float = 2.0          # kg, forearm + hand
    l1: float = 0.35         # m
    l2: float = 0.30         # m
    lc1: float = 0.17        # m, centre of mass along link 1
    lc2: float = 0.15        # m
    i1: float = 0.04         # kg m^2 about its own CoM
    i2: float = 0.02
    d1: float = 0.6          # N m s / rad, joint damping
    d2: float = 0.4

    # -- the two matrices every manipulator textbook opens with -------
    def inertia(self, q2: float) -> np.ndarray:
        """
        M(q). Depends on the ELBOW angle only, which is the whole story of a
        two-link arm: fold the elbow and the shoulder's effective inertia
        drops by a factor of several.
        """
        c2 = math.cos(q2)
        m11 = (self.m1 * self.lc1 ** 2 + self.i1
               + self.m2 * (self.l1 ** 2 + self.lc2 ** 2
                            + 2 * self.l1 * self.lc2 * c2) + self.i2)
        m12 = self.m2 * (self.lc2 ** 2 + self.l1 * self.lc2 * c2) + self.i2
        m22 = self.m2 * self.lc2 ** 2 + self.i2
        return np.array([[m11, m12], [m12, m22]])

    def gravity_stiffness(self, q1: float, q2: float) -> np.ndarray:
        """
        dG/dq at (q1, q2) -- the 'gravity spring'.

        Gravity on an arm behaves like a spring whose stiffness can be
        POSITIVE or NEGATIVE depending on where the arm is. Held out
        horizontally it is a restoring-free destabilising term; hanging
        straight down it is a genuine restoring spring, which is why a
        powered-off arm swings to hang rather than staying put.
        """
        a = (self.m1 * self.lc1 + self.m2 * self.l1) * G
        b = self.m2 * self.lc2 * G
        s1 = math.sin(q1)
        s12 = math.sin(q1 + q2)
        # G1 = a cos q1 + b cos(q1+q2);  G2 = b cos(q1+q2)
        return np.array([[-a * s1 - b * s12, -b * s12],
                         [-b * s12, -b * s12]])

    def coupling_ratio(self, q2: float) -> float:
        """|M12| / sqrt(M11 M22) -- how strongly the two joints fight."""
        M = self.inertia(q2)
        return abs(M[0, 1]) / math.sqrt(M[0, 0] * M[1, 1])


def two_link_ss(arm: TwoLink, q1: float = 0.0, q2: float = 0.5,
                gravity: bool = True) -> StateSpace:
    r"""
    Linearise the arm about (q1, q2) with zero velocity:

        M0 qddot + D qdot + Gq q = tau

    State x = [q1, q2, q1dot, q2dot], input u = [tau1, tau2]. Two inputs and
    four states -- a genuinely MIMO plant, and the first one in this tutor
    where a transfer function per joint is not merely inconvenient but
    actively misleading, because M0 is not diagonal.
    """
    M = arm.inertia(q2)
    Mi = np.linalg.inv(M)
    D = np.diag([arm.d1, arm.d2])
    Kg = arm.gravity_stiffness(q1, q2) if gravity else np.zeros((2, 2))
    A = np.block([[np.zeros((2, 2)), np.eye(2)],
                  [-Mi @ Kg, -Mi @ D]])
    B = np.vstack([np.zeros((2, 2)), Mi])
    C = np.hstack([np.eye(2), np.zeros((2, 2))])
    Dm = np.zeros((2, 2))
    return StateSpace(A, B, C, Dm)


# ==========================================================================
# 5 -- one planar leg in stance: hip, knee, ankle
# ==========================================================================

@dataclass
class PlanarLeg:
    """
    Three independent upright joint approximations for the teaching lab.

    These diagonal inertias and gravity coefficients are illustrative, not
    a derived multibody stance leg. Real contact constraints and coupling
    change the modes; a mode cannot generally be assigned to one joint.
    """
    j_ankle: float = 3.2     # kg m^2 seen at the ankle in stance
    j_knee: float = 1.1
    j_hip: float = 0.45
    d: float = 0.8           # joint damping
    body_mass: float = 30.0  # kg, one-leg share of a trunkless biped
    z_com: float = 0.75      # m

    def inertias(self) -> np.ndarray:
        return np.array([self.j_ankle, self.j_knee, self.j_hip])

    def gravity_stiffness(self) -> np.ndarray:
        r"""
        dG/dq for the stance leg, near upright.

        Negative stiffness is an assumption of this diagonal teaching model,
        not a statement that every joint of every standing leg is unstable.
        """
        m, g, z = self.body_mass, G, self.z_com
        base = m * g * z
        return -np.diag([base, base * 0.45, base * 0.18])


def leg_ss(leg: PlanarLeg) -> StateSpace:
    """
    Six states [q_a, q_k, q_h, qdot...], three inputs, unstable in every
    joint because of the assumed gravity sign. Positive eigenvalues give
    growth rates, not fixed fall deadlines. Damping breaks exact +/- pairing.
    """
    J = np.diag(leg.inertias())
    Ji = np.linalg.inv(J)
    D = np.eye(3) * leg.d
    Kg = leg.gravity_stiffness()
    A = np.block([[np.zeros((3, 3)), np.eye(3)],
                  [-Ji @ Kg, -Ji @ D]])
    B = np.vstack([np.zeros((3, 3)), Ji])
    C = np.hstack([np.eye(3), np.zeros((3, 3))])
    Dm = np.zeros((3, 3))
    return StateSpace(A, B, C, Dm)


# ==========================================================================
# Design helpers shared by the pages
# ==========================================================================

@dataclass
class LQRResult:
    K: np.ndarray
    P: np.ndarray
    poles: list[complex]
    cost: float


def lqr_design(ss: StateSpace, Q: np.ndarray, R: np.ndarray,
               x0: np.ndarray | None = None) -> LQRResult:
    """
    Solve the LQR problem and also report the two things the pages need:
    where the closed-loop poles ended up, and the optimal cost from x0.

    The cost is the payoff of the Riccati solution P and is worth its own
    sentence: J* = x0^T P x0. P is not an intermediate quantity, it is the
    VALUE FUNCTION of the problem -- exactly the same object the RL pages
    call V(s), for the one case where it can be written in closed form.
    """
    A, B = np.asarray(ss.A), np.asarray(ss.B)
    K = lqr(A, B, Q, R)
    Ri = np.linalg.inv(np.asarray(R, dtype=float))
    n = A.shape[0]
    H = np.block([[A, -B @ Ri @ B.T], [-np.asarray(Q, dtype=float), -A.T]])
    vals, vecs = np.linalg.eig(H)
    idx = [i for i in range(2 * n) if vals[i].real < 0]
    V = vecs[:, idx]
    P = np.real(V[n:, :] @ np.linalg.inv(V[:n, :]))
    poles = [complex(v) for v in np.linalg.eigvals(A - B @ K)]
    if x0 is None:
        x0 = np.zeros(n)
    x0 = np.asarray(x0, dtype=float).reshape(-1)
    cost = float(x0 @ P @ x0)
    return LQRResult(K=K, P=P, poles=poles, cost=cost)


def bryson(max_values: list[float]) -> np.ndarray:
    """
    Bryson's rule: the first Q and R anyone should try.

        Q_ii = 1 / (max acceptable x_i)^2
        R_jj = 1 / (max acceptable u_j)^2

    It makes every term in the cost dimensionless and roughly equal to 1 when
    that variable is at the largest value you are willing to see. That is why
    it works: it removes the units problem, which is the actual reason naive
    Q and R choices behave strangely. After Bryson, tuning is a matter of
    scaling whole blocks up or down by factors of ten, and the scaling has a
    meaning -- 'I care about this ten times more than I said'.
    """
    v = np.asarray(max_values, dtype=float)
    return np.diag(1.0 / np.maximum(v, 1e-12) ** 2)


def simulate_feedback(ss: StateSpace, K: np.ndarray, x0, dur: float = 3.0,
                      dt: float = 1e-3, u_max: float | None = None,
                      disturbance=None):
    """
    Closed-loop simulation of xdot = A x + B (u), u = -K x, with an optional
    per-input saturation and an optional disturbance function of time.

    The saturation is not decoration. Every claim pole placement makes is
    conditional on the actuator delivering what the gain asks for, and this
    is the argument that setting u_max small turns a beautifully placed
    closed loop into something else entirely.
    """
    A = np.asarray(ss.A, dtype=float)
    B = np.asarray(ss.B, dtype=float)
    K = np.asarray(K, dtype=float)
    x = np.asarray(x0, dtype=float).reshape(-1)
    n_steps = int(dur / dt)
    ts, xs, us = [], [], []
    sat_hits = 0
    for i in range(n_steps):
        t = i * dt
        u = -K @ x
        if u_max is not None:
            clipped = np.clip(u, -u_max, u_max)
            if not np.allclose(clipped, u):
                sat_hits += 1
            u = clipped
        d = np.zeros(B.shape[1]) if disturbance is None else np.asarray(
            disturbance(t), dtype=float).reshape(-1)
        ts.append(t)
        xs.append(x.copy())
        us.append(np.atleast_1d(u).copy())
        x = x + (A @ x + B @ (u + d)) * dt
        if not np.all(np.isfinite(x)) or np.max(np.abs(x)) > 1e6:
            break
    return (np.array(ts), np.array(xs), np.array(us),
            sat_hits / max(1, len(ts)))


def controllable(ss: StateSpace) -> bool:
    A, B = np.asarray(ss.A), np.asarray(ss.B)
    return rank(ctrb(A, B)) == A.shape[0]


def observable(ss: StateSpace) -> bool:
    A, C = np.asarray(ss.A), np.asarray(ss.C)
    return rank(obsv(A, C)) == A.shape[0]


def ctrb_gramian_svd(ss: StateSpace) -> np.ndarray:
    """
    Singular values of the controllability matrix, normalised to the largest.

    A yes/no rank test is a cliff, and real hardware never sits exactly on
    it. The small singular values are the useful output: a direction with a
    singular value of 1e-6 is technically controllable and practically not,
    because reaching it costs a million times more input than the easy
    directions. This is how 'nearly uncontrollable' gets measured, and it is
    the number to look at before blaming a controller.
    """
    A, B = np.asarray(ss.A), np.asarray(ss.B)
    Wc = ctrb(A, B)
    s = np.linalg.svd(Wc, compute_uv=False)
    return s / max(s[0], 1e-300)
