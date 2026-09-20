"""
First-order systems, taken slowly, across four pages instead of one.

  2  What a First-Order System Is    one store, one drain -- and, concretely,
                                     what knowing that buys you
  3  Time Constant & the Pole        the leaky bucket, e-folding, and why the
                                     current loop runs at 20 kHz
  4  First Order in Frequency        shake it with a sine and watch the corner,
                                     the -3 dB point and the 90 degree ceiling
  5  The s-Plane & Imaginary Numbers what j physically is, and the second
                                     energy store that lifts a pole off the axis

These were one very long page. They were split because every one of these is a
separate idea that people get stuck on separately, and because a page you have
to scroll for two minutes is a page whose interactive controls are never on
screen at the same time as the sentence they illustrate.

The rule followed here: no claim that can be made draggable is left as prose.
"""

from __future__ import annotations

import math

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton

from ctrlcore.linear import (
    TF,
    bode,
    critical_gain,
    first_order,
    log_freqs,
    margins,
    margins_with_delay,
    simulate_ss,
    step_response,
    tf_to_ss,
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

SECTION = "Systems & Stability"


# ==========================================================================
# shared helpers
# ==========================================================================

def _splane(ax, poles, zeros=(), lim=None, marker_label="poles"):
    """
    Pole-zero map. The left half plane is shaded because that shading IS the
    stability condition -- there is no other content in the picture.
    """
    xs = [p.real for p in poles] + [z.real for z in zeros]
    ys = [p.imag for p in poles] + [z.imag for z in zeros]
    span = lim or max(1.0, max([abs(v) for v in xs + ys] or [1.0]) * 1.35)
    ax.axvspan(-span, 0, color=theme.GOOD, alpha=0.06)
    ax.axvspan(0, span, color=theme.BAD, alpha=0.07)
    ax.axhline(0, color=theme.BORDER, lw=1.0)
    ax.axvline(0, color=theme.TEXT_FAINT, lw=1.4, ls="--")
    if poles:
        ax.scatter([p.real for p in poles], [p.imag for p in poles],
                   marker="x", s=90, linewidths=2.2, color=theme.ACCENT,
                   zorder=5, label=marker_label)
    if zeros:
        ax.scatter([z.real for z in zeros], [z.imag for z in zeros],
                   marker="o", s=70, facecolors="none", linewidths=1.8,
                   edgecolors=theme.WARN, zorder=5, label="zeros")
    ax.set_xlim(-span, span)
    ax.set_ylim(-span, span)
    ax.set_xlabel("real  (1/s)   ←  decay rate")
    ax.set_ylabel("imag  (rad/s)   ring")
    ax.text(-span * 0.95, span * 0.86, "STABLE", color=theme.GOOD,
            fontsize=7.5, fontweight="bold")
    ax.text(span * 0.35, span * 0.86, "UNSTABLE", color=theme.BAD,
            fontsize=7.5, fontweight="bold")


def _btn(text, primary=False):
    b = QPushButton(text)
    if primary:
        b.setObjectName("Primary")
    return b


def _btn_row(*buttons):
    lay = QHBoxLayout()
    lay.setSpacing(8)
    for b in buttons:
        lay.addWidget(b)
    lay.addStretch(1)
    return lay


def _readout(text=""):
    lb = QLabel(text)
    lb.setWordWrap(True)
    lb.setTextFormat(Qt.RichText)
    lb.setStyleSheet(f"color:{theme.TEXT}; background:transparent; font-size:13px;")
    return lb


def _lcg(seed: int):
    """Tiny deterministic PRNG -- reproducible 'measurement noise' with no
    dependency on the global random state."""
    state = seed & 0x7FFFFFFF

    def nxt():
        nonlocal state
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        return state / 0x7FFFFFFF - 0.5
    return nxt


# ==========================================================================
# PAGE -- what a first-order system is, and what that buys you
# ==========================================================================

#: name, blurb, stores, drains, tf-builder, ode (html), verdict
_SYSTEMS = [
    dict(
        key="flywheel",
        name="Flywheel + bearing friction   (torque in, SPEED out)",
        blurb="A spinning mass with viscous friction. Push it with a constant "
              "torque and ask what its speed does.",
        stores=[("the spinning mass <b>J</b>",
                 "holds <b>speed ω</b>",
                 "changing ω needs torque, and torque is finite — so ω cannot "
                 "jump")],
        drains=[("bearing friction <b>b</b>", "removes <b>b·ω</b> — bigger the "
                 "faster it spins")],
        ode="J·ω̇ &nbsp;=&nbsp; τ &minus; b·ω",
        tf=lambda: first_order(1.0 / 0.4, 0.25 / 0.4),
        tlim=2.2,
    ),
    dict(
        key="winding",
        name="Motor winding R–L   (voltage in, CURRENT out)",
        blurb="The innermost loop in every servo drive. Apply a voltage, ask "
              "what the current does.",
        stores=[("the coil's inductance <b>L</b>",
                 "holds <b>current i</b>",
                 "changing i needs voltage, and voltage is finite — so i cannot "
                 "jump")],
        drains=[("winding resistance <b>R</b>", "burns <b>R·i</b> — bigger the "
                 "more current flows")],
        ode="L·di/dt &nbsp;=&nbsp; V &minus; R·i",
        tf=lambda: first_order(1.0 / 1.2, 0.0012 / 1.2),
        tlim=0.006,
    ),
    dict(
        key="rc",
        name="RC low-pass filter   (voltage in, voltage out)",
        blurb="The filter on your encoder derivative, or on an analogue force "
              "sensor. Same object in different clothes.",
        stores=[("the capacitor <b>C</b>",
                 "holds <b>voltage v</b>",
                 "changing v needs current, and current is finite — so v cannot "
                 "jump")],
        drains=[("the resistor <b>R</b>", "passes charge away at a rate set by "
                 "the voltage across it")],
        ode="R·C·v̇ &nbsp;+&nbsp; v &nbsp;=&nbsp; v<sub>in</sub>",
        tf=lambda: first_order(1.0, 0.02),
        tlim=0.12,
    ),
    dict(
        key="thermal",
        name="Motor thermal mass   (watts in, TEMPERATURE out)",
        blurb="Why you can overload a motor for two seconds and not for two "
              "minutes. The slowest first-order system on the robot.",
        stores=[("the copper and iron's heat capacity <b>C</b>",
                 "holds <b>temperature T</b>",
                 "heating needs power, and power is finite — so T cannot jump")],
        drains=[("conduction to ambient <b>1/R</b>",
                 "loses heat faster the hotter it already is")],
        ode="C·Ṫ &nbsp;+&nbsp; T/R &nbsp;=&nbsp; P",
        tf=lambda: first_order(1.0, 90.0),
        tlim=420.0,
    ),
    dict(
        key="msd",
        name="Mass + spring + damper   (force in, POSITION out)",
        blurb="Add a spring to the flywheel and count again. This is the "
              "moment the page you are on stops applying.",
        stores=[("the mass <b>m</b>", "holds <b>velocity v</b>",
                 "same reason as the flywheel"),
                ("the spring <b>k</b>", "holds <b>deflection x</b>",
                 "compressing a spring stores energy that is NOT the velocity — "
                 "a second, hidden reservoir")],
        drains=[("the damper <b>c</b>", "removes <b>c·v</b>")],
        ode="m·ẍ &nbsp;+&nbsp; c·ẋ &nbsp;+&nbsp; k·x &nbsp;=&nbsp; F",
        tf=lambda: TF([1.0], [1.0, 2.0, 100.0]),
        tlim=3.0,
    ),
    dict(
        key="poscl",
        name="Rigid joint, torque in, POSITION out",
        blurb="The same joint as the first entry — but you decided to watch "
              "position instead of speed. That decision changed the order.",
        stores=[("the inertia <b>J</b>", "holds <b>speed ω</b>", "as before"),
                ("position itself", "holds <b>angle θ</b>",
                 "θ is the running total of ω and never leaks — a perfect, "
                 "store with no drain at all. This is what an <i>integrator</i> is")],
        drains=[("bearing friction <b>b</b>", "removes <b>b·ω</b> — note it "
                 "drains the speed store, and nothing at all drains θ")],
        ode="J·θ̈ &nbsp;+&nbsp; b·θ̇ &nbsp;=&nbsp; τ",
        tf=lambda: TF([1.0], [0.25, 0.4, 0.0]),
        tlim=2.2,
    ),
    dict(
        key="sea",
        name="Series-elastic actuator   (motor τ in, LOAD SPEED out)",
        blurb="Motor, spring, load. Count the reservoirs before you tune "
              "anything on one of these.",
        stores=[("motor inertia <b>J<sub>m</sub></b>", "holds motor speed", ""),
                ("the series spring <b>k</b>", "holds spring deflection", ""),
                ("load inertia <b>J<sub>l</sub></b>", "holds load speed", "")],
        drains=[("load-side friction <b>b</b>", "removes <b>b·ω<sub>l</sub></b>")],
        ode="J<sub>m</sub>ω̇<sub>m</sub> = τ &minus; τ<sub>s</sub> &nbsp;&nbsp;|"
            "&nbsp;&nbsp; τ̇<sub>s</sub> = k(ω<sub>m</sub>&minus;ω<sub>l</sub>)"
            " &nbsp;&nbsp;|&nbsp;&nbsp; J<sub>l</sub>ω̇<sub>l</sub> = "
            "τ<sub>s</sub> &minus; b·ω<sub>l</sub>",
        tf=lambda: TF([400.0], [0.02 * 0.25, 0.4 * 0.02,
                                400.0 * (0.25 + 0.02), 0.4 * 400.0]),
        tlim=2.0,
    ),
]


class FirstOrderPage(Page):
    TITLE = "What a First-Order System Is"
    SUBTITLE = ("One store, one drain — and, concretely, what knowing that "
                "about the thing in front of you actually buys you.")
    SECTION = SECTION
    NOTES = "foundation"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>Read this page for the answer to one question: <i>so what?</i></b> "
            "Classifying a plant as first order is not trivia and it is not "
            "something to memorise. It is a measurement you make on real "
            "hardware, it costs one experiment, and it tells you four specific "
            "things you would otherwise have to guess. The last card on this "
            "page lists them; everything before it is what you need in order to "
            "believe them.<br><br>"
            "<b>If \"order\" itself still feels arbitrary, page 2 is the one to "
            "read first</b> — it is where the word is defined, where the "
            "storage-versus-dissipation table lives, and where the fact that "
            "one piece of hardware can be first order in speed and second order "
            "in position gets its proper explanation.", "key"))

        # ---- the physical picture, before any algebra ---------------------
        ph = Card("what a first-order system physically IS — no equation needed")
        ph.add(body(
            "<b>The vocabulary, since the previous page insisted on it:</b> what "
            "is called a <i>store</i> below is properly an <b>energy-storage "
            "element</b>, and the quantity it refuses to let jump is a "
            "<b>state variable</b>. <b>Order = number of independent "
            "energy-storage elements = number of state variables.</b> \"Store\" "
            "is kept here only because it is shorter, and because the plumbing "
            "picture on the next page needs it.", dim=True))
        ph.add(body(
            "Forget transfer functions. A system is first order when it has "
            "exactly <b>two</b> physical features:"))
        ph.add(body(
            "&nbsp;&nbsp;<b>1 · One thing that stores.</b> Not \"holds energy\" "
            "— the sharper test is: <b>one quantity that cannot change "
            "instantly.</b> A spinning mass will not let <i>speed</i> jump. A "
            "coil will not let <i>current</i> jump. A hot motor will not let "
            "<i>temperature</i> jump. That refusal is what a store is.<br>"
            "&nbsp;&nbsp;<b>2 · One thing that drains, in proportion to how much "
            "is stored.</b> Friction drags harder the faster you spin. "
            "Resistance burns more the more current flows. A hot object loses "
            "heat faster the hotter it is."))
        ph.add(callout(
            "<b>\"A mass stores speed\" sounds wrong until you read it as \"a "
            "mass refuses to let speed jump\".</b> Nothing is being kept in a "
            "jar. To change ω you need torque; torque is finite; therefore ω "
            "moves smoothly and the past leaks into the present. Every store is "
            "a <i>low-pass on one variable</i> — mass smooths velocity, "
            "inductance smooths current, capacitance smooths voltage, heat "
            "capacity smooths temperature.", "key"))
        ph.add(body(
            "<b>The whole behaviour follows.</b> You pour in at a constant rate. "
            "The level rises. But the fuller it gets, the faster it leaks — so "
            "the rise slows. Eventually the leak exactly matches the pour and "
            "the level stops. That is every first-order response you will ever "
            "see: <b>a constant fill racing a leak that grows with the level, "
            "ending in a draw</b>.", dim=True))
        self.add(ph)

        # ---- interactive: count the stores ------------------------------
        self.add(hline())
        self.add(title("Interactive — how you tell the order of something on "
                       "your bench"))

        ident = Card("count the reservoirs, then check the shape")
        ident.add(body(
            "You do not read the order off a datasheet. You <b>count energy "
            "stores</b> — one per quantity that cannot jump — and then you "
            "confirm it with a step test, because the two answers disagreeing "
            "means you missed a store. Work through the list; the last three "
            "are there to show you what \"missing a store\" looks like.",
            dim=True))
        self.sys_box = QComboBox()
        for s in _SYSTEMS:
            self.sys_box.addItem(s["name"], s["key"])
        ident.add_layout(_btn_row(self.sys_box))
        self.sys_text = _readout()
        ident.add(self.sys_text)
        self.st_stores = Stat("energy stores", "--", theme.ACCENT)
        self.st_order = Stat("order", "--", theme.VIOLET)
        self.st_over = Stat("can overshoot?", "--", theme.WARN)
        self.st_lag = Stat("max phase lag", "--", theme.CYAN)
        ident.add_layout(stat_row(self.st_stores, self.st_order, self.st_over,
                                  self.st_lag))
        self.c_ident = MplCanvas(width=7.4, height=2.8, ncols=2)
        ident.add(self.c_ident)
        ident.add(body(
            "<b>The step-test signature, which is how you check your count "
            "without opening anything up:</b> a curve that leaves the origin "
            "with its steepest slope and only ever flattens has <b>one</b> "
            "store. A curve that starts flat, gathers pace, and then either "
            "overshoots or eases in has <b>two or more</b>. That initial "
            "flatness is the tell — it is the second store having to be filled "
            "before the output can move at all.", dim=True))
        self.add(ident)
        self.sys_box.currentIndexChanged.connect(self._redraw_ident)
        self._redraw_ident()

        # ---- the equation, built from the picture -------------------------
        d = Card("now the equation — it is the picture, written down")
        d.add(body(
            "Newton for the flywheel. Rate of change of the stored quantity = "
            "what you put in, minus what leaks out:"))
        d.add(math_label(r"J\,\dot\omega \;=\; \tau \;-\; b\,\omega", 17))
        d.add(body(
            "&nbsp;&nbsp;<b>J ω̇</b> — the store filling up<br>"
            "&nbsp;&nbsp;<b>τ</b> — the fill rate, constant<br>"
            "&nbsp;&nbsp;<b>b ω</b> — the leak, proportional to <b>ω</b>, the "
            "level itself. That proportionality is the whole mechanism.",
            dim=True))
        d.add(body("Move the leak across and divide by b:"))
        d.add(math_label(r"\frac{J}{b}\,\dot\omega + \omega = \frac{\tau}{b}"
                         r"\qquad\text{i.e.}\qquad "
                         r"\tau_{c}\,\dot y + y = K u", 17))
        d.add(callout(
            "<b>One derivative = one store = first order.</b> Anything you can "
            "write as <i>(something)·ẏ + y = (input)</i> is this system with "
            "different words for the store and the leak. Two derivatives means "
            "two stores, and the next three pages are about what that costs "
            "you.", "key"))
        self.add(d)

        s = Card("the two numbers, and what each physically is")
        s.add(body(
            "<table cellpadding='7'>"
            "<tr><td><b>Symbol</b></td><td><b>Made of</b></td>"
            "<td><b>What it physically is</b></td></tr>"
            "<tr><td><b>K</b><br>DC gain</td><td>1/b — one over the leak</td>"
            "<td><b>How far it eventually gets, per unit of input.</b> A leakier "
            "system settles lower for the same push. Nothing to do with speed — "
            "purely \"where does it end up\".</td></tr>"
            "<tr><td><b>τ<sub>c</sub></b><br>time constant</td>"
            "<td>J/b — store divided by leak</td>"
            "<td><b>How long it takes.</b> A bigger store takes longer to fill; "
            "a bigger leak drains it faster, so it reaches balance sooner. "
            "Seconds. The <i>next page</i> is entirely about this "
            "number.</td></tr>"
            "</table>"))
        s.add(body(
            "<b>K and τ<sub>c</sub> are independent.</b> K says where, τ says "
            "when. You can have a fast joint that barely moves and a sluggish "
            "one that eventually swings a long way — they are different "
            "complaints with different fixes.", dim=True))
        self.add(s)

        # ---- interactive: two numbers are the whole plant ------------------
        self.add(hline())
        self.add(title("Interactive — why anyone cares: two numbers are the "
                       "entire plant"))

        fit = Card("fit K and τ once, then predict every other input for free")
        fit.add(body(
            "The grey dots are a <b>measured</b> step response from a joint you "
            "have never seen — noisy, like a real encoder. Drag K and τ until "
            "your model (blue) sits on the dots. That is a two-minute experiment "
            "on real hardware.<br><br>"
            "Now change the input. <b>Your two numbers keep predicting.</b> Ramp "
            "it, square-wave it, shake it — the model that matched one step "
            "matches everything, because a first-order plant has nothing else in "
            "it. <i>That</i> is what identifying the order buys you: a complete, "
            "permanent model of the machine from one push.", dim=True))
        self.s_fk = slider(2, 60, 40)          # x0.1
        self.s_ft = slider(10, 600, 300)       # ms
        self.l_fk, self.l_ft = QLabel(), QLabel()
        fit.add_layout(slider_row("your model K (×0.1)", self.s_fk, self.l_fk))
        fit.add_layout(slider_row("your model τ (ms)", self.s_ft, self.l_ft))
        self.in_box = QComboBox()
        for name in ("step", "ramp", "square wave", "sine", "torque pulse"):
            self.in_box.addItem(name)
        self.btn_newplant = _btn("new unknown joint")
        fit.add_layout(_btn_row(self.in_box, self.btn_newplant))
        self.st_fiterr = Stat("mismatch (RMS)", "--", theme.WARN)
        self.st_fitv = Stat("verdict", "--", theme.TEXT_DIM)
        fit.add_layout(stat_row(self.st_fiterr, self.st_fitv))
        self.c_fit = MplCanvas(width=7.4, height=3.0, ncols=2)
        fit.add(self.c_fit)
        self.add(fit)
        self._plant_seed = 20250807
        self._new_plant(first=True)
        for w in (self.s_fk, self.s_ft):
            w.valueChanged.connect(self._redraw_fit)
        self.in_box.currentIndexChanged.connect(self._redraw_fit)
        self.btn_newplant.clicked.connect(self._new_plant)
        self._redraw_fit()

        # ---- the payoff ---------------------------------------------------
        self.add(hline())
        self.add(title("So what? Four things the answer \"first order\" actually "
                       "decides"))

        so = Card("what you do differently on Monday morning")
        so.add(body(
            "<table cellpadding='7'>"
            "<tr><td width='30'><b>1</b></td>"
            "<td><b>How fast you are allowed to run the loop around it.</b><br>"
            "τ sets the fastest thing the plant can physically do. A winding "
            "with τ = 0.5 ms settles in ~2 ms, so a 20 kHz current loop is "
            "doing useful work every cycle. A joint with τ = 300 ms cannot "
            "respond to anything you send it faster than a few Hz, so a 20 kHz "
            "position loop is 19,900 wasted computations per second and three "
            "extra sources of noise. <i>Page 6 makes this a calculator.</i>"
            "</td></tr>"
            "<tr><td><b>2</b></td>"
            "<td><b>Whether you are allowed to turn the gain up.</b><br>"
            "A first-order plant with proportional feedback <b>cannot be "
            "destabilised at any gain</b> — that is a theorem, not a rule of "
            "thumb, and it is proved on page 8. So when a loop is first order "
            "you tune it by turning the knob until it is fast enough and then "
            "stopping. When it is second order you cannot, and the entire "
            "controller-design half of this tutor exists for that case."
            "</td></tr>"
            "<tr><td><b>3</b></td>"
            "<td><b>How many states your model, observer or RL agent needs.</b>"
            "<br>One store = one state. A velocity estimator for a first-order "
            "joint needs one number; a position controller for the same joint "
            "needs two, because you added an integrator. Guess low and your "
            "observer will never converge; guess high and you are estimating "
            "noise. The count of energy stores <i>is</i> the state dimension."
            "</td></tr>"
            "<tr><td><b>4</b></td>"
            "<td><b>What it means when the hardware disagrees with you.</b><br>"
            "This is the one that earns its keep. If you counted one store and "
            "the joint <b>rings</b>, your count is wrong: there is a shaft "
            "winding up, a belt stretching, a mount flexing, a filter you "
            "forgot, or a delay. The ringing is not a nuisance to be tuned "
            "away — it is the machine telling you where a reservoir is that you "
            "did not know about. Tuning it out with a lower gain hides the "
            "information and leaves the reservoir there."
            "</td></tr>"
            "</table>"))
        self.add(so)

        v = Card("the vocabulary, since it gets used loosely")
        v.add(body(
            "&nbsp;&nbsp;• <b>Overshoot</b> — the output goes <i>past</i> the "
            "target before coming back. Needs a second store, always.<br>"
            "&nbsp;&nbsp;• <b>Ringing</b> (= wobbling) — it overshoots, comes "
            "back too far, overshoots again, each swing smaller. Energy sloshing "
            "between two stores while friction eats it. It <i>does</i> die "
            "out.<br>"
            "&nbsp;&nbsp;• <b>Hunting</b> — the same swinging, but it <b>does "
            "not die out</b>. The joint never settles; it patrols around the "
            "setpoint forever. Usually too much gain, a delay, or stiction. "
            "Ringing is a tuning imperfection; hunting is a fault.<br>"
            "&nbsp;&nbsp;• <b>Settled</b> — the fill and the leak have become "
            "equal, so the net flow is zero. Strictly this takes forever; in "
            "practice \"settled\" means inside a ±2% band, which is 4τ."))
        v.add(callout(
            "<b>A first-order joint under constant torque does none of the "
            "first three.</b> It rises, it flattens, it stops. If yours "
            "wobbles, re-read row 4 above.", "good"))
        self.add(v)

        w = Card("the same two features, four different physical dresses")
        w.add(body(
            "<table cellpadding='6'>"
            "<tr><td><b>Motor winding</b></td><td>L·di/dt + R·i = V</td>"
            "<td>τ = L/R, typically <b>0.1–2 ms</b>.</td></tr>"
            "<tr><td><b>Velocity of a joint</b></td><td>J·ω̇ + b·ω = τ</td>"
            "<td>τ = J/b. Torque in, speed out — first order, always.</td></tr>"
            "<tr><td><b>Any low-pass filter</b></td><td>τ·ẏ + y = u</td>"
            "<td>Including the derivative filter you were told to always add "
            "on the PID page.</td></tr>"
            "<tr><td><b>Thermal</b></td><td>C·Ṫ + T/R = P</td>"
            "<td>τ = RC, <b>minutes</b>. Motor thermal limits are a first-order "
            "system with a very slow pole.</td></tr>"
            "</table>"))
        self.add(w)

        self.add(callout(
            "<b>Carry forward.</b> One store, one drain, two numbers — and the "
            "count of stores is something you measure, not something you are "
            "told. Next page: what τ actually <i>is</i>, where 0.63 comes from, "
            "and why that one number decides your loop rate.", "good"))

        self.finish()

    # ------------------------------------------------------------------
    def _redraw_ident(self):
        s = _SYSTEMS[self.sys_box.currentIndex()]
        g = s["tf"]()
        order = g.order()

        rows = [f"<i>{s['blurb']}</i><br>"]
        rows.append("<b>Stores — one per quantity that cannot jump:</b>")
        for i, (what, holds, why) in enumerate(s["stores"], start=1):
            tail = f" &nbsp;<span style='color:{theme.TEXT_FAINT}'>({why})</span>" \
                if why else ""
            rows.append(f"&nbsp;&nbsp;<b>{i}.</b> {what} — {holds}{tail}")
        rows.append("<b>Drains — proportional to what is stored:</b>")
        for what, how in s["drains"]:
            rows.append(f"&nbsp;&nbsp;• {what} — {how}")
        rows.append(f"<b>Equation:</b> &nbsp; {s['ode']}")
        self.sys_text.setText("<br>".join(rows))

        n = len(s["stores"])
        self.st_stores.set(str(n))
        self.st_order.set(f"{order}")
        self.st_over.set("no" if order < 2 else "yes")
        self.st_over.set_color(theme.GOOD if order < 2 else theme.BAD)
        self.st_lag.set(f"{90 * order}°")

        c = self.c_ident
        c.clear()
        a1, a2 = c.axes
        t, y = step_response(g, s["tlim"], s["tlim"] / 800.0)
        scale = max(abs(v) for v in y) or 1.0
        a1.plot(t, [v / scale for v in y], color=theme.ACCENT, lw=2.2)
        if order == 1:
            a1.axhline(1.0, color=theme.TEXT_FAINT, lw=1.0, ls="--")
            a1.text(0.03, 0.86, "leaves at its steepest, only ever flattens\n"
                                "→ ONE store",
                    transform=a1.transAxes, color=theme.GOOD, fontsize=7.5)
        else:
            a1.axhline(y[-1] / scale, color=theme.TEXT_FAINT, lw=1.0, ls="--")
            a1.text(0.03, 0.86, "starts FLAT — a second store has to fill\n"
                                "before the output can move  → 2+ stores",
                    transform=a1.transAxes, color=theme.BAD, fontsize=7.5)
        a1.set_xlabel("time (s)")
        a1.set_ylabel("output (normalised)")
        a1.set_title("step response", fontsize=9)
        poles = g.poles()
        lim = max(2.0, max(abs(p) for p in poles) * 1.4)
        _splane(a2, poles, lim=lim)
        a2.set_title(f"{order} pole(s)", fontsize=9)
        c.refresh()

    # ------------------------------------------------------------------
    def _new_plant(self, first=False):
        self._plant_seed = (self._plant_seed * 48271 + 11) & 0x7FFFFFFF
        r = _lcg(self._plant_seed)
        self._k_true = 1.2 + 3.0 * (r() + 0.5)
        self._tau_true = 0.04 + 0.45 * (r() + 0.5)
        if not first:
            self._redraw_fit()

    def _inputs(self, kind, dur):
        """Return u(t) for the selected excitation."""
        if kind == 0:                              # step
            return lambda t: 1.0
        if kind == 1:                              # ramp
            return lambda t: t / dur
        if kind == 2:                              # square wave
            per = dur / 3.0
            return lambda t: 1.0 if (t % per) < per / 2 else 0.0
        if kind == 3:                              # sine
            w = 2 * math.pi * 2.5 / dur * 3
            return lambda t: math.sin(w * t)
        per = dur / 6.0                            # torque pulse
        return lambda t: 1.0 if t < per else 0.0

    def _redraw_fit(self):
        k = self.s_fk.value() / 10.0
        tau = self.s_ft.value() / 1000.0
        self.l_fk.setText(f"{k:.1f}")
        self.l_ft.setText(f"{tau*1000:.0f} ms")

        truth = first_order(self._k_true, self._tau_true)
        model = first_order(k, tau)
        dur = max(6 * self._tau_true, 6 * tau, 0.2)
        dt = dur / 700.0

        # -- left: the measurement you actually made -----------------------
        t, y_true = step_response(truth, dur, dt)
        _, y_mod = step_response(model, dur, dt)
        r = _lcg(self._plant_seed ^ 0x5A5A)
        noise = self._k_true * 0.025
        meas = [v + noise * r() * 2 for v in y_true]

        err = math.sqrt(sum((a - b) ** 2 for a, b in zip(meas, y_mod))
                        / len(meas))
        rel = err / max(self._k_true, 1e-9)
        self.st_fiterr.set(f"{rel*100:.1f}%")
        if rel < 0.035:
            self.st_fitv.set("identified")
            self.st_fitv.set_color(theme.GOOD)
            self.st_fiterr.set_color(theme.GOOD)
        elif rel < 0.12:
            self.st_fitv.set("close")
            self.st_fitv.set_color(theme.WARN)
            self.st_fiterr.set_color(theme.WARN)
        else:
            self.st_fitv.set("keep dragging")
            self.st_fitv.set_color(theme.BAD)
            self.st_fiterr.set_color(theme.BAD)

        c = self.c_fit
        c.clear()
        a1, a2 = c.axes
        step = max(1, len(t) // 90)
        a1.scatter(t[::step], meas[::step], s=11, color=theme.TEXT_FAINT,
                   zorder=3, label="measured (noisy)")
        a1.plot(t, y_mod, color=theme.ACCENT, lw=2.2, label="your model")
        a1.set_xlabel("time (s)")
        a1.set_ylabel("output")
        a1.set_title("the one experiment you ran: a step", fontsize=9)
        c.legend(a1, loc="lower right")

        # -- right: the same two numbers, a different input ----------------
        kind = self.in_box.currentIndex()
        u = self._inputs(kind, dur)
        ts_t, ys_t, _ = simulate_ss(tf_to_ss(truth), u, dur, dt)
        ts_m, ys_m, _ = simulate_ss(tf_to_ss(model), u, dur, dt)
        # the input is drawn above the responses on an arbitrary scale -- it is
        # there to show the SHAPE you are commanding, not a comparable size
        amp = 1.25 * max(max(abs(v) for v in ys_t), 1e-9)
        a2.plot(ts_t, [u(v) * amp for v in ts_t],
                color=theme.TEXT_FAINT, lw=1.1, ls=":",
                label="input shape (arb. scale)")
        a2.plot(ts_t, ys_t, color=theme.GOOD, lw=2.4, label="real joint")
        a2.plot(ts_m, ys_m, color=theme.ACCENT, lw=1.6, ls="--",
                label="your model predicts")
        a2.set_xlabel("time (s)")
        a2.set_ylabel("output")
        a2.set_title(f"prediction — {self.in_box.currentText()}", fontsize=9)
        c.legend(a2, loc="lower right")
        c.refresh()


# ==========================================================================
# PAGE -- the time constant and the pole
# ==========================================================================

class TimeConstantPage(Page):
    TITLE = "The Time Constant & the Pole"
    SUBTITLE = ((
                    "One first-order model, three related quantities. Where 0.63 comes from, what the decay rate "
                    "actually is, and why the current loop runs at 20 kHz and the joint loop does not."
                ))
    SECTION = SECTION
    NOTES = "foundation"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            (
                "<b>Time constant, pole and bandwidth describe the same first-order dynamics in different "
                "units.</b> τ = 50 ms, pole at −20 1/s, bandwidth 3.2 Hz are three ways of saying one fact about"
                " one piece of hardware. This page earns that sentence, then makes it a calculator."
            ), "key"))

        # ---- the bucket ---------------------------------------------------
        b = Card("the cup with a hole in it — hold this picture")
        b.add(body(
            "A cup with a small hole in the bottom, and a tap above it. That is "
            "the entire object. Two things are worth noticing and everything "
            "else on this page follows from them:"))
        b.add(body(
            "&nbsp;&nbsp;<b>The tap pours at a constant rate.</b> It does not "
            "care how full the cup is.<br>"
            "&nbsp;&nbsp;<b>The hole drains at a rate set by the level.</b> High "
            "water → more pressure → drains fast. Low water → drains slowly."))
        b.add(callout(
            "<b>That second sentence is the whole of first-order dynamics.</b> "
            "Because the leak grows with the level, the level does not rise in a "
            "straight line — it rises fast, then eases off, approaching the "
            "balance point more and more gently. That curve <i>is</i> the "
            "exponential. e<sup>−t/τ</sup> is not an abstract function that "
            "happens to fit; it is literally the shape of a thing changing at a "
            "rate proportional to how far it still has to go.", "key"))
        self.add(b)

        i = Card("interactive — pour, then stop pouring")
        i.add(body(
            "Watch the two rate bars on the left, not the level. <b>Settled "
            "does not mean stopped — it means the two bars have become the "
            "same height.</b> Fill equals leak, net flow zero, tug-of-war "
            "balanced. That is the definition of steady state, and it is why "
            "nothing ever \"arrives\": it just stops changing.<br><br>"
            "Then hit <b>stop pouring</b>. The fill bar goes to zero and the "
            "cup drains — fast at first, then slower, for exactly the same "
            "reason.", dim=True))
        self.s_btau = slider(100, 2000, 500)
        self.l_btau = QLabel()
        i.add_layout(slider_row("time constant τ (ms)", self.s_btau,
                                self.l_btau))
        self.btn_pour = _btn("pour", primary=True)
        self.btn_stop = _btn("stop pouring")
        self.btn_breset = _btn("reset")
        i.add_layout(_btn_row(self.btn_pour, self.btn_stop, self.btn_breset))
        self.st_blevel = Stat("level", "--", theme.ACCENT)
        self.st_bfill = Stat("fill rate", "--", theme.GOOD)
        self.st_bleak = Stat("leak rate", "--", theme.BAD)
        self.st_bnet = Stat("net", "--", theme.WARN)
        self.st_bt = Stat("elapsed", "--", theme.TEXT_DIM)
        i.add_layout(stat_row(self.st_blevel, self.st_bfill, self.st_bleak,
                              self.st_bnet, self.st_bt))
        self.c_bucket = MplCanvas(width=7.4, height=3.0, ncols=2)
        i.add(self.c_bucket)
        self.add(i)

        self._blevel = 0.0
        self._bt = 0.0
        self._bpour = True
        self._bhist = [(0.0, 0.0)]
        self._btimer = QTimer(self)
        self._btimer.setInterval(55)
        self._btimer.timeout.connect(self._tick_bucket)
        self.btn_pour.clicked.connect(lambda: self._set_pour(True))
        self.btn_stop.clicked.connect(lambda: self._set_pour(False))
        self.btn_breset.clicked.connect(self._reset_bucket)
        self.s_btau.valueChanged.connect(self._reset_bucket)
        self._build_bucket()

        # ---- where 0.63 comes from ----------------------------------------
        z = Card("where 63.2% comes from — computed, not asserted")
        z.add(body("Solve the equation with the tap turned on at t = 0:"))
        z.add(math_label(r"y(t) = K\left(1 - e^{-t/\tau_c}\right)", 17))
        z.add(body("Put t = τ<sub>c</sub> into it:"))
        z.add(math_label(r"1 - e^{-1} \;=\; 1 - 0.3679 \;=\; 0.632", 17))
        z.add(body(
            "<b>That is the entire origin of the number.</b> It is e<sup>−1</sup> "
            "and nothing else. τ is <i>not</i> \"the time to settle\" — an "
            "exponential never finishes. τ is the time to get 63.2% of the way, "
            "which is a statement about <i>how fast the approach happens</i>, "
            "not about arriving.", dim=True))
        z.add(callout(
            "<b>The other way to read τ, which is the one worth carrying.</b> "
            "At the instant you turn the tap on the cup is empty, so the leak is "
            "zero, so the level is rising at its fastest. <b>If it kept rising "
            "at that initial rate it would reach the final value in exactly "
            "τ<sub>c</sub> seconds.</b> It does not, because the leak grows as "
            "it climbs — so it only gets 63.2% of the way. The dashed tangent "
            "in the plot below is that \"if the leak never grew\" line, and it "
            "crosses the final value at t = τ every single time, for any τ and "
            "any K.", "key"))
        z.add(body(
            "The landmarks you will read off an oscilloscope for the rest of "
            "your life: <b>1τ → 63.2%</b>, 2τ → 86.5%, 3τ → 95.0%, 4τ → 98.2%, "
            "<b>5τ → 99.3%</b>. \"Settled\" conventionally means 4τ, the ±2% "
            "band.", dim=True))
        self.add(z)

        # ---- the pole ------------------------------------------------------
        self.add(hline())
        self.add(title("The pole — a duration, flipped into a rate"))

        p = Card("τ answers \"how long\". The pole answers \"how often per "
                 "second\". Same fact.")
        p.add(body(
            "You have a duration: τ = 0.5 s, \"this cup mostly-drains in half a "
            "second\". Flip it: 1/τ = 2 per second, \"this cup mostly-drains "
            "twice a second\". That is the pole's size. It is the same "
            "information in the other unit — like saying a job takes half an "
            "hour versus you do two an hour."))
        p.add(math_label(r"p \;=\; -\frac{1}{\tau_c} \;=\; -\frac{b}{J} "
                         r"\qquad \left[\;\frac{1}{\text{seconds}}\;\right]", 17))
        p.add(body(
            "<b>Leak divided by store, in units of 1/seconds.</b> Bigger number "
            "= faster draining = shorter τ. The minus sign says draining rather "
            "than growing.", dim=True))

        p.add(body(
            "<b>An e-fold, plainly.</b> One e-fold is one division by "
            "e ≈ 2.718 — a drop to 36.8%. It is exactly the idea of a "
            "half-life, using e instead of 2 because e is what falls out of the "
            "differential equation. If half-lives are more familiar: this "
            "system's half-life is 0.693 τ. <b>|p| is how many e-folds the "
            "transient loses per second.</b><br><br>"
            "A winding with τ = 0.5 ms loses 2000 e-folds per second — after one "
            "millisecond a disturbance is down to 14% of what it was. A joint "
            "with τ = 0.5 s loses 2 per second, so half a second after a bump it "
            "is still 37% wrong."))
        self.add(p)

        # ---- terminology, honestly ----------------------------------------
        t = Card("what this is called in textbooks — and where my word "
                 "\"forgetting\" came from")
        t.add(callout(
            "<b>Straight answer: \"forgetting rate\" is not standard control "
            "terminology. I coined it as a gloss, and if it is not helping, drop "
            "it.</b> Below is the vocabulary the field actually uses for the "
            "identical quantity. Learn these; they are what a colleague, a "
            "datasheet and every textbook will say.", "warn"))
        t.add(body(
            "<table cellpadding='7'>"
            "<tr><td><b>Standard term</b></td><td><b>Symbol</b></td>"
            "<td><b>What it names</b></td></tr>"

            "<tr><td><b>decay rate</b><br>(or <i>exponential decay rate</i>, "
            "<i>rate of decay</i>)</td><td>|σ| = |Re p| = 1/τ</td>"
            "<td><b>This is the standard name for the number I called the "
            "forgetting rate.</b> Units 1/s. \"The transient decays at 20 per "
            "second.\"</td></tr>"

            "<tr><td><b>time constant</b></td><td>τ</td>"
            "<td>Its reciprocal, in seconds. The most common way to quote "
            "it.</td></tr>"

            "<tr><td><b>transient response</b><br>= <i>natural response</i> "
            "= <i>zero-input response</i></td><td>—</td>"
            "<td>The part of the output that dies away and leaves nothing "
            "behind. What \"is forgotten\" is precisely this.</td></tr>"

            "<tr><td><b>mode</b></td><td>e<sup>pt</sup></td>"
            "<td>One pole's contribution. A system's response is a sum of its "
            "modes. \"The slow mode dominates\" is ordinary shop "
            "talk.</td></tr>"

            "<tr><td><b>settling time</b></td><td>T<sub>s</sub> ≈ 4τ</td>"
            "<td>How long until the transient is small enough to ignore "
            "(±2%).</td></tr>"

            "<tr><td><b>disturbance rejection</b></td><td>—</td>"
            "<td>The property of removing the effect of an uncommanded input. "
            "\"Forgetting the rock\" is this, in the proper words.</td></tr>"
            "</table>"))
        t.add(body(
            "<b>Three related terms that are real, so you do not confuse "
            "them:</b><br>"
            "&nbsp;&nbsp;• <b>memoryless</b> — a genuine, standard term for a "
            "component whose output depends only on the input <i>right now</i>: "
            "a resistor, ideal viscous friction, a gain. It has no state, so "
            "there is nothing for it to be late with. Used correctly on page 8 "
            "when friction is said to have no memory.<br>"
            "&nbsp;&nbsp;• <b>fading memory</b> — a real term in systems theory "
            "for exactly the property being described here: the influence of the "
            "distant past decays to nothing. Closest respectable relative of my "
            "coinage.<br>"
            "&nbsp;&nbsp;• <b>forgetting factor</b> λ — a real and common term, "
            "but it belongs to <i>recursive least squares</i> and adaptive "
            "identification, where it weights old <i>data</i> less than new "
            "data. It is not a property of a plant's poles. Do not mix them up.",
            dim=True))
        t.add(callout(
            "<b>So what should you actually say?</b> \"The pole at −20 gives a "
            "50 ms time constant\", or \"the transient decays at 20 per second\", "
            "or \"it settles in about 200 ms\". Those are the three sentences "
            "people use, and they are all the same measurement.<br><br>"
            "Keep the metaphor only for the one thing it is good at: it makes it "
            "obvious <b>why a decaying transient is what you want</b>. Your foot "
            "hits a rock; the bump puts something into the joint's store that you "
            "never commanded. <b>\"The transient decays\" and \"the joint gets "
            "back to the speed you asked for\" are the same event described "
            "twice.</b> Fast decay = fast recovery = fast tracking. The price is "
            "that it also reacts to every twitch, including sensor noise — and "
            "that trade is the whole reason a controller has knobs.", "key"))
        self.add(t)

        # ---- decay meter ----------------------------------------------------
        m = Card("interactive — kick it, and watch the transient decay")
        m.add(body(
            "Two systems, different τ. <b>Kick both</b> injects the same "
            "disturbance into each — one shove, then hands off. Nothing drives "
            "them after that, so what you are watching is the pure <b>zero-input "
            "response</b>: the transient, and nothing else.<br><br>"
            "The right-hand plot is the same two traces on a <b>logarithmic</b> "
            "y-axis, and it is the point of the widget: on a log axis "
            "exponential decay is a <b>straight line, and the pole is its "
            "slope</b>. A steeper line is a bigger pole, a shorter τ, a system "
            "whose transient dies faster. The pole is not an abstraction of the "
            "decay — it is the decay's gradient, in 1/seconds.", dim=True))
        self.s_ma = slider(50, 3000, 200)
        self.s_mb = slider(50, 3000, 1200)
        self.l_ma, self.l_mb = QLabel(), QLabel()
        m.add_layout(slider_row("system A — τ (ms)", self.s_ma, self.l_ma))
        m.add_layout(slider_row("system B — τ (ms)", self.s_mb, self.l_mb))
        self.btn_kick = _btn("kick both", primary=True)
        self.btn_mreset = _btn("reset")
        m.add_layout(_btn_row(self.btn_kick, self.btn_mreset))
        self.mem_text = _readout()
        m.add(self.mem_text)
        self.c_mem = MplCanvas(width=7.4, height=3.0, ncols=2)
        m.add(self.c_mem)
        m.add(body(
            "Set A to 50 ms and B to 3000 ms and kick. A is back to baseline "
            "before B has visibly moved. Those are the same two systems as the "
            "current loop and the joint loop, and the gap you are looking at is "
            "the reason they cannot share a controller.", dim=True))
        self.add(m)

        self._mt = 0.0
        self._mhist = []
        self._mtimer = QTimer(self)
        self._mtimer.setInterval(55)
        self._mtimer.timeout.connect(self._tick_mem)
        self.btn_kick.clicked.connect(self._kick)
        self.btn_mreset.clicked.connect(self._reset_mem)
        for w in (self.s_ma, self.s_mb):
            w.valueChanged.connect(self._reset_mem)
        self._build_mem()

        # ---- three hats ----------------------------------------------------
        self.add(hline())
        self.add(title("One number, three hats"))

        h = Card("move the pole, watch everything else move with it")
        h.add(body(
            "Drag τ. The pole slides along the real axis and the response "
            "changes speed — they are the same fact drawn twice. A pole at "
            "−20 1/s and a 50 ms time constant are one sentence in two "
            "languages, and the bandwidth chip is the third translation "
            "(page 8 earns it).", dim=True))
        self.s_tau = slider(2, 200, 50)          # ms
        self.s_k = slider(1, 50, 10)             # x0.1
        self.l_tau, self.l_k = QLabel(), QLabel()
        h.add_layout(slider_row("time constant τ (ms)", self.s_tau, self.l_tau))
        h.add_layout(slider_row("DC gain K (×0.1)", self.s_k, self.l_k))
        self.st_pole = Stat("pole", "--", theme.ACCENT)
        self.st_efold = Stat("decay rate (e-folds/s)", "--", theme.PINK)
        self.st_63 = Stat("63% at", "--", theme.GOOD)
        self.st_settle = Stat("settled (4τ)", "--", theme.WARN)
        self.st_bw = Stat("bandwidth", "--", theme.VIOLET)
        h.add_layout(stat_row(self.st_pole, self.st_efold, self.st_63,
                              self.st_settle, self.st_bw))
        self.c1 = MplCanvas(width=7.4, height=2.9, ncols=2)
        h.add(self.c1)
        self.add(h)
        for w in (self.s_tau, self.s_k):
            w.valueChanged.connect(self._redraw_step)
        self._redraw_step()

        st = Card("the sign, since it is the one thing people get backwards")
        st.add(math_label(r"y(t) = K\left(1 - e^{\,p\,t}\right), \qquad "
                          r"p = -1/\tau_c", 16))
        st.add(body(
            "&nbsp;&nbsp;• <b>p negative</b> — e<sup>pt</sup> decays, the leak "
            "wins, the disturbance drains away → <b>stable</b>. This is what a "
            "real damper or resistor always does.<br>"
            "&nbsp;&nbsp;• <b>p positive</b> — e<sup>pt</sup> grows. Something "
            "is <i>feeding</i> the store instead of draining it → "
            "<b>unstable</b>. Physically that is negative friction, which sounds "
            "exotic until you meet an inverted pendulum, where gravity does "
            "exactly that.<br>"
            "&nbsp;&nbsp;• <b>p = 0</b> — no leak at all. Whatever goes in stays "
            "in, forever → <b>marginal</b>. A frictionless joint: push it once "
            "and it coasts for the rest of time. This is an "
            "<b>integrator</b>.<br>"
            "&nbsp;&nbsp;• <b>further left = decays faster.</b> The real part "
            "<i>is</i> the decay rate. Nothing is encoded or hidden."))
        st.add(callout(
            "<b>The third case — p = 0 — is important enough that it has the "
            "next page to itself.</b> It is the exact opposite of the winding: a "
            "store with no drain at all, whose transient never decays. That "
            "sounds like a defect, and it is precisely the property that kills "
            "steady-state error, that makes position control second order even "
            "when the mechanism has one moving part, and that makes an "
            "integrator the one thing you cannot leave out of a real "
            "controller.", "key"))
        self.add(st)

        # ---- loop rate bench -------------------------------------------
        self.add(hline())
        self.add(title("Interactive — why the current loop runs at 20 kHz and "
                       "the joint loop cannot"))

        lr = Card("the same calculation, on two pieces of the same motor")
        lr.add(body(
            "This is the question that started the whole cascade. Both columns "
            "are first-order systems; both obey τ = store ÷ drain. They differ "
            "by three orders of magnitude, and that gap — not a convention, not "
            "a CPU limit — is what forces a fast inner loop inside a slow outer "
            "one.<br><br>"
            "Loop rate is taken as <b>≈ 15× the bandwidth</b>, the rule from "
            "page 1: sampling, zero-order hold and computation each cost you "
            "phase, so you buy roughly f<sub>s</sub>/15 of usable control "
            "authority.", dim=True))
        self.s_L = slider(1, 50, 8)       # x0.1 mH
        self.s_R = slider(2, 200, 12)     # x0.1 ohm
        self.s_J = slider(1, 200, 25)     # x0.001 kg m^2
        self.s_b = slider(1, 200, 40)     # x0.01 N m s
        self.l_L, self.l_R, self.l_J, self.l_b = (QLabel() for _ in range(4))
        lr.add_layout(slider_row("winding L (mH)", self.s_L, self.l_L))
        lr.add_layout(slider_row("winding R (Ω)", self.s_R, self.l_R))
        lr.add_layout(slider_row("joint inertia J (kg·m²)", self.s_J, self.l_J))
        lr.add_layout(slider_row("joint damping b (N·m·s)", self.s_b, self.l_b))
        self.st_te = Stat("τ  electrical", "--", theme.CYAN)
        self.st_tm = Stat("τ  mechanical", "--", theme.ORANGE)
        self.st_fe = Stat("loop rate — current", "--", theme.GOOD)
        self.st_fm = Stat("loop rate — joint", "--", theme.WARN)
        self.st_sep = Stat("separation", "--", theme.VIOLET)
        lr.add_layout(stat_row(self.st_te, self.st_tm, self.st_fe, self.st_fm,
                               self.st_sep))
        self.c_lr = MplCanvas(width=7.4, height=3.0, ncols=2)
        lr.add(self.c_lr)
        self.lr_text = _readout()
        lr.add(self.lr_text)
        self.add(lr)
        for w in (self.s_L, self.s_R, self.s_J, self.s_b):
            w.valueChanged.connect(self._redraw_lr)
        self._redraw_lr()

        cc = Card("what it means for the robot in front of you")
        cc.add(body(
            "&nbsp;&nbsp;• <b>The current loop is first order</b> (L/R), which "
            "is why it can be closed at 20 kHz with a plain PI and never argued "
            "about. It is the well-behaved layer everything else stands on.<br>"
            "&nbsp;&nbsp;• <b>A velocity loop on a rigid joint is first "
            "order</b> (J/b). Speed control is genuinely easy. Position control "
            "is not, because integrating velocity adds a pole at the origin — "
            "and that is a second-order system with a marginal pole in it.<br>"
            "&nbsp;&nbsp;• <b>Your sensors and filters are first order too</b>, "
            "and each one hands the loop up to 90° of lag it did not previously "
            "have. Three innocent filters can hand over 270°, which is more "
            "than enough to oscillate. Filters are not free.<br>"
            "&nbsp;&nbsp;• <b>Rule of thumb:</b> a sensor filter should be "
            "5–10× faster than the loop bandwidth, or its pole is now part of "
            "your control problem."))
        self.add(cc)

        self.add(callout(
            "<b>Carry forward.</b> τ = store ÷ drain, in seconds. The pole is "
            "−1/τ, a <b>decay rate</b> in 1/seconds, and it is the slope of the "
            "transient on a log axis. Both are the same measurement of the same "
            "hardware. Next: what happens when the drain is missing "
            "altogether.", "good"))

        self.finish()


    # ------------------------------------------------------------------
    def on_show(self):
        self._btimer.start()
        # only resume the memory trace if a kick is actually in flight --
        # otherwise revisiting the page would start a decay nobody asked for
        if self._mhist and self._mt < 8 * max(self.s_ma.value(),
                                              self.s_mb.value()) / 1000.0:
            self._mtimer.start()

    def on_hide(self):
        self._btimer.stop()
        self._mtimer.stop()

    # -- bucket ---------------------------------------------------------
    def _set_pour(self, on: bool):
        self._bpour = on
        self._btimer.start()

    def _reset_bucket(self):
        self._blevel = 0.0
        self._bt = 0.0
        self._bpour = True
        self._bhist = [(0.0, 0.0)]
        self._build_bucket()
        self._btimer.start()

    def _tick_bucket(self):
        tau = self.s_btau.value() / 1000.0
        dt = 0.055
        fill = 1.0 if self._bpour else 0.0
        # tau*ydot + y = u  ->  ydot = (u - y)/tau
        self._blevel += dt * (fill - self._blevel) / tau
        self._bt += dt
        self._bhist.append((self._bt, self._blevel))
        if len(self._bhist) > 4000:
            self._bhist.pop(0)
        self._frame_bucket()

    def _build_bucket(self):
        """Everything that only changes when tau does. Called rarely."""
        tau = self.s_btau.value() / 1000.0
        self.l_btau.setText(f"{tau*1000:.0f} ms")
        c = self.c_bucket
        c.clear()
        a1, a2 = c.axes

        self._bbars = a1.bar([0, 1, 2], [0.0, 1.0, 0.0],
                             color=[theme.ACCENT, theme.GOOD, theme.BAD],
                             width=0.55)
        a1.set_xticks([0, 1, 2])
        a1.set_xticklabels(["level", "fill rate", "leak rate"], fontsize=8)
        a1.set_ylim(0, 1.15)
        a1.set_ylabel("fraction of full")
        a1.axhline(1.0, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a1.set_title("settled = the two rate bars match", fontsize=9)
        self._bsettled = a1.text(0.5, 0.9, "", transform=a1.transAxes,
                                 ha="center", color=theme.GOOD, fontsize=8.5,
                                 fontweight="bold")

        self._bline, = a2.plot([], [], color=theme.ACCENT, lw=2.2)
        a2.axhline(0.632, color=theme.GOOD, lw=1.0, ls=":", label="63.2%")
        a2.axhline(0.368, color=theme.WARN, lw=1.0, ls=":", label="36.8%")
        a2.axhline(1.0, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        for n in range(1, 9):
            a2.axvline(n * tau, color=theme.BORDER, lw=0.9, ls=":")
            a2.text(n * tau, 1.06, f"{n}τ", color=theme.TEXT_FAINT,
                    fontsize=7, ha="center")
        a2.set_xlim(0, 6 * tau)
        a2.set_ylim(-0.03, 1.18)
        a2.set_xlabel("time (s)")
        a2.set_ylabel("level")
        a2.set_title("level vs time", fontsize=9)
        c.legend(a2, loc="center right")
        c.refresh()
        self._frame_bucket()

    def _frame_bucket(self):
        tau = self.s_btau.value() / 1000.0
        fill = 1.0 if self._bpour else 0.0
        leak = self._blevel
        net = fill - leak
        self.st_blevel.set(f"{self._blevel*100:.1f}%")
        self.st_bfill.set(f"{fill*100:.0f}%")
        self.st_bleak.set(f"{leak*100:.1f}%")
        self.st_bnet.set(f"{net*100:+.1f}%")
        self.st_bnet.set_color(theme.GOOD if abs(net) < 0.02 else theme.WARN)
        self.st_bt.set(f"{self._bt:.2f} s  =  {self._bt/tau:.2f} τ")

        for bar, h in zip(self._bbars, (self._blevel, fill, leak)):
            bar.set_height(h)
        self._bsettled.set_text("SETTLED — net flow zero"
                                if abs(net) < 0.02 else "")
        ts = [p[0] for p in self._bhist]
        ys = [p[1] for p in self._bhist]
        self._bline.set_data(ts, ys)
        self.c_bucket.axes[1].set_xlim(0, max(6 * tau, ts[-1] * 1.02))
        self.c_bucket.refresh(layout=False)

    # -- memory meter ---------------------------------------------------
    def _reset_mem(self):
        self._mt = 0.0
        self._mhist = []
        self._mtimer.stop()
        self._build_mem()

    def _kick(self):
        self._mt = 0.0
        self._mhist = [(0.0, 1.0, 1.0)]
        self._mtimer.start()

    def _tick_mem(self):
        ta = self.s_ma.value() / 1000.0
        tb = self.s_mb.value() / 1000.0
        self._mt += 0.055
        self._mhist.append((self._mt,
                            math.exp(-self._mt / ta),
                            math.exp(-self._mt / tb)))
        if self._mt > 8 * max(ta, tb):
            self._mtimer.stop()
        self._frame_mem()

    def _build_mem(self):
        ta = self.s_ma.value() / 1000.0
        tb = self.s_mb.value() / 1000.0
        self.l_ma.setText(f"{ta*1000:.0f} ms")
        self.l_mb.setText(f"{tb*1000:.0f} ms")
        span = max(4 * max(ta, tb), 0.2)

        c = self.c_mem
        c.clear()
        a1, a2 = c.axes
        self._mlin_a, = a1.plot([], [], color=theme.ACCENT, lw=2.2, label="A")
        self._mlin_b, = a1.plot([], [], color=theme.ORANGE, lw=2.2, label="B")
        for lvl, lab in ((0.368, "1 e-fold  37%"), (0.135, "2  13.5%"),
                         (0.050, "3  5.0%"), (0.018, "4  1.8%")):
            a1.axhline(lvl, color=theme.BORDER, lw=0.9, ls=":")
            a1.text(span * 0.995, lvl + 0.012, lab, color=theme.TEXT_FAINT,
                    fontsize=6.8, ha="right")
        a1.set_xlim(0, span)
        a1.set_ylim(0, 1.05)
        a1.set_xlabel("time since the kick (s)")
        a1.set_ylabel("fraction of the kick still in there")
        a1.set_title("linear axis — the transient decaying", fontsize=9)
        c.legend(a1, loc="upper right")

        a2.set_yscale("log")
        self._mlog_a, = a2.plot([], [], color=theme.ACCENT, lw=2.2,
                                label=f"A  slope = −{1/ta:.1f} 1/s")
        self._mlog_b, = a2.plot([], [], color=theme.ORANGE, lw=2.2,
                                label=f"B  slope = −{1/tb:.1f} 1/s")
        a2.set_xlim(0, span)
        a2.set_ylim(1e-4, 1.6)
        a2.set_xlabel("time since the kick (s)")
        a2.set_ylabel("fraction remaining (log)")
        a2.set_title("log axis — the pole IS the slope", fontsize=9)
        c.legend(a2, loc="lower left")
        c.refresh()
        self._frame_mem()

    def _frame_mem(self):
        ta = self.s_ma.value() / 1000.0
        tb = self.s_mb.value() / 1000.0
        if self._mhist:
            t, ya, yb = self._mhist[-1]
        else:
            t, ya, yb = 0.0, 1.0, 1.0

        def line(name, tau, y, colour):
            return (f"<span style='color:{colour}'><b>{name}</b></span> &nbsp; "
                    f"τ = {tau*1000:.0f} ms &nbsp;·&nbsp; pole = "
                    f"−{1/tau:.1f} 1/s &nbsp;·&nbsp; decays at "
                    f"<b>{1/tau:.1f} e-folds per second</b> &nbsp;·&nbsp; "
                    f"e-folds elapsed: <b>{t/tau:.2f}</b> &nbsp;·&nbsp; "
                    f"transient remaining: <b>{y*100:.2f}%</b>")

        self.mem_text.setText(
            ("press <b>kick both</b> to inject a disturbance"
             if not self._mhist else
             f"time since the kick: <b>{t:.2f} s</b>") + "<br>"
            + line("A", ta, ya, theme.ACCENT) + "<br>"
            + line("B", tb, yb, theme.ORANGE))

        ts = [p[0] for p in self._mhist]
        as_ = [p[1] for p in self._mhist]
        bs = [p[2] for p in self._mhist]
        self._mlin_a.set_data(ts, as_)
        self._mlin_b.set_data(ts, bs)
        self._mlog_a.set_data(ts, [max(v, 1e-4) for v in as_])
        self._mlog_b.set_data(ts, [max(v, 1e-4) for v in bs])
        self.c_mem.refresh(layout=False)

    # -- three hats -----------------------------------------------------
    def _redraw_step(self):
        tau = self.s_tau.value() / 1000.0
        k = self.s_k.value() / 10.0
        self.l_tau.setText(f"{tau*1000:.0f} ms")
        self.l_k.setText(f"{k:.1f}")

        g = first_order(k, tau)
        dur = max(6 * tau, 0.05)
        t, y = step_response(g, dur, dur / 900.0)
        self.st_pole.set(f"{-1/tau:.1f} 1/s")
        self.st_efold.set(f"{1/tau:.1f}")
        self.st_63.set(f"{tau*1000:.0f} ms")
        self.st_settle.set(f"{4*tau*1000:.0f} ms")
        self.st_bw.set(f"{1/(2*math.pi*tau):.1f} Hz")

        c = self.c1
        c.clear()
        a1, a2 = c.axes
        a1.plot([x * 1000 for x in t], y, color=theme.ACCENT, lw=2.2)
        a1.axhline(k, color=theme.TEXT_FAINT, lw=1.1, ls="--", label="final K")
        a1.axhline(0.632 * k, color=theme.GOOD, lw=1.0, ls=":", label="63.2%")
        a1.axvline(tau * 1000, color=theme.GOOD, lw=1.0, ls=":")
        a1.plot([0.0, tau * 1000], [0.0, k], color=theme.WARN, lw=1.3, ls="--",
                label="initial slope, extended")
        a1.scatter([tau * 1000], [k], s=28, color=theme.WARN, zorder=6)
        a1.set_xlabel("time (ms)")
        a1.set_ylabel("y")
        a1.set_title("step response", fontsize=9)
        c.legend(a1, loc="lower right")
        _splane(a2, [complex(-1 / tau, 0.0)], lim=max(2.0, 1.6 / tau))
        a2.set_title("s-plane", fontsize=9)
        c.refresh()

    # -- loop rate bench ------------------------------------------------
    def _redraw_lr(self):
        L = self.s_L.value() / 10.0 * 1e-3
        R = self.s_R.value() / 10.0
        J = self.s_J.value() / 1000.0
        b = self.s_b.value() / 100.0
        self.l_L.setText(f"{L*1e3:.1f} mH")
        self.l_R.setText(f"{R:.1f} Ω")
        self.l_J.setText(f"{J:.3f}")
        self.l_b.setText(f"{b:.2f}")

        te, tm = L / R, J / b
        fe, fm = 1 / (2 * math.pi * te), 1 / (2 * math.pi * tm)
        rate_e, rate_m = 15 * fe, 15 * fm
        self.st_te.set(f"{te*1e3:.2f} ms")
        self.st_tm.set(f"{tm*1e3:.0f} ms")
        self.st_fe.set(f"{rate_e/1000:.1f} kHz")
        self.st_fm.set(f"{rate_m:.0f} Hz")
        self.st_sep.set(f"{tm/te:.0f}×")

        self.lr_text.setText(
            f"The winding's transient decays at <b>{1/te:.0f}</b> e-folds per second; "
            f"the joint's at <b>{1/tm:.1f}</b>. After one winding time constant "
            f"(<b>{te*1e3:.2f} ms</b>), its first-order step is 63.2% complete; "
            f"this is not an interval during which new commands are forbidden.<br>"
            f"The joint model's corner is <b>{fm:.1f} Hz</b>. It still responds "
            f"above that frequency, with reduced amplitude and more lag. The displayed "
            f"<b>{rate_e/1000:.1f} kHz</b> inner and <b>{rate_m:.0f} Hz</b> outer "
            f"update rates are design estimates, not mechanical motion rates. "
            f"The <b>{tm/te:.0f}× time-constant separation</b> motivates a cascade: "
            f"a faster current loop inside a slower motion loop, each verified for "
            f"delay, noise and stability.")

        c = self.c_lr
        c.clear()
        a1, a2 = c.axes
        dur = 6 * tm
        t1, y1 = step_response(first_order(1.0, te), dur, dur / 1400.0)
        t2, y2 = step_response(first_order(1.0, tm), dur, dur / 1400.0)
        a1.semilogx([max(v, 1e-6) for v in t1], y1, color=theme.CYAN, lw=2.2,
                    label=f"current  τ={te*1e3:.2f} ms")
        a1.semilogx([max(v, 1e-6) for v in t2], y2, color=theme.ORANGE, lw=2.2,
                    label=f"joint  τ={tm*1e3:.0f} ms")
        a1.axhline(0.632, color=theme.TEXT_FAINT, lw=1.0, ls=":")
        a1.set_xlabel("time (s, log)")
        a1.set_ylabel("response")
        a1.set_title("same step, three decades apart", fontsize=9)
        c.legend(a1, loc="upper left")

        names = ["joint\nbandwidth", "joint\nloop rate", "current\nbandwidth",
                 "current\nloop rate"]
        vals = [fm, rate_m, fe, rate_e]
        cols = [theme.ORANGE, theme.WARN, theme.CYAN, theme.GOOD]
        a2.bar(range(4), vals, color=cols, width=0.6)
        a2.set_yscale("log")
        a2.set_xticks(range(4))
        a2.set_xticklabels(names, fontsize=7)
        a2.set_ylabel("Hz (log)")
        a2.axhline(20000, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a2.text(3.4, 22000, "20 kHz", color=theme.TEXT_FAINT, fontsize=7,
                ha="right")
        a2.set_title("what each layer can usefully run at", fontsize=9)
        c.refresh()


# ==========================================================================
# PAGE -- the pole at the origin
# ==========================================================================

class IntegratorPage(Page):
    TITLE = "The Pole at the Origin"
    SUBTITLE = ("A store with no drain. Its transient never decays — which is "
                "a defect, a design tool, and the reason position control is "
                "second order even when only one thing is moving.")
    SECTION = SECTION
    NOTES = "foundation"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>Everything so far has had a drain.</b> Friction bleeds speed, "
            "resistance bleeds current, conduction bleeds heat — and because the "
            "drain grows with the level, the level settles and the transient "
            "dies. Now delete the drain and keep the store. That single change "
            "moves the pole to exactly s = 0 and produces an object with "
            "properties unlike anything on the last three pages.", "key"))

        # ---- what it is ----------------------------------------------------
        w = Card("what \"no drain\" does to the equation")
        w.add(body("Start from the flywheel and set the friction b to zero:"))
        w.add(math_label(r"J\,\dot\omega = \tau - b\,\omega \;\;\longrightarrow\;\;"
                         r" J\,\dot\omega = \tau", 17))
        w.add(body(
            "There is no longer any term containing ω on the right. <b>The rate "
            "of change no longer depends on the level at all</b> — only on what "
            "you are putting in. Divide through and the transfer function is"))
        w.add(math_label(r"G(s) = \frac{1}{J\,s}\qquad\text{pole at}\qquad s = 0",
                         17))
        w.add(body(
            "and the output is literally the running total of the input:"))
        w.add(math_label(r"\omega(t) = \frac{1}{J}\int_0^t \tau(t')\,dt'", 17))
        w.add(callout(
            "<b>That is why it is called an integrator: its output is the "
            "integral of its input.</b> It does not respond to the input, it "
            "<i>accumulates</i> it. And because nothing removes what has "
            "accumulated, the accumulation is permanent.", "key"))
        w.add(body(
            "<b>Where they physically come from — always the same two "
            "cases:</b><br>"
            "&nbsp;&nbsp;• <b>A store with negligible loss.</b> A flywheel in "
            "good bearings, a frictionless joint, a superconducting coil, a "
            "perfectly insulated mass. Push it once and it keeps going.<br>"
            "&nbsp;&nbsp;• <b>A quantity that is defined as the running total of "
            "another.</b> Position is the running total of velocity. Charge is "
            "the running total of current. Distance travelled is the running "
            "total of speed. <b>These are integrators by definition, not by "
            "accident, and they are the ones that catch people out.</b>",
            dim=True))
        self.add(w)

        # ---- interactive 1: with and without a drain ----------------------
        self.add(hline())
        self.add(title("Interactive — remove the drain and watch what changes"))

        d = Card("the same experiments, on a leaky store and on a perfect one")
        d.add(body(
            "Drag the drain rate <b>a</b> down towards zero and watch the two "
            "panels. The dashed grey trace is the <b>a = 0</b> case, always "
            "shown for comparison.<br><br>"
            "<b>Left — kick it once, then let go</b> (zero-input response). With "
            "a drain the transient decays and the system returns to where it "
            "started; the disturbance leaves no trace. At a = 0 the kick is "
            "<b>held forever</b>: nothing returns it, so the system is "
            "permanently offset by whatever happened to it.<br>"
            "<b>Right — hold a constant input</b> (step response). With a drain "
            "it settles, because the drain grows until it matches the input. At "
            "a = 0 there is nothing to grow, so nothing ever balances the input "
            "and the output <b>ramps without limit</b>.", dim=True))
        self.s_a = slider(0, 200, 40)      # x0.1  1/s
        self.l_a = QLabel()
        d.add_layout(slider_row("drain rate a (1/s)", self.s_a, self.l_a))
        self.st_ipole = Stat("pole", "--", theme.ACCENT)
        self.st_itau = Stat("τ", "--", theme.GOOD)
        self.st_ikick = Stat("kick left after 3 s", "--", theme.VIOLET)
        self.st_istep = Stat("step response", "--", theme.WARN)
        self.st_iclass = Stat("classification", "--", theme.CYAN)
        d.add_layout(stat_row(self.st_ipole, self.st_itau, self.st_ikick,
                              self.st_istep, self.st_iclass))
        self.c_int = MplCanvas(width=7.4, height=3.0, ncols=2)
        d.add(self.c_int)
        self.int_text = _readout()
        d.add(self.int_text)
        self.add(d)
        self.s_a.valueChanged.connect(self._redraw_int)
        self._redraw_int()

        m = Card("marginally stable — the third category, and why it needs one")
        m.add(body(
            (
                "A pole strictly in the left half plane is <b>stable</b>: transients decay. A pole in the right "
                "half plane is <b>unstable</b>: they grow without bound. A pole exactly <i>on</i> the boundary "
                "is neither, and it gets its own name — <b>marginally stable</b>.<br><br>It is not a "
                "technicality. A single integrator has bounded zero-input motion, but a constant input produces "
                "an unbounded ramp. Marginal zero-input stability is not bounded-input bounded-output stability."
                " But it never settles either, and every disturbance it ever receives is still in there, added "
                "up. Two hours of a tiny sensor bias integrates into a large, confident, completely wrong number"
                " — which is exactly what <b>drift</b> is, and why dead reckoning from an accelerometer fails "
                "and gyro bias has to be estimated rather than ignored."
            )))
        m.add(callout(
            "<b>An integrator is the only linear system whose behaviour depends "
            "on your entire history rather than your recent history.</b> That is "
            "the practical difference. A pole at −20 has a transient that is "
            "effectively gone after ~200 ms, so only the recent past is still "
            "visible in the output. A pole at 0 has no transient decay at all: "
            "every disturbance it has ever received is still in there, summed, "
            "and will still be in there in an hour.", "warn"))
        self.add(m)

        # ---- why you want one ----------------------------------------------
        self.add(hline())
        self.add(title("Why you deliberately put one in your controller"))

        r = Card("the reason: a command built from a decaying state cannot hold a "
                 "bias")
        r.add(body(
            "Take a joint holding a position against gravity. Gravity is a "
            "constant disturbance torque — it does not go away.<br><br>"
            "<b>With proportional control only</b>, the command is "
            "u = K<sub>p</sub>·e. To produce the torque that cancels gravity you "
            "need u ≠ 0, and since u is <i>proportional to the error</i>, you "
            "therefore need <b>e ≠ 0</b>. The joint must stay permanently wrong "
            "in order to hold itself up. Raising K<sub>p</sub> shrinks the error "
            "but never removes it, and eventually costs you stability."))
        r.add(callout(
            "<b>An integrator breaks that logic, and it is the only thing that "
            "can.</b> Its output does not depend on the error <i>now</i>; it "
            "depends on the error's whole history. So it can sit at exactly the "
            "torque gravity demands <b>while the error is zero</b> — the "
            "accumulated total stays put because nothing drains it.<br><br>"
            "That is the whole argument for the <b>I</b> term, and it is a direct "
            "consequence of the pole being at the origin. A state that decayed "
            "would let the command sag back towards zero, and the error would "
            "reappear. <b>You need a state whose transient does not decay, precisely "
            "because you need a command that does not sag.</b>", "key"))
        self.add(r)

        i2 = Card("interactive — P alone versus PI, with the integrator's "
                  "internal state shown")
        i2.add(body(
            "A first-order joint, commanded to 1.0. At the marked time a "
            "constant load disturbance is applied — a hand pushing, or gravity "
            "after the arm extends.<br><br>"
            "Watch the <b>right-hand panel</b>: it is the integrator's stored "
            "value — the command it is holding. Before the load arrives it sits "
            "at 1.0, the command needed to hold the target. When the load lands "
            "it climbs by exactly the size of the load and then <b>stops and "
            "stays there</b>, with the error back at zero. <b>That flat line at "
            "a new non-zero value is the entire point</b> — a state that decayed "
            "would sag back and let the error return. Turn K<sub>i</sub> to zero "
            "and watch the joint settle permanently short instead.", dim=True))
        self.s_kp2 = slider(1, 200, 40)     # x0.1
        self.s_ki2 = slider(0, 2000, 80)    # x0.1
        self.s_dist = slider(0, 100, 50)    # x0.01
        self.l_kp2, self.l_ki2, self.l_dist = QLabel(), QLabel(), QLabel()
        i2.add_layout(slider_row("K_p (×0.1)", self.s_kp2, self.l_kp2))
        i2.add_layout(slider_row("K_i (×0.1)", self.s_ki2, self.l_ki2))
        i2.add_layout(slider_row("disturbance", self.s_dist, self.l_dist))
        self.st_sse_p = Stat("final error — P only", "--", theme.BAD)
        self.st_sse_pi = Stat("final error — PI", "--", theme.GOOD)
        self.st_isteady = Stat("integrator settles at", "--", theme.VIOLET)
        self.st_iover = Stat("PI overshoot", "--", theme.WARN)
        i2.add_layout(stat_row(self.st_sse_p, self.st_sse_pi, self.st_isteady,
                               self.st_iover))
        self.c_pi = MplCanvas(width=7.4, height=3.0, ncols=2)
        i2.add(self.c_pi)
        i2.add(body(
            "<b>Now push K<sub>i</sub> up.</b> The error dies sooner and the "
            "response starts to overshoot and ring — because you have added a "
            "second energy store to the loop, and a loop with two stores can "
            "do that. An integrator is not free: it costs you a pole, 90° of "
            "phase lag at every frequency, and the risk of <b>integrator "
            "windup</b> when the actuator saturates and the accumulation keeps "
            "growing against a command that cannot be executed. The PID page "
            "deals with windup properly.", dim=True))
        self.add(i2)
        for s in (self.s_kp2, self.s_ki2, self.s_dist):
            s.valueChanged.connect(self._redraw_pi)
        self._redraw_pi()

        # ---- position out --------------------------------------------------
        self.add(hline())
        self.add(title("Inertia and damping, position out — where the second "
                       "store is hiding"))

        q = Card("\"there is one moving part and one friction. How is that not "
                 "first order?\"")
        q.add(body(
            "This is the question worth being stubborn about, because the answer "
            "is the whole reason position control is harder than speed "
            "control.<br><br>"
            "The mechanism really does have one mass and one damper. But the "
            "order of a system is <b>not</b> the number of parts — it is the "
            "number of quantities that cannot change instantly, i.e. the number "
            "of numbers you must be told before you can predict the future. Apply "
            "the test honestly:"))
        q.add(body(
            "&nbsp;&nbsp;<b>Can the speed ω jump?</b> No — that would need "
            "infinite torque. <b>One store.</b><br>"
            "&nbsp;&nbsp;<b>Can the angle θ jump?</b> Also no — the joint cannot "
            "teleport. θ is the running total of ω, and a running total of a "
            "finite quantity moves smoothly. <b>Two stores.</b>"))
        q.add(callout(
            "<b>The second store is not a spring. It is the integrator you got "
            "for free the moment you decided to watch position instead of "
            "speed.</b><br><br>"
            "Nothing physical was added — you changed which variable you call "
            "the output, and that changed the order. Friction drains ω; "
            "<b>nothing drains θ</b>. So the joint has one leaky store and one "
            "perfect one, and its two poles are exactly where you would now "
            "expect: one at <b>−b/J</b> from the leaky store, and one at "
            "<b>0</b> from the perfect one.", "key"))
        q.add(math_label(r"J\,\ddot\theta + b\,\dot\theta = \tau "
                         r"\;\;\Longrightarrow\;\; G(s) = \frac{1}{s\,(Js+b)}"
                         r"\;\;\Longrightarrow\;\; s = 0,\; -b/J", 16))
        q.add(body(
            "<b>And now the overshoot question answers itself.</b> Close a "
            "proportional position loop. The controller supplies a restoring "
            "torque proportional to the error, so it is <i>acting as the "
            "spring</i>. When the joint reaches the target the error is zero and "
            "the controller's torque is zero — but the mass is still moving, "
            "because its kinetic energy is a store that is not the output "
            "variable. It sails past. <b>Position control of a plain damped "
            "inertia can ring, and speed control of the identical hardware "
            "cannot.</b> Same metal, different output, different order.", dim=True))
        self.add(q)

        i3 = Card("interactive — the same joint, speed out versus position out")
        i3.add(body(
            "One piece of hardware, two choices of output, two different "
            "systems. Change the damping and the loop gain and watch which one "
            "is capable of overshooting.", dim=True))
        self.s_pj = slider(1, 100, 25)      # x0.01 kg m^2
        self.s_pb = slider(1, 200, 40)      # x0.01 N m s
        self.s_pk = slider(1, 400, 100)     # x0.1 position loop gain
        self.l_pj, self.l_pb, self.l_pk = QLabel(), QLabel(), QLabel()
        i3.add_layout(slider_row("inertia J (kg·m²)", self.s_pj, self.l_pj))
        i3.add_layout(slider_row("damping b (N·m·s)", self.s_pb, self.l_pb))
        i3.add_layout(slider_row("position loop K_p (×0.1)", self.s_pk,
                                 self.l_pk))
        self.st_vorder = Stat("speed out", "--", theme.GOOD)
        self.st_porder = Stat("position out", "--", theme.BAD)
        self.st_ppoles = Stat("open-loop poles", "--", theme.ACCENT)
        self.st_pover = Stat("closed-loop overshoot", "--", theme.WARN)
        i3.add_layout(stat_row(self.st_vorder, self.st_porder, self.st_ppoles,
                               self.st_pover))
        self.c_pos = MplCanvas(width=7.4, height=3.0, ncols=2)
        i3.add(self.c_pos)
        self.add(i3)
        for s in (self.s_pj, self.s_pb, self.s_pk):
            s.valueChanged.connect(self._redraw_pos)
        self._redraw_pos()

        sm = Card("where integrators show up, and what each one costs you")
        sm.add(body(
            "<table cellpadding='7'>"
            "<tr><td><b>Integrator</b></td><td><b>Why it is there</b></td>"
            "<td><b>What it costs</b></td></tr>"
            "<tr><td>position, from velocity</td>"
            "<td>definitional — nothing you can remove</td>"
            "<td>every position loop is at least second order</td></tr>"
            "<tr><td>the <b>I</b> in a PID</td>"
            "<td>deliberate: kills steady-state error against constant "
            "disturbances</td>"
            "<td>a pole, 90° of lag, and windup on saturation</td></tr>"
            "<tr><td>a frictionless / low-friction joint</td>"
            "<td>accidental: good bearings, direct drive</td>"
            "<td>it coasts; it will not stop itself</td></tr>"
            "<tr><td>dead reckoning from a rate sensor</td>"
            "<td>you integrated a gyro or an accelerometer</td>"
            "<td><b>drift</b> — bias accumulates without bound and no filter "
            "recovers it without an absolute reference</td></tr>"
            "<tr><td>a charge-storing capacitor with no leakage path</td>"
            "<td>circuit topology</td>"
            "<td>offsets never clear themselves</td></tr>"
            "</table>"))
        sm.add(callout(
            "<b>The one-line summary.</b> A pole in the left half plane has a "
            "transient that decays at a definite rate; a pole at the origin has a "
            "transient that never decays at all. That is a liability "
            "when the physics hands it to you unasked (drift, coasting, position "
            "loops being second order) and it is exactly the tool you want when "
            "you add it on purpose (steady-state error elimination). The skill is "
            "knowing which of the two you are looking at.", "good"))
        self.add(sm)

        self.add(callout(
            "<b>Carry forward.</b> Real part negative → the transient decays. "
            "Real part zero → it is held forever. Real part positive → it grows. "
            "Those are the only three things the horizontal axis can say. Next "
            "page moves to frequency, and after that the vertical axis finally "
            "gets an explanation.", "good"))

        self.finish()

    # ------------------------------------------------------------------
    def _redraw_int(self):
        a = self.s_a.value() / 10.0
        self.l_a.setText(f"{a:.1f} 1/s")
        dur, n = 3.0, 700
        ts = [dur * i / n for i in range(n + 1)]

        # zero-input response after a unit kick
        kick = [math.exp(-a * t) for t in ts]
        kick0 = [1.0 for _ in ts]
        # step response
        if a > 1e-9:
            step = [(1 - math.exp(-a * t)) / a for t in ts]
        else:
            step = list(ts)
        step0 = list(ts)

        self.st_ipole.set("0.0 1/s" if a < 1e-9 else f"−{a:.1f} 1/s")
        self.st_itau.set("∞" if a < 1e-9 else f"{1000/a:.0f} ms")
        self.st_ikick.set(f"{kick[-1]*100:.1f}%")
        self.st_ikick.set_color(theme.BAD if kick[-1] > 0.9 else theme.GOOD)
        self.st_istep.set("ramps forever" if a < 0.05 else "settles")
        self.st_istep.set_color(theme.BAD if a < 0.05 else theme.GOOD)
        self.st_iclass.set("marginally stable" if a < 1e-9 else "stable")
        self.st_iclass.set_color(theme.WARN if a < 1e-9 else theme.GOOD)

        self.int_text.setText(
            ("<b>a = 0. There is no drain.</b> The kick is held at 100% forever "
             "— the system is permanently offset by something that happened "
             "three seconds ago and will still be offset by it tomorrow. And "
             "with a constant input the output ramps without limit, because "
             "nothing ever grows to balance the input. The pole sits exactly on "
             "the boundary: <b>marginally stable</b>."
             if a < 1e-9 else
             f"<b>a = {a:.1f} 1/s.</b> The drain gives a time constant of "
             f"{1000/a:.0f} ms, so three seconds after the kick "
             f"{kick[-1]*100:.1f}% of it is left — the disturbance is on its way "
             f"out. Under a constant input the drain grows until it matches the "
             f"input at a level of {1/a:.2f}, and there the output stops. "
             f"<b>Both of those only happen because a ≠ 0.</b>"))

        c = self.c_int
        c.clear()
        a1, a2 = c.axes
        a1.plot(ts, kick0, color=theme.TEXT_FAINT, lw=1.4, ls="--",
                label="a = 0 (no drain)")
        a1.plot(ts, kick, color=theme.ACCENT, lw=2.3, label=f"a = {a:.1f}")
        a1.axhline(0, color=theme.BORDER, lw=0.9)
        a1.set_ylim(-0.05, 1.15)
        a1.set_xlabel("time (s)")
        a1.set_ylabel("what is left of the kick")
        a1.set_title("kicked once, then left alone", fontsize=9)
        c.legend(a1, loc="center right")

        a2.plot(ts, step0, color=theme.TEXT_FAINT, lw=1.4, ls="--",
                label="a = 0 (ramps)")
        a2.plot(ts, step, color=theme.ACCENT, lw=2.3, label=f"a = {a:.1f}")
        if a > 1e-9:
            a2.axhline(1 / a, color=theme.GOOD, lw=1.0, ls=":",
                       label="settles here")
        a2.set_ylim(0, max(3.2, min(1 / a * 1.6, 6.0) if a > 1e-9 else 3.2))
        a2.set_xlabel("time (s)")
        a2.set_ylabel("output")
        a2.set_title("constant input held from t = 0", fontsize=9)
        c.legend(a2, loc="upper left")
        c.refresh()

    # ------------------------------------------------------------------
    def _redraw_pi(self):
        kp = self.s_kp2.value() / 10.0
        ki = self.s_ki2.value() / 10.0
        dmag = self.s_dist.value() / 100.0
        self.l_kp2.setText(f"{kp:.1f}")
        self.l_ki2.setText(f"{ki:.1f}")
        self.l_dist.setText(f"{dmag:.2f}")

        tau_p, kdc = 0.15, 1.0
        dur, dt = 4.0, 0.001
        t_d = 1.5
        n = int(dur / dt)

        def run(use_i):
            y = 0.0
            xi = 0.0
            ts, ys, xs = [], [], []
            for k in range(n):
                t = k * dt
                e = 1.0 - y
                if use_i:
                    xi += e * dt
                u = kp * e + (ki * xi if use_i else 0.0)
                # a LOAD: it drags the output down, so the controller has to
                # push harder to stay on target
                d = -dmag if t >= t_d else 0.0
                y += dt * (kdc * (u + d) - y) / tau_p
                ts.append(t)
                ys.append(y)
                xs.append(ki * xi if use_i else 0.0)
            return ts, ys, xs

        ts, y_p, _ = run(False)
        _, y_pi, x_pi = run(True)

        self.st_sse_p.set(f"{(1-y_p[-1])*100:+.1f}%")
        self.st_sse_pi.set(f"{(1-y_pi[-1])*100:+.1f}%")
        self.st_isteady.set(f"{x_pi[-1]:.3f}")
        peak = max(y_pi)
        self.st_iover.set(f"{max(peak-1.0, 0.0)*100:.0f}%")
        self.st_iover.set_color(theme.GOOD if peak < 1.02 else theme.WARN)

        c = self.c_pi
        c.clear()
        a1, a2 = c.axes
        a1.axhline(1.0, color=theme.TEXT_FAINT, lw=1.0, ls="--",
                   label="commanded")
        a1.plot(ts, y_p, color=theme.BAD, lw=2.0, label="P only")
        a1.plot(ts, y_pi, color=theme.GOOD, lw=2.0, label="PI")
        a1.axvline(t_d, color=theme.WARN, lw=1.0, ls=":")
        a1.text(t_d, 0.08, " disturbance on", color=theme.WARN, fontsize=7)
        a1.set_xlabel("time (s)")
        a1.set_ylabel("joint position")
        a1.set_title("P leaves a permanent error; PI does not", fontsize=9)
        c.legend(a1, loc="lower right")

        a2.plot(ts, x_pi, color=theme.VIOLET, lw=2.2,
                label="integrator output")
        a2.axhline(1.0, color=theme.TEXT_FAINT, lw=1.1, ls=":",
                   label="needed with no load")
        a2.axhline(1.0 + dmag, color=theme.WARN, lw=1.2, ls="--",
                   label="needed once the load is on")
        a2.axvline(t_d, color=theme.WARN, lw=1.0, ls=":")
        a2.set_xlabel("time (s)")
        a2.set_ylabel("accumulated command")
        a2.set_title("the state that does not decay", fontsize=9)
        c.legend(a2, loc="lower right")
        c.refresh()

    # ------------------------------------------------------------------
    def _redraw_pos(self):
        J = self.s_pj.value() / 100.0
        b = self.s_pb.value() / 100.0
        kp = self.s_pk.value() / 10.0
        self.l_pj.setText(f"{J:.2f}")
        self.l_pb.setText(f"{b:.2f}")
        self.l_pk.setText(f"{kp:.1f}")

        vel = TF([1.0], [J, b])                 # torque -> speed
        pos = TF([1.0], [J, b, 0.0])            # torque -> position
        cl = (pos * kp).feedback()

        self.st_vorder.set(f"order {vel.order()}")
        self.st_porder.set(f"order {pos.order()}")
        self.st_ppoles.set(f"0, −{b/J:.1f}")
        dur = max(8 * J / b, 2.0)
        tv, yv = step_response(vel, dur, dur / 900.0)
        tc, yc = step_response(cl, dur, dur / 900.0)
        peak = max(yc) if yc else 1.0
        self.st_pover.set(f"{max(peak-1.0, 0.0)*100:.0f}%")
        self.st_pover.set_color(theme.GOOD if peak <= 1.005 else theme.BAD)

        c = self.c_pos
        c.clear()
        a1, a2 = c.axes
        scale = max(yv) or 1.0
        a1.plot(tv, [v / scale for v in yv], color=theme.GOOD, lw=2.2,
                label="speed out — 1 store")
        tp, yp = step_response(pos, dur, dur / 900.0)
        sp = max(yp) or 1.0
        a1.plot(tp, [v / sp for v in yp], color=theme.BAD, lw=2.2,
                label="position out — 2 stores")
        a1.set_xlabel("time (s)")
        a1.set_ylabel("output (normalised)")
        a1.set_title("open loop, constant torque", fontsize=9)
        c.legend(a1, loc="upper left")

        a2.plot(tc, yc, color=theme.ACCENT, lw=2.2, label="position, P loop")
        a2.axhline(1.0, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a2.set_xlabel("time (s)")
        a2.set_ylabel("position")
        a2.set_title("closed position loop — it CAN overshoot", fontsize=9)
        c.legend(a2, loc="lower right")
        c.refresh()


# ==========================================================================
# PAGE -- first order in frequency
# ==========================================================================

class FirstOrderFreqPage(Page):
    TITLE = "First Order in Frequency"
    SUBTITLE = ((
                    "Stop stepping it and start shaking it. Where the corner, the −3 dB point and the 90° ceiling "
                    "come from — and the stability result for a delay-free first-order low-pass under positive "
                    "proportional negative feedback."
                ))
    SECTION = SECTION
    NOTES = "foundation"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>A frequency response is one experiment repeated at many "
            "speeds.</b> Wiggle the input back and forth at some rate; measure "
            "how big the output wiggle is and how far behind it arrives. Two "
            "numbers per frequency: <b>magnitude</b> and <b>phase</b>. Plot "
            "them against frequency and you have a Bode plot. Nothing more "
            "abstract than that is happening.", "key"))

        # ---- why jw -------------------------------------------------------
        w = Card("why s becomes jω — nothing is being thrown away")
        w.add(body(
            "The variable s is not a number you pick; it is a placeholder for "
            "the kind of signal you are feeding in. Write it out:"))
        w.add(math_label(r"e^{st} \;=\; e^{(\sigma + j\omega)t} \;=\; "
                         r"e^{\sigma t}\,\left[\cos\omega t + j\sin\omega t"
                         r"\right]", 16))
        w.add(body(
            "&nbsp;&nbsp;<b>e<sup>σt</sup></b> — the first factor, set by the "
            "<b>real part σ</b>, is an <b>envelope</b>: the signal growing or "
            "shrinking.<br>"
            "&nbsp;&nbsp;<b>[cos ωt + j sin ωt]</b> — the bracket, set by the "
            "<b>imaginary part ω</b>, is the <b>wiggle</b>: how fast it goes "
            "back and forth."))
        w.add(callout(
            "<b>So setting σ = 0 is not deleting anything — it is choosing the "
            "test signal.</b> σ = 0 means an envelope of e<sup>0</sup> = 1: a "
            "sine that neither grows nor dies, going forever at constant "
            "amplitude. That is exactly the signal you want for this "
            "experiment, because \"frequency response\" means <i>steady-state</i> "
            "response — you shake the thing until every transient has drained "
            "away and only the forced wiggle is left, and then you measure. A "
            "test sine that was itself dying would contaminate the "
            "measurement.<br><br>"
            "So <b>s = jω</b> is the sentence \"drive it with a pure, "
            "everlasting sine at ω rad/s\". G(jω) is the answer.", "key"))
        w.add(body(
            "<b>A distinction worth nailing down, because it trips people.</b> "
            "The <b>pole</b> is at s = −1/τ, on the real axis: that is where the "
            "system's <i>own, unforced</i> motion lives, and it describes how a "
            "disturbance drains away. The <b>test point</b> s = jω is on the "
            "imaginary axis: that is where <i>you</i> are poking it. They are "
            "different points on the same map. A first-order system has no pole "
            "off the real axis, but you can still shake it at any frequency you "
            "like.", dim=True))
        w.add(math_label(r"G(j\omega) = \frac{K}{1 + j\omega\tau}, \qquad "
                         r"|G| = \frac{K}{\sqrt{1+(\omega\tau)^2}}, \qquad "
                         r"\angle G = -\arctan(\omega\tau)", 16))
        self.add(w)

        # ---- the shaker ---------------------------------------------------
        self.add(hline())
        self.add(title("Interactive — the shaker"))

        sh = Card("drive it with a sine and read the two numbers off directly")
        sh.add(body(
            "The top plot is the actual experiment: your drive (grey) and the "
            "system's answer (blue), after transients have died. Watch <b>two "
            "things shrink as you speed up</b> — the answer gets smaller, and "
            "it arrives later. The bottom plots are the same two measurements "
            "collected across all frequencies, with a marker showing where you "
            "currently are. <b>The Bode plot is not a new object; it is the "
            "logbook of this one experiment.</b>", dim=True))
        self.s_f = slider(-20, 30, 0)      # decades x10 relative to corner
        self.s_ftau = slider(5, 500, 100)  # ms
        self.l_f, self.l_ftau = QLabel(), QLabel()
        sh.add_layout(slider_row("drive frequency", self.s_f, self.l_f))
        sh.add_layout(slider_row("plant τ (ms)", self.s_ftau, self.l_ftau))
        self.st_ratio = Stat("amplitude out/in", "--", theme.ACCENT)
        self.st_db = Stat("in dB", "--", theme.VIOLET)
        self.st_ph = Stat("phase lag", "--", theme.WARN)
        self.st_cyc = Stat("of a cycle", "--", theme.PINK)
        self.st_lagms = Stat("late by", "--", theme.CYAN)
        sh.add_layout(stat_row(self.st_ratio, self.st_db, self.st_ph,
                               self.st_cyc, self.st_lagms))
        self.c_shake = MplCanvas(width=7.4, height=5.4, nrows=2, ncols=2)
        sh.add(self.c_shake)
        self.shake_text = _readout()
        sh.add(self.shake_text)
        self.add(sh)
        self.s_ftau.valueChanged.connect(self._build_shake)
        self.s_f.valueChanged.connect(self._frame_shake)
        self._build_shake()

        # ---- dB -----------------------------------------------------------
        d = Card("dB, since it is only a unit")
        d.add(body(
            "A decibel is a <b>logarithmic way of writing a ratio</b>, invented "
            "so that cascaded blocks add instead of multiply. For an amplitude "
            "ratio:"))
        d.add(math_label(r"\text{dB} = 20\,\log_{10}\!\left(\frac{|out|}{|in|}"
                         r"\right)", 16))
        d.add(body(
            "<table cellpadding='6'>"
            "<tr><td><b>ratio</b></td><td>1.0</td><td>0.707</td><td>0.5</td>"
            "<td>0.1</td><td>0.01</td></tr>"
            "<tr><td><b>dB</b></td><td>0</td><td><b>−3</b></td><td>−6</td>"
            "<td>−20</td><td>−40</td></tr>"
            "</table>"))
        d.add(callout(
            "<b>Why −3 dB is the one that got a name.</b> Power goes as "
            "amplitude squared, so an amplitude ratio of 1/√2 = 0.707 is a "
            "<b>power</b> ratio of exactly 0.5. In power dB, 10 log₁₀(0.5) = "
            "−3.01. <b>\"Half the power gets through\"</b> means: of the "
            "energy you are pumping into the input at this frequency, half is "
            "coming out the other end — the rest is not appearing at the output "
            "because the store will not move that fast. It is a conventional "
            "line drawn on a smooth curve, but it is a sensible one, and "
            "everyone draws it in the same place.", "key"))
        d.add(body(
            (
                "<b>Does −3 dB define bandwidth for every system, or just first order?</b> The <i>definition</i>"
                " — \"the frequency where the magnitude has fallen 3 dB below its low-frequency value\" — is the "
                "convention used here for a stable low-pass response with finite, nonzero DC gain. Band-pass "
                "systems, integrators and other responses need a different stated reference; a datasheet must "
                "specify its convention. What is <i>not</i> general is the formula: <b>ω<sub>bw</sub> = 1/τ "
                "holds only for a single pole.</b> A second-order system's −3 dB point depends on both "
                "ω<sub>n</sub> and ζ, and a resonant one can be <i>above</i> 0 dB before it falls — which is the"
                " next page's problem."
            ), dim=True))
        self.add(d)

        # ---- roll-off and phase, physically -------------------------------
        r = Card("−20 dB/decade and −90°, physically")
        r.add(body(
            "<b>The roll-off.</b> Past the corner, a factor of 10 in frequency "
            "costs a factor of 10 in amplitude — that is what −20 dB/decade "
            "means. Physically: the store cannot keep up. Shake a coil's current "
            "twice as fast and the inductance opposes the change twice as hard, "
            "so half as much current gets through. The store is a "
            "\"can't-change-that-fast\" wall, and the harder you push the more "
            "it blocks — in exact proportion. Every single-store low-pass does "
            "this, at the same −20 dB/decade, for the same reason: an RC filter, "
            "an RL winding, a mass with damping, a thermal mass."))
        r.add(body(
            "<b>The phase.</b> Push the joint back and forth <i>slowly</i> with "
            "a sinusoidal torque and the speed follows you almost exactly. At "
            "low speed the friction term bω dominates — and friction has no "
            "memory, it depends only on the velocity right now, not on its "
            "history — so there is nothing to lag with and the output is in step "
            "(0°).<br><br>"
            "Now push <i>fast</i>. The friction term never gets a chance to "
            "matter; the inertia Jω̇ dominates, and speed becomes the "
            "<b>integral</b> of your push. The integral of a sine peaks a "
            "<b>quarter cycle</b> after the sine does — that is 90°, and it "
            "cannot get worse, because there is only one integration to do. "
            "<b>One store = one integration = at most a quarter cycle of "
            "lag.</b>"))
        r.add(body(
            "<b>And yes, that depends on what the controller is doing.</b> What "
            "is described above is the bare plant, which is what you feel under "
            "torque control or with the drive disabled. Close a stiff position "
            "or impedance loop around it and you are no longer feeling J and b "
            "— you are feeling the <i>rendered</i> impedance the controller is "
            "synthesising, with its own corner and its own phase. That is the "
            "entire point of the impedance-control pages: the controller gets to "
            "choose the dynamics the world touches.", dim=True))
        self.add(r)

        # ---- the quarter cycle --------------------------------------------
        self.add(hline())
        self.add(title("The quarter cycle you are short by — and how to lose it"))

        q = Card("why one store can never be made to oscillate")
        q.add(body(
            "To make something oscillate with feedback you have to push it in "
            "<b>exactly the wrong phase</b> — your correction must arrive as the "
            "error is already heading back the other way, so that it <i>adds</i> "
            "to the error instead of opposing it. That is a <b>half</b> cycle "
            "of lag: 180°. At that point the minus sign in negative feedback has "
            "been cancelled by the delay, and the loop is positively feeding "
            "itself."))
        q.add(callout(
            "<b>One energy store can only ever supply 90°. You are a quarter "
            "cycle short of the half cycle that would flip the feedback, and no "
            "amount of gain manufactures phase</b> — gain scales the signal, it "
            "does not move it in time.<br><br>"
            "Therefore: a first-order plant with proportional feedback is stable "
            "at <b>every</b> gain. Infinite gain margin, provably. The "
            "closed-loop pole sits at −(1 + K·K<sub>p</sub>)/τ and only ever "
            "moves further left — faster, with less steady-state error, and "
            "never unstable. Enjoy it; it is the only plant in this tutor that "
            "behaves.", "key"))
        self.add(q)

        i2 = Card("interactive — try to destabilise it, then cheat with delay")
        i2.add(body(
            "Turn the gain up as far as it goes: the phase curve never reaches "
            "−180°, so there is nothing to cross and no critical gain to find. "
            "<b>Now add transport delay.</b> Delay has unit magnitude and "
            "unbounded phase lag — it is pure phase loss, exactly as the "
            "real-time page said — so it will happily sell you the missing "
            "quarter cycle, and the guarantee evaporates.<br><br>"
            "That is the honest statement of the theorem: <i>a first-order plant "
            "cannot be destabilised by proportional feedback</i> assumes there "
            "is no delay and no second store. On a real robot both assumptions "
            "are things you have to earn.", dim=True))
        self.s_kp = slider(1, 400, 20)      # x0.1
        self.s_del = slider(0, 200, 0)      # x0.1 ms
        self.l_kp, self.l_del = QLabel(), QLabel()
        i2.add_layout(slider_row("loop gain K_p (×0.1)", self.s_kp, self.l_kp))
        i2.add_layout(slider_row("transport delay (ms)", self.s_del, self.l_del))
        self.st_clp = Stat("closed-loop pole", "--", theme.ACCENT)
        self.st_ctau = Stat("closed-loop τ", "--", theme.GOOD)
        self.st_sse = Stat("steady-state error", "--", theme.WARN)
        self.st_pm = Stat("phase margin", "--", theme.CYAN)
        self.st_crit = Stat("gain that destabilises", "--", theme.BAD)
        i2.add_layout(stat_row(self.st_clp, self.st_ctau, self.st_sse,
                               self.st_pm, self.st_crit))
        self.c2 = MplCanvas(width=7.4, height=3.4, nrows=2)
        i2.add(self.c2)
        self.add(i2)
        for s in (self.s_kp, self.s_del, self.s_ftau):
            s.valueChanged.connect(self._redraw_loop)
        self._redraw_loop()

        self.add(callout(
            (
                "<b>Carry forward.</b> For H(s) = K/(1+sτ<sub>c</sub>), angular bandwidth ω<sub>bw</sub> = "
                "1/τ<sub>c</sub> = |p| in rad/s; bandwidth f<sub>bw</sub> = 1/(2πτ<sub>c</sub>) in Hz. Time "
                "constant τ<sub>c</sub> is in seconds. Beyond it, −20 dB/decade and a phase heading for −90° and"
                " stopping. That stop is a stability guarantee, and it is bought by having exactly one place to "
                "put energy. Next page: what the imaginary axis is, and what a second place to put energy does "
                "to all of this."
            ), "good"))

        self.finish()

    # ------------------------------------------------------------------
    def _build_shake(self):
        """Redrawn only when tau changes -- the Bode curves live here."""
        tau = self.s_ftau.value() / 1000.0
        wc = 1.0 / tau
        self.l_ftau.setText(f"{tau*1000:.0f} ms")
        g = first_order(1.0, tau)

        c = self.c_shake
        c.clear()
        a_t, a_pz, a_m, a_p = c.axes

        self._sh_u, = a_t.plot([], [], color=theme.TEXT_FAINT, lw=1.6, ls="--",
                               label="drive in")
        self._sh_y, = a_t.plot([], [], color=theme.ACCENT, lw=2.4,
                               label="response out")
        self._sh_arrow, = a_t.plot([], [], color=theme.WARN, lw=1.6,
                                   marker="|", ms=8)
        self._sh_lag = a_t.text(0, 0, "", color=theme.WARN, fontsize=7.5,
                                ha="center")
        a_t.axhline(0, color=theme.BORDER, lw=0.9)
        a_t.set_ylim(-1.35, 1.45)
        a_t.set_xlabel("time (ms)")
        a_t.set_ylabel("amplitude")
        a_t.set_title("the experiment: shake it, watch the answer", fontsize=9)
        c.legend(a_t, loc="lower right")

        self._sh_lim = 3.0 * wc
        _splane(a_pz, [complex(-wc, 0.0)], lim=self._sh_lim)
        self._sh_pz, = a_pz.plot([], [], marker="o", ms=7, ls="none",
                                 color=theme.WARN, zorder=6,
                                 label="s = jω  (you)")
        self._sh_off = a_pz.text(0.5, 0.02, "", transform=a_pz.transAxes,
                                 ha="center", color=theme.WARN, fontsize=7)
        a_pz.set_title("pole (blue) vs test point (amber)", fontsize=9)
        c.legend(a_pz, loc="lower left")

        ws = log_freqs(wc / 1000.0, wc * 1000.0, 320)
        _, mags, phs = bode(g, ws)
        a_m.semilogx(ws, mags, color=theme.ACCENT, lw=2.0)
        a_m.semilogx([wc, ws[-1]], [0.0, -60.0], color=theme.TEXT_FAINT,
                     lw=1.1, ls=":", label="−20 dB/decade")
        a_m.axhline(-3.01, color=theme.GOOD, lw=1.0, ls="--", label="−3 dB")
        a_m.axvline(wc, color=theme.VIOLET, lw=1.2, ls=":", label="corner 1/τ")
        self._sh_mk, = a_m.plot([], [], marker="o", ms=7, ls="none",
                                color=theme.WARN, zorder=6)
        a_m.set_ylim(-45, 8)
        a_m.set_ylabel("|G| (dB)")
        a_m.set_xlabel("ω (rad/s)")
        c.legend(a_m, loc="lower left")

        a_p.semilogx(ws, phs, color=theme.ACCENT, lw=2.0)
        a_p.axhline(-45, color=theme.GOOD, lw=1.0, ls="--",
                    label="−45° at corner")
        a_p.axhline(-90, color=theme.WARN, lw=1.0, ls=":", label="−90° ceiling")
        a_p.axhline(-180, color=theme.BAD, lw=1.0, ls=":",
                    label="−180°: unreachable")
        a_p.axvline(wc, color=theme.VIOLET, lw=1.2, ls=":")
        self._sh_pk, = a_p.plot([], [], marker="o", ms=7, ls="none",
                                color=theme.WARN, zorder=6)
        a_p.set_ylim(-195, 10)
        a_p.set_ylabel("phase (deg)")
        a_p.set_xlabel("ω (rad/s)")
        c.legend(a_p, loc="lower left")
        c.refresh()
        self._frame_shake()

    def _frame_shake(self):
        tau = self.s_ftau.value() / 1000.0
        wc = 1.0 / tau                                   # corner, rad/s
        w = wc * (10 ** (self.s_f.value() / 10.0))       # decades from corner
        self.l_f.setText(f"{w/(2*math.pi):.2f} Hz")

        g = first_order(1.0, tau)
        resp = g.response(w)
        mag, ph = abs(resp), math.degrees(math.atan2(resp.imag, resp.real))
        db = 20 * math.log10(max(mag, 1e-12))
        self.st_ratio.set(f"{mag:.3f}")
        self.st_db.set(f"{db:+.1f} dB")
        self.st_ph.set(f"{ph:.1f}°")
        self.st_cyc.set(f"{abs(ph)/360:.3f}")
        self.st_lagms.set(f"{abs(ph)/360*(2*math.pi/w)*1000:.1f} ms")

        at_corner = abs(self.s_f.value()) <= 1
        self.shake_text.setText(
            ((
                 "<b>You are at the corner.</b> ω = 1/τ, magnitude K/√2 = 0.707 (−3.01 dB), phase exactly −45°. "
                 "Half the power through, half a quarter-cycle of lag. The pole is p = −1/τ<sub>c</sub>; its "
                 "magnitude equals this model’s angular bandwidth. The time constant is its reciprocal, not a "
                 "frequency."
             )
             if at_corner else
             ("<b>Below the corner.</b> The store has plenty of time to keep "
              "up, so the output tracks the input nearly full-size and nearly "
              "in step. This is the region where the plant does what you ask."
              if self.s_f.value() < 0 else
              "<b>Above the corner.</b> You are asking the store to change "
              "faster than it can, so most of your drive never reaches the "
              "output and what does arrive is late. Commands up here are "
              "wasted effort.")))

        c = self.c_shake
        a_t, a_pz, a_m, a_p = c.axes

        # -- the experiment ------------------------------------------------
        ncyc = 3.0
        T = 2 * math.pi / w
        ts = [i * ncyc * T / 600.0 for i in range(601)]
        tms = [t * 1000 for t in ts]
        self._sh_u.set_data(tms, [math.sin(w * t) for t in ts])
        self._sh_y.set_data(
            tms, [mag * math.sin(w * t + math.radians(ph)) for t in ts])
        t_pk_in = (0.25 * T) * 1000
        t_pk_out = (0.25 * T - math.radians(ph) / w) * 1000
        self._sh_arrow.set_data([t_pk_in, t_pk_out], [1.12, 1.12])
        self._sh_lag.set_position(((t_pk_in + t_pk_out) / 2, 1.19))
        self._sh_lag.set_text(f"peak arrives {abs(ph):.0f}° later")
        a_t.set_xlim(0, ncyc * T * 1000)

        # -- where you are poking, vs where the pole is --------------------
        edge = self._sh_lim * 0.9
        wm = min(w, edge)
        self._sh_pz.set_data([0.0, 0.0], [wm, -wm])
        self._sh_off.set_text("test point is off the top of this view"
                              if w > edge else "")

        # -- markers on the Bode plots -------------------------------------
        self._sh_mk.set_data([w], [db])
        self._sh_pk.set_data([w], [ph])
        c.refresh(layout=False)

    # ------------------------------------------------------------------
    def _redraw_loop(self):
        tau = self.s_ftau.value() / 1000.0
        kp = self.s_kp.value() / 10.0
        td = self.s_del.value() / 10.0 * 1e-3
        self.l_kp.setText(f"{kp:.1f}")
        self.l_del.setText(f"{td*1000:.1f} ms")

        plant = first_order(1.0, tau)
        loop = plant * kp
        cl = loop.feedback()
        p = cl.poles()[0]
        tau_cl = -1.0 / p.real if p.real < 0 else math.inf
        dc = cl.dc_gain()
        self.st_clp.set(f"{p.real:.0f} 1/s")
        self.st_ctau.set(f"{tau_cl*1000:.1f} ms")
        self.st_sse.set(f"{(1-dc)*100:.1f}%")

        m = margins_with_delay(loop, td) if td > 0 else margins(loop)
        pm = m.phase_margin_deg
        self.st_pm.set("∞" if not math.isfinite(pm) else f"{pm:.0f}°")
        self.st_pm.set_color(theme.GOOD if (not math.isfinite(pm) or pm > 30)
                             else (theme.WARN if pm > 0 else theme.BAD))
        if td > 0:
            self.st_crit.set("delay found it")
            self.st_crit.set_color(theme.BAD if pm < 45 else theme.WARN)
        else:
            crit = critical_gain(plant)
            self.st_crit.set("none" if math.isinf(crit) else f"{crit:.1f}")
            self.st_crit.set_color(theme.GOOD if math.isinf(crit) else theme.BAD)

        c = self.c2
        c.clear()
        a1, a2 = c.axes
        dur = max(6 * tau, 0.05)
        t, y = step_response(cl, dur, dur / 900.0)
        a1.plot([x * 1000 for x in t], y, color=theme.GOOD, lw=2.2,
                label="closed loop")
        t0, y0 = step_response(plant, dur, dur / 900.0)
        a1.plot([x * 1000 for x in t0], y0, color=theme.TEXT_FAINT, lw=1.3,
                ls="--", label="open loop")
        a1.axhline(1.0, color=theme.TEXT_FAINT, lw=1.0, ls=":")
        a1.set_xlabel("time (ms)")
        a1.set_ylabel("y")
        a1.set_title("closed-loop step  (delay not simulated here — see phase)",
                     fontsize=8.5)
        c.legend(a1, loc="lower right")

        ws = log_freqs(1.0 / tau / 100.0, 1.0 / tau * 3000.0, 300)
        _, _, ph = bode(loop, ws)
        ph_d = [p0 - math.degrees(wi * td) for p0, wi in zip(ph, ws)]
        a2.semilogx(ws, ph, color=theme.ACCENT, lw=2.0, label="plant alone")
        if td > 0:
            a2.semilogx(ws, ph_d, color=theme.BAD, lw=2.0,
                        label="plant + delay")
        a2.axhline(-180, color=theme.BAD, lw=1.2, ls=":",
                   label="−180°: the flip point")
        a2.axhline(-90, color=theme.WARN, lw=1.0, ls="--",
                   label="−90° one-store ceiling")
        if m.wgc > 0:
            a2.axvline(m.wgc, color=theme.GOOD, lw=1.0, ls=":",
                       label="gain crossover")
        a2.set_ylim(-300, 5)
        a2.set_xlabel("ω (rad/s)")
        a2.set_ylabel("loop phase (deg)")
        c.legend(a2, loc="lower left")
        c.refresh()


# ==========================================================================
# PAGE -- the s-plane and what imaginary means
# ==========================================================================

class SPlanePage(Page):
    TITLE = "The s-Plane & Imaginary Numbers"
    SUBTITLE = ("What j physically is, why a first-order pole sits flat on the "
                "real axis, and what a second energy store does to lift it "
                "off.")
    SECTION = SECTION
    NOTES = "foundation"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>The s-plane has two axes because a motion can do two things at "
            "once: die away, and wiggle while doing it.</b> Horizontal = how "
            "fast it dies. Vertical = how fast it wiggles. A pole is one point "
            "saying \"this system contains a motion that decays at <i>this</i> "
            "rate while turning at <i>that</i> one\". Everything below is "
            "earning those two sentences.", "key"))

        # ---- what j is ----------------------------------------------------
        j = Card("what the imaginary part physically is — 90 seconds")
        j.add(body(
            "Forget \"imaginary\", which is a bad name for a real thing. Ask "
            "instead what multiplying does to a number on a line:<br><br>"
            "&nbsp;&nbsp;• Multiplying by <b>2</b> <i>stretches</i>.<br>"
            "&nbsp;&nbsp;• Multiplying by <b>−1</b> <i>turns it 180°</i> — it "
            "points the other way.<br>"
            "&nbsp;&nbsp;• So what turns it <b>90°</b>? Something you can apply "
            "<i>twice</i> to get a 180° flip. Call it j. Then j·j = −1, which is "
            "the definition you were given in school, arrived at from the "
            "geometry instead of the other way round."))
        j.add(callout(
            "<b>j is a quarter turn.</b> Real numbers scale; j rotates. A "
            "complex number is therefore \"scale <i>and</i> turn\", and "
            "e<sup>jωt</sup> means \"keep turning, at ω radians per second\" — "
            "a point going round a circle. Its shadow on the real axis, as it "
            "goes round, traces a cosine.<br><br>"
            "That is the connection you need: <b>a rotation and an oscillation "
            "are the same object seen from two directions.</b> A sine is not "
            "fundamentally wavy; it is a circle viewed from the side.", "key"))
        j.add(body(
            "And the physical punchline: <b>rotation is what two things trading "
            "back and forth looks like.</b> As the phasor turns, its horizontal "
            "component shrinks while its vertical one grows, then back. Two "
            "quantities, out of step by a quarter cycle, endlessly handing to "
            "each other while their sum stays put. That is exactly what a spring "
            "and a mass do with energy — which is why <b>a system needs two "
            "stores before its pole can have an imaginary part</b>. One store "
            "has nobody to trade with, so there is nothing to rotate, so the "
            "pole lies flat on the real axis. It can only decay.", dim=True))
        self.add(j)

        # ---- what is rotating ----------------------------------------------
        rot = Card("\"rotating about what axis?\" — the question everyone asks, "
                   "and the answer nobody says out loud")
        rot.add(callout(
            "<b>Nothing in the machine is spinning. The rotation does not happen "
            "in physical space at all — it happens in <i>state space</i>.</b>"
            "<br><br>"
            "The mass on a spring slides back and forth along a straight line. "
            "There is no axis, no shaft, nothing turning. But plot the system's "
            "two stored quantities against each other — <b>position on one axis, "
            "velocity on the other</b> — and the point representing \"the state "
            "of the system right now\" goes round and round that plane. "
            "<i>That</i> is the rotation, and it is the only rotation there "
            "is.", "key"))
        rot.add(body(
            "Follow one cycle of a mass on a spring and watch the pair of "
            "numbers:<br>"
            "&nbsp;&nbsp;• fully compressed — <b>position maximal, velocity "
            "zero</b>. All the energy is in the spring.<br>"
            "&nbsp;&nbsp;• passing through the middle — <b>position zero, "
            "velocity maximal</b>. All the energy is in the mass.<br>"
            "&nbsp;&nbsp;• fully stretched — position maximal the other way, "
            "velocity zero again.<br><br>"
            "Two numbers, each maximal when the other is zero, taking turns — "
            "which is precisely what the x and y coordinates of a point going "
            "round a circle do. <b>The quarter-cycle offset between position and "
            "velocity is the 90° that j supplies.</b> Energy sloshing between "
            "two stores <i>is</i> a rotation in the plane those two stores span. "
            "Engineers call that plane the <b>phase plane</b>, and the picture is "
            "a <b>phase portrait</b> — both standard terms, and you will meet the "
            "phase portrait again on the nonlinear pages."))
        rot.add(body(
            "<b>So why can one store never rotate?</b> Because a rotation needs "
            "two coordinates. With a single store the state is a single number, "
            "and a single number lives on a line. A point on a line can move "
            "towards zero, away from zero, or sit still — it cannot go round "
            "anything, because there is nowhere to go round. <b>ω = 0 is not a "
            "special case of oscillation; it is the statement that the state "
            "space is one-dimensional.</b> You will see this literally in the "
            "phase portrait in the last widget on this page.", dim=True))
        self.add(rot)

        # ---- the six modes --------------------------------------------------
        six = Card("every motion a linear system can make — the complete list, "
                   "and there are six")
        six.add(body(
            "Your question was whether motions can only either continue forever "
            "or die while ringing. Close: there are exactly <b>six</b> "
            "possibilities, and they are just the three things the real part can "
            "be, crossed with the two things the imaginary part can be. Each "
            "pole contributes one of these — the field's word for it is a "
            "<b>mode</b> — and any response is a sum of its modes."))
        six.add(body(
            "<table cellpadding='7'>"
            "<tr><td></td><td><b>ω = 0 &nbsp; (no imaginary part)</b></td>"
            "<td><b>ω ≠ 0 &nbsp; (imaginary part)</b></td></tr>"

            "<tr><td><b>σ &lt; 0</b><br>left half plane</td>"
            "<td><b>decays smoothly to nothing.</b><br>The first-order response. "
            "Stable, no overshoot ever.</td>"
            "<td><b>rings, each swing smaller.</b><br>A decaying oscillation — "
            "underdamped. Stable, but it overshoots.</td></tr>"

            "<tr><td><b>σ = 0</b><br>on the axis</td>"
            "<td><b>held, forever, at whatever value it has.</b><br>An "
            "integrator. Never grows, never decays.</td>"
            "<td><b>rings forever at constant amplitude.</b><br>A lossless "
            "resonator — a bell with no damping.</td></tr>"

            "<tr><td><b>σ &gt; 0</b><br>right half plane</td>"
            "<td><b>runs away smoothly.</b><br>Unstable, no oscillation — an "
            "inverted pendulum falling over.</td>"
            "<td><b>rings, each swing bigger.</b><br>Unstable oscillation — the "
            "howl of a loop with too much gain.</td></tr>"
            "</table>"))
        six.add(callout(
            "<b>That table is the whole vocabulary of linear motion.</b> Nothing "
            "a linear system does falls outside it. The horizontal axis picks the "
            "row, the vertical axis picks the column, and a pole is just the "
            "coordinates of one cell. The six buttons on the widget below put the "
            "pole in each cell in turn — press them in order and you will have "
            "seen everything linear systems can do.", "key"))
        self.add(six)

        # ---- phasor interactive -------------------------------------------
        self.add(hline())
        self.add(title("Interactive — one pole, drawn three ways at once"))

        ph = Card("drag the pole; watch the spiral and the signal it makes")
        ph.add(body(
            "Left: where the pole is. Middle: the actual motion "
            "e<sup>st</sup> in the complex plane — a point at radius "
            "e<sup>σt</sup> and angle ωt. Right: the real part of that motion, "
            "which is the signal you would measure. <b>All three are the same "
            "number.</b><br><br>"
            "Three settings worth doing deliberately:<br>"
            "&nbsp;&nbsp;• <b>ω = 0</b> — nothing rotates, the spiral collapses "
            "onto a line, and the signal is a plain exponential decay. "
            "<b>That is a first-order system.</b><br>"
            "&nbsp;&nbsp;• <b>σ = 0</b> — the radius never shrinks, the spiral "
            "becomes a circle, and the signal is a sine that rings forever. "
            "Marginal.<br>"
            "&nbsp;&nbsp;• <b>σ &gt; 0</b> — the spiral winds outward and the "
            "signal grows. Unstable, and now you can see why the right half "
            "plane is shaded red.", dim=True))
        self.s_sig = slider(-300, 60, -80)     # x0.1  1/s
        self.s_om = slider(0, 400, 150)        # x0.1  rad/s
        self.l_sig, self.l_om = QLabel(), QLabel()
        ph.add_layout(slider_row("σ — real part (1/s)", self.s_sig, self.l_sig))
        ph.add_layout(slider_row("ω — imag part (rad/s)", self.s_om, self.l_om))
        self.btn_run = _btn("play / pause", primary=True)
        self.btn_rrst = _btn("restart")
        ph.add_layout(_btn_row(self.btn_run, self.btn_rrst))
        presets = [("decays, no ring", -80, 0),
                   ("held forever", 0, 0),
                   ("grows, no ring", 40, 0),
                   ("rings + decays", -80, 150),
                   ("rings forever", 0, 150),
                   ("rings + grows", 40, 150)]
        pb = []
        for label, sg, om in presets:
            b = _btn(label)
            b.clicked.connect(
                lambda _=False, x=sg, y=om: self._preset_phasor(x, y))
            pb.append(b)
        ph.add_layout(_btn_row(*pb[:3]))
        ph.add_layout(_btn_row(*pb[3:]))
        self.st_dec = Stat("decay rate", "--", theme.ACCENT)
        self.st_ptau = Stat("τ", "--", theme.GOOD)
        self.st_ring = Stat("ring rate", "--", theme.VIOLET)
        self.st_per = Stat("one wobble takes", "--", theme.CYAN)
        self.st_cycles = Stat("wobbles before it dies", "--", theme.WARN)
        ph.add_layout(stat_row(self.st_dec, self.st_ptau, self.st_ring,
                               self.st_per, self.st_cycles))
        self.c_ph = MplCanvas(width=7.6, height=2.9, ncols=3)
        ph.add(self.c_ph)
        self.ph_text = _readout()
        ph.add(self.ph_text)
        self.add(ph)

        self._pt = 0.0
        self._ptimer = QTimer(self)
        self._ptimer.setInterval(55)
        self._ptimer.timeout.connect(self._tick_phasor)
        self.btn_run.clicked.connect(self._toggle_phasor)
        self.btn_rrst.clicked.connect(self._restart_phasor)
        for w in (self.s_sig, self.s_om):
            w.valueChanged.connect(self._restart_phasor)
        self._build_phasor()

        ax = Card("so the two axes are two physical rates, and that is all")
        ax.add(body(
            "&nbsp;&nbsp;• <b>Horizontal — the real part σ: the decay rate</b>, "
            "in 1/seconds. How fast the motion dies. Left = dies (stable). "
            "Right = grows (unstable). Further left = decays faster. This is "
            "the pole you already met on page 6.<br>"
            "&nbsp;&nbsp;• <b>Vertical — the imaginary part ω: the ring "
            "rate</b>, in rad/s. How fast it wobbles on the way. A first-order "
            "system has nothing to wobble with, so ω = 0 and its pole sits flat "
            "on the horizontal axis."))
        ax.add(callout(
            "<b>\"We don't want the response to die, we want it to settle\" — "
            "these are the same thing.</b> What decays is not the output, it is "
            "the <i>transient</i>: the difference between where you are and "
            "where you were told to be. Killing that difference fast <i>is</i> "
            "settling fast. The output does not die; the error does.", "key"))
        self.add(ax)

        # ---- two stores ----------------------------------------------------
        self.add(hline())
        self.add(title("Interactive — the second store, and where overshoot "
                       "physically comes from"))

        ov = Card("one reservoir versus two, with the energy shown")
        ov.add(body(
            "Both systems get the same step command at t = 0. The left one has "
            "a single store — the moving mass — and the thing you are watching "
            "(its speed) <b>is</b> that store. The right one has two: the mass "
            "holds speed, and the spring holds position.<br><br>"
            "Watch the energy bars. On the left there is one bar and it fills "
            "monotonically. On the right, energy <b>sloshes</b> between the two "
            "bars, and the moment that matters is marked: <b>the output reaches "
            "its target while the mass is still moving.</b> At that instant the "
            "spring force is exactly right, the net force is zero — and yet the "
            "system is not at rest, because there is energy parked somewhere "
            "that is not the output variable. That parked kinetic energy is "
            "<i>momentum</i>, and it carries the output straight past the "
            "target. Then the spring reverses and shoves it back. That is "
            "ringing.", dim=True))
        self.s_zeta = slider(5, 200, 25)      # x0.01
        self.l_zeta = QLabel()
        ov.add_layout(slider_row("damping ζ — right side", self.s_zeta,
                                 self.l_zeta))
        self.s_scrub = slider(0, 1000, 0)
        self.l_scrub = QLabel()
        ov.add_layout(slider_row("time — drag to scrub", self.s_scrub,
                                 self.l_scrub))
        self.btn_go2 = _btn("run both", primary=True)
        self.btn_cross = _btn("jump to the moment it hits target")
        self.btn_rst2 = _btn("reset")
        ov.add_layout(_btn_row(self.btn_go2, self.btn_cross, self.btn_rst2))
        self.st_os = Stat("overshoot", "--", theme.BAD)
        self.st_hidden = Stat("hidden KE at target", "--", theme.VIOLET)
        self.st_now = Stat("KE right now", "--", theme.PINK)
        self.st_poles = Stat("poles", "--", theme.ACCENT)
        self.st_kind = Stat("behaviour", "--", theme.WARN)
        ov.add_layout(stat_row(self.st_os, self.st_hidden, self.st_now,
                               self.st_poles, self.st_kind))
        self.c_ov = MplCanvas(width=7.6, height=5.4, nrows=2, ncols=2)
        ov.add(self.c_ov)
        self.ov_text = _readout()
        ov.add(self.ov_text)
        ov.add(body(
            "<b>The bottom-right panel is the phase portrait</b> — position "
            "across, velocity up — and it is the rotation that the imaginary "
            "axis is talking about. The state spirals inward: turning because "
            "energy is being handed between the two stores, shrinking because "
            "the damper is eating it. Set ζ above 1 and the spiral stops being a "
            "spiral: the state slides straight in without ever going round, "
            "which is exactly what \"the poles left the imaginary axis\" looks "
            "like in the machine.<br><br>"
            "<b>The one-store system cannot be drawn here at all</b>, because "
            "its state is a single number — it would be a point moving along a "
            "line, with no second direction to turn into.", dim=True))
        ov.add(body(
            "<b>Turn ζ up past 1.</b> The poles collide on the real axis and "
            "split apart along it — the imaginary parts vanish, the sloshing "
            "stops, and the overshoot goes to zero. The system still has two "
            "stores, but the damper is now eating the surplus faster than the "
            "spring can hand it back. <b>That is what \"critically damped\" "
            "means, and it is what most joint tuning is trying to buy.</b>",
            dim=True))
        self.add(ov)

        self._ov_i = 0
        self._ovtimer = QTimer(self)
        self._ovtimer.setInterval(55)
        self._ovtimer.timeout.connect(self._tick_ov)
        self.btn_go2.clicked.connect(self._run_ov)
        self.btn_cross.clicked.connect(self._jump_cross)
        self.btn_rst2.clicked.connect(self._reset_ov)
        self.s_zeta.valueChanged.connect(self._reset_ov)
        self.s_scrub.valueChanged.connect(self._scrub_ov)
        self._sim_ov()
        self._build_ov()

        no = Card("the argument, stated once, now that you have seen it")
        no.add(body(
            "<b>To overshoot, a system must arrive at its destination still "
            "carrying something that pushes it past.</b> Ask what that something "
            "could be in a first-order system.<br><br>"
            "The joint reaches its final speed at the exact moment friction bω "
            "has grown to equal the applied torque τ. At that instant the net "
            "torque is <b>precisely zero</b> — nothing is left pushing. And the "
            "only quantity the system stores <i>is</i> the one you are watching. "
            "There is no second reservoir holding a surplus.<br><br>"
            "One store means the output <b>is</b> the state. Reaching the target "
            "means the state is at its final value. Nothing is left over. So it "
            "arrives and stops — for any input, at any gain."))
        no.add(callout(
            "<b>\"Energy in a form that is not the output variable\" — that is "
            "the whole trick, and now it is concrete.</b> You are measuring "
            "position; the surplus is hiding in velocity. Position is on target "
            "and the system is not at rest. Give the system somewhere to hide "
            "energy and it can overshoot; take that hiding place away and it "
            "cannot. Everything about second-order systems is a consequence.",
            "key"))
        self.add(no)

        # ---- what this is for ---------------------------------------------
        use = Card("and this is what a controller is actually for")
        use.add(body(
            "You now have a map on which every behaviour you care about is a "
            "<b>location</b>:<br><br>"
            "&nbsp;&nbsp;• too slow to respond → the pole is too close to the "
            "origin → <b>move it left</b><br>"
            "&nbsp;&nbsp;• rings and wobbles → the poles have too much imaginary "
            "part relative to real → <b>push them down towards the real "
            "axis</b><br>"
            "&nbsp;&nbsp;• never quite reaches the target → you need a pole "
            "<b>at</b> the origin, whose state never decays → add an "
            "integrator<br>"
            "&nbsp;&nbsp;• unstable → a pole is in the right half plane → "
            "<b>drag it back across</b><br><br>"
            "<b>Feedback does not change the plant. It moves the plant's "
            "poles.</b> That single sentence is what the controller-design half "
            "of this tutor is about, and it is only meaningful because you can "
            "now read a pole's position as a pair of physical rates. Root locus, "
            "lead compensators, pole placement and LQR are four different ways "
            "of answering the question \"where do I want these dots, and what "
            "gain puts them there\"."))
        self.add(use)

        self.add(callout(
            "<b>Carry forward.</b> Real part = decay rate. Imaginary part = ring "
            "rate. One store ⇒ no imaginary part ⇒ no overshoot, no ringing, at "
            "most 90° of lag, infinite gain margin. Add the second store and "
            "every one of those five statements breaks — which is the next "
            "page, and it is where every robot joint you will ever tune "
            "lives.", "good"))

        self.finish()

    # ------------------------------------------------------------------
    def on_show(self):
        self._ptimer.start()

    def on_hide(self):
        self._ptimer.stop()
        self._ovtimer.stop()

    # -- phasor ---------------------------------------------------------
    def _pvals(self):
        return self.s_sig.value() / 10.0, self.s_om.value() / 10.0

    def _toggle_phasor(self):
        if self._ptimer.isActive():
            self._ptimer.stop()
        else:
            self._ptimer.start()

    def _preset_phasor(self, sig, om):
        self.s_sig.blockSignals(True)
        self.s_om.blockSignals(True)
        self.s_sig.setValue(sig)
        self.s_om.setValue(om)
        self.s_sig.blockSignals(False)
        self.s_om.blockSignals(False)
        self._restart_phasor()

    def _restart_phasor(self):
        self._pt = 0.0
        self._build_phasor()
        self._ptimer.start()

    def _tick_phasor(self):
        sig, om = self._pvals()
        span = self._pspan(sig, om)
        self._pt += span / 90.0
        if self._pt > span:
            self._pt = 0.0
        self._frame_phasor()

    @staticmethod
    def _pspan(sig, om):
        opts = []
        if sig < -0.05:
            opts.append(5.0 / abs(sig))
        if om > 0.05:
            opts.append(4.0 * 2 * math.pi / om)
        return max(min(opts) if opts else 3.0, 0.2)

    def _build_phasor(self):
        sig, om = self._pvals()
        self.l_sig.setText(f"{sig:+.1f}")
        self.l_om.setText(f"{om:.1f}")
        span = self._pspan(sig, om)

        self.st_dec.set(f"{sig:+.1f} 1/s")
        self.st_dec.set_color(theme.GOOD if sig < 0 else
                              (theme.WARN if sig == 0 else theme.BAD))
        self.st_ptau.set("∞" if abs(sig) < 1e-6 else f"{1000/abs(sig):.0f} ms")
        self.st_ring.set(f"{om:.1f} rad/s")
        self.st_per.set("—" if om < 1e-6 else f"{2*math.pi/om*1000:.0f} ms")
        if om < 1e-6:
            self.st_cycles.set("none — it just decays")
        elif sig >= 0:
            self.st_cycles.set("never dies")
        else:
            self.st_cycles.set(f"{(om/(2*math.pi))*(4.6/abs(sig)):.1f}")

        if om < 0.05:
            msg = ("<b>ω = 0 — this is a first-order system.</b> Nothing "
                   "rotates, so there is nothing to wobble; the motion can only "
                   "shrink along a line. The pole is on the real axis and the "
                   "signal is a pure exponential.")
        elif abs(sig) < 0.05:
            msg = ("<b>σ = 0 — marginal.</b> The radius never shrinks, so the "
                   "circle closes on itself and the ringing never stops. The "
                   "pole is on the imaginary axis, exactly on the boundary.")
        elif sig > 0:
            msg = ("<b>σ &gt; 0 — unstable.</b> The spiral winds outward, the "
                   "envelope grows, and every wobble is bigger than the last. "
                   "The pole is in the red half plane.")
        else:
            msg = ("<b>Both parts non-zero — a decaying oscillation.</b> It "
                   f"wobbles at {om/(2*math.pi):.1f} Hz while its envelope "
                   f"shrinks with τ = {1000/abs(sig):.0f} ms. Two stores are "
                   "trading energy while friction eats it. Every underdamped "
                   "joint you have ever tuned is this picture.")
        self.ph_text.setText(msg)

        c = self.c_ph
        c.clear()
        a_s, a_c, a_t = c.axes

        lim = max(abs(sig), om, 1.0) * 1.5
        poles = [complex(sig, om)] + ([complex(sig, -om)] if om > 1e-6 else [])
        _splane(a_s, poles, lim=lim)
        a_s.set_title("the pole", fontsize=9)

        n = 400
        ts = [span * i / n for i in range(n + 1)]
        xs = [math.exp(sig * t) * math.cos(om * t) for t in ts]
        ys = [math.exp(sig * t) * math.sin(om * t) for t in ts]
        rlim = max(1.05, max(abs(v) for v in xs + ys) * 1.1)
        a_c.plot(xs, ys, color=theme.ACCENT_DIM, lw=1.2)
        self._ph_radius, = a_c.plot([], [], color=theme.WARN, lw=1.8)
        self._ph_dot, = a_c.plot([], [], marker="o", ms=7,
                                 color=theme.WARN, ls="none", zorder=6)
        self._ph_drop, = a_c.plot([], [], color=theme.TEXT_FAINT, lw=0.9,
                                  ls=":")
        self._ph_shadow, = a_c.plot([], [], marker="o", ms=5,
                                    color=theme.ACCENT, ls="none", zorder=6)
        a_c.axhline(0, color=theme.BORDER, lw=0.9)
        a_c.axvline(0, color=theme.BORDER, lw=0.9)
        a_c.set_xlim(-rlim, rlim)
        a_c.set_ylim(-rlim, rlim)
        a_c.set_xlabel("real  (what you measure)")
        a_c.set_ylabel("imag")
        a_c.set_title("the motion $e^{st}$", fontsize=9)

        a_t.plot([t * 1000 for t in ts], xs, color=theme.ACCENT, lw=2.0)
        env = [math.exp(sig * t) for t in ts]
        a_t.plot([t * 1000 for t in ts], env, color=theme.TEXT_FAINT, lw=1.0,
                 ls="--")
        a_t.plot([t * 1000 for t in ts], [-v for v in env],
                 color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a_t.axhline(0, color=theme.BORDER, lw=0.9)
        self._ph_cursor, = a_t.plot([], [], color=theme.WARN, lw=1.2)
        self._ph_cdot, = a_t.plot([], [], marker="o", ms=6, color=theme.WARN,
                                  ls="none", zorder=6)
        a_t.set_xlim(0, span * 1000)
        a_t.set_ylim(-rlim, rlim)
        a_t.set_xlabel("time (ms)")
        a_t.set_ylabel("$Re\\,e^{st}$")
        a_t.set_title("the signal it makes", fontsize=9)
        c.refresh()
        self._frame_phasor()

    def _frame_phasor(self):
        sig, om = self._pvals()
        rt = math.exp(sig * self._pt)
        px, py = rt * math.cos(om * self._pt), rt * math.sin(om * self._pt)
        self._ph_radius.set_data([0, px], [0, py])
        self._ph_dot.set_data([px], [py])
        self._ph_drop.set_data([px, px], [py, 0])
        self._ph_shadow.set_data([px], [0])
        lo, hi = self.c_ph.axes[2].get_ylim()
        self._ph_cursor.set_data([self._pt * 1000, self._pt * 1000], [lo, hi])
        self._ph_cdot.set_data([self._pt * 1000], [px])
        self.c_ph.refresh(layout=False)

    # -- one store vs two -----------------------------------------------
    def _sim_ov(self):
        """Precompute both responses and their energies."""
        zeta = self.s_zeta.value() / 100.0
        m, k = 1.0, 100.0
        wn = math.sqrt(k / m)
        c2 = 2.0 * zeta * wn * m
        F = k                                   # so final x = 1.0
        dur = 2.2
        dt = 0.002
        n = int(dur / dt)

        x = v = 0.0
        T2, X2, V2, PE, KE = [], [], [], [], []
        for i in range(n):
            a = (F - c2 * v - k * x) / m
            v += a * dt
            x += v * dt
            T2.append(i * dt)
            X2.append(x)
            V2.append(v)
            # measure the spring's stored energy from the EQUILIBRIUM point,
            # not from x = 0 -- otherwise the constant bias needed to hold the
            # joint at its target swamps the sloshing you are trying to see
            PE.append(0.5 * k * (x - 1.0) ** 2)
            KE.append(0.5 * m * v * v)

        # one store: mass + damper, velocity out, same m and c
        c1 = max(c2, 1e-3)
        tau1 = m / c1
        vf = F / c1
        V1 = [vf * (1 - math.exp(-t / tau1)) for t in T2]
        KE1 = [0.5 * m * vv * vv for vv in V1]

        emax = max(max(PE), max(KE), 1e-9)
        self._ov = dict(t=T2, x=X2, v=V2, pe=PE, ke=KE,
                        v1=[vv / max(vf, 1e-9) for vv in V1],
                        ke1=KE1,
                        emax=emax,
                        e1max=max(max(KE1), 1e-9),
                        zeta=zeta, wn=wn, dt=dt)
        # first moment the two-store output crosses its target
        self._ov["cross"] = next((i for i, xx in enumerate(X2) if xx >= 1.0),
                                 None)

    def _reset_ov(self):
        self._ovtimer.stop()
        self._sim_ov()
        self._ov_i = 0
        self._set_scrub(0)
        self._build_ov()

    def _set_scrub(self, i):
        n = len(self._ov["t"]) - 1
        self.s_scrub.blockSignals(True)
        self.s_scrub.setValue(int(round(1000 * i / max(n, 1))))
        self.s_scrub.blockSignals(False)

    def _scrub_ov(self):
        self._ovtimer.stop()
        n = len(self._ov["t"]) - 1
        self._ov_i = int(round(n * self.s_scrub.value() / 1000.0))
        self._frame_ov()

    def _jump_cross(self):
        self._ovtimer.stop()
        cr = self._ov["cross"]
        if cr is None:                       # never reaches target: use the peak
            cr = max(range(len(self._ov["x"])),
                     key=lambda i: self._ov["x"][i])
        self._ov_i = cr
        self._set_scrub(cr)
        self._frame_ov()

    def _run_ov(self):
        self._ov_i = 0
        self._ovtimer.start()

    def _tick_ov(self):
        self._ov_i += 12
        if self._ov_i >= len(self._ov["t"]) - 1:
            self._ov_i = len(self._ov["t"]) - 1
            self._ovtimer.stop()
        self._set_scrub(self._ov_i)
        self._frame_ov()

    def _build_ov(self):
        d = self._ov
        zeta, wn = d["zeta"], d["wn"]
        self.l_zeta.setText(f"{zeta:.2f}")

        peak = max(d["x"])
        self.st_os.set(f"{max(peak - 1.0, 0.0)*100:.0f}%")
        self.st_os.set_color(theme.GOOD if peak <= 1.001 else theme.BAD)
        cr = d["cross"]
        hidden = (d["ke"][cr] / max(d["ke"][cr] + d["pe"][cr], 1e-12) * 100.0
                  if cr is not None else 0.0)
        # at the instant the output sits on target the spring's stored energy
        # (measured from equilibrium) is zero, so this share is the fraction of
        # the remaining energy that is hidden in motion -- the surplus that
        # carries it past. Overdamped systems creep in and never have any.
        self.st_hidden.set("0% — arrives at rest" if cr is None
                           else f"{hidden:.0f}%")
        self.st_hidden.set_color(theme.GOOD if cr is None else theme.VIOLET)
        if zeta < 1.0:
            wd = wn * math.sqrt(1 - zeta * zeta)
            self.st_poles.set(f"−{zeta*wn:.1f} ± j{wd:.1f}")
            self.st_kind.set("underdamped — rings")
            self.st_kind.set_color(theme.BAD)
        elif abs(zeta - 1.0) < 1e-9:
            self.st_poles.set(f"−{wn:.1f} (twice)")
            self.st_kind.set("critically damped")
            self.st_kind.set_color(theme.GOOD)
        else:
            r = wn * math.sqrt(zeta * zeta - 1)
            self.st_poles.set(f"−{zeta*wn-r:.1f}, −{zeta*wn+r:.1f}")
            self.st_kind.set("overdamped — no ring")
            self.st_kind.set_color(theme.GOOD)

        c = self.c_ov
        c.clear()
        a1, a2, a3, a4 = c.axes

        # -- 1. outputs -----------------------------------------------------
        self._ov_l1, = a1.plot([], [], color=theme.GOOD, lw=2.0,
                               label="1 store (speed)")
        self._ov_l2, = a1.plot([], [], color=theme.BAD, lw=2.0,
                               label="2 stores (position)")
        a1.axhline(1.0, color=theme.TEXT_FAINT, lw=1.0, ls="--", label="target")
        if cr is not None:
            a1.axvline(d["t"][cr], color=theme.VIOLET, lw=1.0, ls=":")
            a1.text(d["t"][cr], 1.06, " on target,\n still moving",
                    color=theme.VIOLET, fontsize=7)
        self._ov_c1, = a1.plot([], [], color=theme.WARN, lw=1.2)
        a1.set_xlim(0, d["t"][-1])
        a1.set_ylim(-0.1, max(1.5, max(d["x"]) * 1.15))
        a1.set_xlabel("time (s)")
        a1.set_ylabel("output (normalised)")
        a1.set_title("same command, one store vs two", fontsize=9)
        c.legend(a1, loc="lower right")

        # -- 2. energy vs time (the sloshing, over the whole run) -----------
        em = d["emax"]
        a2.plot(d["t"], [v / em for v in d["pe"]], color=theme.ACCENT, lw=1.8,
                label="spring PE")
        a2.plot(d["t"], [v / em for v in d["ke"]], color=theme.PINK, lw=1.8,
                label="mass KE")
        a2.plot(d["t"], [(p_ + k_) / em for p_, k_ in zip(d["pe"], d["ke"])],
                color=theme.TEXT_FAINT, lw=1.1, ls="--", label="total")
        if cr is not None:
            a2.axvline(d["t"][cr], color=theme.VIOLET, lw=1.0, ls=":")
        self._ov_c2, = a2.plot([], [], color=theme.WARN, lw=1.2)
        a2.set_xlim(0, d["t"][-1])
        a2.set_ylim(0, 1.1)
        a2.set_xlabel("time (s)")
        a2.set_ylabel("energy (fraction of peak)")
        a2.set_title("two stores handing energy back and forth", fontsize=9)
        c.legend(a2, loc="upper right")

        # -- 3. bars right now ----------------------------------------------
        self._ov_bars = [
            a3.bar([0], [0.0], color=theme.GOOD, width=0.5)[0],
            a3.bar([1.4], [0.0], color=theme.ACCENT, width=0.5)[0],
            a3.bar([2.1], [0.0], color=theme.PINK, width=0.5)[0],
        ]
        a3.set_xticks([0, 1.4, 2.1])
        a3.set_xticklabels(["mass\n(1 store)", "spring\nPE", "mass\nKE"],
                           fontsize=7.5)
        a3.set_xlim(-0.5, 2.6)
        a3.set_ylim(0, 1.15)
        a3.set_ylabel("energy (fraction of peak)")
        a3.set_title("where the energy is at the cursor", fontsize=9)
        a3.axvline(0.7, color=theme.BORDER, lw=1.0, ls="--")

        # -- 4. phase portrait: THE rotation --------------------------------
        a4.plot(d["x"], d["v"], color=theme.ACCENT_DIM, lw=1.2)
        self._ov_ph, = a4.plot([], [], marker="o", ms=7, ls="none",
                               color=theme.WARN, zorder=6)
        a4.scatter([1.0], [0.0], marker="x", s=70, linewidths=2.0,
                   color=theme.GOOD, zorder=5, label="rest state")
        a4.axhline(0, color=theme.BORDER, lw=0.9)
        a4.axvline(1.0, color=theme.BORDER, lw=0.9, ls=":")
        a4.set_xlabel("position")
        a4.set_ylabel("velocity")
        a4.set_title("phase portrait — the rotation, in state space",
                     fontsize=9)
        c.legend(a4, loc="upper right")
        c.refresh()
        self._frame_ov()

    def _frame_ov(self):
        d = self._ov
        i = min(self._ov_i, len(d["t"]) - 1)
        t = d["t"][i]
        self.l_scrub.setText(f"{t:.2f} s")
        self._ov_l1.set_data(d["t"][:i + 1], d["v1"][:i + 1])
        self._ov_l2.set_data(d["t"][:i + 1], d["x"][:i + 1])
        lo, hi = self.c_ov.axes[0].get_ylim()
        self._ov_c1.set_data([t, t], [lo, hi])
        self._ov_c2.set_data([t, t], [0, 1.1])
        self._ov_ph.set_data([d["x"][i]], [d["v"][i]])
        ke_frac = d["ke"][i] / d["emax"]
        for bar, h in zip(self._ov_bars,
                          (d["ke1"][i] / d["e1max"],
                           d["pe"][i] / d["emax"],
                           ke_frac)):
            bar.set_height(h)

        self.st_now.set(f"{ke_frac*100:.0f}%")
        self.st_now.set_color(theme.PINK if ke_frac > 0.05 else theme.TEXT_DIM)
        share = d["ke"][i] / max(d["ke"][i] + d["pe"][i], 1e-12) * 100.0
        self.ov_text.setText(
            f"<b>Cursor at t = {t:.2f} s.</b> &nbsp; position "
            f"<b>{d['x'][i]:.3f}</b> (target 1.000) &nbsp;·&nbsp; velocity "
            f"<b>{d['v'][i]:+.3f}</b> &nbsp;·&nbsp; of the energy still in the "
            f"system, <b>{share:.0f}%</b> is in the mass and "
            f"<b>{100-share:.0f}%</b> is in the spring."
            + ("<br><b>The mass is still moving while the output sits on its "
               "target — that surplus is what carries it past.</b>"
               if abs(d["x"][i] - 1.0) < 0.05 and abs(d["v"][i]) > 0.05 else ""))
        self.c_ov.refresh(layout=False)
