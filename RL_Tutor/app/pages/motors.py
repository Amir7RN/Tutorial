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
    sea_antiresonance_rad_s,
    sea_bandwidth_hz,
    sea_deflection_ratio,
    sea_resonance_rad_s,
    sea_transmissibility,
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


def _compare_table():
    """Direct drive vs geared, same output torque, real-ish numbers."""
    rows = [
        ("Rotor inertia  Jₘ", "0.0040 kg·m²  (big rotor)",
         "0.00004 kg·m²  (100× lighter)"),
        ("Gear ratio  N", "1 : 1", "50 : 1"),
        ("Reflected rotor  Jₘ·N²", "0.0040", "0.00004 × 2500 = 0.100"),
        ("Limb inertia  Jʟ", "0.025", "0.025"),
        ("J_eff at the joint", "0.029 kg·m²", "0.125 kg·m²   (4.3× worse)"),
        ("Backdriveable?", "yes — push it and the rotor turns",
         "no — stiction may need 20 N before anything moves"),
        ("Motor mass", "heavy", "light, but the gearbox is not"),
        ("Force sensing", "free, from motor current",
         "current tells you about the gearbox, not the world"),
    ]
    t = QTableWidget(len(rows), 3)
    t.setHorizontalHeaderLabels(["", "Direct drive, big motor",
                                 "Small motor + 50:1 gearbox"])
    for r, cells in enumerate(rows):
        for c, v in enumerate(cells):
            it = QTableWidgetItem(v)
            it.setFlags(Qt.ItemIsEnabled)
            t.setItem(r, c, it)
    t.verticalHeader().setVisible(False)
    t.setWordWrap(True)
    t.resizeRowsToContents()
    t.setColumnWidth(0, 170)
    t.setColumnWidth(1, 250)
    t.setColumnWidth(2, 300)
    t.setMinimumHeight(44 + 46 * len(rows))
    return t


def _verdict_table():
    """Which J_eff you want, band by band."""
    rows = [
        ("LOW ω\nslow lean, holding a\npose, human leading",
         "MODERATE — you want some",
         "Too low and the joint is floppy: it drifts under its own weight, "
         "wanders when bumped, and feels dead to a human trying to guide it. "
         "You want enough impedance here to hold a pose and reject slow "
         "disturbances. This is the one band where MORE is often right.",
         "PEA wins: it removes the gravity torque without needing the motor."),
        ("MID ω\nthe robot's own\nmotions, 1–30 Hz",
         "SMOOTH — flat is what you want",
         "This is your working band, so what matters is not the level but the "
         "SHAPE. Resonances and antiresonances here are poison: they make the "
         "plant gain swing wildly with frequency, which no fixed set of gains "
         "can handle. A flat curve is a plant you can tune once and trust.",
         "DD wins: flat everywhere by construction. SEA's resonance pair often "
         "lands exactly here, which is why SEAs are harder to tune."),
        ("HIGH ω\nimpacts, collisions,\nsomeone's hand",
         "AS LOW AS POSSIBLE",
         "Collision energy is ½·J_eff·ω². This is the number that decides "
         "whether a mistake is a bump or an injury, and no controller reaches up "
         "here to help — an impact is broadband, far above any loop bandwidth. "
         "Whatever mechanics presents is what lands.",
         "SEA wins outright: J_eff drops to J_L, the rotor is disconnected. "
         "PEA does nothing here. DD gives you the full machine."),
    ]
    t = QTableWidget(len(rows), 4)
    t.setHorizontalHeaderLabels(
        ["Band", "What you want", "Why", "Who wins"])
    for r, cells in enumerate(rows):
        for c, v in enumerate(cells):
            it = QTableWidgetItem(v)
            it.setFlags(Qt.ItemIsEnabled)
            t.setItem(r, c, it)
    t.verticalHeader().setVisible(False)
    t.setWordWrap(True)
    t.resizeRowsToContents()
    for c, w in enumerate((150, 175, 330, 270)):
        t.setColumnWidth(c, w)
    t.setMinimumHeight(360)
    return t


def _decision_table():
    """Machine type -> topology, with real examples."""
    rows = [
        ("Humanoid arm, works beside people",
         "SEA, or QDD + soft body",
         "Baxter/Sawyer (SEA); 1X Neo (QDD + polymer skin + proprioception)",
         "Impact energy is the binding constraint. Either filter it "
         "mechanically or keep J_eff tiny everywhere."),
        ("Humanoid / biped leg",
         "Hybrid: SEA ankle, PEA knee, QDD hip",
         "Agility Digit, Cassie, ANYmal",
         "Ankle takes the ground impacts; knee holds the body weight for hours; "
         "hip needs speed for swing."),
        ("Running quadruped",
         "QDD, low ratio (~6:1)",
         "MIT Cheetah, Mini Cheetah",
         "Leg repositioning speed beats everything. A 10 Hz mechanical filter "
         "would fight the gait. Compliance is done in software."),
        ("Industrial arm, caged",
         "High-ratio geared, position control",
         "Classic 6-axis welders and palletisers",
         "Nothing unexpected is in the workspace, so precision and stiffness "
         "dominate. Backdrivability is irrelevant."),
        ("Collaborative manipulator",
         "Geared + joint torque sensors",
         "KUKA LBR iiwa, Franka Emika",
         "The third path: keep the gearbox, and buy back torque control with a "
         "sensor on the OUTPUT side, past the friction."),
        ("Prosthesis / exoskeleton",
         "SEA, or geared + admittance",
         "Powered ankle prostheses; most exos",
         "Attached to a person, so compliance is safety. The spring doubles as "
         "the torque sensor and stores push-off energy."),
        ("Surgical / precision tool",
         "Stiff, geared, high-resolution",
         "da Vinci and similar",
         "Compliance is the enemy. Safety comes from scale, limits and the "
         "human in the loop, not from being soft."),
    ]
    t = QTableWidget(len(rows), 4)
    t.setHorizontalHeaderLabels(
        ["Machine", "Topology", "Real examples", "Why"])
    for r, cells in enumerate(rows):
        for c, v in enumerate(cells):
            it = QTableWidgetItem(v)
            it.setFlags(Qt.ItemIsEnabled)
            t.setItem(r, c, it)
    t.verticalHeader().setVisible(False)
    t.setWordWrap(True)
    t.resizeRowsToContents()
    for c, w in enumerate((200, 200, 230, 300)):
        t.setColumnWidth(c, w)
    t.setMinimumHeight(500)
    return t


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
            "<b>Reading the sliders as engineering, not as a curve.</b> The line "
            "height <i>is</i> the performance. Three things scale directly with "
            "it:<br><br>"
            "&nbsp;&nbsp;• <b>Collision energy</b> ½·J<sub>eff</sub>·ω² — double "
            "J<sub>eff</sub>, double the energy delivered into whatever you "
            "hit.<br>"
            "&nbsp;&nbsp;• <b>Torque to accelerate</b> τ = J<sub>eff</sub>·α — "
            "double it, and every motion costs twice the torque, so you size a "
            "bigger motor, which raises J<sub>m</sub>, which… (this loop is real "
            "and it is why big robots are hard).<br>"
            "&nbsp;&nbsp;• <b>Achievable bandwidth</b> ω<sub>bw</sub> ∝ "
            "√(K/J<sub>eff</sub>) — quadrupling the inertia halves the speed at "
            "which the joint can respond, for the same gain.<br><br>"
            "The <b>rotor share</b> is the specifically damning number: on a "
            "direct drive the motor's own mass is <b>always visible</b> to the "
            "world, at every frequency. It is never hidden. Everything in the "
            "next four pages is an attempt to hide it without losing the ability "
            "to feel.", "key"))

        # ---- why it matters -------------------------------------------------
        self.add(hline())
        self.add(title("Why J_eff decides the design, the motor and the controller"))

        m = Card("1 · for mechanism design — watch out for DISTAL mass")
        m.add(body(
            "Inertia about a joint is <b>Σ m<sub>i</sub> d<sub>i</sub>²</b>. The "
            "distance is <b>squared</b>, so mass at the end of the linkage is "
            "punished quadratically. A 1 kg motor at the wrist costs a shoulder "
            "joint <i>sixteen times</i> more inertia than the same motor at "
            "0.25 of the reach."))
        m.add(body(
            "<b>This is why real robots look the way they do:</b><br>"
            "&nbsp;&nbsp;• <b>Proximal actuator placement</b> — put the motors in "
            "the torso or upper arm and transmit power outward. Tendons/cables "
            "(1X Neo, most dexterous hands), belts, or push-rods.<br>"
            "&nbsp;&nbsp;• <b>Parallel &amp; closed-chain mechanisms</b> — delta "
            "robots and five-bar linkages exist almost entirely to keep actuator "
            "mass at the base. Same reason for differential wrists.<br>"
            "&nbsp;&nbsp;• <b>Lightweight distal links</b> — carbon fibre "
            "forearms, hollow sections, and accepting the structural compliance "
            "that comes with them.<br>"
            "&nbsp;&nbsp;• <b>Biology did this first</b> — your calf muscles sit "
            "high on the shin and pull the foot through the Achilles tendon. "
            "Almost no muscle mass is in the foot."))
        self.add(m)

        s = Card("2 · for motor specification")
        s.add(body(
            "The number a datasheet will not tell you directly is the "
            "<b>inertia match</b>, J<sub>L</sub>/J<sub>m</sub> (reflected "
            "through the gearing).<br><br>"
            "&nbsp;&nbsp;• <b>Ratio ≈ 1–3</b> is the classic servo sweet spot: "
            "best acceleration per amp, well-damped, easy to tune.<br>"
            "&nbsp;&nbsp;• <b>Ratio ≫ 10</b> (load dominates) — the motor "
            "struggles to control the load; resonances show up; you need a "
            "gearbox or a bigger motor.<br>"
            "&nbsp;&nbsp;• <b>Ratio ≪ 1</b> (rotor dominates) — you are mostly "
            "spending torque accelerating your own rotor. This is what "
            "over-gearing does, and it is the whole problem on page 5.<br><br>"
            "So J<sub>eff</sub> is not just an output of the design — it is the "
            "<b>input to motor sizing</b>. Pick the topology first, compute "
            "J<sub>eff</sub>, then choose the motor."))
        self.add(s)

        c = Card("3 · for control — and what you can and cannot fix in software")
        c.add(body(
            "<b>What control CAN do:</b><br>"
            "&nbsp;&nbsp;• <b>Feedforward / computed torque.</b> If you know "
            "J(q), compute τ = J(q)q̈<sub>d</sub> + C(q,q̇)q̇ + g(q) and apply it "
            "directly. The feedback loop then only has to correct model error "
            "instead of fighting the full inertia. This is the single biggest "
            "win available and it costs nothing but a model.<br>"
            "&nbsp;&nbsp;• <b>Inertia shaping.</b> With force feedback you can "
            "make the joint <i>feel</i> lighter than it is — admittance control "
            "with M<sub>v</sub> &lt; J<sub>real</sub>.<br>"
            "&nbsp;&nbsp;• <b>Input shaping / notch filters</b> for the "
            "resonances that light distal links introduce."))
        c.add(body(
            "<b>What control CANNOT do — and this is the important half.</b> "
            "Every one of those tricks works <b>only inside the loop "
            "bandwidth</b>. Above it, the physical inertia is exactly what the "
            "world feels, because the controller has not noticed yet.<br><br>"
            "An impact is <b>broadband</b> — a 1 ms collision has energy out to "
            "hundreds of Hz, far above any joint loop. So during the event that "
            "actually matters for safety, your beautiful inertia-shaping law "
            "contributes <b>nothing</b>. Whatever J<sub>eff</sub> the mechanics "
            "presents up there is what hits the person.<br><br>"
            "How far can you push inertia shaping? Roughly: rendering "
            "M<sub>v</sub> much below J<sub>real</sub> demands loop gain, and "
            "loop gain plus delay is instability. A factor of 2–5 is realistic; "
            "a factor of 100 is not. <b>You cannot software your way out of a "
            "heavy rotor.</b>", dim=True))
        self.add(c)

        # ---- DD vs geared, with numbers --------------------------------------
        g = Card("\"big low-inertia motor\" vs \"small motor + gearbox\" — "
                 "the same joint, two ways")
        g.add(body(
            "Both deliver 40 N·m at the joint. They are not remotely the same "
            "machine."))
        g.add(_compare_table())
        g.add(body(
            "The geared version has a rotor <b>100× lighter</b> and still ends up "
            "presenting <b>4× more inertia</b> to the world, because N² = 2,500 "
            "beats the mass saving comfortably. And that inertia arrives with "
            "backlash and stiction attached.", dim=True))
        self.add(g)

        b = Card("so what bandwidth does each actually get?")
        b.add(body(
            "First, separate the three numbers from the Real-Time page — this is "
            "where people go wrong:<br><br>"
            "&nbsp;&nbsp;<b>Current loop:</b> 10–40 kHz on both. Electrical, and "
            "essentially free.<br>"
            "&nbsp;&nbsp;<b>Joint control loop:</b> 1–4 kHz on both. This is your "
            "<i>sample rate</i>, not your bandwidth.<br>"
            "&nbsp;&nbsp;<b>Usable force/impedance bandwidth:</b> this is where "
            "they diverge, and it is set by <b>mechanics</b>, not by the CPU."))
        b.add(body(
            "<table cellpadding='6'>"
            "<tr><td><b>Direct drive / QDD</b></td><td><b>50–100+ Hz</b></td>"
            "<td>Limited by structural resonance of the link, encoder noise and "
            "loop delay. Nothing mechanical is filtering the force path.</td></tr>"
            "<tr><td><b>High-ratio geared</b></td><td><b>~10–30 Hz</b></td>"
            "<td>Limited by friction nonlinearity, backlash, and torsional "
            "windup of the flexspline. The gearbox is a low-pass filter you did "
            "not ask for — and worse, a <i>nonlinear</i> one.</td></tr>"
            "<tr><td><b>SEA</b></td><td><b>10–20 Hz</b></td>"
            "<td>Limited by the spring-load resonance. Page 3 derives it.</td>"
            "</tr></table>"))
        b.add(body(
            "<b>Notice all three sit far below the 1 kHz loop rate.</b> That is "
            "the answer to \"we sample at 1 kHz, so why can't we react in 1 ms?\" "
            "— the sampling is not the constraint. The mechanics is.", dim=True))
        self.add(b)

        self.add(callout(
            "<b>Real machines, so the numbers mean something.</b><br><br>"
            "&nbsp;&nbsp;• <b>MIT Cheetah 3 / Mini Cheetah</b> — QDD, ~6:1. "
            "Chose low reflected inertia over torque density so the legs could "
            "sense ground contact through the motors alone. No force sensors in "
            "the feet at all.<br>"
            "&nbsp;&nbsp;• <b>KUKA LBR iiwa / Franka</b> — high-ratio harmonic "
            "drives <i>plus a torque sensor on every joint output</i>. That third "
            "option recovers torque control without backdrivability, at "
            "considerable cost. Page 6 returns to it.<br>"
            "&nbsp;&nbsp;• <b>ANYmal</b> — SEA legs (ANYdrive). Accepted ~10 Hz "
            "joint bandwidth to get passive impact survival on rough terrain.<br>"
            "&nbsp;&nbsp;• <b>Universal Robots cobots</b> — geared and "
            "position-controlled, with collision detection from motor current. "
            "Safe by <i>stopping</i>, not by being compliant. A completely "
            "different safety philosophy, and a legitimate one.", "good"))

        self.add(callout(
            "<b>The takeaway, in one line each.</b><br><br>"
            "<b>Mechanism design:</b> keep mass proximal, because d² is "
            "merciless.<br>"
            "<b>Motor spec:</b> aim for an inertia match near 1–3 <i>after</i> "
            "choosing the topology.<br>"
            "<b>Control:</b> feedforward what you know; and accept that above "
            "your bandwidth, mechanics is the only controller you have.<br><br>"
            "This is why this tutorial puts actuator mechanics before control "
            "theory, and real-time behaviour before both.", "good"))

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

        # ---- THE key clarification -------------------------------------------
        self.add(callout(
            "<b>Before the plot: three different frequencies live on this "
            "actuator, and conflating them is the #1 source of confusion about "
            "SEAs.</b> They answer three different questions.<br><br>"
            "<b>1 · f<sub>n</sub> = (1/2π)√(k/J<sub>L</sub>) — the MOTOR-side "
            "question.</b> \"If I command the motor to move, how fast can the "
            "load follow?\" This is your <b>control bandwidth</b>: trajectory "
            "tracking, force control, reflexes.<br><br>"
            "<b>2 · ω<sub>a</sub> = √(k/J<sub>m</sub>) — the LOAD-side "
            "antiresonance.</b> \"If the <i>world</i> shakes the joint, what "
            "happens?\" The motor-on-its-spring rings and pins the load. "
            "J<sub>eff</sub> → ∞.<br><br>"
            "<b>3 · ω<sub>r</sub> = √(k(J<sub>m</sub>+J<sub>L</sub>)/"
            "(J<sub>m</sub>J<sub>L</sub>)) — the system resonance.</b> The two "
            "masses swing against each other. J<sub>eff</sub> = 0.<br><br>"
            "The J<sub>eff</sub> plot below shows <b>2 and 3</b>. The bandwidth "
            "number is <b>1</b>, a different transfer function entirely, plotted "
            "separately further down.", "warn"))

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

        self.st_anti = Stat("ω_a antiresonance", "--", theme.BAD)
        self.st_res = Stat("ω_r resonance", "--", theme.VIOLET)
        self.st_hi = Stat("J_eff at impact", "--", theme.ACCENT)
        self.st_defl = Stat("spring deflection @1 rad/s", "--", theme.TEXT_DIM)
        i.add_layout(stat_row(self.st_anti, self.st_res, self.st_hi,
                              self.st_defl))

        self.canvas = MplCanvas(width=7.4, height=3.1)
        i.add(self.canvas)
        self.add(i)

        for s in (self.s_jm, self.s_jl, self.s_k):
            s.valueChanged.connect(self._redraw)
        # _redraw() also fills canvas_bw, which is built further down the page,
        # so the first call is deferred to the end of __init__.

        # ---- is the spring deflecting? ---------------------------------------
        d2 = Card("\"below the antiresonance, is the spring deflecting at all?\"")
        d2.add(body(
            "<b>Yes — but by an amount that vanishes as ω².</b> Solve the same "
            "equations for the deflection instead of the inertia:"))
        d2.add(math_label(r"\left|\frac{\theta_m - \theta_L}{\theta_L}\right| = "
                          r"\frac{J_m\,\omega^2}{\left|k - J_m\omega^2\right|}",
                          16))
        d2.add(body(
            "At low frequency this is ≈ J<sub>m</sub>ω²/k — near zero. The spring "
            "bends by <b>exactly</b> the amount needed to generate the force that "
            "accelerates the rotor, and no more.<br><br>"
            "So the answer to \"is it the motor rotating, or the spring "
            "deflecting?\" is: <b>overwhelmingly the motor rotating</b>, with a "
            "sliver of deflection. That is precisely <i>why</i> you feel "
            "J<sub>m</sub> + J<sub>L</sub> down there — the rotor really is being "
            "dragged along, so its mass really is in your hand."))
        d2.add(body(
            "As ω rises past ω<sub>a</sub>, the ratio passes 1 and keeps growing: "
            "now the spring is taking most of the relative motion and the rotor "
            "is barely moving. <b>The handover from \"motor moves\" to \"spring "
            "bends\" IS the transition on the plot.</b>", dim=True))
        self.add(d2)

        # ---- what happens after the antiresonance ----------------------------
        d3 = Card("\"and after the antiresonance it just converges to Jʟ — what "
                  "does that mean physically?\"")
        d3.add(body(
            "Above ω<sub>r</sub> the rotor is <b>inertially unreachable</b>. To "
            "move it that fast you would need a force the spring cannot transmit "
            "in the time available, so from the load's point of view the far end "
            "of the spring might as well be <b>bolted to the wall</b>."))
        d3.add(body(
            "The load is then a mass on a spring anchored to ground. Push it fast "
            "enough and the spring force kθ becomes negligible next to the "
            "inertial force J<sub>L</sub>ω²θ — so what you feel is a "
            "<b>free mass J<sub>L</sub></b>, and nothing else.<br><br>"
            "<b>That is the safety mechanism, stated properly:</b> the rotor is "
            "not \"absorbed\" or \"cushioned\". It is <b>disconnected</b>. During "
            "a fast impact the motor is not part of the collision at all.",
            dim=True))
        self.add(d3)

        # ---- motor-side bandwidth --------------------------------------------
        self.add(hline())
        self.add(title("Now the MOTOR side — a different question, a different "
                       "plot"))

        bw = Card("motor → load transmissibility")
        bw.add(body(
            "Everything above was the world pushing the load. Now hold the motor "
            "under stiff position control and wiggle <i>it</i>. How much of that "
            "motion reaches the arm?"))
        bw.add(math_label(r"\frac{\theta_L}{\theta_m} = \frac{k}{J_L s^2 + k} "
                          r"\quad\Rightarrow\quad "
                          r"\left|\frac{\theta_L}{\theta_m}\right| = "
                          r"\frac{k}{\left|k - J_L\omega^2\right|}", 16))
        bw.add(math_label(r"f_n = \frac{1}{2\pi}\sqrt{\frac{k}{J_L}}", 17))
        bw.add(body(
            "Below f<sub>n</sub>, the load follows the motor faithfully. Above "
            "it, the spring absorbs the motion and the response rolls off as "
            "1/ω². <b>This is the number that limits trajectory tracking, force "
            "control and reflexes.</b> This is \"the bandwidth\"."))
        self.canvas_bw = MplCanvas(width=7.4, height=2.8)
        bw.add(self.canvas_bw)
        self.add(bw)

        self.add(callout(
            "<b>\"But the spring IS a force sensor — so why do I care about "
            "delay? Just measure the force and tell the motor to react.\"</b><br><br>"
            "This is the right question, and the answer is a clean split:<br><br>"
            "&nbsp;&nbsp;<b>Sensing bandwidth is high.</b> You are correct — "
            "spring deflection gives you an excellent, high-bandwidth torque "
            "measurement. You will <i>know</i> about the disturbance almost "
            "instantly.<br><br>"
            "&nbsp;&nbsp;<b>Actuation bandwidth is low.</b> But to <i>change the "
            "joint torque</i>, the motor must change the spring's deflection — "
            "and to do that it must accelerate J<sub>m</sub> through a finite "
            "spring. That is a physical process bounded by f<sub>n</sub>. No "
            "amount of knowing helps.<br><br>"
            "<b>You can sense fast and still act slowly.</b> Knowing that a car "
            "is about to hit you does not make you able to move. That single "
            "distinction — <b>force sensing bandwidth ≠ force control "
            "bandwidth</b> — is the whole reason SEAs trade safety for speed.",
            "key"))

        num = Card("so what do 50–100 Hz and 10–20 Hz actually mean?")
        num.add(body(
            "They are <b>closed-loop force-control bandwidths</b>: the frequency "
            "at which commanded joint torque still tracks to −3 dB. They are "
            "<b>not</b> sample rates and they are <b>not</b> sensor bandwidths."))
        num.add(body(
            "Your 1 kHz control loop sits far above all of them, and that is "
            "correct and necessary — you need 10–20× oversampling to close a loop "
            "at all (see the Real-Time page). But the loop rate is a "
            "<b>ceiling</b>. The mechanics sets the actual number:<br><br>"
            "&nbsp;&nbsp;<b>Direct drive, 50–100 Hz</b> — no mechanical filter in "
            "the force path. Limited by link structural resonance, encoder noise "
            "and loop delay.<br>"
            "&nbsp;&nbsp;<b>SEA, 10–20 Hz</b> — limited by f<sub>n</sub> = "
            "(1/2π)√(k/J<sub>L</sub>). A <b>physical</b> limit. Sample at 10 kHz "
            "with a perfect control law and it does not move."))
        num.add(body(
            "<b>What 10 Hz buys and costs, concretely:</b> a 10 Hz bandwidth "
            "means the joint can meaningfully change its torque about every "
            "100 ms. Walking has a ~1 s cycle, so 10 Hz is comfortable. Catching "
            "a dropped mug takes ~150 ms of total reaction — 10 Hz is marginal. "
            "Recovering from a shove that started 50 ms ago — 10 Hz is too "
            "slow.<br><br>"
            "For scale: a human ankle reflex fires at 30–50 ms (≈20–30 Hz "
            "equivalent), and passive tendon stiffness acts at 0 ms. Biology "
            "solves this by having <i>both</i>, which is exactly the layered "
            "answer 1X arrived at.", dim=True))
        self.add(num)

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

        # ---- what the spring is and is not for --------------------------------
        purpose = Card("\"is the spring protective, or are we trying to get more "
                       "torque at the joint?\"")
        purpose.add(body(
            "<b>Purely protective — plus two side benefits. It buys you no "
            "torque whatsoever.</b><br><br>"
            "The spring is in <b>series</b>, so every newton-metre still passes "
            "through it from the motor. Peak joint torque is exactly the motor's "
            "peak torque, unchanged. A series spring cannot add force any more "
            "than a longer rope can pull harder.<br><br>"
            "What it actually buys:<br>"
            "&nbsp;&nbsp;<b>1 · Impact protection</b> — J<sub>eff</sub> → "
            "J<sub>L</sub> at collision frequencies. The point.<br>"
            "&nbsp;&nbsp;<b>2 · A torque sensor for free</b> — measure deflection, "
            "multiply by k. No strain gauges.<br>"
            "&nbsp;&nbsp;<b>3 · Energy storage</b> — like a tendon, store in one "
            "gait phase and release in the next.<br><br>"
            "And what it costs: <b>bandwidth</b>. That is the entire trade."))
        purpose.add(body(
            "<b>If you want more torque, that is the PEA on the next page</b> — "
            "spring in <i>parallel</i>, so motor and spring add. Series buys "
            "safety; parallel buys torque and efficiency. Different position in "
            "the drivetrain, completely different function.", dim=True))
        self.add(purpose)

        # ---- the stiffness trade ---------------------------------------------
        kk = Card("\"so is higher stiffness better?\" — k is the safety ⇄ speed dial")
        kk.add(body(
            "Neither higher nor lower is better. k is the one knob that sets "
            "where you sit on the trade, and it moves <b>three things at "
            "once</b>:"))
        kk.add(body(
            "<table cellpadding='6'>"
            "<tr><th align='left'>Raising k</th><th align='left'>Effect</th></tr>"
            "<tr><td>Bandwidth f<sub>n</sub> ∝ √k</td><td><b>Better.</b> Faster "
            "reflexes, better tracking.</td></tr>"
            "<tr><td>Impact protection</td><td><b>Worse.</b> J<sub>eff</sub> "
            "stays at J<sub>m</sub>+J<sub>L</sub> up to a higher frequency, so "
            "less of the impact spectrum gets filtered.</td></tr>"
            "<tr><td>Force resolution</td><td><b>Worse.</b> Deflection per N·m is "
            "1/k, so a stiff spring makes a poor sensor — the deflection "
            "disappears into encoder quantisation.</td></tr>"
            "<tr><td>Energy stored</td><td><b>Less</b> at a given torque "
            "(E = τ²/2k).</td></tr>"
            "</table>"))
        kk.add(body(
            "<b>How it is chosen in practice:</b> pick the softest spring whose "
            "f<sub>n</sub> still clears your fastest required motion, then check "
            "that the deflection at peak torque fits the mechanism and resolves "
            "well on your encoder. Typical result for a humanoid leg: f<sub>n</sub> "
            "around 10–20 Hz, deflection of a few degrees at rated torque.",
            dim=True))
        self.add(kk)

        rw = Card("where SEAs actually are, and where they are deliberately not")
        rw.add(body(
            "<b>Used:</b><br>"
            "&nbsp;&nbsp;• <b>Agility Digit / Cassie</b> — SEA in the legs. A "
            "walking robot in warehouses among people; passive impact survival is "
            "worth more than reflex speed.<br>"
            "&nbsp;&nbsp;• <b>ANYmal (ANYdrive)</b> — SEA legs for rough-terrain "
            "quadruped work. Rocks and steps are exactly the broadband impacts a "
            "spring is good at.<br>"
            "&nbsp;&nbsp;• <b>Baxter / Sawyer</b> — the original \"safe around "
            "untrained people\" arms. SEA in every joint.<br>"
            "&nbsp;&nbsp;• <b>Powered ankle prostheses</b> — the spring doubles as "
            "the torque sensor <i>and</i> stores push-off energy, mimicking the "
            "Achilles tendon.<br><br>"
            "<b>Deliberately avoided:</b><br>"
            "&nbsp;&nbsp;• <b>MIT Cheetah</b> — running needs fast leg "
            "repositioning; a 10 Hz filter fights you.<br>"
            "&nbsp;&nbsp;• <b>1X Neo</b> — rejected SEAs explicitly for bandwidth, "
            "and recovered safety through a soft body plus proprioceptive "
            "control instead. See the case-study page.<br>"
            "&nbsp;&nbsp;• <b>Surgical and machining robots</b> — compliance is "
            "the enemy of precision."))
        self.add(rw)

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

        self._redraw()
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

        anti = sea_antiresonance_rad_s(k, jm)
        res = sea_resonance_rad_s(k, jm, jl)
        self.st_anti.set(f"{anti:.0f} rad/s")
        self.st_res.set(f"{res:.0f} rad/s")
        self.st_hi.set(f"{jl:.3f}")
        self.st_defl.set(f"{sea_deflection_ratio(jm, k, 1.0) * 100:.2f}%")

        # ---- load-side effective inertia ---------------------------------
        c = self.canvas
        c.clear()
        ws = [10 ** (x / 40.0) for x in range(-40, 141)]
        span = jm + jl

        below = [w for w in ws if w < anti * 0.98]
        mid = [w for w in ws if anti * 1.02 < w < res * 0.995]
        above = [w for w in ws if w > res * 1.005]
        for seg, lab in ((below, "SEA — load side"), (mid, None), (above, None)):
            if seg:
                c.ax.semilogx(seg, [j_eff_sea(jm, jl, k, w) for w in seg],
                              color=theme.GOOD, lw=2.4, label=lab)
        c.ax.axhline(span, color=theme.TEXT_FAINT, lw=1.1, ls="--",
                     label="Jₘ+Jʟ  (ω→0)")
        c.ax.axhline(jl, color=theme.ACCENT, lw=1.1, ls=":",
                     label="Jʟ  (ω→∞)  ← the safety number")
        c.ax.axhline(0, color=theme.BORDER, lw=1.0)
        c.ax.axvline(anti, color=theme.BAD, lw=1.1, alpha=0.8)
        c.ax.text(anti, span * 1.35, " ω_a\n antiresonance\n √(k/Jₘ)",
                  color=theme.BAD, fontsize=7.2, va="bottom")
        c.ax.axvline(res, color=theme.VIOLET, lw=1.1, alpha=0.8)
        c.ax.text(res, -span * 1.3, " ω_r\n resonance\n J_eff = 0",
                  color=theme.VIOLET, fontsize=7.2, va="top")
        c.ax.set_xlabel("frequency the WORLD pushes the load at,  ω (rad/s)")
        c.ax.set_ylabel("J_eff  (kg·m²)")
        c.ax.set_ylim(-span * 2.0, span * 2.4)
        c.legend(loc="upper left")
        c.refresh()

        # ---- motor-side transmissibility ----------------------------------
        cb = self.canvas_bw
        cb.clear()
        wn = math.sqrt(k / jl)
        lo = [w for w in ws if w < wn * 0.97]
        hi = [w for w in ws if w > wn * 1.03]
        for seg, lab in ((lo, "θʟ / θₘ"), (hi, None)):
            if seg:
                cb.ax.loglog(seg, [sea_transmissibility(k, jl, w) for w in seg],
                             color=theme.CYAN, lw=2.4, label=lab)
        cb.ax.axhline(1.0, color=theme.TEXT_FAINT, lw=1.1, ls="--",
                      label="load follows motor 1:1")
        cb.ax.axvline(wn, color=theme.GOOD, lw=1.3)
        cb.ax.text(wn, 0.02, f"  f_n = {sea_bandwidth_hz(k, jl):.1f} Hz\n"
                             f"  = {wn:.0f} rad/s",
                   color=theme.GOOD, fontsize=7.5)
        cb.ax.set_xlabel("frequency the MOTOR is commanded at,  ω (rad/s)")
        cb.ax.set_ylabel("|θʟ / θₘ|")
        cb.ax.set_ylim(1e-2, 1e2)
        cb.legend(loc="lower left")
        cb.refresh()


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

        r = Card("three regimes — and one of them is a trap")
        r.add(body(
            "<b>ω → ∞ &nbsp;(fast).</b> The k/ω² term goes to zero and "
            "J<sub>eff</sub> → <b>J<sub>m</sub> + J<sub>L</sub></b>. You feel the "
            "full machine, rotor included. <b>A PEA gives no impact "
            "protection.</b>"))
        r.add(callout(
            "<b>\"But if I shake it fast the spring can't bend, so motor and "
            "spring are locked — shouldn't the link not move at all? And why "
            "isn't it J<sub>L</sub>?\"</b><br><br>"
            "Two things to separate here.<br><br>"
            "<b>First: it is NOT J<sub>L</sub>. It is J<sub>m</sub> + "
            "J<sub>L</sub>.</b> If you were expecting J<sub>L</sub>, you are "
            "thinking of the SEA. That drop to J<sub>L</sub> is the <i>one thing</i> "
            "a series spring does and a parallel spring cannot. In a PEA the "
            "motor is <b>rigidly bolted to the joint</b> — there is no compliance "
            "in the force path at all, so the rotor is always along for the "
            "ride.<br><br>"
            "<b>Second: the spring is not \"locked\" or acting as a stiff rod.</b> "
            "It is deflecting by exactly θ, the same as always — it is in "
            "parallel, so it stretches by whatever the joint moves. Its torque "
            "kθ is perfectly real. It is just <b>negligible in comparison</b>: "
            "the inertial torque grows as Jω²θ while the spring torque stays at "
            "kθ, so by ω = 10ω<sub>r</sub> the spring contributes 1% of the "
            "total. It is not overpowered — it is out-scaled.<br><br>"
            "Contrast with the SEA, where at high ω the spring is doing the "
            "<i>opposite</i>: taking essentially all the relative motion and "
            "thereby disconnecting the rotor. Series compliance decouples masses. "
            "Parallel compliance never can.", "warn"))
        r.add(body(
            "<b>ω = √(k/(J<sub>m</sub>+J<sub>L</sub>)) &nbsp;(resonance).</b> "
            "J<sub>eff</sub> = 0 exactly. The spring's restoring torque and the "
            "inertial torque cancel, so a tiny applied torque produces large "
            "motion. Bounce the joint at its natural frequency and it costs "
            "almost nothing — the same reason a child on a swing needs only small "
            "pushes."))
        r.add(body(
            "<b>ω → 0 &nbsp;(slow).</b> J<sub>eff</sub> goes large and "
            "<b>negative</b>. Read this one carefully."))
        r.add(callout(
            "<b>What \"negative effective inertia\" does and does not mean.</b><br><br>"
            "It does <b>not</b> mean the joint has negative mass, or that it "
            "spontaneously accelerates, or that you get energy for free. I "
            "over-stated this in an earlier version of this page and it is worth "
            "correcting plainly.<br><br>"
            "Dividing every torque by s²θ forces <i>everything</i> into inertia "
            "units — but a spring's impedance carries the opposite sign to a "
            "mass's, because a spring's force is in phase with displacement while "
            "a mass's is in phase with acceleration (180° apart). So a negative "
            "number here says exactly one thing:<br><br>"
            "&nbsp;&nbsp;&nbsp;&nbsp;<b>Below resonance, this joint feels like a "
            "SPRING, not like a MASS.</b><br><br>"
            "Push it slowly and what pushes back is stiffness. Which is useful "
            "and real — if that spring was sized against gravity, its stiffness "
            "is holding the limb up so the motor does not have to. But the honest "
            "statement is about <b>torque</b>, not inertia, which is why the "
            "gravity-compensation section below is the one that actually "
            "matters.", "bad"))
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

        i2 = Card("tune the spring — what you are minimising, and why you cannot "
                  "win everywhere")
        i2.add(body(
            "<b>The objective:</b> <i>minimise |τ<sub>m</sub>| — the green curve — "
            "over the range of angles the robot actually spends its time in.</b> "
            "Nothing else. Not peak torque, not stiffness: <b>motor effort while "
            "holding a pose</b>, because that is what turns into heat and flat "
            "batteries."))
        i2.add(body(
            "<b>What you may change:</b> the spring stiffness k and its rest "
            "angle θ₀ — those are your design freedoms. The limb mass slider is "
            "there to show you that a spring tuned for one payload is "
            "<b>mistuned for another</b>; gravity is not yours to choose.<br><br>"
            "<b>Why you cannot zero it everywhere:</b> gravity torque goes as "
            "<b>sin θ</b> and a linear spring goes as <b>θ₀ − θ</b>. A straight "
            "line cannot match a sine. It can cross it at <b>two angles at most</b>, "
            "and that is your entire budget.<br><br>"
            "<b>So the real design question is: which pose do you want free?</b> "
            "Standing? Mid-stance? Arms-forward-holding-a-box? Put your two "
            "crossings there. Everywhere else the motor pays — and on the far "
            "side, it pays <i>double</i>, because it is now fighting the spring "
            "as well as gravity."))
        i2.add(body(
            "Try it: set θ₀ ≈ 55° and watch the green curve sit near zero across "
            "the mid-range. Then drag the limb mass and watch that carefully "
            "tuned cancellation fall apart. That is a robot picking up an "
            "unexpected payload.", dim=True))
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

        # ---- answering "which is better" head on ------------------------------
        self.add(hline())
        self.add(title("\"So is higher J_eff better? Flat better? Negative "
                       "better?\" — answered directly"))

        ans = Card("there is no globally better curve. There is a better curve "
                   "AT EACH FREQUENCY.")
        ans.add(body(
            "That is the whole point of plotting against ω, and it is why the "
            "question has no single answer. Break it into the three bands that "
            "correspond to three different things that can go wrong:"))
        ans.add(_verdict_table())
        ans.add(body(
            "<b>Read the three rows as three different accidents.</b> Row 1 is a "
            "robot that is too floppy to be useful. Row 2 is a robot that rings "
            "when you push it. Row 3 is a robot that breaks someone's hand. They "
            "are not the same failure and they do not have the same fix.",
            dim=True))
        self.add(ans)

        w = Card("and \"is higher bandwidth always better?\" — no")
        w.add(body(
            "<b>What more bandwidth buys:</b> faster reflexes, better trajectory "
            "tracking, the ability to catch things and recover from shoves, and "
            "stiffer rendered impedance without instability.<br><br>"
            "<b>What it costs:</b><br>"
            "&nbsp;&nbsp;• <b>Noise.</b> Loop gain rises with bandwidth, and so "
            "does the amplification of encoder quantisation. Audible whine, motor "
            "heating, worn bearings.<br>"
            "&nbsp;&nbsp;• <b>Robustness.</b> A high-bandwidth loop reaches up "
            "into frequencies where your model is wrong — unmodelled structural "
            "resonances, cable dynamics, payload flex. It will find them and "
            "excite them.<br>"
            "&nbsp;&nbsp;• <b>Safety.</b> Bandwidth is the ability to apply force "
            "quickly, which is also the ability to <i>hurt</i> quickly.<br><br>"
            "<b>The right target is \"enough\", not \"maximum\":</b> comfortably "
            "above your fastest required motion, comfortably below your first "
            "unmodelled resonance. For a walking humanoid leg, 10–30 Hz. For a "
            "manipulator doing contact tasks, 50–100 Hz. For a surgical tool, "
            "higher still — and none of them wants \"as much as possible\"."))
        self.add(w)

        d = Card("the decision table — what to actually build")
        d.add(_decision_table())
        self.add(d)

        self.add(callout(
            "<b>Design rule of thumb.</b> Ask what frequency the danger arrives "
            "at.<br><br>"
            "• Danger is a <b>collision</b> (high ω) → you need the inertia "
            "hidden up there → <b>SEA</b>, or a soft body.<br>"
            "• Danger is a <b>flat battery</b> (holding a pose, ω ≈ 0) → you need "
            "the gravity torque taken off the motor → <b>PEA</b>.<br>"
            "• Danger is <b>being too slow</b> (catching, balancing) → you cannot "
            "afford any mechanical filter → <b>DD/QDD</b> plus software "
            "compliance.<br><br>"
            "And note these compose: a real humanoid leg can be <b>QDD hip, SEA "
            "ankle, PEA knee</b>, because the three joints face three different "
            "dangers.", "key"))

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

        third = Card("the third option nobody mentions: sense AFTER the gearbox")
        third.add(body(
            "Impedance needs backdrivability. Admittance needs a sensor at the "
            "contact point. There is a middle path that is what most "
            "collaborative arms actually do:<br><br>"
            "<b>Put a torque sensor on the joint OUTPUT — downstream of the "
            "gearbox.</b>"))
        third.add(body(
            "Now the friction, backlash and reflected inertia of the transmission "
            "are all <i>inside</i> the loop, between the motor and the sensor. "
            "The controller closes on the torque that is <b>actually leaving the "
            "joint</b>, so the gearbox's sins become a disturbance to be "
            "rejected rather than a wall you cannot see through.<br><br>"
            "This is how <b>KUKA LBR iiwa</b> and <b>Franka Emika</b> do genuine "
            "impedance control through 100:1 harmonic drives. It is also how "
            "high-end SEAs work — the spring <i>is</i> an output-side torque "
            "sensor, just a mechanical one."))
        third.add(body(
            "<b>The costs:</b> a strain-gauge torque sensor per joint is "
            "expensive, adds compliance (it must deflect to measure), adds a "
            "failure mode, and its bandwidth and noise now cap your torque loop. "
            "You have also not fixed the <b>inertia</b> — during an impact faster "
            "than your loop, the reflected N²J<sub>m</sub> still arrives. Sensing "
            "after the gearbox buys you control authority, not passive safety.",
            dim=True))
        self.add(third)

        self.add(callout(
            "<b>Three ways out of a gearbox, ranked by what they actually "
            "fix.</b><br><br>"
            "<b>1 · Don't gear.</b> QDD. Fixes sensing <i>and</i> inertia. Costs "
            "torque density and motor mass.<br>"
            "<b>2 · Output-side torque sensor.</b> Fixes sensing. Does <b>not</b> "
            "fix inertia. Costs money and adds compliance.<br>"
            "<b>3 · F/T sensor at the contact point + admittance.</b> Fixes "
            "sensing at one point only. Does <b>not</b> fix inertia. Goes "
            "unstable against stiff contact.<br><br>"
            "Note that none of them fixes reflected inertia except the first. "
            "Once N² inertia exists, only mechanics removes it — which is the "
            "same lesson as page 2.", "key"))

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
