"""
Pages 16-18: proprioception, in biology and in machines.

 16  Proprioception in Biology  -- spindles, GTOs, joint receptors
 17  Robotic Proprioception     -- transparency is the prerequisite, not the goal
 18  Active Compliance          -- the three layers, and what happens without them

The organising idea, and it is worth stating before anything else:

    Proprioception is not about WHAT variables you know.
    It is about WHERE that information comes from.
"""

from __future__ import annotations

import math

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem

from ctrlcore.neuro import joint_torque_from_motor, motor_torque_from_current
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

SECTION = "Proprioception"


def _pairs_table(headers, rows, widths):
    t = QTableWidget(len(rows), len(headers))
    t.setHorizontalHeaderLabels(headers)
    for r, cells in enumerate(rows):
        for c, v in enumerate(cells):
            it = QTableWidgetItem(v)
            it.setFlags(Qt.ItemIsEnabled)
            t.setItem(r, c, it)
    t.verticalHeader().setVisible(False)
    t.setWordWrap(True)
    t.resizeRowsToContents()
    for c, w in enumerate(widths):
        t.setColumnWidth(c, w)
    t.setMinimumHeight(40 + 54 * len(rows))
    return t


# ==========================================================================
# PAGE 16 -- biology
# ==========================================================================

class BioProprioPage(Page):
    TITLE = "Proprioception in Biology"
    SUBTITLE = ("The sixth sense. Vision tells you where the door is; "
                "proprioception tells you where <i>you</i> are.")
    SECTION = SECTION
    NOTES = "material p.6"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "Proprioception tells you where you are <b>without you having to look "
            "at your limbs</b>. In a biological system this isn't just a static "
            "\"map\" — it is a high-speed feedback loop consisting of three "
            "variables: <b>length, velocity, and force</b>.", "key"))

        s = Card("two kinds of sensor, buried in the muscle")
        s.add(body(
            "<b>1 · Muscle spindles (length &amp; velocity)</b><br>"
            "Buried inside the muscle fibres. They act like <b>linear "
            "encoders</b>. They detect how much a muscle is stretched (length) "
            "and how fast it is stretching (velocity). If you trip, these sensors "
            "detect the sudden stretch and trigger a reflex to stiffen the muscle "
            "<b>before your brain even knows what happened</b>.<br><br>"
            "Function: posture control, stretch reflex, stabilisation against "
            "perturbations. Control effect: <b>resists changes in length</b> — "
            "acts like stiffness and damping. 👉 <i>This is analogous to impedance "
            "control.</i>"))
        s.add(body(
            "<b>2 · Golgi tendon organs (force / tension)</b><br>"
            "Located where the muscle meets the bone. They act like <b>strain "
            "gauges</b>, measuring the pulling force the muscle is exerting. If "
            "the force is too high — trying to lift a car — they can actually "
            "<b>shut off</b> the muscle to prevent it from tearing.<br><br>"
            "Function: protect muscles from excessive load, enable force "
            "regulation. 👉 <i>This is where positive force feedback comes "
            "from.</i>"))
        s.add(body(
            "<b>3 · Joint receptors</b><br>"
            "Sense joint angle extremes and provide coarse positional awareness."))
        self.add(s)

        self.add(callout(
            "<b>Humans do not need vision to stand or walk.</b> Proprioception is "
            "the dominant feedback loop. Human locomotion isn't a pre-programmed "
            "\"video\"; it's a <b>reactive dance</b> — every step adjusts based on "
            "length, velocity and force to maintain balance.", "good"))

        # ---- interactive timing -----------------------------------------------
        i = Card("the timescales — why mechanics beats software")
        i.add(body(
            "This is the whole safety argument in one chart. Slide the control "
            "loop rate and watch where a software reflex lands relative to the "
            "physics it is trying to beat.", dim=True))
        self.s_rate = slider(50, 5000, 1000)
        self.l_rate = QLabel()
        i.add_layout(slider_row("robot control loop (Hz)", self.s_rate, self.l_rate))
        self.st_lat = Stat("one control tick", "--", theme.WARN)
        self.st_spring = Stat("spring response", "0.1 ms", theme.GOOD)
        self.st_reflex = Stat("human reflex", "30–50 ms", theme.ACCENT)
        i.add_layout(stat_row(self.st_lat, self.st_spring, self.st_reflex))
        self.canvas = MplCanvas(width=7.4, height=2.6)
        i.add(self.canvas)
        self.add(i)
        self.s_rate.valueChanged.connect(self._redraw)
        self._redraw()

        self.add(callout(
            (
                "<b>Passive tissue responds without waiting for neural feedback.</b> Reflex delays depend on the"
                " pathway and task (tens of milliseconds here). Tendons are compliant series elements between "
                "muscle and skeleton; biological proprioception senses several parts of that system.<br><br>That"
                " last sentence is why a real SEA is not simply \"a robot muscle.\" In an SEA the chain is joint →"
                " spring → motor, so fast disturbances are absorbed by the spring and the motor only learns "
                "about them afterwards. Biology gets the compliance <i>and</i> the immediate signal. That is the"
                " design target."
            ), "warn"))

        self.finish()

    def _redraw(self):
        hz = self.s_rate.value()
        ms = 1000.0 / hz
        self.l_rate.setText(f"{hz} Hz")
        self.st_lat.set(f"{ms:.2f} ms")

        c = self.canvas
        c.clear()
        ax = c.ax
        events = [
            ("passive stiffness\n(spring / tissue)", 0.1, theme.GOOD),
            (f"control loop tick\n({hz} Hz)", ms, theme.WARN),
            ("human reflex\n(spindle → cord → muscle)", 40.0, theme.ACCENT),
            ("voluntary reaction\n(cortex)", 200.0, theme.VIOLET),
        ]
        for k, (lab, t, colour) in enumerate(events):
            ax.barh(k, t, color=colour, height=0.55, alpha=0.85)
            ax.text(t * 1.15, k, f"{t:.2f} ms", color=colour, va="center",
                    fontsize=8)
        ax.set_yticks(range(len(events)))
        ax.set_yticklabels([e[0] for e in events], fontsize=8)
        ax.set_xscale("log")
        ax.set_xlim(0.05, 600)
        ax.set_xlabel("time to respond (ms, log scale)")
        c.refresh()


# ==========================================================================
# PAGE 17 -- robotic proprioception
# ==========================================================================

class RobotProprioPage(Page):
    TITLE = "Robotic Proprioception"
    SUBTITLE = ("How does a robot \"feel itself\" without skin or muscles? And "
                "what single design choice destroys the ability?")
    SECTION = SECTION
    NOTES = "material p.6"

    def __init__(self, parent=None):
        super().__init__(parent)

        d = Card("the definition — reset it before anything else")
        d.add(title("Proprioception is the ability of a system to estimate its "
                    "own mechanical state using internal sensing alone.", 15))
        d.add(body(
            "That state includes joint position, joint velocity, and joint "
            "torque / force — sensed <b>without relying on external sensors</b> "
            "like force plates, tactile skins or vision."))
        d.add(body(
            "❗ Proprioception is <b>not</b> about <i>what</i> variables you "
            "know.<br>"
            "❗ It is about <b>where that information comes from</b>.", dim=True))
        d.add(body(
            "In robots: <b>the motor is the muscle</b>. If the motor does not "
            "feel load, the robot has no \"muscle sense\" — no matter how many "
            "encoders you bolt on."))
        self.add(d)

        self.add(callout(
            "<b>The single most important principle:</b><br><br>"
            "&nbsp;&nbsp;&nbsp;&nbsp;<b>External forces must propagate back to "
            "the actuator.</b><br><br>"
            "Said another way: joint interaction forces must be <b>observable at "
            "the actuator level</b>. Otherwise the actuator is \"blind\", control "
            "becomes feedforward or delayed, and compliance becomes unsafe or "
            "sluggish.", "key"))

        e = Card("the core equations")
        e.add(math_label(r"\tau = K_t \cdot I", 18))
        e.add(body("Motor torque is proportional to current. Free, kHz-rate, "
                   "low latency. But what you care about is the joint:", dim=True))
        e.add(math_label(r"\tau_{joint} \approx \tau_{motor} \cdot r", 18))
        e.add(body(
            "…which holds only where <b>r is a known transmission ratio</b> and "
            "the <b>losses are small and predictable</b>. That requires low "
            "friction, low backlash, transparency. Meet those and joint force "
            "becomes <b>observable internally</b> — that <i>is</i> robotic "
            "proprioception.", dim=True))
        self.add(e)

        # ---- interactive ------------------------------------------------------
        i = Card("watch proprioception break")
        i.add(body(
            "Raise the gear ratio and drop the transmission efficiency. The blue "
            "line is what the controller <i>believes</i> the joint torque is; the "
            "red line is the truth. The gap is the robot losing its sense of "
            "touch.", dim=True))
        self.s_n = slider(1, 150, 1)
        self.s_eff = slider(20, 100, 98)
        self.l_n, self.l_eff = QLabel(), QLabel()
        i.add_layout(slider_row("gear ratio N", self.s_n, self.l_n))
        i.add_layout(slider_row("transmission efficiency (%)", self.s_eff, self.l_eff))

        self.st_err = Stat("torque estimate error", "--", theme.BAD)
        self.st_refl = Stat("reflected inertia ×", "--", theme.WARN)
        self.st_state = Stat("proprioceptive?", "--", theme.GOOD)
        i.add_layout(stat_row(self.st_err, self.st_refl, self.st_state))
        self.canvas = MplCanvas(width=7.4, height=2.9)
        i.add(self.canvas)
        self.add(i)
        self.s_n.valueChanged.connect(self._redraw)
        self.s_eff.valueChanged.connect(self._redraw)
        self._redraw()

        b = Card("what breaks proprioception")
        b.add(body(
            (
                (
                    "<b>High gear ratios (e.g. harmonic drives)</b><br>&nbsp;&nbsp;• External forces do <b>not</b> "
                    "reach the motor<br>&nbsp;&nbsp;• Backdriveability is poor<br>&nbsp;&nbsp;• The motor \"doesn't "
                    "feel\" the world<br><br><b>Result:</b> motor current alone can become an inaccurate "
                    "external-torque estimate, and current alone may no longer give an accurate external-torque "
                    "estimate; output sensing or a dynamics observer can restore information."
                )
            )))
        b.add(body(
            "<b>Why gears specifically:</b> gears reflect inertia (N²), filter "
            "force, and create backlash. A <b>tendon</b> gives a continuous force "
            "path with no discrete tooth contact and high mechanical "
            "transparency — the same job a biological tendon does, transmitting "
            "force with minimal loss.", dim=True))
        self.add(b)

        w = Card("why internal force sensing matters at all")
        w.add(body(
            (
                "<b>1 · Scalability.</b> You cannot put force sensors in every joint, every finger, every "
                "tendon. Humanoids need <b>dozens</b> of force channels.<br><br><b>2 · Bandwidth.</b> "
                "Motor-current sensing is kHz-level and low latency. Dedicated force sensors have their own "
                "noise, bandwidth and mechanical limits; compare specifications rather than assuming they are "
                "always slower."
            )))
        self.add(w)

        s = Card("what a transparent robot can sense with no external sensors")
        s.add(_pairs_table(
            ["Quantity", "How"],
            [("Joint position", "Encoder"),
             ("Joint velocity", "Encoder differentiation"),
             ("Joint torque", "Motor current"),
             ("Contact force", "Torque deviation from the expected model"),
             ("Collision", "Current spike"),
             ("Weight of a held object", "Sustained current"),
             ("Human touch", "Small torque disturbance")],
            [230, 420]))
        s.add(body("This is <b>muscle-like sensing</b>.", dim=True))
        self.add(s)

        self.add(callout(
            (
                "<b>Joint torque or motor torque — which one matters?</b><br><br><b>Joint torque matters. Motor "
                "torque is how we estimate it.</b><br><br>The estimate is only valid through a transparent "
                "transmission. Where it is valid you get proprioception for free; where it isn't, no amount of "
                "filtering recovers it, and you must go buy a force sensor (which can support torque feedback, "
                "impedance control or admittance control; the signal-to-command law decides which)."
            ), "warn"))

        self.finish()

    def _redraw(self):
        n = float(self.s_n.value())
        eff = self.s_eff.value() / 100.0
        self.l_n.setText(f"{n:.0f}:1")
        self.l_eff.setText(f"{eff * 100:.0f}%")

        self.st_refl.set(f"{n * n:,.0f}×")
        err = abs(1.0 - eff) * 100.0
        self.st_err.set(f"{err:.0f}%")
        good = (n <= 10) and (eff >= 0.85)
        self.st_state.set("yes" if good else "no")
        self.st_state.set_color(theme.GOOD if good else theme.BAD)

        c = self.canvas
        c.clear()
        currents = [x * 0.2 for x in range(0, 51)]
        k_t = 0.09
        believed = [joint_torque_from_motor(motor_torque_from_current(a, k_t), n, 1.0)
                    for a in currents]
        actual = [joint_torque_from_motor(motor_torque_from_current(a, k_t), n, eff)
                  for a in currents]
        c.ax.plot(currents, believed, color=theme.ACCENT, lw=2.2,
                  label="what the controller believes  (τ = K_t·I·r)")
        c.ax.plot(currents, actual, color=theme.BAD, lw=2.2, ls="--",
                  label="what the joint actually delivers")
        c.ax.fill_between(currents, believed, actual, color=theme.BAD, alpha=0.15)
        c.ax.set_xlabel("motor current  (A)")
        c.ax.set_ylabel("joint torque  (N·m)")
        c.legend(loc="upper left")
        c.refresh()


# ==========================================================================
# PAGE 18 -- active proprioceptive compliance
# ==========================================================================

class ActiveCompliancePage(Page):
    TITLE = "Active Proprioceptive Compliance"
    SUBTITLE = ("Software-defined compliance: three layers, and the system is "
                "only proprioceptive when all three exist.")
    SECTION = SECTION
    NOTES = "material p.6"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>Definition.</b> Active compliance is <b>software-defined</b> "
            "compliance built from proprioceptive sensing plus real-time control, "
            "<i>instead of</i> physical springs.", "key"))

        s = Card("how it works, step by step")
        s.add(body(
            "<b>Step 1 — detect force via current.</b> An unexpected torque "
            "shows up as a current spike.<br><br>"
            "<b>Step 2 — interpret the force.</b> Is this intentional "
            "manipulation? Contact? A collision? Gravity load? Same measurement, "
            "four completely different correct responses.<br><br>"
            "<b>Step 3 — modulate impedance.</b> The controller adjusts "
            "stiffness, damping, and torque limits — in real time, in "
            "milliseconds."))
        self.add(s)

        m = Card("this mimics biological reflex loops")
        m.add(_pairs_table(
            ["Biology", "Robot"],
            [("Muscle spindle", "Encoder + velocity"),
             ("Golgi tendon organ", "Motor current"),
             ("Reflex modulation", "Software impedance"),
             ("CNS control", "Central controller")],
            [300, 340]))
        self.add(m)

        # ---- interactive ------------------------------------------------------
        i = Card("modulate the impedance live")
        i.add(body(
            "One disturbance, four interpretations. Pick what the controller "
            "decides the contact <i>is</i>, and watch the stiffness and damping "
            "it selects — and what that does to the joint's response.", dim=True))

        self.s_k = slider(0, 300, 120)
        self.s_b = slider(0, 120, 14)
        self.s_lim = slider(1, 100, 40)
        self.l_k, self.l_b, self.l_lim = QLabel(), QLabel(), QLabel()
        i.add_layout(slider_row("stiffness K", self.s_k, self.l_k))
        i.add_layout(slider_row("damping B", self.s_b, self.l_b))
        i.add_layout(slider_row("torque limit (N·m)", self.s_lim, self.l_lim))

        self.st_mode = Stat("behaviour", "--", theme.ACCENT)
        self.st_peak = Stat("peak torque on human", "--", theme.BAD)
        self.st_dev = Stat("how far it yields", "--", theme.GOOD)
        i.add_layout(stat_row(self.st_mode, self.st_peak, self.st_dev))

        self.canvas = MplCanvas(width=7.4, height=3.0)
        i.add(self.canvas)

        presets = Card("presets — what the interpretation step chooses")
        for name, (k, b, lim, why) in {
            "intentional manipulation": (10, 4, 8,
                "The human is leading. Go soft and let them."),
            "expected contact": (90, 12, 30,
                "Picking something up. Firm enough to hold a pose."),
            "collision": (4, 30, 5,
                "Something unexpected. Drop stiffness, raise damping, clamp "
                "torque — yield and bleed energy."),
            "gravity load": (200, 20, 80,
                "Holding a heavy object. Stiff, high limit, no yielding."),
        }.items():
            row = QLabel(f"<b>{name}</b> — K={k}, B={b}, limit={lim} N·m &nbsp; "
                         f"<i>{why}</i>")
            row.setWordWrap(True)
            row.setTextFormat(Qt.RichText)
            row.setStyleSheet(f"color:{theme.TEXT_DIM}; background:transparent;")
            presets.add(row)
        i.add(presets)
        self.add(i)

        for s_ in (self.s_k, self.s_b, self.s_lim):
            s_.valueChanged.connect(self._redraw)
        self._redraw()

        self.add(hline())

        w = Card("why 1X rejected series elastic actuators")
        w.add(body(
            "<b>SEAs give:</b> passive safety — but fixed compliance, bandwidth "
            "loss, and phase lag.<br><br>"
            "<b>Humanoids require:</b> fast balance recovery, manipulation, "
            "catching, reflex-level response.<br><br>"
            "<b>Neo achieves SEA-like safety without SEA lag</b>, by combining a "
            "soft outer body, tendon micro-compliance, and proprioceptive "
            "control."))
        self.add(w)

        l = Card("layered safety — proprioception + soft body = whole-body safety")
        l.add(body(
            "<b>Passive (external)</b><br>"
            "&nbsp;&nbsp;• Polymer lattice skin<br>"
            "&nbsp;&nbsp;• Energy absorption<br><br>"
            "<b>Active (internal)</b><br>"
            "&nbsp;&nbsp;• Proprioceptive sensing<br>"
            "&nbsp;&nbsp;• Torque limiting<br>"
            "&nbsp;&nbsp;• Reflex shutdown<br><br>"
            "This mirrors <b>skin + muscle + reflex arc</b> in humans."))
        self.add(l)

        t = Card("the three layers — all three, or none")
        t.add(body(
            "<b>1. Mechanical transparency</b> → enables force to propagate<br>"
            "<b>2. Internal force estimation</b> → motor current → torque<br>"
            "<b>3. Active impedance control</b> → software-defined compliance"))
        t.add(title("Only when all three exist is the system proprioceptive.", 15))
        self.add(t)

        self.add(callout(
            "<b>Why this matters for household humanoids.</b> They must touch "
            "humans, interact unpredictably, be quiet, be safe, <i>and</i> be "
            "fast. Proprioception enables intuitive interaction, no violent "
            "motion, smooth response, and trust. Without it the robot feels "
            "\"dead\" and interaction feels dangerous.<br><br>"
            "<b>Interview line:</b> \"Because Neo's joints are quasi-direct and "
            "tendon-driven, joint torque propagates directly to the motor, "
            "enabling high-bandwidth proprioceptive force estimation and active "
            "impedance control.\"", "good"))

        self.finish()

    def _redraw(self):
        from ctrlcore.impedance import run_impedance
        k = float(self.s_k.value())
        b = float(self.s_b.value())
        lim = float(self.s_lim.value())
        self.l_k.setText(f"{k:.0f}")
        self.l_b.setText(f"{b:.0f}")
        self.l_lim.setText(f"{lim:.0f}")

        tr = run_impedance(k, b, tau_ff=0.0)
        clipped = [max(-lim, min(lim, t)) for t in tr.tau]
        peak = max(abs(t) for t in clipped)
        dev = math.degrees(max(abs(x) for x in tr.theta))
        self.st_peak.set(f"{peak:.1f} N·m")
        self.st_dev.set(f"{dev:.1f}°")

        z = k + b
        if z < 30:
            mode, colour = "yielding / soft", theme.GOOD
        elif z < 130:
            mode, colour = "compliant", theme.ACCENT
        else:
            mode, colour = "stiff / holding", theme.BAD
        self.st_mode.set(mode)
        self.st_mode.set_color(colour)

        c = self.canvas
        c.clear()
        c.ax.plot(tr.t, tr.tau, color=theme.TEXT_FAINT, lw=1.2, ls="--",
                  label="torque the impedance law wants")
        c.ax.plot(tr.t, clipped, color=colour, lw=2.3,
                  label="torque after the limit")
        c.ax.axhline(lim, color=theme.BAD, lw=1.0, ls=":")
        c.ax.axhline(-lim, color=theme.BAD, lw=1.0, ls=":",
                     label="torque limit (reflex clamp)")
        c.ax.set_xlabel("time (s)")
        c.ax.set_ylabel("τ  (N·m)")
        c.legend(loc="upper right")
        c.refresh()
