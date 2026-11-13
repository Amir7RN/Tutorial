"""
HUMANOID BALANCE -- the upper body of a G1 as a balance machine.

A chapter built for one project: a Unitree G1 in MuJoCo is pushed, and the
waist and arms are used to absorb the push. It spends the dynamics block
(pages 133-139) on that machine: derive the equations of motion of the
legs-torso-arms chain in one plane, lock joints to move between planes, read
the momentum those Jacobians carry, and build the law that turns a push into
joint torques. The numerics are in ctrlcore/upperbody.py; the labs
(app/assets/steplab/g1_upper_body.html, upper_body_lagrange.html,
upper_body_recovery.html) run the same model in the browser (ub.js), and
tests/test_upperbody.py checks every claim made here, in both languages.

    165  the G1 upper body as a machine: joints, planes, locks
    166  sagittal plane: derive the equations of motion yourself
    167  momentum: why the arms can save a fall
    168  the recovery law: from a push to joint torques
    169  from this model to MuJoCo and C++
"""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtWidgets import QPushButton

from ctrlcore import upperbody as ub
from .. import theme
from ..widgets import Card, body, callout, math_label
from ..widgets.code import CodePane
from .base import Page
from .cpp_course import Choice, Reveal, WebLab, two_col
from .robo_common import interview, mat_html, plain, start_here

SEC = "Upper-Body Balance"


def _table(head, rows):
    h = "".join(f"<th align='left' style='padding:4px 10px;color:{theme.TEXT_DIM}'>{x}</th>" for x in head)
    r = "".join("<tr>" + "".join(f"<td style='padding:4px 10px;vertical-align:top'>{c}</td>" for c in row) + "</tr>"
                for row in rows)
    return body(f"<table cellspacing='0'><tr>{h}</tr>{r}</table>")


class BalancePage(Page):
    SECTION = SEC
    NO_RECAP = True       # the chapter ends in a project page, not a recap

    def lab(self, html, title, height):
        self.add(WebLab(html, "", title, height))


# ==========================================================================
# 165
# ==========================================================================

class UpperBodyMachinePage(BalancePage):
    TITLE = "The G1 Upper Body as a Machine: Joints, Planes, Locks"
    SUBTITLE = ("Before any equation: which joints move in which plane, what a lock does to the mass matrix, "
                "and why one planar chain is enough to start.")
    NOTES = "G1 · project"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(start_here(
            "The project: a G1 standing in MuJoCo is pushed at the shoulder. The feet stay where they are, "
            "so the ankle can only push on the ground within the foot. Everything else has to come from the "
            "waist and the arms. This chapter builds that machine in the smallest form that still has the "
            "physics: a <b>planar chain</b> of legs, torso and arms pinned at the ankle. Pages 133 to 139 "
            "gave you M, c and g for an arm; here you derive them for this chain yourself, then read the "
            "momentum they carry, then write the law. The real robot is a tree with a floating base; the "
            "plane is where the ideas are learnt and the numbers are checked."))
        m = ub.PLANES["sagittal"]
        t = Card("the sagittal model and its numbers (approximate G1, 35 kg)")
        t.add(_table(["link", "moved by", "m (kg)", "L (m)", "r to COM (m)", "I about COM (kg·m²)"],
                     [[l.name, l.joint, l.m, l.L, l.r, l.I] for l in m.links]))
        t.add(body(
            "Both arms are folded into one link of twice the mass because in a plane they move together. "
            "The legs and pelvis are one rigid link because the feet are planted. These numbers are for "
            "learning: read the real ones from each body's <code>mass</code>, <code>inertia</code> and "
            "<code>pos</code> in the G1 MJCF (mujoco_menagerie/unitree_g1) before trusting a torque.", dim=True))
        self.add(t)
        self.lab("g1_upper_body.html", "Lab · the G1 in 3-D: pick a plane, lock joints, watch M shrink", 980)
        p = Card("three planes, one recipe")
        p.add(_table(["plane", "the chain", "gravity", "the push it answers", "G1 joints"],
                     [["sagittal (side)", "ankle pitch → waist pitch → shoulder pitch → elbow", "yes",
                       "from behind or in front", ", ".join(ub.G1_JOINTS["sagittal"])],
                      ["frontal (front)", "ankle roll → waist roll → shoulder roll (arms straight)", "yes",
                       "from the side (your beam-walking problem)", ", ".join(ub.G1_JOINTS["frontal"])],
                      ["transverse (top)", "feet on the floor → waist yaw → shoulder yaw (arms held out)", "no",
                       "a twist", ", ".join(ub.G1_JOINTS["transverse"])]]))
        p.add(body(
            "Nothing in the derivation knows which plane it is in. Only the joint names, the rest angles "
            "(the arms hang in the sagittal plane, they are held out in the transverse one) and whether "
            "gravity acts change. In ctrlcore/upperbody.py the three planes are three parameter sets "
            "of one <code>Model</code>."))
        self.add(p)
        self.add(plain(
            "<b>Locking a joint</b> freezes its angle. The mass of everything above it still rides along "
            "when the joints below move, so nothing is removed from the physics; what is removed is a "
            "<i>choice</i>. In the equations that is one column of every Jacobian multiplied by zero, "
            "so M loses a row and a column: <b>M<sub>locked</sub> = SᵀMS</b>, where S keeps the free "
            "columns. The diagonal entries of the surviving joints do not change. Try it in the lab: lock "
            "the elbow and M<sub>00</sub> stays the same."))
        self.add(two_col(
            Reveal("Say it out loud", [
                ("Why is joint 0 never locked?",
                 "Because it is not a motor's choice. The ankle angle is the thing to be balanced; the ground "
                 "can push back only within the foot. Locking it would hide the whole problem."),
                ("Why can both arms be one link?",
                 "In a planar model they are given the same angle, so their masses and inertias simply add. "
                 "The moment one arm does something the other does not (the real robot can), the model "
                 "needs a tree, which is what MuJoCo gives you on page 169."),
                ("What is M<sub>01</sub> physically?",
                 "The torque the ankle feels when the waist alone accelerates by 1 rad/s²: every mass above "
                 "the waist, times its arm to the ankle, times its arm to the waist, times the cosine between "
                 "the arms (page 134). It is the coupling that lets the upper body act on a joint it has no "
                 "motor at."),
                ("Which plane is the G1 project?",
                 "Start sagittal: a push from behind is the common case and gravity makes it dangerous. The "
                 "frontal plane is the same chain with roll joints; it is also the plane of your mediolateral "
                 "exoskeleton work, so the law you write will look familiar."),
            ]),
            Choice("Quick check", "Lock the elbow at 0°. Which entries of the sagittal M change?",
                   [("M₀₀ shrinks: the forearm no longer counts", False,
                     "The forearm's mass still rides on the arm. M₀₀ is unchanged; the lab shows the same "
                     "number before and after."),
                    ("only the elbow row and column disappear", True,
                     "The forearm stays in every remaining sum; what goes is the elbow as a coordinate. "
                     "SᵀMS keeps the 3×3 block of the free joints exactly."),
                    ("every entry changes a little", False,
                     "The entries are sums over masses and arms; locking changes neither."),
                    ("nothing, M is a property of the robot", False,
                     "M is a property of the robot <i>and</i> of the coordinates you choose. Fewer "
                     "coordinates, smaller M.")])))
        self.finish()


# ==========================================================================
# 166
# ==========================================================================

class UpperBodyDerivePage(BalancePage):
    TITLE = "Sagittal Plane: Derive the Equations of Motion Yourself"
    SUBTITLE = ("Positions, one Jacobian per centre of mass, kinetic energy, potential energy, and the "
                "velocity products: the same five moves as page 133, on your own machine, with every "
                "number checkable.")
    NOTES = "G1 · derive"

    Q = np.array([0.15, -0.2, -0.9, -0.6])
    QD = np.array([0.6, -0.5, 2.0, 1.0])

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(start_here(
            "Do this page with paper. The lab on the left computes every intermediate quantity at the "
            "posture you set; your job is to get the same number first. The derivation never touches "
            "Christoffel symbols: velocities come from Jacobians, M from the kinetic energy, g from the "
            "potential energy, and the velocity-product term from the accelerations the COMs have when "
            "the joints are only spinning. That is also exactly what the code computes, in Python and "
            "in the browser, and the two are tested against each other and against page 135's recursion."))
        e = Card("the recipe, in five lines")
        e.add(math_label(r"\phi_i=\sum_{j\le i}(q_j+\mathrm{off}_j),\quad u_i=(\sin\phi_i,\cos\phi_i),\quad "
                         r"p_{i+1}=p_i+L_iu_i,\quad c_i=p_i+r_iu_i", 14))
        e.add(math_label(r"\frac{\partial c_i}{\partial q_j}=\big((c_i-p_j)_y,\,-(c_i-p_j)_x\big)\ (j\le i),"
                         r"\qquad v_i=J_i\dot q,\qquad \omega_i=\sum_{j\le i}\dot q_j", 14))
        e.add(math_label(r"K=\tfrac12\dot q^TM\dot q,\qquad M=\sum_i m_iJ_i^TJ_i+I_iJ_{\omega i}^TJ_{\omega i}", 15))
        e.add(math_label(r"P=\sum_i m_i g\,c_{i,y},\qquad g_j=\frac{\partial P}{\partial q_j}"
                         r"=-g\sum_{i\ge j}m_i\,(c_i-p_j)_x", 15))
        e.add(math_label(r"c=\sum_i m_iJ_i^T a_i^{\mathrm{vel}},\quad a_i^{\mathrm{vel}}=\sum_{j\le i}\dot q_j\,"
                         r"\mathrm{swing}(v_i-\dot p_j)\qquad\Rightarrow\qquad \tau=M(q)\ddot q+c(q,\dot q)+g(q)", 15))
        e.add(body(
            "<b>Conventions</b> (the G1's own): x forward, y up, every angle positive when the top of the "
            "link moves forward. A forward lean is a positive ankle angle; a positive shoulder pitch swings "
            "the hanging arm backward. The rest offset is π at the shoulder so that q = 0 is standing "
            "straight with the arms down. <b>swing(d) = (d<sub>y</sub>, −d<sub>x</sub>)</b> is the velocity "
            "of a point at offset d from a pivot turning at 1 rad/s in the forward sense.", dim=True))
        self.add(e)
        self.lab("upper_body_lagrange.html", "Lab · the derivation, one step at a time, with live numbers", 1000)

        w = ub.worked(ub.PLANES["sagittal"], self.Q, self.QD)
        m = ub.PLANES["sagittal"]
        k = Card("worked numbers at one posture (compute first, then open)")
        k.add(body(f"q = {np.round(np.degrees(self.Q), 1).tolist()} degrees, "
                   f"q̇ = {self.QD.tolist()} rad/s. Set the sliders to these and the lab agrees to three decimals."))
        k.add(Reveal("", [
            ("Where is the shoulder (p₂), and the hand (p₄)?",
             f"p₂ = ({w['p'][2][0]:.3f}, {w['p'][2][1]:.3f}) m, p₄ = ({w['p'][4][0]:.3f}, {w['p'][4][1]:.3f}) m. "
             "Two cumulative sums of q + off, then sines and cosines."),
            ("Column 1 (waist) of the forearm's Jacobian J₃?",
             f"d = c₃ − p₁ = ({(w['c'][3] - w['p'][1])[0]:.3f}, {(w['c'][3] - w['p'][1])[1]:.3f}), so the column is "
             f"(d_y, −d_x) = ({w['Jv'][3][0][1]:.3f}, {w['Jv'][3][1][1]:.3f}). Perpendicular to d, forward sense."),
            ("M₀₀ and M₀₁?",
             f"M₀₀ = {w['M'][0, 0]:.3f}, M₀₁ = {w['M'][0, 1]:.3f} kg·m². M₀₀ sums every link's m|swing₀|² + I; "
             f"M₀₁ sums, over torso and arms only, m (swing₀·swing₁) + I. Full matrix:<br>{mat_html(w['M'])}"),
            ("The gravity vector g?",
             f"g = {np.round(w['g'], 2).tolist()} N·m. g₀ = −{m.m_tot:.0f} × 9.81 × x_c = "
             f"−{w['gravity_moment']:.2f} N·m: a forward lean needs a backward ankle torque, and the foot can "
             f"give at most ±{m.tau_ankle_max():.1f} N·m."),
            ("The velocity-product vector c?",
             f"c = {np.round(w['cvec'], 2).tolist()} N·m. Set every q̇ to zero and it vanishes; double them all "
             "and it quadruples, because every term is q̇ × q̇."),
        ]))
        self.add(k)
        self.add(plain(
            "<b>What each term means for balance.</b> M₀₀ is how hard the whole body is to tip about the "
            "ankle. The off-diagonal M₀ⱼ is how much joint j can shove the ankle without any motor there: "
            "the only handle the upper body has. g₀ is gravity's torque about the ankle, m g x<sub>c</sub>, "
            "and the foot can resist it only up to m g × (half the foot). The moment the lean puts "
            "x<sub>c</sub> beyond the toes, the ankle row cannot be satisfied and the equation says "
            "<i>fall</i>, unless the upper body changes x<sub>c</sub> or the momentum."))
        self.add(Choice("Quick check", "You double every joint rate q̇ and keep q. What happens to c, g and K?",
                        [("c ×2, g ×2, K ×2", False, "g depends on q only; the others are quadratic in q̇."),
                         ("c ×4, g unchanged, K ×4", True,
                          "Every velocity product is a product of two rates; so is ½q̇ᵀMq̇. Gravity does not "
                          "know how fast you move."),
                         ("c ×4, g ×4, K ×4", False, "Gravity is a function of posture alone."),
                         ("nothing: M fixes everything", False,
                          "M fixes the ratio of torque to acceleration; the rates still enter c and K.")]))
        self.finish()


# ==========================================================================
# 167
# ==========================================================================

class UpperBodyMomentumPage(BalancePage):
    TITLE = "Momentum: Why the Arms Can Save a Fall"
    SUBTITLE = ("Angular momentum about the ankle can only be changed by three things: the ankle torque, "
                "gravity, and the push. Motors inside the body only move it between the links, and shift "
                "where gravity acts. That is the whole theory of upper-body balance.")
    NOTES = "G1 · momentum"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(start_here(
            "One identity carries this page and the next. Take the angular momentum of the whole body "
            "about the ankle, H<sub>O</sub>. Internal torques come in equal and opposite pairs, so they "
            "cannot change it. Only external moments can: the ankle torque, gravity acting at the COM, and "
            "the push. After a push H<sub>O</sub> is positive (rotating forward) and will keep growing while "
            "the COM is in front of the ankle. Recovery means driving it back to zero with the only three "
            "levers that exist."))
        e = Card("the balance identity, and the momentum matrix")
        e.add(math_label(r"\frac{dH_O}{dt}=\tau_{\mathrm{ankle}}+m_{\mathrm{tot}}\,g\,x_c+(p_{\mathrm{push}}\times F)", 17))
        e.add(math_label(r"H_O=\sum_i I_i\omega_i+m_i\,(c_i\times v_i)=A_O(q)\,\dot q,\qquad "
                         r"h_c=\begin{bmatrix}p_x\\p_y\\H_c\end{bmatrix}=A(q)\,\dot q,\quad "
                         r"A=\sum_i\begin{bmatrix}m_iJ_i\\ I_iJ_{\omega i}+m_i(c_i-x_c)\times J_i\end{bmatrix}", 15))
        e.add(body(
            "Compare A with M = Σ m<sub>i</sub>J<sub>i</sub>ᵀJ<sub>i</sub> + I<sub>i</sub>J<sub>ωi</sub>ᵀJ<sub>ωi</sub>: "
            "<b>the momentum matrix is the mass matrix with the outer Jᵀ stripped off</b>. Same Jacobians, same "
            "masses and inertias; M lands in joint space, A lands in physical momentum. A about the COM is "
            "the <i>centroidal momentum matrix</i> of the humanoid literature. At q = 0 the H row of A<sub>O</sub> "
            "equals row 0 of M: the ankle's share of the inertia is the momentum about the ankle per unit "
            "joint rate. (Step 9 of the lab on page 166 prints both.)"))
        self.add(e)
        m = ub.PLANES["sagittal"]
        qd = np.array([0.0, 0.0, -3.0, 0.0])
        lh = m.link_momenta(np.zeros(4), qd)
        A_O = m.momentum_matrix(np.zeros(4), about=(0, 0))
        w = Card("where the mass moves, not how it spins")
        w.add(body(
            f"Stand straight and swing the arms <b>forward</b> at 3 rad/s (shoulder rate −3, the arm's own "
            f"spin is backward). The arms' share of H<sub>O</sub> is +{lh[2] + lh[3]:.2f} N·m·s: <b>forward</b>. "
            f"Their spin contributes only {m.links[2].I * qd[2]:.2f}; their mass moving forward one metre above "
            f"the pivot contributes the rest, because c × v = (c<sub>y</sub> v<sub>x</sub> − c<sub>x</sub> v<sub>y</sub>). "
            f"With H<sub>O</sub> fixed, the legs must take the opposite share: their rate becomes "
            f"{-(A_O[2, 2] * qd[2]) / A_O[2, 0]:+.2f} rad/s, backward. Swinging the arms forward rotates the "
            "legs back. That is the arm strategy, and it is a statement about the arms' <i>height</i>, "
            "not their rotation."))
        w.add(body(f"Row H of A<sub>O</sub> at q = 0: {np.round(A_O[2], 3).tolist()} N·m·s per rad/s "
                   f"(ankle, waist, shoulder, elbow). The shoulder entry is negative: a positive shoulder rate "
                   f"(arm backward) is backward momentum about the ankle.", dim=True))
        self.add(w)

        sim = Card("a 70 N push, 100 ms, at the shoulder: the momentum moves between the links")
        self.sim_btn = QPushButton("Simulate it (about three seconds)")
        self.sim_btn.setMaximumWidth(280)
        self.sim_out = body("")
        sim.add(self.sim_btn)
        sim.add(self.sim_out)
        self.sim_btn.clicked.connect(self._simulate)
        sim.add(body("The same run, animated, with every slider live, is the lab on page 168.", dim=True))
        self.add(sim)
        self.add(plain(
            "<b>What the arms can and cannot do.</b> They cannot change H<sub>O</sub> at all. They can "
            "(1) take forward momentum so that the legs lose it, which stops the lean from growing for a "
            "moment, and (2) move the COM, which changes the sign of gravity's moment. Both are bounded: "
            "the arms reach their range and the torso its stop, and then the momentum comes back. The ankle "
            "torque and gravity must do the rest within that window. Page 168 measures the window."))
        self.add(interview(
            "<b>\"How does swinging the arms help a humanoid balance?\"</b> Angular momentum about the stance "
            "point is conserved by internal torques, so accelerating the arms in the direction of the fall "
            "gives them momentum the trunk and legs must give up; while that lasts the lean stops growing and "
            "the ankle and gravity can recover it. It is a momentum exchange with a bounded budget (the arms' "
            "range), not a source of momentum. In the centroidal formulation: choose ḣ, solve A q̈ = ḣ − Ȧq̇, "
            "put posture in the null space."))
        self.add(Choice("Quick check", "The robot is falling forward. Which arm motion helps most, per unit of arm speed?",
                        [("swing the hanging arms forward", True,
                          "Their mass moves forward a metre above the pivot: large forward momentum, and the "
                          "legs must rotate back. The arm's own backward spin is a tenth of that."),
                         ("swing the hanging arms backward", False,
                          "Their mass moves backward: backward momentum about the ankle, so the legs rotate "
                          "<i>forward</i>. That is the right move for a backward fall."),
                         ("spin the forearms only", False,
                          "The forearms are light and close to the elbow; their spin and travel are both small."),
                         ("hold the arms rigid: the hip does it all", False,
                          "The hip strategy works the same way, with the torso. The arms add to it, and they are "
                          "the only lever that costs no COM height.")]))
        self.finish()

    def _simulate(self):
        m = ub.PLANES["sagittal"]
        res = ub.simulate(m, ub.Gains(), ub.Push(force=70), active=[1, 2, 3], T=1.6)
        rows = []
        for i in range(0, len(res["t"]), 8):
            H = res["link_H"][i]
            rows.append([f"{res['t'][i]:.2f}", f"{math.degrees(res['q'][i][0]):+.1f}°",
                         f"{math.degrees(res['q'][i][1]):+.0f}°", f"{math.degrees(res['q'][i][2]):+.0f}°",
                         f"{H[0]:+.2f}", f"{H[1]:+.2f}", f"{H[2] + H[3]:+.2f}", f"{res['H_O'][i]:+.2f}",
                         f"{res['xc'][i][0]:+.3f}"])
        verdict = ("fell" if res["fell"] else f"recovered, peak lean {res['peak_lean_deg']:.1f}°")
        self.sim_out.setText(f"<b>{verdict}</b> (LQR law, whole upper body, 10 cm foot).<br>"
                             + _table(["t (s)", "lean", "waist", "shoulder", "H legs", "H torso", "H arms", "H total", "x_c (m)"],
                                      rows).text())
        self.sim_btn.setEnabled(False)


# ==========================================================================
# 168
# ==========================================================================

RECOVERY_TABLE = [
    # (push force at the shoulder for 0.1 s, everything locked, whole upper body with the LQR law)
    (60, "stands, peak 6.0°", "stands, peak 5.0°"),
    (70, "stands, peak 7.9°", "stands, peak 6.2°"),
    (75, "falls", "stands, peak 7.1°"),
    (80, "falls", "stands, peak 8.4°"),
    (85, "falls", "falls"),
]


class UpperBodyRecoveryPage(BalancePage):
    TITLE = "The Recovery Law: From a Push to Joint Torques"
    SUBTITLE = ("Three laws, one that works. What the upper body buys with a 10 cm foot, measured, and why the "
                "two formulas every paper writes fail on this machine.")
    NOTES = "G1 · control"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(start_here(
            "The controller's job: at every tick, from (q, q̇), produce torques for the waist and the arms. "
            "The ankle is not a command: it is a spring-damper saturated at m g × (half foot), the most the "
            "sole can do. Everything on this page was simulated with the model of page 166 and is tested. "
            "The honest result first: with a 10 cm foot the ankle alone survives a 70 N × 0.1 s push and "
            "falls at 75 N; with the upper body under a linear law it survives 80 N and falls at 85 N. "
            "The upper body buys about 15 percent of push, and halves the lean on the pushes the ankle could "
            "already take. It is not magic, and the two \"obvious\" laws make things worse."))
        laws = Card("three laws")
        laws.add(body("<b>1 · LQR on the linearised machine (the one that works).</b> Linearise "
                      "ẋ = f(x, u) about standing with the ankle spring included (page 19 style, by central "
                      "differences), choose Q and R by Bryson's rule (a 0.1 rad lean, 0.5 rad of posture, 1 and "
                      "5 rad/s, each motor's torque limit), and apply"))
        laws.add(math_label(r"\tau_u=-K\begin{bmatrix}q\\\dot q\end{bmatrix},\qquad K=R^{-1}B^TP", 15))
        laws.add(body("clipped to the limits. It discovers the hip-and-arm strategy by itself: torso and arms go "
                      "forward with the fall for a moment, then return while the ankle and gravity finish."))
        laws.add(body("<b>2 · The counterweight (looks right, fails).</b> Put the whole-body COM behind the "
                      "ankle in proportion to the lean, through a virtual spring on the upper body's COM and "
                      "page 144's Jᵀ:"))
        laws.add(math_label(r"x_{c,\mathrm{des}}=-(\kappa_p q_0+\kappa_d\dot q_0),\quad "
                            r"F=k_x(x_{\mathrm{up,des}}-x_{\mathrm{up}})-b_x\dot x_{\mathrm{up}},\quad "
                            r"\tau_u=J_{\mathrm{up}}^TF+(c+g)_u+N\,\tau_{\mathrm{posture}}", 14))
        laws.add(body("<b>3 · Resolved momentum control with a QP (the paper formula, fails here).</b> Choose "
                      "a desired momentum rate from the divergent component of motion, keep the ankle row as a "
                      "constraint, solve for the upper-body torques inside their box:"))
        laws.add(math_label(r"\xi=x_c+\dot x_c/\omega,\ \ \dot H_{c,\mathrm{des}}=m g\,\xi(1+k/\omega)+\tau_{\mathrm{ankle}},\quad "
                            r"\min_{\tau_u}\ w(\dot H_c-\dot H_{c,\mathrm{des}})^2+\lambda\|\ddot q_u-\ddot q_{\mathrm{post}}\|^2"
                            r"\ \ \mathrm{s.t.}\ |\tau_u|\le\tau_{\max}", 13))
        laws.add(body("Without the limits this is the weighted pseudo-inverse plus a null-space posture term, "
                      "q̈<sub>u</sub> = Ã⁺(ḣ<sub>des</sub> − b̃) + N q̈₀, the structure you were promised. "
                      "The QP is three unknowns with box bounds, solved by trying every saturation pattern.", dim=True))
        self.add(laws)
        self.lab("upper_body_recovery.html", "Lab · push it: lock joints, switch laws, compare the four strategies", 1180)
        t = Card("what the upper body buys (sagittal, 10 cm foot, push at the shoulder for 0.1 s)")
        t.add(_table(["push", "everything locked (ankle only)", "whole upper body, LQR"],
                     [[f"{F} N ({F * 0.1:.1f} N·s)", a, b] for F, a, b in RECOVERY_TABLE]))
        t.add(body("Arms only does about as well as the whole upper body on this model, and the waist only "
                   "slightly less: the arms are light but they move a metre above the pivot. "
                   "tests/test_upperbody.py reruns the 70 N and 75 N rows.", dim=True))
        self.add(t)
        self.add(plain(
            "<b>Why the counterweight fails: the kick.</b> Moving the 17 kg upper body back by 0.1 m gives it "
            "backward momentum about the ankle of about m × height × Δx = 17 × 1.0 × 0.1 = 1.7 kg·m² (as an "
            "angle-integral). Conservation hands the legs the same amount forward: with about 17.5 kg·m² "
            "about the ankle, the legs advance 0.1 rad, 5.6°, which moves the COM forward 0.66 × 0.1 = "
            "0.065 m. Net COM shift: −0.1 + 0.065 = −0.035 m, a third of what was paid for, and the lean is "
            "worse. <b>Why the momentum QP fails:</b> it asks for a momentum <i>rate</i>, which a torso with "
            "a ±30° range cannot keep supplying; it hits the stop with the COM in front of the foot. The LQR "
            "wins because it is a law on the <i>state</i>, with posture in the cost, so it spends the torso "
            "and arms for a moment and brings them home."))
        self.add(two_col(
            Reveal("Say it out loud", [
                ("Why is the ankle a spring and not a command?",
                 "The sole can only push on the ground between heel and toe, so the ankle torque is bounded by "
                 "m g × (distance from ankle to the edge of the foot): 33 N·m for 34 kg and 10 cm. A law that "
                 "asks for more lifts the heel, which this model represents as saturation."),
                ("What does LQR know that the counterweight does not?",
                 "The coupling and the kick. Its A matrix contains M⁻¹ and the gravity stiffness, so it knows "
                 "that moving the torso back pushes the legs forward, and it chooses the forward whip first."),
                ("Why does the momentum QP spin the torso?",
                 "Because its target is a rate. As long as the DCM is in front of the foot it asks for forward "
                 "momentum rate, and the torso delivers it by accelerating until the stop. Nothing in a rate "
                 "task says where the posture is."),
                ("What would make the upper body matter more?",
                 "Heavier or longer arms, a lighter lower body, a smaller foot, or a push that arrives faster "
                 "than the ankle can react. On a G1 the arms are 20 percent of the mass; on a human with a "
                 "backpack they are less. That is why the real design question is the ankle and the step."),
            ]),
            Choice("Quick check", "Locked, the robot falls at 75 N. With LQR and the whole upper body it stands at 80 N. The lab shows it also stands at 80 N with the arms only. Why?",
                   [("the arms are heavier than the torso", False, "They are 6 kg against 11 kg."),
                    ("the arms act a metre above the pivot and have a wide range", True,
                     "Momentum about the ankle is mass × height × speed. The arms are high and can travel far "
                     "before their stop, so they can hold forward momentum longer than the torso's 30°."),
                    ("the waist motor is too weak", False,
                     "88 N·m is plenty; the waist's problem is its range, not its torque."),
                    ("the arms change H about the ankle", False,
                     "Nothing inside the body can. They move it between links.")])))
        self.finish()


# ==========================================================================
# 169
# ==========================================================================

MUJOCO_CHECK = r'''
# check_g1.py -- the planar model against MuJoCo, one quantity at a time.
# pip install mujoco; clone google-deepmind/mujoco_menagerie for unitree_g1.
import mujoco, numpy as np
from ctrlcore import upperbody as ub

model = mujoco.MjModel.from_xml_path("mujoco_menagerie/unitree_g1/scene.xml")
data = mujoco.MjData(model)
mujoco.mj_resetDataKeyframe(model, data, 0)          # the standing keyframe
mujoco.mj_forward(model, data)

def jid(name):                                        # joint -> its dof index
    return model.jnt_dofadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)]

# 1. the mass matrix MuJoCo computes, restricted to the sagittal joints
M = np.zeros((model.nv, model.nv)); mujoco.mj_fullM(model, M, data.qM)
dofs = [jid("left_ankle_pitch_joint"), jid("waist_pitch_joint"),
        jid("left_shoulder_pitch_joint"), jid("left_elbow_joint")]
M_sag = M[np.ix_(dofs, dofs)]                         # ONE leg and ONE arm: halve the planar arm masses
planar = ub.PLANES["sagittal"]
print(M_sag.round(3)); print(planar.mass_matrix(np.zeros(4)).round(3))

# 2. gravity: the torque needed to hold the pose is data.qfrc_bias with qvel = 0
data.qvel[:] = 0; mujoco.mj_forward(model, data)
print(data.qfrc_bias[dofs].round(2), planar.gravity(np.zeros(4)).round(2))

# 3. momentum: subtree angular momentum about the subtree COM (the centroidal part)
mujoco.mj_subtreeVel(model, data)
pelvis = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "pelvis")
print(data.subtree_angmom[pelvis], data.subtree_com[pelvis])

# 4. the push: a force at the torso for 100 ms, then your controller in the loop
torso = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "torso_link")
for step in range(3000):
    data.xfrc_applied[torso, :3] = [70.0, 0, 0] if 300 <= step < 400 else 0
    data.ctrl[:] = controller(data)                   # yours: q, qd -> torques, LQR first
    mujoco.mj_step(model, data)
'''


class UpperBodyProjectPage(BalancePage):
    TITLE = "From This Model to MuJoCo and C++"
    SUBTITLE = ("The project plan: get the controller working in Python on the real G1 model, checking each "
                "quantity against the plane you derived, then port it to C++ as a class with an invariant.")
    NOTES = "G1 · project"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(start_here(
            "Do not learn C++ and the dynamics at the same time. Phase 1 is Python and MuJoCo: the planar "
            "model is your oracle, and every number MuJoCo gives you is compared with it before you trust the "
            "next one. Phase 2 ports the working controller to C++, where the only new thing is the language "
            "and the structure you learnt in pages 150 to 164 is the design."))
        ph = Card("phase 1 · Python + MuJoCo, in checkable steps")
        ph.add(_table(["step", "do", "check against the plane"],
                      [["1", "Load unitree_g1 from mujoco_menagerie, reset to the standing keyframe, weld the "
                             "pelvis or fix the feet", "the robot stands still with zero ctrl plus gravity compensation"],
                       ["2", "mj_fullM; take the sagittal rows and columns", "M₀₀, M₀₁ within 30 percent of page "
                             "166 (one leg and one arm per side: halve the planar arm masses)"],
                       ["3", "qfrc_bias with qvel = 0", "the gravity vector g; a forward lean gives a negative ankle entry"],
                       ["4", "mj_subtreeVel; subtree_angmom and subtree_com of the pelvis", "H about the COM equals "
                             "A q̇ from page 167, at the same joint rates"],
                       ["5", "Linearise by finite differences of mj_step (mjd_transitionFD does it for you), "
                             "design K with the same Bryson weights", "the gains have the same signs as the planar K: "
                             "torso and arms go forward with the fall"],
                       ["6", "Apply the push with xfrc_applied; log lean, link momenta, torques", "the plots of "
                             "page 168: momentum moves to the arms, then returns; find the push at which it falls"],
                       ["7", "Free the base (feet on the ground through contact), keep the legs' joints under a stiff "
                             "PD", "the ankle saturation now happens by itself: the heel lifts"]]))
        self.add(ph)
        code = Card("the checking script, as far as this tutor can take it")
        code.add(CodePane(MUJOCO_CHECK.strip("\n")))
        code.add(body("Names come from the menagerie MJCF and may differ between the 23- and 29-dof files; "
                      "<code>mujoco</code> is not installed here, so this was not run. Treat it as a map, "
                      "not a result.", dim=True))
        self.add(code)
        cpp = Card("phase 2 · the C++ port, in the words of pages 150 to 164")
        cpp.add(body(
            "<b>One class per invariant.</b> <code>PlanarModel</code> owns the link parameters and promises "
            "that M is symmetric positive definite for every q (that is a unit test, page 156). "
            "<code>BalanceController</code> owns K, the limits and the ankle model, and promises that every "
            "torque it returns is inside the limits. <code>Scheduler</code> runs the controller at 1 kHz and "
            "the logger at 50 Hz with a triple buffer between them (page 163).<br><br>"
            "<b>Fixed-size Eigen</b> for everything: <code>Eigen::Matrix&lt;double,4,4&gt;</code> for M, "
            "<code>Matrix&lt;double,3,8&gt;</code> for K. No allocation in <code>update()</code>; design K in "
            "<code>configure()</code> (page 160).<br><br>"
            "<b>The port is the test.</b> Compile the C++ model, feed it the posture of page 166, and compare "
            "M, c, g and A with ctrlcore/upperbody.py to 1e-9, exactly as ub.js is compared today. Only then "
            "port the controller. The structure to copy is tests/test_upperbody.py's JavaScriptPort test."))
        self.add(cpp)
        self.add(Reveal("Before you start, say it out loud", [
            ("What is the plant, the input, and the disturbance?",
             "The plant is the G1 from the pelvis up, on legs the ankle can only steer within the foot. The "
             "inputs are the waist and arm torques. The disturbance is a force at the torso for 100 ms."),
            ("What is the first number you will check?",
             "M₀₀ from mj_fullM against 18 kg·m² from the plane. If that is off by a factor, the joint "
             "indices or the units are wrong, and nothing after it means anything."),
            ("What will you measure to say the upper body helped?",
             "The largest push impulse that does not end in a fall, with and without the upper body, at the "
             "same foot. One number per configuration, like the table on page 168."),
            ("Where does the project touch your beam-walking paper?",
             "The frontal-plane chain is the mediolateral problem, and the law on momentum about the stance "
             "foot is the same quantity your exoskeleton regulated. The G1 just has to do it with its own "
             "torso instead of a motor at the hip."),
        ]))
        self.finish()


BALANCE_PAGES = [UpperBodyMachinePage, UpperBodyDerivePage, UpperBodyMomentumPage,
                 UpperBodyRecoveryPage, UpperBodyProjectPage]
