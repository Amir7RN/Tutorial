"""
BEAM BALANCE -- the general control machinery of this tutor, spent on one real
project: a mediolaterally powered hip exoskeleton assisting frontal-plane
balance during narrow-beam walking.

Nine pages, deliberately parallel to the general block:

    1  real-time      -- the loop rates this device actually runs, and why 5 Hz
    2  the plant      -- three links in the frontal plane; what stores, what does not
    3  measuring      -- where J, b, k and the segment numbers come from
    4  stability      -- an unstable pole, a delayed human, and an added torque
    5  frequency      -- the sine sweep, the corner, and what is rendered
    6  controller     -- the momentum law, term by term
    7  estimation     -- three IMUs, a reference generator, and drift
    8  impedance vs admittance -- what a 100:1 harmonic drive forces on you
    9  capstone       -- what the beam actually said, and what it did not

Every measured number is quoted from the two papers (and marked as quoted).
Every simulation is a teaching model of the published mechanism and is labelled
as one -- see the docstring of `ctrlcore.beamexo`.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel

from ctrlcore import beamexo as bx
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
from .motors import slider, slider_row

SECTION = "Beam Balance"

SOURCE = (
    "<b>Sources.</b> Naseri, Nalam, Tacca &amp; Huang, <i>A Robotic Approach to "
    "Assist Mediolateral Walking Stability in Humans: Evidence from Narrow Beam "
    "Walking</i>; Nalam et al., <i>Development of a Hip Abduction-Adduction "
    "Exoskeleton for Mediolateral Assistance</i>; and, for the hip hardware and "
    "its benchtop identification, <i>HipExoAnalysis</i>. Measured numbers on "
    "these pages are quoted from those papers. Simulations are teaching models "
    "of the published control law, not validated models of a human on a beam."
)


def _quoted(text):
    return callout(text, "good", label="QUOTED FROM THE PAPER")


@lru_cache(maxsize=96)
def _sim_cached(assist: bool, gain: float, kick: float, seed: int,
                extra_mass: float, dead_zone: float):
    """One beam trial. Cached, because each run is 10 s of 1 kHz integration."""
    saved = bx.CONTROL["dead_zone_rad"]
    bx.CONTROL["dead_zone_rad"] = dead_zone
    try:
        return bx.BeamSim(assist=assist, gain=gain, swing_momentum=kick,
                          extra_mass_kg=extra_mass, seed=seed).run()
    finally:
        bx.CONTROL["dead_zone_rad"] = saved


@lru_cache(maxsize=16)
def _survival_cached(kick: float, n_trials: int = 10):
    return bx.survival_curves(n_trials=n_trials, swing_momentum=kick)


# ==========================================================================
# 1 -- real-time
# ==========================================================================

class BeamRealTimePage(Page):
    TITLE = "Real Time on the Hip Exo"
    SUBTITLE = ("1 kHz admittance, a 4 kHz drive, a 5 Hz bandwidth target and a "
                "200 ms human. Page 1's timing argument, with this device's "
                "numbers in it.")
    SECTION = SECTION
    NOTES = "beam · hip exo"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(body(SOURCE, dim=True))

        c = Card("the clock stack, innermost first")
        c.add(body(
            "<b>Current loop — inside the Elmo drive.</b> Maxon EC-60 windings, "
            "L/R in the hundreds of microseconds. First order, one store, and "
            "nobody argues with it. Page 6's point about why a current loop can "
            "be closed at kilohertz is this layer.<br><br>"
            "<b>Velocity loop — Elmo Gold Solo Twitter, PID, 4 kHz.</b> 24 V, up "
            "to 40 A. Its job is to make the commanded joint velocity true.<br><br>"
            "<b>Admittance loop — TwinCAT, 1 kHz.</b> Torque in from the load "
            "cell, velocity out to the drive. One independent loop per hip.<br><br>"
            "<b>Momentum loop — the same 1 kHz task.</b> Three IMUs in, torso "
            "momentum error out, corrective torque out of that."))
        c.add(body(
            "That is the cascade of page 1 and the cascade Q&amp;A, built in "
            "hardware: each layer watches a state the layer inside it is blind "
            "to, and each runs near the timescale of the pole it regulates.",
            dim=True))
        self.add(c)

        self.add(_quoted(
            "Design target: <b>5 Hz</b> of assistance bandwidth at the hip, "
            "because <b>200 ms</b> is the reported duration of the active "
            "volitional balance response — assistance that arrives after that "
            "window is arriving after the human has already committed. Benchtop "
            "sine sweep of <b>1–100 Hz</b> at 50 % of motor current rating, "
            "loaded by an <b>85 kg</b> user in quiet standing, gave a closed-loop "
            "velocity bandwidth of <b>more than 5 Hz</b>, with the 1–5 Hz "
            "behaviour unchanged between unloaded and loaded."))

        b = Card("what \"5 Hz is enough\" actually claims")
        b.add(math_label(r"\text{bandwidth } 5\ \mathrm{Hz}\;\Rightarrow\;"
                         r"\tau \approx \frac{1}{2\pi\cdot 5} \approx 32\ \mathrm{ms}"
                         r"\;\Rightarrow\; 4\tau \approx 130\ \mathrm{ms}", 16))
        b.add(body(
            "Read it as page 6 taught: a 5 Hz corner is a 32 ms time constant, so "
            "a step of assistance is essentially delivered inside <b>130 ms</b>, "
            "which fits inside the 200 ms window with room to spare. That is the "
            "entire justification, and it is a first-order argument."))
        self.add(b)

        i = Card("the phase budget at the frequency you care about")
        i.add(body(
            "Three blocks stand between the momentum error and the torque the "
            "user feels: the closed-loop velocity response (first order at the "
            "identified bandwidth), transport delay (sample, compute, EtherCAT, "
            "drive), and the <b>2 Hz second-order Butterworth</b> the raw torque "
            "command is filtered by. Only the first is free.<br><br>"
            "Drag the delay up and watch which curve moves. The magnitude does "
            "not — delay is pure phase loss, exactly as page 1 and page 8 said.",
            dim=True))

        self.s_bw = slider(20, 200, 50)          # x0.1 Hz
        self.s_del = slider(0, 200, 20)          # x0.1 ms
        self.l_bw, self.l_del = QLabel(), QLabel()
        i.add_layout(slider_row("velocity bandwidth (Hz)", self.s_bw, self.l_bw))
        i.add_layout(slider_row("transport delay (ms)", self.s_del, self.l_del))
        self.chk_filt = QCheckBox("include the 2 Hz torque filter (as shipped)")
        self.chk_filt.setChecked(True)
        self.chk_filt.stateChanged.connect(self._redraw)
        i.add(self.chk_filt)

        self.st_lag = Stat("phase lag at 2 Hz", "--", theme.WARN)
        self.st_delay_share = Stat("of that, from delay", "--", theme.BAD)
        self.st_tau = Stat("assist time constant", "--", theme.ACCENT)
        i.add_layout(stat_row(self.st_lag, self.st_delay_share, self.st_tau))
        self.c1 = MplCanvas(width=7.4, height=4.0, nrows=2)
        i.add(self.c1)
        self.add(i)
        for s_ in (self.s_bw, self.s_del):
            s_.valueChanged.connect(self._redraw)
        self._redraw()

        self.add(callout(
            "<b>The honest version of the timing claim.</b> 1 kHz is not the "
            "bandwidth. 4 kHz is not the bandwidth. The bandwidth is 5 Hz, and it "
            "was <i>measured</i> with a sine sweep on the loaded device, because "
            "the harmonic drive, the load cell, the filters and the bus each take "
            "their cut. The fast clocks are what make a 5 Hz loop honest, not what "
            "make it fast.", "key"))

        self.finish()

    def _redraw(self):
        bw = self.s_bw.value() / 10.0
        dl = self.s_del.value() / 10.0
        filt = bx.CONTROL["filter_hz"] if self.chk_filt.isChecked() else None
        self.l_bw.setText(f"{bw:.1f} Hz")
        self.l_del.setText(f"{dl:.1f} ms")

        pb = bx.phase_budget(2.0, bw, dl, bx.CONTROL["filter_hz"])
        total = pb["total"] if filt else pb["velocity loop"] + pb["transport delay"]
        self.st_lag.set(f"{total:.0f}°")
        self.st_lag.set_color(theme.BAD if total < -120 else theme.WARN
                              if total < -70 else theme.GOOD)
        share = 0.0 if abs(total) < 1e-9 else 100 * pb["transport delay"] / total
        self.st_delay_share.set(f"{share:.0f}%")
        self.st_tau.set(f"{1000 / (2 * np.pi * bw):.0f} ms")

        f = np.logspace(-1, 2, 400)
        mag, ph = bx.velocity_loop_bode(f, bw, dl, filt)
        mag0, ph0 = bx.velocity_loop_bode(f, bw, 0.0, None)

        c = self.c1
        c.clear()
        a1, a2 = c.axes
        a1.semilogx(f, mag0, color=theme.TEXT_FAINT, lw=1.2, ls="--",
                    label="velocity loop alone")
        a1.semilogx(f, mag, color=theme.ACCENT, lw=2.0, label="as shipped")
        a1.axhline(-3, color=theme.WARN, lw=1.0, ls=":", label="−3 dB")
        a1.axvline(5.0, color=theme.CYAN, lw=1.0, ls=":")
        a1.set_ylabel("magnitude (dB)")
        a1.set_ylim(-40, 8)
        c.legend(a1, loc="lower left")
        a2.semilogx(f, ph0, color=theme.TEXT_FAINT, lw=1.2, ls="--")
        a2.semilogx(f, ph, color=theme.ACCENT, lw=2.0)
        a2.axhline(-180, color=theme.BAD, lw=1.0, ls=":", label="−180°")
        a2.axvline(2.0, color=theme.VIOLET, lw=1.0, ls=":",
                   label="2 Hz — where sway lives")
        a2.set_xlabel("frequency (Hz)")
        a2.set_ylabel("phase (deg)")
        a2.set_ylim(-360, 10)
        c.legend(a2, loc="lower left")
        c.refresh()


# ==========================================================================
# 2 -- the plant
# ==========================================================================

class BeamPlantPage(Page):
    TITLE = "The Plant: Three Links, Frontal Plane"
    SUBTITLE = ("Torso and two legs about the stance foot. Count the stores, "
                "name the state, and read whole-body angular momentum off the "
                "same three angles.")
    SECTION = SECTION

    def __init__(self, parent=None):
        super().__init__(parent)

        p = Card("the model the controller believes in")
        p.add(math_label(r"q(t)=\begin{bmatrix}\theta_T\\ \theta_L\\ "
                         r"\theta_R\end{bmatrix},\qquad "
                         r"H_{wb}=\sum_{i\in\{T,L,R\}}\left(I_i\omega_i + "
                         r"r_{S\to i}\times m_i v_i\right)", 16))
        p.add(body(
            "Three segments, each with an angle measured from vertical and a "
            "rate: <b>six state variables</b>, because each segment stores "
            "kinetic energy and none of the three angles can jump. Order six, "
            "and it is the hardware that says so, not the maths — exactly the "
            "count-the-energy-stores test from page 2."))
        p.add(body(
            "The output the controller chose to watch is <b>whole-body angular "
            "momentum about the stance-foot contact</b>. That choice matters as "
            "much as the model: page 2's \"the plant is the plant, but what you "
            "watch decides the order\" is the same sentence. Watch step width and "
            "you get a slow, stride-level plant. Watch H about the stance foot "
            "and you get a continuous signal that reacts inside a step."))
        self.add(p)

        w = Card("why momentum, and not step width or XCoM")
        w.add(body(
            "On a 4 cm beam the centre of pressure has essentially nowhere to go, "
            "and foot placement is constrained by the beam itself. Two of the "
            "three human balance strategies are therefore unavailable, which "
            "leaves rotating body segments to cancel angular momentum. The "
            "controller assists the strategy the task leaves intact.<br><br>"
            "It is also the difference between assisting balance and modulating a "
            "<i>proxy</i> for balance: a wider step is not automatically a safer "
            "step, but excess momentum about the pivot is unambiguous."))
        self.add(w)

        t = Card("the target: CoM and CoM-rate to zero, solved for the torso")
        t.add(math_label(r"x_{CoM}=\frac{1}{M}\left(m_T d_T\sin\theta_T + "
                         r"m_L d_L\sin\theta_L + m_R d_R\sin\theta_R\right)", 15))
        t.add(math_label(r"\theta_{T,d}=\sin^{-1}\!\left(\frac{-\left(m_L d_L"
                         r"\sin\theta_L+m_R d_R\sin\theta_R\right)}{m_T d_T}"
                         r"\right),\qquad "
                         r"\dot\theta_{T,d}=\frac{-\left(m_L d_L\dot\theta_L"
                         r"\cos\theta_L+m_R d_R\dot\theta_R\cos\theta_R\right)}"
                         r"{m_T d_T\cos\theta_{T,d}}", 14))
        t.add(body(
            "Set the lateral CoM and its rate to zero, solve for the torso, and "
            "you have a <b>reference generator</b>: the torso angle and rate that "
            "would exactly cancel what the legs are doing right now. Evaluate the "
            "momentum expression there and the desired whole-body momentum is "
            "zero by construction. Everything downstream is tracking that "
            "reference.", dim=True))
        self.add(t)

        i = Card("move the three links and watch the four quantities")
        i.add(body(
            "The legs are yours to set; the readouts show what the controller "
            "computes from them. Note the dead zone: below about <b>0.08 rad</b> "
            "of torso sway the distribution matrix is zero and the device is "
            "transparent, whatever the momentum error says.", dim=True))

        self.s_h = slider(150, 200, 175)
        self.s_m = slider(45, 110, 75)
        self.s_tt = slider(-30, 30, 9)       # deg
        self.s_tl = slider(-20, 20, 8)
        self.s_wt = slider(-100, 100, 25)    # x0.01 rad/s
        self.l_h, self.l_m = QLabel(), QLabel()
        self.l_tt, self.l_tl, self.l_wt = QLabel(), QLabel(), QLabel()
        i.add_layout(slider_row("height (cm)", self.s_h, self.l_h))
        i.add_layout(slider_row("body mass (kg)", self.s_m, self.l_m))
        i.add_layout(slider_row("torso sway θ_T (deg)", self.s_tt, self.l_tt))
        i.add_layout(slider_row("leg angle θ_L (deg)", self.s_tl, self.l_tl))
        i.add_layout(slider_row("torso rate (×0.01 rad/s)", self.s_wt, self.l_wt))

        self.st_com = Stat("x_CoM", "--", theme.CYAN)
        self.st_h = Stat("H_wb about foot", "--", theme.VIOLET)
        self.st_thd = Stat("θ_T desired", "--", theme.ACCENT)
        self.st_dz = Stat("dead zone", "--", theme.GOOD)
        i.add_layout(stat_row(self.st_com, self.st_h, self.st_thd, self.st_dz))
        self.c2 = MplCanvas(width=7.4, height=3.2, ncols=2)
        i.add(self.c2)
        self.add(i)
        for s_ in (self.s_h, self.s_m, self.s_tt, self.s_tl, self.s_wt):
            s_.valueChanged.connect(self._redraw)
        self._redraw()

        self.add(callout(
            "<b>Six states, one scalar output, one actuator pair.</b> That is the "
            "shape of the whole control problem, and it is why the design is a "
            "momentum <i>regulator</i> rather than a trajectory tracker: you "
            "cannot place six poles with two hips, but you can drive one "
            "well-chosen combination of them to zero.", "key"))

        self.finish()

    def _redraw(self):
        s = bx.Subject(self.s_h.value() / 100.0, float(self.s_m.value()))
        th_t = np.radians(self.s_tt.value())
        th_l = np.radians(self.s_tl.value())
        th_r = -th_l * 0.6
        w_t = self.s_wt.value() / 100.0
        w_l, w_r = 0.35, -0.2

        self.l_h.setText(f"{s.height_m:.2f} m")
        self.l_m.setText(f"{s.mass_kg:.0f} kg")
        self.l_tt.setText(f"{np.degrees(th_t):.0f}°")
        self.l_tl.setText(f"{np.degrees(th_l):.0f}°")
        self.l_wt.setText(f"{w_t:+.2f} rad/s")

        com = s.com_x(th_t, th_l, th_r)
        H = s.wbam(th_t, th_l, th_r, w_t, w_l, w_r)
        th_d, w_d = s.desired_torso_state(th_l, th_r, w_l, w_r)
        stance, swing = bx.distribution(th_t)

        self.st_com.set(f"{com * 100:+.1f} cm")
        self.st_com.set_color(theme.BAD if abs(com) > 0.02 else theme.GOOD)
        self.st_h.set(f"{H:+.1f}")
        self.st_thd.set(f"{np.degrees(th_d):+.1f}°")
        self.st_dz.set("transparent" if stance == 0 else f"{stance*100:.0f}/"
                                                        f"{swing*100:.0f}%")
        self.st_dz.set_color(theme.GOOD if stance == 0 else theme.WARN)

        c = self.c2
        c.clear()
        a1, a2 = c.axes
        names = ["torso", "stance leg", "swing leg"]
        contrib = [s.m_torso * s.d_torso * np.sin(th_t) / s.mass_kg,
                   s.m_leg * s.d_leg * np.sin(th_l) / s.mass_kg,
                   s.m_leg * s.d_leg * np.sin(th_r) / s.mass_kg]
        cols = [theme.ACCENT, theme.CYAN, theme.VIOLET]
        a1.bar(names, [v * 100 for v in contrib], color=cols)
        a1.axhline(0, color=theme.BORDER, lw=1.0)
        a1.set_ylabel("contribution to x_CoM (cm)")
        a1.set_title("who moved the centre of mass")

        sway = np.linspace(-0.35, 0.35, 400)
        share = np.array([bx.distribution(x)[0] + bx.distribution(x)[1]
                          for x in sway])
        a2.plot(np.degrees(sway), share * 100, color=theme.ACCENT, lw=2.0)
        a2.axvline(np.degrees(th_t), color=theme.CYAN, lw=1.4, ls="--",
                   label="you are here")
        a2.set_xlabel("torso sway (deg)")
        a2.set_ylabel("torque share applied (%)")
        a2.set_title("the dead zone, drawn")
        c.legend(a2, loc="lower right")
        c.refresh()


# ==========================================================================
# 3 -- measuring
# ==========================================================================

class BeamMeasuringPage(Page):
    TITLE = "Where This Device's Numbers Come From"
    SUBTITLE = ("Segment inertias from anthropometry, actuator inertia from the "
                "gear ratio, and rendered stiffness from a bench test with an "
                "R² next to it.")
    SECTION = SECTION

    def __init__(self, parent=None):
        super().__init__(parent)

        a = Card("the plant numbers: scaled, not looked up")
        a.add(body(
            "Page 3 said nobody looks these up. Here they are scaled: segment "
            "mass, length, centre-of-mass offset and moment of inertia come from "
            "standard anthropometric tables, scaled per participant by <b>height, "
            "weight and leg length measured from the greater trochanter to the "
            "ground</b>. That is what makes the control law personal — and the "
            "paper checked it worked, reporting no significant correlation "
            "between the performance improvement and either height "
            "(r = −0.243, p = 0.498) or weight (r = −0.139, p = 0.707)."))
        self.add(a)

        self.add(_quoted(
            "Actuator, per hip: <b>Maxon EC-60</b> brushless motor with a "
            "<b>100:1 harmonic drive</b> (CSD-20-100-2A-GR-SP674), a cantilevered "
            "<b>load cell in parallel</b> with the actuator for interaction-torque "
            "feedback, passive hinges so hip flexion/extension is not arrested, "
            "and a climbing harness on a thoracolumbar orthosis as the reaction "
            "shell. Torque target <b>0.8 N·m/kg → 72 N·m</b> for a 90 kg user; "
            "range of motion <b>±30°</b>; housings sized by FEA to a safety "
            "factor of <b>1.5</b>; total worn mass <b>≈6 kg</b>."))

        b = Card("the bench test that identified the rendered admittance")
        b.add(body(
            "<b>Static:</b> push the thigh strap while the device renders a fixed "
            "stiffness (20, 40, 60, 80 N·m/rad) and record deflection at steady "
            "state. The force-deflection relation was linear with <b>R² ≥ 99.4 %</b> "
            "and the fitted slope inside <b>2.5 %</b> of the commanded stiffness."
            "<br><br>"
            "<b>Dynamic:</b> compare the measured step response against the "
            "second-order system the admittance parameters specify, at "
            "<b>K = 12, 48 and 95.04 N·m/rad</b> crossed with "
            "<b>ζ = 0.6, 0.8, 1.0, 1.2</b>. R² ran from 98.5 % to 99.96 %."))
        b.add(math_label(r"\omega_n=\sqrt{K/M},\qquad \zeta=\frac{B}{2\sqrt{KM}}", 16))
        b.add(body(
            "Those are page 11's two numbers, and here they are being used as a "
            "<i>specification</i>: you name ω_n and ζ, the identification tells "
            "you whether the hardware actually rendered them. Underdamped through "
            "overdamped was tested on purpose, because a device that can only do "
            "one damping ratio cannot claim to render an admittance.", dim=True))
        self.add(b)

        i = Card("scale a participant, then ask what it costs to move them")
        i.add(body(
            "Left: the three segments the model carries. Right: the rendered "
            "second-order system for a commanded stiffness, with the tested points "
            "marked. Push the stiffness past 95 N·m/rad and you are outside what "
            "the bench test validated.", dim=True))
        self.s_h = slider(150, 200, 175)
        self.s_m = slider(45, 110, 75)
        self.s_k = slider(5, 140, 48)
        self.l_h, self.l_m, self.l_k = QLabel(), QLabel(), QLabel()
        i.add_layout(slider_row("height (cm)", self.s_h, self.l_h))
        i.add_layout(slider_row("body mass (kg)", self.s_m, self.l_m))
        i.add_layout(slider_row("rendered K (N·m/rad)", self.s_k, self.l_k))

        self.st_I = Stat("I_wb about foot", "--", theme.VIOLET)
        self.st_grav = Stat("tipping torque at 5°", "--", theme.BAD)
        self.st_need = Stat("as % of 72 N·m", "--", theme.WARN)
        self.st_val = Stat("inside bench range", "--", theme.GOOD)
        i.add_layout(stat_row(self.st_I, self.st_grav, self.st_need, self.st_val))
        self.c3 = MplCanvas(width=7.4, height=3.2, ncols=2)
        i.add(self.c3)
        self.add(i)
        for s_ in (self.s_h, self.s_m, self.s_k):
            s_.valueChanged.connect(self._redraw)
        self._redraw()

        self.add(callout(
            "<b>The measurement that decides the project.</b> The gravitational "
            "tipping torque at a few degrees of sway is the load the assistance "
            "has to argue with. Compare it with 72 N·m and with the 15–20 % share "
            "the controller actually applies, and the design philosophy stops "
            "being a slogan: the device was never going to hold the user up, only "
            "nudge them.", "key"))

        self.finish()

    def _redraw(self):
        s = bx.Subject(self.s_h.value() / 100.0, float(self.s_m.value()))
        K = float(self.s_k.value())
        self.l_h.setText(f"{s.height_m:.2f} m")
        self.l_m.setText(f"{s.mass_kg:.0f} kg")
        self.l_k.setText(f"{K:.0f}")

        I = s.whole_body_inertia()
        l_com = 0.55 * s.height_m
        grav = s.mass_kg * 9.81 * l_com * np.sin(np.radians(5.0))
        self.st_I.set(f"{I:.1f} kg·m²")
        self.st_grav.set(f"{grav:.0f} N·m")
        self.st_need.set(f"{100 * grav / bx.HARDWARE['peak_torque_nm']:.0f}%")
        ok = K <= bx.HARDWARE["max_rendered_stiffness"]
        self.st_val.set("yes" if ok else "extrapolating")
        self.st_val.set_color(theme.GOOD if ok else theme.BAD)

        c = self.c3
        c.clear()
        a1, a2 = c.axes
        labels = ["torso", "one leg"]
        mass = [s.m_torso, s.m_leg]
        inert = [s.torso_inertia_about_foot(), s.I_leg + s.m_leg * s.d_leg ** 2]
        x = np.arange(2)
        a1.bar(x - 0.18, mass, width=0.34, color=theme.ACCENT, label="mass (kg)")
        a1.bar(x + 0.18, inert, width=0.34, color=theme.VIOLET,
               label="I about foot (kg·m²)")
        a1.set_xticks(x)
        a1.set_xticklabels(labels)
        a1.set_title("segments, scaled to this participant")
        c.legend(a1, loc="upper right")

        M = bx.CONTROL["admittance_M"]
        ks = np.linspace(5, 140, 300)
        wn = np.sqrt(ks / M) / (2 * np.pi)
        a2.plot(ks, wn, color=theme.ACCENT, lw=2.0)
        for kk in bx.HARDWARE["stiffnesses_tested"]:
            a2.axvline(kk, color=theme.CYAN, lw=1.0, ls=":")
        a2.axvline(bx.HARDWARE["max_rendered_stiffness"], color=theme.BAD,
                   lw=1.2, ls="--", label="95 N·m/rad — validated ceiling")
        a2.plot([K], [np.sqrt(K / M) / (2 * np.pi)], "o", color=theme.WARN, ms=8)
        a2.set_xlabel("commanded stiffness (N·m/rad)")
        a2.set_ylabel("rendered ω_n (Hz)")
        a2.set_title("stiffness → natural frequency")
        c.legend(a2, loc="lower right")
        c.refresh()


# ==========================================================================
# 4 -- stability
# ==========================================================================

class BeamStabilityPage(Page):
    TITLE = "Stability: An Unstable Pole and a Late Human"
    SUBTITLE = ("The frontal-plane body on a beam has a pole in the right half "
                "plane. The human closes the loop 120 ms late. The exo is a "
                "third torque source in the same loop.")
    SECTION = SECTION

    def __init__(self, parent=None):
        super().__init__(parent)

        p = Card("the plant, linearised, and why it is page 12's bad case")
        p.add(math_label(r"I_{wb}\ddot\theta_T = m g \ell\,\theta_T + "
                         r"\tau_{human} + \tau_{exo}\;\Rightarrow\;"
                         r"s = \pm\sqrt{\frac{mg\ell}{I_{wb}}}", 16))
        p.add(body(
            "Gravity's sign is positive on the right-hand side — lean further and "
            "the torque that caused the lean grows. One pole in the right half "
            "plane, and its magnitude is a rate you can feel: the time for a "
            "disturbance to double. That is the number every balance controller "
            "is racing.<br><br>"
            "On a beam, this is the whole problem. The base of support cannot be "
            "widened, so no amount of centre-of-pressure work moves that pole; "
            "only torque about the hips does."))
        self.add(p)

        h = Card("the human is inside the loop, and is the slow part")
        h.add(body(
            "The wearer's own response is a delayed, saturating controller: "
            "roughly proportional-plus-derivative on trunk sway, arriving "
            "<b>100–150 ms</b> late, with a ceiling set by hip strength. Page 8's "
            "lesson applies without modification — that delay is unbounded phase "
            "lag, so the loop has a critical gain, and pushing human gain up is "
            "not available as a fix.<br><br>"
            "The exoskeleton is not replacing that loop. It adds a torque in "
            "parallel with it, with <b>15–20 %</b> of the computed correction and "
            "a dead zone, which is the design decision that keeps the human's own "
            "response authoritative."))
        self.add(h)

        i = Card("drag the assist gain and watch the closed-loop poles")
        i.add(body(
            "Poles of the linearised balance loop: the unstable plant pole, the "
            "human's delayed PD (Padé-approximated so it can be drawn), and the "
            "exo's contribution through its 5 Hz actuator lag. Watch two things — "
            "the pair crossing into the left half plane, and what raising human "
            "delay does to the crossing you just bought.", dim=True))
        self.s_g = slider(0, 100, 20)        # % of correction
        self.s_d = slider(40, 220, 120)      # ms human delay
        self.s_bw = slider(10, 120, 50)      # x0.1 Hz actuator
        self.l_g, self.l_d, self.l_bw = QLabel(), QLabel(), QLabel()
        i.add_layout(slider_row("exo share applied (%)", self.s_g, self.l_g))
        i.add_layout(slider_row("human delay (ms)", self.s_d, self.l_d))
        i.add_layout(slider_row("actuator bandwidth (Hz)", self.s_bw, self.l_bw))

        self.st_pole = Stat("slowest pole", "--", theme.ACCENT)
        self.st_verdict = Stat("verdict", "--", theme.GOOD)
        self.st_double = Stat("doubling time", "--", theme.BAD)
        i.add_layout(stat_row(self.st_pole, self.st_verdict, self.st_double))
        self.c4 = MplCanvas(width=7.4, height=3.4, ncols=2)
        i.add(self.c4)
        self.add(i)
        for s_ in (self.s_g, self.s_d, self.s_bw):
            s_.valueChanged.connect(self._redraw)
        self._redraw()

        self.add(callout(
            "<b>Why the dead zone is a stability device, not a comfort feature.</b> "
            "Inside ±0.08 rad the exo contributes nothing, so the loop it could "
            "destabilise is not closed at all. Outside it, the torque is "
            "unidirectional — always adducting, always pulling the trunk back — "
            "which removes the sign switching that a small-signal bidirectional "
            "law would perform around every zero crossing of sway.", "key"))

        self.finish()

    def _redraw(self):
        share = self.s_g.value() / 100.0
        delay = self.s_d.value() / 1000.0
        bw = self.s_bw.value() / 10.0
        self.l_g.setText(f"{share*100:.0f}%")
        self.l_d.setText(f"{delay*1000:.0f} ms")
        self.l_bw.setText(f"{bw:.1f} Hz")

        s = bx.Subject()
        I = s.whole_body_inertia() + bx.HARDWARE["mass_kg"] * (0.55 * s.height_m) ** 2
        m, l = s.mass_kg + bx.HARDWARE["mass_kg"], 0.55 * s.height_m
        a = m * 9.81 * l / I                 # unstable: s^2 = a
        kp, kd = 210.0 / I, 34.0 / I
        ke = share * 9.0 * 40.0 / I          # exo torque per rad, through its lag
        pa = 2 * np.pi * bw

        # I s^2 - mgl = -(kp + kd s) e^{-Ts} - exo/(s/pa + 1)
        # first-order Pade on the delay, one pole for the actuator
        num_d = np.array([-delay / 2, 1.0])
        den_d = np.array([delay / 2, 1.0])
        plant = np.array([1.0, 0.0, -a])
        human = np.polyadd(np.polymul(plant, den_d),
                           np.polymul(np.array([kd, kp]), num_d))
        act = np.array([1.0 / pa, 1.0])
        poly = np.polyadd(np.polymul(human, act),
                          np.polymul(np.array([ke]), np.polymul(den_d, [1.0])))
        roots = np.roots(poly)

        slow = roots[np.argmax(roots.real)]
        self.st_pole.set(f"{slow.real:+.1f}")
        stable = slow.real < 0
        self.st_verdict.set("stable" if stable else "unstable")
        self.st_verdict.set_color(theme.GOOD if stable else theme.BAD)
        self.st_double.set("—" if stable else
                           f"{np.log(2)/slow.real*1000:.0f} ms")

        c = self.c4
        c.clear()
        a1, a2 = c.axes
        a1.axvline(0, color=theme.BAD, lw=1.2)
        a1.axhline(0, color=theme.BORDER, lw=1.0)
        a1.plot(roots.real, roots.imag, "x", color=theme.ACCENT, ms=10, mew=2)
        a1.plot([np.sqrt(a), -np.sqrt(a)], [0, 0], "o", mfc="none",
                color=theme.TEXT_FAINT, ms=9, label="open-loop plant")
        a1.set_xlabel("Re (1/s)")
        a1.set_ylabel("Im (rad/s)")
        a1.set_title("closed-loop poles")
        c.legend(a1, loc="upper left")

        shares = np.linspace(0, 1, 60)
        worst = []
        for sh in shares:
            kee = sh * 9.0 * 40.0 / I
            pp = np.polyadd(np.polymul(human, act),
                            np.polymul(np.array([kee]), np.polymul(den_d, [1.0])))
            worst.append(np.max(np.roots(pp).real))
        a2.plot(shares * 100, worst, color=theme.CYAN, lw=2.0)
        a2.axhline(0, color=theme.BAD, lw=1.2, ls="--")
        a2.plot([share * 100], [slow.real], "o", color=theme.WARN, ms=8)
        a2.axvspan(15, 20, color=theme.GOOD, alpha=0.15)
        a2.text(17.5, max(worst), "as shipped", color=theme.GOOD, fontsize=8,
                ha="center", va="top")
        a2.set_xlabel("exo share applied (%)")
        a2.set_ylabel("slowest pole (1/s)")
        a2.set_title("what the assist share buys")
        c.refresh()


# ==========================================================================
# 5 -- frequency
# ==========================================================================

class BeamFrequencyPage(Page):
    TITLE = "The Sine Sweep, and What Actually Gets Rendered"
    SUBTITLE = ("1–100 Hz on the bench; 5 Hz at the hip; and above that, what "
                "the wearer feels is 6 kg of hardware.")
    SECTION = SECTION

    def __init__(self, parent=None):
        super().__init__(parent)

        s = Card("the experiment, and why it had to be run loaded")
        s.add(body(
            "A sinusoidal sweep from <b>1 to 100 Hz</b> at 50 % of motor current "
            "rating, with the device worn by an <b>85 kg</b> user in quiet "
            "standing, and the output velocity's frequency response measured. The "
            "answer: faithful tracking with no meaningful phase lag to about "
            "<b>5 Hz</b>, and the 1–5 Hz behaviour indistinguishable between "
            "loaded and unloaded.<br><br>"
            "That last clause is the load-bearing one. Page 8's formula gives you "
            "a corner from J and b; the bench gives you the corner the assembled "
            "machine has, including harmonic-drive friction, the load cell's own "
            "dynamics, the bus and the filters. This is exactly the "
            "\"compute it first, then go and measure it\" answer from the "
            "bandwidth discussion."))
        self.add(s)

        r = Card("rendered impedance: the honest version of \"it feels compliant\"")
        r.add(body(
            "Page 4's three failure modes, on this device:<br><br>"
            "<b>Bandwidth.</b> Below the corner, what the wearer feels is the "
            "admittance the software specified. Above it, the software's "
            "contribution drops out and what is left is real reflected inertia — "
            "100² times the rotor, plus the linkage, plus 6 kg of worn hardware. "
            "Tap the device quickly and it is metal.<br><br>"
            "<b>Torque limit.</b> 72 N·m at 90 kg, and only 15–20 % of the "
            "computed correction is ever applied.<br><br>"
            "<b>Delay.</b> The 2 Hz Butterworth that smooths the torque command "
            "costs phase exactly where trunk sway lives. It was bought "
            "deliberately: unfiltered momentum-derived torque on a walking human "
            "is noise."))
        self.add(r)

        i = Card("push the device at a frequency and see which block answers")
        i.add(body(
            "Left: the assistance path's magnitude, and the frequency above which "
            "the wearer is feeling hardware rather than control. Right: how the "
            "phase at your chosen frequency is split between the velocity loop, "
            "the delay and the torque filter.", dim=True))
        self.s_f = slider(2, 300, 20)        # x0.1 Hz
        self.s_bw = slider(10, 150, 50)
        self.s_del = slider(0, 120, 20)      # x0.1 ms
        self.l_f, self.l_bw, self.l_del = QLabel(), QLabel(), QLabel()
        i.add_layout(slider_row("push frequency (Hz)", self.s_f, self.l_f))
        i.add_layout(slider_row("velocity bandwidth (Hz)", self.s_bw, self.l_bw))
        i.add_layout(slider_row("transport delay (ms)", self.s_del, self.l_del))

        self.st_gain = Stat("assist magnitude", "--", theme.ACCENT)
        self.st_ph = Stat("total lag", "--", theme.WARN)
        self.st_reg = Stat("what you feel", "--", theme.CYAN)
        i.add_layout(stat_row(self.st_gain, self.st_ph, self.st_reg))
        self.c5 = MplCanvas(width=7.4, height=3.4, ncols=2)
        i.add(self.c5)
        self.add(i)
        for s_ in (self.s_f, self.s_bw, self.s_del):
            s_.valueChanged.connect(self._redraw)
        self._redraw()

        self.add(callout(
            "<b>Beam walking lives at 1–3 Hz.</b> Step frequency on a 4 cm beam "
            "is around one step per second, and the corrective trunk motion sits "
            "just above it. A 5 Hz actuator with a 2 Hz command filter is "
            "therefore a tight but deliberate fit — not comfortable headroom. "
            "That is why the device's reported bandwidth is the specification it "
            "is judged against.", "key"))

        self.finish()

    def _redraw(self):
        f = self.s_f.value() / 10.0
        bw = self.s_bw.value() / 10.0
        dl = self.s_del.value() / 10.0
        self.l_f.setText(f"{f:.1f} Hz")
        self.l_bw.setText(f"{bw:.1f} Hz")
        self.l_del.setText(f"{dl:.1f} ms")

        mag, ph = bx.velocity_loop_bode([f], bw, dl, bx.CONTROL["filter_hz"])
        pb = bx.phase_budget(f, bw, dl)
        self.st_gain.set(f"{mag[0]:.1f} dB")
        self.st_ph.set(f"{ph[0]:.0f}°")
        self.st_ph.set_color(theme.BAD if ph[0] < -150 else theme.WARN)
        control_region = mag[0] > -6
        self.st_reg.set("the rendered law" if control_region else "the hardware")
        self.st_reg.set_color(theme.GOOD if control_region else theme.BAD)

        fs = np.logspace(-1, 2, 400)
        m_all, _ = bx.velocity_loop_bode(fs, bw, dl, bx.CONTROL["filter_hz"])
        m_loop, _ = bx.velocity_loop_bode(fs, bw, dl, None)

        c = self.c5
        c.clear()
        a1, a2 = c.axes
        a1.semilogx(fs, m_loop, color=theme.TEXT_FAINT, lw=1.3, ls="--",
                    label="velocity loop + delay")
        a1.semilogx(fs, m_all, color=theme.ACCENT, lw=2.0,
                    label="+ 2 Hz torque filter")
        a1.axhline(-6, color=theme.BAD, lw=1.0, ls=":",
                   label="−6 dB: hardware takes over")
        a1.axvline(f, color=theme.WARN, lw=1.2)
        a1.axvspan(0.8, 3.0, color=theme.CYAN, alpha=0.12)
        a1.set_xlabel("frequency (Hz)")
        a1.set_ylabel("magnitude (dB)")
        a1.set_ylim(-60, 8)
        a1.set_title("cyan band = where beam walking lives")
        c.legend(a1, loc="lower left")

        keys = ["velocity loop", "transport delay", "torque filter"]
        vals = [pb[k] for k in keys]
        a2.barh(keys, vals, color=[theme.ACCENT, theme.BAD, theme.VIOLET])
        a2.set_xlabel(f"phase contribution at {f:.1f} Hz (deg)")
        a2.set_title(f"total {pb['total']:.0f}°")
        c.refresh()


# ==========================================================================
# 6 -- the controller
# ==========================================================================

class BeamControllerPage(Page):
    TITLE = "The Momentum Controller, Term by Term"
    SUBTITLE = ("Momentum error, dead zone, asymmetric distribution, absolute "
                "derivative, Butterworth, admittance. Six blocks, and every one "
                "of them is a decision.")
    SECTION = SECTION

    def __init__(self, parent=None):
        super().__init__(parent)

        e = Card("the law, as published")
        e.add(math_label(r"x(t)=\begin{bmatrix}\Delta H_T(t)\\ "
                         r"\Delta \dot H_T(t)\end{bmatrix},\qquad "
                         r"\Delta H_T = H_T - H_{T,d}", 16))
        e.add(math_label(r"\tau_{raw}(t)=\text{gain}\cdot D(\theta_T)\,"
                         r"\begin{bmatrix}\Delta H_T\\ "
                         r"\left|\Delta\dot H_T\right|\end{bmatrix},\qquad "
                         r"D(\theta_T)=\begin{cases}"
                         r"\text{0.20 stance, 0.05 swing} & |\theta_T|>0.08\\"
                         r"0 & |\theta_T|\le 0.08\end{cases}", 15))
        e.add(math_label(r"\tau_{filt}=F(s)\,\tau_{raw},\quad "
                         r"F(s)=\frac{\omega_c^2}{s^2+2\zeta\omega_c s+\omega_c^2},"
                         r"\ \ \omega_c=2\pi\cdot 2,\ \zeta=0.707", 15))
        e.add(math_label(r"\omega_{cmd}(s)=\frac{1}{M s^2 + B s + K}\,\tau_{filt},"
                         r"\qquad \{M,B,K\}=\{10^{-3},10^{-2},5\times10^{-2}\}", 15))
        self.add(e)

        d = Card("five decisions hiding in those four lines")
        d.add(body(
            "<b>1 · The state is a momentum error, not an angle error.</b> Page "
            "2's vocabulary: the controller regulates a quantity that already "
            "contains velocity, so it is not a virtual spring pulling towards a "
            "pose. There is no \"correct\" torso angle to hold on a beam, and this "
            "is how that is expressed in code.<br><br>"
            "<b>2 · The dead zone.</b> ±0.08 rad ≈ 4.6° of transparency. Natural "
            "sway is not corrected; only sway past the stance leg is.<br><br>"
            "<b>3 · Asymmetric distribution.</b> 20 % of the correction to the "
            "stance hip, 5 % to the swing hip, with the stance side chosen by the "
            "sign of torso sway. The stance hip is the one with a pivot to push "
            "against.<br><br>"
            "<b>4 · The absolute value on the momentum rate.</b> The output is "
            "unidirectional — always adducting, always drawing torso and leg back "
            "toward the midline. That deliberately removes the polarity switching "
            "a bidirectional law would do around small sway, which is the "
            "oscillation mechanism from page 12 seen in advance.<br><br>"
            "<b>5 · gain ∈ [0.75, 1].</b> Two personalised levels, 15 % and 20 % "
            "of the computed correction, chosen per participant from verbal "
            "feedback and then fixed for every session."))
        self.add(d)

        self.add(_quoted(
            "On why the assistance is small: <i>partial torque assistance (e.g. "
            "15–20 %) is often sufficient to improve stability and reduce effort "
            "without disrupting voluntary control.</i> Participants rated "
            "helpfulness <b>1.57 ± 0.58</b> on a −3…+3 scale and could reliably "
            "feel when assistance was applied (<b>4.2 ± 0.8</b> of 5) — so the "
            "intervention was both detectable and welcome, which is the pair of "
            "claims a small-torque design has to support."))

        i = Card("a trial, with the law switched on and off")
        i.add(body(
            "A frontal-plane teaching model: swing-leg momentum kicks the trunk "
            "once per step, the wearer responds 120 ms late with a saturating PD, "
            "and the exo adds its share through a 2 Hz filter and a 5 Hz actuator. "
            "Step off happens when the modelled CoM leaves the beam plus a foot "
            "margin. <b>Distances here are model output, not experimental "
            "results.</b>", dim=True))
        self.s_gain = slider(0, 100, 100)     # x0.01 -> gain
        self.s_kick = slider(10, 60, 32)      # x0.1 momentum per step
        self.s_seed = slider(0, 17, 3)
        self.l_gain, self.l_kick, self.l_seed = QLabel(), QLabel(), QLabel()
        i.add_layout(slider_row("personalisation gain", self.s_gain, self.l_gain))
        i.add_layout(slider_row("swing momentum / step", self.s_kick, self.l_kick))
        i.add_layout(slider_row("trial (seed)", self.s_seed, self.l_seed))
        self.chk_dz = QCheckBox("keep the ±0.08 rad dead zone")
        self.chk_dz.setChecked(True)
        self.chk_dz.stateChanged.connect(self._redraw)
        i.add(self.chk_dz)

        self.st_peak = Stat("peak exo torque", "--", theme.ACCENT)
        self.st_duty = Stat("time assisting", "--", theme.CYAN)
        self.st_dist = Stat("model distance", "--", theme.WARN)
        self.st_gainx = Stat("vs no assist", "--", theme.GOOD)
        i.add_layout(stat_row(self.st_peak, self.st_duty, self.st_dist,
                              self.st_gainx))
        self.c6 = MplCanvas(width=7.4, height=4.2, nrows=3)
        i.add(self.c6)
        self.add(i)
        for s_ in (self.s_gain, self.s_kick, self.s_seed):
            s_.valueChanged.connect(self._redraw)
        self._redraw()

        self.finish()

    def _redraw(self):
        gain = max(0.01, self.s_gain.value() / 100.0)
        kick = self.s_kick.value() / 10.0
        seed = self.s_seed.value()
        self.l_gain.setText(f"{gain:.2f}")
        self.l_kick.setText(f"{kick:.1f} kg·m²/s")
        self.l_seed.setText(f"#{seed}")

        dz_saved = 0.08
        dz = dz_saved if self.chk_dz.isChecked() else 0.0
        mass = bx.HARDWARE["mass_kg"]
        on = _sim_cached(True, gain, kick, seed, mass, dz)
        off = _sim_cached(False, 1.0, kick, seed, mass, dz)

        self.st_peak.set(f"{on['peak_torque']:.1f} N·m")
        self.st_duty.set(f"{on['duty']*100:.0f}%")
        self.st_dist.set(f"{on['distance_m']:.2f} m")
        delta = on["distance_m"] - off["distance_m"]
        self.st_gainx.set(f"{delta:+.2f} m")
        self.st_gainx.set_color(theme.GOOD if delta >= 0 else theme.BAD)

        c = self.c6
        c.clear()
        a1, a2, a3 = c.axes
        a1.plot(off["t"], np.degrees(off["theta"]), color=theme.TEXT_FAINT,
                lw=1.3, label="no assist")
        a1.plot(on["t"], np.degrees(on["theta"]), color=theme.ACCENT, lw=1.8,
                label="active assist")
        a1.axhline(np.degrees(dz_saved), color=theme.VIOLET, lw=0.9, ls=":")
        a1.axhline(-np.degrees(dz_saved), color=theme.VIOLET, lw=0.9, ls=":",
                   label="dead zone")
        a1.set_ylabel("torso sway (deg)")
        c.legend(a1, loc="upper left")

        a2.plot(off["t"], off["com"] * 100, color=theme.TEXT_FAINT, lw=1.3)
        a2.plot(on["t"], on["com"] * 100, color=theme.CYAN, lw=1.8)
        hb = bx.BEAM["test_width_m"] / 2 * 100
        a2.axhline(hb, color=theme.BAD, lw=1.0, ls="--")
        a2.axhline(-hb, color=theme.BAD, lw=1.0, ls="--", label="beam edge")
        a2.set_ylabel("lateral CoM (cm)")
        c.legend(a2, loc="upper left")

        a3.plot(on["t"], on["tau_exo"], color=theme.WARN, lw=1.4,
                label="exo torque")
        a3.plot(on["t"], on["tau_human"], color=theme.GOOD, lw=1.0, alpha=0.8,
                label="modelled human torque")
        a3.set_xlabel("time (s)")
        a3.set_ylabel("N·m")
        c.legend(a3, loc="upper left")
        c.refresh()


# ==========================================================================
# 7 -- estimation
# ==========================================================================

class BeamEstimationPage(Page):
    TITLE = "Three IMUs, a Reference Generator, and Drift"
    SUBTITLE = ("The controller never measures momentum. It estimates it from "
                "three angles and three rates — which is page 20's problem with "
                "page 7's liability attached."
                )
    SECTION = SECTION

    def __init__(self, parent=None):
        super().__init__(parent)

        o = Card("what is measured, and what is inferred")
        o.add(body(
            "<b>Measured:</b> segment angle and angular rate from one IMU on the "
            "torso and one on each leg, zeroed in a neutral standing posture, "
            "read over UART into an EtherCAT frame.<br><br>"
            "<b>Inferred:</b> lateral CoM position and velocity (mass-weighted "
            "sums of those angles), whole-body angular momentum about the stance "
            "foot, the desired torso state, and the momentum error the torque is "
            "proportional to. None of those four is a sensor reading."))
        o.add(body(
            "This is an observer without being called one: a model — segment "
            "masses, lengths and inertias scaled to the participant — turning "
            "measurable quantities into an unmeasurable state. Page 20's rule "
            "applies in full: an estimate is only as good as the model behind "
            "it, and a bias in the model appears as a bias in the correction.",
            dim=True))
        self.add(o)

        d = Card("the two error sources that matter, and why the design survives them")
        d.add(body(
            "<b>Gyro bias → drift.</b> Any rate offset integrates without bound; "
            "that is page 7's pole at the origin, arriving unasked. The design "
            "never integrates rate into angle for control: the momentum error uses "
            "rates directly, and the angles come from the IMU's own attitude "
            "solution with a standing zero. A dead zone on <i>angle</i> also means "
            "slow drift has to grow past 4.6° before it can command anything."
            "<br><br>"
            "<b>Model error → biased desired state.</b> θ_T,d comes from segment "
            "mass-times-distance ratios. Get the torso's centre of mass wrong by "
            "10 % and the desired torso angle is wrong by roughly the same "
            "fraction — but the correction is 15–20 % of a momentum error and "
            "unidirectional, so a biased reference perturbs magnitude, not sign."))
        self.add(d)

        i = Card("inject bias and noise, and watch the estimate leave the truth")
        i.add(body(
            "Truth is the teaching model's own torso momentum; the estimate is "
            "what the controller would compute from IMU signals carrying the bias "
            "and noise you set. The right panel is the thing to watch: how much "
            "commanded torque the estimation error alone is responsible for.",
            dim=True))
        self.s_bias = slider(0, 100, 15)     # x0.001 rad/s
        self.s_noise = slider(0, 100, 20)    # x0.001 rad/s rms
        self.s_mod = slider(-25, 25, 0)      # % model error on torso CoM
        self.l_bias, self.l_noise, self.l_mod = QLabel(), QLabel(), QLabel()
        i.add_layout(slider_row("gyro bias (×0.001 rad/s)", self.s_bias,
                                self.l_bias))
        i.add_layout(slider_row("rate noise (×0.001 rad/s)", self.s_noise,
                                self.l_noise))
        i.add_layout(slider_row("torso CoM model error (%)", self.s_mod,
                                self.l_mod))

        self.st_drift = Stat("H estimate error", "--", theme.BAD)
        self.st_spur = Stat("spurious torque", "--", theme.WARN)
        self.st_frac = Stat("of commanded torque", "--", theme.ACCENT)
        i.add_layout(stat_row(self.st_drift, self.st_spur, self.st_frac))
        self.c7 = MplCanvas(width=7.4, height=3.4, ncols=2)
        i.add(self.c7)
        self.add(i)
        for s_ in (self.s_bias, self.s_noise, self.s_mod):
            s_.valueChanged.connect(self._redraw)
        self._redraw()

        self.add(callout(
            "<b>Estimation is where this controller is most exposed.</b> There is "
            "no force plate, no motion capture and no absolute reference on the "
            "beam — three IMUs and a scaled anthropometric model are the whole "
            "sensing story. That is what makes it wearable, and it is what any "
            "future version has to improve first.", "warn"))

        self.finish()

    def _redraw(self):
        bias = self.s_bias.value() / 1000.0
        noise = self.s_noise.value() / 1000.0
        mod = self.s_mod.value() / 100.0
        self.l_bias.setText(f"{bias:.3f}")
        self.l_noise.setText(f"{noise:.3f}")
        self.l_mod.setText(f"{mod*100:+.0f}%")

        sim = _sim_cached(True, 1.0, 3.2, 5, bx.HARDWARE["mass_kg"], 0.08)
        t, th, w = sim["t"], sim["theta"], sim["omega"]
        s_true = bx.Subject()
        s_est = bx.Subject()
        s_est.torso_com_frac = s_true.torso_com_frac * (1 + mod)

        rng = np.random.default_rng(11)
        w_meas = w + bias + noise * rng.standard_normal(w.size)
        H_true = np.array([s_true.torso_momentum(a, b) for a, b in zip(th, w)])
        H_est = np.array([s_est.torso_momentum(a, b) for a, b in zip(th, w_meas)])
        err = H_est - H_true

        self.st_drift.set(f"{np.mean(np.abs(err)):.2f}")
        spur = 9.0 * 0.25 * np.mean(np.abs(err))
        self.st_spur.set(f"{spur:.2f} N·m")
        denom = max(1e-6, np.mean(np.abs(sim["tau_exo"])))
        self.st_frac.set(f"{100*spur/denom:.0f}%")

        c = self.c7
        c.clear()
        a1, a2 = c.axes
        a1.plot(t, H_true, color=theme.ACCENT, lw=1.6, label="true H_T")
        a1.plot(t, H_est, color=theme.BAD, lw=1.0, alpha=0.85,
                label="estimated H_T")
        a1.set_xlabel("time (s)")
        a1.set_ylabel("torso momentum (kg·m²/s)")
        c.legend(a1, loc="upper left")

        a2.plot(t, err, color=theme.WARN, lw=1.1)
        a2.axhline(0, color=theme.BORDER, lw=1.0)
        a2.set_xlabel("time (s)")
        a2.set_ylabel("estimate − truth")
        a2.set_title("the part the torque cannot tell from a real error")
        c.refresh()


# ==========================================================================
# 8 -- impedance vs admittance
# ==========================================================================

class BeamAdmittancePage(Page):
    TITLE = "Why Admittance, and Not Impedance"
    SUBTITLE = ("A 100:1 harmonic drive makes the choice for you. Page 38's "
                "decision, with this gearbox as the deciding evidence.")
    SECTION = SECTION

    def __init__(self, parent=None):
        super().__init__(parent)

        g = Card("the gearbox decides")
        g.add(math_label(r"J_{eff}=J_{link}+N^2 J_{rotor},\qquad N=100", 16))
        g.add(body(
            "Page 29's square law, with N = 100: the rotor is reflected to the "
            "hip multiplied by <b>ten thousand</b>. Add harmonic-drive friction "
            "and cogging and the joint is effectively non-backdrivable, and motor "
            "current stops being a usable estimate of the torque reaching the "
            "human.<br><br>"
            "So torque control at this joint is not available in the honest sense, "
            "and impedance control — motion in, torque out — has nothing reliable "
            "to put out. The device instead measures interaction torque with a "
            "<b>cantilevered load cell in parallel with the actuator</b> and "
            "commands motion: that is admittance control, and the hardware chose "
            "it."))
        self.add(g)

        a = Card("the admittance parameters, and the trick in them")
        a.add(math_label(r"\omega_{cmd}=\frac{1}{Ms^2+Bs+K}\tau,\qquad "
                         r"\omega_n=\sqrt{K/M}\approx 7.1\ \mathrm{rad/s},\qquad "
                         r"\zeta=\frac{B}{2\sqrt{KM}}\approx 0.7", 15))
        a.add(body(
            "With M = 1×10⁻³, B = 1×10⁻², K = 5×10⁻², the rendered mechanism is so "
            "light and so soft that the block is, for practical purposes, a "
            "torque-to-velocity pass-through. The paper says this outright: the "
            "virtual stiffness, damping and inertia are set very low so the "
            "controller behaves as a <b>torque source</b> while remaining an "
            "admittance.<br><br>"
            "That is not a fudge — it is how you get a torque source out of a "
            "non-backdrivable joint while keeping the passivity argument that an "
            "admittance structure with a real interaction-torque measurement "
            "gives you. Page 4's warning about active virtual mechanisms "
            "injecting energy is exactly what that structure is there to bound."))
        self.add(a)

        t = Card("and the same trick, used in reverse, is the control condition")
        t.add(body(
            "The <b>no assist</b> condition is not the motors switched off. The "
            "actuators were actively controlled to emulate a transparent, "
            "zero-impedance mode — compensating the device's intrinsic impedance "
            "rather than imposing it — so that the comparison isolates the "
            "momentum controller rather than the hardware's drag. The paper is "
            "careful about this and still declines to claim residual pelvis-torso "
            "coupling is exactly zero."))
        self.add(t)

        i = Card("reflected inertia, and what it costs above the bandwidth")
        i.add(body(
            "Left: where the inertia at the hip comes from, as N changes. Right: "
            "what the wearer feels across frequency — the rendered law below the "
            "corner, hardware above it.", dim=True))
        self.s_N = slider(1, 160, 100)
        self.s_rot = slider(2, 40, 10)       # x1e-5 kg m^2
        self.s_bw = slider(10, 120, 50)
        self.l_N, self.l_rot, self.l_bw = QLabel(), QLabel(), QLabel()
        i.add_layout(slider_row("gear ratio N", self.s_N, self.l_N))
        i.add_layout(slider_row("rotor inertia (×1e-5)", self.s_rot, self.l_rot))
        i.add_layout(slider_row("velocity bandwidth (Hz)", self.s_bw, self.l_bw))

        self.st_ref = Stat("reflected rotor", "--", theme.BAD)
        self.st_tot = Stat("J_eff at the hip", "--", theme.WARN)
        self.st_ratio = Stat("rotor : link", "--", theme.ACCENT)
        self.st_mode = Stat("control mode forced", "--", theme.CYAN)
        i.add_layout(stat_row(self.st_ref, self.st_tot, self.st_ratio,
                              self.st_mode))
        self.c8 = MplCanvas(width=7.4, height=3.4, ncols=2)
        i.add(self.c8)
        self.add(i)
        for s_ in (self.s_N, self.s_rot, self.s_bw):
            s_.valueChanged.connect(self._redraw)
        self._redraw()

        self.add(callout(
            "<b>The one-line decision rule.</b> Backdrivable and low friction → "
            "impedance, torque out. Geared, stiff and non-backdrivable, with a "
            "force sensor → admittance, motion out. This device is the second "
            "case, and every downstream choice — velocity-mode drives, the "
            "load cell, the low virtual parameters, the transparent control "
            "condition — follows from it.", "key"))

        self.finish()

    def _redraw(self):
        N = float(self.s_N.value())
        rot = self.s_rot.value() * 1e-5
        bw = self.s_bw.value() / 10.0
        self.l_N.setText(f"{N:.0f}:1")
        self.l_rot.setText(f"{rot:.0e}")
        self.l_bw.setText(f"{bw:.1f} Hz")

        r = bx.reflected_inertia(rot, N, 0.9)
        self.st_ref.set(f"{r['reflected']:.2f}")
        self.st_tot.set(f"{r['total']:.2f} kg·m²")
        self.st_ratio.set(f"{r['ratio']:.1f}×")
        adm = r["ratio"] > 0.5
        self.st_mode.set("admittance" if adm else "impedance is viable")
        self.st_mode.set_color(theme.WARN if adm else theme.GOOD)

        c = self.c8
        c.clear()
        a1, a2 = c.axes
        Ns = np.linspace(1, 160, 200)
        a1.plot(Ns, rot * Ns ** 2, color=theme.BAD, lw=2.0,
                label="reflected rotor")
        a1.axhline(0.9, color=theme.CYAN, lw=1.4, ls="--", label="link inertia")
        a1.axvline(N, color=theme.WARN, lw=1.2)
        a1.set_xlabel("gear ratio N")
        a1.set_ylabel("inertia at the hip (kg·m²)")
        a1.set_yscale("log")
        a1.set_title("the N² square law, on this gearbox")
        c.legend(a1, loc="upper left")

        f = np.logspace(-1, 2, 400)
        mag, _ = bx.velocity_loop_bode(f, bw, 2.0, bx.CONTROL["filter_hz"])
        rendered = 10 ** (mag / 20)
        felt_inertia = r["total"] * (2 * np.pi * f) ** 2
        a2.loglog(f, np.maximum(rendered * 40.0, 1e-3), color=theme.ACCENT,
                  lw=2.0, label="what the law renders")
        a2.loglog(f, felt_inertia, color=theme.BAD, lw=1.6, ls="--",
                  label="what the hardware is")
        a2.axvline(bw, color=theme.CYAN, lw=1.0, ls=":")
        a2.set_xlabel("frequency (Hz)")
        a2.set_ylabel("apparent torque per unit motion")
        a2.set_title("above the corner, you feel metal")
        c.legend(a2, loc="lower right")
        c.refresh()


# ==========================================================================
# 9 -- capstone
# ==========================================================================

class BeamResultsPage(Page):
    TITLE = "Capstone: What the Beam Actually Said"
    SUBTITLE = ("Ten participants, 18 trials per condition, a 4 cm beam — and a "
                "result that breaks even with a 6 kg penalty rather than beating "
                "it.")
    SECTION = SECTION

    def __init__(self, parent=None):
        super().__init__(parent)

        p = Card("the experiment, in one paragraph")
        p.add(body(
            "Ten able-bodied participants, arms folded, walking a <b>5.6 m</b> "
            "beam: 0.6 m at 8.4 cm to start, then <b>5 m at 4 cm</b>. Three "
            "conditions — unencumbered baseline, exo in transparent mode "
            "(<i>no assist</i>), exo with the momentum controller "
            "(<i>active assist</i>). <b>18 trials per condition</b>, randomised "
            "within sessions, participants blind to the condition. Distance to "
            "step-off measured with a marked parallel reference beam; maximum "
            "possible distance 90 m per condition. Failure = stepping off, "
            "touching the ground, or unfolding the arms."))
        self.add(p)

        self.add(_quoted(
            "<b>Beam completion.</b> active assist <b>79.5 %</b> vs no assist "
            "<b>70.1 %</b> (paired t-test p = 0.049, Cohen's d = 0.89): "
            "+9.4 percentage points, 95 % CI 1.83–17.16, about <b>8.5 m more</b> "
            "across the 18 trials, ≈47 cm per trial. Unencumbered baseline "
            "<b>80.9 %</b>; no assist was significantly <i>worse</i> than baseline "
            "(p = 0.048) while active assist was statistically "
            "indistinguishable from it (p = 0.965).<br><br>"
            "<b>Speed</b> higher with assistance (p = 0.0386, d = 0.76). "
            "<b>Normalised lateral CoM deviation</b> lower (p = 0.019, "
            "d = −0.90). <b>Normalised frontal-plane H_wb deviation</b> lower "
            "(p = 0.0169, d = −1.395). Survival curves identical over the wide "
            "lead-in section and diverging as the beam narrowed."))

        r = Card("reading those numbers like a control engineer")
        r.add(body(
            "<b>The engineering metrics moved in the direction the design "
            "predicted, and by more than the outcome did.</b> The largest effect "
            "size in the study is on momentum deviation (d = −1.395) — the "
            "quantity the controller regulates — and the outcome measure "
            "(distance) has a smaller one. That ordering is what a working "
            "mechanism looks like: the regulated variable improves most, and the "
            "task improves because of it.<br><br>"
            "<b>The honest ceiling is the hardware.</b> 6 kg of worn mass and its "
            "inertia cost about 10.8 percentage points of baseline performance, "
            "and the controller bought back 9.4. The result is a break-even "
            "against the unencumbered condition, which the paper states plainly. "
            "One participant did exceed their own baseline.<br><br>"
            "<b>What it does not show.</b> Able-bodied young adults, short-term "
            "exposure, one task. The link to real-world falls is via an external "
            "longitudinal finding (≈8.3 % better beam performance ↔ ≈32 % lower "
            "12-month odds of falling), not measured here."))
        self.add(r)

        i = Card("survival curves — quoted numbers beside model output")
        i.add(body(
            "Bars: the published group percentages. Curves: the teaching model's "
            "own survival, run with the same swing-leg disturbances in both "
            "conditions, which is the paired structure of the real design. The "
            "model is here to show the <i>mechanism</i> producing a divergence as "
            "the beam narrows — not to reproduce the measured values.", dim=True))
        self.s_kick = slider(10, 60, 32)
        self.s_gain = slider(50, 100, 100)
        self.l_kick, self.l_gain = QLabel(), QLabel()
        i.add_layout(slider_row("swing momentum / step", self.s_kick, self.l_kick))
        i.add_layout(slider_row("personalisation gain", self.s_gain, self.l_gain))

        self.st_a = Stat("model: active", "--", theme.ACCENT)
        self.st_n = Stat("model: no assist", "--", theme.BAD)
        self.st_b = Stat("model: baseline", "--", theme.CYAN)
        self.st_q = Stat("published gap", "9.4 pp", theme.GOOD)
        i.add_layout(stat_row(self.st_a, self.st_n, self.st_b, self.st_q))
        self.c9 = MplCanvas(width=7.4, height=3.4, ncols=2)
        i.add(self.c9)
        self.add(i)
        for s_ in (self.s_kick, self.s_gain):
            s_.valueChanged.connect(self._redraw)
        self._redraw()

        n = Card("where this goes next")
        n.add(body(
            "<b>Hardware, not control, is the binding constraint.</b> Lighter "
            "actuation and an untethered EtherCAT replacement are named as the "
            "two engineering fixes; the device is 6 kg and currently tethered.<br><br>"
            "<b>Second strategy.</b> The controller assists segment-rotation "
            "momentum regulation. Foot placement is the other hip-mediated "
            "strategy, and a controller that assists both is the stated next "
            "step.<br><br>"
            "<b>Populations.</b> Lower-limb prosthesis users and older adults, "
            "where hip strength and sensorimotor control are already compromised — "
            "and where task difficulty has to be re-tuned (beam width) for the "
            "measurement to be sensitive at all."))
        self.add(n)

        self.add(callout(
            "<b>What this section was for.</b> Every page of the general block "
            "shows up here as a design decision with a number attached: the "
            "unstable pole set the urgency, the 200 ms volitional window set the "
            "bandwidth, the bandwidth measurement set what could be rendered, the "
            "gear ratio chose admittance over impedance, the dead zone and the "
            "unidirectional torque were stability decisions, and the estimation "
            "chain is where the remaining risk lives. That is what it looks like "
            "to spend control theory on one real machine.", "good"))

        self.finish()

    def _redraw(self):
        kick = self.s_kick.value() / 10.0
        gain = self.s_gain.value() / 100.0
        self.l_kick.setText(f"{kick:.1f} kg·m²/s")
        self.l_gain.setText(f"{gain:.2f}")

        curves = _survival_cached(round(kick, 1))
        self.st_a.set(f"{curves['active assist']['pct']:.0f}%")
        self.st_n.set(f"{curves['no assist']['pct']:.0f}%")
        self.st_b.set(f"{curves['baseline']['pct']:.0f}%")

        c = self.c9
        c.clear()
        a1, a2 = c.axes
        labels = ["baseline", "no assist", "active assist"]
        vals = [bx.TRIAL_RESULTS["baseline_pct"],
                bx.TRIAL_RESULTS["no_assist_pct"],
                bx.TRIAL_RESULTS["active_pct"]]
        a1.bar(labels, vals, color=[theme.CYAN, theme.BAD, theme.ACCENT])
        for x, v in enumerate(vals):
            a1.text(x, v + 1, f"{v:.1f}", color=theme.TEXT, fontsize=9,
                    ha="center")
        a1.set_ylim(0, 100)
        a1.set_ylabel("% of beam completed")
        a1.set_title("published group means (n = 10)")

        for label, col in (("baseline", theme.CYAN), ("no assist", theme.BAD),
                           ("active assist", theme.ACCENT)):
            d = curves[label]
            a2.plot(d["x"], d["survival"] * 100, color=col, lw=1.8, label=label)
        a2.axvspan(0, 0.6, color=theme.TEXT_FAINT, alpha=0.12)
        a2.text(0.3, 10, "wide\nlead-in", color=theme.TEXT_FAINT, fontsize=8,
                ha="center")
        a2.set_xlabel("distance along the beam (m)")
        a2.set_ylabel("% of trials surviving")
        a2.set_title("teaching model, paired disturbances")
        c.legend(a2, loc="lower left")
        c.refresh()
