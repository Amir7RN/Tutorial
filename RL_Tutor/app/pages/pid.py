"""
PID in practice: the four defences that separate a textbook PID from one
that works on hardware.

Placed straight after Position Control because a position controller IS a
PID, and every failure mode below is a failure of the page before it.

The through-line, and it answers a specific question directly:

    If the loop jitters, WHICH term breaks?  ->  D, almost exclusively.
    P has no time in it. I averages its errors away over many ticks.
    D is a division by dt, so a wrong dt is a proportionally wrong D --
    in the one term whose job is to predict, and which already amplifies
    noise more than anything else in the loop.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel, QTableWidget, QTableWidgetItem

from ctrlcore.realtime import PID, derivative_error_from_jitter, run_pid
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
    labelled,
    math_label,
    stat_row,
    title,
)
from .base import Page
from .motors import slider, slider_row

SECTION = "Control Paradigms"


class PIDPracticePage(Page):
    TITLE = "PID in Practice"
    SUBTITLE = ("Anti-windup, derivative filtering, and what timing jitter "
                "actually breaks. The gap between the equation and the robot.")
    SECTION = SECTION
    NOTES = "real-time"

    def __init__(self, parent=None):
        super().__init__(parent)

        e = Card("the equation, and what each term is really for")
        e.add(math_label(r"u(t) = K_p\,e(t) + K_i\!\int_0^t\! e(\tau)\,d\tau "
                         r"+ K_d\,\frac{de(t)}{dt}", 17))
        e.add(body(
            (
                "<b>P — the present.</b> Proportional to the error right now. Does the work. Raise it for "
                "stiffness and speed; raise it too far and the loop oscillates because the phase lag around the "
                "loop reaches −180° while the gain is still above 1.<br><br><b>I — the past.</b> Accumulates. "
                "Exists to kill <b>steady-state error</b>: with a constant load, a pure P controller must hold a"
                " standing error to generate the holding torque, and I is what removes it. Costs phase (it is a "
                "lag), so its effect on stability must be assessed in the full loop.<br><br><b>D — the "
                "future.</b> Predicts where the error is heading and acts early. Adds damping and phase "
                "<i>lead</i>, which can improve damping. D amplifies high-frequency noise especially strongly; P"
                " can amplify noise too, and both I and D depend on elapsed time."
            )))
        self.add(e)

        self.add(callout(
            "<b>Frequency reading, which is the useful one.</b> P acts on the "
            "error's magnitude at all frequencies. I has huge gain at low "
            "frequency (kills DC error) and none at high. D has gain rising with "
            "frequency (hence the noise problem) and contributes <b>+90° of "
            "phase</b>, which is why it buys stability back from the phase you "
            "lost to delay on page 1.", "key"))

        # ==================================================================
        self.add(hline())
        self.add(title("Defence 1 — integral windup"))

        w = Card("what goes wrong")
        w.add(body(
            "Every actuator saturates. Your motor has a current limit, and that "
            "is a torque limit."))
        w.add(body(
            "Now suppose the joint is blocked — a person is holding it, or it is "
            "against a hard stop. The error stays large. The integrator keeps "
            "accumulating, second after second, climbing to a number that the "
            "actuator could never deliver. Then the obstruction is "
            "<b>removed</b>.<br><br>"
            "The joint now flies. It has to <i>overshoot in the opposite "
            "direction long enough to integrate all that accumulated area back "
            "out</i>. On a robot arm that is a violent, unexplained lunge "
            "seconds after the thing that caused it."))
        self.add(w)

        f = Card("three fixes, in increasing order of quality")
        f.add(body(
            "<b>1 · Clamping the integrator</b> (\"conditional integration\"). "
            "Stop accumulating whenever the output is saturated <i>and</i> the "
            "error would push further into the stop. Trivial to implement, and "
            "good enough for most joint loops.<br><br>"
            "<b>2 · Back-calculation</b> (\"tracking anti-windup\"). Feed the "
            "difference between the saturated and unsaturated output back into "
            "the integrator:"))
        f.add(math_label(r"\dot I = K_i e + K_t\,(u_{sat} - u_{unsat})", 16))
        f.add(body(
            (
                "The integrator is continuously bled toward whatever value would have produced the achievable "
                "output. Smoother recovery than clamping, at the cost of one more gain (K<sub>t</sub>, typically"
                " ≈ 1/T<sub>i</sub>).<br><br><b>3 · Incremental (velocity) form.</b> Compute Δu each tick and "
                "accumulate on the <i>output</i> instead of on the error. The saturation then lives on the same "
                "variable you are integrating, but the accumulated output must be limited and reconciled with "
                "the actual actuator command to prevent windup. Also makes bumpless auto/manual transfer nearly "
                "free."
            ), dim=True))
        self.add(f)

        i = Card("watch it wind up, then watch the fix")
        i.add(body(
            "<b>The joint is held immovable for the first 1.5 s</b> — a hard stop, "
            "or a hand gripping it — and then released. Output is clamped to "
            "±12 N·m.<br><br>"
            "Switch anti-windup to <b>none</b> and watch the integral trace climb "
            "long after the output has flatlined at the limit. Then watch what "
            "happens at 1.5 s. That lunge is not a new fault: it is the stored "
            "area being paid back, seconds after the thing that caused it.",
            dim=True))

        self.aw = QComboBox()
        for k, lab in (("none", "none — let it wind up"),
                       ("clamp", "clamp (conditional integration)"),
                       ("back_calc", "back-calculation (tracking)")):
            self.aw.addItem(lab, k)
        self.aw.setCurrentIndex(1)
        self.aw.currentIndexChanged.connect(self._redraw_windup)
        i.add_layout(labelled("Anti-windup", self.aw, width=150))

        self.s_ki = slider(0, 400, 120)
        self.s_hold = slider(0, 30, 15)
        self.l_ki, self.l_hold = QLabel(), QLabel()
        i.add_layout(slider_row("K_i", self.s_ki, self.l_ki))
        i.add_layout(slider_row("joint held for (×0.1 s)", self.s_hold,
                                self.l_hold))

        self.st_over = Stat("overshoot", "--", theme.BAD)
        self.st_imax = Stat("peak integral", "--", theme.WARN)
        self.st_sat = Stat("time saturated", "--", theme.ACCENT)
        i.add_layout(stat_row(self.st_over, self.st_imax, self.st_sat))
        self.c1 = MplCanvas(width=7.4, height=3.5, nrows=2)
        i.add(self.c1)
        self.add(i)
        self.s_ki.valueChanged.connect(self._redraw_windup)
        self.s_hold.valueChanged.connect(self._redraw_windup)
        self._redraw_windup()

        # ==================================================================
        self.add(hline())
        self.add(title("Defence 2 — the derivative term, which is where jitter "
                       "lands"))

        d = Card("why D and not P or I")
        d.add(body("The discrete derivative is"))
        d.add(math_label(r"D_k \approx K_d\,\frac{e_k - e_{k-1}}{\Delta t}", 17))
        d.add(body(
            "<b>Δt is in the denominator.</b> That is the whole story. If the "
            "loop was supposed to run every 1.00 ms but actually ran 1.10 ms "
            "later, and your code divides by the constant 0.001 you typed at the "
            "top of the file, then your derivative estimate is wrong by about "
            "<b>9%</b> — this tick, and every tick, in a random direction."))
        d.add(body(
            "&nbsp;&nbsp;<b>P</b> has no Δt in it. Jitter does not touch it.<br>"
            "&nbsp;&nbsp;<b>I</b> multiplies by Δt. Errors are of opposite sign "
            "on alternate ticks and largely average out over the integration "
            "window.<br>"
            "&nbsp;&nbsp;<b>D</b> divides by Δt, does not average, and its output "
            "is already the noisiest signal in the loop. It takes essentially "
            "all the damage.", dim=True))
        d.add(math_label(r"\frac{D_{est}}{D_{true}} = "
                         r"\frac{T_{nominal}}{T_{actual}} = \frac{1}{1+j}", 16))
        self.add(d)

        fix = Card("the fixes, and they are not \"reduce jitter\"")
        fix.add(body(
            "<b>1 · Measure Δt and divide by the real number.</b> Read a hardware "
            "timer at the top of the ISR. This is one line and removes most of "
            "the problem. Jitter in <i>when</i> you sample still costs you a "
            "little, but jitter in <i>what you think the interval was</i> is "
            "pure self-inflicted error.<br><br>"
            "<b>2 · Filter the derivative</b> (\"dirty derivative\"). Replace the "
            "ideal <i>s</i> with"))
        fix.add(math_label(r"\frac{N s}{s + N}\qquad\text{i.e. a first-order "
                           r"low-pass on }D", 16))
        fix.add(body(
            (
                "Pure differentiation has gain rising forever with frequency, so it turns encoder quantisation "
                "into audible motor buzz and heat. Here N is the derivative filter pole in rad/s; a starting "
                "estimate is 8–20 times the angular crossover, followed by noise and margin checks. Never ship "
                "an unfiltered derivative.<br><br><b>3 · Differentiate the measurement, not the error.</b> "
                "d(−y)/dt instead of de/dt. A step change in the setpoint then produces <b>no impulse</b> in the"
                " output — the notorious \"derivative kick\" that slams the motor every time an operator types a "
                "new target. The plant did not move; only your wish did.<br><br><b>4 · Do not differentiate at "
                "all if you can avoid it.</b> Use a velocity sensor, or a state observer / Kalman filter that "
                "estimates velocity from the model plus the position measurement. This is what high-end drives "
                "actually do."
            ), dim=True))
        self.add(fix)

        i2 = Card("inject jitter and watch D fall apart")
        i2.add(body(
            "Turn jitter up with <b>\"controller assumes nominal dt\"</b> ticked, "
            "then untick it. Same jitter, but the second case divides by the "
            "interval that actually elapsed. Then add the derivative filter.",
            dim=True))
        self.s_jit = slider(0, 60, 0)
        self.s_taud = slider(0, 40, 0)
        self.s_noise = slider(0, 50, 8)
        self.l_jit, self.l_taud, self.l_noise = QLabel(), QLabel(), QLabel()
        i2.add_layout(slider_row("timing jitter (%)", self.s_jit, self.l_jit))
        i2.add_layout(slider_row("D filter τ (×0.1 ms)", self.s_taud, self.l_taud))
        i2.add_layout(slider_row("encoder noise (×1e-5 rad)", self.s_noise,
                                 self.l_noise))
        self.chk_nominal = QCheckBox("controller assumes nominal dt  (the bug)")
        self.chk_nominal.setChecked(True)
        self.chk_nominal.stateChanged.connect(self._redraw_jitter)
        i2.add(self.chk_nominal)
        self.chk_dmeas = QCheckBox("differentiate measurement, not error  (kills "
                                   "setpoint kick)")
        self.chk_dmeas.setChecked(True)
        self.chk_dmeas.stateChanged.connect(self._redraw_jitter)
        i2.add(self.chk_dmeas)

        self.st_derr = Stat("D error from jitter", "--", theme.BAD)
        self.st_chatter = Stat("control chatter", "--", theme.WARN)
        self.st_settle = Stat("final error", "--", theme.GOOD)
        i2.add_layout(stat_row(self.st_derr, self.st_chatter, self.st_settle))
        self.c2 = MplCanvas(width=7.4, height=3.5, nrows=2)
        i2.add(self.c2)
        self.add(i2)
        for s_ in (self.s_jit, self.s_taud, self.s_noise):
            s_.valueChanged.connect(self._redraw_jitter)
        self._redraw_jitter()

        # ==================================================================
        self.add(hline())
        self.add(title("Defence 3 — sampling and Nyquist, applied"))

        s = Card("choosing f_s for a PID")
        s.add(body(
            (
                "<b>Starting rule of thumb:</b> sample 10–20× your desired closed-loop bandwidth, then check "
                "delay and margins. Not 2×. Nyquist's 2× is the bound for <i>reconstructing a signal</i>; a "
                "control loop additionally has to pay zero-order-hold delay, computation delay, and phase margin"
                " — see page 1.<br><br><b>Prevent aliasing before sampling.</b> An analog filter must "
                "sufficiently attenuate unwanted content by f<sub>s</sub>/2 before the ADC; a corner below "
                "Nyquist alone is insufficient. Digital filtering before later downsampling serves the same role"
                " for that downsampling step. A geared joint is full of tooth-mesh energy at hundreds of Hz that"
                " will otherwise fold down into your control band and be indistinguishable from a real "
                "disturbance.<br><br><b>Quantisation sets your derivative floor.</b> A 12-bit encoder on a 360° "
                "joint resolves 0.088°. Differentiating that at 1 kHz gives velocity steps of 88°/s. That "
                "number, not your gain choice, is what decides how much you can filter — and it is why 19–23 bit"
                " encoders exist on torque-controlled robots."
            )))
        self.add(s)

        # ==================================================================
        self.add(hline())
        self.add(title("Defence 4 — the loop must be honest about time"))

        code = Card("the PID this tutor actually runs")
        pane = CodePane(get_source(PID.step))
        pane.sizeHintLine(24)
        code.add(pane)
        code.add(body(
            "Note what is <i>not</i> in it: no allocation, no branching on data "
            "length, no I/O. Bounded worst-case execution time is a property you "
            "design in, not one you measure afterwards and hope for.", dim=True))
        self.add(code)

        t = Card("tuning, in the order that works")
        t.add(body(
            "<b>1.</b> Set K<sub>i</sub> = K<sub>d</sub> = 0. Raise K<sub>p</sub> "
            "until the response is fast and just barely oscillates. Halve it.<br>"
            "<b>2.</b> Add K<sub>d</sub> to damp the overshoot. <i>Filter it</i>. "
            "Stop when you hear the motor.<br>"
            "<b>3.</b> Add K<sub>i</sub> only if you actually have steady-state "
            "error. Add anti-windup <b>at the same time</b>, never afterwards.<br>"
            "<b>4.</b> Test against the saturation limit and against a blocked "
            "joint. Most PID bugs only appear when the actuator runs out of "
            "authority."))
        t.add(body(
            "<b>Better than all of the above:</b> add a feedforward term. If you "
            "know the gravity torque, apply it directly rather than making the "
            "integrator discover it. Feedback should be correcting the model's "
            "mistakes, not doing the model's job — which is exactly the "
            "τ<sub>ff</sub> argument that returns on the Impedance Spectrum "
            "page.", dim=True))
        self.add(t)

        self.add(callout(
            (
                "<b>Carry forward.</b> Jitter affects sampled feedback and both I and D; it is particularly "
                "visible in <b>D</b>. Saturation creates <b>windup</b> in I. Noise is amplified by <b>D</b>. "
                "Steady-state load requires <b>I</b> — or, far better, a feedforward term. Every controller in "
                "the rest of this section is built out of these parts, so every one of them inherits these "
                "failure modes."
            ), "good"))

        self.finish()

    # ------------------------------------------------------------------
    def _redraw_windup(self):
        ki = self.s_ki.value() * 1.0
        hold = self.s_hold.value() * 0.1
        mode = self.aw.currentData()
        self.l_ki.setText(f"{ki:.0f}")
        self.l_hold.setText(f"{hold:.1f} s")

        pid = PID(kp=40.0, ki=ki, kd=3.0, tau_d=0.002, anti_windup=mode,
                  out_min=-12.0, out_max=12.0)
        tr = run_pid(pid, setpoint=0.35, duration=4.0,
                     block_until=hold if hold > 0 else None)

        target = 0.35
        over = max(0.0, max(tr.y) - target)
        self.st_over.set(f"{over / target * 100:.0f}%")
        self.st_imax.set(f"{max(abs(v) for v in tr.i):.0f}")
        sat = sum(1 for u in tr.u if abs(abs(u) - 12.0) < 1e-6) / max(1, len(tr.u))
        self.st_sat.set(f"{sat * 100:.0f}%")

        c = self.c1
        c.clear()
        a1, a2 = c.axes
        a1.plot(tr.t, tr.y, color=theme.ACCENT, lw=2.0, label="θ")
        a1.axhline(target, color=theme.TEXT_FAINT, lw=1.2, ls="--", label="target")
        if hold > 0:
            a1.axvspan(0, hold, color=theme.BAD, alpha=0.10)
            a1.text(hold / 2, target * 0.5, "joint held", color=theme.BAD,
                    fontsize=8, ha="center")
        a1.set_ylabel("θ (rad)")
        c.legend(a1, loc="lower right")
        a2.plot(tr.t, tr.u, color=theme.BAD, lw=1.6, label="output u (saturated)")
        a2.plot(tr.t, tr.i, color=theme.WARN, lw=1.6, ls="--",
                label="integral term")
        a2.axhline(12, color=theme.TEXT_FAINT, lw=1.0, ls=":")
        a2.axhline(-12, color=theme.TEXT_FAINT, lw=1.0, ls=":",
                   label="actuator limit")
        a2.set_xlabel("time (s)")
        a2.set_ylabel("N·m")
        c.legend(a2, loc="upper right")
        c.refresh()

    # ------------------------------------------------------------------
    def _redraw_jitter(self):
        jit = self.s_jit.value() / 100.0
        taud = self.s_taud.value() * 0.0001
        noise = self.s_noise.value() * 1e-5
        nominal = self.chk_nominal.isChecked()
        dmeas = self.chk_dmeas.isChecked()
        self.l_jit.setText(f"{jit * 100:.0f}%")
        self.l_taud.setText(f"{taud * 1000:.1f} ms" if taud > 0 else "off")
        self.l_noise.setText(f"{noise:.0e}")

        pid = PID(kp=40.0, ki=0.0, kd=3.0, tau_d=taud, anti_windup="clamp",
                  d_on_measurement=dmeas)
        tr = run_pid(pid, setpoint=0.35, duration=1.4, jitter_frac=jit,
                     use_nominal_dt=nominal, noise=noise)

        derr = derivative_error_from_jitter(jit) if (jit > 0 and nominal) else 0.0
        self.st_derr.set(f"{derr * 100:.0f}%")
        self.st_derr.set_color(theme.BAD if derr > 0.05 else theme.GOOD)
        chatter = (sum(abs(b - a) for a, b in zip(tr.u, tr.u[1:]))
                   / max(1, len(tr.u) - 1))
        self.st_chatter.set(f"{chatter:.2f}")
        self.st_settle.set(f"{abs(0.35 - tr.y[-1]) * 1000:.1f} mrad")

        c = self.c2
        c.clear()
        a1, a2 = c.axes
        a1.plot(tr.t, tr.y, color=theme.ACCENT, lw=1.8, label="θ")
        a1.axhline(0.35, color=theme.TEXT_FAINT, lw=1.2, ls="--", label="target")
        a1.set_ylabel("θ (rad)")
        c.legend(a1, loc="lower right")
        a2.plot(tr.t, tr.d, color=theme.BAD, lw=1.0, label="D term")
        a2.set_xlabel("time (s)")
        a2.set_ylabel("D contribution (N·m)")
        c.legend(a2, loc="upper right")
        c.refresh()
