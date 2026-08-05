"""
Pages 6-12: what control is actually for, and the four ways to do it.

  6   The Goal of Control  -- from scratch: what are we even trying to achieve?
  7   Position Control     -- when, why, and what it costs
  8   Torque / Current     -- when, why, and what it costs
  9   Impedance Control    -- the virtual spring, in full
 10   Admittance Control   -- force in, motion out, in full
 11   Impedance vs Admittance -- the decision, and the hardware that forces it
 12   The Impedance Spectrum  -- Best/Rouse/Gregg: they were all one controller

Page 12 is the punchline of the whole section: position control, impedance
control and torque control are not three paradigms, they are one controller
with a single knob turned to three different places.
"""

from __future__ import annotations

import math

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
)

from ctrlcore.impedance import (
    VirtualModel,
    equilibrium_angle,
    impedance_magnitude,
    impedance_torque,
    run_admittance,
    run_impedance,
    two_controller_demo,
)
from .. import theme
from ..widgets import (
    BlockDiagram,
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

SECTION = "Control Paradigms"


def _rl_mapping_table():
    """Control vocabulary <-> RL vocabulary, for the second half of the tutor."""
    return _table(
        ["In control", "In reinforcement learning", "On a real robot"],
        [("Controller", "Policy  π(a|s)",
          "The code in the 1 kHz interrupt"),
         ("Control input  u, τ", "Action  a",
          "Motor current, i.e. joint torque"),
         ("State  θ, θ̇", "State  s",
          "Encoder counts and their derivative"),
         ("Plant / process", "Environment",
          "The limb, the gearbox, the floor"),
         ("Reference / setpoint  θ_d", "Goal, or part of the reward",
          "Where you want the joint"),
         ("Cost  J = ∫ e² + ρu²", "Reward  r  (negated)",
          "Error, effort, and what you are willing to trade"),
         ("Disturbance  τ_ext", "Environment stochasticity",
          "The person leaning on the arm")],
        col0=175, colw=245, height=390)


def _pd_vs_imp_table():
    return _table(
        ["", "PD position control", "Impedance control"],
        [("The equation", "τ = −K_p e − K_d ė",
          "τ = −K e − B ė + τ_ff   (identical when τ_ff = 0)"),
         ("What you are trying to achieve",
          "Make e small. Error is the enemy.",
          "Make the force–displacement RELATIONSHIP what you specified. Error "
          "is the mechanism, not the failure."),
         ("How you pick the gains",
          "As high as stability allows. Higher = better tracking.",
          "To hit a target stiffness in N·m/rad, chosen for the task. Often "
          "deliberately LOW."),
         ("Is there a τ_ff?",
          "No. Any steady load must be paid for with standing error, or by an "
          "integrator.",
          "Yes, and it is the whole point: hold the load WITHOUT error, and let "
          "K and B govern only the response to surprises."),
         ("What K means physically",
          "A tuning knob. Units are incidental.",
          "The stiffness a human feels. You could measure it with a spring "
          "scale."),
         ("Response to a person pushing",
          "A disturbance to be rejected. Push harder.",
          "An interaction to be shaped. Yield by exactly τ_ext/K."),
         ("Typical gain magnitude",
          "As high as possible", "Often 10–100× lower, on purpose")],
        col0=200, colw=290, height=520)


def _table(headers, rows, col0=170, colw=280, height=None):
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
    t.setColumnWidth(0, col0)
    for c in range(1, len(headers)):
        t.setColumnWidth(c, colw)
    t.setMinimumHeight(height or (40 + 62 * len(rows)))
    return t


# ==========================================================================
# PAGE 6 -- What is the goal of control?
# ==========================================================================

class GoalOfControlPage(Page):
    TITLE = "The Goal of Control"
    SUBTITLE = ("Start from nothing. What is a controller actually for — and why "
                "\"go to this position\" is the wrong answer for a robot that "
                "touches things.")
    SECTION = SECTION
    NOTES = "from scratch"

    def __init__(self, parent=None):
        super().__init__(parent)

        # ---- the loop, before any equations ---------------------------------
        loop = Card("first: the picture, and it is the same picture as "
                    "reinforcement learning")
        loop.add(body(
            "Later in this tutor you will meet an <b>agent</b> that takes an "
            "<b>action</b>, an <b>environment</b> that responds with a new "
            "<b>state</b> and a <b>reward</b>, and a <b>policy</b> that decides "
            "what to do next. Control is that identical loop with different "
            "vocabulary — and seeing the correspondence early makes both halves "
            "of this tutor easier."))
        self.d_loop = BlockDiagram(width=7.4, height=2.1)
        loop.add(self.d_loop)
        loop.add(_rl_mapping_table())
        loop.add(body(
            "<b>The one real difference:</b> RL <i>learns</i> the policy from "
            "experience; classical control <i>derives</i> it from a model. The "
            "loop, the causality, and the fact that the environment gets the "
            "last word are all identical.<br><br>"
            "And note what the environment is in a robot: <b>gravity, the floor, "
            "the object being carried, and the person leaning on the arm</b>. It "
            "is not noise to be rejected. It is the other half of the system.",
            dim=True))
        self.add(loop)
        self._draw_loop()

        self.add(callout(
            "<b>The naive goal.</b> \"Make the joint go where I tell it.\"<br><br>"
            "That is a complete and correct goal — for a robot in a cage, doing "
            "the same weld a million times, touching nothing but the part it was "
            "designed around. For that robot, position <i>is</i> the task.<br><br>"
            "<b>The moment it fails.</b> The instant something unplanned touches "
            "the robot — a person, an uneven floor, a door that is heavier than "
            "the model said — \"go where I tell you\" becomes \"push through "
            "whatever is in the way.\" A position controller has no vocabulary "
            "for yielding. Its only response to resistance is more torque.",
            "key"))

        g = Card("so what IS the goal?")
        g.add(body(
            "For any robot that shares space with the physical world, the goal is "
            "not a position and not a force. It is:"))
        g.add(title("Regulate the <i>relationship</i> between motion and force "
                    "at the point of contact.", 17))
        g.add(body(
            "That relationship has a name. If you push on something and ask how "
            "much it pushes back, you are asking for its <b>mechanical "
            "impedance</b>. If you push on something and ask how much it moves, "
            "you are asking for its <b>admittance</b>. They are inverses of each "
            "other, and between them they describe everything an interacting "
            "robot needs to decide."))
        g.add(math_label(r"Z(s) = \frac{F(s)}{V(s)} \qquad\quad "
                         r"Y(s) = \frac{V(s)}{F(s)} = \frac{1}{Z(s)}", 16))
        self.add(g)

        # ---- three quantities ------------------------------------------------
        q = Card("you only ever get to command ONE of these")
        grid = QGridLayout()
        grid.setSpacing(12)
        for col, (name, colour, txt) in enumerate((
            ("Position", theme.ACCENT,
             "Command <b>where</b>. The force becomes whatever it has to be to "
             "get there. If a hand is in the way, the force becomes enormous."),
            ("Force / Torque", theme.WARN,
             "Command <b>how hard</b>. The position becomes whatever the world "
             "decides. If nothing resists, the joint runs away."),
            ("Impedance", theme.GOOD,
             "Command <b>the relationship</b>. Neither position nor force is "
             "fixed; the <i>ratio</i> between them is. This is the only one of "
             "the three that is safe by construction."),
        )):
            c = Card(name)
            lb = QLabel(name.upper())
            lb.setStyleSheet(f"color:{colour}; font-weight:800; font-size:11px;"
                             f"background:transparent; letter-spacing:1px;")
            c.add(lb)
            c.add(body(txt))
            grid.addWidget(c, 0, col)
            grid.setColumnStretch(col, 1)
        q.add_layout(grid)
        self.add(q)

        self.add(callout(
            "<b>You cannot command position and force independently.</b> Once the "
            "environment is in contact, they are locked together by physics. "
            "Choose one and the world chooses the other. The whole of interaction "
            "control is the study of that trade — which is exactly why the "
            "impedance formulation is so useful: it lets you specify the trade "
            "itself instead of picking a side.", "warn"))

        # ---- how do we reach the goal ---------------------------------------
        self.add(hline())
        self.add(title("How do we reach the goal?"))

        h = Card("four strategies, in the order they were invented")
        h.add(_table(
            ["", "What you command", "What you measure", "What the world gets to decide"],
            [
                ("Position control", "a trajectory θ_d(t)", "joint angle θ",
                 "the interaction force — unbounded"),
                ("Torque / current control", "a torque τ(t)", "motor current I",
                 "the resulting motion — unbounded"),
                ("Impedance control", "K, B and an equilibrium",
                 "joint angle θ and velocity θ̇",
                 "both, but only within the K, B relationship you set"),
                ("Admittance control", "M_v, B_v, K_v of a virtual model",
                 "interaction force F", "nothing — the robot moves to admit you"),
            ], col0=175, colw=225))
        self.add(h)

        self.add(body(
            "The next four pages take these one at a time: what it is, when to "
            "use it, why, and what it costs you. Then the Impedance Spectrum page "
            "shows that they were all secretly the same equation.", dim=True))

        # ---- what "good" means -----------------------------------------------
        g2 = Card("what a controller is judged on — five things, always in tension")
        g2.add(body(
            "<b>1 · Stability.</b> Does it stay bounded? Non-negotiable, and the "
            "first thing every other property is traded against.<br><br>"
            "<b>2 · Tracking / steady-state accuracy.</b> Does it get there, and "
            "stay there under load? This is what integral action buys.<br><br>"
            "<b>3 · Bandwidth / responsiveness.</b> How fast can it correct? "
            "Bounded by mechanics and by delay, as the last five pages "
            "established.<br><br>"
            "<b>4 · Disturbance rejection.</b> How hard does it fight what it did "
            "not expect? Note this is the <i>same</i> knob as compliance, "
            "measured with the opposite sign — a robot that rejects disturbances "
            "well is a robot that fights people.<br><br>"
            "<b>5 · Robustness.</b> Does it still work when the payload changes, "
            "the joint heats up, or the model is 20% wrong? A controller tuned to "
            "the edge of stability on a bench is not a controller."))
        g2.add(body(
            "<b>The reason interaction control exists at all</b> is that #4 is "
            "the wrong objective when a person is involved. A perfect "
            "disturbance-rejecting controller treats a human hand as an error to "
            "be crushed. Impedance control is what you get when you decide that "
            "the right goal is not to <i>reject</i> the interaction but to "
            "<b>shape</b> it.", dim=True))
        self.add(g2)

        self.finish()

    def _draw_loop(self):
        d = self.d_loop
        d.band(0.15, 3.05, 0.45, 1.95, "the robot's side", theme.ACCENT)
        d.band(4.75, 7.85, 0.45, 1.95, "the world's side", theme.WARN)
        d.block(1.6, 1.35, "Controller / Policy", colour=theme.ACCENT,
                w=1.9, sub="decides what to do")
        d.block(6.3, 1.35, "Plant + Environment", colour=theme.WARN, w=2.1,
                sub="gravity, floor, objects, people")
        d.arrow(2.6, 1.35, 5.2, 1.35, "action:  torque / position command")
        d.feedback(6.3, 1.35, 1.6, 1.11,
                   "state: θ, θ̇, measured force   —   the environment always answers",
                   drop=0.72)
        d.note(4.0, 0.30, "the environment gets the last word",
               colour=theme.TEXT_FAINT)
        d.done()


# ==========================================================================
# PAGE 7 -- Position control
# ==========================================================================

class PositionControlPage(Page):
    TITLE = "Position Control"
    SUBTITLE = "Command where. Accept whatever force that takes."
    SECTION = SECTION
    NOTES = "from scratch"

    def __init__(self, parent=None):
        super().__init__(parent)

        c = Card("what it is")
        self.d_pos = BlockDiagram(width=7.4, height=2.0)
        c.add(self.d_pos)
        c.add(math_label(r"\tau = -K_p(\theta - \theta_d) "
                         r"- K_d(\dot\theta - \dot\theta_d)", 17))
        c.add(body(
            "A PD loop. Error in, torque out. Raise the gains until the error is "
            "small enough for the task and stop thinking about it."))
        c.add(body(
            "The defining property is that it is <b>purely reactive</b>: the "
            "controller can only produce torque <i>in response to an observed "
            "error</i>. If gravity, inertia or a person is loading the joint, "
            "there <b>must</b> be a standing tracking error, because that error "
            "is the only thing generating the torque that holds the load. "
            "Perfect tracking and non-zero load are mutually exclusive.", dim=True))
        self.add(c)

        self.add(callout(
            "This also causes inevitable <b>phase lag</b> between a time-varying "
            "reference and the actual joint position. You are always chasing. "
            "(An integral term helps when the required output is constant — but "
            "the only way an integrator changes its output is by accumulating "
            "more error, so it is a slow fix, not a preventive one.)", "warn"))

        w = Card("when to use it — and why")
        w.add(body(
            "<b>Use it when the environment is known and rigid.</b><br>"
            "• Pick-and-place, welding, machining, 3D printing — the geometry is "
            "the task and nothing unexpected is in the workspace.<br>"
            "• As the <b>inner loop</b> of something smarter. Every admittance "
            "controller in existence has a high-gain position loop at the bottom "
            "of it (page 10).<br>"
            "• When your hardware leaves you no choice. Behind a 100:1 gearbox "
            "with high stiction you cannot do faithful torque control anyway; "
            "position is what the mechanics will actually deliver.<br><br>"
            "<b>Why it wins there:</b> it is the most accurate and most robust "
            "thing you can do. High gains reject disturbances hard. Nothing beats "
            "it for repeatability."))
        w.add(body(
            "<b>Do not use it when a human is in the loop.</b> A stiff position "
            "controller treats a person as a disturbance to be rejected. That is "
            "exactly the wrong behaviour, and it is dangerous in proportion to "
            "how good the controller is.", dim=True))
        self.add(w)

        # ---- interactive -----------------------------------------------------
        i = Card("feel the stiffness")
        i.add(body(
            "A 6 N·m push is applied for 0.6 s. Raise the gain and watch the "
            "deviation shrink while the fight-back torque grows. The compliant "
            "robot and the accurate robot are the same robot with the dial in "
            "two places.", dim=True))
        self.s_kp = slider(1, 400, 60)
        self.s_kd = slider(0, 100, 8)
        self.l_kp, self.l_kd = QLabel(), QLabel()
        i.add_layout(slider_row("K_p  (N·m/rad)", self.s_kp, self.l_kp))
        i.add_layout(slider_row("K_d  (N·m·s/rad)", self.s_kd, self.l_kd))

        self.st_dev = Stat("peak deviation", "--", theme.WARN)
        self.st_tau = Stat("peak torque", "--", theme.BAD)
        self.st_res = Stat("residual error", "--", theme.TEXT_DIM)
        i.add_layout(stat_row(self.st_dev, self.st_tau, self.st_res))

        self.canvas = MplCanvas(width=7.4, height=3.4, nrows=2)
        i.add(self.canvas)
        self.add(i)
        self.s_kp.valueChanged.connect(self._redraw)
        self.s_kd.valueChanged.connect(self._redraw)
        self._redraw()

        self.add(callout(
            "<b>Position control is a special case of impedance control</b> — the "
            "one where the feedforward torque is zero. Hold that thought; the "
            "Impedance Spectrum page makes it exact.", "key"))

        pid = Card("in practice this is a PID, and PIDs have failure modes")
        pid.add(body(
            "Everything above is the <b>PD</b> part. Add an integrator and you "
            "can finally hold a load with zero steady-state error — at the cost "
            "of phase margin, and of <b>windup</b> whenever the actuator "
            "saturates.<br><br>"
            "Timing matters too: if the loop jitters, it is the <b>D</b> term "
            "that breaks, because it is the only one that divides by Δt.<br><br>"
            "The next page is entirely about those failures and their fixes."))
        self.add(pid)

        self._draw_diagram()
        self.finish()

    def _draw_diagram(self):
        d = self.d_pos
        d.sum(0.75, 1.35, signs=("+", "−"))
        d.block(2.3, 1.35, "PD / PID", colour=theme.ACCENT, w=1.3,
                sub="K_p e + K_d ė")
        d.plant(5.0, 1.35, "Joint", sub="J θ̈ + b θ̇ = τ + τ_ext", w=1.7)
        d.arrow(0.15, 1.35, 0.59, 1.35, "θ_d")
        d.arrow(0.91, 1.35, 1.65, 1.35, "e")
        d.arrow(2.95, 1.35, 4.15, 1.35, "τ  (via motor current)")
        d.arrow(5.85, 1.35, 7.4, 1.35, "θ")
        d.arrow(5.0, 2.15, 5.0, 1.62, "τ_ext  (the world pushes)",
                colour=theme.WARN, dashed=True)
        d.feedback(6.9, 1.35, 0.75, 1.13, "measured θ, θ̇", drop=0.62)
        d.note(2.3, 0.42, "torque is an OUTPUT here — whatever the error demands",
               colour=theme.TEXT_FAINT)
        d.done()

    def _redraw(self):
        kp = float(self.s_kp.value())
        kd = float(self.s_kd.value())
        self.l_kp.setText(f"{kp:.0f}")
        self.l_kd.setText(f"{kd:.0f}")
        tr = run_impedance(kp, kd, tau_ff=0.0)

        dev = max(abs(x) for x in tr.theta)
        self.st_dev.set(f"{math.degrees(dev):.1f}°")
        self.st_tau.set(f"{max(abs(x) for x in tr.tau):.1f} N·m")
        self.st_res.set(f"{math.degrees(abs(tr.theta[-1])):.2f}°")

        c = self.canvas
        c.clear()
        a1, a2 = c.axes
        a1.plot(tr.t, [math.degrees(x) for x in tr.theta],
                color=theme.ACCENT, lw=2.0)
        a1.axhline(0, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a1.set_ylabel("θ  (°)")
        a2.plot(tr.t, tr.tau, color=theme.BAD, lw=1.8, label="motor torque")
        a2.plot(tr.t, tr.f_ext, color=theme.WARN, lw=1.4, ls="--",
                label="human push")
        a2.set_xlabel("time (s)")
        a2.set_ylabel("τ  (N·m)")
        c.legend(a2, loc="upper right")
        c.refresh()


# ==========================================================================
# PAGE 8 -- Torque / current control
# ==========================================================================

class TorqueControlPage(Page):
    TITLE = "Torque & Current Control"
    SUBTITLE = "Command how hard. Accept whatever motion that produces."
    SECTION = SECTION
    NOTES = "from scratch"

    def __init__(self, parent=None):
        super().__init__(parent)

        # ---- the cascade, which answers most of the confusion ----------------
        casc = Card("the cascade — and yes, position control is ALSO current "
                    "control")
        casc.add(body(
            "This is the picture that dissolves the question \"what is the "
            "reference in torque control?\" Every electric drive is the same "
            "nest of loops:"))
        self.d_casc = BlockDiagram(width=7.6, height=2.4)
        casc.add(self.d_casc)
        casc.add(body(
            "<b>Read it from the inside out.</b> The current loop is always "
            "there, always running at 10–40 kHz, and it is the only thing that "
            "actually touches the hardware. Everything outside it exists purely "
            "to <b>generate its setpoint</b>."))
        casc.add(body(
            "<b>So what distinguishes the paradigms is WHERE YOU INJECT.</b><br><br>"
            "&nbsp;&nbsp;• <b>Position control</b> — inject at the outermost "
            "loop. Position error generates a velocity reference, which "
            "generates a current reference.<br>"
            "&nbsp;&nbsp;• <b>Torque control</b> — <b>bypass the outer loops "
            "entirely</b> and write the current reference yourself.<br>"
            "&nbsp;&nbsp;• <b>Impedance control</b> — also injects at the current "
            "reference, but computes it from position error.<br>"
            "&nbsp;&nbsp;• <b>Admittance control</b> — injects at the outermost "
            "loop, computing the <i>position</i> reference from measured force."))
        casc.add(body(
            "You were right to be suspicious: <b>they are all current control at "
            "the bottom.</b> \"Torque control\" does not mean a different "
            "actuator — it means you took responsibility for the current "
            "reference instead of letting a cascade of error loops produce it.",
            dim=True))
        self.add(casc)

        self.add(callout(
            "<b>\"So in torque control, what IS the reference?\"</b><br><br>"
            "There isn't one, in the feedback sense — and that is the defining "
            "property, not an omission. Torque control is <b>open loop in "
            "position</b>. The torque command comes from outside the loop "
            "entirely:<br><br>"
            "&nbsp;&nbsp;• <b>Inverse dynamics</b> — τ = M(q)q̈<sub>d</sub> + "
            "C(q,q̇)q̇ + g(q). You computed what torque the motion requires.<br>"
            "&nbsp;&nbsp;• <b>An impedance law</b> — τ from position error, which "
            "makes it an impedance controller.<br>"
            "&nbsp;&nbsp;• <b>A trajectory optimiser</b>, offline.<br>"
            "&nbsp;&nbsp;• <b>An RL policy</b> emitting joint torques directly — "
            "this is what most locomotion policies do.<br>"
            "&nbsp;&nbsp;• <b>A human</b>, through a haptic device.<br><br>"
            "The <i>only</i> feedback loop that remains closed is the current "
            "loop making sure the commanded torque is actually delivered. Where "
            "the joint ends up is the world's business.", "key"))

        c = Card("what it is — and why it is really CURRENT control")
        c.add(body(
            "You do not have a torque actuator. You have a current amplifier "
            "attached to a magnetic field. What makes torque control possible at "
            "all is one linear relationship:"))
        c.add(math_label(r"\tau = K_t \cdot I", 18))
        c.add(body(
            "τ is motor torque, K<sub>t</sub> the torque constant, I the current. "
            "Command a current and you have commanded a torque — <b>with no "
            "sensor at all</b>. This is the cheapest force actuation in "
            "robotics, and, run backwards, the cheapest force <i>sensor</i>: "
            "read the current and you have read the torque."))
        self.add(c)

        self.add(callout(
            "<b>The catch, and it is the whole ballgame.</b> τ = K<sub>t</sub>·I "
            "tells you the torque <i>at the rotor</i>. What you actually care "
            "about is the torque <i>at the joint</i>:<br><br>"
            "&nbsp;&nbsp;&nbsp;&nbsp;τ<sub>joint</sub> ≈ τ<sub>motor</sub> · r"
            "<br><br>"
            "…which is only true if r is known and the losses are small and "
            "predictable: <b>low friction, low backlash, transparency</b>. Behind "
            "a harmonic drive with 20 N of stiction, motor current tells you "
            "about the gearbox, not about the world.", "warn"))

        w = Card("when to use it — and why")
        w.add(body(
            "<b>Use it when the interaction is the task.</b><br>"
            "• Legged locomotion: you want a specified ground reaction force, not "
            "a specified foot position. The floor decides the position.<br>"
            "• Anything with an accurate dynamic model, where you can compute the "
            "torque required and just <i>apply</i> it — feedforward. This is "
            "faster than any feedback loop because there is no error to wait "
            "for.<br>"
            "• As the output stage of impedance control. Impedance controllers "
            "command torque; they are torque controllers with an opinion.<br><br>"
            "<b>Why it wins there:</b> maximum transparency and zero phase lag "
            "from feedback, because there is no feedback. On a backdriveable "
            "drive it is the closest thing to \"the robot is not there.\""))
        w.add(body(
            "<b>The cost.</b> Open loop in position. Feedforward control cannot "
            "modify its behaviour when conditions differ from expected — it will "
            "confidently apply yesterday's torque to today's world. Drift, "
            "accumulate model error, and nothing corrects it. Also: on a geared "
            "drive it is a lie, as above.", dim=True))
        self.add(w)

        s = Card("where 'force' can come from in a robot")
        for key, (name, txt) in {
            "sensor": ("Direct force/torque sensor",
                       "Load cell or strain gauge. Honest and direct — but noisy, "
                       "lower bandwidth, fragile, and you cannot afford one in "
                       "every joint, every finger, every tendon."),
            "current": ("Motor current  (τ ∝ I)",
                        "Free, kHz-rate, low latency. Truthful only through a "
                        "transparent transmission."),
            "estimate": ("Model-based estimate",
                         "From dynamics, from motor + kinematics, or from an "
                         "impedance model. Cheap and everywhere — and only as "
                         "good as the model."),
        }.items():
            s.add(body(f"<b>{name}</b> — {txt}"))
        s.add(body(
            "All three are valid. <b>They are not equivalent conceptually</b>, "
            "and confusing them is how people end up claiming force feedback they "
            "do not have (see the Positive Force Feedback pages).", dim=True))
        self.add(s)

        i = Card("open-loop torque: perfect transparency, zero authority")
        i.add(body(
            "Command a constant torque against gravity-free friction, then push. "
            "Notice the joint never comes back. There is no restoring force "
            "because there is no position feedback — ||Z|| = 0.", dim=True))
        self.s_tau = slider(-40, 40, 0)
        self.l_tau = QLabel()
        i.add_layout(slider_row("commanded τ  (×0.1 N·m)", self.s_tau, self.l_tau))
        self.canvas = MplCanvas(width=7.4, height=2.8)
        i.add(self.canvas)
        self.add(i)
        self.s_tau.valueChanged.connect(self._redraw)
        self._redraw()

        self._draw_cascade()
        self.finish()

    def _draw_cascade(self):
        d = self.d_casc
        d.band(0.15, 7.9, 0.30, 2.28, "position control injects HERE ↴",
               theme.ACCENT)
        d.band(2.35, 7.9, 0.55, 1.95, "velocity loop", theme.VIOLET)
        d.band(4.75, 7.9, 0.78, 1.72, "current loop  10–40 kHz", theme.GOOD)

        d.sum(0.72, 1.30, signs=("+", "−"))
        d.block(1.75, 1.30, "position\nloop", colour=theme.ACCENT, w=1.0)
        d.sum(2.72, 1.30, signs=("+", "−"))
        d.block(3.62, 1.30, "velocity\nloop", colour=theme.VIOLET, w=0.95)
        d.sum(4.52, 1.30, signs=("+", "−"))
        d.block(5.45, 1.30, "current\nloop", colour=theme.GOOD, w=0.95)
        d.plant(6.95, 1.30, "Motor + Joint", sub="τ = K_t·I", w=1.35)

        d.arrow(0.16, 1.30, 0.56, 1.30, "θ_d")
        d.arrow(0.88, 1.30, 1.25, 1.30)
        d.arrow(2.25, 1.30, 2.56, 1.30, "θ̇_d", fontsize=6.8)
        d.arrow(2.88, 1.30, 3.14, 1.30)
        d.arrow(4.10, 1.30, 4.36, 1.30, "I_d", fontsize=6.8)
        d.arrow(4.68, 1.30, 4.97, 1.30)
        d.arrow(5.93, 1.30, 6.28, 1.30, "V", fontsize=6.8)
        d.arrow(7.62, 1.30, 7.9, 1.30)

        d.note(2.4, 2.12, "torque control writes I_d directly — everything to "
                          "its left is skipped",
               colour=theme.WARN, ha="left", fontsize=6.9)
        d.arrow(4.52, 2.02, 4.52, 1.50, colour=theme.WARN, dashed=True)
        d.note(4.0, 0.16, "every paradigm ends at the same current loop",
               colour=theme.TEXT_FAINT)
        d.done()

    def _redraw(self):
        tau = self.s_tau.value() * 0.1
        self.l_tau.setText(f"{tau:+.1f}")
        tr = run_impedance(0.0, 0.0, tau_ff=tau)
        c = self.canvas
        c.clear()
        c.ax.plot(tr.t, [math.degrees(x) for x in tr.theta],
                  color=theme.WARN, lw=2.2, label="θ — goes where the world says")
        c.ax.plot(tr.t, [x * 3 for x in tr.f_ext], color=theme.TEXT_FAINT,
                  lw=1.3, ls="--", label="human push (scaled)")
        c.ax.axhline(0, color=theme.BORDER, lw=1.0)
        c.ax.set_xlabel("time (s)")
        c.ax.set_ylabel("θ  (°)")
        c.legend(loc="upper left")
        c.refresh()


# ==========================================================================
# PAGE 9 -- Impedance control
# ==========================================================================

class ImpedanceControlPage(Page):
    TITLE = "Impedance Control"
    SUBTITLE = "\"Motion in → force out.\" You do not command a position; you "\
               "command a push proportional to how far away you are."
    SECTION = SECTION
    NOTES = "material p.1 · Hogan 1984"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>The virtual spring.</b> In impedance control you treat the robot "
            "as a spring-damper system.<br><br>"
            "&nbsp;&nbsp;<b>The goal:</b> you want to reach position "
            "X<sub>d</sub>.<br>"
            "&nbsp;&nbsp;<b>The process:</b> an external force pushes the robot "
            "away to X<sub>m</sub>, and the controller computes<br>"
            "&nbsp;&nbsp;<b>The result:</b> the motor produces a <b>torque</b> to "
            "push back. You aren't commanding a position; you are commanding a "
            "\"push\" proportional to how far away you are from your goal.",
            "key"))

        e = Card("the control law")
        self.d_imp = BlockDiagram(width=7.4, height=2.0)
        e.add(self.d_imp)
        e.add(math_label(r"\tau = K(X_d - X_m) + B(\dot X_d - \dot X_m)", 18))
        e.add(body(
            "<b>K</b> — virtual stiffness. How hard it resists displacement.<br>"
            "<b>B</b> — virtual damping. How hard it resists velocity.<br>"
            "<b>X<sub>d</sub></b> — the virtual rest position of the spring.",
            dim=True))
        e.add(body(
            "Written for a joint, in the form used from here on:"))
        e.add(math_label(r"\tau = -K(\theta - \theta_d) "
                         r"- B(\dot\theta - \dot\theta_d) + \tau_{ff}", 17))
        e.add(body(
            "The τ<sub>ff</sub> term is a feedforward torque — the torque the "
            "controller applies <i>even when tracking perfectly</i>. Set it to "
            "zero and this is literally the PD position controller from page 7. "
            "Page 12 makes that equivalence a theorem.", dim=True))
        self.add(e)

        w = Card("when to use it — and why")
        w.add(body(
            "<b>Use it when the robot is backdriveable.</b> Direct drive, "
            "quasi-direct drive, low-ratio transmissions, tendon drives, SEAs. "
            "Impedance control needs the motor to <i>feel</i> the human through "
            "the encoder; if the mechanics hide the motion, the controller is "
            "blind.<br><br>"
            "<b>Why it wins:</b> no force sensor needed. No extra hardware, no "
            "extra failure point, no bandwidth ceiling from a load cell. The "
            "encoder you already have is the sensor, and the whole loop runs at "
            "whatever rate your current loop runs at.<br><br>"
            "<b>Why it is safe:</b> the maximum force the robot can exert is "
            "bounded by K times the displacement. Bound the displacement — a soft "
            "limit — and you have bounded the force. Safety by construction "
            "rather than by watchdog."))
        w.add(body(
            "<b>Do not use it behind a big gearbox.</b> Impedance control is an "
            "<b>open-loop force</b> strategy: you command a torque and "
            "<i>assume</i> the mechanics will let the arm move if someone pushes "
            "it. With a 100:1 harmonic drive that assumption is false — see "
            "\"Gearing & Reflected Inertia\".", dim=True))
        self.add(w)

        # ---- interactive ----------------------------------------------------
        i = Card("tune the virtual spring")
        i.add(body(
            "Same 6 N·m push. Watch three separate things: how far it moves, how "
            "hard it fights back, and how it settles. Low K + low B is a robot "
            "you can walk into safely. High K + low B rings. High K + high B is "
            "a position controller wearing a costume.", dim=True))

        self.s_k = slider(0, 300, 45)
        self.s_b = slider(0, 120, 10)
        self.s_ff = slider(-40, 40, 0)
        self.l_k, self.l_b, self.l_ff = QLabel(), QLabel(), QLabel()
        i.add_layout(slider_row("virtual stiffness K", self.s_k, self.l_k))
        i.add_layout(slider_row("virtual damping B", self.s_b, self.l_b))
        i.add_layout(slider_row("feedforward τ_ff (×0.1)", self.s_ff, self.l_ff))

        self.st_z = Stat("‖Z‖ = |K|+|B|", "--", theme.VIOLET)
        self.st_dev = Stat("peak deviation", "--", theme.WARN)
        self.st_eq = Stat("θ_eq", "--", theme.ACCENT)
        i.add_layout(stat_row(self.st_z, self.st_dev, self.st_eq))

        self.canvas = MplCanvas(width=7.4, height=3.4, nrows=2)
        i.add(self.canvas)
        self.add(i)
        for s in (self.s_k, self.s_b, self.s_ff):
            s.valueChanged.connect(self._redraw)
        self._redraw()

        self.add(callout(
            "<b>Watch θ_eq as you move τ_ff.</b> The equilibrium angle is "
            "<i>not</i> where you want the joint to be. It is a control input "
            "chosen so that, after the world pushes back, the joint ends up "
            "where you wanted. θ_eq = θ_d + (τ_ff + Bθ̇_d)/K. Two controllers "
            "with wildly different θ_eq can produce identical walking.", "warn"))

        # ---- PD vs impedance --------------------------------------------------
        self.add(hline())
        self.add(title("\"I still can't separate PD control from impedance "
                       "control\" — because structurally they are the same"))

        pd = Card("the honest answer")
        pd.add(body(
            "You are not missing something. Put them side by side:"))
        pd.add(math_label(r"\text{PD:}\quad \tau = -K_p(\theta-\theta_d) "
                          r"- K_d(\dot\theta-\dot\theta_d)", 15))
        pd.add(math_label(r"\text{Impedance:}\quad \tau = -K(\theta-\theta_d) "
                          r"- B(\dot\theta-\dot\theta_d) + \tau_{ff}", 15))
        pd.add(body(
            "<b>Set τ<sub>ff</sub> = 0 and they are character-for-character "
            "identical.</b> Any PD position controller <i>is</i> an impedance "
            "controller. The equation cannot tell you which one you are running."))
        pd.add(_pd_vs_imp_table())
        pd.add(body(
            "<b>The practical test:</b> ask what happens when you <b>double the "
            "gains</b>. If your answer is \"tracking gets better\", you are "
            "thinking in position control. If it is \"the joint gets stiffer, "
            "which is a physical property I chose deliberately and could have "
            "chosen differently\", you are thinking in impedance.<br><br>"
            "Same code. Different question being asked of it. That is genuinely "
            "the whole distinction, and being clear-eyed about that is more "
            "useful than inventing one.", dim=True))
        self.add(pd)

        # ---- theta_eq ---------------------------------------------------------
        self.add(hline())
        self.add(title("Why θ_eq is not θ_d — and how it is actually chosen"))

        eq = Card("the joint is not alone")
        eq.add(body(
            "If the joint were floating in space, commanding θ_eq would put it at "
            "θ_eq and there would be no puzzle. But a prosthetic ankle is being "
            "pressed by the ground and driven by the user. Those interaction "
            "torques τ<sub>ext</sub> do not go away because your controller "
            "ignores them."))
        eq.add(body("At equilibrium the controller torque balances the external "
                    "torque:"))
        eq.add(math_label(r"K(\theta_{eq} - \theta) = -\tau_{ext} "
                          r"\quad\Rightarrow\quad "
                          r"\theta = \theta_{eq} + \frac{\tau_{ext}}{K}", 16))
        eq.add(body(
            "So the joint settles <b>offset from θ_eq</b> by exactly "
            "τ<sub>ext</sub>/K. To make it land on the angle you actually want, "
            "you must aim <b>off-target</b>, by that same offset:"))
        eq.add(math_label(r"\theta_{eq} = \theta_d - \frac{\tau_{ext}}{K} "
                          r"\;=\; \theta_d + \frac{\tau_{ff} + B\dot\theta_d}{K}",
                          16))
        eq.add(body(
            "<b>That is the entire mystery.</b> θ_eq is not a target — it is a "
            "target <i>pre-distorted</i> by the load you expect. Like aiming "
            "upwind. Softer spring (small K) → bigger offset. Stiff spring "
            "(large K) → θ_eq ≈ θ_d, which is why nobody notices this in "
            "high-gain position control.", dim=True))
        self.add(eq)

        how = Card("so how do you choose it? Not by trial and error.")
        how.add(body(
            "<b>1 · From biomechanics data (the usual answer for prostheses).</b> "
            "Able-bodied datasets give you both the joint angle <i>and</i> the "
            "joint moment through the gait cycle. Set θ_d to the measured angle "
            "and τ<sub>ff</sub> to the measured moment. Then compute θ_eq. Both "
            "inputs are <b>directly observable in a motion-capture lab</b>; θ_eq "
            "is not, which is exactly why parameterising by it was a bad "
            "idea.<br><br>"
            "<b>2 · From a dynamic model.</b> Inverse dynamics or trajectory "
            "optimisation gives you the τ<sub>ff</sub> that produces the motion "
            "you want.<br><br>"
            "<b>3 · By learning it.</b> An RL policy that outputs joint torque is "
            "producing τ<sub>ff</sub>, whether or not it was told so — and you "
            "can differentiate the policy to read off the K and B it implicitly "
            "chose. That is Property 2 on the Impedance Spectrum page.<br><br>"
            "<b>4 · Trial and error</b> — the historical method, and the reason "
            "impedance tuning has a reputation for being black magic. You are "
            "hand-tuning a quantity that has no physical referent."))
        how.add(body(
            "<b>The paper's point in one line:</b> stop parameterising by "
            "(K, B, θ_eq), which nobody can observe or interpret. Parameterise "
            "by (K, B, τ_ff, θ_d), where θ_d is <i>where you want the joint</i> "
            "and τ_ff is <i>the torque that gets it there</i> — both meaningful, "
            "both measurable.", dim=True))
        self.add(how)

        # ---- what is being modelled -------------------------------------------
        mod = Card("\"what is the spring-damper modelling — motor↔link, or "
                   "link↔environment?\"")
        mod.add(body(
            "<b>Link ↔ environment. The interaction port.</b><br><br>"
            "The virtual spring-damper describes the relationship between "
            "<b>how far the robot is from its reference</b> and <b>the force it "
            "exchanges with whatever it is touching</b>. You are specifying what "
            "the robot <i>feels like to push</i>.<br><br>"
            "It is <b>not</b> a model of the motor-to-link drivetrain. That "
            "physical chain — rotor, gearbox, spring, link — is the <i>plant</i>, "
            "and it is what determines whether you can successfully render the "
            "impedance you asked for. The impedance law is the behaviour you "
            "want; the drivetrain decides whether you get it."))
        mod.add(body(
            "This is why the actuator pages came first. Asking for K = 5 N·m/rad "
            "on a joint whose reflected inertia is 0.1 kg·m² behind a stiction "
            "band is asking for something the hardware will simply not deliver — "
            "and the controller has no way to tell you.", dim=True))
        self.add(mod)

        code = Card("the entire controller")
        pane = CodePane(get_source(impedance_torque))
        pane.sizeHintLine(11)
        code.add(pane)
        code.add(body(
            "That is the whole thing. Everything else on this page is about "
            "when the two gains are allowed to be what you want them to be.",
            dim=True))
        self.add(code)

        self._draw_diagram()
        self.finish()

    def _draw_diagram(self):
        d = self.d_imp
        d.sum(0.75, 1.35, signs=("+", "−"))
        d.block(2.15, 1.35, "K, B", colour=theme.GOOD, w=1.15,
                sub="virtual spring-damper")
        d.sum(3.25, 1.35, signs=("+", "+"))
        d.plant(5.1, 1.35, "Joint + Environment",
                sub="the impedance is rendered HERE", w=2.0)
        d.arrow(0.15, 1.35, 0.59, 1.35, "θ_d")
        d.arrow(0.91, 1.35, 1.55, 1.35, "e")
        d.arrow(2.73, 1.35, 3.09, 1.35)
        d.arrow(3.41, 1.35, 4.1, 1.35, "τ")
        # feedforward rail: in from the right, then down into the summing node
        d.ax.plot([5.85, 3.25], [2.05, 2.05], color=theme.VIOLET, lw=1.4,
                  ls="--")
        d.note(4.55, 2.22, "τ_ff  feedforward torque", colour=theme.VIOLET,
               fontsize=7.4)
        d.arrow(3.25, 2.05, 3.25, 1.53, colour=theme.VIOLET, dashed=True)
        d.arrow(6.1, 1.35, 7.4, 1.35, "θ")
        d.feedback(6.9, 1.35, 0.75, 1.13, "measured θ, θ̇  —  MOTION IN", drop=0.62)
        d.note(2.15, 0.40, "FORCE OUT: torque proportional to displacement",
               colour=theme.GOOD)
        d.done()

    def _redraw(self):
        k = float(self.s_k.value())
        b = float(self.s_b.value())
        ff = self.s_ff.value() * 0.1
        self.l_k.setText(f"{k:.0f}")
        self.l_b.setText(f"{b:.0f}")
        self.l_ff.setText(f"{ff:+.1f}")

        tr = run_impedance(k, b, tau_ff=ff)
        self.st_z.set(f"{impedance_magnitude(k, b):.0f}")
        self.st_dev.set(f"{math.degrees(max(abs(x) for x in tr.theta)):.1f}°")
        eq = equilibrium_angle(0.0, 0.0, k, b, ff)
        self.st_eq.set("∞" if math.isinf(eq) else f"{math.degrees(eq):+.1f}°")

        c = self.canvas
        c.clear()
        a1, a2 = c.axes
        a1.plot(tr.t, [math.degrees(x) for x in tr.theta], color=theme.GOOD,
                lw=2.2, label="θ")
        if not math.isinf(eq):
            a1.axhline(math.degrees(eq), color=theme.ACCENT, lw=1.1, ls=":",
                       label="θ_eq")
        a1.axhline(0, color=theme.TEXT_FAINT, lw=1.0, ls="--", label="θ_d")
        a1.set_ylabel("θ  (°)")
        c.legend(a1, loc="upper left")
        a2.plot(tr.t, tr.tau, color=theme.BAD, lw=1.8, label="motor torque")
        a2.plot(tr.t, tr.f_ext, color=theme.WARN, lw=1.4, ls="--",
                label="human push")
        a2.set_xlabel("time (s)")
        a2.set_ylabel("τ  (N·m)")
        c.legend(a2, loc="upper right")
        c.refresh()


# ==========================================================================
# PAGE 10 -- Admittance control
# ==========================================================================

class AdmittanceControlPage(Page):
    TITLE = "Admittance Control"
    SUBTITLE = "\"Force in → motion out.\" Measure the push, invent the motion a "\
               "perfect robot would have made, then go there."
    SECTION = SECTION
    NOTES = "material p.1"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>The exact mirror of impedance control.</b> Impedance measures "
            "motion and outputs force. Admittance measures <b>force</b> and "
            "outputs <b>motion</b>. Same physics, opposite causality, and the "
            "choice between them is decided almost entirely by your gearbox.",
            "key"))

        self.d_adm = BlockDiagram(width=7.6, height=2.3)
        self.add(self.d_adm)

        # ---- the translator -------------------------------------------------
        t = Card("the \"translator\": from force to motion")
        t.add(body(
            "How does 10 N of force become a \"move 2 degrees\" command? You use "
            "a <b>virtual model</b>.<br><br>"
            "Inside your software you create a <b>ghost robot</b> that has no "
            "friction. You define its virtual properties:"))
        t.add(body(
            "&nbsp;&nbsp;<b>M<sub>v</sub></b> — virtual mass. How heavy you want "
            "the robot to <i>feel</i>.<br>"
            "&nbsp;&nbsp;<b>B<sub>v</sub></b> — virtual damping. How \"thick\" or "
            "viscous the air feels.<br>"
            "&nbsp;&nbsp;<b>K<sub>v</sub></b> — virtual stiffness. Usually set to "
            "<b>0</b> for transparent following."))
        t.add(math_label(r"M_v\ddot x + B_v\dot x + K_v x = F_{ext}", 17))
        self.add(t)

        loop = Card("the calculation loop")
        loop.add(body(
            "<b>1. Read force.</b> &nbsp; F<sub>ext</sub> = 10 N<br>"
            "<b>2. Calculate acceleration.</b> &nbsp; ẍ = F<sub>ext</sub> / "
            "M<sub>v</sub><br>"
            "<b>3. Integrate for velocity.</b> &nbsp; ẋ<sub>new</sub> = "
            "ẋ<sub>old</sub> + ẍ·Δt<br>"
            "<b>4. Integrate for position.</b> &nbsp; x<sub>new</sub> = "
            "x<sub>old</sub> + ẋ<sub>new</sub>·Δt"))
        pane = CodePane(get_source(VirtualModel.step))
        pane.sizeHintLine(19)
        loop.add(pane)
        self.add(loop)

        ex = Card("the execution: the inner loop")
        ex.add(body(
            "Once you have x<sub>new</sub> — the target position — you send it to "
            "the motor's <b>internal position controller</b>, usually a high-gain "
            "PID loop.<br><br>"
            "Because the motor is very strong and the PID is stiff, the motor "
            "moves to that position accurately <b>regardless of the gear "
            "friction</b>. To the human it feels like the robot is weightless and "
            "following their hand perfectly."))
        ex.add(body(
            "Notice the inversion: the <i>stiffness</i> of the inner loop is what "
            "makes the outer behaviour <i>soft</i>. The robot is rigid so that it "
            "can be commanded to be gentle.", dim=True))
        self.add(ex)

        w = Card("when to use it — and why")
        w.add(body(
            "<b>Use it when the robot is NOT backdriveable.</b> High gear ratios, "
            "harmonic drives, ball screws with load, anything with serious "
            "stiction. The F/T sensor sits <b>outside</b> the transmission, so it "
            "notices you before the gears do.<br><br>"
            "<b>Why it wins there:</b> it allows the robot to use its own power to "
            "overcome its own friction. The robot feels your 1 N push and says: "
            "<i>\"I will start the motor for you so you don't have to fight my "
            "10,000× inertia.\"</i><br><br>"
            "<b>The costs:</b> you need an F/T sensor (money, fragility, noise, "
            "bandwidth ceiling). And it can go <b>unstable on contact with stiff "
            "environments</b> — pressing a rigid wall means a tiny motion causes a "
            "huge force change, which the loop turns into a bigger motion. "
            "Impedance control has the opposite failure mode: it is stable "
            "against walls and useless in free space at high gearing."))
        self.add(w)

        # ---- interactive -----------------------------------------------------
        i = Card("feel the ghost robot — including the stiction bypass")
        i.add(body(
            "Turn <b>gearbox stiction</b> up and watch what does <i>not</i> "
            "happen: the response barely changes. The force sensor never had to "
            "fight the gears to notice you. That is the entire argument for "
            "admittance control on a geared drive.", dim=True))

        self.s_m = slider(2, 200, 20)
        self.s_b = slider(0, 200, 60)
        self.s_st = slider(0, 100, 0)
        self.l_m, self.l_b, self.l_st = QLabel(), QLabel(), QLabel()
        i.add_layout(slider_row("virtual mass M_v (×0.1)", self.s_m, self.l_m))
        i.add_layout(slider_row("virtual damping B_v (×0.1)", self.s_b, self.l_b))
        i.add_layout(slider_row("gearbox stiction (N·m)", self.s_st, self.l_st))

        self.st_move = Stat("motion from 6 N·m", "--", theme.GOOD)
        self.st_settle = Stat("drift after push", "--", theme.WARN)
        i.add_layout(stat_row(self.st_move, self.st_settle))

        self.canvas = MplCanvas(width=7.4, height=3.4, nrows=2)
        i.add(self.canvas)
        self.add(i)
        for s in (self.s_m, self.s_b, self.s_st):
            s.valueChanged.connect(self._redraw)
        self._redraw()

        self.add(callout(
            "<b>Your beam-balance project is classic admittance control.</b> You "
            "measure the excessive torque and use it to decide where the beam "
            "should go.<br><br>"
            "• <b>Your logic:</b> a desired state (zero momentum / torque "
            "balance); measure actual torque T<sub>measured</sub>; find the error "
            "T<sub>excess</sub> = 6 N·m.<br>"
            "• <b>The virtual world:</b> feed that 6 N·m into a virtual "
            "mass-spring-damper model in your code.<br>"
            "• <b>The command:</b> the code computes <i>\"if a 6 N·m force hit a "
            "virtual object with this much inertia and damping, it would move at "
            "this velocity.\"</i><br>"
            "• <b>The result:</b> you send a position or velocity command to your "
            "stiff motor. The motor moves to \"admit\" the force, which makes the "
            "beam feel compliant to the person touching it.", "good"))

        # ---- the shape of the response ---------------------------------------
        self.add(hline())
        self.add(title("\"What exactly is the relation between force and motion? "
                       "How smooth, how fast?\""))

        sh = Card("read it off the virtual model — all three parameters have "
                  "a job")
        sh.add(body(
            "Apply a constant force F to M<sub>v</sub>ẍ + B<sub>v</sub>ẋ + "
            "K<sub>v</sub>x = F and the answer is a first-order velocity "
            "response with a very concrete shape:"))
        sh.add(math_label(r"\dot x(t) = \frac{F}{B_v}\left(1 - "
                          r"e^{-t/(M_v/B_v)}\right)", 17))
        sh.add(body(
            "<b>Terminal velocity = F / B<sub>v</sub>.</b> This is the "
            "\"gearing\" of the interaction: push with 10 N against "
            "B<sub>v</sub> = 5 and the robot ends up moving at 2 units/s. "
            "<b>B<sub>v</sub> sets how far you get per newton.</b><br><br>"
            "<b>Time constant = M<sub>v</sub> / B<sub>v</sub>.</b> How long it "
            "takes to reach that speed. <b>M<sub>v</sub> sets the smoothness and "
            "the lag.</b> Big M<sub>v</sub> feels like pushing a heavy trolley: "
            "gradual, forgiving, hard to jerk. Small M<sub>v</sub> feels darty "
            "and immediate — and amplifies every bit of sensor noise into "
            "motion.<br><br>"
            "<b>Initial acceleration = F / M<sub>v</sub>.</b> The instant "
            "response to your push.<br><br>"
            "<b>K<sub>v</sub> decides whether it comes back.</b> At 0 (the usual "
            "choice) the robot stays wherever you left it — a frictionless cart. "
            "Non-zero, and it drifts back to a home pose, which you sometimes "
            "want for a tool holder and almost never want for hand-guiding."))
        sh.add(body(
            "<b>And deceleration is symmetric:</b> let go, and the velocity "
            "decays with the same M<sub>v</sub>/B<sub>v</sub>. That is why "
            "hand-guided industrial arms feel like they are moving through "
            "syrup — the damping is deliberately high so the arm stops promptly "
            "when you release it, rather than coasting into something.",
            dim=True))
        self.add(sh)

        self.add(callout(
            "<b>Typical numbers, for a hand-guided arm.</b> Aim for a terminal "
            "velocity around 0.1–0.3 m/s at a comfortable 20–30 N push, and a "
            "time constant of 0.1–0.3 s. Faster than that and the arm feels "
            "twitchy and unsafe; slower and it feels like it is resisting "
            "you.<br><br>"
            "<b>The stability limit.</b> You cannot simply keep lowering "
            "M<sub>v</sub> to make it feel lighter. Rendering a virtual mass much "
            "below the true joint inertia demands high loop gain, and high loop "
            "gain plus sensor delay is exactly the recipe for oscillation on "
            "contact. This is the well-known result that <b>admittance control "
            "goes unstable against stiff environments</b> — press a rigid wall "
            "and a tiny motion produces a huge force change, which the loop turns "
            "into a bigger motion. Impedance control has the mirror-image failure: "
            "stable on walls, useless in free space behind a gearbox.", "warn"))

        self._draw_diagram()
        self.finish()

    def _draw_diagram(self):
        d = self.d_adm
        d.band(3.35, 7.9, 0.55, 2.02, "the robot's own stiff inner loop",
               theme.ACCENT)
        d.block(1.05, 1.35, "F/T sensor", colour=theme.WARN, w=1.15,
                sub="at the contact point")
        d.block(2.75, 1.35, "virtual model", colour=theme.VIOLET, w=1.25,
                sub="M_v ẍ + B_v ẋ + K_v x = F")
        d.sum(4.35, 1.35, signs=("+", "−"))
        d.block(5.45, 1.35, "stiff PID", colour=theme.ACCENT, w=1.05)
        d.plant(7.05, 1.35, "Geared joint", sub="high friction, not backdrivable",
                w=1.5)
        d.arrow(0.2, 1.35, 0.45, 1.35)
        d.note(0.12, 1.62, "human push", colour=theme.WARN, fontsize=6.9,
               ha="left")
        d.arrow(1.65, 1.35, 2.1, 1.35, "F", fontsize=7)
        d.arrow(3.4, 1.35, 4.17, 1.35, "x_ref", fontsize=7)
        d.arrow(4.53, 1.35, 4.9, 1.35)
        d.arrow(6.0, 1.35, 6.28, 1.35, "τ", fontsize=7)
        d.feedback(7.6, 1.35, 4.35, 1.13, "measured θ", drop=0.55)
        d.note(2.75, 0.32, "FORCE IN → MOTION OUT", colour=theme.VIOLET)
        d.note(1.05, 2.15, "sensor is OUTSIDE the gearbox — this is the bypass",
               colour=theme.WARN, fontsize=6.9, ha="left")
        d.done()

    def _redraw(self):
        m = self.s_m.value() * 0.1
        b = self.s_b.value() * 0.1
        st = float(self.s_st.value())
        self.l_m.setText(f"{m:.1f}")
        self.l_b.setText(f"{b:.1f}")
        self.l_st.setText(f"{st:.0f}")

        tr = run_admittance(m, b, stiction=st)
        self.st_move.set(f"{math.degrees(max(abs(x) for x in tr.theta)):.1f}°")
        self.st_settle.set(f"{math.degrees(abs(tr.theta[-1])):.1f}°")

        c = self.canvas
        c.clear()
        a1, a2 = c.axes
        a1.plot(tr.t, [math.degrees(x) for x in tr.theta_ref], color=theme.VIOLET,
                lw=1.6, ls="--", label="ghost robot (virtual model)")
        a1.plot(tr.t, [math.degrees(x) for x in tr.theta], color=theme.GOOD,
                lw=2.2, label="real joint")
        a1.set_ylabel("position  (°)")
        c.legend(a1, loc="upper left")
        a2.plot(tr.t, tr.tau, color=theme.BAD, lw=1.6, label="inner-loop torque")
        a2.plot(tr.t, tr.f_ext, color=theme.WARN, lw=1.4, ls="--",
                label="measured human force")
        a2.set_xlabel("time (s)")
        a2.set_ylabel("τ  (N·m)")
        c.legend(a2, loc="upper right")
        c.refresh()


# ==========================================================================
# PAGE 11 -- Impedance vs admittance
# ==========================================================================

class ImpVsAdmPage(Page):
    TITLE = "Impedance vs Admittance"
    SUBTITLE = ("The fundamental difference is what the controller \"sees\" as "
                "the input, and what it tells the motor to do.")
    SECTION = SECTION
    NOTES = "material p.1"

    def __init__(self, parent=None):
        super().__init__(parent)

        t = Card("side by side")
        t.add(_table(
            ["Feature", "Impedance Control", "Admittance Control"],
            [
                ("Philosophy", "\"Motion in → Force out\"", "\"Force in → Motion out\""),
                ("Input", "Position / velocity (from encoders)",
                 "Interaction force / torque (from F/T sensor)"),
                ("Output", "Torque command to the motor",
                 "Position / velocity command to the motor"),
                ("Analogy", "A physical spring you are pushing.",
                 "A shopping cart that \"admits\" your push."),
                ("Hardware", "Best for \"soft\" motors (direct drive, low ratio)",
                 "Best for \"stiff\" motors (high gear ratios)"),
                ("Extra sensor?", "None — the encoder is enough",
                 "Requires an F/T sensor at the contact point"),
                ("Fails when…",
                 "Gears hide the motion, so the controller never sees the push",
                 "Contact with a very stiff environment — small motion, huge "
                 "force change, loop goes unstable"),
                ("Bandwidth limit",
                 "Current-loop rate; very high",
                 "F/T sensor bandwidth and inner-loop rate"),
            ], col0=140, colw=330, height=560))
        self.add(t)

        self.add(callout(
            "<b>The fundamental difference lies in what the controller \"sees\" "
            "as the input and what it tells the motor to do.</b> Everything else "
            "in the table follows from that one line.", "key"))

        d = Card("the decision, as a flowchart in words")
        d.add(body(
            "<b>1. Is the joint backdriveable?</b> Push the powered-off robot by "
            "hand. Does it move easily?<br>"
            "&nbsp;&nbsp;&nbsp;<b>Yes</b> → impedance control. You get force "
            "control for free from the encoder and current sensor.<br>"
            "&nbsp;&nbsp;&nbsp;<b>No</b> → you cannot do impedance control "
            "honestly, whatever the software claims. Go to 2.<br><br>"
            "<b>2. Can you put an F/T sensor at the contact point?</b><br>"
            "&nbsp;&nbsp;&nbsp;<b>Yes</b> → admittance control. The sensor "
            "bypasses the transmission.<br>"
            "&nbsp;&nbsp;&nbsp;<b>No</b> → you have a position-controlled robot. "
            "Be honest about it and keep people out of the workspace.<br><br>"
            "<b>3. Will it touch stiff things?</b> If yes, prefer impedance; "
            "admittance destabilises against rigid contact. If it mostly moves in "
            "free space with a human leading it, admittance feels better."))
        self.add(d)

        self.add(callout(
            "<b>Why the 100:1 case forces the answer.</b> At N = 100 the "
            "reflected inertia is 10,000× and the breakaway stiction may be 20 N. "
            "In impedance control the motor 'feels' the user through motion — but "
            "the gears mask that motion entirely. Admittance control uses an "
            "external force sensor to bypass the gear friction, allowing the "
            "controller to 'see' the user's intent even when the gears are "
            "physically locked.", "good"))

        self.finish()


# ==========================================================================
# PAGE 12 -- The impedance spectrum
# ==========================================================================

class SpectrumPage(Page):
    TITLE = "The Impedance Spectrum"
    SUBTITLE = ("Position, impedance and torque control are one controller with "
                "one knob. Best, Rouse & Gregg, 2025.")
    SECTION = SECTION
    NOTES = "ImpedanceControl.pdf"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "The classic impedance law hides its own structure. Add and subtract "
            "Bθ̇_d, regroup, and a completely different reading falls out — one "
            "in which the three paradigms of the last five pages are the same "
            "equation at three settings.", "key"))

        d = Card("the decoupling")
        d.add(body("Start from the traditional form, where θ_eq is the "
                   "equilibrium angle:"))
        d.add(math_label(r"\tau = -K(\theta - \theta_{eq}) - B\dot\theta"))
        d.add(body("Define the <b>deviation angle</b> θ̂ := θ_eq − θ_d, "
                   "substitute, add and subtract Bθ̇_d, and group:", dim=True))
        d.add(math_label(r"\tau = \underbrace{-K(\theta-\theta_d) "
                         r"- B(\dot\theta - \dot\theta_d)}_{\rm feedback}"
                         r" + \underbrace{K\hat\theta - B\dot\theta_d}_{\rm feedforward}"))
        d.add(body("θ̂ is free, so the second group can be anything at all. "
                   "Name it τ_ff:", dim=True))
        d.add(math_label(r"\boxed{\;\tau = -K(\theta-\theta_d) "
                         r"- B(\dot\theta-\dot\theta_d) + \tau_{ff}\;}", 18))
        d.add(body("And to go back:", dim=True))
        d.add(math_label(r"\theta_{eq} = \theta_d + "
                         r"\frac{\tau_{ff} + B\dot\theta_d}{K}", 16))
        self.add(d)

        p = Card("the four properties")
        p.add(body(
            "<b>Property 1.</b> An impedance controller is mathematically "
            "equivalent to a feedforward torque controller combined with a PD "
            "position controller. <i>So a PD position controller is just the "
            "special case τ_ff = 0.</i>"))
        p.add(body(
            "<b>Property 2.</b> An impedance controller is a <b>first-order "
            "approximation to any torque policy</b> τ = f(θ, θ̇, ξ) about a "
            "nominal trajectory. Taylor-expand f and equate coefficients:"))
        p.add(math_label(r"\tau_{ff} = f(\theta_d,\dot\theta_d,\xi_d),\quad "
                         r"K = -\frac{\partial f}{\partial\theta},\quad "
                         r"B = -\frac{\partial f}{\partial\dot\theta}", 15))
        p.add(body(
            "That includes a neural-network policy. Train a network to output "
            "ankle torque, differentiate it along a nominal gait, and you have "
            "read its stiffness and damping — even though the author never "
            "designed any.", dim=True))
        p.add(body(
            "<b>Property 3.</b> When θ = θ_d and θ̇ = θ̇_d, the feedback term is "
            "<b>exactly zero</b> and the controller reduces to τ = τ_ff. K and B "
            "can be varied arbitrarily <b>without changing the output at all</b>."))
        p.add(body(
            "<b>Corollary 3.1.</b> If two controllers share a τ_ff that makes the "
            "system follow the desired kinematics, they produce the <b>same "
            "torque and the same angles</b> regardless of differences in "
            "stiffness and damping."))
        self.add(p)

        self.add(callout(
            "<b>The tuning consequence, and it is a sharp one.</b> If you tune K "
            "and B by watching nominal walking, you are tuning parameters that "
            "<i>have no effect on nominal walking</i>. Their entire influence "
            "lives in the perturbed response. Tuning on nominal behaviour alone "
            "is not merely incomplete — it is uninformative.", "warn"))

        # ---- interactive ----------------------------------------------------
        i = Card("two controllers, one nominal behaviour")
        i.add(body(
            "Controller <b>α</b> uses biological ankle stiffness and damping. "
            "Controller <b>β</b> uses flat, medium constants. Both share the same "
            "θ_d, θ̇_d and τ_ff.<br><br>"
            "With the perturbation at <b>0°</b> the two torque curves lie exactly "
            "on top of each other — that is Property 3, drawn. Their equilibrium "
            "angles are wildly different and it does not matter. Now drag the "
            "perturbation.", dim=True))

        self.s_ka = slider(0, 300, 160)
        self.s_kb = slider(0, 300, 45)
        self.s_pert = slider(-80, 80, 0)
        self.l_ka, self.l_kb, self.l_pert = QLabel(), QLabel(), QLabel()
        i.add_layout(slider_row("α stiffness K_α", self.s_ka, self.l_ka))
        i.add_layout(slider_row("β stiffness K_β", self.s_kb, self.l_kb))
        i.add_layout(slider_row("perturbation (×0.1°)", self.s_pert, self.l_pert))

        self.st_gap = Stat("peak torque gap", "--", theme.BAD)
        self.st_za = Stat("‖Z‖ of α", "--", theme.ACCENT)
        self.st_zb = Stat("‖Z‖ of β", "--", theme.GOOD)
        i.add_layout(stat_row(self.st_gap, self.st_za, self.st_zb))

        self.canvas = MplCanvas(width=7.5, height=3.6, nrows=2)
        i.add(self.canvas)
        self.add(i)
        for s in (self.s_ka, self.s_kb, self.s_pert):
            s.valueChanged.connect(self._redraw)
        self._redraw()

        # ---- the spectrum ----------------------------------------------------
        sp = Card("the spectrum: ‖Z‖ = |K| + |B|")
        sp.add(body(
            "Every joint-space controller lives somewhere on one axis."))
        self.spec = MplCanvas(width=7.5, height=1.9)
        sp.add(self.spec)
        sp.add(body(
            "<b>Left (‖Z‖ = 0):</b> pure feedforward torque control. Prioritises "
            "nominal <b>torques</b>; position goes where the world says.<br>"
            "<b>Right (‖Z‖ ≫ 0):</b> high-gain position control. Prioritises "
            "nominal <b>positions</b>; torque does whatever it must.<br>"
            "<b>Middle:</b> where almost every published \"impedance controller\" "
            "actually lives.<br><br>"
            "The impedance magnitude is therefore a <b>design knob that trades "
            "between enforcing nominal joint torques and enforcing nominal joint "
            "positions</b> — not a category you belong to."))
        self.add(sp)
        self._draw_spectrum()

        self.add(callout(
            "<b>Why this matters even if you never write an impedance "
            "controller.</b> Understanding where a controller sits on this "
            "spectrum predicts its behaviour under perturbation — even for "
            "controllers never designed with impedance in mind. An RL policy that "
            "outputs joint torque has a K and a B; you can measure them by "
            "differentiating it. If they come out negative, the policy will "
            "<i>amplify</i> deviations rather than correct them, which is a real "
            "and checkable failure mode.", "key"))

        h = Card("and it maps onto human motor control")
        h.add(body(
            "The two parameterisations line up with two long-standing theories of "
            "how people move.<br><br>"
            "<b>Traditional form (K, B, θ_eq)</b> ↔ the <b>equilibrium point "
            "hypothesis</b>: the nervous system regulates muscle recruitment "
            "thresholds, and the resulting joint torque and equilibrium position "
            "<i>emerge</i> from interaction with the environment rather than from "
            "explicit calculation.<br><br>"
            "<b>Decoupled form (K, B, τ_ff, θ_d)</b> ↔ <b>internal model "
            "theory</b>: motor commands like τ_ff are directly computed from an "
            "internal dynamic model to achieve a task.<br><br>"
            "Skeletal muscle-tendon units have long been shown to have spring- "
            "and damper-like responses to displacement — the linear \"short-range "
            "stiffness\" at small displacements. Joint perturbation studies during "
            "gait find the same thing. That biological match may be exactly why "
            "impedance control has worked so well for prostheses."))
        self.add(h)

        self.finish()

    def _redraw(self):
        ka = float(self.s_ka.value())
        kb = float(self.s_kb.value())
        pert = self.s_pert.value() * 0.1
        ba, bb = ka * 0.06, kb * 0.06
        self.l_ka.setText(f"{ka:.0f}")
        self.l_kb.setText(f"{kb:.0f}")
        self.l_pert.setText(f"{pert:+.1f}°")

        ph, thd, ta, tb, eqa, eqb = two_controller_demo(ka, ba, kb, bb, pert)
        gap = max(abs(a - b) for a, b in zip(ta, tb))
        self.st_gap.set(f"{gap:.1f} N·m")
        self.st_za.set(f"{impedance_magnitude(ka, ba):.0f}")
        self.st_zb.set(f"{impedance_magnitude(kb, bb):.0f}")

        c = self.canvas
        c.clear()
        a1, a2 = c.axes
        a1.plot(ph, ta, color=theme.ACCENT, lw=2.6, label="controller α  (bio K,B)")
        a1.plot(ph, tb, color=theme.GOOD, lw=1.8, ls="--",
                label="controller β  (flat K,B)")
        a1.set_ylabel("ankle torque  (N·m)")
        a1.set_title("torque output" +
                     ("  —  IDENTICAL: the feedback term is zero" if abs(pert) < 1e-9
                      else "  —  they separate in proportion to K"),
                     fontsize=9)
        c.legend(a1, loc="lower left")

        a2.plot(ph, eqa, color=theme.ACCENT, lw=1.8, label="θ_eq of α")
        a2.plot(ph, eqb, color=theme.GOOD, lw=1.8, ls="--", label="θ_eq of β")
        a2.plot(ph, thd, color=theme.TEXT_FAINT, lw=1.6, ls=":",
                label="θ_d  (what we actually want)")
        a2.set_xlabel("gait cycle (%)")
        a2.set_ylabel("angle  (°)")
        a2.set_ylim(-60, 60)
        c.legend(a2, loc="upper left")
        c.refresh()

    def _draw_spectrum(self):
        c = self.spec
        c.clear()
        ax = c.ax
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 1)
        ax.axis("off")
        ax.annotate("", xy=(9.7, 0.55), xytext=(0.3, 0.55),
                    arrowprops=dict(arrowstyle="-|>", color=theme.TEXT_DIM, lw=1.6))
        for x, lab, sub, colour in (
            (0.6, "Torque\nControl", "‖Z‖ = 0", theme.WARN),
            (5.0, "Impedance\nControl", "‖Z‖ moderate", theme.GOOD),
            (9.0, "Position\nControl", "‖Z‖ ≫ 0", theme.ACCENT),
        ):
            ax.scatter([x], [0.55], s=90, color=colour, zorder=5)
            ax.text(x, 0.72, lab, color=colour, fontsize=9, ha="center",
                    fontweight="bold")
            ax.text(x, 0.34, sub, color=theme.TEXT_FAINT, fontsize=8, ha="center")
        ax.text(0.6, 0.10, "prioritise nominal TORQUES", color=theme.TEXT_DIM,
                fontsize=8, ha="center")
        ax.text(9.0, 0.10, "prioritise nominal POSITIONS", color=theme.TEXT_DIM,
                fontsize=8, ha="center")
        c.refresh()
