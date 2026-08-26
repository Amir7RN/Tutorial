"""
Capstone pages -- two robots, three checkpoints each.

The tutor's blocks each end with a pair of pages that take everything just
established and spend it on one specific machine:

    after linear systems + controller design
        Biped I       six joints, three unstable eigenvalues, one deadline
                      per joint, and the input bound nobody can tune away
        Arm I         a MIMO plant whose A matrix moves when the elbow does,
                      and gravity as a spring that changes sign

    after the actuator block
        Biped II      what to put in each of the six joints, and why the
                      answer is different at the ankle and the hip
        Arm II        the same question with the opposite inertia ordering
                      and a payload that changes everything downstream

    after the control paradigms
        Biped III     which controller for which joint, in which gait phase
        Arm III       which controller for which task, with contact as the
                      thing that decides

The two robots are fixed throughout so the answers can be compared:

    BIPED    trunkless, 2 legs x (ankle, knee, hip) = 6 actuators, 30 kg
    ARM      shoulder, elbow, wrist manipulator, 0.65 m reach, 2 kg payload

Nothing here introduces new theory. Every page is a decision table with the
reasoning attached, and an interactive that lets the decision be wrong so
you can see what wrong looks like.
"""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QLabel, QTableWidget, QTableWidgetItem

from ctrlcore.actuators import (
    j_eff,
    reflected_inertia,
    sea_resonance_rad_s,
)
from ctrlcore.linear import lqr
from ctrlcore.multibody import (
    G,
    PlanarLeg,
    TwoLink,
    bryson,
    capture_point,
    leg_ss,
    lipm_omega,
    lipm_ss,
    lqr_design,
    simulate_feedback,
    two_link_ss,
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

SEC_SYS = "Capstone · Systems"
SEC_ACT = "Capstone · Actuators"
SEC_CTRL = "Capstone · Control"

# The two machines, defined once.
BIPED = dict(mass=30.0, z_com=0.75, foot=0.20, joints=("ankle", "knee", "hip"))
ARM = dict(reach=0.65, payload=2.0, joints=("shoulder", "elbow", "wrist"))


def _tbl(headers, rows, col0=130, colw=250, height=None):
    t = QTableWidget(len(rows), len(headers))
    t.setHorizontalHeaderLabels(headers)
    for r, cells in enumerate(rows):
        for c, v in enumerate(cells):
            it = QTableWidgetItem(v)
            it.setFlags(Qt.ItemIsEnabled)
            if c == 0:
                f = it.font()
                f.setBold(True)
                it.setFont(f)
            t.setItem(r, c, it)
    t.verticalHeader().setVisible(False)
    t.setWordWrap(True)
    t.resizeRowsToContents()
    t.setColumnWidth(0, col0)
    for c in range(1, len(headers)):
        t.setColumnWidth(c, colw)
    t.setMinimumHeight(height or (44 + 66 * len(rows)))
    return t


def _spec_card(which: str) -> Card:
    """The machine, restated at the top of every capstone page."""
    if which == "biped":
        c = Card("the machine: a trunkless biped")
        c.add(body(
            "<b>Two legs, no trunk, six actuators.</b> Ankle, knee and hip on "
            "each side, all in the sagittal plane for the purposes of these "
            "pages. 30 kg, centre of mass 0.75 m up when standing, feet "
            "0.20 m long. No arms, so no angular momentum to throw around — "
            "the only way to stay upright is where the feet are and what the "
            "ankles do."))
        c.add(body(
            "<table cellpadding='6'>"
            "<tr><td><b>Joint</b></td><td><b>Carries</b></td>"
            "<td><b>Peak torque</b></td><td><b>Range</b></td>"
            "<td><b>Speed</b></td></tr>"
            "<tr><td>ankle</td><td>the entire body above it</td>"
            "<td>~90 N·m</td><td>−20° … +25°</td><td>modest</td></tr>"
            "<tr><td>knee</td><td>trunk + thigh</td><td>~120 N·m</td>"
            "<td>0° … 110°</td><td>high in swing</td></tr>"
            "<tr><td>hip</td><td>the leg it is swinging</td><td>~80 N·m</td>"
            "<td>−25° … +90°</td><td>highest</td></tr>"
            "</table>"))
        return c
    c = Card("the machine: a three-joint manipulator")
    c.add(body(
        "<b>Shoulder, elbow, wrist.</b> 0.65 m reach, 2 kg payload, mounted "
        "on a fixed base. Everything is bolted down, so unlike the biped "
        "there is no danger of falling over — and everything it does happens "
        "at the end of a chain, so unlike the biped the errors "
        "<b>accumulate outward</b>."))
    c.add(body(
        "<table cellpadding='6'>"
        "<tr><td><b>Joint</b></td><td><b>Carries</b></td>"
        "<td><b>Peak torque</b></td><td><b>What it decides</b></td></tr>"
        "<tr><td>shoulder</td><td>both links + payload, at full reach</td>"
        "<td>~45 N·m</td><td>gross position; dominates gravity load</td></tr>"
        "<tr><td>elbow</td><td>forearm + payload</td><td>~20 N·m</td>"
        "<td>reach; and it sets the shoulder's inertia</td></tr>"
        "<tr><td>wrist</td><td>payload only</td><td>~4 N·m</td>"
        "<td>orientation, and all the fine contact work</td></tr>"
        "</table>"))
    return c


# ==========================================================================
# CAPSTONE 1A -- biped, systems and stability
# ==========================================================================

class BipedSystemsPage(Page):
    TITLE = "Biped I — Poles, Deadlines and the Foot"
    SUBTITLE = ("Everything from first order through LQR, spent on six "
                "joints that are all trying to fall over.")
    SECTION = SEC_SYS
    NOTES = "capstone"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(_spec_card("biped"))

        self.add(callout(
            "<b>One fact organises this entire page.</b> Every joint of a "
            "standing leg is an inverted pendulum, so the gravity term enters "
            "with the <i>wrong sign</i> — it pushes the joint further from "
            "upright, not back toward it. In state-space terms the A matrix "
            "has right-half-plane eigenvalues, one per joint, and each one is "
            "a <b>deadline</b>. Nothing on this page is a tuning question "
            "until those deadlines are met.", "key"))

        # ---- the eigenvalues -------------------------------------------
        ev = Card("six states, three unstable eigenvalues, three clocks")
        ev.add(body(
            "Linearise one stance leg about upright. Three joints, three "
            "angles and three rates, so six states and a 6×6 A. Its "
            "eigenvalues come in pairs ±p<sub>i</sub>, and the positive one "
            "of each pair is the rate at which that joint collapses if you "
            "stop pushing."))
        ev.add(math_label(r"p_i = \sqrt{\frac{m g z_i}{J_i}} \qquad "
                          r"t_{\text{double}} = \frac{\ln 2}{p_i}", 17))
        ev.add(body(
            "<b>Read the fraction.</b> The numerator is how hard gravity "
            "pulls this joint over; the denominator is how much inertia "
            "resists. So the ankle — carrying the whole body on a small "
            "effective inertia lever — diverges fastest, and the hip, "
            "swinging one leg, diverges slowest. <b>The joint with the "
            "hardest control problem is the one at the bottom</b>, which is "
            "the exact reverse of the manipulator on the next page."))
        ev.add(callout(
            "<b>And now the rule from the Stabilising page, applied six "
            "times.</b> Crossover must clear 2p, and 5–10p is what gets "
            "built. Page 1 caps crossover at roughly f<sub>s</sub>/15. Put "
            "those together and <b>the sample rate for the whole robot is set "
            "by its worst joint</b>, not by an average. That is why balance "
            "controllers run in the kHz while the gait planner above them is "
            "happy at 100 Hz — they are answering to different "
            "eigenvalues.", "key"))
        ev.add(body(
            "Two things this does <i>not</i> say, because they are the usual "
            "over-readings. It does not say the leg is uncontrollable — it is "
            "perfectly controllable, and the interactive below places all six "
            "poles. And it does not say a stiffer joint is better: raising "
            "J<sub>i</sub> lowers p<sub>i</sub> and buys you time, which is "
            "the real reason heavy feet and long feet make balancing easier "
            "and why toddlers and robots both benefit from big shoes.",
            dim=True))
        self.add(ev)

        i1 = Card("place all six poles, then take the sample rate away")
        i1.add(body(
            "<b>Left:</b> the open-loop eigenvalues of the stance leg — note "
            "the three sitting in the red half. <b>Middle:</b> the three "
            "joints recovering from a 5° lean under LQR. <b>Right:</b> each "
            "joint's doubling time against the response time your loop rate "
            "buys.<br><br>"
            "<b>Three things to do:</b><br>"
            "&nbsp;&nbsp;<b>1.</b> Drop the loop rate. Watch the ankle bar "
            "cross first — it always does, and it is the joint that decides "
            "your CPU budget.<br>"
            "&nbsp;&nbsp;<b>2.</b> Raise the body mass without changing "
            "anything else. Every p grows as √m, so a heavier robot is a "
            "<b>faster</b> problem, and the actuator sizing you did for the "
            "lighter one is now a timing problem as well as a torque "
            "one.<br>"
            "&nbsp;&nbsp;<b>3.</b> Tighten the torque budget until the "
            "saturation stat lights up. The poles stay exactly where LQR put "
            "them and the robot still falls, which is the whole lesson of the "
            "state-feedback page arriving on a real machine.", dim=True))
        self.s_mass = slider(100, 900, 300)      # x0.1 kg
        self.s_zc = slider(40, 120, 75)          # x0.01 m
        self.s_fs = slider(50, 3000, 500)        # Hz
        self.s_tmax = slider(10, 400, 150)       # N m
        self.l_mass, self.l_zc = QLabel(), QLabel()
        self.l_fs, self.l_tmax = QLabel(), QLabel()
        i1.add_layout(slider_row("body mass (×0.1 kg)", self.s_mass,
                                 self.l_mass))
        i1.add_layout(slider_row("CoM height (cm)", self.s_zc, self.l_zc))
        i1.add_layout(slider_row("loop rate f_s (Hz)", self.s_fs, self.l_fs))
        i1.add_layout(slider_row("torque limit (N·m)", self.s_tmax,
                                 self.l_tmax))
        self.st_pa = Stat("ankle p", "--", theme.BAD)
        self.st_pk = Stat("knee p", "--", theme.WARN)
        self.st_ph = Stat("hip p", "--", theme.VIOLET)
        self.st_wgc = Stat("crossover available", "--", theme.ACCENT)
        self.st_verdict = Stat("verdict", "--", theme.GOOD)
        i1.add_layout(stat_row(self.st_pa, self.st_pk, self.st_ph,
                               self.st_wgc, self.st_verdict))
        self.c1 = MplCanvas(width=7.6, height=2.9, ncols=3)
        i1.add(self.c1)
        self.t1 = body("", dim=True)
        i1.add(self.t1)
        self.add(i1)
        for s in (self.s_mass, self.s_zc, self.s_fs, self.s_tmax):
            s.valueChanged.connect(self._redraw_leg)
        self._redraw_leg()

        # ---- the foot ---------------------------------------------------
        self.add(hline())
        self.add(title("The one constraint no controller negotiates with: "
                       "the foot"))

        ft = Card("the input is bounded by geometry, not by the motor")
        ft.add(body(
            "Collapse the whole robot to its centre of mass and you get the "
            "linear inverted pendulum, which is the model every balance "
            "controller is really running:"))
        ft.add(math_label(r"\ddot x = \omega^2 (x - p), \qquad "
                          r"\omega = \sqrt{g/z}", 18))
        ft.add(body(
            "x is the CoM position and <b>p — the centre of pressure — is the "
            "input</b>. Now read what kind of input that is. It is not a "
            "torque, it is a <i>place under the foot where the ground pushes "
            "back</i>. The ground can only push, never pull, so p is confined "
            "to the support polygon:<br><br>"
            "&nbsp;&nbsp;&nbsp;&nbsp;<b>|p| ≤ foot length / 2</b><br><br>"
            "That is a hard saturation on the only input, and it comes from a "
            "tape measure. Ankle torque is exactly τ = −m g p, so "
            "\"maximum ankle torque\" and \"the CoP at the toe\" are the same "
            "sentence — and buying a stronger ankle motor past that point "
            "buys nothing at all, because the foot lifts."))
        ft.add(callout(
            "<b>The capture point, and why it is the most useful number in "
            "legged robotics.</b> Take the LIPM's unstable eigenvector and "
            "give its coordinate a name:<br><br>"
            "&nbsp;&nbsp;&nbsp;&nbsp;<b>ξ = x + ẋ/ω</b><br><br>"
            "ξ is where you would have to put the CoP to bring the CoM "
            "exactly to rest. It is the one combination of position and "
            "velocity that <i>grows</i>, cleanly separated from the "
            "combination that decays — which is precisely what an "
            "eigenvector is for.<br><br>"
            "&nbsp;&nbsp;• <b>ξ inside the foot</b> → you can stop with "
            "ankles alone. Stand still.<br>"
            "&nbsp;&nbsp;• <b>ξ outside the foot</b> → no ankle torque "
            "whatsoever will stop you. <b>You must step, and the step goes "
            "to ξ.</b><br><br>"
            "That verdict is geometry plus one eigenvalue. It contains no "
            "gains, and it is why \"balance\" and \"where to step\" are the "
            "same question rather than two.", "key"))
        self.add(ft)

        i2 = Card("push the robot and watch the capture point leave the foot")
        i2.add(body(
            "A shove gives the CoM a velocity at t = 0. <b>Left:</b> the CoM "
            "and the capture point over time, with the foot drawn as a band. "
            "<b>Right:</b> the required CoP against what the foot can "
            "deliver.<br><br>"
            "<b>Three things to do:</b><br>"
            "&nbsp;&nbsp;<b>1.</b> Small push: ξ stays in the band, the CoP "
            "stays inside the foot, ankles handle it.<br>"
            "&nbsp;&nbsp;<b>2.</b> Bigger push: ξ leaves the band. The "
            "controller now demands a CoP outside the foot, the foot rolls "
            "onto its toe, and the demand is simply not met. <b>Read the step "
            "distance the stat gives you</b> — that is where the foot has to "
            "land, and it is computed without any controller at "
            "all.<br>"
            "&nbsp;&nbsp;<b>3.</b> Lengthen the foot. The band widens and the "
            "same push becomes survivable. This is why robots that must not "
            "step have big feet, and why a robot that steps well can afford "
            "small ones.", dim=True))
        self.s_push = slider(0, 200, 30)         # x0.01 m/s
        self.s_foot = slider(8, 40, 20)          # cm
        self.s_zc2 = slider(40, 120, 75)         # cm
        self.l_push, self.l_foot, self.l_zc2 = QLabel(), QLabel(), QLabel()
        i2.add_layout(slider_row("push (×0.01 m/s)", self.s_push, self.l_push))
        i2.add_layout(slider_row("foot length (cm)", self.s_foot, self.l_foot))
        i2.add_layout(slider_row("CoM height (cm)", self.s_zc2, self.l_zc2))
        self.st_omega = Stat("ω = √(g/z)", "--", theme.CYAN)
        self.st_xi = Stat("capture point ξ", "--", theme.ACCENT)
        self.st_edge = Stat("foot half-length", "--", theme.WARN)
        self.st_step = Stat("must step?", "--", theme.GOOD)
        self.st_tau = Stat("max ankle torque", "--", theme.VIOLET)
        i2.add_layout(stat_row(self.st_omega, self.st_xi, self.st_edge,
                               self.st_step, self.st_tau))
        self.c2 = MplCanvas(width=7.6, height=2.8, ncols=2)
        i2.add(self.c2)
        self.t2 = body("", dim=True)
        i2.add(self.t2)
        self.add(i2)
        for s in (self.s_push, self.s_foot, self.s_zc2):
            s.valueChanged.connect(self._redraw_lipm)
        self._redraw_lipm()

        # ---- what each earlier page bought ------------------------------
        self.add(hline())
        self.add(title("What each earlier idea is actually for, on this "
                       "robot"))
        self.add(_tbl(
            ["Idea", "On the biped", "The number it produces"],
            [("first order, τ",
              "the current loop inside each motor, and the low-pass on every "
              "IMU channel",
              "τ_elec ≈ 0.2 ms; anything slower than ~10τ is a lie"),
             ("second order, ζ",
              "every joint under PD, and the whole body under the ankle "
              "strategy",
              "ζ ≈ 0.7 at each joint; below 0.4 the leg visibly wobbles"),
             ("poles / s-plane",
              "the six eigenvalues above; three are in the right half plane "
              "and stay there until feedback moves them",
              "p_ankle ≈ 8 1/s → 87 ms doubling"),
             ("phase margin",
              "the honest measure of how much delay the balance loop can "
              "absorb before it oscillates",
              "PM ≥ 45°; each 1 ms of extra latency costs PM at ω_gc"),
             ("Bode / crossover",
              "where the loop stops having authority, and therefore where "
              "the robot stops being controlled",
              "ω_gc > 5p ≈ 40 rad/s minimum"),
             ("Nyquist",
              "the one that matters here, because an unstable plant does not "
              "obey the naive margin rules — the encirclement count is the "
              "actual stability test",
              "N = P: one encirclement required per RHP pole"),
             ("zeros / non-minimum phase",
              "the wrong-way step: to move the CoM left, first push the CoP "
              "right. A genuine RHP zero in the CoM-to-CoP path",
              "bandwidth capped near the zero, regardless of gain"),
             ("root locus / PD",
              "the joint-level servo underneath everything else",
              "K_p, K_d per joint, and the D term is not optional"),
             ("lead-lag",
              "buying phase back at crossover after the delay budget has "
              "eaten it",
              "one lead section ≈ +40° at ω_gc, ×6 noise gain"),
             ("state feedback",
              "the only formulation in which 'the knee is bending because "
              "the ankle moved' is expressible",
              "one 3×6 gain matrix instead of three PD loops"),
             ("LQR",
              "how those 18 numbers get chosen: weight ankle angle hard, hip "
              "angle loosely, and torque by what the motors have",
              "Q, R from tolerances; poles land where they land")],
            col0=150, colw=270, height=740))

        self.add(callout(
            "<b>The through-line.</b> A biped is an unstable MIMO plant with "
            "a hard input constraint and a non-minimum-phase path from the "
            "thing you command to the thing you care about. Every one of "
            "those three words was a page earlier in this tutor, and the "
            "reason balance is hard is that it is all three at "
            "once — not because the controller is exotic. The controller is "
            "usually LQR or PD.", "good"))
        self.finish()

    # ------------------------------------------------------------------
    def _redraw_leg(self):
        m = self.s_mass.value() / 10.0
        z = self.s_zc.value() / 100.0
        fs = float(self.s_fs.value())
        tmax = float(self.s_tmax.value())
        self.l_mass.setText(f"{m:.1f} kg")
        self.l_zc.setText(f"{z*100:.0f} cm")
        self.l_fs.setText(f"{fs:.0f} Hz")
        self.l_tmax.setText(f"{tmax:.0f} N·m")

        leg = PlanarLeg(body_mass=m, z_com=z)
        ss = leg_ss(leg)
        eig = np.linalg.eigvals(np.asarray(ss.A))
        pos = sorted([v.real for v in eig if v.real > 1e-9], reverse=True)
        while len(pos) < 3:
            pos.append(0.0)
        p_a, p_k, p_h = pos[0], pos[1], pos[2]
        wgc = 2.0 * math.pi * (fs / 15.0)
        ratio = wgc / max(p_a, 1e-9)

        self.st_pa.set(f"{p_a:.1f} 1/s")
        self.st_pk.set(f"{p_k:.1f} 1/s")
        self.st_ph.set(f"{p_h:.1f} 1/s")
        self.st_wgc.set(f"{wgc:.0f} rad/s")
        ok, comfy = ratio >= 2.0, ratio >= 5.0
        self.st_verdict.set("comfortable" if comfy else
                            ("marginal" if ok else "IMPOSSIBLE"))
        self.st_verdict.set_color(theme.GOOD if comfy else
                                  (theme.WARN if ok else theme.BAD))

        Q = bryson([0.05, 0.08, 0.15, 0.5, 0.8, 1.5])
        R = bryson([tmax, tmax, tmax])
        res = lqr_design(ss, Q, R, x0=np.array([0.09, 0.0, 0.0, 0, 0, 0]))
        ts, xs, us, sat = simulate_feedback(
            ss, res.K, [0.09, 0.0, 0.0, 0, 0, 0], dur=1.5, dt=5e-4,
            u_max=tmax)

        if sat > 1e-9:
            self.t1.setText(
                f"<b>Torque saturating on {sat*100:.0f}% of ticks.</b> LQR "
                f"placed the poles where its cost said, and the motor cannot "
                f"deliver the gains those poles require. The trace in the "
                f"middle panel is not the closed loop you designed — while u "
                f"is clipped the leg is running open loop against three "
                f"right-half-plane eigenvalues. Raise the torque limit or "
                "accept a slower response by making R more expensive.")
        elif not ok:
            self.t1.setText(
                f"<b>No controller exists at {fs:.0f} Hz.</b> The ankle "
                f"doubles its lean every {math.log(2)/max(p_a,1e-9)*1000:.0f} "
                f"ms and this loop rate buys {wgc:.0f} rad/s of crossover, "
                f"under the 2p = {2*p_a:.0f} floor. Nothing inside the "
                "controller closes that gap — not LQR, not a network, not a "
                "better gain. Raise f_s, or make the robot slower by adding "
                "inertia or height.")
        else:
            self.t1.setText(
                f"<b>ω_gc/p = {ratio:.1f} at the ankle</b>, which is the "
                f"joint that sets the budget: it always diverges fastest, "
                f"because it carries the whole body. Knee and hip have "
                f"{p_a/max(p_k,1e-9):.1f}× and {p_a/max(p_h,1e-9):.1f}× more "
                f"time. Note that raising the mass makes every p grow as √m — "
                "a heavier robot is not just a stronger-motor problem, it is "
                "a faster-loop problem.")

        c = self.c1
        c.clear()
        a1, a2, a3 = c.axes
        _splane(a1, [complex(v) for v in eig], lim=max(12.0, p_a * 1.6),
                marker_label="open loop")
        a1.scatter([p.real for p in res.poles], [p.imag for p in res.poles],
                   marker="o", s=32, color=theme.GOOD, zorder=6,
                   label="after LQR")
        a1.set_title("three poles in the red half", fontsize=8.5)
        c.legend(a1, loc="upper left")

        names = ["ankle", "knee", "hip"]
        cols = [theme.BAD, theme.WARN, theme.VIOLET]
        for j in range(3):
            a2.plot(ts, np.degrees(xs[:, j]), color=cols[j], lw=1.8,
                    label=names[j])
        a2.axhline(0, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a2.set_xlabel("time (s)")
        a2.set_ylabel("joint angle (°)")
        a2.set_title("recovering from a 5° lean", fontsize=8.5)
        c.legend(a2, loc="upper right")

        dbl = [math.log(2) / max(p, 1e-9) * 1000 for p in (p_a, p_k, p_h)]
        loop = 1000.0 / wgc
        a3.barh([0, 1, 2], dbl, height=0.5, color=cols, alpha=0.8)
        a3.axvline(loop, color=theme.ACCENT, lw=1.8,
                   label=f"loop responds in {loop:.0f} ms")
        a3.set_yticks([0, 1, 2])
        a3.set_yticklabels(names, fontsize=8)
        a3.set_xlabel("doubling time (ms)")
        a3.set_title("who has the least time", fontsize=8.5)
        c.legend(a3, loc="lower right")
        c.refresh()

    # ------------------------------------------------------------------
    def _redraw_lipm(self):
        v = self.s_push.value() / 100.0
        foot = self.s_foot.value() / 100.0
        z = self.s_zc2.value() / 100.0
        self.l_push.setText(f"{v:.2f} m/s")
        self.l_foot.setText(f"{foot*100:.0f} cm")
        self.l_zc2.setText(f"{z*100:.0f} cm")

        w = lipm_omega(z)
        half = foot / 2.0
        xi = capture_point(0.0, v, z)
        m = BIPED["mass"]
        must_step = xi > half

        self.st_omega.set(f"{w:.2f} 1/s")
        self.st_xi.set(f"{xi*100:.1f} cm")
        self.st_edge.set(f"±{half*100:.0f} cm")
        self.st_step.set(f"yes — step {xi*100:.0f} cm" if must_step
                         else "no — ankles suffice")
        self.st_step.set_color(theme.BAD if must_step else theme.GOOD)
        self.st_tau.set(f"{m*G*half:.0f} N·m")

        # The CoP is SATURATED at the foot edge, because the ground cannot
        # push outside the support polygon. That saturation is the whole
        # point of the panel: it is a constraint on the input, not a limit
        # of the motor, and it is why big pushes end in a step.
        ss = lipm_ss(z)
        K = lqr(np.asarray(ss.A), np.asarray(ss.B),
                np.diag([40.0, 8.0]), np.array([[1.0]]))
        ts, xs, us, sat = simulate_feedback(ss, K, [0.0, v], dur=2.0,
                                            dt=1e-3, u_max=half)
        xis = xs[:, 0] + xs[:, 1] / w
        fell = bool(len(xs)) and abs(xs[-1, 0]) > 3.0 * max(half, 1e-6)

        if must_step:
            self.t2.setText(
                f"<b>ξ = {xi*100:.1f} cm, and the foot only reaches "
                f"{half*100:.0f} cm.</b> The CoP saturates at the toe — look "
                f"at the flat top on the right panel — and the CoM keeps "
                f"going, because the ground cannot push from outside the "
                f"foot. No ankle torque stops this; the foot would have to "
                f"pull. <b>The robot must step, and the step target is ξ "
                f"itself: {xi*100:.0f} cm ahead.</b> Notice this was decided "
                f"by a tape measure and one eigenvalue, with no controller "
                "involved. A trunkless biped has no arms to throw, so "
                "stepping is the only other option it has.")
        else:
            self.t2.setText(
                f"<b>ξ = {xi*100:.1f} cm, inside the {half*100:.0f} cm "
                f"foot.</b> The ankle strategy is sufficient: the CoP shifts "
                f"forward, stays within the support polygon, the CoM "
                f"decelerates and the robot stands still. Peak ankle torque "
                f"{m*G*float(np.max(np.abs(us))):.0f} N·m against the "
                f"{m*G*half:.0f} N·m the geometry allows"
                f"{' — and the CoP is already pinned at the toe for part of the recovery' if sat > 1e-9 else ''}"
                ". Push harder and watch the margin close: the failure is "
                "geometric, and it arrives long before the motor runs out.")

        c = self.c2
        c.clear()
        a1, a2 = c.axes
        a1.axhspan(-half * 100, half * 100, color=theme.GOOD, alpha=0.12,
                   label="support polygon")
        a1.plot(ts, xs[:, 0] * 100, color=theme.ACCENT, lw=2.0, label="CoM x")
        a1.plot(ts, xis * 100, color=theme.PINK, lw=1.9, ls="--",
                label="capture point ξ")
        a1.axhline(0, color=theme.TEXT_FAINT, lw=1.0, ls=":")
        a1.set_xlabel("time (s)")
        a1.set_ylabel("position (cm)")
        a1.set_ylim(-half * 250, max(half * 250, xi * 160, 8.0))
        a1.set_title("pushed at t = 0" + ("  —  FALLING" if fell else ""),
                     fontsize=9)
        c.legend(a1, loc="upper left")

        a2.plot(ts, us[:, 0] * 100, color=theme.VIOLET, lw=2.0,
                label="CoP applied")
        a2.axhline(half * 100, color=theme.BAD, lw=1.5, ls="--",
                   label="toe / heel — hard limit")
        a2.axhline(-half * 100, color=theme.BAD, lw=1.5, ls="--")
        a2.set_ylim(-half * 190, half * 190)
        a2.set_xlabel("time (s)")
        a2.set_ylabel("CoP (cm)")
        a2.set_title("the input the ground can give", fontsize=9)
        c.legend(a2, loc="lower right")
        c.refresh()


# ==========================================================================
# CAPSTONE 1B -- arm, systems and stability
# ==========================================================================

class ArmSystemsPage(Page):
    TITLE = "Arm I — Coupling, Configuration and Gravity"
    SUBTITLE = ("A stable plant whose A matrix changes when you move it, and "
                "a gravity term that is a spring with a sign you do not "
                "control.")
    SECTION = SEC_SYS
    NOTES = "capstone"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(_spec_card("arm"))

        self.add(callout(
            "<b>The arm is the easy robot and the hard plant.</b> It cannot "
            "fall over — bolt the base down and every eigenvalue is either "
            "stable or marginal — so none of the deadline arithmetic from the "
            "biped page applies. What replaces it is worse in a different "
            "way: <b>the plant is not one plant</b>. Fold the elbow and the "
            "shoulder's inertia drops by a factor of three; swing to "
            "horizontal and gravity turns from a restoring spring into a "
            "destabilising one. A controller tuned in one configuration is "
            "tuned for a machine the arm is not currently being.", "key"))

        # ---- coupling ---------------------------------------------------
        cp = Card("the inertia matrix is not diagonal, and that is the whole "
                  "difficulty")
        cp.add(math_label(r"M(q)\,\ddot q + C(q,\dot q)\dot q + G(q) = \tau",
                          18))
        cp.add(body(
            "For a two-link planar arm, written out:"))
        cp.add(math_label(
            r"M = \begin{bmatrix} m_1 l_{c1}^2 + I_1 + m_2(l_1^2 + l_{c2}^2 "
            r"+ 2 l_1 l_{c2}\cos q_2) + I_2 & m_2(l_{c2}^2 + l_1 l_{c2}"
            r"\cos q_2) + I_2 \\ \cdot & m_2 l_{c2}^2 + I_2\end{bmatrix}", 13))
        cp.add(body(
            "<b>Three readings of that matrix, in order of usefulness.</b><br><br>"
            "&nbsp;&nbsp;• <b>M₁₂ ≠ 0.</b> Accelerating the elbow applies a "
            "torque at the shoulder whether you asked for it or not. A "
            "per-joint PID sees that as a disturbance and fights it after the "
            "fact; state feedback sees it as an entry in a matrix and cancels "
            "it in advance. <b>This is the first plant in the tutor where "
            "loop-at-a-time design is not merely inconvenient but "
            "wrong.</b><br>"
            "&nbsp;&nbsp;• <b>Everything depends on q₂ only.</b> The elbow "
            "angle, and nothing else, sets the shoulder's effective inertia. "
            "Arm folded → small; arm extended → large. The shoulder's plant "
            "changes by several times over the workspace, and so does its "
            "natural frequency, which is why a fixed gain feels crisp in one "
            "pose and sluggish in another.<br>"
            "&nbsp;&nbsp;• <b>M is symmetric and positive definite</b>, "
            "always. That is not a coincidence — it is kinetic energy being "
            "positive — and it is the property every passivity-based "
            "controller in the nonlinear pages leans on."))
        cp.add(callout(
            "<b>Gravity as a spring whose sign you do not control.</b> "
            "Linearise G(q) and you get ∂G/∂q, which enters the A matrix "
            "exactly where a stiffness would. Hanging straight down it is "
            "<b>positive</b> — a real restoring spring, which is why a "
            "powered-off arm swings to hang rather than staying put. Held "
            "horizontally it is <b>zero or negative</b>, and a negative "
            "stiffness is a right-half-plane pole.<br><br>"
            "So the arm has an unstable configuration after all — not because "
            "it falls over, but because at full extension the linearised "
            "plant has a pole in the right half plane and the controller is "
            "the only thing holding the arm up. Cut power at full reach and "
            "it drops; cut power hanging down and nothing happens. Same "
            "robot, different A.", "key"))
        self.add(cp)

        i1 = Card("move the elbow and watch the plant change underneath you")
        i1.add(body(
            "<b>Left:</b> the open-loop eigenvalues at the current pose. "
            "<b>Middle:</b> inertia terms and the coupling ratio across the "
            "elbow's whole range. <b>Right:</b> a step at the shoulder under "
            "<i>one fixed gain</i>, evaluated at three different elbow "
            "angles.<br><br>"
            "<b>Four things to do:</b><br>"
            "&nbsp;&nbsp;<b>1.</b> Sweep the elbow. q₂ = 0 is <b>straight</b> "
            "(links in line, cos q₂ = 1, maximum inertia); q₂ → 180° is "
            "<b>folded back</b>. Watch M₁₁ fall by about 3× and the coupling "
            "ratio collapse with it. That ratio is roughly the fraction of "
            "shoulder torque that leaks into the elbow.<br>"
            "&nbsp;&nbsp;<b>2.</b> Set the shoulder near horizontal (q₁ ≈ 0) "
            "and watch a pole cross into the red half. Gravity has become "
            "negative stiffness.<br>"
            "&nbsp;&nbsp;<b>3.</b> Look at the right panel: one gain, three "
            "poses, three completely different responses. <b>That is why "
            "gain scheduling exists</b>, and why the alternative — computed "
            "torque, from the nonlinear pages — is worth its complexity.<br>"
            "&nbsp;&nbsp;<b>4.</b> Add payload. Everything above gets worse "
            "at once, and the wrist barely notices while the shoulder "
            "does.", dim=True))
        self.s_q1 = slider(-90, 90, 0)           # deg, shoulder
        self.s_q2 = slider(5, 170, 60)           # deg, elbow
        self.s_pay = slider(0, 80, 20)           # x0.1 kg
        self.l_q1, self.l_q2, self.l_pay = QLabel(), QLabel(), QLabel()
        i1.add_layout(slider_row("shoulder q₁ (°)", self.s_q1, self.l_q1))
        i1.add_layout(slider_row("elbow q₂ (°)", self.s_q2, self.l_q2))
        i1.add_layout(slider_row("payload (×0.1 kg)", self.s_pay, self.l_pay))
        self.st_m11 = Stat("M₁₁ shoulder", "--", theme.ACCENT)
        self.st_m12 = Stat("M₁₂ coupling", "--", theme.WARN)
        self.st_cr = Stat("coupling ratio", "--", theme.VIOLET)
        self.st_grav = Stat("gravity stiffness", "--", theme.CYAN)
        self.st_stab = Stat("open loop", "--", theme.GOOD)
        i1.add_layout(stat_row(self.st_m11, self.st_m12, self.st_cr,
                               self.st_grav, self.st_stab))
        self.c1 = MplCanvas(width=7.6, height=2.9, ncols=3)
        i1.add(self.c1)
        self.t1 = body("", dim=True)
        i1.add(self.t1)
        self.add(i1)
        for s in (self.s_q1, self.s_q2, self.s_pay):
            s.valueChanged.connect(self._redraw_arm)
        self._redraw_arm()

        # ---- what each idea buys ---------------------------------------
        self.add(hline())
        self.add(title("What each earlier idea is actually for, on this arm"))
        self.add(_tbl(
            ["Idea", "On the manipulator", "The number it produces"],
            [("first order, τ",
              "the current loop, and the structural low-pass of a "
              "harmonic drive's flexspline",
              "τ_elec ≈ 0.2 ms; first structural mode 30–80 Hz"),
             ("second order, ζ",
              "each joint servo, and the link's first bending mode — which "
              "is the one that limits you",
              "joint ζ ≈ 0.7; structural ζ ≈ 0.01, i.e. it rings for a long "
              "time"),
             ("poles / s-plane",
              "four eigenvalues that MOVE as the elbow moves; at full "
              "extension with the arm horizontal one is in the right half "
              "plane",
              "λ(q) — a family, not a set"),
             ("phase margin",
              "measured in the worst configuration, not the nominal one. The "
              "worst is usually fully extended with payload",
              "PM ≥ 45° at the worst pose, not the average"),
             ("Bode / crossover",
              "capped by the first structural resonance, not by the motor",
              "ω_gc ≲ (1/3) ω_resonance"),
             ("notch",
              "the obvious answer to that resonance, and the dangerous one, "
              "because the resonance MOVES with configuration and payload",
              "a notch tuned at full extension is mistuned when folded"),
             ("zeros",
              "the flexible-link case: a non-collocated tip sensor puts a "
              "pair of lightly damped zeros between actuator and output",
              "collocated → safe; non-collocated → the classic ringing case"),
             ("root locus / PID",
              "the per-joint servo everyone actually ships, with gravity "
              "compensation feedforward bolted on",
              "K_p, K_d per joint + τ_gravity(q)"),
             ("lead-lag",
              "raising crossover on the shoulder without touching the "
              "structural mode",
              "one lead ≈ +40°, placed a decade below resonance"),
             ("state feedback",
              "the formulation that can express 'cancel M₁₂ before it "
              "becomes an error'",
              "one 2×4 gain matrix, no cross-loop tuning"),
             ("LQR",
              "how those gains get chosen per configuration, and the natural "
              "home of a gain schedule: solve it at a grid of poses and "
              "interpolate",
              "K(q), stored as a lookup or fitted")],
            col0=150, colw=270, height=740))

        self.add(callout(
            "<b>Biped versus arm, in one comparison.</b> The biped is "
            "<i>unstable and roughly configuration-independent</i>: hard "
            "deadlines, a fixed input constraint, and a plant that does not "
            "change much while you balance. The arm is <i>stable and strongly "
            "configuration-dependent</i>: no deadlines, no falling, but a "
            "plant that is a different plant in every pose and a resonance "
            "that moves with it.<br><br>"
            "That is why legged control is dominated by timing and "
            "constraints, and manipulator control by models and "
            "scheduling — and why the same engineer's instincts do not "
            "transfer between them without translation.", "good"))
        self.finish()

    # ------------------------------------------------------------------
    def _redraw_arm(self):
        q1 = math.radians(self.s_q1.value())
        q2 = math.radians(self.s_q2.value())
        pay = self.s_pay.value() / 10.0
        self.l_q1.setText(f"{self.s_q1.value()}°")
        self.l_q2.setText(f"{self.s_q2.value()}°")
        self.l_pay.setText(f"{pay:.1f} kg")

        arm = TwoLink(m2=2.0 + pay, lc2=0.15 + 0.10 * pay / 4.0)
        M = arm.inertia(q2)
        Kg = arm.gravity_stiffness(q1, q2)
        ss = two_link_ss(arm, q1, q2)
        eig = np.linalg.eigvals(np.asarray(ss.A))
        unstable = any(v.real > 1e-6 for v in eig)

        self.st_m11.set(f"{M[0,0]:.3f}")
        self.st_m12.set(f"{M[0,1]:+.3f}")
        cr = arm.coupling_ratio(q2)
        self.st_cr.set(f"{cr:.2f}")
        self.st_cr.set_color(theme.BAD if cr > 0.6 else theme.VIOLET)
        self.st_grav.set(f"{Kg[0,0]:+.1f}")
        self.st_grav.set_color(theme.BAD if Kg[0, 0] < 0 else theme.GOOD)
        self.st_stab.set("UNSTABLE" if unstable else "stable")
        self.st_stab.set_color(theme.BAD if unstable else theme.GOOD)

        if unstable:
            self.t1.setText(
                f"<b>A pole is in the right half plane at this pose.</b> "
                f"Gravity's linearised stiffness at the shoulder is "
                f"{Kg[0,0]:+.1f} N·m/rad — negative, which is a spring "
                f"pushing the wrong way. Cut power here and the arm falls; "
                f"cut power hanging down and it does not. Same robot, "
                f"different A, and the only thing holding it up is the "
                f"controller. Coupling ratio {cr:.2f}: {cr*100:.0f}% of "
                "shoulder acceleration leaks into the elbow.")
        else:
            self.t1.setText(
                f"<b>Stable open loop at this pose</b>, with gravity acting "
                f"as a genuine restoring spring ({Kg[0,0]:+.1f} N·m/rad). "
                f"M₁₁ = {M[0,0]:.3f} kg·m² and coupling ratio {cr:.2f}. "
                f"Sweep the elbow and watch M₁₁ change by a factor of "
                f"{arm.inertia(math.radians(5))[0,0]/arm.inertia(math.radians(170))[0,0]:.1f} "
                "across its range — that factor is what a fixed gain has to "
                "survive, and it is why the right panel looks the way it "
                "does.")

        c = self.c1
        c.clear()
        a1, a2, a3 = c.axes
        _splane(a1, [complex(v) for v in eig], lim=8.0,
                marker_label="open loop")
        a1.set_title(f"eigenvalues at q₂ = {self.s_q2.value()}°", fontsize=8.5)

        q2s = np.radians(np.linspace(5, 170, 120))
        a2.plot(np.degrees(q2s), [arm.inertia(q)[0, 0] for q in q2s],
                color=theme.ACCENT, lw=2.0, label="M₁₁")
        a2.plot(np.degrees(q2s), [abs(arm.inertia(q)[0, 1]) for q in q2s],
                color=theme.WARN, lw=1.7, ls="--", label="|M₁₂|")
        a2b = a2.twinx()
        a2b.plot(np.degrees(q2s), [arm.coupling_ratio(q) for q in q2s],
                 color=theme.VIOLET, lw=1.5, alpha=0.8)
        a2b.set_ylabel("coupling ratio", color=theme.VIOLET, fontsize=9)
        a2b.tick_params(colors=theme.VIOLET, labelsize=8)
        a2.axvline(self.s_q2.value(), color=theme.GOOD, lw=1.3)
        a2.set_xlabel("elbow q₂ (°)")
        a2.set_ylabel("kg·m²")
        a2.set_title("one joint sets the other's plant", fontsize=8.5)
        c.legend(a2, loc="upper right")

        # one fixed gain, three poses
        base = two_link_ss(TwoLink(m2=2.0 + pay), 0.0, math.radians(60))
        # deliberately MODEST: a high-gain loop hides the very effect this
        # panel exists to show
        Kfix = lqr(np.asarray(base.A), np.asarray(base.B),
                   bryson([0.25, 0.25, 2.0, 2.0]), bryson([6.0, 3.0]))
        for qq, col, lab in ((math.radians(15), theme.BAD, "straight 15°"),
                             (math.radians(60), theme.ACCENT, "60°"),
                             (math.radians(165), theme.GOOD, "folded 165°")):
            ssq = two_link_ss(arm, q1, qq)
            ts, xs, _u, _s = simulate_feedback(ssq, Kfix, [0.15, 0.0, 0, 0],
                                               dur=1.2, dt=5e-4)
            a3.plot(ts, np.degrees(xs[:, 0]), color=col, lw=1.8, label=lab)
        a3.axhline(0, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a3.set_xlabel("time (s)")
        a3.set_ylabel("shoulder (°)")
        a3.set_title("ONE gain, three elbow angles", fontsize=8.5)
        c.legend(a3, loc="upper right")
        c.refresh()


# ==========================================================================
# CAPSTONE 2A -- biped actuators
# ==========================================================================

class BipedActuatorsPage(Page):
    TITLE = "Biped II — An Actuator For Each Of Six Joints"
    SUBTITLE = ("Direct drive, QDD, SEA, harmonic drive — and why the right "
                "answer at the ankle is the wrong answer at the hip.")
    SECTION = SEC_ACT
    NOTES = "capstone"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(_spec_card("biped"))

        self.add(callout(
            "<b>The single fact that decides everything below.</b> Reflected "
            "inertia scales as N², so a 100:1 gearbox makes the rotor feel "
            "10 000 times heavier at the output. That number decides "
            "backdrivability, which decides whether impedance control is "
            "available, which decides whether the joint can absorb an impact "
            "it did not see coming. <b>For a leg, impact is not an edge case "
            "— it happens twice per step, forever.</b>", "key"))

        # ---- the three demands ------------------------------------------
        d = Card("what a leg joint is actually asked to do, and it is three "
                 "different things")
        d.add(body(
            "&nbsp;&nbsp;• <b>Stance: hold a large torque with little "
            "motion.</b> Nearly static, so this is a thermal problem — "
            "current × time, not power. A gearbox is very good at this and a "
            "direct drive is very bad at it.<br>"
            "&nbsp;&nbsp;• <b>Swing: move fast under almost no load.</b> A "
            "speed problem, and the opposite of the above. Gearboxes trade "
            "speed for torque, so the gear ratio that made stance easy makes "
            "swing hard.<br>"
            "&nbsp;&nbsp;• <b>Impact: survive and absorb, in under 10 ms.</b> "
            "Heel strike delivers a torque spike faster than any control loop "
            "can respond to. <b>Whatever happens in those milliseconds is "
            "decided by mechanics alone</b> — the controller is not in the "
            "conversation. This is the demand that eliminates most "
            "candidates."))
        d.add(callout(
            "<b>Read the third bullet again, because it is the one people "
            "skip.</b> Your loop runs at 1 kHz, so one control tick is 1 ms "
            "and a meaningful correction takes several. A heel strike's peak "
            "arrives in 2–5 ms. By the time the controller has noticed, the "
            "event is over. So the impact requirement is a requirement on "
            "<b>reflected inertia and series compliance</b>, both of which are "
            "purchase-order decisions, not tuning decisions.", "warn"))
        self.add(d)

        # ---- the options ------------------------------------------------
        self.add(_tbl(
            ["Topology", "Backdrivable?", "Torque density", "Impact",
             "Where it belongs on this robot"],
            [("Direct drive  N = 1",
              "perfectly — nothing between rotor and load",
              "poor; needs a large, heavy, hot motor for leg torques",
              "excellent — nothing to break, and J_eff is just the rotor",
              "nowhere on a 30 kg biped, on thermal grounds alone. The reason "
              "it appears here is that everything else is measured against "
              "it."),
             ("QDD  N = 6–10",
              "yes — N² is 36–100, which is still small",
              "good; this is the modern legged-robot default",
              "good — low enough J_eff that the impact is absorbed by the "
              "structure rather than by the gear teeth",
              "<b>knee and hip.</b> High speed in swing, enough torque in "
              "stance, and survives heel strike without a spring."),
             ("SEA  spring in series",
              "yes, and it also MEASURES torque via deflection",
              "as good as its gearbox, with a bandwidth ceiling from the "
              "spring",
              "excellent — the spring is a mechanical low-pass on impact "
              "force, working at the speed of physics",
              "<b>ankle</b>, if impact absorption and torque accuracy matter "
              "more than bandwidth. Costs you the resonance from the "
              "state-feedback page."),
             ("Harmonic drive  N = 100+",
              "no — N² = 10 000; the joint feels like a wall",
              "excellent; smallest and lightest for a given torque",
              "poor — the impact goes into the gear teeth, and the joint "
              "cannot yield",
              "acceptable only where nothing hits the joint and nothing "
              "needs to yield. On a leg, that is nowhere."),
             ("Hydraulic",
              "somewhat, with valve control",
              "outstanding — the highest available",
              "good, with accumulators",
              "large or fast machines where the power plant is justified. "
              "Not a 30 kg biped.")],
            col0=140, colw=225, height=520))

        # ---- interactive -------------------------------------------------
        i1 = Card("choose a topology per joint and watch what it costs")
        i1.add(body(
            "<b>Left:</b> effective inertia against frequency for the chosen "
            "topology, with the impact band shaded — what matters is "
            "J<sub>eff</sub> <i>up there</i>, not at DC. <b>Middle:</b> the "
            "torque a heel strike puts through the joint. <b>Right:</b> the "
            "three demands scored.<br><br>"
            "<b>Three things to do:</b><br>"
            "&nbsp;&nbsp;<b>1.</b> Put a harmonic drive on the ankle and look "
            "at the impact torque. That spike goes into the gear "
            "teeth.<br>"
            "&nbsp;&nbsp;<b>2.</b> Switch to SEA and watch the spike drop by "
            "an order of magnitude — and watch the bandwidth stat drop with "
            "it. <b>You bought impact survival with response speed</b>, and "
            "there is no setting where you get both.<br>"
            "&nbsp;&nbsp;<b>3.</b> Now shorten the contact time — harder ground, "
            "a stone instead of carpet. <b>Every rigid topology's spike grows "
            "as 1/t, without limit. The SEA's does not move at all</b>, "
            "because a spring's peak torque is set by energy rather than by "
            "how fast the collision was. That single difference is the whole "
            "argument for series elasticity, and no controller reproduces "
            "it.<br>"
            "&nbsp;&nbsp;<b>4.</b> Soften the SEA spring further. Impact "
            "keeps improving, bandwidth keeps falling, and at some point the "
            "bandwidth drops under what the ankle needs to reject a "
            "disturbance before the capture point leaves the foot. <b>That "
            "crossing is the actual design constraint</b>, and it comes from "
            "the previous capstone page rather than from this one.", dim=True))
        self.cmb_joint = QComboBox()
        for lab in ("ankle", "knee", "hip"):
            self.cmb_joint.addItem(lab)
        self.cmb_top = QComboBox()
        for lab, key in (("QDD  (N = 8)", "qdd"), ("SEA", "sea"),
                         ("harmonic drive  (N = 100)", "hd"),
                         ("direct drive  (N = 1)", "dd")):
            self.cmb_top.addItem(lab, key)
        self.cmb_top.setCurrentIndex(0)
        i1.add_layout(labelled("Joint", self.cmb_joint, width=60))
        i1.add_layout(labelled("Topology", self.cmb_top, width=60))
        self.s_ratio = slider(1, 160, 8)
        self.s_kspring = slider(200, 8000, 1500)
        self.s_tc = slider(2, 100, 15)           # x0.1 ms, contact duration
        self.l_ratio, self.l_kspring, self.l_tc = QLabel(), QLabel(), QLabel()
        i1.add_layout(slider_row("gear ratio N", self.s_ratio, self.l_ratio))
        i1.add_layout(slider_row("SEA spring (N·m/rad)", self.s_kspring,
                                 self.l_kspring))
        i1.add_layout(slider_row("contact time (×0.1 ms)", self.s_tc,
                                 self.l_tc))
        self.st_jeff = Stat("J_eff at impact", "--", theme.BAD)
        self.st_bw = Stat("torque bandwidth", "--", theme.ACCENT)
        self.st_imp = Stat("impact torque", "--", theme.WARN)
        self.st_back = Stat("backdrivable?", "--", theme.GOOD)
        self.st_score = Stat("verdict", "--", theme.VIOLET)
        i1.add_layout(stat_row(self.st_jeff, self.st_bw, self.st_imp,
                               self.st_back, self.st_score))
        self.c1 = MplCanvas(width=7.6, height=2.8, ncols=3)
        i1.add(self.c1)
        self.t1 = body("", dim=True)
        i1.add(self.t1)
        self.add(i1)
        self.cmb_joint.currentIndexChanged.connect(self._redraw_act)
        self.cmb_top.currentIndexChanged.connect(self._redraw_act)
        for s in (self.s_ratio, self.s_kspring, self.s_tc):
            s.valueChanged.connect(self._redraw_act)
        self._redraw_act()

        self.add(callout(
            "<b>The answer for this robot, stated once.</b><br><br>"
            "&nbsp;&nbsp;• <b>Ankle — SEA, or QDD with a compliant foot.</b> "
            "It takes every heel strike, it holds large near-static torque in "
            "stance, and its bandwidth requirement is set by the capture-point "
            "argument rather than by a spec sheet. Series compliance is doing "
            "work no controller can do.<br>"
            "&nbsp;&nbsp;• <b>Knee — QDD, N ≈ 8.</b> The highest torque "
            "demand of the three, and it must also move fast in swing. It "
            "sees impact but through the ankle and shank, already "
            "filtered.<br>"
            "&nbsp;&nbsp;• <b>Hip — QDD, N ≈ 6.</b> Lowest inertia, highest "
            "speed, least impact exposure. This is the joint where you could "
            "get away with more gearing and should not, because the hip is "
            "how you place the foot and foot placement is how you "
            "balance.<br><br>"
            "Notice that the <i>same</i> topology wins twice for different "
            "reasons, and that the outlier is at the bottom of the chain. On "
            "the arm, the outlier is at the top.", "good"))
        self.finish()

    # ------------------------------------------------------------------
    def _redraw_act(self):
        joint = self.cmb_joint.currentText()
        top = self.cmb_top.currentData()
        N = float(self.s_ratio.value())
        ks = float(self.s_kspring.value())
        self.l_ratio.setText(f"{N:.0f}")
        self.l_kspring.setText(f"{ks:.0f}")
        self.l_tc.setText(f"{self.s_tc.value()/10.0:.1f} ms")

        j_load = {"ankle": 3.2, "knee": 1.1, "hip": 0.45}[joint]
        j_rotor = 6e-5
        if top == "dd":
            N = 1.0
        elif top == "hd":
            N = max(N, 60.0)
        j_m = reflected_inertia(j_rotor, N)

        ws = np.logspace(0, 3.3, 200)
        if top == "sea":
            jj = [j_eff("sea", j_m, j_load, ks, w) for w in ws]
            # practical torque bandwidth of a SEA: you can close a torque loop
            # up to roughly a third of the motor-spring-load resonance, and no
            # further -- past that the loop is fighting the resonance itself
            bw = sea_resonance_rad_s(ks, j_m, j_load) / (2 * math.pi * 3.0)
            backd = "yes + senses τ"
        else:
            jj = [j_eff("direct", j_m, j_load, 0.0, w) for w in ws]
            bw = 200.0 if N <= 12 else 60.0
            backd = "yes" if N <= 12 else "no"
        # ---- heel strike -------------------------------------------------
        # A collision is a momentum change, so the torque through the
        # TRANSMISSION is (what it must accelerate) x (change in rate) /
        # (how long the collision lasts). Only the local foot-and-shank
        # inertia is involved; the body's momentum goes up the leg as a
        # strut, not through the ankle actuator.
        #
        #   rigid:  tau = (J_reflected + J_local) * dw / t_contact
        #           -- and note the 1/t_contact. Harder ground, bigger spike,
        #              without limit, and nothing in software gets a vote.
        #   SEA:    the spring cannot deliver more than it can wind up in
        #           the time available, and energy fixes that:
        #              1/2 J dw^2 = 1/2 k d^2  =>  tau = dw sqrt(k J)
        #           which contains NO t_contact at all. That independence is
        #           the entire argument for series elasticity.
        j_local = {"ankle": 0.15, "knee": 0.10, "hip": 0.06}[joint]
        v_imp = 0.35                     # m/s at the foot
        r_lever = 0.10                   # m, foot to joint axis
        dw = v_imp / r_lever
        t_c = self.s_tc.value() / 10000.0
        tau_rigid = (j_m + j_local) * dw / max(t_c, 1e-6)
        if top == "sea":
            tau_imp = min(dw * math.sqrt(max(ks, 1e-9) * j_local), tau_rigid)
            t_stop = min(0.5 * math.pi / math.sqrt(max(ks, 1e-9) / j_local),
                         0.02)
        else:
            tau_imp = tau_rigid
            t_stop = max(t_c, 1e-6)
        w_imp = 2 * math.pi * 150.0
        j_at_impact = j_m + j_local

        self.st_jeff.set(f"{j_at_impact:.3f} kg·m²")
        self.st_jeff.set_color(theme.BAD if j_at_impact > 0.4 else theme.GOOD)
        self.st_bw.set(f"{bw:.0f} Hz")
        self.st_bw.set_color(theme.BAD if bw < 12 else theme.ACCENT)
        self.st_imp.set(f"{tau_imp:.0f} N·m")
        self.st_imp.set_color(theme.BAD if tau_imp > 400 else theme.GOOD)
        self.st_back.set(backd)
        self.st_back.set_color(theme.BAD if backd == "no" else theme.GOOD)

        need_bw = {"ankle": 12.0, "knee": 20.0, "hip": 25.0}[joint]
        good = (backd != "no") and bw >= need_bw and tau_imp < 400
        self.st_score.set("suitable" if good else "poor fit")
        self.st_score.set_color(theme.GOOD if good else theme.BAD)

        if backd == "no":
            self.t1.setText(
                f"<b>N = {N:.0f} gives J_eff = {j_at_impact:.3f} kg·m² at "
                f"impact frequencies — the joint is a wall.</b> It cannot "
                f"yield, so the {tau_imp:.0f} N·m of heel strike goes into "
                f"the gear teeth and the structure. It also cannot do "
                f"impedance control in any honest sense: commanding a low "
                f"stiffness does not make the joint feel soft when the "
                f"mechanics feel hard. On the {joint} of a walking robot this "
                "is the wrong choice, and no amount of loop rate fixes it.")
        elif top == "sea" and bw < need_bw:
            self.t1.setText(
                f"<b>The spring is too soft for this joint.</b> Torque "
                f"bandwidth {bw:.0f} Hz against the {need_bw:.0f} Hz the "
                f"{joint} needs. Impact is beautifully handled — "
                f"{tau_imp:.0f} N·m — and the joint is now too slow to reject "
                f"a disturbance before the capture point leaves the foot. "
                "Stiffen the spring until bandwidth clears the requirement, "
                "then stop: every extra N·m/rad you add past that is impact "
                "absorption you threw away for nothing.")
        elif top == "sea":
            self.t1.setText(
                f"<b>SEA at k = {ks:.0f} N·m/rad: {bw:.0f} Hz of torque "
                f"bandwidth and {tau_imp:.0f} N·m through the joint at heel "
                f"strike.</b> The spring is doing two jobs at once — it is a "
                f"mechanical low-pass that works at the speed of physics, and "
                f"its deflection is your torque sensor. The price is the "
                f"resonance you met on the state-feedback page, and a "
                "bandwidth ceiling you cannot control your way out of.")
        else:
            self.t1.setText(
                f"<b>N = {N:.0f}: J_eff = {j_at_impact:.3f} kg·m², "
                f"{bw:.0f} Hz, {tau_imp:.0f} N·m at impact.</b> This is the "
                f"quasi-direct-drive bargain and it is why modern legged "
                f"robots look the way they do: enough reduction to make the "
                f"motor small, little enough that N² keeps the joint "
                f"backdrivable and the impact survivable. On the {joint} it "
                f"{'works' if good else 'falls short — check the bandwidth and impact stats'}.")

        c = self.c1
        c.clear()
        a1, a2, a3 = c.axes
        a1.loglog(ws, jj, color=theme.ACCENT, lw=2.0)
        a1.axvspan(2 * math.pi * 80, 2 * math.pi * 400, color=theme.BAD,
                   alpha=0.13, label="impact band")
        a1.axhline(j_load, color=theme.TEXT_FAINT, lw=1.2, ls="--",
                   label="load alone")
        a1.set_xlabel("ω (rad/s)")
        a1.set_ylabel("J_eff (kg·m²)")
        a1.set_title("what the world feels", fontsize=8.5)
        c.legend(a1, loc="upper left")

        tt = np.linspace(0, 0.03, 400)
        prof = tau_imp * np.exp(-((tt - t_stop) / (0.4 * t_stop)) ** 2)
        a2.plot(tt * 1000, prof, color=theme.BAD, lw=2.0)
        a2.axhline(400, color=theme.WARN, lw=1.3, ls="--",
                   label="what the structure takes")
        a2.set_xlabel("time (ms)")
        a2.set_ylabel("joint torque (N·m)")
        a2.set_title("heel strike, and the loop is not there", fontsize=8.5)
        c.legend(a2, loc="upper right")

        scores = [
            min(1.0, bw / max(need_bw, 1e-9)),
            min(1.0, 400.0 / max(tau_imp, 1e-9)),
            0.15 if backd == "no" else 1.0,
        ]
        cols = [theme.GOOD if s >= 1.0 else theme.BAD for s in scores]
        a3.barh([0, 1, 2], scores, height=0.5, color=cols, alpha=0.85)
        a3.axvline(1.0, color=theme.TEXT_FAINT, lw=1.3, ls="--")
        a3.set_yticks([0, 1, 2])
        a3.set_yticklabels(["bandwidth", "impact", "backdrive"], fontsize=8)
        a3.set_xlim(0, 1.4)
        a3.set_xlabel("1.0 = meets requirement")
        a3.set_title(f"the {joint}'s three demands", fontsize=8.5)
        c.refresh()


# ==========================================================================
# CAPSTONE 2B -- arm actuators
# ==========================================================================

class ArmActuatorsPage(Page):
    TITLE = "Arm II — An Actuator For Each Of Three Joints"
    SUBTITLE = ("The inertia ordering is upside down compared with a leg, and "
                "that single reversal changes every answer.")
    SECTION = SEC_ACT
    NOTES = "capstone"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(_spec_card("arm"))

        self.add(callout(
            "<b>The reversal, stated first because everything follows from "
            "it.</b> On a leg in stance, the joint nearest the ground carries "
            "the most and the joint furthest carries the least. On an arm, "
            "the joint nearest the base carries the entire chain plus the "
            "payload, and the joint at the end carries only the payload. "
            "<b>The arm's hard joint is at the top; the leg's is at the "
            "bottom.</b><br><br>"
            "And there is a second reversal on top of it: an arm's mass is "
            "its own enemy. Every kilogram you add to the forearm is a "
            "kilogram the shoulder must accelerate at the end of a long "
            "lever, so making a distal joint stronger makes the proximal "
            "joint's problem worse. A leg pushing on the ground does not have "
            "that property.", "key"))

        d = Card("what an arm joint is asked to do")
        d.add(body(
            "&nbsp;&nbsp;• <b>Hold a pose against gravity, indefinitely.</b> "
            "Static torque with no motion. Thermally brutal for a direct "
            "drive, trivial for a gearbox — and this is why industrial arms "
            "are geared and why they are not backdrivable.<br>"
            "&nbsp;&nbsp;• <b>Move fast and stop precisely.</b> A bandwidth "
            "and repeatability problem, and the reason harmonic drives "
            "dominate: near-zero backlash at very high ratio.<br>"
            "&nbsp;&nbsp;• <b>Touch things without breaking them.</b> This is "
            "the demand that has changed in the last decade, and it is "
            "entirely a backdrivability question. Contact is not an impact "
            "twice per step — it is the <i>task</i>, and it can happen at any "
            "joint at any time.<br>"
            "&nbsp;&nbsp;• <b>Not fall on anyone.</b> A stationary arm "
            "holding a pose with a non-backdrivable actuator is safe when "
            "powered and a falling weight when it is not. Brakes are a real "
            "design item, not an afterthought."))
        self.add(d)

        self.add(_tbl(
            ["Topology", "Static holding", "Precision", "Contact safety",
             "Where it belongs on this arm"],
            [("Harmonic drive  N = 100+",
              "excellent — small motor, low current, cool",
              "excellent — near-zero backlash, the reason it dominates",
              "poor — not backdrivable; needs a torque sensor per joint to "
              "fake compliance, and that fake stops at the sensor's bandwidth",
              "<b>shoulder</b>, on a position-controlled arm. The static "
              "gravity load is relentless and there is no other cheap way to "
              "hold it."),
             ("QDD  N = 6–10",
              "poor — the motor is holding current all day and getting hot",
              "good, but needs a decent encoder",
              "excellent — genuinely backdrivable, so impedance control is "
              "real rather than emulated",
              "<b>the whole arm</b>, if it is a collaborative or contact-rich "
              "arm. You pay for it in motor size and thermals."),
             ("Cycloidal / planetary  N = 30–50",
              "good",
              "good; some backlash",
              "moderate — partially backdrivable",
              "<b>elbow</b>, as a middle position: more static capability "
              "than QDD, more yield than harmonic."),
             ("SEA",
              "good",
              "limited by the spring's bandwidth ceiling",
              "excellent, and it measures torque",
              "<b>wrist</b> or a dedicated force-control axis. Rarely the "
              "whole arm, because the bandwidth cost compounds down a chain."),
             ("Direct drive  N = 1",
              "very poor — thermally impossible for a held pose",
              "excellent",
              "perfect",
              "specialised high-speed pick-and-place, where nothing is held "
              "for long.")],
            col0=150, colw=215, height=520))

        # ---- interactive -------------------------------------------------
        i1 = Card("size the three joints, and watch distal mass poison the "
                  "proximal joint")
        i1.add(body(
            "<b>Left:</b> static holding torque per joint against reach. "
            "<b>Middle:</b> what one extra kilogram at the wrist costs each "
            "joint. <b>Right:</b> reflected inertia versus contact "
            "safety.<br><br>"
            "<b>Three things to do:</b><br>"
            "&nbsp;&nbsp;<b>1.</b> Extend the reach. Shoulder torque grows "
            "linearly while the wrist's does not move at all. Everything "
            "expensive is at the base.<br>"
            "&nbsp;&nbsp;<b>2.</b> Add mass at the wrist — a bigger wrist "
            "motor, a heavier gripper, a torque sensor. <b>Watch the shoulder "
            "requirement grow faster than the wrist's own.</b> This is why "
            "arm design proceeds from the tip inward and why every gram at "
            "the end of the chain is argued about.<br>"
            "&nbsp;&nbsp;<b>3.</b> Raise the shoulder's gear ratio to make "
            "the static problem go away, then look at the contact panel. You "
            "solved gravity and lost the ability to feel anything.", dim=True))
        self.s_reach = slider(30, 120, 65)       # cm
        self.s_payl = slider(0, 100, 20)         # x0.1 kg
        self.s_wristm = slider(0, 40, 8)         # x0.1 kg, distal hardware
        self.s_Ns = slider(1, 160, 100)          # shoulder ratio
        self.l_reach, self.l_payl = QLabel(), QLabel()
        self.l_wristm, self.l_Ns = QLabel(), QLabel()
        i1.add_layout(slider_row("reach (cm)", self.s_reach, self.l_reach))
        i1.add_layout(slider_row("payload (×0.1 kg)", self.s_payl,
                                 self.l_payl))
        i1.add_layout(slider_row("distal hardware (×0.1 kg)", self.s_wristm,
                                 self.l_wristm))
        i1.add_layout(slider_row("shoulder gear ratio N", self.s_Ns,
                                 self.l_Ns))
        self.st_ts = Stat("shoulder static τ", "--", theme.BAD)
        self.st_te = Stat("elbow static τ", "--", theme.WARN)
        self.st_tw = Stat("wrist static τ", "--", theme.GOOD)
        self.st_pen = Stat("1 kg at wrist costs", "--", theme.VIOLET)
        self.st_bd = Stat("shoulder backdrive", "--", theme.CYAN)
        i1.add_layout(stat_row(self.st_ts, self.st_te, self.st_tw,
                               self.st_pen, self.st_bd))
        self.c1 = MplCanvas(width=7.6, height=2.8, ncols=3)
        i1.add(self.c1)
        self.t1 = body("", dim=True)
        i1.add(self.t1)
        self.add(i1)
        for s in (self.s_reach, self.s_payl, self.s_wristm, self.s_Ns):
            s.valueChanged.connect(self._redraw_armact)
        self._redraw_armact()

        self.add(callout(
            "<b>The answer for this arm, and it depends on one question.</b>"
            "<br><br>"
            "<b>If it is a position-controlled arm behind a fence:</b> "
            "harmonic drives everywhere. Best torque density, best "
            "repeatability, and the lack of backdrivability costs you nothing "
            "because nothing is supposed to touch it.<br><br>"
            "<b>If it is a contact-rich or collaborative arm:</b> QDD at "
            "shoulder and elbow, and either QDD or a SEA at the wrist. You "
            "will pay in motor mass, in thermals, and in a gravity-"
            "compensation term you can never switch off — and in exchange the "
            "arm can be pushed, can feel what it touches, and does not need a "
            "torque sensor per joint to pretend.<br><br>"
            "<b>The one thing you should not do</b> is build a harmonic-drive "
            "arm and add joint torque sensors expecting impedance control. It "
            "works, it ships, and its rendered stiffness is bounded by the "
            "sensor loop's bandwidth rather than by the mechanics — which is "
            "the admittance-versus-impedance argument, arriving as a "
            "purchase order.", "good"))
        self.finish()

    # ------------------------------------------------------------------
    def _redraw_armact(self):
        reach = self.s_reach.value() / 100.0
        pay = self.s_payl.value() / 10.0
        wm = self.s_wristm.value() / 10.0
        Ns = float(self.s_Ns.value())
        self.l_reach.setText(f"{reach*100:.0f} cm")
        self.l_payl.setText(f"{pay:.1f} kg")
        self.l_wristm.setText(f"{wm:.1f} kg")
        self.l_Ns.setText(f"{Ns:.0f}")

        l1 = reach * 0.55
        l2 = reach * 0.45
        m_link1, m_link2 = 3.0, 2.0 + wm
        tip = pay + wm

        def torques(r):
            a, b = r * 0.55, r * 0.45
            t_sh = G * (m_link1 * a / 2 + m_link2 * (a + b / 2) + pay * r)
            t_el = G * (m_link2 * b / 2 + pay * b)
            t_wr = G * pay * 0.06
            return t_sh, t_el, t_wr

        t_sh, t_el, t_wr = torques(reach)
        t_sh1, t_el1, t_wr1 = torques(reach)
        # what one extra kg at the wrist costs
        pay_save = pay
        pay = pay + 1.0
        t_sh2, t_el2, t_wr2 = torques(reach)
        pay = pay_save
        d_sh = t_sh2 - t_sh1

        j_rot = 8e-5
        j_ref = reflected_inertia(j_rot, Ns)
        backd = j_ref < 0.15

        self.st_ts.set(f"{t_sh:.0f} N·m")
        self.st_te.set(f"{t_el:.0f} N·m")
        self.st_tw.set(f"{t_wr:.1f} N·m")
        self.st_pen.set(f"+{d_sh:.0f} N·m at shoulder")
        self.st_bd.set(f"J_ref {j_ref:.3f} — "
                       f"{'yes' if backd else 'no'}")
        self.st_bd.set_color(theme.GOOD if backd else theme.BAD)

        self.t1.setText(
            f"<b>Shoulder {t_sh:.0f} N·m, elbow {t_el:.0f}, wrist "
            f"{t_wr:.1f} — a factor of {t_sh/max(t_wr,1e-6):.0f} across three "
            f"joints.</b> One extra kilogram at the wrist adds {d_sh:.0f} N·m "
            f"at the shoulder and nothing at the wrist itself, which is the "
            f"whole reason arms are designed from the tip inward. At N = "
            f"{Ns:.0f} the shoulder's reflected inertia is {j_ref:.3f} kg·m², "
            f"so it is {'backdrivable and can do genuine impedance control' if backd else 'not backdrivable — impedance control here is emulated through a torque sensor, and it stops working above that sensor loop bandwidth'}.")

        c = self.c1
        c.clear()
        a1, a2, a3 = c.axes
        rr = np.linspace(0.3, 1.2, 60)
        sh = [torques(r)[0] for r in rr]
        el = [torques(r)[1] for r in rr]
        wr = [torques(r)[2] for r in rr]
        a1.plot(rr * 100, sh, color=theme.BAD, lw=2.0, label="shoulder")
        a1.plot(rr * 100, el, color=theme.WARN, lw=1.8, label="elbow")
        a1.plot(rr * 100, wr, color=theme.GOOD, lw=1.8, label="wrist")
        a1.axvline(reach * 100, color=theme.ACCENT, lw=1.3)
        a1.set_xlabel("reach (cm)")
        a1.set_ylabel("static τ (N·m)")
        a1.set_title("everything expensive is at the base", fontsize=8.5)
        c.legend(a1, loc="upper left")

        a2.bar([0, 1, 2], [t_sh2 - t_sh1, t_el2 - t_el1, t_wr2 - t_wr1],
               color=[theme.BAD, theme.WARN, theme.GOOD], alpha=0.85,
               width=0.55)
        a2.set_xticks([0, 1, 2])
        a2.set_xticklabels(["shoulder", "elbow", "wrist"], fontsize=8)
        a2.set_ylabel("Δτ per +1 kg at wrist")
        a2.set_title("distal mass poisons proximal joints", fontsize=8.5)

        Ns_r = np.linspace(1, 160, 120)
        a3.semilogy(Ns_r, [reflected_inertia(j_rot, n) for n in Ns_r],
                    color=theme.VIOLET, lw=2.0)
        a3.axhline(0.15, color=theme.GOOD, lw=1.4, ls="--",
                   label="backdrivable below")
        a3.scatter([Ns], [j_ref], s=50, color=theme.ACCENT, zorder=5)
        a3.set_xlabel("gear ratio N")
        a3.set_ylabel("reflected J (kg·m²)")
        a3.set_title("N² decides whether you can feel", fontsize=8.5)
        c.legend(a3, loc="upper left")
        c.refresh()


# ==========================================================================
# CAPSTONE 3A -- biped control
# ==========================================================================

class BipedControlPage(Page):
    TITLE = "Biped III — Which Controller, Which Joint, Which Phase"
    SUBTITLE = ("Position, torque, impedance, admittance, PID, lead-lag — "
                "assigned to six joints across a gait cycle, with reasons.")
    SECTION = SEC_CTRL
    NOTES = "capstone"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(_spec_card("biped"))

        self.add(callout(
            "<b>The question is not \"which controller is best\".</b> On a "
            "walking robot the answer changes <i>within a single step</i>, "
            "because the same joint is doing different physics in stance and "
            "in swing. A leg in swing is a manipulator moving through free "
            "space; a leg in stance is a structural member with the floor at "
            "one end. Those want opposite controllers, and the interesting "
            "engineering is in the handover.", "key"))

        self.add(_tbl(
            ["Phase", "Ankle", "Knee", "Hip", "Why"],
            [("early stance  (heel strike → foot flat)",
              "<b>low-impedance / torque</b> — yield to the impact, absorb "
              "energy",
              "<b>impedance, low K</b> — the knee's job is shock absorption",
              "<b>impedance</b> — hold the body, softly",
              "Impact happens faster than any loop. All you can choose is "
              "what the joint does mechanically, and the answer is yield."),
             ("mid stance  (supporting)",
              "<b>impedance, moderate K</b> — this is the balance actuator; "
              "CoP modulation is ankle torque",
              "<b>impedance, higher K</b> — hold the body height",
              "<b>impedance</b> — regulate trunk attitude",
              "Balance is a force-relationship task against a rigid "
              "environment. Position control against the floor is the "
              "textbook way to fight infinite stiffness and lose."),
             ("push-off  (heel rise → toe off)",
              "<b>torque</b> — deliver a commanded impulse, open loop in "
              "position",
              "<b>torque / impedance</b>",
              "<b>torque</b> — inject the energy the step costs",
              "You are commanding energy into the ground. Nobody cares "
              "exactly where the ankle is; they care how much work it did."),
             ("swing  (foot off the ground)",
              "<b>position, moderate gains</b> — just clear the toe",
              "<b>position</b> — trajectory tracking, free space",
              "<b>position, high gains</b> — foot placement accuracy is "
              "balance",
              "Nothing is in contact, so there is no interaction force to "
              "shape. This is a free-space tracking problem, which is what "
              "position control is for."),
             ("touchdown  (about to strike)",
              "<b>impedance, dropping K</b> — pre-soften",
              "<b>impedance, dropping K</b>",
              "<b>impedance</b>",
              "The handover. Switching stiffness AT contact is too late; you "
              "ramp it down before, because the contact time is shorter than "
              "your transient.")],
            col0=170, colw=205, height=560))

        # ---- the paradigm choice ---------------------------------------
        self.add(hline())
        self.add(title("Impedance or admittance, and the hardware decides"))

        ia = Card("for this robot, the answer is impedance, and here is the "
                  "argument")
        ia.add(body(
            "The rule from the Impedance vs Admittance page: <b>impedance "
            "control needs a backdrivable joint; admittance control needs a "
            "stiff, non-backdrivable one and a force sensor.</b> They are not "
            "preferences, they are consequences of what the mechanics already "
            "do.<br><br>"
            "This biped has QDD and SEA joints, chosen on the previous page "
            "precisely because they are backdrivable. So:<br><br>"
            "&nbsp;&nbsp;• <b>Impedance</b> — command torque, read motion, no "
            "force sensor required. Works against the stiff environment a "
            "floor is. Stable when the environment gets stiffer, which is "
            "exactly the direction a foot's environment moves at heel "
            "strike.<br>"
            "&nbsp;&nbsp;• <b>Admittance</b> — would need a force sensor in "
            "each foot and a stiff joint underneath, and it goes "
            "<b>unstable against stiff contact</b>, which is the one thing a "
            "foot does. It is the right answer for a heavy geared arm "
            "polishing a surface, and the wrong answer for a leg."))
        ia.add(callout(
            "<b>And now the sentence that ties the whole tutor together.</b> "
            "Position control, impedance control and torque control are one "
            "controller with the stiffness knob at three settings — that was "
            "the Spectrum page. On this robot you are not choosing between "
            "three paradigms, you are <b>scheduling one number across the "
            "gait cycle</b>: K high in swing, K moderate in mid stance, K low "
            "at touchdown, K → 0 at push-off with a feedforward torque "
            "instead.<br><br>"
            "That is one controller, one schedule, and it is why the "
            "impedance pages spent so long on the fact that τ_ff and K are "
            "independent knobs. The gait cycle moves both, for different "
            "reasons.", "key"))
        self.add(ia)

        i1 = Card("schedule stiffness across a step and watch the impact")
        i1.add(body(
            "A simplified step: the ankle tracks a reference through swing, "
            "hits the ground, and supports. You choose the stiffness "
            "schedule.<br><br>"
            "<b>Three things to do:</b><br>"
            "&nbsp;&nbsp;<b>1.</b> Leave stiffness high through touchdown. "
            "The impact force spikes — a stiff joint meeting a stiff floor "
            "has nothing to absorb the collision, and both the peak force and "
            "the tracking error blow up.<br>"
            "&nbsp;&nbsp;<b>2.</b> Ramp the stiffness down before contact. "
            "Peak force drops sharply and swing tracking is unaffected, "
            "because the ramp happens while the foot is still in the "
            "air.<br>"
            "&nbsp;&nbsp;<b>3.</b> Ramp it down too early and watch swing "
            "tracking degrade — the foot no longer goes where you put it, "
            "which on a biped means the capture-point argument from the first "
            "capstone page stops being satisfiable. <b>There is a window, and "
            "finding it is what gait tuning actually is.</b>", dim=True))
        self.s_khigh = slider(50, 800, 400)
        self.s_klow = slider(5, 400, 60)
        self.s_ramp = slider(0, 55, 15)          # % of cycle before contact
        self.l_khigh, self.l_klow, self.l_ramp = QLabel(), QLabel(), QLabel()
        i1.add_layout(slider_row("swing K (N·m/rad)", self.s_khigh,
                                 self.l_khigh))
        i1.add_layout(slider_row("contact K (N·m/rad)", self.s_klow,
                                 self.l_klow))
        i1.add_layout(slider_row("ramp starts (% early)", self.s_ramp,
                                 self.l_ramp))
        self.st_peakf = Stat("peak contact torque", "--", theme.BAD)
        self.st_track = Stat("swing tracking RMS", "--", theme.ACCENT)
        self.st_win = Stat("verdict", "--", theme.GOOD)
        i1.add_layout(stat_row(self.st_peakf, self.st_track, self.st_win))
        self.c1 = MplCanvas(width=7.6, height=2.8, ncols=2)
        i1.add(self.c1)
        self.t1 = body("", dim=True)
        i1.add(self.t1)
        self.add(i1)
        for s in (self.s_khigh, self.s_klow, self.s_ramp):
            s.valueChanged.connect(self._redraw_sched)
        self._redraw_sched()

        # ---- classical controllers -------------------------------------
        self.add(hline())
        self.add(title("PID, lead-lag, LQR — where each one actually sits on "
                       "this robot"))
        self.add(_tbl(
            ["Method", "Where on the biped", "Why there, and not elsewhere"],
            [("P / PD",
              "inside every joint, as the impedance law itself",
              "K and B <i>are</i> K_p and K_d. There is no separate PD loop — "
              "the impedance controller is one. D is not optional: a leg with "
              "no damping oscillates at its own resonance."),
             ("PI / integral",
              "the ankle in mid stance, and the trunk attitude loop — "
              "cautiously",
              "Integral action removes the droop from a constant load, which "
              "at the ankle means standing dead upright rather than "
              "1° off. It also winds up during the swing phase when the "
              "joint is unloaded, so it must be reset or clamped at every "
              "phase transition. Windup across a gait cycle is a classic "
              "biped bug."),
             ("Lead compensator",
              "the balance loop, when the delay budget has eaten the phase "
              "margin",
              "You need crossover above 5p and the delays have cost you "
              "phase. A lead buys ~40° back at crossover for ×6 noise gain — "
              "and the noise lands on an IMU, so check the actual signal "
              "before spending it."),
             ("Lag",
              "rarely; the ankle's steady-state accuracy loop",
              "A lag buys DC gain without integral windup, which is "
              "attractive on a joint whose load disappears every step. Its "
              "phase dip must sit a decade below crossover."),
             ("Notch",
              "structural mode of the shank, if you have one",
              "And it is dangerous exactly as advertised: the resonance moves "
              "with load and temperature, and a mistuned notch leaves a "
              "lightly damped mode under high loop gain. Prefer stiffening "
              "the shank."),
             ("Pole placement",
              "almost never, directly",
              "Twelve poles, no intuition for where to put them, and no "
              "notion of torque cost. Useful as a way to <i>read</i> what a "
              "design did, not to specify one."),
             ("LQR",
              "the whole-body balance controller, and the joint-level "
              "regulator on a good day",
              "This is where LQR earns its keep: MIMO, coupled, and you can "
              "state the weights in engineering units — ankle angle tight, "
              "hip angle loose, torque priced by what the motors have. Solve "
              "at several operating points and schedule."),
             ("MPC",
              "the layer above: footstep planning with the CoP constraint",
              "The capture-point constraint is a HARD constraint, and LQR "
              "cannot express one. MPC can, which is why every serious "
              "walking controller has an MPC somewhere above the joint "
              "loops."),
             ("RL",
              "gait-level policy, gain scheduling, and adaptation to terrain "
              "the model does not have",
              "It is the answer when the model runs out — contact "
              "modes, deformable ground, disturbances you cannot enumerate. "
              "Note what it does NOT replace: the joint-level impedance loop "
              "underneath is still classical, still at 1 kHz, and still the "
              "thing keeping the robot safe while the policy is wrong.")],
            col0=140, colw=290, height=650))

        self.add(callout(
            "<b>The stack, bottom to top, on this robot.</b><br><br>"
            "&nbsp;&nbsp;<b>1 kHz</b> — joint impedance control, τ = "
            "−K(θ−θ_d) − Bθ̇ + τ_ff. Classical, boring, and the thing that "
            "makes everything above it safe.<br>"
            "&nbsp;&nbsp;<b>200–500 Hz</b> — whole-body LQR or QP: distribute "
            "a desired CoM wrench across six joints subject to friction and "
            "torque limits.<br>"
            "&nbsp;&nbsp;<b>20–50 Hz</b> — MPC over the next few steps, with "
            "the CoP constraint and the capture point.<br>"
            "&nbsp;&nbsp;<b>1–10 Hz</b> — the learned or planned policy: "
            "where to step, how fast to walk, what to do about terrain.<br><br>"
            "<b>Every layer is slower and smarter than the one below.</b> "
            "That is not an accident of implementation — it is the real-time "
            "argument from page 1 turned into an architecture, and it is the "
            "same shape as the fast-loop/slow-learner split the DDPG "
            "deployment page ends on.", "good"))
        self.finish()

    # ------------------------------------------------------------------
    def _redraw_sched(self):
        kh = float(self.s_khigh.value())
        kl = float(self.s_klow.value())
        ramp = self.s_ramp.value() / 100.0
        self.l_khigh.setText(f"{kh:.0f}")
        self.l_klow.setText(f"{kl:.0f}")
        self.l_ramp.setText(f"{ramp*100:.0f}%")

        n = 600
        t = np.linspace(0.0, 1.0, n)
        t_contact = 0.6
        # stiffness schedule
        K = np.full(n, kh)
        start = max(0.0, t_contact - ramp)
        for i, ti in enumerate(t):
            if ti >= t_contact:
                K[i] = kl
            elif ti > start and ramp > 1e-6:
                f = (ti - start) / max(ramp, 1e-9)
                K[i] = kh + (kl - kh) * f

        # Swing reference: lift the toe and bring it back down to 0, which is
        # where the floor is. After touchdown the reference holds at 0 and the
        # floor is a very stiff one-sided constraint BELOW the joint -- the
        # foot can rest on it and cannot pass through it.
        # Reference: lift the toe, bring it down to the floor at t_contact,
        # and then keep commanding DOWNWARD -- which is what a stance leg is
        # actually told to do. The floor stops it, and how hard it presses is
        # K x (how far past the floor you asked for). That product is the
        # steady contact force, and the schedule is what sets it.
        s_swing = np.clip(t / t_contact, 0.0, 1.0)
        ref = 0.35 * np.sin(np.pi * s_swing)
        after = t >= t_contact
        ref[after] = -0.08 * np.clip((t[after] - t_contact) / 0.12, 0.0, 1.0)
        dt = 0.7 / n
        ref_dot = np.gradient(ref, dt)

        # TWO bodies, because with one the answer is wrong. The foot is light
        # (j_f) and hits the ground; the body is heavy (j_b) and keeps coming.
        # The virtual spring sits BETWEEN them, so the torque the transmission
        # sees during the collision is limited by K -- peak deflection is
        # v*sqrt(j_b/K), hence peak torque v*sqrt(K*j_b), which scales as the
        # square root of the stiffness you scheduled. Model the foot alone and
        # K barely appears, which is exactly the wrong conclusion.
        j_f, j_b = 0.05, 3.0
        th = np.zeros(n)                # foot angle -- the one that lands
        thb = np.zeros(n)               # body angle
        v, vb = 0.0, 0.0
        joint_tau = np.zeros(n)
        ground_tau = np.zeros(n)
        for i in range(1, n):
            # a virtual spring, its damper, and a velocity feedforward. The
            # damper is scaled to the CURRENT stiffness -- a schedule that
            # moves K without moving B changes zeta as a side effect, which is
            # a real and common bug.
            b_ctrl = 2.0 * 0.8 * math.sqrt(max(K[i], 1e-9) * j_f)
            rel = th[i - 1] - thb[i - 1]
            tj = K[i] * (ref[i] - rel) + b_ctrl * (ref_dot[i] - (v - vb))
            gt = -3.5                            # the foot's own weight
            if th[i - 1] < 0.0:                     # penetrating the floor
                gt += -9000.0 * th[i - 1] - 60.0 * min(v, 0.0)
            joint_tau[i] = tj
            ground_tau[i] = gt
            v += (tj + gt) / j_f * dt
            vb += (-tj) / j_b * dt
            th[i] = th[i - 1] + v * dt
            thb[i] = thb[i - 1] + vb * dt
            if not np.isfinite(th[i]):
                th[i:] = th[i - 1]
                break

        after_i = t >= t_contact
        peak = float(np.max(np.abs(joint_tau[after_i]))) if after_i.any() else 0.0
        contact_tau = joint_tau
        swing = t < t_contact
        rms = float(np.sqrt(np.mean(((th - thb)[swing] - ref[swing]) ** 2)))
        good = peak < 15 and rms < 0.018

        self.st_peakf.set(f"{peak:.0f} N·m")
        self.st_peakf.set_color(theme.BAD if peak > 15 else theme.GOOD)
        self.st_track.set(f"{math.degrees(rms):.1f}°")
        self.st_track.set_color(theme.BAD if rms > 0.018 else theme.GOOD)
        self.st_win.set("in the window" if good else "out of the window")
        self.st_win.set_color(theme.GOOD if good else theme.BAD)

        if peak > 15 and rms <= 0.018:
            self.t1.setText(
                f"<b>Peak joint torque at impact {peak:.0f} N·m — too stiff at "
                f"touchdown.</b> A stiff joint meeting a stiff floor has "
                f"nothing to absorb the collision with, so the whole "
                f"momentum change appears as force in a few milliseconds. "
                "Start the ramp earlier, or take the contact stiffness down. "
                "Note that no loop rate helps here: the event is over before "
                "the controller has taken three samples.")
        elif rms > 0.018:
            self.t1.setText(
                f"<b>Swing tracking has degraded to {math.degrees(rms):.1f}° "
                f"RMS.</b> The ramp started too early, so the joint went soft "
                f"while it was still supposed to be placing the foot. On a "
                f"biped that is not a cosmetic error — foot placement IS the "
                f"balance strategy, and the capture point has to land "
                f"somewhere you chose. Impact is {peak:.0f} N·m, which is "
                "fine, and you bought it with the wrong currency.")
        else:
            self.t1.setText(
                f"<b>In the window: {peak:.0f} N·m at impact and "
                f"{math.degrees(rms):.1f}° of swing tracking error.</b> The "
                f"stiffness ramps down while the foot is still in the air, so "
                f"the joint is already compliant when it arrives and the "
                f"tracking that mattered has already happened. That window is "
                "what gait tuning is, and it is why the impedance pages "
                "insisted that K is a schedulable design parameter rather "
                "than a gain you tune once.")

        c = self.c1
        c.clear()
        a1, a2 = c.axes
        a1.plot(t, np.degrees(ref), color=theme.TEXT_FAINT, lw=1.5, ls="--",
                label="reference")
        a1.plot(t, np.degrees(th - thb), color=theme.GOOD, lw=2.0,
                label="joint angle")
        a1.axhline(0, color=theme.BAD, lw=1.2, ls=":", alpha=0.7)
        a1.axvline(t_contact, color=theme.BAD, lw=1.5, ls="-.",
                   label="touchdown")
        a1.set_xlabel("gait cycle")
        a1.set_ylabel("ankle angle (°)")
        a1.set_title("swing, then contact", fontsize=8.5)
        c.legend(a1, loc="upper left")

        a2.plot(t, K, color=theme.VIOLET, lw=2.0, label="stiffness schedule")
        a2b = a2.twinx()
        a2b.plot(t, np.abs(contact_tau), color=theme.BAD, lw=1.5, alpha=0.85)
        a2b.set_ylabel("contact τ (N·m)", color=theme.BAD, fontsize=9)
        a2b.tick_params(colors=theme.BAD, labelsize=8)
        a2.axvline(t_contact, color=theme.BAD, lw=1.3, ls="-.")
        a2.set_xlabel("gait cycle")
        a2.set_ylabel("K (N·m/rad)", color=theme.VIOLET)
        a2.set_title("one number, scheduled", fontsize=8.5)
        c.refresh()


# ==========================================================================
# CAPSTONE 3B -- arm control
# ==========================================================================

class ArmControlPage(Page):
    TITLE = "Arm III — Which Controller, Which Task, Which Contact"
    SUBTITLE = ("For a manipulator the phase is not a gait cycle, it is "
                "whether you are touching something — and that single bit "
                "changes the controller.")
    SECTION = SEC_CTRL
    NOTES = "capstone"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add(_spec_card("arm"))

        self.add(callout(
            "<b>One bit decides almost everything: am I in contact?</b><br><br>"
            "In free space the arm is a tracking problem and position control "
            "is correct — there is no interaction force to shape, and stiff "
            "is simply better. The instant the tool touches something, "
            "position control is trying to command the position of a point "
            "that is now constrained by an object, and the resulting force is "
            "<b>stiffness × your position error</b>, which for a stiff joint "
            "and a small error is a very large number. That is how "
            "position-controlled arms break things.", "key"))

        self.add(_tbl(
            ["Task", "Controller", "Why", "The failure if you get it wrong"],
            [("free-space move  (pick, place, reposition)",
              "<b>position / PD + gravity feedforward</b>",
              "No contact, so no interaction to shape. Stiff tracking is "
              "exactly what you want, and gravity compensation removes the "
              "steady error without integral windup.",
              "None, really. This is the easy case, and it is why "
              "industrial arms shipped for forty years without force "
              "control."),
             ("guarded move  (approach until touch)",
              "<b>impedance, low K, with a force threshold</b>",
              "You do not know where the surface is. A soft virtual spring "
              "means the contact force is bounded by K × overshoot, so "
              "arriving early costs a small force rather than a collision.",
              "Position control here converts a 2 mm surface-location error "
              "into whatever force the joint can produce."),
             ("insertion  (peg in hole, connector)",
              "<b>impedance, low K laterally, higher K axially</b>",
              "Genuinely different stiffness per direction. Compliance "
              "sideways lets the geometry guide the part in; stiffness along "
              "the axis provides the insertion force.",
              "Uniform stiffness jams. This is the classic remote-centre-of-"
              "compliance problem, and it is solved mechanically on "
              "production lines for exactly this reason."),
             ("surface following  (polish, wipe, sand)",
              "<b>hybrid: force control normal, position control tangential</b>",
              "The two directions want different things and are geometrically "
              "orthogonal, so you can genuinely control force in one and "
              "position in the other.",
              "Position control normal to the surface means the force is set "
              "by how flat your model of the surface is — which is never "
              "flat enough."),
             ("human contact  (handover, lead-through)",
              "<b>impedance, very low K, or admittance</b>",
              "The person is the reference. On a backdrivable arm, impedance. "
              "On a geared arm with a wrist force sensor, admittance — it is "
              "the only option and it works well as long as the person is "
              "soft.",
              "Admittance against a stiff constraint goes unstable. Grab a "
              "lead-through arm and brace it against a table and you can "
              "usually make it buzz."),
             ("high-speed repetitive  (cycle time matters)",
              "<b>position + feedforward inverse dynamics</b>",
              "The trajectory is known in advance, so most of the torque can "
              "be computed rather than fed back — feedback only fixes the "
              "residual.",
              "Pure feedback needs high gain to be fast, and high gain runs "
              "into the structural mode from the first arm page.")],
            col0=170, colw=215, height=640))

        # ---- impedance vs admittance -----------------------------------
        self.add(hline())
        self.add(title("Impedance or admittance — and this time the hardware "
                       "can go either way"))

        ia = Card("the arm is the case where the choice is genuinely open")
        ia.add(body(
            "The biped's answer was forced: backdrivable joints, stiff "
            "environment, so impedance. An arm can be built either way, and "
            "the two builds want opposite controllers.<br><br>"
            "&nbsp;&nbsp;• <b>QDD arm, backdrivable</b> → impedance. Command "
            "torque, read motion, no force sensor. <b>Stable against stiff "
            "contact</b>, degrades gracefully, and the rendered stiffness can "
            "go all the way down to the mechanics' own — which is "
            "low.<br>"
            "&nbsp;&nbsp;• <b>Harmonic-drive arm with a wrist force sensor</b> "
            "→ admittance. Measure force, move a virtual model, command "
            "position to the stiff inner loop. <b>Excellent against soft "
            "environments</b> — a human hand, free air — and it can render a "
            "very light apparent mass, lighter than the arm actually is, "
            "which impedance cannot do.<br><br>"
            "<b>The failure modes are mirror images and both are worth being "
            "able to predict.</b> Impedance cannot render a stiffness higher "
            "than its own structure, so it feels mushy on a precision task. "
            "Admittance goes unstable when the environment is stiffer than "
            "the virtual model — press a lead-through arm against a rigid "
            "table and it buzzes. Neither is a bug; both are the same "
            "sentence about who is stiffer than whom."))
        ia.add(callout(
            "<b>The decision rule, and it fits in one line: match the "
            "controller to whichever side is stiffer.</b><br><br>"
            "&nbsp;&nbsp;• stiff environment, soft robot → <b>impedance</b><br>"
            "&nbsp;&nbsp;• soft environment, stiff robot → <b>admittance</b>"
            "<br><br>"
            "A leg meets the floor, which is the stiffest thing in the "
            "building, so a leg is impedance-controlled and is built "
            "backdrivable to make that possible. A collaborative arm meets a "
            "human, who is soft, so a geared arm with a force sensor can be "
            "admittance-controlled and feel weightless. <b>The same robot "
            "doing both tasks needs to switch</b>, and the switch is a real "
            "engineering problem, not a mode flag.", "key"))
        self.add(ia)

        i1 = Card("push the arm into a wall, and choose the wrong paradigm")
        i1.add(body(
            "The arm approaches a surface and presses. You choose the "
            "controller and the environment's stiffness.<br><br>"
            "<b>Three things to do:</b><br>"
            "&nbsp;&nbsp;<b>1.</b> Position control against a stiff wall. The "
            "contact force is stiffness × penetration and the penetration is "
            "your position error — read the peak force and imagine it against "
            "a person.<br>"
            "&nbsp;&nbsp;<b>2.</b> Impedance against the same wall. The force "
            "is bounded by your chosen K, and it stays bounded as the wall "
            "gets stiffer. <b>That boundedness is the safety argument</b>, "
            "and it is by construction rather than by watchdog.<br>"
            "&nbsp;&nbsp;<b>3.</b> Admittance against a stiff wall. Watch it "
            "oscillate, then soften the wall and watch it become the best of "
            "the three. Same controller, same gains, opposite verdict — "
            "because the verdict was never about the controller.", dim=True))
        self.cmb_ctrl = QComboBox()
        for lab, key in (("position control (stiff PD)", "pos"),
                         ("impedance control", "imp"),
                         ("admittance control", "adm")):
            self.cmb_ctrl.addItem(lab, key)
        self.cmb_ctrl.setCurrentIndex(1)
        self.cmb_ctrl.currentIndexChanged.connect(self._redraw_contact)
        i1.add_layout(labelled("Controller", self.cmb_ctrl, width=75))
        self.s_kenv = slider(1, 600, 200)        # x100 N/m  -> 100 .. 60 000
        self.s_kctrl = slider(5, 600, 80)        # x100 N/m  -> 500 .. 60 000
        self.s_over = slider(1, 60, 15)          # mm of commanded overshoot
        self.l_kenv, self.l_kctrl, self.l_over = QLabel(), QLabel(), QLabel()
        i1.add_layout(slider_row("environment k (×100 N/m)", self.s_kenv,
                                 self.l_kenv))
        i1.add_layout(slider_row("controller K (×100 N/m)", self.s_kctrl,
                                 self.l_kctrl))
        i1.add_layout(slider_row("commanded past surface (mm)", self.s_over,
                                 self.l_over))
        self.st_pf = Stat("peak contact force", "--", theme.BAD)
        self.st_ss = Stat("steady force", "--", theme.ACCENT)
        self.st_osc = Stat("stable?", "--", theme.GOOD)
        self.st_safe = Stat("safe on a person?", "--", theme.VIOLET)
        i1.add_layout(stat_row(self.st_pf, self.st_ss, self.st_osc,
                               self.st_safe))
        self.c1 = MplCanvas(width=7.6, height=2.8, ncols=2)
        i1.add(self.c1)
        self.t1 = body("", dim=True)
        i1.add(self.t1)
        self.add(i1)
        for s in (self.s_kenv, self.s_kctrl, self.s_over):
            s.valueChanged.connect(self._redraw_contact)
        self._redraw_contact()

        # ---- classical methods -----------------------------------------
        self.add(hline())
        self.add(title("PID, lead-lag, LQR — where each one sits on this arm"))
        self.add(_tbl(
            ["Method", "Where on the arm", "Why there, and not elsewhere"],
            [("PD + gravity feedforward",
              "every joint, always, underneath everything else",
              "The workhorse. Gravity compensation is what lets K be low "
              "without sagging — the same τ_ff argument as the impedance "
              "pages, and on an arm it is a function of configuration rather "
              "than a constant."),
             ("PID",
              "joints with unmodelled friction, and only there",
              "The I term's real job on an arm is stiction and gearbox "
              "friction, not gravity — gravity should be feedforward because "
              "you know it. Integral against a known load is a slow "
              "workaround for a calculation you could have done."),
             ("Lead compensator",
              "the shoulder, to raise crossover without exciting the "
              "structural mode",
              "The most useful classical tool on a geared arm. Note the "
              "constraint: you are raising crossover toward a resonance, so "
              "the lead and the notch are competing for the same decade."),
             ("Notch",
              "the first structural mode, and reluctantly",
              "The resonance moves with configuration and payload — which is "
              "exactly the drift case the lead-lag page warns about, except "
              "here the drift is not slow ageing, it is <i>every time the arm "
              "moves</i>. Either schedule the notch with configuration or do "
              "not use one."),
             ("Pole placement",
              "per-joint, at a nominal configuration, to sanity-check a "
              "design",
              "Four states per two joints is small enough that pole placement "
              "is meaningful. It still says nothing about torque."),
             ("LQR",
              "the natural home of a gain schedule: solve at a grid of "
              "configurations and interpolate K(q)",
              "MIMO and coupled, weights in engineering units, and the "
              "configuration-dependence that made a fixed gain fail on the "
              "first arm page is handled by re-solving rather than "
              "re-tuning."),
             ("Computed torque  (inverse dynamics)",
              "the feedforward path on any arm that moves fast",
              "This is the nonlinear-pages answer and the correct one when "
              "you have a model: cancel M(q)q̈ + C + G exactly, and what "
              "remains for feedback is a decoupled double integrator per "
              "joint. Its weakness is that it is only as good as your "
              "model."),
             ("Hybrid force/position",
              "surface tasks, with the split chosen in task coordinates",
              "Force normal, position tangential. The subtlety is that the "
              "split is defined by the contact geometry, so it has to be "
              "re-computed as the tool moves over a curved surface."),
             ("Imitation learning / RL",
              "contact-rich assembly, and anything where the model runs out",
              "Insertion under uncertainty, deformable objects, "
              "cluttered grasping. Same caveat as the biped: the impedance "
              "loop underneath stays classical, and it is what makes it safe "
              "to let a policy be wrong.")],
            col0=160, colw=280, height=690))

        self.add(callout(
            "<b>Biped and arm, side by side, one last time.</b><br><br>"
            "&nbsp;&nbsp;• The biped's schedule is driven by <b>time</b> — "
            "the gait cycle — and its hard constraint is <b>geometric</b>: "
            "the CoP must stay under the foot.<br>"
            "&nbsp;&nbsp;• The arm's schedule is driven by <b>contact "
            "state</b>, and its hard constraint is <b>force</b>: do not "
            "exceed what the object, the tool, or the person can take.<br><br>"
            "Both end up running the same joint-level law — τ = −K(θ−θ_d) − "
            "Bθ̇ + τ_ff — with K, B and τ_ff scheduled by something above. "
            "<b>That is the whole of this tutor in one equation, and the four "
            "hundred pages behind it are about where those three numbers come "
            "from and what happens when they are wrong.</b>", "good"))
        self.finish()

    # ------------------------------------------------------------------
    def _redraw_contact(self):
        kenv = self.s_kenv.value() * 100.0
        kc = self.s_kctrl.value() * 100.0
        over = self.s_over.value() / 1000.0
        mode = self.cmb_ctrl.currentData()
        self.l_kenv.setText(f"{kenv:.0f} N/m")
        self.l_kctrl.setText(f"{kc:.0f} N/m")
        self.l_over.setText(f"{over*1000:.0f} mm")

        m = 2.5                      # apparent mass of the tool + last link
        k_pos = 3.0e5                # a stiff position loop, for comparison
        dt = 5e-5
        n = int(1.2 / dt)
        x = -0.02
        v = 0.0
        xd = over               # commanded target, PAST the surface at x = 0
        xs, fs, ts = [], [], []
        mv, vv = 0.0, 0.0       # admittance virtual model state
        unstable = False
        keep = max(1, n // 1200)
        for i in range(n):
            t = i * dt
            # one-sided contact: the surface pushes back only while penetrated
            f_env = (-kenv * x - 0.02 * kenv * v) if x > 0.0 else 0.0
            if mode == "pos":
                u = k_pos * (xd - x) - 2.0 * 0.9 * math.sqrt(k_pos * m) * v
            elif mode == "imp":
                u = kc * (xd - x) - 2.0 * 0.9 * math.sqrt(kc * m) * v
            else:
                # admittance: the measured force drives a light virtual model
                # (mass m_v, damping b_v), and a stiff inner position loop
                # chases wherever that model went. The instability is real and
                # is the point: when the environment is stiffer than the
                # virtual model, this loop has gain above one.
                m_v, b_v, k_v = 1.2, 55.0, 3000.0
                vv += ((-f_env) - b_v * vv - k_v * mv) / m_v * dt
                mv += vv * dt
                u = k_pos * ((xd + mv) - x) - 2.0 * 0.9 * math.sqrt(
                    k_pos * m) * v
            v += (u + f_env) / m * dt
            x += v * dt
            if i % keep == 0:
                ts.append(t)
                xs.append(x)
                fs.append(-f_env)
            if abs(x) > 0.5 or not math.isfinite(x):
                unstable = True
                break

        fs_arr = np.array(fs)
        peak = float(np.max(np.abs(fs_arr))) if len(fs_arr) else 0.0
        tail = fs_arr[int(len(fs_arr) * 0.7):] if len(fs_arr) > 10 else fs_arr
        steady = float(np.mean(tail)) if len(tail) else 0.0
        ripple = float(np.std(tail)) if len(tail) else 0.0
        osc = unstable or ripple > 0.15 * max(abs(steady), 1.0)

        self.st_pf.set(f"{peak:.0f} N")
        self.st_pf.set_color(theme.BAD if peak > 150 else theme.GOOD)
        self.st_ss.set(f"{steady:.0f} N")
        self.st_osc.set("UNSTABLE" if unstable else
                        ("ringing" if osc else "stable"))
        self.st_osc.set_color(theme.BAD if osc else theme.GOOD)
        self.st_safe.set("no" if peak > 150 else "yes")
        self.st_safe.set_color(theme.BAD if peak > 150 else theme.GOOD)

        if mode == "pos":
            self.t1.setText(
                f"<b>Position control: {peak:.0f} N peak.</b> The force is "
                f"the joint's stiffness times how far past the surface you "
                f"commanded — {over*1000:.0f} mm of commanded overshoot "
                f"against a {kenv:.0f} N/m wall. Nothing here is a tuning "
                f"failure; the controller is doing exactly its job, which is "
                f"to reach a position, and the object is in the way. "
                "Increase the commanded overshoot and the force grows without "
                "limit. This is why a position-controlled arm needs a fence.")
        elif mode == "imp":
            self.t1.setText(
                f"<b>Impedance control: {peak:.0f} N peak, {steady:.0f} N "
                f"steady.</b> The force is bounded by K × penetration and K "
                f"is yours to choose — raise the wall stiffness and the force "
                f"barely moves, because the compliant element is now the "
                f"robot rather than the wall. <b>That is safety by "
                f"construction</b>: bound the displacement and you have "
                "bounded the force, with no sensor and no watchdog in the "
                "argument. The price is that this arm cannot render a "
                "stiffness higher than its own structure.")
        else:
            self.t1.setText(
                f"<b>Admittance control against a {kenv:.0f} N/m "
                f"environment: {'unstable' if unstable else ('ringing' if osc else 'stable')}.</b> "
                f"Admittance measures force and moves a virtual model, so the "
                f"loop goes force → motion → more force. When the environment "
                f"is stiffer than the virtual model, that loop has gain above "
                f"one and it buzzes. Soften the wall — take it toward what a "
                f"human hand feels like — and the same controller becomes the "
                "best of the three, rendering an apparent mass lighter than "
                "the arm actually is, which impedance cannot do.")

        c = self.c1
        c.clear()
        a1, a2 = c.axes
        a1.plot(ts, np.array(xs) * 1000, color=theme.ACCENT, lw=2.0,
                label="tool position")
        a1.axhline(0, color=theme.BAD, lw=1.6, ls="--", label="surface")
        a1.axhline(over * 1000, color=theme.TEXT_FAINT, lw=1.2, ls=":",
                   label="commanded")
        a1.set_xlabel("time (s)")
        a1.set_ylabel("position (mm)")
        a1.set_title("approach and press", fontsize=8.5)
        c.legend(a1, loc="lower right")

        a2.plot(ts, fs, color=theme.BAD, lw=2.0)
        a2.axhline(150, color=theme.WARN, lw=1.4, ls="--",
                   label="safe on a person")
        a2.set_xlabel("time (s)")
        a2.set_ylabel("contact force (N)")
        a2.set_title("what the object feels", fontsize=8.5)
        c.legend(a2, loc="upper right")
        c.refresh()
