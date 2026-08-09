"""
The orientation page: what the whole linear-systems block is FOR.

This page exists because "is it first order or second order?" is a useless
question until you know what the answer is going to be used for. It comes
before the first-order pages and answers, in order:

  * what a control problem actually is, in four steps
  * why "order" is the first thing anyone asks about a plant
  * the standard vocabulary -- state, state variable, energy-storage element
    -- and which physical parts contribute one and which contribute none
  * the confusion that trips everybody: the plant does not change when you
    change what you measure, but the transfer function does, and why that is
    not a contradiction

Nothing here is derived. It is the map you look at before walking into the
territory, and every claim on it is discharged somewhere in pages 3-8.
"""

from __future__ import annotations

import math

import numpy as np

from PySide6.QtWidgets import QComboBox, QLabel

from ctrlcore.linear import (
    TF,
    is_observable,
    step_metrics,
    step_response,
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
from .motors import slider, slider_row
from .firstorder import _btn_row, _readout, _splane

SECTION = "Systems & Stability"


# --------------------------------------------------------------------------
# the element inventory used by the order counter
# --------------------------------------------------------------------------
#   name, [(element, kind, stores-what)], transfer function, output label
_BUILDS = [
    dict(
        name="1 · rotor spinning in free space   (torque → SPEED)",
        parts=[("rotor inertia J", "STORE", "kinetic energy — the state is "
                                            "<b>speed ω</b>")],
        tf=lambda: TF([1 / 0.25], [1.0, 0.0]),
        out="speed", dur=2.0,
        note="One storage element, no dissipation at all. Order 1 — and the "
             "single pole sits at the origin, so it never settles: a constant "
             "torque just keeps accelerating it. This is the integrator from "
             "page 5.",
    ),
    dict(
        name="2 · rotor + bearing friction   (torque → SPEED)",
        parts=[("rotor inertia J", "STORE", "kinetic energy — the state is "
                                            "<b>speed ω</b>"),
               ("bearing friction b", "DISSIPATE", "turns energy into heat and "
                                                   "loses it — <b>no state</b>")],
        tf=lambda: TF([1 / 0.25], [1.0, 0.4 / 0.25]),
        out="speed", dur=2.0,
        note="Adding the damper did <b>not</b> change the order. It moved the "
             "pole off the origin, so now the thing settles — but it is still "
             "order 1, because a damper stores nothing.",
    ),
    dict(
        name="3 · rotor + friction + a second damper   (torque → SPEED)",
        parts=[("rotor inertia J", "STORE", "kinetic energy — the state is "
                                            "<b>speed ω</b>"),
               ("bearing friction b₁", "DISSIPATE", "no state"),
               ("windage / seal drag b₂", "DISSIPATE", "no state")],
        tf=lambda: TF([1 / 0.25], [1.0, 0.9 / 0.25]),
        out="speed", dur=2.0,
        note="<b>Two dampers, still order 1.</b> This is the case worth "
             "staring at: you can bolt on as many dissipative elements as you "
             "like and the order never moves. All they do is push the existing "
             "pole further left. Order counts storage, and only storage.",
    ),
    dict(
        name="4 · mass + spring + damper   (force → POSITION)",
        parts=[("mass m", "STORE", "kinetic energy — the state is "
                                   "<b>velocity v</b>"),
               ("spring k", "STORE", "potential energy — the state is "
                                     "<b>deflection x</b>"),
               ("damper c", "DISSIPATE", "no state")],
        tf=lambda: TF([100.0], [1.0, 5.0, 100.0]),
        out="position", dur=2.0,
        note="Now a second <i>storage</i> element. Order 2, and for the first "
             "time the response can overshoot — because energy can sit in the "
             "mass while the spring is already where it wants to be.",
    ),
    dict(
        name="5 · series-elastic actuator: motor + spring + load   (τ → LOAD SPEED)",
        parts=[("motor inertia Jₘ", "STORE", "the state is motor speed"),
               ("series spring k", "STORE", "the state is spring deflection"),
               ("load inertia J_L", "STORE", "the state is load speed"),
               ("load damping b", "DISSIPATE", "no state")],
        tf=lambda: TF([400.0], [0.02 * 0.25, 0.4 * 0.02,
                                400.0 * (0.25 + 0.02), 0.4 * 400.0]),
        out="load speed", dur=2.0,
        note="<b>Three storage elements, order 3.</b> This is the answer to "
             "\"what does a third-order system look like?\" — not two dampers "
             "and two springs, but <i>three places to keep energy</i>. Note "
             "how it rings: with three stores there are more ways for energy "
             "to slosh, and the response gets harder to predict by eye.",
    ),
    dict(
        name="6 · SEA driving a flexible link   (τ → TIP SPEED)",
        parts=[("motor inertia Jₘ", "STORE", "motor speed"),
               ("series spring k₁", "STORE", "spring deflection"),
               ("link inertia J_L", "STORE", "link speed"),
               ("link flexibility k₂", "STORE", "link twist"),
               ("damping b", "DISSIPATE", "no state")],
        tf=lambda: TF([1.0], [1.0, 0.6, 22.0, 8.0, 60.0]),
        out="tip speed", dur=4.0,
        note="Four storage elements, order 4 — two pairs of poles, two "
             "resonances, and a response no one can tune by feel. This is why "
             "mechanical designers are asked to make things stiff: every "
             "flexibility you add is another state that the controller now has "
             "to cope with.",
    ),
]


class ControlProblemPage(Page):
    TITLE = "The Control Problem"
    SUBTITLE = ("Before any of the machinery: what we are trying to do, why "
                "\"what order is it?\" is the first question anyone asks, and "
                "the standard words for all of it.")
    SECTION = SECTION
    NOTES = "orientation"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>You already worked out the shape of this yourself, and you were "
            "right.</b> A plant has some behaviour of its own. You want "
            "different behaviour. So you characterise what it does, decide what "
            "you want instead, and add a controller that closes the gap. "
            "Everything in the next six pages is <i>characterising</i>, and "
            "everything in the six after that is <i>closing the gap</i>. This "
            "page is the map.", "key"))

        # ---- the four steps -------------------------------------------------
        f = Card("every control problem, in four steps — and where each one "
                 "lives in this tutor")
        f.add(body(
            "<table cellpadding='8'>"
            "<tr><td width='26'><b>1</b></td>"
            "<td><b>What does the thing do on its own?</b><br>"
            "Push it and watch. This is the <b>plant</b>, and its unforced "
            "behaviour is the <b>open-loop response</b>. Characterising it means "
            "answering: how fast, how far, does it overshoot, can it be "
            "destabilised. <i>Pages 3–8 are entirely this.</i></td></tr>"

            "<tr><td><b>2</b></td>"
            "<td><b>What do you want instead?</b><br>"
            "Written as <b>specifications</b>: settle within 200 ms, no more "
            "than 5% overshoot, zero steady-state error against gravity, "
            "recover from a kick in half a second, and stay that way when the "
            "payload doubles. Notice these are all statements about the "
            "<i>transient</i> and the <i>steady state</i> — the two things the "
            "next pages teach you to read.</td></tr>"

            "<tr><td><b>3</b></td>"
            "<td><b>How far apart are those two?</b><br>"
            "This is where order matters. Some gaps close with a single gain "
            "knob. Some cannot be closed by any gain and need a different kind "
            "of controller. Some cannot be closed at all without changing the "
            "mechanics — and knowing which case you are in, <i>before</i> you "
            "start tuning, is most of the skill.</td></tr>"

            "<tr><td><b>4</b></td>"
            "<td><b>Add a controller and close the loop.</b><br>"
            "P, PD, PI, PID, lead, lag, state feedback. <i>Pages 11–14.</i> "
            "And the sentence that makes it all one subject: <b>a controller "
            "does not change the plant. It moves the plant's poles.</b> The "
            "metal is unchanged; feedback rearranges where the roots of the "
            "closed-loop equation sit.</td></tr>"
            "</table>"))
        self.add(f)

        # ---- interactive: what a controller does ---------------------------
        self.add(hline())
        self.add(title("Interactive — the same joint, with and without a "
                       "controller"))

        c1 = Card("watch the poles move, and nothing else change")
        c1.add(body(
            "One rigid joint: inertia J, bearing friction b, torque in, "
            "<b>position</b> out. The mechanism is identical in every case — "
            "the only thing you are changing is what software sits in front of "
            "it.<br><br>"
            "Step through the controllers in order. <b>No controller</b>: a "
            "constant torque makes the angle run away, because nothing is "
            "comparing it to a target. <b>P</b>: it now aims at the target, but "
            "it rings, and against a load it settles short. <b>PD</b>: the "
            "ringing is damped out. <b>PI</b>: the steady-state error is "
            "removed. <b>PID</b>: both. Every one of those changes is visible "
            "as poles moving in the right-hand panel, and <i>nothing else in "
            "the plot is a different plant</i>.", dim=True))
        self.ctrl_box = QComboBox()
        for n in ("no controller (open loop)", "P", "PD", "PI", "PID"):
            self.ctrl_box.addItem(n)
        self.ctrl_box.setCurrentIndex(1)
        c1.add_layout(_btn_row(self.ctrl_box))
        self.s_cp = slider(1, 400, 90)      # x0.1
        self.s_cd = slider(0, 300, 60)      # x0.1
        self.s_ci = slider(0, 400, 20)      # x0.1
        self.l_cp, self.l_cd, self.l_ci = QLabel(), QLabel(), QLabel()
        c1.add_layout(slider_row("K_p (×0.1)", self.s_cp, self.l_cp))
        c1.add_layout(slider_row("K_d (×0.1)", self.s_cd, self.l_cd))
        c1.add_layout(slider_row("K_i (×0.1)", self.s_ci, self.l_ci))
        self.st_cover = Stat("overshoot", "--", theme.WARN)
        self.st_cset = Stat("settling time", "--", theme.GOOD)
        self.st_csse = Stat("error vs load", "--", theme.BAD)
        self.st_cord = Stat("closed-loop order", "--", theme.VIOLET)
        self.st_cstab = Stat("stable?", "--", theme.ACCENT)
        c1.add_layout(stat_row(self.st_cover, self.st_cset, self.st_csse,
                               self.st_cord, self.st_cstab))
        self.c_ctrl = MplCanvas(width=7.4, height=3.0, ncols=2)
        c1.add(self.c_ctrl)
        self.ctrl_text = _readout()
        c1.add(self.ctrl_text)
        self.add(c1)
        self.ctrl_box.currentIndexChanged.connect(self._redraw_ctrl)
        for s in (self.s_cp, self.s_cd, self.s_ci):
            s.valueChanged.connect(self._redraw_ctrl)
        self._redraw_ctrl()

        # ---- why order is the first question --------------------------------
        o = Card("so why is \"what order is it?\" the first thing anyone asks")
        o.add(body(
            "Because the answer decides what kind of problem you are in, before "
            "you touch a single gain:"))
        o.add(body(
            "&nbsp;&nbsp;• <b>Whether turning the gain up can ever hurt you.</b> "
            "A first-order plant under proportional feedback is stable at any "
            "gain — that is a theorem. A second-order one is not. So \"first "
            "order\" means <i>tune until fast enough and stop</i>, and \"second "
            "order or more\" means <i>there is a limit and you must find "
            "it</i>.<br>"
            "&nbsp;&nbsp;• <b>Whether it can overshoot at all.</b> One storage "
            "element cannot. If yours does, your model is wrong and the "
            "overshoot is telling you where.<br>"
            "&nbsp;&nbsp;• <b>How fast a loop around it is worth running.</b> "
            "The slowest pole sets the ceiling. Everything faster than that is "
            "wasted computation and amplified noise.<br>"
            "&nbsp;&nbsp;• <b>How many numbers your model, observer or "
            "estimator needs.</b> Order = number of state variables = size of "
            "the vector you must carry.<br>"
            "&nbsp;&nbsp;• <b>How much phase lag the plant will contribute</b>, "
            "which is what decides how much feedback you can apply before the "
            "loop turns on you. Roughly 90° per storage element."))
        o.add(callout(
            "<b>The short version: order tells you how much trouble the plant "
            "is capable of causing.</b> One store, no trouble. Two, it can "
            "overshoot and can be destabilised. Three or more, you stop tuning "
            "by feel and start designing.", "key"))
        self.add(o)

        # ---- vocabulary -----------------------------------------------------
        self.add(hline())
        self.add(title("The standard vocabulary — including the words I should "
                       "have been using"))

        v = Card("state, state variable, energy-storage element, order")
        v.add(callout(
            "<b>I have been saying \"store\". The textbook word is "
            "<i>state variable</i>, and the physical part that creates one is an "
            "<i>energy-storage element</i>.</b> Use those; they are what "
            "everyone else says.", "warn"))
        v.add(body(
            "<table cellpadding='7'>"
            "<tr><td><b>Term</b></td><td><b>What it means</b></td></tr>"

            "<tr><td><b>plant</b></td>"
            "<td>The physical thing you are trying to control, plus its "
            "actuator and sensor. The joint, the motor, the arm.</td></tr>"

            "<tr><td><b>state</b></td>"
            "<td>The <b>smallest set of numbers that, together with all future "
            "inputs, determines all future behaviour.</b> That is the actual "
            "definition, and it is worth reading twice. \"If you told me these "
            "numbers right now and then told me what torque I will apply from "
            "here on, I could predict everything.\"</td></tr>"

            "<tr><td><b>state variable</b></td>"
            "<td>One of those numbers. For a spinning rotor, ω. For a coil, i. "
            "For a spring, its deflection.</td></tr>"

            "<tr><td><b>energy-storage element</b></td>"
            "<td>The physical part that makes a state variable necessary: a "
            "mass, a spring, an inductor, a capacitor, a thermal mass. Each one "
            "holds energy, and the amount it holds cannot change "
            "instantly.</td></tr>"

            "<tr><td><b>order</b></td>"
            "<td><b>The number of state variables = the number of independent "
            "energy-storage elements.</b> Equivalently: the highest derivative "
            "in the differential equation, or the degree of the denominator of "
            "the transfer function. These are the same number.</td></tr>"

            "<tr><td><b>pole</b></td>"
            "<td>A root of that denominator. One per order. Each one describes "
            "one <b>mode</b> — one way the system's transient can "
            "behave.</td></tr>"
            "</table>"))
        v.add(callout(
            "<b>Why \"cannot change instantly\" and \"stores energy\" are the "
            "same test.</b> To change the energy in a component you have to "
            "move power through it, and power is finite — so the energy, and "
            "therefore the variable that carries it, has to move smoothly. That "
            "is why the test \"can this quantity jump?\" and the test \"does "
            "this part store energy?\" always give the same answer. Use "
            "whichever is easier to see on the hardware in front of you.",
            "key"))
        self.add(v)

        el = Card("which parts add a state, and which add none — the table to "
                  "memorise")
        el.add(body(
            "<table cellpadding='7'>"
            "<tr><td><b>Part</b></td><td><b>Stores?</b></td>"
            "<td><b>State variable it creates</b></td>"
            "<td><b>Adds to the order?</b></td></tr>"

            "<tr><td>mass / inertia</td><td>yes — kinetic, ½mv²</td>"
            "<td>velocity (or speed ω)</td><td><b>+1</b></td></tr>"
            "<tr><td>spring / stiffness</td><td>yes — potential, ½kx²</td>"
            "<td>deflection (or position)</td><td><b>+1</b></td></tr>"
            "<tr><td>inductor / winding</td><td>yes — magnetic, ½Li²</td>"
            "<td>current</td><td><b>+1</b></td></tr>"
            "<tr><td>capacitor</td><td>yes — electric, ½Cv²</td>"
            "<td>voltage</td><td><b>+1</b></td></tr>"
            "<tr><td>thermal mass</td><td>yes — heat, CT</td>"
            "<td>temperature</td><td><b>+1</b></td></tr>"

            "<tr><td colspan='4'>&nbsp;</td></tr>"

            "<tr><td>damper / viscous friction</td>"
            "<td><b>no</b> — converts to heat and loses it</td>"
            "<td>none</td><td><b>0</b></td></tr>"
            "<tr><td>resistor</td><td><b>no</b></td><td>none</td>"
            "<td><b>0</b></td></tr>"
            "<tr><td>thermal conduction</td><td><b>no</b></td><td>none</td>"
            "<td><b>0</b></td></tr>"
            "<tr><td>a plain gain / lever / gear</td><td><b>no</b></td>"
            "<td>none</td><td><b>0</b></td></tr>"
            "</table>"))
        el.add(callout(
            "<b>This answers both of your questions at once.</b><br><br>"
            "<b>\"If the damper dissipates, what does stiffness do?\"</b> — It "
            "<i>stores</i>. A spring is an energy-storage element exactly like a "
            "mass, just holding a different kind of energy. That is why a "
            "mass–spring–damper is second order: <b>two storers, one "
            "dissipator</b>.<br><br>"
            "<b>\"Is a third-order system two storages and two dampings?\"</b> — "
            "No. <b>Third order means three storage elements.</b> Dampers never "
            "count, no matter how many there are. A motor inertia, a series "
            "spring and a load inertia is third order whether it has one damper "
            "or six. The interactive below is built to make that impossible to "
            "misremember.", "key"))
        el.add(body(
            "<b>The one caveat, so it does not bite you later:</b> the elements "
            "have to be <b>independent</b>. Two springs bolted rigidly in "
            "parallel are one spring and one state, not two — because their "
            "deflections are not free to differ. Only count storage elements "
            "whose stored quantity can vary on its own.", dim=True))
        self.add(el)

        # ---- interactive: count the order -----------------------------------
        b = Card("interactive — add parts and watch the order (not) change")
        b.add(body(
            "Six machines, built up one element at a time. The inventory panel "
            "lists every part and marks it <span style='color:%s'><b>STORE</b>"
            "</span> or <span style='color:%s'><b>DISSIPATE</b></span>. Compare "
            "entries <b>2 and 3</b> — a whole extra damper, and the order does "
            "not move. Then compare <b>3 and 4</b> — one spring, and it jumps."
            % (theme.ACCENT, theme.TEXT_FAINT), dim=True))
        self.build_box = QComboBox()
        for bd in _BUILDS:
            self.build_box.addItem(bd["name"])
        b.add_layout(_btn_row(self.build_box))
        self.build_text = _readout()
        b.add(self.build_text)
        self.st_bstore = Stat("storage elements", "--", theme.ACCENT)
        self.st_bdiss = Stat("dissipators", "--", theme.TEXT_DIM)
        self.st_border = Stat("order", "--", theme.VIOLET)
        self.st_bstates = Stat("state variables", "--", theme.GOOD)
        self.st_bpoles = Stat("poles", "--", theme.WARN)
        b.add_layout(stat_row(self.st_bstore, self.st_bdiss, self.st_border,
                              self.st_bstates, self.st_bpoles))
        self.c_build = MplCanvas(width=7.4, height=3.0, ncols=2)
        b.add(self.c_build)
        self.add(b)
        self.build_box.currentIndexChanged.connect(self._redraw_build)
        self._redraw_build()

        # ---- the plant is the plant -----------------------------------------
        self.add(hline())
        self.add(title("\"The plant is the plant\" — the thing that has been "
                       "bothering you, answered"))

        pp = Card("you are right, and the resolution is a real and standard "
                  "idea")
        pp.add(body(
            "Your objection: a car's suspension is a car's suspension. It has "
            "the springs it has and the dampers it has. How can the same lump "
            "of metal be first order when I watch one thing and second order "
            "when I watch another?<br><br>"
            "<b>The physics does not change. The plant really is the plant.</b> "
            "What changes is which part of it your chosen output can see. Take "
            "the rotor: inertia J, friction b, torque in."))
        pp.add(math_label(r"\dot\theta = \omega, \qquad "
                          r"J\,\dot\omega = \tau - b\,\omega", 17))
        pp.add(body(
            "<b>That is the plant, and it has two state variables — θ and ω — "
            "always.</b> Two numbers you would need to be told before you could "
            "predict its future. Nothing you measure changes that. The rotor "
            "really is accumulating angle whether or not anyone is looking at "
            "it."))
        pp.add(callout(
            "<b>Now look at the first equation. θ appears on the left, but it "
            "appears nowhere on the right of either equation.</b><br><br>"
            "The angle is <i>fed by</i> the speed and <i>affects nothing</i>. "
            "It is a dead end — a state that the rest of the system does not "
            "care about. So if your output is <b>speed</b>, the θ state has no "
            "influence on anything you can measure, and the input–output "
            "behaviour you can see is governed by one equation, not two. "
            "<b>First order.</b><br><br>"
            "If your output is <b>position</b>, that dead end is now exactly "
            "the thing you are watching, and both equations matter. "
            "<b>Second order.</b>", "key"))
        pp.add(body(
            "<b>The standard name for this is observability, and it is a whole "
            "page later on (page 15).</b> A state that produces no signature at "
            "your sensor is called <b>unobservable</b>, and a transfer function "
            "silently drops every unobservable mode — which is why the "
            "<i>transfer-function order</i> can be lower than the number of "
            "state variables. The full model is called a <b>realisation</b>; "
            "the reduced one that keeps only what is both drivable and visible "
            "is the <b>minimal realisation</b>, and that is what a transfer "
            "function always is."))
        pp.add(callout(
            "<b>So the honest statement, which is the one to carry:</b><br>"
            "&nbsp;&nbsp;• <b>The plant</b> has a fixed number of state "
            "variables, set by its energy-storage elements. That is a property "
            "of the hardware and nothing you do changes it.<br>"
            "&nbsp;&nbsp;• <b>A transfer function</b> is not the plant. It is "
            "the answer to one specific question — \"if I push <i>here</i>, "
            "what happens <i>there</i>?\" — and different questions about the "
            "same hardware have different answers, and different orders.<br><br>"
            "When people say \"the joint is first order\" they always mean "
            "\"torque in, speed out is first order\". The sloppiness is in the "
            "sentence, not in the physics.", "good"))
        self.add(pp)

        i3 = Card("interactive — and the part that is not just bookkeeping")
        i3.add(body(
            "A velocity loop is holding the joint at zero speed, and it is "
            "doing it well. At the marked time something knocks the joint — a "
            "foot hits a rock, someone bumps the arm.<br><br>"
            "<b>Left:</b> the speed dips and comes straight back to zero. The "
            "controller did its job perfectly; as far as it is concerned "
            "nothing happened and the error is gone.<br>"
            "<b>Right:</b> the angle. It moved, and it <b>never comes "
            "back</b>. The joint is now somewhere it was not asked to be, "
            "permanently, and no amount of velocity-loop gain will ever fix it "
            "— because the loop cannot see θ. That unobservable state was not a "
            "mathematical technicality; it was a real physical quantity that "
            "quietly changed while a perfectly healthy controller reported no "
            "error.", dim=True))
        self.s_vk = slider(1, 300, 60)      # x0.1 velocity loop gain
        self.s_vd = slider(1, 100, 40)      # x0.01 disturbance size
        self.l_vk, self.l_vd = QLabel(), QLabel()
        i3.add_layout(slider_row("velocity loop K_p (×0.1)", self.s_vk,
                                 self.l_vk))
        i3.add_layout(slider_row("size of the knock", self.s_vd, self.l_vd))
        self.st_vobs = Stat("τ→ω: observable?", "--", theme.GOOD)
        self.st_pobs = Stat("τ→θ: observable?", "--", theme.GOOD)
        self.st_vtf = Stat("τ→ω order", "--", theme.ACCENT)
        self.st_ptf = Stat("τ→θ order", "--", theme.BAD)
        self.st_drift = Stat("permanent angle error", "--", theme.WARN)
        i3.add_layout(stat_row(self.st_vobs, self.st_pobs, self.st_vtf,
                               self.st_ptf, self.st_drift))
        self.c_obs = MplCanvas(width=7.4, height=3.0, ncols=2)
        i3.add(self.c_obs)
        i3.add(body(
            "<b>This is why real machines run a position loop wrapped around a "
            "velocity loop wrapped around a current loop.</b> Each layer watches "
            "a state the layer inside it is blind to. The cascade is not a "
            "convention — it is the direct consequence of the fact that "
            "different outputs see different parts of the same plant.",
            dim=True))
        self.add(i3)
        for s in (self.s_vk, self.s_vd):
            s.valueChanged.connect(self._redraw_obs)
        self._redraw_obs()

        # ---- the words for the response -------------------------------------
        self.add(hline())
        self.add(title("The five words used for what a response does — pinned "
                       "down"))

        w = Card("transient, steady state, decay, settle, die")
        w.add(body(
            "These get used loosely and it makes everything harder than it "
            "needs to be. Every response splits into exactly two parts, and "
            "four of the five words are about the first part."))
        w.add(math_label(r"y(t) \;=\; y_{\text{steady state}} \;+\; "
                         r"y_{\text{transient}}(t)", 17))
        w.add(body(
            "<table cellpadding='7'>"
            "<tr><td><b>steady state</b></td>"
            "<td>Where the output ends up and stays. The part that does "
            "<b>not</b> go away. If you commanded 1.0 and it ends at 0.9, the "
            "steady state is 0.9 and the 0.1 gap is <b>steady-state "
            "error</b>.</td></tr>"

            "<tr><td><b>transient</b></td>"
            "<td>Everything else: the difference between where the output is "
            "right now and where it will end up. <b>This is the part that "
            "decays</b>, and it is the only thing poles describe.</td></tr>"

            "<tr><td><b>decay</b></td>"
            "<td>What the transient does. It shrinks exponentially, at a rate "
            "given by the real part of the pole. Standard, precise, and the "
            "word to use.</td></tr>"

            "<tr><td><b>settle</b></td>"
            "<td>The observable consequence of the transient having decayed far "
            "enough to ignore. \"Settling time\" = when the response enters and "
            "stays inside a ±2% band. <b>Settling and decaying are the same "
            "event</b>: one named from the outside, one from the "
            "inside.</td></tr>"

            "<tr><td><b>die</b></td>"
            "<td>Informal, and the source of your confusion. When someone says "
            "\"the response dies\" they mean <b>the transient</b> dies. The "
            "output does not go to zero — it goes to the steady state and "
            "stays there. <b>What dies is the error, not the "
            "motion.</b></td></tr>"
            "</table>"))
        w.add(callout(
            "<b>So \"we want it to settle, not to die\" was never a real "
            "conflict.</b> You want the joint to hold 30° — that is the steady "
            "state, and it persists. You want the wobbling and the leftover "
            "swing on the way there to vanish quickly — that is the transient, "
            "and it is what decays. Fast decay <i>is</i> fast settling. The "
            "output survives; the discrepancy is what dies.", "key"))
        self.add(w)

        # ---- roadmap ---------------------------------------------------------
        rm = Card("what the next six pages do, and why in that order")
        rm.add(body(
            "<table cellpadding='7'>"
            "<tr><td width='34'><b>3</b></td><td><b>What a first-order system "
            "is.</b> One storage element. How you identify order on real "
            "hardware, and what the answer buys you.</td></tr>"
            "<tr><td><b>4</b></td><td><b>The time constant and the pole.</b> "
            "How fast, expressed three equivalent ways. Where 0.63 comes from. "
            "Why the current loop runs at 20 kHz.</td></tr>"
            "<tr><td><b>5</b></td><td><b>The pole at the origin.</b> A storage "
            "element with no dissipation. Why position is second order, and why "
            "the I term works.</td></tr>"
            "<tr><td><b>6</b></td><td><b>First order in frequency.</b> Shake it "
            "with a sine instead of stepping it. Bandwidth, dB, phase lag — the "
            "language every datasheet and every loop-shaping argument "
            "uses.</td></tr>"
            "<tr><td><b>7</b></td><td><b>The s-plane.</b> The two axes, what "
            "the imaginary part physically is, and the second storage element "
            "that creates it.</td></tr>"
            "<tr><td><b>8</b></td><td><b>Second-order systems.</b> ω<sub>n</sub> "
            "and ζ — and the fact that the K and B of an impedance controller "
            "<i>are</i> ω<sub>n</sub> and ζ. This is where every robot joint you "
            "will tune actually lives.</td></tr>"
            "</table>"))
        rm.add(callout(
            "<b>Read them as one argument, not six topics.</b> Count the "
            "storage elements → that gives the order → the order gives the "
            "number of poles → each pole's position gives one rate → those "
            "rates are the whole behaviour → and a controller is a device for "
            "moving them. Every page is one link in that chain.", "good"))
        self.add(rm)

        self.finish()

    # ------------------------------------------------------------------
    def _plant(self):
        J, b = 0.25, 0.4
        return TF([1.0], [J, b, 0.0])          # torque -> position

    def _redraw_ctrl(self):
        kp = self.s_cp.value() / 10.0
        kd = self.s_cd.value() / 10.0
        ki = self.s_ci.value() / 10.0
        self.l_cp.setText(f"{kp:.1f}")
        self.l_cd.setText(f"{kd:.1f}")
        self.l_ci.setText(f"{ki:.1f}")
        mode = self.ctrl_box.currentIndex()

        g = self._plant()
        if mode == 0:
            sys_ = g                                  # open loop, no feedback
            note = ("<b>No controller.</b> A constant torque and nothing "
                    "watching the angle: it accelerates until friction balances "
                    "the torque, and then keeps turning at that speed forever. "
                    "The output runs away. This is what \"open loop\" means, and "
                    "it is why the pole at the origin matters.")
        else:
            # built directly rather than via pid_tf() so that no uncancelled
            # s appears in both numerator and denominator -- TF does no
            # pole-zero cancellation, and a spurious root at the origin would
            # make the order and the stability verdict both wrong
            td = 0.02
            ctrl = {1: TF([kp], [1.0]),
                    2: TF([kd + kp * td, kp], [td, 1.0]),
                    3: TF([kp, ki], [1.0, 0.0]),
                    4: TF([kd + kp * td, kp + ki * td, ki],
                          [td, 1.0, 0.0])}[mode]
            sys_ = (ctrl * g).feedback()
            note = {
                1: ("<b>P.</b> Now it aims. The controller supplies a restoring "
                    "torque proportional to the error, so it behaves like a "
                    "spring — which means there are now two storage elements in "
                    "the loop, and it can <b>ring</b>. Against a constant load "
                    "it settles short, because zero error would mean zero "
                    "torque."),
                2: ("<b>PD.</b> The D term reacts to how fast the error is "
                    "changing, which acts like a damper. The poles are dragged "
                    "away from the imaginary axis and the ringing goes. It "
                    "still settles short against a load."),
                3: ("<b>PI.</b> The I term adds a state that never decays, so "
                    "the command can hold a bias with zero error — the load "
                    "error disappears. But it added a pole, so the loop is "
                    "higher order and can be pushed unstable."),
                4: ("<b>PID.</b> D damps the ringing, I removes the load error. "
                    "Three knobs, three pole positions you are bargaining over. "
                    "Everything from here on is about doing that bargaining "
                    "deliberately instead of by trial and error."),
            }[mode]

        poles = sys_.poles()
        stable = all(p.real < -1e-9 for p in poles)
        dur = 4.0
        t, y = step_response(sys_, dur, dur / 900.0)
        self.st_cord.set(str(sys_.order()))
        self.st_cstab.set("yes" if stable else "NO")
        self.st_cstab.set_color(theme.GOOD if stable else theme.BAD)

        if mode == 0 or not stable:
            self.st_cover.set("—")
            self.st_cset.set("never")
            self.st_cset.set_color(theme.BAD)
            self.st_csse.set("—")
        else:
            m = step_metrics(t, y, 1.0)
            self.st_cover.set(f"{m.overshoot*100:.0f}%")
            self.st_cover.set_color(theme.GOOD if m.overshoot < 0.05
                                    else theme.WARN)
            self.st_cset.set("—" if math.isinf(m.settling_time)
                             else f"{m.settling_time:.2f} s")
            self.st_cset.set_color(theme.GOOD)
            # steady-state error against a constant load torque
            has_i = mode in (3, 4)
            self.st_csse.set("zero" if has_i else "leaves one")
            self.st_csse.set_color(theme.GOOD if has_i else theme.BAD)

        self.ctrl_text.setText(
            note + "<br><b>The plant never changed.</b> J and b are the same in "
            "every one of these — only the pole positions moved.")

        c = self.c_ctrl
        c.clear()
        a1, a2 = c.axes
        a1.plot(t, y, color=theme.ACCENT, lw=2.3)
        a1.axhline(1.0, color=theme.TEXT_FAINT, lw=1.0, ls="--",
                   label="commanded")
        top = 2.2 if mode == 0 or not stable else max(1.6, max(y) * 1.15)
        a1.set_ylim(-0.15, top)
        a1.set_xlabel("time (s)")
        a1.set_ylabel("joint angle")
        a1.set_title("closed-loop step response", fontsize=9)
        c.legend(a1, loc="lower right")

        lim = max(2.0, max(abs(p) for p in poles) * 1.35)
        _splane(a2, poles, lim=lim)
        a2.set_title("where the poles ended up", fontsize=9)
        c.refresh()

    # ------------------------------------------------------------------
    def _redraw_build(self):
        bd = _BUILDS[self.build_box.currentIndex()]
        g = bd["tf"]()
        stores = sum(1 for _, kind, _ in bd["parts"] if kind == "STORE")
        diss = sum(1 for _, kind, _ in bd["parts"] if kind == "DISSIPATE")

        rows = []
        for name, kind, what in bd["parts"]:
            col = theme.ACCENT if kind == "STORE" else theme.TEXT_FAINT
            rows.append(f"&nbsp;&nbsp;<span style='color:{col}'><b>{kind}</b>"
                        f"</span> &nbsp; <b>{name}</b> — {what}")
        rows.append("<br>" + bd["note"])
        self.build_text.setText("<br>".join(rows))

        self.st_bstore.set(str(stores))
        self.st_bdiss.set(str(diss))
        self.st_border.set(str(g.order()))
        self.st_bstates.set(str(stores))
        self.st_bpoles.set(str(len(g.poles())))
        self.st_border.set_color(theme.VIOLET if g.order() == stores
                                 else theme.BAD)

        c = self.c_build
        c.clear()
        a1, a2 = c.axes
        t, y = step_response(g, bd["dur"], bd["dur"] / 900.0)
        sc = max(abs(v) for v in y) or 1.0
        a1.plot(t, [v / sc for v in y], color=theme.ACCENT, lw=2.2)
        a1.set_xlabel("time (s)")
        a1.set_ylabel(f"{bd['out']} (normalised)")
        a1.set_title("step response", fontsize=9)
        poles = g.poles()
        lim = max(2.0, max(abs(p) for p in poles) * 1.35)
        _splane(a2, poles, lim=lim)
        a2.set_title(f"{len(poles)} pole(s) — one per storage element",
                     fontsize=9)
        c.refresh()

    # ------------------------------------------------------------------
    def _redraw_obs(self):
        J, b = 0.25, 0.4
        kv = self.s_vk.value() / 10.0
        dmag = self.s_vd.value() / 100.0
        self.l_vk.setText(f"{kv:.1f}")
        self.l_vd.setText(f"{dmag:.2f}")

        A = np.array([[0.0, 1.0], [0.0, -b / J]])
        C_w = np.array([[0.0, 1.0]])
        C_th = np.array([[1.0, 0.0]])
        obs_w = is_observable(A, C_w)
        obs_th = is_observable(A, C_th)
        self.st_vobs.set("no — 1 of 2" if not obs_w else "yes")
        self.st_vobs.set_color(theme.BAD if not obs_w else theme.GOOD)
        self.st_pobs.set("yes — both" if obs_th else "no")
        self.st_pobs.set_color(theme.GOOD if obs_th else theme.BAD)
        self.st_vtf.set(str(TF([1.0], [J, b]).order()))
        self.st_ptf.set(str(TF([1.0], [J, b, 0.0]).order()))

        # velocity loop holding zero speed, hit by a torque pulse
        dur, dt = 4.0, 0.001
        t_d, t_w = 1.0, 0.25
        n = int(dur / dt)
        th = w = 0.0
        ts, ws, ths = [], [], []
        for k in range(n):
            t = k * dt
            u = kv * (0.0 - w)
            d = dmag if t_d <= t < t_d + t_w else 0.0
            w += dt * (u + d - b * w) / J
            th += dt * w
            ts.append(t)
            ws.append(w)
            ths.append(th)

        self.st_drift.set(f"{math.degrees(ths[-1]):.1f}°")
        self.st_drift.set_color(theme.BAD if abs(ths[-1]) > 1e-3
                                else theme.GOOD)

        c = self.c_obs
        c.clear()
        a1, a2 = c.axes
        a1.plot(ts, ws, color=theme.GOOD, lw=2.2)
        a1.axhline(0.0, color=theme.TEXT_FAINT, lw=1.0, ls="--",
                   label="commanded speed")
        a1.axvspan(t_d, t_d + t_w, color=theme.WARN, alpha=0.15)
        a1.text(t_d, max(ws) * 0.9 if max(ws) > 0 else 0.1, " the knock",
                color=theme.WARN, fontsize=7.5)
        a1.set_xlabel("time (s)")
        a1.set_ylabel("speed ω (rad/s)")
        a1.set_title("the state the loop CAN see — fully recovered",
                     fontsize=9)
        c.legend(a1, loc="upper right")

        a2.plot(ts, [math.degrees(v) for v in ths], color=theme.BAD, lw=2.2)
        a2.axhline(0.0, color=theme.TEXT_FAINT, lw=1.0, ls="--",
                   label="where it started")
        a2.axvspan(t_d, t_d + t_w, color=theme.WARN, alpha=0.15)
        a2.set_xlabel("time (s)")
        a2.set_ylabel("angle θ (deg)")
        a2.set_title("the state it CANNOT — permanently moved", fontsize=9)
        c.legend(a2, loc="lower right")
        c.refresh()
