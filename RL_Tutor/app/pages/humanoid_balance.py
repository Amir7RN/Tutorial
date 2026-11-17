"""
HUMANOID BALANCE -- the upper body of a G1 as a balance machine.

A chapter built for one project: a Unitree G1 in MuJoCo is pushed, and the
waist and arms are used to absorb the push. It spends the dynamics block
(pages 133-140) on that machine: derive the equations of motion of the
legs-torso-arms chain in one plane, lock joints to move between planes, read
the momentum those Jacobians carry, and build the law that turns a push into
joint torques. The numerics are in ctrlcore/upperbody.py; the labs
(app/assets/steplab/g1_upper_body.html, upper_body_lagrange.html,
upper_body_recovery.html) run the same model in the browser (ub.js), and
tests/test_upperbody.py checks every claim made here, in both languages.

    166  the G1 upper body as a machine: joints, planes, locks
    167  sagittal plane: from twists to the equations of motion
    168  momentum: why the arms can save a fall
    169  the recovery law: from a push to joint torques
    170  LQR opened up: from -Kx to a torque at each joint
    171  from this model to MuJoCo and C++
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
            "physics: a <b>planar chain</b> of legs, torso and arms pinned at the ankle. Pages 133 to 140 "
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
                 "needs a tree, which is what MuJoCo gives you on page 171."),
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
    TITLE = "Sagittal Plane: From Twists to the Equations of Motion"
    SUBTITLE = ("Page 166 gave the mass matrix. Here the same simplified G1 goes from screw axes and body "
                "Jacobians to τ = M(q)q̈ + c(q,q̇) + g(q), in the Kinematics notation, one step at a time.")
    NOTES = "G1 · derive"

    Q = np.array([0.15, -0.2, -0.9, -0.6])
    QD = np.array([0.6, -0.5, 2.0, 1.0])

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(start_here(
            "<b>Where we are.</b> Page 166 built M(q), how much torque each joint needs per unit q̈. That is "
            "one of three terms. A robot standing still with q̈ = 0 still needs torque to carry its weight, "
            "g(q). A robot whose joints are turning needs torque just to keep them turning, c(q, q̇). This "
            "page derives all three on the simplified G1 with the tools of the Kinematics pages: frame {s}, "
            "screw axes 𝒮, the product of exponentials, the body Jacobian J<sub>b</sub> and the twist 𝒱<sub>b</sub>. "
            "<b>The plan in one line:</b> treat each of the four bodies as a frame at its centre of mass; "
            "for each one find its pose by the product of exponentials (step 3) and its body Jacobian "
            "J<sub>b,i</sub> (step 4: 3 rows, one column per joint). That gives four Jacobians, one per body, not one per joint. "
            "M, g and c are then each a sum of four terms, one per body. "
            "Do it on paper first; the lab splits every step into sub-steps and computes each number at the posture you set."))
        e = Card("the recipe, in the Kinematics notation")
        e.add(math_label(r"\mathcal{S}_j=(\hat\omega,\,-\hat\omega\times q_j),\qquad "
                         r"T_{si}(q)=e^{[\mathcal{S}_0]q_0}\cdots e^{[\mathcal{S}_i]q_i}M_i", 15))
        e.add(math_label(r"J_{b,i}=[\mathrm{Ad}_{T_{is}}]\,J_{s,i},\qquad "
                         r"\mathcal{V}_{b,i}=J_{b,i}\,\dot q,\qquad "
                         r"\mathcal{G}_i=\mathrm{diag}(I_i,\,m_i,\,m_i)", 15))
        e.add(math_label(r"M(q)=\sum_i J_{b,i}^T\mathcal{G}_iJ_{b,i},\qquad "
                         r"g(q)=-\sum_i J_{b,i}^T\mathcal{F}_{g,i}", 15))
        e.add(math_label(r"c(q,\dot q)=\sum_i J_{b,i}^T\big(\mathcal{G}_i\dot{\mathcal{V}}_{b,i}"
                         r"-[\mathrm{ad}_{\mathcal{V}_{b,i}}]^T\mathcal{G}_i\mathcal{V}_{b,i}\big)\big|_{\ddot q=0}"
                         r"\quad\Rightarrow\quad\tau=M(q)\ddot q+c(q,\dot q)+g(q)", 15))
        e.add(body(
            "<b>Frame and signs</b> (the G1's own): {s} at the ankle, x forward, y left, z up. Every joint "
            "turns about ŷ, positive when the top of the link moves forward. In the plane a twist has "
            "three entries that can be nonzero, so <b>𝒱 = (ω<sub>y</sub>, v<sub>x</sub>, v<sub>z</sub>)</b> "
            "and a pitch joint at height h has 𝒮 = (1, −h, 0), the planar part of (0,1,0, −h,0,0). "
            "Body i's COM frame {i} sits at its centre of mass and turns with it. The upper-arm and "
            "forearm frames are flipped by π at home, so the arms hang at q = 0.", dim=True))
        e.add(body(
            "<b>Why these three, and why in this order.</b> M multiplies q̈, g depends on q only, and c "
            "is quadratic in q̇. Each one is a sum over the four bodies of J<sub>b,i</sub>ᵀ times a wrench "
            "on body i: the inertial wrench 𝒢𝒱̇, the weight, and the velocity-product wrench. That is the "
            "statics rule τ = Jᵀ𝓕 applied to every body, with Newton–Euler giving each wrench.", dim=True))
        self.add(e)
        self.lab("upper_body_lagrange.html", "Lab · the simplified G1 in 3-D: screw axes → J_b → M, g, c → τ", 1060)

        w = ub.worked(ub.PLANES["sagittal"], self.Q, self.QD)
        m = ub.PLANES["sagittal"]
        p2, c3, p1 = w["p"][2], w["c"][3], w["p"][1]
        ph = w["phi"][3]
        d = c3 - p1
        sw = np.array([d[1], -d[0]])                                   # ŷ × (c₃ − p₁), in (x, z)
        Rt = np.array([[math.cos(ph), -math.sin(ph)], [math.sin(ph), math.cos(ph)]])
        jb = Rt @ sw
        k = Card("worked numbers at one posture (compute first, then open)")
        k.add(body(f"q = {np.round(np.degrees(self.Q), 1).tolist()} degrees, "
                   f"q̇ = {self.QD.tolist()} rad/s. Set the sliders to these and the lab agrees to three decimals."))
        k.add(Reveal("", [
            ("Screw axis of the shoulder at home, and at this posture?",
             f"Home: the shoulder is at (0, 0, {m.links[0].L + m.links[1].L:.2f}), so 𝒮₂ = (1, "
             f"−{m.links[0].L + m.links[1].L:.2f}, 0). Now it sits at p₂ = ({p2[0]:.3f}, {p2[1]:.3f}), "
             f"so column 2 of J<sub>s</sub> is (1, −p<sub>z</sub>, p<sub>x</sub>) = "
             f"(1, {-p2[1]:.3f}, {p2[0]:.3f})."),
            ("Column 1 (waist) of the forearm's body Jacobian J<sub>b,3</sub>?",
             f"Arm d = c₃ − p₁ = ({d[0]:.3f}, {d[1]:.3f}); ŷ × d = (d<sub>z</sub>, −d<sub>x</sub>) = "
             f"({sw[0]:.3f}, {sw[1]:.3f}); rotate into {{3}} with R₃ᵀ, φ₃ = {math.degrees(ph):.1f}°: "
             f"column = (1, {jb[0]:.3f}, {jb[1]:.3f})."),
            ("M₀₀ and M₀₁?",
             f"M₀₀ = {w['M'][0, 0]:.3f}, M₀₁ = {w['M'][0, 1]:.3f} kg·m². Each body adds "
             f"J<sub>b,i</sub>ᵀ𝒢<sub>i</sub>J<sub>b,i</sub>; entry (0, 1) of that is I<sub>i</sub> + m<sub>i</sub> "
             f"(arm₀·arm₁) for the torso and arms. Full matrix:<br>{mat_html(w['M'])}"),
            ("The gravity vector g?",
             f"g = {np.round(w['g'], 2).tolist()} N·m. g₀ = −{m.m_tot:.0f} × 9.81 × x<sub>c</sub> = "
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
            "the only handle the upper body has. g₀ is gravity's torque about the ankle, −m g x<sub>c</sub>, "
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
            "Compare A with M = Σ J<sub>b,i</sub>ᵀ𝒢<sub>i</sub>J<sub>b,i</sub> (page 167): "
            "<b>the momentum matrix is the mass matrix with the outer Jᵀ stripped off</b>. Same Jacobians, same "
            "masses and inertias; M lands in joint space, A lands in physical momentum. A about the COM is "
            "the <i>centroidal momentum matrix</i> of the humanoid literature. At q = 0 the H row of A<sub>O</sub> "
            "equals row 0 of M: the ankle's share of the inertia is the momentum about the ankle per unit "
            "joint rate."))
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
        sim.add(body("The same run, animated, with every slider live, is the lab on page 169.", dim=True))
        self.add(sim)
        self.add(plain(
            "<b>What the arms can and cannot do.</b> They cannot change H<sub>O</sub> at all. They can "
            "(1) take forward momentum so that the legs lose it, which stops the lean from growing for a "
            "moment, and (2) move the COM, which changes the sign of gravity's moment. Both are bounded: "
            "the arms reach their range and the torso its stop, and then the momentum comes back. The ankle "
            "torque and gravity must do the rest within that window. Page 169 measures the window."))
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
            "sole can do. Everything on this page was simulated with the model of page 167 and is tested. "
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
        laws.add(body("clipped to the limits. It discovers a hip strategy by itself: while the push is on, the waist "
                      "throws the torso back behind vertical (the legs pay with a faster lean), then reverses and brakes "
                      "it, and that reaction holds the legs back while the ankle is saturated. Page 170 opens it step by step."))
        laws.add(body("<b>2 · The counterweight (looks right, fails).</b> Put the whole-body COM behind the "
                      "ankle in proportion to the lean, through a virtual spring on the upper body's COM and "
                      "page 145's Jᵀ:"))
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
                 "that moving the torso back pushes the legs forward. It moves the torso back early, while the ankle "
                 "still has torque in hand, and reverses the waist torque when the ankle saturates (page 170)."),
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
# 170
# ==========================================================================

def lqr_numbers():
    """Everything page 170 quotes about the LQR design at standing, computed, not typed."""
    m, g = ub.PLANES["sagittal"], ub.Gains()
    K, free, A, B, poles = ub.lqr_gain(m, g, [1, 2, 3])
    k = m.core(np.zeros(4))
    eps = 1e-6
    G = np.array([(m.core(eps * e).g - m.core(-eps * e).g) / (2 * eps) for e in np.eye(4)]).T
    qmax = [g.lean_max] + [g.posture_max] * 3
    vmax = [g.lean_rate_max] + [g.posture_rate_max] * 3
    Q = np.diag([1 / v ** 2 for v in qmax + vmax])
    R = np.diag([1 / float(g.tau_max[j]) ** 2 for j in (1, 2, 3)])
    Hm = np.block([[A, -B @ np.linalg.inv(R) @ B.T], [-Q, -A.T]])
    w, V = np.linalg.eig(Hm)
    Vs = V[:, w.real < 0]
    P = np.real(Vs[8:] @ np.linalg.inv(Vs[:8]))
    return dict(m=m, g=g, K=K, A=A, B=B, M=k.M, Minv=np.linalg.inv(k.M), G=G, Q=Q, R=R, P=P,
                poles=np.sort_complex(poles), open=np.sort_complex(np.linalg.eigvals(A)))


# a 70 N x 0.1 s push at the shoulder from t = 0.2 s, read off ub.simulate (tests/test_upperbody.py checks them)
LQR_STORY = dict(peak=6.2, t_peak=0.52, locked_peak=7.9, sat=(0.30, 0.50), flip=0.32,
                 waist_terms_025=(-2.6, 3.9, 1.1, 0.1, -98.3, 61.2, 13.1, 1.0), waist_025=-20.5,
                 qdd0_025=(-2.80, 14.03, -0.21, -0.07, 0.44, -2.75, 8.64),
                 qdd0_040=(-5.95, -3.54, 0.11, 0.07, 5.49, 0.0, -3.84), torso_back=-7.3)


class UpperBodyLQRPage(BalancePage):
    TITLE = "LQR, Opened Up: How −Kx Becomes a Torque at Each Joint"
    SUBTITLE = ("Page 169 said: linearise, choose Q and R by Bryson's rule, apply τ = −Kx. Here every one of "
                "those words is opened, with the G1's own numbers, and one push is followed from the sensors "
                "to the motion of every link.")
    NOTES = "G1 · LQR"

    def __init__(self, parent=None):
        super().__init__(parent)
        n = lqr_numbers()
        K, A, B, M, G, P = n["K"], n["A"], n["B"], n["M"], n["G"], n["P"]
        m, g = n["m"], n["g"]
        lim0 = m.tau_ankle_max()
        st = LQR_STORY
        XS = ["q₀", "q₁", "q₂", "q₃", "q̇₀", "q̇₁", "q̇₂", "q̇₃"]
        self.add(start_here(
            "<b>The question.</b> The controller of page 169 is one line, τ<sub>u</sub> = −K x. Where do the "
            "24 numbers in K come from, what does each one mean, and how does a number in K end up as a turn "
            "of the legs? This page answers in seven stages, all on the simplified G1 of page 167 (ankle, "
            "waist, shoulder, elbow in the sagittal plane), and then follows the 70 N push of page 169 "
            "through them. Read a stage, then open the same stage in the lab."))

        a = Card("the pipeline: what runs offline and what runs every millisecond")
        a.add(_table(["stage", "in", "out", "when"], [
            ["1 · state", "joint encoders", "x = (q, q̇): 8 numbers", "every 1 ms"],
            ["2 · machine", "page 167's M, c, g and the ankle spring", "ẋ = f(x, u)", "once, on paper"],
            ["3 · linearise", "f near standing, central differences", "A (8×8), B (8×3)", "offline, once"],
            ["4 · prices", "Bryson's rule: largest acceptable values", "Q (8×8), R (3×3)", "offline, your choice"],
            ["5 · Riccati", "A, B, Q, R", "P (8×8), K = R⁻¹BᵀP (3×8)", "offline, once"],
            ["6 · the law", "x and K", "u = −Kx, clipped: 3 torques", "every 1 ms: 24 multiply-adds"],
            ["7 · physics", "τ (3 motors + the foot), the push", "q̈ = M⁻¹(τ − c − g + Jᵀ F)", "the robot does it"],
        ]))
        a.add(body("Online, the controller is a 3×8 matrix times a vector and a clip. Everything it knows about "
                   "masses, reactions, gravity and what matters is baked into K before the robot moves.", dim=True))
        self.add(a)

        s1 = Card("stages 1 and 2 · the state, the inputs, and the machine")
        s1.add(math_label(r"x=\begin{bmatrix}q_0&q_1&q_2&q_3&\dot q_0&\dot q_1&\dot q_2&\dot q_3\end{bmatrix}^T,\qquad "
                          r"u=\begin{bmatrix}\tau_1&\tau_2&\tau_3\end{bmatrix}^T", 15))
        s1.add(math_label(r"\dot x=f(x,u)=\begin{bmatrix}\dot q\\ M(q)^{-1}\big(\tau-c(q,\dot q)-g(q)\big)\end{bmatrix},\qquad "
                          r"\tau=\begin{bmatrix}-k_a q_0-b_a\dot q_0\\ u\end{bmatrix}", 15))
        s1.add(body(
            "q₀ is the lean of the legs on the foot (+ forward), q₁ the torso relative to the legs, q₂ the arms "
            "relative to the torso (+ swings them back), q₃ the forearms. <b>Three inputs, four joints:</b> the "
            "ankle is not a motor the law commands. It is what the sole can do, modelled as a spring-damper "
            f"(k<sub>a</sub> = {g.ankle_k:.0f} N·m/rad, b<sub>a</sub> = {g.ankle_b:.0f}), and it is put <i>inside</i> "
            f"f so the design knows it is there. In the simulation it is also clipped at ±{lim0:.1f} N·m "
            "= m g × half the foot. The linear design does not know that clip; remember it, it matters later."))
        self.add(s1)

        s3 = Card("stage 3 · linearise: what A and B say")
        s3.add(body(
            "Page 19's recipe: perturb one entry of x (or u) by ±ε, call f, difference. Column i of A is "
            "(f(εeᵢ, 0) − f(−εeᵢ, 0)) / 2ε. At standing it can also be written by hand, because there "
            "τ − c − g = 0 (so the ∂M/∂q terms vanish) and c is quadratic in q̇ (so its derivative at q̇ = 0 is zero):"))
        s3.add(math_label(r"A=\begin{bmatrix}0&I\\-M^{-1}(G+K_a)&-M^{-1}D_a\end{bmatrix},\quad "
                          r"B=\begin{bmatrix}0\\M^{-1}S_u\end{bmatrix},\quad G=\frac{\partial g}{\partial q}\Big|_0,\ "
                          r"K_a=\mathrm{diag}(k_a,0,0,0),\ D_a=\mathrm{diag}(b_a,0,0,0)", 14))
        s3.add(body(f"At standing (rows and columns: ankle, waist, shoulder, elbow) M is<br>{mat_html(M, 3)}"
                    f"G (gravity's stiffness, N·m/rad) is<br>{mat_html(G, 1)}"
                    f"and the lower-left block of A, −M⁻¹(G + K<sub>a</sub>), in rad/s² per rad:<br>{mat_html(A[4:, :4], 1)}"))
        s3.add(body(
            f"<b>Read G₀₀ = {G[0, 0]:.1f}.</b> Lean the rigid robot 1 rad and the COM moves {-G[0, 0] / (m.m_tot * m.g):.3f} m "
            f"forward, so gravity's moment grows by m g × that = {-G[0, 0]:.1f} N·m/rad. The ankle spring's {g.ankle_k:.0f} "
            f"is larger, so a <i>rigid</i> robot on this spring is stable for small leans. Not for large ones: the spring "
            f"saturates at {lim0:.1f} / {g.ankle_k:.0f} = {lim0 / g.ankle_k:.3f} rad, and gravity's moment reaches the foot "
            f"limit at {lim0 / -G[0, 0]:.3f} rad ({math.degrees(lim0 / -G[0, 0]):.1f}°)."))
        bc = B[4:]
        s3.add(_table(["1 N·m at the…", "q̈₀ legs", "q̈₁ torso", "q̈₂ arms", "q̈₃ forearms"],
                      [[nm] + [f"{bc[r, c]:+.3f}" for r in range(4)]
                       for c, nm in enumerate(["waist", "shoulder", "elbow"])]))
        s3.add(body(
            "<b>B is where the torque goes.</b> Each column is M⁻¹ times one unit generalised force: a motor "
            "between two links pushes the outer one forward and the inner one back, and M⁻¹ spreads that to "
            f"every joint. The number that decides everything is the first entry of the waist column: <b>+1 N·m at "
            f"the waist gives the lean {bc[0, 0]:+.3f} rad/s²</b>. Turning the torso forward pushes the legs back; "
            "turning it back pushes them forward. The upper body has no other door to the lean except moving the COM."))
        ol = n["open"]
        s3.add(body(
            "Open-loop poles (u = 0, motors off): "
            + ", ".join(f"{z.real:+.2f}{'' if abs(z.imag) < 1e-6 else f' ± {abs(z.imag):.2f}j'}"
                        for z in ol if z.imag >= -1e-9)
            + f". The one at {max(ol.real):+.2f} /s is the torso falling over the waist with no motor to hold it: "
            "it is the upper body, not the ankle, that is unstable here.", dim=True))
        self.add(s3)

        s4 = Card("stage 4 · Bryson's rule: the price list")
        s4.add(math_label(r"J=\int_0^\infty\big(x^TQx+u^TRu\big)\,dt,\qquad Q_{ii}=\frac{1}{x_{i,\max}^2},\quad "
                          r"R_{jj}=\frac{1}{\tau_{j,\max}^2}", 15))
        lims = [g.lean_max] + [g.posture_max] * 3 + [g.lean_rate_max] + [g.posture_rate_max] * 3
        s4.add(_table(["variable", "largest acceptable", "weight"],
                      [[XS[i] + (" (lean)" if i == 0 else " (lean rate)" if i == 4 else ""),
                        f"{v:g} {'rad' if i < 4 else 'rad/s'}", f"{1 / v ** 2:.3g}"] for i, v in enumerate(lims)]
                      + [[f"τ {nm}", f"{g.tau_max[j]:.0f} N·m", f"{1 / g.tau_max[j] ** 2:.2e}"]
                         for j, nm in ((1, "waist"), (2, "shoulder"), (3, "elbow"))]))
        s4.add(body(
            "Each term costs 1 when its variable sits at its limit, so the table is a trade: 0.1 rad of lean "
            "costs the same as 0.5 rad of torso bend and as the waist's full 88 N·m. The lean is expensive and "
            "the posture is cheap, which is what licenses the law to spend the upper body. The 0.1 rad was "
            f"picked near the ankle's saturation, {lim0 / g.ankle_k:.3f} rad."))
        s4.add(body(
            "<b>A warning you can test in the lab.</b> Asking for less lean (0.05 rad) makes the peak lean "
            "<i>worse</i>, about 7.3° instead of 6.2°; letting the torso move less (posture 0.2 rad) makes it "
            "better, about 5.7°. K is optimal for the linear model, and the linear model has no foot limit. "
            "Bryson gives a sensible start; the final prices are tuned on the nonlinear simulation.", dim=True))
        self.add(s4)

        s5 = Card("stage 5 · the Riccati equation, P and K")
        s5.add(math_label(r"A^TP+PA-PBR^{-1}B^TP+Q=0,\qquad K=R^{-1}B^TP,\qquad J_{\min}(x_0)=x_0^TPx_0", 15))
        s5.add(body(
            "P is the price of starting at x₀: the cheapest possible future cost from there is x₀ᵀPx₀. "
            f"A lean of 0.1 rad alone costs P₀₀ × 0.01 = {P[0, 0] * 0.01:.2f}. K = R⁻¹BᵀP says how fast that "
            "price falls per N·m of each motor: B maps torque to motion, P prices the motion, R⁻¹ converts the "
            "price back into a torque worth spending. ctrlcore/linear.py solves it through the stable eigenvectors "
            "of the Hamiltonian matrix; the lab iterates the Riccati recursion instead."))
        s5.add(_table(["joint"] + XS, [[nm] + [f"{v:+.1f}" for v in K[r]]
                                       for r, nm in enumerate(["waist", "shoulder", "elbow"])]))
        s5.add(body(
            f"<b>Read the waist row.</b> The gains on q₀ ({K[0, 0]:.0f}) and q₁ ({K[0, 1]:.0f}) are almost equal, so "
            f"τ<sub>waist</sub> ≈ −{K[0, 0]:.0f}(q₀ + q₁) − {K[0, 4]:.0f} q̇₀ − {K[0, 5]:.0f} q̇₁ + small terms. q₀ + q₁ "
            "is the torso's angle <i>to the vertical</i>. So the waist is a stiff spring holding the torso upright in "
            "the world, plus a strong damper on the lean rate. When the legs lean forward, holding the torso upright "
            "means bending it back relative to them, a negative waist torque, and by B a forward push on the legs."))
        s5.add(body(
            f"<b>The arm rows</b> are a third of that: a forward lean gives a {'positive' if K[1, 0] < 0 else 'negative'} "
            f"shoulder torque ({-K[1, 0]:+.0f} N·m per rad), which swings the arms back, and each arm joint's own angle "
            f"pulls it home ({K[1, 2]:.0f}, {K[2, 3]:.0f}). With these prices the waist does most of the work."))
        pl = n["poles"]
        s5.add(body(
            "Closed-loop poles: " + ", ".join(f"{z.real:.1f}{'' if abs(z.imag) < 1e-6 else f' ± {abs(z.imag):.1f}j'}"
                                               for z in pl if z.imag >= -1e-9)
            + f". All in the left half plane. The slowest, {pl.real.max():.2f} /s, is the lean and torso drifting "
            f"home over about {1 / -pl.real.max():.2f} s; the fastest is the light forearm snapped to its target.", dim=True))
        self.add(s5)

        s6 = Card("stage 6 · one torque, term by term (t = 0.25 s, mid-push)")
        s6.add(math_label(r"\tau_{\mathrm{waist}}=-\sum_{i=1}^{8}K_{\mathrm{waist},i}\,x_i,\qquad "
                          r"\tau_j\leftarrow\mathrm{clip}(\tau_j,\,\pm\tau_{j,\max})", 15))
        s6.add(_table(["term"] + XS + ["sum"],
                      [["−K·x (N·m)"] + [f"{v:+.1f}" for v in st["waist_terms_025"]] + [f"<b>{st['waist_025']:+.1f}</b>"]]))
        s6.add(body(
            "Fifty milliseconds into the push the angles are still under a degree, so their terms are small. The "
            "rates carry it: the lean rate (0.40 rad/s) asks for −98 N·m, the torso already swinging back "
            "(−0.91 rad/s) asks for +61, the arms add +13. Net −20.5 N·m, inside the 88 N·m limit, so no clip. "
            "Shoulder and elbow come out at −0.8 and −0.2 N·m. The ankle, not commanded, gives −14.6 N·m from its spring."))
        self.add(s6)

        s7 = Card("stage 7 · where the torque goes: every torque moves every joint")
        s7.add(math_label(r"\ddot q=M(q)^{-1}\big(\tau-c-g+J_{\mathrm{sh}}^TF_{\mathrm{push}}\big),\qquad "
                          r"\ddot q_0=\sum_j (M^{-1})_{0j}\,(\mathrm{force})_j", 15))
        s7.add(body(
            "A motor torque τⱼ acts on two links, +τⱼ on the outer one and −τⱼ on the inner one. In joint "
            "coordinates that pair is the single entry τⱼ, and row 0 of M⁻¹ says how much of it reaches the lean. "
            "Split the lean's acceleration into one piece per force (rad/s²):"))
        h = ["", "ankle τ", "waist τ", "shoulder τ", "elbow τ", "gravity", "push", "q̈₀"]
        s7.add(_table(h, [["t = 0.25 s"] + [f"{v:+.2f}" for v in st["qdd0_025"]],
                          ["t = 0.40 s"] + [f"{v:+.2f}" for v in st["qdd0_040"]]]))
        s7.add(body(
            "<b>At 0.25 s</b> the waist's −20.5 N·m is the biggest thing pushing the lean <i>forward</i> (+14.0). "
            "The push itself is negative on the lean: on a limp chain a shove at the shoulder mostly folds the torso "
            "forward and tips the legs back, and it is the waist resisting that fold that passes the push down. "
            "<b>At 0.40 s</b> the waist torque has turned positive (+5.8 N·m) and its share is −3.5: it brakes the "
            f"torso's backward swing, and the reaction pulls the legs back while the ankle is stuck at −{lim0:.1f}."))
        s7.add(math_label(r"\frac{dH_O}{dt}=\tau_{\mathrm{ankle}}+m g\,x_c+M_{\mathrm{push}}", 15))
        s7.add(body(
            "The momentum ledger of page 168 has no waist, shoulder or elbow term. Internal torques only move H "
            "between links and move x<sub>c</sub>, which changes gravity's term. That is the whole of what the "
            "upper body can do, and the LQR does both.", dim=True))
        self.add(s7)

        s8 = Card("the push, phase by phase: pay early, collect late")
        s8.add(_table(["time", "what happens"], [
            ["0.20 s", "70 N at the shoulder for 0.1 s: 76 N·m about the ankle. x = 0, so u = 0."],
            ["0.205 s", "The push folds the torso forward first; the waist answers through its q̇₁ gain."],
            ["0.25 s", "Waist −20.5 N·m, mostly from the lean rate. The torso goes back, the legs are pushed forward: "
                       "the lean grows <i>faster</i> than with everything locked. This is the price."],
            [f"{st['sat'][0]:.2f} s", f"The ankle saturates at −{lim0:.1f} N·m: the centre of pressure is at the toes."],
            [f"{st['flip']:.2f} s", "The waist torque flips positive and brakes the torso; its reaction pulls the legs back."],
            ["0.40 s", f"The torso is about {-st['torso_back']:.0f}° behind vertical: the COM is held back."],
            [f"{st['sat'][1]:.2f} s", "The ankle leaves saturation: the brake has nearly stopped the lean."],
            [f"{st['t_peak']:.2f} s", f"Peak lean {st['peak']:.1f}° with the COM at 0.049 m, inside the 0.10 m foot. "
                                     f"Everything locked: {st['locked_peak']:.1f}°, COM about 0.09 m. Then the spring "
                                     "and the posture gains bring everything home."],
        ]))
        s8.add(body(
            "Nobody wrote \"bend back, then brake\". It falls out of three facts the design was given: B says a "
            "waist torque pushes the legs the other way, A says gravity grows with x<sub>c</sub>, and Q says lean "
            "is expensive and posture is cheap. The counterweight law of page 169 has the first half (torso back) "
            "and not the second (the timed brake), which is why it loses."))
        self.add(s8)

        self.lab("lqr_torque_flow.html", "Lab · LQR opened up: state → A, B → Q, R → K → each joint's torque → the motion", 1180)

        self.add(two_col(
            Reveal("Say it out loud", [
                ("What does the controller compute every millisecond?",
                 "Eight numbers in, three torques out: u = −Kx is 24 multiply-adds, then a clip to each motor's "
                 "limit. A, B, Q, R, P and the Riccati equation are all offline."),
                ("Why does the waist push the legs forward at first, and why is that acceptable?",
                 "Holding the torso upright while the legs lean means bending it back, and the reaction is forward "
                 "on the legs. It is paid while the ankle still has torque in hand; once the ankle saturates the waist "
                 "reverses and the reaction becomes the brake the ankle can no longer give."),
                ("Why does asking for less lean give more lean?",
                 "Because K is optimal for a model with no foot limit. A higher lean price makes the waist react "
                 "harder and earlier, which kicks the legs more while the push is on; the real ankle saturates and "
                 "cannot absorb the extra."),
                ("If the ankle were a motor you could command, what changes?",
                 "u gains an entry and B a column, M⁻¹e₀, and K a row. The foot limit still bounds that torque, so "
                 "the design would need the clip, or a constraint, to know about it: the problem the momentum QP "
                 "of page 169 tries to solve."),
            ]),
            Choice("Quick check", "The waist gains on q₀ and on q₁ are both about 300 N·m/rad. What does the waist mostly regulate?",
                   [("the torso's angle to the vertical, q₀ + q₁", True,
                     "−300 q₀ − 295 q₁ ≈ −300 (q₀ + q₁): a spring that holds the torso upright in the world."),
                    ("the waist joint angle q₁", False, "Then the q₀ gain would be near zero."),
                    ("the lean q₀", False, "Then the q₁ gain would be near zero."),
                    ("the whole-body COM", False,
                     "The COM weights q₀ about seven times more than q₁ (0.66 m against 0.09 m per rad).")])))
        self.add(interview(
            "<b>\"Walk me through LQR for humanoid push recovery.\"</b> State: joint angles and rates. Model: "
            "M q̈ + c + g = τ with the passive ankle inside, linearised at standing by finite differences, so "
            "A = [0 I; −M⁻¹(G + K<sub>a</sub>) −M⁻¹D<sub>a</sub>] and B = [0; M⁻¹S]. Prices by Bryson's rule. Solve the "
            "CARE, K = R⁻¹BᵀP, run u = −Kx at 1 kHz with clipping. Then the honest part: the design ignores the foot "
            "limit, so verify on the nonlinear model with saturation, and tune Q and R there."))
        self.finish()


# ==========================================================================
# 171
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
            "and the structure you learnt in pages 151 to 165 is the design."))
        ph = Card("phase 1 · Python + MuJoCo, in checkable steps")
        ph.add(_table(["step", "do", "check against the plane"],
                      [["1", "Load unitree_g1 from mujoco_menagerie, reset to the standing keyframe, weld the "
                             "pelvis or fix the feet", "the robot stands still with zero ctrl plus gravity compensation"],
                       ["2", "mj_fullM; take the sagittal rows and columns", "M₀₀, M₀₁ within 30 percent of page "
                             "166 (one leg and one arm per side: halve the planar arm masses)"],
                       ["3", "qfrc_bias with qvel = 0", "the gravity vector g; a forward lean gives a negative ankle entry"],
                       ["4", "mj_subtreeVel; subtree_angmom and subtree_com of the pelvis", "H about the COM equals "
                             "A q̇ from page 168, at the same joint rates"],
                       ["5", "Linearise by finite differences of mj_step (mjd_transitionFD does it for you), "
                             "design K with the same Bryson weights", "the gains have the same signs as the planar K: "
                             "a forward lean gives a backward waist torque (page 170)"],
                       ["6", "Apply the push with xfrc_applied; log lean, link momenta, torques", "the plots of "
                             "page 169: momentum moves to the arms, then returns; find the push at which it falls"],
                       ["7", "Free the base (feet on the ground through contact), keep the legs' joints under a stiff "
                             "PD", "the ankle saturation now happens by itself: the heel lifts"]]))
        self.add(ph)
        code = Card("the checking script, as far as this tutor can take it")
        code.add(CodePane(MUJOCO_CHECK.strip("\n")))
        code.add(body("Names come from the menagerie MJCF and may differ between the 23- and 29-dof files; "
                      "<code>mujoco</code> is not installed here, so this was not run. Treat it as a map, "
                      "not a result.", dim=True))
        self.add(code)
        cpp = Card("phase 2 · the C++ port, in the words of pages 151 to 165")
        cpp.add(body(
            "<b>One class per invariant.</b> <code>PlanarModel</code> owns the link parameters and promises "
            "that M is symmetric positive definite for every q (that is a unit test, page 157). "
            "<code>BalanceController</code> owns K, the limits and the ankle model, and promises that every "
            "torque it returns is inside the limits. <code>Scheduler</code> runs the controller at 1 kHz and "
            "the logger at 50 Hz with a triple buffer between them (page 164).<br><br>"
            "<b>Fixed-size Eigen</b> for everything: <code>Eigen::Matrix&lt;double,4,4&gt;</code> for M, "
            "<code>Matrix&lt;double,3,8&gt;</code> for K. No allocation in <code>update()</code>; design K in "
            "<code>configure()</code> (page 161).<br><br>"
            "<b>The port is the test.</b> Compile the C++ model, feed it the posture of page 167, and compare "
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
             "same foot. One number per configuration, like the table on page 169."),
            ("Where does the project touch your beam-walking paper?",
             "The frontal-plane chain is the mediolateral problem, and the law on momentum about the stance "
             "foot is the same quantity your exoskeleton regulated. The G1 just has to do it with its own "
             "torso instead of a motor at the hip."),
        ]))
        self.finish()


BALANCE_PAGES = [UpperBodyMachinePage, UpperBodyDerivePage, UpperBodyMomentumPage,
                 UpperBodyRecoveryPage, UpperBodyLQRPage, UpperBodyProjectPage]
