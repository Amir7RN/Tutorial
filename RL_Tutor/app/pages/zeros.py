"""
Zeros -- the other kind of dot on the s-plane, and the one nobody explains.

This page sits at the end of the Systems & Stability block, immediately before
root locus, because every sentence on the root-locus page ("D adds a zero",
"the poles migrate to the zeros") is unreadable until a zero is a physical
object rather than "a root of the numerator".

Three things get built here, in this order, because each one needs the last:

  1  a zero is a frequency the system REFUSES TO PASS -- shown by driving a
     notch with a sine and watching the output collapse to nothing
  2  a zero reshapes the response WITHOUT moving a single pole -- shown by
     sliding one zero across a fixed second-order joint, including into the
     right half plane, where the output goes the wrong way first
  3  a zero is a DESTINATION -- shown by sweeping loop gain and watching the
     closed-loop poles walk toward it

The rule followed on the first-order pages is followed here too: no claim that
can be made draggable is left as prose.
"""

from __future__ import annotations

import cmath
import math

from PySide6.QtWidgets import QComboBox, QLabel

from ctrlcore.linear import (
    TF,
    bode,
    log_freqs,
    notch,
    poly_roots,
    root_locus,
    simulate_ss,
    step_response,
    tf_to_ss,
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

SECTION = "Systems & Stability"

#: the blocking demo's notch frequency, in rad/s. Fixed, because the point of
#: the widget is that the INPUT moves and the hole stays put.
W_BLOCK = 6.0

#: the joint used for the "one zero, nothing else changes" widget
WN_JOINT = 4.0


class ZerosPage(Page):
    TITLE = "What a Zero Is"
    SUBTITLE = ("A pole is what the system does when you leave it alone. A "
                "zero is what it refuses to pass — and the place its poles go "
                "when you push hard enough.")
    SECTION = SECTION
    NOTES = "foundation"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>Both dots live on the same map and mean opposite kinds of "
            "thing.</b> A <b>pole</b> is a motion the system will make with no "
            "input at all — roots of the <i>denominator</i>. A <b>zero</b> is "
            "an input the system will not respond to at all — roots of the "
            "<i>numerator</i>. Poles say what it does by itself; zeros say "
            "what it ignores.<br><br>"
            "That is the whole definition. Everything below is turning it into "
            "something you can predict with.", "key"))

        # ---- the definition ------------------------------------------------
        d = Card("the definition, and the word \"frequency\" applied to it")
        d.add(body(
            "Write the transfer function as a ratio of two polynomials:"))
        d.add(math_label(r"G(s) = \frac{\mathrm{num}(s)}{\mathrm{den}(s)}"
                         r" = K\,\frac{(s-z_1)(s-z_2)\cdots}"
                         r"{(s-p_1)(s-p_2)\cdots}", 17))
        d.add(body(
            "&nbsp;&nbsp;• <b>p<sub>i</sub></b> — a <b>pole</b>. G blows up "
            "there. Physically: a motion e<sup>p·t</sup> the system can sustain "
            "on its own.<br>"
            "&nbsp;&nbsp;• <b>z<sub>i</sub></b> — a <b>zero</b>. G goes to "
            "<i>zero</i> there. Physically: an input shaped like "
            "e<sup>z·t</sup> that produces <b>no output at all</b>, however "
            "hard you drive it."))
        d.add(callout(
            "<b>\"The zero's frequency\" just means the zero's value.</b> Same "
            "convention you already use for poles, nothing new. A pole at "
            "s = −1/τ is called \"a pole at 1/τ rad/s\"; a zero at s = −5 is "
            "\"a zero at 5 rad/s\". It is the magnitude of the s-value, used as "
            "a rate marker on the same axis. When someone says \"below the "
            "zero's frequency the D term does nothing\", they mean: at "
            "frequencies smaller than |z|.", "key"))
        d.add(body(
            "<b>Same map, different marker.</b> By universal convention poles "
            "are drawn as <b>×</b> and zeros as <b>○</b>, and both are plotted "
            "on the same s-plane you already read: horizontal = decay rate, "
            "vertical = ring rate. Every pole-zero picture on this page and "
            "every page after it uses that convention.", dim=True))
        self.add(d)

        # ---- where the cancellation physically comes from -------------------
        m = Card("why any input can be ignored — the mechanism is always two "
                 "paths")
        m.add(body(
            "A zero is never magic and never bookkeeping. It happens for one "
            "reason only: <b>there are two routes from input to output, and at "
            "one particular input shape they arrive equal and opposite</b>. "
            "The sum is nothing. That is a zero."))
        m.add(body(
            "The cleanest example is the derivative term in a PD controller, "
            "which computes two things from the same error and adds them:"))
        m.add(math_label(r"u = K_p\,e + K_d\,\dot e \;\;\Rightarrow\;\; "
                         r"C(s) = K_d\left(s + \frac{K_p}{K_d}\right)", 17))
        m.add(body(
            "Feed it an error that decays as e<sup>−λt</sup>. The P path "
            "produces K<sub>p</sub>e<sup>−λt</sup>; the D path differentiates "
            "and produces −λK<sub>d</sub>e<sup>−λt</sup> — <b>opposite sign</b>, "
            "because a decaying signal has a negative slope. Pick "
            "λ = K<sub>p</sub>/K<sub>d</sub> and the two are exactly equal in "
            "size: the controller outputs <b>zero</b> for an error that is "
            "plainly not zero. It has decided that an error dying at that "
            "particular rate needs no help, because the D term can already see "
            "it going away.<br><br>"
            "So the zero at s = −K<sub>p</sub>/K<sub>d</sub> is the crossover "
            "between two behaviours: <b>well below it</b>, ė is negligible and "
            "the controller acts like plain P; <b>well above it</b>, "
            "K<sub>d</sub>ė dominates and the controller is reacting to how "
            "fast the error is changing rather than how big it is. The zero's "
            "location <i>is</i> that dial."))
        m.add(callout(
            "<b>And this is why plant zeros are not a different subject.</b> A "
            "flexible arm with the motor at one end and the encoder at the "
            "other has a stiff structural path and a bending path; at one "
            "frequency they arrive out of phase and cancel. A strain gauge "
            "picking up both bending and torsion has two contributions that can "
            "cancel. Same mechanism, same map, same marker — the only "
            "difference is that nobody designed it. <b>The controller's zero "
            "was chosen; the plant's zero was discovered.</b>", "key"))
        self.add(m)

        # ================= interactive 1: the blocking test ==================
        self.add(hline())
        self.add(title("Interactive 1 — the frequency it refuses to pass"))

        b1 = Card("drive it with a sine and hunt for the hole")
        b1.add(body(
            f"This system has a pair of zeros at s = ±j{W_BLOCK:.0f} — on the "
            "imaginary axis, so they block a pure sine rather than a decaying "
            "exponential. Its numerator is literally two paths added together:"))
        b1.add(math_label(r"\mathrm{num}(s) = s^2 + 36 \;\;\longrightarrow\;\; "
                          r"(j\omega)^2 + 36 = 36 - \omega^2", 16))
        b1.add(body(
            "At ω = 6 the acceleration-like path (s²) contributes −36 and the "
            "static path contributes +36. They cancel exactly. <b>Drag the "
            "input frequency through 6 rad/s and watch the output die while "
            "the input keeps going.</b> Nothing about the system changed; the "
            "input walked into the hole.", dim=True))
        self.s_win = slider(5, 200, 60)                # x0.1 rad/s
        self.l_win = QLabel()
        b1.add_layout(slider_row("input ω (rad/s)", self.s_win, self.l_win))
        self.st_ratio = Stat("output / input", "--", theme.ACCENT)
        self.st_db = Stat("|G(jω)|", "--", theme.VIOLET)
        self.st_paths = Stat("36 − ω²", "--", theme.CYAN)
        self.st_verdict1 = Stat("verdict", "--", theme.GOOD)
        b1.add_layout(stat_row(self.st_ratio, self.st_db, self.st_paths,
                               self.st_verdict1))
        self.c1 = MplCanvas(width=7.6, height=2.9, ncols=2)
        b1.add(self.c1)
        b1.add(body(
            "<b>This is exactly what a notch filter is</b>, and it is the "
            "honest way to read one: a notch is not a \"filter setting\", it is "
            "a pair of zeros parked on top of a resonance you want silenced. "
            "You will meet it again on the Lead, Lag & Notch page — together "
            "with the reason it is dangerous, which is that the resonance can "
            "move and the zeros cannot.", dim=True))
        self.add(b1)
        self.s_win.valueChanged.connect(self._redraw_block)
        self._redraw_block()

        # ---- what zeros do to a step ---------------------------------------
        self.add(hline())
        self.add(title("Interactive 2 — one zero, and not one pole moved"))

        w = Card("the same joint every time; only the zero slides")
        w.add(body(
            f"The plant underneath is a fixed second-order joint — "
            f"ω<sub>n</sub> = {WN_JOINT:.0f} rad/s, damping on the second "
            "slider — and a single zero is multiplied onto it, scaled so the "
            "steady-state value is 1 no matter where the zero goes:"))
        w.add(math_label(r"G(s) = \left(1-\frac{s}{z}\right)\cdot"
                         r"\frac{\omega_n^2}{s^2+2\zeta\omega_n s+\omega_n^2}",
                         17))
        w.add(body(
            "<b>z is the zero's location on the s-plane, signed</b> — z = −2 "
            "puts the ○ at s = −2 in the left half plane, z = +2 puts it at "
            "s = +2 in the right. That form is written with a minus so that the "
            "numerator vanishes at s = z and the steady-state value stays 1 for "
            "every setting.", dim=True))
        w.add(body(
            "<b>The poles never move.</b> They are the × marks, and they stay "
            "exactly where ζ puts them for every setting of the zero slider. "
            "Everything you see change in the step response is the zero's doing "
            "alone.<br><br>"
            "Three positions worth visiting deliberately:<br>"
            "&nbsp;&nbsp;• <b>zero far left (say −20)</b> — barely any effect. "
            "A zero far outside the bandwidth is a zero you can ignore, and "
            "this is why plants with distant zeros get modelled without "
            "them.<br>"
            "&nbsp;&nbsp;• <b>zero close in (−2 to −0.5)</b> — the rise gets "
            "sharply faster and a big overshoot appears, <i>with the same "
            "damping</i>. Overshoot is not only a ζ story.<br>"
            "&nbsp;&nbsp;• <b>zero positive (right half plane)</b> — the output "
            "sets off in the <b>wrong direction</b> before turning round. "
            "Nothing became unstable; the poles are where they always were.",
            dim=True))
        self.s_zpos = slider(-200, 200, -20)          # x0.1  rad/s
        self.s_zzeta = slider(10, 150, 60)            # x0.01
        self.l_zpos, self.l_zzeta = QLabel(), QLabel()
        w.add_layout(slider_row("zero location z (rad/s)", self.s_zpos,
                                self.l_zpos))
        w.add_layout(slider_row("damping ζ (poles)", self.s_zzeta,
                                self.l_zzeta))
        self.st_os = Stat("overshoot", "--", theme.WARN)
        self.st_us = Stat("wrong-way dip", "--", theme.BAD)
        self.st_rise = Stat("rise time 10→90%", "--", theme.GOOD)
        self.st_poles2 = Stat("poles (unchanged)", "--", theme.ACCENT)
        self.st_phase = Stat("phase at ω_n", "--", theme.VIOLET)
        w.add_layout(stat_row(self.st_os, self.st_us, self.st_rise,
                              self.st_poles2, self.st_phase))
        self.c2 = MplCanvas(width=7.6, height=5.4, nrows=2, ncols=2)
        w.add(self.c2)
        self.zt2 = body("", dim=True)
        w.add(self.zt2)
        self.add(w)
        for s in (self.s_zpos, self.s_zzeta):
            s.valueChanged.connect(self._redraw_zero)
        self._redraw_zero()

        # ---- the two things a zero does to the response --------------------
        e = Card("what a left-half-plane zero actually does, stated once")
        e.add(body(
            "In the time domain, a zero adds a scaled copy of the "
            "<b>derivative</b> of the zero-free response. That is not a "
            "metaphor — it falls straight out of the algebra:"))
        e.add(math_label(r"\left(1-\tfrac{s}{z}\right)G_0(s)\;\;\Rightarrow\;\;"
                         r"y(t) = y_0(t) - \tfrac{1}{z}\,\dot y_0(t)", 16))
        e.add(body(
            "So the response you get is the old one plus a slug of its own "
            "slope. For a left-half-plane zero, z is negative, −1/z is "
            "<b>positive</b>, and early on — when y₀ is rising steeply — that "
            "slug is large and adds: the output leaps ahead of where it would "
            "have been, which is the faster rise and the extra overshoot you "
            "just watched appear. The closer the zero (small |z|, big 1/|z|), "
            "the bigger the slug.<br><br>"
            "In the frequency domain the same fact reads as <b>+20 dB/decade "
            "and up to +90° of phase</b> above |z| — a zero is the exact mirror "
            "of a pole, which subtracts 20 dB/decade and up to 90°. That is why "
            "a zero is the standard cure for a phase-margin problem: you are "
            "buying back phase that the poles spent."))
        self.add(e)

        rhp = Card("a right-half-plane zero, and why it is a hardware verdict")
        rhp.add(body(
            "Put z on the right (z &gt; 0) and −1/z is now negative, so the "
            "same algebra reads y = y₀ − (1/z)·ẏ₀ with a positive 1/z. The slug "
            "of derivative arrives with a "
            "<b>minus</b> sign, so at the very start — when the slope is "
            "biggest and the output is still near nothing — the derivative term "
            "wins and drags the output <b>backwards</b>. That is the dip you "
            "just produced with the slider, and its formal name is "
            "<b>non-minimum phase</b>."))
        rhp.add(body(
            "<table cellpadding='6'>"
            "<tr><td><b>Machine</b></td><td><b>The wrong-way move</b></td></tr>"
            "<tr><td>a bicycle</td><td>to turn left you must first steer "
            "<i>right</i> — countersteering</td></tr>"
            "<tr><td>an aircraft in pitch</td><td>elevator up: the tail lifts "
            "the aircraft <i>down</i> for a moment before the nose rises</td>"
            "</tr>"
            "<tr><td>a boost converter</td><td>ask for more output volts and "
            "the volts <i>sag</i> first</td></tr>"
            "<tr><td>a hydro turbine</td><td>open the gate and the power "
            "<i>drops</i> before it climbs</td></tr>"
            "<tr><td>a biped taking a step</td><td>the CoM must move the wrong "
            "way to unload the foot that is about to swing</td></tr>"
            "</table>"))
        rhp.add(callout(
            "<b>You cannot design this away, and that is the point of finding "
            "it before you write any controller.</b> Feedback reacts to the "
            "output it sees; if the short-term direction of the output is "
            "backwards from the long-term one, then reacting fast means "
            "reacting <i>wrongly</i>, fast. The standard rule of thumb is a hard "
            "ceiling on closed-loop bandwidth of roughly <b>ω<sub>c</sub> &lt; "
            "z/2</b>, and it holds for <i>every</i> controller — PID, LQR, "
            "H<sub>∞</sub>, a neural network. It is a property of the plant, "
            "not of your design.<br><br>"
            "Note also what the Bode phase plot in the widget did when you "
            "crossed over: an RHP zero contributes the magnitude rise of a zero "
            "with the <b>phase lag</b> of a pole. You pay phase and get no "
            "stability for it. Hence \"non-minimum phase\": the least phase lag "
            "consistent with that magnitude curve is not what you got.", "warn"))
        self.add(rhp)

        # ================= interactive 3: destination ========================
        self.add(hline())
        self.add(title("Interactive 3 — the zero as a destination"))

        b3 = Card("turn the gain up and watch a pole walk to the ○")
        b3.add(body(
            "Close the loop with a PD controller, so the loop transfer function "
            "is K·(s + z)·plant. The closed-loop poles are the roots of "
            "<b>den + K·num</b> — the rule from the Stability page — and that "
            "expression has an obvious behaviour at each end:"))
        b3.add(math_label(r"\mathrm{den}(s) + K\,\mathrm{num}(s) = 0"
                          r"\quad\Rightarrow\quad"
                          r"K\to 0:\ \mathrm{den}=0 \qquad "
                          r"K\to\infty:\ \mathrm{num}=0", 16))
        b3.add(body(
            "<b>At zero gain the closed-loop poles are the plant's own poles. "
            "At infinite gain they are the zeros.</b> The grey cloud is every "
            "position they pass through on the way; the × marks are where they "
            "sit at the gain you have selected. Physically: a strong enough "
            "controller overpowers what the plant wanted to do and substitutes "
            "the behaviour its own zero specifies.<br><br>"
            "Pick the pendulum and note what that buys — the plant has a pole "
            "in the right half plane (it falls over), and there is a gain at "
            "which the locus has dragged it across into the left half plane. "
            "<b>That crossing is what stabilisation physically is</b>, and the "
            "zero you placed is what it is heading for.", dim=True))
        self.cmb3 = QComboBox()
        self.cmb3.addItem("rigid joint — τ in, θ out  (marginal: pole at 0)",
                          "joint")
        self.cmb3.addItem("inverted pendulum — unstable pole in the RHP",
                          "pend")
        b3.add_layout(labelled("plant", self.cmb3))
        self.s_z3 = slider(2, 200, 30)                 # x0.1 rad/s
        self.s_k3 = slider(1, 600, 120)                # x0.1
        self.l_z3, self.l_k3 = QLabel(), QLabel()
        b3.add_layout(slider_row("zero location (rad/s)", self.s_z3, self.l_z3))
        b3.add_layout(slider_row("loop gain K", self.s_k3, self.l_k3))
        self.st_cl = Stat("closed-loop poles", "--", theme.ACCENT)
        self.st_st3 = Stat("verdict", "--", theme.GOOD)
        self.st_z3 = Stat("distance to the zero", "--", theme.WARN)
        self.st_zeta3 = Stat("ζ now", "--", theme.VIOLET)
        b3.add_layout(stat_row(self.st_cl, self.st_st3, self.st_z3,
                               self.st_zeta3))
        self.c3 = MplCanvas(width=7.6, height=3.0, ncols=2)
        b3.add(self.c3)
        self.zt3 = body("", dim=True)
        b3.add(self.zt3)
        self.add(b3)
        self.cmb3.currentIndexChanged.connect(self._redraw_locus)
        for s in (self.s_z3, self.s_k3):
            s.valueChanged.connect(self._redraw_locus)
        self._redraw_locus()

        inf = Card("\"zeros at infinity\" — the leftover poles")
        inf.add(body(
            "A PD controller adds one zero, and the plants above have two "
            "poles. One closed-loop pole therefore has somewhere finite to go; "
            "the other does not, and it runs off to the left without limit as K "
            "rises. That is all the phrase <b>\"zeros at infinity\"</b> means: "
            "poles minus zeros is the count of branches with no finite "
            "destination.<br><br>"
            "It is not a failure. It says those modes simply keep getting "
            "faster as you push, with no designed-in ceiling — and in practice "
            "they are the modes that eventually run into the things this "
            "tutor's real-time page is about: sampling, delay, and the "
            "unmodelled resonance you were pretending was not there."))
        self.add(inf)

        # ---- where they come from ------------------------------------------
        src = Card("every zero you will actually meet, and which kind it is")
        src.add(body(
            "<table cellpadding='6'>"
            "<tr><td><b>Source</b></td><td><b>Zero</b></td>"
            "<td><b>Designed or inherent?</b></td></tr>"
            "<tr><td>PD control &nbsp; K<sub>p</sub>+K<sub>d</sub>s</td>"
            "<td>s = −K<sub>p</sub>/K<sub>d</sub></td><td>designed — you chose "
            "it when you picked the gain ratio, whether you meant to or "
            "not</td></tr>"
            "<tr><td>PI control &nbsp; K<sub>p</sub>+K<sub>i</sub>/s</td>"
            "<td>s = −K<sub>i</sub>/K<sub>p</sub>, plus a pole at 0</td>"
            "<td>designed</td></tr>"
            "<tr><td>lead / lag compensator</td><td>one zero <i>and</i> one "
            "pole</td><td>designed — see below</td></tr>"
            "<tr><td>notch filter</td><td>a zero pair near the imaginary "
            "axis</td><td>designed, aimed at a specific resonance</td></tr>"
            "<tr><td>flexible link, sensor not at the actuator</td>"
            "<td>a zero pair below the resonant pole pair</td>"
            "<td>inherent — geometry and stiffness</td></tr>"
            "<tr><td>SEA: motor torque in, load force out</td>"
            "<td>zeros from the spring path versus the inertia path</td>"
            "<td>inherent</td></tr>"
            "<tr><td>a sensor blending two states</td><td>wherever the two "
            "contributions cancel</td><td>inherent</td></tr>"
            "<tr><td>a plant that must move the wrong way first</td>"
            "<td>a zero in the RIGHT half plane</td>"
            "<td>inherent, and a hard limit on every controller</td></tr>"
            "</table>"))
        src.add(callout(
            "<b>Lead and lag have both a zero and a pole, and that is not a "
            "different interpretation — it is the same two.</b> Read them "
            "separately and in order of frequency:<br><br>"
            "&nbsp;&nbsp;<b>lead</b>, C = (s+z)/(s+p) with p &gt; z: the zero "
            "comes first and starts lifting phase; the pole arrives later and "
            "stops the magnitude climbing forever. You wanted a zero's phase "
            "and could not afford a zero's infinite high-frequency gain — the "
            "pole is the price. It is exactly a D term with a filter on it, "
            "which is the only kind of D term anyone actually ships.<br><br>"
            "&nbsp;&nbsp;<b>lag</b>, p &lt; z: the pole comes first and lifts "
            "the low-frequency gain (killing steady-state error), and the zero "
            "arrives to flatten it back out before the phase loss reaches "
            "anywhere that matters. It is a nearly-integrator that stops being "
            "one before it can hurt you.<br><br>"
            "Same objects, always: the pole is what the block does on its own, "
            "the zero is what it declines to pass, and their <i>ordering on the "
            "frequency axis</i> is the entire design.", "key"))
        self.add(src)

        # ---- what zeros do NOT do -------------------------------------------
        nots = Card("three things a zero does not do — the corrections that "
                    "matter")
        nots.add(body(
            "<b>1 · A zero does not make a system unstable.</b> Stability is a "
            "statement about poles, full stop. An RHP <i>pole</i> is an "
            "instability; an RHP <i>zero</i> is a perfectly stable system that "
            "moves the wrong way first. The bicycle is not unstable in pitch "
            "because of countersteering — it is stable, and awkward.<br><br>"
            "<b>2 · A zero of the plant does not move the plant's poles.</b> "
            "You just watched that: two sliders, one moved the ○ and the × "
            "marks never budged. But close a loop around it and the numerator "
            "enters the closed-loop denominator (den + K·num), so <b>the plant's "
            "zeros absolutely do decide where the closed-loop poles end "
            "up</b>. Zeros are inert open-loop and decisive closed-loop, and "
            "that difference is why they get skipped in teaching and then "
            "become the whole story in design.<br><br>"
            "<b>3 · Feedback does not move the zeros.</b> Look at "
            "<code>TF.feedback()</code>: the numerator is copied through "
            "untouched and only the denominator changes. Closed-loop poles are "
            "yours to place; open-loop zeros are yours to live with. Which is "
            "the sharpest possible statement of why an RHP zero is a hardware "
            "problem — no amount of loop-shaping relocates it."))
        self.add(nots)

        canc = Card("and the one place people get hurt: cancellation")
        canc.add(body(
            "If a controller zero sits exactly on a plant pole, the factors "
            "cancel on paper and the pole vanishes from the transfer function. "
            "This is legitimate and common for a well-damped, well-known, "
            "stable pole — it is what \"cancel the slow lag\" means in a "
            "current-loop design."))
        canc.add(callout(
            "<b>Never cancel a pole you are afraid of.</b> The cancellation is "
            "only exact if your model is exact. Cancel a lightly damped "
            "resonance and a 5% shift in payload leaves the pole uncancelled "
            "with your full loop gain wrapped around it. Cancel an "
            "<i>unstable</i> pole and the mode is still there, still growing, "
            "merely invisible at the output — the transfer function is clean and "
            "the machine is not. The formal statement is that the cancelled mode "
            "becomes uncontrollable or unobservable, which is exactly the "
            "vocabulary of the State Feedback and Observer pages.", "warn"))
        self.add(canc)

        self.add(callout(
            "<b>Carry forward.</b> Poles = what it does alone; zeros = what it "
            "will not pass. Zeros come from two paths cancelling, designed "
            "(PD, lead, notch) or inherent (flexible links, SEAs, wrong-way "
            "plants). A zero adds a slug of derivative: LHP zero ⇒ faster rise, "
            "more overshoot, +phase, no danger. RHP zero ⇒ wrong way first, "
            "−phase, and a hard bandwidth ceiling nobody can design around. And "
            "in a closed loop the zeros are where the poles are heading — which "
            "is the sentence the next page is built entirely out of.", "good"))

        self.finish()

    # ------------------------------------------------------------------
    # interactive 1 -- the blocking test
    # ------------------------------------------------------------------
    def _redraw_block(self):
        w_in = self.s_win.value() / 10.0
        self.l_win.setText(f"{w_in:.1f}")

        g = notch(W_BLOCK, zeta_zero=0.0, zeta_pole=0.6)
        gain = abs(g.response(w_in))

        # long enough that the transient has gone and only the forced sine is
        # left -- otherwise the "output dies" claim is unverifiable on screen
        dur = max(6.0, 12.0 / max(w_in, 0.5))
        t, y, _ = simulate_ss(tf_to_ss(g), lambda tt: math.sin(w_in * tt),
                              dur, dur / 2400.0)
        half = len(t) // 2
        amp = (max(y[half:]) - min(y[half:])) / 2.0

        paths = W_BLOCK * W_BLOCK - w_in * w_in
        blocked = gain < 0.08
        self.st_ratio.set(f"{amp:.3f}")
        self.st_ratio.set_color(theme.BAD if blocked else theme.ACCENT)
        self.st_db.set(f"{20*math.log10(max(gain, 1e-6)):+.1f} dB")
        self.st_paths.set(f"{paths:+.1f}")
        self.st_verdict1.set("BLOCKED" if blocked
                             else ("passing" if gain > 0.5 else "attenuated"))
        self.st_verdict1.set_color(theme.BAD if blocked else
                                   (theme.GOOD if gain > 0.5 else theme.WARN))

        c = self.c1
        c.clear()
        a1, a2 = c.axes
        a1.plot(t, [math.sin(w_in * tt) for tt in t], color=theme.TEXT_FAINT,
                lw=1.4, label="input")
        a1.plot(t, y, color=theme.BAD if blocked else theme.ACCENT, lw=2.2,
                label="output")
        a1.set_ylim(-1.35, 1.35)
        a1.set_xlabel("time (s)")
        a1.set_ylabel("amplitude")
        a1.set_title("same drive, and what comes out", fontsize=9)
        c.legend(a1, loc="upper right")

        ws = log_freqs(0.5, 60.0, 400)
        mags = [abs(g.response(x)) for x in ws]
        a2.semilogx(ws, mags, color=theme.VIOLET, lw=2.0)
        a2.scatter([w_in], [gain], s=55, color=theme.ACCENT, zorder=5)
        a2.axvline(W_BLOCK, color=theme.BAD, lw=1.0, ls=":")
        a2.set_ylim(-0.05, 1.35)
        a2.set_xlabel("input frequency ω (rad/s)")
        a2.set_ylabel("|G(jω)|")
        a2.set_title("the hole, and where you are in it", fontsize=9)
        c.refresh()

    # ------------------------------------------------------------------
    # interactive 2 -- one zero over a fixed joint
    # ------------------------------------------------------------------
    def _redraw_zero(self):
        z = self.s_zpos.value() / 10.0
        if abs(z) < 0.5:                 # z = 0 is not a zero, it is a hole
            z = 0.5 if z >= 0 else -0.5
        zeta = self.s_zzeta.value() / 100.0
        self.l_zpos.setText(f"{z:+.1f}")
        self.l_zzeta.setText(f"{zeta:.2f}")

        wn = WN_JOINT
        den = [1.0, 2 * zeta * wn, wn * wn]
        g0 = TF([wn * wn], den)
        # (1 - s/z) * G0 -- vanishes at s = z, and G(0) = G0(0) for every z
        g = TF([-wn * wn / z, wn * wn], den)

        dur = 6.0
        t, y = step_response(g, dur, dur / 1500.0)
        _, y0 = step_response(g0, dur, dur / 1500.0)

        peak, dip = max(y), min(y)
        os = max(0.0, peak - 1.0) * 100.0
        us = min(0.0, dip) * 100.0
        t_lo = t_hi = None
        for ti, yi in zip(t, y):
            if t_lo is None and yi >= 0.1:
                t_lo = ti
            if t_hi is None and yi >= 0.9:
                t_hi = ti
                break
        rise = (t_hi - t_lo) if (t_lo is not None and t_hi is not None) else None

        poles = poly_roots(den)
        ph_wn = math.degrees(cmath.phase(g.response(wn)))
        self.st_os.set(f"{os:.0f} %")
        self.st_us.set("none" if us > -0.5 else f"{us:.0f} %")
        self.st_us.set_color(theme.GOOD if us > -0.5 else theme.BAD)
        self.st_rise.set("--" if rise is None else f"{rise*1000:.0f} ms")
        if abs(poles[0].imag) < 1e-6:      # overdamped -- two real poles
            self.st_poles2.set(", ".join(f"{p.real:+.1f}" for p in poles))
        else:
            self.st_poles2.set(
                f"{poles[0].real:+.1f} ± j{abs(poles[0].imag):.1f}")
        self.st_phase.set(f"{ph_wn:+.0f}°")
        self.st_phase.set_color(theme.BAD if z > 0 else theme.VIOLET)

        if z > 0:
            self.zt2.setText(
                f"<b>Zero at s = +{z:.1f} — right half plane.</b> The output "
                f"dips to {dip:+.2f} before it ever heads for 1. The phase at "
                f"ω<sub>n</sub> is {ph_wn:+.0f}° — <b>more</b> lag than the "
                "zero-free joint, not less, which is the frequency-domain "
                "signature of the same defect. Any loop closed around this "
                f"plant is capped near ω ≈ {z/2:.1f} rad/s.")
        elif abs(z) < 2.0:
            self.zt2.setText(
                f"<b>Zero at s = {z:.1f} — close in, and dominant.</b> It sits "
                f"inside the joint's own ω<sub>n</sub> = {wn:.0f} rad/s, so the "
                f"derivative slug is large: {os:.0f}% overshoot out of a joint "
                f"whose ζ = {zeta:.2f} would give far less on its own. Reading "
                "an overshoot as \"low damping\" without checking for a zero is "
                "how joints get mistuned.")
        else:
            self.zt2.setText(
                f"<b>Zero at s = {z:.1f} — outside the bandwidth.</b> Well "
                f"beyond ω<sub>n</sub> = {wn:.0f} rad/s, so 1/z is small, the "
                "derivative slug is small, and the response is nearly the plain "
                "second-order curve. This is the regime in which people write "
                "models with no zeros in them and get away with it.")

        c = self.c2
        c.clear()
        a_st, a_pz, a_mag, a_ph = c.axes
        a_st.plot(t, y0, color=theme.TEXT_FAINT, lw=1.3, ls="--",
                  label="no zero")
        a_st.plot(t, y, color=theme.BAD if z > 0 else theme.ACCENT, lw=2.2,
                  label="with the zero")
        a_st.axhline(1.0, color=theme.TEXT_FAINT, lw=1.0, ls=":")
        a_st.axhline(0.0, color=theme.BORDER, lw=1.0)
        a_st.set_xlabel("time (s)")
        a_st.set_ylabel("y")
        a_st.set_title("step response", fontsize=9)
        c.legend(a_st, loc="lower right")

        _splane(a_pz, poles, [complex(z, 0.0)],
                lim=max(6.0, abs(z) * 1.3, wn * 1.4))
        a_pz.set_title("poles fixed, zero moving", fontsize=9)

        ws = log_freqs(0.05, 300.0, 400)
        _, mag, ph = bode(g, ws)
        _, mag0, ph0 = bode(g0, ws)
        a_mag.semilogx(ws, mag0, color=theme.TEXT_FAINT, lw=1.3, ls="--")
        a_mag.semilogx(ws, mag, color=theme.VIOLET, lw=2.0)
        a_mag.axhline(0, color=theme.TEXT_FAINT, lw=0.9, ls=":")
        a_mag.set_ylabel("|G| (dB)")
        a_mag.set_xlabel("ω (rad/s)")
        a_ph.semilogx(ws, ph0, color=theme.TEXT_FAINT, lw=1.3, ls="--")
        a_ph.semilogx(ws, ph, color=theme.CYAN, lw=2.0)
        a_ph.axvline(abs(z), color=theme.WARN, lw=1.0, ls=":")
        a_ph.set_ylabel("phase (deg)")
        a_ph.set_xlabel("ω (rad/s)   —   dotted line: |z|")
        c.refresh()

    # ------------------------------------------------------------------
    # interactive 3 -- the zero as a destination
    # ------------------------------------------------------------------
    def _plant3(self):
        if self.cmb3.currentData() == "pend":
            # theta'' = 9 theta + tau  --  poles at +-3, one of them unstable
            return TF([1.0], [1.0, 0.0, -9.0])
        return TF([1.0], [0.25, 0.4, 0.0])

    def _redraw_locus(self):
        z = self.s_z3.value() / 10.0
        k = self.s_k3.value() / 10.0
        self.l_z3.setText(f"{-z:+.1f}")
        self.l_k3.setText(f"{k:.1f}")

        plant = self._plant3()
        l0 = TF([1.0, z], plant.den)                 # PD zero on the plant
        gains = [10 ** (-2 + 5 * i / 249.0) for i in range(250)]
        locus = root_locus(l0, gains)
        cl = (l0 * k).feedback()
        here = poly_roots(cl.den)

        worst = max(here, key=lambda p: p.real)
        stable = all(p.real < -1e-9 for p in here)
        near = min(here, key=lambda p: abs(p + z))
        wn = abs(worst)
        zeta = (-worst.real / wn) if wn > 1e-9 else 0.0
        self.st_cl.set(", ".join(f"{p.real:+.1f}{p.imag:+.1f}j" for p in here))
        self.st_st3.set("stable" if stable else "UNSTABLE")
        self.st_st3.set_color(theme.GOOD if stable else theme.BAD)
        self.st_z3.set(f"{abs(near + z):.2f}")
        self.st_zeta3.set(f"{zeta:+.2f}")

        if self.cmb3.currentData() == "pend":
            need_k = 9.0 / z
            self.zt3.setText(
                "<b>Inverted pendulum.</b> Closed-loop denominator is "
                f"s² + K·s + K·z − 9, so it is stable only when K·z &gt; 9 — "
                f"with this zero, K &gt; {need_k:.1f}. Below that, the × stays "
                "in the red. <b>K·z is the P gain and K is the D gain</b>, so "
                "that one inequality is the whole statement \"you need both "
                "enough stiffness to beat gravity and some damping to stop it "
                "ringing\", derived rather than guessed.")
        else:
            self.zt3.setText(
                "<b>Rigid joint.</b> Its own poles are 0 and −1.6 — one of them "
                "on the axis, so the joint drifts and never returns. Any K &gt; "
                "0 drags the pole at the origin left, and as K grows it heads "
                f"for the ○ at −{z:.1f} while the other branch runs off to the "
                "left without limit. Put the zero further out and you buy a "
                "faster destination — at the cost of amplifying more sensor "
                "noise, which is why K<sub>d</sub> cannot simply be raised.")

        c = self.c3
        c.clear()
        a1, a2 = c.axes
        allr = [p for step in locus for p in step]
        lim = max(6.0, z * 1.5, max([abs(p) for p in here] or [6.0]) * 1.3)
        a1.scatter([p.real for p in allr], [p.imag for p in allr], s=1.2,
                   color=theme.TEXT_FAINT, alpha=0.5)
        _splane(a1, here, [complex(-z, 0.0)], lim=lim,
                marker_label="poles at this K")
        a1.set_title("root locus — the ○ is the destination", fontsize=9)
        c.legend(a1, loc="upper left")

        t, y = step_response(cl, 8.0, 4e-3)
        y = [min(max(v, -4.0), 4.0) for v in y]
        a2.plot(t, y, color=theme.GOOD if stable else theme.BAD, lw=2.0)
        dc = cl.dc_gain()
        if abs(dc) < 4:
            a2.axhline(dc, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a2.set_xlabel("time (s)")
        a2.set_ylabel("closed loop (clipped)")
        a2.set_title("what that gain actually does", fontsize=9)
        c.refresh()
