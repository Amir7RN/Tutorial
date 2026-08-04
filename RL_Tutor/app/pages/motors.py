"""
Pages 1-5: Motor selection, and the one question that decides it.

  1  Effective Inertia   -- the vocabulary, then direct drive from first principles
  2  Series Elastic      -- the spring between motor and load, derived in full
  3  Parallel Elastic    -- the spring alongside, and negative effective inertia
  4  DD vs SEA vs PEA    -- torque, speed, inertia, bandwidth, responsiveness
  5  Gearing             -- the N^2 square law and the death of transparency

The order is deliberate. You cannot argue about impedance control until you
know what the environment actually feels when it touches the robot, and that
number -- J_eff -- is set by mechanics long before any software runs.
"""

from __future__ import annotations

import math

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
)

from ctrlcore.actuators import (
    TOPOLOGY_NAMES,
    gear_output,
    gravity_torque,
    j_eff,
    j_eff_direct,
    j_eff_pea,
    j_eff_sea,
    motor_torque_pea,
    pea_resonance_rad_s,
    reflected_inertia,
    sea_bandwidth_hz,
    spring_torque,
)
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

SECTION = "Actuators"


# --------------------------------------------------------------------------
# small shared helper
# --------------------------------------------------------------------------

def slider(lo, hi, val, step=1):
    s = QSlider(Qt.Horizontal)
    s.setRange(lo, hi)
    s.setValue(val)
    s.setSingleStep(step)
    return s


def slider_row(label, sld, readout):
    lay = QHBoxLayout()
    lay.setSpacing(8)
    lb = QLabel(label)
    lb.setStyleSheet(f"color:{theme.TEXT_DIM}; background:transparent;")
    lb.setFixedWidth(150)
    lay.addWidget(lb)
    lay.addWidget(sld, 1)
    readout.setStyleSheet(
        f"color:{theme.ACCENT}; font-family:Consolas; font-weight:700;"
        f"background:transparent; min-width:78px;")
    lay.addWidget(readout)
    return lay


# ==========================================================================
# PAGE 1 -- Effective inertia and direct drive
# ==========================================================================

class EffectiveInertiaPage(Page):
    TITLE = "Effective Inertia"
    SUBTITLE = ("Before any controller exists, mechanics has already decided how "
                "heavy your robot feels to whoever touches it.")
    SECTION = SECTION
    NOTES = "material p.1-3"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>The question this whole section answers.</b> You grab the output "
            "shaft of a robot joint and shake it. How much mass do you feel?<br><br>"
            "Not \"how much does the robot weigh\" — how much <i>inertia is "
            "presented at the point of contact</i>. That number is called the "
            "<b>effective inertia</b> J<sub>eff</sub>, and it is the single number "
            "that decides whether your robot is safe to stand next to, whether it "
            "can feel a human push, and how fast it can react.<br><br>"
            "Three mechanical layouts give three completely different answers. "
            "Same motor, same limb.", "key"))

        v = Card("the four symbols, used everywhere below")
        v.add(body(
            "<table cellpadding='6'>"
            "<tr><td><b>J<sub>m</sub></b></td><td>motor (rotor) inertia — the "
            "spinning mass inside the motor itself</td></tr>"
            "<tr><td><b>J<sub>L</sub></b></td><td>limb / load inertia — the arm, "
            "leg or tool bolted to the output</td></tr>"
            "<tr><td><b>k</b></td><td>spring stiffness, if there is a spring "
            "anywhere in the drivetrain</td></tr>"
            "<tr><td><b>ω</b></td><td>frequency of the interaction — how fast the "
            "outside world is pushing on the joint</td></tr>"
            "</table>"))
        v.add(body(
            "That last one is the one people forget. <b>ω is not a property of "
            "the robot.</b> It is a property of what is happening to it. A slow "
            "lean and a sharp impact are the same joint at two different "
            "frequencies — and, as the next two pages show, they can feel like "
            "two completely different machines.", dim=True))
        self.add(v)

        self.add(hline())

        # ---- direct drive derivation -------------------------------------
        self.add(title("① Direct Drive — no compliance, muscle CE, precise and fast"))
        self.add(body(
            "Motor bolted straight to the limb (or through a very low-ratio "
            "gearbox — <i>quasi-</i>direct drive, QDD). Nothing elastic anywhere. "
            "The two bodies are welded into one body, so they share one "
            "acceleration."))

        d = Card("derivation")
        d.add(math_label(r"J_m\,\ddot\theta_m = \tau - J_L\,\ddot\theta"))
        d.add(body("Motor and limb move together, so θ<sub>m</sub> = θ. Collect "
                   "them:", dim=True))
        d.add(math_label(r"(J_m + J_L)\,\ddot\theta = \tau"))
        d.add(body("Divide by the acceleration and read off what the world feels:",
                   dim=True))
        d.add(math_label(r"\boxed{\;J_{eff} = J_m + J_L\;}", 18))
        d.add(body(
            "<b>No ω anywhere.</b> The answer is the same whether you lean on it "
            "for ten seconds or hit it in one millisecond. Hit a wall, move "
            "slowly — either way you feel the combined mass of motor <i>and</i> "
            "limb.", dim=True))
        self.add(d)

        self.add(callout(
            "<b>Why this is dangerous.</b> High-torque direct drive is risky "
            "around humans: there is nothing between the rotor and the person. "
            "A fast impact drives the full J<sub>m</sub> + J<sub>L</sub> into "
            "whatever it hit — and into the motor's own magnets and bearings on "
            "the way back.<br><br>"
            "<b>Unless</b> you pair it with external compliance. A soft skin, a "
            "compliant end-effector, a remote centre of compliance — put the give "
            "somewhere else and direct drive becomes acceptable again.", "warn"))

        # ---- interactive --------------------------------------------------
        i = Card("feel it: direct drive is flat in frequency")
        i.add(body(
            "Slide the two inertias. The curve is what an outside push feels "
            "across the whole frequency range — and for direct drive it is a "
            "flat line at J<sub>m</sub> + J<sub>L</sub>. Remember this shape; "
            "the next two pages break it.", dim=True))

        self.s_jm = slider(1, 200, 40)
        self.s_jl = slider(1, 200, 60)
        self.l_jm = QLabel()
        self.l_jl = QLabel()
        i.add_layout(slider_row("Motor  Jₘ", self.s_jm, self.l_jm))
        i.add_layout(slider_row("Limb  Jʟ", self.s_jl, self.l_jl))

        self.st_sum = Stat("J_eff  (kg·m²)", "--", theme.ACCENT)
        self.st_ratio = Stat("rotor share", "--", theme.WARN)
        i.add_layout(stat_row(self.st_sum, self.st_ratio))

        self.canvas = MplCanvas(width=7.4, height=2.9)
        i.add(self.canvas)
        self.add(i)

        self.s_jm.valueChanged.connect(self._redraw)
        self.s_jl.valueChanged.connect(self._redraw)
        self._redraw()

        self.add(callout(
            "The rotor share is the number to watch. On a direct-drive joint the "
            "motor's own mass is <b>always visible</b> to the world — it is never "
            "hidden, at any speed. Everything that follows is an attempt to hide "
            "it without giving up the ability to feel.", "key"))

        self.finish()

    def _vals(self):
        return self.s_jm.value() / 1000.0, self.s_jl.value() / 1000.0

    def _redraw(self):
        jm, jl = self._vals()
        self.l_jm.setText(f"{jm:.3f}")
        self.l_jl.setText(f"{jl:.3f}")
        tot = j_eff_direct(jm, jl)
        self.st_sum.set(f"{tot:.3f}")
        self.st_ratio.set(f"{100.0 * jm / tot:.0f}%")

        c = self.canvas
        c.clear()
        ws = [10 ** (x / 40.0) for x in range(-40, 121)]
        c.ax.semilogx(ws, [tot] * len(ws), color=theme.ACCENT, lw=2.4,
                      label="direct drive")
        c.ax.semilogx(ws, [jl] * len(ws), color=theme.TEXT_FAINT, lw=1.2,
                      ls="--", label="limb alone (Jʟ)")
        c.ax.set_xlabel("interaction frequency ω  (rad/s)")
        c.ax.set_ylabel("J_eff  (kg·m²)")
        c.ax.set_ylim(0, max(tot * 1.35, 0.01))
        c.legend(loc="lower left")
        c.refresh()


# ==========================================================================
# PAGE 2 -- Series elastic actuator
# ==========================================================================

class SEAPage(Page):
    TITLE = "Series Elastic Actuators"
    SUBTITLE = ("Put a spring between motor and load and the effective inertia "
                "stops being a number — it becomes a function of frequency.")
    SECTION = SECTION
    NOTES = "material p.2"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>The idea in one line.</b> If the robot hits something, let the "
            "spring compress <i>first</i> and absorb the energy before the motor "
            "can be damaged — or before the motor can do damage.<br><br>"
            "The spring is <b>passive</b>. It does not need electricity or a "
            "computer. A 1 kHz control loop takes 1.0 ms just to think; a spring "
            "compresses in 0.1 ms. The spring protects the human before the "
            "software even knows a collision happened.", "key"))

        # ---- derivation ---------------------------------------------------
        d = Card("derivation — two bodies now, not one")
        d.add(body(
            "The spring separates motor and load, so they are no longer the same "
            "body. Two equations, two angles:"))
        d.add(math_label(r"J_m\,\ddot\theta_m = -k\,(\theta_m - \theta_L)"))
        d.add(math_label(r"J_L\,\ddot\theta_L = k\,(\theta_m - \theta_L) + \tau_L"))
        d.add(body("Laplace the first and solve for the motor angle:", dim=True))
        d.add(math_label(r"(J_m s^2 + k)\,\theta_m = k\,\theta_L"
                         r"\quad\Rightarrow\quad "
                         r"\theta_m = \frac{k}{k + J_m s^2}\,\theta_L"))
        d.add(body("Substitute into the second and collect θ<sub>L</sub>:",
                   dim=True))
        d.add(math_label(r"\left[J_L s^2 + \frac{k\,J_m s^2}{k + J_m s^2}\right]"
                         r"\theta_L = \tau_L"))
        d.add(math_label(r"\boxed{\;J_{eff}(s) = J_L + "
                         r"\frac{k\,J_m}{k + J_m s^2}\;}", 18))
        d.add(body("On the imaginary axis s = jω, so s² = −ω²:", dim=True))
        d.add(math_label(r"J_{eff}(\omega) = J_L + \frac{k\,J_m}{k - J_m\omega^2}",
                         16))
        self.add(d)

        # ---- the two limits ----------------------------------------------
        lim = Card("the two limits — this is the whole argument for SEAs")
        g = QGridLayout()
        g.setSpacing(12)
        g.setColumnStretch(0, 1)
        g.setColumnStretch(1, 1)

        lo = Card("ω → 0   (slow push)")
        lo.add(math_label(r"J_{eff} \rightarrow J_L + J_m", 16))
        lo.add(body(
            "The spring is stiff enough to <b>move the motor</b>. Push slowly and "
            "you drag the whole machine along — you feel exactly what direct "
            "drive would give you. No benefit at all down here."))
        g.addWidget(lo, 0, 0)

        hi = Card("ω → ∞   (high-speed impact)")
        hi.add(math_label(r"J_{eff} \rightarrow J_L", 16))
        hi.add(body(
            "The motor's inertia cannot accelerate that fast, so the spring takes "
            "essentially all the relative motion and stores the disturbance "
            "energy. The spring <b>decouples motor from limb</b>, and the "
            "environment just feels the light limb.<br><br>"
            "<b>This is the safety mechanism.</b> The rotor is mechanically "
            "hidden during exactly the events that would hurt someone."))
        g.addWidget(hi, 0, 1)
        lim.add_layout(g)
        self.add(lim)

        # ---- interactive ---------------------------------------------------
        i = Card("watch the transition")
        i.add(body(
            "Drag the stiffness. Low k moves the whole transition to low "
            "frequency: safer, but the joint goes mushy and slow. High k pushes "
            "it right: crisper and faster, but the spring stops protecting "
            "anything until the impact is very fast indeed.", dim=True))

        self.s_jm = slider(1, 200, 40)
        self.s_jl = slider(1, 200, 60)
        self.s_k = slider(5, 4000, 300)
        self.l_jm, self.l_jl, self.l_k = QLabel(), QLabel(), QLabel()
        i.add_layout(slider_row("Motor  Jₘ", self.s_jm, self.l_jm))
        i.add_layout(slider_row("Limb  Jʟ", self.s_jl, self.l_jl))
        i.add_layout(slider_row("Spring  k  (N·m/rad)", self.s_k, self.l_k))

        self.st_bw = Stat("bandwidth f_n", "--", theme.GOOD)
        self.st_anti = Stat("antiresonance", "--", theme.BAD)
        self.st_hi = Stat("J_eff at impact", "--", theme.ACCENT)
        i.add_layout(stat_row(self.st_bw, self.st_anti, self.st_hi))

        self.canvas = MplCanvas(width=7.4, height=3.1)
        i.add(self.canvas)
        self.add(i)

        for s in (self.s_jm, self.s_jl, self.s_k):
            s.valueChanged.connect(self._redraw)
        self._redraw()

        # ---- bandwidth ------------------------------------------------------
        bw = Card("the mechanical low-pass filter")
        bw.add(body(
            "The spring and the load form a resonant pair with natural "
            "frequency"))
        bw.add(math_label(r"f_n = \frac{1}{2\pi}\sqrt{\frac{k}{J_L}}", 17))
        bw.add(body(
            "Try to command the joint faster than f<sub>n</sub> and the spring "
            "simply absorbs the motion instead of passing it to the arm. That is "
            "what \"the spring is a low-pass filter\" means, literally."))
        bw.add(body(
            "<b>What \"bandwidth\" means here — precisely.</b> When people say "
            "\"SEAs have lower bandwidth\" they are <i>not</i> talking about "
            "sensor bandwidth or controller sampling rate. They mean: <b>the "
            "fastest frequency at which joint torque can be accurately "
            "controlled and modified.</b> How quickly can the actuator change "
            "force at the joint in response to a disturbance? This is a "
            "<b>physical limit, not a software one.</b> Sample at 10 kHz with a "
            "perfect control law and you are still bounded by "
            "τ<sub>response</sub> ≥ 1/ω<sub>n</sub>."))
        bw.add(body(
            "<table cellpadding='6'>"
            "<tr><td><b>Direct drive</b></td><td>50–100 Hz or higher</td></tr>"
            "<tr><td><b>SEA</b></td><td>often limited to 10–20 Hz</td></tr>"
            "</table>"
            "10 Hz is fine for walking. It is too slow for a cat-like reflex or "
            "for catching a falling object."))
        self.add(bw)

        self.add(callout(
            "<b>Why the motor needs to \"feel the world\" at all.</b> Control is "
            "not about <i>knowing</i> force; it is about <b>reacting fast enough "
            "to shape the interaction</b>. Force sensors tell you what happened. "
            "Motor transparency determines whether you can prevent what happens "
            "next.<br><br>"
            "In humans, muscles are <b>directly coupled</b> to joints — there is "
            "no compliant spring isolating the nervous system from the joint, so "
            "force propagates immediately into muscle tension. Spindles give "
            "velocity, Golgi tendon organs give force, reflexes act in 30–50 ms, "
            "and passive tissue stiffness acts at <b>0 ms</b>.<br><br>"
            "With an SEA the chain is joint → spring → motor. Fast disturbances "
            "are absorbed by spring deflection, motor torque only changes "
            "<i>after</i> the deflection, and the reflex-like response is "
            "delayed. That delay is mechanical and no amount of sampling rate "
            "removes it.", "key"))

        pc = Card("pros and cons, plainly")
        pc.add(body(
            "<b>Pros</b><br>"
            "• <b>Mechanical low-pass filter (safety).</b> At impact frequencies "
            "the spring absorbs energy before it reaches the motor: "
            "J<sub>eff</sub> ≈ J<sub>L</sub>. Protects robot and human.<br>"
            "• <b>Force sensing for free.</b> Measure the spring's deflection and "
            "you have a torque sensor. No strain gauges needed — you only need to "
            "know how much the spring bent.<br>"
            "• <b>Energy storage.</b> Like a tendon: store energy in one phase of "
            "the gait and release it in the next.<br><br>"
            "<b>Cons</b><br>"
            "• <b>Lower bandwidth.</b> The spring introduces lag. You cannot move "
            "the joint faster than the spring-mass resonance.<br>"
            "• <b>Stability is harder.</b> Motor and load are separated by a "
            "spring — they are <b>non-collocated</b>. High-frequency control "
            "gains can excite structural resonances and go unstable. Controlling "
            "an SEA at 1 kHz is harder than controlling a direct drive.<br><br>"
            "<b>Best for:</b> humanoids in home environments (1X Neo, Agility "
            "Digit) where safety is the #1 requirement. You sacrifice high-speed "
            "precision to gain passive shock tolerance and high-fidelity force "
            "sensing."))
        self.add(pc)

        self.finish()

    def _vals(self):
        return (self.s_jm.value() / 1000.0,
                self.s_jl.value() / 1000.0,
                float(self.s_k.value()))

    def _redraw(self):
        jm, jl, k = self._vals()
        self.l_jm.setText(f"{jm:.3f}")
        self.l_jl.setText(f"{jl:.3f}")
        self.l_k.setText(f"{k:.0f}")

        self.st_bw.set(f"{sea_bandwidth_hz(k, jl):.1f} Hz")
        self.st_anti.set(f"{math.sqrt(k / jm):.0f} rad/s")
        self.st_hi.set(f"{jl:.3f}")

        c = self.canvas
        c.clear()
        ws = [10 ** (x / 40.0) for x in range(-40, 141)]
        anti = math.sqrt(k / jm)

        below = [w for w in ws if w < anti * 0.985]
        above = [w for w in ws if w > anti * 1.015]
        for seg, lab in ((below, "SEA"), (above, None)):
            if seg:
                c.ax.semilogx(seg, [j_eff_sea(jm, jl, k, w) for w in seg],
                              color=theme.GOOD, lw=2.4, label=lab)
        c.ax.axhline(jm + jl, color=theme.TEXT_FAINT, lw=1.1, ls="--",
                     label="Jₘ+Jʟ  (ω→0)")
        c.ax.axhline(jl, color=theme.ACCENT, lw=1.1, ls=":",
                     label="Jʟ  (ω→∞)")
        c.ax.axvline(anti, color=theme.BAD, lw=1.0, alpha=0.7)
        c.ax.text(anti, (jm + jl) * 1.5, "  antiresonance\n  √(k/Jₘ)",
                  color=theme.BAD, fontsize=7.5, va="bottom")
        c.ax.set_xlabel("interaction frequency ω  (rad/s)")
        c.ax.set_ylabel("J_eff  (kg·m²)")
        c.ax.set_ylim(0, (jm + jl) * 2.6)
        c.legend(loc="upper right")
        c.refresh()


# ==========================================================================
# PAGE 3 -- Parallel elastic actuator
# ==========================================================================

class PEAPage(Page):
    TITLE = "Parallel Elastic Actuators"
    SUBTITLE = ("Spring alongside the motor instead of between. Buys energy, "
                "not safety — and can make the joint feel lighter than nothing.")
    SECTION = SECTION
    NOTES = "material p.3"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "In a PEA a passive spring is added <b>next to</b> the motor. Motor "
            "and spring work together to move the same load. Crucially, motor and "
            "load are still <b>rigidly connected</b> — so unlike an SEA, a hit to "
            "the arm still goes straight into the motor's gears.", "key"))

        d = Card("derivation — one body again, plus a spring torque")
        d.add(math_label(r"\tau_{ext} = J_L\ddot\theta + J_m\ddot\theta + k\theta"))
        d.add(math_label(r"= (J_m + J_L)s^2\theta + k\theta "
                         r"= \left[(J_m+J_L)s^2 + k\right]\theta"))
        d.add(body("Divide by s²θ to read off the inertia:", dim=True))
        d.add(math_label(r"\boxed{\;\frac{\tau_{ext}}{s^2\theta} = "
                         r"J_{eff} = (J_m + J_L) + \frac{k}{s^2}\;}", 18))
        d.add(body("With s = jω:", dim=True))
        d.add(math_label(r"J_{eff}(\omega) = (J_m + J_L) - \frac{k}{\omega^2}", 16))
        self.add(d)

        r = Card("three regimes — and one of them is strange")
        r.add(body(
            "<b>ω → ∞ &nbsp;(fast).</b> The k/ω² term goes to zero and "
            "J<sub>eff</sub> ≈ J<sub>m</sub> + J<sub>L</sub>. Shake the robot "
            "fast and the spring has no time to help. You feel the full weight of "
            "motor <i>and</i> load. <b>A PEA gives no impact protection.</b>"))
        r.add(body(
            "<b>ω → 0 &nbsp;(slow).</b> The k/ω² term becomes very large and the "
            "effective inertia goes <b>large and negative</b>. This is gravity "
            "compensation: move slowly and the stored spring torque pushes the "
            "load for you. The joint behaves as if it had <i>negative mass</i> — "
            "it wants to accelerate on its own from the stored spring energy."))
        r.add(body(
            "<b>ω = √(k/(J<sub>m</sub>+J<sub>L</sub>)) &nbsp;(resonance).</b> "
            "J<sub>eff</sub> = 0 exactly. Spring and inertia cancel and you can "
            "move the joint with almost zero effort."))
        self.add(r)

        # ---- interactive 1: frequency ---------------------------------------
        i = Card("effective inertia vs frequency")
        self.s_jm = slider(1, 200, 40)
        self.s_jl = slider(1, 200, 60)
        self.s_k = slider(5, 2000, 200)
        self.l_jm, self.l_jl, self.l_k = QLabel(), QLabel(), QLabel()
        i.add_layout(slider_row("Motor  Jₘ", self.s_jm, self.l_jm))
        i.add_layout(slider_row("Limb  Jʟ", self.s_jl, self.l_jl))
        i.add_layout(slider_row("Spring  k  (N·m/rad)", self.s_k, self.l_k))

        self.st_res = Stat("J_eff = 0 at", "--", theme.VIOLET)
        self.st_hi = Stat("J_eff at impact", "--", theme.BAD)
        i.add_layout(stat_row(self.st_res, self.st_hi))

        self.canvas = MplCanvas(width=7.4, height=3.0)
        i.add(self.canvas)
        self.add(i)

        for s in (self.s_jm, self.s_jl, self.s_k):
            s.valueChanged.connect(self._redraw)

        # ---- gravity compensation ------------------------------------------
        self.add(hline())
        self.add(title("Why a PEA exists: gravity compensation"))

        g = Card("the torque balance")
        g.add(body(
            "Picture a knee holding up a leg. Three torques act on the joint:"))
        g.add(body(
            "&nbsp;&nbsp;<b>τ<sub>g</sub></b> — gravity, pulling the leg down<br>"
            "&nbsp;&nbsp;<b>τ<sub>s</sub></b> — the spring, pushing it up<br>"
            "&nbsp;&nbsp;<b>τ<sub>m</sub></b> — the motor's effort to hold position"))
        g.add(math_label(r"\tau_m + \tau_s(\theta) = \tau_g(\theta)"))
        g.add(body("Gravity compensation means the motor does nothing "
                   "(τ<sub>m</sub> = 0), which happens when", dim=True))
        g.add(math_label(r"\tau_s(\theta) = \tau_g(\theta)"))
        g.add(body("Write both out — a straight line trying to match a sine:",
                   dim=True))
        g.add(math_label(r"\tau_g = m\,g\,L\sin\theta \qquad "
                         r"\tau_s = k\,(\theta_0 - \theta)"))
        g.add(math_label(r"k\,(\theta_0 - \theta) \approx m\,g\,L\,\sin\theta", 16))
        self.add(g)

        i2 = Card("tune the spring, watch the motor's workload")
        i2.add(body(
            "The green curve is what the motor must still supply. Where it "
            "crosses zero the spring is doing <b>100% of the work</b> and the "
            "motor draws no current at all — no heat, no battery drain. You can "
            "only get that at one or two angles: pick the pose the robot holds "
            "the longest.", dim=True))
        self.s_k2 = slider(1, 300, 90)
        self.s_th0 = slider(-90, 90, 55)
        self.s_mass = slider(1, 200, 60)
        self.l_k2, self.l_th0, self.l_mass = QLabel(), QLabel(), QLabel()
        i2.add_layout(slider_row("Spring  k", self.s_k2, self.l_k2))
        i2.add_layout(slider_row("Rest angle  θ₀  (°)", self.s_th0, self.l_th0))
        i2.add_layout(slider_row("Limb mass  (×0.5 kg)", self.s_mass, self.l_mass))
        self.canvas2 = MplCanvas(width=7.4, height=3.0)
        i2.add(self.canvas2)
        self.add(i2)

        for s in (self.s_k2, self.s_th0, self.s_mass):
            s.valueChanged.connect(self._redraw_grav)

        self._redraw()
        self._redraw_grav()

        pc = Card("pros and cons")
        pc.add(body(
            "<b>Pros</b><br>"
            "• <b>Gravity compensation.</b> Tune the spring to hold the robot's "
            "weight and the motor uses <b>zero power</b> to stand still.<br>"
            "• <b>High peak torque.</b> Motor and spring pulling together beat "
            "the motor alone.<br>"
            "• <b>Efficiency.</b> Excellent for cyclic tasks — the bounce of a "
            "bipedal run.<br><br>"
            "<b>Cons</b><br>"
            "• <b>No impact protection.</b> The motor is still rigidly connected "
            "to the joint. A hit goes straight to the gears.<br>"
            "• <b>Asymmetric effort.</b> A spring that helps you <i>stand up</i> "
            "actively <b>fights</b> you when you <i>squat down</i>. Standing: "
            "gravity pulls down, spring pulls up, they help each other, "
            "τ<sub>m</sub> is tiny. Squatting: gravity still pulls down, but now "
            "the spring <i>also</i> pulls up — the motor must push against the "
            "spring to bend the joint.<br><br>"
            "A PEA tunes the robot to be very efficient at <b>one specific "
            "task</b> at the cost of making other movements harder."))
        self.add(pc)

        self.add(callout(
            "<b>SEA vs PEA in one line each.</b><br><br>"
            "<b>SEA</b> — motor → spring → load. Primary benefit: <b>safety and "
            "impacts</b>. It <i>decouples</i> J<sub>m</sub> at high "
            "frequencies.<br>"
            "<b>PEA</b> — motor ∥ spring → load. Primary benefit: <b>energy "
            "efficiency</b>. It <i>subtracts</i> inertia at low frequencies "
            "(gravity comp).<br><br>"
            "They are not competitors — a real humanoid often wants SEA in the "
            "ankle for balance and impact, PEA in the knee to hold up the torso "
            "without draining the battery.", "good"))

        self.finish()

    def _redraw(self):
        jm = self.s_jm.value() / 1000.0
        jl = self.s_jl.value() / 1000.0
        k = float(self.s_k.value())
        self.l_jm.setText(f"{jm:.3f}")
        self.l_jl.setText(f"{jl:.3f}")
        self.l_k.setText(f"{k:.0f}")

        wr = pea_resonance_rad_s(k, jm, jl)
        self.st_res.set(f"{wr:.0f} rad/s")
        self.st_hi.set(f"{jm + jl:.3f}")

        c = self.canvas
        c.clear()
        ws = [10 ** (x / 40.0) for x in range(-20, 141)]
        vals = [j_eff_pea(jm, jl, k, w) for w in ws]
        c.ax.semilogx(ws, vals, color=theme.VIOLET, lw=2.4, label="PEA")
        c.ax.axhline(jm + jl, color=theme.TEXT_FAINT, lw=1.1, ls="--",
                     label="Jₘ+Jʟ  (ω→∞)")
        c.ax.axhline(0, color=theme.BORDER, lw=1.0)
        c.ax.axvline(wr, color=theme.GOOD, lw=1.0, alpha=0.8)
        c.ax.text(wr, (jm + jl) * 0.55, "  J_eff = 0", color=theme.GOOD,
                  fontsize=8)
        c.ax.fill_between(ws, vals, 0, where=[v < 0 for v in vals],
                          color=theme.BAD, alpha=0.16)
        c.ax.text(ws[6], -(jm + jl) * 1.2, "negative effective inertia\n"
                  "the spring pushes for you",
                  color=theme.BAD, fontsize=7.5)
        c.ax.set_xlabel("interaction frequency ω  (rad/s)")
        c.ax.set_ylabel("J_eff  (kg·m²)")
        c.ax.set_ylim(-(jm + jl) * 2.2, (jm + jl) * 1.7)
        c.legend(loc="lower right")
        c.refresh()

    def _redraw_grav(self):
        k = float(self.s_k2.value())
        th0 = math.radians(self.s_th0.value())
        mass = self.s_mass.value() * 0.5
        length = 0.4
        self.l_k2.setText(f"{k:.0f}")
        self.l_th0.setText(f"{self.s_th0.value()}°")
        self.l_mass.setText(f"{mass:.1f} kg")

        c = self.canvas2
        c.clear()
        degs = list(range(0, 91))
        ths = [math.radians(d) for d in degs]
        tg = [gravity_torque(mass, length, t) for t in ths]
        ts = [spring_torque(k, t, th0) for t in ths]
        tm = [motor_torque_pea(mass, length, k, t, th0) for t in ths]
        c.ax.plot(degs, tg, color=theme.WARN, lw=2.0, label="τ_g  gravity")
        c.ax.plot(degs, ts, color=theme.ACCENT, lw=2.0, label="τ_s  spring")
        c.ax.plot(degs, tm, color=theme.GOOD, lw=2.6, label="τ_m  motor must supply")
        c.ax.axhline(0, color=theme.BORDER, lw=1.0)
        c.ax.set_xlabel("joint angle from vertical  (°)")
        c.ax.set_ylabel("torque  (N·m)")
        c.legend(loc="upper left")
        c.refresh()


# ==========================================================================
# PAGE 4 -- Head to head
# ==========================================================================

class ActuatorCompare(Page):
    TITLE = "DD vs SEA vs PEA"
    SUBTITLE = ("The three curves on one axis: output torque, speed, effective "
                "inertia, bandwidth and responsiveness.")
    SECTION = SECTION
    NOTES = "material p.2-3"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(body(
            "Everything so far, superimposed. Same J<sub>m</sub>, same "
            "J<sub>L</sub>, same k — three different places to put the spring."))

        i = Card("all three at once")
        self.s_jm = slider(1, 200, 40)
        self.s_jl = slider(1, 200, 60)
        self.s_k = slider(5, 2000, 300)
        self.l_jm, self.l_jl, self.l_k = QLabel(), QLabel(), QLabel()
        i.add_layout(slider_row("Motor  Jₘ", self.s_jm, self.l_jm))
        i.add_layout(slider_row("Limb  Jʟ", self.s_jl, self.l_jl))
        i.add_layout(slider_row("Spring  k", self.s_k, self.l_k))

        self.chk = {}
        row = QHBoxLayout()
        row.setSpacing(16)
        for key, colour in (("direct", theme.ACCENT), ("sea", theme.GOOD),
                            ("pea", theme.VIOLET)):
            cb = QCheckBox(TOPOLOGY_NAMES[key])
            cb.setChecked(True)
            cb.setStyleSheet(f"color:{colour};")
            cb.stateChanged.connect(self._redraw)
            self.chk[key] = cb
            row.addWidget(cb)
        row.addStretch(1)
        i.add_layout(row)

        self.canvas = MplCanvas(width=7.6, height=3.4)
        i.add(self.canvas)
        i.add(body(
            "Read the plot as a story about <b>who you are protecting from "
            "what</b>. Right-hand side = impacts. The SEA curve drops to the bare "
            "limb there; the other two do not. Left-hand side = slow "
            "interaction. The PEA curve dives negative there; the other two do "
            "not.", dim=True))
        self.add(i)

        for s in (self.s_jm, self.s_jl, self.s_k):
            s.valueChanged.connect(self._redraw)
        self._redraw()

        # ---- the table ------------------------------------------------------
        t = Card("the comparison, column by column")
        tbl = QTableWidget(7, 4)
        tbl.setHorizontalHeaderLabels(
            ["", "Direct Drive / QDD", "Series Elastic", "Parallel Elastic"])
        rows = [
            ("Effective inertia",
             "Jₘ + Jʟ, at every frequency",
             "Jₘ+Jʟ slow → Jʟ at impact",
             "Jₘ+Jʟ fast → negative when slow"),
            ("Output torque",
             "Low density: needs a big heavy motor to get torque without gears",
             "Same as the motor can give; spring adds nothing to peak",
             "Motor + spring together → higher peak torque than motor alone"),
            ("Output velocity",
             "Fast, unfiltered; limited only by the motor",
             "Limited above fₙ — the spring absorbs the motion instead",
             "Fast; spring does not restrict motion, only biases it"),
            ("Bandwidth",
             "50–100 Hz and up. No spring slop, reacts instantly",
             "10–20 Hz. Physical limit τ ≥ 1/ωₙ, not a software one",
             "High — no series compliance in the force path"),
            ("Responsiveness",
             "Crisp. Push it and the motor spins immediately",
             "Lagged. Fast disturbance deflects the spring before the motor "
             "knows",
             "Crisp, but biased: the spring is always pulling one way"),
            ("Transparency /\nbackdriveability",
             "Excellent. No friction or spring hiding the external force",
             "Good at low ω; the spring masks fast events by design",
             "Good, but the spring torque must be modelled out"),
            ("Best for",
             "Small quadrupeds (MIT Cheetah): high-speed leg swinging beats "
             "carrying heavy loads",
             "Humanoids among people (1X Neo, Agility Digit): safety is "
             "requirement #1",
             "Heavy-duty bipeds and prosthetics: battery life and weight "
             "carrying"),
        ]
        for r, cells in enumerate(rows):
            for c, v in enumerate(cells):
                it = QTableWidgetItem(v)
                it.setFlags(Qt.ItemIsEnabled)
                tbl.setItem(r, c, it)
        tbl.verticalHeader().setVisible(False)
        tbl.setWordWrap(True)
        tbl.resizeRowsToContents()
        tbl.setColumnWidth(0, 150)
        for c in (1, 2, 3):
            tbl.setColumnWidth(c, 260)
        tbl.setMinimumHeight(430)
        t.add(tbl)
        self.add(t)

        self.add(callout(
            "<b>Design rule of thumb.</b> Ask what frequency the danger arrives "
            "at.<br><br>"
            "• Danger is a <b>collision</b> (high ω) → you need the inertia "
            "hidden up there → <b>SEA</b>.<br>"
            "• Danger is a <b>flat battery</b> (holding a pose, ω ≈ 0) → you need "
            "inertia subtracted down there → <b>PEA</b>.<br>"
            "• Danger is <b>being too slow</b> (catching, balancing) → you cannot "
            "afford any filter → <b>DD/QDD</b> plus software compliance.", "key"))

        self.finish()

    def _redraw(self):
        jm = self.s_jm.value() / 1000.0
        jl = self.s_jl.value() / 1000.0
        k = float(self.s_k.value())
        self.l_jm.setText(f"{jm:.3f}")
        self.l_jl.setText(f"{jl:.3f}")
        self.l_k.setText(f"{k:.0f}")

        c = self.canvas
        c.clear()
        ws = [10 ** (x / 40.0) for x in range(-20, 141)]
        colours = {"direct": theme.ACCENT, "sea": theme.GOOD, "pea": theme.VIOLET}
        anti = math.sqrt(k / jm)
        for key, colour in colours.items():
            if not self.chk[key].isChecked():
                continue
            if key == "sea":
                for seg in ([w for w in ws if w < anti * 0.985],
                            [w for w in ws if w > anti * 1.015]):
                    if seg:
                        c.ax.semilogx(seg, [j_eff(key, jm, jl, k, w) for w in seg],
                                      color=colour, lw=2.3,
                                      label=TOPOLOGY_NAMES[key] if seg[0] == ws[0]
                                      else None)
            else:
                c.ax.semilogx(ws, [j_eff(key, jm, jl, k, w) for w in ws],
                              color=colour, lw=2.3, label=TOPOLOGY_NAMES[key])
        c.ax.axhline(0, color=theme.BORDER, lw=1.0)
        c.ax.axhline(jl, color=theme.TEXT_FAINT, lw=0.9, ls=":")
        c.ax.set_xlabel("interaction frequency ω  (rad/s)   —   slow lean ← → sharp impact")
        c.ax.set_ylabel("J_eff  (kg·m²)")
        c.ax.set_ylim(-(jm + jl) * 1.6, (jm + jl) * 2.2)
        c.legend(loc="upper left")
        c.refresh()


# ==========================================================================
# PAGE 5 -- Gearing and the square law
# ==========================================================================

class GearingPage(Page):
    TITLE = "Gearing & Reflected Inertia"
    SUBTITLE = ("The N² square law: why a 100:1 gearbox makes your motor feel "
                "10,000 times heavier — and kills impedance control.")
    SECTION = SECTION
    NOTES = "material p.1"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>The \"Square Law\" of reflected inertia.</b> This is the single "
            "most important technical reason behind most humanoid actuator "
            "choices. When you put a gear ratio N between motor and joint, the "
            "inertia of the motor's rotor is <i>reflected</i> to the output shaft "
            "by <b>N²</b>.", "key"))

        d = Card("the maths, and the number that follows from it")
        d.add(math_label(r"J_{reflected} = J_m \times N^2", 18))
        d.add(body(
            "For a 100:1 drive: 100² = <b>10,000</b>.<br><br>"
            "The human at the output shaft doesn't just feel the weight of the "
            "robot arm; they feel the motor's internal rotor inertia "
            "<b>10,000 times heavier</b> than it actually is."))
        self.add(d)

        i = Card("turn the ratio")
        self.s_n = slider(1, 200, 100)
        self.s_jm = slider(1, 200, 40)
        self.l_n, self.l_jm = QLabel(), QLabel()
        i.add_layout(slider_row("Gear ratio  N", self.s_n, self.l_n))
        i.add_layout(slider_row("Rotor  Jₘ", self.s_jm, self.l_jm))

        self.st_refl = Stat("reflected inertia", "--", theme.BAD)
        self.st_mult = Stat("multiplier", "--", theme.WARN)
        self.st_tq = Stat("output torque", "--", theme.GOOD)
        self.st_sp = Stat("output speed", "--", theme.ACCENT)
        i.add_layout(stat_row(self.st_refl, self.st_mult, self.st_tq, self.st_sp))

        self.canvas = MplCanvas(width=7.4, height=2.9)
        i.add(self.canvas)
        self.add(i)
        self.s_n.valueChanged.connect(self._redraw)
        self.s_jm.valueChanged.connect(self._redraw)
        self._redraw()

        self.add(hline())
        self.add(title("Why this kills impedance control"))

        k = Card("loss of transparency")
        k.add(body(
            "Impedance control is an <b>open-loop force</b> strategy. You command "
            "a torque and <i>assume</i> the mechanics will let the arm move if "
            "someone pushes it. The encoder is your only witness."))
        k.add(body(
            "<b>With a direct drive:</b> I push the arm, the motor spins "
            "immediately, the encoder sees the change, and the software says "
            "\"he pushed it 1 degree, I should apply X of virtual spring "
            "force.\""))
        k.add(body(
            "<b>With a 100:1 harmonic drive:</b> I push the arm with 5 N and "
            "<b>it does not move at all</b> — the reflected inertia and the "
            "friction hold it. Since the arm doesn't move, the encoder sees "
            "<b>zero change</b>, and the software thinks <b>no one is touching "
            "it</b>."))
        k.add(body(
            "<b>Stiction on top.</b> High-ratio gears have high static friction. "
            "You might have to push with 20 N of force just to get the gears to "
            "\"break away\" and start moving at all. The system is no longer "
            "<b>backdriveable</b>.", dim=True))
        self.add(k)

        self.add(callout(
            "In impedance control the motor 'feels' the user through <b>motion</b> "
            "(encoders). Behind a gearbox, the gears mask that motion. This is "
            "the reason to choose <b>admittance control</b> instead: it uses an "
            "external force sensor to bypass the gear friction entirely, so the "
            "controller can 'see' the user's intent even when the gears are "
            "physically locked.", "warn"))

        b = Card("the bypass: how a force sensor physically skips the gears")
        b.add(body(
            "In a standard robot without a force sensor, the <b>only</b> way the "
            "controller knows you are pushing is if the motor's encoder sees the "
            "shaft move. With a 100:1 harmonic drive the gears are so stiff that "
            "a human push might not move the motor at all. The encoder sees 0 "
            "movement, so the controller does 0."))
        b.add(body(
            "<b>The bypass solution:</b> put a Force/Torque sensor at the "
            "interface where the human touches the robot — the end-effector, or "
            "the cuff of an exoskeleton.<br><br>"
            "&nbsp;&nbsp;<b>Input:</b> the sensor picks up your 5 N push "
            "instantly.<br>"
            "&nbsp;&nbsp;<b>The bypass:</b> that signal goes directly to the "
            "computer <b>before</b> the force has to fight the gears. The "
            "computer sees your intent even though the arm hasn't moved a single "
            "millimetre yet."))
        b.add(body(
            "Admittance control is essential here because it lets the robot use "
            "<b>its own power</b> to overcome <b>its own friction</b>. The robot "
            "feels your 1 N push and says: <i>\"I will start the motor for you so "
            "you don't have to fight my 10,000× inertia.\"</i>", dim=True))
        self.add(b)

        self.add(callout(
            "<b>Interview-ready summary.</b> \"The bypass happens because we "
            "sense the user's force at the point of contact <b>before</b> it "
            "enters the transmission. In a 100:1 system, the reflected inertia "
            "and friction would otherwise lock the joint. By feeding that force "
            "into a virtual mass-damper model, we calculate the motion a "
            "'perfect' frictionless robot would have, and then command our actual "
            "motor to reach that position using a high-gain inner loop.\"", "good"))

        self.finish()

    def _redraw(self):
        n = float(self.s_n.value())
        jm = self.s_jm.value() / 1000.0
        self.l_n.setText(f"{n:.0f}:1")
        self.l_jm.setText(f"{jm:.3f}")

        refl = reflected_inertia(jm, n)
        tq, sp = gear_output(1.0, 100.0, n)
        self.st_refl.set(f"{refl:.1f}")
        self.st_mult.set(f"{n * n:,.0f}×")
        self.st_tq.set(f"{tq:.0f} N·m")
        self.st_sp.set(f"{sp:.1f} rad/s")

        c = self.canvas
        c.clear()
        ns = list(range(1, 201))
        c.ax.semilogy(ns, [reflected_inertia(jm, x) for x in ns],
                      color=theme.BAD, lw=2.4, label="reflected Jₘ · N²")
        c.ax.semilogy(ns, [jm * x for x in ns], color=theme.TEXT_FAINT, lw=1.3,
                      ls="--", label="if it were only linear in N")
        c.ax.axvline(n, color=theme.ACCENT, lw=1.2)
        c.ax.scatter([n], [refl], color=theme.ACCENT, zorder=5, s=34)
        c.ax.set_xlabel("gear ratio N")
        c.ax.set_ylabel("inertia felt at output  (kg·m²)")
        c.legend(loc="upper left")
        c.refresh()
