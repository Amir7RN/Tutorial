"""
ROBOT MECHANICS, part 1 -- configuration space and rigid-body motion.
Modern Robotics playlists 1 and 2 (chapters 2 and 3).

    roadmap          the twelve playlists, and which page answers which
    C-space          degrees of freedom, Gruebler, topology
    constraints      holonomic vs nonholonomic; task space vs workspace
    rotations        SO(3), so(3), Rodrigues, the matrix log
    twists/wrenches  SE(3), screw axes, the adjoint, and power = V . F
"""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtWidgets import QComboBox

from ctrlcore import robokin as rk
from .. import theme
from ..widgets import Card, MplCanvas, Stat, body, callout, math_label, stat_row
from .base import Page
from .robo_common import (
    PL,
    PLAYLISTS,
    SEC_CSPACE,
    deg,
    draw_arm,
    interview,
    labelled_slider,
    mat_html,
    playlist_badge,
    square,
    watch,
)


# ==========================================================================
# Roadmap
# ==========================================================================

class RoboRoadmapPage(Page):
    TITLE = "Robot Mechanics: The Missing Half"
    SUBTITLE = ("Everything before this page controlled one joint, or a model "
                "someone handed you. A robotics interview starts one level "
                "lower: where is the hand, how fast does it move, what torque "
                "does that take. This block derives all of it.")
    SECTION = SEC_CSPACE
    NOTES = "roadmap · 12 playlists"

    def __init__(self, parent=None):
        super().__init__(parent)

        c = Card("why the control pages were not enough")
        c.add(body(
            "Pages 1–51 treated the plant as given: <i>Jθ̈ + bθ̇ = τ</i>, or "
            "<i>M(q)q̈ + C q̇ + g = τ</i> quoted once on the arm capstone. An "
            "interviewer asks where that equation comes from, why M is "
            "symmetric positive definite, what the Jacobian's null space is "
            "for, and how to make a hand follow a line while the elbow does "
            "something else. Those are kinematics and dynamics questions, and "
            "no amount of pole placement answers them."))
        c.add(body(
            "The chain of ideas is one line long, and every page below is one "
            "link of it:", dim=True))
        c.add(math_label(
            r"q \;\rightarrow\; T(q) \;\rightarrow\; "
            r"\mathcal{V}=J(q)\dot q \;\rightarrow\; "
            r"\tau=J^TF \;\rightarrow\; "
            r"\tau=M(q)\ddot q+c(q,\dot q)+g(q)", 15))
        self.add(c)

        t = Card("the twelve playlists, one by one")
        rows = "".join(
            f"<tr><td style='padding:3px 10px; color:{theme.WARN}'><b>{n}</b></td>"
            f"<td style='padding:3px 10px'>ch. {ch}</td>"
            f"<td style='padding:3px 10px'><a style='color:{theme.CYAN}' "
            f"href='{PL}{pid}'>{title}</a></td>"
            f"<td style='padding:3px 10px; color:{theme.TEXT_DIM}'>{pages}</td></tr>"
            for n, ch, title, pid, pages in PLAYLISTS)
        lb = body(f"<table>{rows}</table>")
        lb.setOpenExternalLinks(True)
        t.add(lb)
        t.add(body(
            "Read in this order. Each page's badge names its playlist, and "
            "each opens with a <b>Watch alongside</b> link. Watch the videos "
            "for the derivation, then use the page to break the result with "
            "sliders until it stops surprising you.", dim=True))
        self.add(t)

        p = Card("what to master for an interview, ranked")
        p.add(body(
            "<b>1. Jacobian, both directions.</b> ẋ = J q̇ for velocity, "
            "τ = Jᵀ F for force, and why the same matrix does both (power is "
            "frame-independent).<br>"
            "<b>2. Singularities and null space.</b> rank-deficient J, the "
            "manipulability ellipse, J⁺, N = I − J⁺J, self-motion.<br>"
            "<b>3. Inverse dynamics vs forward dynamics.</b> τ from (q, q̇, q̈) "
            "by recursive Newton–Euler in O(n); q̈ from τ by solving M q̈ = τ − h.<br>"
            "<b>4. Properties of M(q) and C.</b> symmetric, positive definite, "
            "configuration dependent; Ṁ − 2C skew-symmetric, which is the "
            "passivity property every Lyapunov proof uses.<br>"
            "<b>5. Task-space dynamics.</b> Λ = (J M⁻¹ Jᵀ)⁻¹, the dynamically "
            "consistent inverse J̄, and the null-space torque projector "
            "I − Jᵀ J̄ᵀ.<br>"
            "<b>6. Control built on all of it.</b> computed torque, operational "
            "space control, impedance and hybrid force control."))
        self.add(p)

        self.add(callout(
            "The block reuses the planar arm on purpose. A 2R or 3R planar arm "
            "has every structure of a 7-DOF manipulator — coupling, Coriolis "
            "terms, gravity, singularities, redundancy — with matrices small "
            "enough to check by hand on a whiteboard, which is exactly where "
            "the interview will put you.", "key"))
        self.finish()


# ==========================================================================
# Playlist 1 -- configuration space
# ==========================================================================

_MECHS = {
    "planar 3R open chain": (4, [1, 1, 1], 3,
                             "Three links plus ground, three revolute joints."),
    "four-bar linkage": (4, [1, 1, 1, 1], 3,
                         "The loop closes: four joints, but only one freedom."),
    "slider-crank": (4, [1, 1, 1, 1], 3,
                     "Three revolute joints and one prismatic. Still one DOF."),
    "planar five-bar": (5, [1] * 5, 3,
                        "Two cranks driven independently: a 2-DOF parallel robot."),
    "Stephenson six-bar": (6, [1] * 7, 3,
                           "Seven joints, six links: one DOF again."),
    "6R industrial arm": (7, [1] * 6, 6,
                          "Spatial open chain: the classic six-axis manipulator."),
    "7R redundant arm": (8, [1] * 7, 6,
                         "One more joint than task freedoms: a null space appears."),
    "Stewart platform": (14, [2] * 6 + [1] * 6 + [3] * 6, 6,
                         "Six UPS legs. 14 links, 18 joints, six freedoms."),
    "Delta robot": (11, [1] * 3 + [3] * 12, 6,
                    "Three arms, each forearm a parallelogram of two S–S rods. "
                    "Grübler gives 9, but six of those are idle spins of the rods "
                    "about their own axes: the platform itself has 3."),
}


class CSpacePage(Page):
    TITLE = "Configuration Space and Degrees of Freedom"
    SUBTITLE = ("The configuration is the smallest list of numbers that pins "
                "every point of the robot. Its length is the number of degrees "
                "of freedom, and Grübler's formula counts it without drawing.")
    SECTION = SEC_CSPACE
    NOTES = playlist_badge(1)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(watch(1))

        d = Card("dof = freedoms of the bodies − constraints of the joints")
        d.add(math_label(
            r"\mathrm{dof}=m(N-1-J)+\sum_{i=1}^{J} f_i,\qquad "
            r"m=3\ (\mathrm{planar}),\; m=6\ (\mathrm{spatial})", 16))
        d.add(body(
            "N counts links <b>including ground</b>. Each free body has m "
            "freedoms; ground has none; each joint removes m − f<sub>i</sub>. "
            "Revolute and prismatic joints have f = 1, universal 2, spherical "
            "3. The formula assumes the joint constraints are independent — "
            "special geometry (parallel links, the Delta robot's "
            "parallelograms) can make it lie, and the true answer is then the "
            "rank of the constraint Jacobian, which is the closed-chains page's subject."))
        self.add(d)

        g = Card("count it: pick a mechanism")
        self.combo = QComboBox()
        for k in _MECHS:
            self.combo.addItem(k)
        self.combo.currentIndexChanged.connect(self._mech)
        g.add(self.combo)
        self.mech_txt = body("")
        g.add(self.mech_txt)
        self.st_N = Stat("links N (incl. ground)", "--", theme.ACCENT)
        self.st_J = Stat("joints J", "--", theme.VIOLET)
        self.st_f = Stat("Σ f_i", "--", theme.CYAN)
        self.st_dof = Stat("dof", "--", theme.GOOD)
        g.add_layout(stat_row(self.st_N, self.st_J, self.st_f, self.st_dof))
        self.add(g)
        self._mech()

        t = Card("the shape of C-space: topology, not just dimension")
        t.add(body(
            "Two joint angles give a 2-dimensional C-space, but it is a "
            "<b>torus</b> T² = S¹ × S¹, not the plane ℝ²: turning q₁ by 2π "
            "returns you to the same arm. A rigid body in space has "
            "C-space ℝ³ × SO(3), six dimensional, and SO(3) cannot be covered "
            "by three angles without a singularity (gimbal lock). This is why "
            "the next pages use rotation matrices and exponential coordinates "
            "rather than Euler angles."))
        t.add(body(
            "Drag the joints: the left panel is the arm in its workspace, the "
            "right is the same configuration as one point in C-space. Every "
            "edge of the right panel is glued to the opposite edge.", dim=True))
        self.s1 = labelled_slider(t, "q₁", -180, 180, 40, deg, self._draw)
        self.s2 = labelled_slider(t, "q₂", -180, 180, 70, deg, self._draw)
        self.cv = MplCanvas(width=7.6, height=3.6, ncols=2)
        t.add(self.cv)
        self.add(t)
        self._trail = []
        self._draw()

        self.add(interview(
            "<b>“How many DOF does a rigid body in space have, and why can't "
            "you represent its orientation with three numbers everywhere?”</b> "
            "Six: three for position, three for orientation. SO(3) is a 3-D "
            "manifold that is not homeomorphic to any open set of ℝ³, so every "
            "3-parameter chart (ZYX Euler, roll–pitch–yaw) has a singularity "
            "somewhere — at pitch ±90° for ZYX. Use rotation matrices or unit "
            "quaternions for computation; use three-number exponential "
            "coordinates only locally."))
        self.finish()

    def _mech(self):
        k = self.combo.currentText()
        N, f, m, txt = _MECHS[k]
        self.mech_txt.setText(txt)
        self.st_N.set(str(N))
        self.st_J.set(str(len(f)))
        self.st_f.set(str(sum(f)))
        self.st_dof.set(str(rk.grubler(N, f, m)))

    def _draw(self):
        L = [1.0, 0.8]
        q = np.radians([self.s1.value(), self.s2.value()])
        self._trail = (self._trail + [q.copy()])[-60:]
        c = self.cv
        c.clear()
        a1, a2 = c.axes
        for qq in self._trail[:-1]:
            draw_arm(a1, L, qq, ghost=True)
        draw_arm(a1, L, q)
        square(a1, 2.0)
        a1.set_title("workspace (what you see)")
        tr = np.degrees(np.array(self._trail))
        a2.plot(tr[:, 0], tr[:, 1], ".", color=theme.TEXT_FAINT, ms=3)
        a2.plot(*np.degrees(q), "o", color=theme.WARN, ms=9)
        a2.set_xlim(-180, 180)
        a2.set_ylim(-180, 180)
        a2.set_xlabel("q₁ (deg)")
        a2.set_ylabel("q₂ (deg)")
        a2.set_title("C-space: a torus, edges glued")
        c.refresh()


class ConstraintsPage(Page):
    TITLE = "Constraints, Task Space and Workspace"
    SUBTITLE = ("Holonomic constraints shrink the C-space; nonholonomic ones "
                "only restrict velocities. Task space is where you describe the "
                "job; workspace is where the hand can actually reach.")
    SECTION = SEC_CSPACE
    NOTES = playlist_badge(1)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(watch(1))

        h = Card("holonomic: a constraint on q")
        h.add(math_label(r"g(q)=0\quad\Rightarrow\quad "
                         r"\frac{\partial g}{\partial q}\,\dot q = A(q)\,\dot q = 0", 16))
        h.add(body(
            "A closed loop is holonomic: the four-bar's loop-closure equations "
            "g(q) = 0 remove three of the four joint angles. Differentiate and "
            "you get a <b>Pfaffian</b> velocity constraint A(q)q̇ = 0 that came "
            "from a position constraint — so it is integrable, and the "
            "C-space itself is smaller."))
        self.add(h)

        n = Card("nonholonomic: a constraint on q̇ that is NOT integrable")
        n.add(math_label(r"A(q)\dot q=\left[-\sin\phi\;\;\cos\phi\;\;0\right]"
                         r"\begin{bmatrix}\dot x\\ \dot y\\ \dot\phi\end{bmatrix}=0", 16))
        n.add(body(
            "A rolling wheel cannot slide sideways. That is one constraint on "
            "velocity, yet a car can still reach every (x, y, φ) — parallel "
            "parking is the proof. The constraint reduces the <b>velocity "
            "freedoms</b> (2 instead of 3) but not the dimension of C-space "
            "(still 3). Playlist 12 spends a whole chapter here."))
        self.add(n)

        w = Card("task space versus workspace")
        w.add(body(
            "<b>Task space</b> is a choice of coordinates for the job: (x, y) of "
            "the pen, (x, y, z, R) of a gripper, or just the height of a "
            "spray nozzle. <b>Workspace</b> is the set of task-space points "
            "the robot can actually reach. A 3R planar arm drawing on paper "
            "has a 3-D C-space, a 2-D task space, and its workspace is an "
            "annulus — and because 3 > 2 it is <b>redundant</b> for this task."
            "<br><br>Slide the link lengths: the workspace of a 2R arm is an "
            "annulus with radii |L₁ − L₂| and L₁ + L₂. The dexterous "
            "workspace (reachable at every orientation) is much smaller."))
        self.s1 = labelled_slider(w, "L₁ (m)", 2, 20, 10, lambda v: f"{v/10:.1f}", self._draw)
        self.s2 = labelled_slider(w, "L₂ (m)", 2, 20, 7, lambda v: f"{v/10:.1f}", self._draw)
        self.s3 = labelled_slider(w, "L₃ (m)", 0, 10, 0, lambda v: f"{v/10:.1f}", self._draw)
        self.st_in = Stat("inner radius", "--", theme.WARN)
        self.st_out = Stat("outer radius", "--", theme.GOOD)
        self.st_red = Stat("redundancy for (x, y)", "--", theme.VIOLET)
        w.add_layout(stat_row(self.st_in, self.st_out, self.st_red))
        self.cv = MplCanvas(width=7.4, height=3.6, ncols=2)
        w.add(self.cv)
        self.add(w)
        self._draw()

        self.add(interview(
            "<b>“Is a car's rolling constraint holonomic?”</b> No. "
            "−sin φ ẋ + cos φ ẏ = 0 has no integrating factor, so it does not "
            "come from any g(x, y, φ) = 0. Test: the Lie bracket of the two "
            "allowed velocity fields (drive, turn) produces the forbidden "
            "sideways direction, so the reachable set is all of C-space "
            "(Chow's theorem). Consequence: a car needs a planner and cannot "
            "be stabilised to a point by smooth time-invariant feedback "
            "(Brockett)."))
        self.finish()

    def _draw(self):
        L = [self.s1.value() / 10, self.s2.value() / 10]
        L3 = self.s3.value() / 10
        if L3 > 0:
            L = L + [L3]
        R = sum(L)
        longest = max(L)
        inner = max(0.0, longest - (R - longest))
        self.st_in.set(f"{inner:.2f} m")
        self.st_out.set(f"{R:.2f} m")
        self.st_red.set(f"{len(L) - 2}")
        rng = np.random.default_rng(1)
        Q = rng.uniform(-math.pi, math.pi, (2500, len(L)))
        P = np.array([rk.planar_points(L, q)[-1] for q in Q])
        c = self.cv
        c.clear()
        a1, a2 = c.axes
        a1.plot(P[:, 0], P[:, 1], ".", color=theme.ACCENT, ms=1.5, alpha=0.5)
        t = np.linspace(0, 2 * math.pi, 200)
        a1.plot(R * np.cos(t), R * np.sin(t), color=theme.GOOD, lw=1.2)
        if inner > 0:
            a1.plot(inner * np.cos(t), inner * np.sin(t), color=theme.WARN, lw=1.2)
        draw_arm(a1, L, [0.6, -1.0, 0.8][:len(L)])
        square(a1, max(R, 0.5) * 1.1)
        a1.set_title("workspace = reachable task space")
        a2.hist(np.hypot(P[:, 0], P[:, 1]), bins=40, color=theme.VIOLET, alpha=0.8)
        a2.set_xlabel("distance of hand from base (m)")
        a2.set_ylabel("samples")
        a2.set_title("uniform q is NOT uniform in task space")
        c.refresh()


# ==========================================================================
# Playlist 2 -- rigid-body motions
# ==========================================================================

class RotationsPage(Page):
    TITLE = "Rotations: SO(3) and Exponential Coordinates"
    SUBTITLE = ("A rotation is a 3×3 orthonormal matrix with det +1. Every one "
                "of them is a single turn θ about a single axis ω̂, and "
                "Rodrigues' formula turns that axis–angle pair into the matrix.")
    SECTION = SEC_CSPACE
    NOTES = playlist_badge(2)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(watch(2))

        r = Card("three jobs one rotation matrix does")
        r.add(math_label(r"R\in SO(3)=\{R\in\mathbb{R}^{3\times3}:R^TR=I,\ \det R=1\}", 16))
        r.add(body(
            "<b>1. Represent an orientation.</b> R<sub>sb</sub> has the axes of "
            "frame {b} written in {s} as its columns.<br>"
            "<b>2. Change reference frame.</b> p<sub>s</sub> = R<sub>sb</sub> "
            "p<sub>b</sub>; subscripts cancel: R<sub>ab</sub>R<sub>bc</sub> = "
            "R<sub>ac</sub>.<br>"
            "<b>3. Rotate a vector or frame.</b> R·R<sub>sb</sub> rotates about "
            "an axis in {s} (premultiply); R<sub>sb</sub>·R rotates about the "
            "same axis expressed in {b} (postmultiply). Order matters because "
            "rotations do not commute."))
        self.add(r)

        e = Card("angular velocity, so(3), and the matrix exponential")
        e.add(math_label(r"\dot R R^{-1}=[\omega_s],\qquad R^{-1}\dot R=[\omega_b],"
                         r"\qquad [\omega]=\begin{bmatrix}0&-\omega_3&\omega_2\\ "
                         r"\omega_3&0&-\omega_1\\ -\omega_2&\omega_1&0\end{bmatrix}", 15))
        e.add(math_label(r"\mathrm{Rot}(\hat\omega,\theta)=e^{[\hat\omega]\theta}"
                         r"=I+\sin\theta\,[\hat\omega]+(1-\cos\theta)[\hat\omega]^2", 16))
        e.add(body(
            "Integrate a constant angular velocity ω̂ for θ seconds and you get "
            "e<sup>[ω̂]θ</sup>. The vector ω̂θ ∈ ℝ³ is the <b>exponential "
            "coordinate</b> of R; the matrix log goes back. Three numbers, "
            "no gimbal lock locally, singular only at θ = π where the axis "
            "sign is ambiguous."))
        self.add(e)

        lab = Card("build R from axis and angle, then take it back with log")
        self.sa = labelled_slider(lab, "axis azimuth", -180, 180, 30, deg, self._draw)
        self.se = labelled_slider(lab, "axis elevation", -90, 90, 50, deg, self._draw)
        self.st = labelled_slider(lab, "angle θ", -180, 180, 110, deg, self._draw)
        self.R_txt = body("")
        lab.add(self.R_txt)
        self.st_det = Stat("det R", "--", theme.GOOD)
        self.st_orth = Stat("‖RᵀR − I‖", "--", theme.GOOD)
        self.st_log = Stat("θ from log R", "--", theme.ACCENT)
        lab.add_layout(stat_row(self.st_det, self.st_orth, self.st_log))
        self.cv = MplCanvas(width=7.4, height=3.6)
        self.ax3 = self.cv.fig.add_subplot(111, projection="3d")
        self.cv.ax.remove()
        lab.add(self.cv)
        self.add(lab)
        self._draw()

        self.add(interview(
            "<b>“Why not Euler angles in a controller?”</b> They have a "
            "singularity (ZYX at pitch ±90°: roll and yaw become the same "
            "rotation, the map from rates to ω loses rank), their composition "
            "is not addition, and interpolating them gives curved, "
            "speed-varying motion. Compute with R or quaternions, and express "
            "orientation error as log(R<sub>d</sub>ᵀR) — a 3-vector you can "
            "multiply by a gain."))
        self.finish()

    def _draw(self):
        az, el = math.radians(self.sa.value()), math.radians(self.se.value())
        w = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
        th = math.radians(self.st.value())
        R = rk.rot_exp(w * th)
        self.R_txt.setText("R = e<sup>[ω̂]θ</sup> =" + mat_html(R))
        self.st_det.set(f"{np.linalg.det(R):.6f}")
        self.st_orth.set(f"{np.linalg.norm(R.T @ R - np.eye(3)):.1e}")
        self.st_log.set(f"{math.degrees(np.linalg.norm(rk.rot_log(R))):.1f}°")
        ax = self.ax3
        ax.clear()
        ax.set_facecolor(theme.BG_INPUT)
        cols = (theme.BAD, theme.GOOD, theme.ACCENT)
        for i in range(3):
            e = np.eye(3)[:, i]
            ax.plot([0, e[0]], [0, e[1]], [0, e[2]], color=cols[i], alpha=0.25, lw=1.5)
            v = R[:, i]
            ax.plot([0, v[0]], [0, v[1]], [0, v[2]], color=cols[i], lw=3)
        ax.plot([-w[0], w[0]], [-w[1], w[1]], [-w[2], w[2]], color=theme.WARN, lw=2, ls="--")
        ts = np.linspace(0, th, 40)
        arc = np.array([rk.rot_exp(w * t) @ np.array([1.0, 0, 0]) for t in ts])
        ax.plot(arc[:, 0], arc[:, 1], arc[:, 2], color=theme.BAD, lw=1, ls=":")
        for s in ("x", "y", "z"):
            getattr(ax, f"set_{s}lim")(-1, 1)
        ax.set_title("faint: {s}   bold: {b} = R·{s}   dashed: ω̂", color=theme.TEXT, fontsize=9)
        ax.tick_params(colors=theme.TEXT_DIM, labelsize=7)
        self.cv.refresh()


class TwistsPage(Page):
    TITLE = "Twists, Screws, the Adjoint and Wrenches"
    SUBTITLE = ("Every rigid-body motion is a screw: rotate about an axis while "
                "translating along it. The twist V = (ω, v) is its velocity, "
                "the wrench F = (m, f) its dual, and V·F is power in any frame.")
    SECTION = SEC_CSPACE
    NOTES = playlist_badge(2)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(watch(2))

        h = Card("SE(3): pose as a 4×4 matrix")
        h.add(math_label(r"T=\begin{bmatrix}R&p\\ 0&1\end{bmatrix},\quad "
                         r"T^{-1}=\begin{bmatrix}R^T&-R^Tp\\ 0&1\end{bmatrix},\quad "
                         r"T^{-1}\dot T=[\mathcal{V}_b],\ \ \dot TT^{-1}=[\mathcal{V}_s]", 15))
        h.add(body(
            "The <b>body twist</b> V<sub>b</sub> is the velocity of the body "
            "frame expressed in itself; the <b>spatial twist</b> V<sub>s</sub> "
            "is the same motion seen in {s} — its linear part is the velocity "
            "of the (imaginary) point of the body currently at the {s} origin, "
            "not of the body's own origin. That distinction is the single most "
            "common slip in Jacobian questions."))
        self.add(h)

        s = Card("screw axis and the exponential of a twist")
        s.add(math_label(r"\mathcal{S}=\begin{bmatrix}\hat s\\ -\hat s\times q+h\hat s\end{bmatrix}"
                         r"\ \ (\mathrm{revolute}: h=0),\qquad "
                         r"\mathcal{S}=\begin{bmatrix}0\\ \hat v\end{bmatrix}\ (\mathrm{prismatic})", 15))
        s.add(math_label(r"e^{[\mathcal{S}]\theta}=\begin{bmatrix}e^{[\hat\omega]\theta}&"
                         r"(I\theta+(1-\cos\theta)[\hat\omega]+(\theta-\sin\theta)[\hat\omega]^2)v"
                         r"\\ 0&1\end{bmatrix}", 15))
        s.add(body(
            "Chasles–Mozzi: any displacement is a rotation θ about some line "
            "plus a translation hθ along it. The 6-vector Sθ is the "
            "<b>exponential coordinate</b> of a pose, the same way ω̂θ was of a "
            "rotation. Forward kinematics on the next section's first page is nothing more than a "
            "product of these exponentials, one per joint."))
        self.add(s)

        lab = Card("a planar screw: drag the axis point and the angle")
        lab.add(body(
            "In the plane a screw is a rotation about a point q (h = 0). The "
            "square is carried along the exponential path; its corners trace "
            "circular arcs about q, and the twist's linear part v = −ω × q "
            "is the velocity of whatever body point sits at the origin.",
            dim=True))
        self.sx = labelled_slider(lab, "axis point q_x", -20, 20, 10, lambda v: f"{v/10:.1f}", self._draw)
        self.sy = labelled_slider(lab, "axis point q_y", -20, 20, 5, lambda v: f"{v/10:.1f}", self._draw)
        self.st = labelled_slider(lab, "θ", -180, 180, 90, deg, self._draw)
        self.S_txt = body("")
        lab.add(self.S_txt)
        self.cv = MplCanvas(width=7.4, height=3.8)
        lab.add(self.cv)
        self.add(lab)
        self._draw()

        a = Card("the adjoint: moving twists and wrenches between frames")
        a.add(math_label(r"[\mathrm{Ad}_{T}]=\begin{bmatrix}R&0\\ [p]R&R\end{bmatrix},\qquad "
                         r"\mathcal{V}_s=[\mathrm{Ad}_{T_{sb}}]\mathcal{V}_b,\qquad "
                         r"\mathcal{F}_b=[\mathrm{Ad}_{T_{sb}}]^T\mathcal{F}_s", 15))
        a.add(body(
            "A wrench F = (m, f) — moment then force, matching (ω, v) — "
            "transforms with the transpose because <b>power</b> "
            "V<sub>b</sub>ᵀF<sub>b</sub> = V<sub>s</sub>ᵀF<sub>s</sub> cannot "
            "depend on which frame you write it in. Hold onto that sentence: "
            "it is the entire reason τ = JᵀF on the statics page."))
        self.add(a)

        self.add(interview(
            "<b>“A force sensor at the wrist reads F<sub>b</sub>. What torque "
            "does that force produce about the base?”</b> Transform it: "
            "F<sub>s</sub> = Ad<sub>T<sub>bs</sub></sub>ᵀ F<sub>b</sub>; the "
            "moment part picks up p × f. Then joint torques are "
            "τ = J<sub>b</sub>ᵀ F<sub>b</sub> = J<sub>s</sub>ᵀ F<sub>s</sub> — "
            "same answer, because both are power balances."))
        self.finish()

    def _draw(self):
        qx, qy = self.sx.value() / 10, self.sy.value() / 10
        th = math.radians(self.st.value())
        S = rk.screw_axis([qx, qy, 0], [0, 0, 1])
        self.S_txt.setText(
            f"S = (ω; v) = ({S[0]:.0f}, {S[1]:.0f}, {S[2]:.0f}; "
            f"{S[3]:+.2f}, {S[4]:+.2f}, {S[5]:.0f})  —  v = −ω̂ × q")
        sq = np.array([[-0.3, -0.3], [0.3, -0.3], [0.3, 0.3], [-0.3, 0.3], [-0.3, -0.3]])
        c = self.cv
        c.clear()
        ax = c.ax
        ax.plot(sq[:, 0], sq[:, 1], color=theme.TEXT_FAINT, lw=1.5, label="start pose")
        for t in np.linspace(0, th, 7)[1:-1]:
            T = rk.exp6(S, t)
            P = (T[:2, :2] @ sq.T).T + T[:2, 3]
            ax.plot(P[:, 0], P[:, 1], color=theme.ACCENT, lw=0.8, alpha=0.4)
        T = rk.exp6(S, th)
        P = (T[:2, :2] @ sq.T).T + T[:2, 3]
        ax.plot(P[:, 0], P[:, 1], color=theme.CYAN, lw=2.5, label="e^[S]θ · start")
        for corner in sq[:4]:
            arc = np.array([(rk.exp6(S, t)[:2, :2] @ corner) + rk.exp6(S, t)[:2, 3]
                            for t in np.linspace(0, th, 30)])
            ax.plot(arc[:, 0], arc[:, 1], ":", color=theme.WARN, lw=1)
        ax.plot(qx, qy, "x", color=theme.BAD, ms=12, mew=3, label="screw axis q")
        ax.quiver(0, 0, S[3], S[4], color=theme.VIOLET, angles="xy", scale_units="xy",
                  scale=1, width=0.006, label="v (velocity of point at origin)")
        ax.set_xlim(-3, 3)
        ax.set_ylim(-2.2, 2.2)
        ax.set_aspect("equal", adjustable="box")
        c.legend(ax, loc="lower left")
        c.refresh()
