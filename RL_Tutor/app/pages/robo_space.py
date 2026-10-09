"""
ROBOT MECHANICS, part 1 -- configuration space and rigid-body motion.
Modern Robotics playlists 1 and 2 (chapters 2 and 3).

    roadmap          the twelve playlists, and which page answers which
    C-space          degrees of freedom, Gruebler, topology, representation
    constraints      holonomic vs nonholonomic; task space vs workspace
                     (the interactive cards for videos 2.3.1-2.5 live in
                     robo_space_topo.py)
    rotations        SO(3), angular velocity, so(3), Rodrigues, the matrix log
    twists/wrenches  SE(3), screw axes, the adjoint, and power = V . F
                     (one card group per chapter-3 video lives in
                     robo_space_rigid.py)
"""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtWidgets import QComboBox

from ctrlcore import robokin as rk
from .. import theme
from ..widgets import Card, MplCanvas, Stat, body, callout, math_label, stat_row
from .base import Page
from . import robo_space_rigid as rr
from .robo_space_topo import (
    AngleWrapCard,
    CarConstraintCard,
    FourBarCard,
    HoopConstraintCard,
    JointLimitWorkspaceCard,
    RepresentationCard,
    TaskSpaceCard,
    TopologyExplorer,
    WallCard,
    choose_rep_card,
    constraint_uses_card,
    fourbar_A_card,
    gap_meter_card,
    topology_card,
    why_card,
)
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
            "order. <b>Where is the hand?</b> (kinematics, pages 115–120). "
            "<b>How fast and how hard can the hand move when the motors "
            "turn?</b> (the Jacobian, pages 121–125). <b>What motor torques "
            "does a given motion need?</b> (dynamics, pages 126–132). The "
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
            "derivation. Pages 115–119 (playlists 1–2) are vocabulary; it is "
            "normal for them to feel abstract until page 121 (the Jacobian) "
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
            "the Kinematics section (pages 120–125), items 3–5 the Dynamics "
            "section (126–132), item 6 Robot Control (136–138). If you only "
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
            "on this map. This page counts the numbers and shows the map for "
            "a two-joint arm. The next page asks two more questions about "
            "that map: what <b>shape</b> is it (its topology — flat, a "
            "sphere, a doughnut?) and what <b>numbers</b> do we write a point "
            "on it with (its representation)."))
        self.add(why_card())

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
            "without a bad spot — hence the rotation matrices on page 118."))
        self.add(t)
        self._trail = []
        self._draw()

        self.add(interview(
            "<b>“How many DOF does a planar four-bar have, and when does "
            "Grübler's formula give the wrong answer?”</b> One: "
            "3(4 − 1 − 4) + 4 = 1. Grübler assumes every joint constraint is "
            "independent. Special geometry breaks that — a parallelogram "
            "linkage with an extra parallel link counts 0 but moves with 1 "
            "DOF — and then the true DOF is n minus the rank of the "
            "constraint Jacobian at that pose (page 117)."))
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


class CSpaceTopoPage(Page):
    TITLE = "C-Space Topology and Representation"
    SUBTITLE = ("Two questions about the C-space map: what shape it is "
                "(the robot decides), and which numbers you store for a point "
                "on it (you decide). The shape tells you which choice is safe.")
    SECTION = SEC_CSPACE
    NOTES = playlist_badge(1)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(watch(1))
        self.add(start_here(
            "Page 115 gave the C-space a size: how many numbers. This page "
            "asks two separate questions about it. <b>Shape (topology):</b> "
            "does the map go on forever, have walls, or wrap round on itself? "
            "The robot decides this; you cannot change it. <b>Numbers "
            "(representation):</b> which numbers do you store for one point "
            "on the map — the fewest possible (explicit), or a few extra tied "
            "by rules (implicit)? You choose this. The page ends with one "
            "rule: plain angles for joints, wrapped; a rotation matrix for "
            "anything that can point in any 3-D direction."))
        self.add(topology_card())
        self.topo = TopologyExplorer()
        self.add(self.topo.card)
        self.wrap = AngleWrapCard()
        self.add(self.wrap.card)
        self.rep = RepresentationCard()
        self.add(self.rep.card)
        self.add(choose_rep_card())

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
        self.hoop = HoopConstraintCard()
        self.add(self.hoop.card)
        self.add(gap_meter_card())
        self.wall = WallCard()
        self.add(self.wall.card)
        self.add(fourbar_A_card())
        self.fourbar = FourBarCard()
        self.add(self.fourbar.card)

        n = Card("nonholonomic: the same-looking equation, with no g behind it")
        n.add(body(
            "Both kinds of constraint end up written the same way, "
            "A(q)q̇ = 0. The difference is <b>where the row of A came from</b>, "
            "and whether you can go back. Holonomic: someone built a "
            "violation meter g first, and A is its list of slopes, ∂g/∂q. "
            "Then A q̇ = 0 says 'the meter is not moving', so g keeps its "
            "starting value forever and the robot is trapped on the surface "
            "g = 0. Nonholonomic: you are handed the row of A directly, and "
            "<b>no meter g has it as its slopes</b>. Nothing is conserved, so "
            "nothing traps you."))
        n.add(math_label(
            r"\mathrm{holonomic:}\;\;A=\frac{\partial g}{\partial q}\;\;"
            r"\Rightarrow\;\;\frac{dg}{dt}=A\dot q=0\;\;\Rightarrow\;\;"
            r"g(q(t))=g(q(0))=0", 15))
        n.add(math_label(
            r"\mathrm{nonholonomic:}\;\;A(q)\dot q=0\;\;\mathrm{but\ no}\;g\;"
            r"\mathrm{with}\;\frac{\partial g}{\partial q}=A\;"
            r"(\mathrm{or\ any\ multiple\ of}\;A)", 15))
        n.add(body(
            "<b>The test, by hand, on two rolling wheels.</b> Is the row of A "
            "the slope list of some meter g?<br>"
            "<b>(a) A coin rolling along a straight rail</b>, q = (x, θ): "
            "no slip means ẋ = rθ̇, i.e. [1, −r] q̇ = 0. We need ∂g/∂x = 1 and "
            "∂g/∂θ = −r. Both slopes are constants, so g = x − rθ works. It "
            "<b>is</b> holonomic, a position rule in disguise: x − rθ never "
            "changes, and the C-space is a 1-D line in the (x, θ) plane — "
            "the coin's angle is fixed by how far it has rolled.<br>"
            "<b>(b) A car (or a wheel that can steer)</b>, q = (φ, x, y): no "
            "sideways slip means ẋ sin φ − ẏ cos φ = 0, the row "
            "[0, sin φ, −cos φ]. We would need ∂g/∂φ = 0, ∂g/∂x = sin φ, "
            "∂g/∂y = −cos φ. The first says g ignores φ. The second says g's "
            "x-slope changes when φ changes. Both cannot hold: the order of "
            "differentiation of a smooth function does not matter, and "
            "here it would:"))
        n.add(math_label(
            r"\frac{\partial}{\partial\phi}\left(\frac{\partial g}{\partial x}\right)"
            r"=\cos\phi\;\neq\;0=\frac{\partial}{\partial x}"
            r"\left(\frac{\partial g}{\partial\phi}\right)", 15))
        n.add(body(
            "So no g exists, and multiplying the row by any factor does not "
            "fix it either (the general test is the Lie bracket, chapter 13). "
            "<b>What changes because of it:</b> a holonomic rule with n "
            "coordinates and k rules leaves n − k dimensions of places "
            "<i>and</i> n − k velocity choices. A nonholonomic one leaves n − k "
            "velocity choices but <b>all n dimensions of places</b>. For the "
            "car: 2 velocity choices (drive, turn) in a 3-D C-space. If the "
            "rule were holonomic the car would be stuck on one 2-D surface "
            "g(φ, x, y) = const; parallel parking ends at the same φ and x "
            "with a different y, which no such surface allows.", dim=True))
        n.add(plain(
            "Why can the car get sideways at all? Look at the forbidden "
            "direction (sin φ, −cos φ): it <b>turns with the heading φ</b>. "
            "A rail's forbidden direction is fixed in space, so you can never "
            "leak out of it. The car's turns whenever you steer, so a "
            "direction forbidden now is allowed after a turn: drive a little "
            "at one heading, a little at another, and the net step points "
            "where neither leg was allowed to go. In the coin's row [1, −r] "
            "nothing depends on q, which is exactly why it integrates. "
            "Picture: holonomic is a train on rails — the rule says "
            "<i>where</i> you can be. Nonholonomic is an ice skate — the blade "
            "only says which way you can glide <i>right now</i>, yet you can "
            "reach any spot on the rink, facing any way."))
        self.add(n)
        self.car = CarConstraintCard()
        self.add(self.car.card)
        self.add(constraint_uses_card())
        self.task = TaskSpaceCard()
        self.add(self.task.card)

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
            "for sampling planners on page 135."))
        self.add(w)
        self._draw()
        self.wslim = JointLimitWorkspaceCard()
        self.add(self.wslim.card)

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
    TITLE = "Rotations: SO(3), Angular Velocity, Exponential Coordinates"
    SUBTITLE = ("A rotation is a 3×3 matrix whose columns are a frame's axes: "
                "9 numbers held to 3 freedoms by 6 rules. Differentiate the "
                "rules and angular velocity appears; integrate it and "
                "Rodrigues' formula appears.")
    SECTION = SEC_CSPACE
    NOTES = playlist_badge(2)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(watch(2))
        self.add(start_here(
            "How do you write down which way an object is pointing in 3-D, "
            "how fast it is turning, and where a steady turn takes it? This "
            "page follows the first six videos of chapter 3, in order, one "
            "blue <b>VIDEO</b> box per video:<br>"
            "<b>3.1</b> frames and the right-hand rule → <b>3.2.1 (1)</b> the "
            "rotation matrix R and its 6 rules → <b>3.2.1 (2)</b> the three "
            "jobs R does → <b>3.2.2</b> angular velocity ω → <b>3.2.3 (1)</b> "
            "the matrix exponential → <b>3.2.3 (2)</b> Rodrigues' formula and "
            "the matrix log.<br>"
            "Almost nothing here is new in idea: it is pages 115–117 (DOF, "
            "implicit representation, holonomic and Pfaffian constraints) "
            "applied to orientation. The orange <b>CONNECTS TO PAGE</b> boxes "
            "say exactly which old word each new word renames. Start with the "
            "dictionary card, then take one video at a time: watch it, read "
            "its cards, play its lab."))
        self.add(rr.bridge_card())

        self.add(rr.video_tag("3.1", "Introduction to rigid-body motions", (
            "Frames, right-handedness, stationary frames, and the right-hand "
            "rule for positive rotation — plus the promise that orientation "
            "will be stored implicitly and velocity will not be a derivative "
            "of coordinates.")))
        self.add(rr.intro_card())
        self.hand = rr.FrameHandCard()
        self.add(self.hand.card)

        self.add(rr.video_tag("3.2.1", "Rotation matrices, part 1 of 2", (
            "R<sub>sb</sub> = {b}'s axes written in {s}; 9 numbers, 6 rules "
            "(RᵀR = I), det = +1; the group SO(3) and its properties.")))
        self.rmat = rr.RotationMatrixCard()
        self.add(self.rmat.card)
        self.add(rr.count_card())
        self.comm = rr.CommuteCard()
        self.add(self.comm.card)

        self.add(rr.video_tag("3.2.1", "Rotation matrices, part 2 of 2", (
            "Three uses of one matrix: represent an orientation, change the "
            "frame of reference (subscript cancellation), rotate a vector or "
            "frame (premultiply = space axis, postmultiply = body axis).")))
        self.subs = rr.SubscriptCard()
        self.add(self.subs.card)
        self.rop = rr.RotateOperatorCard()
        self.add(self.rop.card)

        self.add(rr.video_tag("3.2.2", "Angular velocities", (
            "Why Ṙ (9 numbers) is not the angular velocity; ω = ω̂θ̇; "
            "Ṙ = [ω<sub>s</sub>]R; the bracket [ω] and so(3); "
            "ω<sub>b</sub> = Rᵀω<sub>s</sub>.")))
        self.add(rr.angvel_why_card())
        self.angv = rr.AngularVelocityCard()
        self.add(self.angv.card)

        self.add(rr.video_tag("3.2.3", "Exponential coordinates of rotation, part 1 of 2", (
            "Three numbers ω̂θ for an orientation, and why they are called "
            "exponential: ẋ = ax gives e<sup>at</sup>, ẋ = Ax gives the "
            "matrix exponential e<sup>At</sup>.")))
        self.series = rr.ExpSeriesCard()
        self.add(self.series.card)

        self.add(rr.video_tag("3.2.3", "Exponential coordinates of rotation, part 2 of 2", (
            "Integrate ṗ = [ω̂]p for θ seconds: R = e<sup>[ω̂]θ</sup>, "
            "Rodrigues' closed form; the matrix log goes back; preview: a "
            "revolute joint is ω̂ = its axis, θ = its angle.")))
        self.integ = rr.IntegrateCard()
        self.add(self.integ.card)
        self.axang = rr.AxisAngleCard()
        self.add(self.axang.card)

        self.add(interview(
            "<b>“Why not Euler angles in a controller?”</b> They have a "
            "singularity (ZYX at pitch ±90°: roll and yaw become the same "
            "rotation, the map from rates to ω loses rank), their composition "
            "is not addition, and interpolating them gives curved, "
            "speed-varying motion. Compute with R or quaternions, and express "
            "orientation error as log(R<sub>d</sub>ᵀR) — a 3-vector you can "
            "multiply by a gain."))
        self.finish()


class TwistsPage(Page):
    TITLE = "Transforms, Twists, Screws and Wrenches"
    SUBTITLE = ("Page 118 again with position added: T = (R, p) for where a "
                "body is, a twist V = (ω, v) for how it moves (always a "
                "screw), a wrench F = (m, f) for what pushes it, and V·F is "
                "power in any frame.")
    SECTION = SEC_CSPACE
    NOTES = playlist_badge(2)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(watch(2))
        self.add(start_here(
            "Page 118 handled orientation only. Now add position. This page "
            "follows the last five videos of chapter 3, one blue <b>VIDEO</b> "
            "box each:<br>"
            "<b>3.3.1</b> the 4×4 transform T = (R, p) and its three uses → "
            "<b>3.3.2 (1)</b> the twist: every velocity is a screw → "
            "<b>3.3.2 (2)</b> moving a twist between frames (the adjoint) and "
            "its 4×4 form → <b>3.3.3</b> following a screw for θ: the "
            "exponential of a twist → <b>3.4</b> forces and torques as one "
            "6-vector, the wrench.<br>"
            "Each step copies a step of page 118: R → T, ω → V, "
            "so(3) → se(3), Rodrigues → its 4×4 version. If a step feels "
            "new, find its twin on page 118 first. In C-space words (page "
            "115): this page is about the 6-D C-space of one free body and "
            "its 6-D velocities and forces."))

        self.add(rr.video_tag("3.3.1", "Homogeneous transformation matrices", (
            "Pack (R, p) into T ∈ SE(3); inverse = swap subscripts; "
            "homogeneous coordinates (append a 1); T on the left uses space "
            "axes, T on the right uses body axes.")))
        self.add(rr.transform_card())
        self.homog = rr.HomogeneousCard()
        self.add(self.homog.card)
        self.lr = rr.LeftRightCard()
        self.add(self.lr.card)

        self.add(rr.video_tag("3.3.2", "Twists, part 1 of 2", (
            "Any velocity is a turn about a screw axis (q, ŝ, h) at rate θ̇; "
            "store it as S = (S<sub>ω</sub>, S<sub>v</sub>) in some frame; "
            "twist V = Sθ̇; infinite pitch = pure slide; body vs spatial twist.")))
        self.add(rr.twist_card())
        self.turn = rr.TurntableCard()
        self.add(self.turn.card)

        self.add(rr.video_tag("3.3.2", "Twists, part 2 of 2", (
            "The 6×6 adjoint moves twists between frames; [V<sub>b</sub>] = "
            "T⁻¹Ṫ and [V<sub>s</sub>] = ṪT⁻¹ are 4×4 matrices in se(3).")))
        self.add(rr.adjoint_card())

        self.add(rr.video_tag("3.3.3", "Exponential coordinates of rigid-body motion", (
            "Follow a screw S for θ: T = e<sup>[S]θ</sup>, 6 exponential "
            "coordinates Sθ; exp and log between se(3) and SE(3); S in {b} "
            "multiplies on the right, S in {s} on the left; every joint is a "
            "screw.")))
        self.add(rr.analogy_card())
        self.screw = rr.ScrewCard()
        self.add(self.screw.card)
        self.two = rr.ScrewTwoFramesCard()
        self.add(self.two.card)

        self.add(rr.video_tag("3.4", "Wrenches", (
            "Moment and force packed as F = (m, f); power VᵀF is the same in "
            "every frame, which forces F<sub>s</sub> = "
            "[Ad<sub>T<sub>bs</sub></sub>]ᵀF<sub>b</sub>; the apple and the "
            "wrist force sensor.")))
        self.add(rr.wrench_card())
        self.apple = rr.AppleCard()
        self.add(self.apple.card)

        self.add(interview(
            "<b>“A force sensor at the wrist reads F<sub>b</sub>. What torque "
            "does that force produce about the base?”</b> Transform it: "
            "F<sub>s</sub> = [Ad<sub>T<sub>bs</sub></sub>]ᵀ F<sub>b</sub>; the "
            "moment part picks up p × f. Then joint torques are "
            "τ = J<sub>b</sub>ᵀ F<sub>b</sub> = J<sub>s</sub>ᵀ F<sub>s</sub> — "
            "same answer, because both are power balances."))
        self.finish()


