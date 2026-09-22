"""
State feedback and LQR -- the two pages that replace "tune it" with "solve
it", built from nothing on a mass-spring-damper and then on a SEA.

  1  State Feedback & Pole Placement   what a state IS, what u = -Kx does,
                                       and why on a 2-state plant it is
                                       literally PD control
  2  LQR                               choosing the poles by naming a price,
                                       what Q and R and P actually are, and
                                       the closed-form ancestor of every
                                       value function in the RL half

These come after the frequency-domain pages on purpose. Everything up to
here shaped ONE transfer function from ONE input to ONE output. A robot has
six actuators whose dynamics are coupled through an inertia matrix, and the
moment that is true, a loop-at-a-time design is not merely inconvenient --
it is describing a system that does not exist.
"""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QComboBox, QLabel, QPushButton, QHBoxLayout
from ctrlcore.pole_lesson import second_order_poles, regulator_response

from ctrlcore.linear import StateSpace, lqr, place_poles, settling_time
from ctrlcore.multibody import (
    bryson,
    ctrb_gramian_svd,
    controllable,
    lqr_design,
    msd_natural,
    msd_ss,
    observable,
    sea_modes,
    sea_output,
    sea_ss,
    simulate_feedback,
)
from .. import theme
from ..widgets import (
    Card,
    MplCanvas,
    Stat,
    body,
    callout,
    hline,
    labelled,
    math_label,
    stat_row,
    title,
)
from .base import Page
from .linsys import _splane
from .motors import slider, slider_row

SECTION = "Controller Design"


def _matrix_html(M, name, fmt="{:+.2f}", colour=None):
    """A matrix as an HTML table -- easier to read than a text dump."""
    M = np.atleast_2d(np.asarray(M, dtype=float))
    col = colour or theme.ACCENT
    cells = ""
    for r in range(M.shape[0]):
        cells += "<tr>"
        for c in range(M.shape[1]):
            cells += (f"<td align='right' style='padding:2px 9px;'>"
                      f"<span style='font-family:Segoe UI; font-size:13px;'>{fmt.format(M[r, c])}</span></td>")
        cells += "</tr>"
    return (f"<table cellspacing='0'><tr><td valign='middle'>"
            f"<b style='color:{col}'>{name}</b> &nbsp;=&nbsp;</td>"
            f"<td><table cellspacing='0' style='border-left:2px solid {col};"
            f"border-right:2px solid {col};'>{cells}</table></td></tr></table>")


# ==========================================================================
# PAGE -- state feedback and pole placement
# ==========================================================================

class StateFeedbackPage(Page):
    TITLE = "State Feedback & Pole Placement"
    SUBTITLE = ("Choose the response, solve for the gains, then check force limits, "
                "available measurements and the target equilibrium.")
    SECTION = SECTION
    NOTES = "design"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._msd_timer = QTimer(self)
        self._sea_timer = QTimer(self)
        for timer, callback in ((self._msd_timer, self._redraw_msd), (self._sea_timer, self._redraw_sea)):
            timer.setSingleShot(True)
            timer.setInterval(120)
            timer.timeout.connect(callback)
        self.add(callout(
            '<b>The point of this page:</b> choose a response, solve for the gains, then check what the actuator must deliver. '
            'Writing ẋ = Ax + Bu describes the plant; applying u = −Kx changes it to ẋ = (A−BK)x. '
            'Matching the second-order polynomial gives k₁ and k₂ for a controllable two-state model. '
            'It does not guarantee that a real motor can supply the resulting force, or that every state is measured. '
            '<br><br><b>Read the labs as two questions:</b> (1) Does the chosen response fit the force limit? '
            '(2) How does the same method work when a spring adds two more states? Both labs return an initial displacement to zero; neither is a reference-tracking test.', 'key'))

        # ==============================================================
        # 1. what is a state
        # ==============================================================
        self.add(callout(
            "<b>Start with the word, because everything else follows from "
            "it.</b> The <b>state</b> of a system is the smallest set of "
            "numbers such that, if you know them now and you know every "
            "future input, you can predict the entire future. Nothing about "
            "the past adds anything once you have them. The state is "
            "<i>exactly the system's memory</i>, written down.", "key"))

        wh = Card("why position alone is not enough — the whole idea in one "
                  "example")
        wh.add(body(
            "Take a mass on a spring. I tell you it is 3 cm to the right of "
            "rest. Where will it be in half a second?<br><br>"
            "<b>You cannot answer.</b> Not because the question is unfair, "
            "but because the information is genuinely missing: the mass could "
            "be moving right at 2 m/s, moving left at 2 m/s, or momentarily "
            "at rest, and those three give completely different futures. Add "
            "one number — the velocity — and the question becomes answerable "
            "and stays answerable forever. Two numbers is the smallest set "
            "that works, so the state is two-dimensional."))
        wh.add(callout(
            "<b>And now a fact you have already met, wearing a different "
            "hat.</b> The number of states equals the number of independent "
            "<b>energy stores</b>: a mass stores kinetic energy (velocity), a "
            "spring stores potential energy (position). It also equals the "
            "<b>order</b> of the differential equation, and it also equals "
            "the <b>number of poles</b>. Those are not three coincidences — "
            "they are one fact counted three ways. A second-order system has "
            "two poles because it has two states because it has two places to "
            "put energy.", "key"))
        wh.add(body(
            "So for the machines in this tutor:<br><br>"
            "&nbsp;&nbsp;• one rigid joint → <b>2 states</b> [θ, θ̇]<br>"
            "&nbsp;&nbsp;• a series elastic actuator → <b>4 states</b> "
            "[θ<sub>m</sub>, θ̇<sub>m</sub>, θ<sub>l</sub>, θ̇<sub>l</sub>] — "
            "motor and load can move independently, so each needs its own "
            "pair<br>"
            "&nbsp;&nbsp;• a two-link arm → <b>4 states</b> [q₁, q₂, q̇₁, q̇₂]"
            "<br>"
            "&nbsp;&nbsp;• a trunkless biped, 6 joints → <b>12 states</b>, "
            "before you add the floating base<br><br>"
            "Notice the last one. Twelve poles. There is no version of "
            "\"sketch the root locus\" that survives twelve poles, and that "
            "is the practical reason this page exists.", dim=True))
        self.add(wh)

        # ==============================================================
        # 2. the four matrices
        # ==============================================================
        self.add(hline())
        self.add(title("From f = ma to ẋ = Ax + Bu, with nothing skipped"))

        sf = Card("the mass-spring-damper, converted line by line")
        sf.add(body("Newton, for a mass m on a spring k with damping b, "
                    "pushed by a force F:"))
        sf.add(math_label(r"m\,\ddot x + b\,\dot x + k\,x = F", 18))
        sf.add(body(
            "One second-order equation. The trick is to refuse to have a "
            "second derivative at all: <b>name the velocity</b>, and the one "
            "second-order equation becomes two first-order ones."))
        sf.add(math_label(r"x_1 = x, \qquad x_2 = \dot x", 17))
        sf.add(math_label(r"\dot x_1 = x_2 \qquad\qquad "
                          r"\dot x_2 = -\frac{k}{m}x_1 - \frac{b}{m}x_2 "
                          r"+ \frac{1}{m}F", 17))
        sf.add(body(
            "The first line is a definition — the derivative of position is "
            "velocity. The second line is Newton's law rearranged for "
            "acceleration. Stack them:"))
        sf.add(math_label(
            r"\underbrace{\begin{bmatrix}\dot x_1\\ \dot x_2\end{bmatrix}}"
            r"_{\dot x} = \underbrace{\begin{bmatrix}0 & 1\\ "
            r"-k/m & -b/m\end{bmatrix}}_{A}"
            r"\underbrace{\begin{bmatrix}x_1\\ x_2\end{bmatrix}}_{x} + "
            r"\underbrace{\begin{bmatrix}0\\ 1/m\end{bmatrix}}_{B} u", 18))
        sf.add(body(
            "<b>Nothing was approximated.</b> That matrix equation and the "
            "Newton equation above it contain exactly the same physics; only "
            "the bookkeeping changed. And the bookkeeping is what scales: the "
            "form ẋ = Ax + Bu is identical whether x has 2 entries or 40."))
        sf.add(body(
            "<table cellpadding='7'>"
            "<tr><td><b>Symbol</b></td><td><b>Shape</b></td>"
            "<td><b>What it is, physically</b></td></tr>"
            "<tr><td><b>A</b></td><td>n×n</td>"
            "<td>the system left alone. How the states feed each other with "
            "no input at all — inertia, stiffness, damping, coupling. "
            "<b>The eigenvalues of A are the poles.</b></td></tr>"
            "<tr><td><b>B</b></td><td>n×m</td>"
            "<td>where the actuators push. A row of zeros means that state "
            "cannot be driven directly — note that B's first row here IS "
            "zero, because a force does not move a position instantly, it "
            "moves a velocity.</td></tr>"
            "<tr><td><b>C</b></td><td>p×n</td>"
            "<td>what the sensors see. An encoder on the load is "
            "C = [0 0 1 0] — one row picking one state out of four.</td></tr>"
            "<tr><td><b>D</b></td><td>p×m</td>"
            "<td>input straight through to output with no dynamics. Almost "
            "always zero on a mechanical system, because nothing physical "
            "responds instantaneously.</td></tr>"
            "</table>"))
        self.add(sf)

        # ==============================================================
        # 3. u = -Kx
        # ==============================================================
        self.add(hline())
        self.add(title("u = −Kx, and the discovery that you have been doing "
                       "this all along"))

        law = Card("what the control law literally computes")
        law.add(math_label(r"u = -K x = -\begin{bmatrix}k_1 & k_2\end{bmatrix}"
                           r"\begin{bmatrix}x_1\\ x_2\end{bmatrix} "
                           r"= -k_1 x_1 - k_2 x_2", 18))
        law.add(body(
            "That is the entire algorithm. Multiply each state by a number "
            "and add them up. On the mass-spring-damper, x₁ is position error "
            "and x₂ is velocity, so"))
        law.add(math_label(r"u = -k_1\,(\text{position}) - k_2\,"
                           r"(\text{velocity})", 17))
        law.add(callout(
            "<b>That is a PD controller. Character for character.</b> "
            "k₁ is K<sub>p</sub> and k₂ is K<sub>d</sub>. State feedback on a "
            "two-state plant <i>is</i> PD control — not an analogy, the same "
            "arithmetic.<br><br>"
            "So what did you gain? <b>A method for choosing the numbers.</b> "
            "PID gives you three knobs and no procedure. State feedback gives "
            "you n knobs, n poles, and a closed-form map between them. And "
            "unlike PID, it does not stop working at four states — a SEA gets "
            "u = −k₁θ<sub>m</sub> − k₂θ̇<sub>m</sub> − k₃θ<sub>l</sub> − "
            "k₄θ̇<sub>l</sub>, which no amount of PID vocabulary describes.",
            "key"))
        law.add(body("Substitute the law into the plant and the loop closes "
                     "in one line:"))
        law.add(math_label(r"\dot x = Ax + Bu = Ax + B(-Kx) = (A - BK)\,x",
                           18))
        law.add(body(
            "<b>The closed-loop system is a system with matrix A − BK.</b> "
            "Its poles are the eigenvalues of A − BK. K appears inside that "
            "matrix, so choosing K <i>moves the eigenvalues</i> — and the "
            "design question becomes: which K puts them where I want?",
            dim=True))
        self.add(law)

        pp = Card("pole placement, worked by hand on this exact plant")
        pp.add(body(
            "Do it once with symbols and it stops being mysterious. Compute "
            "A − BK for the mass-spring-damper:"))
        pp.add(math_label(
            r"A - BK = \begin{bmatrix}0 & 1\\ "
            r"-\dfrac{k + k_1}{m} & -\dfrac{b + k_2}{m}\end{bmatrix}", 18))
        pp.add(body(
            "<b>Read that matrix before going on.</b> k₁ landed on top of the "
            "spring constant and k₂ landed on top of the damping. Your "
            "position gain <i>is</i> a virtual spring; your velocity gain "
            "<i>is</i> a virtual damper. This is the impedance-control page "
            "arriving from the algebra rather than from the physics."))
        pp.add(body("Its characteristic polynomial, and the one you want:"))
        pp.add(math_label(
            r"s^2 + \frac{b + k_2}{m}s + \frac{k + k_1}{m} "
            r"\;\;\overset{!}{=}\;\; s^2 + 2\zeta\omega_n s + \omega_n^2",
            18))
        pp.add(body("Match coefficients. Two equations, two unknowns, no "
                    "iteration:"))
        pp.add(math_label(r"\boxed{\;k_1 = m\,\omega_n^2 - k, \qquad "
                          r"k_2 = 2\zeta\omega_n m - b\;}", 18))
        pp.add(callout(
            "<b>That is pole placement.</b> You wrote down the response you "
            "want as a polynomial, wrote down the polynomial your gains "
            "produce, and set them equal. For n = 2 you can do it in your "
            "head. For n = 12 the same idea is <b>Ackermann's formula</b>, "
            "which is that comparison automated — and the code in "
            "<code>ctrlcore/linear.py</code> is four lines long.<br><br>"
            "Look at the boxed result once more: <b>k₁ = mω<sub>n</sub>² − k "
            "subtracts off the spring you already have.</b> The controller is "
            "not adding stiffness on top of physics — it is <i>replacing</i> "
            "the plant's stiffness with the one you asked for. If your model "
            "of k is wrong by 20%, your ω<sub>n</sub> is wrong by 20%, and "
            "that sensitivity is the honest cost of a model-based method.",
            "key"))
        self.add(pp)

        # ---- interactive 1: MSD ---------------------------------------
        i1 = Card("place the poles of a mass-spring-damper, and watch the "
                  "formula be right")
        i1.add(body(
            '<b>Purpose: separate “I can calculate these poles” from “my actuator can deliver this response.”</b> '
            'The mass starts 5 cm from zero, at rest. We are watching it return to zero, not follow a step command.<br><br>'
            '<b>Read left → right:</b> position compares controlled motion with the same plant without feedback; '
            'force shows what the controller actually delivers and its limit; the pole map shows the ideal unsaturated design.<br><br>'
            '<b>Try the three buttons in order.</b> At m = 5 kg, b = 0.6 and k = 20, '
            'ω_n = 4 and ζ = 0.9 give k₁ = 60, k₂ = 35.4 and an initial force of −3 N. '
            'Raising ω_n to 12 gives k₁ = 700, k₂ = 107.4 and −35 N initially: faster recovery requires more force. '
            'Keep that design and limit force to 5 N: the pole markers stay put, but the actual response changes.<br><br>'
            '<b>Then explore:</b> change mass while holding the requested response fixed. The gains are recalculated, so more mass '
            'requires more control effort to preserve that response. This differs from the earlier experiment with fixed gains. '
            'The top three sliders describe the plant, the next two the desired response, and the last the actuator. Release a slider to update.', dim=True))
        self.s_m = slider(1, 200, 50)            # x0.1 kg
        self.s_b = slider(0, 200, 6)             # x0.1
        self.s_k = slider(0, 800, 200)           # x0.1
        self.s_wn = slider(5, 400, 120)          # x0.1 rad/s
        self.s_z = slider(10, 200, 90)           # x0.01
        self.s_fmax = slider(5, 600, 600)        # N
        self.l_m, self.l_b, self.l_k = QLabel(), QLabel(), QLabel()
        self.l_wn, self.l_z, self.l_fmax = QLabel(), QLabel(), QLabel()
        i1.add_layout(slider_row("mass m (×0.1 kg)", self.s_m, self.l_m))
        i1.add_layout(slider_row("damping b (×0.1)", self.s_b, self.l_b))
        i1.add_layout(slider_row("spring k (×0.1)", self.s_k, self.l_k))
        i1.add_layout(slider_row("want ω_n (×0.1 rad/s)", self.s_wn,
                                 self.l_wn))
        i1.add_layout(slider_row("want ζ (×0.01)", self.s_z, self.l_z))
        i1.add_layout(slider_row("force limit (N)", self.s_fmax, self.l_fmax))
        self.st_k1 = Stat("k₁  (virtual spring)", "--", theme.ACCENT)
        self.st_k2 = Stat("k₂  (virtual damper)", "--", theme.VIOLET)
        self.st_check = Stat("hand formula", "--", theme.GOOD)
        self.st_pk = Stat("peak force", "--", theme.BAD)
        self.st_sat = Stat("saturated", "--", theme.WARN)
        i1.add_layout(stat_row(self.st_k1, self.st_k2, self.st_check,
                               self.st_pk, self.st_sat))
        self.mat1 = body("")
        i1.add(self.mat1)
        self.c1 = MplCanvas(width=7.6, height=2.9, ncols=3)
        i1.add(self.c1)
        self.t1 = body("", dim=True)
        i1.add(self.t1)
        self.add(i1)
        for s in (self.s_m, self.s_b, self.s_k, self.s_wn, self.s_z,
                  self.s_fmax):
            s.setTracking(False)
            s.valueChanged.connect(lambda _value: self._msd_timer.start())
        presets = QHBoxLayout()
        for label, wn, limit in (('1 · Moderate response', 40, 600), ('2 · Faster response', 120, 600), ('3 · Same poles, 5 N limit', 120, 5)):
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, w=wn, f=limit: self._msd_example(w, f))
            presets.addWidget(button)
        i1.add_layout(presets)
        self._redraw_msd()

        # ==============================================================
        # 4. controllability
        # ==============================================================
        self.add(hline())
        self.add(title("Controllability — the permission slip, and it is "
                       "about your mechanism, not your code"))

        ct = Card("the theorem, and the honest version of it")
        ct.add(title("If (A, B) is controllable, K exists that puts the "
                     "eigenvalues of A − BK anywhere you name.", 15))
        ct.add(body(
            "Anywhere. Not \"nudged toward\" — placed. That is a remarkable "
            "theorem and it is why the method is worth learning. The test:"))
        ct.add(math_label(r"\mathcal{C} = \big[\,B \;\; AB \;\; A^2B \;\cdots"
                          r"\; A^{n-1}B\,\big], \qquad "
                          r"\text{controllable} \iff \operatorname{rank}"
                          r"\mathcal{C} = n", 17))
        ct.add(body(
            "<b>Why that matrix.</b> B is where the input pushes directly. AB "
            "is where that push has spread to after an instant of the "
            "dynamics. A²B is where it has spread after another. Stack n of "
            "them and you have every direction the actuator can eventually "
            "reach. If those directions span the whole space, you can steer "
            "anywhere. If they do not, some combination of states is "
            "<b>invisible to your actuator forever</b>.<br><br>"
            "This is exactly how a SEA gets away with one motor and four "
            "states: the motor pushes only θ̇<sub>m</sub> directly, but the "
            "spring propagates that into the load within one multiplication "
            "by A. <b>The spring is the thing that makes the load "
            "controllable.</b> Set k = 0 and the two halves are mechanically "
            "disconnected and the rank collapses."))
        ct.add(callout(
            '<b>Controllable does not mean easy to control.</b> Exact uncontrollable modes can exist: '
            'with a disconnected spring, motor torque cannot move the load. Even when the rank test passes, '
            'weak coupling can require large gains and make a design sensitive to error. '
            'The singular values of the controllability matrix depend on state units and scaling; '
            'their ratio is not directly a motor-force or energy ratio. Check actual effort, limits and robustness. '
            'Observability is a separate question: can the chosen sensor reveal the state over time?', 'warn'))
        self.add(ct)

        # ---- interactive 2: SEA ---------------------------------------
        self.add(hline())
        self.add(title("Now four states: a series elastic actuator"))

        i2 = Card("one motor, one spring, one load — and all four poles "
                  "placed at once")
        i2.add(body(
            '<b>Purpose: extend the same pole-placement calculation from two states to four.</b> '
            'A motor and load joined by a spring each have an angle and velocity: '
            'x = [θ_m, θ̇_m, θ_L, θ̇_L]. One motor torque can influence all four through the spring. '
            'The later actuator lesson (page 26) explores the mechanics in detail; here focus on the extra states.<br><br>'
            '<b>What is being designed?</b> The first pair follows your ω_n and ζ, just as above. '
            'The other pair is set to −3ω_n ± j0.6ω_n for this demonstration. Four desired poles give four feedback gains. '
            'ω_n is a pole-design parameter, not a measured tracking bandwidth.<br><br>'
            '<b>Read left → right:</b> motor and load start together at 11.5° with an unstretched spring and return to zero; '
            'the middle plot shows the spring deflection and motor torque needed; the right shows all four ideal closed-loop poles. '
            'There is no torque limit in this lab: use the torque curve to judge effort, not as a promise the hardware can deliver it.<br><br>'
            '<b>Try:</b> compare the two speed buttons at the same hardware, then soften the spring. '
            'Watch the gains, torque and relative motion change. The dashed frequency lines mark the free elastic resonance. '
            'The motor anti-resonance stat is the zero of motor angle / motor torque, where the motor can stay still while the load moves.<br><br>'
            '<b>The sensor menu asks a separate question:</b> could one sensor’s time history let an observer reconstruct all states? '
            'It only changes the observability verdict; the simulation still assumes full-state feedback. '
            'A load-angle sensor can be observable without directly measuring all four states. Spring deflection alone misses common motion. '
            'Observers are introduced on page 20. Release a slider to update.', dim=True))
        self.s_sk = slider(50, 3000, 400)        # N m / rad
        self.s_jm = slider(5, 200, 20)           # x0.001 kg m^2
        self.s_jl = slider(20, 800, 250)         # x0.001
        self.s_bw = slider(10, 600, 400)         # x0.1 rad/s, desired
        self.s_sz = slider(30, 150, 80)          # x0.01 desired zeta
        self.l_sk, self.l_jm, self.l_jl = QLabel(), QLabel(), QLabel()
        self.l_bw, self.l_sz = QLabel(), QLabel()
        i2.add_layout(slider_row("spring k (N·m/rad)", self.s_sk, self.l_sk))
        i2.add_layout(slider_row("motor J_m (×0.001)", self.s_jm, self.l_jm))
        i2.add_layout(slider_row("load J_l (×0.001)", self.s_jl, self.l_jl))
        i2.add_layout(slider_row("want ω_n (×0.1 rad/s)", self.s_bw,
                                 self.l_bw))
        i2.add_layout(slider_row("want ζ (×0.01)", self.s_sz, self.l_sz))
        self.cmb_sensor = QComboBox()
        for lab, key in (("load angle only  (non-collocated)", "load"),
                         ("motor angle only  (collocated)", "motor"),
                         ("spring deflection  (torque sensor)", "deflection")):
            self.cmb_sensor.addItem(lab, key)
        self.cmb_sensor.currentIndexChanged.connect(lambda _index: self._sea_timer.start())
        i2.add_layout(labelled("Sensor", self.cmb_sensor, width=60))
        self.st_res = Stat("resonance", "--", theme.WARN)
        self.st_anti = Stat("motor anti-resonance", "--", theme.CYAN)
        self.st_kmax = Stat("max |Kᵢ| (mixed units)", "--", theme.BAD)
        self.st_defl = Stat("peak deflection", "--", theme.VIOLET)
        self.st_ctrb = Stat("controllable?", "--", theme.GOOD)
        i2.add_layout(stat_row(self.st_res, self.st_anti, self.st_kmax,
                               self.st_defl, self.st_ctrb))
        self.mat2 = body("")
        i2.add(self.mat2)
        self.c2 = MplCanvas(width=7.6, height=2.9, ncols=3)
        i2.add(self.c2)
        self.t2 = body("", dim=True)
        i2.add(self.t2)
        self.add(i2)
        for s in (self.s_sk, self.s_jm, self.s_jl, self.s_bw, self.s_sz):
            s.setTracking(False)
            s.valueChanged.connect(lambda _value: self._sea_timer.start())
        presets = QHBoxLayout()
        for label, speed in (('1 · ω_n = 20 rad/s', 200), ('2 · ω_n = 60 rad/s', 600)):
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, w=speed: self._sea_example(w))
            presets.addWidget(button)
        i2.add_layout(presets)
        self._redraw_sea()

        self.add(callout(
            '<b>Takeaway 1 · Choosing the poles is still a design decision.</b><br><br>'
            'You now know how to calculate K once the poles are chosen. The first lab shows why “make them faster” is not enough: '
            'the 12 rad/s design starts by asking for 35 N, versus 3 N at 4 rad/s. A 5 N actuator cannot reproduce that ideal fast response.<br><br>'
            'Pole placement does not include a penalty for force or tell you which response is worth its cost. '
            'In the four-state lab you must also choose a second pole pair. '
            '<b>Page 19, LQR, chooses K from weights on state error and control effort.</b> Its poles are a result of that tradeoff. '
            'LQR still needs checks for saturation and model error; it is not an automatic hardware guarantee.', 'key'))

        n = Card('Takeaway 2 · Returning to zero and reaching a requested position are different tasks')
        n.add(body(
            '<b>Both labs here are regulation:</b> start displaced and use u = −Kx to return to zero. '
            'Placing poles shapes how deviations decay. To hold a nonzero target, also define the required equilibrium.<br><br>'
            '<b>Example using the first lab:</b> ask the mass to hold r = 0.05 m against its spring k = 20 N/m. '
            'At rest the spring pulls with 1 N, so the motor must supply +1 N. Use '
            '<b>u = −k₁(q−r) − k₂q̇ + kr</b>. At q = r and q̇ = 0, the feedback terms vanish and kr holds the spring. '
            'Expanding gives u = −Kx + (k+k₁)r; the feedforward factor is N = k+k₁. '
            'This changes the target while preserving the same ideal error poles.<br><br>'
            '<b>Why add an integrator later?</b> An unknown constant load or an inaccurate spring model can leave an offset. '
            'An integral state accumulates r−q and adjusts the command until that persistent error vanishes, '
            'provided the augmented loop is stable and the actuator has enough authority. Page 19 introduces LQI.<br><br>'
            '<b>Why an observer?</b> If velocities or other states are not measured, an observer estimates them from sensors and a model (page 20). '
            'Estimating an unknown disturbance requires an additional disturbance model; an ordinary state observer does not automatically cancel it.'))
        self.add(n)

        self.finish()

    # ------------------------------------------------------------------
    def _msd_example(self, wn, limit):
        for slider_, value in ((self.s_m, 50), (self.s_b, 6), (self.s_k, 200),
                               (self.s_wn, wn), (self.s_z, 90), (self.s_fmax, limit)):
            slider_.setValue(value)
        self._msd_timer.stop()
        self._redraw_msd()

    def _sea_example(self, wn):
        for slider_, value in ((self.s_sk, 400), (self.s_jm, 20), (self.s_jl, 250),
                               (self.s_bw, wn), (self.s_sz, 80)):
            slider_.setValue(value)
        self._sea_timer.stop()
        self._redraw_sea()

    def _redraw_msd(self):
        m = self.s_m.value() / 10.0
        b = self.s_b.value() / 10.0
        k = self.s_k.value() / 10.0
        wn = self.s_wn.value() / 10.0
        z = self.s_z.value() / 100.0
        fmax = float(self.s_fmax.value())
        self.l_m.setText(f"{m:.1f} kg")
        self.l_b.setText(f"{b:.1f}")
        self.l_k.setText(f"{k:.1f}")
        self.l_wn.setText(f"{wn:.1f} rad/s")
        self.l_z.setText(f"{z:.2f}")
        self.l_fmax.setText(f"{fmax:.0f} N")

        ss = msd_ss(m, b, k)
        desired = second_order_poles(wn, z)
        K = place_poles(ss.A, ss.B, desired)
        k1, k2 = float(K[0, 0]), float(K[0, 1])
        k1_hand = m * wn * wn - k
        k2_hand = 2 * z * wn * m - b
        agree = abs(k1 - k1_hand) < 1e-6 * max(1.0, abs(k1_hand)) and \
            abs(k2 - k2_hand) < 1e-6 * max(1.0, abs(k2_hand))

        self.st_k1.set(f"{k1:+.1f}")
        self.st_k1.set_color(theme.ACCENT if k1 >= 0 else theme.BAD)
        self.st_k2.set(f"{k2:+.2f}")
        self.st_k2.set_color(theme.VIOLET if k2 >= 0 else theme.BAD)
        self.st_check.set("matches" if agree else "differs!")
        self.st_check.set_color(theme.GOOD if agree else theme.BAD)

        ts, xs, us, sat = regulator_response(ss, K, [0.05, 0.0], dur=3.0,
                                            dt=5e-4, u_max=fmax)
        pk = float(np.max(np.abs(us))) if len(us) else 0.0
        self.st_pk.set(f"{pk:.0f} N")
        self.st_pk.set_color(theme.BAD if pk >= fmax * 0.999 else theme.GOOD)
        self.st_sat.set("no" if sat < 1e-9 else f"{sat*100:.0f}% of ticks")
        self.st_sat.set_color(theme.GOOD if sat < 1e-9 else theme.BAD)

        A_cl = np.asarray(ss.A) - np.asarray(ss.B) @ K
        self.mat1.setText(
            _matrix_html(ss.A, "A", colour=theme.TEXT_DIM) +
            _matrix_html(A_cl, "A − BK", colour=theme.ACCENT) +
            f"<span style='color:{theme.TEXT_FAINT}'>hand formula: "
            f"k₁ = mω<sub>n</sub>² − k = {k1_hand:+.2f}, &nbsp; "
            f"k₂ = 2ζω<sub>n</sub>m − b = {k2_hand:+.2f}</span>")

        wn0, z0 = msd_natural(m, b, k)
        if sat > 1e-9:
            self.t1.setText(
                f'<b>The force is limited for {sat*100:.0f}% of simulation steps.</b> '
                'The plotted poles describe A−BK before clipping. During clipping the command no longer equals −Kx, '
                'so those poles alone do not predict the nonlinear response. Compare the actual position trace '
                'with the same design at a higher force limit; the requested gains and ideal poles stay unchanged.')
        elif abs(k1) < 0.05 and abs(k2) < 0.05:
            self.t1.setText(
                f"<b>Both gains are ~0, because you asked for what the plant "
                f"already does</b> (ω<sub>n</sub> = {wn0:.1f}, ζ = {z0:.2f}). "
                "The controller has nothing to add. Worth pausing on: this "
                "means K measures <i>the difference between the machine you "
                "have and the machine you asked for</i>, not some absolute "
                "amount of control.")
        elif k1 < 0:
            self.t1.setText(
                f"<b>k₁ is negative ({k1:+.1f}), and that is correct.</b> You "
                f"asked for ω<sub>n</sub> = {wn:.1f} rad/s, below the plant's "
                f"own {wn0:.1f}. Making it slower than its own spring means "
                f"<i>cancelling part of the spring</i> — pushing in the "
                "direction of displacement. The algebra is fine. The risk is "
                "not: negative stiffness that over-cancels because k was "
                "mis-modelled gives you a machine that runs away, and it will "
                "do so smoothly and without warning.")
        else:
            self.t1.setText(
                f"<b>k₁ = {k1:.1f} N/m of virtual spring and k₂ = {k2:.2f} "
                f"N·s/m of virtual damper</b>, on top of the {k:.1f} and "
                f"{b:.1f} the hardware already had. Total closed-loop "
                f"stiffness {k + k1:.1f}, total damping {b + k2:.1f} — and "
                f"√((k+k₁)/m) = {math.sqrt(max(0.0,(k+k1))/m):.1f} rad/s, "
                "which is exactly the ω_n you asked for. That is what "
                "\"placed\" means.")

        c = self.c1
        c.clear()
        a1, a2, a3 = c.axes
        a1.plot(ts, xs[:, 0] * 100, color=theme.ACCENT, lw=2.0,
                label="closed loop")
        ts0, xs0, _u0, _s = regulator_response(ss, np.zeros_like(K),
                                              [0.05, 0.0], dur=3.0, dt=5e-4)
        a1.plot(ts0, xs0[:, 0] * 100, color=theme.TEXT_FAINT, lw=1.3, ls="--",
                label="no control")
        a1.axhline(0, color=theme.TEXT_FAINT, lw=1.0, ls=":")
        a1.set_xlabel("time (s)")
        a1.set_ylabel("position (cm)")
        a1.set_title("released from 5 cm", fontsize=9)
        c.legend(a1, loc="upper right")

        a2.plot(ts, us[:, 0], color=theme.BAD, lw=1.8)
        a2.axhline(fmax, color=theme.WARN, lw=1.2, ls="--", label="limit")
        a2.axhline(-fmax, color=theme.WARN, lw=1.2, ls="--")
        a2.set_xlabel("time (s)")
        a2.set_ylabel("force (N)")
        a2.set_title("what it costs", fontsize=9)
        c.legend(a2, loc="upper right")

        lim = max(4.0, wn * 1.6, 1.2*float(np.max(np.abs(np.linalg.eigvals(A_cl)))))
        _splane(a3, [complex(v) for v in np.linalg.eigvals(A_cl)], lim=lim,
                marker_label="placed")
        op = np.linalg.eigvals(np.asarray(ss.A))
        a3.scatter([p.real for p in op], [p.imag for p in op], marker="x",
                   s=60, linewidths=1.6, color=theme.TEXT_FAINT, zorder=4,
                   label="open loop")
        a3.set_title("open loop → placed", fontsize=8.5)
        c.legend(a3, loc="upper left")
        c.fig.subplots_adjust(left=.085, right=.94, bottom=.22, top=.84, wspace=.65)
        c.refresh(layout=False)

    # ------------------------------------------------------------------
    def _redraw_sea(self):
        k = float(self.s_sk.value())
        jm = self.s_jm.value() / 1000.0
        jl = self.s_jl.value() / 1000.0
        wn = self.s_bw.value() / 10.0
        z = self.s_sz.value() / 100.0
        self.l_sk.setText(f"{k:.0f}")
        self.l_jm.setText(f"{jm:.3f}")
        self.l_jl.setText(f"{jl:.3f}")
        self.l_bw.setText(f"{wn:.1f} rad/s")
        self.l_sz.setText(f"{z:.2f}")

        ss = sea_ss(jm, jl, k)
        w_res, w_anti = sea_modes(jm, jl, k)
        self.st_res.set(f"{w_res:.0f} rad/s")
        self.st_anti.set(f"{w_anti:.0f} rad/s")
        self.st_ctrb.set("yes" if controllable(ss) else "NO")
        self.st_ctrb.set_color(theme.GOOD if controllable(ss) else theme.BAD)

        # dominant pair at (wn, z); the other pair pushed 3x further left
        desired = second_order_poles(wn, z) + [complex(-3.0*wn, .6*wn), complex(-3.0*wn, -.6*wn)]
        try:
            K = place_poles(ss.A, ss.B, desired)
        except Exception:
            K = np.zeros((1, 4))
        kmax = float(np.max(np.abs(K)))
        self.st_kmax.set(f"{kmax:.3g}")
        self.st_kmax.set_color(theme.BAD if kmax > 5e3 else theme.GOOD)

        # both bodies offset by the same angle: the whole joint is 11.5 deg
        # from where it should be, with the spring relaxed. Starting with
        # the spring pre-wound would confuse a transient for a design.
        x0 = [0.20, 0.0, 0.20, 0.0]
        key = (k, jm, jl, wn, z)
        if getattr(self, '_sea_response_key', None) != key:
            self._sea_response = regulator_response(ss, K, x0, dur=1.2, dt=2e-4)
            self._sea_response_key = key
        ts, xs, us, _sat = self._sea_response
        defl = float(np.max(np.abs(xs[:, 0] - xs[:, 2]))) if len(xs) else 0.0
        self.st_defl.set(f"{math.degrees(defl):.1f}°")
        self.st_defl.set_color(theme.BAD if math.degrees(defl) > 20
                               else theme.VIOLET)

        sensor = self.cmb_sensor.currentData()
        ss_obs = StateSpace(ss.A, ss.B, sea_output(sensor),
                            np.array([[0.0]]))
        obs_ok = observable(ss_obs)

        self.mat2.setText(
            _matrix_html(K, "K", fmt="{:+.1f}", colour=theme.ACCENT) +
            f"<span style='color:{theme.TEXT_FAINT}'>order: "
            "θ<sub>m</sub>, θ̇<sub>m</sub>, θ<sub>l</sub>, θ̇<sub>l</sub>"
            "</span>")

        ratio = wn / w_res if w_res > 0 else 0.0
        obs_txt = ("observable" if obs_ok else
                   "<b style='color:#f85149'>NOT observable</b>")
        self.t2.setText(
            f'<b>Requested pole scale:</b> ω_n = {wn:.1f} rad/s; free resonance = {w_res:.1f} rad/s. '
            f'Peak motor torque = {np.max(np.abs(us)):.2f} N·m; peak spring deflection = {math.degrees(defl):.1f}°. '
            'These traces assume an ideal unsaturated motor and all four states available. '
            f'<br><b>Selected sensor:</b> {self.cmb_sensor.currentText()} → {obs_txt}. '
            'This verdict concerns reconstructing the states from measurements over time. '
            'Changing the menu does not replace full-state feedback in these traces.')
        if getattr(self, '_last_sea_plot', None) == (k, jm, jl, wn, z):
            return
        self._last_sea_plot = (k, jm, jl, wn, z)

        c = self.c2
        for axis in list(c.fig.axes):
            if axis not in c.axes:
                axis.remove()
        c.clear()
        a1, a2, a3 = c.axes
        a1.plot(ts, np.degrees(xs[:, 2]), color=theme.GOOD, lw=2.0,
                label="load θ_l")
        a1.plot(ts, np.degrees(xs[:, 0]), color=theme.ACCENT, lw=1.5, ls="--",
                label="motor θ_m")
        a1.axhline(0, color=theme.TEXT_FAINT, lw=1.0, ls=":")
        a1.set_xlabel("time (s)")
        a1.set_ylabel("angle (°)")
        a1.set_title("whole joint 11.5° off, released", fontsize=8.5)
        c.legend(a1, loc="upper right")

        a2.plot(ts, np.degrees(xs[:, 0] - xs[:, 2]), color=theme.VIOLET,
                lw=1.8, label="spring deflection")
        a2b = a2.twinx()
        a2b.plot(ts, us[:, 0], color=theme.BAD, lw=1.3, alpha=0.75)
        a2b.set_ylabel("τ (N·m)", color=theme.BAD, fontsize=9)
        a2b.tick_params(colors=theme.BAD, labelsize=8)
        a2.set_xlabel("time (s)")
        a2.set_ylabel("deflection (°)", color=theme.VIOLET)
        a2.set_title("the spring is the torque sensor", fontsize=8.5)

        lim = max(w_res * 1.3, wn * 4.0)
        _splane(a3, [complex(v) for v in
                     np.linalg.eigvals(np.asarray(ss.A) -
                                       np.asarray(ss.B) @ K)],
                lim=lim, marker_label="placed")
        op = np.linalg.eigvals(np.asarray(ss.A))
        a3.scatter([p.real for p in op], [p.imag for p in op], marker="x",
                   s=55, linewidths=1.5, color=theme.TEXT_FAINT, zorder=4,
                   label="open loop")
        a3.axhline(w_res, color=theme.WARN, lw=1.0, ls=":")
        a3.axhline(-w_res, color=theme.WARN, lw=1.0, ls=":")
        a3.set_title("4 poles placed at once", fontsize=8.5)
        c.legend(a3, loc="upper left")
        c.fig.subplots_adjust(left=.085, right=.94, bottom=.22, top=.84, wspace=.65)
        c.refresh(layout=False)


# ==========================================================================
# PAGE -- LQR
# ==========================================================================

class LQRPage(Page):
    TITLE = "LQR & Optimal Control"
    SUBTITLE = ((
                    "Stop naming pole locations you have no intuition for and name a price instead. What Q, R and P "
                    "actually are — and why xᵀPx is cost-to-go, related by a reward-sign convention to RL value."
                ))
    SECTION = SECTION
    NOTES = "design"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>The question pole placement cannot answer.</b> A trunkless "
            "biped has twelve states, so it has twelve poles. Where do you "
            "put them? \"All at −20\"? Why −20, and why all together, and why "
            "should the ankle and the hip want the same dynamics when one "
            "carries the whole body and the other carries a thigh?<br><br>"
            "Nobody has intuition for twelve pole locations. Everybody has "
            "intuition for <b>\"I will accept 2 cm of error and I have 40 N·m "
            "of torque\"</b>. LQR is the machine that turns the second "
            "sentence into the first.", "key"))

        # ==============================================================
        # the cost
        # ==============================================================
        cf = Card("the cost functional, read as a running bill")
        cf.add(math_label(r"J = \int_0^\infty \Big( \underbrace{x^T Q x}"
                          r"_{\text{price of being wrong}} + "
                          r"\underbrace{u^T R u}_{\text{price of the fix}}"
                          r"\Big)\, dt", 18))
        cf.add(body(
            "Every instant, you are charged for two things: how far off you "
            "are, and how hard you are pushing. Integrate over all time and "
            "you have a single number attached to a controller. <b>The best "
            "controller is the one with the smallest bill.</b><br><br>"
            "The quadratic form is not arbitrary. Squaring makes the penalty "
            "sign-blind (2 cm left is as bad as 2 cm right), it punishes "
            "large errors disproportionately, and — the reason it is actually "
            "used — it is the one choice for which the whole problem has a "
            "closed-form solution."))
        cf.add(body(
            "Written out for a two-state plant with diagonal Q, the mystery "
            "evaporates:"))
        cf.add(math_label(r"x^TQx + u^TRu = q_{11}x_1^2 + q_{22}x_2^2 + r\,u^2",
                          18))
        cf.add(callout(
            "<b>So Q and R are just weights, one per squared quantity.</b><br><br>"
            "&nbsp;&nbsp;• <b>Q</b> (n×n, positive semi-definite) — the price "
            "of state error. <b>q₁₁ is the price of position² and q₂₂ is the "
            "price of velocity².</b> Big q₁₁ means \"I hate being off "
            "target\". A zero on the diagonal means \"I do not care about "
            "that state at all\", which is a legitimate and common "
            "choice.<br>"
            "&nbsp;&nbsp;• <b>R</b> (m×m, positive definite) — the price of "
            "effort, one entry per actuator. Big R means \"torque is "
            "expensive, be gentle\". R must be strictly positive: if effort "
            "were free the optimiser would use infinite gain, and the problem "
            "would have no solution.<br><br>"
            "Off-diagonal entries exist and mean \"I care about this "
            "<i>combination</i>\" — for a SEA, an off-diagonal term coupling "
            "θ<sub>m</sub> and θ<sub>l</sub> is how you say \"I care about "
            "spring deflection\". Almost everything in practice is diagonal, "
            "and the exceptions are worth flagging when they appear.",
            "key"))
        cf.add(body(
            "<b>Only the ratio matters.</b> Multiply Q and R both by 1000 and "
            "K does not change — the same controller is optimal, the bill is "
            "just denominated in different units. So there are not 2n knobs, "
            "there are 2n−1, and the single most useful one is <b>Q/R "
            "overall</b>: crank it up for aggressive, down for gentle. Every "
            "other adjustment is about the relative importance of states to "
            "each other.", dim=True))
        self.add(cf)

        # ==============================================================
        # units and Bryson
        # ==============================================================
        br = Card("the units problem, and Bryson's rule — the only sane place "
                  "to start")
        br.add(body(
            "Here is why naive Q and R behave strangely. In the sum "
            "q₁₁x₁² + q₂₂x₂², x₁ is in metres and x₂ is in metres per second. "
            "<b>Setting q₁₁ = q₂₂ = 1 does not mean \"weight them equally\"</b> "
            "— it means \"one square metre of position error costs the same "
            "as one square metre-per-second of velocity error\", which is a "
            "statement about your choice of units and nothing else. Switch to "
            "millimetres and the same numbers mean something a million times "
            "different."))
        br.add(body("Bryson's rule removes the problem by normalising each "
                    "term by the largest value you are willing to tolerate:"))
        br.add(math_label(r"Q_{ii} = \frac{1}{(x_i^{\max})^2}, \qquad "
                          r"R_{jj} = \frac{1}{(u_j^{\max})^2}", 18))
        br.add(body(
            "<b>Now every term is dimensionless and equals 1 when that "
            "variable is at its limit.</b> The cost has become \"how many "
            "times over budget am I, summed\", which is comparable across "
            "quantities with different units. After Bryson, tuning means "
            "scaling blocks by factors of ten and each factor has a "
            "meaning — \"I care about this ten times more than I first "
            "said\".<br><br>"
            "<b>Worked, for the mass-spring-damper:</b> \"I will accept 2 cm "
            "of position error, 30 cm/s of velocity, and I have 10 N of "
            "force.\" That is"))
        br.add(math_label(r"Q = \begin{bmatrix} 1/0.02^2 & 0\\ 0 & 1/0.3^2"
                          r"\end{bmatrix} = \begin{bmatrix}2500 & 0\\ 0 & 11.1"
                          r"\end{bmatrix}, \qquad R = \frac{1}{10^2} = 0.01",
                          17))
        br.add(body(
            "Note what those numbers say without any control theory: position "
            "matters about 225 times more than velocity, because 2 cm is a "
            "much tighter budget than 30 cm/s. <b>That ratio came out of the "
            "specification, not out of tuning</b>, and that is the whole "
            "point of the rule.", dim=True))
        self.add(br)

        # ==============================================================
        # the answer, and what P is
        # ==============================================================
        self.add(hline())
        self.add(title("The answer — and P, which is the most important "
                       "matrix in this tutor"))

        ans = Card("K = R⁻¹BᵀP, and P solves a quadratic matrix equation")
        ans.add(math_label(r"A^TP + PA - PBR^{-1}B^TP + Q = 0", 18))
        ans.add(math_label(r"K = R^{-1}B^TP", 18))
        ans.add(body(
            "The first is the <b>algebraic Riccati equation</b>. It is "
            "quadratic in P (that is the −PBR⁻¹BᵀP term), which is why it has "
            "several solutions and you want the unique positive-definite one. "
            "<code>ctrlcore</code> solves it through the Hamiltonian matrix's "
            "stable eigenvectors, which is how it is actually done."))
        ans.add(callout(
            "<b>P parameterises the optimal cost-to-go.</b><br><br>"
            "Start the system at x₀, run the optimal controller forever, and "
            "add up the entire bill. The answer is"
            "<br><br>&nbsp;&nbsp;&nbsp;&nbsp;<b>J*(x₀) = x₀ᵀ P x₀</b><br><br>"
            "P converts \"where you are\" into \"what the rest of your life "
            "will cost, assuming you play optimally from here\". Read that "
            "sentence with the later RL vocabulary in mind: LQR minimises "
            "<b>cost-to-go</b>; RL maximises <b>expected return</b>. If reward is "
            "the negative running cost under matching horizon and dynamics "
            "conventions, the optimal return is <b>−x₀ᵀPx₀</b>, not P alone.<br><br>"
            "For this linear–quadratic problem, the value/cost function has a "
            "quadratic form. Substituting it into continuous-time optimality "
            "gives the Riccati equation. This is a concrete connection to "
            "Bellman reasoning; it does not make every Riccati numerical solver "
            "a value-iteration algorithm.", "key"))
        ans.add(body(
            "<b>And the guarantees, which are why LQR is trusted.</b> If "
            "(A,B) is stabilisable and Q does not hide an unstable mode, the "
            "closed loop is <b>guaranteed stable</b> — for any positive Q and "
            "R, with no stability check needed. On top of that, full-state "
            "LQR has famous margins: <b>at least 60° of phase margin</b>, "
            "infinite gain margin upward, and tolerance of a 50% gain "
            "reduction. You could not ask for a better robustness "
            "certificate."))
        ans.add(callout(
            "<b>And now the caveat every interview eventually reaches.</b> "
            "Those margins hold for <i>full state feedback</i>. Put a Kalman "
            "filter or any observer in front of it — which you must, because "
            "you cannot measure twelve states — and <b>the guarantees "
            "vanish</b>. Doyle's 1978 paper is one page long and its title is "
            "\"Guaranteed Margins for LQG Regulators\"; the abstract says "
            "there are none. The fix in practice is <b>loop transfer "
            "recovery</b>, or designing the observer several times faster "
            "than the controller and then checking the margins you actually "
            "got rather than the ones you were promised.", "warn"))
        self.add(ans)

        # ---- interactive 1: MSD LQR -------------------------------------
        i1 = Card("price the mass-spring-damper, and watch the poles move "
                  "without being told where to go")
        i1.add(body(
            "The sliders are <b>tolerances</b>, not gains and not poles: how "
            "much position error you will accept, how much velocity, and how "
            "much force you have. Q and R are built from them by Bryson's "
            "rule and printed below. You never name a pole; the poles move "
            "anyway, and the map shows where they went.<br><br>"
            "<b>Four things to do:</b><br>"
            "&nbsp;&nbsp;<b>1.</b> Tighten the position tolerance. Gains rise, "
            "poles move left, force rises. You are buying speed with "
            "torque and the exchange rate is being computed for you.<br>"
            "&nbsp;&nbsp;<b>2.</b> Now tighten the <i>force budget</i> "
            "instead. The optimiser backs off on its own — no re-tuning, no "
            "instability, just a gentler controller. Compare that with what "
            "happened on the previous page when you saturated: LQR does not "
            "get you out of a torque limit, but it lets you <b>state</b> the "
            "limit up front instead of discovering it.<br>"
            "&nbsp;&nbsp;<b>3.</b> Scale both budgets by the same factor. "
            "<b>K does not change.</b> Only the ratio matters, and the stat "
            "confirms it.<br>"
            "&nbsp;&nbsp;<b>4.</b> Read J* = x₀ᵀPx₀ as you move things. That "
            "single number is the whole future cost from the current start, "
            "and it is the closest thing classical control has to a critic.",
            dim=True))
        self.s_xmax = slider(2, 200, 20)         # x0.001 m
        self.s_vmax = slider(2, 300, 30)         # x0.01 m/s
        self.s_umax = slider(1, 400, 100)        # x0.1 N
        self.l_xmax, self.l_vmax, self.l_umax = QLabel(), QLabel(), QLabel()
        i1.add_layout(slider_row("accept x error (mm)", self.s_xmax,
                                 self.l_xmax))
        i1.add_layout(slider_row("accept v (×0.01 m/s)", self.s_vmax,
                                 self.l_vmax))
        i1.add_layout(slider_row("force budget (×0.1 N)", self.s_umax,
                                 self.l_umax))
        self.s_scale = slider(-20, 20, 0)        # log10 x0.1, common scale
        self.l_scale = QLabel()
        i1.add_layout(slider_row("scale Q and R (log₁₀×0.1)", self.s_scale,
                                 self.l_scale))
        self.st_lk1 = Stat("k₁", "--", theme.ACCENT)
        self.st_lk2 = Stat("k₂", "--", theme.VIOLET)
        self.st_lpk = Stat("peak force", "--", theme.BAD)
        self.st_lcost = Stat("J* = x₀ᵀPx₀", "--", theme.CYAN)
        self.st_lpm = Stat("closed-loop ζ", "--", theme.GOOD)
        i1.add_layout(stat_row(self.st_lk1, self.st_lk2, self.st_lpk,
                               self.st_lcost, self.st_lpm))
        self.mat3 = body("")
        i1.add(self.mat3)
        self.c3 = MplCanvas(width=7.6, height=2.9, ncols=3)
        i1.add(self.c3)
        self.t3 = body("", dim=True)
        i1.add(self.t3)
        self.add(i1)
        for s in (self.s_xmax, self.s_vmax, self.s_umax, self.s_scale):
            s.valueChanged.connect(self._redraw_lqr_msd)
        self._redraw_lqr_msd()

        # ---- interactive 2: SEA LQR -------------------------------------
        self.add(hline())
        self.add(title("Q and R for a real four-state plant: the SEA"))

        se = Card("what each of the four weights means on hardware")
        se.add(body(
            "This is where Q stops being an abstraction, because each "
            "diagonal entry is a sentence about the machine.<br><br>"
            "<table cellpadding='7'>"
            "<tr><td><b>Weight</b></td><td><b>On</b></td>"
            "<td><b>What raising it says</b></td></tr>"
            "<tr><td>q₁₁</td><td>θ<sub>m</sub>, motor angle</td>"
            "<td>\"the motor must return to its commanded position\". Usually "
            "the one you care <i>least</i> about — nobody is looking at the "
            "rotor.</td></tr>"
            "<tr><td>q₂₂</td><td>θ̇<sub>m</sub>, motor speed</td>"
            "<td>\"do not let the rotor whip about\". Mostly a smoothness and "
            "back-EMF term.</td></tr>"
            "<tr><td>q₃₃</td><td>θ<sub>l</sub>, <b>load angle</b></td>"
            "<td>\"the output must be where I said\". <b>This is the one the "
            "task cares about</b>, and it is the state furthest from the "
            "actuator.</td></tr>"
            "<tr><td>q₄₄</td><td>θ̇<sub>l</sub>, load speed</td>"
            "<td>\"do not let the output oscillate\". This is what actually "
            "damps the resonance.</td></tr>"
            "<tr><td>q<sub>δ</sub></td><td>θ<sub>m</sub> − θ<sub>l</sub>, "
            "<b>deflection</b></td>"
            "<td>\"do not over-stress the spring\" — and since deflection × k "
            "is torque, this is literally <b>a penalty on output torque</b>. "
            "It is an off-diagonal Q, and it is the one non-diagonal term "
            "worth knowing.</td></tr>"
            "</table>"))
        se.add(math_label(
            r"Q_\delta = q_\delta \begin{bmatrix}1 & 0 & -1 & 0\end{bmatrix}^T"
            r"\begin{bmatrix}1 & 0 & -1 & 0\end{bmatrix} \;\;\Rightarrow\;\;"
            r"x^TQ_\delta x = q_\delta(\theta_m - \theta_l)^2", 16))
        se.add(body(
            "<b>That construction is worth remembering.</b> To penalise any "
            "linear combination cᵀx, add c·cᵀ to Q with a weight. It is how "
            "you say \"I care about this <i>relationship</i> between states\" "
            "rather than about the states individually — the same move that "
            "turns a position cost into a tracking-error cost.", dim=True))
        self.add(se)

        i2 = Card("tune a SEA by naming tolerances")
        i2.add(body(
            "Same plant as the previous page. Now nothing names a pole.<br><br>"
            "<b>Three things to do:</b><br>"
            "&nbsp;&nbsp;<b>1.</b> Raise the load-angle weight alone. The "
            "response gets faster and the spring deflection grows — the only "
            "way to move the load harder is to wind the spring "
            "further.<br>"
            "&nbsp;&nbsp;<b>2.</b> Now raise the <b>deflection</b> weight. "
            "Peak deflection falls, which means peak <i>output torque</i> "
            "falls, which is exactly how you protect a spring or a harmonic "
            "drive from its own controller. Note that this is a constraint "
            "you could not express at all in the language of pole "
            "placement.<br>"
            "&nbsp;&nbsp;<b>3.</b> Set the load weights to zero and leave "
            "only motor weights. The motor behaves beautifully and the load "
            "rings — you optimised the thing you measured instead of the "
            "thing you wanted, which is the most common way a well-posed "
            "optimal controller produces a bad machine.", dim=True))
        self.s_q3 = slider(-20, 60, 30)          # log10 x0.1, load angle
        self.s_q4 = slider(-20, 60, 10)          # log10 x0.1, load speed
        self.s_qd = slider(-30, 60, -30)         # log10 x0.1, deflection
        self.s_ru = slider(-40, 30, -10)         # log10 x0.1, torque price
        self.l_q3, self.l_q4 = QLabel(), QLabel()
        self.l_qd, self.l_ru = QLabel(), QLabel()
        i2.add_layout(slider_row("q₃₃ load angle (log)", self.s_q3, self.l_q3))
        i2.add_layout(slider_row("q₄₄ load speed (log)", self.s_q4, self.l_q4))
        i2.add_layout(slider_row("q_δ deflection (log)", self.s_qd, self.l_qd))
        i2.add_layout(slider_row("R torque price (log)", self.s_ru, self.l_ru))
        self.st_sdef = Stat("peak deflection", "--", theme.VIOLET)
        self.st_stau = Stat("peak torque", "--", theme.BAD)
        self.st_sts = Stat("load settling", "--", theme.GOOD)
        self.st_scost = Stat("J*", "--", theme.CYAN)
        self.st_sfast = Stat("fastest pole", "--", theme.WARN)
        i2.add_layout(stat_row(self.st_sdef, self.st_stau, self.st_sts,
                               self.st_scost, self.st_sfast))
        self.mat4 = body("")
        i2.add(self.mat4)
        self.c4 = MplCanvas(width=7.6, height=2.9, ncols=3)
        i2.add(self.c4)
        self.t4 = body("", dim=True)
        i2.add(self.t4)
        self.add(i2)
        for s in (self.s_q3, self.s_q4, self.s_qd, self.s_ru):
            s.valueChanged.connect(self._redraw_lqr_sea)
        self._redraw_lqr_sea()

        # ==============================================================
        # comparison + LQI + bridge
        # ==============================================================
        self.add(hline())
        self.add(title("Pole placement versus LQR, and where each one belongs"))

        cmp_ = Card("head to head")
        cmp_.add(body(
            "<table cellpadding='7'>"
            "<tr><td></td><td><b>Pole placement</b></td><td><b>LQR</b></td>"
            "</tr>"
            "<tr><td><b>You specify</b></td><td>n pole locations</td>"
            "<td>2 weight matrices — really, a set of tolerances</td></tr>"
            "<tr><td><b>Intuition needed</b></td>"
            "<td>high, and it does not survive past n = 2</td>"
            "<td>low; the units are engineering units</td></tr>"
            "<tr><td><b>MIMO</b></td>"
            "<td>awkward — K is not unique, and the extra freedom has to be "
            "resolved by something</td>"
            "<td>natural; one gain matrix falls out</td></tr>"
            "<tr><td><b>Knows about effort</b></td><td>no, not at all</td>"
            "<td>yes — R is exactly that</td></tr>"
            "<tr><td><b>Stability</b></td>"
            "<td>you chose it, so yes by construction</td>"
            "<td>guaranteed for any valid Q, R</td></tr>"
            "<tr><td><b>Margins</b></td><td>whatever you happen to get</td>"
            "<td>≥60° PM, ∞ GM — with full state feedback only</td></tr>"
            "<tr><td><b>Good for</b></td>"
            "<td>small systems where you genuinely want a specific response; "
            "matching a known second-order spec; teaching</td>"
            "<td>anything with more than about three states; every "
            "multi-joint robot</td></tr>"
            "</table>"))
        cmp_.add(body(
            "<b>They are not rivals.</b> A very standard workflow is: use "
            "LQR to get a sensible gain, look at where the poles landed, and "
            "if one of them is somewhere you dislike, adjust Q rather than "
            "the pole. You are steering with a specification and checking "
            "with a map.", dim=True))
        self.add(cmp_)

        lqi = Card("LQI — the same trick that gives PID its I term")
        lqi.add(body(
            "LQR regulates to zero and, exactly like state feedback, has no "
            "answer to a constant load. The fix is to invent a new state that "
            "<i>accumulates error</i> and then let the optimiser deal with "
            "it:"))
        lqi.add(math_label(r"\dot x_I = r - y = r - Cx, \qquad "
                           r"\tilde x = \begin{bmatrix} x \\ x_I\end{bmatrix}",
                           17))
        lqi.add(body(
            "Now run LQR on the augmented system. The extra diagonal entry in "
            "Q is <b>the price of accumulated error</b>, and the extra column "
            "in K is an integral gain. Steady-state error goes to zero for "
            "the same reason it does in PI control — there is a pole at the "
            "origin in the loop — but the gain came from the same "
            "optimisation as all the others rather than from a separate "
            "tuning session.<br><br>"
            "Everything true of integral action stays true: it still winds "
            "up, and it still needs anti-windup. Optimality does not repeal "
            "actuator limits.", dim=True))
        self.add(lqi)

        self.add(callout(
            "<b>The bridge to the second half of this tutor, stated "
            "plainly.</b> LQR and reinforcement learning solve the same "
            "problem: choose a policy that minimises an accumulated cost. "
            "Line them up:<br><br>"
            "&nbsp;&nbsp;• cost ∫(xᵀQx + uᵀRu)dt &nbsp;↔&nbsp; return "
            "Σγᵗr<sub>t</sub> &nbsp;(negated)<br>"
            "&nbsp;&nbsp;• P, with J* = xᵀPx &nbsp;↔&nbsp; V(s), the value "
            "function<br>"
            "&nbsp;&nbsp;• K, with u = −Kx &nbsp;↔&nbsp; π(s), the policy — "
            "and it is deterministic, which is why DDPG's actor is the direct "
            "descendant<br>"
            "&nbsp;&nbsp;• the Riccati equation &nbsp;↔&nbsp; the Bellman "
            "optimality equation<br>"
            "&nbsp;&nbsp;• solving Riccati &nbsp;↔&nbsp; value iteration<br><br>"
            "<b>LQR is the case where you can do the whole thing with "
            "linear algebra</b> because A and B are known and the cost is "
            "quadratic. You reach for RL when the dynamics are nonlinear, or "
            "unknown, or the cost is not quadratic — and you give up the "
            "closed form, the guarantees and the margins in exchange. Knowing "
            "exactly which of those three you are giving up, and why, is the "
            "difference between choosing RL and defaulting to it.", "good"))

        self.finish()

    # ------------------------------------------------------------------
    def _redraw_lqr_msd(self):
        xm = self.s_xmax.value() / 1000.0
        vm = self.s_vmax.value() / 100.0
        um = self.s_umax.value() / 10.0
        sc = 10 ** (self.s_scale.value() / 10.0)
        self.l_xmax.setText(f"{xm*1000:.0f} mm")
        self.l_vmax.setText(f"{vm:.2f} m/s")
        self.l_umax.setText(f"{um:.1f} N")
        self.l_scale.setText(f"×{sc:.3g}")

        ss = msd_ss(1.0, 0.6, 20.0)
        Q = bryson([xm, vm]) * sc
        R = bryson([um]) * sc
        x0 = np.array([0.02, 0.0])
        res = lqr_design(ss, Q, R, x0=x0)
        K = res.K
        k1, k2 = float(K[0, 0]), float(K[0, 1])

        ts, xs, us, _s = simulate_feedback(ss, K, x0, dur=3.0, dt=5e-4)
        pk = float(np.max(np.abs(us))) if len(us) else 0.0
        dom = max(res.poles, key=lambda p: p.real)
        wn_cl = abs(dom)
        z_cl = (-dom.real / wn_cl) if wn_cl > 1e-9 else 0.0

        self.st_lk1.set(f"{k1:.0f}")
        self.st_lk2.set(f"{k2:.1f}")
        self.st_lpk.set(f"{pk:.1f} N")
        self.st_lpk.set_color(theme.BAD if pk > um else theme.GOOD)
        self.st_lcost.set(f"{res.cost:.3g}")
        self.st_lpm.set(f"{z_cl:.2f}")
        self.st_lpm.set_color(theme.GOOD if z_cl > 0.5 else theme.WARN)

        self.mat3.setText(
            _matrix_html(Q, "Q", fmt="{:.4g}", colour=theme.VIOLET) +
            _matrix_html(R, "R", fmt="{:.4g}", colour=theme.WARN) +
            _matrix_html(res.P, "P", fmt="{:.4g}", colour=theme.CYAN) +
            _matrix_html(K, "K = R⁻¹BᵀP", fmt="{:.4g}", colour=theme.ACCENT))

        over = pk > um
        self.t3.setText(
            (f"<b>The optimiser exceeded your own force budget "
             f"({pk:.1f} N against {um:.1f} N declared).</b> Bryson's rule is "
             "a soft weighting, not a hard constraint — LQR minimises an "
             "average bill and will happily spend over budget briefly if the "
             "state error term is worth more. If the limit is real, raise R "
             "until the peak fits, or use a method that takes hard "
             "constraints, which is exactly what MPC is for."
             if over else
             f"<b>k₁ = {k1:.0f}, k₂ = {k2:.1f}, and you never named a "
             f"pole.</b> They came from three tolerances and one matrix "
             f"equation. J* = x₀ᵀPx₀ = {res.cost:.3g} is the entire remaining "
             f"cost from 2 cm — the number a critic network spends its life "
             f"trying to approximate. Closed-loop ζ = {z_cl:.2f} and peak "
             f"force {pk:.1f} N, inside the {um:.1f} N you declared."))

        c = self.c3
        c.clear()
        a1, a2, a3 = c.axes
        a1.plot(ts, xs[:, 0] * 100, color=theme.GOOD, lw=2.0)
        a1.axhline(xm * 100, color=theme.WARN, lw=1.1, ls=":",
                   label="declared tolerance")
        a1.axhline(-xm * 100, color=theme.WARN, lw=1.1, ls=":")
        a1.axhline(0, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a1.set_xlabel("time (s)")
        a1.set_ylabel("position (cm)")
        a1.set_title("released from 2 cm", fontsize=9)
        c.legend(a1, loc="upper right")

        a2.plot(ts, us[:, 0], color=theme.BAD, lw=1.8)
        a2.axhline(um, color=theme.WARN, lw=1.2, ls="--", label="budget")
        a2.axhline(-um, color=theme.WARN, lw=1.2, ls="--")
        a2.set_xlabel("time (s)")
        a2.set_ylabel("force (N)")
        a2.set_title("R is the price of this", fontsize=9)
        c.legend(a2, loc="upper right")

        lim = max(4.0, wn_cl * 1.6)
        _splane(a3, res.poles, lim=lim, marker_label="LQR poles")
        op = np.linalg.eigvals(np.asarray(ss.A))
        a3.scatter([p.real for p in op], [p.imag for p in op], marker="x",
                   s=60, linewidths=1.6, color=theme.TEXT_FAINT, zorder=4,
                   label="open loop")
        a3.set_title("nobody placed these", fontsize=8.5)
        c.legend(a3, loc="upper left")
        c.refresh()

    # ------------------------------------------------------------------
    def _redraw_lqr_sea(self):
        q3 = 10 ** (self.s_q3.value() / 10.0)
        q4 = 10 ** (self.s_q4.value() / 10.0)
        qd = 10 ** (self.s_qd.value() / 10.0)
        r = 10 ** (self.s_ru.value() / 10.0)
        self.l_q3.setText(f"{q3:.3g}")
        self.l_q4.setText(f"{q4:.3g}")
        self.l_qd.setText(f"{qd:.3g}")
        self.l_ru.setText(f"{r:.3g}")

        jm, jl, k = 0.02, 0.25, 400.0
        ss = sea_ss(jm, jl, k)
        Q = np.diag([1e-3, 1e-3, q3, q4])
        c_def = np.array([1.0, 0.0, -1.0, 0.0]).reshape(-1, 1)
        Q = Q + qd * (c_def @ c_def.T)
        R = np.array([[r]])
        x0 = np.array([0.0, 0.0, 0.20, 0.0])
        res = lqr_design(ss, Q, R, x0=x0)
        K = res.K

        ts, xs, us, _s = simulate_feedback(ss, K, x0, dur=1.5, dt=2e-4)
        defl = np.degrees(xs[:, 0] - xs[:, 2]) if len(xs) else np.zeros(1)
        pk_def = float(np.max(np.abs(defl)))
        pk_tau = float(np.max(np.abs(us))) if len(us) else 0.0
        # load settling to 2% of its initial displacement
        band = 0.02 * abs(x0[2])
        ts_set = None
        for i in range(len(ts) - 1, -1, -1):
            if abs(xs[i, 2]) > band:
                ts_set = ts[min(i + 1, len(ts) - 1)]
                break
        fastest = min(res.poles, key=lambda p: p.real)

        self.st_sdef.set(f"{pk_def:.1f}°")
        self.st_sdef.set_color(theme.BAD if pk_def > 25 else theme.VIOLET)
        self.st_stau.set(f"{pk_tau:.1f} N·m")
        self.st_sts.set("—" if ts_set is None else f"{ts_set:.2f} s")
        self.st_scost.set(f"{res.cost:.3g}")
        self.st_sfast.set(f"{fastest.real:.0f} 1/s")
        self.st_sfast.set_color(theme.BAD if fastest.real < -2000
                                else theme.WARN)

        self.mat4.setText(
            _matrix_html(Q, "Q", fmt="{:.3g}", colour=theme.VIOLET) +
            _matrix_html(K, "K", fmt="{:+.1f}", colour=theme.ACCENT) +
            f"<span style='color:{theme.TEXT_FAINT}'>state order: "
            "θ<sub>m</sub>, θ̇<sub>m</sub>, θ<sub>l</sub>, θ̇<sub>l</sub>"
            "&nbsp;·&nbsp; output torque = k·deflection = "
            f"{k*math.radians(pk_def):.1f} N·m peak</span>")

        if q3 < 1e-2 and q4 < 1e-2:
            self.t4.setText(
                "<b>You put weight only on the motor states.</b> Look at the "
                "left panel: the motor is beautifully behaved and the load is "
                "still ringing. The optimiser did exactly what you asked and "
                "the machine is worse for it. This is the failure mode of "
                "every well-posed optimisation — <b>it optimises the thing "
                "you weighted, not the thing you wanted</b> — and on a SEA "
                "the thing you wanted is on the far side of a spring from the "
                "thing you measured.")
        elif qd > 10 * q3:
            self.t4.setText(
                f"<b>Deflection is dominating the cost, so peak deflection is "
                f"held to {pk_def:.1f}° and peak output torque to "
                f"{k*math.radians(pk_def):.1f} N·m.</b> The load settles more "
                f"slowly in exchange, which is the trade you asked for. Note "
                f"what just happened: <b>you constrained output torque by "
                f"weighting a state</b>. Pole placement has no vocabulary for "
                "that at all, and it is how a spring — or a harmonic drive, "
                "or a tendon — gets protected from its own controller.")
        else:
            self.t4.setText(
                f"<b>Load-dominated weighting.</b> Peak deflection "
                f"{pk_def:.1f}° = {k*math.radians(pk_def):.1f} N·m of output "
                f"torque, fastest closed-loop pole at {fastest.real:.0f} 1/s. "
                f"Watch that last number as you cheapen torque (R down): the "
                f"optimiser will place a pole at several thousand rad/s "
                f"without hesitation, because nothing in the cost knows about "
                "your sample rate. LQR respects your torque budget and knows "
                "nothing whatsoever about your loop rate — that check is "
                "still yours to make, on page 1's terms.")

        c = self.c4
        c.clear()
        a1, a2, a3 = c.axes
        a1.plot(ts, np.degrees(xs[:, 2]), color=theme.GOOD, lw=2.0,
                label="load θ_l")
        a1.plot(ts, np.degrees(xs[:, 0]), color=theme.ACCENT, lw=1.4, ls="--",
                label="motor θ_m")
        a1.axhline(0, color=theme.TEXT_FAINT, lw=1.0, ls=":")
        a1.set_xlabel("time (s)")
        a1.set_ylabel("angle (°)")
        a1.set_title("load released from 11.5°", fontsize=8.5)
        c.legend(a1, loc="upper right")

        a2.plot(ts, defl, color=theme.VIOLET, lw=1.9, label="deflection")
        a2.set_xlabel("time (s)")
        a2.set_ylabel("deflection (°)")
        a2.set_title(f"= output torque / {k:.0f}", fontsize=8.5)
        c.legend(a2, loc="upper right")

        a3.plot(ts, us[:, 0], color=theme.BAD, lw=1.8)
        a3.axhline(0, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a3.set_xlabel("time (s)")
        a3.set_ylabel("motor τ (N·m)")
        a3.set_title("R is the price of this", fontsize=8.5)
        c.refresh()
