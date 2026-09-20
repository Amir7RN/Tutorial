"""
Linear systems and stability -- the four pages that make every later claim
about "bandwidth", "damping" and "margin" mean something specific.

  1  Second-Order Systems   two poles, and the moment overshoot becomes
                            possible -- which is where every robot joint lives
  2  Stability              what stable actually means, and the three ways to
                            check it without guessing
  3  Bode & Margins         how far you are from the edge, in the two
                            directions you can actually be wrong
  4  Nyquist                the same question asked geometrically, and the
                            cases where Bode quietly lies

First order comes before all of this, in `firstorder.py`, across four pages of
its own. Everything here assumes you can already read a pole as a pair of
physical rates; if you cannot, those pages are where that is built.

The block comes straight after Real-Time on purpose. That page said your
bandwidth is roughly f_s/10 and that delay costs you phase margin. Both of
those sentences are claims about the objects defined here, and until you can
see a pole move there is no way to check either one.
"""

from __future__ import annotations

import cmath
import math

from PySide6.QtWidgets import QComboBox, QLabel

from ctrlcore.linear import (
    TF,
    bandwidth_second_order,
    bode,
    damped_frequency,
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
    quality_factor,
    resonant_frequency,
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
# PAGE -- free vibration
# ==========================================================================

class FreeVibrationPage(Page):
    TITLE = "Free Vibration — Solving It From Initial Conditions"
    SUBTITLE = ("Nobody is pushing. Displace it, shove it, let go — and the "
                "answer is one cosine with a shifted start. Every response on "
                "the next four pages is this, plus a forcing term.")
    SECTION = SECTION
    NOTES = "foundation"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>Solve the system with nothing driving it first.</b><br><br>"
            "The previous page put a second pole on the map and said the "
            "system can now ring. This page does the thing that makes that "
            "concrete: <b>writes down the actual function of time</b>, from "
            "an initial displacement and an initial velocity, with no input "
            "at all.<br><br>"
            "It is worth its own page because of a structural fact about "
            "linear equations: <b>the response to anything is the free "
            "response plus a piece that depends on the input.</b> Solve the "
            "free problem once and the step response, the ramp response and "
            "the swept sine all become \"that, plus a term\". Skip it and "
            "every one of those has to be memorised separately.", "key"))

        # ---- the undamped case, solved -----------------------------------
        u = Card("the undamped case: mass and spring, nothing else")
        u.add(body(
            "No damper, no torque. Just a mass, a spring, and whatever state "
            "you left it in:"))
        u.add(math_label(r"m\ddot x + k x = 0, \qquad "
                         r"x(0) = x_0, \qquad \dot x(0) = v_0", 18))
        u.add(body(
            "<b>Step 1 — guess an exponential.</b> Every linear constant-"
            "coefficient equation is solved by x = e<sup>st</sup>, because "
            "differentiating an exponential just multiplies it by s. Substitute "
            "and the whole equation collapses to a polynomial:"))
        u.add(math_label(r"(m s^2 + k)\,e^{st} = 0 \;\Longrightarrow\; "
                         r"s^2 = -\frac{k}{m} \;\Longrightarrow\; "
                         r"s = \pm j\sqrt{k/m} = \pm j\omega_n", 17))
        u.add(body(
            "<b>The roots are purely imaginary, and that is the whole "
            "story.</b> No real part means nothing decays — there is no "
            "damper to decay into. The imaginary part is ω<sub>n</sub> = "
            "√(k/m), so the answer oscillates at ω<sub>n</sub> forever."))
        u.add(body(
            "<b>Step 2 — turn e<sup>±jω<sub>n</sub>t</sup> into real "
            "functions.</b> Euler says those two exponentials are cos ω<sub>n</sub>t "
            "and sin ω<sub>n</sub>t in disguise, so the general real solution "
            "is any mix of the two — two roots, two free constants:"))
        u.add(math_label(r"x(t) = C_1\cos\omega_n t + C_2\sin\omega_n t", 18))
        u.add(body(
            "<b>Step 3 — the two constants are exactly the two initial "
            "conditions.</b> Set t = 0: cos is 1, sin is 0, so C<sub>1</sub> = "
            "x<sub>0</sub> immediately. Differentiate, then set t = 0: the cos "
            "term's derivative vanishes and the sin term's leaves "
            "C<sub>2</sub>ω<sub>n</sub> = v<sub>0</sub>. That is the whole "
            "derivation:"))
        u.add(math_label(r"\boxed{\;x(t) = x_0\cos\omega_n t \;+\; "
                         r"\frac{v_0}{\omega_n}\sin\omega_n t\;}", 19))
        u.add(body(
            "<b>Read the two terms physically.</b> The cosine is the part you "
            "put in <i>as position</i> — it starts at full height with zero "
            "slope. The sine is the part you put in <i>as speed</i> — it "
            "starts at zero height with full slope. They are the same "
            "oscillation, a quarter cycle apart, and the system does not care "
            "which way you loaded it.<br><br>"
            "Note the division by ω<sub>n</sub> in the second term. A given "
            "velocity buys you <i>less</i> displacement on a stiffer, faster "
            "system: it turns around sooner. v<sub>0</sub>/ω<sub>n</sub> is "
            "\"how far this speed gets you before the spring wins\", and it is "
            "the only way a velocity can enter an answer measured in metres.",
            dim=True))
        self.add(u)

        # ---- the amplitude-phase form ------------------------------------
        ap = Card("the same answer as ONE cosine — amplitude and phase")
        ap.add(body(
            "Two terms is correct but hard to picture. A sum of a cosine and a "
            "sine <i>at the same frequency</i> is always a single cosine of "
            "that frequency, shifted — that is the standard trigonometric "
            "identity, and it is worth applying here because the shifted form "
            "is the one that answers the questions people ask:"))
        ap.add(math_label(r"x(t) = A\cos(\omega_n t - \varphi)", 19))
        ap.add(math_label(r"A = \sqrt{x_0^2 + \left(\frac{v_0}"
                          r"{\omega_n}\right)^{2}}, \qquad "
                          r"\varphi = \tan^{-1}\!\left(\frac{v_0}"
                          r"{x_0\,\omega_n}\right)", 18))
        ap.add(body(
            "<b>Where it comes from:</b> expand the right-hand side with the "
            "angle-subtraction rule — A cos(ω<sub>n</sub>t − φ) = "
            "(A cos φ) cos ω<sub>n</sub>t + (A sin φ) sin ω<sub>n</sub>t — and "
            "match it term by term against the solution above. So "
            "A cos φ = x<sub>0</sub> and A sin φ = v<sub>0</sub>/ω<sub>n</sub>. "
            "Square and add: the φ disappears and you get A. Divide instead: "
            "the A disappears and you get tan φ. It is a right triangle whose "
            "legs are the two initial conditions, and A is the "
            "<b>hypotenuse</b>.", dim=True))
        ap.add(callout(
            "<b>So the peak is not x<sub>0</sub>. It is the hypotenuse, and it "
            "is bigger.</b><br><br>"
            "This is the practical content of the page. Release a joint from "
            "x<sub>0</sub> with <i>any</i> velocity at all and the furthest it "
            "ever gets is A = √(x<sub>0</sub>² + (v<sub>0</sub>/ω<sub>n</sub>)²) "
            "— strictly greater than x<sub>0</sub> whenever v<sub>0</sub> ≠ 0, "
            "and it does not matter which <i>direction</i> the velocity points, "
            "because v<sub>0</sub> enters squared. A shove towards the target "
            "and a shove away from it produce the same peak excursion; they "
            "only differ in <i>when</i> it happens, which is the φ.<br><br>"
            "An impact that leaves a limb at 2° of deflection and 40°/s of "
            "speed on a joint with ω<sub>n</sub> = 20 rad/s does not swing to "
            "2°. It swings to √(2² + (40/20)²) = <b>2.83°</b>.", "key"))
        ap.add(body(
            "<b>And A is conservation of energy wearing a different hat.</b> "
            "At the peak the mass is momentarily still, so every joule is in "
            "the spring: E = ½kA². At t = 0 the energy is ½kx<sub>0</sub>² in "
            "the spring plus ½mv<sub>0</sub>² in the mass. Set them equal, "
            "divide by ½k, and use k/m = ω<sub>n</sub>²:"))
        ap.add(math_label(r"\tfrac12 k A^2 = \tfrac12 k x_0^2 "
                          r"+ \tfrac12 m v_0^2 \;\Longrightarrow\; "
                          r"A^2 = x_0^2 + \frac{m}{k}v_0^2 "
                          r"= x_0^2 + \frac{v_0^2}{\omega_n^2}", 17))
        ap.add(body(
            "…the identical formula. The Pythagorean A is not a trigonometric "
            "coincidence: <b>the two legs of that triangle are the square "
            "roots of the two energy stores</b>, and the hypotenuse is the "
            "total. This is the algebra behind the energy-sloshing picture the "
            "next page opens with.", dim=True))
        ap.add(body(
            "<b>And φ is a time shift wearing angular units.</b> A cosine "
            "peaks when its argument is zero, so A cos(ω<sub>n</sub>t − φ) "
            "peaks at ω<sub>n</sub>t = φ. Divide:"))
        ap.add(math_label(r"\Delta t = \frac{\varphi}{\omega_n} "
                          r"\qquad\Longleftrightarrow\qquad "
                          r"\varphi = \omega_n\,\Delta t", 17))
        ap.add(body(
            "<b>φ is literally \"how long until the peak\", scaled by "
            "ω<sub>n</sub>.</b> That is the only reading of a phase angle "
            "worth carrying: an angle is a delay, and the conversion factor "
            "is the frequency. φ = 90° on a system with ω<sub>n</sub> = "
            "20 rad/s means the peak arrives (π/2)/20 = 78 ms after you let "
            "go.<br><br>"
            "It also explains the sign convention. A <i>positive</i> φ is a "
            "<i>later</i> peak — the cosine has been pushed to the right — "
            "which is why a shove <b>towards</b> the target (v<sub>0</sub> the "
            "same sign as x<sub>0</sub>) gives a positive φ and a delayed, "
            "larger swing, while a shove <b>back</b> gives a negative φ and an "
            "earlier one. Same A, opposite Δt. Every \"phase lag\" on every "
            "later page is this same sentence at a different frequency.",
            dim=True))
        self.add(ap)

        # ---- interactive: initial conditions -----------------------------
        iv = Card("set x₀ and v₀, and watch the peak leave x₀ behind — then "
                  "raise ζ through all three regimes")
        iv.add(body(
            "The two pale curves are the two terms — the cosine you loaded as "
            "<b>position</b> and the sine you loaded as <b>speed</b>. The "
            "bright curve is their sum, and the dotted lines are the ±A "
            "envelope.<br><br>"
            "<b>With ζ = 0:</b> set v<sub>0</sub> = 0 and the sine term "
            "vanishes, A = x<sub>0</sub>, φ = 0 — the textbook \"release from "
            "rest\". Now move v<sub>0</sub> either way and watch A grow while "
            "the whole curve slides sideways. Flip v<sub>0</sub> from +60 to "
            "−60: <b>A does not change at all</b>, only φ. And set "
            "x<sub>0</sub> = 0 for a pure hammer blow — a clean sine, peak "
            "v<sub>0</sub>/ω<sub>n</sub>, φ = 90°.<br><br>"
            "<b>Now walk ζ across the three branches.</b> Below 1 the roots "
            "are complex and the envelope squeezes a shrinking cosine. At "
            "exactly 1 the roots collide, the pale curves change to the two "
            "terms of the repeated-root solution, and the last crossing "
            "disappears. Above 1 the roots are two real numbers and the pale "
            "curves become <b>two plain exponentials</b> — watch the slower "
            "one take over the shape completely as you push ζ to 2.",
            dim=True))
        self.s_x0 = slider(-40, 40, 20)          # degrees
        self.s_v0 = slider(-200, 200, 60)        # deg/s
        self.s_wnf = slider(10, 400, 100)        # x0.1 rad/s
        self.s_zf0 = slider(0, 200, 0)           # x0.01 damping, 0 .. 2.0
        self.l_x0, self.l_v0 = QLabel(), QLabel()
        self.l_wnf, self.l_zf0 = QLabel(), QLabel()
        iv.add_layout(slider_row("x₀ (°)", self.s_x0, self.l_x0))
        iv.add_layout(slider_row("v₀ (°/s)", self.s_v0, self.l_v0))
        iv.add_layout(slider_row("ω_n (×0.1 rad/s)", self.s_wnf, self.l_wnf))
        iv.add_layout(slider_row("damping ζ (×0.01)", self.s_zf0, self.l_zf0))
        self.st_A = Stat("amplitude A", "--", theme.ACCENT)
        self.st_phi = Stat("phase φ", "--", theme.VIOLET)
        self.st_gain = Stat("A / x₀", "--", theme.WARN)
        self.st_per = Stat("damped period", "--", theme.GOOD)
        self.st_regf = Stat("regime", "--", theme.CYAN)
        iv.add_layout(stat_row(self.st_A, self.st_phi, self.st_gain,
                               self.st_per, self.st_regf))
        self.cfv = MplCanvas(width=7.4, height=3.2)
        iv.add(self.cfv)
        self.tfv = body("", dim=True)
        iv.add(self.tfv)
        self.add(iv)
        for s in (self.s_x0, self.s_v0, self.s_wnf, self.s_zf0):
            s.valueChanged.connect(self._redraw_free)
        self._redraw_free()

        # ---- the damped case ---------------------------------------------
        dm = Card("now put the damper back — the same answer inside an "
                  "envelope")
        dm.add(body(
            "Add the damper and redo the three steps. Only the first one "
            "changes, and it changes in one place: the characteristic "
            "polynomial picks up a middle term, so the roots pick up a real "
            "part. Substitute x = A e<sup>st</sup> again — the same guess, "
            "because the equation is still linear with constant coefficients "
            "— and the quadratic formula does the rest:"))
        dm.add(math_label(r"m\ddot x + c\dot x + kx = 0 \;\Longrightarrow\; "
                          r"s^2 + 2\zeta\omega_n s + \omega_n^2 = 0 "
                          r"\;\Longrightarrow\; "
                          r"s_{1,2} = -\zeta\omega_n \pm "
                          r"\omega_n\sqrt{\zeta^2-1}", 17))
        dm.add(body(
            "<b>Everything that follows is decided by the sign under that "
            "square root, and by nothing else.</b> There is no third "
            "possibility, which is why the three regimes are exhaustive:"))
        dm.add(body(
            "<table cellpadding='7'>"
            "<tr><td><b>ζ &lt; 1</b></td>"
            "<td>ζ²−1 is negative, so the root is imaginary: "
            "s = −ζω<sub>n</sub> ± jω<sub>d</sub></td>"
            "<td><b>oscillates.</b> Two complex-conjugate roots → a decaying "
            "cosine</td></tr>"
            "<tr><td><b>ζ = 1</b></td>"
            "<td>the root is zero, so the two roots <i>collide</i> at "
            "−ω<sub>n</sub></td>"
            "<td><b>does not oscillate.</b> A repeated root, and the second "
            "solution has to be t·e<sup>−ω<sub>n</sub>t</sup></td></tr>"
            "<tr><td><b>ζ &gt; 1</b></td>"
            "<td>the root is real, so both s are real and negative: "
            "−ω<sub>n</sub>(ζ ∓ √(ζ²−1))</td>"
            "<td><b>does not oscillate.</b> A sum of two plain decaying "
            "exponentials</td></tr>"
            "</table>"))
        dm.add(body(
            "<b>Take the ζ &lt; 1 branch first</b>, since it is the one real "
            "joints live in. Write √(ζ²−1) = j√(1−ζ²) and the root becomes "
            "s = −ζω<sub>n</sub> ± jω<sub>d</sub>, with ω<sub>d</sub> = "
            "ω<sub>n</sub>√(1−ζ²). Then e<sup>st</sup> = "
            "e<sup>−ζω<sub>n</sub>t</sup>·e<sup>±jω<sub>d</sub>t</sup> — a "
            "<b>shrinking</b> factor times the same oscillation, at a slightly "
            "lower frequency. The solution is therefore the undamped one with "
            "two edits: a decaying multiplier out front, and ω<sub>d</sub> "
            "wherever ω<sub>n</sub> used to be inside the cosine."))
        dm.add(math_label(r"\boxed{\;x(t) = A\,e^{-\zeta\omega_n t}"
                          r"\cos(\omega_d t - \varphi)\;}", 19))
        dm.add(math_label(r"A = \sqrt{x_0^2 + \left("
                          r"\frac{v_0 + \zeta\omega_n x_0}{\omega_d}"
                          r"\right)^{2}}, \qquad "
                          r"\varphi = \tan^{-1}\!\left("
                          r"\frac{v_0 + \zeta\omega_n x_0}"
                          r"{\omega_d\,x_0}\right)", 17))
        dm.add(body(
            "<b>Why v<sub>0</sub> became v<sub>0</sub> + ζω<sub>n</sub>x<sub>0</sub>.</b> "
            "Matching the initial slope now has to account for the envelope, "
            "which is already falling at t = 0 at a rate ζω<sub>n</sub>x<sub>0</sub>. "
            "Part of the velocity you measure is the envelope coming down "
            "rather than the oscillation moving, so the oscillation's own "
            "share is the measured velocity <i>plus</i> what the envelope is "
            "taking away. Set ζ = 0 and the correction disappears, "
            "ω<sub>d</sub> → ω<sub>n</sub>, and both formulas collapse back to "
            "the undamped pair — which is the check worth doing on any result "
            "of this shape.", dim=True))
        dm.add(callout(
            "<b>This is the single most reused formula in the rest of the "
            "tutor, so it is worth naming its three parts.</b><br><br>"
            "&nbsp;&nbsp;• <b>A</b> — how big, set entirely by the initial "
            "conditions. Nothing about the response's <i>shape</i>.<br>"
            "&nbsp;&nbsp;• <b>e<sup>−ζω<sub>n</sub>t</sup></b> — the envelope, "
            "set by the <b>real</b> part of the pole. This alone decides "
            "settling time.<br>"
            "&nbsp;&nbsp;• <b>cos(ω<sub>d</sub>t − φ)</b> — the wiggle, set by "
            "the <b>imaginary</b> part. This alone decides how many visible "
            "oscillations you get.<br><br>"
            "Turn the damping slider in the widget above from 0 upwards and "
            "watch exactly these three things separate: the envelope appears "
            "and steepens, the wiggle slows a little, and A barely moves.",
            "key"))
        dm.add(body(
            "One honest caveat on the damped case: <b>A is no longer the "
            "peak.</b> It is the height of the envelope at t = 0, and the "
            "curve touches that envelope a little later, by which time the "
            "envelope has already come down. So A is an upper bound on the "
            "excursion, tight when ζ is small and loose when it is not.",
            dim=True))
        self.add(dm)

        # ---- the same answer, split by which IC caused it ----------------
        sp = Card("the same solution, split by which initial condition "
                  "caused which piece")
        sp.add(body(
            "The single-cosine form is compact, but it blends x<sub>0</sub> "
            "and v<sub>0</sub> together inside A and φ, so you cannot see "
            "which one is responsible for what. There is an equivalent "
            "arrangement that keeps them apart, and it is the more useful one "
            "when you are debugging a real ring-down:"))
        sp.add(math_label(r"x(t) = e^{-\zeta\omega_n t}\left["
                          r"\frac{x_0}{\sqrt{1-\zeta^2}}"
                          r"\cos(\omega_d t - \psi) \;+\; "
                          r"\frac{v_0}{\omega_n\sqrt{1-\zeta^2}}"
                          r"\sin(\omega_d t)\right]", 17))
        sp.add(math_label(r"\psi = \tan^{-1}\!\frac{\zeta}{\sqrt{1-\zeta^2}} "
                          r"\;=\; \sin^{-1}\zeta", 17))
        sp.add(body(
            "<b>Two independent contributions, and each one is clean.</b> The "
            "<b>displacement</b> you started with produces a cosine that is "
            "already phase-shifted by ψ and inflated by 1/√(1−ζ²). The "
            "<b>velocity</b> you started with produces a pure sine — no phase "
            "shift at all — scaled by v<sub>0</sub>/ω<sub>d</sub>. Set either "
            "initial condition to zero and the other term is the whole "
            "answer, which makes this the form to reach for when you can only "
            "excite one of them."))
        sp.add(body(
            "<b>It is the same function, not an approximation.</b> Expand the "
            "cosine with the angle-subtraction rule, using cos ψ = √(1−ζ²) "
            "and sin ψ = ζ — which is why ψ = sin⁻¹ζ — and the √(1−ζ²) "
            "cancels out of the first term, leaving x<sub>0</sub> cos "
            "ω<sub>d</sub>t plus a sine whose coefficient collects to exactly "
            "(v<sub>0</sub> + ζω<sub>n</sub>x<sub>0</sub>)/ω<sub>d</sub>. The "
            "previous card's constants, recovered.", dim=True))
        sp.add(callout(
            "<b>And notice ψ is the complement of φ from the pole "
            "picture.</b> The pole-angle card on the next page reads the "
            "angle from the negative real axis as arccos ζ; here the same "
            "triangle is read from the other side as arcsin ζ. Adjacent ζ, "
            "opposite √(1−ζ²), hypotenuse 1 — one right triangle, and <b>every "
            "phase angle in second-order theory is one of its two acute "
            "angles</b>. arccos ζ, arcsin ζ, and arctan(ζ/√(1−ζ²)) are three "
            "names for the same two numbers.", "key"))
        self.add(sp)

        # ---- the light-damping simplification ----------------------------
        lt = Card("when you may drop the √(1−ζ²), and the one place you may "
                  "not")
        lt.add(body(
            "√(1−ζ²) is scattered through every formula above and it is "
            "tiresome. For the damping a real joint actually has, most of "
            "those instances are doing nothing, and dropping them is standard "
            "practice. But one of them is <b>not</b> negligible, and the "
            "distinction is the point of this card."))
        lt.add(body(
            "<table cellpadding='7'>"
            "<tr><td><b>ζ</b></td><td><b>√(1−ζ²)</b></td>"
            "<td><b>error if you call it 1</b></td>"
            "<td><b>ψ = sin⁻¹ζ</b></td></tr>"
            "<tr><td>0.05</td><td>0.9987</td><td>0.13%</td><td>2.9°</td></tr>"
            "<tr><td>0.10</td><td>0.9950</td><td>0.50%</td><td>5.7°</td></tr>"
            "<tr><td>0.20</td><td>0.9798</td><td>2.0%</td><td>11.5°</td></tr>"
            "<tr><td>0.30</td><td>0.9539</td><td>4.6%</td><td>17.5°</td></tr>"
            "</table>"))
        lt.add(body(
            "<b>Where it is safe to drop.</b> Anywhere it appears as an "
            "<i>amplitude</i> or a <i>frequency</i> correction:"))
        lt.add(math_label(r"\omega_d \approx \omega_n, \qquad "
                          r"\frac{1}{\sqrt{1-\zeta^2}} \approx 1, \qquad "
                          r"A \approx \sqrt{x_0^2 + (v_0/\omega_n)^2}", 16))
        lt.add(body(
            "At ζ = 0.1 these are all wrong by half a percent, which is far "
            "inside the uncertainty on any J or K you measured. <b>The "
            "undamped formulas are the right formulas for a lightly damped "
            "system, as long as you keep the envelope.</b> That is the useful "
            "form of the simplification: amplitude and frequency come from "
            "the undamped analysis, and the only thing damping contributes is "
            "e<sup>−ζω<sub>n</sub>t</sup> multiplying the lot."))
        lt.add(callout(
            "<b>Where you may NOT drop it: anything that is a phase, because "
            "phases accumulate and amplitudes do not.</b><br><br>"
            "ψ = sin⁻¹ζ is 5.7° at ζ = 0.1. That looks as negligible as the "
            "0.5% next to it, and it is not — for two reasons.<br><br>"
            "<b>1 · A phase error compounds along a cascade.</b> Amplitude "
            "errors multiply, so 0.5% across four blocks is still 2%. Phase "
            "errors <b>add</b>, so 5.7° across four blocks is 23° — and you "
            "are spending it out of a phase margin that is only about 45° to "
            "begin with. Half your margin, gone to a term you called "
            "negligible.<br><br>"
            "<b>2 · The frequency error accumulates in time.</b> Calling "
            "ω<sub>d</sub> = ω<sub>n</sub> is a 0.5% frequency error, which "
            "sounds harmless — but after n cycles the predicted waveform is "
            "0.005 × n cycles out of step with the real one. By n = 50 that "
            "is a quarter of a cycle: your prediction says peak where the "
            "hardware says zero crossing. Fine for a settling-time estimate, "
            "useless for anything that has to stay in step.<br><br>"
            "<b>The rule: drop √(1−ζ²) from magnitudes freely; keep it in "
            "anything you will integrate over time or add up around a "
            "loop.</b>", "warn"))
        self.add(lt)

        # ---- the two non-oscillating branches ----------------------------
        no = Card("the other two branches: ζ = 1 and ζ > 1, where there is no "
                  "ω_d to have")
        no.add(body(
            "The boxed formula divides by √(1−ζ²), so it says nothing at all "
            "once ζ reaches 1. The two remaining branches of the quadratic "
            "have to be solved separately, and neither contains a "
            "trigonometric function anywhere — which is the algebraic form of "
            "\"it does not oscillate\"."))
        no.add(body(
            "<b>ζ = 1 — repeated root.</b> Both roots sit at −ω<sub>n</sub>, "
            "so e<sup>−ω<sub>n</sub>t</sup> is only <i>one</i> solution and a "
            "second-order equation needs two. The standard repeated-root rule "
            "supplies the missing one by multiplying by t:"))
        no.add(math_label(r"x(t) = e^{-\omega_n t}\left[x_0 + "
                          r"(v_0 + \omega_n x_0)\,t\right]", 17))
        no.add(body(
            "The bracket is a straight line and the exponential beats it, so "
            "the product rises at most once and then decays. <b>At most one "
            "extremum, and no crossing unless the initial velocity points "
            "hard enough the wrong way</b> — the boundary case, exactly."))
        no.add(body(
            "<b>ζ > 1 — two real roots.</b> Call them "
            "s<sub>1,2</sub> = −ω<sub>n</sub>(ζ ∓ √(ζ²−1)). The answer is a "
            "difference of two exponentials, and the constants come from the "
            "same two initial conditions:"))
        no.add(math_label(r"x(t) = C_1 e^{s_1 t} + C_2 e^{s_2 t}, \qquad "
                          r"C_1 = \frac{v_0 - s_2 x_0}{s_1 - s_2}, \qquad "
                          r"C_2 = \frac{s_1 x_0 - v_0}{s_1 - s_2}", 16))
        no.add(callout(
            "<b>And here is the thing worth taking away from the overdamped "
            "branch.</b> As ζ rises past 1 the two roots do not both move "
            "left — <b>they split, and one of them moves back towards the "
            "origin</b>. At ζ = 3 they are at −0.17 ω<sub>n</sub> and "
            "−5.83 ω<sub>n</sub>.<br><br>"
            "The slow one dominates everything you see, so a heavily "
            "overdamped joint behaves like a <i>first-order</i> system with "
            "τ = 1/(0.17 ω<sub>n</sub>) — nearly six times slower than the "
            "critically damped case. <b>That is why more damping is not "
            "safer past ζ = 1</b>: you are not adding stability, you are "
            "dragging a pole towards the imaginary axis.", "warn"))
        self.add(no)

        # ---- logarithmic decrement ---------------------------------------
        ld = Card("measuring ζ from the trace: the logarithmic decrement")
        ld.add(body(
            "Everything above goes from parameters to a curve. On hardware "
            "you have the curve and want the parameters, and for ζ there is a "
            "method that needs no model, no excitation equipment and no "
            "force sensor — just a ring-down and a ruler."))
        ld.add(body(
            "<b>The idea in one line.</b> The cosine repeats exactly every "
            "damped period T<sub>d</sub> = 2π/ω<sub>d</sub>, so two samples "
            "one period apart differ <i>only</i> by the envelope. Take any "
            "two points n periods apart and the cosines cancel identically:"))
        ld.add(math_label(r"\frac{x(t)}{x(t + nT_d)} = "
                          r"\frac{A e^{-\zeta\omega_n t}\cos(\omega_d t"
                          r"-\varphi)}"
                          r"{A e^{-\zeta\omega_n (t+nT_d)}"
                          r"\cos(\omega_d t + 2\pi n - \varphi)} "
                          r"= e^{\zeta\omega_n n T_d}", 16))
        ld.add(body(
            "<b>Now take the log, and watch ω<sub>n</sub> disappear.</b> "
            "Substitute T<sub>d</sub> = 2π/ω<sub>d</sub> and "
            "ω<sub>d</sub> = ω<sub>n</sub>√(1−ζ²), and the ω<sub>n</sub> "
            "cancels top and bottom:"))
        ld.add(math_label(r"\ln\frac{x(t)}{x(t+nT_d)} = "
                          r"\zeta\omega_n\,n\,\frac{2\pi}{\omega_d} = "
                          r"\frac{2\pi n \zeta}{\sqrt{1-\zeta^2}} "
                          r"\;\approx\; 2\pi n \zeta", 17))
        ld.add(math_label(r"\boxed{\;\delta \equiv \frac{1}{n}"
                          r"\ln\frac{x(t)}{x(t+nT_d)} "
                          r"\qquad\Longrightarrow\qquad "
                          r"\zeta = \frac{\delta}{\sqrt{4\pi^2 + \delta^2}} "
                          r"\;\approx\; \frac{\delta}{2\pi}\;}", 17))
        ld.add(callout(
            "<b>ω<sub>n</sub> cancelled, and that is what makes this "
            "usable.</b><br><br>"
            "You do not need to know the stiffness, the inertia, the natural "
            "frequency or the units of the sensor. Two amplitudes and a count "
            "of cycles between them give you ζ outright — and because the "
            "ratio is dimensionless, an uncalibrated sensor works perfectly "
            "well. Hit the joint, record the ring-down, measure two peaks, "
            "divide, take a log.<br><br>"
            "Then, if you also count the time for those n cycles, you have "
            "ω<sub>d</sub> = 2πn/Δt, and ω<sub>n</sub> = ω<sub>d</sub>/√(1−ζ²) "
            "follows. <b>One ring-down gives you both parameters of the "
            "system.</b>", "key"))
        ld.add(body(
            "<b>The rule of thumb for choosing n: pick enough cycles that the "
            "amplitude has dropped by at least half.</b> That is not "
            "arbitrary — it is a noise argument. δ comes from a ratio, so the "
            "fractional error in δ goes roughly as the sensor noise divided "
            "by ln(ratio). Comparing two peaks that differ by 3% means "
            "dividing your noise by 0.03 and the answer is garbage; comparing "
            "peaks that differ by 2× means dividing by ln 2 = 0.69 and the "
            "answer is solid.<br><br>"
            "Half-amplitude means 2πnζ ≈ ln 2 = 0.693, so:"))
        ld.add(math_label(r"n_{50\%} \approx \frac{0.11}{\zeta}", 17))
        ld.add(body(
            "<b>ζ = 0.05 → about 2 cycles. ζ = 0.01 → about 11. ζ = 0.3 → "
            "less than one</b>, which is the honest warning attached to this "
            "method: at heavy damping there are not enough peaks left to "
            "measure, and by ζ = 1 there are none at all. Log decrement is a "
            "<i>lightly damped</i> technique — which is fine, because a "
            "lightly damped system is exactly the case where you urgently "
            "need to know ζ and cannot guess it.", dim=True))
        ld.add(body(
            "<b>Two practical cautions.</b> Use <b>peaks</b>, not arbitrary "
            "samples — a peak is where the derivative is zero, so a small "
            "timing error costs you almost no amplitude error, whereas on the "
            "steep part of the curve it costs a lot. And subtract the "
            "<b>resting offset</b> first: the derivation assumes the "
            "oscillation decays to zero, and a gravity sag or a sensor bias "
            "makes every ratio wrong in the same direction, which shows up as "
            "a ζ that drifts as you choose later and later peaks. If your "
            "answer depends on which pair you picked, you have an offset.",
            dim=True))
        self.add(ld)

        self.add(callout(
            "<b>What the next page adds, and why it is only one more term.</b> "
            "Everything above is the <i>homogeneous</i> solution — the answer "
            "when the right-hand side is zero. Put a force on the right and "
            "linearity splits the problem in two: a <b>particular</b> solution "
            "that matches the input, plus this same free response, sized so "
            "the total starts where the system actually started.<br><br>"
            "That is why the step response on the next page looks like "
            "<b>1 − (this)</b>: the particular solution for a constant input "
            "is the constant 1, and the free vibration is what rides on top "
            "while the system gets there. And it is why a swept sine looks "
            "like <b>a sine at the drive frequency plus (this)</b> — with the "
            "free part fading out, which is exactly what \"wait for the "
            "transient to die\" means.", "good"))

        self.finish()

    # ------------------------------------------------------------------
    def _redraw_free(self):
        """
        The free response from (x0, v0), drawn as its two component terms plus
        their sum, so the amplitude-phase collapse is something you watch
        rather than something you are told.

        All three branches of the quadratic are here, because the whole point
        of the page is that the sign of zeta^2 - 1 decides the shape:

            zeta < 1   complex pair   -> decaying cosine inside an envelope
            zeta = 1   repeated root  -> (a + b t) e^(-wn t)
            zeta > 1   two real roots -> C1 e^(s1 t) + C2 e^(s2 t)
        """
        x0 = float(self.s_x0.value())           # degrees
        v0 = float(self.s_v0.value())           # degrees / second
        wn = self.s_wnf.value() / 10.0
        z = self.s_zf0.value() / 100.0
        self.l_x0.setText(f"{x0:.0f}°")
        self.l_v0.setText(f"{v0:.0f}°/s")
        self.l_wnf.setText(f"{wn:.1f} rad/s")
        self.l_zf0.setText(f"{z:.2f}")

        n = 900
        critical = abs(z - 1.0) < 5e-3

        if z < 1.0 and not critical:
            # ---- underdamped: the branch the boxed formula covers ---------
            wd = wn * math.sqrt(1.0 - z * z)
            c1 = x0
            # the envelope is already falling at t=0, so the oscillation's own
            # share of the initial slope is v0 PLUS what the envelope takes
            c2 = (v0 + z * wn * x0) / wd
            amp = math.hypot(c1, c2)
            phi = math.degrees(math.atan2(c2, c1))
            period = 2 * math.pi / wd
            dur = min(8.0, 6.0 * period)
            ts = [i * dur / n for i in range(n + 1)]
            env = [math.exp(-z * wn * t) for t in ts]
            p1 = [c1 * e * math.cos(wd * t) for t, e in zip(ts, env)]
            p2 = [c2 * e * math.sin(wd * t) for t, e in zip(ts, env)]
            lab1 = "x₀·cos(ω_d t)  — loaded as position"
            lab2 = "(v₀+ζω_n x₀)/ω_d · sin(ω_d t)  — loaded as speed"
            labt = "their sum = A·e^(−ζω_n t)·cos(ω_d t − φ)"
            regime = "underdamped" if z > 0 else "undamped"
            reg_col = theme.WARN if 0 < z < 0.5 else (
                theme.BAD if z <= 0 else theme.GOOD)
        elif critical:
            # ---- critical: repeated root, so the second solution is t e^st -
            ts = [i * (6.0 / (wn)) / n for i in range(n + 1)]
            env = [math.exp(-wn * t) for t in ts]
            p1 = [x0 * e for e in env]
            p2 = [(v0 + wn * x0) * t * e for t, e in zip(ts, env)]
            amp, phi, period = abs(x0), 0.0, math.inf
            lab1 = "x₀·e^(−ω_n t)"
            lab2 = "(v₀+ω_n x₀)·t·e^(−ω_n t)  — the repeated-root term"
            labt = "their sum — no cosine anywhere"
            regime, reg_col = "critical", theme.GOOD
        else:
            # ---- overdamped: two real roots, and one of them is slow ------
            r = wn * math.sqrt(z * z - 1.0)
            s1, s2 = -z * wn + r, -z * wn - r     # s1 is the SLOW one
            c1 = (v0 - s2 * x0) / (s1 - s2)
            c2 = (s1 * x0 - v0) / (s1 - s2)
            dur = min(12.0, 6.0 / abs(s1))
            ts = [i * dur / n for i in range(n + 1)]
            p1 = [c1 * math.exp(s1 * t) for t in ts]
            p2 = [c2 * math.exp(s2 * t) for t in ts]
            env = [math.exp(s1 * t) for t in ts]   # the slow pole's envelope
            amp, phi, period = abs(x0), 0.0, math.inf
            lab1 = f"slow root  s₁ = {s1:.2f}  — this one is the shape"
            lab2 = f"fast root  s₂ = {s2:.2f}  — gone almost immediately"
            labt = "their sum — two exponentials, no oscillation"
            regime, reg_col = "overdamped", theme.WARN

        tot = [a + b for a, b in zip(p1, p2)]

        self.st_A.set(f"{amp:.2f}°")
        self.st_phi.set("—" if z >= 1.0 else f"{phi:.1f}°")
        if abs(x0) > 1e-6 and z < 1.0:
            g = amp / abs(x0)
            self.st_gain.set(f"{g:.2f}×")
            self.st_gain.set_color(theme.GOOD if g < 1.05 else theme.WARN)
        else:
            self.st_gain.set("x₀ = 0" if abs(x0) <= 1e-6 else "—")
            self.st_gain.set_color(theme.TEXT_DIM)
        self.st_per.set("none" if not math.isfinite(period)
                        else f"{period:.3f} s")
        self.st_regf.set(regime)
        self.st_regf.set_color(reg_col)

        c = self.cfv
        c.clear()
        a = c.ax
        a.plot(ts, p1, color=theme.TEXT_FAINT, lw=1.2, ls="--", label=lab1)
        a.plot(ts, p2, color=theme.CYAN, lw=1.2, ls="--", alpha=0.8, label=lab2)
        a.plot(ts, tot, color=theme.ACCENT, lw=2.4, label=labt)
        if z < 1.0 and not critical:
            a.plot(ts, [amp * e for e in env], color=theme.VIOLET, lw=1.1,
                   ls=":", label="±A envelope")
            a.plot(ts, [-amp * e for e in env], color=theme.VIOLET, lw=1.1,
                   ls=":")
        a.axhline(0, color=theme.BORDER, lw=1.0)
        a.scatter([0.0], [x0], s=45, color=theme.WARN, zorder=6)
        a.annotate("x₀", (0.0, x0), color=theme.WARN, fontsize=8,
                   xytext=(6, 4), textcoords="offset points")
        a.set_xlabel("time (s)")
        a.set_ylabel("x (°)")
        a.set_title("free vibration — no input, only initial conditions",
                    fontsize=9)
        c.legend(loc="upper right")
        c.refresh()

        if z >= 1.0 and not critical:
            r = wn * math.sqrt(z * z - 1.0)
            s1, s2 = -z * wn + r, -z * wn - r
            self.tfv.setText(
                f"<b>ζ = {z:.2f} &gt; 1 — overdamped, and the roots have "
                f"split.</b> s₁ = {s1:.2f} and s₂ = {s2:.2f} per second. The "
                f"fast one is {abs(s2/s1):.1f}× quicker and is over almost "
                f"before the plot starts; <b>everything you see is the slow "
                f"root</b>, which behaves like a first-order lag of "
                f"τ = {1/abs(s1):.3f} s. Note s₁ is <i>closer to zero</i> "
                f"than the critical case's −{wn:.1f}: more damping moved one "
                f"pole the wrong way.")
        elif critical:
            self.tfv.setText(
                f"<b>ζ = 1 — critical, the boundary.</b> Both roots sit on "
                f"top of each other at −{wn:.1f}, so one exponential cannot "
                f"carry two initial conditions and the second solution has to "
                f"be t·e^(−ω_n t) — the cyan curve. It rises, the exponential "
                f"beats it, and the sum reaches rest without a single "
                f"crossing. This is the fastest arrival that has no "
                f"overshoot at all.")
        elif abs(x0) < 1e-6:
            self.tfv.setText(
                f"<b>x₀ = 0 — a pure hammer blow.</b> The cosine term is "
                f"gone, so the answer is a clean sine of amplitude "
                f"v₀/ω_d = {amp:.2f}°, and φ = {phi:.0f}°. All the energy "
                f"entered as kinetic and the spring converts it to "
                f"displacement over the first quarter cycle.")
        elif abs(v0) < 1e-6 and z <= 0:
            self.tfv.setText(
                f"<b>v₀ = 0 — released from rest.</b> The sine term is gone, "
                f"A = |x₀| = {amp:.2f}° and φ = 0°. This is the only case "
                f"where the peak equals the starting displacement — and it is "
                f"the case textbooks draw, which is why the general result "
                f"surprises people.")
        else:
            extra = (amp / abs(x0) - 1.0) * 100.0 if abs(x0) > 1e-6 else 0.0
            decay = ("100% of the one before — nothing is being taken, so it "
                     "rings forever" if z <= 0 else
                     f"{math.exp(-2*math.pi*z/math.sqrt(1-z*z))*100:.0f}% of "
                     f"the one before — that ratio is the logarithmic "
                     f"decrement")
            self.tfv.setText(
                f"<b>A = {amp:.2f}° against a start of {x0:.0f}°</b> — the "
                f"envelope starts {extra:+.0f}% above where the curve began, "
                f"because v₀ = {v0:.0f}°/s contributes through the second leg "
                f"of the triangle. Flip the sign of v₀ and A is unchanged; "
                f"only φ = {phi:.0f}° moves. Damped period "
                f"{period:.3f} s, and each swing is {decay}.")


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

        sh = Card("what the curve actually looks like — first order vs second "
                  "order, side by side")
        sh.add(body(
            "Before any formula, the <b>shape</b>, because the two are easy to "
            "picture wrongly:"))
        sh.add(body(
            "<b>First order.</b> Starts at zero, rises smoothly, decelerating "
            "the whole way, and flattens onto the plateau. <b>Monotonic</b> — "
            "it never goes down, never crosses its target, never wiggles. One "
            "clean curve. (The previous page's argument: nothing is left over "
            "when it arrives.)<br><br>"
            "<b>Second order, underdamped</b> — the common case on a real "
            "joint. Starts at zero, rises — and <b>keeps going past the "
            "target</b>. Comes back down, crosses the target again, <b>dips "
            "below it</b> (undershoot), turns around, overshoots again but "
            "less, and keeps swapping sides with each swing smaller than the "
            "last, converging on the plateau."))
        sh.add(callout(
            "<b>The image that gets it right: a bouncing ball.</b> Each bounce "
            "is smaller than the one before, the bounces get closer together in "
            "amplitude, and the whole thing converges onto the floor. It does "
            "not <i>approach</i> the floor smoothly — it repeatedly overshoots "
            "and comes back, with the excursions shrinking.<br><br>"
            "And the shrinking follows a rule: the peaks sit on a decaying "
            "exponential <b>envelope</b>, e<sup>−ζω<sub>n</sub>t</sup>. That "
            "envelope is <i>the same shape as the entire first-order "
            "response</i>. So the honest one-liner is: <b>a second-order "
            "response is a first-order decay with an oscillation living inside "
            "it.</b><br><br>"
            "The envelope is drawn as the dashed curves on the plot below, and "
            "<b>the response touches it exactly at every peak and trough</b> — "
            "it is the curve the extrema ride on. The envelope is set by the "
            "<b>real</b> part of the poles (−ζω<sub>n</sub>); the wiggling "
            "inside it is set by the <b>imaginary</b> part (ω<sub>d</sub>). Two "
            "parts of the pole, two features of the picture.", "key"))
        sh.add(body(
            "<b>And the envelope is where the overshoot formula comes "
            "from.</b> The first peak happens at t<sub>p</sub> = π/ω<sub>d</sub>. "
            "Put that into the envelope and the exponent becomes "
            "ζω<sub>n</sub>·π/(ω<sub>n</sub>√(1−ζ²)) — the ω<sub>n</sub> "
            "cancels, and what is left is"))
        sh.add(math_label(r"M_p = e^{-\zeta\omega_n t_p} "
                          r"= e^{-\pi\zeta/\sqrt{1-\zeta^2}}", 16))
        sh.add(body(
            "…the formula from the previous card, derived rather than quoted. "
            "It also explains, in one line, <b>why overshoot cannot depend on "
            "ω<sub>n</sub></b>: a faster system has a faster-decaying envelope "
            "<i>and</i> reaches its peak proportionally sooner, and the two "
            "effects cancel exactly.", dim=True))
        sh.add(body(
            "<b>Raise ζ and the wiggles disappear before the curve does.</b> At "
            "ζ = 1 there is no crossing at all and the response looks "
            "first-order-ish again — smooth, monotonic — except that it starts "
            "flat rather than at full slope, because the mass has to be "
            "accelerated first. That subtle difference at t = 0 is the "
            "last visible trace of the second energy store.", dim=True))
        self.add(sh)

        # ---- the step response, solved in full ---------------------------
        so = Card("the step response, actually solved — and then every metric "
                  "falls out of it")
        so.add(body(
            "The envelope argument above gets the overshoot right, but it "
            "leans on knowing where the peak is. Do it properly instead: "
            "<b>write down y(t)</b>, and then the peak, the overshoot and the "
            "settling time are three questions you <i>ask</i> of a function "
            "you already have, rather than three formulas to memorise."))
        so.add(body(
            "<b>Step 1 — split the problem, which is all linearity ever "
            "does.</b> With a constant command r = 1 on the right-hand side:"))
        so.add(math_label(r"\ddot y + 2\zeta\omega_n\dot y + \omega_n^2 y "
                          r"= \omega_n^2 \qquad\Longrightarrow\qquad "
                          r"y(t) = \underbrace{y_p}_{\text{particular}} "
                          r"+ \underbrace{y_h(t)}_{\text{free vibration}}",
                          17))
        so.add(body(
            "The <b>particular</b> part is whatever holds the equation true "
            "forever. Try a constant: the two derivatives vanish and you are "
            "left with ω<sub>n</sub>²y = ω<sub>n</sub>², so "
            "<b>y<sub>p</sub> = 1</b>. That is the final value, and it took "
            "one line.<br><br>"
            "The <b>homogeneous</b> part is the previous page, unchanged — "
            "the free vibration of this same joint, "
            "A e<sup>−ζω<sub>n</sub>t</sup>cos(ω<sub>d</sub>t − φ). Nothing "
            "about it depends on the input; the input only decides how much "
            "of it there is."))
        so.add(body(
            "<b>Step 2 — the initial conditions pick A and φ.</b> A step onto "
            "a joint at rest means y(0) = 0 and ẏ(0) = 0. But the particular "
            "part is already sitting at 1, so the free part has to start at "
            "<b>−1</b> to cancel it. Feed x<sub>0</sub> = −1, v<sub>0</sub> = 0 "
            "into the amplitude formula from the previous page:"))
        so.add(math_label(r"A = \sqrt{(-1)^2 + \left(\frac{0 + "
                          r"\zeta\omega_n(-1)}{\omega_d}\right)^{2}} "
                          r"= \sqrt{1 + \frac{\zeta^2}{1-\zeta^2}} "
                          r"= \frac{1}{\sqrt{1-\zeta^2}}", 17))
        so.add(body(
            "Write the result with a sine instead of a cosine — same function, "
            "phase shifted by 90°, and this is the form everyone quotes:"))
        so.add(math_label(r"\boxed{\;y(t) = 1 - \frac{e^{-\zeta\omega_n t}}"
                          r"{\sqrt{1-\zeta^2}}\,\sin(\omega_d t + \varphi),"
                          r"\qquad \varphi = \arccos\zeta\;}", 18))
        so.add(body(
            "<b>Every symbol in that line has already been earned.</b> The "
            "<b>1</b> is the particular solution. The "
            "<b>e<sup>−ζω<sub>n</sub>t</sup></b> is the pole's real part. "
            "<b>ω<sub>d</sub></b> is its imaginary part. The "
            "<b>1/√(1−ζ²)</b> is the initial-condition amplitude A. And "
            "<b>φ = arccos ζ</b> is the <i>same angle the poles make with the "
            "negative real axis</i> — the one the pole-plot card called \"the "
            "angle is the damping\". It shows up here because it is the same "
            "right triangle: adjacent ζ, opposite √(1−ζ²), hypotenuse 1.",
            dim=True))
        so.add(callout(
            "<b>Sanity-check it at the two ends, which is how you catch a "
            "dropped sign.</b><br><br>"
            "At <b>t = 0</b>: sin φ = √(1−ζ²), so the second term is "
            "(1/√(1−ζ²))·1·√(1−ζ²) = 1, and y(0) = 1 − 1 = <b>0</b>. "
            "Correct.<br>"
            "As <b>t → ∞</b>: the exponential kills the second term and "
            "y → <b>1</b>. Correct — and note this is where \"no steady-state "
            "error\" comes from, with nothing to do with damping.<br>"
            "At <b>ζ → 0</b>: φ → 90°, the exponential → 1, and y = 1 − "
            "cos ω<sub>n</sub>t — a pure undamped oscillation between 0 and "
            "<b>2</b>. That is 100% overshoot, which is exactly what the "
            "formula predicts at ζ = 0.", "key"))

        so.add(body(
            "<b>Step 3 — differentiate once, and the rest of the page is "
            "arithmetic.</b> The derivative looks like it should be a mess of "
            "two terms, but the ζ and √(1−ζ²) in them are cos φ and sin φ, so "
            "the angle-subtraction rule collapses the pair into a single "
            "sine — and the φ <b>disappears</b>:"))
        so.add(math_label(r"\dot y(t) = \frac{\omega_n\,e^{-\zeta\omega_n t}}"
                          r"{\sqrt{1-\zeta^2}}\;\sin(\omega_d t)", 17))
        so.add(body(
            "<b>That one line is worth more than the three formulas below "
            "it.</b> The slope of a second-order step response is a decaying "
            "sine at ω<sub>d</sub>, with <b>no phase offset at all</b>. So the "
            "turning points are wherever sin ω<sub>d</sub>t = 0 — and they are "
            "evenly spaced, forever, at multiples of π/ω<sub>d</sub>.",
            dim=True))
        self.add(so)

        d = Card("the four metrics, each one derived in a line")
        d.add(body(
            "<b>Peak time t<sub>p</sub>.</b> Set ẏ = 0. The exponential is "
            "never zero, so the condition is sin ω<sub>d</sub>t = 0, i.e. "
            "ω<sub>d</sub>t = nπ. n = 0 is the start; <b>n = 1 is the first "
            "peak</b>; n = 2 is the first trough, and so on:"))
        d.add(math_label(r"t_p = \frac{\pi}{\omega_d}, \qquad "
                         r"t_{\text{n-th extremum}} = \frac{n\pi}{\omega_d}",
                         17))
        d.add(body(
            "So the peaks and troughs alternate on a fixed grid of half damped "
            "periods. Counting visible wiggles on a scope trace and dividing is "
            "how you measure ω<sub>d</sub> off hardware."))
        d.add(body(
            "<b>Overshoot M<sub>p</sub>.</b> Put t<sub>p</sub> back into y(t). "
            "The sine term becomes sin(π + φ) = −sin φ = −√(1−ζ²), the minus "
            "signs cancel, and the √(1−ζ²) <b>divides out against the "
            "amplitude</b> — which is why the answer is so much simpler than "
            "the function it came from:"))
        d.add(math_label(r"M_p = y(t_p) - 1 = \frac{\sqrt{1-\zeta^2}}"
                         r"{\sqrt{1-\zeta^2}}\,e^{-\zeta\omega_n \pi/\omega_d} "
                         r"= e^{-\pi\zeta/\sqrt{1-\zeta^2}}", 17))
        d.add(body(
            "and the ω<sub>n</sub> cancels in the exponent too, because "
            "ω<sub>n</sub>/ω<sub>d</sub> = 1/√(1−ζ²). <b>Two cancellations, "
            "and that is the whole reason overshoot is a function of ζ "
            "alone.</b> It is not a deep fact about robots; it is those two "
            "ratios.<br><br>"
            "The same substitution with n instead of 1 gives every later "
            "extremum: the n-th one overshoots by "
            "e<sup>−nπζ/√(1−ζ²)</sup>, alternating sides. Each swing is the "
            "previous one raised to the same power — which is the logarithmic "
            "decrement from earlier on the page, arriving a second time from a "
            "different direction.", dim=True))
        d.add(body(
            "<b>Settling time t<sub>s</sub>.</b> \"Settled\" means the "
            "oscillation is trapped inside a band. The sine is bounded by 1, "
            "so |y − 1| never exceeds the envelope, and you solve the envelope "
            "for the band instead of solving y:"))
        d.add(math_label(r"\frac{e^{-\zeta\omega_n t_s}}{\sqrt{1-\zeta^2}} "
                         r"= \delta \;\Longrightarrow\; "
                         r"t_s = \frac{-\ln\!\left(\delta\sqrt{1-\zeta^2}"
                         r"\right)}{\zeta\omega_n} \;\approx\; "
                         r"\frac{4}{\zeta\omega_n}\ \ (\delta = 2\%)", 16))
        d.add(body(
            "−ln(0.02) = 3.91, and the √(1−ζ²) correction is small for the ζ "
            "anyone uses, so it gets rounded to 4. <b>That is the entire "
            "provenance of the famous 4/(ζω<sub>n</sub>)</b>: a logarithm of "
            "the tolerance you chose, divided by the real part of the pole. "
            "Use −ln(0.05) = 3.0 if your spec is a 5% band — the rule is not "
            "attached to the number 4.", dim=True))
        d.add(body(
            "<b>Rise time t<sub>r</sub>.</b> This is the one with no clean "
            "closed form: solving y(t) = 0.9 means solving a transcendental "
            "equation, because t appears both in the exponential and inside "
            "the sine. Everyone therefore quotes a fit, and it is honest to "
            "call it that:"))
        d.add(math_label(r"t_r^{(0-100\%)} = \frac{\pi - \varphi}{\omega_d} "
                         r"\qquad "
                         r"t_r^{(10-90\%)} \approx "
                         r"\frac{2.16\zeta + 0.60}{\omega_n}\ \ "
                         r"(0.3 \leq \zeta \leq 0.8)", 16))
        d.add(body(
            "The first one <i>is</i> exact, and it is the same calculation as "
            "t<sub>p</sub>: the response first touches its final value when "
            "the sine term vanishes, ω<sub>d</sub>t + φ = π. It is only usable "
            "for underdamped systems, because an overdamped one never reaches "
            "100% in finite time — which is exactly why the 10–90% definition "
            "and its fitted formula exist.", dim=True))
        d.add(callout(
            "<b>And the two cases the boxed formula does not cover, because "
            "√(1−ζ²) is zero or imaginary.</b><br><br>"
            "At <b>ζ = 1</b> the two roots collide at −ω<sub>n</sub>. A "
            "repeated root only supplies one exponential, so the second "
            "solution is t·e<sup>−ω<sub>n</sub>t</sup> — the standard "
            "repeated-root rule — and the answer is "
            "<b>y = 1 − e<sup>−ω<sub>n</sub>t</sup>(1 + ω<sub>n</sub>t)</b>. "
            "No sine anywhere: nothing oscillates, and the (1 + ω<sub>n</sub>t) "
            "is the algebraic ghost of the missing wiggle.<br><br>"
            "At <b>ζ > 1</b> the roots are two distinct real numbers "
            "−ω<sub>n</sub>(ζ ∓ √(ζ²−1)), and y is a difference of two plain "
            "exponentials. The <b>slower</b> one dominates everything you see, "
            "which is the precise reason overdamped is slower than critical: "
            "you have pushed one pole left, but the other one has moved "
            "<i>right</i>, towards the origin.", "warn"))
        self.add(d)

        m = Card("the four formulas, now that they have been earned")
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

        # ==================================================================
        # frequency response -- the magnitude-vs-omega family
        # ==================================================================
        self.add(hline())
        self.add(title("The same system, shaken instead of stepped — where the "
                       "resonance comes from"))

        fr = Card("stop letting go of it, and start shaking it")
        fr.add(body(
            "Everything above released the joint and watched. Now do the other "
            "experiment: drive it with a sinusoidal torque at frequency ω, wait "
            "for the transient to die, and ask <b>how far does it move</b>. "
            "Sweep ω and plot the answer. That plot is the frequency response, "
            "and it has three completely different regions — each one a "
            "different physical thing doing the resisting."))
        fr.add(body(
            "<table cellpadding='7'>"
            "<tr><td><b>ω ≪ ω<sub>n</sub></b><br><i>slow shaking</i></td>"
            "<td><b>The spring resists you.</b> You push slowly, the joint has "
            "all the time in the world to follow, and the only thing opposing "
            "you is the spring stretching. Amplitude = τ/K — <b>flat</b>, and "
            "independent of frequency. Motion is <b>in phase</b> with your push "
            "(0°): you push right, it goes right.</td></tr>"
            "<tr><td><b>ω ≈ ω<sub>n</sub></b><br><i>resonance</i></td>"
            "<td><b>Neither spring nor mass resists you — they cancel.</b> The "
            "spring force and the inertial force are equal and opposite here, "
            "so the <i>only</i> thing left opposing you is the damper. You are "
            "pushing at exactly the rate the energy wants to slosh, so every "
            "push adds energy in step with the motion and it accumulates — "
            "until the damper's losses grow to match what you are putting in. "
            "<b>Small damper ⇒ enormous amplitude.</b> Phase is exactly "
            "<b>−90°</b>.</td></tr>"
            "<tr><td><b>ω ≫ ω<sub>n</sub></b><br><i>fast shaking</i></td>"
            "<td><b>The mass resists you.</b> You reverse before the joint has "
            "gone anywhere; it simply cannot keep up. Amplitude falls as 1/ω² — "
            "<b>−40 dB/decade</b> — and the motion ends up <b>−180°</b> out of "
            "phase: you push right and it is still moving left.</td></tr>"
            "</table>"))
        fr.add(callout(
            "<b>Resonance is not a mathematical artifact — it is the energy "
            "trade being fed.</b><br><br>"
            "The system already wants to pass energy between spring and mass at "
            "ω<sub>n</sub>. Drive it at that frequency and your input arrives in "
            "phase with the velocity every single cycle, so it does positive "
            "work every cycle, and the stored energy climbs. Nothing stops it "
            "except the damper, whose losses grow with amplitude. Equilibrium is "
            "reached when \"energy in per cycle\" equals \"energy the damper "
            "removes per cycle\".<br><br>"
            "So the peak height is set by <b>ζ alone</b>, and it is exactly the "
            "reciprocal of the damping:", "key"))
        fr.add(math_label(r"|G(j\omega_n)| = \frac{1}{2\zeta} = Q, "
                          r"\qquad M_r = \frac{1}{2\zeta\sqrt{1-\zeta^2}} "
                          r"\;\;\text{at}\;\; "
                          r"\omega_r = \omega_n\sqrt{1-2\zeta^2}", 16))
        fr.add(body(
            "<b>Q — the quality factor — is the single most physical number "
            "here.</b> Q = 1/(2ζ) is the gain at ω<sub>n</sub>, and it is also "
            "\"energy stored ÷ energy lost per radian\". A joint with ζ = 0.01 "
            "has Q = 50: shake it at ω<sub>n</sub> with a torque that would "
            "statically move it 1°, and it will swing <b>50°</b>. That is how a "
            "trivial vibration destroys a lightly damped structure, and it is "
            "why the SEA pages care so much about the spring resonance.",
            dim=True))
        self.add(fr)

        # ---- the swept sine, solved the same way -------------------------
        sw = Card("solve the swept sine too — same split, different particular "
                  "solution")
        sw.add(body(
            "The table above is the answer read off a picture. Here is the "
            "same answer read off the equation, because it is the identical "
            "two-part split that produced the step response, with exactly one "
            "thing changed: the right-hand side."))
        sw.add(math_label(r"\ddot y + 2\zeta\omega_n\dot y + \omega_n^2 y "
                          r"= \omega_n^2\sin\omega t", 17))
        sw.add(body(
            "<b>The particular solution is a sine at the driving "
            "frequency.</b> Not at ω<sub>n</sub>, not at ω<sub>d</sub> — at "
            "<b>ω</b>, the frequency you are shaking it at. That is forced on "
            "you by the algebra: differentiating a sine gives sines of the "
            "same frequency, so nothing on the left can produce any other "
            "frequency. Substitute y<sub>p</sub> = M sin(ωt + ψ), collect "
            "terms, and M and ψ come straight out:"))
        sw.add(math_label(r"M(\omega) = |G(j\omega)| = \frac{\omega_n^2}"
                          r"{\sqrt{(\omega_n^2-\omega^2)^2 "
                          r"+ (2\zeta\omega_n\omega)^2}}, \qquad "
                          r"\psi(\omega) = -\tan^{-1}\!\frac"
                          r"{2\zeta\omega_n\omega}{\omega_n^2-\omega^2}", 16))
        sw.add(body(
            "<b>That denominator is the whole frequency-response story in one "
            "expression.</b> Two terms fight under the square root. "
            "(ω<sub>n</sub>² − ω²) is the spring and the mass, and it goes to "
            "<b>zero</b> when ω = ω<sub>n</sub> — that is them cancelling, "
            "algebraically. The other term, 2ζω<sub>n</sub>ω, is the damper, "
            "and it is the <i>only</i> thing left holding the denominator up "
            "at that point. Small ζ, small denominator, enormous M. The "
            "sentence \"only the damper resists you at resonance\" is that "
            "cancellation.", dim=True))
        sw.add(body(
            "<b>And the homogeneous part is still there, unchanged.</b> "
            "Adding it back gives the complete answer to \"shake it starting "
            "from rest\":"))
        sw.add(math_label(r"y(t) = \underbrace{M\sin(\omega t + \psi)}"
                          r"_{\text{steady state, at }\omega} \;+\; "
                          r"\underbrace{A\,e^{-\zeta\omega_n t}"
                          r"\cos(\omega_d t - \phi)}"
                          r"_{\text{transient, at }\omega_d}", 17))
        sw.add(callout(
            "<b>Two sinusoids at two different frequencies, and only one of "
            "them survives.</b><br><br>"
            "The second term is the free vibration from the previous page, "
            "letter for letter — same envelope, same ω<sub>d</sub>. But "
            "<b>A and φ here are not the initial conditions.</b> The joint "
            "starts at rest, so the transient's job is to cancel whatever the "
            "steady-state term is doing at t = 0, which means A and φ depend "
            "on the <i>drive frequency</i> ω as well as on ζ and "
            "ω<sub>n</sub>. Same shape, different constants, different "
            "meaning — and that is the trap in reusing the letters A and "
            "φ.<br><br>"
            "The transient decays at e<sup>−ζω<sub>n</sub>t</sup> and the "
            "steady-state term does not decay at all. So after roughly "
            "<b>4/(ζω<sub>n</sub>)</b> — the same settling time as the step — "
            "the ω<sub>d</sub> component is gone and only the ω component is "
            "left. <b>That is what \"wait for the transient to die\" means, "
            "and that is how long you have to wait.</b>", "key"))
        sw.add(body(
            "<b>So a frequency-response plot is a plot of M(ω) and ψ(ω), and "
            "nothing else.</b> Pick an ω, drive, wait 4/(ζω<sub>n</sub>), "
            "measure the surviving amplitude ratio and time shift, plot the "
            "point, move to the next ω. The whole Bode plot is that loop. Two "
            "practical consequences fall out of it immediately:<br><br>"
            "&nbsp;&nbsp;<b>1.</b> <b>Sweep too fast and you measure the "
            "transient.</b> A lightly damped joint needs a long dwell at every "
            "point precisely <i>because</i> ζ is small — which is worst "
            "exactly where the interesting peak is. A too-fast sweep smears "
            "the resonance and under-reports its height.<br>"
            "&nbsp;&nbsp;<b>2.</b> <b>The ringing you see while the sweep is "
            "settling is at ω<sub>d</sub>, not at your drive frequency.</b> "
            "Seeing two frequencies beat against each other on the scope is "
            "the transient and the steady state coexisting, and it is the "
            "normal appearance of this equation, not a fault.", dim=True))
        self.add(sw)

        pk = Card("the peak exists only below ζ = 0.707 — and that is the whole "
                  "reason for that number")
        pk.add(body(
            "Look at ω<sub>r</sub> = ω<sub>n</sub>√(1 − 2ζ²). The moment "
            "<b>2ζ² &gt; 1</b>, that square root has nothing real left, and "
            "there is no peak at all — the curve just falls away from DC. That "
            "threshold is:"))
        pk.add(math_label(r"\zeta = \frac{1}{\sqrt{2}} = 0.7071", 17))
        pk.add(body(
            "<b>And it goes out gracefully, not abruptly</b> — worth knowing, "
            "because \"the peak disappears at 0.707\" makes it sound like a "
            "cliff. Feed ζ = 1/√2 into both formulas: ω<sub>r</sub> → 0 "
            "<i>and</i> M<sub>r</sub> → 1 (0 dB). So as you raise ζ the peak "
            "slides <b>leftwards toward DC</b> while simultaneously flattening, "
            "and the two effects finish together. At the threshold the \"peak\" "
            "is at zero frequency and the same height as the DC gain — which is "
            "another way of saying there is no peak.", dim=True))
        pk.add(body(
            "<b>So ζ = 0.707 is not a taste or a tradition.</b> It is the exact "
            "boundary between \"this system amplifies some band of frequencies\" "
            "and \"this system amplifies nothing\". Below it there is a band the "
            "robot is <i>more</i> sensitive to than DC — feed it a disturbance "
            "there and you get it back magnified. At and above it, the response "
            "is <b>maximally flat</b>: every frequency is attenuated or passed, "
            "none is amplified.<br><br>"
            "And at ζ = 0.707 the −3 dB bandwidth comes out almost exactly equal "
            "to ω<sub>n</sub>, so the number you designed for is the number you "
            "measure. Three good properties at one value of ζ, which is why "
            "every controls textbook and every servo drive defaults to it."))
        pk.add(callout(
            "<b>Three frequencies, and they are not the same number.</b> This "
            "trips up everybody, and the SEA page made the same complaint about "
            "actuators.<br><br>"
            "&nbsp;&nbsp;• <b>ω<sub>n</sub> = √(K/J)</b> — the natural "
            "frequency. The pole radius. What it would ring at with no damper.<br>"
            "&nbsp;&nbsp;• <b>ω<sub>d</sub> = ω<sub>n</sub>√(1−ζ²)</b> — what a "
            "<i>step response</i> actually rings at. Slower, because the damper "
            "steals energy mid-trade.<br>"
            "&nbsp;&nbsp;• <b>ω<sub>r</sub> = ω<sub>n</sub>√(1−2ζ²)</b> — where "
            "a <i>swept sine</i> peaks. Slower still.<br><br>"
            "Always ω<sub>r</sub> &lt; ω<sub>d</sub> &lt; ω<sub>n</sub>. At "
            "ζ = 0.1 they are 0.99, 0.995 and 1.0 — indistinguishable, which is "
            "why nobody notices. At ζ = 0.6 they are <b>0.53, 0.80 and "
            "1.0</b> — and now confusing them is a 47% error.", "warn"))
        self.add(pk)

        # ---- interactive: the magnitude/phase family ---------------------
        rd = Card("before the plot: the peak is NOT at ω_n, and the two dots "
                  "that prove it")
        rd.add(body(
            "The widget below is the first place the three frequencies stop "
            "being a table and start being pixels, and there is a specific "
            "misreading it invites. It is worth heading off, because it is "
            "the one people leave this material still believing."))
        rd.add(body(
            "<b>The misreading:</b> \"every curve peaks at ω/ω<sub>n</sub> = 1, "
            "and the ω<sub>r</sub> marker sits to the left of the peak where "
            "the curve is lower — so ω<sub>r</sub> is not where it "
            "peaks.\"<br><br>"
            "<b>What is actually true:</b> the curve peaks at ω<sub>r</sub>, "
            "always, and the magnitude there is the <i>highest point on the "
            "whole curve</i> — strictly higher than the magnitude at "
            "ω<sub>n</sub>. Both of these are exact, not approximate:"))
        rd.add(math_label(r"|G(j\omega_n)| = \frac{1}{2\zeta} = Q "
                          r"\qquad\text{but}\qquad "
                          r"|G(j\omega_r)| = M_r = "
                          r"\frac{1}{2\zeta\sqrt{1-\zeta^2}} "
                          r"\;=\; \frac{Q}{\sqrt{1-\zeta^2}} \;>\; Q", 16))
        rd.add(body(
            "The ratio between them is 1/√(1−ζ²), which is <b>always greater "
            "than 1</b> and is the same factor that appeared in the step "
            "response's amplitude. So M<sub>r</sub> > Q for every ζ > 0."))
        rd.add(body(
            "<b>So why does it look like the peak is at 1.0?</b> Because at "
            "light damping the two are numerically the same to the width of a "
            "drawn line, and light damping is where the peak is tall enough to "
            "look at:"))
        rd.add(body(
            "<table cellpadding='7'>"
            "<tr><td><b>ζ</b></td><td><b>ω<sub>r</sub>/ω<sub>n</sub></b></td>"
            "<td><b>Q at ω<sub>n</sub></b></td>"
            "<td><b>M<sub>r</sub> at ω<sub>r</sub></b></td>"
            "<td><b>gap</b></td></tr>"
            "<tr><td>0.05</td><td>0.9975</td><td>20.0 dB</td><td>20.01 dB</td>"
            "<td>0.01 dB — invisible</td></tr>"
            "<tr><td>0.20</td><td>0.959</td><td>7.96 dB</td><td>8.14 dB</td>"
            "<td>0.18 dB — still invisible</td></tr>"
            "<tr><td>0.40</td><td>0.825</td><td>1.94 dB</td><td>2.70 dB</td>"
            "<td>0.76 dB — now visible</td></tr>"
            "<tr><td>0.60</td><td>0.529</td><td>−1.58 dB</td><td>0.35 dB</td>"
            "<td>1.96 dB — obvious</td></tr>"
            "<tr><td>0.707</td><td>0 — no peak</td><td>−3.0 dB</td>"
            "<td>0 dB at DC</td><td>the peak has reached DC</td></tr>"
            "</table>"))
        rd.add(callout(
            "<b>Read the ζ = 0.6 row again, because it is the one that "
            "settles it.</b> At ω<sub>n</sub> the magnitude is "
            "<b>−1.58 dB</b> — the curve is <i>below</i> 0 dB there, already "
            "attenuating. At ω<sub>r</sub> = 0.53 ω<sub>n</sub> it is "
            "<b>+0.38 dB</b>. The highest point is nowhere near 1.0, and the "
            "point at 1.0 is not even a local maximum.<br><br>"
            "So the rule is: <b>at small ζ the peak is at ω<sub>n</sub> for "
            "all practical purposes; at moderate ζ it is measurably to the "
            "left; and above 0.707 it does not exist.</b> The widget draws a "
            "dot at each of the two points so you can watch them separate "
            "instead of taking this on trust — drag ζ from 0.05 up to 0.65 and "
            "watch the two dots pull apart.", "key"))
        rd.add(body(
            "One more thing the same table explains: <b>the peak height at "
            "ω<sub>n</sub> is the number worth quoting anyway.</b> Q = 1/(2ζ) "
            "is what the SEA and vibration pages use, because it is the "
            "energy-per-radian reading, it is exact, and at the light damping "
            "where any of this is dangerous it is within a rounding error of "
            "the true peak.", dim=True))
        self.add(rd)

        i3 = Card("the plot itself — magnitude and phase against ω, for every ζ")
        i3.add(body(
            "The pale curves are a family of fixed ζ values — 0.05, 0.1, 0.2, "
            "0.4, 0.707, 1.0, 2.0, labelled at the right-hand edge — drawn so "
            "you can see the shape change; the bright one is yours. The x-axis "
            "is ω/ω<sub>n</sub>, so <b>1.0 is always the natural "
            "frequency</b> whatever you set it to.<br><br>"
            "The two dots on the bright curve are the point the card above is "
            "about: <b>violet sits at ω<sub>n</sub> (height Q), red sits at "
            "ω<sub>r</sub> (height M<sub>r</sub>, the true maximum)</b>. The "
            "small faint dots on the pale curves are <i>their</i> peaks, so "
            "the leftward march of ω<sub>r</sub> with rising ζ is visible as a "
            "trail.<br><br>"
            "<b>Four things to check for yourself:</b><br>"
            "&nbsp;&nbsp;<b>1.</b> Every curve passes through the same point at "
            "ω/ω<sub>n</sub> = 1 on the <i>phase</i> plot: exactly <b>−90°</b>, "
            "for every ζ. That is how you find ω<sub>n</sub> from a measured "
            "plant even when damping has flattened the peak out of "
            "existence.<br>"
            "&nbsp;&nbsp;<b>2.</b> Drag ζ down and watch the peak grow without "
            "limit — and watch the phase transition get <i>sharper</i>. A "
            "lightly damped system flips from 0° to −180° almost "
            "instantaneously, which is what makes it so dangerous to wrap a "
            "loop around.<br>"
            "&nbsp;&nbsp;<b>3.</b> Drag ζ from 0.05 up through 0.6 and watch "
            "the <b>two dots separate</b>. Below about 0.2 they are on top of "
            "each other; by 0.6 the red one is at half the frequency and "
            "the violet one has fallen below 0 dB.<br>"
            "&nbsp;&nbsp;<b>4.</b> Walk ζ up towards 0.707 and watch <i>how</i> "
            "the peak goes. It does not shrink in place — the ω<sub>r</sub> "
            "marker <b>slides left towards DC</b> while the peak height falls "
            "to 0 dB, and the two arrive together exactly at ζ = 1/√2. Past "
            "that there is no peak to find.", dim=True))
        self.s_zf = slider(3, 200, 30)           # x0.01
        self.l_zf = QLabel()
        i3.add_layout(slider_row("damping ζ (×0.01)", self.s_zf, self.l_zf))
        self.st_mr = Stat("peak M_r (at ω_r)", "--", theme.BAD)
        self.st_q = Stat("Q = |G| at ω_n", "--", theme.VIOLET)
        self.st_wr = Stat("peak at ω_r", "--", theme.WARN)
        self.st_gap = Stat("M_r − Q", "--", theme.CYAN)
        self.st_bw2 = Stat("−3 dB bandwidth", "--", theme.GOOD)
        i3.add_layout(stat_row(self.st_mr, self.st_q, self.st_wr, self.st_gap,
                               self.st_bw2))
        self.c3 = MplCanvas(width=7.4, height=3.8, nrows=2)
        i3.add(self.c3)
        self.t3 = body("", dim=True)
        i3.add(self.t3)
        self.add(i3)
        self.s_zf.valueChanged.connect(self._redraw_freq)
        self._redraw_freq()

        self.add(callout(
            "<b>What this costs you on a real robot.</b> The frequency response "
            "is not a curiosity — it is the map of which disturbances your "
            "machine amplifies.<br><br>"
            "A leg with a lightly damped SEA spring at 12 Hz and ζ = 0.05 has "
            "<b>Q = 10</b>. Ground texture, a gearbox tooth-mesh harmonic, or a "
            "gait frequency that happens to land near 12 Hz arrives ten times "
            "larger at the joint than its actual size. Nothing is wrong with the "
            "controller; the mechanism is a 10× amplifier in that band.<br><br>"
            "The three fixes are the three terms: <b>add damping</b> (raise ζ — "
            "physical or via the loop's D term), <b>move ω<sub>n</sub></b> away "
            "from the excitation (change K or J), or <b>notch it</b> — with all "
            "the caveats the Lead/Lag page attaches to notches.", "warn"))

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

        # ==================================================================
        # open loop vs closed loop vs the raw plant -- the mix-up that the
        # shared omega_n/zeta vocabulary creates, killed with one picture
        # ==================================================================
        self.add(hline())
        self.add(title("Is the canonical form open-loop or closed-loop? — the "
                       "question that has no answer, and what to ask instead"))

        top = Card("the honest answer: the form is topology-agnostic")
        top.add(body(
            "You have now seen the same expression arrive twice, from opposite "
            "directions, and it is worth stating flatly that <b>neither one is "
            "\"the\" canonical second-order system</b>:"))
        top.add(body(
            "&nbsp;&nbsp;• <b>As a raw physical plant, no controller anywhere.</b> "
            "A mass–spring–damper is 1/(Js² + Bs + K) — normalise it and it is "
            "the canonical form. Nothing has been closed around it. An RLC "
            "circuit, an SEA spring with its load, a flexible link: all of them, "
            "open-loop.<br>"
            "&nbsp;&nbsp;• <b>As the result of closing a loop.</b> Wrap PD "
            "around a rigid inertia — the card directly above — and the closed "
            "loop is the canonical form, with K<sub>p</sub> playing the spring "
            "and K<sub>d</sub> playing the damper. No physical spring exists "
            "anywhere in that machine."))
        top.add(callout(
            "<b>So \"is this formula open-loop or closed-loop?\" is the wrong "
            "question — it is a question about your particular system, not about "
            "the formula.</b> The canonical form is the signature of one thing "
            "and one thing only: <b>a complex-conjugate pole pair</b>. Two poles "
            "off the real axis, however they got there — bolted on by a "
            "mechanical spring, or created by feedback out of nothing.<br><br>"
            "<b>The dividing line you actually want is not open vs closed. It is "
            "two well-separated REAL poles versus a COMPLEX PAIR.</b> Real, "
            "separated poles give a monotonic magnitude curve with no peak of "
            "any kind. A complex pair peaks whenever ζ &lt; 0.707. That is the "
            "distinction doing all the work, and it applies identically on both "
            "sides of the feedback wire.", "key"))
        self.add(top)

        three = Card("three plots, three jobs — and only two of them look alike")
        three.add(body(
            "Where the confusion actually bites is that three different objects "
            "get described with the same ω<sub>n</sub>/ζ words, and people "
            "expect them to look alike on a Bode plot. Two of them do. The one "
            "you check stability on does not."))
        three.add(body(
            "<table cellpadding='7'>"
            "<tr><td></td><td><b>1 · the raw plant P(s)</b></td>"
            "<td><b>2 · the loop gain L(s)</b></td>"
            "<td><b>3 · the closed loop T(s)</b></td></tr>"

            "<tr><td><b>What it is</b></td>"
            "<td>one physical object, shaken. No feedback exists.</td>"
            "<td>controller × plant × sensor, with the feedback wire "
            "<i>imagined cut</i></td>"
            "<td>reference in, real output out, feedback actually closed: "
            "T = L/(1+L)</td></tr>"

            "<tr><td><b>What it answers</b></td>"
            "<td>what does this hardware amplify, and where does it "
            "resonate?</td>"
            "<td><b>how close am I to instability?</b> — gain margin, phase "
            "margin, the −180° crossing</td>"
            "<td><b>how will the robot actually behave?</b> — overshoot, "
            "settling, tracking</td></tr>"

            "<tr><td><b>Magnitude shape</b></td>"
            "<td>flat at its DC gain, resonant bump if ζ &lt; 0.707, then "
            "−40 dB/dec</td>"
            "<td><b>no bump.</b> Starts very high and falls monotonically — "
            "because it usually contains an integrator</td>"
            "<td>flat at ≈ 0 dB, bump if the closed-loop ζ &lt; 0.707, then "
            "rolls off</td></tr>"

            "<tr><td><b>Phase starts at</b></td><td>0°</td>"
            "<td><b>−90°</b> immediately — that is the integrator, and it is "
            "the giveaway</td><td>0°</td></tr>"

            "<tr><td><b>Read it for</b></td><td>hardware resonances, Q</td>"
            "<td>margins — <i>only</i> margins</td>"
            "<td>overshoot, bandwidth, tracking error</td></tr>"
            "</table>"))
        three.add(callout(
            "<b>The practical rule, and it is worth memorising verbatim.</b> "
            "Whenever you are checking gain margin, phase margin or the −180° "
            "crossing, you are looking at <b>L</b> — feedback imagined cut — and "
            "it will typically have no resonant bump and a phase starting at "
            "−90°. Whenever you are predicting overshoot, settling time or how "
            "well a command is tracked, you are looking at <b>T</b> — and that "
            "is where the bump and the whole ω<sub>n</sub>/ζ step-response story "
            "genuinely apply.<br><br>"
            "Plugging numbers read off one picture into a formula meant for the "
            "other is the single most common way this material goes wrong, and "
            "it is invisible while you do it, because both pictures are labelled "
            "with the same two Greek letters.", "warn"))
        self.add(three)

        # ---- interactive: all three, on one pair of axes -------------------
        i4 = Card("all three on one figure — magnitude on top, phase below")
        i4.add(body(
            "The three curves are computed from one setting of ω<sub>n</sub> and "
            "ζ, and they are deliberately the <i>related</i> trio, so the "
            "identity is visible rather than asserted:"))
        i4.add(math_label(r"P(s) = \frac{1}{k}\cdot"
                          r"\frac{\omega_n^2}{s^2+2\zeta\omega_n s+\omega_n^2}"
                          r"\qquad "
                          r"L(s) = \frac{\omega_n^2}{s\,(s+2\zeta\omega_n)}"
                          r"\qquad T = \frac{L}{1+L}", 15))
        i4.add(body(
            "Do the algebra on T once and the point is made permanently: "
            "L/(1+L) with that L clears to ω<sub>n</sub>²/(s² + 2ζω<sub>n</sub>s "
            "+ ω<sub>n</sub>²) — <b>exactly the canonical form</b>. So the green "
            "curve lies on top of the blue one whenever k = 1, even though blue "
            "is a raw open-loop resonator and green is an assembled closed loop. "
            "<b>Same drawing, different roles.</b> Meanwhile the red curve — "
            "which is the <i>only</i> one of the three you may read a margin "
            "from — looks nothing like either of them.", dim=True))
        i4.add(body(
            "<b>Four things to do with the sliders:</b><br>"
            "&nbsp;&nbsp;<b>1.</b> Drop ζ below 0.707 and watch blue and green "
            "grow a bump while red stays perfectly monotonic. The loop gain "
            "never peaks; the thing it produces does.<br>"
            "&nbsp;&nbsp;<b>2.</b> Look at the phase plot at the far left. Blue "
            "and green start at 0°; red starts at <b>−90°</b> and never comes "
            "back. That single fact identifies which curve you have been handed "
            "when nobody labelled it.<br>"
            "&nbsp;&nbsp;<b>3.</b> Move the <b>plant DC gain</b> slider. Blue's "
            "flat left-hand level moves up and down — that level is <b>1/k</b>, "
            "the DC gain, and it has nothing whatever to do with resonance. "
            "Green does not move at all: unity feedback pins the closed loop's "
            "DC gain at ≈ 1 by construction.<br>"
            "&nbsp;&nbsp;<b>4.</b> Watch the phase margin stat as ζ changes. It "
            "is read off red, and it tracks the overshoot of green — which is "
            "the PM ≈ 100ζ bridge, two pages ahead.", dim=True))
        self.s_z4 = slider(5, 200, 40)            # x0.01  zeta
        self.s_k4 = slider(2, 400, 100)           # x0.01  plant DC gain 1/k
        self.l_z4, self.l_k4 = QLabel(), QLabel()
        i4.add_layout(slider_row("damping ζ (×0.01)", self.s_z4, self.l_z4))
        i4.add_layout(slider_row("plant DC gain 1/k", self.s_k4, self.l_k4))
        self.st_pdc = Stat("plant DC gain", "--", theme.ACCENT)
        self.st_ppk = Stat("plant peak", "--", theme.CYAN)
        self.st_tpk = Stat("closed-loop peak", "--", theme.GOOD)
        self.st_lpm = Stat("phase margin of L", "--", theme.VIOLET)
        self.st_tos = Stat("overshoot of T", "--", theme.WARN)
        i4.add_layout(stat_row(self.st_pdc, self.st_ppk, self.st_tpk,
                               self.st_lpm, self.st_tos))
        self.c4 = MplCanvas(width=7.6, height=4.4, nrows=2)
        i4.add(self.c4)
        self.t4 = body("", dim=True)
        i4.add(self.t4)
        self.add(i4)
        for s in (self.s_z4, self.s_k4):
            s.valueChanged.connect(self._redraw_three)
        self._redraw_three()

        two = Card("two separate reasons a magnitude can exceed 1 — do not "
                   "conflate them")
        two.add(body(
            "This is the other half of the same confusion, and it is worth "
            "isolating because both effects push the curve above 0 dB and they "
            "have nothing to do with each other."))
        two.add(body(
            "<b>Reason 1 — the DC level itself.</b> Put ω → 0 into the canonical "
            "magnitude and the square-root term goes to 1, leaving:"))
        two.add(math_label(r"|H(0)| = \frac{1}{k}", 16))
        two.add(body(
            "The flat left-hand part of the curve is just the gain constant out "
            "front. It is above 1 if k &lt; 1, exactly 1 if k = 1, below 1 if "
            "k &gt; 1. No damping, no resonance, no feedback involved — it is a "
            "multiplier. A unity-DC-gain system starts at exactly 0 dB, which is "
            "the normal closed-loop tracking case."))
        two.add(body(
            "<b>Reason 2 — the resonant peak, on top of whatever the DC level "
            "is.</b> Even at k = 1, the curve bumps above its own DC value near "
            "ω<sub>n</sub> when damping is light:"))
        two.add(math_label(r"|H|_{\mathrm{peak}} = \frac{1}{k}\cdot"
                           r"\frac{1}{2\zeta\sqrt{1-\zeta^2}} \approx "
                           r"\frac{1}{2\zeta k}\ \ (\text{small }\zeta), "
                           r"\qquad \omega_r = \omega_n\sqrt{1-2\zeta^2}", 16))
        two.add(callout(
            "<b>DC level = 1/k. Peak-above-DC ≈ 1/(2ζ).</b> The first is a gain "
            "you chose; the second is amplification the physics gives you for "
            "free, and only when ζ &lt; 0.707. A curve sitting at +6 dB on the "
            "left is <i>not</i> resonating — it has a DC gain of 2. A curve that "
            "starts at 0 dB and bulges to +14 dB at ω<sub>r</sub> is resonating, "
            "with Q ≈ 5. Diagnose the left-hand level and the bump "
            "separately.", "key"))
        self.add(two)

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
    def _redraw_three(self):
        """
        The raw plant, the loop gain and the closed loop, on one pair of axes.

        The trio is chosen so that T is ALGEBRAICALLY the canonical form: with
        L = wn^2 / (s(s + 2 zeta wn)), closing unity feedback gives exactly
        wn^2 / (s^2 + 2 zeta wn s + wn^2). Green therefore lands on blue at
        k = 1 -- which is the whole point of the widget, and it is a fact
        rather than a coincidence.
        """
        zeta = self.s_z4.value() / 100.0
        dc = self.s_k4.value() / 100.0          # this is 1/k, the plant DC gain
        self.l_z4.setText(f"{zeta:.2f}")
        self.l_k4.setText(f"{dc:.2f}  ({20*math.log10(dc):+.1f} dB)")

        wn = 10.0
        p = TF([dc * wn * wn], [1.0, 2 * zeta * wn, wn * wn])   # raw plant
        l = TF([wn * wn], [1.0, 2 * zeta * wn, 0.0])            # loop gain
        t = l.feedback()                                        # closed loop

        ws = log_freqs(0.05 * wn, 60.0 * wn, 500)
        _, mp, pp = bode(p, ws)
        _, ml, pl = bode(l, ws)
        _, mt, pt = bode(t, ws)

        peaked = zeta < 0.7071
        mr_db = resonant_peak_db(zeta)         # already in dB, 0 when flat
        self.st_pdc.set(f"{20*math.log10(dc):+.1f} dB")
        self.st_ppk.set("none" if not peaked
                        else f"{mr_db + 20*math.log10(dc):+.1f} dB")
        self.st_ppk.set_color(theme.CYAN if peaked else theme.TEXT_DIM)
        self.st_tpk.set("none" if not peaked else f"{mr_db:+.1f} dB")
        mg = margins(l)
        self.st_lpm.set(f"{mg.phase_margin_deg:.0f}°")
        self.st_tos.set(f"{overshoot_fraction(zeta)*100:.0f} %")

        if peaked:
            self.t4.setText(
                f"<b>ζ = {zeta:.2f} — below 0.707, so blue and green both "
                f"peak.</b> The bump is {mr_db:+.1f} dB above the DC level, at "
                f"ω<sub>r</sub> = {resonant_frequency(zeta, wn):.1f} rad/s. Red "
                "has no bump and never will: an integrator plus one real pole "
                "has no complex pair to resonate with — the complex pair only "
                "appears <i>after</i> the loop is closed, which is why green "
                "peaks and red does not, from the same system.")
        else:
            self.t4.setText(
                f"<b>ζ = {zeta:.2f} — at or above 0.707, so nothing peaks.</b> "
                "All three curves are monotonic now, and blue and green are "
                "still identical to each other while red is still a completely "
                "different shape starting at −90°. That difference is "
                "structural, not a damping effect: it survives every setting of "
                "these sliders.")

        c = self.c4
        c.clear()
        a_m, a_p = c.axes
        for mag, ph, col, lab in (
                (mp, pp, theme.ACCENT, "P — raw plant, open loop"),
                (ml, pl, theme.BAD, "L — loop gain (margins live here)"),
                (mt, pt, theme.GOOD, "T — closed loop (behaviour lives here)")):
            a_m.semilogx(ws, mag, color=col, lw=2.0, label=lab)
            a_p.semilogx(ws, ph, color=col, lw=2.0)
        a_m.axhline(0, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a_m.axvline(wn, color=theme.TEXT_FAINT, lw=1.0, ls=":")
        a_m.set_ylim(-60, 40)
        a_m.set_ylabel("|·|  (dB)")
        a_m.set_title("magnitude — dotted line is ω_n", fontsize=9)
        c.legend(a_m, loc="lower left")
        a_p.axhline(-90, color=theme.TEXT_FAINT, lw=0.9, ls=":")
        a_p.axhline(-180, color=theme.BAD, lw=0.9, ls=":")
        a_p.set_ylabel("phase (deg)")
        a_p.set_xlabel("frequency ω (rad/s)")
        a_p.set_title("phase — red starts at −90°, the other two at 0°",
                      fontsize=9)
        c.refresh()

    # ------------------------------------------------------------------
    def _redraw_freq(self):
        """
        Magnitude and phase against normalised frequency, with a family of zeta
        curves behind the selected one. Plotted against w/wn so the natural
        frequency is always at 1.0 and only the SHAPE varies with zeta -- which
        is the point being made.
        """
        z = self.s_zf.value() / 100.0
        self.l_zf.setText(f"{z:.2f}")
        wn = 1.0                       # normalised: x-axis is w/wn

        ratios = [10 ** (-1.0 + 2.0 * i / 259.0) for i in range(260)]

        def mag_phase(zz):
            m, p = [], []
            for r in ratios:
                g = second_order(wn, zz).response(r)
                m.append(20.0 * math.log10(max(abs(g), 1e-12)))
                # unwrap by hand: a 2nd-order lag runs 0 -> -180, monotonically
                ang = math.degrees(cmath.phase(g))
                if ang > 1.0:
                    ang -= 360.0
                p.append(ang)
            return m, p

        mr_db = resonant_peak_db(z)
        wr = resonant_frequency(z, wn)
        q = quality_factor(z)
        q_db = 20.0 * math.log10(q) if math.isfinite(q) and q > 0 else math.inf
        bw = bandwidth_second_order(z, wn)
        self.st_mr.set("none" if wr <= 0 else f"+{mr_db:.2f} dB")
        self.st_mr.set_color(theme.GOOD if wr <= 0 else
                             (theme.WARN if mr_db < 10 else theme.BAD))
        self.st_q.set(f"{q_db:+.2f} dB" if math.isfinite(q_db) else "∞")
        self.st_wr.set("no peak" if wr <= 0 else f"{wr:.3f} ω_n")
        # the number the confusion is actually about: the peak is ABOVE the
        # value at wn, always, by exactly -20 log10 sqrt(1 - z^2)
        if wr > 0 and math.isfinite(q_db):
            self.st_gap.set(f"{mr_db - q_db:+.2f} dB")
            self.st_gap.set_color(theme.CYAN if mr_db - q_db > 0.3
                                  else theme.TEXT_DIM)
        else:
            self.st_gap.set("—")
            self.st_gap.set_color(theme.TEXT_DIM)
        self.st_bw2.set(f"{bw:.2f} ω_n")

        c = self.c3
        c.clear()
        a1, a2 = c.axes
        for zz in (0.05, 0.1, 0.2, 0.4, 0.707, 1.0, 2.0):
            m, p = mag_phase(zz)
            a1.semilogx(ratios, m, color=theme.TEXT_FAINT, lw=0.9, alpha=0.55)
            a2.semilogx(ratios, p, color=theme.TEXT_FAINT, lw=0.9, alpha=0.55)
            a1.text(ratios[-1], m[-1], f" {zz:g}", color=theme.TEXT_FAINT,
                    fontsize=6.2, va="center")
            # each pale curve's OWN peak, so the leftward march of w_r with
            # rising zeta is a visible trail rather than a claim
            wrr = resonant_frequency(zz, wn)
            if wrr > 0:
                a1.scatter([wrr], [resonant_peak_db(zz)], s=14,
                           color=theme.TEXT_FAINT, alpha=0.8, zorder=4)
        m, p = mag_phase(z)
        a1.semilogx(ratios, m, color=theme.ACCENT, lw=2.4,
                    label=f"your ζ = {z:.2f}")
        a2.semilogx(ratios, p, color=theme.ACCENT, lw=2.4)

        a1.axhline(0, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a1.axhline(-3.0, color=theme.GOOD, lw=1.0, ls=":", label="−3 dB")
        a1.axvline(1.0, color=theme.VIOLET, lw=1.2, ls="-.", label="ω_n")
        # the two dots the card above is about: |G| at w_n, and the real peak
        if math.isfinite(q_db):
            a1.scatter([1.0], [q_db], s=60, color=theme.VIOLET, zorder=7,
                       label=f"at ω_n: {q_db:+.2f} dB")
        if wr > 0:
            a1.axvline(wr, color=theme.BAD, lw=1.2)
            a1.scatter([wr], [mr_db], s=60, color=theme.BAD, zorder=7,
                       label=f"peak at ω_r: {mr_db:+.2f} dB")
            a1.text(wr, mr_db + 1.5, " ω_r", color=theme.BAD, fontsize=7.5)
        a1.set_ylim(-45, max(30, mr_db + 8))
        a1.set_ylabel("|G|  (dB)")
        a1.set_title("magnitude: |G| at ω_n is 1/(2ζ); the true peak is "
                     "higher, and to the LEFT, at ω_r", fontsize=8.5)
        c.legend(a1, loc="lower left")

        a2.axvline(1.0, color=theme.VIOLET, lw=1.2, ls="-.")
        a2.axhline(-90.0, color=theme.VIOLET, lw=1.0, ls=":")
        a2.scatter([1.0], [-90.0], s=45, color=theme.VIOLET, zorder=6)
        a2.set_ylim(-190, 10)
        a2.set_ylabel("phase (deg)")
        a2.set_xlabel("ω / ω_n      (1.0 IS the natural frequency)")
        a2.set_title("phase: every curve passes −90° at ω_n, whatever ζ is",
                     fontsize=8.5)
        c.refresh()

        if wr <= 0:
            self.t3.setText(
                f"<b>ζ = {z:.2f} ≥ 0.707 — there is no peak.</b> The red dot "
                f"and the red ω<sub>r</sub> line are gone because "
                f"√(1−2ζ²) is not a real number any more. The curve falls "
                f"monotonically from DC, and |G| at ω<sub>n</sub> is "
                f"{q_db:+.2f} dB — below 0 dB, so even the natural frequency "
                f"is being attenuated.")
        else:
            gap = mr_db - q_db
            near = gap < 0.25
            self.t3.setText(
                f"<b>Peak = {mr_db:+.2f} dB at ω<sub>r</sub> = "
                f"{wr:.3f} ω<sub>n</sub>; the curve at ω<sub>n</sub> itself is "
                f"only {q_db:+.2f} dB.</b> The peak is {gap:+.2f} dB higher "
                f"than the point at 1.0 and sits {(1-wr)*100:.1f}% to the left "
                + ("— which at this ζ is far too small to see, and is exactly "
                   "why the peak <i>looks</i> like it is at ω<sub>n</sub>. "
                   "Raise ζ past 0.4 and the two dots visibly separate."
                   if near else
                   "— now large enough to read straight off the plot. Note "
                   "the violet dot at ω<sub>n</sub> is no longer anywhere near "
                   "the top of the curve."))

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
            # The peak locus, exp(-zeta*wn*t). Note this is NOT the outer bound
            # of the sinusoid -- that one is larger by 1/sqrt(1-z^2) and is
            # touched between the peaks. This curve is the one that passes
            # exactly THROUGH the extrema of y, which is the one worth drawing:
            # evaluated at the first peak time it reproduces the overshoot
            # formula exactly.
            env = [math.exp(-z * wn * ti) for ti in t]
            a1.plot(t, [1 + e for e in env], color=theme.VIOLET, lw=1.1,
                    ls="--", label="envelope  e^(−ζω_n t)")
            a1.plot(t, [1 - e for e in env], color=theme.VIOLET, lw=1.1,
                    ls="--")
            a1.axhline(1 + overshoot_fraction(z), color=theme.WARN, lw=1.0,
                       ls=":", label="predicted peak")
            a1.axvline(peak_time(z, wn), color=theme.WARN, lw=1.0, ls=":")
            a1.set_ylim(min(-0.15, min(y) - 0.1), max(2.1, 1 + env[0] * 1.05))
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
        r.add(math_label(r"L(s) = \frac{K}{s(s+1)(s+2)}", 16))
        r.add(body(
            "<b>First: where does a characteristic polynomial come from?</b> "
            "This step gets skipped constantly and then nothing afterwards "
            "makes sense. You are handed an <i>open-loop</i> L(s) and you need "
            "the <i>closed-loop</i> denominator. The bridge is the same fact "
            "the Nyquist page is built on — closed-loop poles are where "
            "L(s) = −1, i.e. where 1 + L(s) = 0. So write that down and clear "
            "the fraction:"))
        r.add(math_label(r"1 + \frac{K}{s(s+1)(s+2)} = 0", 16))
        r.add(body(
            "Multiply <b>every term</b> by the denominator s(s+1)(s+2). The "
            "fraction cancels and the 1 becomes the whole denominator:"))
        r.add(math_label(r"s(s+1)(s+2) + K = 0", 16))
        r.add(body("Now just expand the product, left to right:"))
        r.add(math_label(r"s(s+1) = s^2 + s", 15))
        r.add(math_label(r"(s^2+s)(s+2) = s^3 + 2s^2 + s^2 + 2s "
                         r"= s^3 + 3s^2 + 2s", 15))
        r.add(math_label(r"\boldsymbol{s^3 + 3s^2 + 2s + K = 0}", 17))
        r.add(callout(
            "<b>The general rule, so you never have to redo the algebra.</b> "
            "For L(s) = num/den, clearing the fraction in 1 + num/den = 0 "
            "always gives<br><br>"
            "&nbsp;&nbsp;&nbsp;&nbsp;<b>characteristic polynomial = den(L) + "
            "num(L)</b><br><br>"
            "Add the numerator to the denominator. That is the entire "
            "operation, and it is exactly what <code>TF.feedback()</code> does "
            "in one line of <code>ctrlcore/linear.py</code> — "
            "<code>poly_add(self.den, self.num)</code>.<br><br>"
            "Note what it means: the closed-loop poles are the roots of "
            "den + num, and the open-loop poles were the roots of den alone. "
            "<b>Feedback mixes the numerator into the denominator</b>, and that "
            "is why the poles move. Same sentence as the Making It Stable "
            "page, arrived at from the algebra instead.", "key"))
        r.add(body(
            "Those four coefficients — <b>1, 3, 2, K</b> — are what you feed "
            "into the Routh array. Note K sits in the constant term, which is "
            "why it ends up in the last row and why the stability condition "
            "comes out as a bound on K.", dim=True))
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
            "table. Under 6 dB of gain margin is cutting it thin; far beyond "
            "12 dB you are usually trading away performance for margin you do "
            "not need.", dim=True))
        self.add(m)

        # ---- the sign trap ------------------------------------------------
        sg = Card("the minus sign in GM — where it comes from, and what "
                  "positive/negative mean")
        sg.add(body(
            "Read the gain-margin formula again and notice it has a <b>minus "
            "sign glued to the front</b>. That is not decoration; it flips the "
            "convention, and it is the source of a very common mix-up."))
        sg.add(body(
            "At a healthy ω<sub>pc</sub> the loop gain is <i>below</i> 1, so "
            "log<sub>10</sub>|L| is <b>negative</b> — and the leading minus "
            "turns it <b>positive</b>. So, by construction:"))
        sg.add(body(
            "<table cellpadding='7'>"
            "<tr><td><b>|L| at ω<sub>pc</sub></b></td><td><b>raw dB</b></td>"
            "<td><b>GM = −(raw dB)</b></td><td><b>meaning</b></td></tr>"
            "<tr><td>0.25</td><td>−12 dB</td>"
            "<td style='color:#3fb950'><b>+12 dB</b></td>"
            "<td>4× of headroom before it oscillates. Comfortable.</td></tr>"
            "<tr><td>0.5</td><td>−6 dB</td>"
            "<td style='color:#3fb950'><b>+6 dB</b></td>"
            "<td>2× of headroom. The usual lower bound.</td></tr>"
            "<tr><td>1.0</td><td>0 dB</td><td style='color:#d29922'><b>0 dB</b>"
            "</td><td>Exactly on the edge — sustained oscillation.</td></tr>"
            "<tr><td>2.0</td><td>+6 dB</td>"
            "<td style='color:#f85149'><b>−6 dB</b></td>"
            "<td><b>Already unstable.</b> You are past the edge, not "
            "approaching it.</td></tr>"
            "</table>"))
        sg.add(body(
            "<b>So for the gain-margin number: positive = safe, negative = "
            "already unstable, and bigger positive = more room.</b> A negative "
            "gain margin is not a small margin; it is a statement that the "
            "nominal design does not work.", dim=True))
        self.add(sg)

        # ---- the two readings of one axis ---------------------------------
        self.add(hline())
        self.add(title("One dB axis, two completely different questions — the "
                       "mix-up worth killing now"))

        tw = Card("\"is positive dB good or bad?\" — wrong question, until you "
                  "say which reading")
        tw.add(body(
            "Having just been told that <i>negative</i> dB at ω<sub>pc</sub> is "
            "the safe case, it is very natural to conclude that negative dB is "
            "generally good — which collides head-on with the first-order "
            "frequency page, where the flat <b>positive</b> region was the good "
            "part (faithful tracking) and the rolloff into negative dB was the "
            "system falling behind.<br><br>"
            "<b>Both statements are correct.</b> They are answers to two "
            "different questions that happen to be asked of the same curve, on "
            "the same axis."))
        tw.add(body(
            "<table cellpadding='7'>"
            "<tr><td></td><td><b>The fidelity reading</b></td>"
            "<td><b>The stability reading</b></td></tr>"
            "<tr><td><b>Question</b></td>"
            "<td>Does the output faithfully follow the input at this "
            "frequency?</td>"
            "<td>Is the loop weak enough here to avoid sustaining its own "
            "oscillation?</td></tr>"
            "<tr><td><b>Asked of</b></td>"
            "<td>one block on its own — a plant, a sensor, a filter</td>"
            "<td>the <i>whole loop</i> L = controller × plant × sensor</td></tr>"
            "<tr><td><b>Asked where</b></td>"
            "<td><b>at every frequency</b> — the whole curve is the answer</td>"
            "<td><b>at exactly one frequency</b> — where the phase is "
            "−180°</td></tr>"
            "<tr><td><b>0 dB means</b></td>"
            "<td>output = input. Perfect tracking.</td>"
            "<td>the returning signal comes back exactly full-size. The edge of "
            "instability.</td></tr>"
            "<tr><td><b>Positive dB</b></td>"
            "<td><span style='color:#3fb950'>fine</span> — and normal at low "
            "frequency, where you <i>want</i> strong correction</td>"
            "<td><span style='color:#f85149'>fatal</span>, but only if it "
            "happens at ω<sub>pc</sub></td></tr>"
            "<tr><td><b>Negative dB</b></td>"
            "<td><span style='color:#d29922'>attenuated</span> — poor tracking, "
            "but perfectly stable; normal at high frequency</td>"
            "<td><span style='color:#3fb950'>safe</span> — this is what buys "
            "you gain margin</td></tr>"
            "</table>"))
        tw.add(callout(
            "<b>Every real loop's magnitude curve is positive at low frequency "
            "and negative at high frequency.</b> That shape is not a fault to "
            "be fixed — it is what a working design looks like. High gain down "
            "low is how you reject disturbances and kill steady-state error; "
            "rolloff up high is how you ignore noise and stay stable.<br><br>"
            "So do not scan the curve for its sign. <b>There is exactly one "
            "frequency where the sign carries a stability verdict, and you have "
            "to find it on the phase plot first.</b> Everywhere else, the sign "
            "is telling you about tracking, not about danger.", "key"))
        tw.add(body(
            "<b>And now the payoff, which is the nicest result on this "
            "page.</b> Those two readings are not merely compatible — the "
            "\"bad\" one causes the \"good\" one.<br><br>"
            "A plant's magnitude rolloff is poor tracking at high frequency. It "
            "is <i>also</i> exactly the thing that has already crushed the loop "
            "gain by the time the phase has crawled around to −180°. The "
            "attenuation that makes it a bad follower is what makes it a safe "
            "loop.<br><br>"
            "That is the mechanism behind the claim on the two previous pages "
            "that a plain first- or second-order plant cannot be destabilised "
            "by proportional feedback: <b>one pole runs out of phase at −90° "
            "and two only reach −180° asymptotically — and by then their own "
            "rolloff has taken the gain far below 1.</b> Phase and magnitude "
            "are racing, and for those plants magnitude always wins. "
            "Instability needs a third pole, a resonance, or a delay — "
            "something that supplies extra phase <i>without</i> the "
            "accompanying attenuation. A pure delay is the purest example: "
            "unlimited phase lag at <b>unity gain</b>, forever.", dim=True))
        self.add(tw)

        wh = Card("which of the three curves is on your screen — the 10-second "
                  "identification")
        wh.add(body(
            "The second-order page built this in full with all three plotted "
            "together; here is the operational version, because on this page you "
            "are about to read numbers off a curve and the numbers are only "
            "valid for one of them."))
        wh.add(body(
            "<table cellpadding='7'>"
            "<tr><td><b>Curve</b></td><td><b>Tell-tale</b></td>"
            "<td><b>Legitimate to read off it</b></td></tr>"
            "<tr><td><b>L</b> — loop gain, feedback cut<br>"
            "controller × plant × sensor</td>"
            "<td>starts <b>high</b> at low ω and falls monotonically; phase "
            "starts at <b>−90°</b> (integrator) or −180° (double integrator); "
            "usually <i>no</i> resonant bump</td>"
            "<td><b>GM, PM, ω<sub>gc</sub>, ω<sub>pc</sub></b>, the −1 point, "
            "everything on this page</td></tr>"
            "<tr><td><b>T</b> = L/(1+L) — closed loop</td>"
            "<td>starts flat at ≈ <b>0 dB</b>; bump if the closed-loop ζ &lt; "
            "0.707; rolls off past the bandwidth; phase starts at 0°</td>"
            "<td><b>overshoot, settling time, −3 dB bandwidth, tracking "
            "error</b></td></tr>"
            "<tr><td><b>P</b> — the raw plant, no loop</td>"
            "<td>starts flat at its own DC gain 1/k, which is whatever the "
            "hardware happens to be; resonant bump if the mechanism is "
            "underdamped; phase starts at 0°</td>"
            "<td><b>hardware resonances, Q, anti-resonances</b>, what "
            "frequencies the mechanism amplifies</td></tr>"
            "</table>"))
        wh.add(callout(
            "<b>P and T can look identical and mean completely different "
            "things.</b> A raw mass–spring–damper and a PD-controlled rigid "
            "joint both produce the canonical second-order curve — flat, bump, "
            "rolloff — because both have a complex pole pair. In the first the "
            "pair is a steel spring; in the second it is your K<sub>p</sub> and "
            "K<sub>d</sub>, and there is no spring in the machine at all.<br><br>"
            "So <b>the canonical form is not \"the closed-loop form\" and not "
            "\"the open-loop form\"</b> — it is the signature of a complex pole "
            "pair, and it turns up on both sides of the feedback wire. What "
            "never produces a bump is a chain of well-separated <i>real</i> "
            "poles, which is what a typical L is made of. That, and not the "
            "words open/closed, is the distinction that predicts the shape.",
            "key"))
        wh.add(body(
            "<b>One consequence worth stating, since it is the reason margins "
            "exist at all.</b> You cannot read a margin off T. T is the answer "
            "<i>after</i> the loop is closed — if it is unstable, T's step "
            "diverges and there is nothing left to measure a margin against. "
            "Margins are questions about how much the <i>uncut</i> loop could "
            "change before the closure goes bad, so they are necessarily "
            "properties of L. That is why every stability tool on this page and "
            "the next asks you to cut the wire first.", dim=True))
        self.add(wh)

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
        pm.add(callout(
            "<b>\"Phase margin is damping\" is not an analogy — it is a "
            "prediction, and this is what makes the frequency domain worth "
            "learning.</b><br><br>"
            "Follow the chain: you measure <b>45° of phase margin</b> on a "
            "swept sine. The table says that is <b>ζ ≈ 0.43</b>. The "
            "second-order page says overshoot is e<sup>−πζ/√(1−ζ²)</sup>, which "
            "at that ζ is <b>≈ 22%</b>. So you now know the robot will "
            "overshoot its step by about a fifth and ring a couple of visible "
            "cycles before settling.<br><br>"
            "<b>You have not run a step.</b> You never commanded a trajectory, "
            "never watched a transient, and you got the <i>shape</i> of the "
            "time response — how bouncy, how many wiggles, how far past — out "
            "of a single number read off a frequency plot.<br><br>"
            "Backwards works too, and is what you will actually do on hardware: "
            "the robot overshoots ~20%, so ζ ≈ 0.45, so the loop has roughly "
            "45° of phase margin, so there is not much room left — stop raising "
            "the gain.", "key"))
        self.add(pm)

        # ==================================================================
        # bandwidth -- the word that six different frequencies answer to
        # ==================================================================
        self.add(hline())
        self.add(title("\"Bandwidth\" — six different frequencies have now "
                       "been introduced, and only two of them are one"))

        zoo = Card("the six frequencies, what each one is a property of, and "
                   "where you read it")
        zoo.add(body(
            "By this point in the tutor ω has been subscripted six ways, and "
            "they are routinely swapped for each other in conversation. They "
            "are not interchangeable, and the fastest way to keep them "
            "straight is to notice that <b>each one is a property of a "
            "different object</b>: some describe a pole pair, some describe a "
            "loop, one describes a closed loop."))
        zoo.add(body(
            "<table cellpadding='6'>"
            "<tr><td><b>Symbol</b></td><td><b>What it is</b></td>"
            "<td><b>Property of</b></td><td><b>Read it off</b></td></tr>"

            "<tr><td><b>1/τ</b></td>"
            "<td>a first-order pole's rate. The <i>only</i> frequency a "
            "first-order system has.</td>"
            "<td>one real pole</td>"
            "<td>the corner of its own magnitude plot — and it is also its "
            "−3 dB point, exactly</td></tr>"

            "<tr><td><b>ω<sub>n</sub></b></td>"
            "<td>√(K/J). Pole radius; what it rings at undamped.</td>"
            "<td>a complex pole pair</td>"
            "<td>the −90° crossing on <i>that pair's</i> phase plot</td></tr>"

            "<tr><td><b>ω<sub>d</sub></b></td>"
            "<td>ω<sub>n</sub>√(1−ζ²). The pole's imaginary part.</td>"
            "<td>the same pole pair</td>"
            "<td>counting wiggles on a <b>step response</b></td></tr>"

            "<tr><td><b>ω<sub>r</sub></b></td>"
            "<td>ω<sub>n</sub>√(1−2ζ²). Where the magnitude actually peaks; "
            "gone above ζ = 0.707.</td>"
            "<td>the same pole pair</td>"
            "<td>the top of the bump on a <b>swept sine</b></td></tr>"

            "<tr><td><b>ω<sub>gc</sub></b></td>"
            "<td>where |L| = 1. <b>The crossover.</b></td>"
            "<td><b>L</b>, the loop gain</td>"
            "<td>the 0 dB crossing on the L magnitude plot</td></tr>"

            "<tr><td><b>ω<sub>pc</sub></b></td>"
            "<td>where ∠L = −180°. Where gain margin is measured.</td>"
            "<td><b>L</b>, the loop gain</td>"
            "<td>the −180° crossing on the L phase plot</td></tr>"

            "<tr><td><b>ω<sub>BW</sub></b></td>"
            "<td>where |T| has fallen 3 dB below its DC value. "
            "<b>The bandwidth.</b></td>"
            "<td><b>T</b>, the closed loop</td>"
            "<td>the −3 dB crossing on the T magnitude plot</td></tr>"
            "</table>"))
        zoo.add(callout(
            "<b>The one sentence that sorts them.</b> ω<sub>n</sub>, "
            "ω<sub>d</sub> and ω<sub>r</sub> are three readings of <b>one pole "
            "pair</b> and differ only by factors of √(1−ζ²) and √(1−2ζ²). "
            "ω<sub>gc</sub> and ω<sub>pc</sub> are two readings of <b>the "
            "uncut loop</b> and have nothing to do with a pole pair. "
            "ω<sub>BW</sub> is a reading of <b>the closed loop</b>.<br><br>"
            "So: pole-pair frequencies describe <i>what rings</i>, loop "
            "frequencies describe <i>how close to the edge you are</i>, and "
            "the bandwidth describes <i>how fast the finished machine "
            "is</i>.", "key"))
        self.add(zoo)

        tb = Card("converting a time constant into a bandwidth — the bridge "
                  "back to first order")
        tb.add(body(
            "The first-order pages gave you τ; everything from here on is "
            "specified in Hz. The conversion is not a convention, it is a "
            "derivation, and it is two lines. Take the first-order magnitude "
            "and ask where it has fallen to 1/√2 of its DC value — which is "
            "what \"−3 dB\" means, because 20 log<sub>10</sub>(1/√2) = "
            "−3.01:"))
        tb.add(math_label(r"|G(j\omega)| = \frac{1}{\sqrt{1+(\omega\tau)^2}} "
                          r"= \frac{1}{\sqrt2} \;\Longrightarrow\; "
                          r"(\omega\tau)^2 = 1 \;\Longrightarrow\; "
                          r"\boxed{\;\omega_{BW} = \frac{1}{\tau}, \qquad "
                          r"f_{BW} = \frac{1}{2\pi\tau}\;}", 17))
        tb.add(body(
            "<b>So the pole, the corner and the bandwidth are the same "
            "number.</b> For a first-order system there is nothing else to "
            "know. A 10 ms current loop is a 100 rad/s pole is a "
            "<b>15.9 Hz</b> bandwidth — three names for one fact.<br><br>"
            "<b>And why −3 dB and not some other level:</b> 1/√2 in amplitude "
            "is exactly <b>half</b> in power, since power goes as amplitude "
            "squared. The \"half-power point\" is the honest name; −3 dB is "
            "the same thing in the units people plot in."))
        tb.add(body(
            "<table cellpadding='7'>"
            "<tr><td><b>τ</b></td><td><b>ω<sub>BW</sub> = 1/τ</b></td>"
            "<td><b>f<sub>BW</sub></b></td>"
            "<td><b>t<sub>s</sub> (2%) = 4τ</b></td>"
            "<td><b>t<sub>r</sub> (10–90%) = 2.2τ</b></td></tr>"
            "<tr><td>10 ms</td><td>100 rad/s</td><td>15.9 Hz</td>"
            "<td>40 ms</td><td>22 ms</td></tr>"
            "<tr><td>50 ms</td><td>20 rad/s</td><td>3.2 Hz</td>"
            "<td>200 ms</td><td>110 ms</td></tr>"
            "<tr><td>200 ms</td><td>5 rad/s</td><td>0.80 Hz</td>"
            "<td>800 ms</td><td>440 ms</td></tr>"
            "</table>"))
        tb.add(callout(
            "<b>Multiply the last two columns of any row and you get the same "
            "number: t<sub>r</sub> × f<sub>BW</sub> ≈ 0.35.</b><br><br>"
            "That is the rise-time–bandwidth product, and it is exact for a "
            "first-order system by construction: 2.2τ × 1/(2πτ) = 2.2/6.283 = "
            "0.350, with the τ cancelling. It is the most useful sanity check "
            "in this whole area — a datasheet claiming a 1 kHz bandwidth is "
            "claiming a <b>0.35 ms</b> rise time, and if the scope shows 3 ms "
            "then one of you is wrong.<br><br>"
            "It generalises approximately to second order as well (0.35–0.45 "
            "over the usual damping range), which is why the rule survives "
            "contact with real hardware.", "key"))
        tb.add(body(
            "<b>The second-order version is not 1/τ, because there is no "
            "τ.</b> Solve the same |T| = 1/√2 condition on the canonical form "
            "and you get a less pretty closed form:"))
        tb.add(math_label(r"\omega_{BW} = \omega_n\sqrt{\,1 - 2\zeta^2 "
                          r"+ \sqrt{2 - 4\zeta^2 + 4\zeta^4}\,}", 16))
        tb.add(body(
            "<b>Worth knowing three values of it and no more:</b> at "
            "ζ = 0.4 it is 1.37 ω<sub>n</sub>; at <b>ζ = 0.707 it is "
            "1.000 ω<sub>n</sub></b>; at ζ = 1 it is 0.64 ω<sub>n</sub>. "
            "The middle one is the fourth good property of 0.707 — the "
            "bandwidth you get is the ω<sub>n</sub> you designed for, to four "
            "figures. Away from it you are always within a factor of about "
            "1.5 either way, which is why people say \"bandwidth ≈ "
            "ω<sub>n</sub>\" and get away with it.", dim=True))
        self.add(tb)

        ol = Card("open-loop \"bandwidth\" is the crossover; closed-loop "
                  "bandwidth is the −3 dB point")
        ol.add(body(
            "This is the question the vocabulary above was built to answer, "
            "and the two halves have genuinely different definitions — but "
            "they land within a factor of two of each other, which is why the "
            "sloppiness usually survives."))
        ol.add(body(
            "<b>Open loop: the bandwidth is ω<sub>gc</sub>, the crossover.</b> "
            "And that is a <i>derived</i> choice, not a naming convention. "
            "Below crossover |L| > 1, so the error-rejection factor 1/(1+L) is "
            "small and the loop is genuinely in charge — disturbances get "
            "squashed and commands get followed. Above crossover |L| < 1, "
            "1/(1+L) ≈ 1, and the loop is a spectator: whatever the world does "
            "to the plant simply happens."))
        ol.add(math_label(r"\frac{E}{R} = \frac{1}{1+L(j\omega)} \approx "
                          r"\begin{cases} 1/L & |L| \gg 1 "
                          r"\;\;(\omega \ll \omega_{gc}) \\ "
                          r"1 & |L| \ll 1 \;\;(\omega \gg \omega_{gc}) "
                          r"\end{cases}", 16))
        ol.add(body(
            "<b>ω<sub>gc</sub> is therefore the frequency at which authority "
            "runs out</b>, and calling it the bandwidth is a statement about "
            "control authority, not about tracking fidelity."))
        ol.add(body(
            "<b>Closed loop: the bandwidth is where |T| drops 3 dB below its "
            "DC value.</b> Same definition as any filter, because T <i>is</i> "
            "a filter — reference in, motion out. Note \"below its DC value\", "
            "not \"below 0 dB\": a loop with steady-state droop starts under "
            "0 dB and you measure the 3 dB from wherever it started."))
        ol.add(callout(
            "<b>And the bridge between them, which is the number to "
            "remember.</b> For the standard loop the closed-loop bandwidth "
            "lands consistently just above the crossover:<br><br>"
            "&nbsp;&nbsp;ζ = 0.2 → ω<sub>BW</sub> = 1.57 ω<sub>gc</sub><br>"
            "&nbsp;&nbsp;ζ = 0.4 → 1.61 ω<sub>gc</sub><br>"
            "&nbsp;&nbsp;ζ = 0.707 → 1.55 ω<sub>gc</sub><br>"
            "&nbsp;&nbsp;ζ = 1.0 → 1.32 ω<sub>gc</sub><br><br>"
            "<b>So ω<sub>gc</sub> ≤ ω<sub>BW</sub> ≤ 2 ω<sub>gc</sub>, and "
            "≈ 1.5× is the working estimate.</b> That is why the two usages "
            "of \"bandwidth\" rarely cause an argument — and also why you "
            "should say which one you mean when a factor of 1.5 matters, "
            "which on a spec sheet it does.<br><br>"
            "The physical reason they track each other: raising the loop gain "
            "pushes ω<sub>gc</sub> right, which drags the closed-loop poles "
            "outward, which moves ω<sub>BW</sub> right by the same rough "
            "factor. One knob, both numbers.", "good"))
        self.add(ol)

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

        # ==================================================================
        # experiment 2, done properly -- the SEA ceiling as an inequality
        # ==================================================================
        self.add(hline())
        self.add(title("Experiment 2 in full: why a spring in the drivetrain "
                       "puts a hard ceiling on bandwidth"))

        se = Card("what the resonance does to L — two effects, and only one "
                  "of them is the phase")
        se.add(body(
            "Turning that resonance slider on multiplies the loop gain by one "
            "extra factor — the canonical second-order form, with its own "
            "ω<sub>res</sub> and its own, very small, ζ<sub>r</sub>:"))
        se.add(math_label(r"L(s) = \underbrace{C(s)\,P_{rigid}(s)}"
                          r"_{\text{what you designed}}\;\cdot\;"
                          r"\underbrace{\frac{\omega_{res}^2}"
                          r"{s^2 + 2\zeta_r\omega_{res}s + \omega_{res}^2}}"
                          r"_{\text{the spring, uninvited}}", 16))
        se.add(body(
            "Below ω<sub>res</sub> that factor is ≈ 1 in magnitude and ≈ 0° "
            "in phase: <b>the spring is invisible, and everything you "
            "designed for a rigid joint is still true.</b> That is exactly "
            "why the ceiling is a ceiling rather than a general penalty — "
            "under it you pay nothing at all.<br><br>"
            "At and above ω<sub>res</sub> it does two things at once, and "
            "they compound:"))
        se.add(body(
            "&nbsp;&nbsp;<b>1 · It adds 180° of phase lag</b>, all of it "
            "inside about one octave around ω<sub>res</sub>, because "
            "ζ<sub>r</sub> is small and the transition is therefore sharp. "
            "The rigid loop was already sitting near −90° from its "
            "integrator, so the total sails through <b>−180°</b> right about "
            "there. <b>That is where ω<sub>pc</sub> now lives</b>, and before "
            "the spring existed there was no ω<sub>pc</sub> at all — gain "
            "margin was infinite.<br>"
            "&nbsp;&nbsp;<b>2 · It multiplies the magnitude by Q = "
            "1/(2ζ<sub>r</sub>)</b> at that same frequency. A steel flexure "
            "at ζ<sub>r</sub> = 0.05 is a <b>×10</b> amplifier, precisely "
            "where the phase has just handed you −180°.", dim=True))
        se.add(callout(
            "<b>Both effects land at the same frequency, and that "
            "coincidence is the entire problem.</b><br><br>"
            "The card earlier on this page explained that a plain plant is "
            "safe because phase and magnitude race each other: by the time "
            "the phase reaches −180° the rolloff has already crushed the "
            "gain. A lightly damped resonance breaks that race in the worst "
            "possible way — it supplies the phase <b>and simultaneously "
            "boosts the gain</b>. It is the same structural problem as a pure "
            "delay, except a delay only refuses to attenuate, whereas a "
            "resonance actively amplifies.", "warn"))
        self.add(se)

        ce = Card("the ceiling, as an inequality you can evaluate before "
                  "building anything")
        ce.add(body(
            "Put the two effects together and gain margin falls out. Gain "
            "margin is measured at ω<sub>pc</sub>, which we have just "
            "established is ≈ ω<sub>res</sub>, and the loop gain there is the "
            "rigid design's gain multiplied by Q:"))
        ce.add(math_label(r"|L(j\omega_{res})| \;\approx\; Q\cdot"
                          r"|L_{rigid}(j\omega_{res})| "
                          r"\qquad\Longrightarrow\qquad "
                          r"GM \;\approx\; -20\log_{10}\!\left("
                          r"Q\,|L_{rigid}(j\omega_{res})|\right)\ \text{dB}",
                          16))
        ce.add(body(
            "<b>That estimate is worth trusting.</b> Evaluated against the "
            "exact margin of the widget's own plant it comes out within "
            "1–3 dB across resonances from 15 Hz to 100 Hz and gains spanning "
            "a factor of 13, and it errs on the pessimistic side. Two "
            "quantities, both known before anything is built.", dim=True))
        ce.add(body(
            "<b>Now turn it into a bandwidth limit.</b> Above crossover a "
            "typical loop rolls off at about −20 dB/decade, so its magnitude "
            "out at the resonance is roughly ω<sub>gc</sub>/ω<sub>res</sub>. "
            "Substitute, demand a gain margin of at least a factor g (g = 2 "
            "is 6 dB), and solve for the crossover:"))
        ce.add(math_label(r"Q\,\frac{\omega_{gc}}{\omega_{res}} \leq "
                          r"\frac{1}{g} \qquad\Longrightarrow\qquad "
                          r"\boxed{\;\omega_{gc} \;\leq\; "
                          r"\frac{\omega_{res}}{g\,Q} "
                          r"\;=\; \frac{2\zeta_r}{g}\,\omega_{res}\;}", 17))
        ce.add(callout(
            "<b>Read that inequality, because it is the SEA design rule and "
            "it is brutal.</b><br><br>"
            "The achievable bandwidth is <b>not</b> the resonant frequency. "
            "It is the resonant frequency multiplied by <b>2ζ<sub>r</sub></b> "
            "— the damping of a spring nobody designed to be damped — and "
            "then divided by your margin requirement.<br><br>"
            "A 15 Hz SEA spring at ζ<sub>r</sub> = 0.05 with a 6 dB gain "
            "margin gives ω<sub>gc</sub> ≤ 15 × 0.10 / 2 = <b>0.75 Hz</b>. "
            "Not 15 Hz. Not 5 Hz. <b>Under one hertz</b>, from a mechanism "
            "whose resonance is at fifteen.", "warn"))
        ce.add(body(
            "<b>Which is why real SEAs do not live with that number, and "
            "what they do instead.</b> Every term in the inequality is a "
            "lever, and the fix is always one of exactly three things:<br><br>"
            "&nbsp;&nbsp;<b>• Raise ζ<sub>r</sub>.</b> The bound is "
            "<i>linear</i> in it, so this is the highest-value fix available: "
            "damping the spring from 0.05 to 0.25 buys a 5× bandwidth. Do it "
            "physically if you can, or with an inner torque loop, which is "
            "the whole reason an SEA has a torque sensor and a cascade "
            "structure in the first place.<br>"
            "&nbsp;&nbsp;<b>• Raise ω<sub>res</sub>.</b> A stiffer spring — "
            "but stiffness was the thing you fitted a spring to give up, so "
            "this trades away force fidelity, shock tolerance and "
            "backdriveability. <b>This is the SEA trade, stated as one "
            "inequality</b>, and it is the same sentence the SEA page makes "
            "with hardware.<br>"
            "&nbsp;&nbsp;<b>• Notch it.</b> Put a filter zero on the "
            "resonance so the loop never sees the Q. It works, and it is "
            "fragile: a notch is tuned to a frequency that moves with "
            "payload, temperature and wear, and a mistuned notch is worse "
            "than none. The Lead/Lag page spends a full card on why.",
            dim=True))
        self.add(ce)

        cmp_ = Card("SEA versus direct drive, in the terms of that "
                    "inequality")
        cmp_.add(body(
            "The comparison people want is \"how much bandwidth does a series "
            "spring cost me\", and the inequality answers it by saying <b>the "
            "two architectures are limited by entirely different "
            "things</b>."))
        cmp_.add(body(
            "<table cellpadding='7'>"
            "<tr><td></td><td><b>Direct drive / rigid</b></td>"
            "<td><b>Series elastic</b></td></tr>"

            "<tr><td><b>What caps ω<sub>gc</sub></b></td>"
            "<td>sampling rate, loop delay, motor electrical pole, "
            "sensor noise — <b>all implementation</b></td>"
            "<td>2ζ<sub>r</sub>ω<sub>res</sub>/g — <b>a mechanical "
            "property you bolted in on purpose</b></td></tr>"

            "<tr><td><b>Gain margin with a P controller</b></td>"
            "<td><b>infinite</b> — the widget shows GM = ∞ at every "
            "K<sub>p</sub> with the resonance off</td>"
            "<td><b>finite, and it can start out negative.</b> With the "
            "widget's 15 Hz spring and K<sub>d</sub> = 4 it is already "
            "−4 dB at K<sub>p</sub> = 10, before you have tuned "
            "anything</td></tr>"

            "<tr><td><b>Which margin dies first</b></td>"
            "<td>phase margin, gradually, as you raise the gain</td>"
            "<td>gain margin, and it was already gone</td></tr>"

            "<tr><td><b>Typical ceiling</b></td>"
            "<td>tens of Hz to a few hundred — set by the 1 kHz loop rate "
            "and its delay, from page 1</td>"
            "<td>a few Hz, unless ζ<sub>r</sub> is engineered up or the "
            "spring is stiffened</td></tr>"

            "<tr><td><b>What you bought for it</b></td>"
            "<td>bandwidth, and transparency only if the gearbox is "
            "small</td>"
            "<td>shock tolerance, honest force sensing from spring "
            "deflection, and safety on impact</td></tr>"
            "</table>"))
        cmp_.add(callout(
            "<b>The honest summary: an SEA trades bandwidth for force "
            "fidelity, and the exchange rate is 2ζ<sub>r</sub>.</b><br><br>"
            "That is not a criticism of series elasticity — it is the reason "
            "to choose it. A leg that must survive heel strike wants the "
            "spring, and does not need 100 Hz of position bandwidth to walk. "
            "An arm doing precise insertion wants the bandwidth and can avoid "
            "the impacts.<br><br>"
            "What is <i>not</i> acceptable is choosing series elasticity and "
            "then being surprised by the ceiling. The inequality is "
            "evaluable at the CAD stage: you know ω<sub>res</sub> from the "
            "spring rate and the load inertia, you can measure ζ<sub>r</sub> "
            "with one ring-down test, and the bandwidth you are allowed "
            "follows. The actuator pages later on spend this result on "
            "specific joints of both robots.", "key"))
        cmp_.add(body(
            "<b>To watch all of this happen in the widget above:</b> set the "
            "resonance to 0 (rigid) and K<sub>d</sub> = 4, then raise "
            "K<sub>p</sub> from 10 to 1600 — crossover climbs from 2.6 Hz to "
            "12.7 Hz, phase margin bleeds from 85° to 1°, and <b>gain margin "
            "reads ∞ the entire way</b>. Now set the resonance to 15 Hz and "
            "repeat: gain margin is <b>−4.3 dB at the very first step</b>, "
            "and ω<sub>pc</sub> has appeared at 14.8 Hz — sitting right on "
            "the spring. Move the resonance out to 50 Hz and gain margin "
            "returns to about +9 dB, which is the inequality's "
            "ω<sub>res</sub> term doing its work.", dim=True))
        self.add(cmp_)

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
