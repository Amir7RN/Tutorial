"""
Upper-body balance -- the planar equations of motion of a humanoid's legs,
torso and arms, the momentum they carry, and a recovery law that uses the
upper body to absorb a push. The teaching model behind the Humanoid Balance
pages, and the reference the JavaScript labs (app/assets/steplab/ub.js) are
tested against.

The machine is a serial planar chain standing on a pinned joint:

    ground --ankle--> legs --waist--> torso --shoulder--> upper arm --elbow--> forearm

Conventions (chosen to agree with the G1's own joint signs):
    x forward, y up. Pitch angles are positive when the top of the link moves
    forward (clockwise on a drawing with x to the right). So a forward lean is
    a positive ankle angle, and a positive shoulder pitch swings the hanging
    arm backward, exactly as on the robot. Angular momentum is reported in the
    same pitch sense: positive = rotating forward.
    q_i is the RELATIVE joint angle; q = 0 is standing straight with the arms
    hanging (each link has a rest offset `off` from its parent).
    Both arms are folded into one link of twice the mass, because in a planar
    model they move together.

Three planes are three parameter sets of the same chain (PLANES). Only the
names, the rest offsets and whether gravity acts change. Locking a joint keeps
its angle fixed and deletes its column from every Jacobian, which is why the
mass matrix of the locked machine is a principal sub-matrix of the full one.

Everything is derived with Jacobians, the way page 133 builds M:
    M(q)  = sum_i  m_i Jv_i^T Jv_i + I_i Jw_i^T Jw_i
    c     = sum_i  m_i Jv_i^T a_i^vel          a_i^vel: COM acceleration with qdd = 0
    g     = dP/dq,  P = sum_i m_i g c_iy
    h     = A(q) qdot,  A = sum_i [ m_i Jv_i ; I_i Jw_i + m_i (c_i - x_c) x Jv_i ]
and the one balance identity the whole chapter rests on,
    dH_O/dt = tau_ankle + m_tot g x_c + (push moment about O)
where H_O is the angular momentum about the ankle: internal torques cannot
change it, only the ankle, gravity and the push can.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from types import SimpleNamespace

import numpy as np

G0 = 9.81


@dataclass(frozen=True)
class Link:
    name: str       # what the link is
    joint: str      # the joint that moves it (its parent-side joint)
    m: float        # kg (both arms combined when they move together)
    L: float        # joint-to-next-joint length, m
    r: float        # joint-to-centre-of-mass distance, m
    I: float        # inertia about the centre of mass, kg m^2
    off: float = 0  # rest angle relative to the parent link (pi: hangs down)
    lo: float = -1e9  # joint range, rad (mechanical stops in the simulator)
    hi: float = 1e9


# Approximate G1 segments. The robot is about 35 kg and 1.32 m tall; these
# numbers are for teaching: read the real ones from the MJCF (each body's
# mass, inertia and pos) before trusting a torque.
SAGITTAL = (
    Link("legs + pelvis", "ankle pitch", 17.0, 0.72, 0.42, 0.73),
    Link("torso + head", "waist pitch", 11.0, 0.36, 0.20, 0.15, lo=-0.52, hi=0.52),
    Link("upper arms (x2)", "shoulder pitch", 3.2, 0.22, 0.11, 0.013, off=math.pi, lo=-3.0, hi=2.6),
    Link("forearms + hands (x2)", "elbow pitch", 2.8, 0.26, 0.14, 0.016, lo=-2.0, hi=0.3),
)
# the two arm links of SAGITTAL merged into one straight rod (elbow locked)
FRONTAL = (
    Link("legs + pelvis", "ankle roll", 17.0, 0.72, 0.42, 0.73),
    Link("torso + head", "waist roll", 11.0, 0.36, 0.20, 0.15, lo=-0.52, hi=0.52),
    Link("arms, straight (x2)", "shoulder roll", 6.0, 0.48, 0.2267, 0.1224, off=math.pi, lo=-1.6, hi=1.6),
)
# Transverse: seen from above. The pivot is the feet twisting on the floor
# (friction, not an actuator), the torso is a disc whose "length" is the
# distance from the spine to the shoulder, the arms are held out horizontally
# and swing about the shoulder yaw axis. No gravity in this plane.
TRANSVERSE = (
    Link("legs + pelvis (seen from above)", "feet on the floor (yaw)", 17.0, 0.0, 0.0, 0.25),
    Link("torso (spine to shoulder)", "waist yaw", 11.0, 0.16, 0.0, 0.20, lo=-2.6, hi=2.6),
    Link("arms, held out forward (x2)", "shoulder yaw", 6.0, 0.48, 0.2267, 0.1224, off=-math.pi / 2, lo=-1.6, hi=1.6),
)


def pcross(ax, ay, bx, by) -> float:
    """Planar cross product in the pitch sense (positive = forward rotation)."""
    return ay * bx - ax * by


@dataclass
class Model:
    links: tuple[Link, ...] = SAGITTAL
    g: float = G0
    plane: str = "sagittal"
    # how far the centre of pressure can move in front of / behind the ankle:
    # the ankle torque is limited to m_tot g foot, beyond that the foot tips
    foot: float = 0.10

    # ------------------------------------------------------------------ basics
    @property
    def n(self) -> int:
        return len(self.links)

    @property
    def m_tot(self) -> float:
        return sum(l.m for l in self.links)

    @property
    def joints(self) -> list[str]:
        return [l.joint for l in self.links]

    def tau_ankle_max(self) -> float:
        return self.m_tot * self.g * self.foot if self.g else 0.0

    # -------------------------------------------------------------------- core
    def core(self, q, qd=None, momentum: bool = True, about=None) -> SimpleNamespace:
        """
        Every quantity at one state, in one pass of scalar arithmetic (this runs
        thousands of times per simulated second).
            p, c        joint points (n+1) and link COMs (n), as (x, y) tuples
            Jx, Jy      Jx[i][j], Jy[i][j]: d c_i / d q_j
            M, g        mass matrix, gravity vector
        and with qd:
            v, a        COM velocities and their accelerations with qdd = 0
            cvec        velocity-product forces  sum m_i Jv_i^T a_i
            w           absolute angular velocities
        and with momentum:
            xc, vc      whole-body COM and its velocity
            A, bias     momentum matrix about `about` (default: the COM) and Adot qd
            A_O, H_O    the same about the ankle, and the momentum there
            link_H      each link's share of H_O
        """
        links = self.links
        n = len(links)
        q = [float(v) for v in q]
        phi = []
        s = 0.0
        for i in range(n):
            s += q[i] + links[i].off
            phi.append(s)
        ux = [math.sin(f) for f in phi]
        uy = [math.cos(f) for f in phi]
        px, py, cx, cy = [0.0], [0.0], [], []
        for i, l in enumerate(links):
            cx.append(px[i] + l.r * ux[i])
            cy.append(py[i] + l.r * uy[i])
            px.append(px[i] + l.L * ux[i])
            py.append(py[i] + l.L * uy[i])
        Jx = [[0.0] * n for _ in range(n)]
        Jy = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(i + 1):
                Jx[i][j] = cy[i] - py[j]
                Jy[i][j] = -(cx[i] - px[j])
        M = np.zeros((n, n))
        for i, l in enumerate(links):
            for a in range(i + 1):
                for b in range(a, i + 1):
                    v = l.m * (Jx[i][a] * Jx[i][b] + Jy[i][a] * Jy[i][b]) + l.I
                    M[a, b] += v
                    if a != b:
                        M[b, a] += v
        g = np.zeros(n)
        if self.g:
            for j in range(n):
                g[j] = -self.g * sum(links[i].m * (cx[i] - px[j]) for i in range(j, n))
        out = SimpleNamespace(phi=phi, p=list(zip(px, py)), c=list(zip(cx, cy)), Jx=Jx, Jy=Jy, M=M, g=g)
        if qd is None:
            return out
        qd = [float(v) for v in qd]
        w, s = [], 0.0
        for i in range(n):
            s += qd[i]
            w.append(s)
        pdx, pdy = [0.0], [0.0]
        for j in range(1, n + 1):
            pdx.append(sum(qd[k] * (py[j] - py[k]) for k in range(j)))
            pdy.append(sum(-qd[k] * (px[j] - px[k]) for k in range(j)))
        vx, vy, ax, ay = [], [], [], []
        for i in range(n):
            vxi = sum(qd[j] * Jx[i][j] for j in range(i + 1))
            vyi = sum(qd[j] * Jy[i][j] for j in range(i + 1))
            vx.append(vxi)
            vy.append(vyi)
            ax.append(sum(qd[j] * (vyi - pdy[j]) for j in range(i + 1)))
            ay.append(sum(-qd[j] * (vxi - pdx[j]) for j in range(i + 1)))
        cvec = np.zeros(n)
        for j in range(n):
            cvec[j] = sum(links[i].m * (Jx[i][j] * ax[i] + Jy[i][j] * ay[i]) for i in range(j, n))
        out.qd, out.w, out.v, out.a, out.cvec = qd, w, list(zip(vx, vy)), list(zip(ax, ay)), cvec
        if not momentum:
            return out
        mt = self.m_tot
        xc = sum(l.m * cx[i] for i, l in enumerate(links)) / mt
        yc = sum(l.m * cy[i] for i, l in enumerate(links)) / mt
        vcx = sum(l.m * vx[i] for i, l in enumerate(links)) / mt
        vcy = sum(l.m * vy[i] for i, l in enumerate(links)) / mt
        if about is None:
            ox, oy, vox, voy = xc, yc, vcx, vcy
        else:
            ox, oy, vox, voy = float(about[0]), float(about[1]), 0.0, 0.0
        A = np.zeros((3, n))
        A_O = np.zeros((3, n))
        bias = np.zeros(3)
        link_H = np.zeros(n)
        H_O = 0.0
        for i, l in enumerate(links):
            dx, dy = cx[i] - ox, cy[i] - oy
            for j in range(i + 1):
                A[0, j] += l.m * Jx[i][j]
                A[1, j] += l.m * Jy[i][j]
                A[2, j] += l.I + l.m * pcross(dx, dy, Jx[i][j], Jy[i][j])
                A_O[2, j] += l.I + l.m * pcross(cx[i], cy[i], Jx[i][j], Jy[i][j])
            bias[0] += l.m * ax[i]
            bias[1] += l.m * ay[i]
            bias[2] += l.m * (pcross(vx[i] - vox, vy[i] - voy, vx[i], vy[i]) + pcross(dx, dy, ax[i], ay[i]))
            link_H[i] = l.I * w[i] + l.m * pcross(cx[i], cy[i], vx[i], vy[i])
            H_O += link_H[i]
        A_O[:2] = A[:2]
        out.xc, out.vc = (xc, yc), (vcx, vcy)
        out.A, out.bias, out.A_O, out.H_O, out.link_H = A, bias, A_O, H_O, link_H
        out.h = A @ np.array(qd)
        return out

    # --------------------------------------------------------------- kinematics
    def angles(self, q) -> np.ndarray:
        """Absolute pitch angle of every link (from vertical, forward positive)."""
        return np.array(self.core(q).phi)

    def points(self, q):
        """Joint positions p[0..n] (p[n] is the free end) and COM positions c[0..n-1]."""
        k = self.core(q)
        return [np.array(v) for v in k.p], [np.array(v) for v in k.c]

    def com_jacobians(self, q):
        """Jv[i]: 2 x n Jacobian of COM i. Column j is non-zero for j <= i."""
        k = self.core(q)
        return ([np.array(v) for v in k.p], [np.array(v) for v in k.c],
                [np.array([k.Jx[i], k.Jy[i]]) for i in range(self.n)])

    def point_jacobian(self, q, k: int) -> np.ndarray:
        """Jacobian of joint point p[k] (k = n is the free end)."""
        p, _ = self.points(q)
        J = np.zeros((2, self.n))
        for j in range(min(k, self.n)):
            d = p[k] - p[j]
            J[:, j] = [d[1], -d[0]]
        return J

    def com(self, q, qd=None):
        """Whole-body COM position, and its velocity if qd is given."""
        if qd is None:
            return np.array(self.core(q, np.zeros(self.n)).xc)
        k = self.core(q, qd)
        return np.array(k.xc), np.array(k.vc)

    # ----------------------------------------------------------------- dynamics
    def mass_matrix(self, q) -> np.ndarray:
        return self.core(q).M

    def velocity_product(self, q, qd) -> np.ndarray:
        """c(q, qd): the Coriolis + centripetal generalised forces."""
        return self.core(q, qd, momentum=False).cvec

    def gravity(self, q) -> np.ndarray:
        return self.core(q).g

    def h(self, q, qd) -> np.ndarray:
        k = self.core(q, qd, momentum=False)
        return k.cvec + k.g

    def energy(self, q, qd):
        k = self.core(q, qd, momentum=False)
        qd = np.asarray(qd, float)
        T = 0.5 * qd @ k.M @ qd
        V = sum(l.m * self.g * k.c[i][1] for i, l in enumerate(self.links))
        return float(T), float(V)

    # ----------------------------------------------------------------- momentum
    @staticmethod
    def pcross(a, b) -> float:
        return pcross(a[0], a[1], b[0], b[1])

    def momentum_matrix(self, q, about=None) -> np.ndarray:
        """
        A(q), 3 x n:  [p_x; p_y; H] = A qdot.
        about=None: H about the whole-body COM (the centroidal momentum matrix).
        about=(x, y): H about that fixed point, for example the ankle (0, 0).
        """
        return self.core(q, np.zeros(self.n), about=about).A

    def momentum(self, q, qd, about=None):
        """(p_x, p_y, H) from the definitions directly, not through A: a cross-check."""
        k = self.core(q, qd, momentum=False)
        o = self.com(q) if about is None else np.asarray(about, float)
        px = py = H = 0.0
        for i, l in enumerate(self.links):
            px += l.m * k.v[i][0]
            py += l.m * k.v[i][1]
            H += l.I * k.w[i] + l.m * pcross(k.c[i][0] - o[0], k.c[i][1] - o[1], k.v[i][0], k.v[i][1])
        return np.array([px, py, H])

    def link_momenta(self, q, qd) -> np.ndarray:
        """Each link's share of the angular momentum about the ankle."""
        return self.core(q, qd).link_H

    def momentum_bias(self, q, qd, about=None) -> np.ndarray:
        """Adot qdot: the part of hdot that is there even with qdd = 0."""
        return self.core(q, qd, about=about).bias

    def gravity_moment(self, q) -> float:
        """Moment of gravity about the ankle, pitch sense: + m_tot g x_c."""
        return self.m_tot * self.g * float(self.com(q)[0])

    # ------------------------------------------------------------------- locks
    @staticmethod
    def selection(n: int, free) -> np.ndarray:
        """S (n x k): q = S q_free. Locking a joint deletes its column."""
        free = list(free)
        S = np.zeros((n, len(free)))
        for k, j in enumerate(free):
            S[j, k] = 1.0
        return S

    def locked(self, q, qd, free) -> dict:
        """
        The equations of motion with every joint outside `free` held still:
            S^T M S  qdd_free + S^T (c + g) = S^T tau,     h = (A S) qdot_free
        The locked joints' velocities must be zero in qd for c to be right.
        """
        S = self.selection(self.n, free)
        k = self.core(q, qd)
        return dict(S=S, M=S.T @ k.M @ S, c=S.T @ k.cvec, g=S.T @ k.g, A=k.A @ S, A_O=k.A_O @ S)


# ==========================================================================
# planes
# ==========================================================================

PLANES = {
    "sagittal": Model(SAGITTAL, G0, "sagittal"),
    "frontal": Model(FRONTAL, G0, "frontal"),
    "transverse": Model(TRANSVERSE, 0.0, "transverse"),
}

# the G1 joints each plane keeps, by the names in the mujoco_menagerie MJCF
G1_JOINTS = {
    "sagittal": ["left/right_ankle_pitch_joint", "waist_pitch_joint",
                 "left/right_shoulder_pitch_joint", "left/right_elbow_joint"],
    "frontal": ["left/right_ankle_roll_joint", "waist_roll_joint", "left/right_shoulder_roll_joint"],
    "transverse": ["(feet on the floor)", "waist_yaw_joint", "left/right_shoulder_yaw_joint"],
}


# ==========================================================================
# the recovery controller
# ==========================================================================

@dataclass
class Gains:
    task: str = "dcm"         # "dcm": stop the divergent COM motion; "lean": servo the ankle angle
    k_dcm: float = 3.0        # DCM gain (1/s): xi converges as exp(-k_dcm t)
    kp_lean: float = 40.0     # "lean" task: qdd_0 = -kp q_0 - kd qd_0 through the coupling
    kd_lean: float = 12.0
    w_task: float = 1.0       # weight of the task row
    kp_post: float = 40.0     # posture (null-space) stiffness
    kd_post: float = 10.0     # posture damping
    lam_post: float = 0.05    # weight of the posture term (null space when the task is met)
    # joint torque limits, N m. Ankle: set by the foot. Waist 88, shoulder and
    # elbow 25 per arm, so 50 for the two arms moving together.
    tau_max: tuple = (0.0, 88.0, 50.0, 50.0)
    ankle_k: float = 300.0    # passive ankle stiffness, N m/rad (saturates at m g foot)
    ankle_b: float = 30.0     # passive ankle damping
    law: str = "lqr"          # "lqr", "counterweight" or "momentum" (see each *_step)
    # the counterweight law
    kappa_p: float = 0.15     # m of COM shift per rad of lean
    kappa_d: float = 0.08     # m of COM shift per rad/s of lean rate
    k_x: float = 1500.0       # N/m, the spring that drags the upper-body COM to x_up,des
    b_x: float = 220.0        # N s/m
    # the LQR law: the biggest acceptable value of each state (Bryson's rule)
    lean_max: float = 0.1     # rad
    posture_max: float = 0.5  # rad
    lean_rate_max: float = 1.0
    posture_rate_max: float = 5.0


def ankle_torque(model: Model, q, qd, gains: Gains) -> float:
    """What the foot can do: a weak spring-damper, saturated at m g foot."""
    tau = -gains.ankle_k * q[0] - gains.ankle_b * qd[0]
    lim = model.tau_ankle_max()
    return float(np.clip(tau, -lim, lim))


def box_qp(R, r0, lo, hi):
    """
    min ||R x + r0||^2  with  lo <= x <= hi, for a handful of unknowns.
    Every combination of (free / at lower / at upper) per unknown is tried;
    the cheapest one whose free part lands inside the box is the optimum
    (the problem is convex, so the true optimum appears as one such case).
    This is the whole-body QP of a humanoid controller, shrunk to a size you
    can read.
    """
    n = R.shape[1]
    x = np.linalg.lstsq(R, -r0, rcond=None)[0]
    if np.all(x >= lo - 1e-9) and np.all(x <= hi + 1e-9):
        return np.clip(x, lo, hi), 0
    best, best_cost, tried = np.clip(x, lo, hi), None, 0
    import itertools
    for states in itertools.product((0, 1, 2), repeat=n):
        if all(st == 0 for st in states):
            continue
        tried += 1
        x = np.where(np.array(states) == 1, lo, hi).astype(float)
        free = [i for i in range(n) if states[i] == 0]
        if free:
            fixed = [i for i in range(n) if states[i] != 0]
            rhs = -(r0 + R[:, fixed] @ x[fixed])
            x[free] = np.linalg.lstsq(R[:, free], rhs, rcond=None)[0]
            if np.any(x[free] < lo[free] - 1e-9) or np.any(x[free] > hi[free] + 1e-9):
                continue
        cost = float(np.sum((R @ x + r0) ** 2))
        if best_cost is None or cost < best_cost:
            best, best_cost = x, cost
    return best, tried


def dcm(model: Model, k) -> tuple[float, float]:
    """
    The divergent component of motion. With the ankle torque and the momentum
    rate folded into one point, the COM obeys  xdd_c = w^2 (x_c - p_cmp),
    w = sqrt(g / y_c). The DCM  xi = x_c + xdot_c / w  then obeys
    xi_dot = w (xi - p_cmp): it runs away unless the CMP is placed beyond it.
    Returns (xi, w).
    """
    w = math.sqrt(model.g / max(k.xc[1], 0.05))
    return k.xc[0] + k.vc[0] / w, w


def recovery_step(model: Model, q, qd, gains: Gains, active=None, q_home=None, detail=False):
    """
    One controller tick: resolved momentum control with a tiny QP. Returns the
    joint torques (the ankle entry is the passive ankle torque, the rest are
    commands).

    The idea in one line: decide how the whole-body momentum should change,
    then find the upper-body torques that produce it, knowing that the ankle
    is not yours to command and that every motor has a limit.

        task "dcm":   p_cmp,des = xi (1 + k/w)             where to put the centroidal moment pivot
                      Hdot_c,des = m g p_cmp,des + tau_ankle  the momentum rate that puts it there
        task "lean":  qdd_0,des = -kp q_0 - kd qd_0          servo the passive joint through M_0u
        row 0 of  M qdd + c + g = tau_ankle  =>  qdd_0 = f(qdd_u)   the ankle's own law
        hdot = A qdd + Adot qdot = A_tilde qdd_u + b_tilde           affine in the upper body
        tau_u = T qdd_u + t_0                                        affine too (T: Schur complement)
        min_tau_u  w (task - target)^2 + lam || qdd_u - qdd_posture ||^2
                   subject to  -tau_max <= tau_u <= tau_max           a tiny QP (box_qp)
    Without the limits the answer is the weighted pseudo-inverse plus a
    null-space posture term, which is the formula on the page.
    """
    n = model.n
    q = np.asarray(q, float)
    qd = np.asarray(qd, float)
    active = list(range(1, n)) if active is None else [i for i in active if i > 0]
    q_home = np.zeros(n) if q_home is None else np.asarray(q_home, float)

    k = model.core(q, qd)
    M, cg, A, b = k.M, k.cvec + k.g, k.A, k.bias
    xc, vc = k.xc, k.vc
    H = float(A[2] @ qd)
    tau1 = ankle_torque(model, q, qd, gains)

    tau = np.zeros(n)
    tau[0] = tau1
    if not active:
        if detail:
            return tau, dict(target=0.0, qdd=np.zeros(n), H=H, xc=xc, vc=vc, saturated=0, xi=0.0)
        return tau

    # the ankle row decides qdd_0 once the upper body has chosen qdd_u
    u = active
    e0 = np.zeros(n)
    e0[0] = (tau1 - cg[0]) / M[0, 0]
    E = np.zeros((n, len(u)))
    for kk, j in enumerate(u):
        E[0, kk] = -M[0, j] / M[0, 0]
        E[j, kk] = 1.0
    xi = 0.0
    if gains.task == "dcm" and model.g:
        xi, w = dcm(model, k)
        p_cmp = xi * (1.0 + gains.k_dcm / w)
        target = model.m_tot * model.g * p_cmp + tau1
        row = (A @ E)[2]
        off = float((A @ e0 + b)[2])
    else:
        target = -gains.kp_lean * q[0] - gains.kd_lean * qd[0]
        row = E[0]
        off = float(e0[0])
    qdd_post = -gains.kp_post * (q[u] - q_home[u]) - gains.kd_post * qd[u]
    # torques are affine in the upper-body accelerations
    T = (M @ E)[u]
    t0 = (M @ e0 + cg)[u]
    Tinv = np.linalg.inv(T)
    sw = math.sqrt(gains.w_task)
    sl = math.sqrt(gains.lam_post)
    # residual as a function of tau_u:  R tau_u + r0
    rT = row @ Tinv
    R = np.vstack([sw * rT[None, :], sl * Tinv])
    r0 = np.concatenate([[sw * (off - target - rT @ t0)], sl * (-Tinv @ t0 - qdd_post)])
    lim = np.asarray(gains.tau_max, float)[u]
    tau_u, tried = box_qp(R, r0, -lim, lim)
    for kk, j in enumerate(u):
        tau[j] = tau_u[kk]
    if detail:
        qdd_u = Tinv @ (tau_u - t0)
        qdd = E @ qdd_u + e0
        unc = np.linalg.lstsq(R, -r0, rcond=None)[0]
        return tau, dict(target=target, achieved=float(row @ qdd_u + off), qdd=qdd, H=H, xc=xc, vc=vc,
                         xi=xi, row=row, off=off, T=T, t0=t0, tau_unclipped=unc, saturated=tried)
    return tau


def passive(model, q, qd, gains, active=None):
    """A controller that does nothing: only the passive ankle acts."""
    tau = np.zeros(model.n)
    tau[0] = ankle_torque(model, q, qd, gains)
    return tau


def upper_com(model: Model, k, u):
    """The upper body's own COM (every link above the legs), its horizontal
    velocity, and the row of its Jacobian for the joints in u."""
    m_up = sum(l.m for l in model.links[1:])
    x_up = sum(l.m * k.c[i][0] for i, l in enumerate(model.links) if i >= 1) / m_up
    y_up = sum(l.m * k.c[i][1] for i, l in enumerate(model.links) if i >= 1) / m_up
    J = np.zeros(model.n)
    for i, l in enumerate(model.links):
        if i >= 1:
            for j in range(i + 1):
                J[j] += l.m * k.Jx[i][j] / m_up
    return m_up, (x_up, y_up), float(J @ k.qd), J[u]


def counterweight_step(model: Model, q, qd, gains: Gains, active=None, q_home=None, detail=False):
    """
    The law that works with a small foot: treat the upper body as a
    counterweight and put the whole-body COM behind the ankle while the legs
    lean forward, then let gravity and the ankle bring the legs back.

        x_c,des  = -(kappa_p q_0 + kappa_d qd_0)             where the COM should be (m, from the ankle)
        x_up,des = (m x_c,des - m_legs x_legs) / m_up         what that asks of the upper body's own COM
        F        = k_x (x_up,des - x_up) - b_x xdot_up         a horizontal spring-damper on that point
        tau_u    = J_up^T F  +  (c + g)_u  +  N (posture PD)   page 144: J^T force, compensation, null space
    clipped to the motor limits. J_up is one row of the linear part of the
    momentum matrix (divided by m_up): the COM Jacobian of the upper body.
    """
    n = model.n
    q = np.asarray(q, float)
    qd = np.asarray(qd, float)
    active = list(range(1, n)) if active is None else [i for i in active if i > 0]
    q_home = np.zeros(n) if q_home is None else np.asarray(q_home, float)
    k = model.core(q, qd)
    tau = np.zeros(n)
    tau[0] = ankle_torque(model, q, qd, gains)
    if not active:
        return (tau, dict(x_des=0.0)) if detail else tau
    u = active
    m_up, (x_up, _), xd_up, J = upper_com(model, k, u)
    m_legs = model.links[0].m
    x_c_des = -(gains.kappa_p * q[0] + gains.kappa_d * qd[0])
    x_up_des = (model.m_tot * x_c_des - m_legs * k.c[0][0]) / m_up
    F = gains.k_x * (x_up_des - x_up) - gains.b_x * xd_up
    JJ = float(J @ J)
    pinv = J / JJ if JJ > 1e-12 else np.zeros_like(J)
    N = np.eye(len(u)) - np.outer(pinv, J)
    post = -gains.kp_post * (q[u] - q_home[u]) - gains.kd_post * qd[u]
    tau_u = J * F + (k.cvec + k.g)[u] + N @ post
    lim = np.asarray(gains.tau_max, float)
    for kk, j in enumerate(u):
        tau[j] = float(np.clip(tau_u[kk], -lim[j], lim[j]))
    if detail:
        return tau, dict(x_c_des=x_c_des, x_up_des=x_up_des, x_up=x_up, F=F, J=J, xc=k.xc, H=k.h[2],
                         tau_unclipped=tau_u)
    return tau


# ==========================================================================
# the linear law: LQR on the linearised machine, ankle spring included
# ==========================================================================

def linearise(model: Model, active, gains: Gains, q0=None, eps: float = 1e-5):
    """
    x = [q_free; qd_free], u = tau_active.  xdot = f(x, u) = [qd; M^-1 (tau - c - g)]
    with the ankle's passive spring-damper (unsaturated) and the locked joints
    removed. A and B by central differences of f.
    """
    n = model.n
    active = sorted(j for j in active if 0 < j < n)
    free = [0] + active
    S = model.selection(n, free)
    q0 = np.zeros(n) if q0 is None else np.asarray(q0, float)
    nf, nu = len(free), len(active)

    def f(x, u):
        q = q0 + S @ x[:nf]
        qd = S @ x[nf:]
        tau = np.zeros(n)
        tau[0] = -gains.ankle_k * q[0] - gains.ankle_b * qd[0]
        for kk, j in enumerate(active):
            tau[j] = u[kk]
        k = model.core(q, qd, momentum=False)
        qdd = np.linalg.solve(S.T @ k.M @ S, S.T @ (tau - k.cvec - k.g))
        return np.concatenate([x[nf:], qdd])

    x0, u0 = np.zeros(2 * nf), np.zeros(nu)
    A = np.zeros((2 * nf, 2 * nf))
    B = np.zeros((2 * nf, nu))
    for i in range(2 * nf):
        e = np.zeros(2 * nf)
        e[i] = eps
        A[:, i] = (f(x0 + e, u0) - f(x0 - e, u0)) / (2 * eps)
    for i in range(nu):
        e = np.zeros(nu)
        e[i] = eps
        B[:, i] = (f(x0, u0 + e) - f(x0, u0 - e)) / (2 * eps)
    return A, B, free


_LQR_CACHE: dict = {}


def lqr_gain(model: Model, gains: Gains, active):
    """K (n_active x 2 n_free) for  tau_u = -K [q_free; qd_free]. Cached per design."""
    active = tuple(sorted(j for j in active if 0 < j < model.n))
    key = (model.plane, tuple(model.links), model.foot, active, gains.ankle_k, gains.ankle_b, gains.lean_max,
           gains.posture_max, gains.lean_rate_max, gains.posture_rate_max, tuple(gains.tau_max))
    if key in _LQR_CACHE:
        return _LQR_CACHE[key]
    from .linear import lqr
    A, B, free = linearise(model, active, gains)
    nf = len(free)
    qmax = [gains.lean_max] + [gains.posture_max] * (nf - 1)
    vmax = [gains.lean_rate_max] + [gains.posture_rate_max] * (nf - 1)
    Q = np.diag([1 / v ** 2 for v in qmax + vmax])
    R = np.diag([1 / float(gains.tau_max[j]) ** 2 for j in active])
    K = lqr(A, B, Q, R) if active else np.zeros((0, 2 * nf))
    poles = np.linalg.eigvals(A - B @ K) if active else np.linalg.eigvals(A)
    _LQR_CACHE[key] = (K, free, A, B, poles)
    return _LQR_CACHE[key]


def lqr_step(model: Model, q, qd, gains: Gains, active=None, q_home=None, detail=False):
    """tau_u = -K x on the linearised machine, clipped to the motor limits."""
    n = model.n
    active = list(range(1, n)) if active is None else sorted(i for i in active if i > 0)
    q = np.asarray(q, float)
    qd = np.asarray(qd, float)
    tau = np.zeros(n)
    tau[0] = ankle_torque(model, q, qd, gains)
    if not active:
        return (tau, {}) if detail else tau
    K, free, A, B, poles = lqr_gain(model, gains, active)
    x = np.concatenate([q[free], qd[free]])
    u = -K @ x
    lim = np.asarray(gains.tau_max, float)
    for kk, j in enumerate(active):
        tau[j] = float(np.clip(u[kk], -lim[j], lim[j]))
    if detail:
        return tau, dict(K=K, x=x, u=u, poles=poles)
    return tau


LAWS = {"counterweight": counterweight_step, "momentum": recovery_step, "lqr": lqr_step}


def control_step(model: Model, q, qd, gains: Gains, active=None, q_home=None, detail=False):
    """The controller the simulator calls: whichever law `gains.law` names."""
    return LAWS[gains.law](model, q, qd, gains, active=active, q_home=q_home, detail=detail)


def stop_torque(model: Model, q, qd, k: float = 400.0, b: float = 15.0) -> np.ndarray:
    """The mechanical joint stops: a stiff spring-damper beyond each range."""
    tau = np.zeros(model.n)
    for j, l in enumerate(model.links):
        if j == 0:
            continue
        if q[j] > l.hi:
            tau[j] = -k * (q[j] - l.hi) - b * max(qd[j], 0.0)
        elif q[j] < l.lo:
            tau[j] = -k * (q[j] - l.lo) - b * min(qd[j], 0.0)
    return tau


# ==========================================================================
# simulation
# ==========================================================================

@dataclass
class Push:
    force: float = 80.0       # N, +x is from behind (the robot falls forward)
    t0: float = 0.2           # s
    duration: float = 0.1     # s
    point: int = 2            # joint index the force acts at (2: the shoulder)


def simulate(model: Model, gains: Gains = None, push: Push = None, active=None, q0=None,
             T: float = 3.0, dt: float = 1e-3, controller=control_step, fall_deg: float = 30.0,
             sample: int = 10) -> dict:
    """
    Integrate the chain under the controller and a push. RK4, a fixed step,
    the torque held over each step like a real 1 kHz loop.
    `active`: which joints the controller may use. The others are locked
    exactly: only the free coordinates are integrated, using S^T M S, and the
    torque a locked joint needs to stay put is reported in `tau`.
    """
    gains = gains or Gains()
    push = push or Push()
    n = model.n
    q = np.zeros(n) if q0 is None else np.asarray(q0, float)
    qd = np.zeros(n)
    active = list(range(1, n)) if active is None else list(active)
    free = [0] + sorted(j for j in active if 0 < j < n)
    S = model.selection(n, free)
    all_free = len(free) == n

    def gen_force(t, qq):
        if push.t0 <= t < push.t0 + push.duration and push.force:
            J = model.point_jacobian(qq, push.point)
            return J.T @ np.array([push.force, 0.0])
        return None

    def accel(t, qq, qqd, tau):
        k = model.core(qq, qqd, momentum=False)
        rhs = tau + stop_torque(model, qq, qqd) - k.cvec - k.g
        f = gen_force(t, qq)
        if f is not None:
            rhs = rhs + f
        if all_free:
            qdd = np.linalg.solve(k.M, rhs)
            return qdd, np.zeros(n)
        qdd = S @ np.linalg.solve(S.T @ k.M @ S, S.T @ rhs)
        return qdd, k.M @ qdd - rhs          # torque the locked joints add to stay still

    out = dict(t=[], q=[], qd=[], tau=[], xc=[], H_O=[], H_c=[], link_H=[], fell=False, t_fall=None)
    steps = int(round(T / dt))
    for i in range(steps + 1):
        t = i * dt
        tau = controller(model, q, qd, gains, active=active)
        if i % sample == 0:
            k = model.core(q, qd)
            _, hold = accel(t, q, qd, tau)
            out["t"].append(t)
            out["q"].append(q.copy())
            out["qd"].append(qd.copy())
            out["tau"].append(tau + hold)
            out["xc"].append(np.array(k.xc))
            out["H_O"].append(k.H_O)
            out["H_c"].append(float(k.h[2]))
            out["link_H"].append(k.link_H)
        if abs(q[0]) > math.radians(fall_deg):
            out["fell"], out["t_fall"] = True, t
            break
        k1v, _ = accel(t, q, qd, tau)
        k1x = qd
        k2v, _ = accel(t + dt / 2, q + dt / 2 * k1x, qd + dt / 2 * k1v, tau)
        k2x = qd + dt / 2 * k1v
        k3v, _ = accel(t + dt / 2, q + dt / 2 * k2x, qd + dt / 2 * k2v, tau)
        k3x = qd + dt / 2 * k2v
        k4v, _ = accel(t + dt, q + dt * k3x, qd + dt * k3v, tau)
        k4x = qd + dt * k3v
        q = q + dt / 6 * (k1x + 2 * k2x + 2 * k3x + k4x)
        qd = qd + dt / 6 * (k1v + 2 * k2v + 2 * k3v + k4v)
    for key in ("t", "q", "qd", "tau", "xc", "H_O", "H_c", "link_H"):
        out[key] = np.array(out[key])
    out["peak_lean_deg"] = float(np.degrees(np.max(np.abs(out["q"][:, 0])))) if len(out["q"]) else 0.0
    out["free"] = free
    return out


def strategies(model: Model = None, gains: Gains = None, push: Push = None, T: float = 3.0) -> dict:
    """The four ways to meet the same push: every joint locked, waist only (hip
    strategy), arms only, and the whole upper body."""
    model = model or PLANES["sagittal"]
    n = model.n
    sets = {"everything locked": [], "waist only": [1], "arms only": list(range(2, n)),
            "whole upper body": list(range(1, n))}
    return {name: simulate(model, gains, push, active=act, T=T) for name, act in sets.items()}


# ==========================================================================
# the derivation page's worked numbers
# ==========================================================================

def worked(model: Model, q, qd) -> dict:
    """Every intermediate quantity of the Lagrange derivation at one state,
    for the page that asks the reader to compute them by hand first."""
    k = model.core(q, qd)
    v = np.array(k.v)
    K = [0.5 * l.m * float(v[i] @ v[i]) + 0.5 * l.I * k.w[i] ** 2 for i, l in enumerate(model.links)]
    P = [l.m * model.g * k.c[i][1] for i, l in enumerate(model.links)]
    return dict(phi=np.array(k.phi), p=np.array(k.p), c=np.array(k.c),
                Jv=np.array([[k.Jx[i], k.Jy[i]] for i in range(model.n)]), v=v, w=np.array(k.w),
                K=np.array(K), P=np.array(P), M=k.M, cvec=k.cvec, g=k.g, A=k.A, A_O=k.A_O,
                h=k.h, H_O=k.H_O, xc=np.array(k.xc), gravity_moment=model.gravity_moment(q))
