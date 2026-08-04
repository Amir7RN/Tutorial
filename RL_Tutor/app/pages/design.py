"""
Pages 13-15: choosing a drivetrain for a real machine.

 13  Which Actuator, Which Robot -- humanoid, biped, quadruped
 14  Scaling Up                  -- the square-cube law and hybrid actuation
 15  Case Study: 1X Neo          -- a machine that refuses all three categories

Page 14 is where the mechanics of pages 1-5 stop being an academic exercise:
inertia grows as L^5, so the same design that works at 20 kg is unbuildable
at 200 kg, and the fix is not a bigger motor.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem

from ctrlcore.actuators import scale_factors
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

SECTION = "Robot Design"


# ==========================================================================
# PAGE 13 -- which actuator for which robot
# ==========================================================================

class ActuatorChoicePage(Page):
    TITLE = "Which Actuator, Which Robot"
    SUBTITLE = ("Humanoid, biped, quadruped — three machines, three different "
                "answers, all from the same physics.")
    SECTION = SECTION
    NOTES = "material p.4"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(body(
            "The five actuator pages gave you the curves. This page is what to "
            "actually build, and it changes with what the robot has to survive."))

        h = Card("for a humanoid  (e.g. 1X Neo)")
        h.add(title("You want SEAs in the arms and legs.", 15))
        h.add(body(
            "<b>Why?</b> Because a humanoid interacts with humans. If Neo "
            "accidentally hits a child's hand, the <b>series spring</b> allows the "
            "limb to \"give\" instantly — <i>even before the 1 kHz software can "
            "react</i>. It mimics the compliance of the human muscle-tendon "
            "unit.<br><br>"
            "This is the passive-safety argument in full: the spring compresses "
            "in ~0.1 ms, the control loop needs ~1.0 ms just to notice. No amount "
            "of software is fast enough to substitute."))
        self.add(h)

        b = Card("for a biped  (balancing / walking)")
        b.add(title("You might use a hybrid: SEA + PEA.", 15))
        b.add(body(
            "&nbsp;&nbsp;<b>SEA in the ankle</b> — fine balance control and "
            "impact absorption. The ankle is where the ground arrives.<br>"
            "&nbsp;&nbsp;<b>PEA in the knee</b> — help support the weight of the "
            "torso without draining the battery. The knee is where the standing "
            "load lives.<br><br>"
            "Two different failure modes, two different springs, two different "
            "places to put them. This is the payoff for understanding that SEA "
            "helps at high ω and PEA helps at low ω."))
        self.add(b)

        q = Card("for a quadruped  (running / jumping)")
        q.add(title("Usually QDD — quasi-direct drive.", 15))
        q.add(body(
            "<b>Why?</b> Running requires extremely fast leg repositioning. A "
            "spring (SEA) might be too slow to \"swing\" the leg forward in time "
            "for the next step — you would be fighting your own low-pass "
            "filter.<br><br>"
            "Quadrupeds instead rely on <b>software compliance</b>: simulating a "
            "spring using high-speed motor control, rather than installing a "
            "physical one. You give up passive safety and buy back bandwidth. "
            "For a machine that is not usually holding hands with a person, that "
            "is a good trade."))
        self.add(q)

        self.add(callout(
            "<b>The script.</b> \"While Direct Drive offers high transparency, it "
            "lacks the 'Passive Safety' inherent in biological systems. By using "
            "<b>Series Elastic Actuators</b>, we replicate the <b>Hill Muscle "
            "Model</b>, effectively decoupling the motor inertia from the "
            "environment during high-frequency impacts. This allows us to achieve "
            "'Human-Safe' interaction without sacrificing the force-density "
            "needed for heavy lifting, especially if we augment it with "
            "<b>Parallel Elasticity</b> for gravity compensation in the stance "
            "phase.\"", "good"))

        self.finish()


# ==========================================================================
# PAGE 14 -- scaling up
# ==========================================================================

class ScalingPage(Page):
    TITLE = "Scaling Up: The Square-Cube Law"
    SUBTITLE = ("Mass goes as L³, torque as L², inertia as L⁵. Physics works "
                "against you as robots get bigger.")
    SECTION = SECTION
    NOTES = "material p.4"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>The systems-design question.</b> \"Design an agile, large-scale "
            "humanoid for a hazardous construction zone.\" The answer is not one "
            "actuator type. It is three pillars: <b>the square-cube law "
            "(scaling)</b>, <b>actuator topology (SEA vs QDD vs PEA)</b>, and "
            "<b>environmental robustness</b>.", "key"))

        s = Card("the challenge of scale")
        s.add(body(
            "Move from a small robot to a \"horse\"-sized humanoid and physics "
            "works against you:"))
        s.add(math_label(r"m \propto L^3 \qquad \tau \propto L^2 "
                         r"\qquad J \propto L^5", 18))
        s.add(body(
            "&nbsp;&nbsp;<b>Mass</b> increases by the <b>cube</b> of the "
            "scale.<br>"
            "&nbsp;&nbsp;<b>Strength / torque</b> increases by only the "
            "<b>square</b> (cross-sectional area of motor and gear teeth).<br>"
            "&nbsp;&nbsp;<b>Inertia</b> increases by the <b>fifth power</b> — "
            "mass × length², i.e. L³ × L²."))
        s.add(body(
            "<b>The general conclusion:</b> as you scale up, your robot becomes "
            "\"lazier\" and \"weaker\" relative to its own weight.", dim=True))
        self.add(s)

        i = Card("drag the scale")
        self.s_L = slider(50, 400, 100)
        self.l_L = QLabel()
        i.add_layout(slider_row("linear scale  (%)", self.s_L, self.l_L))
        self.st_m = Stat("mass ×", "--", theme.WARN)
        self.st_t = Stat("torque ×", "--", theme.GOOD)
        self.st_j = Stat("inertia ×", "--", theme.BAD)
        self.st_r = Stat("torque per kg", "--", theme.VIOLET)
        i.add_layout(stat_row(self.st_m, self.st_t, self.st_j, self.st_r))
        self.canvas = MplCanvas(width=7.4, height=3.0)
        i.add(self.canvas)
        i.add(body(
            "The gap between the torque line and the mass line is the problem. "
            "The inertia line is the reason a big robot cannot be caught by "
            "software when it falls.", dim=True))
        self.add(i)
        self.s_L.valueChanged.connect(self._redraw)
        self._redraw()

        c = Card("what that forces you to do")
        c.add(body(
            "<b>Small robot (agile):</b> you can use <b>QDD</b>. Because the mass "
            "is low, you don't need high gear ratios. This gives incredible "
            "agility and transparency.<br><br>"
            "<b>Large robot (heavy work):</b> you are <b>forced</b> into high gear "
            "ratios (100:1 or more) just to lift your own limbs. That introduces "
            "high reflected inertia, making the robot stiff and prone to breaking "
            "its gears on impact — and, as page 5 showed, blind to human touch."))
        self.add(c)

        self.add(hline())
        self.add(title("The hybrid actuation strategy"))

        strat = Card("three body regions, three answers")
        strat.add(body(
            "<b>A. Lower body (legs) — Series Elastic Actuators.</b><br>"
            "&nbsp;&nbsp;<i>Why:</i> construction sites are uneven. The robot "
            "<b>will</b> trip, fall, or drop heavy beams.<br>"
            "&nbsp;&nbsp;<i>Benefit:</i> in a large-scale robot the gears are the "
            "most fragile part. An SEA provides <b>passive mechanical "
            "protection</b> — when the foot hits a concrete step hard, the spring "
            "absorbs the shock before it shatters the high-ratio harmonic "
            "drive.<br>"
            "&nbsp;&nbsp;<i>Bonus:</i> store energy in the springs during walking, "
            "like an Achilles tendon — vital for a heavy robot's battery life."))
        strat.add(body(
            "<b>B. Back / waist — Parallel Elastic Actuators.</b><br>"
            "&nbsp;&nbsp;<i>Why:</i> manual labour means holding heavy loads for "
            "long periods.<br>"
            "&nbsp;&nbsp;<i>Benefit:</i> carrying a 50 kg bag of cement, a PEA "
            "spring in parallel with the motor can \"cancel out\" that weight. The "
            "motor provides the torque to <b>move</b>; the spring provides the "
            "torque to <b>hold</b>. Prevents thermal shutdown in a hot "
            "environment."))
        strat.add(body(
            "<b>C. Upper body / arms — Quasi-Direct Drive.</b><br>"
            "&nbsp;&nbsp;<i>Why:</i> agility and interaction.<br>"
            "&nbsp;&nbsp;<i>Benefit:</i> if the robot needs to catch a falling "
            "tool or react to a human coworker, it needs high <b>bandwidth</b>. "
            "QDD keeps the arms transparent and fast."))
        self.add(strat)

        haz = Card("design considerations for hazardous zones")
        haz.add(body(
            "<b>Thermal management.</b> Large motors generate massive heat, "
            "especially fighting high friction in geared systems. Liquid cooling "
            "or advanced heat-sinking for the leg actuators, which do the most "
            "work.<br><br>"
            "<b>Ingress protection.</b> Construction sites are dusty (concrete "
            "dust is abrasive) and wet. Actuators must be sealed to IP65 or "
            "higher. This is a <b>pro for SEAs</b> — you can seal the "
            "motor/gearbox inside a housing and expose only the spring-load "
            "interface.<br><br>"
            "<b>Admittance control for manual labour.</b> Since the large robot "
            "has high-ratio gears, use admittance control for the arms. This lets "
            "the robot feel a human \"leading\" it — a coworker helping carry a "
            "heavy pipe — without the user having to fight the motor's internal "
            "friction."))
        self.add(haz)

        self.add(callout(
            "<b>The summary.</b> \"To design an agile, large-scale construction "
            "humanoid, my primary consideration is managing the <b>L⁵ scaling of "
            "inertia</b>. I would move away from the quasi-direct drive used in "
            "small robots and implement <b>SEAs in the legs</b> to protect the "
            "high-ratio gears from high-impact shocks. To handle heavy manual "
            "labour I would add <b>parallel elasticity</b> to the lumbar and knee "
            "joints to offload the static weight. Finally I would use an "
            "<b>admittance control</b> framework so that, despite the high gear "
            "ratios required for scale, the robot remains safe and compliant when "
            "interacting with human workers.\"", "good"))

        self.finish()

    def _redraw(self):
        L = self.s_L.value() / 100.0
        f = scale_factors(L)
        self.l_L.setText(f"{L:.2f}×")
        self.st_m.set(f"{f['mass']:.2f}")
        self.st_t.set(f"{f['torque']:.2f}")
        self.st_j.set(f"{f['inertia']:.2f}")
        self.st_r.set(f"{f['torque_per_mass']:.2f}")

        c = self.canvas
        c.clear()
        xs = [x / 100.0 for x in range(50, 401)]
        c.ax.plot(xs, [x ** 2 for x in xs], color=theme.GOOD, lw=2.2,
                  label="torque  ∝ L²")
        c.ax.plot(xs, [x ** 3 for x in xs], color=theme.WARN, lw=2.2,
                  label="mass  ∝ L³")
        c.ax.plot(xs, [x ** 5 for x in xs], color=theme.BAD, lw=2.4,
                  label="inertia  ∝ L⁵")
        c.ax.axvline(L, color=theme.ACCENT, lw=1.2)
        c.ax.set_yscale("log")
        c.ax.set_xlabel("linear scale L  (×)")
        c.ax.set_ylabel("multiplier (log)")
        c.legend(loc="upper left")
        c.refresh()


# ==========================================================================
# PAGE 15 -- 1X Neo case study
# ==========================================================================

class NeoPage(Page):
    TITLE = "Case Study: 1X Neo"
    SUBTITLE = ("A tendon-driven proprioceptive quasi-direct drive — a machine "
                "that deliberately fits none of the three boxes.")
    SECTION = SECTION
    NOTES = "material p.5"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "Neo's actuation doesn't fit neatly into a single category. It is "
            "best described as a <b>Tendon-Driven Proprioceptive (Quasi-Direct) "
            "Drive</b>.<br><br>"
            "1X intentionally <b>rejected the SEA path</b> for the same reason it "
            "appears in the SEA \"cons\" list: <b>bandwidth</b>. If you want a "
            "robot to catch a ball or react at lightning speed, a physical spring "
            "is often too \"mushy.\"", "key"))

        m = Card("1 · the motor: Revo1, high-torque direct drive")
        m.add(body(
            "At the heart of every Neo joint is the <b>Revo1</b> motor. Most "
            "humanoid motors are off-the-shelf; 1X built their own to get the "
            "world's highest torque-to-weight ratio.<br><br>"
            "<b>Relationship to DD:</b> the motor itself is a <b>direct drive</b> "
            "motor, designed to produce massive torque at low speed so it does "
            "<i>not</i> need a heavy 100:1 harmonic drive that would ruin "
            "backdriveability."))
        self.add(m)

        t = Card("2 · the transmission: a tendon drive")
        t.add(body(
            "Instead of gears or belts, 1X uses a patented <b>tendon drive</b>: "
            "high-strength ropes wrap around the motor and the joint.<br><br>"
            "<b>Like an SEA:</b> the ropes have a tiny bit of inherent \"give.\" "
            "They aren't bouncy springs, but they act as a <b>high-frequency "
            "shock absorber</b>, protecting the motor magnets from impact.<br>"
            "<b>Like a QDD:</b> the effective gear ratio is very low, making the "
            "system <b>95% backdriveable</b>. Push Neo's arm and you aren't "
            "fighting a gearbox — you are spinning the motor rotor directly "
            "through the ropes."))
        t.add(body(
            "<b>Proximal actuator placement.</b> The motor doesn't have to sit at "
            "the joint centre; the rope routes force to the joint pulley. Heavy "
            "components move closer to the trunk and away from distal links "
            "(hands, forearms, feet). Biomechanically this gives lower distal "
            "inertia → safer impacts, faster swing motions, lower energy cost, "
            "and more human-like mass distribution — directly inspired by "
            "musculoskeletal anatomy.", dim=True))
        self.add(t)

        mc = Card("3 · micro-compliance — precisely what it is and is not")
        mc.add(body(
            "&nbsp;&nbsp;• This is <b>not</b> a series elastic actuator.<br>"
            "&nbsp;&nbsp;• There is <b>no intentional spring</b>.<br>"
            "&nbsp;&nbsp;• The compliance is <b>small, passive, and "
            "high-frequency</b>."))
        mc.add(body(
            "It comes from rope material elasticity and acts as a mechanical "
            "low-pass filter at very high frequencies only.<br><br>"
            "<b>Biological analogy:</b> tendons are very stiff at low frequencies "
            "and slightly compliant at high strain rates. That protects muscles "
            "and joints from impulsive loads. Neo's tendon drive does the same "
            "thing at robotic scale."))
        self.add(mc)

        a = Card("4 · active proprioceptive compliance — the key concept")
        a.add(body(
            "Neo does <b>not rely on hardware springs</b> to be compliant. It "
            "relies on <b>motor transparency + sensing + control</b>."))
        a.add(body(
            "<b>Step 1 — high backdriveability (the mechanical prerequisite).</b> "
            "Low gear ratio, no harmonic drive, rope transmission. External forces "
            "at the joint propagate back to the motor and cause measurable motor "
            "torque. <i>Without backdriveability, nothing below works.</i><br><br>"
            "<b>Step 2 — torque sensing via motor current.</b> τ ∝ I, and because "
            "the transmission is transparent, joint torque ≈ motor torque. The "
            "motor current becomes a <b>virtual force sensor</b>.<br><br>"
            "<b>Step 3 — software impedance.</b> Stiffness, damping and torque "
            "limits are modulated in real time, in milliseconds."))
        a.add(body(
            "<b>Passive safety on top:</b> Neo's \"muscles\" are encased in a 3D "
            "lattice polymer soft body. If it hits you, the outer shell deforms. "
            "That is a parallel-elastic effect — but for the <b>skin, not the "
            "joint</b>.", dim=True))
        self.add(a)

        cmp = Card("Neo vs SEA, in the terms of this tutorial")
        tbl = QTableWidget(3, 3)
        tbl.setHorizontalHeaderLabels(["", "SEA", "Neo's approach"])
        for r, cells in enumerate([
            ("Where compliance lives",
             "Fixed by the physical spring",
             "Context-dependent, set in software"),
            ("Safety", "Good — passive, needs no power",
             "Good, and with no lag from a series spring"),
            ("Bandwidth / precision",
             "Bad — limited by the spring-mass resonance",
             "Fast reactions: catching, balancing, manipulation"),
        ]):
            for c, v in enumerate(cells):
                it = QTableWidgetItem(v)
                it.setFlags(Qt.ItemIsEnabled)
                tbl.setItem(r, c, it)
        tbl.verticalHeader().setVisible(False)
        tbl.setWordWrap(True)
        tbl.resizeRowsToContents()
        tbl.setColumnWidth(0, 190)
        tbl.setColumnWidth(1, 290)
        tbl.setColumnWidth(2, 290)
        tbl.setMinimumHeight(200)
        cmp.add(tbl)
        self.add(cmp)

        self.add(callout(
            "<b>One clean sentence.</b> \"Neo achieves compliance through "
            "mechanical transparency and high-bandwidth proprioceptive torque "
            "control rather than physical springs, allowing it to be soft when "
            "needed and stiff when required, similar to biological reflex "
            "modulation.\"<br><br>"
            "<b>Ultra-short summary:</b><br>"
            "&nbsp;&nbsp;<b>Proximal</b> → closer to the torso, reducing distal "
            "inertia<br>"
            "&nbsp;&nbsp;<b>Micro-compliance</b> → tiny rope elasticity filters "
            "high-frequency shocks<br>"
            "&nbsp;&nbsp;<b>Active compliance</b> → backdriveable motor + current "
            "sensing + software impedance", "good"))

        self.finish()
