"""
Linear systems and stability -- the five pages that make every later claim
about "bandwidth", "damping" and "margin" mean something specific.

  1  First-Order Systems    one pole, one time constant, and why it cannot
                            oscillate no matter what you do to it
  2  Second-Order Systems   two poles, and the moment overshoot becomes
                            possible -- which is where every robot joint lives
  3  Stability              what stable actually means, and the three ways to
                            check it without guessing
  4  Bode & Margins         how far you are from the edge, in the two
                            directions you can actually be wrong
  5  Nyquist                the same question asked geometrically, and the
                            cases where Bode quietly lies

These come straight after Real-Time on purpose. That page said your bandwidth
is roughly f_s/10 and that delay costs you phase margin. Both of those
sentences are claims about the objects defined here, and until you can see a
pole move there is no way to check either one.
"""

from __future__ import annotations

import math

from PySide6.QtWidgets import QComboBox, QLabel

from ctrlcore.linear import (
    TF,
    bode,
    critical_gain,
    damped_frequency,
    first_order,
    geared_joint_plant,
    joint_wn_zeta,
    log_freqs,
    margins,
    margins_with_delay,
    nyquist_points,
    encirclements,
    overshoot_fraction,
    peak_time,
    poly_roots,
    resonant_peak_db,
    routh_rhp_count,
    routh_table,
    second_order,
    settling_time,
    step_response,
    vector_margin,
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
from .motors import slider, slider_row

SECTION = "Systems & Stability"


# --------------------------------------------------------------------------
# shared drawing helpers
# --------------------------------------------------------------------------

def _splane(ax, poles, zeros=(), lim=None, marker_label="poles"):
    """
    Draw a pole-zero map. The left half plane is shaded because that shading
    IS the stability condition -- there is no other content in the picture.
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


def _bode_axes(a_mag, a_ph, w, mag, ph, colour=None, label=None):
    colour = colour or theme.ACCENT
    a_mag.semilogx(w, mag, color=colour, lw=2.0, label=label)
    a_mag.axhline(0, color=theme.TEXT_FAINT, lw=1.0, ls="--")
    a_mag.set_ylabel("|G|  (dB)")
    a_ph.semilogx(w, ph, color=colour, lw=2.0)
    a_ph.axhline(-180, color=theme.BAD, lw=1.0, ls=":")
    a_ph.set_ylabel("phase (deg)")
    a_ph.set_xlabel("frequency  ω  (rad/s)")


# ==========================================================================
# PAGE -- first order
# ==========================================================================

class FirstOrderPage(Page):
    TITLE = "First-Order Systems"
    SUBTITLE = ("One pole, one time constant. The simplest thing that can be "
                "called a system — and the only one that is unconditionally "
                "safe to close a loop around.")
    SECTION = SECTION
    NOTES = "foundation"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>Why this page is first.</b> Every claim the rest of this tutor "
            "makes about speed — \"bandwidth\", \"time constant\", \"the loop "
            "cannot react faster than\" — is a claim about where a <b>pole</b> "
            "is. A first-order system has exactly one, so it is the place to "
            "learn what a pole does before there are two of them interacting.",
            "key"))

        # ---- the physical picture, before any algebra ---------------------
        ph = Card("first: what a first-order system physically IS — no equation "
                  "needed")
        ph.add(body(
            "Forget transfer functions for a moment. A system is first order "
            "when it has exactly <b>two</b> physical features:"))
        ph.add(body(
            "&nbsp;&nbsp;<b>1 · One thing that stores.</b> A reservoir with a "
            "level in it. A spinning mass stores <i>speed</i>. A coil stores "
            "<i>current</i>. A hot motor stores <i>heat</i>.<br>"
            "&nbsp;&nbsp;<b>2 · One thing that drains, in proportion to how much "
            "is stored.</b> Friction drags harder the faster you spin. "
            "Resistance drops more voltage the more current flows. A hot object "
            "loses heat faster the hotter it is."))
        ph.add(callout(
            "<b>The whole behaviour follows from those two sentences.</b> You "
            "pour in at a constant rate. The level rises. But the fuller it "
            "gets, the faster it leaks — so the rise slows down. Eventually the "
            "leak exactly matches the pour, and the level stops.<br><br>"
            "That is the entire story of every first-order response you will "
            "ever see: <b>a race between a constant fill and a leak that grows "
            "with the level</b>, ending in a draw.", "key"))
        ph.add(body(
            "<b>Take the joint you actually have.</b> Apply a constant torque τ "
            "to a joint with inertia J and bearing friction b. It speeds up. As "
            "it speeds up, friction fights back harder — bω. When bω has grown "
            "to equal τ, the net torque is zero and the joint holds that speed "
            "forever.<br><br>"
            "Nothing else happens. It does not overshoot, it does not ring, it "
            "does not hunt. It fills up and stops. If your real joint does "
            "something else, it is not first order and you have found a second "
            "energy store you had not accounted for.", dim=True))
        self.add(ph)

        # ---- the equation, built from the picture -------------------------
        d = Card("now the equation — it is the picture, written down")
        d.add(body(
            "Newton for that joint. Rate of change of the stored quantity = "
            "what you put in, minus what leaks out:"))
        d.add(math_label(r"J\,\dot\omega \;=\; \tau \;-\; b\,\omega", 17))
        d.add(body(
            "&nbsp;&nbsp;<b>J ω̇</b> — the store filling up<br>"
            "&nbsp;&nbsp;<b>τ</b> — the fill rate, constant<br>"
            "&nbsp;&nbsp;<b>b ω</b> — the leak, and note it is proportional to "
            "<b>ω</b>, the level itself. That proportionality is the whole "
            "mechanism.", dim=True))
        d.add(body(
            "Move the leak across and divide by b, purely to make the shape "
            "obvious:"))
        d.add(math_label(r"\frac{J}{b}\,\dot\omega + \omega = \frac{\tau}{b}"
                         r"\qquad\text{i.e.}\qquad "
                         r"\tau_{c}\,\dot y + y = K u", 17))
        d.add(body(
            "<b>That is the canonical first-order equation, and it was not "
            "handed to you — it came out of \"one store, one leak\".</b> Every "
            "first-order system in engineering is this equation with different "
            "words for the store and the leak.", dim=True))
        self.add(d)

        # ---- what each symbol physically is -------------------------------
        s = Card("what every symbol in it physically means")
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
            "Seconds.</td></tr>"
            "<tr><td><b>the pole</b><br>s = −1/τ<sub>c</sub></td>"
            "<td>b/J — leak divided by store</td>"
            "<td><b>A rate. Units of 1/seconds.</b> Literally \"how many times "
            "per second this system forgets what you did to it\". The minus sign "
            "means forgetting, not growing.</td></tr>"
            "</table>"))
        s.add(callout(
            "<b>The single most useful mental image for the time constant.</b> "
            "At the instant you apply the input, the leak is still zero, so the "
            "system is rising at its fastest. <b>If it kept rising at that "
            "initial rate, it would arrive at the final value in exactly "
            "τ<sub>c</sub> seconds.</b><br><br>"
            "It does not, because the leak grows as it climbs — so instead it "
            "gets <b>63.2%</b> of the way there in τ<sub>c</sub>. That is where "
            "the famous number comes from. It is not a definition; it is what is "
            "left over after the leak has had τ<sub>c</sub> seconds to fight "
            "back. The dashed tangent line in the plot below is that "
            "\"if it kept going\" line.", "key"))
        self.add(s)

        w = Card("the same two features, four different physical dresses")
        w.add(body(
            "<table cellpadding='6'>"
            "<tr><td><b>Motor winding</b></td><td>L·di/dt + R·i = V</td>"
            "<td>τ = L/R, typically <b>0.1–2 ms</b>. This is why the current "
            "loop can run at 20 kHz and the joint loop cannot.</td></tr>"
            "<tr><td><b>Velocity of a joint</b></td><td>J·ω̇ + b·ω = τ</td>"
            "<td>τ = J/b. Torque in, speed out — first order, always.</td></tr>"
            "<tr><td><b>Any low-pass filter</b></td><td>τ·ẏ + y = u</td>"
            "<td>Including the derivative filter you were told to always add "
            "on the PID page.</td></tr>"
            "<tr><td><b>Thermal</b></td><td>C·Ṫ + T/R = P</td>"
            "<td>τ = RC, <b>minutes</b>. Motor thermal limits are a first-order "
            "system with a very slow pole.</td></tr>"
            "</table>"))
        w.add(body(
            "The pattern: <b>one energy store</b> (an inductance, a mass, a "
            "capacitance, a heat capacity) and <b>one dissipation</b> "
            "(resistance, friction, conduction). One store, one pole.", dim=True))
        self.add(w)

        # ---- what a pole physically is ------------------------------------
        self.add(hline())
        self.add(title("What a \"pole\" physically is — and why the s-plane is "
                       "not mystical"))

        e = Card("a pole is a rate, not a piece of notation")
        e.add(body(
            "In transfer-function form the same system is written"))
        e.add(math_label(r"G(s) = \frac{K}{\tau_c s + 1}", 17))
        e.add(body(
            "and the <b>pole</b> is the value of s that makes the bottom zero: "
            "s = −1/τ<sub>c</sub>. People treat that as bookkeeping. It is not. "
            "Look at what it physically is:"))
        e.add(math_label(r"s = -\frac{1}{\tau_c} = -\frac{b}{J} "
                         r"\qquad \left[\;\frac{1}{\text{seconds}}\;\right]", 17))
        e.add(body(
            "<b>It is the leak divided by the store, and its units are "
            "1/seconds — a rate.</b> Specifically the rate at which this system "
            "forgets. A pole at −20 means \"this thing loses 20 e-foldings of "
            "memory per second\"; a pole at −2 means it is ten times more "
            "stubborn.<br><br>"
            "And that is exactly why it shows up as the exponent:"))
        e.add(math_label(r"y(t) = K\left(1 - e^{-t/\tau_c}\right) "
                         r"= K\left(1 - e^{\,p\,t}\right), \quad p = -1/\tau_c",
                         16))
        e.add(body(
            "<b>A pole at s = p contributes a term e<sup>pt</sup>.</b> Keep that "
            "sentence; the whole of the next four pages is consequences of "
            "it:<br><br>"
            "&nbsp;&nbsp;• <b>p negative</b> — the leak wins, memory fades, "
            "e<sup>pt</sup> decays → <b>stable</b><br>"
            "&nbsp;&nbsp;• <b>p positive</b> — something is <i>feeding</i> the "
            "store instead of draining it, so it grows → <b>unstable</b>. "
            "Physically: negative friction. It sounds exotic until you meet an "
            "inverted pendulum, where gravity does exactly that.<br>"
            "&nbsp;&nbsp;• <b>p = 0</b> — no leak at all. Whatever you put in "
            "stays in, forever → <b>marginal</b>. This is a frictionless joint: "
            "give it a push and it coasts for ever. Also called an "
            "integrator.<br>"
            "&nbsp;&nbsp;• <b>further left = forgets faster.</b> The real part "
            "<i>is</i> the decay rate. Nothing is being encoded or hidden."))
        e.add(callout(
            "<b>So what are the axes of the s-plane?</b> They are two physical "
            "rates, and that is all.<br><br>"
            "&nbsp;&nbsp;• <b>Horizontal (real part): the decay rate</b>, in "
            "1/seconds. How fast the response dies away. Left = dies. Right = "
            "grows.<br>"
            "&nbsp;&nbsp;• <b>Vertical (imaginary part): the ringing rate</b>, in "
            "rad/s. How fast it wobbles while doing so. A first-order system has "
            "nothing to wobble with, so its pole sits flat on the horizontal "
            "axis — no vertical component at all.<br><br>"
            "A pole is therefore a single point saying \"this system contains a "
            "motion that dies at <i>this</i> rate while wiggling at <i>that</i> "
            "one\". The next page gives it something to wiggle with, and the "
            "pole lifts off the axis.", "key"))
        e.add(body(
            "The τ landmarks worth memorising, because you will read them off "
            "oscilloscopes for the rest of your life: "
            "<b>1τ → 63.2%</b>, 2τ → 86.5%, 3τ → 95.0%, 4τ → 98.2%, "
            "<b>5τ → 99.3%</b>. \"Settled\" conventionally means 4τ (2% band).",
            dim=True))
        self.add(e)

        # ---- interactive 1 ---------------------------------------------
        i = Card("move the pole, watch the response")
        i.add(body(
            "Drag τ and watch two things move together: the pole slides along "
            "the real axis, and the response changes speed. They are the same "
            "fact drawn twice — a pole at −20 1/s and a 50 ms time constant are "
            "the same sentence in two languages.<br><br>"
            "The <b>dashed tangent</b> is the \"if the leak never grew\" line. "
            "Where it crosses the final value is exactly t = τ<sub>c</sub>, "
            "always, for any τ<sub>c</sub> and any K.", dim=True))
        self.s_tau = slider(2, 200, 50)          # x1 ms
        self.s_k = slider(1, 50, 10)             # x0.1
        self.l_tau, self.l_k = QLabel(), QLabel()
        i.add_layout(slider_row("time constant τ (ms)", self.s_tau, self.l_tau))
        i.add_layout(slider_row("DC gain K (×0.1)", self.s_k, self.l_k))
        self.st_pole = Stat("pole", "--", theme.ACCENT)
        self.st_63 = Stat("63% at", "--", theme.GOOD)
        self.st_settle = Stat("settled (4τ)", "--", theme.WARN)
        self.st_bw = Stat("bandwidth", "--", theme.VIOLET)
        i.add_layout(stat_row(self.st_pole, self.st_63, self.st_settle,
                              self.st_bw))
        self.c1 = MplCanvas(width=7.4, height=2.9, ncols=2)
        i.add(self.c1)
        self.add(i)
        for s in (self.s_tau, self.s_k):
            s.valueChanged.connect(self._redraw_step)
        self._redraw_step()

        # ---- frequency view --------------------------------------------
        self.add(hline())
        self.add(title("The same pole, seen in frequency"))

        no = Card("why it physically cannot overshoot — the argument, not the "
                  "assertion")
        no.add(body(
            "Textbooks state \"first-order systems do not overshoot\" as a fact "
            "to memorise. It is a two-line physical argument, and understanding "
            "it is what makes the next page make sense.<br><br>"
            "<b>To overshoot, a system has to arrive at its destination still "
            "carrying something that pushes it past.</b> Ask what that "
            "something could be here.<br><br>"
            "The joint reaches its final speed at the exact moment the friction "
            "torque bω has grown to equal the applied torque τ. At that instant "
            "the <b>net torque is precisely zero</b>. There is nothing left "
            "pushing. And the only quantity the system stores <i>is</i> the one "
            "you are watching — the speed. There is no second reservoir holding "
            "back some surplus that could carry it further."))
        no.add(callout(
            "<b>Overshoot is momentum, and momentum needs a second store.</b> "
            "The system has to be able to hold energy in a form that is <i>not</i> "
            "the output variable, so that when the output reaches its target the "
            "hidden store is still full and shoves it past.<br><br>"
            "One store means the output <i>is</i> the state. Reaching the target "
            "means the state is at its final value. Nothing is left over. So it "
            "arrives and stops — always, for any input, at any gain.<br><br>"
            "Give the system a spring as well as a mass and you have somewhere "
            "to hide that surplus. That is the whole of the next page.", "key"))
        self.add(no)

        f = Card("the corner frequency, and where −3 dB comes from")
        f.add(math_label(r"G(j\omega) = \frac{K}{1 + j\omega\tau}, \qquad "
                         r"|G| = \frac{K}{\sqrt{1+(\omega\tau)^2}}, \qquad "
                         r"\angle G = -\arctan(\omega\tau)", 16))
        f.add(body(
            "At <b>ω = 1/τ</b> — the corner, and the same number as the pole — "
            "the magnitude is K/√2, which is <b>−3.01 dB</b>, and the phase is "
            "exactly <b>−45°</b>. That is the definition of bandwidth, and it is "
            "not arbitrary: half the power gets through.<br><br>"
            "Beyond the corner the magnitude falls at <b>−20 dB/decade</b> "
            "(a factor of 10 in frequency costs a factor of 10 in amplitude) and "
            "the phase heads for <b>−90° and stops</b>."))
        f.add(body(
            "<b>What that phase lag physically is.</b> Push the joint back and "
            "forth with a slow sinusoidal torque and the speed follows you "
            "almost exactly — friction dominates, and friction has no memory, so "
            "there is nothing to lag (0°). Now push very fast. The friction "
            "term never gets a chance to matter; the inertia takes over, and "
            "speed becomes the <i>integral</i> of your push. An integral of a "
            "sine peaks a <b>quarter cycle</b> after the sine does — that is "
            "90°, and it cannot get worse, because there is only one "
            "integration to do.<br><br>"
            "So the −90° asymptote is not a curve fit. It is \"one energy store "
            "= one integration = at most a quarter cycle of lag\".", dim=True))
        f.add(callout(
            "<b>That −90° ceiling is the most important fact on this page.</b> "
            "An oscillation needs the loop to return a signal exactly inverted "
            "— <b>−180°</b> — while the gain is still above 1. One pole can only "
            "ever supply 90°. So no matter how large you make the proportional "
            "gain, <b>a first-order plant with proportional feedback cannot be "
            "destabilised</b>. Infinite gain margin, provably.<br><br>"
            "Physically: to make something oscillate you have to push it in "
            "<i>exactly the wrong phase</i> — arriving to help just as it is "
            "heading the other way, a <b>half</b> cycle behind. One store buys "
            "you a quarter cycle. You are short by a quarter, and no amount of "
            "gain manufactures phase.<br><br>"
            "Which is why, when something you modelled as first order starts "
            "ringing, the model is wrong — there is a second energy store, a "
            "resonance, or a delay you have not accounted for. The ringing is "
            "information.", "key"))
        self.add(f)

        # ---- interactive 2 ---------------------------------------------
        i2 = Card("try to destabilise it — you cannot")
        i2.add(body(
            "Close a proportional loop around the first-order plant above and "
            "turn the gain up. The closed-loop pole is at "
            "−(1+K·K<sub>p</sub>)/τ — it only ever moves <b>further left</b>. "
            "Faster, and with less steady-state error, and never unstable. "
            "Enjoy it; this is the only plant in the tutor that behaves.",
            dim=True))
        self.s_kp = slider(1, 400, 20)           # x0.1
        self.l_kp = QLabel()
        i2.add_layout(slider_row("loop gain K_p (×0.1)", self.s_kp, self.l_kp))
        self.st_clp = Stat("closed-loop pole", "--", theme.ACCENT)
        self.st_ctau = Stat("closed-loop τ", "--", theme.GOOD)
        self.st_sse = Stat("steady-state error", "--", theme.WARN)
        self.st_crit = Stat("gain that destabilises", "--", theme.BAD)
        i2.add_layout(stat_row(self.st_clp, self.st_ctau, self.st_sse,
                               self.st_crit))
        self.c2 = MplCanvas(width=7.4, height=3.4, nrows=2)
        i2.add(self.c2)
        self.add(i2)
        self.s_kp.valueChanged.connect(self._redraw_loop)
        self._redraw_loop()

        c = Card("what it means for the robot in front of you")
        c.add(body(
            "&nbsp;&nbsp;• <b>The current loop is first order</b> (L/R), which is "
            "why it can be closed at 20 kHz with a plain PI and never argued "
            "about. It is the well-behaved layer everything else stands on.<br>"
            "&nbsp;&nbsp;• <b>A velocity loop on a rigid joint is first order</b> "
            "(J/b). Speed control is genuinely easy; position control is not, "
            "because integrating velocity adds a pole at the origin and that is "
            "a second-order system with a marginal pole in it.<br>"
            "&nbsp;&nbsp;• <b>Your sensors and filters are first order</b>, and "
            "each one hands the loop up to 90° of lag it did not previously "
            "have. Three innocent filters can hand over 270°, which is more "
            "than enough to oscillate. Filters are not free.<br>"
            "&nbsp;&nbsp;• <b>The rule of thumb</b>: a sensor filter should be "
            "5–10× faster than the loop bandwidth, or its pole is now part of "
            "your control problem."))
        self.add(c)

        self.add(callout(
            "<b>Carry forward.</b> One pole ⇒ one exponential, no overshoot, no "
            "oscillation, at most 90° of phase lag, infinite gain margin. Add "
            "the second pole on the next page and every one of those five "
            "statements breaks.", "good"))

        self.finish()

    # ------------------------------------------------------------------
    def _vals(self):
        return self.s_tau.value() / 1000.0, self.s_k.value() / 10.0

    def _redraw_step(self):
        tau, k = self._vals()
        self.l_tau.setText(f"{tau*1000:.0f} ms")
        self.l_k.setText(f"{k:.1f}")

        g = first_order(k, tau)
        dur = max(6 * tau, 0.05)
        t, y = step_response(g, dur, dur / 900.0)
        self.st_pole.set(f"{-1/tau:.1f} 1/s")
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
        # the initial slope, extended: "if the leak never grew" -- it always
        # crosses the final value at exactly t = tau
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

    def _redraw_loop(self):
        tau, k = self._vals()
        kp = self.s_kp.value() / 10.0
        self.l_kp.setText(f"{kp:.1f}")

        plant = first_order(k, tau)
        loop = plant * kp
        cl = loop.feedback()
        p = cl.poles()[0]
        tau_cl = -1.0 / p.real if p.real < 0 else math.inf
        dc = cl.dc_gain()
        self.st_clp.set(f"{p.real:.0f} 1/s")
        self.st_ctau.set(f"{tau_cl*1000:.1f} ms")
        self.st_sse.set(f"{(1-dc)*100:.1f}%")
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
        a1.plot([x * 1000 for x in t0], [v / max(k, 1e-9) for v in y0],
                color=theme.TEXT_FAINT, lw=1.3, ls="--",
                label="open loop (normalised)")
        a1.axhline(1.0, color=theme.TEXT_FAINT, lw=1.0, ls=":")
        a1.set_xlabel("time (ms)")
        a1.set_ylabel("y")
        c.legend(a1, loc="lower right")
        w, mag, ph = bode(loop, log_freqs(1.0, 1e5, 240))
        a2.semilogx(w, ph, color=theme.ACCENT, lw=2.0)
        a2.axhline(-180, color=theme.BAD, lw=1.2, ls=":",
                   label="−180°: unreachable with one pole")
        a2.axhline(-90, color=theme.WARN, lw=1.0, ls="--",
                   label="−90° asymptote")
        a2.set_ylim(-200, 5)
        a2.set_xlabel("ω (rad/s)")
        a2.set_ylabel("loop phase (deg)")
        c.legend(a2, loc="lower left")
        c.refresh()


# ==========================================================================
# PAGE -- second order
# ==========================================================================

class SecondOrderPage(Page):
    TITLE = "Second-Order Systems"
    SUBTITLE = ("Two poles, two energy stores, and the first system that can "
                "overshoot. Every robot joint you will ever tune is one of "
                "these.")
    SECTION = SECTION
    NOTES = "foundation"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>Add one thing to the last page: a second place to keep "
            "energy.</b><br><br>"
            "The joint on the previous page had a mass (which stores speed) and "
            "friction (which only drains). Bolt a spring to it. Now there are "
            "<b>two</b> stores — the mass holds <i>kinetic</i> energy, the "
            "spring holds <i>potential</i> energy — and, crucially, they can "
            "<b>hand it to each other</b>.<br><br>"
            "That handover is what oscillation physically <i>is</i>. Not a "
            "mathematical property of a quadratic; a literal sloshing of energy "
            "between two containers.", "key"))

        # ---- the physical mechanism ---------------------------------------
        ph = Card("watch the energy move — this is the whole page")
        ph.add(body(
            "Pull the joint 20° away from rest and let go. Follow the energy, "
            "not the angle:"))
        ph.add(body(
            "&nbsp;&nbsp;<b>1.</b> At full deflection: the spring is stretched, "
            "so all the energy is <b>potential</b>. The joint is not moving — "
            "zero kinetic.<br>"
            "&nbsp;&nbsp;<b>2.</b> The spring pulls it back. Potential drains, "
            "kinetic fills. The joint speeds up.<br>"
            "&nbsp;&nbsp;<b>3.</b> It passes through the rest position. The "
            "spring is now relaxed — <b>zero potential</b> — so all the energy "
            "has become <b>kinetic</b>. Which means this is the moment it is "
            "moving <b>fastest</b>.<br>"
            "&nbsp;&nbsp;<b>4.</b> And that is the answer. <b>It cannot stop "
            "at its destination, because it arrives there at maximum "
            "speed.</b> It sails through and starts compressing the spring on "
            "the far side.<br>"
            "&nbsp;&nbsp;<b>5.</b> Kinetic drains back into potential until it "
            "stops — overshot — and the whole thing runs in reverse."))
        ph.add(callout(
            "<b>Overshoot is momentum, and momentum is energy hiding in the "
            "other store.</b><br><br>"
            "That is exactly what the previous page said was impossible with one "
            "store: reaching the target means the state is at its final value, "
            "with nothing left over. Here, reaching the target means the "
            "<i>spring</i> is at its final value while the <i>mass</i> is still "
            "carrying everything. Something is left over, and it is left over "
            "somewhere you were not looking.<br><br>"
            "Every overshoot you have ever seen on a robot is this. Every "
            "oscillation is energy that has nowhere to go and two places to "
            "be.", "key"))
        ph.add(body(
            "<b>Now add the damper back in.</b> It does not participate in the "
            "trade — it only takes. Each pass, some of the energy leaves as "
            "heat, so the amount being handed back and forth shrinks, and the "
            "swings get smaller. The three regimes everyone memorises are just "
            "three answers to \"how much does the damper steal per swing?\"",
            dim=True))
        self.add(ph)

        # ---- energy trade interactive --------------------------------------
        ie = Card("see the trade: release it from 20° and watch the two stores")
        ie.add(body(
            "Left: the angle. Right: where the energy actually is. Blue is "
            "stored in the <b>spring</b>, orange is carried by the <b>mass</b>, "
            "and the pale line is the total — everything the damper has not yet "
            "turned into heat.<br><br>"
            "<b>Start at ζ = 0.</b> The two curves swap perfectly and the total "
            "is a flat line: nothing is lost, so it rings forever. Every time "
            "the angle crosses zero, the spring's energy is zero and the mass "
            "holds all of it — that peak in the orange curve <i>is</i> the "
            "overshoot, before it happens.<br><br>"
            "<b>Now raise ζ.</b> The total starts falling. At ζ = 1 the trade "
            "barely completes once: the damper drains the spring before enough "
            "of it can become speed, so the mass never gets the momentum to "
            "carry past. That is critical damping, and it is an energy "
            "statement, not a root-locus one.", dim=True))
        self.s_ze = slider(0, 250, 30)           # x0.01
        self.l_ze = QLabel()
        ie.add_layout(slider_row("damping ζ (×0.01)", self.s_ze, self.l_ze))
        self.st_lost = Stat("energy left after one swing", "--", theme.VIOLET)
        self.st_cross = Stat("zero crossings", "--", theme.WARN)
        self.st_peakke = Stat("peak kinetic share", "--", theme.ACCENT)
        self.st_reg = Stat("regime", "--", theme.GOOD)
        ie.add_layout(stat_row(self.st_lost, self.st_cross, self.st_peakke,
                               self.st_reg))
        self.ce = MplCanvas(width=7.4, height=3.0, ncols=2)
        ie.add(self.ce)
        self.add(ie)
        self.s_ze.valueChanged.connect(self._redraw_energy)
        self._redraw_energy()

        # ---- the equation, built from the picture -------------------------
        e = Card("the equation is those three sentences, written down")
        e.add(math_label(r"J\ddot\theta + B\dot\theta + K\theta = \tau", 18))
        e.add(body(
            "&nbsp;&nbsp;<b>J θ̈</b> — the <b>mass</b>. Stores kinetic energy; "
            "resists changes of speed. This is the store the previous page "
            "had.<br>"
            "&nbsp;&nbsp;<b>K θ</b> — the <b>spring</b>. Stores potential "
            "energy; pulls harder the further you are from rest. <b>This term is "
            "the new one, and it is the entire difference between the two "
            "pages.</b><br>"
            "&nbsp;&nbsp;<b>B θ̇</b> — the <b>damper</b>. Stores nothing; "
            "converts motion into heat, in proportion to speed.<br>"
            "&nbsp;&nbsp;<b>τ</b> — what you push with."))
        e.add(body(
            "Delete the K term and you are back to the first-order joint: one "
            "store, one leak, no overshoot. Delete the B term and nothing ever "
            "removes energy, so it rings forever. <b>The interesting behaviour "
            "lives entirely in the ratio between those two.</b>", dim=True))
        e.add(body("Divide through by J and the three physical parameters "
                   "collapse into two more useful ones:"))
        e.add(math_label(r"G(s) = \frac{\omega_n^2}{s^2 + 2\zeta\omega_n s "
                         r"+ \omega_n^2}, \qquad "
                         r"\omega_n = \sqrt{K/J}, \qquad "
                         r"\zeta = \frac{B}{2\sqrt{KJ}}", 17))
        e.add(body(
            "<b>ω<sub>n</sub> — how fast the energy sloshes.</b> Read "
            "√(K/J) physically: a <i>stiffer</i> spring hands the energy back "
            "faster, so the trade happens quicker; a <i>heavier</i> mass takes "
            "longer to turn around, so it happens slower. ω<sub>n</sub> is "
            "literally the rate of that handover, in rad/s — and it is the "
            "frequency the joint would ring at with <b>no damper at all</b>."))
        e.add(body(
            "<b>ζ — what fraction of the sloshing the damper eats.</b> This one "
            "is worth unpacking, because \"damping ratio\" hides a ratio of "
            "<i>what</i> to <i>what</i>. The bottom of that fraction, "
            "2√(KJ), is not arbitrary — it is <b>exactly the amount of damping "
            "that would just barely stop the trade from happening at all</b>. "
            "So:"))
        e.add(math_label(r"\zeta = \frac{B}{2\sqrt{KJ}} "
                         r"= \frac{\text{the damping you have}}"
                         r"{\text{the damping that would just kill the "
                         r"oscillation}}", 15))
        e.add(body(
            "It is dimensionless because it compares damping with damping. "
            "ζ = 0.3 means \"I have 30% of the damping needed to suppress the "
            "sloshing entirely\", which is why it, and not B, predicts the "
            "overshoot.<br><br>"
            "<b>The same number, read a second way: how much the damper steals "
            "per swing.</b> Successive <i>peaks</i> shrink by a fixed factor "
            "every cycle — that is the logarithmic decrement:"))
        e.add(math_label(r"\frac{\theta_{k+1}}{\theta_k} "
                         r"= e^{-2\pi\zeta/\sqrt{1-\zeta^2}}, \qquad "
                         r"\frac{E_{k+1}}{E_k} "
                         r"= e^{-4\pi\zeta/\sqrt{1-\zeta^2}}", 16))
        e.add(body(
            "Energy carries the <b>square</b> of the amplitude, so it falls "
            "twice as fast in the exponent — which is why the widget above "
            "reports 28% of the energy surviving one swing at ζ = 0.1, while "
            "the <i>amplitude</i> at that ζ is still 53% of what it was. Both "
            "numbers are correct; they are measuring different things, and "
            "confusing them is a standard way to misread a decay trace.",
            dim=True))
        e.add(callout(
            "<b>This is the impedance-control connection, and it is exact.</b> "
            "When you chose K and B on the Impedance Control page you were not "
            "choosing \"stiffness and damping\" — you were choosing "
            "ω<sub>n</sub> and ζ, and therefore the overshoot and the settling "
            "time, whether or not you meant to.<br><br>"
            "And note the trap in the formulas: <b>double K alone</b> and "
            "ω<sub>n</sub> rises by √2 while ζ <b>falls</b> by √2. Stiffening a "
            "joint without raising B always makes it ring more. That is the "
            "most common impedance-tuning mistake there is, and it is visible "
            "right there in the algebra.", "warn"))
        self.add(e)

        r = Card("the five regimes, as energy accounting")
        r.add(body(
            "Every one of these is the same question — <b>can the spring get "
            "enough energy into the mass, before the damper takes it, for the "
            "mass to carry past the target?</b>"))
        r.add(body(
            "<table cellpadding='7'>"
            "<tr><td><b>ζ &lt; 0</b></td>"
            "<td>Something <i>adds</i> energy every swing instead of removing "
            "it — negative damping. The trade continues and grows. "
            "<b>Unstable.</b> Physically real: a controller feeding back with "
            "the wrong sign, or a delay that makes a correction arrive as a "
            "push.</td></tr>"
            "<tr><td><b>ζ = 0</b></td>"
            "<td>Nothing takes anything. The energy trades perfectly, forever. "
            "<b>Marginal.</b> An undamped SEA spring, or a frictionless "
            "joint.</td></tr>"
            "<tr><td><b>0 &lt; ζ &lt; 1</b></td>"
            "<td>The damper takes a slice each swing, but not enough to stop "
            "the trade. It rings, and each ring is smaller. "
            "<b>Underdamped</b> — and this is where nearly every real robot "
            "joint lives.</td></tr>"
            "<tr><td><b>ζ = 1</b></td>"
            "<td>The damper takes it at exactly the rate the spring can hand it "
            "over. The mass never accumulates enough speed to overshoot — not "
            "even slightly — and it gets home as fast as that allows. "
            "<b>Critically damped</b>: the fastest arrival with no "
            "overshoot.</td></tr>"
            "<tr><td><b>ζ &gt; 1</b></td>"
            "<td>The damper is greedier than the spring is generous. Most of "
            "the potential energy leaves as heat before it can become motion, "
            "so the joint <i>oozes</i> home. <b>Overdamped</b> — and slower "
            "than critical, which surprises people who assume more damping is "
            "safer.</td></tr>"
            "</table>"))
        r.add(body(
            "Note what is <i>not</i> in that table: ω<sub>n</sub>. The regime is "
            "decided entirely by ζ. ω<sub>n</sub> only sets how fast the whole "
            "story plays out.", dim=True))
        self.add(r)

        p = Card("where the poles are — and why the picture looks like that")
        p.add(math_label(r"s = -\zeta\omega_n \pm j\,\omega_n\sqrt{1-\zeta^2}",
                         17))
        p.add(body(
            "The previous page said the two axes of the s-plane are two physical "
            "rates: <b>horizontal = how fast it dies, vertical = how fast it "
            "wiggles</b>. A first-order pole had nothing to wiggle with and sat "
            "on the axis. Now there are two stores trading, so the pole lifts "
            "off — and each part of that expression is one of those rates:"))
        p.add(body(
            "&nbsp;&nbsp;• <b>Real part = −ζω<sub>n</sub></b> — the decay rate. "
            "How fast the damper is draining the total. It is exactly the "
            "\"pole = leak/store\" of the previous page, and settling time "
            "depends on it and nothing else.<br>"
            "&nbsp;&nbsp;• <b>Imaginary part = ω<sub>d</sub> = "
            "ω<sub>n</sub>√(1−ζ²)</b> — the rate the energy is actually "
            "sloshing. Note it is <i>slower</i> than ω<sub>n</sub>: the damper "
            "is stealing energy mid-trade, so each round trip takes longer. "
            "This is the frequency you hear.<br>"
            "&nbsp;&nbsp;• <b>Distance from the origin = ω<sub>n</sub></b> — "
            "Pythagoras on the two above. The poles ride a circle of radius "
            "ω<sub>n</sub>, so changing ζ alone slides them <i>around</i> that "
            "circle without changing how energetic the system is, only how the "
            "energy is split between dying and wiggling.<br>"
            "&nbsp;&nbsp;• <b>Angle from the negative real axis = arccos ζ</b> — "
            "therefore the angle <i>is</i> the damping. Straight left on the "
            "axis is ζ = 1 (all decay, no wiggle); straight up is ζ = 0 (all "
            "wiggle, no decay); 45° is ζ = 0.707."))
        p.add(callout(
            "<b>So a pole plot is a picture of how a system spends its "
            "energy.</b> How far left = how fast it gives it up. How far up = "
            "how fast it passes it back and forth. That is the whole reason "
            "experienced people read pole plots instead of step responses — the "
            "two things you care about are on two perpendicular axes instead of "
            "tangled together in one curve.", "key"))
        p.add(body(
            "<table cellpadding='6'>"
            "<tr><td><b>ζ &lt; 0</b></td><td>poles in the RIGHT half plane</td>"
            "<td><b>unstable</b> — growing oscillation</td></tr>"
            "<tr><td><b>ζ = 0</b></td><td>poles exactly on the jω axis</td>"
            "<td><b>marginal</b> — rings forever. An undamped SEA spring.</td></tr>"
            "<tr><td><b>0 &lt; ζ &lt; 1</b></td><td>complex pair, left half</td>"
            "<td><b>underdamped</b> — overshoots, then settles</td></tr>"
            "<tr><td><b>ζ = 1</b></td><td>two equal real poles</td>"
            "<td><b>critically damped</b> — fastest with no overshoot</td></tr>"
            "<tr><td><b>ζ &gt; 1</b></td><td>two distinct real poles</td>"
            "<td><b>overdamped</b> — the slow pole dominates; sluggish</td></tr>"
            "</table>"))
        self.add(p)

        m = Card("the four formulas you will actually use")
        m.add(math_label(r"M_p = e^{-\pi\zeta/\sqrt{1-\zeta^2}} \qquad "
                         r"t_s \approx \frac{4}{\zeta\omega_n} \qquad "
                         r"t_p = \frac{\pi}{\omega_d} \qquad "
                         r"\omega_d = \omega_n\sqrt{1-\zeta^2}", 16))
        m.add(body(
            "<b>Overshoot depends only on ζ.</b> Not on ω<sub>n</sub>, not on "
            "the plant, not on how big the step was. ζ = 0.1 → 73%, 0.3 → 37%, "
            "0.5 → 16%, <b>0.707 → 4.3%</b>, 1.0 → 0%.<br><br>"
            "<b>Settling time depends only on the real part.</b> ζω<sub>n</sub> "
            "is the distance the poles sit to the left of the axis, and "
            "t<sub>s</sub> ≈ 4 divided by it. So \"faster\" and \"less "
            "overshoot\" are <i>separate</i> knobs — which is why \"it "
            "overshoots, so slow it down\" is bad advice. Raise ζ, keep "
            "ω<sub>n</sub>, and you get both."))
        m.add(body(
            "<b>Why ζ = 0.707 is everywhere.</b> It is the value at which the "
            "closed-loop magnitude response has <i>no peak at all</i> — "
            "maximally flat — while still being as fast as possible. Below it "
            "you get a resonant bump that amplifies disturbances at that "
            "frequency; above it you are just being slow. 0.707 in analysis, "
            "0.8–1.0 in a real robot where you would rather not overshoot into "
            "a person.", dim=True))
        self.add(m)

        # ---- interactive 1 ---------------------------------------------
        i = Card("ζ and ω_n, and the pole pair they place")
        i.add(body(
            "Watch the poles ride the circle as you change ζ, and the circle "
            "grow as you change ω<sub>n</sub>. Cross ζ = 0 and the poles cross "
            "into the red.", dim=True))
        self.s_z = slider(-20, 200, 70)          # x0.01
        self.s_wn = slider(5, 400, 100)          # x0.1 rad/s
        self.l_z, self.l_wn = QLabel(), QLabel()
        i.add_layout(slider_row("damping ζ (×0.01)", self.s_z, self.l_z))
        i.add_layout(slider_row("ω_n (×0.1 rad/s)", self.s_wn, self.l_wn))
        self.st_mp = Stat("overshoot", "--", theme.WARN)
        self.st_ts = Stat("settling (2%)", "--", theme.GOOD)
        self.st_wd = Stat("ring freq", "--", theme.VIOLET)
        self.st_peak = Stat("resonant peak", "--", theme.ACCENT)
        i.add_layout(stat_row(self.st_mp, self.st_ts, self.st_wd, self.st_peak))
        self.c1 = MplCanvas(width=7.4, height=3.0, ncols=2)
        i.add(self.c1)
        self.add(i)
        for s in (self.s_z, self.s_wn):
            s.valueChanged.connect(self._redraw_zeta)
        self._redraw_zeta()

        # ---- interactive 2 ---------------------------------------------
        self.add(hline())
        self.add(title("The same thing, in the units you actually tune"))

        i2 = Card("J, K and B — and the ω_n, ζ they secretly are")
        i2.add(body(
            "This is the previous widget with the physical parameters on the "
            "front. Raise <b>K alone</b> and watch ζ fall and the overshoot "
            "grow — the mistake described above, made visible. Then raise B to "
            "put it back.", dim=True))
        self.s_j = slider(2, 100, 25)            # x0.01 kg m^2
        self.s_kk = slider(5, 600, 100)          # N m / rad
        self.s_bb = slider(0, 200, 40)           # x0.1 N m s / rad
        self.l_j, self.l_kk, self.l_bb = QLabel(), QLabel(), QLabel()
        i2.add_layout(slider_row("inertia J (×0.01)", self.s_j, self.l_j))
        i2.add_layout(slider_row("stiffness K", self.s_kk, self.l_kk))
        i2.add_layout(slider_row("damping B (×0.1)", self.s_bb, self.l_bb))
        self.st_wn2 = Stat("ω_n", "--", theme.ACCENT)
        self.st_z2 = Stat("ζ", "--", theme.VIOLET)
        self.st_mp2 = Stat("overshoot", "--", theme.WARN)
        self.st_ts2 = Stat("settling", "--", theme.GOOD)
        i2.add_layout(stat_row(self.st_wn2, self.st_z2, self.st_mp2,
                               self.st_ts2))
        self.c2 = MplCanvas(width=7.4, height=2.7)
        i2.add(self.c2)
        self.add(i2)
        for s in (self.s_j, self.s_kk, self.s_bb):
            s.valueChanged.connect(self._redraw_joint)
        self._redraw_joint()

        u = Card("why second order is the universal model")
        u.add(body(
            "It is not that the world happens to be second order. It is that "
            "<b>a mass with a spring and a damper is what a controlled joint "
            "becomes</b>. Close a PD loop around a rigid inertia:"))
        u.add(math_label(r"J\ddot\theta + b\dot\theta = "
                         r"-K_p\theta - K_d\dot\theta "
                         r"\;\Longrightarrow\; "
                         r"J\ddot\theta + (b + K_d)\dot\theta + K_p\theta = 0",
                         16))
        u.add(body(
            "Identical form. Your <b>proportional gain became the spring</b> and "
            "your <b>derivative gain became the damper</b>. That is not an "
            "analogy — it is the same differential equation, so"))
        u.add(math_label(r"\omega_n = \sqrt{K_p/J}, \qquad "
                         r"\zeta = \frac{b + K_d}{2\sqrt{K_p J}}", 16))
        u.add(body(
            "…which is a complete PD tuning recipe. Want ω<sub>n</sub> = 20 "
            "rad/s and ζ = 0.8 on J = 0.25 kg·m² with b = 0.4? Then "
            "K<sub>p</sub> = Jω<sub>n</sub>² = <b>100</b> and "
            "K<sub>d</sub> = 2ζω<sub>n</sub>J − b = <b>7.6</b>. No trial and "
            "error, no twiddling.", dim=True))
        self.add(u)

        self.add(callout(
            "<b>And here is the fact that surprises people.</b> A pure "
            "second-order plant <i>still</i> cannot be destabilised by "
            "proportional feedback. Two poles supply at most 180° of phase lag "
            "and only reach it asymptotically, so |L| has fallen far below 1 by "
            "the time the phase gets there.<br><br>"
            "You need a <b>third</b> pole, or a <b>delay</b>, or a "
            "<b>resonance</b> to make a loop oscillate. Which is exactly why "
            "the Real-Time page mattered: your loop delay is the thing that "
            "turns a well-behaved second-order joint into one that rings. Real "
            "instabilities are almost never the plant's fault — they are the "
            "implementation's.", "warn"))

        self.finish()

    # ------------------------------------------------------------------
    def _redraw_energy(self):
        """
        Free release from 20 degrees, integrated directly in (theta, omega) so
        the two energy stores are the actual state variables rather than
        something recovered from a canonical form. J = 1, so K = wn^2 and
        B = 2*zeta*wn.
        """
        z = self.s_ze.value() / 100.0
        self.l_ze.setText(f"{z:.2f}")
        wn = 10.0
        k, b = wn * wn, 2.0 * z * wn

        th, w = math.radians(20.0), 0.0
        dt, dur = 2e-3, 1.6
        ts, ths, ke, pe = [], [], [], []

        def acc(x, v):
            return -b * v - k * x

        for i in range(int(dur / dt)):
            ts.append(i * dt)
            ths.append(th)
            ke.append(0.5 * w * w)
            pe.append(0.5 * k * th * th)
            k1a, k1b = w, acc(th, w)
            k2a, k2b = w + dt / 2 * k1b, acc(th + dt / 2 * k1a, w + dt / 2 * k1b)
            k3a, k3b = w + dt / 2 * k2b, acc(th + dt / 2 * k2a, w + dt / 2 * k2b)
            k4a, k4b = w + dt * k3b, acc(th + dt * k3a, w + dt * k3b)
            th += dt / 6 * (k1a + 2 * k2a + 2 * k3a + k4a)
            w += dt / 6 * (k1b + 2 * k2b + 2 * k3b + k4b)

        total = [a + p for a, p in zip(ke, pe)]
        e0 = total[0]
        # "how much does the damper steal per swing" -- the energy still in the
        # system one full damped period later, which is the number the prose
        # above is about
        if z < 1.0:
            t_swing = 2 * math.pi / (wn * math.sqrt(1 - z * z))
            idx = min(int(t_swing / dt), len(total) - 1)
            self.st_lost.set(f"{total[idx]/e0*100:.1f}%")
        else:
            self.st_lost.set("no swing")
        crossings = sum(1 for a, b_ in zip(ths, ths[1:]) if a * b_ < 0)
        self.st_cross.set(str(crossings))
        self.st_peakke.set(f"{max(k_ / e0 for k_ in ke)*100:.0f}%")
        if z <= 0.001:
            reg, col = "undamped", theme.BAD
        elif z < 0.999:
            reg, col = "underdamped", theme.WARN if z < 0.5 else theme.GOOD
        elif z < 1.001:
            reg, col = "critical", theme.GOOD
        else:
            reg, col = "overdamped", theme.WARN
        self.st_reg.set(reg)
        self.st_reg.set_color(col)

        c = self.ce
        c.clear()
        a1, a2 = c.axes
        a1.plot(ts, [math.degrees(x) for x in ths], color=theme.ACCENT, lw=2.0)
        a1.axhline(0, color=theme.TEXT_FAINT, lw=1.1, ls="--", label="rest")
        a1.set_xlabel("time (s)")
        a1.set_ylabel("θ (°)")
        a1.set_title("the angle", fontsize=9)
        c.legend(a1, loc="upper right")
        a2.plot(ts, pe, color=theme.ACCENT, lw=1.7, label="spring (potential)")
        a2.plot(ts, ke, color=theme.WARN, lw=1.7, label="mass (kinetic)")
        a2.plot(ts, total, color=theme.TEXT_FAINT, lw=1.5, ls="--",
                label="total — the rest is heat")
        a2.set_xlabel("time (s)")
        a2.set_ylabel("energy (J, per unit inertia)")
        a2.set_title("where the energy is", fontsize=9)
        c.legend(a2, loc="upper right")
        c.refresh()

    # ------------------------------------------------------------------
    def _redraw_zeta(self):
        z = self.s_z.value() / 100.0
        wn = self.s_wn.value() / 10.0
        self.l_z.setText(f"{z:.2f}")
        self.l_wn.setText(f"{wn:.1f} rad/s")

        g = second_order(wn, z)
        dur = 10.0 / max(abs(z) * wn, wn / 8.0)
        dur = min(max(dur, 0.3), 8.0)
        t, y = step_response(g, dur, dur / 1000.0)
        self.st_mp.set("—" if z <= 0 else f"{overshoot_fraction(z)*100:.0f}%")
        self.st_mp.set_color(theme.BAD if z <= 0.2 else theme.WARN)
        self.st_ts.set("never" if z <= 0 else f"{settling_time(z, wn):.2f} s")
        wd = damped_frequency(z, wn)
        self.st_wd.set("—" if wd <= 0 else f"{wd/(2*math.pi):.2f} Hz")
        pk = resonant_peak_db(z) if z > 0 else math.inf
        self.st_peak.set("∞" if not math.isfinite(pk) else
                         ("none" if pk <= 0 else f"{pk:.1f} dB"))

        c = self.c1
        c.clear()
        a1, a2 = c.axes
        a1.plot(t, y, color=theme.ACCENT if z > 0 else theme.BAD, lw=2.2)
        a1.axhline(1.0, color=theme.TEXT_FAINT, lw=1.1, ls="--")
        if 0 < z < 1:
            a1.axhline(1 + overshoot_fraction(z), color=theme.WARN, lw=1.0,
                       ls=":", label="predicted peak")
            a1.axvline(peak_time(z, wn), color=theme.WARN, lw=1.0, ls=":")
            c.legend(a1, loc="lower right")
        a1.set_xlabel("time (s)")
        a1.set_ylabel("θ")
        a1.set_title("step response", fontsize=9)
        lim = wn * 1.5
        _splane(a2, g.poles(), lim=lim)
        if 0 < z < 1:
            ang = math.acos(min(1.0, z))
            a2.plot([0, -lim * math.cos(ang)], [0, lim * math.sin(ang)],
                    color=theme.VIOLET, lw=1.0, ls=":")
            a2.plot([0, -lim * math.cos(ang)], [0, -lim * math.sin(ang)],
                    color=theme.VIOLET, lw=1.0, ls=":")
            th = [i * math.pi / 60 for i in range(121)]
            a2.plot([wn * math.cos(math.pi / 2 + a) for a in th],
                    [wn * math.sin(math.pi / 2 + a) for a in th],
                    color=theme.TEXT_FAINT, lw=0.8, ls="--")
        a2.set_title("s-plane: radius = ω_n, angle = arccos ζ", fontsize=8.5)
        c.refresh()

    def _redraw_joint(self):
        j = self.s_j.value() / 100.0
        k = float(self.s_kk.value())
        b = self.s_bb.value() / 10.0
        self.l_j.setText(f"{j:.2f} kg·m²")
        self.l_kk.setText(f"{k:.0f}")
        self.l_bb.setText(f"{b:.1f}")

        wn, z = joint_wn_zeta(k, b, j)
        self.st_wn2.set(f"{wn:.1f} rad/s")
        self.st_z2.set(f"{z:.2f}")
        self.st_z2.set_color(theme.GOOD if 0.6 <= z <= 1.2 else theme.WARN)
        self.st_mp2.set(f"{overshoot_fraction(z)*100:.0f}%")
        self.st_ts2.set("∞" if z <= 0 else f"{settling_time(z, wn):.2f} s")

        g = TF([k], [j, b, k])
        dur = min(max(10.0 / max(z * wn, wn / 8.0), 0.3), 8.0)
        t, y = step_response(g, dur, dur / 1000.0)
        c = self.c2
        c.clear()
        c.ax.plot(t, y, color=theme.GOOD, lw=2.2, label="this J, K, B")
        c.ax.axhline(1.0, color=theme.TEXT_FAINT, lw=1.1, ls="--")
        g2 = TF([2 * k], [j, b, 2 * k])
        t2, y2 = step_response(g2, dur, dur / 1000.0)
        c.ax.plot(t2, y2, color=theme.BAD, lw=1.5, ls="--",
                  label="K doubled, B unchanged")
        c.ax.set_xlabel("time (s)")
        c.ax.set_ylabel("θ (normalised)")
        c.legend(loc="lower right")
        c.refresh()


# ==========================================================================
# PAGE -- stability
# ==========================================================================

class StabilityPage(Page):
    TITLE = "Stability & How to Check It"
    SUBTITLE = ("What \"stable\" is a statement about, why marginal is its own "
                "category, and three ways to decide without guessing.")
    SECTION = SECTION
    NOTES = "foundation"

    def __init__(self, parent=None):
        super().__init__(parent)

        d = Card("the definition, and it is narrower than the word suggests")
        d.add(body(
            "<b>BIBO stability:</b> every <i>bounded</i> input produces a "
            "<i>bounded</i> output. For a linear time-invariant system that is "
            "equivalent to one geometric statement:"))
        d.add(title("Every pole has a strictly negative real part.", 16))
        d.add(body(
            "\"Strictly\" is load-bearing. A pole exactly on the imaginary axis "
            "is not a mild case of stable — it is a different category with "
            "different failure behaviour, and it is extremely common in "
            "robotics."))
        d.add(body(
            "<table cellpadding='6'>"
            "<tr><td><b>Pole</b></td><td><b>Time response</b></td>"
            "<td><b>Verdict</b></td><td><b>Where you meet it</b></td></tr>"
            "<tr><td>s = −a (a&gt;0)</td><td>e<sup>−at</sup>, decays</td>"
            "<td style='color:#3fb950'>stable</td><td>any damped mode</td></tr>"
            "<tr><td>−σ ± jω</td><td>e<sup>−σt</sup>cos ωt, rings down</td>"
            "<td style='color:#3fb950'>stable</td><td>a joint under PD</td></tr>"
            "<tr><td>s = 0</td><td>constant — never returns</td>"
            "<td style='color:#d29922'>marginal</td>"
            "<td>a free joint: torque in, position drifts</td></tr>"
            "<tr><td>±jω</td><td>cos ωt, rings forever</td>"
            "<td style='color:#d29922'>marginal</td>"
            "<td>an undamped SEA spring, a frictionless pendulum</td></tr>"
            "<tr><td>s = +a</td><td>e<sup>+at</sup>, grows</td>"
            "<td style='color:#f85149'>unstable</td>"
            "<td>an inverted pendulum — every biped</td></tr>"
            "<tr><td>repeated s = 0</td><td>t, ramps away</td>"
            "<td style='color:#f85149'>unstable</td>"
            "<td>a double integrator: J θ̈ = τ with no friction</td></tr>"
            "</table>"))
        self.add(d)

        self.add(callout(
            "<b>Marginal is not \"almost stable\", it is \"nothing decides\".</b> "
            "A marginal system neither recovers from a disturbance nor "
            "diverges from it — it keeps whatever you gave it, forever. In "
            "practice that means the tiniest unmodelled term picks the outcome, "
            "and you have handed the decision to noise.<br><br>"
            "It is also the normal state of robot hardware. A joint with "
            "negligible friction <i>is</i> a double integrator; a good SEA "
            "spring <i>is</i> nearly undamped. Feedback is not there to improve "
            "an already-stable machine — it is there to <b>move those poles off "
            "the axis</b>, which is the entire job.", "warn"))

        # ---- interactive 1 ---------------------------------------------
        i = Card("place the poles yourself and watch the taxonomy")
        i.add(body(
            "One complex pair. Slide the real part through zero and you have "
            "walked the whole table above in one gesture — decaying, ringing "
            "forever, growing.", dim=True))
        self.s_re = slider(-60, 30, -20)         # x0.1
        self.s_im = slider(0, 300, 100)          # x0.1
        self.l_re, self.l_im = QLabel(), QLabel()
        i.add_layout(slider_row("real part σ (×0.1)", self.s_re, self.l_re))
        i.add_layout(slider_row("imag part ω (×0.1)", self.s_im, self.l_im))
        self.st_verdict = Stat("verdict", "--", theme.GOOD)
        self.st_zz = Stat("ζ", "--", theme.VIOLET)
        self.st_wnn = Stat("ω_n", "--", theme.ACCENT)
        self.st_half = Stat("halving / doubling time", "--", theme.WARN)
        i.add_layout(stat_row(self.st_verdict, self.st_zz, self.st_wnn,
                              self.st_half))
        self.c1 = MplCanvas(width=7.4, height=3.0, ncols=2)
        i.add(self.c1)
        self.add(i)
        for s in (self.s_re, self.s_im):
            s.valueChanged.connect(self._redraw_poles)
        self._redraw_poles()

        # ---- how to check ----------------------------------------------
        self.add(hline())
        self.add(title("Four ways to check, in the order you would reach for "
                       "them"))

        h = Card("the methods, and what each is actually for")
        h.add(body(
            "<b>1 · Compute the roots.</b> If you have the closed-loop "
            "polynomial, factor it. Exact, trivial on a computer, and useless "
            "for design because it tells you the answer for <i>one</i> set of "
            "gains and nothing about the neighbouring ones.<br><br>"
            "<b>2 · Routh–Hurwitz.</b> Decide the same question <i>without</i> "
            "computing a single root, using only the coefficients. Its real "
            "value today is not speed — it is that the entries stay "
            "<b>symbolic in your gain</b>, so you can solve for the exact gain "
            "at which stability is lost instead of hunting for it.<br><br>"
            "<b>3 · Frequency margins (Bode / Nyquist).</b> The only method "
            "that works on a plant you <i>measured</i> rather than modelled — "
            "and the only one that tells you how much room you have left. Next "
            "two pages.<br><br>"
            "<b>4 · Lyapunov.</b> Works when the system is nonlinear and has no "
            "poles at all. Find an energy-like function that can only decrease. "
            "Covered on the nonlinear pages."))
        self.add(h)

        r = Card("Routh–Hurwitz, worked")
        r.add(body(
            "Write the closed-loop characteristic polynomial, list the "
            "coefficients in two alternating rows, then cross-multiply "
            "downwards. <b>The number of sign changes in the first column is "
            "the number of poles in the right half plane.</b> Zero sign changes "
            "means stable, and you knew it without factoring anything."))
        r.add(body(
            "The classic worked example, which is also the standard cautionary "
            "tale about proportional gain:"))
        r.add(math_label(r"L(s) = \frac{K}{s(s+1)(s+2)} \quad\Longrightarrow"
                         r"\quad s^3 + 3s^2 + 2s + K = 0", 16))
        r.add(body(
            "The first column comes out as 1, 3, (6−K)/3, K. For every entry to "
            "stay positive you need <b>0 &lt; K &lt; 6</b>. At exactly K = 6 a "
            "whole row goes to zero — the signature of a pole pair sitting "
            "<i>on</i> the imaginary axis — and the loop oscillates at "
            "ω = √2 rad/s forever.<br><br>"
            "That number, 6, is a design fact you obtained algebraically. No "
            "simulation, no sweep. And notice the shape of the result: a "
            "third-order loop has a <b>maximum</b> usable gain. The first- and "
            "second-order plants of the last two pages did not.", dim=True))
        self.add(r)

        # ---- interactive 2 ---------------------------------------------
        i2 = Card("build a cubic and let Routh judge it")
        i2.add(body(
            "Coefficients of s³ + a₂s² + a₁s + a₀. The Routh column and the "
            "actual roots are computed independently — they always agree, which "
            "is the point.", dim=True))
        self.s_a2 = slider(-40, 100, 30)         # x0.1
        self.s_a1 = slider(-40, 100, 20)         # x0.1
        self.s_a0 = slider(-40, 200, 10)         # x0.1
        self.l_a2, self.l_a1, self.l_a0 = QLabel(), QLabel(), QLabel()
        i2.add_layout(slider_row("a₂ (×0.1)", self.s_a2, self.l_a2))
        i2.add_layout(slider_row("a₁ (×0.1)", self.s_a1, self.l_a1))
        i2.add_layout(slider_row("a₀ (×0.1)", self.s_a0, self.l_a0))
        self.st_rhp = Stat("RHP poles (Routh)", "--", theme.BAD)
        self.st_rhp2 = Stat("RHP poles (roots)", "--", theme.ACCENT)
        self.st_class = Stat("classification", "--", theme.GOOD)
        i2.add_layout(stat_row(self.st_rhp, self.st_rhp2, self.st_class))
        self.lbl_routh = body("", dim=True)
        i2.add(self.lbl_routh)
        self.c2 = MplCanvas(width=7.4, height=2.8, ncols=2)
        i2.add(self.c2)
        self.add(i2)
        for s in (self.s_a2, self.s_a1, self.s_a0):
            s.valueChanged.connect(self._redraw_routh)
        self._redraw_routh()

        self.add(callout(
            "<b>Necessary, not sufficient — and this is where beginners stop "
            "too early.</b> \"Stable\" only promises the response is bounded. "
            "It says nothing about whether the robot settles in 50 ms or 50 "
            "seconds, whether it overshoots into the person standing next to "
            "it, or whether it is still stable when the payload changes.<br><br>"
            "A controller sitting one decimal place from the stability boundary "
            "is stable and worthless. That is why the rest of this section is "
            "about <b>margins</b> — not \"is it stable\" but \"how much would "
            "have to be wrong before it is not\".", "key"))

        self.finish()

    # ------------------------------------------------------------------
    def _redraw_poles(self):
        sig = self.s_re.value() / 10.0
        om = self.s_im.value() / 10.0
        self.l_re.setText(f"{sig:+.1f}")
        self.l_im.setText(f"{om:.1f}")

        poles = [complex(sig, om), complex(sig, -om)]
        wn = math.hypot(sig, om)
        z = (-sig / wn) if wn > 1e-9 else 0.0
        if sig < -1e-6:
            verdict, col = "stable", theme.GOOD
        elif sig > 1e-6:
            verdict, col = "UNSTABLE", theme.BAD
        else:
            verdict, col = "marginal", theme.WARN
        self.st_verdict.set(verdict)
        self.st_verdict.set_color(col)
        self.st_zz.set(f"{z:+.2f}")
        self.st_wnn.set(f"{wn:.1f} rad/s")
        self.st_half.set("never" if abs(sig) < 1e-6
                         else f"{math.log(2)/abs(sig):.2f} s")
        self.st_half.set_color(col)

        den = [1.0, -2 * sig, sig * sig + om * om]
        g = TF([den[-1]], den)
        dur = 6.0
        t, y = step_response(g, dur, dur / 1200.0)
        y = [min(max(v, -6.0), 6.0) for v in y]

        c = self.c1
        c.clear()
        a1, a2 = c.axes
        a1.plot(t, y, color=col, lw=2.2)
        a1.axhline(1.0, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a1.set_xlabel("time (s)")
        a1.set_ylabel("y  (clipped at ±6)")
        a1.set_title("step response", fontsize=9)
        _splane(a2, poles, lim=max(3.0, wn * 1.4))
        a2.set_title("s-plane", fontsize=9)
        c.refresh()

    def _redraw_routh(self):
        a2 = self.s_a2.value() / 10.0
        a1 = self.s_a1.value() / 10.0
        a0 = self.s_a0.value() / 10.0
        self.l_a2.setText(f"{a2:+.1f}")
        self.l_a1.setText(f"{a1:+.1f}")
        self.l_a0.setText(f"{a0:+.1f}")

        coeffs = [1.0, a2, a1, a0]
        n_routh = routh_rhp_count(coeffs)
        roots = poly_roots(coeffs)
        n_roots = sum(1 for r in roots if r.real > 1e-9)
        marginal = any(abs(r.real) <= 1e-9 for r in roots)
        self.st_rhp.set(str(n_routh))
        self.st_rhp.set_color(theme.GOOD if n_routh == 0 else theme.BAD)
        self.st_rhp2.set(str(n_roots))
        cls = ("unstable" if n_roots else
               ("marginal" if marginal else "stable"))
        self.st_class.set(cls)
        self.st_class.set_color(theme.GOOD if cls == "stable" else
                                (theme.WARN if cls == "marginal" else theme.BAD))

        rows = routh_table(coeffs)
        names = ["s³", "s²", "s¹", "s⁰"]
        txt = ["<b>Routh array</b> &nbsp; (first column decides)"]
        for nm, row in zip(names, rows):
            cells = "&nbsp;&nbsp;".join(f"{v:+8.3f}" for v in row)
            txt.append(f"<code>{nm} &nbsp; {cells}</code>")
        self.lbl_routh.setText("<br>".join(txt))

        g = TF([abs(a0) if abs(a0) > 1e-9 else 1.0], coeffs)
        t, y = step_response(g, 8.0, 8.0 / 1200.0)
        y = [min(max(v, -8.0), 8.0) for v in y]
        c = self.c2
        c.clear()
        ax1, ax2 = c.axes
        ax1.plot(t, y, color=theme.GOOD if cls == "stable" else
                 (theme.WARN if cls == "marginal" else theme.BAD), lw=2.0)
        ax1.set_xlabel("time (s)")
        ax1.set_ylabel("y  (clipped)")
        ax1.set_title("step response", fontsize=9)
        _splane(ax2, roots, lim=max(3.0, max([abs(r) for r in roots] or [3.0]) * 1.4))
        ax2.set_title("roots of the cubic", fontsize=9)
        c.refresh()


# ==========================================================================
# PAGE -- Bode and margins
# ==========================================================================

class BodePage(Page):
    TITLE = "Bode Plots, Gain & Phase Margin"
    SUBTITLE = ("Not \"is it stable\" but \"how much would have to be wrong "
                "before it is not\". The two numbers every real loop is signed "
                "off on.")
    SECTION = SECTION
    NOTES = "foundation"

    def __init__(self, parent=None):
        super().__init__(parent)

        w = Card("what a Bode plot is, and why the axes are the shape they are")
        w.add(body(
            "Feed a linear system a sine at frequency ω and, once the "
            "transients die, the output is <b>the same sine</b> — different "
            "amplitude, shifted in time. Only two numbers change, so the entire "
            "behaviour at that frequency is one complex number:"))
        w.add(math_label(r"G(j\omega) = |G(j\omega)|\;e^{\,j\angle G(j\omega)}",
                         17))
        w.add(body(
            "A Bode plot is those two numbers versus frequency. Both axes are "
            "logarithmic, and that is not cosmetic:<br><br>"
            "&nbsp;&nbsp;• <b>Cascaded blocks multiply.</b> Controller × plant × "
            "sensor. Take the log and multiplication becomes <b>addition</b> — "
            "so on a dB plot you can literally add curves with a pencil.<br>"
            "&nbsp;&nbsp;• <b>Phases add directly.</b> No log needed; that is "
            "just how complex multiplication works.<br>"
            "&nbsp;&nbsp;• <b>Log frequency</b> because a robot spans decades: "
            "a 20 kHz current loop and a 2 Hz gait live on the same picture."))
        w.add(body(
            "<b>The three building blocks, which is all you need to sketch "
            "one:</b><br>"
            "&nbsp;&nbsp;• a <b>pole</b> at ω<sub>p</sub>: flat, then "
            "−20 dB/decade after ω<sub>p</sub>; phase slides from 0 to −90°, "
            "passing −45° <i>at</i> ω<sub>p</sub><br>"
            "&nbsp;&nbsp;• a <b>zero</b> at ω<sub>z</sub>: the mirror image, "
            "+20 dB/decade and +90°<br>"
            "&nbsp;&nbsp;• an <b>integrator</b> (pole at the origin): "
            "−20 dB/decade everywhere and a flat −90°", dim=True))
        self.add(w)

        self.add(callout(
            "<b>Where instability comes from, in one sentence.</b> Feedback "
            "subtracts. If the loop delays a signal by exactly half a cycle — "
            "<b>−180°</b> — the subtraction turns into an <i>addition</i>, and "
            "if the loop gain is still ≥ 1 at that frequency, the signal comes "
            "back bigger every trip. That is oscillation. Everything below is "
            "measuring how far you are from that condition.", "key"))

        m = Card("the two margins")
        m.add(body(
            "<b>Gain margin.</b> Find the frequency where the phase hits "
            "−180° (call it ω<sub>pc</sub>). The gain there is below 1 — GM is "
            "how far below, in dB. It answers: <i>how much stronger could my "
            "plant be than I think, before this oscillates?</i>"))
        m.add(math_label(r"GM = -20\log_{10}|L(j\omega_{pc})| \quad "
                         r"\text{dB},\qquad \angle L(j\omega_{pc}) = -180°",
                         16))
        m.add(body(
            "<b>Phase margin.</b> Find the frequency where the gain passes "
            "through 1 = 0 dB (ω<sub>gc</sub>, the crossover). The phase there "
            "is above −180° — PM is how far above. It answers: <i>how much more "
            "delay could there be before this oscillates?</i>"))
        m.add(math_label(r"PM = 180° + \angle L(j\omega_{gc}), \qquad "
                         r"|L(j\omega_{gc})| = 1", 16))
        m.add(body(
            "<b>Targets on real hardware: PM 45–60°, GM 6–12 dB.</b> Below "
            "PM 30° a robot rings visibly and any payload change is a gamble. "
            "Above PM 70° you are almost certainly leaving bandwidth on the "
            "table.", dim=True))
        self.add(m)

        pm = Card("phase margin IS damping — the bridge to the last page")
        pm.add(body(
            "PM is not an abstract safety number. For the standard second-order "
            "loop it maps exactly onto ζ, and therefore onto overshoot:"))
        pm.add(body(
            "<table cellpadding='6'>"
            "<tr><td><b>PM</b></td><td>30°</td><td>45°</td><td>55°</td>"
            "<td>65°</td><td>76°</td></tr>"
            "<tr><td><b>ζ ≈</b></td><td>0.30</td><td>0.43</td><td>0.55</td>"
            "<td>0.71</td><td>1.0</td></tr>"
            "<tr><td><b>overshoot</b></td><td>37%</td><td>22%</td><td>13%</td>"
            "<td>4.3%</td><td>0%</td></tr>"
            "</table>"))
        pm.add(body(
            "Hence the rule of thumb <b>PM ≈ 100·ζ</b> (good to a few degrees "
            "up to ζ ≈ 0.7). And hence the practical translation: <b>\"my loop "
            "has 45° of phase margin\" and \"my robot overshoots about 20%\" "
            "are the same sentence.</b>", dim=True))
        self.add(pm)

        # ---- interactive ------------------------------------------------
        i = Card("build a loop and watch the margins move")
        i.add(body(
            "The plant is a real joint: 1/(J s² + b s) — note the pole at the "
            "origin, which is why the phase starts at −90°. Add loop gain, "
            "derivative action, a mechanical resonance and loop delay, and "
            "watch the two margins and the closed-loop step respond together.",
            dim=True))
        self.s_kp = slider(1, 400, 60)
        self.s_kd = slider(0, 200, 40)          # x0.1
        self.s_res = slider(0, 200, 0)          # Hz, 0 = rigid
        self.s_del = slider(0, 40, 4)           # x0.5 ms
        self.l_kp, self.l_kd = QLabel(), QLabel()
        self.l_res, self.l_del = QLabel(), QLabel()
        i.add_layout(slider_row("K_p", self.s_kp, self.l_kp))
        i.add_layout(slider_row("K_d (×0.1)", self.s_kd, self.l_kd))
        i.add_layout(slider_row("resonance (Hz, 0=rigid)", self.s_res,
                                self.l_res))
        i.add_layout(slider_row("loop delay (×0.5 ms)", self.s_del, self.l_del))
        self.st_pm = Stat("phase margin", "--", theme.GOOD)
        self.st_gm = Stat("gain margin", "--", theme.ACCENT)
        self.st_wgc = Stat("crossover", "--", theme.VIOLET)
        self.st_os = Stat("overshoot implied", "--", theme.WARN)
        i.add_layout(stat_row(self.st_pm, self.st_gm, self.st_wgc, self.st_os))
        self.c1 = MplCanvas(width=7.4, height=4.4, nrows=3)
        i.add(self.c1)
        self.add(i)
        for s in (self.s_kp, self.s_kd, self.s_res, self.s_del):
            s.valueChanged.connect(self._redraw)
        self._redraw()

        self.add(callout(
            "<b>Three experiments worth doing in that widget.</b><br><br>"
            "<b>1 · Raise K<sub>p</sub> with the resonance off.</b> Crossover "
            "moves right, phase margin barely suffers, and gain margin stays "
            "infinite. This is the second-order result from two pages ago: you "
            "cannot destabilise it.<br><br>"
            "<b>2 · Turn the resonance on at 15 Hz, then raise "
            "K<sub>p</sub>.</b> The moment crossover approaches the resonance, "
            "gain margin collapses. <i>This is the SEA bandwidth ceiling, "
            "derived rather than asserted.</i><br><br>"
            "<b>3 · Set the delay to 5 ms and watch only the phase plot.</b> "
            "The magnitude does not move at all — a delay has unit gain at "
            "every frequency — but the phase is dragged down by −360·f·T<sub>d</sub> "
            "degrees, and the phase margin drains away. Page 1 said delay is "
            "pure loss; this is the picture of it.", "good"))

        self.finish()

    # ------------------------------------------------------------------
    def _redraw(self):
        kp = float(self.s_kp.value())
        kd = self.s_kd.value() / 10.0
        res = float(self.s_res.value())
        delay = self.s_del.value() * 0.0005
        self.l_kp.setText(f"{kp:.0f}")
        self.l_kd.setText(f"{kd:.1f}")
        self.l_res.setText("rigid" if res <= 0 else f"{res:.0f} Hz")
        self.l_del.setText(f"{delay*1000:.1f} ms")

        plant = geared_joint_plant(0.25, 0.4, res)
        ctrl = TF([kd, kp], [1.0]) if kd > 0 else TF([kp], [1.0])
        # keep the controller proper: filter the derivative, as on the PID page
        if kd > 0:
            ctrl = TF([kd, kp], [1.0 / 400.0, 1.0])
        loop = plant * ctrl

        mg = margins_with_delay(loop, delay) if delay > 0 else margins(loop)
        self.st_pm.set("∞" if not math.isfinite(mg.phase_margin_deg)
                       else f"{mg.phase_margin_deg:.0f}°")
        self.st_pm.set_color(theme.GOOD if mg.phase_margin_deg > 40 else
                             (theme.WARN if mg.phase_margin_deg > 20
                              else theme.BAD))
        self.st_gm.set("∞" if not math.isfinite(mg.gain_margin_db)
                       else f"{mg.gain_margin_db:.1f} dB")
        self.st_gm.set_color(theme.GOOD if mg.gain_margin_db > 6 else theme.BAD)
        self.st_wgc.set(f"{mg.wgc/(2*math.pi):.1f} Hz" if mg.wgc else "—")
        z_eq = max(0.0, min(1.0, mg.phase_margin_deg / 100.0))
        self.st_os.set(f"{overshoot_fraction(z_eq)*100:.0f}%")

        ws = log_freqs(0.5, 3000.0, 220)
        w, mag, ph = bode(loop, ws)
        if delay > 0:
            ph = [p - math.degrees(wi * delay) for p, wi in zip(ph, w)]

        c = self.c1
        c.clear()
        a1, a2, a3 = c.axes
        a1.semilogx(w, mag, color=theme.ACCENT, lw=2.0)
        a1.axhline(0, color=theme.TEXT_FAINT, lw=1.1, ls="--")
        if mg.wgc:
            a1.axvline(mg.wgc, color=theme.GOOD, lw=1.2)
            a1.text(mg.wgc, max(mag) * 0.5, " ω_gc", color=theme.GOOD,
                    fontsize=7.5)
        if mg.wpc:
            a1.axvline(mg.wpc, color=theme.BAD, lw=1.1, ls="-.")
        a1.set_ylabel("|L| (dB)")
        a2.semilogx(w, ph, color=theme.ACCENT, lw=2.0)
        a2.axhline(-180, color=theme.BAD, lw=1.2, ls=":")
        if mg.wgc:
            a2.axvline(mg.wgc, color=theme.GOOD, lw=1.2)
        if mg.wpc:
            a2.axvline(mg.wpc, color=theme.BAD, lw=1.1, ls="-.")
            a2.text(mg.wpc, -100, " ω_pc", color=theme.BAD, fontsize=7.5)
        a2.set_ylabel("∠L (deg)")
        a2.set_xlabel("ω (rad/s)")
        a2.set_ylim(max(-540, min(ph) - 20), 10)

        cl = loop.feedback()
        t, y = step_response(cl, 1.2, 1e-3)
        a3.plot(t, y, color=theme.GOOD if mg.phase_margin_deg > 25
                else theme.BAD, lw=2.0)
        a3.axhline(1.0, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a3.set_ylim(-0.3, 2.4)
        a3.set_xlabel("time (s)")
        a3.set_ylabel("closed loop")
        c.refresh()


# ==========================================================================
# PAGE -- Nyquist
# ==========================================================================

class NyquistPage(Page):
    TITLE = "The Nyquist Plot"
    SUBTITLE = ("One curve, one point, and a counting rule that survives the "
                "cases where Bode margins quietly lie.")
    SECTION = SECTION
    NOTES = "foundation"

    def __init__(self, parent=None):
        super().__init__(parent)

        w = Card("the same information, plotted differently")
        w.add(body(
            "A Bode plot splits L(jω) into magnitude and phase and draws them "
            "against frequency. A Nyquist plot keeps them together and draws "
            "the complex number itself: <b>each point on the curve is one "
            "frequency</b>, its distance from the origin is |L|, and its angle "
            "is ∠L. Frequency runs along the curve rather than along an axis."))
        w.add(body(
            "Nothing is added and nothing is lost. What changes is that one "
            "specific point on the plane — <b>−1</b> — becomes visible, and the "
            "whole of stability turns into a question about how the curve is "
            "arranged around it."))
        self.add(w)

        m = Card("why −1, and not some other number")
        m.add(body("The closed-loop transfer function of a unity feedback loop "
                   "is"))
        m.add(math_label(r"T(s) = \frac{L(s)}{1 + L(s)}", 17))
        m.add(body(
            "so the closed-loop <b>poles</b> are the roots of "
            "<b>1 + L(s) = 0</b>, i.e. the values of s where <b>L(s) = −1</b>. "
            "If that ever happens for s = jω — a real frequency — then at that "
            "frequency the loop returns exactly the negative of what went in, "
            "the feedback subtraction becomes reinforcement, and the loop "
            "sustains an oscillation with no input at all.<br><br>"
            "So −1 is not a convention. It is the point where the denominator "
            "of the closed loop vanishes."))
        self.add(m)

        c = Card("the criterion, and how to count")
        c.add(math_label(r"Z = N + P", 18))
        c.add(body(
            "&nbsp;&nbsp;<b>Z</b> — closed-loop poles in the right half plane. "
            "You want <b>0</b>.<br>"
            "&nbsp;&nbsp;<b>N</b> — net <b>clockwise</b> encirclements of −1 by "
            "the Nyquist curve.<br>"
            "&nbsp;&nbsp;<b>P</b> — <i>open-loop</i> poles in the right half "
            "plane. Known before you start."))
        c.add(body(
            "<b>The common case:</b> the plant is open-loop stable, so P = 0, "
            "and the rule collapses to <i>the curve must not encircle −1</i>. "
            "Simple enough to check by eye.<br><br>"
            "<b>The case that matters in robotics:</b> an inverted pendulum has "
            "P = 1 — a genuinely unstable plant. Now you need <b>N = −1</b>: "
            "the curve must encircle −1 exactly once <i>counter</i>-clockwise. "
            "Not encircling it is now the failure. A Bode plot cannot tell you "
            "this; Nyquist can, and that is the main reason it is still taught.",
            dim=True))
        self.add(c)

        g = Card("reading the margins straight off the picture")
        g.add(body(
            "&nbsp;&nbsp;• <b>Gain margin</b> — where the curve crosses the "
            "negative real axis, at distance d from the origin. GM = 1/d. Push "
            "the whole curve out by that factor and it lands on −1.<br>"
            "&nbsp;&nbsp;• <b>Phase margin</b> — where the curve crosses the "
            "<b>unit circle</b>. PM is the angle from there back to the negative "
            "real axis. Rotate the curve by that much and it lands on −1.<br>"
            "&nbsp;&nbsp;• <b>Vector margin</b> — the <b>shortest distance from "
            "the curve to −1</b>, in any direction at all."))
        g.add(math_label(r"V_m = \min_\omega |1 + L(j\omega)| = \frac{1}{M_s}",
                         17))
        g.add(callout(
            "<b>Vector margin is the honest one, and it is why this page "
            "exists.</b> Gain margin measures how far you are from −1 moving "
            "radially. Phase margin measures how far you are moving "
            "tangentially. A curve can be comfortable in <i>both</i> of those "
            "directions and still pass within a hair of −1 <b>diagonally</b> — "
            "which is exactly what a plant does when its gain and its phase are "
            "both a little wrong at once, which is exactly what real plants "
            "do.<br><br>"
            "Aim for <b>V<sub>m</sub> ≥ 0.5</b> (equivalently M<sub>s</sub> ≤ 2). "
            "A loop with 60° of phase margin, 12 dB of gain margin and "
            "V<sub>m</sub> = 0.15 is a loop that will surprise you on the "
            "robot.", "key"))
        self.add(g)

        # ---- interactive -------------------------------------------------
        i = Card("sweep the gain, watch the curve approach −1")
        i.add(body(
            "The three-pole loop K/((s+1)(s+2)(s+3))·scaled — the simplest "
            "system that <i>can</i> be destabilised by gain alone. Turn K up "
            "and watch the curve inflate until it swallows −1. The verdict is "
            "computed by counting encirclements, and cross-checked against the "
            "closed-loop roots.", dim=True))
        self.s_k = slider(1, 1200, 200)         # x0.1
        self.l_k = QLabel()
        i.add_layout(slider_row("loop gain K (×0.1)", self.s_k, self.l_k))
        self.cmb = QComboBox()
        for lab, key in (("three real poles  1/((s+1)(s+2)(s+3))", "three"),
                         ("joint + integrator  1/(s(s+1)(s+2))", "integ"),
                         ("unstable plant  1/((s−1)(s+3))  [P = 1]", "unst")):
            self.cmb.addItem(lab, key)
        self.cmb.currentIndexChanged.connect(self._redraw)
        i.add_layout(labelled("Plant", self.cmb, width=60))
        self.st_n = Stat("encirclements N", "--", theme.ACCENT)
        self.st_p = Stat("open-loop RHP P", "--", theme.VIOLET)
        self.st_z = Stat("closed-loop RHP Z", "--", theme.BAD)
        self.st_vm = Stat("vector margin", "--", theme.WARN)
        i.add_layout(stat_row(self.st_n, self.st_p, self.st_z, self.st_vm))
        self.c1 = MplCanvas(width=7.4, height=3.4, ncols=2)
        i.add(self.c1)
        self.add(i)
        self.s_k.valueChanged.connect(self._redraw)
        self._redraw()

        self.add(callout(
            "<b>When Bode is enough, and when it is not.</b><br><br>"
            "Bode is fine for the overwhelmingly common case: an open-loop "
            "stable plant whose magnitude crosses 0 dB exactly once. That "
            "covers most joints most of the time, and it is easier to read.<br><br>"
            "Reach for Nyquist when any of these is true:<br>"
            "&nbsp;&nbsp;• the plant is <b>open-loop unstable</b> (a balancing "
            "robot, a magnetic bearing) — the counting rule is the only thing "
            "that works<br>"
            "&nbsp;&nbsp;• the loop is <b>conditionally stable</b>: stable at "
            "the design gain but unstable if the gain is <i>reduced</i>. This "
            "happens when the magnitude crosses 0 dB more than once, and it is "
            "genuinely dangerous, because saturation reduces effective gain — "
            "so the robot destabilises itself by being pushed hard<br>"
            "&nbsp;&nbsp;• you care about the <b>vector margin</b>, which has no "
            "natural reading on a Bode plot at all", "warn"))

        self.finish()

    # ------------------------------------------------------------------
    def _plant(self):
        key = self.cmb.currentData()
        if key == "integ":
            return TF([1.0], [1.0, 3.0, 2.0, 0.0]), 0
        if key == "unst":
            return TF([1.0], [1.0, 2.0, -3.0]), 1
        return TF([1.0], [1.0, 6.0, 11.0, 6.0]), 0

    def _redraw(self):
        k = self.s_k.value() / 10.0
        self.l_k.setText(f"{k:.1f}")
        plant, p_rhp = self._plant()
        loop = plant * k

        n = encirclements(loop, n=3000)
        cl = loop.feedback()
        z = sum(1 for r in cl.poles() if r.real > 1e-9)
        vm = vector_margin(loop, n=800)
        self.st_n.set(f"{n:+d}")
        self.st_p.set(str(p_rhp))
        self.st_z.set(str(z))
        self.st_z.set_color(theme.GOOD if z == 0 else theme.BAD)
        self.st_vm.set(f"{vm:.2f}")
        self.st_vm.set_color(theme.GOOD if vm >= 0.5 else
                             (theme.WARN if vm >= 0.25 else theme.BAD))

        re, im = nyquist_points(loop, 1e-2, 1e4, 1200)
        c = self.c1
        c.clear()
        a1, a2 = c.axes
        a1.plot(re, im, color=theme.ACCENT, lw=1.8, label="ω > 0")
        a1.plot(re, [-v for v in im], color=theme.ACCENT, lw=1.0, ls="--",
                alpha=0.6, label="ω < 0 (mirror)")
        th = [i * math.pi / 90 for i in range(181)]
        a1.plot([math.cos(a) for a in th], [math.sin(a) for a in th],
                color=theme.TEXT_FAINT, lw=0.9, ls=":", label="unit circle")
        a1.scatter([-1], [0], marker="+", s=140, linewidths=2.2,
                   color=theme.BAD, zorder=6, label="−1")
        lim = 3.0
        a1.set_xlim(-lim, lim * 0.7)
        a1.set_ylim(-lim, lim)
        a1.axhline(0, color=theme.BORDER, lw=0.9)
        a1.axvline(0, color=theme.BORDER, lw=0.9)
        a1.set_xlabel("Re L(jω)")
        a1.set_ylabel("Im L(jω)")
        a1.set_title(f"Z = N + P = {n:+d} + {p_rhp} = {n + p_rhp}", fontsize=9)
        c.legend(a1, loc="upper left")

        t, y = step_response(cl, 8.0, 3e-3)
        y = [min(max(v, -5.0), 5.0) for v in y]
        a2.plot(t, y, color=theme.GOOD if z == 0 else theme.BAD, lw=2.0)
        a2.axhline(cl.dc_gain() if abs(cl.dc_gain()) < 5 else 0,
                   color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a2.set_xlabel("time (s)")
        a2.set_ylabel("closed-loop step (clipped)")
        a2.set_title("stable" if z == 0 else f"UNSTABLE — {z} RHP poles",
                     fontsize=9)
        c.refresh()
