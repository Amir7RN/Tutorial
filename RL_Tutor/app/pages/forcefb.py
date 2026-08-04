"""
Pages 19-20: positive force feedback.

 19  Positive Force Feedback   -- what it is, why "positive" is not a mistake
 20  Closing the Loop          -- the maths, live, and the honesty test

The single sentence this section is built around:

    Positive force feedback exists only if force changes activation.
    If force does not affect activation, it is not feedback.

Page 20 lets you run both cases side by side and see that the difference is
not cosmetic: one is an open-loop neuromuscular controller, the other is a
reflex loop with a loop gain that can be measured and can run away.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QLabel, QTableWidget, QTableWidgetItem

from ctrlcore.neuro import (
    PffLoop,
    force_length,
    force_velocity,
    loop_gain,
    run_pff,
)
from .. import theme
from ..widgets import (
    Card,
    CodePane,
    MplCanvas,
    Stat,
    body,
    callout,
    get_source,
    hline,
    math_label,
    stat_row,
    title,
)
from .base import Page
from .motors import slider, slider_row

SECTION = "Force Feedback"


# ==========================================================================
# PAGE 19 -- what PFF is
# ==========================================================================

class PFFIntroPage(Page):
    TITLE = "Positive Force Feedback"
    SUBTITLE = ("Muscles are not controlled by position and velocity alone. The "
                "third signal is force — and it is fed back with a <i>plus</i> "
                "sign.")
    SECTION = SECTION
    NOTES = "material p.9"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(body(
            "In human physiology, muscles are <b>not</b> controlled only by "
            "position or velocity. They have <b>three distinct feedback "
            "signals</b>."))

        a = Card("(A) Muscle spindle — length &amp; velocity feedback")
        a.add(body(
            "<b>Sensors:</b> muscle spindles<br>"
            "<b>Measures:</b> muscle length, muscle velocity<br>"
            "<b>Function:</b> posture control, stretch reflex, stabilisation "
            "against perturbations<br>"
            "<b>Control effect:</b> resists changes in length — acts like "
            "stiffness and damping<br><br>"
            "👉 This is analogous to <b>impedance control</b>."))
        self.add(a)

        b = Card("(B) Golgi tendon organ — force feedback")
        b.add(body(
            "<b>Sensors:</b> Golgi tendon organs<br>"
            "<b>Measures:</b> muscle force / tension<br><br>"
            "This is where <b>positive force feedback</b> comes from."))
        self.add(b)

        c = Card("(C) Central command — activation")
        c.add(body(
            "<b>Source:</b> CNS / EMG<br>"
            "<b>Measures:</b> intended muscle activation<br><br>"
            "Note this is a <b>command</b>, not feedback. Confusing the two is "
            "the mistake page 20 is built to catch."))
        self.add(c)

        self.add(hline())
        self.add(title("What does <i>positive</i> force feedback mean?"))

        p = Card("the classical intuition, and why it is wrong here")
        p.add(body(
            "People think feedback should always be <b>negative</b> for "
            "stability. But <b>locomotion is not static control</b>."))
        p.add(title("When muscle force increases, activation is increased "
                    "further — temporarily.", 15))
        p.add(body(
            "That sounds unstable. It is not, because it is "
            "<b>phase-dependent</b>."))
        self.add(p)

        w = Card("why PFF exists biologically")
        w.add(body(
            "During stance and push-off:<br>"
            "&nbsp;&nbsp;• the body <i>wants</i> force to build rapidly<br>"
            "&nbsp;&nbsp;• the ankle plantarflexors (soleus, gastrocnemius) "
            "<b>amplify force</b><br>"
            "&nbsp;&nbsp;• PFF gives rapid load acceptance, efficient energy "
            "transfer, and push-off power generation<br><br>"
            "This is <b>functional amplification</b>, not instability."))
        w.add(body(
            "It stays bounded because it is <b>phase-gated</b>, "
            "<b>time-limited</b>, and <b>embedded in a compliant musculoskeletal "
            "system</b>. The loop exists <b>only when load-bearing is "
            "desired</b>.", dim=True))
        self.add(w)

        self.add(callout(
            "<b>Why not just length or velocity feedback?</b><br><br>"
            "<b>Length / velocity feedback:</b> good for stability, good for "
            "disturbance rejection, <b>bad for power amplification</b>.<br><br>"
            "<b>Force feedback:</b> directly reflects interaction with the "
            "environment, <b>scales with load</b>, and enables emergent behaviour "
            "— a stronger push when more load exists.<br><br>"
            "In other words: <b>length/velocity feedback stabilises posture; "
            "force feedback enables propulsion.</b>", "key"))

        q = Card("the two questions each loop answers")
        tbl = QTableWidget(2, 2)
        tbl.setHorizontalHeaderLabels(["Feedback signal", "The question it answers"])
        for r, cells in enumerate([
            ("Length & velocity", "\"Where am I and how fast am I moving?\""),
            ("Force", "\"How hard am I interacting with the world?\""),
        ]):
            for c2, v in enumerate(cells):
                it = QTableWidgetItem(v)
                it.setFlags(Qt.ItemIsEnabled)
                tbl.setItem(r, c2, it)
        tbl.verticalHeader().setVisible(False)
        tbl.setColumnWidth(0, 220)
        tbl.setColumnWidth(1, 420)
        tbl.setMinimumHeight(120)
        q.add(tbl)
        q.add(body(
            "That is why PFF <b>scales torque with load</b>, enables "
            "<b>emergent push-off</b>, and <b>avoids rigid trajectory "
            "enforcement</b>.", dim=True))
        self.add(q)

        # ---- Hill curves ------------------------------------------------------
        h = Card("the Hill machinery the loop rides on")
        h.add(body(
            "Before closing any loop, know what the muscle can do open-loop. "
            "Force depends on activation <i>and</i> on where the fibre is and how "
            "fast it is moving:"))
        h.add(math_label(r"F_m = a \cdot F_{max} \cdot f_l(l) \cdot f_v(\dot l)", 17))
        self.canvas = MplCanvas(width=7.4, height=2.7, ncols=2)
        h.add(self.canvas)
        h.add(body(
            "Note the eccentric branch on the right: being <b>stretched while "
            "active</b> gives you up to ~1.8× force for free. The calf exploits "
            "exactly that during the first half of stance — and it means the "
            "loop gain is not constant through the gait cycle.", dim=True))
        self.add(h)
        self._draw_hill()

        self.finish()

    def _draw_hill(self):
        c = self.canvas
        c.clear()
        a1, a2 = c.axes
        ls = [x / 100.0 for x in range(40, 161)]
        a1.plot(ls, [force_length(x) for x in ls], color=theme.ACCENT, lw=2.2)
        a1.axvline(1.0, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a1.set_title("force-length  f_l(l)", fontsize=9)
        a1.set_xlabel("normalised fibre length")
        a1.set_ylabel("force factor")

        vs = [x / 100.0 for x in range(-100, 101)]
        a2.plot(vs, [force_velocity(x) for x in vs], color=theme.GOOD, lw=2.2)
        a2.axvline(0.0, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a2.set_title("force-velocity  f_v(l̇)", fontsize=9)
        a2.set_xlabel("← shortening    normalised velocity    lengthening →")
        c.refresh()


# ==========================================================================
# PAGE 20 -- closing the loop
# ==========================================================================

class PFFMathPage(Page):
    TITLE = "Closing the Force Loop"
    SUBTITLE = ("Where the loop is closed mathematically — and the honesty test "
                "for whether you actually built one.")
    SECTION = SECTION
    NOTES = "material p.9"

    def __init__(self, parent=None):
        super().__init__(parent)

        s = Card("standard Hill-type structure")
        s.add(math_label(r"F_m = a \cdot F_{max} \cdot f_l(l) \cdot f_v(\dot l)", 17))
        s.add(body(
            "&nbsp;&nbsp;<b>a</b> — activation (from EMG)<br>"
            "&nbsp;&nbsp;<b>f<sub>l</sub></b> — force-length relation<br>"
            "&nbsp;&nbsp;<b>f<sub>v</sub></b> — force-velocity relation"))
        s.add(title("So far: no feedback. This is feedforward.", 15))
        self.add(s)

        n = Card("now add positive force feedback")
        n.add(body("Activation is <b>not just EMG</b> any more. Instead:"))
        n.add(math_label(r"a(t) = a_{EMG}(t) + k_f \cdot F_m(t - \tau)", 18))
        n.add(body("<b>This is the key equation.</b>"))
        n.add(body(
            "&nbsp;&nbsp;• The force generated at time <b>t − τ</b> is fed "
            "back<br>"
            "&nbsp;&nbsp;• It increases activation at time <b>t</b><br>"
            "&nbsp;&nbsp;• <b>This closes the loop</b><br><br>"
            "Biologically: <b>k<sub>f</sub></b> is the reflex gain and "
            "<b>τ</b> is the neural delay (~30–50 ms)."))
        self.add(n)

        # ---- interactive ------------------------------------------------------
        i = Card("run it")
        i.add(body(
            "One gait cycle of an ankle plantarflexor. Raise the reflex gain and "
            "watch the push-off peak grow out of a constant, unchanging EMG "
            "command — that is amplification you did not have to command. Then "
            "<b>turn the phase gate off</b> and watch the same gain become a "
            "runaway.", dim=True))

        self.s_kf = slider(0, 60, 12)
        self.s_delay = slider(0, 120, 40)
        self.s_emg = slider(1, 60, 15)
        self.l_kf, self.l_delay, self.l_emg = QLabel(), QLabel(), QLabel()
        i.add_layout(slider_row("reflex gain k_f (×10⁻⁵)", self.s_kf, self.l_kf))
        i.add_layout(slider_row("neural delay τ (ms)", self.s_delay, self.l_delay))
        i.add_layout(slider_row("EMG command a_EMG (%)", self.s_emg, self.l_emg))

        self.gate = QCheckBox("phase gate ON  (loop active only during stance / "
                              "push-off, 10–60%)")
        self.gate.setChecked(True)
        self.gate.stateChanged.connect(self._redraw)
        i.add(self.gate)

        self.st_gain = Stat("loop gain G", "--", theme.VIOLET)
        self.st_peak = Stat("peak force", "--", theme.GOOD)
        self.st_amp = Stat("amplification", "--", theme.ACCENT)
        self.st_stable = Stat("verdict", "--", theme.GOOD)
        i.add_layout(stat_row(self.st_gain, self.st_peak, self.st_amp,
                              self.st_stable))

        self.canvas = MplCanvas(width=7.5, height=3.6, nrows=2)
        i.add(self.canvas)
        self.add(i)
        for s_ in (self.s_kf, self.s_delay, self.s_emg):
            s_.valueChanged.connect(self._redraw)
        self._redraw()

        self.add(callout(
            "<b>What you just saw.</b> Loop gain G = k<sub>f</sub>·F<sub>max</sub>"
            "·f<sub>l</sub>·f<sub>v</sub>. Below 1 the loop decays and merely "
            "boosts. Above 1 it grows — and the <i>only</i> thing keeping "
            "biology safe at that point is that the gate closes before the "
            "exponential has time to matter. Phase-gated, time-limited, and "
            "damped by compliant tissue. Take any one of those away and it is "
            "exactly as unstable as your instincts said.", "warn"))

        code = Card("the loop, in full")
        pane = CodePane(get_source(PffLoop.step))
        pane.sizeHintLine(18)
        code.add(pane)
        self.add(code)

        # ---- robot side --------------------------------------------------------
        self.add(hline())
        self.add(title("Where does force come from in a robot?"))

        r = Card("three sources — valid, but not equivalent")
        r.add(body(
            "<b>1. Direct force/torque sensor</b> — load cell, strain gauge<br>"
            "<b>2. Motor current</b> — τ ∝ I<br>"
            "<b>3. Estimated force</b> — from dynamics, from motor + kinematics, "
            "or from an impedance model<br><br>"
            "All are valid, but <b>they are not equivalent conceptually</b>."))
        self.add(r)

        self.add(hline())
        self.add(title("The honesty test"))

        h = Card("Case A — no force feedback loop (most common)")
        h.add(body("If your controller is:"))
        h.add(math_label(r"a = a_{EMG} \qquad F = f(a, l, \dot l)", 16))
        h.add(body(
            "then:<br><br>"
            "&nbsp;&nbsp;✘ This is <b>NOT</b> positive force feedback<br>"
            "&nbsp;&nbsp;☑ This is <b>neuromuscular feedforward control</b><br><br>"
            "Still bio-inspired — but <b>not reflexive PFF</b>."))
        self.add(h)

        h2 = Card("Case B — force modifies activation (true PFF)")
        h2.add(body("If your controller does:"))
        h2.add(math_label(r"a(t) = a_{EMG}(t) + k_f \cdot \hat F(t - \tau)", 16))
        h2.add(body(
            "where F̂ is measured torque, motor current, or estimated tendon "
            "force, then:<br><br>"
            "&nbsp;&nbsp;☑ This <b>IS</b> positive force feedback. The loop is "
            "closed on <b>force</b>."))
        self.add(h2)

        f = Card("so where does the feedback come from?")
        f.add(body(
            "<b>Correct answers</b> (depending on implementation):<br>"
            "&nbsp;&nbsp;• from measured joint torque<br>"
            "&nbsp;&nbsp;• from motor current<br>"
            "&nbsp;&nbsp;• from estimated muscle / tendon force<br><br>"
            "<b>Incorrect answer:</b><br>"
            "&nbsp;&nbsp;• from EMG alone — <b>EMG is command, not feedback</b>."))
        self.add(f)

        self.add(callout(
            "<b>How to describe your own project accurately.</b><br><br>"
            "<b>If you did NOT close force feedback:</b> \"I implemented a "
            "neuromuscular ankle controller based on EMG-driven activation and "
            "muscle force generation, inspired by reflex-based control, but "
            "without closing an explicit force feedback loop.\"<br><br>"
            "<b>If you DID close it (even weakly):</b> \"I incorporated a "
            "reflex-inspired positive force feedback term, where estimated joint "
            "torque modulated activation to enable load-dependent ankle "
            "assistance.\"<br><br>"
            "<b>Never claim PFF unless the loop is explicit.</b>", "good"))

        self.add(callout(
            "<b>One-sentence mental model — remember this.</b><br><br>"
            "<b>Positive force feedback exists only if force changes "
            "activation.</b> If force does not affect activation, it's not "
            "feedback.", "key"))

        self.finish()

    def _redraw(self):
        kf = self.s_kf.value() * 1e-5
        delay = self.s_delay.value() / 1000.0
        emg = self.s_emg.value() / 100.0
        gated = self.gate.isChecked()
        self.l_kf.setText(f"{self.s_kf.value()}")
        self.l_delay.setText(f"{self.s_delay.value()} ms")
        self.l_emg.setText(f"{emg * 100:.0f}%")

        t, f, a, ph = run_pff(kf, delay, gated, emg)
        _, f0, _, _ = run_pff(0.0, delay, gated, emg)

        g = loop_gain(kf, 3000.0, 1.0, -0.3)
        self.st_gain.set(f"{g:.2f}")
        self.st_peak.set(f"{max(f):.0f} N")
        base = max(f0) or 1.0
        self.st_amp.set(f"{max(f) / base:.2f}×")

        if g < 0.85:
            verdict, colour = "amplifies, decays", theme.GOOD
        elif g < 1.0:
            verdict, colour = "marginal", theme.WARN
        elif gated:
            verdict, colour = "gate saves it", theme.WARN
        else:
            verdict, colour = "RUNAWAY", theme.BAD
        self.st_stable.set(verdict)
        self.st_stable.set_color(colour)

        c = self.canvas
        c.clear()
        a1, a2 = c.axes
        pct = [p * 100 for p in ph]
        a1.plot(pct, f0, color=theme.TEXT_FAINT, lw=1.4, ls="--",
                label="k_f = 0  (pure feedforward)")
        a1.plot(pct, f, color=colour, lw=2.4, label="with force feedback")
        if gated:
            a1.axvspan(10, 60, color=theme.GOOD, alpha=0.08)
            a1.text(35, max(max(f), 1) * 0.06, "gate open", color=theme.GOOD,
                    fontsize=8, ha="center")
        a1.set_ylabel("muscle force  (N)")
        c.legend(a1, loc="upper left")

        a2.plot(pct, a, color=theme.ACCENT, lw=2.0, label="activation a(t)")
        a2.axhline(emg, color=theme.TEXT_FAINT, lw=1.2, ls="--",
                   label="a_EMG (the command)")
        a2.set_xlabel("gait cycle (%)")
        a2.set_ylabel("activation")
        a2.set_ylim(0, 1.05)
        c.legend(a2, loc="upper left")
        c.refresh()
