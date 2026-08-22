"""
Controller design -- the four pages that answer "the poles are in the wrong
place, now what?"

  1  Stabilising          what feedback actually DOES to poles, and why the
                          derivative term is the one that buys stability
  2  Lead, Lag & Notch    shaping the frequency response on purpose
  3  State Feedback       place every pole at once -- if you are allowed to
  4  Observers            estimate the states you cannot measure, including
                          the external torque nobody sensed

The previous section was diagnosis: where are the poles, how close to the edge
am I. This one is treatment. The through-line is a single sentence:

    A controller cannot change the plant. It can only move the plant's poles,
    and it does that by adding poles and zeros of its own.

Everything below -- P, I, D, lead, lag, notch, state feedback -- is a
different way of choosing what to add.
"""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel

from ctrlcore.linear import (
    TF,
    bode,
    critical_gain,
    lead,
    lead_phase_deg,
    log_freqs,
    lqr,
    margins,
    notch,
    overshoot_fraction,
    pid_tf,
    place_poles,
    poly_add,
    poly_mul,
    poly_roots,
    root_locus,
    run_velocity_observer,
    settling_time,
    StateSpace,
    step_metrics,
    step_response,
)
from ctrlcore.nonlinear import Pendulum
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


# ==========================================================================
# PAGE -- stabilising
# ==========================================================================

class StabilisingPage(Page):
    TITLE = "Making It Stable"
    SUBTITLE = ("Feedback does not change the plant — it moves the plant's "
                "poles. Which term moves them where, and why D is the one that "
                "buys stability.")
    SECTION = SECTION
    NOTES = "design"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._crit_cache: dict[str, float] = {}

        self.add(callout(
            "<b>The one equation this page is about.</b> Close a unity loop "
            "around L(s) = num/den and the closed-loop poles are the roots "
            "of<br><br>"
            "&nbsp;&nbsp;&nbsp;&nbsp;<b>den(s) + K·num(s) = 0</b><br><br>"
            "Read what that says. The open-loop poles were the roots of den "
            "alone. Turning K up mixes num into den, and the roots <b>move</b>. "
            "Feedback is a pole-relocation machine, and the only question in "
            "controller design is where you want them to end up.", "key"))

        r = Card("the root locus, and its two endpoints")
        r.add(body(
            "Sweep K from 0 to ∞ and trace the roots. Two facts fall straight "
            "out of the equation above and they are worth more than the "
            "sketching rules:<br><br>"
            "&nbsp;&nbsp;• <b>K → 0:</b> den dominates, so the closed-loop poles "
            "<i>are</i> the open-loop poles. Every branch <b>starts at a "
            "pole</b>.<br>"
            "&nbsp;&nbsp;• <b>K → ∞:</b> num dominates, so the roots go to the "
            "roots of num. Every branch <b>ends at a zero</b> — and if there "
            "are not enough zeros, the leftover branches run off to infinity "
            "along asymptotes."))
        r.add(callout(
            "<b>And that is the whole reason a derivative term stabilises "
            "things.</b> A PD controller K<sub>p</sub> + K<sub>d</sub>s is a "
            "<b>zero</b> at s = −K<sub>p</sub>/K<sub>d</sub>. A zero is a "
            "<i>destination</i>: it reaches out and pulls the locus toward "
            "itself. Put it in the left half plane and it drags the closed-loop "
            "poles left with it — which is damping.<br><br>"
            "Move the zero closer to the origin (raise K<sub>d</sub> relative to "
            "K<sub>p</sub>) and it pulls harder. That is the entire mechanism, "
            "and it is why \"add some D\" is the standard answer to \"it's "
            "ringing\".", "key"))
        self.add(r)

        t = Card("what each term adds, and what it costs")
        t.add(body(
            "<table cellpadding='6'>"
            "<tr><td><b>Term</b></td><td><b>Adds</b></td><td><b>Effect on the "
            "poles</b></td><td><b>Price</b></td></tr>"
            "<tr><td><b>P</b> &nbsp; K<sub>p</sub></td><td>nothing — pure gain</td>"
            "<td>slides the poles <i>along</i> the existing locus, faster and "
            "less damped</td>"
            "<td>on a 3rd-order plant it eventually crosses into the right half "
            "plane; and noise straight to the motor</td></tr>"
            "<tr><td><b>D</b> &nbsp; K<sub>d</sub>s</td>"
            "<td>a <b>zero</b> at −K<sub>p</sub>/K<sub>d</sub></td>"
            "<td>pulls the locus <b>left</b> → damping, and +90° of phase "
            "<i>lead</i></td>"
            "<td>amplifies noise ∝ frequency; must be filtered, and the filter "
            "adds a pole back</td></tr>"
            "<tr><td><b>I</b> &nbsp; K<sub>i</sub>/s</td>"
            "<td>a <b>pole at the origin</b> (plus a zero)</td>"
            "<td>drags the locus <b>right</b> → less damped, closer to the "
            "edge</td>"
            "<td>−90° of phase at low frequency, and windup</td></tr>"
            "</table>"))
        t.add(body(
            "So the familiar advice — \"P for speed, D for damping, I only if "
            "you must\" — is not folklore. It is a statement about which "
            "direction each term drags the roots.", dim=True))
        self.add(t)

        # ---- interactive 1 ----------------------------------------------
        i = Card("sweep the gain and watch the roots migrate")
        i.add(body(
            "The grey trace is the whole locus; the crosses are where the poles "
            "sit at your current gain. The three-pole plant is the interesting "
            "one — take K past the critical value and watch a branch cross into "
            "the red half.", dim=True))
        self.cmb = QComboBox()
        for lab, key in (
                ("3 poles:  1/((s+1)(s+2)(s+3))", "three"),
                ("joint + integrator:  1/(s(s+1)(s+2))", "integ"),
                ("rigid joint:  1/(0.25s² + 0.4s)", "joint"),
                ("with PD zero:  (s+8)/(s(s+1)(s+2))", "pd")):
            self.cmb.addItem(lab, key)
        self.cmb.currentIndexChanged.connect(self._redraw_locus)
        i.add_layout(labelled("Plant", self.cmb, width=60))
        self.s_k = slider(1, 1500, 150)          # x0.1
        self.l_k = QLabel()
        i.add_layout(slider_row("gain K (×0.1)", self.s_k, self.l_k))
        self.st_worst = Stat("worst pole", "--", theme.ACCENT)
        self.st_zeta = Stat("damping ζ", "--", theme.VIOLET)
        self.st_stable = Stat("verdict", "--", theme.GOOD)
        self.st_kcrit = Stat("critical gain", "--", theme.BAD)
        i.add_layout(stat_row(self.st_worst, self.st_zeta, self.st_stable,
                              self.st_kcrit))
        self.c1 = MplCanvas(width=7.4, height=3.2, ncols=2)
        i.add(self.c1)
        self.add(i)
        self.s_k.valueChanged.connect(self._redraw_locus)
        self._redraw_locus()

        # ---- K_p, K_i, K_d, one at a time --------------------------------
        self.add(hline())
        self.add(title("K_p, K_i, K_d — which direction each one drags the "
                       "poles, and what that costs you"))

        wy = Card("why each term moves the poles the way it does — the "
                  "mechanism, not the table")
        wy.add(body(
            "The table above states the directions. Here is <i>why</i> each one "
            "is forced, in terms of den + K·num, so none of it has to be "
            "memorised."))
        wy.add(body(
            "<b>K<sub>p</sub> — pure gain, no new poles or zeros. It slides the "
            "roots along a track that was already fixed.</b><br>"
            "The locus is drawn by the plant and the other terms; K<sub>p</sub> "
            "only decides how far along it you sit. For a joint J s² + b s, "
            "closing P gives J s² + b s + K<sub>p</sub>, so ω<sub>n</sub> = "
            "√(K<sub>p</sub>/J) rises with gain while ζ = b/(2√(K<sub>p</sub>J)) "
            "<b>falls</b>. The poles travel out along a circle of growing radius "
            "and swing upward toward the imaginary axis: <b>faster, and less "
            "damped, simultaneously.</b> That trade is not a tuning "
            "failure — it is arithmetic. Raising stiffness without raising "
            "damping always buys speed with ringing.<br><br>"
            "<b>K<sub>d</sub> — adds a zero at −K<sub>p</sub>/K<sub>d</sub>, and "
            "a zero is a destination.</b><br>"
            "Branches end at zeros, so a left-half-plane zero reaches out and "
            "bends the locus toward itself — the poles move <b>left</b>, which "
            "is damping. In the same joint, D shows up as J s² + (b + "
            "K<sub>d</sub>)s + K<sub>p</sub>: it adds directly to the physical "
            "friction. Your derivative gain <i>is</i> a damper, in the same "
            "units, doing the same job.<br><br>"
            "<b>K<sub>i</sub> — adds a pole at the origin, and the poles have to "
            "get out of its way.</b><br>"
            "A pole at s = 0 is a branch start sitting at the worst possible "
            "place, and the extra −90° of phase it contributes at low frequency "
            "has to be paid for somewhere. The locus is pushed <b>right</b>, "
            "toward the imaginary axis: less damping, less margin, and on a "
            "high-order plant a lower critical gain than you had without it. In "
            "exchange you get the one thing the other two terms cannot give — "
            "zero steady-state error against a constant load."))
        wy.add(callout(
            "<b>The performance consequences, stated as the four numbers you "
            "actually care about.</b><br><br>"
            "&nbsp;&nbsp;• <b>Speed (rise time, bandwidth)</b> — set by how far "
            "left/out the dominant poles are. K<sub>p</sub> buys it directly; "
            "K<sub>d</sub> lets you keep buying it without ringing.<br>"
            "&nbsp;&nbsp;• <b>Overshoot / ringing</b> — set by the poles' angle "
            "from the real axis (ζ). K<sub>d</sub> improves it; K<sub>p</sub> "
            "and K<sub>i</sub> both make it worse.<br>"
            "&nbsp;&nbsp;• <b>Steady-state error</b> — set by the loop's DC "
            "gain. Only an integrator drives it to exactly zero; K<sub>p</sub> "
            "only shrinks it, as 1/(1+K<sub>p</sub>·plant DC gain).<br>"
            "&nbsp;&nbsp;• <b>Noise and effort</b> — K<sub>d</sub> multiplies "
            "sensor noise by frequency and puts it straight into the motor, "
            "which is why K<sub>d</sub> is capped in practice by encoder "
            "resolution and current-loop headroom rather than by "
            "stability.", "key"))
        self.add(wy)

        # ---- interactive: PID on a real joint -----------------------------
        i3 = Card("move one gain at a time and watch all three consequences")
        i3.add(body(
            "Plant: the rigid joint from the linear-systems pages, "
            "1/(0.25 s² + 0.4 s) — one integrator already present, which is why "
            "a plain P controller can hold a position at all. The D term is "
            "filtered (τ<sub>d</sub> = 5 ms) because an unfiltered derivative is "
            "not buildable; that filter is itself a pole, and you can watch it "
            "on the map.<br><br>"
            "<b>Left:</b> the closed-loop poles (×) and zeros (○). <b>Middle:</b> "
            "step response, so you can read overshoot and settling. "
            "<b>Right:</b> the response to a constant torque disturbance applied "
            "at t = 0 — a hand pushing on the joint, or gravity on a load.<br><br>"
            "<b>Four experiments, in this order:</b><br>"
            "&nbsp;&nbsp;<b>1.</b> Raise K<sub>p</sub> alone. Poles swing "
            "outward and upward, response gets faster and starts ringing, "
            "disturbance droop shrinks but never reaches zero.<br>"
            "&nbsp;&nbsp;<b>2.</b> Now add K<sub>d</sub>. Poles march left and "
            "down toward the real axis, ringing dies, and you can push "
            "K<sub>p</sub> higher than before.<br>"
            "&nbsp;&nbsp;<b>3.</b> Add K<sub>i</sub>. Watch the disturbance "
            "panel return to zero — and watch the poles creep back toward the "
            "imaginary axis and the overshoot grow. That is the trade, "
            "visible.<br>"
            "&nbsp;&nbsp;<b>4.</b> Push K<sub>i</sub> far with K<sub>d</sub> = "
            "0. The verdict flips to UNSTABLE. An integrator is the only one of "
            "the three that can destabilise this plant on its own.", dim=True))
        self.s_ikp = slider(5, 600, 120)
        self.s_iki = slider(0, 800, 0)
        self.s_ikd = slider(0, 400, 40)          # x0.1
        self.l_ikp, self.l_iki, self.l_ikd = QLabel(), QLabel(), QLabel()
        i3.add_layout(slider_row("K_p", self.s_ikp, self.l_ikp))
        i3.add_layout(slider_row("K_i", self.s_iki, self.l_iki))
        i3.add_layout(slider_row("K_d (×0.1)", self.s_ikd, self.l_ikd))
        self.st_iover = Stat("overshoot", "--", theme.WARN)
        self.st_iset = Stat("settling (2%)", "--", theme.GOOD)
        self.st_isse = Stat("droop under load", "--", theme.BAD)
        self.st_izeta = Stat("dominant ζ", "--", theme.VIOLET)
        self.st_ipm = Stat("phase margin", "--", theme.ACCENT)
        i3.add_layout(stat_row(self.st_iover, self.st_iset, self.st_isse,
                               self.st_izeta, self.st_ipm))
        self.c3 = MplCanvas(width=7.6, height=2.9, ncols=3)
        i3.add(self.c3)
        self.t3 = body("", dim=True)
        i3.add(self.t3)
        self.add(i3)
        for s in (self.s_ikp, self.s_iki, self.s_ikd):
            s.valueChanged.connect(self._redraw_pid)
        self._redraw_pid()

        # ---- the unstable case ------------------------------------------
        self.add(hline())
        self.add(title("The genuinely unstable case: an inverted pendulum"))

        p = Card("why proportional gain alone can never do it")
        p.add(body(
            "Linearise a pendulum about upright. The gravity term flips sign — "
            "it now pushes the pendulum <i>away</i> from the equilibrium — and "
            "the plant has a pole in the right half plane:"))
        p.add(math_label(r"J\ddot\theta - mgl\,\theta = \tau "
                         r"\qquad\Longrightarrow\qquad "
                         r"s = \pm\sqrt{mgl/J} = \pm\sqrt{g/l}", 17))
        p.add(body(
            "Now try pure proportional feedback, τ = −K<sub>p</sub>θ:"))
        p.add(math_label(r"J s^2 + (K_p - mgl) = 0 \qquad\Longrightarrow\qquad "
                         r"s = \pm j\sqrt{(K_p - mgl)/J}", 16))
        p.add(body(
            "<b>Look at what happened.</b> With K<sub>p</sub> &lt; mgl the poles "
            "stay real and one is still in the right half plane — the pendulum "
            "falls, only slower. With K<sub>p</sub> &gt; mgl the poles are "
            "<b>purely imaginary</b>: the pendulum no longer falls, it "
            "<i>oscillates about upright forever</i>. Marginal, never stable, "
            "for any gain whatsoever.<br><br>"
            "There is no damping term in the equation, so nothing removes "
            "energy. Add one:"))
        p.add(math_label(r"J s^2 + K_d s + (K_p - mgl) = 0", 16))
        p.add(body(
            "<b>Stable if and only if K<sub>d</sub> &gt; 0 <i>and</i> "
            "K<sub>p</sub> &gt; mgl.</b> Two conditions, both necessary, both "
            "physically obvious in hindsight: you must push back harder than "
            "gravity pulls (K<sub>p</sub> &gt; mgl), and you must remove energy "
            "(K<sub>d</sub> &gt; 0).<br><br>"
            "This is the smallest complete example of why D is not optional. "
            "For a balancing robot it is not a tuning nicety — without it the "
            "machine cannot stand up at any gain.", dim=True))
        self.add(p)

        # ---- interactive 2 ----------------------------------------------
        i2 = Card("balance it yourself")
        i2.add(body(
            "A 0.5 m pendulum, released 20° from upright. The dashed line marks "
            "K<sub>p</sub> = mgl — below it no amount of damping helps. Set "
            "K<sub>d</sub> = 0 with K<sub>p</sub> above the line and watch the "
            "marginal oscillation the algebra predicted.", dim=True))
        self.s_pkp = slider(0, 400, 120)
        self.s_pkd = slider(0, 200, 0)           # x0.1
        self.l_pkp, self.l_pkd = QLabel(), QLabel()
        i2.add_layout(slider_row("K_p (N·m/rad)", self.s_pkp, self.l_pkp))
        i2.add_layout(slider_row("K_d (×0.1)", self.s_pkd, self.l_pkd))
        self.st_mgl = Stat("mgl (must beat)", "--", theme.WARN)
        self.st_ppole = Stat("worst pole", "--", theme.ACCENT)
        self.st_pver = Stat("verdict", "--", theme.GOOD)
        self.st_prhp = Stat("open-loop RHP pole", "--", theme.BAD)
        i2.add_layout(stat_row(self.st_mgl, self.st_ppole, self.st_pver,
                               self.st_prhp))
        self.c2 = MplCanvas(width=7.4, height=3.2, ncols=2)
        i2.add(self.c2)
        self.add(i2)
        for s in (self.s_pkp, self.s_pkd):
            s.valueChanged.connect(self._redraw_pend)
        self._redraw_pend()

        w = Card("two rules that come with unstable plants")
        w.add(body(
            "<b>1 · You must be faster than the instability.</b> A right-half "
            "plane pole at s = +p grows like e<sup>pt</sup>, doubling every "
            "ln2/p seconds. Your loop crossover has to sit comfortably above p "
            "— a common rule is ω<sub>gc</sub> &gt; 2p — or the divergence "
            "outruns the correction.<br><br>"
            "For a 1 m inverted pendulum, p = √(9.81/1) = 3.1 rad/s and the "
            "doubling time is <b>220 ms</b>. That single number is why a "
            "balance controller must run in the kHz and why a 200 ms perception "
            "stall is a fall. It is the Real-Time page's argument arriving from "
            "the other direction.<br><br>"
            "<b>2 · Never cancel an unstable pole with a zero.</b> On paper "
            "(s−p)/(s−p) = 1 and the problem disappears. In reality the "
            "cancellation is never exact, and what you have built is a system "
            "whose unstable mode is <i>invisible from the output</i> — it grows "
            "silently until something saturates. The pole must be <b>moved</b> "
            "by feedback, not hidden."))
        self.add(w)

        w2 = Card("\"you must be faster than the instability\" — unpacked, "
                  "because every clause is a separate fact")
        w2.add(body(
            "<b>e<sup>pt</sup>, and what p physically is.</b> A pole at s = +p "
            "means the error obeys ė = p·e — the bigger the error, the faster "
            "it grows. Nothing about that is a controller property; it is the "
            "hardware falling over. Solve it and the error is e<sub>0</sub>"
            "e<sup>pt</sup>: multiplied by e every 1/p seconds, and doubled "
            "every <b>ln2/p</b> seconds. For an inverted pendulum p = √(g/l), "
            "so <i>shorter is worse</i> — a 1 m pendulum doubles its lean angle "
            "every 220 ms, a 0.25 m one every 110 ms. This is why a Segway is "
            "easier to balance than a broom handle, and why balancing a pencil "
            "on your finger is nearly impossible."))
        w2.add(body(
            "<b>Why crossover is the number that has to beat it.</b> "
            "ω<sub>gc</sub> is where the loop gain passes 1 — above it the loop "
            "has less than unit authority and is, for practical purposes, not "
            "correcting anything. So 1/ω<sub>gc</sub> is roughly how long the "
            "loop takes to respond to a change. Put that next to the doubling "
            "time: <b>if the error doubles faster than the loop can react, each "
            "correction is aimed at a state the robot has already left</b>, and "
            "you are always applying yesterday's answer to a bigger problem. "
            "The margin you need for that race is where ω<sub>gc</sub> &gt; 2p "
            "comes from — a factor of two is the minimum anyone quotes, and 5–10× "
            "is what gets built."))
        w2.add(callout(
            "<b>And this is the sentence that connects to page 1.</b> Your "
            "crossover is bounded above by sampling and delay — roughly "
            "f<sub>s</sub>/10 to f<sub>s</sub>/20, minus whatever your latency "
            "costs. The instability rate p is bounded below by physics you "
            "cannot negotiate with. <b>The controller must fit in the gap, and "
            "when there is no gap there is no controller</b> — no gain, no "
            "algorithm, no learning method closes it. That is the real-time "
            "page's claim arriving as a hard design constraint rather than "
            "advice.", "warn"))
        self.add(w2)

        i4 = Card("race the divergence: pick a machine, pick a loop rate")
        i4.add(body(
            "Left: the error growing as e<sup>pt</sup>, with the doubling time "
            "marked, against the loop's response time 1/ω<sub>gc</sub>. Right: "
            "where your crossover sits relative to the p and 2p lines. The "
            "sample rate slider caps the crossover through the f<sub>s</sub>/15 "
            "rule from page 1, so you can watch a perfectly reasonable "
            "controller become impossible by lowering the loop rate "
            "alone.", dim=True))
        self.s_len = slider(5, 200, 100)          # x0.01 m, pendulum length
        self.s_fs = slider(20, 2000, 500)         # Hz
        self.l_len, self.l_fs = QLabel(), QLabel()
        i4.add_layout(slider_row("pendulum length (cm)", self.s_len,
                                 self.l_len))
        i4.add_layout(slider_row("loop rate f_s (Hz)", self.s_fs, self.l_fs))
        self.st_p = Stat("instability rate p", "--", theme.BAD)
        self.st_dbl = Stat("doubling time", "--", theme.WARN)
        self.st_wgc = Stat("crossover available", "--", theme.ACCENT)
        self.st_ratio2 = Stat("ω_gc / p", "--", theme.VIOLET)
        self.st_race = Stat("verdict", "--", theme.GOOD)
        i4.add_layout(stat_row(self.st_p, self.st_dbl, self.st_wgc,
                               self.st_ratio2, self.st_race))
        self.c4 = MplCanvas(width=7.6, height=2.8, ncols=2)
        i4.add(self.c4)
        self.t4 = body("", dim=True)
        i4.add(self.t4)
        self.add(i4)
        for s in (self.s_len, self.s_fs):
            s.valueChanged.connect(self._redraw_race)
        self._redraw_race()

        self.add(callout(
            "<b>Carry forward.</b> P slides the poles along the locus; D adds a "
            "zero that pulls them left; I adds a pole at the origin that drags "
            "them right. Marginal plants need D. Unstable plants need D "
            "<i>and</i> enough gain, and need the loop to be faster than the "
            "instability. The next page does the same job in the frequency "
            "domain, where it is easier to be quantitative.", "good"))

        self.finish()

    # ------------------------------------------------------------------
    def _redraw_race(self):
        """
        The two clocks that decide whether an unstable plant is controllable
        at all: how fast it diverges, and how fast the loop can answer.
        """
        length = self.s_len.value() / 100.0
        fs = float(self.s_fs.value())
        self.l_len.setText(f"{length*100:.0f} cm")
        self.l_fs.setText(f"{fs:.0f} Hz")

        p = math.sqrt(9.81 / length)                  # rad/s, the RHP pole
        t_double = math.log(2.0) / p
        wgc = 2.0 * math.pi * (fs / 15.0)             # page 1's f_s/15 rule
        ratio = wgc / p
        ok = ratio >= 2.0
        comfy = ratio >= 5.0

        self.st_p.set(f"{p:.2f} 1/s")
        self.st_dbl.set(f"{t_double*1000:.0f} ms")
        self.st_wgc.set(f"{wgc:.0f} rad/s")
        self.st_ratio2.set(f"{ratio:.1f}×")
        self.st_race.set("comfortable" if comfy
                         else ("marginal" if ok else "IMPOSSIBLE"))
        self.st_race.set_color(theme.GOOD if comfy else
                               (theme.WARN if ok else theme.BAD))

        if not ok:
            self.t4.setText(
                f"<b>No controller exists at this loop rate.</b> The lean angle "
                f"doubles every {t_double*1000:.0f} ms, and a {fs:.0f} Hz loop "
                f"buys about {wgc:.0f} rad/s of crossover — under the 2p = "
                f"{2*p:.1f} rad/s floor. Raise the loop rate, or lengthen the "
                "pendulum. Nothing you do inside the controller helps.")
        elif not comfy:
            self.t4.setText(
                f"<b>Marginal.</b> ω<sub>gc</sub>/p = {ratio:.1f}, just over "
                "the factor of two that is quoted as the minimum. It will "
                "balance on a clean day and fall over when a disturbance, a "
                "missed deadline or a modelling error takes a bite out of the "
                "margin. Real balance controllers are built at 5–10×.")
        else:
            self.t4.setText(
                f"<b>Comfortable.</b> ω<sub>gc</sub>/p = {ratio:.1f}, so the "
                f"loop answers roughly {ratio:.0f} times faster than the fall "
                f"develops. Note what happens if you drag the length down: p "
                "rises as 1/√l, the doubling time collapses, and the same "
                "controller runs out of room — the machine got harder, not the "
                "code.")

        c = self.c4
        c.clear()
        a1, a2 = c.axes
        tt = [i * (4.0 * t_double) / 300.0 for i in range(301)]
        a1.plot(tt, [math.exp(p * t) for t in tt], color=theme.BAD, lw=2.2,
                label="error, e^{pt}")
        a1.axhline(2.0, color=theme.TEXT_FAINT, lw=1.0, ls=":")
        a1.axvline(t_double, color=theme.WARN, lw=1.4, ls="--",
                   label=f"doubles at {t_double*1000:.0f} ms")
        a1.axvline(1.0 / wgc, color=theme.ACCENT, lw=1.4,
                   label=f"loop responds in {1000/wgc:.0f} ms")
        a1.set_xlabel("time (s)")
        a1.set_ylabel("error growth (×)")
        a1.set_ylim(0, 8)
        a1.set_title("the race", fontsize=9)
        c.legend(a1, loc="upper left")

        bars = [p, 2.0 * p, wgc]
        cols = [theme.BAD, theme.WARN,
                theme.GOOD if comfy else (theme.WARN if ok else theme.BAD)]
        a2.barh([0, 1, 2], bars, height=0.55, color=cols, alpha=0.7)
        a2.set_yticks([0, 1, 2])
        a2.set_yticklabels(["p — instability", "2p — the floor",
                            "ω_gc — what you have"], fontsize=8)
        a2.set_xlabel("rad/s")
        a2.set_title("crossover must clear the floor", fontsize=9)
        c.refresh()

    # ------------------------------------------------------------------
    def _redraw_pid(self):
        """
        One joint, three gains, three consequences: pole positions, command
        tracking and load rejection. The disturbance panel is the one that
        earns the I term -- nothing else on the page shows what it is for.
        """
        kp = float(self.s_ikp.value())
        ki = float(self.s_iki.value())
        kd = self.s_ikd.value() / 10.0
        self.l_ikp.setText(f"{kp:.0f}")
        self.l_iki.setText(f"{ki:.0f}")
        self.l_ikd.setText(f"{kd:.1f}")

        plant = TF([1.0], [0.25, 0.4, 0.0])          # J s^2 + b s
        # With K_i = 0 the generic PID form still carries s in its denominator,
        # which cancels against its own numerator and leaves a spurious pole at
        # the origin in the closed loop. Build the filtered PD directly instead.
        if ki > 0:
            ctrl = pid_tf(kp, ki, kd, tau_d=0.005)
        else:
            ctrl = TF([kp * 0.005 + kd, kp], [0.005, 1.0])
        l = ctrl * plant
        t_cl = l.feedback()
        poles = poly_roots(t_cl.den)
        stable = all(p.real < -1e-9 for p in poles)

        # load rejection: P / (1 + L) = num_P den_C / (den_C den_P + num_C num_P)
        dist = TF(poly_mul(plant.num, ctrl.den),
                  poly_add(poly_mul(ctrl.den, plant.den),
                           poly_mul(ctrl.num, plant.num)))

        dur = 3.0
        tt, yy = step_response(t_cl, dur, dur / 1500.0)
        yy = [min(max(v, -3.0), 3.0) for v in yy]
        td, yd = step_response(dist, dur, dur / 1500.0, amplitude=1.0)
        yd = [min(max(v, -3.0), 3.0) for v in yd]

        met = step_metrics(tt, yy)
        droop = abs(yd[-1]) if yd else 0.0        # where the load leaves you
        dom = max((p for p in poles if abs(p.imag) > 1e-6),
                  key=lambda p: p.real, default=None)
        if dom is None:
            dom = max(poles, key=lambda p: p.real)
        wn = abs(dom)
        zeta = (-dom.real / wn) if wn > 1e-9 else 0.0
        mg = margins(l)
        # the unwrapped phase can come back a full turn away from the branch
        # the margin is quoted on; fold it back into (-180, 180]
        pm = ((mg.phase_margin_deg + 180.0) % 360.0) - 180.0

        self.st_iover.set(f"{met.overshoot*100:.0f} %" if stable else "--")
        self.st_iover.set_color(theme.WARN if met.overshoot < 0.3 else theme.BAD)
        self.st_iset.set("never" if not stable or math.isinf(met.settling_time)
                         else f"{met.settling_time:.2f} s")
        self.st_isse.set(f"{droop:.4f} rad" if droop > 1e-3 else "0 — rejected")
        self.st_isse.set_color(theme.GOOD if droop <= 1e-3 else theme.BAD)
        self.st_izeta.set(f"{zeta:+.2f}")
        self.st_ipm.set("--" if not stable else f"{pm:.0f}°")
        self.st_ipm.set_color(theme.GOOD if stable and pm > 40 else theme.BAD)

        if not stable:
            msg = ("<b>UNSTABLE.</b> A pole has crossed into the right half "
                   "plane — with K_i large and K_d small, the integrator's "
                   "−90° of low-frequency phase is more than this plant can "
                   "absorb. Add D, or take I back.")
        elif ki <= 0:
            msg = (f"<b>No integrator.</b> The joint holds its commanded angle "
                   f"— the plant's own pole at the origin does that — but "
                   f"under a constant load it settles {droop:.4f} rad away "
                   f"from the target and stays there. K_p only shrinks that "
                   f"droop; nothing here removes it.")
        else:
            msg = (f"<b>Integrator working.</b> The droop is driven to zero: "
                   f"the I term keeps accumulating until the load is exactly "
                   f"cancelled. The price is on the left panel — poles nearer "
                   f"the imaginary axis, ζ = {zeta:.2f} — and on the phase "
                   f"margin stat, {pm:.0f}°.")
        self.t3.setText(msg)

        c = self.c3
        c.clear()
        a_pz, a_st, a_ds = c.axes
        lim = max(6.0, max([abs(p) for p in poles] or [6.0]) * 1.25)
        _splane(a_pz, poles, t_cl.zeros(), lim=lim, marker_label="closed poles")
        a_pz.set_title("closed-loop poles", fontsize=9)

        a_st.plot(tt, yy, color=theme.GOOD if stable else theme.BAD, lw=2.0)
        a_st.axhline(1.0, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a_st.set_xlabel("time (s)")
        a_st.set_ylabel("angle (clipped)")
        a_st.set_title("step command", fontsize=9)

        a_ds.plot(td, yd, color=theme.VIOLET, lw=2.0)
        a_ds.axhline(0.0, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a_ds.set_xlabel("time (s)")
        a_ds.set_ylabel("angle error (rad)")
        a_ds.set_title("1 N·m load applied at t = 0", fontsize=9)
        c.refresh()

    # ------------------------------------------------------------------
    def _plant(self):
        key = self.cmb.currentData()
        if key == "integ":
            return TF([1.0], [1.0, 3.0, 2.0, 0.0])
        if key == "joint":
            return TF([1.0], [0.25, 0.4, 0.0])
        if key == "pd":
            return TF([1.0, 8.0], [1.0, 3.0, 2.0, 0.0])
        return TF([1.0], [1.0, 6.0, 11.0, 6.0])

    def _redraw_locus(self):
        k = self.s_k.value() / 10.0
        self.l_k.setText(f"{k:.1f}")
        plant = self._plant()

        gains = [10 ** (-3 + 6 * i / 179.0) for i in range(180)]
        locus = root_locus(plant, gains)
        here = poly_roots((plant * k).feedback().den)

        worst = max(here, key=lambda p: p.real) if here else complex(0, 0)
        wn = abs(worst)
        z = (-worst.real / wn) if wn > 1e-9 else 0.0
        stable = all(p.real < -1e-9 for p in here)
        self.st_worst.set(f"{worst.real:+.2f}")
        self.st_zeta.set(f"{z:+.2f}")
        self.st_stable.set("stable" if stable else "UNSTABLE")
        self.st_stable.set_color(theme.GOOD if stable else theme.BAD)
        # the critical gain is a property of the PLANT, not of the slider --
        # bisecting for it on every slider move would be pure waste
        key = self.cmb.currentData()
        if key not in self._crit_cache:
            self._crit_cache[key] = critical_gain(plant)
        crit = self._crit_cache[key]
        self.st_kcrit.set("none" if math.isinf(crit) else f"{crit:.2f}")
        self.st_kcrit.set_color(theme.GOOD if math.isinf(crit) else theme.WARN)

        c = self.c1
        c.clear()
        a1, a2 = c.axes
        allr = [p for step in locus for p in step]
        lim = max(4.0, max([abs(p) for p in here + plant.poles()] or [4.0]) * 1.5)
        a1.scatter([p.real for p in allr], [p.imag for p in allr], s=1.2,
                   color=theme.TEXT_FAINT, alpha=0.5)
        _splane(a1, here, plant.zeros(), lim=lim, marker_label="poles now")
        a1.set_title("root locus", fontsize=9)
        c.legend(a1, loc="upper left")

        cl = (plant * k).feedback()
        t, y = step_response(cl, 12.0, 6e-3)
        y = [min(max(v, -4.0), 4.0) for v in y]
        a2.plot(t, y, color=theme.GOOD if stable else theme.BAD, lw=2.0)
        dc = cl.dc_gain()
        if abs(dc) < 4:
            a2.axhline(dc, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a2.set_xlabel("time (s)")
        a2.set_ylabel("closed loop (clipped)")
        a2.set_title("step response", fontsize=9)
        c.refresh()

    def _redraw_pend(self):
        kp = float(self.s_pkp.value())
        kd = self.s_pkd.value() / 10.0
        self.l_pkp.setText(f"{kp:.0f}")
        self.l_pkd.setText(f"{kd:.1f}")

        pend = Pendulum(m=1.0, l=0.5, b=0.0)
        mgl = pend.m * pend.g * pend.l
        J = pend.J
        den = [J, kd, kp - mgl]
        roots = poly_roots(den)
        stable = bool(roots) and all(p.real < -1e-9 for p in roots)
        marginal = bool(roots) and any(abs(p.real) < 1e-9 for p in roots)
        worst = max(roots, key=lambda p: p.real) if roots else complex(0, 0)

        self.st_mgl.set(f"{mgl:.1f} N·m/rad")
        self.st_ppole.set(f"{worst.real:+.2f}")
        self.st_pver.set("stable" if stable else
                         ("marginal" if marginal else "FALLS"))
        self.st_pver.set_color(theme.GOOD if stable else
                               (theme.WARN if marginal else theme.BAD))
        self.st_prhp.set(f"+{pend.unstable_pole_inverted():.2f}")

        # simulate the true nonlinear pendulum about upright
        from ctrlcore.nonlinear import trajectory
        law = lambda th, w, t: -kp * (th - math.pi) - kd * w   # noqa: E731
        ts, th, om, _ = trajectory(pend, math.pi - math.radians(20), 0.0,
                                   duration=6.0, dt=3e-3, tau_fn=law)
        dev = [math.degrees(x - math.pi) for x in th]
        dev = [min(max(v, -200.0), 200.0) for v in dev]

        c = self.c2
        c.clear()
        a1, a2 = c.axes
        a1.plot(ts, dev, color=theme.GOOD if stable else
                (theme.WARN if marginal else theme.BAD), lw=2.0)
        a1.axhline(0, color=theme.TEXT_FAINT, lw=1.1, ls="--",
                   label="upright")
        a1.set_xlabel("time (s)")
        a1.set_ylabel("deviation from upright (°)")
        a1.set_ylim(-200, 200)
        c.legend(a1, loc="upper right")
        lim = max(6.0, max([abs(p) for p in roots] or [6.0]) * 1.4)
        _splane(a2, roots, lim=lim)
        a2.scatter([pend.unstable_pole_inverted()], [0.0], marker="x", s=70,
                   linewidths=2.0, color=theme.BAD, zorder=6,
                   label="open-loop RHP pole")
        a2.set_title("closed-loop poles", fontsize=9)
        c.legend(a2, loc="upper left")
        c.refresh()


# ==========================================================================
# PAGE -- lead, lag, notch
# ==========================================================================

class LeadLagPage(Page):
    TITLE = "Lead, Lag & Notch"
    SUBTITLE = ("Buying phase where you need it, gain where you need it, and "
                "killing one resonance you wish you did not have.")
    SECTION = SECTION
    NOTES = "design"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>Same job as PID, stated in the language that makes it "
            "designable.</b> A PID controller is tuned; a lead-lag compensator "
            "is <i>designed</i> — you write down the phase margin and crossover "
            "frequency you want and solve for the parameters. They are close "
            "relatives:<br><br>"
            "&nbsp;&nbsp;• <b>PD ≈ lead</b> — a zero, plus a pole to keep it "
            "realisable<br>"
            "&nbsp;&nbsp;• <b>PI ≈ lag</b> — a lag whose pole went all the way "
            "to the origin<br>"
            "&nbsp;&nbsp;• <b>PID ≈ lead-lag</b><br><br>"
            "The differences are real but small, and they run in the "
            "compensator's favour: a lead has finite high-frequency gain "
            "(a filtered derivative, by construction), and a lag cannot wind "
            "up.", "key"))

        le = Card("lead — buys phase, costs high-frequency gain")
        le.add(math_label(r"C(s) = K_c\,\frac{s + z}{s + p}, \qquad "
                          r"p = \alpha z, \quad \alpha > 1", 17))
        le.add(body(
            "The zero comes first, so between z and p the phase is positive — "
            "the output <i>leads</i> the input. The peak lead, and where it "
            "sits, are both exact:"))
        le.add(math_label(r"\phi_{max} = \arcsin\frac{\alpha-1}{\alpha+1}, "
                          r"\qquad \omega_{max} = \sqrt{zp}", 17))
        le.add(body(
            "<table cellpadding='6'>"
            "<tr><td><b>α</b></td><td>2</td><td>4</td><td>10</td><td>20</td>"
            "<td>100</td></tr>"
            "<tr><td><b>φ<sub>max</sub></b></td><td>19°</td><td>37°</td>"
            "<td>55°</td><td>65°</td><td>79°</td></tr>"
            "<tr><td><b>HF gain</b></td><td>×2</td><td>×4</td><td>×10</td>"
            "<td>×20</td><td>×100</td></tr>"
            "</table>"))
        le.add(body(
            "<b>Read the third row.</b> The high-frequency gain is exactly α, "
            "and that gain lands on your sensor noise. Past α ≈ 10 the phase "
            "returns collapse while the noise cost keeps climbing linearly — "
            "which is why <b>two cascaded moderate leads beat one aggressive "
            "one</b> when you need more than ~55°.<br><br>"
            "<b>Design procedure</b>, and it is genuinely mechanical:<br>"
            "&nbsp;&nbsp;1. measure the phase margin you have and the one you "
            "want; the difference (plus ~5–10° for the gain shift) is "
            "φ<sub>max</sub><br>"
            "&nbsp;&nbsp;2. α = (1+sin φ)/(1−sin φ)<br>"
            "&nbsp;&nbsp;3. put ω<sub>max</sub> <b>at the crossover</b> — that "
            "is the only frequency where phase matters<br>"
            "&nbsp;&nbsp;4. z = ω<sub>max</sub>/√α, p = ω<sub>max</sub>√α",
            dim=True))
        self.add(le)

        la = Card("lag — buys low-frequency gain, costs a little phase")
        la.add(math_label(r"C(s) = K_c\,\frac{s + z}{s + p}, \qquad "
                          r"z = \beta p, \quad \beta > 1", 17))
        la.add(body(
            "The pole comes first now, so the phase dips negative in between — "
            "which is why you keep it well away from crossover. What you are "
            "buying is the <b>β× extra DC gain</b>, and DC gain is exactly what "
            "kills steady-state error.<br><br>"
            "<b>Place the zero about a decade below crossover.</b> By the time "
            "the loop reaches ω<sub>gc</sub> the lag's phase penalty has "
            "recovered to a few degrees, but the low-frequency gain is "
            "permanently β times higher.<br><br>"
            "<b>Lag versus integral action:</b> a pure integrator gives you "
            "<i>infinite</i> DC gain and therefore exactly zero steady-state "
            "error — but it also gives a permanent −90° and a windup problem. "
            "A lag gives you a large finite gain, a small phase cost, and no "
            "windup. When \"nearly zero error\" is enough, it is the better "
            "trade.", dim=True))
        self.add(la)

        # ==================================================================
        # lead/lag ARE PD/PI -- the one-object view, with the limits shown
        # ==================================================================
        self.add(hline())
        self.add(title("They are one object: (s+z)/(s+p), and PD and PI are "
                       "its two limits"))

        one = Card("stop treating these as four compensators — there is one, "
                   "with a dial")
        one.add(body(
            "Look at the two formulas above. <b>They are the same formula.</b> "
            "Both are K(s + z)/(s + p): one zero, one pole, one gain. The only "
            "difference is <b>which of z and p you meet first as frequency "
            "rises</b>, and that single ordering decides the name, the shape, "
            "the phase sign and what the block is for."))
        one.add(math_label(r"C(s) = K\,\frac{s+z}{s+p}"
                           r"\qquad\begin{cases}"
                           r"p > z & \text{zero first} \Rightarrow "
                           r"\textbf{lead} \\[2pt]"
                           r"p < z & \text{pole first} \Rightarrow "
                           r"\textbf{lag}\end{cases}", 17))
        one.add(body(
            "&nbsp;&nbsp;• <b>Zero first (lead).</b> Between z and p the gain "
            "is climbing at +20 dB/decade and the phase is <i>positive</i> — up "
            "to +90°, in practice φ<sub>max</sub> = arcsin((α−1)/(α+1)). Above "
            "p the pole flattens the gain at ×α and hands the phase back. You "
            "used the zero for its phase and paid for it with high-frequency "
            "gain.<br>"
            "&nbsp;&nbsp;• <b>Pole first (lag).</b> Between p and z the gain is "
            "<i>falling</i> from its high DC value and the phase is negative. "
            "Above z the zero stops the fall and returns the phase. You used "
            "the pole for its low-frequency gain and paid for it with a "
            "temporary phase dip you keep away from crossover."))
        one.add(callout(
            "<b>Now push each one to its limit and PD and PI fall out — they "
            "are not analogies, they are the endpoints.</b><br><br>"
            "&nbsp;&nbsp;• <b>Send the lead's pole to infinity (p → ∞) and you "
            "have an ideal PD.</b> Nothing is left to stop the gain climbing, "
            "which is exactly why an ideal D term has infinite high-frequency "
            "gain and cannot be built. <b>The lead's pole IS the derivative "
            "filter</b>, with τ<sub>d</sub> = 1/p — the same filter every real "
            "PID implementation has, named differently.<br><br>"
            "&nbsp;&nbsp;• <b>Send the lag's pole to the origin (p → 0) and you "
            "have an exact PI.</b> DC gain goes to infinity, which is what "
            "drives steady-state error to exactly zero, and the −90° becomes "
            "permanent. <b>The lag's pole IS the integrator, moved slightly off "
            "the origin on purpose</b> — trading \"exactly zero error\" for "
            "\"large finite gain, recoverable phase, and no windup\".", "key"))
        one.add(body(
            "<table cellpadding='7'>"
            "<tr><td><b>Compensator</b></td><td><b>Is</b></td>"
            "<td><b>Exact mapping</b></td><td><b>What the extra pole buys "
            "you</b></td></tr>"
            "<tr><td><b>lead</b>, p &gt; z</td><td>a filtered PD</td>"
            "<td>K<sub>p</sub> = Kz/p, &nbsp; K<sub>d</sub> = K(p−z)/p², "
            "&nbsp; τ<sub>d</sub> = 1/p</td>"
            "<td>finite noise gain (×α instead of ×∞) — the difference between "
            "a controller and a noise amplifier</td></tr>"
            "<tr><td><b>lag</b>, p &lt; z</td><td>a leaky PI</td>"
            "<td>K<sub>p</sub> → K, &nbsp; K<sub>i</sub> → Kz &nbsp;(as p → "
            "0); DC gain = Kz/p</td>"
            "<td>no windup, and a phase penalty that expires below "
            "crossover</td></tr>"
            "<tr><td><b>lead-lag</b></td><td>a PID</td>"
            "<td>both of the above cascaded</td>"
            "<td>both benefits, and two more parameters to place</td></tr>"
            "</table>"))
        self.add(one)

        i0 = Card("one compensator, one pole slider — cross z and watch it "
                  "change species")
        i0.add(body(
            "The pole and zero are yours to place. <b>Drag the pole across the "
            "zero</b> and the block changes from lead to lag in front of you: "
            "the phase bump flips from positive to negative, the gain slope "
            "flips from rising to falling, and the readout switches which PID "
            "form it is equivalent to.<br><br>"
            "<b>Four things to do:</b><br>"
            "&nbsp;&nbsp;<b>1.</b> Put the pole far right of the zero "
            "(p ≫ z). Phase bump is big and positive, high-frequency gain is "
            "large: an aggressive PD. Read the K<sub>d</sub> equivalent "
            "climbing.<br>"
            "&nbsp;&nbsp;<b>2.</b> Slide the pole in toward the zero. "
            "α → 1, the bump shrinks to nothing, and at p = z the compensator "
            "is a plain gain — pole and zero cancel. <b>That is what \"a lead "
            "with α = 1 does nothing\" means, seen rather than asserted.</b><br>"
            "&nbsp;&nbsp;<b>3.</b> Take the pole below the zero. It is now a "
            "lag: DC gain rises, phase dips, and the steady-state error in the "
            "step panel shrinks.<br>"
            "&nbsp;&nbsp;<b>4.</b> Drive the pole to its minimum. DC gain goes "
            "enormous, error goes to nearly zero, and the phase penalty at low "
            "frequency approaches the integrator's permanent −90°. You have "
            "built a PI by moving one slider.<br><br>"
            "<b>Why the droop stat is exactly 1/C(0).</b> This plant already "
            "contains an integrator, so a step <i>command</i> is tracked "
            "perfectly by any of these — but a constant <i>load</i> leaves an "
            "error of 1/(loop DC gain), and the only DC gain in the loop is the "
            "compensator's. That is why the lag shrinks droop by exactly β and "
            "the lead, which has DC gain Kz/p &lt; K, makes it <b>worse</b>. "
            "Lead buys phase, not accuracy; lag buys accuracy, not phase. "
            "Needing both is precisely when you cascade them and call the "
            "result a PID.", dim=True))
        self.s_lz = slider(1, 500, 40)          # x0.1 rad/s -- the zero
        self.s_lp = slider(1, 3000, 800)        # x0.1 rad/s -- the pole
        self.s_lk = slider(1, 400, 80)          # loop gain
        self.l_lz, self.l_lp, self.l_lk = QLabel(), QLabel(), QLabel()
        i0.add_layout(slider_row("zero  −z (×0.1 rad/s)", self.s_lz, self.l_lz))
        i0.add_layout(slider_row("pole  −p (×0.1 rad/s)", self.s_lp, self.l_lp))
        i0.add_layout(slider_row("gain K", self.s_lk, self.l_lk))
        self.st_kind = Stat("species", "--", theme.VIOLET)
        self.st_ratio3 = Stat("α or β", "--", theme.CYAN)
        self.st_equiv = Stat("equivalent to", "--", theme.ACCENT)
        self.st_dcg = Stat("DC gain of C", "--", theme.GOOD)
        self.st_sse = Stat("droop under load", "--", theme.WARN)
        i0.add_layout(stat_row(self.st_kind, self.st_ratio3, self.st_equiv,
                               self.st_dcg, self.st_sse))
        self.c0 = MplCanvas(width=7.6, height=2.9, ncols=3)
        i0.add(self.c0)
        self.t0 = body("", dim=True)
        i0.add(self.t0)
        self.add(i0)
        for s in (self.s_lz, self.s_lp, self.s_lk):
            s.valueChanged.connect(self._redraw_morph)
        self._redraw_morph()

        # ---- interactive 1 ----------------------------------------------
        i = Card("design a lead for a real joint")
        i.add(body(
            "Plant: 1/(0.25s² + 0.4s) with proportional gain — the rigid joint "
            "again. Note the phase margin without the lead, then place "
            "ω<sub>max</sub> at the crossover and raise α. Watch the phase "
            "curve lift exactly where the magnitude crosses 0 dB, and the "
            "overshoot fall.", dim=True))
        self.chk_lead = QCheckBox("lead compensator on")
        self.chk_lead.setChecked(True)
        self.chk_lead.stateChanged.connect(self._redraw_lead)
        i.add(self.chk_lead)
        self.s_kp = slider(1, 400, 80)
        self.s_wmax = slider(5, 800, 200)        # x0.1 rad/s
        self.s_alpha = slider(11, 300, 60)       # x0.1
        self.l_kp, self.l_wmax, self.l_alpha = QLabel(), QLabel(), QLabel()
        i.add_layout(slider_row("K_p", self.s_kp, self.l_kp))
        i.add_layout(slider_row("ω_max (×0.1 rad/s)", self.s_wmax, self.l_wmax))
        i.add_layout(slider_row("α (×0.1)", self.s_alpha, self.l_alpha))
        self.st_phi = Stat("lead available", "--", theme.VIOLET)
        self.st_pm = Stat("phase margin", "--", theme.GOOD)
        self.st_wgc = Stat("crossover", "--", theme.ACCENT)
        self.st_os = Stat("overshoot", "--", theme.WARN)
        i.add_layout(stat_row(self.st_phi, self.st_pm, self.st_wgc, self.st_os))
        self.c1 = MplCanvas(width=7.4, height=4.4, nrows=3)
        i.add(self.c1)
        self.add(i)
        for s in (self.s_kp, self.s_wmax, self.s_alpha):
            s.valueChanged.connect(self._redraw_lead)
        self._redraw_lead()

        # ---- notch -------------------------------------------------------
        self.add(hline())
        self.add(title("Notch — and the reason it is the most dangerous "
                       "compensator here"))

        n = Card("cancelling a resonance you cannot remove")
        n.add(math_label(r"N(s) = \frac{s^2 + 2\zeta_z\omega_0 s + \omega_0^2}"
                         r"{s^2 + 2\zeta_p\omega_0 s + \omega_0^2}, \qquad "
                         r"\zeta_z \ll \zeta_p", 17))
        n.add(body(
            "Unity gain everywhere except a deep narrow hole at ω<sub>0</sub>. "
            "You place the hole on the SEA spring, the belt, the flexible "
            "forearm — the mode that is stopping you raising the gain — and the "
            "loop stops seeing it."))
        n.add(callout(
            "<b>A notch cancels a pole with a zero, and cancellation is a "
            "promise about a number you do not control.</b><br><br>"
            "The resonance moves. The payload changes, the arm extends and its "
            "inertia changes, the structure warms up, the belt ages. When "
            "ω<sub>0</sub> drifts even 10–20%, the zero is no longer on the "
            "pole — and what is left is a very lightly damped mode with your "
            "now-higher loop gain wrapped around it. Notches fail suddenly and "
            "in service, not gradually on the bench.<br><br>"
            "<b>Prefer, in this order:</b> fix it mechanically (stiffen, damp, "
            "shorten); then a plain low-pass below the resonance, which costs "
            "bandwidth but cannot be detuned; then a <i>wide</i> notch, which "
            "tolerates drift; and only then a sharp one.", "warn"))
        self.add(n)

        # ---- interactive 2 ----------------------------------------------
        i2 = Card("notch a resonance, then move the resonance")
        i2.add(body(
            "The plant has a lightly damped mode at 18 Hz. Tune the notch onto "
            "it and watch the gain margin recover. Then use the <b>resonance "
            "drift</b> slider to simulate a payload change — the notch stays "
            "where you put it, and the margin you thought you had disappears.",
            dim=True))
        self.chk_notch = QCheckBox("notch on")
        self.chk_notch.setChecked(True)
        self.chk_notch.stateChanged.connect(self._redraw_notch)
        i2.add(self.chk_notch)
        self.s_nf = slider(80, 320, 180)         # x0.1 Hz — notch centre
        self.s_nw = slider(1, 60, 8)             # x0.01 — notch zero damping
        self.s_drift = slider(-50, 50, 0)        # %
        self.l_nf, self.l_nw, self.l_drift = QLabel(), QLabel(), QLabel()
        i2.add_layout(slider_row("notch at (×0.1 Hz)", self.s_nf, self.l_nf))
        i2.add_layout(slider_row("notch width ζ_z (×0.01)", self.s_nw,
                                 self.l_nw))
        i2.add_layout(slider_row("resonance drift (%)", self.s_drift,
                                 self.l_drift))
        self.st_ngm = Stat("gain margin", "--", theme.ACCENT)
        self.st_npm = Stat("phase margin", "--", theme.GOOD)
        self.st_nres = Stat("actual resonance", "--", theme.WARN)
        i2.add_layout(stat_row(self.st_ngm, self.st_npm, self.st_nres))
        self.c2 = MplCanvas(width=7.4, height=3.6, nrows=2)
        i2.add(self.c2)
        self.add(i2)
        for s in (self.s_nf, self.s_nw, self.s_drift):
            s.valueChanged.connect(self._redraw_notch)
        self._redraw_notch()

        self.finish()

    # ------------------------------------------------------------------
    def _redraw_morph(self):
        """
        K (s+z)/(s+p) with both z and p draggable. p > z is a lead and is a
        filtered PD; p < z is a lag and is a leaky PI. The species readout is
        decided by nothing but the ordering, which is the point.
        """
        z = self.s_lz.value() / 10.0
        p = self.s_lp.value() / 10.0
        k = float(self.s_lk.value())
        self.l_lz.setText(f"{z:.1f}")
        self.l_lp.setText(f"{p:.1f}")
        self.l_lk.setText(f"{k:.0f}")

        c_tf = TF([k, k * z], [1.0, p])
        plant = TF([1.0], [0.25, 0.4, 0.0])
        l = c_tf * plant
        cl = l.feedback()
        # load rejection, as on the previous page: P / (1 + L)
        dist = TF(poly_mul(plant.num, c_tf.den),
                  poly_add(poly_mul(c_tf.den, plant.den),
                           poly_mul(c_tf.num, plant.num)))

        lead_mode = p > z * 1.001
        lag_mode = p < z * 0.999
        ratio = (p / z) if lead_mode else ((z / p) if lag_mode else 1.0)
        dc = c_tf.dc_gain()

        if lead_mode:
            kp_eq = k * z / p
            kd_eq = k * (p - z) / (p * p)
            self.st_kind.set("LEAD")
            self.st_kind.set_color(theme.GOOD)
            self.st_ratio3.set(f"α = {ratio:.1f}")
            self.st_equiv.set(f"PD: Kp {kp_eq:.0f}, Kd {kd_eq:.2f}")
            phi = math.degrees(math.asin((ratio - 1) / (ratio + 1)))
            note = (f"<b>Lead.</b> Peak phase +{phi:.0f}° at ω = "
                    f"{math.sqrt(z*p):.1f} rad/s, high-frequency gain ×"
                    f"{ratio:.1f}. As a PID this is K<sub>p</sub> = "
                    f"{kp_eq:.1f} with K<sub>d</sub> = {kd_eq:.3f} and a "
                    f"derivative filter τ<sub>d</sub> = {1000/p:.1f} ms. Push "
                    "the pole further right and it approaches an ideal, "
                    "unbuildable PD.")
        elif lag_mode:
            self.st_kind.set("LAG")
            self.st_kind.set_color(theme.WARN)
            self.st_ratio3.set(f"β = {ratio:.1f}")
            self.st_equiv.set(f"PI: Kp {k:.0f}, Ki ≈ {k*z:.0f}")
            note = (f"<b>Lag.</b> DC gain {dc:.0f} — that is β = {ratio:.1f} "
                    f"times the high-frequency gain of {k:.0f}, and it is what "
                    "shrinks the droop in the right-hand panel. As a PID this "
                    f"is K<sub>p</sub> ≈ {k:.0f} with K<sub>i</sub> ≈ "
                    f"{k*z:.0f}, except that the integrator leaks: the pole is "
                    f"at −{p:.2f} instead of 0, so the error lands on "
                    "something small rather than exactly zero — and cannot "
                    "wind up.")
        else:
            self.st_kind.set("neither")
            self.st_kind.set_color(theme.TEXT_DIM)
            self.st_ratio3.set("1.0")
            self.st_equiv.set(f"plain gain {k:.0f}")
            note = ("<b>p = z: the pole and the zero cancel exactly</b> and "
                    "what is left is a proportional gain. No phase is bought, "
                    "no DC gain is bought. Both compensators are built out of "
                    "the gap between these two numbers, and here the gap is "
                    "zero.")
        self.st_dcg.set(f"{dc:.0f}")

        dur = 3.0
        tt, yy = step_response(cl, dur, dur / 1200.0)
        yy = [min(max(v, -3.0), 3.0) for v in yy]
        # the droop a load leaves behind is 1/C(0) exactly -- read it off the
        # transfer function rather than off a simulation that a slow lag has
        # not finished settling within the plotted window
        droop = abs(dist.dc_gain())
        self.st_sse.set(f"{droop:.4f} rad" if droop > 1e-4 else "≈ 0")
        self.st_sse.set_color(theme.GOOD if droop < 5e-3 else theme.WARN)
        self.t0.setText(note)

        ws = log_freqs(0.02, 3000.0, 400)
        _, mag, ph = bode(c_tf, ws)

        c = self.c0
        c.clear()
        a_m, a_p, a_s = c.axes
        col = theme.GOOD if lead_mode else (theme.WARN if lag_mode
                                            else theme.TEXT_DIM)
        a_m.semilogx(ws, mag, color=col, lw=2.0)
        for x, lab, cc in ((z, "z", theme.ACCENT), (p, "p", theme.VIOLET)):
            a_m.axvline(x, color=cc, lw=1.2, ls="--")
            a_m.text(x, max(mag), f" {lab}", color=cc, fontsize=8)
        a_m.set_ylabel("|C| (dB)")
        a_m.set_xlabel("ω (rad/s)")
        a_m.set_title("compensator magnitude", fontsize=9)
        a_p.semilogx(ws, ph, color=col, lw=2.0)
        a_p.axhline(0, color=theme.TEXT_FAINT, lw=1.0, ls=":")
        a_p.set_ylabel("phase (deg)")
        a_p.set_xlabel("ω (rad/s)")
        a_p.set_title("+ve = lead, −ve = lag", fontsize=9)
        a_s.plot(tt, yy, color=col, lw=2.0)
        a_s.axhline(1.0, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a_s.set_xlabel("time (s)")
        a_s.set_ylabel("closed loop")
        a_s.set_title("step, with this C on the joint", fontsize=9)
        c.refresh()

    # ------------------------------------------------------------------
    def _redraw_lead(self):
        kp = float(self.s_kp.value())
        wmax = self.s_wmax.value() / 10.0
        alpha = self.s_alpha.value() / 10.0
        on = self.chk_lead.isChecked()
        self.l_kp.setText(f"{kp:.0f}")
        self.l_wmax.setText(f"{wmax:.1f} rad/s")
        self.l_alpha.setText(f"{alpha:.1f}")

        plant = TF([1.0], [0.25, 0.4, 0.0])
        base = plant * kp
        comp = lead(wmax, alpha) if on else TF([1.0], [1.0])
        loop = base * comp

        mg = margins(loop)
        self.st_phi.set(f"{lead_phase_deg(alpha):.0f}°" if on else "off")
        self.st_pm.set("∞" if not math.isfinite(mg.phase_margin_deg)
                       else f"{mg.phase_margin_deg:.0f}°")
        self.st_pm.set_color(theme.GOOD if mg.phase_margin_deg > 40
                             else theme.WARN)
        self.st_wgc.set(f"{mg.wgc:.1f} rad/s" if mg.wgc else "—")
        z_eq = max(0.0, min(1.0, mg.phase_margin_deg / 100.0))
        self.st_os.set(f"{overshoot_fraction(z_eq)*100:.0f}%")

        ws = log_freqs(0.5, 2000.0, 180)
        w0, m0, p0 = bode(base, ws)
        w1, m1, p1 = bode(loop, ws)

        c = self.c1
        c.clear()
        a1, a2, a3 = c.axes
        a1.semilogx(w0, m0, color=theme.TEXT_FAINT, lw=1.3, ls="--",
                    label="no lead")
        a1.semilogx(w1, m1, color=theme.ACCENT, lw=2.0, label="with lead")
        a1.axhline(0, color=theme.TEXT_FAINT, lw=1.0, ls=":")
        if mg.wgc:
            a1.axvline(mg.wgc, color=theme.GOOD, lw=1.2)
        a1.set_ylabel("|L| (dB)")
        c.legend(a1, loc="upper right")
        a2.semilogx(w0, p0, color=theme.TEXT_FAINT, lw=1.3, ls="--")
        a2.semilogx(w1, p1, color=theme.ACCENT, lw=2.0)
        a2.axhline(-180, color=theme.BAD, lw=1.1, ls=":")
        if mg.wgc:
            a2.axvline(mg.wgc, color=theme.GOOD, lw=1.2)
        if on:
            a2.axvline(wmax, color=theme.VIOLET, lw=1.0, ls="-.")
            a2.text(wmax, -170, " ω_max", color=theme.VIOLET, fontsize=7.2)
        a2.set_ylabel("∠L (deg)")
        a2.set_ylim(-280, 10)

        t, y = step_response(loop.feedback(), 1.5, 1e-3)
        a3.plot(t, y, color=theme.GOOD, lw=2.0, label="with lead" if on
                else "no lead")
        t0, y0 = step_response(base.feedback(), 1.5, 1e-3)
        a3.plot(t0, y0, color=theme.TEXT_FAINT, lw=1.3, ls="--",
                label="proportional only")
        a3.axhline(1.0, color=theme.TEXT_FAINT, lw=1.0, ls=":")
        a3.set_ylim(-0.2, 2.2)
        a3.set_xlabel("time (s)   /   ω (rad/s) above")
        a3.set_ylabel("closed loop")
        c.legend(a3, loc="lower right")
        c.refresh()

    def _redraw_notch(self):
        nf = self.s_nf.value() / 10.0
        nz = self.s_nw.value() / 100.0
        drift = self.s_drift.value() / 100.0
        on = self.chk_notch.isChecked()
        self.l_nf.setText(f"{nf:.1f} Hz")
        self.l_nw.setText(f"{nz:.2f}")
        self.l_drift.setText(f"{drift*100:+.0f}%")

        f_res = 18.0 * (1.0 + drift)
        self.st_nres.set(f"{f_res:.1f} Hz")
        wr = 2 * math.pi * f_res
        plant = TF([1.0], [0.25, 0.4, 0.0]) * \
            TF([wr * wr], [1.0, 2 * 0.02 * wr, wr * wr])
        loop = plant * 90.0
        if on:
            w0 = 2 * math.pi * nf
            loop = loop * notch(w0, nz, 0.7)

        mg = margins(loop)
        self.st_ngm.set("∞" if not math.isfinite(mg.gain_margin_db)
                        else f"{mg.gain_margin_db:.1f} dB")
        self.st_ngm.set_color(theme.GOOD if mg.gain_margin_db > 6 else theme.BAD)
        self.st_npm.set("∞" if not math.isfinite(mg.phase_margin_deg)
                        else f"{mg.phase_margin_deg:.0f}°")
        self.st_npm.set_color(theme.GOOD if mg.phase_margin_deg > 30
                              else theme.BAD)

        ws = log_freqs(1.0, 2000.0, 260)
        w, m, p = bode(loop, ws)
        c = self.c2
        c.clear()
        a1, a2 = c.axes
        a1.semilogx(w, m, color=theme.ACCENT, lw=1.9)
        a1.axhline(0, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a1.axvline(wr, color=theme.BAD, lw=1.2, ls="-.", label="resonance")
        if on:
            a1.axvline(2 * math.pi * nf, color=theme.VIOLET, lw=1.1, ls=":",
                       label="notch")
        a1.set_ylabel("|L| (dB)")
        c.legend(a1, loc="upper right")
        a2.semilogx(w, p, color=theme.ACCENT, lw=1.9)
        a2.axhline(-180, color=theme.BAD, lw=1.1, ls=":")
        a2.axvline(wr, color=theme.BAD, lw=1.2, ls="-.")
        if on:
            a2.axvline(2 * math.pi * nf, color=theme.VIOLET, lw=1.1, ls=":")
        a2.set_ylabel("∠L (deg)")
        a2.set_xlabel("ω (rad/s)")
        a2.set_ylim(max(-560, min(p) - 20), 10)
        c.refresh()


# ==========================================================================
# PAGE -- state feedback
# ==========================================================================

class StateFeedbackPage(Page):
    TITLE = "State Feedback & Pole Placement"
    SUBTITLE = ("Stop shaping one transfer function and start placing every "
                "pole at once — if the actuator can reach them.")
    SECTION = SECTION
    NOTES = "design"

    def __init__(self, parent=None):
        super().__init__(parent)

        w = Card("why leave transfer functions at all")
        w.add(math_label(r"\dot x = A x + B u, \qquad y = C x + D u", 17))
        w.add(body(
            "Same systems, different bookkeeping — the poles are now the "
            "<b>eigenvalues of A</b>, which is why control engineers use "
            "\"pole\" and \"eigenvalue\" interchangeably. Three reasons this "
            "form takes over once a robot has more than one joint:<br><br>"
            "&nbsp;&nbsp;• <b>MIMO without pain.</b> Six inputs and six outputs "
            "is a 6×6 matrix, not thirty-six transfer functions with cross "
            "terms.<br>"
            "&nbsp;&nbsp;• <b>It is what nonlinear methods linearise into.</b> "
            "Every Jacobian linearisation, every gain schedule, every MPC model "
            "arrives in this form.<br>"
            "&nbsp;&nbsp;• <b>It exposes the internal states</b> — which is what "
            "an observer estimates and what an RL policy consumes."))
        self.add(w)

        f = Card("the control law, and what it does")
        f.add(math_label(r"u = -Kx \qquad\Longrightarrow\qquad "
                         r"\dot x = (A - BK)x", 18))
        f.add(body(
            "The closed-loop dynamics are the eigenvalues of <b>A − BK</b>. And "
            "here is the theorem that makes the method worth learning:"))
        f.add(title("If (A, B) is controllable, K can place those eigenvalues "
                    "<i>anywhere</i> you choose.", 15))
        f.add(body(
            "Not \"nudge\" — <b>place</b>. Complete authority over the "
            "dynamics, computed in closed form by Ackermann's formula rather "
            "than found by tuning.<br><br>"
            "Compare with PID: three gains shaping one loop, with the poles "
            "landing wherever the algebra puts them. State feedback uses n "
            "gains to place n poles exactly. The catch is that it needs "
            "<b>all n states</b>, which is what the next page is about.",
            dim=True))
        self.add(f)

        ct = Card("controllability — a mechanical property, not a tuning one")
        ct.add(math_label(r"\mathcal{C} = [\,B \;\; AB \;\; A^2B \;\cdots\; "
                          r"A^{n-1}B\,]", 17))
        ct.add(body(
            "Full rank ⇒ every direction in state space can be reached by the "
            "input. Rank deficient ⇒ some combination of states is <b>invisible "
            "to your actuator</b>, and no controller can move it. Ever."))
        ct.add(callout(
            "<b>This is a design verdict, not a control problem.</b> If a mode "
            "is uncontrollable the answer is a different mechanism, a different "
            "actuator placement, or an extra actuator — never a better "
            "algorithm. Two real cases:<br><br>"
            "&nbsp;&nbsp;• A tendon that can only <i>pull</i> gives you "
            "one-sided control authority; the return direction is uncontrolled "
            "and has to come from a spring or an antagonist. That is why "
            "tendon-driven hands are built in antagonistic pairs.<br>"
            "&nbsp;&nbsp;• A perfectly symmetric two-link arm driven at the base "
            "cannot excite its antisymmetric mode. Real designs break the "
            "symmetry on purpose.", "key"))
        self.add(ct)

        # ---- interactive 1 ----------------------------------------------
        i = Card("place the poles of a real joint")
        i.add(body(
            "The plant is J θ̈ + b θ̇ = τ in state form, x = [θ, θ̇]. Choose the "
            "closed-loop ω<sub>n</sub> and ζ you want and read off the gains "
            "that produce them. Notice that K<sub>1</sub> and K<sub>2</sub> are "
            "exactly the K<sub>p</sub> and K<sub>d</sub> of a PD controller — "
            "<b>state feedback on a second-order plant IS PD control</b>, "
            "derived instead of tuned.", dim=True))
        self.s_wn = slider(10, 600, 200)         # x0.1 rad/s
        self.s_z = slider(10, 200, 80)           # x0.01
        self.l_wn, self.l_z = QLabel(), QLabel()
        i.add_layout(slider_row("desired ω_n (×0.1)", self.s_wn, self.l_wn))
        i.add_layout(slider_row("desired ζ (×0.01)", self.s_z, self.l_z))
        self.st_k1 = Stat("K₁  (= K_p)", "--", theme.ACCENT)
        self.st_k2 = Stat("K₂  (= K_d)", "--", theme.VIOLET)
        self.st_ts = Stat("settling", "--", theme.GOOD)
        self.st_peak = Stat("peak torque", "--", theme.BAD)
        i.add_layout(stat_row(self.st_k1, self.st_k2, self.st_ts, self.st_peak))
        self.c1 = MplCanvas(width=7.4, height=3.0, ncols=3)
        i.add(self.c1)
        self.add(i)
        for s in (self.s_wn, self.s_z):
            s.valueChanged.connect(self._redraw_place)
        self._redraw_place()

        self.add(callout(
            "<b>What pole placement does not tell you.</b> Push "
            "ω<sub>n</sub> to the top of that slider and read the peak torque. "
            "The mathematics is perfectly happy; the motor is not. Poles placed "
            "far into the left half plane demand gains that demand torque you "
            "may not have — and the instant the actuator saturates, the "
            "placement is fiction and you are running an unknown nonlinear "
            "controller.<br><br>"
            "Pole placement answers <i>where</i>. It has nothing to say about "
            "<i>how much that costs</i>. Which is the entire motivation for "
            "what follows.", "warn"))

        # ---- LQR ---------------------------------------------------------
        self.add(hline())
        self.add(title("LQR — choosing the poles by choosing what you care "
                       "about"))

        q = Card("the reformulation")
        q.add(math_label(r"J = \int_0^\infty \left( x^T Q x + u^T R u \right) dt",
                         17))
        q.add(body(
            "Instead of naming pole locations — which nobody has real intuition "
            "for beyond second order — you name a <b>price</b>. Q is how much "
            "you dislike state error. R is how much you dislike effort. Minimise "
            "the total and the optimal gain is"))
        q.add(math_label(r"K = R^{-1}B^T P, \qquad "
                         r"A^TP + PA - PBR^{-1}B^TP + Q = 0", 16))
        q.add(body(
            "<b>Why this is the version that gets used.</b> \"How much torque "
            "is a radian of error worth?\" is a question an engineer can "
            "actually answer, and the answer generalises to twelve states "
            "without any new intuition. The resulting closed loop is also "
            "guaranteed stable and comes with famous robustness margins "
            "(≥60° phase margin for the full-state case).<br><br>"
            "It is also, not coincidentally, the exact classical counterpart of "
            "what reinforcement learning does later in this tutor: define a "
            "cost, optimise the policy against it. LQR is the case where the "
            "optimisation can be solved in closed form because the dynamics are "
            "linear and the cost is quadratic. RL is what you reach for when "
            "neither is true.", dim=True))
        self.add(q)

        # ---- interactive 2 ----------------------------------------------
        i2 = Card("move the price of torque")
        i2.add(body(
            "Same joint. Q is fixed; only R — the cost of effort — moves. Cheap "
            "torque buys a fast, high-gain response; expensive torque buys a "
            "gentle one. You are not choosing poles, and yet the poles move.",
            dim=True))
        self.s_r = slider(-30, 30, 0)            # log10 x0.1
        self.s_q = slider(-20, 30, 0)            # log10 x0.1, position weight
        self.l_r, self.l_q = QLabel(), QLabel()
        i2.add_layout(slider_row("log₁₀ R (×0.1)", self.s_r, self.l_r))
        i2.add_layout(slider_row("log₁₀ Q₁₁ (×0.1)", self.s_q, self.l_q))
        self.st_lk1 = Stat("K₁", "--", theme.ACCENT)
        self.st_lk2 = Stat("K₂", "--", theme.VIOLET)
        self.st_lpk = Stat("peak torque", "--", theme.BAD)
        self.st_lts = Stat("settling", "--", theme.GOOD)
        i2.add_layout(stat_row(self.st_lk1, self.st_lk2, self.st_lpk,
                               self.st_lts))
        self.c2 = MplCanvas(width=7.4, height=3.2, ncols=2)
        i2.add(self.c2)
        self.add(i2)
        for s in (self.s_r, self.s_q):
            s.valueChanged.connect(self._redraw_lqr)
        self._redraw_lqr()

        n = Card("one honest gap: state feedback alone does not track")
        n.add(body(
            "u = −Kx drives the state to <b>zero</b>. To follow a non-zero "
            "reference you need one of:<br><br>"
            "&nbsp;&nbsp;• <b>a feedforward gain</b> u = −Kx + N·r, with N "
            "computed from the DC gain. Exact if the model is exact, and "
            "wrong by exactly the model error otherwise.<br>"
            "&nbsp;&nbsp;• <b>an integral state</b>: augment x with ∫(r − y) and "
            "place its pole too. This is state feedback rediscovering the I "
            "term, with anti-windup still your problem.<br>"
            "&nbsp;&nbsp;• <b>a disturbance observer</b> that estimates the "
            "steady load and cancels it — the next page."))
        self.add(n)

        self.finish()

    # ------------------------------------------------------------------
    def _joint_ss(self):
        J, b = 0.25, 0.4
        A = np.array([[0.0, 1.0], [0.0, -b / J]])
        B = np.array([[0.0], [1.0 / J]])
        C = np.array([[1.0, 0.0]])
        D = np.array([[0.0]])
        return StateSpace(A, B, C, D)

    def _sim_regulate(self, K, x0=(0.35, 0.0), dur=2.0, dt=1e-3):
        """Regulate x to zero under u = -Kx. Plain floats: 2 states, and this
        runs on every slider move."""
        ss = self._joint_ss()
        A_cl = np.asarray(ss.A - ss.B @ K)
        a11, a12 = float(A_cl[0, 0]), float(A_cl[0, 1])
        a21, a22 = float(A_cl[1, 0]), float(A_cl[1, 1])
        k1, k2 = float(K[0, 0]), float(K[0, 1])
        x1, x2 = float(x0[0]), float(x0[1])
        ts, th, tau = [], [], []
        for i in range(int(dur / dt)):
            ts.append(i * dt)
            th.append(x1)
            tau.append(-k1 * x1 - k2 * x2)
            d1 = a11 * x1 + a12 * x2
            d2 = a21 * x1 + a22 * x2
            x1 += d1 * dt
            x2 += d2 * dt
        return ts, th, tau

    def _redraw_place(self):
        wn = self.s_wn.value() / 10.0
        z = self.s_z.value() / 100.0
        self.l_wn.setText(f"{wn:.1f} rad/s")
        self.l_z.setText(f"{z:.2f}")

        ss = self._joint_ss()
        if z < 1.0:
            wd = wn * math.sqrt(1 - z * z)
            desired = [complex(-z * wn, wd), complex(-z * wn, -wd)]
        else:
            desired = [complex(-z * wn, 0), complex(-z * wn * 1.001, 0)]
        K = place_poles(ss.A, ss.B, desired)
        self.st_k1.set(f"{K[0,0]:.1f}")
        self.st_k2.set(f"{K[0,1]:.2f}")
        self.st_ts.set(f"{settling_time(z, wn):.3f} s")

        ts, th, tau = self._sim_regulate(K)
        self.st_peak.set(f"{max(abs(v) for v in tau):.0f} N·m")
        self.st_peak.set_color(theme.BAD if max(abs(v) for v in tau) > 60
                               else theme.GOOD)

        c = self.c1
        c.clear()
        a1, a2, a3 = c.axes
        a1.plot(ts, [math.degrees(v) for v in th], color=theme.ACCENT, lw=2.0)
        a1.axhline(0, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a1.set_xlabel("time (s)")
        a1.set_ylabel("θ (°)")
        a1.set_title("regulation from 20°", fontsize=9)
        a2.plot(ts, tau, color=theme.BAD, lw=1.8)
        a2.axhline(0, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a2.set_xlabel("time (s)")
        a2.set_ylabel("τ (N·m)")
        a2.set_title("what it costs", fontsize=9)
        _splane(a3, [complex(v) for v in np.linalg.eigvals(ss.A - ss.B @ K)],
                lim=max(6.0, wn * 1.5))
        a3.scatter([p.real for p in ss.poles()], [p.imag for p in ss.poles()],
                   marker="x", s=60, linewidths=1.6, color=theme.TEXT_FAINT,
                   zorder=4, label="open loop")
        a3.set_title("placed vs open loop", fontsize=8.5)
        c.refresh()

    def _redraw_lqr(self):
        r = 10 ** (self.s_r.value() / 10.0)
        q11 = 10 ** (self.s_q.value() / 10.0)
        self.l_r.setText(f"{r:.3g}")
        self.l_q.setText(f"{q11:.3g}")

        ss = self._joint_ss()
        Q = np.diag([q11, 0.1])
        K = lqr(ss.A, ss.B, Q, np.array([[r]]))
        self.st_lk1.set(f"{K[0,0]:.1f}")
        self.st_lk2.set(f"{K[0,1]:.2f}")

        ts, th, tau = self._sim_regulate(K, dur=3.0)
        pk = max(abs(v) for v in tau)
        self.st_lpk.set(f"{pk:.0f} N·m")
        eig = np.linalg.eigvals(ss.A - ss.B @ K)
        sig = -max(v.real for v in eig)
        self.st_lts.set(f"{4.0/sig:.3f} s" if sig > 1e-6 else "∞")

        c = self.c2
        c.clear()
        a1, a2 = c.axes
        a1.plot(ts, [math.degrees(v) for v in th], color=theme.GOOD, lw=2.0)
        a1.axhline(0, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a1.set_xlabel("time (s)")
        a1.set_ylabel("θ (°)")
        a1.set_title("cheap R = aggressive, expensive R = gentle", fontsize=8.5)
        a2.plot(ts, tau, color=theme.BAD, lw=1.8)
        a2.axhline(0, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a2.set_xlabel("time (s)")
        a2.set_ylabel("τ (N·m)")
        a2.set_title("what it cost", fontsize=9)
        c.refresh()


# ==========================================================================
# PAGE -- observers
# ==========================================================================

class ObserverPage(Page):
    TITLE = "Observers & Observability"
    SUBTITLE = ("You have an encoder and you need velocity, load torque and "
                "everything else. Differentiating is the wrong answer; this is "
                "the right one.")
    SECTION = SECTION
    NOTES = "design"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>The problem, stated concretely.</b> State feedback needs "
            "<i>every</i> state. Your robot joint has one sensor: a position "
            "encoder. So where does θ̇ come from?<br><br>"
            "The obvious answer — subtract consecutive samples and divide by dt "
            "— multiplies the encoder noise by <b>1/dt</b>. At 1 kHz that is a "
            "gain of <b>1000</b> applied directly to your noise, and it is the "
            "same problem the PID page called \"the D term is the noisiest "
            "signal in the loop\". An observer is what you use instead.", "key"))

        e = Card("the Luenberger observer — a simulation that is corrected")
        e.add(math_label(r"\dot{\hat x} = A\hat x + Bu + L\,(y - C\hat x)", 18))
        e.add(body(
            "Read it as two halves:<br><br>"
            "&nbsp;&nbsp;• <b>A x̂ + B u</b> — run a copy of the model in "
            "software, driven by the same input you sent the motor. This is a "
            "pure prediction and it drifts, because the model is wrong.<br>"
            "&nbsp;&nbsp;• <b>L (y − C x̂)</b> — compare the measurement you got "
            "with the one your model predicted, and correct in proportion to "
            "the discrepancy. This is the only place real data enters."))
        e.add(body("Subtract the true dynamics from the estimate and the error "
                   "e = x − x̂ obeys something remarkably clean:"))
        e.add(math_label(r"\dot e = (A - LC)\,e", 18))
        e.add(body(
            "<b>No input, no reference, no coupling to the control.</b> The "
            "estimation error is a little autonomous linear system, and you "
            "choose its poles by choosing L. Place them far left and the "
            "estimate converges fast.", dim=True))
        self.add(e)

        d = Card("duality — the observer is a controller in a mirror")
        d.add(math_label(r"(A, B)\ \text{controllable} \;\Longleftrightarrow\; "
                         r"(A^T, B^T)\ \text{...} \qquad "
                         r"L = \text{place}(A^T, C^T, p)^T", 16))
        d.add(body(
            "Placing eigenvalues of <b>A − LC</b> is the same algebra as placing "
            "eigenvalues of <b>A − BK</b>, transposed. So the observer needs no "
            "new theory and, in this tutor, no new code — "
            "<code>observer_gain</code> literally calls the pole-placement "
            "routine on the transposed system and transposes the answer back."))
        d.add(math_label(r"\mathcal{O} = "
                         r"[\,C;\; CA;\; CA^2;\; \cdots\; CA^{n-1}\,]", 16))
        d.add(body(
            "<b>Observability</b> is the mirror of controllability. Full rank ⇒ "
            "the output history determines the state. Rank deficient ⇒ some "
            "internal motion produces <b>no signature at the sensor at all</b>, "
            "and no observer, no filter and no amount of machine learning can "
            "recover it. Like uncontrollability, it is a sensing-hardware "
            "verdict, not a software one.<br><br>"
            "A concrete robot case: measure only motor-side position on an SEA "
            "and the <i>link</i> deflection is weakly observable — which is "
            "exactly why SEAs carry a second encoder across the spring. The "
            "spring deflection is the force measurement, and you cannot infer "
            "it from the motor side alone.", dim=True))
        self.add(d)

        s = Card("the separation principle — why this is allowed to work")
        s.add(body(
            "Run state feedback on the <i>estimate</i>, u = −K x̂, and you might "
            "reasonably worry that the controller and the observer will fight "
            "each other. They do not. The closed-loop eigenvalues of the "
            "combined system are exactly"))
        s.add(math_label(r"\text{eig}(A - BK) \;\cup\; \text{eig}(A - LC)", 17))
        s.add(body(
            "— the union of the two designs, unchanged. <b>Design them "
            "independently.</b> That is the separation principle, it is why "
            "observer-based control is practical at all, and it is exact for "
            "linear systems (and merely a good approximation for the real "
            "nonlinear robot, which is the usual bargain).<br><br>"
            "<b>How fast should the observer be?</b> Conventionally <b>2–5× the "
            "controller bandwidth</b> — fast enough that estimation lag does "
            "not show up inside the control loop, slow enough that it is still "
            "filtering. Push it faster and L grows, which weights the noisy "
            "measurement more heavily, and you have rebuilt the finite "
            "difference you were trying to avoid. That trade is the whole "
            "design, and the widget below is it.", dim=True))
        self.add(s)

        # ---- interactive 1 -----------------------------------------------
        i = Card("finite difference vs observer, on the same noisy encoder")
        i.add(body(
            "A joint is driven with a 1 Hz torque. Its angle is measured "
            "through an encoder with noise and quantisation. Both velocity "
            "estimates see <b>exactly the same measurements</b>.", dim=True))
        self.s_bw = slider(5, 400, 60)           # rad/s
        self.s_noise = slider(0, 100, 20)        # x1e-5 rad
        self.s_q = slider(0, 100, 0)             # x1e-5 rad, quantisation
        self.l_bw, self.l_noise, self.l_q = QLabel(), QLabel(), QLabel()
        i.add_layout(slider_row("observer bandwidth (rad/s)", self.s_bw,
                                self.l_bw))
        i.add_layout(slider_row("encoder noise (×1e-5)", self.s_noise,
                                self.l_noise))
        i.add_layout(slider_row("quantisation (×1e-5)", self.s_q, self.l_q))
        self.st_efd = Stat("finite-diff error", "--", theme.BAD)
        self.st_eob = Stat("observer error", "--", theme.GOOD)
        self.st_ratio = Stat("improvement", "--", theme.ACCENT)
        self.st_lag = Stat("observer lag", "--", theme.WARN)
        i.add_layout(stat_row(self.st_efd, self.st_eob, self.st_ratio,
                              self.st_lag))
        self.c1 = MplCanvas(width=7.4, height=3.4, nrows=2)
        i.add(self.c1)
        self.add(i)
        for s_ in (self.s_bw, self.s_noise, self.s_q):
            s_.valueChanged.connect(self._redraw_obs)
        self._redraw_obs()

        self.add(callout(
            "<b>Turn the observer bandwidth down to 10 and back up to 400.</b> "
            "At the low end the estimate is beautifully smooth and arrives "
            "late — it is trusting the model. At the high end it is fast and "
            "noisy — it is trusting the encoder. Somewhere in the middle is "
            "your design, and the right answer depends on how good your model "
            "is relative to your sensor.<br><br>"
            "<b>That sentence is the Kalman filter.</b> A Kalman filter is a "
            "Luenberger observer whose L is computed <i>optimally</i> from two "
            "numbers you supply: how noisy the sensor is, and how wrong the "
            "model is. Same structure, same equations — the gain is derived "
            "rather than placed, and it is time-varying while it converges. "
            "Everything on this page is the thing a Kalman filter is.", "key"))

        # ---- disturbance observer ----------------------------------------
        self.add(hline())
        self.add(title("The disturbance observer — force sensing with no force "
                       "sensor"))

        do = Card("estimate the thing nobody measured")
        do.add(body(
            "Augment the state with the unknown external torque and declare it "
            "constant — not because it is, but because it changes slowly "
            "compared with the observer:"))
        do.add(math_label(r"x = [\theta,\ \dot\theta,\ \tau_{ext}]^T, "
                          r"\qquad \dot\tau_{ext} = 0", 17))
        do.add(body(
            "The augmented system is still observable from position alone, so "
            "the same Luenberger machinery now estimates <b>τ<sub>ext</sub></b> "
            "as a by-product. The mechanism is simple and worth stating plainly: "
            "the observer knows what torque it commanded and what motion that "
            "should have produced; <b>the discrepancy is the external "
            "torque</b>."))
        do.add(body(
            "<b>This is what \"sensorless\" collision detection actually is</b> "
            "— on Universal Robots cobots, on Franka, in friction "
            "compensation, in load estimation. It is also the honest version of "
            "the \"model-based estimate\" row in the force-sensing table on the "
            "Torque Control page.<br><br>"
            "<b>And its limits are the ones you already know.</b> The estimate "
            "is only as good as the model of everything else — so behind a "
            "gearbox with 20 N·m of stiction, the disturbance observer "
            "faithfully reports the stiction. It cannot separate \"a person "
            "pushed me\" from \"my own friction model is wrong\", because "
            "nothing in the measurement distinguishes them. Transparency is "
            "still the prerequisite.", dim=True))
        self.add(do)

        # ---- interactive 2 -----------------------------------------------
        i2 = Card("watch it recover an unmeasured load")
        i2.add(body(
            "A constant external torque is applied that the controller never "
            "measures. The observer's third state converges on it — from the "
            "position encoder alone.", dim=True))
        self.s_text = slider(-60, 60, 20)        # x0.1 N m
        self.s_dbw = slider(5, 120, 25)          # rad/s
        self.s_dn = slider(0, 60, 10)            # x1e-5
        self.l_text, self.l_dbw, self.l_dn = QLabel(), QLabel(), QLabel()
        i2.add_layout(slider_row("true τ_ext (×0.1 N·m)", self.s_text,
                                 self.l_text))
        i2.add_layout(slider_row("observer bandwidth", self.s_dbw, self.l_dbw))
        i2.add_layout(slider_row("encoder noise (×1e-5)", self.s_dn, self.l_dn))
        self.st_true = Stat("true τ_ext", "--", theme.WARN)
        self.st_est = Stat("estimated", "--", theme.GOOD)
        self.st_err = Stat("error", "--", theme.BAD)
        self.st_conv = Stat("convergence", "--", theme.ACCENT)
        i2.add_layout(stat_row(self.st_true, self.st_est, self.st_err,
                               self.st_conv))
        self.c2 = MplCanvas(width=7.4, height=2.9)
        i2.add(self.c2)
        self.add(i2)
        for s_ in (self.s_text, self.s_dbw, self.s_dn):
            s_.valueChanged.connect(self._redraw_dob)
        self._redraw_dob()

        self.add(callout(
            "<b>Carry forward.</b> An observer is a model you run alongside the "
            "robot, corrected by whatever you can measure. It buys you the "
            "states you did not instrument, at the price of trusting your "
            "model exactly as far as its bandwidth. Controllability and "
            "observability are hardware verdicts decided before any code is "
            "written, and the separation principle is what lets you design "
            "controller and estimator without them interfering.", "good"))

        self.finish()

    # ------------------------------------------------------------------
    def _redraw_obs(self):
        bw = float(self.s_bw.value())
        noise = self.s_noise.value() * 1e-5
        quant = self.s_q.value() * 1e-5
        self.l_bw.setText(f"{bw:.0f} rad/s")
        self.l_noise.setText(f"{noise:.0e}" if noise else "none")
        self.l_q.setText(f"{quant:.0e}" if quant else "none")

        tr = run_velocity_observer(duration=1.5, obs_bw=bw, noise=noise,
                                   quant=quant)
        n = len(tr.omega)
        skip = int(n * 0.15)
        e_fd = sum(abs(a - b) for a, b in
                   zip(tr.omega_fd[skip:], tr.omega[skip:])) / (n - skip)
        e_ob = sum(abs(a - b) for a, b in
                   zip(tr.omega_hat[skip:], tr.omega[skip:])) / (n - skip)
        self.st_efd.set(f"{e_fd:.3f}")
        self.st_eob.set(f"{e_ob:.4f}")
        self.st_ratio.set(f"{e_fd/max(e_ob,1e-9):.0f}×")
        self.st_lag.set(f"{1000.0/bw:.1f} ms")

        c = self.c1
        c.clear()
        a1, a2 = c.axes
        a1.plot(tr.t, tr.omega_fd, color=theme.BAD, lw=0.7, alpha=0.75,
                label="finite difference")
        a1.plot(tr.t, tr.omega, color=theme.TEXT_FAINT, lw=2.4,
                label="true velocity")
        a1.plot(tr.t, tr.omega_hat, color=theme.GOOD, lw=1.8,
                label="observer estimate")
        lim = max(2.0, max(abs(v) for v in tr.omega) * 2.2)
        a1.set_ylim(-lim, lim)
        a1.set_ylabel("ω (rad/s)")
        c.legend(a1, loc="upper right")
        a2.plot(tr.t, [a - b for a, b in zip(tr.omega_hat, tr.omega)],
                color=theme.GOOD, lw=1.4, label="observer error")
        a2.axhline(0, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a2.set_xlabel("time (s)")
        a2.set_ylabel("estimation error")
        c.legend(a2, loc="upper right")
        c.refresh()

    def _redraw_dob(self):
        text = self.s_text.value() * 0.1
        bw = float(self.s_dbw.value())
        noise = self.s_dn.value() * 1e-5
        self.l_text.setText(f"{text:+.1f} N·m")
        self.l_dbw.setText(f"{bw:.0f} rad/s")
        self.l_dn.setText(f"{noise:.0e}" if noise else "none")

        tr = run_velocity_observer(duration=3.0, obs_bw=bw, noise=noise,
                                   tau_ext=text, estimate_disturbance=True)
        est = tr.tau_hat[-1]
        self.st_true.set(f"{text:+.2f}")
        self.st_est.set(f"{est:+.2f}")
        self.st_err.set(f"{abs(est-text):.3f}")
        self.st_err.set_color(theme.GOOD if abs(est - text) < 0.15
                              else theme.BAD)
        conv = next((t for t, v in zip(tr.t, tr.tau_hat)
                     if abs(v - text) < 0.1 * max(abs(text), 0.1)), None)
        self.st_conv.set(f"{conv*1000:.0f} ms" if conv else "—")

        c = self.c2
        c.clear()
        c.ax.plot(tr.t, tr.tau_ext, color=theme.WARN, lw=2.0, ls="--",
                  label="true τ_ext (never measured)")
        c.ax.plot(tr.t, tr.tau_hat, color=theme.GOOD, lw=1.8,
                  label="observer estimate")
        c.ax.axhline(0, color=theme.TEXT_FAINT, lw=1.0)
        c.ax.set_xlabel("time (s)")
        c.ax.set_ylabel("τ (N·m)")
        c.legend(loc="lower right")
        c.refresh()
