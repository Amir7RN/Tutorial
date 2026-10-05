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
    plain,
    playlist_badge,
    square,
    start_here,
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
        self.add(start_here(
            "This block answers three questions about any robot arm, in "
            "order. <b>Where is the hand?</b> (kinematics, pages 115–119). "
            "<b>How fast and how hard can the hand move when the motors "
            "turn?</b> (the Jacobian, pages 120–124). <b>What motor torques "
            "does a given motion need?</b> (dynamics, pages 125–131). The "
            "last pages use those three answers to plan and control the arm. "
            "You need no earlier page of the tutor: only that a matrix times "
            "a vector is a weighted sum of columns, and that a derivative is "
            "a rate of change."))

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
        c.add(plain(
            "Read the arrow chain like a recipe, left to right. <b>q</b> is "
            "the list of joint angles, the robot's knob settings. <b>T(q)</b> "
            "is where the hand is and which way it points for those settings. "
            "<b>V = J q̇</b>: if the knobs turn at some speeds, J tells how "
            "fast the hand moves; J is a table of 'how much hand motion per "
            "unit of each joint's motion'. <b>τ = JᵀF</b>: the same table, "
            "flipped, tells which motor torques make the hand push with force "
            "F. The last arrow is Newton's F = ma for a robot: torque = (mass "
            "× acceleration) + (forces caused by joints already spinning) + "
            "(holding up the weight). Every page in this block fills in one "
            "arrow."))
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

        h = Card("how to study this block: videos first, or pages first?")
        h.add(body(
            "Neither on its own. The pages are compressed: they assume you "
            "have seen the derivation once. The videos are slow and careful "
            "but give you nothing to touch. Use them together, one page at a "
            "time:<br><b>1. Read the page's START HERE box and every IN PLAIN "
            "WORDS box first</b>, about five minutes, skipping every formula. "
            "Goal: know which question the page answers.<br><b>2. Watch that "
            "page's playlist</b> (the Watch alongside link). The videos are 3 "
            "to 8 minutes each; pause on every boxed equation and say what "
            "each symbol is in words.<br><b>3. Come back and do the lab.</b> "
            "Move one slider at a time, predict what will happen before you "
            "look, and compare with the plain-words box under the "
            "lab.<br><b>4. Say the interview answer out loud</b> without "
            "reading it. If you cannot, go back to step 1 for that page only."))
        h.add(body(
            "If a formula still makes no sense after the video, do not stop "
            "there: the plain-words box tells you what result to carry "
            "forward, and later pages only use the result, not the "
            "derivation. Pages 115–118 (playlists 1–2) are vocabulary; it is "
            "normal for them to feel abstract until page 120 (the Jacobian) "
            "uses them.", dim=True))
        self.add(h)

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
        p.add(plain(
            "Do not try to master this list on the first pass. Items 1–2 are "
            "the Kinematics section (pages 119–124), items 3–5 the Dynamics "
            "section (125–131), item 6 Robot Control (135–137). If you only "
            "have time for one idea, take the Jacobian: almost every other "
            "item is built from it."))
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
        self.add(start_here(
            "Question: what is the smallest list of numbers that tells you "
            "exactly how the whole robot is posed? For a two-motor arm it is "
            "two angles. The length of that list is the <b>degrees of freedom "
            "(DOF)</b>. The set of all possible lists is the <b>configuration "
            "space (C-space)</b>: a map in which one point is one complete "
            "pose of the robot. Planning, kinematics and dynamics all happen "
            "on this map."))

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
        d.add(plain(
            "Count freedoms like a budget. A loose body sliding on a table "
            "can move 3 ways (slide x, slide y, spin), so m = 3; a loose body "
            "in space can move 6 ways, so m = 6. You have N − 1 moving bodies "
            "(ground never moves), so m(N − 1) freedoms to start with. Each "
            "joint then takes some away: a hinge in the plane leaves only 1 "
            "of the 3, so it removes m − f = 2. Freedoms left = m(N − 1) − "
            "Σ(m − fᵢ), which rearranges to the formula above.<br><b>Check it "
            "by hand.</b> Planar 3R arm: N = 4 (three links plus ground), J = "
            "3 hinges, so 3(4 − 1 − 3) + 3 = 3. Four-bar: N = 4, J = 4, so "
            "3(4 − 1 − 4) + 4 = 1 — closing the loop cost two freedoms."))
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
        g.add(plain(
            "Pick each mechanism and work out the dof yourself before you "
            "read the green number. Pattern to notice: an open chain (an "
            "ordinary arm) has dof equal to its number of joints, because "
            "nothing ties the end down. A closed chain (four-bar, Stewart, "
            "Delta) has fewer, because the loops force joints to agree with "
            "each other."))
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
        t.add(plain(
            "The right panel is a map where each point is a whole arm pose: "
            "horizontal = q₁, vertical = q₂. Turning q₁ by a full 360° gives "
            "the same arm, so the map's right edge is the same place as its "
            "left edge, and top equals bottom. Glue both pairs of edges and "
            "the flat square becomes a donut, a <b>torus</b>. Why it matters: "
            "a planner can leave the right edge and come back on the left — "
            "that is a short smooth motion, not a jump. <b>Try:</b> drag q₁ "
            "past +180° and watch the dot reappear on the left while the arm "
            "on the left panel barely moves. For a body flying in space the "
            "map is 6-D and, for orientation, has no flat three-number chart "
            "without a bad spot — hence the rotation matrices on page 117."))
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
        self.add(start_here(
            "A constraint is a rule the robot must always obey. Two kinds "
            "matter. <b>Rules about where it can be</b> (holonomic) — e.g. "
            "'the end of this loop stays bolted to the ground'. They remove "
            "dimensions from C-space. <b>Rules about which way it can move "
            "right now</b> (nonholonomic) — e.g. 'a wheel cannot skid "
            "sideways'. They do not shrink C-space; they only remove "
            "directions of motion at each instant. The second half of the "
            "page separates three spaces people mix up: C-space, task space "
            "and workspace."))

        h = Card("holonomic: a constraint on q")
        h.add(math_label(r"g(q)=0\quad\Rightarrow\quad "
                         r"\frac{\partial g}{\partial q}\,\dot q = A(q)\,\dot q = 0", 16))
        h.add(body(
            "A closed loop is holonomic: the four-bar's loop-closure equations "
            "g(q) = 0 remove three of the four joint angles. Differentiate and "
            "you get a <b>Pfaffian</b> velocity constraint A(q)q̇ = 0 that came "
            "from a position constraint — so it is integrable, and the "
            "C-space itself is smaller."))
        h.add(plain(
            "g(q) = 0 is an equation the joint angles must satisfy, like "
            "'walking round the loop brings you back to the start'. Each "
            "independent equation removes one dimension. Take its rate of "
            "change and you get A(q)q̇ = 0: a rule on joint "
            "<i>velocities</i>. 'Pfaffian' is only the name for a velocity "
            "rule written as matrix × q̇ = 0. 'Integrable' means you can go "
            "backwards from that velocity rule to a position rule — here you "
            "can, because it came from one."))
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
        n.add(plain(
            "φ is the heading of the wheel or car, and (−sin φ, cos φ) is the "
            "direction pointing sideways out of its door. The equation says: "
            "velocity along that sideways direction is zero — no skidding. "
            "Yet you can still reach a spot directly to your side by parallel "
            "parking (forward, turn, back, turn). So the car still needs 3 "
            "numbers (x, y, heading) to describe it — C-space stays 3-D — but "
            "at any instant it has only 2 velocity choices: drive speed and "
            "turn rate."))
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
        w.add(plain(
            "<b>C-space</b> = joint angles. <b>Task space</b> = the numbers "
            "you care about for the job, e.g. pen tip (x, y). "
            "<b>Workspace</b> = the part of task space the hand can actually "
            "reach. <b>Redundant</b> = more joints than task numbers, so "
            "infinitely many arm poses put the hand on the same point — put a "
            "fingertip on the desk and move your elbow.<br><b>Try:</b> make "
            "L₂ longer than L₁: a hole (inner radius) opens because the hand "
            "cannot fold back to the base. Add L₃ and the third stat shows 1 "
            "extra (redundant) freedom. The histogram on the right is not "
            "flat: picking joint angles at random piles the hand up near the "
            "inner and outer edges (arm nearly folded or straight), so "
            "'random in joints' is not 'random in task space' — it matters "
            "for sampling planners on page 134."))
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
        self.add(start_here(
            "How do you write down which way an object is pointing in 3-D? "
            "With a 3×3 <b>rotation matrix R</b>. Its three columns are the "
            "object's own x, y and z axes, written in world coordinates — "
            "that is all it is. The page then shows the one fact that makes "
            "the rest easy: any orientation can be reached by a <b>single "
            "turn θ about a single axis ω̂</b>, and there are formulas to go "
            "from (axis, angle) to R and back."))

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
        r.add(plain(
            "Glue a tiny x-y-z frame {b} to the object; {s} is the fixed "
            "world frame. R<sub>sb</sub> means 'frame b as seen from s': "
            "column 1 is where b's x-axis points, and so on. RᵀR = I says the "
            "three columns are unit length and at right angles (still a "
            "proper frame); det = +1 says it is right-handed, not a mirror "
            "image.<br>Job 2 works like unit conversion: in "
            "R<sub>ab</sub>R<sub>bc</sub> the inner b's cancel and you get "
            "R<sub>ac</sub>.<br>Job 3: try it with your phone. Turn it 90° "
            "about the vertical, then 90° about the world's left-right axis. "
            "Reset and do it in the other order. The phone ends up different: "
            "rotations do not commute, so left- versus right-multiplication "
            "matters."))
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
        e.add(plain(
            "[ω] is the cross product written as a matrix: [ω]p = ω × p. "
            "Nothing more. Angular velocity ω points along the spin axis and "
            "its length is the spin rate. If you spin about a fixed unit axis "
            "ω̂ at 1 rad/s for θ seconds you end at R = e<sup>[ω̂]θ</sup>, "
            "and Rodrigues' formula is the closed form of that exponential — "
            "you never sum a series. So three numbers, ω̂θ (axis scaled by "
            "angle), describe any rotation, and 'log R' recovers them. The "
            "only awkward case is a half-turn (θ = 180°), where turning about "
            "ω̂ and about −ω̂ give the same R."))
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
        lab.add(plain(
            "Point the axis with azimuth and elevation (dashed line), then "
            "choose the turn θ. Faint lines are the world axes, bold lines "
            "the turned frame, and the dotted arc is the tip of the x-axis "
            "during the turn. Check the stats: det R stays 1 and the "
            "orthogonality error is around 10⁻¹⁶ — numerical zero. 'θ from "
            "log R' always comes back between 0° and 180°: a −110° turn about "
            "ω̂ is the same rotation as +110° about −ω̂, so the log reports "
            "the positive one."))
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
        self.add(start_here(
            "Page 117 handled orientation only. Now add position. A "
            "<b>pose</b> = rotation R + position p, packed into one 4×4 "
            "matrix T. A rigid body's <b>velocity</b> = spin ω + linear speed "
            "v, packed into a 6-vector called a <b>twist</b>. A <b>force</b> "
            "on it = moment m + force f, packed into a 6-vector called a "
            "<b>wrench</b>. This page is vocabulary; the Jacobian and "
            "dynamics pages use these words on every line."))

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
        h.add(plain(
            "Why 4×4? So that 'rotate, then shift' is a single "
            "multiplication: T·[p; 1] = Rp + offset. T⁻¹ undoes it — rotate "
            "back, then remove the shift. A <b>body twist</b> describes the "
            "motion from the moving body's own point of view ('I am going "
            "forward and turning left'). A <b>spatial twist</b> describes the "
            "same motion in the fixed world frame. The trap: in the spatial "
            "twist, v is not the speed of the body's centre; it is the speed "
            "of an imaginary point glued to the body that happens to be at "
            "the world origin right now. Strange, but it makes the algebra "
            "clean."))
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
        s.add(plain(
            "Any move from pose A to pose B can be done as one <b>screw "
            "motion</b>: turn about some line while sliding along it, like a "
            "screw going into wood. A hinge is a screw with no sliding (pitch "
            "h = 0); a slider is a screw with no turning. The screw axis S "
            "stores the line's direction ŝ and, through v = −ŝ × q, where the "
            "line is (q is any point on it). e<sup>[S]θ</sup> is 'perform "
            "this screw motion by amount θ' as a 4×4 matrix. Forward "
            "kinematics (page 119) multiplies one of these per joint."))
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
        lab.add(plain(
            "The red × is where the hinge axis pierces the page. Slide θ: the "
            "square swings around that point like a door around its hinge, "
            "and the dotted arcs are its corners. The violet arrow is v, the "
            "velocity the motion would give a point sitting at the origin. "
            "<b>Try:</b> keep θ fixed and move the hinge point — the motion "
            "is the same kind of turn, but v changes, because v encodes where "
            "the hinge is. Put the hinge at (0, 0) and v becomes zero."))
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
        a.add(plain(
            "Ad<sub>T</sub> is a 6×6 'translator' that re-expresses a twist "
            "seen from one frame in another frame. The [p]R block is there "
            "because a spin about a distant axis looks, from here, like a "
            "spin plus a sliding motion — a rider on a merry-go-round is "
            "moving even though the centre only turns. Wrenches use the "
            "transpose because power (velocity · force) is a physical number "
            "and cannot depend on which frame you write it in. Remember that "
            "one sentence and τ = JᵀF on page 121 needs no memorising."))
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
