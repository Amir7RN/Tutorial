"""
FAULT TOLERANCE -- the same control machinery, spent on the second project: an
active fault-tolerant mechanism (FTM) for a robotic knee prosthesis.

Nine pages, parallel to the general block and to the Beam Balance section:

    1  real-time     -- the timing chain that decides whether compensation helps
    2  the plant     -- what a knee fault moves first, and which signal is robust
    3  FSM impedance -- four states, three numbers each, and what a wrong set does
    4  detection     -- a residual, a threshold, and a persistence test
    5  stability     -- bolting a second controller onto a working loop
    6  compensation  -- momentum error to additive torque, scaled by severity
    7  estimation    -- Gaussian processes as observers of nominal behaviour
    8  latency       -- 43 ms vs 103 ms, and why that is the whole result
    9  capstone      -- what eight participants showed, and what is still missing

Published numbers are quoted and marked. Simulations are teaching models of the
published architecture -- see the docstring of `ctrlcore.faulttol`.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel

from ctrlcore import faulttol as ft
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

SECTION = "Fault Tolerance"

SOURCE = (
    "<b>Source.</b> <i>Active Fault-Tolerant Control of Robotic Knee Prostheses "
    "for Safe Locomotion</i> (IEEE T-RO submission). Measured numbers on these "
    "pages are quoted from that manuscript. Simulations are teaching models of "
    "the published architecture on a single-joint plant, not reproductions of "
    "the experiment."
)


def _quoted(text):
    return callout(text, "good", label="QUOTED FROM THE PAPER")


@lru_cache(maxsize=32)
def _roc_cached(alpha: float):
    """Sweeping k costs a few dozen strides, so hold the answer per severity."""
    return ft.detector_roc(k_values=np.linspace(0.4, 3.0, 7), n_strides=4,
                           alpha=alpha)


@lru_cache(maxsize=64)
def _trial_cached(mode: str, alpha: float, state: str, ftm: bool,
                  k: float = ft.DETECTOR["k"], n_consec: int = 10,
                  noise: float = 0.05, false_alarm: bool = False, seed: int = 3):
    return ft.FaultTrial(fault_mode=mode, alpha=alpha, fault_state=state,
                         ftm=ftm, detector_k=k, n_consec=n_consec, noise=noise,
                         false_alarm=false_alarm, seed=seed).run()


# ==========================================================================
# 1 -- real time
# ==========================================================================

class FaultRealTimePage(Page):
    TITLE = "Real Time on a Prosthetic Knee"
    SUBTITLE = ("A 200 ms fault, a 10 ms persistence test, a 54 ms detection and "
                "a 200–250 ms human. Every number in this project is a "
                "millisecond budget.")
    SECTION = SECTION
    NOTES = "knee · FTM"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(body(SOURCE, dim=True))

        c = Card("the timeline, and why each interval is the length it is")
        c.add(body(
            "<b>1 kHz control task</b> on TwinCAT: one sample, one FSM state "
            "evaluation, one detection decision, one compensatory torque, every "
            "millisecond.<br><br>"
            "<b>200 ms injected fault.</b> Chosen to be <i>shorter</i> than the "
            "200–250 ms volitional reactive balance response, so that what the "
            "measurement captures is the mechanical consequence of the fault "
            "rather than the user's voluntary recovery. That is a beautiful piece "
            "of experiment design and it is also a hard constraint on the "
            "controller: whatever the FTM is going to do, it has to happen inside "
            "that window.<br><br>"
            "<b>10 ms persistence.</b> The detector requires <b>all 10</b> "
            "consecutive samples to exceed threshold before declaring a fault. "
            "Ten milliseconds of the 200 ms budget spent buying immunity to "
            "single-sample noise.<br><br>"
            "<b>Filters.</b> Load and IMU rates low-passed at 30 Hz (4th-order "
            "Butterworth), preserving the 0–8 Hz band that is biomechanically "
            "real. The compensatory torque is filtered at 15 Hz (2nd-order), "
            "which costs under 5 ms of group delay in 0–10 Hz — explicitly "
            "checked against the detection time it would otherwise spoil."))
        self.add(c)

        self.add(_quoted(
            "Detection performance: <b>100 % sensitivity</b> across all tested "
            "walking conditions, false-alarm rate <b>10.8 ± 10.0 %</b>, detection "
            "time <b>54.4 ± 28.7 ms</b>. Cases that still produced perceived "
            "instability had an average detection delay of <b>103.5 ms</b>, "
            "against <b>43.1 ± 11.5 ms</b> for the ones where compensation "
            "worked."))

        b = Card("where the milliseconds go")
        b.add(math_label(r"200\ \mathrm{ms\ fault} = "
                         r"\underbrace{10}_{\text{persistence}} + "
                         r"\underbrace{\sim 30\text{--}90}_{\text{residual grows "
                         r"past threshold}} + "
                         r"\underbrace{\sim 5}_{\text{torque filter}} + "
                         r"\underbrace{\text{the rest}}_{\text{compensated}}", 14)
              )
        b.add(body(
            "Read that as a page 1 budget. The persistence test and the torque "
            "filter are fixed costs you chose. The variable cost — how long the "
            "residual takes to climb past threshold — depends on how severe the "
            "fault is and where in the gait cycle it lands, and it is the only "
            "term the designer can attack. Everything on page 8 of this section "
            "is about that term.", dim=True))
        self.add(b)

        i = Card("slide the detection time and watch the margin of stability")
        i.add(body(
            "The fault enters as a disturbance over its 200 ms window; "
            "compensation removes most of what remains once detection has fired. "
            "Nothing else changes. The only variable is <b>when</b>.", dim=True))
        self.s_det = slider(10, 180, 54)
        self.s_dur = slider(50, 400, 200)
        self.l_det, self.l_dur = QLabel(), QLabel()
        i.add_layout(slider_row("detection time (ms)", self.s_det, self.l_det))
        i.add_layout(slider_row("fault duration (ms)", self.s_dur, self.l_dur))
        self.chk_ftm = QCheckBox("FTM active")
        self.chk_ftm.setChecked(True)
        self.chk_ftm.stateChanged.connect(self._redraw)
        i.add(self.chk_ftm)

        self.st_frac = Stat("fault let through", "--", theme.BAD)
        self.st_mos = Stat("worst MoS excursion", "--", theme.WARN)
        self.st_vol = Stat("vs volitional window", "--", theme.CYAN)
        i.add_layout(stat_row(self.st_frac, self.st_mos, self.st_vol))
        self.c1 = MplCanvas(width=7.4, height=3.4, ncols=2)
        i.add(self.c1)
        self.add(i)
        for s_ in (self.s_det, self.s_dur):
            s_.valueChanged.connect(self._redraw)
        self._redraw()

        self.add(callout(
            "<b>The defining constraint of this project.</b> A prosthesis fault "
            "does its damage before the wearer can react, so a supervisory layer "
            "is only useful if it fits inside a window that was chosen to exclude "
            "human reaction. That is why the detector is tuned for speed and not "
            "for precision — a design choice the next pages justify with numbers.",
            "key"))

        self.finish()

    def _redraw(self):
        det = float(self.s_det.value())
        dur = float(self.s_dur.value())
        comp = self.chk_ftm.isChecked()
        self.l_det.setText(f"{det:.0f} ms")
        self.l_dur.setText(f"{dur:.0f} ms")

        t, mos, win = ft.mos_trace(det, comp, fault_ms=dur)
        t0, mos0, _ = ft.mos_trace(det, False, fault_ms=dur)
        frac = min(1.0, det / dur) if comp else 1.0
        self.st_frac.set(f"{frac*100:.0f}%")
        self.st_frac.set_color(theme.GOOD if frac < 0.35 else theme.WARN
                               if frac < 0.6 else theme.BAD)
        self.st_mos.set(f"{np.min(mos):.3f} m")
        self.st_vol.set(f"{det/225*100:.0f}% of it")

        c = self.c1
        c.clear()
        a1, a2 = c.axes
        a1.plot(t0 * 1000, mos0, color=theme.BAD, lw=1.4, ls="--",
                label="no compensation")
        a1.plot(t * 1000, mos, color=theme.ACCENT, lw=2.0,
                label="FTM active" if comp else "FTM off")
        a1.axvspan(win[0] * 1000, win[1] * 1000, color=theme.WARN, alpha=0.15)
        a1.axvline(win[0] * 1000 + det, color=theme.CYAN, lw=1.2, ls=":",
                   label="detection")
        a1.axhline(0, color=theme.BAD, lw=1.0)
        a1.set_xlabel("time (ms)")
        a1.set_ylabel("margin of stability (m)")
        c.legend(a1, loc="lower left")

        dets = np.linspace(10, 200, 60)
        worst = [np.min(ft.mos_trace(d, True, fault_ms=dur)[1]) for d in dets]
        a2.plot(dets, worst, color=theme.VIOLET, lw=2.0)
        a2.axvline(ft.RESULTS["detect_effective_ms"], color=theme.GOOD, lw=1.2,
                   ls=":", label="43 ms — compensation worked")
        a2.axvline(ft.RESULTS["detect_delayed_ms"], color=theme.BAD, lw=1.2,
                   ls=":", label="103 ms — still perceived")
        a2.plot([det], [np.min(mos)], "o", color=theme.WARN, ms=8)
        a2.set_xlabel("detection time (ms)")
        a2.set_ylabel("worst MoS")
        a2.set_title("the whole result is on this axis")
        c.legend(a2, loc="lower left")
        c.refresh()


# ==========================================================================
# 2 -- the plant
# ==========================================================================

class FaultPlantPage(Page):
    TITLE = "The Plant, and Which Signal to Trust"
    SUBTITLE = ("A knee fault moves the proximal segments first. Knee velocity "
                "is the sensitive signal; axial load is the robust one. The "
                "architecture is built on that asymmetry.")
    SECTION = SECTION

    def __init__(self, parent=None):
        super().__init__(parent)

        p = Card("what is measured on this device")
        p.add(body(
            "<b>Potentiometer</b> at the knee — angle. <b>Six-axis load cell</b> "
            "(ATI Mini58) between prosthetic foot and pylon — axial load. Two "
            "<b>IMUs</b>, one on the socket (thigh) and one on the shank — segment "
            "kinematics. Nothing external: no motion capture, no instrumented "
            "floor. The paper makes a point of this — the entire mechanism is "
            "self-contained, which is what makes it a candidate for daily use."))
        self.add(p)

        s = Card("the asymmetry the whole design rests on")
        s.add(body(
            "Prior work established that <b>knee angular velocity is highly "
            "sensitive</b> to control errors while <b>axial load is relatively "
            "robust</b> to them. So the architecture uses:<br><br>"
            "&nbsp;&nbsp;<b>load → input</b>, because you need an input that the "
            "fault has not corrupted;<br>"
            "&nbsp;&nbsp;<b>velocity → output</b>, because you need an output the "
            "fault will visibly move.<br><br>"
            "That is a sharper statement of page 2's observability point. Two "
            "signals from the same hardware: one barely sees the fault, one sees "
            "it immediately. The first is your reference channel, the second is "
            "your detector."))
        s.add(math_label(r"u(t)=\begin{bmatrix}F_p(t)\\ \dot F_p(t)\end{bmatrix}"
                         r"\;\longrightarrow\;\hat{\dot\theta}_{Knee}(t)", 16))
        s.add(body(
            "And the derivative is in there for a specific, checkable reason: a "
            "given axial load occurs <b>twice</b> per stance — once while loading, "
            "once while unloading — with different knee velocities. Load alone is "
            "ambiguous; load plus its sign of change is not.", dim=True))
        self.add(s)

        m = Card("why momentum is the compensation variable")
        m.add(math_label(r"H_{Knee}=\sum_{s\in\{th,sh\}}\left(I_s\omega_s + "
                         r"r_{Knee\to s}\times m_s v_s\right)", 16))
        m.add(body(
            "A wrong knee torque acts on the segments next to the knee before it "
            "acts on anything else, so the thigh's and shank's angular momentum "
            "about the joint is the earliest informative measure of the "
            "disturbance. It also correlated with users' <i>perceived</i> "
            "instability in prior work — which is why compensation is scaled by a "
            "momentum deviation rather than by a fixed corrective action."))
        self.add(m)

        i = Card("the two signals, over one stride")
        i.add(body(
            "Left: the robust input pair — load and its derivative. Right: the "
            "ambiguity being resolved. Pick a load level and see the two knee "
            "velocities compatible with it; the derivative's sign is what tells "
            "them apart.", dim=True))
        self.s_load = slider(10, 95, 60)      # % of peak
        self.s_speed = slider(4, 10, 6)       # x0.1 m/s
        self.l_load, self.l_speed = QLabel(), QLabel()
        i.add_layout(slider_row("load level (% of peak)", self.s_load, self.l_load))
        i.add_layout(slider_row("walking speed (m/s)", self.s_speed, self.l_speed))

        self.st_amb = Stat("candidate velocities", "--", theme.WARN)
        self.st_sep = Stat("they differ by", "--", theme.BAD)
        self.st_res = Stat("resolved by dF/dt", "--", theme.GOOD)
        i.add_layout(stat_row(self.st_amb, self.st_sep, self.st_res))
        self.c2 = MplCanvas(width=7.4, height=3.4, ncols=2)
        i.add(self.c2)
        self.add(i)
        for s_ in (self.s_load, self.s_speed):
            s_.valueChanged.connect(self._redraw)
        self._redraw()

        self.finish()

    def _redraw(self):
        lvl = self.s_load.value() / 100.0
        speed = self.s_speed.value() / 10.0
        stride = 1.25 * 0.6 / speed
        self.l_load.setText(f"{lvl*100:.0f}%")
        self.l_speed.setText(f"{speed:.1f} m/s")

        t = np.arange(0, stride, 1e-3)
        load = ft.axial_load_profile(t, stride)
        dload = np.gradient(load, t)
        mu, sigma = ft.nominal_knee_velocity(t, stride)

        target = lvl * load.max()
        crossings = np.where(np.diff(np.sign(load - target)) != 0)[0]
        vels = [mu[k] for k in crossings[:2]]
        self.st_amb.set(", ".join(f"{v:+.2f}" for v in vels) if vels else "—")
        self.st_sep.set(f"{abs(vels[0]-vels[1]):.2f} rad/s"
                        if len(vels) > 1 else "—")
        if len(vels) > 1:
            signs = [np.sign(dload[k]) for k in crossings[:2]]
            self.st_res.set("yes" if signs[0] != signs[1] else "no")
            self.st_res.set_color(theme.GOOD if signs[0] != signs[1] else theme.BAD)

        c = self.c2
        c.clear()
        a1, a2 = c.axes
        a1.plot(t, load, color=theme.ACCENT, lw=2.0, label="axial load F_p (N)")
        a1.plot(t, dload / 20, color=theme.VIOLET, lw=1.2,
                label="dF_p/dt  (÷20)")
        a1.axhline(target, color=theme.WARN, lw=1.2, ls="--")
        a1.set_xlabel("time (s)")
        a1.set_ylabel("N")
        a1.set_title("the robust input pair")
        c.legend(a1, loc="upper right")

        a2.plot(t, mu, color=theme.CYAN, lw=2.0, label="nominal knee velocity")
        a2.fill_between(t, mu - sigma, mu + sigma, color=theme.CYAN, alpha=0.18,
                        label="±1σ of undisturbed walking")
        for k in crossings[:2]:
            a2.plot([t[k]], [mu[k]], "o", color=theme.WARN, ms=8)
        a2.set_xlabel("time (s)")
        a2.set_ylabel("rad/s")
        a2.set_title("same load, two velocities")
        c.legend(a2, loc="lower left")
        c.refresh()


# ==========================================================================
# 3 -- FSM impedance
# ==========================================================================

class FaultFSMPage(Page):
    TITLE = "FSM Impedance, and What a Wrong Parameter Set Does"
    SUBTITLE = ("Four states, three numbers each. A locomotion-mode "
                "misclassification swaps the numbers, and the joint obeys them.")
    SECTION = SECTION

    def __init__(self, parent=None):
        super().__init__(parent)

        f = Card("the baseline controller")
        f.add(math_label(r"\tau_{FSM}=-K_q\left(\theta-\theta_{eq,q}\right)"
                         r"-B_q\dot\theta,\qquad "
                         r"q\in\{\mathrm{SF,SE,SwF,SwE}\}", 16))
        f.add(body(
            "Stance flexion, stance extension, swing flexion, swing extension. "
            "Each state has a constant stiffness, damping and equilibrium angle, "
            "tuned per participant for undisturbed walking. Inside one state this "
            "is exactly page 11's second-order system with page 4's virtual "
            "spring and damper — so ω_n and ζ are decided by the three numbers in "
            "the table, and the shape of the knee's response follows."))
        self.add(f)

        e = Card("how the fault is created, and why that is the realistic one")
        e.add(math_label(r"P_e(\alpha)=P_n+\alpha\left(P_o-P_n\right)", 16))
        e.add(body(
            "P_n is the participant's tuned level-ground set. P_o is a "
            "standardised set for another locomotion mode — ramp ascent or "
            "descent, stair ascent or descent. Interpolating between them with α "
            "generates a whole family of faults: intermediate α is a soft "
            "estimation or blending error, α = 1 is an abrupt misclassification "
            "between modes.<br><br>"
            "The primary deviations are in <b>equilibrium angle and stiffness "
            "during SF and SE</b>. This is not an abstract disturbance: it is what "
            "a mode-recognition mistake physically does to a prosthetic knee, "
            "substituted into the live controller for 200 ms during stance."))
        self.add(e)

        self.add(_quoted(
            "Fault severity was calibrated per participant by raising α until the "
            "participant reported a <b>'Large'</b> disturbance, using a four-level "
            "scale (None / Small / Medium / Large). That is a perception-normalised "
            "severity, not a fixed torque — which is what makes the participants "
            "comparable without a shared α."))

        i = Card("pick a misclassification and see what the knee is told to do")
        i.add(body(
            "The impedance law is drawn for both parameter sets over the knee's "
            "working range. The gap between the two lines <i>is</i> the fault: it "
            "is the torque error the joint receives, and everything the FTM does "
            "downstream is an attempt to put that gap back.", dim=True))
        self.mode = QComboBox()
        for k in ft.PARAM_SETS:
            if k != "level ground (nominal)":
                self.mode.addItem(k, k)
        self.mode.currentIndexChanged.connect(self._redraw)
        i.add_layout(labelled("misclassified as", self.mode, width=150))
        self.state = QComboBox()
        self.state.addItem("stance flexion (SF)", "SF")
        self.state.addItem("stance extension (SE)", "SE")
        self.state.currentIndexChanged.connect(self._redraw)
        i.add_layout(labelled("during", self.state, width=150))

        self.s_alpha = slider(0, 100, 100)
        self.l_alpha = QLabel()
        i.add_layout(slider_row("severity α", self.s_alpha, self.l_alpha))

        self.st_dk = Stat("ΔK", "--", theme.BAD)
        self.st_deq = Stat("Δθ_eq", "--", theme.WARN)
        self.st_dtau = Stat("torque error at 20°", "--", theme.ACCENT)
        self.st_wn = Stat("ω_n shift", "--", theme.VIOLET)
        i.add_layout(stat_row(self.st_dk, self.st_deq, self.st_dtau, self.st_wn))
        self.c3 = MplCanvas(width=7.4, height=3.4, ncols=2)
        i.add(self.c3)
        self.add(i)
        self.s_alpha.valueChanged.connect(self._redraw)
        self._redraw()

        self.add(callout(
            "<b>An impedance fault is not a torque spike.</b> It is a different "
            "virtual mechanism, installed for 200 ms. A stiffer spring with a "
            "further-away equilibrium keeps pushing for as long as it is "
            "installed, and its effect grows with how far the joint has already "
            "moved. That is why a fixed on-off corrective action is the wrong "
            "answer and a severity-scaled one is the right one.", "key"))

        self.finish()

    def _redraw(self):
        mode = self.mode.currentData()
        st = self.state.currentData()
        alpha = self.s_alpha.value() / 100.0
        self.l_alpha.setText(f"{alpha:.2f}")

        nominal = ft.PARAM_SETS["level ground (nominal)"]
        faulty = ft.blend(nominal, ft.PARAM_SETS[mode], alpha)
        Kn, Bn, eqn = nominal[st]
        Kf, Bf, eqf = faulty[st]

        self.st_dk.set(f"{Kf-Kn:+.0f} N·m/rad")
        self.st_deq.set(f"{np.degrees(eqf-eqn):+.1f}°")
        th = np.radians(20.0)
        err = (-Kf * (th - eqf)) - (-Kn * (th - eqn))
        self.st_dtau.set(f"{err:+.1f} N·m")
        J = ft.Knee().J
        self.st_wn.set(f"{np.sqrt(Kf/J)-np.sqrt(Kn/J):+.1f} rad/s")

        c = self.c3
        c.clear()
        a1, a2 = c.axes
        angs = np.radians(np.linspace(-5, 60, 300))
        a1.plot(np.degrees(angs), -Kn * (angs - eqn), color=theme.ACCENT, lw=2.0,
                label="nominal")
        a1.plot(np.degrees(angs), -Kf * (angs - eqf), color=theme.BAD, lw=2.0,
                ls="--", label=f"{mode} (α={alpha:.2f})")
        a1.fill_between(np.degrees(angs), -Kn * (angs - eqn),
                        -Kf * (angs - eqf), color=theme.BAD, alpha=0.12)
        a1.axhline(0, color=theme.BORDER, lw=1.0)
        a1.set_xlabel("knee angle (deg)")
        a1.set_ylabel("commanded torque (N·m)")
        a1.set_title(f"the impedance law in {st}")
        c.legend(a1, loc="lower left")

        trial_off = _trial_cached(mode, round(alpha, 2), st, False)
        a2.plot(trial_off["t"], trial_off["tau_base"], color=theme.BAD, lw=1.4,
                label="commanded torque during the fault")
        a2.axvspan(*trial_off["fault_window"], color=theme.WARN, alpha=0.15)
        a2.set_xlabel("time (s)")
        a2.set_ylabel("N·m")
        a2.set_title("one stride, fault injected")
        c.legend(a2, loc="upper left")
        c.refresh()


# ==========================================================================
# 4 -- detection
# ==========================================================================

class FaultDetectionPage(Page):
    TITLE = "Detection: One Residual, One Threshold, One Persistence Test"
    SUBTITLE = ("T_vel = |μ| + kσ with k = 1, and all ten of the last ten "
                "samples. A deliberately trigger-happy detector, and the "
                "argument for it.")
    SECTION = SECTION

    def __init__(self, parent=None):
        super().__init__(parent)

        d = Card("the detector, in three lines")
        d.add(math_label(r"r_v(t)=\dot\theta_{Knee}(t)-\hat{\dot\theta}_{Knee}(t)",
                         16))
        d.add(math_label(r"T_{vel}(t)=\left|\mu_{\dot\theta}(t)\right| + "
                         r"k\,\sigma_{\dot\theta}(t),\qquad k=1", 16))
        d.add(math_label(r"\Gamma(t)=1 \iff \left|r_v(t-i)\right|>T_{vel}"
                         r"\ \ \forall\, i=0\ldots N_c-1,\qquad N_c=10", 15))
        d.add(body(
            "Three things worth noticing. The threshold is <b>time-varying</b> — "
            "it tracks the nominal mean and the nominal spread through the gait "
            "cycle, so a swing-phase velocity of 3 rad/s is not a fault while the "
            "same number in mid-stance is. The absolute value keeps the threshold "
            "non-negative in phases where the mean velocity is negative. And the "
            "persistence test is a logical AND, not a count — ten in a row, not "
            "ten out of twenty."))
        self.add(d)

        k = Card("why k = 1, stated as a trade and not a preference")
        k.add(body(
            "k sets where you sit on the ROC curve. Small k: detect everything, "
            "fast, with more false alarms. Large k: fewer false alarms, later "
            "detections, and eventually missed faults.<br><br>"
            "The paper chooses k = 1 and says why: <b>the cost of the two errors "
            "is not symmetric</b>. A false alarm generates a small corrective "
            "impulse (0.021 N·m·s/kg measured) that does not measurably disturb "
            "gait; a late detection lets the fault reach the user's balance, and "
            "the cases that still felt unstable were exactly the late ones "
            "(103.5 ms vs 43.1 ms). So the detector is tuned for sensitivity, and "
            "the <i>compensator</i> is designed to make false alarms cheap. Those "
            "two decisions are one decision."))
        self.add(k)

        i = Card("move k and N_c and watch the trade happen")
        i.add(body(
            "Left: the residual against its moving threshold band for one injected "
            "fault. Right: sensitivity, false-alarm rate and mean detection time "
            "against k, computed over repeated strides of the teaching model.",
            dim=True))
        self.s_k = slider(4, 30, 10)         # x0.1
        self.s_n = slider(1, 40, 10)
        self.s_alpha = slider(20, 100, 100)
        self.l_k, self.l_n, self.l_alpha = QLabel(), QLabel(), QLabel()
        i.add_layout(slider_row("threshold multiplier k", self.s_k, self.l_k))
        i.add_layout(slider_row("persistence N_c (samples)", self.s_n, self.l_n))
        i.add_layout(slider_row("fault severity α", self.s_alpha, self.l_alpha))

        self.st_t = Stat("detection time", "--", theme.ACCENT)
        self.st_s = Stat("sensitivity", "--", theme.GOOD)
        self.st_f = Stat("false alarms", "--", theme.WARN)
        i.add_layout(stat_row(self.st_t, self.st_s, self.st_f))
        self.c4 = MplCanvas(width=7.4, height=3.4, ncols=2)
        i.add(self.c4)
        self.add(i)
        for s_ in (self.s_k, self.s_n, self.s_alpha):
            s_.valueChanged.connect(self._redraw)
        self._redraw()

        self.add(callout(
            "<b>This is page 13's honesty argument in a different costume.</b> "
            "Gain margin and phase margin ask \"how wrong can the world be before "
            "this fails\". A detector's k and N_c ask \"how wrong can a single "
            "sample be before I act\". Both are chosen against the cost of being "
            "wrong in each direction, not against a number that sounds safe.",
            "key"))

        self.finish()

    def _redraw(self):
        k = self.s_k.value() / 10.0
        n = self.s_n.value()
        alpha = self.s_alpha.value() / 100.0
        self.l_k.setText(f"{k:.1f}")
        self.l_n.setText(f"{n} ({n} ms)")
        self.l_alpha.setText(f"{alpha:.2f}")

        tr = _trial_cached("ramp ascent", round(alpha, 2), "SE", False,
                           k=k, n_consec=n)
        self.st_t.set("missed" if tr["detect_ms"] is None
                      else f"{tr['detect_ms']:.0f} ms")
        self.st_t.set_color(theme.BAD if tr["detect_ms"] is None
                            or tr["detect_ms"] > 90 else theme.GOOD)

        roc = _roc_cached(round(alpha, 2))
        idx = int(np.argmin(np.abs(roc["k"] - k)))
        self.st_s.set(f"{roc['sensitivity'][idx]:.0f}%")
        self.st_f.set(f"{roc['false_alarm'][idx]:.0f}%")

        c = self.c4
        c.clear()
        a1, a2 = c.axes
        a1.plot(tr["t"], tr["residual"], color=theme.CYAN, lw=1.2,
                label="residual r_v")
        a1.plot(tr["t"], tr["threshold"], color=theme.WARN, lw=1.2, ls="--",
                label="T_vel")
        a1.plot(tr["t"], -tr["threshold"], color=theme.WARN, lw=1.2, ls="--")
        a1.axvspan(*tr["fault_window"], color=theme.BAD, alpha=0.15)
        a1.set_xlabel("time (s)")
        a1.set_ylabel("rad/s")
        a1.set_title("residual vs a moving threshold")
        c.legend(a1, loc="upper left")

        a2.plot(roc["k"], roc["sensitivity"], color=theme.GOOD, lw=2.0,
                label="sensitivity (%)")
        a2.plot(roc["k"], roc["false_alarm"], color=theme.BAD, lw=2.0,
                label="false alarm (%)")
        a2.plot(roc["k"], roc["detect_ms"], color=theme.VIOLET, lw=1.6, ls="--",
                label="detection time (ms)")
        a2.axvline(1.0, color=theme.ACCENT, lw=1.2, ls=":", label="k = 1 (shipped)")
        a2.set_xlabel("threshold multiplier k")
        a2.set_title("the trade, drawn")
        c.legend(a2, loc="center right")
        c.refresh()


# ==========================================================================
# 5 -- stability of a supervisory layer
# ==========================================================================

class FaultStabilityPage(Page):
    TITLE = "Bolting a Second Controller onto a Working Loop"
    SUBTITLE = ("An additive torque interface, a bias that cancels, and a filter "
                "whose group delay was checked. Why the FTM does not fight the "
                "controller it supervises.")
    SECTION = SECTION

    def __init__(self, parent=None):
        super().__init__(parent)

        a = Card("the interface, and what it guarantees")
        a.add(math_label(r"\tau_{Final}(t)=\tau_{base}(t)+\tau_{FTM}(t)", 17))
        a.add(body(
            "One line, and it is the architectural claim of the whole paper. The "
            "baseline controller stays engaged at all times, keeping its "
            "compliance and its passive stability properties; the FTM only adds. "
            "Because the interface is a torque sum and the inputs are prosthesis-"
            "side kinematics and kinetics, the layer does not care whether the "
            "baseline is an FSM, a continuous-phase controller or EMG-driven.<br><br>"
            "Compare this with the alternative of replacing the controller when a "
            "fault is suspected. A switch changes the plant the user is standing "
            "on, mid-stance, on the basis of a detector that is deliberately "
            "trigger-happy. An additive term with a bounded magnitude does not."))
        self.add(a)

        b = Card("the bias cancellation, which is the quietly clever part")
        b.add(math_label(r"\tau_{FTM}=\hat\tau_{FSM}\!\left(\hat x\right)-"
                         r"\tau_{FSM}\!\left(x\right)", 16))
        b.add(body(
            "The <i>same</i> learned map G_fsm is evaluated twice — once at the "
            "estimated nominal state and once at the measured state — and only the "
            "difference is commanded. Any constant bias in that map appears in "
            "both terms and subtracts out. So a systematically wrong model does "
            "not produce a systematically wrong torque; it produces a slightly "
            "wrong <i>gain</i> on a difference that is zero when nothing is "
            "wrong.<br><br>"
            "That property is why the layer is safe to leave switched on. This is "
            "the same reasoning as the feedforward-vs-feedback argument from the "
            "PID page: make the term you add vanish identically in the nominal "
            "case, and its errors cannot accumulate."))
        self.add(b)

        c = Card("three remaining exposures, named")
        c.add(body(
            "<b>Filter phase.</b> The 15 Hz Butterworth on τ_FTM costs under 5 ms "
            "of group delay in 0–10 Hz, and that was checked against detection "
            "time and stance sub-phase duration rather than assumed negligible."
            "<br><br>"
            "<b>False alarms as disturbances.</b> A false detection is a small "
            "commanded torque with no fault to cancel — a disturbance the "
            "supervisory layer injects. Measured impulse: 0.021 vs 0.099 N·m·s/kg "
            "for real faults, and the false-alarm condition was statistically "
            "indistinguishable from normal walking on margin of stability "
            "(p = 0.95).<br><br>"
            "<b>Sensor failure.</b> The detector's input is a load cell. A hard "
            "disconnection does not produce a fault report; it produces a broken "
            "detector. The paper says so, and names sensor redundancy on critical "
            "FTM inputs as the layer that would cover it."))
        self.add(c)

        i = Card("true fault, false alarm, and normal — same axes")
        i.add(body(
            "Three runs of the teaching model: a real fault with the FTM on, a "
            "false detection with no fault present, and undisturbed walking. The "
            "point is the size of the middle one.", dim=True))
        self.s_alpha = slider(20, 100, 100)
        self.l_alpha = QLabel()
        i.add_layout(slider_row("fault severity α", self.s_alpha, self.l_alpha))

        self.st_it = Stat("impulse, true fault", "--", theme.ACCENT)
        self.st_if = Stat("impulse, false alarm", "--", theme.WARN)
        self.st_r = Stat("ratio", "--", theme.GOOD)
        i.add_layout(stat_row(self.st_it, self.st_if, self.st_r))
        self.c5 = MplCanvas(width=7.4, height=3.4, ncols=2)
        i.add(self.c5)
        self.add(i)
        self.s_alpha.valueChanged.connect(self._redraw)
        self._redraw()

        self.add(callout(
            "<b>Measured, for comparison.</b> Corrective torque impulse "
            "0.099 N·m·s/kg for true faults against 0.021 for false alarms "
            "(p = 0.0034) — a factor of about five. That number is the "
            "justification for a sensitive detector, and it is an engineering "
            "measurement, not an argument.", "good"))

        self.finish()

    def _redraw(self):
        alpha = self.s_alpha.value() / 100.0
        self.l_alpha.setText(f"{alpha:.2f}")

        true_ = _trial_cached("ramp ascent", round(alpha, 2), "SE", True)
        false_ = _trial_cached("ramp ascent", 0.0, "SE", True, false_alarm=True)
        norm = _trial_cached("ramp ascent", 0.0, "SE", False)

        self.st_it.set(f"{true_['impulse']:.3f}")
        self.st_if.set(f"{false_['impulse']:.3f}")
        ratio = true_["impulse"] / max(1e-6, false_["impulse"])
        self.st_r.set(f"{ratio:.1f}×")

        c = self.c5
        c.clear()
        a1, a2 = c.axes
        a1.plot(true_["t"], true_["tau_ftm"], color=theme.ACCENT, lw=1.8,
                label="true fault")
        a1.plot(false_["t"], false_["tau_ftm"], color=theme.WARN, lw=1.4,
                label="false alarm")
        a1.axvspan(*true_["fault_window"], color=theme.BAD, alpha=0.12)
        a1.axhline(0, color=theme.BORDER, lw=1.0)
        a1.set_xlabel("time (s)")
        a1.set_ylabel("τ_FTM (N·m)")
        a1.set_title("what the supervisory layer injects")
        c.legend(a1, loc="upper left")

        labels = ["normal", "false alarm", "true fault\n+ FTM"]
        vals = [norm["momentum_nrmse"], false_["momentum_nrmse"],
                true_["momentum_nrmse"]]
        a2.bar(labels, vals, color=[theme.CYAN, theme.WARN, theme.ACCENT])
        a2.set_ylabel("knee momentum N-RMSE")
        a2.set_title("a false alarm is close to normal")
        c.refresh()


# ==========================================================================
# 6 -- compensation
# ==========================================================================

class FaultCompensationPage(Page):
    TITLE = "Compensation Scaled by Severity"
    SUBTITLE = ("Momentum deviation in, additive torque out, held until the end "
                "of the stance sub-state. Not an on-off reflex — a proportional "
                "one.")
    SECTION = SECTION

    def __init__(self, parent=None):
        super().__init__(parent)

        s = Card("the state, and the two model evaluations")
        s.add(math_label(r"x(t)=\begin{bmatrix}H_{Knee}\\ \dot H_{Knee}"
                         r"\end{bmatrix},\qquad "
                         r"\hat x(t)=G_{moment}\!\left(u(t)\right)", 16))
        s.add(body(
            "The compensator's state is the knee's angular momentum and its rate "
            "— and the rate is interpreted as the inertial knee torque, which is "
            "why a single learned map can turn either into an expected FSM torque. "
            "One model predicts the nominal state from the robust input; a second "
            "maps a state to the FSM torque that state implies; the difference "
            "between the two evaluations is commanded."))
        self.add(s)

        a = Card("the application logic, which is gait-aware")
        a.add(body(
            "If a fault is detected inside a stance sub-state (SF or SE), "
            "compensation stays active <b>until the end of that sub-state</b>. At "
            "the boundary it is released if the velocity residual has fallen back "
            "inside the threshold; otherwise it persists through stance.<br><br>"
            "That is a deliberately coarse hold, and it is right for the same "
            "reason the fault window is 200 ms: the mechanical consequence of a "
            "bad impedance setting does not end when the parameter is corrected, "
            "so neither can the correction. Releasing on a phase boundary also "
            "means the layer never fights the FSM's own transitions."))
        self.add(a)

        r = Card("what it bought, measured")
        r.add(body(
            "<b>Knee momentum deviation −47 %</b> with the FTM active versus "
            "without, at the nominal 0.6 m/s condition (with-FTM vs without-FTM "
            "p = 0.0078). Across the other conditions: −30.6 ± 8.3 % at 0.4 m/s, "
            "−17.3 ± 2.1 % at 0.8 m/s, −35.9 ± 1.1 % on a 4.6° ramp — about "
            "−27.6 % overall.<br><br>"
            "<b>Knee phase-variable N-RMSE:</b> 0.14 normal, <b>0.38</b> with FTM, "
            "<b>1.61</b> without. An 11-fold deviation from nominal becomes a "
            "2.7-fold one. The remainder is attributed to the transient that "
            "passes before compensation takes effect — which is the latency "
            "argument again, arriving from a third direction.", dim=True))
        self.add(r)

        i = Card("severity in, compensation out")
        i.add(body(
            "Left: knee momentum against its nominal profile, with and without "
            "the layer. Right: how the corrective impulse and the remaining "
            "deviation scale with fault severity — the property an on-off "
            "corrective action does not have.", dim=True))
        self.mode = QComboBox()
        for k in ft.PARAM_SETS:
            if k != "level ground (nominal)":
                self.mode.addItem(k, k)
        self.mode.currentIndexChanged.connect(self._redraw)
        i.add_layout(labelled("fault mode", self.mode, width=150))
        self.s_alpha = slider(10, 100, 100)
        self.l_alpha = QLabel()
        i.add_layout(slider_row("severity α", self.s_alpha, self.l_alpha))

        self.st_on = Stat("N-RMSE with FTM", "--", theme.ACCENT)
        self.st_off = Stat("without FTM", "--", theme.BAD)
        self.st_red = Stat("reduction", "--", theme.GOOD)
        self.st_imp = Stat("corrective impulse", "--", theme.VIOLET)
        i.add_layout(stat_row(self.st_on, self.st_off, self.st_red, self.st_imp))
        self.c6 = MplCanvas(width=7.4, height=3.4, ncols=2)
        i.add(self.c6)
        self.add(i)
        self.s_alpha.valueChanged.connect(self._redraw)
        self._redraw()

        self.finish()

    def _redraw(self):
        mode = self.mode.currentData()
        alpha = self.s_alpha.value() / 100.0
        self.l_alpha.setText(f"{alpha:.2f}")

        on = _trial_cached(mode, round(alpha, 2), "SE", True)
        off = _trial_cached(mode, round(alpha, 2), "SE", False)
        self.st_on.set(f"{on['momentum_nrmse']:.2f}")
        self.st_off.set(f"{off['momentum_nrmse']:.2f}")
        red = 100 * (1 - on["momentum_nrmse"] / max(1e-9, off["momentum_nrmse"]))
        self.st_red.set(f"{red:.0f}%")
        self.st_red.set_color(theme.GOOD if red > 20 else theme.WARN)
        self.st_imp.set(f"{on['impulse']:.3f}")

        c = self.c6
        c.clear()
        a1, a2 = c.axes
        a1.plot(on["t"], on["H_nom"], color=theme.TEXT_FAINT, lw=1.4, ls="--",
                label="nominal H_knee")
        a1.plot(off["t"], off["H"], color=theme.BAD, lw=1.3, label="fault, no FTM")
        a1.plot(on["t"], on["H"], color=theme.ACCENT, lw=1.7, label="fault + FTM")
        a1.axvspan(*on["fault_window"], color=theme.WARN, alpha=0.15)
        a1.set_xlabel("time (s)")
        a1.set_ylabel("knee momentum (kg·m²/s)")
        c.legend(a1, loc="upper left")

        alphas = np.linspace(0.1, 1.0, 10)
        imps, rem = [], []
        for al in alphas:
            r_on = _trial_cached(mode, round(float(al), 2), "SE", True)
            r_off = _trial_cached(mode, round(float(al), 2), "SE", False)
            imps.append(r_on["impulse"])
            rem.append(r_on["momentum_nrmse"] / max(1e-9, r_off["momentum_nrmse"]))
        a2.plot(alphas, imps, color=theme.VIOLET, lw=2.0,
                label="corrective impulse (N·m·s/kg)")
        a2b = a2.twinx()
        a2b.plot(alphas, rem, color=theme.GOOD, lw=2.0, ls="--",
                 label="remaining deviation (fraction)")
        a2b.tick_params(colors=theme.TEXT_DIM, labelsize=8)
        a2.set_xlabel("fault severity α")
        a2.set_title("scaling, which on-off control does not do")
        c.legend(a2, loc="upper left")
        c.refresh()


# ==========================================================================
# 7 -- estimation
# ==========================================================================

class FaultEstimationPage(Page):
    TITLE = "Gaussian Processes as Observers of Normal"
    SUBTITLE = ("Five minutes of undisturbed walking, three learned maps, and a "
                "prediction that carries its own uncertainty — which is what the "
                "threshold is made of.")
    SECTION = SECTION

    def __init__(self, parent=None):
        super().__init__(parent)

        o = Card("three models, one job each")
        o.add(body(
            "<b>GP Velocity.</b> Robust input → nominal knee angular velocity. "
            "Feeds the detector.<br>"
            "<b>GP Momentum.</b> Robust input → nominal knee momentum and its "
            "derivative. Feeds the compensator's reference state.<br>"
            "<b>GP FSM.</b> Kinetic state → the FSM torque that state implies. "
            "Evaluated twice, at the nominal and the measured state.<br><br>"
            "All three are trained per participant on five minutes of undisturbed "
            "walking, so body-mass distribution and individual gait are already "
            "inside them — no population model, no transfer learning. All three "
            "use a <b>sparse GP with the FITC approximation</b>, which is what "
            "makes an inference affordable inside a 1 ms task."))
        self.add(o)

        w = Card("why a GP and not a physics model")
        w.add(body(
            "Page 20's observer needs a model. For a human-prosthesis system, "
            "that model is genuinely hard: the socket interface, the residual "
            "limb's dynamics and the user's own control vary across people and "
            "across days, and the prior literature that attempted robust "
            "model-based prosthesis control validated it in simulation rather "
            "than in human-in-the-loop walking.<br><br>"
            "A GP sidesteps the model by learning the map from a signal the fault "
            "does not corrupt to the signal it does. And, crucially, it returns a "
            "<b>variance as well as a mean</b> — which is exactly the σ in "
            "T_vel = |μ| + kσ. The detector's threshold is not a tuned constant; "
            "it is the model's own statement about how much this signal normally "
            "varies at this point in the gait cycle."))
        self.add(w)

        self.add(callout(
            "<b>Where the estimate is vulnerable, said plainly in the paper.</b> "
            "Because the whole mechanism is driven by sensor-derived inputs, a "
            "hard sensor failure — a disconnected load cell — impairs the FTM "
            "itself. Fault tolerance at one level needs redundancy at the level "
            "below it. That is the honest boundary of a supervisory layer.",
            "warn"))

        i = Card("the nominal band, and what a fault looks like against it")
        i.add(body(
            "The band is ±kσ around the predicted mean. Widen k and the same "
            "fault takes longer to poke out of it; add sensor noise and the "
            "residual starts touching the band on its own. Both effects are the "
            "detector's two failure directions, visible at once.", dim=True))
        self.s_k = slider(4, 30, 10)
        self.s_noise = slider(0, 40, 5)      # x0.01 rad/s
        self.s_alpha = slider(20, 100, 100)
        self.l_k, self.l_noise, self.l_alpha = QLabel(), QLabel(), QLabel()
        i.add_layout(slider_row("threshold multiplier k", self.s_k, self.l_k))
        i.add_layout(slider_row("sensor noise (×0.01 rad/s)", self.s_noise,
                                self.l_noise))
        i.add_layout(slider_row("fault severity α", self.s_alpha, self.l_alpha))

        self.st_t = Stat("detection time", "--", theme.ACCENT)
        self.st_margin = Stat("residual / threshold", "--", theme.WARN)
        self.st_touch = Stat("noise-only exceedances", "--", theme.BAD)
        i.add_layout(stat_row(self.st_t, self.st_margin, self.st_touch))
        self.c7 = MplCanvas(width=7.4, height=3.4, ncols=2)
        i.add(self.c7)
        self.add(i)
        for s_ in (self.s_k, self.s_noise, self.s_alpha):
            s_.valueChanged.connect(self._redraw)
        self._redraw()

        self.finish()

    def _redraw(self):
        k = self.s_k.value() / 10.0
        noise = self.s_noise.value() / 100.0
        alpha = self.s_alpha.value() / 100.0
        self.l_k.setText(f"{k:.1f}")
        self.l_noise.setText(f"{noise:.2f}")
        self.l_alpha.setText(f"{alpha:.2f}")

        tr = _trial_cached("ramp ascent", round(alpha, 2), "SE", False,
                           k=k, noise=noise)
        clean = _trial_cached("ramp ascent", 0.0, "SE", False, k=k,
                              noise=noise, seed=21)
        self.st_t.set("missed" if tr["detect_ms"] is None
                      else f"{tr['detect_ms']:.0f} ms")
        peak = np.max(np.abs(tr["residual"]) / np.maximum(tr["threshold"], 1e-6))
        self.st_margin.set(f"{peak:.2f}×")
        exceed = np.mean(np.abs(clean["residual"]) > clean["threshold"]) * 100
        self.st_touch.set(f"{exceed:.1f}%")
        self.st_touch.set_color(theme.GOOD if exceed < 2 else theme.BAD)

        c = self.c7
        c.clear()
        a1, a2 = c.axes
        a1.plot(tr["t"], tr["mu"], color=theme.CYAN, lw=1.8,
                label="GP nominal mean")
        a1.fill_between(tr["t"], tr["mu"] - tr["threshold"],
                        tr["mu"] + tr["threshold"], color=theme.CYAN, alpha=0.16,
                        label="±T_vel band")
        a1.plot(tr["t"], tr["omega"], color=theme.BAD, lw=1.0,
                label="measured velocity")
        a1.axvspan(*tr["fault_window"], color=theme.WARN, alpha=0.15)
        a1.set_xlabel("time (s)")
        a1.set_ylabel("rad/s")
        c.legend(a1, loc="upper left")

        a2.plot(clean["t"], clean["residual"], color=theme.TEXT_FAINT, lw=1.0,
                label="undisturbed residual")
        a2.plot(clean["t"], clean["threshold"], color=theme.WARN, lw=1.2,
                ls="--", label="T_vel")
        a2.plot(clean["t"], -clean["threshold"], color=theme.WARN, lw=1.2,
                ls="--")
        a2.set_xlabel("time (s)")
        a2.set_ylabel("rad/s")
        a2.set_title("what the detector sees when nothing is wrong")
        c.legend(a2, loc="upper left")
        c.refresh()


# ==========================================================================
# 8 -- latency
# ==========================================================================

class FaultLatencyPage(Page):
    TITLE = "43 ms or 103 ms: the Whole Result"
    SUBTITLE = ("Every remaining failure in the study was a late detection. That "
                "single sentence is the design specification for the next "
                "version.")
    SECTION = SECTION

    def __init__(self, parent=None):
        super().__init__(parent)

        a = Card("the finding, stated as it deserves")
        a.add(body(
            "Compensation worked when detection landed at <b>43.1 ± 11.5 ms</b>. "
            "The residual perturbations participants still rated Medium or Large "
            "had an average detection delay of <b>103.5 ms</b>. Same controller, "
            "same compensator, same participants — different latency, different "
            "outcome.<br><br>"
            "So the false-alarm rate is not the number to optimise. The paper says "
            "so outright: a modest increase in false alarms is an acceptable "
            "system-level trade if it enables earlier detection, because false "
            "alarms cost a fifth of the corrective impulse and no measurable "
            "instability, while a late detection costs balance."))
        self.add(a)

        b = Card("why latency dominates, in the language of the earlier pages")
        b.add(body(
            "<b>It is a disturbance-rejection problem with a dead time.</b> Page "
            "1: delay is pure phase loss, bounded by nothing. Page 8: a first-order "
            "plant is unconditionally stable under proportional feedback until "
            "delay sells you the missing quarter cycle. Here the delay is not in "
            "the actuator — it is in <i>deciding</i> — and the consequence is the "
            "same shape: the correction arrives after the state it was computed "
            "for has moved on.<br><br>"
            "<b>And the integral of the uncorrected torque error is what moves the "
            "user.</b> A fault let through for 100 ms instead of 40 ms delivers "
            "roughly two and a half times the momentum change to the thigh and "
            "shank, and that momentum is what the margin of stability inherits. "
            "The relationship is not subtle and it is not statistical — it is "
            "integration."))
        self.add(b)

        i = Card("the latency budget, and what each term is worth")
        i.add(body(
            "Build a detection time from its parts and watch the outcome metrics "
            "move. The persistence test and the filter are fixed choices; the "
            "residual growth time is what a better detector attacks.", dim=True))
        self.s_nc = slider(1, 40, 10)
        self.s_grow = slider(5, 120, 35)
        self.s_filt = slider(0, 20, 5)
        self.l_nc, self.l_grow, self.l_filt = QLabel(), QLabel(), QLabel()
        i.add_layout(slider_row("persistence N_c (ms)", self.s_nc, self.l_nc))
        i.add_layout(slider_row("residual growth (ms)", self.s_grow, self.l_grow))
        i.add_layout(slider_row("filter group delay (ms)", self.s_filt,
                                self.l_filt))

        self.st_tot = Stat("total latency", "--", theme.ACCENT)
        self.st_let = Stat("fault let through", "--", theme.BAD)
        self.st_mos = Stat("worst MoS", "--", theme.WARN)
        self.st_cls = Stat("class", "--", theme.GOOD)
        i.add_layout(stat_row(self.st_tot, self.st_let, self.st_mos, self.st_cls))
        self.c8 = MplCanvas(width=7.4, height=3.4, ncols=2)
        i.add(self.c8)
        self.add(i)
        for s_ in (self.s_nc, self.s_grow, self.s_filt):
            s_.valueChanged.connect(self._redraw)
        self._redraw()

        self.add(callout(
            "<b>The engineering conclusion.</b> Spend milliseconds, not "
            "precision. Anything that makes the residual cross threshold sooner — "
            "a better nominal model, a second sensitive signal, a shorter "
            "persistence window with a smarter voting rule — buys outcome "
            "directly. Anything that makes the detector more conservative spends "
            "outcome to buy a metric nobody feels.", "key"))

        self.finish()

    def _redraw(self):
        nc = float(self.s_nc.value())
        grow = float(self.s_grow.value())
        fl = float(self.s_filt.value())
        self.l_nc.setText(f"{nc:.0f} ms")
        self.l_grow.setText(f"{grow:.0f} ms")
        self.l_filt.setText(f"{fl:.0f} ms")

        total = nc + grow + fl
        self.st_tot.set(f"{total:.0f} ms")
        frac = min(1.0, total / ft.DETECTOR["fault_duration_ms"])
        self.st_let.set(f"{frac*100:.0f}%")
        t, mos, win = ft.mos_trace(total, True)
        self.st_mos.set(f"{np.min(mos):.3f} m")
        if total <= 55:
            self.st_cls.set("effective")
            self.st_cls.set_color(theme.GOOD)
        elif total <= 90:
            self.st_cls.set("marginal")
            self.st_cls.set_color(theme.WARN)
        else:
            self.st_cls.set("late")
            self.st_cls.set_color(theme.BAD)

        c = self.c8
        c.clear()
        a1, a2 = c.axes
        parts = ["persistence", "residual growth", "torque filter"]
        vals = [nc, grow, fl]
        a1.barh(parts, vals, color=[theme.VIOLET, theme.BAD, theme.CYAN])
        a1.axvline(ft.RESULTS["detect_effective_ms"], color=theme.GOOD, lw=1.2,
                   ls=":")
        a1.set_xlabel("milliseconds")
        a1.set_title(f"total {total:.0f} ms of the 200 ms window")

        lat = np.linspace(10, 200, 80)
        worst = [np.min(ft.mos_trace(L, True)[1]) for L in lat]
        a2.plot(lat, worst, color=theme.ACCENT, lw=2.0)
        a2.axvspan(0, 55, color=theme.GOOD, alpha=0.12)
        a2.axvspan(90, 200, color=theme.BAD, alpha=0.12)
        a2.plot([total], [np.min(mos)], "o", color=theme.WARN, ms=9)
        a2.set_xlabel("detection latency (ms)")
        a2.set_ylabel("worst margin of stability (m)")
        a2.set_title("green = the study's effective band")
        c.refresh()


# ==========================================================================
# 9 -- capstone
# ==========================================================================

class FaultResultsPage(Page):
    TITLE = "Capstone: What Eight Participants Showed"
    SUBTITLE = ("Handrail touches, perceived severity, phase portraits and "
                "margin of stability — four metrics, one direction, and a "
                "carefully bounded claim.")
    SECTION = SECTION

    def __init__(self, parent=None):
        super().__init__(parent)

        p = Card("the experiment")
        p.add(body(
            "Eight participants: five non-disabled using a bypass adapter, three "
            "with unilateral transfemoral amputation (K3–K4, daily prosthesis "
            "users). Five familiarisation sessions with a certified prosthetist, "
            "then five minutes of undisturbed walking to train the models, then "
            "eight trials of 2–3 minutes at 0.6 m/s. <b>Ten perturbations per "
            "trial — five with the FTM, five without</b> — with both the timing "
            "and the FTM state randomised and the participant blind to both. "
            "Ceiling harness and handrails available. A control trial with no "
            "induced errors produced no handrail use and no reported disturbance, "
            "which is the check that makes the rest interpretable."))
        self.add(p)

        self.add(_quoted(
            "<b>Detection.</b> 100 % sensitivity; FAR 10.8 ± 10.0 %; "
            "54.4 ± 28.7 ms.<br>"
            "<b>Mechanics.</b> knee momentum deviation −47 % (with vs without, "
            "p = 0.0078); phase-variable N-RMSE 0.14 / 0.38 / 1.61 for normal / "
            "with / without; margin-of-stability deviation −46 %, with-FTM "
            "statistically indistinguishable from normal (p = 0.062, d = 0.74) "
            "while without-FTM differed strongly (d = 1.72 vs normal).<br>"
            "<b>User level.</b> handrail touches down by 15 on average "
            "(Wilcoxon Z = 2.41, p = 0.016, d = 1.12); handrail assistance needed "
            "in 50 % of fault events without the FTM against 10 % with it; "
            "perceived 'Critical' perturbations fell from <b>87 ± 9 %</b> to "
            "<b>15 ± 11 %</b>, about 30 fewer per participant.<br>"
            "<b>Other conditions</b> (0.4 m/s, 0.8 m/s, 4.6° ramp, two "
            "participants): momentum deviation down ≈28 %, handrail use down in "
            "every condition."))

        r = Card("reading it")
        r.add(body(
            "<b>The engineering metric and the human metric agree, and that is "
            "the finding.</b> A 47 % reduction in the regulated variable shows up "
            "as a 46 % reduction in a balance metric, a 2.7-fold rather than "
            "11-fold deviation in joint dynamics, and an 87 %→15 % collapse in "
            "how often the wearer felt something serious. Four independent "
            "measurement channels, one mechanism.<br><br>"
            "<b>It is a compensation layer, not a fault-elimination system.</b> "
            "The paper is explicit: the FTM belongs inside a multi-layer safety "
            "architecture alongside algorithmic safeguards at the classification "
            "level, sensor redundancy, user-facing transparency for anticipatory "
            "strategies, and design-level robustness. Nothing here prevents "
            "faults; it reacts to them.<br><br>"
            "<b>What is not established.</b> n = 8, treadmill only, one baseline "
            "controller (FSM impedance), one fault family (impedance-parameter "
            "misclassification), fixed error direction and FSM state within a "
            "trial, and no comparable prior method to benchmark against — the "
            "comparison in the paper is qualitative for that reason."))
        self.add(r)

        i = Card("the four channels, side by side")
        i.add(body(
            "All bars are published values. The right panel is the teaching "
            "model's phase portrait for the same three conditions, which is what "
            "the N-RMSE numbers are measuring the spread of.", dim=True))
        self.mode = QComboBox()
        for k in ft.PARAM_SETS:
            if k != "level ground (nominal)":
                self.mode.addItem(k, k)
        self.mode.currentIndexChanged.connect(self._redraw)
        i.add_layout(labelled("fault mode shown", self.mode, width=150))
        self.c9 = MplCanvas(width=7.4, height=3.6, ncols=2)
        i.add(self.c9)
        self.add(i)
        self._redraw()

        n = Card("what the next version has to do")
        n.add(body(
            "<b>Detect sooner.</b> Named in the paper as the refinement that "
            "matters: the thresholding strategy is what produced the delayed "
            "detections, and delayed detections produced every residual failure."
            "<br><br>"
            "<b>Cover the detector's own inputs.</b> Sensor redundancy on the "
            "load cell, because the supervisory layer cannot supervise its own "
            "blindness.<br><br>"
            "<b>Generalise the baseline.</b> The additive-torque interface is "
            "designed to be controller-agnostic; validating it on continuous-phase "
            "and EMG-driven controllers is the stated next step.<br><br>"
            "<b>Harder fault conditions.</b> Heterogeneous within-trial errors, "
            "so adaptation cannot help the participant, and fault families beyond "
            "impedance-parameter mismatch."))
        self.add(n)

        self.add(callout(
            "<b>What the two project sections share.</b> Both take one "
            "well-chosen physical quantity — frontal-plane whole-body momentum, "
            "knee angular momentum — and regulate it with a small, bounded, "
            "deliberately partial torque, on top of a control structure that "
            "keeps working when the new layer does nothing. Both pick a signal "
            "the disturbance cannot corrupt as their reference and a signal it "
            "moves immediately as their trigger. And in both, the number that "
            "decides success is a latency, not a gain.", "good"))

        self.finish()

    def _redraw(self):
        mode = self.mode.currentData()
        on = _trial_cached(mode, 1.0, "SE", True)
        off = _trial_cached(mode, 1.0, "SE", False)
        norm = _trial_cached(mode, 0.0, "SE", False)

        c = self.c9
        c.clear()
        a1, a2 = c.axes
        labels = ["momentum\ndeviation", "MoS\ndeviation", "critical\nperceived",
                  "handrail\nevents"]
        without = [100, 100, ft.RESULTS["critical_without_pct"][0], 100]
        with_ = [100 - ft.RESULTS["momentum_reduction_pct"],
                 100 - ft.RESULTS["mos_reduction_pct"],
                 ft.RESULTS["critical_with_pct"][0], 20]
        x = np.arange(len(labels))
        a1.bar(x - 0.18, without, width=0.34, color=theme.BAD, label="without FTM")
        a1.bar(x + 0.18, with_, width=0.34, color=theme.ACCENT, label="with FTM")
        a1.set_xticks(x)
        a1.set_xticklabels(labels, fontsize=8)
        a1.set_ylabel("relative to without-FTM (%)")
        a1.set_title("published outcomes, normalised")
        c.legend(a1, loc="upper right")

        for tr, lab, col in ((norm, "normal", theme.CYAN),
                             (off, "fault, no FTM", theme.BAD),
                             (on, "fault + FTM", theme.ACCENT)):
            a2.plot(np.degrees(tr["theta"]), tr["omega"], color=col, lw=1.3,
                    label=lab)
        a2.set_xlabel("knee angle (deg)")
        a2.set_ylabel("knee velocity (rad/s)")
        a2.set_title("phase portrait (teaching model)")
        c.legend(a2, loc="lower right")
        c.refresh()
