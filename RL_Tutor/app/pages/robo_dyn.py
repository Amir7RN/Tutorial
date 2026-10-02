"""
ROBOT MECHANICS, part 3 -- dynamics of open chains.
Modern Robotics playlist 7 (chapter 8). The pages the interview was about.

    Lagrange             L = K - P, and the 2R equations in closed form
    mass matrix          M(q): symmetric, positive definite, configuration
                         dependent; Christoffel symbols; Mdot - 2C skew
    Newton-Euler         one rigid body, then the O(n) recursion
    inverse dynamics     tau(t) from a trajectory, term by term
    forward dynamics     qdd = M^-1 (tau - h), integrators and energy drift
    task-space dynamics  Lambda, mu, p; the mass the hand feels
    constrained dynamics Lagrange multipliers, contact forces, unilateral
"""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QPushButton

from ctrlcore import robodyn as rd
from ctrlcore import robokin as rk
from .. import theme
from ..widgets import Card, MplCanvas, Stat, body, callout, math_label, stat_row
from .base import Page
from .robo_common import (
    SEC_DYN,
    deg,
    draw_arm,
    interview,
    labelled_slider,
    mat_html,
    playlist_badge,
    square,
    watch,
)

ARM = dict(L=[1.0, 0.8], m=[2.0, 1.5], r=[0.5, 0.4], I=[0.17, 0.08])


def _arm(**kw):
    d = dict(ARM)
    d.update(kw)
    return rd.PlanarArm(**d)


# ==========================================================================
# Lagrange
# ==========================================================================

class LagrangePage(Page):
    TITLE = "Lagrangian Dynamics: τ = M(q)q̈ + c(q,q̇) + g(q)"
    SUBTITLE = ("Write kinetic and potential energy as functions of q and q̇, "
                "differentiate once, and the equations of motion fall out — "
                "no constraint forces, no free-body diagrams.")
    SECTION = SEC_DYN
    NOTES = playlist_badge(7)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(watch(7))

        e = Card("the Euler–Lagrange equations")
        e.add(math_label(r"\mathcal{L}(q,\dot q)=K-P=\frac{1}{2}\dot q^TM(q)\dot q-P(q),\qquad "
                         r"\tau_i=\frac{d}{dt}\frac{\partial\mathcal{L}}{\partial\dot q_i}-"
                         r"\frac{\partial\mathcal{L}}{\partial q_i}", 16))
        e.add(math_label(r"\Rightarrow\ \tau=M(q)\ddot q+\underbrace{\dot q^T\Gamma(q)\dot q}_{c(q,\dot q)}"
                         r"+\underbrace{\partial P/\partial q}_{g(q)}", 16))
        e.add(body(
            "Kinetic energy of link i: ½m<sub>i</sub>‖v<sub>ci</sub>‖² + "
            "½I<sub>i</sub>ω<sub>i</sub>², and v<sub>ci</sub> = J<sub>vi</sub>(q)q̇, "
            "so K = ½q̇ᵀ[Σ m<sub>i</sub>J<sub>vi</sub>ᵀJ<sub>vi</sub> + "
            "I<sub>i</sub>J<sub>ωi</sub>ᵀJ<sub>ωi</sub>]q̇ = ½q̇ᵀM(q)q̇. "
            "That bracket <b>is</b> the mass matrix — built from the same "
            "Jacobians as the kinematics pages, one per centre of mass."))
        self.add(e)

        r = Card("the 2R arm, in closed form (memorise the structure)")
        r.add(math_label(r"M=\begin{bmatrix}a+2b\cos q_2 & d+b\cos q_2\\ d+b\cos q_2 & d\end{bmatrix},\ "
                         r"a=I_1+I_2+m_1r_1^2+m_2(L_1^2+r_2^2),\ b=m_2L_1r_2,\ d=I_2+m_2r_2^2", 14))
        r.add(math_label(r"c=b\sin q_2\begin{bmatrix}-2\dot q_1\dot q_2-\dot q_2^2\\ "
                         r"\dot q_1^2\end{bmatrix},\qquad "
                         r"g=\begin{bmatrix}(m_1r_1+m_2L_1)g\cos q_1+m_2r_2g\cos(q_1+q_2)\\ "
                         r"m_2r_2g\cos(q_1+q_2)\end{bmatrix}", 14))
        r.add(body(
            "<b>q̇₁q̇₂</b> terms are <b>Coriolis</b>; <b>q̇₁²</b>, <b>q̇₂²</b> are "
            "<b>centripetal</b>. Every one carries sin q₂: they exist only "
            "because the elbow is bent, and they vanish when the arm is "
            "straight or folded. M depends on q₂ only — rotating the whole arm "
            "about the shoulder changes nothing inertially.", dim=True))
        self.add(r)

        lab = Card("evaluate every term at a state")
        self.q1 = labelled_slider(lab, "q₁", -180, 180, 30, deg, self._draw)
        self.q2 = labelled_slider(lab, "q₂", -180, 180, 60, deg, self._draw)
        self.v1 = labelled_slider(lab, "q̇₁ (rad/s)", -60, 60, 20, lambda v: f"{v/10:.1f}", self._draw)
        self.v2 = labelled_slider(lab, "q̇₂ (rad/s)", -60, 60, -15, lambda v: f"{v/10:.1f}", self._draw)
        self.a1 = labelled_slider(lab, "q̈₁ (rad/s²)", -100, 100, 30, lambda v: f"{v/10:.1f}", self._draw)
        self.a2 = labelled_slider(lab, "q̈₂ (rad/s²)", -100, 100, 0, lambda v: f"{v/10:.1f}", self._draw)
        self.M_txt = body("")
        lab.add(self.M_txt)
        self.st_chk = Stat("‖τ_Lagrange − τ_RNEA‖", "--", theme.GOOD)
        lab.add_layout(stat_row(self.st_chk))
        self.cv = MplCanvas(width=7.6, height=3.6, ncols=2)
        lab.add(self.cv)
        self.add(lab)
        self._draw()

        self.add(interview(
            "<b>“Derive the dynamics of a pendulum / 2R arm.”</b> Write K and P, "
            "apply d/dt ∂L/∂q̇ − ∂L/∂q = τ. For one link: "
            "(I + mr²)q̈ + mgr cos q = τ. Then state the general structure: "
            "M(q) symmetric positive definite, c quadratic in q̇, g the gradient "
            "of potential energy. Interviewers care that you know the "
            "<i>structure</i> and where each term comes from, then that you "
            "know Lagrange is O(n⁴) symbolic and nobody computes it that way "
            "on a robot — that is what Newton–Euler is for."))
        self.finish()

    def _draw(self):
        arm = _arm()
        q = np.radians([self.q1.value(), self.q2.value()])
        qd = np.array([self.v1.value(), self.v2.value()]) / 10
        qdd = np.array([self.a1.value(), self.a2.value()]) / 10
        M, c, g = rd.lagrange_2r(arm, q, qd)
        tau = M @ qdd + c + g
        err = np.linalg.norm(tau - arm.rnea(q, qd, qdd))
        self.M_txt.setText(
            "M(q) =" + mat_html(M) +
            f"c = ({c[0]:+.3f}, {c[1]:+.3f}) N·m,  g = ({g[0]:+.3f}, {g[1]:+.3f}) N·m,  "
            f"<b>τ = ({tau[0]:+.3f}, {tau[1]:+.3f}) N·m</b>")
        self.st_chk.set(f"{err:.1e}")
        cv = self.cv
        cv.clear()
        ax, bx = cv.axes
        draw_arm(ax, arm.L, q)
        square(ax, 2.0)
        ax.set_title("the state")
        parts = [M @ qdd, c, g]
        names = ["M q̈ (inertial)", "c (Coriolis + centripetal)", "g (gravity)"]
        cols = [theme.ACCENT, theme.VIOLET, theme.WARN]
        x = np.arange(2)
        bottom_p = np.zeros(2)
        bottom_n = np.zeros(2)
        for p, nme, col in zip(parts, names, cols):
            base = np.where(p >= 0, bottom_p, bottom_n)
            bx.bar(x, p, 0.5, bottom=base, color=col, label=nme)
            bottom_p += np.maximum(p, 0)
            bottom_n += np.minimum(p, 0)
        bx.plot(x, tau, "D", color=theme.TEXT, ms=8, label="total τ")
        bx.set_xticks(x, ["joint 1", "joint 2"])
        bx.axhline(0, color=theme.BORDER)
        bx.set_ylabel("N·m")
        cv.legend(bx, loc="best")
        cv.refresh()


# ==========================================================================
# Mass matrix
# ==========================================================================

class MassMatrixPage(Page):
    TITLE = "The Mass Matrix and Its Properties"
    SUBTITLE = ("M(q) is symmetric, positive definite and changes with posture. "
                "Its off-diagonal terms are coupling, its eigenvalues bound how "
                "hard the arm is to accelerate, and Ṁ − 2C is skew-symmetric — "
                "the property every robot stability proof leans on.")
    SECTION = SEC_DYN
    NOTES = playlist_badge(7)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(watch(7))

        p = Card("the four properties, and why each holds")
        p.add(body(
            "<b>1. Symmetric.</b> K = ½q̇ᵀMq̇ only sees the symmetric part.<br>"
            "<b>2. Positive definite.</b> K > 0 for every q̇ ≠ 0: a moving arm "
            "has energy. So M⁻¹ exists everywhere — forward dynamics is never "
            "singular, unlike the Jacobian.<br>"
            "<b>3. Bounded.</b> λ<sub>min</sub>I ≤ M(q) ≤ λ<sub>max</sub>I for "
            "revolute arms; used in every robust-control bound.<br>"
            "<b>4. Ṁ − 2C(q, q̇) is skew-symmetric</b> when C is built from the "
            "Christoffel symbols, so q̇ᵀ(Ṁ − 2C)q̇ = 0. Energy then obeys "
            "dK/dt + dP/dt = q̇ᵀτ: the arm is <b>passive</b> from τ to q̇."))
        p.add(math_label(r"C_{ij}=\sum_k\Gamma_{ijk}\dot q_k,\quad "
                         r"\Gamma_{ijk}=\frac{1}{2}\left(\frac{\partial M_{ij}}{\partial q_k}+"
                         r"\frac{\partial M_{ik}}{\partial q_j}-\frac{\partial M_{jk}}{\partial q_i}\right),"
                         r"\quad c=C(q,\dot q)\dot q", 15))
        p.add(body(
            "C is not unique — many matrices satisfy c = Cq̇ — but only the "
            "Christoffel choice gives skew symmetry. Use it whenever you write "
            "a Lyapunov function V = ½ėᵀMė + ….", dim=True))
        self.add(p)

        lab = Card("M(q₂), its eigenvalues, and the kinetic-energy ellipse")
        self.q2 = labelled_slider(lab, "elbow q₂", -180, 180, 60, deg, self._draw)
        self.pay = labelled_slider(lab, "payload at hand (kg)", 0, 50, 0,
                                   lambda v: f"{v/10:.1f}", self._draw)
        self.rot = labelled_slider(lab, "reflected rotor N²J_m", 0, 200, 0,
                                   lambda v: f"{v/100:.2f} kg·m²", self._draw)
        self.M_txt = body("")
        lab.add(self.M_txt)
        self.st_l1 = Stat("λ_max(M)", "--", theme.WARN)
        self.st_l2 = Stat("λ_min(M)", "--", theme.GOOD)
        self.st_cp = Stat("coupling |M₁₂|/√(M₁₁M₂₂)", "--", theme.VIOLET)
        self.st_sk = Stat("‖(Ṁ−2C) + (Ṁ−2C)ᵀ‖", "--", theme.ACCENT)
        lab.add_layout(stat_row(self.st_l1, self.st_l2, self.st_cp, self.st_sk))
        self.cv = MplCanvas(width=7.6, height=3.6, ncols=2)
        lab.add(self.cv)
        self.add(lab)
        self._draw()

        self.add(callout(
            "Turn up the reflected rotor inertia. It adds to the <b>diagonal "
            "only</b>, so coupling drops: a highly geared arm (N = 100, "
            "N²J<sub>m</sub> dominating) behaves like n decoupled single "
            "joints, which is why independent joint PID works on industrial "
            "arms and fails on direct-drive and quasi-direct-drive legs. This "
            "is page 29's N² law, seen from the mass matrix.", "key"))

        self.add(interview(
            "<b>“Why is Ṁ − 2C skew-symmetric and why should I care?”</b> "
            "Ṁ = C + Cᵀ for the Christoffel C, so Ṁ − 2C = Cᵀ − C. Care "
            "because with V = ½q̇ᵀMq̇ + P, dV/dt = q̇ᵀτ — the robot only stores "
            "or returns the energy you put in. That makes PD + gravity "
            "compensation globally asymptotically stable (V = ½q̇ᵀMq̇ + "
            "½eᵀK<sub>p</sub>e, LaSalle), and it is the basis of passivity-"
            "based and adaptive (Slotine–Li) control."))
        self.finish()

    def _draw(self):
        pay = self.pay.value() / 10
        rot = self.rot.value() / 100
        L, m, r, I = ARM["L"], list(ARM["m"]), list(ARM["r"]), list(ARM["I"])
        # payload at the tip: shift link 2's COM and inertia
        m2 = m[1] + pay
        r2 = (m[1] * r[1] + pay * L[1]) / m2
        I2 = I[1] + m[1] * (r[1] - r2) ** 2 + pay * (L[1] - r2) ** 2
        arm = rd.PlanarArm(L=L, m=[m[0], m2], r=[r[0], r2], I=[I[0], I2],
                           rotor=[rot, rot])
        q = np.array([0.3, math.radians(self.q2.value())])
        qd = np.array([1.2, -0.7])
        M = arm.mass_matrix(q)
        ev = np.linalg.eigvalsh(M)
        C = arm.coriolis_matrix(q, qd)
        S = arm.Mdot(q, qd) - 2 * C
        self.M_txt.setText("M(q) =" + mat_html(M) +
                           "C(q, q̇) at q̇ = (1.2, −0.7) =" + mat_html(C))
        self.st_l1.set(f"{ev[1]:.3f}")
        self.st_l2.set(f"{ev[0]:.3f}")
        self.st_cp.set(f"{abs(M[0,1]) / math.sqrt(M[0,0] * M[1,1]):.2f}")
        self.st_sk.set(f"{np.linalg.norm(S + S.T):.1e}")
        cv = self.cv
        cv.clear()
        ax, bx = cv.axes
        qs = np.linspace(-math.pi, math.pi, 181)
        Ms = np.array([arm.mass_matrix([0.0, a]) for a in qs])
        ax.plot(np.degrees(qs), Ms[:, 0, 0], color=theme.ACCENT, label="M₁₁")
        ax.plot(np.degrees(qs), Ms[:, 0, 1], color=theme.VIOLET, label="M₁₂")
        ax.plot(np.degrees(qs), Ms[:, 1, 1], color=theme.CYAN, label="M₂₂")
        ax.axvline(math.degrees(q[1]), color=theme.WARN, ls=":")
        ax.set_xlabel("q₂ (deg)")
        ax.set_ylabel("kg·m²")
        ax.set_title("M depends on the elbow only")
        cv.legend(ax, loc="upper right")
        # K = 1/2 qd^T M qd = 1 ellipse in joint-velocity space
        w, V = np.linalg.eigh(M)
        E = rk.ellipse_points(V @ np.diag(np.sqrt(2.0 / w)))
        bx.plot(E[:, 0], E[:, 1], color=theme.GOOD, lw=2)
        for k in range(2):
            v = V[:, k] * math.sqrt(2.0 / w[k])
            bx.plot([0, v[0]], [0, v[1]], color=theme.WARN if k else theme.GOOD, lw=1.5)
        bx.set_aspect("equal", adjustable="datalim")
        bx.set_xlabel("q̇₁ (rad/s)")
        bx.set_ylabel("q̇₂ (rad/s)")
        bx.set_title("joint velocities with K = 1 J")
        cv.refresh()


# ==========================================================================
# Newton-Euler
# ==========================================================================

class NewtonEulerPage(Page):
    TITLE = "Recursive Newton–Euler: Inverse Dynamics in O(n)"
    SUBTITLE = ("Push velocities and accelerations out from the base, then "
                "push forces back in from the tip. Two loops, linear in the "
                "number of joints, and the joint torque is the moment each "
                "link needs from the one before it.")
    SECTION = SEC_DYN
    NOTES = playlist_badge(7)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(watch(7))

        b = Card("one rigid body: the Newton–Euler equations")
        b.add(math_label(r"f=m\,a_c,\qquad m_c=\mathcal{I}_c\dot\omega+"
                         r"\omega\times\mathcal{I}_c\omega,\qquad "
                         r"\mathcal{F}_b=\mathcal{G}_b\dot{\mathcal{V}}_b-"
                         r"[\mathrm{ad}_{\mathcal{V}_b}]^T\mathcal{G}_b\mathcal{V}_b", 15))
        b.add(body(
            "Euler's equation has the gyroscopic term ω × Iω, which is zero "
            "in the plane (ω ∥ ẑ, I ẑ ∥ ẑ). The book packs both into the "
            "6×6 spatial inertia G<sub>b</sub> = diag(I<sub>b</sub>, mI) and "
            "the Lie bracket ad<sub>V</sub>, so one line covers a body in any "
            "frame."))
        self.add(b)

        r = Card("the recursion (planar revolute version, as coded)")
        r.add(body(
            "<b>Forward, i = 1 … n</b> (kinematics):<br>"
            "&nbsp;&nbsp;ω<sub>i</sub> = ω<sub>i−1</sub> + q̇<sub>i</sub>, "
            "α<sub>i</sub> = α<sub>i−1</sub> + q̈<sub>i</sub><br>"
            "&nbsp;&nbsp;a<sub>ci</sub> = a<sub>i</sub> + α<sub>i</sub> ẑ×r<sub>ci</sub> − "
            "ω<sub>i</sub>² r<sub>ci</sub>, a<sub>i+1</sub> = a<sub>i</sub> + "
            "α<sub>i</sub> ẑ×l<sub>i</sub> − ω<sub>i</sub>² l<sub>i</sub>,"
            "&nbsp; with a<sub>0</sub> = (0, +g): <b>gravity as a fake upward "
            "base acceleration</b><br>"
            "<b>Backward, i = n … 1</b> (forces):<br>"
            "&nbsp;&nbsp;f<sub>i</sub> = f<sub>i+1</sub> + m<sub>i</sub>a<sub>ci</sub><br>"
            "&nbsp;&nbsp;n<sub>i</sub> = n<sub>i+1</sub> + l<sub>i</sub> × f<sub>i+1</sub> + "
            "r<sub>ci</sub> × m<sub>i</sub>a<sub>ci</sub> + I<sub>i</sub>α<sub>i</sub>,"
            "&nbsp;&nbsp; τ<sub>i</sub> = n<sub>i</sub><br>"
            "&nbsp;&nbsp;f<sub>n+1</sub> = the force the tip applies to the "
            "environment (zero in free space)."))
        r.add(body(
            "Cost: O(n) multiplies, versus O(n³)–O(n⁴) for a symbolic "
            "Lagrangian. Every real-time controller that computes "
            "M q̈ + c + g (computed torque, gravity compensation, "
            "contact-torque estimation) calls this, usually at 1 kHz.",
            dim=True))
        self.add(r)

        lab = Card("trace one call: every intermediate quantity")
        self.n3 = QComboBox()
        self.n3.addItems(["2 links", "3 links"])
        self.n3.currentIndexChanged.connect(self._draw)
        lab.add(self.n3)
        self.q1 = labelled_slider(lab, "q₁", -180, 180, 20, deg, self._draw)
        self.q2 = labelled_slider(lab, "q₂", -180, 180, 50, deg, self._draw)
        self.sp = labelled_slider(lab, "all q̇ᵢ (rad/s)", -40, 40, 10, lambda v: f"{v/10:.1f}", self._draw)
        self.ac = labelled_slider(lab, "all q̈ᵢ (rad/s²)", -50, 50, 0, lambda v: f"{v/10:.1f}", self._draw)
        self.fx = labelled_slider(lab, "tip pushes env., f_x (N)", -30, 30, 0, lambda v: f"{v} N", self._draw)
        self.tbl = body("")
        lab.add(self.tbl)
        self.cv = MplCanvas(width=7.4, height=3.6)
        lab.add(self.cv)
        self.add(lab)
        self._draw()

        self.add(interview(
            "<b>“How would you compute the inverse dynamics of a 7-DOF arm in "
            "real time?”</b> Recursive Newton–Euler: outward pass for link "
            "twists and accelerations (gravity injected as base "
            "acceleration), inward pass for wrenches, project onto joint axes. "
            "O(n). Libraries: Pinocchio, RBDL, KDL, Drake. Follow-ups: M(q) "
            "with n RNEA calls or the Composite Rigid Body Algorithm (O(n²)); "
            "forward dynamics with Featherstone's Articulated Body Algorithm "
            "(O(n)), next page."))
        self.finish()

    def _draw(self):
        n = 2 if self.n3.currentIndex() == 0 else 3
        arm = _arm() if n == 2 else rd.PlanarArm(L=[1, .8, .5], m=[2, 1.5, .8])
        q = np.zeros(n)
        q[0] = math.radians(self.q1.value())
        q[1] = math.radians(self.q2.value())
        if n == 3:
            q[2] = -0.6
        qd = np.full(n, self.sp.value() / 10)
        qdd = np.full(n, self.ac.value() / 10)
        tau, tr = arm.rnea(q, qd, qdd, trace=True, f_tip=[self.fx.value(), 0.0])
        rows = "".join(
            f"<tr><td>{i+1}</td><td>{tr['omega'][i]:+.2f}</td><td>{tr['alpha'][i]:+.2f}</td>"
            f"<td>({tr['acc_c'][i][0]:+.2f}, {tr['acc_c'][i][1]:+.2f})</td>"
            f"<td>({tr['force'][i][0]:+.2f}, {tr['force'][i][1]:+.2f})</td>"
            f"<td><b>{tau[i]:+.3f}</b></td></tr>" for i in range(n))
        self.tbl.setText(
            "<table style='font-family:Consolas' cellpadding='4'>"
            f"<tr style='color:{theme.TEXT_DIM}'><td>link</td><td>ω (rad/s)</td>"
            "<td>α (rad/s²)</td><td>a_c incl. +g (m/s²)</td><td>f from link before (N)</td>"
            "<td>τ (N·m)</td></tr>" + rows + "</table>"
            f"<span style='color:{theme.TEXT_DIM}'>Forward pass fills ω, α, a_c top to bottom; "
            "backward pass fills f and τ bottom to top.</span>")
        cv = self.cv
        cv.clear()
        ax = cv.ax
        pts = draw_arm(ax, arm.L, q)
        ang = np.cumsum(q)
        for i in range(n):
            c = pts[i] + arm.r[i] * np.array([math.cos(ang[i]), math.sin(ang[i])])
            ax.quiver(*c, *(tr["acc_c"][i] / 30), color=theme.VIOLET, angles="xy",
                      scale_units="xy", scale=1, width=0.005)
            ax.quiver(*pts[i], *(tr["force"][i] / 60), color=theme.BAD, angles="xy",
                      scale_units="xy", scale=1, width=0.007)
        if self.fx.value():
            ax.quiver(*pts[-1], self.fx.value() / 60, 0, color=theme.WARN, angles="xy",
                      scale_units="xy", scale=1, width=0.007)
        square(ax, 2.6)
        ax.set_title("violet: a_c (incl. fake +g)   red: joint reaction force on link")
        cv.refresh()


# ==========================================================================
# Inverse dynamics along a trajectory
# ==========================================================================

class InverseDynamicsPage(Page):
    TITLE = "Inverse Dynamics: Torque From a Trajectory"
    SUBTITLE = ("Given q(t), q̇(t), q̈(t), the torque is τ = M q̈ + c + g — "
                "computed, not simulated. Split it and you see what dominates "
                "at each speed: halve the move time and the inertial part "
                "quadruples while gravity does not move.")
    SECTION = SEC_DYN
    NOTES = playlist_badge(7)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(watch(7))

        u = Card("what inverse dynamics is for")
        u.add(body(
            "<b>Feedforward.</b> τ<sub>ff</sub>(t) = M q̈<sub>d</sub> + c + g "
            "along the planned path, so feedback only fixes errors.<br>"
            "<b>Actuator sizing.</b> peak and RMS torque over the task decide "
            "motor and gearbox; RMS sets heating.<br>"
            "<b>Feasibility.</b> if τ(t) exceeds a limit anywhere, the "
            "trajectory must be slowed (time scaling, playlist 8).<br>"
            "<b>Contact estimation.</b> τ<sub>measured</sub> − τ<sub>ID</sub> "
            "= Jᵀ F<sub>ext</sub>: collision detection without a skin."))
        u.add(math_label(r"q(s(t)),\ \dot q=q'(s)\dot s,\ \ddot q=q'\ddot s+q''\dot s^2"
                         r"\ \Rightarrow\ \tau\propto\frac{1}{T^2}\ (\mathrm{inertial,\ Coriolis})"
                         r",\ \ \tau\propto T^0\ (\mathrm{gravity})", 15))
        self.add(u)

        lab = Card("a quintic move from A to B: the torque, term by term")
        self.T = labelled_slider(lab, "move duration T", 3, 40, 12,
                                 lambda v: f"{v/10:.1f} s", self._draw)
        self.pay = labelled_slider(lab, "payload (kg)", 0, 50, 10,
                                   lambda v: f"{v/10:.1f}", self._draw)
        self.joint = QComboBox()
        self.joint.addItems(["shoulder (joint 1)", "elbow (joint 2)"])
        self.joint.currentIndexChanged.connect(self._draw)
        lab.add(self.joint)
        self.st_pk = Stat("peak |τ|", "--", theme.BAD)
        self.st_rms = Stat("RMS τ", "--", theme.WARN)
        self.st_g = Stat("gravity share of peak", "--", theme.GOOD)
        lab.add_layout(stat_row(self.st_pk, self.st_rms, self.st_g))
        self.cv = MplCanvas(width=7.6, height=3.8, ncols=2)
        lab.add(self.cv)
        self.add(lab)
        self._draw()

        self.add(interview(
            "<b>“Inverse vs forward dynamics — which one does a controller "
            "use and which one does a simulator use?”</b> Controllers use "
            "inverse dynamics: desired motion in, torque out (computed torque, "
            "feedforward, gravity compensation). Simulators use forward "
            "dynamics: torque in, acceleration out, then integrate. Same "
            "equation, solved for different unknowns; ID is a direct O(n) "
            "evaluation, FD needs a linear solve with M (or ABA)."))
        self.finish()

    def _draw(self):
        T = self.T.value() / 10
        pay = self.pay.value() / 10
        m2 = ARM["m"][1] + pay
        r2 = (ARM["m"][1] * ARM["r"][1] + pay * ARM["L"][1]) / m2
        arm = rd.PlanarArm(L=ARM["L"], m=[ARM["m"][0], m2], r=[ARM["r"][0], r2],
                           I=[ARM["I"][0], ARM["I"][1] + pay * (ARM["L"][1] - r2) ** 2])
        qA, qB = np.array([-1.2, 1.6]), np.array([0.9, 0.4])
        ts = np.linspace(0, T, 160)
        s, sd, sdd = rd.quintic(ts, T)
        Q = qA + np.outer(s, qB - qA)
        QD = np.outer(sd, qB - qA)
        QDD = np.outer(sdd, qB - qA)
        parts = np.zeros((len(ts), 3, 2))
        for k in range(len(ts)):
            g = arm.gravity(Q[k])
            c = arm.h(Q[k], QD[k]) - g
            parts[k] = [arm.mass_matrix(Q[k]) @ QDD[k], c, g]
        tau = parts.sum(axis=1)
        j = self.joint.currentIndex()
        pk = np.abs(tau[:, j]).max()
        self.st_pk.set(f"{pk:.1f} N·m")
        self.st_rms.set(f"{math.sqrt(np.mean(tau[:, j] ** 2)):.1f} N·m")
        self.st_g.set(f"{100 * np.abs(parts[:, 2, j]).max() / pk:.0f}%")
        cv = self.cv
        cv.clear()
        ax, bx = cv.axes
        for k in range(0, len(ts), 16):
            draw_arm(ax, arm.L, Q[k], ghost=True)
        draw_arm(ax, arm.L, qA, color=theme.TEXT_DIM, lw=2)
        draw_arm(ax, arm.L, qB)
        square(ax, 2.0)
        ax.set_title("A (grey) → B (cyan), quintic time scaling")
        bx.plot(ts, parts[:, 0, j], color=theme.ACCENT, label="M q̈")
        bx.plot(ts, parts[:, 1, j], color=theme.VIOLET, label="c(q, q̇)")
        bx.plot(ts, parts[:, 2, j], color=theme.WARN, label="g(q)")
        bx.plot(ts, tau[:, j], color=theme.TEXT, lw=2.2, label="τ total")
        bx.set_xlabel("time (s)")
        bx.set_ylabel("N·m")
        cv.legend(bx, loc="best")
        cv.refresh()


# ==========================================================================
# Forward dynamics
# ==========================================================================

class ForwardDynamicsPage(Page):
    TITLE = "Forward Dynamics and Simulation"
    SUBTITLE = ("q̈ = M(q)⁻¹(τ − c − g), then integrate. Build M from n "
                "inverse-dynamics calls, solve, step. The integrator you "
                "choose decides whether a frictionless pendulum keeps its "
                "energy or slowly explodes.")
    SECTION = SEC_DYN
    NOTES = playlist_badge(7)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(watch(7))

        a = Card("three ways to get q̈")
        a.add(math_label(r"M(q)\ddot q=\tau-h(q,\dot q),\quad "
                         r"h=\mathrm{RNEA}(q,\dot q,0),\quad "
                         r"M_{:,i}=\mathrm{RNEA}(q,0,e_i)\big|_{g=0}", 16))
        a.add(body(
            "<b>RNEA n+1 times + Cholesky</b> (what this page does): O(n³), "
            "fine for n ≤ 10.<br>"
            "<b>Composite Rigid Body Algorithm</b>: M directly in O(n²), "
            "then solve.<br>"
            "<b>Articulated Body Algorithm</b> (Featherstone): O(n) with no "
            "matrix at all, by propagating 'articulated inertias' inward. "
            "MuJoCo, Drake, Pinocchio, RBDL all ship it."))
        self.add(a)

        lab = Card("a passive double pendulum: chaos, and integrator honesty")
        self.meth = QComboBox()
        self.meth.addItems(["RK4", "semi-implicit (symplectic) Euler", "explicit Euler"])
        self.meth.currentIndexChanged.connect(self._sim)
        lab.add(self.meth)
        self.dt = labelled_slider(lab, "time step dt", 1, 30, 5,
                                  lambda v: f"{v} ms", self._sim, tracking=False)
        self.q0 = labelled_slider(lab, "initial q₁", -180, 180, 100, deg, self._sim,
                                  tracking=False)
        self.b = labelled_slider(lab, "joint friction b", 0, 50, 0,
                                 lambda v: f"{v/100:.2f} N·m·s", self._sim, tracking=False)
        btns = QHBoxLayout()
        self.play = QPushButton("Play")
        self.play.setObjectName("Primary")
        self.play.clicked.connect(self._toggle)
        btns.addWidget(self.play)
        btns.addStretch(1)
        lab.add_layout(btns)
        self.st_e = Stat("energy drift after 6 s", "--", theme.WARN)
        self.st_c = Stat("cost (RNEA calls)", "--", theme.ACCENT)
        lab.add_layout(stat_row(self.st_e, self.st_c))
        self.cv = MplCanvas(width=7.6, height=3.8, ncols=2)
        lab.add(self.cv)
        self.add(lab)
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._frame)
        self.k = 0
        self._sim()

        self.add(callout(
            "Explicit Euler pumps energy in every step; with friction off the "
            "pendulum swings ever higher. Semi-implicit Euler is symplectic: "
            "energy wobbles but does not drift. RK4 is accurate per step but "
            "not symplectic, so over very long runs it drifts too. Physics "
            "engines choose semi-implicit (MuJoCo, Bullet) for robustness; "
            "trajectory optimisers choose RK4 or collocation for accuracy.",
            "key"))

        self.add(interview(
            "<b>“How does a physics simulator step a robot?”</b> Read τ from "
            "the controller, compute q̈ = FD(q, q̇, τ) (ABA or M⁻¹ via "
            "Cholesky), add contact forces from a constraint solver (LCP / "
            "complementarity, or soft contacts), integrate with a small fixed "
            "step (semi-implicit Euler at ~1 ms). Sim-to-real gaps come from "
            "the parts not in M, c, g: friction, backlash, motor dynamics, "
            "contact compliance, delay."))
        self.finish()

    def _sim(self):
        self.timer.stop()
        self.play.setText("Play")
        b = self.b.value() / 100
        arm = _arm(friction=[b, b])
        dt = self.dt.value() / 1000
        method = ("rk4", "semi", "euler")[self.meth.currentIndex()]
        q0 = [math.radians(self.q0.value()), 0.0]
        ts, Q, QD, _ = rd.simulate(arm, q0, [0, 0], 6.0, dt, method=method)
        E = np.array([sum(arm.energy(a, v)) for a, v in zip(Q, QD)])
        self.arm, self.ts, self.Q, self.E = arm, ts, Q, E
        self.st_e.set(f"{E[-1] - E[0]:+.2f} J")
        self.st_e.set_color(theme.GOOD if abs(E[-1] - E[0]) < 0.05 else theme.BAD)
        calls = len(ts) * (4 if method == "rk4" else 1) * (arm.n + 1)
        self.st_c.set(f"{calls:,}")
        self.k = len(ts) - 1
        self._draw()

    def _toggle(self):
        if self.timer.isActive():
            self.timer.stop()
            self.play.setText("Play")
        else:
            self.k = 0
            self.timer.start()
            self.play.setText("Pause")

    def on_hide(self):
        self.timer.stop()
        self.play.setText("Play")

    def _frame(self):
        step = max(1, int(0.033 / (self.ts[1] - self.ts[0])))
        self.k = min(self.k + step, len(self.ts) - 1)
        self._draw(layout=False)
        if self.k >= len(self.ts) - 1:
            self.timer.stop()
            self.play.setText("Play")

    def _draw(self, layout=True):
        k = self.k
        cv = self.cv
        cv.clear()
        ax, bx = cv.axes
        tips = np.array([rk.planar_points(self.arm.L, q)[-1] for q in self.Q[:k + 1:3]])
        if len(tips):
            ax.plot(tips[:, 0], tips[:, 1], color=theme.VIOLET, lw=0.7, alpha=0.6)
        draw_arm(ax, self.arm.L, self.Q[k])
        square(ax, 2.0)
        ax.set_title(f"t = {self.ts[k]:.2f} s")
        bx.plot(self.ts[:k + 1], self.E[:k + 1] - self.E[0], color=theme.WARN)
        bx.set_xlim(0, self.ts[-1])
        bx.set_xlabel("time (s)")
        bx.set_ylabel("E(t) − E(0)  (J)")
        bx.set_title("total energy error")
        cv.refresh(layout=layout)


# ==========================================================================
# Task-space dynamics
# ==========================================================================

class TaskDynamicsPage(Page):
    TITLE = "Task-Space Dynamics: The Mass the Hand Feels"
    SUBTITLE = ("Rewrite the equations of motion in hand coordinates: "
                "Λ(q)ẍ + μ(q,q̇) + p(q) = F. Λ is the inertia an object feels "
                "when the hand hits it, and it depends on direction.")
    SECTION = SEC_DYN
    NOTES = playlist_badge(7)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(watch(7))

        d = Card("from joint space to task space")
        d.add(math_label(r"\dot x=J\dot q,\ \ddot x=J\ddot q+\dot J\dot q,\ "
                         r"\tau=J^TF\quad\Rightarrow\quad\Lambda\ddot x+\mu+p=F", 16))
        d.add(math_label(r"\Lambda=(JM^{-1}J^T)^{-1},\quad \bar J=M^{-1}J^T\Lambda,\quad "
                         r"\mu=\bar J^Tc-\Lambda\dot J\dot q,\quad p=\bar J^Tg", 16))
        d.add(body(
            "Derivation: q̈ = M⁻¹(JᵀF − c − g); multiply by J and add J̇q̇; "
            "solve for F. When J is square and invertible Λ = J⁻ᵀMJ⁻¹; "
            "the expression with M⁻¹ also works for redundant arms. "
            "J̄ is the <b>dynamically consistent generalised inverse</b>: "
            "J J̄ = I, and it is the M-weighted pseudo-inverse, so it yields "
            "the minimum-kinetic-energy joint motion for a given hand motion."))
        self.add(d)

        lab = Card("effective mass at the hand, by direction")
        lab.add(body(
            "The mass felt along unit direction u is m<sub>u</sub> = "
            "1/(uᵀΛ⁻¹u) — what an obstacle feels in a collision along u. "
            "Fold the elbow toward straight: along the arm Λ blows up "
            "(the structure, not the motors, carries the impact).", dim=True))
        self.q1 = labelled_slider(lab, "q₁", -180, 180, 20, deg, self._draw)
        self.q2 = labelled_slider(lab, "q₂", -175, 175, 70, deg, self._draw)
        self.L_txt = body("")
        lab.add(self.L_txt)
        self.st_mn = Stat("lightest direction", "--", theme.GOOD)
        self.st_mx = Stat("heaviest direction", "--", theme.BAD)
        lab.add_layout(stat_row(self.st_mn, self.st_mx))
        self.cv = MplCanvas(width=7.6, height=3.8, ncols=2)
        lab.add(self.cv)
        self.add(lab)
        self._draw()

        self.add(callout(
            "Why this matters beyond control: the impact force of a "
            "collision scales with √(m<sub>u</sub> k) × speed, so ISO/TS 15066 "
            "speed limits for collaborative robots are really limits on "
            "Λ along the motion direction. Lightweight arms and backdrivable "
            "low-ratio actuators lower Λ; a high-ratio gearbox adds "
            "N²J<sub>m</sub> to M and therefore to Λ.", "key"))

        self.add(interview(
            "<b>“What is the operational space inertia matrix?”</b> "
            "Λ = (JM⁻¹Jᵀ)⁻¹: the end-effector's apparent inertia, the matrix "
            "that relates a hand force to hand acceleration. It is "
            "configuration and direction dependent, singular-infinite at "
            "kinematic singularities, and it is the 'M' of the task-space "
            "equations that Khatib's operational space controller cancels."))
        self.finish()

    def _draw(self):
        arm = _arm()
        q = np.radians([self.q1.value(), self.q2.value()])
        J = arm.jacobian(q)
        Li = J @ np.linalg.solve(arm.mass_matrix(q), J.T)     # Λ⁻¹, always defined
        if np.linalg.cond(Li) < 1e8:
            Lam, Jbar, mu, p = arm.task_space(q, np.zeros(2))
            self.L_txt.setText("Λ(q) (kg) =" + mat_html(Lam) +
                               f"p(q) = J̄ᵀg = ({p[0]:+.2f}, {p[1]:+.2f}) N")
        else:
            self.L_txt.setText("Λ⁻¹ = J M⁻¹ Jᵀ is singular here: the arm is straight "
                               "and Λ is infinite along it." + mat_html(Li))
        th = np.linspace(0, 2 * math.pi, 361)
        mu_ = np.array([1.0 / max(np.array([math.cos(t), math.sin(t)]) @ Li
                                  @ np.array([math.cos(t), math.sin(t)]), 1e-6) for t in th])
        self.st_mn.set(f"{mu_.min():.2f} kg @ {math.degrees(th[np.argmin(mu_)]) % 180:.0f}°")
        self.st_mx.set(f"{mu_.max():.2f} kg @ {math.degrees(th[np.argmax(mu_)]) % 180:.0f}°")
        cv = self.cv
        cv.clear()
        ax, bx = cv.axes
        pts = draw_arm(ax, arm.L, q)
        tip = pts[-1]
        sc = 0.6 / max(mu_.max(), 1e-9) if mu_.max() > 0 else 1
        sc = min(sc, 0.2)
        ax.plot(tip[0] + sc * mu_ * np.cos(th), tip[1] + sc * mu_ * np.sin(th),
                color=theme.WARN, lw=1.6, label="m_u by direction (scaled)")
        square(ax, 2.0)
        cv.legend(ax, loc="lower left")
        bx.plot(np.degrees(th), mu_, color=theme.WARN)
        bx.set_yscale("log")
        bx.set_xlabel("direction of hand motion (deg)")
        bx.set_ylabel("effective mass (kg)")
        cv.refresh()


# ==========================================================================
# Constrained dynamics
# ==========================================================================

class ConstrainedDynamicsPage(Page):
    TITLE = "Constrained Dynamics and Contact Forces"
    SUBTITLE = ("Hold the hand on a wall and the wall pushes back with exactly "
                "the force needed to keep it there. That force is a Lagrange "
                "multiplier, and when it changes sign the contact is about to "
                "break.")
    SECTION = SEC_DYN
    NOTES = playlist_badge(7)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(watch(7))

        e = Card("equations of motion with k constraints A(q)q̇ = 0")
        e.add(math_label(r"\begin{bmatrix}M&-A^T\\ A&0\end{bmatrix}"
                         r"\begin{bmatrix}\ddot q\\ \lambda\end{bmatrix}="
                         r"\begin{bmatrix}\tau-h\\ -\dot A\dot q\end{bmatrix}", 17))
        e.add(body(
            "Aᵀλ is the generalised constraint force; λ is the contact force "
            "itself when A is the contact Jacobian's normal row. The "
            "constraint does no work (Aq̇ = 0 ⇒ q̇ᵀAᵀλ = 0). Equivalently, "
            "project the dynamics with P = I − Aᵀ(AM⁻¹Aᵀ)⁻¹AM⁻¹ "
            "and only n − k equations remain — exactly the reduced C-space of "
            "the Constraints page. A contact is <b>unilateral</b>: λ ≥ 0 into "
            "the surface, and the arm lifts off when the solve asks for a pull. "
            "Simulators turn that into a complementarity problem."))
        self.add(e)

        lab = Card("2R hand on a vertical wall, sliding under gravity")
        lab.add(body(
            "The tip is constrained to x = x<sub>wall</sub> (Baumgarte "
            "stabilised so numerical drift is pulled back). Motor torque "
            "pushes the hand into the wall; gravity drags it down; λ is what "
            "the wall pushes back. Drag the push negative and λ would have "
            "to pull — that is the moment a real contact lifts off.", dim=True))
        self.push = labelled_slider(lab, "commanded wall push (N)", -20, 40, 15,
                                    lambda v: f"{v} N", self._sim, tracking=False)
        self.hold = labelled_slider(lab, "vertical support (N)", 0, 40, 10,
                                    lambda v: f"{v} N", self._sim, tracking=False)
        self.st_l = Stat("final wall force", "--", theme.ACCENT)
        self.st_d = Stat("max constraint drift", "--", theme.GOOD)
        self.st_lift = Stat("contact stays closed?", "--", theme.GOOD)
        lab.add_layout(stat_row(self.st_l, self.st_d, self.st_lift))
        self.cv = MplCanvas(width=7.6, height=3.8, ncols=2)
        lab.add(self.cv)
        self.add(lab)
        self._sim()

        self.add(interview(
            "<b>“How do you control a legged robot's contact forces?”</b> "
            "Write floating-base dynamics M q̈ + h = Sᵀτ + J<sub>c</sub>ᵀλ with "
            "S selecting actuated joints. Choose λ inside friction cones that "
            "produce the desired centroidal momentum change (a QP), then "
            "τ from the actuated rows. The equality-constrained system above "
            "is the core of that whole-body controller; the friction cone is "
            "the inequality that makes it a QP."))
        self.finish()

    def _sim(self):
        arm = _arm()
        xw = 1.1
        q = rk.ik_2r(*arm.L, xw, 0.6, 1)
        qd = np.zeros(2)
        dt = 0.002
        ts, ys, lams, drift = [], [], [], []
        push, hold = self.push.value(), self.hold.value()
        for k in range(1500):
            t = k * dt
            F = np.array([push, hold])
            tau = arm.jacobian(q).T @ F
            q, qd, lam = rd.wall_constrained_step(arm, q, qd, tau, xw, dt)
            tip = arm.tip(q)
            ts.append(t)
            ys.append(tip[1])
            lams.append(lam)
            drift.append(abs(tip[0] - xw))
        lams = np.array(lams)
        self.st_l.set(f"{-lams[-1]:+.1f} N into arm")
        self.st_d.set(f"{max(drift) * 1000:.2f} mm")
        lift = np.any(lams > 0)
        self.st_lift.set("NO — wall would have to pull" if lift else "yes")
        self.st_lift.set_color(theme.BAD if lift else theme.GOOD)
        cv = self.cv
        cv.clear()
        ax, bx = cv.axes
        draw_arm(ax, arm.L, q)
        ax.axvline(xw, color=theme.TEXT_DIM, lw=5)
        square(ax, 2.0)
        ax.set_title("final pose; grey = wall")
        bx.plot(ts, -lams, color=theme.ACCENT, label="wall push on hand, −λ (N)")
        bx.plot(ts, np.array(ys) * 20, color=theme.VIOLET, label="hand height ×20 (m)")
        bx.axhline(0, color=theme.BAD, ls=":")
        bx.set_xlabel("time (s)")
        cv.legend(bx, loc="best")
        cv.refresh()
