"""
The two pages that sit between "what is a control problem" and the
first-order machinery, and answer the two questions that make the rest of it
mean anything on real hardware:

  1  Measuring a Real Joint      where J, b and k actually come from -- the
                                 four bench experiments, and the least-squares
                                 regression that industry actually uses
  2  How Software Changes        the one that everybody gets stuck on:
     Physics                     software cannot change J or b, so how can a
                                 gain change the behaviour? Because it changes
                                 the TORQUE, and substituting a state-dependent
                                 torque into Newton's law changes the equation
                                 of motion itself

The first has to come before the second because you cannot control what you
have not measured, and the second has to come before any pole is discussed
because "the controller moves the poles" is meaningless until you have seen a
controller gain appear as a coefficient in a differential equation.
"""

from __future__ import annotations

import math

import numpy as np

from PySide6.QtWidgets import QComboBox, QLabel

from ctrlcore.linear import TF, step_response
from .. import theme
from ..widgets import (
    Card,
    MplCanvas,
    Stat,
    body,
    callout,
    hline,
    math_label,
    stat_row,
    title,
)
from .base import Page
from .motors import slider, slider_row
from .firstorder import _btn_row, _lcg, _readout, _splane

SECTION = "Systems & Stability"

# the joint every experiment on these two pages is run against
J_TRUE = 0.25          # kg m^2   link + reflected rotor
B_TRUE = 0.40          # N m s    viscous friction
FC_TRUE = 0.60         # N m      Coulomb friction
MGL_TRUE = 2.00        # N m      gravity torque at full extension
K_TRUE = 900.0         # N m /rad transmission stiffness


# ==========================================================================
# PAGE -- measuring a real joint
# ==========================================================================

class MeasuringPage(Page):
    TITLE = "Measuring a Real Joint"
    SUBTITLE = ("Where J, b and k actually come from. Four bench experiments "
                "you can run this afternoon, and the regression that gets all "
                "of them at once.")
    SECTION = SECTION
    NOTES = "orientation"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>Nobody looks these numbers up.</b> You are handed an elbow: a "
            "motor, a gearbox, a shaft, a forearm. Its inertia is whatever the "
            "aluminium happens to weigh and wherever it happens to sit, its "
            "friction is whatever the bearings and the seals do today, and its "
            "stiffness is whatever the harmonic drive and the shaft add up to. "
            "<b>Every one of those is measured</b>, and each has a standard "
            "experiment that takes minutes.", "key"))

        # ---- the three numbers ---------------------------------------------
        w = Card("the three numbers, and where each one comes from")
        w.add(body(
            "<table cellpadding='7'>"
            "<tr><td><b>Number</b></td><td><b>What it physically is</b></td>"
            "<td><b>How you get it</b></td></tr>"

            "<tr><td><b>J</b><br>inertia<br><i>kg·m²</i></td>"
            "<td>How much torque it takes to change the speed. For a joint it "
            "is the link's own inertia about the joint axis <b>plus</b> the "
            "rotor's inertia multiplied by N² — and on a geared joint that "
            "second term usually dominates.</td>"
            "<td>CAD mass properties are the starting estimate and are usually "
            "10–30% wrong. Measure it: a <b>pendulum swing</b> test, or an "
            "<b>acceleration</b> test, or the regression below.</td></tr>"

            "<tr><td><b>b</b><br>viscous friction<br><i>N·m·s</i></td>"
            "<td>Torque lost in proportion to speed — oil shear, seals, "
            "windage. Not the whole story: see the warning below.</td>"
            "<td><b>Constant-speed sweep</b>: hold several speeds, record the "
            "torque at each, and the slope of torque-vs-speed is b. Or a "
            "<b>coast-down</b>.</td></tr>"

            "<tr><td><b>k</b><br>stiffness<br><i>N·m/rad</i></td>"
            "<td>How much the transmission and the structure wind up under "
            "load. Harmonic drives are springs; so are long shafts, belts and "
            "thin links.</td>"
            "<td><b>Static deflection</b>: lock the output, apply a known "
            "torque, measure the twist. Or a <b>tap test</b> — hit it and read "
            "the ringing frequency, since ω<sub>n</sub> = √(k/J).</td></tr>"
            "</table>"))
        w.add(callout(
            "<b>The warning that catches everyone: real friction is not b·ω.</b> "
            "A real joint has <b>Coulomb friction</b> — a roughly constant "
            "torque that opposes motion regardless of speed — on top of the "
            "viscous term, plus <b>stiction</b>, which is larger still and only "
            "shows up at zero speed. So the honest model is<br><br>"
            "&nbsp;&nbsp;τ<sub>friction</sub> = b·ω + f<sub>c</sub>·sign(ω)"
            "<br><br>"
            "and if you fit only b you will get a number that is wrong at every "
            "speed except the one you fitted at. This is why the first-order "
            "picture is an approximation: sign(ω) is not linear, and a joint "
            "that is <i>modelled</i> as first order still has a dead zone near "
            "zero speed where it does something else entirely.", "warn"))
        self.add(w)

        # ---- interactive: the four experiments ------------------------------
        self.add(hline())
        self.add(title("Interactive — the four experiments, and the arithmetic "
                       "you do afterwards"))

        e = Card("what the scope shows, and what you read off it")
        e.add(body(
            "Each entry is a real bench procedure. The plot is what your data "
            "logger would show, complete with sensor noise — turn it up and "
            "watch the estimates degrade, which is the honest part. The panel "
            "underneath is the arithmetic, and the chips compare what you "
            "extracted against the truth the simulation used.", dim=True))
        self.exp_box = QComboBox()
        for n in ("1 · coast-down          (cut the power, watch it slow)",
                  "2 · torque step         (hold a torque, wait for steady speed)",
                  "3 · pendulum swing      (let the link swing, time it)",
                  "4 · tap test            (hit it, listen to the ring)"):
            self.exp_box.addItem(n)
        e.add_layout(_btn_row(self.exp_box))
        self.s_noise = slider(0, 100, 15)
        self.l_noise = QLabel()
        e.add_layout(slider_row("sensor noise", self.s_noise, self.l_noise))
        self.st_e1 = Stat("measured", "--", theme.ACCENT)
        self.st_e2 = Stat("gives", "--", theme.GOOD)
        self.st_e3 = Stat("true value", "--", theme.TEXT_DIM)
        self.st_e4 = Stat("error", "--", theme.WARN)
        e.add_layout(stat_row(self.st_e1, self.st_e2, self.st_e3, self.st_e4))
        self.c_exp = MplCanvas(width=7.4, height=3.0, ncols=2)
        e.add(self.c_exp)
        self.exp_text = _readout()
        e.add(self.exp_text)
        self.add(e)
        self.exp_box.currentIndexChanged.connect(self._redraw_exp)
        self.s_noise.valueChanged.connect(self._redraw_exp)
        self._redraw_exp()

        # ---- the regression --------------------------------------------------
        self.add(hline())
        self.add(title("How it is really done: one trajectory, all the "
                       "parameters at once"))

        r = Card("the property that makes identification easy — linear in the "
                 "parameters")
        r.add(body(
            "Write the joint's equation of motion with every effect you believe "
            "in:"))
        r.add(math_label(r"\tau = J\,\dot\omega + b\,\omega "
                         r"+ f_c\,\mathrm{sign}(\omega) + mgl\,\sin\theta", 17))
        r.add(body(
            "It is <b>nonlinear in the motion</b> — there is a sign() and a "
            "sin() in there. But look at it as an equation in the "
            "<i>parameters</i> J, b, f<sub>c</sub>, mgl: each one appears "
            "exactly once, multiplied by something you can measure and added "
            "to the rest. So it can be written as a row times a column:"))
        r.add(math_label(r"\tau = \underbrace{\left[\;\dot\omega \;\;\; \omega "
                         r"\;\;\; \mathrm{sign}(\omega) \;\;\; \sin\theta\;"
                         r"\right]}_{\text{measured}}\;"
                         r"\underbrace{\left[J \;\; b \;\; f_c \;\; mgl"
                         r"\right]^{T}}_{\text{unknown}}", 16))
        r.add(callout(
            "<b>That is the whole trick, and it is standard: robot dynamics are "
            "<i>linear in the dynamic parameters</i>.</b> Move the joint around "
            "while logging torque, position, speed and acceleration. Every "
            "sample gives you one row. Stack ten thousand rows and solve the "
            "least-squares problem, and out come all four numbers at once — no "
            "special rig, no locked shafts, no separate experiments.<br><br>"
            "For a whole arm the same thing holds with a bigger row: "
            "τ = <b>Y</b>(q, q̇, q̈)·Θ, where Y is called the <b>regressor</b> "
            "and Θ holds every mass, centre of mass and inertia in the robot. "
            "It is how every manipulator you have used was calibrated.",
            "key"))
        self.add(r)

        rg = Card("interactive — and why the trajectory you drive matters more "
                  "than the maths")
        rg.add(body(
            "Same joint, same regression, three different motions. Watch the "
            "<b>condition number</b> — it measures how much the data pins the "
            "answer down.<br><br>"
            "<b>Rich excitation</b> moves through many speeds and accelerations "
            "and both directions, so every column of the regressor does "
            "something different and all four parameters come out. <b>One "
            "constant speed</b> is the classic mistake: with ω̇ = 0 the inertia "
            "column is <i>all zeros</i>, so the data contains no information "
            "about J whatsoever, and the solver returns a confident number that "
            "is pure noise. <b>Slow single sine</b> is in between: barely any "
            "acceleration, so J is poorly determined.", dim=True))
        self.traj_box = QComboBox()
        for n in ("rich excitation (sum of sinusoids, both directions)",
                  "slow single sine (hardly any acceleration)",
                  "one constant speed (no acceleration at all)"):
            self.traj_box.addItem(n)
        rg.add_layout(_btn_row(self.traj_box))
        self.s_rnoise = slider(0, 100, 20)
        self.l_rnoise = QLabel()
        rg.add_layout(slider_row("torque sensor noise", self.s_rnoise,
                                 self.l_rnoise))
        self.st_rj = Stat("J estimate", "--", theme.ACCENT)
        self.st_rb = Stat("b estimate", "--", theme.GOOD)
        self.st_rf = Stat("f_c estimate", "--", theme.VIOLET)
        self.st_rg = Stat("mgl estimate", "--", theme.CYAN)
        self.st_rc = Stat("condition number", "--", theme.WARN)
        rg.add_layout(stat_row(self.st_rj, self.st_rb, self.st_rf, self.st_rg,
                               self.st_rc))
        self.c_reg = MplCanvas(width=7.4, height=3.0, ncols=2)
        rg.add(self.c_reg)
        self.reg_text = _readout()
        rg.add(self.reg_text)
        self.add(rg)
        self.traj_box.currentIndexChanged.connect(self._redraw_reg)
        self.s_rnoise.valueChanged.connect(self._redraw_reg)
        self._redraw_reg()

        # ---- what you do NOT get --------------------------------------------
        n = Card("what identification gives you, and what it does not")
        n.add(body(
            "&nbsp;&nbsp;• <b>J is not a constant on an arm.</b> The inertia "
            "the elbow motor feels depends on where the wrist is — arm out, big "
            "inertia; arm folded, small. What you identify is the <b>inertia "
            "matrix</b> M(q), a function of configuration. On a single joint "
            "this shows up as \"the time constant changed when I extended the "
            "link\", which is real and not a measurement error.<br>"
            "&nbsp;&nbsp;• <b>Gravity depends on configuration too</b> — mgl·"
            "sinθ is zero straight down and maximal horizontal. That is why the "
            "regressor carries a sinθ column.<br>"
            "&nbsp;&nbsp;• <b>Friction is not stationary.</b> It changes with "
            "temperature, with load, with how long the joint has been running, "
            "and it has a stiction hump at zero speed that no linear fit will "
            "capture.<br>"
            "&nbsp;&nbsp;• <b>Backlash and hysteresis are invisible to a "
            "linear fit</b> and will silently pollute your parameters if the "
            "trajectory crosses zero speed a lot."))
        n.add(callout(
            "<b>The rule to carry: a model is only valid where you excited "
            "it.</b> Identify at 1 rad/s and the model will be wrong at "
            "50 rad/s. Identify with the arm folded and it will be wrong with "
            "the arm extended. This is not a flaw in the method — it is the "
            "reason robust control and gain scheduling exist, and the reason "
            "the nonlinear pages exist later on.", "warn"))
        self.add(n)

        self.add(callout(
            "<b>Carry forward.</b> J, b and k are measurements, not constants "
            "handed down. They are what set the plant's poles, and therefore "
            "everything the next pages say about speed and settling. The next "
            "page answers the other half of your question: given that those "
            "numbers are welded into the hardware, how can a line of software "
            "possibly change what the joint does?", "good"))

        self.finish()

    # ------------------------------------------------------------------
    def _redraw_exp(self):
        idx = self.exp_box.currentIndex()
        nz = self.s_noise.value() / 100.0
        self.l_noise.setText(f"{nz*100:.0f}%")
        rnd = _lcg(4242)

        c = self.c_exp
        c.clear()
        a1, a2 = c.axes

        if idx == 0:
            # ---- coast-down ------------------------------------------------
            tau_true = J_TRUE / B_TRUE
            w0 = 20.0
            dur = 5 * tau_true
            ts = [dur * i / 400 for i in range(401)]
            clean = [w0 * math.exp(-t / tau_true) for t in ts]
            meas = [v + nz * 0.9 * rnd() for v in clean]
            # fit the slope of log(omega) -- that IS the pole
            pts = [(t, math.log(max(v, 1e-3)))
                   for t, v in zip(ts, meas) if v > w0 * 0.08]
            n_ = len(pts)
            sx = sum(p[0] for p in pts)
            sy = sum(p[1] for p in pts)
            sxx = sum(p[0] * p[0] for p in pts)
            sxy = sum(p[0] * p[1] for p in pts)
            slope = (n_ * sxy - sx * sy) / max(n_ * sxx - sx * sx, 1e-12)
            tau_est = -1.0 / slope
            self.st_e1.set(f"τ = {tau_est*1000:.0f} ms")
            self.st_e2.set(f"J/b = {tau_est:.3f}")
            self.st_e3.set(f"{tau_true:.3f} s")
            self.st_e4.set(f"{abs(tau_est-tau_true)/tau_true*100:.1f}%")
            self.exp_text.setText(
                "<b>Procedure.</b> Spin the joint up to a comfortable speed, "
                "then <b>cut the drive current</b> and log the encoder while it "
                "coasts to a stop. Nothing is driving it, so the only thing "
                "acting is friction — which makes this the cleanest measurement "
                "on the bench.<br>"
                "<b>Arithmetic.</b> With no input, J·ω̇ = −b·ω, so ω decays "
                "exponentially with τ = J/b. Plot log(ω) against time: it is a "
                "<b>straight line whose slope is the pole</b>, and that is the "
                "same picture as the log-axis widget on page 6. Fit "
                "the slope, invert it, and you have τ.<br>"
                "<b>The catch.</b> This gives you the <i>ratio</i> J/b and "
                "nothing else. To split them you need one more experiment — "
                "which is why nobody does only one.")
            a1.plot(ts, clean, color=theme.TEXT_FAINT, lw=1.2, ls="--",
                    label="truth")
            a1.plot(ts, meas, color=theme.ACCENT, lw=1.6, label="measured")
            a1.axvline(tau_true, color=theme.GOOD, lw=1.0, ls=":")
            a1.axhline(w0 * 0.368, color=theme.GOOD, lw=1.0, ls=":",
                       label="36.8%")
            a1.set_xlabel("time (s)")
            a1.set_ylabel("speed ω (rad/s)")
            a1.set_title("power cut at t = 0", fontsize=9)
            c.legend(a1, loc="upper right")
            a2.semilogy([p[0] for p in pts],
                        [math.exp(p[1]) for p in pts],
                        color=theme.ACCENT, lw=1.6, label="measured")
            a2.semilogy(ts, [max(v, 1e-3) for v in clean],
                        color=theme.WARN, lw=1.2, ls="--",
                        label=f"fit: τ = {tau_est*1000:.0f} ms")
            a2.set_xlabel("time (s)")
            a2.set_ylabel("ω (log)")
            a2.set_title("log axis — the slope IS the pole", fontsize=9)
            c.legend(a2, loc="lower left")

        elif idx == 1:
            # ---- torque step -----------------------------------------------
            tau_c = J_TRUE / B_TRUE
            torque = 4.0
            w_ss = torque / B_TRUE
            dur = 5 * tau_c
            ts = [dur * i / 400 for i in range(401)]
            clean = [w_ss * (1 - math.exp(-t / tau_c)) for t in ts]
            meas = [v + nz * 0.9 * rnd() for v in clean]
            w_meas = sum(meas[-40:]) / 40.0
            b_est = torque / w_meas
            # 63% crossing
            target = 0.632 * w_meas
            t63 = next((t for t, v in zip(ts, clean) if v >= target), tau_c)
            j_est = b_est * t63
            self.st_e1.set(f"ω_ss = {w_meas:.2f}")
            self.st_e2.set(f"b = {b_est:.3f}, J = {j_est:.3f}")
            self.st_e3.set(f"b={B_TRUE}, J={J_TRUE}")
            self.st_e4.set(f"{abs(j_est-J_TRUE)/J_TRUE*100:.1f}% on J")
            self.exp_text.setText(
                "<b>Procedure.</b> Command a constant, known torque — on a "
                "motor that means a constant current, since τ = K<sub>t</sub>·i "
                "— and log the speed until it stops rising.<br>"
                "<b>Arithmetic.</b> Two readings from one trace. The "
                "<b>final speed</b> gives the friction directly: at steady "
                "state the torque you applied is exactly balanced by b·ω, so "
                "<b>b = τ / ω<sub>ss</sub></b>. The <b>63% time</b> gives the "
                "time constant, and since τ<sub>c</sub> = J/b you now get "
                "<b>J = b·τ<sub>c</sub></b>. One experiment, both numbers.<br>"
                "<b>The catch.</b> b comes out contaminated by Coulomb "
                "friction, because at a single speed you cannot tell a constant "
                "torque loss from a proportional one. Repeat at several torques "
                "and plot torque against speed: the <i>slope</i> is the real b "
                "and the <b>intercept is f<sub>c</sub></b>.")
            a1.plot(ts, clean, color=theme.TEXT_FAINT, lw=1.2, ls="--",
                    label="truth")
            a1.plot(ts, meas, color=theme.ACCENT, lw=1.6, label="measured")
            a1.axhline(w_meas, color=theme.GOOD, lw=1.0, ls="--",
                       label="ω_ss → b")
            a1.axhline(target, color=theme.WARN, lw=1.0, ls=":")
            a1.axvline(t63, color=theme.WARN, lw=1.0, ls=":", label="63% → τ")
            a1.set_xlabel("time (s)")
            a1.set_ylabel("speed ω (rad/s)")
            a1.set_title(f"constant {torque:.0f} N·m applied at t = 0",
                         fontsize=9)
            c.legend(a1, loc="lower right")
            # torque vs speed sweep, showing the intercept
            ws = [0.5 * i for i in range(1, 26)]
            tq = [B_TRUE * v + FC_TRUE + nz * 0.35 * rnd() for v in ws]
            a2.scatter(ws, tq, s=14, color=theme.ACCENT, label="measured")
            a2.plot(ws, [B_TRUE * v + FC_TRUE for v in ws], color=theme.WARN,
                    lw=1.4, label=f"slope b={B_TRUE}, intercept f_c={FC_TRUE}")
            a2.axhline(FC_TRUE, color=theme.GOOD, lw=1.0, ls=":")
            a2.set_xlim(0, 13)
            a2.set_ylim(0, max(tq) * 1.1)
            a2.set_xlabel("steady speed ω (rad/s)")
            a2.set_ylabel("torque needed (N·m)")
            a2.set_title("the sweep that separates b from f_c", fontsize=9)
            c.legend(a2, loc="upper left")

        elif idx == 2:
            # ---- pendulum swing --------------------------------------------
            wn = math.sqrt(MGL_TRUE / J_TRUE)
            zeta = B_TRUE / (2 * math.sqrt(MGL_TRUE * J_TRUE))
            wd = wn * math.sqrt(max(1 - zeta * zeta, 1e-6))
            per = 2 * math.pi / wd
            dur = 6 * per
            ts = [dur * i / 700 for i in range(701)]
            clean = [0.4 * math.exp(-zeta * wn * t) * math.cos(wd * t)
                     for t in ts]
            meas = [v + nz * 0.012 * rnd() for v in clean]
            j_est = MGL_TRUE / (wd * wd) * (1 - zeta * zeta)
            self.st_e1.set(f"period = {per*1000:.0f} ms")
            self.st_e2.set(f"J = {j_est:.3f}")
            self.st_e3.set(f"{J_TRUE:.3f} kg·m²")
            self.st_e4.set(f"{abs(j_est-J_TRUE)/J_TRUE*100:.1f}%")
            self.exp_text.setText(
                "<b>Procedure.</b> Switch the drive off so the joint is free, "
                "hold the link out to one side, and let go. Log the encoder "
                "while it swings. You need the link's <b>mass and centre of "
                "mass</b> first — a set of scales and a balance point, or CAD "
                "you trust — because gravity is the spring in this "
                "experiment.<br>"
                "<b>Arithmetic.</b> A hanging link is a pendulum: J·θ̈ + b·θ̇ "
                "+ mgl·sinθ = 0. For small swings sinθ ≈ θ, which is a "
                "mass–spring–damper with stiffness mgl. So ω<sub>n</sub> = "
                "√(mgl/J), and <b>timing the swings gives you J directly</b>. "
                "The shrinking envelope gives the damping: the ratio of "
                "successive peaks is the <b>logarithmic decrement</b>, and it "
                "converts straight to ζ and then to b.<br>"
                "<b>Why bother.</b> This is the one experiment that measures J "
                "with the motor switched off, so no torque constant, no current "
                "sensor and no gearbox efficiency can bias the answer.")
            a1.plot(ts, clean, color=theme.TEXT_FAINT, lw=1.2, ls="--",
                    label="truth")
            a1.plot(ts, meas, color=theme.ACCENT, lw=1.5, label="measured")
            env = [0.4 * math.exp(-zeta * wn * t) for t in ts]
            a1.plot(ts, env, color=theme.WARN, lw=1.0, ls=":",
                    label="envelope → ζ → b")
            a1.plot(ts, [-v for v in env], color=theme.WARN, lw=1.0, ls=":")
            for k in range(1, 4):
                a1.axvline(k * per, color=theme.GOOD, lw=0.9, ls=":")
            a1.set_xlabel("time (s)")
            a1.set_ylabel("angle θ (rad)")
            a1.set_title("released from 0.4 rad, drive off", fontsize=9)
            c.legend(a1, loc="upper right")
            # peak decay -> log decrement
            peaks = [(k * per, 0.4 * math.exp(-zeta * wn * k * per))
                     for k in range(0, 5)]
            a2.semilogy([p[0] for p in peaks], [p[1] for p in peaks],
                        marker="o", color=theme.ACCENT, lw=1.8,
                        label="peak heights")
            a2.set_xlabel("time (s)")
            a2.set_ylabel("peak amplitude (log)")
            a2.set_title(f"log decrement → ζ = {zeta:.3f}", fontsize=9)
            c.legend(a2, loc="lower left")

        else:
            # ---- tap test ---------------------------------------------------
            wn = math.sqrt(K_TRUE / J_TRUE)
            zeta = 0.04
            wd = wn * math.sqrt(1 - zeta * zeta)
            dur = 10 * 2 * math.pi / wd
            ts = [dur * i / 900 for i in range(901)]
            clean = [math.exp(-zeta * wn * t) * math.sin(wd * t) for t in ts]
            meas = [v + nz * 0.05 * rnd() for v in clean]
            f_meas = wd / (2 * math.pi)
            k_est = J_TRUE * (2 * math.pi * f_meas) ** 2 / (1 - zeta * zeta)
            self.st_e1.set(f"ring at {f_meas:.1f} Hz")
            self.st_e2.set(f"k = {k_est:.0f}")
            self.st_e3.set(f"{K_TRUE:.0f} N·m/rad")
            self.st_e4.set(f"{abs(k_est-K_TRUE)/K_TRUE*100:.1f}%")
            self.exp_text.setText(
                "<b>Procedure.</b> Clamp the motor side, hit the link with a "
                "soft mallet — an instrumented impact hammer if you are being "
                "careful — and log the encoder or an accelerometer. This is a "
                "<b>modal test</b>, and it is done exactly this way on real "
                "machines.<br>"
                "<b>Arithmetic.</b> The joint rings at its natural frequency, "
                "which for a mass on a spring is ω<sub>n</sub> = √(k/J). You "
                "already know J from the swing test, so <b>k = J·ω<sub>n</sub>²"
                "</b>. Count the cycles per second off the trace, or take an "
                "FFT and read the peak.<br>"
                "<b>Why this one matters most for control.</b> That ringing "
                "frequency is a <b>hard ceiling on your loop bandwidth</b>. "
                "Push the controller near it and you will excite it. Everything "
                "the tutor says later about notches, and about why gearboxes "
                "ruin transparency, is about this number — and it is measured "
                "with a hammer in about thirty seconds.")
            a1.plot(ts, meas, color=theme.ACCENT, lw=1.2, label="measured")
            env = [math.exp(-zeta * wn * t) for t in ts]
            a1.plot(ts, env, color=theme.WARN, lw=1.0, ls=":", label="envelope")
            a1.plot(ts, [-v for v in env], color=theme.WARN, lw=1.0, ls=":")
            a1.set_xlabel("time (s)")
            a1.set_ylabel("response")
            a1.set_title("struck at t = 0", fontsize=9)
            c.legend(a1, loc="upper right")
            # crude spectrum
            fs = [0.2 * i for i in range(1, 260)]
            mag = [1.0 / math.sqrt((1 - (f / f_meas) ** 2) ** 2
                                   + (2 * zeta * f / f_meas) ** 2)
                   for f in fs]
            a2.semilogy(fs, mag, color=theme.ACCENT, lw=1.8)
            a2.axvline(f_meas, color=theme.GOOD, lw=1.2, ls=":",
                       label=f"peak = {f_meas:.1f} Hz")
            a2.set_xlabel("frequency (Hz)")
            a2.set_ylabel("magnitude")
            a2.set_title("spectrum — read the peak, get k", fontsize=9)
            c.legend(a2, loc="upper right")

        c.refresh()

    # ------------------------------------------------------------------
    def _redraw_reg(self):
        kind = self.traj_box.currentIndex()
        nz = self.s_rnoise.value() / 100.0
        self.l_rnoise.setText(f"{nz*100:.0f}%")

        dur, dt = 8.0, 0.002
        n = int(dur / dt)
        ts = np.arange(n) * dt

        if kind == 0:                                   # rich
            w = (2.6 * np.sin(2 * np.pi * 0.35 * ts)
                 + 1.7 * np.sin(2 * np.pi * 0.9 * ts + 1.1)
                 + 1.1 * np.sin(2 * np.pi * 2.1 * ts + 2.3))
        elif kind == 1:                                 # slow single sine
            w = 0.35 * np.sin(2 * np.pi * 0.05 * ts)
        else:                                           # constant speed
            w = np.full(n, 3.0)

        wdot = np.gradient(w, dt)
        th = np.cumsum(w) * dt
        tau = (J_TRUE * wdot + B_TRUE * w + FC_TRUE * np.sign(w)
               + MGL_TRUE * np.sin(th))
        rnd = _lcg(918273)
        tau_m = tau + nz * 1.2 * np.array([rnd() for _ in range(n)])

        Y = np.column_stack([wdot, w, np.sign(w), np.sin(th)])
        theta_hat, *_ = np.linalg.lstsq(Y, tau_m, rcond=None)
        cond = np.linalg.cond(Y)
        truth = [J_TRUE, B_TRUE, FC_TRUE, MGL_TRUE]

        for st, est, tv, unit in ((self.st_rj, theta_hat[0], J_TRUE, ""),
                                  (self.st_rb, theta_hat[1], B_TRUE, ""),
                                  (self.st_rf, theta_hat[2], FC_TRUE, ""),
                                  (self.st_rg, theta_hat[3], MGL_TRUE, "")):
            err = abs(est - tv) / tv * 100
            st.set(f"{est:.3f}{unit}")
            st.set_color(theme.GOOD if err < 10 else
                         (theme.WARN if err < 40 else theme.BAD))
        self.st_rc.set(f"{cond:.0f}" if cond < 1e6 else f"{cond:.1e}")
        self.st_rc.set_color(theme.GOOD if cond < 100 else
                             (theme.WARN if cond < 1e4 else theme.BAD))

        msgs = [
            ("<b>Rich excitation.</b> The joint sweeps through a range of "
             "speeds and accelerations in both directions, so every column of "
             "the regressor carries independent information. The condition "
             "number is small, every parameter comes out close, and adding "
             "noise degrades them gracefully. <b>This is what an excitation "
             "trajectory is for</b>, and designing one — usually a finite "
             "Fourier series, optimised to minimise exactly this condition "
             "number — is a standard step in commissioning a robot."),
            ("<b>Slow single sine.</b> There is barely any acceleration in this "
             "motion, so the ω̇ column is small and J is only weakly "
             "determined: its estimate wanders as soon as you add noise, while "
             "b and gravity stay respectable. This is the common real-world "
             "failure — the trajectory looked fine, but it never asked the "
             "joint the question you needed answered."),
            ("<b>One constant speed.</b> ω̇ = 0, so the inertia column is "
             "<b>identically zero</b>: the data contains literally no "
             "information about J. Worse, sign(ω) is also constant, so the "
             "Coulomb and gravity columns cannot be told apart either. The "
             "condition number explodes and the solver still returns four "
             "confident-looking numbers, most of them meaningless. "
             "<b>Least squares never refuses to answer — it is your job to "
             "check whether the question was askable.</b>"),
        ]
        self.reg_text.setText(msgs[kind])

        c = self.c_reg
        c.clear()
        a1, a2 = c.axes
        a1.plot(ts, w, color=theme.ACCENT, lw=1.4, label="speed ω")
        a1.plot(ts, wdot / 10.0, color=theme.PINK, lw=1.0,
                label="accel ω̇ ÷ 10")
        a1.axhline(0, color=theme.BORDER, lw=0.9)
        a1.set_xlabel("time (s)")
        a1.set_ylabel("rad/s,  rad/s²")
        a1.set_title("the trajectory you drove", fontsize=9)
        c.legend(a1, loc="upper right")

        names = ["J", "b", "f_c", "mgl"]
        x = np.arange(4)
        a2.bar(x - 0.19, truth, width=0.36, color=theme.TEXT_FAINT,
               label="true")
        a2.bar(x + 0.19, theta_hat, width=0.36, color=theme.ACCENT,
               label="identified")
        a2.set_xticks(x)
        a2.set_xticklabels(names)
        a2.axhline(0, color=theme.BORDER, lw=0.9)
        lo = min(0.0, float(np.min(theta_hat)) * 1.2)
        hi = max(max(truth), float(np.max(theta_hat))) * 1.25
        a2.set_ylim(lo, hi)
        a2.set_ylabel("parameter value")
        a2.set_title("what the regression recovered", fontsize=9)
        c.legend(a2, loc="upper left")
        c.refresh()


# ==========================================================================
# PAGE -- how software changes physics
# ==========================================================================

class SoftwarePhysicsPage(Page):
    TITLE = "How Software Changes Physics"
    SUBTITLE = ("You cannot change the inertia with a gain. So how does "
                "changing a gain change what the joint does? The answer is one "
                "substitution, and it is the foundation of every controller in "
                "this tutor.")
    SECTION = SECTION
    NOTES = "orientation"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>The question, stated properly: J and b are welded into the "
            "aluminium. A gain is a number in a loop. How can the number change "
            "what the aluminium does?</b><br><br>"
            "<b>It cannot, and it does not need to.</b> The motion of the joint "
            "is not decided by J and b alone — it is decided by <b>Newton's "
            "law</b>, which says the acceleration comes from the <i>sum of the "
            "torques acting</i>. Software cannot touch J. But software decides "
            "the motor torque, and the motor torque is one of the terms in that "
            "sum. Change a term in the equation and you change the equation, "
            "and the equation is what the motion obeys.", "key"))

        # ---- the substitution ------------------------------------------------
        s = Card("the whole answer, in three lines of algebra")
        s.add(body("<b>Line 1 — the hardware.</b> This is fixed. Nothing you "
                   "ever write changes it:"))
        s.add(math_label(r"J\,\ddot\theta + b\,\dot\theta \;=\; "
                         r"\tau_{\text{motor}} + \tau_{\text{external}}", 17))
        s.add(body(
            "<b>Line 2 — the controller.</b> Here is the only thing software "
            "actually does: it reads the sensors and decides, right now, what "
            "number to send to the current loop. Take a plain PD aiming at a "
            "target angle θ<sub>d</sub>:"))
        s.add(math_label(r"\tau_{\text{motor}} \;=\; -K_p\,(\theta - \theta_d) "
                         r"\;-\; K_d\,\dot\theta", 17))
        s.add(body(
            "<b>Line 3 — substitute the second into the first</b>, and move "
            "everything that depends on the motion to the left:"))
        s.add(math_label(r"J\,\ddot\theta + (b + K_d)\,\dot\theta + K_p\,\theta"
                         r" \;=\; K_p\,\theta_d + \tau_{\text{external}}", 17))
        s.add(callout(
            "<b>Stop and read that equation, because it is the answer to your "
            "question.</b><br><br>"
            "It is a <b>mass–spring–damper</b>. The mass is still J — you were "
            "right, software cannot change it. But the damping coefficient is "
            "now <b>b + K<sub>d</sub></b>, and there is a <b>stiffness "
            "K<sub>p</sub></b> in a joint that has no spring anywhere in "
            "it.<br><br>"
            "Nothing was faked. A steel spring produces a torque proportional "
            "to displacement and opposing it. Your controller reads "
            "displacement off the encoder and commands a torque proportional to "
            "it and opposing it. <b>The two torques are the same number, "
            "arriving at the same shaft, at the same moment.</b> The joint has "
            "no mechanism by which it could tell them apart — and neither does "
            "the person pushing on the arm.", "key"))
        s.add(body(
            "<b>So the honest one-liner: software does not change the "
            "hardware's parameters. It adds terms to the hardware's equation of "
            "motion.</b> And since behaviour is a property of the equation and "
            "not of the hardware alone, that is enough. Everything else in "
            "control — pole placement, lead compensators, impedance control, "
            "LQR — is a more careful way of choosing which terms to add.",
            dim=True))
        self.add(s)

        # ---- interactive: real vs virtual -----------------------------------
        self.add(hline())
        self.add(title("Interactive — a steel spring and a software spring, "
                       "side by side"))

        v = Card("two different machines, one identical trace")
        v.add(body(
            "<b>Left rig:</b> a bare joint with a real steel torsion spring "
            "k<sub>real</sub> and a real oil damper c<sub>real</sub> bolted to "
            "it. No electronics at all.<br>"
            "<b>Right rig:</b> the same joint with <i>nothing</i> bolted to it, "
            "driven by a motor running "
            "τ = −K<sub>p</sub>θ − K<sub>d</sub>θ̇.<br><br>"
            "Set K<sub>p</sub> = k<sub>real</sub> and K<sub>d</sub> = "
            "c<sub>real</sub> and the two traces lie exactly on top of each "
            "other. Not approximately — the differential equations are the same "
            "equation, so the motions are the same motion. Press <b>match the "
            "hardware</b> to do it in one click.", dim=True))
        self.s_kreal = slider(10, 600, 200)     # x0.1 N m/rad
        self.s_creal = slider(1, 300, 60)       # x0.1 N m s
        self.s_kp = slider(0, 600, 200)         # x0.1
        self.s_kd = slider(-100, 300, 20)       # x0.1
        (self.l_kreal, self.l_creal,
         self.l_kp, self.l_kd) = (QLabel() for _ in range(4))
        v.add_layout(slider_row("real spring k (×0.1)", self.s_kreal,
                                self.l_kreal))
        v.add_layout(slider_row("real damper c (×0.1)", self.s_creal,
                                self.l_creal))
        v.add_layout(slider_row("software K_p (×0.1)", self.s_kp, self.l_kp))
        v.add_layout(slider_row("software K_d (×0.1)", self.s_kd, self.l_kd))
        from PySide6.QtWidgets import QPushButton
        self.btn_match = QPushButton("match the hardware")
        self.btn_match.setObjectName("Primary")
        v.add_layout(_btn_row(self.btn_match))
        self.st_ke = Stat("effective stiffness", "--", theme.ACCENT)
        self.st_be = Stat("effective damping", "--", theme.GOOD)
        self.st_je = Stat("effective inertia", "--", theme.VIOLET)
        self.st_zeta = Stat("resulting ζ", "--", theme.WARN)
        self.st_match = Stat("traces agree?", "--", theme.CYAN)
        v.add_layout(stat_row(self.st_ke, self.st_be, self.st_je,
                              self.st_zeta, self.st_match))
        self.c_vs = MplCanvas(width=7.4, height=3.0, ncols=2)
        v.add(self.c_vs)
        self.vs_text = _readout()
        v.add(self.vs_text)
        self.add(v)
        self.btn_match.clicked.connect(self._match)
        for w_ in (self.s_kreal, self.s_creal, self.s_kp, self.s_kd):
            w_.valueChanged.connect(self._redraw_vs)
        self._redraw_vs()

        # ---- what you can and cannot synthesise ------------------------------
        cn = Card("what you can synthesise, what is hard, and what you cannot")
        cn.add(body(
            "<table cellpadding='7'>"
            "<tr><td><b>Property</b></td><td><b>How</b></td>"
            "<td><b>How well it works</b></td></tr>"

            "<tr><td><b>Stiffness</b><br>make one from nothing</td>"
            "<td>τ = −K<sub>p</sub>·(θ − θ<sub>d</sub>)</td>"
            "<td><b>Easy.</b> The joint has no spring; you can give it any "
            "stiffness you like, and change it mid-motion, which no steel "
            "spring can do. This is the single biggest reason to use a motor "
            "rather than a mechanism.</td></tr>"

            "<tr><td><b>Damping</b><br>add</td><td>τ = −K<sub>d</sub>·θ̇</td>"
            "<td><b>Easy</b>, and the most common thing a controller does.</td>"
            "</tr>"

            "<tr><td><b>Damping</b><br>remove</td>"
            "<td>τ = +K<sub>d</sub>·θ̇, i.e. a negative gain</td>"
            "<td><b>Possible but dangerous.</b> You are commanding the motor to "
            "help the motion along, which is exactly the negative-friction case "
            "that puts a pole in the right half plane. Used deliberately for "
            "friction compensation and transparency, and it is always a "
            "knife-edge.</td></tr>"

            "<tr><td><b>Gravity</b><br>cancel</td>"
            "<td>τ += mgl·sin θ &nbsp;(feedforward)</td>"
            "<td><b>Easy, and it feels like magic.</b> Add the torque gravity "
            "is taking away and the arm becomes weightless in your hand. Pure "
            "software, no hardware change, and it is why you need the mgl from "
            "the previous page.</td></tr>"

            "<tr><td><b>Inertia</b><br>increase</td>"
            "<td>τ = −K<sub>a</sub>·θ̈</td>"
            "<td><b>Works</b>, if you can get a clean acceleration signal — "
            "which you usually cannot, since differentiating an encoder twice "
            "is mostly noise.</td></tr>"

            "<tr><td><b>Inertia</b><br>reduce</td>"
            "<td>τ = +K<sub>a</sub>·θ̈</td>"
            "<td><b>The hard one, and the honest limit.</b> To make the arm "
            "feel lighter than it is, the motor must supply torque the instant "
            "you push — before it has measured anything. You are always one "
            "sample late, so the cancellation fails at exactly the frequencies "
            "where it matters. <b>This is why an SEA hides its rotor "
            "mechanically instead</b>, and it is the whole subject of the "
            "effective-inertia pages.</td></tr>"
            "</table>"))
        cn.add(callout(
            "<b>The pattern behind that table.</b> You can only synthesise a "
            "term in a variable you can <i>measure</i>, and you can only "
            "synthesise it as fast as your loop <i>runs</i>. Stiffness needs "
            "position — cheap, accurate, available. Damping needs velocity — "
            "one derivative, noisier, hence the filter on the D term. Inertia "
            "needs acceleration — two derivatives, mostly noise, and needed "
            "instantly. <b>The difficulty ranking is exactly the "
            "differentiation ranking</b>, and that is not a coincidence.",
            "key"))
        self.add(cn)

        # ---- where the illusion breaks --------------------------------------
        self.add(hline())
        self.add(title("Interactive — the three places the illusion breaks"))

        lim = Card("a software spring is a spring only inside the bandwidth")
        lim.add(body(
            "This is the part that separates people who have read about "
            "impedance control from people who have shipped it.<br><br>"
            "The plot on the left is <b>what the world feels</b> when it pushes "
            "the joint at a given frequency — the <b>rendered impedance</b>. "
            "Push slowly and you feel the virtual spring K<sub>p</sub>, exactly "
            "as designed. Push faster and the controller starts falling behind; "
            "past the loop bandwidth it has no useful influence at all and what "
            "your hand feels is the <b>raw inertia J</b>, rising as Jω². "
            "<b>Tap a software-compliant joint sharply and it is a lump of "
            "metal.</b> A steel spring has no such limit — it is a spring at "
            "every frequency, because it does not have to compute "
            "anything.", dim=True))
        self.s_kp2 = slider(10, 2000, 400)     # x0.1
        self.s_kd2 = slider(0, 400, 40)        # x0.1
        self.s_lat = slider(0, 300, 20)        # x0.1 ms
        self.s_sat = slider(5, 3000, 600)      # x0.1 N m
        (self.l_kp2, self.l_kd2,
         self.l_lat, self.l_sat) = (QLabel() for _ in range(4))
        lim.add_layout(slider_row("virtual stiffness K_p", self.s_kp2,
                                  self.l_kp2))
        lim.add_layout(slider_row("virtual damping K_d", self.s_kd2,
                                  self.l_kd2))
        lim.add_layout(slider_row("loop delay (ms)", self.s_lat, self.l_lat))
        lim.add_layout(slider_row("motor torque limit (N·m)", self.s_sat,
                                  self.l_sat))
        self.st_bw = Stat("rendered up to", "--", theme.ACCENT)
        self.st_feel = Stat("above that it feels like", "--", theme.TEXT_DIM)
        self.st_travel = Stat("travel before saturating", "--", theme.WARN)
        self.st_stab = Stat("with the delay", "--", theme.GOOD)
        lim.add_layout(stat_row(self.st_bw, self.st_feel, self.st_travel,
                                self.st_stab))
        self.c_lim = MplCanvas(width=7.4, height=3.0, ncols=2)
        lim.add(self.c_lim)
        self.lim_text = _readout()
        lim.add(self.lim_text)
        self.add(lim)
        for w_ in (self.s_kp2, self.s_kd2, self.s_lat, self.s_sat):
            w_.valueChanged.connect(self._redraw_lim)
        self._redraw_lim()

        # ---- energy ----------------------------------------------------------
        en = Card("the deepest difference: where the energy comes from")
        en.add(body(
            "A steel spring is <b>passive</b>. Every joule it gives back was a "
            "joule you put in. It is physically incapable of injecting energy "
            "into your arm, which is why no arrangement of springs and dampers "
            "has ever oscillated on its own.<br><br>"
            "A software spring is <b>active</b>. Its torque is supplied by the "
            "motor, out of the DC bus, and there is nothing in the arithmetic "
            "that forbids it from putting in more than it takes out. Get the "
            "phase slightly wrong — through delay, a filter, or a gain that is "
            "too high — and the \"damper\" starts pushing <i>with</i> the "
            "motion instead of against it."))
        en.add(callout(
            "<b>That is the real price of doing mechanics in software, and it "
            "is the one thing a mechanism never charges you.</b> A virtual "
            "spring can destabilise the machine it is attached to. A steel one "
            "cannot, ever.<br><br>"
            "The formal version of this is <b>passivity</b>, and it is why "
            "series-elastic actuators exist: putting a real spring in the "
            "transmission means the fast, high-force part of the interaction is "
            "handled by something that is passive by construction, leaving "
            "software to shape only the slow part it can actually keep up with. "
            "The SEA and passivity pages are that argument in full.", "warn"))
        self.add(en)

        # ---- poles and zeros, physically -------------------------------------
        pz = Card("and so: what a pole or a zero \"in the controller\" "
                  "physically is")
        pz.add(body(
            "You asked what it means to <i>add</i> a pole or a zero when all "
            "you have is arithmetic. Now it can be answered concretely:"))
        pz.add(body(
            "&nbsp;&nbsp;• <b>A controller pole is a number the software "
            "remembers between samples.</b> The integrator's accumulator is "
            "one. A filter's previous output is one. It is a state variable "
            "made of memory instead of metal — and it behaves like one, "
            "including contributing phase lag.<br>"
            "&nbsp;&nbsp;• <b>A controller zero is the controller reacting to a "
            "rate of change.</b> The D term is a zero. It contributes phase "
            "<i>lead</i>, which is why it damps.<br>"
            "&nbsp;&nbsp;• <b>The closed-loop poles are the roots of the "
            "combined equation</b>, the one you derived at the top of this "
            "page. The plant contributes its terms, the controller contributes "
            "its terms, and the roots depend on both. Neither side owns "
            "them."))
        pz.add(callout(
            "<b>The picture to keep.</b> The controller is a machine built out "
            "of arithmetic, wired to the real machine through a sensor and a "
            "motor. The pair is <b>one bigger machine</b>, with more state "
            "variables than the metal had on its own, and it is the bigger "
            "machine's equation that decides what happens.<br><br>"
            "\"Placing the poles\" is choosing the coefficients of that "
            "equation. \"Designing a controller\" is deciding what virtual "
            "mechanism to build out of software and bolt on. Root locus, lead "
            "compensators, LQR and pole placement are four ways of doing that "
            "deliberately.", "key"))
        self.add(pz)

        # ---- the three paradigms fall out ------------------------------------
        pa = Card("and now the three control paradigms are one equation")
        pa.add(body(
            "Look at what you derived and read off the special cases. They are "
            "not three different subjects; they are three choices of two "
            "numbers."))
        pa.add(math_label(r"J\,\ddot\theta + (b + K_d)\,\dot\theta "
                          r"+ K_p\,\theta = K_p\,\theta_d "
                          r"+ \tau_{\text{external}}", 16))
        pa.add(body(
            "<table cellpadding='7'>"
            "<tr><td><b>Paradigm</b></td><td><b>Choice</b></td>"
            "<td><b>What the world feels</b></td></tr>"
            "<tr><td><b>Torque control</b></td>"
            "<td>K<sub>p</sub> = K<sub>d</sub> = 0, command τ directly</td>"
            "<td>Zero virtual stiffness. Push it and it moves — the joint does "
            "not argue. Maximum transparency, no position "
            "authority.</td></tr>"
            "<tr><td><b>Impedance control</b></td>"
            "<td>K<sub>p</sub>, K<sub>d</sub> set to the stiffness and damping "
            "you <i>want</i> the world to feel</td>"
            "<td>Exactly the mechanical impedance you designed — inside the "
            "bandwidth. This whole page is the derivation of impedance "
            "control; the later pages only add detail.</td></tr>"
            "<tr><td><b>Position control</b></td>"
            "<td>K<sub>p</sub>, K<sub>d</sub> as large as stability "
            "allows</td>"
            "<td>A very stiff virtual spring: \"be at θ<sub>d</sub>, whatever "
            "force that takes\". The external torque term is overwhelmed, which "
            "is the same as saying the joint stops noticing you.</td></tr>"
            "</table>"))
        pa.add(callout(
            "<b>They were one controller all along, with a knob between "
            "them</b> — and that knob is ‖Z‖ = |K<sub>p</sub>| + "
            "|K<sub>d</sub>|. Turn it to zero and you have torque control; turn "
            "it up and you slide continuously to position control. If that "
            "sentence now feels obvious rather than clever, this page did its "
            "job, and the impedance pages later on will read as detail rather "
            "than as a new subject.", "good"))
        self.add(pa)

        self.add(callout(
            "<b>Carry forward.</b> Software cannot change J or b. It adds terms "
            "to the equation of motion, and the equation is what the motion "
            "obeys — so the joint genuinely behaves as though it had a spring "
            "and a damper it does not physically have. The limits are real and "
            "worth respecting: only inside the bandwidth, only within the "
            "torque limit, and only while the phase is honest. Everything from "
            "here is about choosing those added terms well.", "good"))

        self.finish()

    # ------------------------------------------------------------------
    def _match(self):
        self.s_kp.setValue(self.s_kreal.value())
        self.s_kd.setValue(self.s_creal.value())

    def _redraw_vs(self):
        kr = self.s_kreal.value() / 10.0
        cr = self.s_creal.value() / 10.0
        kp = self.s_kp.value() / 10.0
        kd = self.s_kd.value() / 10.0
        self.l_kreal.setText(f"{kr:.1f}")
        self.l_creal.setText(f"{cr:.1f}")
        self.l_kp.setText(f"{kp:.1f}")
        self.l_kd.setText(f"{kd:.1f}")

        # left rig: J thetadd + (b + c_real) thetad + k_real theta = k_real*cmd
        left = TF([kr], [J_TRUE, B_TRUE + cr, kr])
        # right rig: J thetadd + (b + Kd) thetad + Kp theta = Kp*cmd
        right = (TF([kp], [J_TRUE, B_TRUE + kd, kp]) if kp > 1e-9
                 else TF([0.0], [J_TRUE, B_TRUE + kd, 1.0]))

        ke, be = kp, B_TRUE + kd
        self.st_ke.set(f"{ke:.1f} N·m/rad")
        self.st_be.set(f"{be:.2f} N·m·s")
        self.st_je.set(f"{J_TRUE:.2f} kg·m²")
        if ke > 1e-9 and be > 0:
            z = be / (2 * math.sqrt(ke * J_TRUE))
            self.st_zeta.set(f"{z:.2f}")
            self.st_zeta.set_color(theme.GOOD if 0.5 < z < 1.5 else theme.WARN)
        else:
            self.st_zeta.set("—")

        same = abs(kp - kr) < 0.06 and abs((B_TRUE + kd) - (B_TRUE + cr)) < 0.06
        self.st_match.set("identical" if same else "different")
        self.st_match.set_color(theme.GOOD if same else theme.TEXT_DIM)

        dur = 2.5
        t1, y1 = step_response(left, dur, dur / 900.0)
        t2, y2 = step_response(right, dur, dur / 900.0)

        self.vs_text.setText(
            ("<b>The traces are on top of each other, and that is the whole "
             "point.</b> One rig has a steel spring in it and the other has a "
             "motor obeying two multiplications. No measurement you can make at "
             "the shaft — position, velocity, reaction torque, energy — "
             "distinguishes them. <b>The physics does not care where the torque "
             "came from.</b>"
             if same else
             "Press <b>match the hardware</b>, or set K<sub>p</sub> equal to "
             "the real spring and K<sub>d</sub> equal to the real damper. Note "
             "that the joint's own friction b = %.2f is present in <i>both</i> "
             "rigs and is already doing its share — the software only has to "
             "supply what the bolted-on hardware would have added." % B_TRUE))

        c = self.c_vs
        c.clear()
        a1, a2 = c.axes
        a1.plot(t1, y1, color=theme.WARN, lw=3.0, alpha=0.85,
                label="steel spring + oil damper")
        a1.plot(t2, y2, color=theme.ACCENT, lw=1.6, ls="--",
                label="motor + K_p, K_d")
        a1.axhline(1.0, color=theme.TEXT_FAINT, lw=1.0, ls=":")
        a1.set_xlabel("time (s)")
        a1.set_ylabel("angle (normalised)")
        a1.set_title("step command — both rigs", fontsize=9)
        c.legend(a1, loc="lower right")

        poles = left.poles() + right.poles()
        lm = max(2.0, max(abs(p) for p in poles) * 1.3)
        _splane(a2, right.poles(), lim=lm)
        a2.scatter([p.real for p in left.poles()], [p.imag for p in left.poles()],
                   marker="o", s=95, facecolors="none", linewidths=2.0,
                   edgecolors=theme.WARN, zorder=6, label="steel rig")
        a2.set_title("poles — the software rig lands on the steel one",
                     fontsize=9)
        c.legend(a2, loc="lower left")
        c.refresh()

    # ------------------------------------------------------------------
    def _redraw_lim(self):
        kp = self.s_kp2.value() / 10.0
        kd = self.s_kd2.value() / 10.0
        td = self.s_lat.value() / 10.0 * 1e-3
        sat = self.s_sat.value() / 10.0
        self.l_kp2.setText(f"{kp:.1f} N·m/rad")
        self.l_kd2.setText(f"{kd:.1f} N·m·s")
        self.l_lat.setText(f"{td*1000:.1f} ms")
        self.l_sat.setText(f"{sat:.1f} N·m")

        be = B_TRUE + kd
        wn = math.sqrt(kp / J_TRUE)
        self.st_bw.set(f"{wn/(2*math.pi):.1f} Hz")
        self.st_feel.set(f"J = {J_TRUE:.2f} kg·m²")
        self.st_travel.set(f"{math.degrees(sat/max(kp,1e-9)):.1f}°")
        self.st_travel.set_color(theme.WARN if sat / max(kp, 1e-9) < 0.05
                                 else theme.GOOD)

        # rendered impedance |Z(jw)| = |k + j w b_e - w^2 J|
        ws = [10 ** (-1 + 4.0 * i / 300) for i in range(301)]
        z = [abs(complex(kp - J_TRUE * w * w, be * w)) for w in ws]
        z_spring = [kp for _ in ws]
        z_inertia = [J_TRUE * w * w for w in ws]

        # closed loop with delay: does the "damper" still damp?
        cmd = 0.2                       # a small step, so saturation is a
        dur, dt = 2.0, 2e-4             # separate effect you turn on, not
        n = int(dur / dt)               # something that hides the delay
        nd = max(0, int(round(td / dt)))
        th = 0.0
        w_ = 0.0
        hist_th = [0.0] * (nd + 1)
        hist_w = [0.0] * (nd + 1)
        ts, ths = [], []
        unstable = False
        for k in range(n):
            th_m = hist_th[0]
            w_m = hist_w[0]
            u = -kp * (th_m - cmd) - kd * w_m
            u = max(-sat, min(sat, u))
            w_ += dt * (u - B_TRUE * w_) / J_TRUE
            th += dt * w_
            hist_th = hist_th[1:] + [th]
            hist_w = hist_w[1:] + [w_]
            ts.append(k * dt)
            ths.append(th / cmd)
            if abs(th / cmd) > 8.0:
                unstable = True
                break

        # A saturating loop that has gone unstable does not fly apart -- the
        # torque limit turns the divergence into a LIMIT CYCLE, so detect
        # "still swinging at the end of the window" rather than "large".
        # ...and detect OSCILLATION rather than mere movement, so that a
        # legitimately slow response is not mistaken for a buzz
        tail = ths[int(len(ths) * 0.7):] or [0.0]
        p2p = max(tail) - min(tail)
        mean = sum(tail) / len(tail)
        crossings = sum(1 for a_, b_ in zip(tail, tail[1:])
                        if (a_ - mean) * (b_ - mean) < 0)
        buzzing = (not unstable) and p2p > 0.03 and crossings >= 4
        if unstable:
            self.st_stab.set("diverging")
            self.st_stab.set_color(theme.BAD)
        elif buzzing:
            self.st_stab.set("buzzing")
            self.st_stab.set_color(theme.BAD)
        else:
            self.st_stab.set("stable")
            self.st_stab.set_color(theme.GOOD)
        unstable = unstable or buzzing

        self.lim_text.setText(
            ("<b>The delay turned the virtual damper into a virtual "
             "<i>anti</i>-damper.</b> K<sub>d</sub> commands a torque opposing "
             "the velocity it measured — but that velocity is %.1f ms old, and "
             "at this frequency the joint has already reversed by the time the "
             "torque arrives, so it pushes <b>with</b> the motion and adds "
             "energy on every cycle. A steel damper cannot do this: it responds "
             "to the velocity <i>now</i>, because it is not computing "
             "anything.<br><br>"
             "Notice it does not fly apart — it settles into a steady buzz. "
             "That is the torque limit turning a divergence into a <b>limit "
             "cycle</b>, and it is exactly what an unstable joint sounds like "
             "on a real robot: a hum at a fixed frequency and amplitude, not an "
             "explosion." % (td * 1000)
             if unstable else
             "Below the corner at <b>%.1f Hz</b> your hand feels the virtual "
             "spring you designed. Above it, the K<sub>p</sub> term has no "
             "authority and what you feel is the bare inertia rising as Jω². "
             "<b>Slow contact feels like a spring; impact feels like "
             "metal.</b> Now raise K<sub>p</sub> to push the corner up — and "
             "watch the travel before saturation shrink, and the delay margin "
             "with it. Those three limits trade against each other and you "
             "cannot have all of them." % (wn / (2 * math.pi))))

        c = self.c_lim
        c.clear()
        a1, a2 = c.axes
        a1.loglog(ws, z, color=theme.ACCENT, lw=2.3, label="what the hand feels")
        a1.loglog(ws, z_spring, color=theme.GOOD, lw=1.1, ls="--",
                  label="the spring you asked for")
        a1.loglog(ws, z_inertia, color=theme.BAD, lw=1.1, ls=":",
                  label="the raw inertia Jω²")
        a1.axvline(wn, color=theme.VIOLET, lw=1.2, ls=":")
        a1.set_xlabel("how fast you push  ω (rad/s)")
        a1.set_ylabel("rendered impedance |Z|")
        a1.set_title("a software spring, only up to the corner", fontsize=9)
        c.legend(a1, loc="upper left")

        a2.plot(ts, ths, color=theme.BAD if unstable else theme.ACCENT, lw=2.0)
        a2.axhline(1.0, color=theme.TEXT_FAINT, lw=1.0, ls="--",
                   label="commanded")
        a2.set_xlim(0, dur)
        a2.set_ylim(-1.2, 2.6 if not unstable else 8.5)
        a2.set_xlabel("time (s)")
        a2.set_ylabel("angle")
        a2.set_title("step, with the delay and the torque limit applied",
                     fontsize=9)
        c.legend(a2, loc="lower right")
        c.refresh()
