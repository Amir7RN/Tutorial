"""
ROBOT MECHANICS, part 2 -- kinematics.
Modern Robotics playlists 3-6 (chapters 4-7).

    forward kinematics   product of exponentials, space and body form, D-H
    Jacobian             columns are screw axes; v = J qdot; the ellipse
    statics/singularity  tau = J^T F, force ellipse, rank loss
    inverse kinematics   analytic 2R branches, Newton-Raphson, damping
    redundancy           J^+, N = I - J^+ J, self-motion, secondary tasks
    closed chains        four-bar, loop closure, actuated vs passive joints
"""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QCheckBox, QComboBox, QPushButton

from ctrlcore import robokin as rk
from .. import theme
from ..widgets import Card, MplCanvas, Stat, body, callout, math_label, stat_row
from .base import Page
from .robo_common import (
    SEC_KIN,
    deg,
    draw_arm,
    interview,
    labelled_slider,
    mat_html,
    plain,
    playlist_badge,
    square,
    start_here,
    watch,
)

L3 = [1.0, 0.8, 0.5]


# ==========================================================================
# Playlist 3 -- forward kinematics
# ==========================================================================

class PoEPage(Page):
    TITLE = "Forward Kinematics: Product of Exponentials"
    SUBTITLE = ("Write down the home pose M and one screw axis per joint. "
                "Then T(θ) = e^[S₁]θ₁ ⋯ e^[Sₙ]θₙ M. No link frames, no "
                "four-parameter tables, and the axes are readable off a sketch.")
    SECTION = SEC_KIN
    NOTES = playlist_badge(3)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(watch(3))
        self.add(start_here(
            "<b>Forward kinematics</b>: given the joint angles, where is the "
            "hand and which way does it point? The recipe on this page has "
            "three steps. (1) Put the robot at <b>home</b> (every joint at "
            "zero) and write the hand's pose there: that is M. (2) For each "
            "joint, write its screw axis Sᵢ at home: which way the hinge "
            "points and where it sits. (3) Multiply T = e<sup>[S₁]θ₁</sup> ⋯ "
            "e<sup>[Sₙ]θₙ</sup> M. Each factor means 'swing everything beyond "
            "joint i about joint i's hinge by θᵢ'."))

        s = Card("space form and body form")
        s.add(math_label(r"T(\theta)=e^{[\mathcal{S}_1]\theta_1}\cdots"
                         r" e^{[\mathcal{S}_n]\theta_n}M"
                         r"\qquad\qquad T(\theta)=M e^{[\mathcal{B}_1]\theta_1}\cdots"
                         r" e^{[\mathcal{B}_n]\theta_n}", 16))
        s.add(body(
            "<b>Space form.</b> S<sub>i</sub> is joint i's screw axis written in "
            "the fixed frame {s} <i>with the robot at home</i>. Read the product "
            "right to left: move the last joint first, while every joint before "
            "it is still at home, so its axis is still where you drew it.<br>"
            "<b>Body form.</b> B<sub>i</sub> is the same axis written in the "
            "end-effector frame at home; B<sub>i</sub> = [Ad<sub>M⁻¹</sub>]"
            "S<sub>i</sub>. Read left to right."))
        s.add(body(
            "For a revolute joint, S = (ω̂, −ω̂ × q) with q any point on the axis. "
            "For the planar 3R below, every ω̂ = ẑ and the axes pass through "
            "(0,0), (L₁,0), (L₁+L₂,0) at home, so S₂ = (0,0,1, 0,−L₁,0).",
            dim=True))
        s.add(plain(
            "Why only home axes are needed: read the product from the right. "
            "Move the <i>last</i> joint first — every joint before it is "
            "still at home, so its hinge is exactly where you drew it. Then "
            "move joint n − 1: it carries joint n and the hand along, and its "
            "own hinge has not moved either. Continue down to joint 1. So you "
            "only ever need hinge positions at home, which you read straight "
            "off a sketch.<br><b>Work the example.</b> Joint 2 points out of "
            "the page, ω̂ = (0, 0, 1), and passes through q = (L₁, 0, 0). "
            "Then ω̂ × q = (0, L₁, 0), so v = −ω̂ × q = (0, −L₁, 0) and S₂ = "
            "(0, 0, 1, 0, −L₁, 0). The body form is the same idea with axes "
            "written from the hand's point of view."))
        self.add(s)

        lab = Card("planar 3R: drag joints, read T from the product")
        self.q = [labelled_slider(lab, f"θ{i+1}", -180, 180, v, deg, self._draw)
                  for i, v in enumerate((30, 45, -60))]
        self.T_txt = body("")
        lab.add(self.T_txt)
        self.cv = MplCanvas(width=7.4, height=3.8)
        lab.add(self.cv)
        lab.add(plain(
            "The ghost is the home pose M. The coloured stages show the "
            "product being applied right to left: first θ₃ swings the last "
            "link, then θ₂ swings the last two, then θ₁ swings everything. "
            "The printed matrix is T: its upper-left block is the hand's "
            "rotation, its last column the hand's position. <b>Check one "
            "number yourself:</b> x = L₁cos θ₁ + L₂cos(θ₁+θ₂) + "
            "L₃cos(θ₁+θ₂+θ₃) with L = (1.0, 0.8, 0.5) should match the top "
            "entry of the last column."))
        self.add(lab)
        self._draw()

        dh = Card("why not Denavit–Hartenberg?")
        dh.add(body(
            "D–H attaches a frame to every link with four parameters "
            "(a, α, d, θ) and multiplies 4×4 link transforms. It is minimal "
            "and still everywhere in industry and in ROS URDF tooling, so "
            "know it. But the frame rules are fiddly, parallel consecutive "
            "axes make d ill-defined, and a tiny misalignment of the real "
            "robot can force a large parameter jump. PoE uses six numbers per "
            "joint, no link frames, and varies smoothly — which is why "
            "calibration and the book prefer it."))
        dh.add(plain(
            "D–H is the older recipe: bolt a frame to every link and describe "
            "each link with four numbers (link length a, twist α, offset d, "
            "angle θ). You will meet it in textbooks, datasheets and robot "
            "description files, so know what the four numbers are. PoE is "
            "easier to set up from a drawing and less fragile. In an "
            "interview either method is accepted; the 2R formula below is "
            "what they actually ask you to write."))
        self.add(dh)

        self.add(interview(
            "<b>“Derive the forward kinematics of a 2R arm.”</b> "
            "x = L₁cos θ₁ + L₂cos(θ₁+θ₂), y = L₁sin θ₁ + L₂sin(θ₁+θ₂), "
            "φ = θ₁+θ₂. Then say how it generalises: one screw axis per joint, "
            "T = Π e<sup>[S<sub>i</sub>]θ<sub>i</sub></sup> M, and that the "
            "Jacobian columns on the next page are these same S<sub>i</sub> "
            "moved by the joints before them."))
        self.finish()

    def _draw(self):
        q = np.radians([s.value() for s in self.q])
        S, M = rk.planar_screws(L3)
        T = rk.fk_space(M, S, q)
        self.T_txt.setText(
            "T(θ) =" + mat_html(T) +
            f"<span style='color:{theme.TEXT_DIM}'>x = {T[0,3]:.3f}, y = {T[1,3]:.3f}, "
            f"φ = {math.degrees(math.atan2(T[1,0], T[0,0])):.1f}°  "
            f"(trig check: φ = θ₁+θ₂+θ₃ = {math.degrees(q.sum()):.1f}°)</span>")
        c = self.cv
        c.clear()
        ax = c.ax
        draw_arm(ax, L3, np.zeros(3), ghost=True)
        # partial products: apply joints one at a time from the LAST, as the
        # space form reads
        for k, col in zip(range(3), (theme.VIOLET, theme.ACCENT, theme.CYAN)):
            qq = np.zeros(3)
            qq[2 - k:] = q[2 - k:]
            draw_arm(ax, L3, qq, color=col, alpha=0.4 + 0.3 * k, lw=2 + k,
                     label=f"θ{3-k}…θ3 applied")
        pts = rk.planar_points(L3, q)
        R = T[:2, :2]
        for v, col in ((R[:, 0], theme.BAD), (R[:, 1], theme.GOOD)):
            ax.quiver(*pts[-1], *(0.4 * v), color=col, angles="xy", scale_units="xy",
                      scale=1, width=0.006)
        square(ax, 2.4)
        c.legend(ax, loc="lower left")
        ax.set_title("ghost = home pose M; apply e^[S3]θ3, then e^[S2]θ2, then e^[S1]θ1")
        c.refresh()


# ==========================================================================
# Playlist 4 -- velocity kinematics and statics
# ==========================================================================

class JacobianPage(Page):
    TITLE = "The Jacobian: Joint Rates to Hand Velocity"
    SUBTITLE = ("v = J(θ) θ̇. Column i is the hand velocity when only joint i "
                "moves at unit speed — for the space Jacobian, the screw axis "
                "Sᵢ moved by the joints before it. The unit circle of joint "
                "rates maps to an ellipse of hand velocities.")
    SECTION = SEC_KIN
    NOTES = playlist_badge(4)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(watch(4))
        self.add(start_here(
            "Forward kinematics gave the hand's position. Now its "
            "<b>speed</b>: if the joints turn at rates θ̇, how fast does the "
            "hand move? Answer: hand velocity = J(θ) θ̇. J is a matrix that "
            "changes with the pose. <b>Column i of J</b> = the hand velocity "
            "you get if only joint i turns, at 1 rad/s. Add up the columns, "
            "each weighted by its joint's real speed, and you have the hand "
            "velocity."))

        j = Card("space Jacobian, body Jacobian, analytic Jacobian")
        j.add(math_label(r"\mathcal{V}_s=J_s(\theta)\dot\theta,\quad "
                         r"J_{si}=[\mathrm{Ad}_{e^{[\mathcal{S}_1]\theta_1}\cdots "
                         r"e^{[\mathcal{S}_{i-1}]\theta_{i-1}}}]\mathcal{S}_i,\qquad "
                         r"J_s=[\mathrm{Ad}_{T_{sb}}]J_b", 15))
        j.add(body(
            "<b>Geometric</b> Jacobians (J<sub>s</sub>, J<sub>b</sub>) map to "
            "twists. The <b>analytic</b> Jacobian maps to the time derivative "
            "of whatever coordinates you chose for the pose (x, y, z, Euler "
            "angles) — it is J<sub>geom</sub> times a coordinate-dependent "
            "matrix and inherits that parametrisation's singularities. For "
            "position only, the 3×n top rows of the linear-velocity Jacobian "
            "of a point are ∂p/∂θ. For a planar revolute joint: column i is "
            "ẑ × (p<sub>tip</sub> − p<sub>i</sub>) — rotate the lever arm by 90°."))
        j.add(plain(
            "For a planar hinge, think of a clock hand: the tip moves at "
            "right angles to the hand, faster the longer the hand. Column i "
            "is exactly that — the lever arm from joint i to the hand, turned "
            "90°. For the 2R arm (s₁ = sin θ₁, c₁₂ = cos(θ₁+θ₂), …):<br>J = [ "
            "−L₁s₁ − L₂s₁₂ , −L₂s₁₂ ; L₁c₁ + L₂c₁₂ , L₂c₁₂ ].<br>Get it by "
            "differentiating x(θ) and y(θ) from page 122 with respect to each "
            "angle. 'Geometric' Jacobians give the true angular velocity ω; "
            "the 'analytic' one gives rates of whatever angles you chose "
            "(e.g. Euler angles) and can blow up wherever those angles do."))
        self.add(j)

        lab = Card("the velocity ellipse, and what each column is")
        lab.add(body(
            "Arrows: each column of the 2×n position Jacobian, the hand "
            "velocity from one joint alone. Ellipse: every hand velocity "
            "reachable with ‖θ̇‖ = 1. Its axes are J's left singular vectors, "
            "its semi-axes the singular values.", dim=True))
        self.chk3 = QCheckBox("third link (redundant 3R)")
        self.chk3.stateChanged.connect(self._draw)
        lab.add(self.chk3)
        self.q = [labelled_slider(lab, f"θ{i+1}", -180, 180, v, deg, self._draw)
                  for i, v in enumerate((20, 70, -40))]
        self.J_txt = body("")
        lab.add(self.J_txt)
        self.st_s1 = Stat("σ₁ (fast direction)", "--", theme.GOOD)
        self.st_s2 = Stat("σ₂ (slow direction)", "--", theme.WARN)
        self.st_mu = Stat("μ = σ₁σ₂ = √det(JJᵀ)", "--", theme.ACCENT)
        self.st_k = Stat("condition σ₁/σ₂", "--", theme.VIOLET)
        lab.add_layout(stat_row(self.st_s1, self.st_s2, self.st_mu, self.st_k))
        self.cv = MplCanvas(width=7.6, height=3.8, ncols=2)
        lab.add(self.cv)
        lab.add(plain(
            "Arrows = the columns: what each joint alone does to the hand. "
            "Green ellipse = every hand velocity you can get with a "
            "joint-speed vector of length 1. Long axis σ₁: the direction the "
            "hand moves easily. Short axis σ₂: the direction it moves slowly. "
            "μ = σ₁σ₂ is an area-like score of dexterity, and σ₁/σ₂ says how "
            "lopsided the ellipse is (1 = a circle, equally good in all "
            "directions).<br><b>Try:</b> bring θ₂ near 0°. The two arrows "
            "line up, the ellipse flattens into a line, σ₂ → 0: the hand "
            "cannot move along the arm at any joint speed. The right map "
            "shows μ for every pose; the red bands at θ₂ = 0° and ±180° are "
            "those singular poses, and they do not depend on θ₁."))
        self.add(lab)
        self._draw()

        self.add(callout(
            "Straighten the elbow (θ₂ → 0) and watch σ₂ collapse: both columns "
            "become parallel, the ellipse becomes a line segment, and no joint "
            "rate can move the hand radially. That is a <b>singularity</b>: "
            "rank J drops. The right panel shows μ over the whole (θ₁, θ₂) "
            "plane — for a 2R arm it is L₁L₂|sin θ₂|, independent of θ₁.",
            "key"))

        self.add(interview(
            "<b>“What are the columns of the Jacobian, physically?”</b> The "
            "end-effector twist produced by moving joint i alone at unit rate "
            "with the others frozen. For the space Jacobian, it is joint i's "
            "screw axis at its <i>current</i> location: the home axis "
            "S<sub>i</sub> transformed by the motion of joints 1…i−1 only."))
        self.finish()

    def _L(self):
        return L3 if self.chk3.isChecked() else L3[:2]

    def _draw(self):
        L = self._L()
        q = np.radians([s.value() for s in self.q])[:len(L)]
        J = rk.planar_jacobian(L, q)
        U, s, mu, cond = rk.manipulability(J)
        self.J_txt.setText("J(θ) = ∂(x, y)/∂θ =" + mat_html(J))
        self.st_s1.set(f"{s[0]:.3f}")
        self.st_s2.set(f"{s[1]:.3f}")
        self.st_mu.set(f"{mu:.3f}")
        self.st_k.set("∞" if math.isinf(cond) else f"{cond:.1f}")
        self.st_s2.set_color(theme.BAD if s[1] < 0.05 else theme.WARN)
        c = self.cv
        c.clear()
        a1, a2 = c.axes
        pts = draw_arm(a1, L, q)
        tip = pts[-1]
        E = rk.ellipse_points(U @ np.diag(s), 120)
        a1.plot(tip[0] + 0.5 * E[:, 0], tip[1] + 0.5 * E[:, 1], color=theme.GOOD, lw=1.8)
        cols = (theme.BAD, theme.VIOLET, theme.PINK)
        for i in range(len(L)):
            a1.quiver(*tip, *(0.5 * J[:, i]), color=cols[i], angles="xy",
                      scale_units="xy", scale=1, width=0.007)
        square(a1, sum(L) + 0.3)
        a1.set_title("arrows: columns of J (×0.5); green: velocity ellipse")
        th1 = np.linspace(-math.pi, math.pi, 60)
        th2 = np.linspace(-math.pi, math.pi, 60)
        Z = np.array([[rk.manipulability(rk.planar_jacobian(L[:2], [a, b]))[2]
                       for a in th1] for b in th2])
        a2.contourf(np.degrees(th1), np.degrees(th2), Z, 20, cmap="viridis")
        a2.plot(math.degrees(q[0]), math.degrees(q[1]), "o", color=theme.WARN, ms=8)
        a2.axhline(0, color=theme.BAD, lw=1, ls="--")
        a2.set_xlabel("θ₁ (deg)")
        a2.set_ylabel("θ₂ (deg)")
        a2.set_title("μ(θ₁, θ₂) for the first two links; red = singular")
        c.refresh()


class StaticsPage(Page):
    TITLE = "Statics, Singularities and the Force Ellipse"
    SUBTITLE = ("τ = Jᵀ F. The joint torque that holds a hand force follows "
                "from one line of power balance, and it turns the velocity "
                "ellipse inside out: where the hand is slow, it is strong.")
    SECTION = SEC_KIN
    NOTES = playlist_badge(4)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(watch(4))
        self.add(start_here(
            "Flip the question. Not 'joint speeds → hand speed', but 'what "
            "motor torques must I apply so the hand <b>pushes</b> with force "
            "F?' Answer: <b>τ = JᵀF</b> — the same Jacobian, transposed. You "
            "use it to push on things, to hold a payload, and to estimate a "
            "contact force from motor currents. The page also explains "
            "singularities, the poses where J loses a direction."))

        p = Card("one line of derivation you must be able to give")
        p.add(math_label(r"\tau^T\dot\theta=F^T\mathcal{V}=F^TJ\dot\theta\ \ "
                         r"\forall\dot\theta\quad\Rightarrow\quad\tau=J^T(\theta)F", 17))
        p.add(body(
            "Power in at the joints equals power out at the hand (no losses, "
            "static). Because it must hold for every θ̇, the matrices match. "
            "Body and space versions: τ = J<sub>b</sub>ᵀF<sub>b</sub> = "
            "J<sub>s</sub>ᵀF<sub>s</sub>. F here is the wrench the robot "
            "<i>applies</i> to the environment; gravity torques are added "
            "separately."))
        p.add(plain(
            "An energy argument. Power going into the joints = Σ torque × "
            "joint speed = τᵀθ̇. Power coming out at the hand = force · hand "
            "velocity = Fᵀ(Jθ̇). A static, lossless arm gains no energy, so "
            "the two are equal. That has to be true for any θ̇ you might "
            "pick, which forces τᵀ = FᵀJ, i.e. τ = JᵀF. Intuition: a joint "
            "far from the hand has a long lever arm, so it needs more torque "
            "for the same hand force — like a long wrench."))
        self.add(p)

        lab = Card("hold a force at the hand")
        self.q = [labelled_slider(lab, f"θ{i+1}", -180, 180, v, deg, self._draw)
                  for i, v in enumerate((30, 60))]
        self.fa = labelled_slider(lab, "force direction", -180, 180, -90, deg, self._draw)
        self.fm = labelled_slider(lab, "force magnitude (N)", 0, 50, 20,
                                  lambda v: f"{v} N", self._draw)
        self.st_t1 = Stat("τ₁ (N·m)", "--", theme.ACCENT)
        self.st_t2 = Stat("τ₂ (N·m)", "--", theme.CYAN)
        self.st_det = Stat("det J", "--", theme.WARN)
        lab.add_layout(stat_row(self.st_t1, self.st_t2, self.st_det))
        self.cv = MplCanvas(width=7.6, height=3.8, ncols=2)
        lab.add(self.cv)
        lab.add(plain(
            "Choose a direction and size for the force the hand applies "
            "(arrow). τ₁ and τ₂ are the motor torques needed to hold it. Left "
            "panel: the velocity ellipse and the force ellipse share axes but "
            "swap lengths — where the hand moves fast it is weak, where it "
            "moves slowly it is strong, like changing gear on a bicycle. "
            "Right panel: torque per newton for every force "
            "direction.<br><b>Try:</b> stretch the arm (θ₂ → 0) and point the "
            "force along the arm. Both torques drop to almost zero and det J "
            "→ 0: the links carry the load in compression, the motors feel "
            "nothing."))
        self.add(lab)
        self._draw()

        k = Card("singularities, read three ways")
        k.add(body(
            "<b>Velocity:</b> some hand direction needs infinite joint speed "
            "(σ<sub>min</sub> = 0, J⁻¹ blows up).<br>"
            "<b>Force:</b> along that same direction, a hand force needs "
            "<i>zero</i> joint torque — the structure carries it. Push along a "
            "straight arm and the motors feel nothing; that is why you lock "
            "your knees to stand.<br>"
            "<b>Null spaces:</b> at a singularity Jᵀ has a nonzero null space "
            "too — wrenches the joints cannot resist <i>or</i> cannot feel. A "
            "force sensor-less contact estimator τ<sub>ext</sub> → F is blind "
            "along it.<br><br>"
            "Kinds: <b>boundary</b> (arm fully stretched or folded, edge of "
            "the workspace) and <b>interior</b> (two axes align inside the "
            "workspace, e.g. wrist singularity of a 6R arm when joints 4 and 6 "
            "line up). Interior ones are the dangerous ones: the planner did "
            "not expect them."))
        k.add(plain(
            "A <b>singularity</b> is a pose where J loses a direction (det J "
            "= 0 for a square J). Three faces of the same fact: the hand "
            "cannot move that way at any joint speed; a force that way costs "
            "no torque; and a force estimate from motor torques cannot see "
            "forces that way. <b>Boundary</b> singularities are at the edge "
            "of reach (arm straight or fully folded) and are easy to spot. "
            "<b>Interior</b> ones happen when two joint axes line up inside "
            "the workspace, e.g. joints 4 and 6 of an industrial wrist — "
            "dangerous because nothing about the pose looks unusual."))
        self.add(k)

        self.add(interview(
            "<b>“Your Cartesian controller commands huge joint velocities "
            "near some pose. Why, and what do you do?”</b> J is near-singular, "
            "so J⁻¹v amplifies v along the 1/σ<sub>min</sub> direction. Fixes: "
            "damped least squares J<sup>T</sup>(JJ<sup>T</sup>+λ²I)⁻¹ (trades "
            "tracking accuracy for bounded rates), avoid the region in the "
            "planner, use redundancy to keep μ high, or switch to Jᵀ-based "
            "control (τ = JᵀK e), which never inverts J."))
        self.finish()

    def _draw(self):
        L = [1.0, 0.8]
        q = np.radians([s.value() for s in self.q])
        a = math.radians(self.fa.value())
        F = self.fm.value() * np.array([math.cos(a), math.sin(a)])
        J = rk.planar_jacobian(L, q)
        tau = J.T @ F
        self.st_t1.set(f"{tau[0]:+.2f}")
        self.st_t2.set(f"{tau[1]:+.2f}")
        self.st_det.set(f"{np.linalg.det(J):+.3f}")
        c = self.cv
        c.clear()
        a1, a2 = c.axes
        pts = draw_arm(a1, L, q)
        tip = pts[-1]
        a1.quiver(*tip, *(F / 40), color=theme.BAD, angles="xy", scale_units="xy",
                  scale=1, width=0.008, label="F the hand applies")
        U, s, _, _ = rk.manipulability(J)
        V = rk.ellipse_points(U @ np.diag(s))
        a1.plot(tip[0] + 0.4 * V[:, 0], tip[1] + 0.4 * V[:, 1], color=theme.GOOD,
                lw=1.5, label="velocity ellipse")
        if s[1] > 1e-3:
            Fe = rk.ellipse_points(U @ np.diag(1 / s))
            sc = 0.4 / max(1 / s[1], 1)
            a1.plot(tip[0] + sc * Fe[:, 0], tip[1] + sc * Fe[:, 1], color=theme.WARN,
                    lw=1.5, label="force ellipse (same axes, 1/σ)")
        square(a1, 2.0)
        c.legend(a1, loc="lower left")
        angles = np.linspace(-math.pi, math.pi, 181)
        T = np.array([J.T @ np.array([math.cos(t), math.sin(t)]) for t in angles])
        a2.plot(np.degrees(angles), T[:, 0], color=theme.ACCENT, label="τ₁ per newton")
        a2.plot(np.degrees(angles), T[:, 1], color=theme.CYAN, label="τ₂ per newton")
        a2.axvline(math.degrees(a), color=theme.BAD, lw=1, ls=":")
        a2.set_xlabel("direction of hand force (deg)")
        a2.set_ylabel("joint torque per N (N·m/N)")
        c.legend(a2, loc="lower left")
        c.refresh()


# ==========================================================================
# Playlist 5 -- inverse kinematics and redundancy
# ==========================================================================

class IKPage(Page):
    TITLE = "Inverse Kinematics: Analytic and Newton–Raphson"
    SUBTITLE = ("Given the hand pose, find θ. Zero, one, two or infinitely "
                "many answers. Closed form when the geometry allows it; "
                "otherwise iterate θ ← θ + J⁺(x_d − f(θ)) and watch it converge "
                "quadratically — or wander when J is singular.")
    SECTION = SEC_KIN
    NOTES = playlist_badge(5)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(watch(5))
        self.add(start_here(
            "<b>Inverse kinematics</b>: given where you want the hand, find "
            "the joint angles. Harder than forward kinematics, because there "
            "may be <b>no</b> answer (out of reach), <b>two</b> (elbow up or "
            "down), or <b>infinitely many</b> (redundant arm). Two "
            "approaches: geometry, giving a formula; or iteration — guess, "
            "measure the error, correct using the Jacobian, repeat."))

        a = Card("analytic 2R: the law of cosines, two branches")
        a.add(math_label(r"\cos\theta_2=\frac{x^2+y^2-L_1^2-L_2^2}{2L_1L_2},\quad "
                         r"\theta_2=\pm\arccos(\cdot),\quad "
                         r"\theta_1=\mathrm{atan2}(y,x)-\mathrm{atan2}(L_2\sin\theta_2,"
                         r"L_1+L_2\cos\theta_2)", 15))
        a.add(body(
            "Elbow-up and elbow-down. Outside the annulus |cos θ₂| > 1: no "
            "solution. On its boundary: one (singular). A 6R arm with a "
            "spherical wrist decouples into a position problem (first three "
            "joints place the wrist centre) and an orientation problem (last "
            "three), with up to 8 solutions; a general 6R has up to 16. "
            "<b>Always use atan2</b>, never atan or arccos alone."))
        a.add(plain(
            "A triangle trick. Shoulder, elbow and hand form a triangle with "
            "sides L₁, L₂ and r = √(x² + y²), the distance to the target. The "
            "law of cosines gives the elbow angle θ₂ from those three sides, "
            "and ± gives the two mirror triangles (elbow up, elbow down). "
            "Then θ₁ = direction to the target minus the angle the triangle "
            "adds at the shoulder. <b>atan2(y, x)</b> instead of atan(y/x) "
            "because atan2 knows the quadrant: atan cannot tell (1, 1) from "
            "(−1, −1). If the cosine comes out bigger than 1 in size, the "
            "target is too far or too close."))
        self.add(a)

        n = Card("numerical: Newton–Raphson on the residual")
        n.add(math_label(r"\theta^{k+1}=\theta^k+J^{\dagger}(\theta^k)\,"
                         r"\left(x_d-f(\theta^k)\right),\qquad "
                         r"J^{\dagger}=J^T(JJ^T+\lambda^2I)^{-1}", 16))
        n.add(body(
            "For full poses, the residual is the body twist "
            "V<sub>b</sub> = log(T<sub>sb</sub>⁻¹T<sub>sd</sub>) and the "
            "Jacobian is J<sub>b</sub>. Converges quadratically near a "
            "solution; from a bad guess it can diverge or land on the other "
            "branch. λ > 0 (damped least squares / Levenberg–Marquardt) keeps "
            "steps bounded near singularities at the cost of speed."))
        n.add(plain(
            "Like adjusting a shower knob: (1) guess the angles θ; (2) "
            "compute where the hand really is, f(θ); (3) error = target − "
            "actual; (4) the Jacobian says how the hand moves per small joint "
            "change, so J⁺ × error is the joint correction; (5) repeat. Close "
            "to the answer each step roughly squares the error (10⁻² → 10⁻⁴ → "
            "10⁻⁸): that is 'quadratic convergence'. λ (damping) makes every "
            "step more cautious so it cannot leap wildly near a singularity, "
            "at the price of more steps."))
        self.add(n)

        lab = Card("click a target: both analytic branches and the Newton path")
        self.tx = labelled_slider(lab, "target x", -20, 20, 12, lambda v: f"{v/10:.1f} m", self._draw)
        self.ty = labelled_slider(lab, "target y", -20, 20, 6, lambda v: f"{v/10:.1f} m", self._draw)
        self.g1 = labelled_slider(lab, "initial guess θ₁", -180, 180, -120, deg, self._draw)
        self.g2 = labelled_slider(lab, "initial guess θ₂", -180, 180, 10, deg, self._draw)
        self.lam = labelled_slider(lab, "damping λ", 0, 100, 0, lambda v: f"{v/100:.2f}", self._draw)
        self.st_br = Stat("analytic solutions", "--", theme.GOOD)
        self.st_it = Stat("Newton iterations", "--", theme.ACCENT)
        self.st_err = Stat("final error", "--", theme.WARN)
        lab.add_layout(stat_row(self.st_br, self.st_it, self.st_err))
        self.cv = MplCanvas(width=7.6, height=3.8, ncols=2)
        lab.add(self.cv)
        lab.add(plain(
            "Move the target (star). The green and violet arms are the two "
            "analytic answers. Ghost arms are the Newton iterates starting "
            "from your initial guess; cyan is where Newton ends. The right "
            "plot is the error per iteration on a log scale.<br><b>Try:</b> "
            "(1) put the guess near one branch, then near the other — Newton "
            "lands on whichever is closer. (2) Drag the target outside the "
            "outer circle: 0 analytic answers, and Newton stalls at the "
            "nearest reachable point with a red error. (3) Start with θ₂ near "
            "0 (arm straight) and λ = 0: jumpy steps; raise λ: smooth but "
            "slower."))
        self.add(lab)
        self._draw()

        self.add(interview(
            "<b>“Analytic or numerical IK?”</b> Analytic when it exists: "
            "every branch, deterministic time, no initial guess — required "
            "for real-time on most industrial arms. Numerical for "
            "redundant/general arms and when you want secondary objectives "
            "(joint limits, collision) via the null space. In production "
            "(TRAC-IK, KDL, IKFast) people combine them: analytic seeds, "
            "Newton polish, random restarts."))
        self.finish()

    def _draw(self):
        L = [1.0, 0.8]
        x = np.array([self.tx.value() / 10, self.ty.value() / 10])
        q0 = np.radians([self.g1.value(), self.g2.value()])
        lam = self.lam.value() / 100
        sols = [rk.ik_2r(*L, *x, e) for e in (1, -1)]
        sols = [s for s in sols if s is not None]
        q, Q, errs = rk.ik_newton(L, x, q0, max_iter=40, damping=lam)
        self.st_br.set(str(len(sols)) if sols else "0 — unreachable")
        self.st_it.set(str(len(errs) - 1))
        self.st_err.set(f"{errs[-1]:.1e} m")
        self.st_err.set_color(theme.GOOD if errs[-1] < 1e-5 else theme.BAD)
        c = self.cv
        c.clear()
        a1, a2 = c.axes
        t = np.linspace(0, 2 * math.pi, 200)
        a1.plot(1.8 * np.cos(t), 1.8 * np.sin(t), color=theme.BORDER, lw=1)
        a1.plot(0.2 * np.cos(t), 0.2 * np.sin(t), color=theme.BORDER, lw=1)
        for qq in Q[:-1]:
            draw_arm(a1, L, qq, ghost=True)
        for s, col, lab in zip(sols, (theme.GOOD, theme.VIOLET), ("elbow +", "elbow −")):
            draw_arm(a1, L, s, color=col, alpha=0.7, lw=3, label=lab)
        draw_arm(a1, L, q, color=theme.CYAN, label="Newton result")
        a1.plot(*x, "*", color=theme.WARN, ms=14)
        square(a1, 2.0)
        c.legend(a1, loc="lower left")
        a2.semilogy(np.maximum(errs, 1e-16), "o-", color=theme.ACCENT)
        a2.set_xlabel("iteration")
        a2.set_ylabel("‖x_d − f(θ)‖ (m)")
        a2.set_title("quadratic convergence = digits double each step")
        c.refresh()


class NullSpacePage(Page):
    TITLE = "Redundancy and the Null Space"
    SUBTITLE = ("Three joints, two task coordinates: one direction of joint "
                "motion moves nothing at the hand. N = I − J⁺J projects any "
                "joint motion onto that direction, so a second objective can "
                "run without disturbing the first.")
    SECTION = SEC_KIN
    NOTES = playlist_badge(5)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(watch(5))
        self.add(start_here(
            "Put your fingertip on the table and wave your elbow: the "
            "fingertip does not move. That is <b>redundancy</b> — more joints "
            "(here 3) than task numbers (2: x and y). The joint motions that "
            "leave the hand still form the <b>null space</b> of J. This page "
            "shows how to use them for a second goal — stay away from joint "
            "limits, keep a comfortable posture — without disturbing the "
            "hand."))

        m = Card("the general solution of ẋ = J θ̇")
        m.add(math_label(r"\dot\theta=J^{+}\dot x_d+(I-J^{+}J)\,\dot\theta_0,\qquad "
                         r"J^{+}=J^T(JJ^T)^{-1}", 17))
        m.add(body(
            "J is m×n with n > m. J⁺ẋ<sub>d</sub> is the minimum-norm joint "
            "velocity that achieves the task. N = I − J⁺J is the orthogonal "
            "projector onto null(J): J N = 0, N² = N, rank N = n − m. "
            "Anything in θ̇<sub>0</sub> — a pull toward a comfortable posture, "
            "away from joint limits, toward higher manipulability, away from "
            "an obstacle — is filtered so that only its harmless part survives."))
        m.add(math_label(r"\dot\theta_0=-k\,\nabla_\theta H(\theta)\quad "
                         r"(\mathrm{gradient\ projection}),\qquad "
                         r"J_W^{+}=W^{-1}J^T(JW^{-1}J^T)^{-1}", 15))
        m.add(body(
            "A weighted pseudo-inverse minimises θ̇ᵀWθ̇ instead of ‖θ̇‖²; with "
            "W = M(θ) it minimises kinetic energy and becomes the dynamically "
            "consistent inverse of the task-space dynamics page.", dim=True))
        m.add(plain(
            "Two pieces added together. <b>J⁺ẋ<sub>d</sub></b>: the smallest "
            "joint motion (least total joint speed) that moves the hand as "
            "wanted. <b>(I − J⁺J)θ̇₀</b>: take any joint motion you like for "
            "the second goal, θ̇₀, and strip out the part of it that would "
            "move the hand. N is a filter; J N = 0 is the promise that "
            "whatever passes through it causes zero hand motion. 'Gradient "
            "projection' means θ̇₀ = 'walk downhill on a cost H', e.g. H = "
            "how close you are to the joint limits. A weighted inverse "
            "measures 'smallest' differently; with W = M it means least "
            "kinetic energy, which page 133 uses."))
        self.add(m)

        lab = Card("self-motion: the hand stays put, the elbow swings")
        lab.add(body(
            "Press <b>Play</b>: the 3R arm integrates θ̇ = J⁺·k(x<sub>d</sub> − x) "
            "+ N θ̇<sub>0</sub>. Choose the secondary task. The hand error stays "
            "at numerical zero while the posture changes — that is the null "
            "space, made visible.", dim=True))
        self.task = QComboBox()
        self.task.addItems(["swing the elbow (θ̇₀ = sinusoid)",
                            "keep joints near centre (−∇ Σθᵢ²)",
                            "maximise manipulability (+∇ μ)",
                            "no secondary task (N θ̇₀ = 0)",
                            "WRONG: add θ̇₀ without projecting"])
        self.task.currentIndexChanged.connect(self._reset)
        lab.add(self.task)
        self.btn = QPushButton("Play")
        self.btn.setObjectName("Primary")
        self.btn.clicked.connect(self._toggle)
        rb = QPushButton("Reset")
        rb.clicked.connect(self._reset)
        from PySide6.QtWidgets import QHBoxLayout
        row = QHBoxLayout()
        row.addWidget(self.btn)
        row.addWidget(rb)
        row.addStretch(1)
        lab.add_layout(row)
        self.st_err = Stat("hand error ‖x − x_d‖", "--", theme.GOOD)
        self.st_q = Stat("θ (deg)", "--", theme.ACCENT)
        self.st_mu = Stat("manipulability μ", "--", theme.VIOLET)
        lab.add_layout(stat_row(self.st_err, self.st_q, self.st_mu))
        self.cv = MplCanvas(width=7.6, height=3.8, ncols=2)
        self.a2b = self.cv.axes[1].twinx()
        lab.add(self.cv)
        lab.add(plain(
            "Press Play. The star (hand target) stays put; the arm reshapes "
            "itself. The left stat (hand error) stays below a millimetre "
            "(a feedback term k(x<sub>d</sub> − x) holds it). Switch secondary tasks and watch the joint "
            "angles on the right change while the hand still does not move. "
            "Then choose the last option, <b>WRONG: add θ̇₀ without "
            "projecting</b>: the hand error now grows, because the second "
            "goal leaks into the hand. That leak is exactly what N exists to "
            "stop."))
        self.add(lab)
        self.timer = QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self._step)
        self._reset()

        self.add(callout(
            "<b>Task priority.</b> With two tasks x₁ = f₁(θ), x₂ = f₂(θ): "
            "θ̇ = J₁⁺ẋ₁ + (J₂N₁)⁺(ẋ₂ − J₂J₁⁺ẋ₁). Task 2 gets whatever "
            "freedom task 1 leaves, never more. This recursion is how a "
            "humanoid keeps balance (priority 1), reaches (2), and looks "
            "natural (3) at the same time.", "key"))

        self.add(interview(
            "<b>“What is the null space of the Jacobian, and how do you use "
            "it?”</b> The set of joint velocities producing zero end-effector "
            "velocity, dimension n − rank J. Use: θ̇ = J⁺ẋ + (I − J⁺J)θ̇₀ with "
            "θ̇₀ the gradient of a secondary cost (joint limits, singularity "
            "avoidance, obstacle distance). For torques the projector is "
            "I − JᵀJ̄ᵀ with the <i>dynamically consistent</i> J̄ = M⁻¹JᵀΛ, "
            "otherwise posture torques leak into the hand — the operational-space control page shows it."))
        self.finish()

    def _reset(self):
        self.timer.stop()
        self.btn.setText("Play")
        self.qv = np.array([0.4, 1.2, -0.9])
        self.xd = rk.planar_points(L3, self.qv)[-1].copy()
        self.t = 0.0
        self.hist = []
        self._draw()

    def _toggle(self):
        if self.timer.isActive():
            self.timer.stop()
            self.btn.setText("Play")
        else:
            self.timer.start()
            self.btn.setText("Pause")

    def on_hide(self):
        self.timer.stop()
        self.btn.setText("Play")

    def _qdot0(self, q):
        k = self.task.currentIndex()
        if k in (0, 4):
            return np.array([0.0, 1.0, -1.0]) * 1.5 * math.cos(1.5 * self.t)
        if k == 1:
            return -2.0 * q
        if k == 2:
            eps = 1e-5
            mu = lambda qq: rk.manipulability(rk.planar_jacobian(L3, qq))[2]
            return 3.0 * np.array([(mu(q + eps * e) - mu(q - eps * e)) / (2 * eps)
                                   for e in np.eye(3)])
        return np.zeros(3)

    def _step(self):
        dt = 0.02
        for _ in range(2):
            J = rk.planar_jacobian(L3, self.qv)
            x = rk.planar_points(L3, self.qv)[-1]
            Jp = rk.pinv_damped(J)
            qd0 = self._qdot0(self.qv)
            if self.task.currentIndex() == 4:
                qd = Jp @ (5.0 * (self.xd - x)) + qd0
            else:
                qd = Jp @ (5.0 * (self.xd - x)) + (np.eye(3) - Jp @ J) @ qd0
            self.qv = self.qv + dt * qd
            self.t += dt
        self._draw()

    def _draw(self):
        x = rk.planar_points(L3, self.qv)[-1]
        err = np.linalg.norm(x - self.xd)
        mu = rk.manipulability(rk.planar_jacobian(L3, self.qv))[2]
        self.hist = (self.hist + [(self.t, err, *self.qv)])[-300:]
        self.st_err.set(f"{err:.1e} m")
        self.st_err.set_color(theme.GOOD if err < 1e-3 else theme.BAD)
        self.st_q.set(", ".join(f"{math.degrees(v):.0f}" for v in self.qv))
        self.st_mu.set(f"{mu:.3f}")
        c = self.cv
        c.clear()
        a1, a2 = c.axes
        draw_arm(a1, L3, self.qv)
        a1.plot(*self.xd, "*", color=theme.WARN, ms=14)
        square(a1, 2.4)
        a1.set_title("star = hand target, held fixed")
        if self.hist:
            H = np.array(self.hist)
            for i, col in enumerate((theme.ACCENT, theme.CYAN, theme.VIOLET)):
                a2.plot(H[:, 0], np.degrees(H[:, 2 + i]), color=col, label=f"θ{i+1}")
            a2b = self.a2b
            a2b.clear()
            a2b.semilogy(H[:, 0], np.maximum(H[:, 1], 1e-12), color=theme.BAD, lw=1)
            a2b.set_ylabel("hand error (m)", color=theme.BAD)
            a2b.tick_params(colors=theme.TEXT_DIM, labelsize=7)
            c.legend(a2, loc="upper left")
        a2.set_xlabel("time (s)")
        a2.set_ylabel("joint angle (deg)")
        c.refresh(layout=False)


# ==========================================================================
# Playlist 6 -- closed chains
# ==========================================================================

class ClosedChainPage(Page):
    TITLE = "Closed Chains: Four-Bar, Stewart, Delta"
    SUBTITLE = ("In a parallel mechanism some joints are actuated and the rest "
                "are dragged along. Forward kinematics becomes the hard "
                "direction, inverse kinematics the easy one, and singularities "
                "come in more than one kind.")
    SECTION = SEC_KIN
    NOTES = playlist_badge(6)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(watch(6))
        self.add(start_here(
            "So far every robot was a single chain from base to hand "
            "(serial). A <b>parallel</b> robot has several chains meeting at "
            "the moving platform: Delta pick-and-place robots, Stewart "
            "flight-simulator platforms, or the humble four-bar linkage. Only "
            "some joints have motors; the rest are dragged along. Everything "
            "flips: inverse kinematics becomes easy and forward kinematics "
            "hard."))

        c = Card("loop-closure equations")
        c.add(math_label(r"g(\theta_a,\theta_p)=0\ \Rightarrow\ "
                         r"H_a\dot\theta_a+H_p\dot\theta_p=0\ \Rightarrow\ "
                         r"\dot\theta_p=-H_p^{-1}H_a\dot\theta_a", 16))
        c.add(body(
            "Split the joints into actuated θ<sub>a</sub> and passive "
            "θ<sub>p</sub>. Differentiating the loop gives the passive rates "
            "from the actuated ones, and the end-effector Jacobian follows by "
            "walking any one open sub-chain. For a Stewart platform the "
            "opposite direction is trivial: given the platform pose, each leg "
            "length is ‖p + R b<sub>i</sub> − a<sub>i</sub>‖ — inverse "
            "kinematics in closed form, forward kinematics a polynomial system "
            "with up to 40 solutions."))
        c.add(body(
            "<b>Singularities.</b> (1) <i>actuator</i>: H<sub>p</sub> loses "
            "rank — the platform gains a freedom the motors cannot hold "
            "(dangerous, inside the workspace). (2) <i>configuration</i>: the "
            "mechanism reaches a branch point — e.g. the four-bar's coupler "
            "and rocker align. (3) <i>end-effector</i>: the output loses a "
            "direction, as in an open chain."))
        c.add(plain(
            "<b>Loop closure</b>: walking round the loop link by link must "
            "bring you back to the start. That gives equations g = 0. "
            "Differentiate them and the motor (actuated) joint speeds fix the "
            "free (passive) joint speeds: θ̇<sub>p</sub> = "
            "−H<sub>p</sub>⁻¹H<sub>a</sub>θ̇<sub>a</sub>, as long as "
            "H<sub>p</sub> can be inverted. Why Stewart IK is easy: given the "
            "platform pose, each leg length is just the distance between its "
            "two mounting points — one line per leg. The reverse (given six "
            "leg lengths, find the pose) is a polynomial puzzle with many "
            "answers.<br><b>Singularities in plain words.</b> Actuator: "
            "motors locked, yet the platform can still wobble — it loses "
            "stiffness. Configuration: the linkage reaches a fork where it "
            "could flip to another way of being assembled. End-effector: as "
            "for a serial arm, the output loses a direction."))
        self.add(c)

        lab = Card("four-bar: drive the crank, watch the loop close (or fail to)")
        self.sa = labelled_slider(lab, "crank a", 3, 30, 10, lambda v: f"{v/10:.1f}", self._draw)
        self.sb = labelled_slider(lab, "coupler b", 3, 40, 25, lambda v: f"{v/10:.1f}", self._draw)
        self.sc = labelled_slider(lab, "rocker c", 3, 40, 20, lambda v: f"{v/10:.1f}", self._draw)
        self.sd = labelled_slider(lab, "ground d", 3, 40, 30, lambda v: f"{v/10:.1f}", self._draw)
        self.st = labelled_slider(lab, "crank angle", -180, 180, 40, deg, self._draw)
        self.branch = QCheckBox("other assembly branch (crossed)")
        self.branch.stateChanged.connect(self._draw)
        lab.add(self.branch)
        self.st_g = Stat("Grashof", "--", theme.GOOD)
        self.st_ok = Stat("loop closes?", "--", theme.ACCENT)
        self.st_r = Stat("coupler-point speed ratio", "--", theme.VIOLET)
        lab.add_layout(stat_row(self.st_g, self.st_ok, self.st_r))
        self.cv = MplCanvas(width=7.6, height=3.8)
        lab.add(self.cv)
        lab.add(plain(
            "Crank a is the motor; the coupler b and rocker c follow; the "
            "ground link d never moves. The violet curve is the path of a "
            "point on the coupler. <b>Grashof</b>: if shortest + longest ≤ "
            "the other two added, some link can spin all the way round; "
            "otherwise every link only rocks back and forth. <b>Loop "
            "closes?</b> says no when, at this crank angle, the coupler and "
            "rocker cannot reach each other — try a long crank and a short "
            "coupler. 'Crossed' is the same four lengths assembled the other "
            "way. The speed ratio spikes when two links line up: a singular "
            "pose."))
        self.add(lab)
        self._draw()

        self.add(interview(
            "<b>“Serial vs parallel robot — trade-offs?”</b> Parallel: motors "
            "on the base so the moving mass is small (fast, stiff, accurate — "
            "Delta pick-and-place, Stewart flight simulators); but small "
            "workspace, easy IK / hard FK, and actuator singularities inside "
            "the workspace. Serial: large workspace, easy FK / harder IK, "
            "every motor carries the ones after it, errors accumulate."))
        self.finish()

    def _draw(self):
        a, b, cc, d = (s.value() / 10 for s in (self.sa, self.sb, self.sc, self.sd))
        th = math.radians(self.st.value())
        br = -1 if self.branch.isChecked() else 1
        ls = sorted([a, b, cc, d])
        gr = ls[0] + ls[3] <= ls[1] + ls[2]
        self.st_g.set("yes — some link fully rotates" if gr else "no — all links rock")
        self.st_g.set_color(theme.GOOD if gr else theme.WARN)
        res = rk.four_bar(th, a, b, cc, d, br)
        self.st_ok.set("yes" if res else "NO — out of reach")
        self.st_ok.set_color(theme.GOOD if res else theme.BAD)
        cv = self.cv
        cv.clear()
        ax = cv.ax
        trace = []
        for t in np.linspace(-math.pi, math.pi, 361):
            r = rk.four_bar(t, a, b, cc, d, br)
            if r:
                A, B = r
                trace.append(A + 0.5 * (B - A) + 0.4 * np.array([-(B - A)[1], (B - A)[0]]))
            else:
                trace.append([np.nan, np.nan])
        trace = np.array(trace)
        ax.plot(trace[:, 0], trace[:, 1], color=theme.VIOLET, lw=1, alpha=0.7,
                label="coupler-point curve")
        ax.plot([0, d], [0, 0], color=theme.TEXT_DIM, lw=5, label="ground")
        if res:
            A, B = res
            P = A + 0.5 * (B - A) + 0.4 * np.array([-(B - A)[1], (B - A)[0]])
            ax.plot([0, A[0]], [0, A[1]], color=theme.ACCENT, lw=4, label="crank (actuated)")
            ax.plot([A[0], B[0]], [A[1], B[1]], color=theme.CYAN, lw=4, label="coupler")
            ax.plot([B[0], d], [B[1], 0], color=theme.PINK, lw=4, label="rocker")
            ax.fill([A[0], B[0], P[0]], [A[1], B[1], P[1]], color=theme.CYAN, alpha=0.2)
            ax.plot(*P, "o", color=theme.WARN, ms=8)
            for pt in ([0, 0], A, B, [d, 0]):
                ax.plot(*pt, "o", color=theme.TEXT, ms=6)
            r2 = rk.four_bar(th + 1e-4, a, b, cc, d, br)
            if r2:
                A2, B2 = r2
                P2 = A2 + 0.5 * (B2 - A2) + 0.4 * np.array([-(B2 - A2)[1], (B2 - A2)[0]])
                self.st_r.set(f"{np.linalg.norm(P2 - P) / 1e-4:.2f} m/rad")
            else:
                self.st_r.set("∞ (branch point)")
        else:
            self.st_r.set("--")
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlim(-3, 6)
        ax.set_ylim(-3.5, 3.5)
        cv.legend(ax, loc="lower left")
        cv.refresh()
