"""
Nonlinear systems -- the two pages that say what the previous nine were
quietly assuming, and what to do when it stops being true.

  1  Nonlinear Systems   what superposition was buying you, what you lose when
                         it goes, and the phenomena you get instead
  2  Nonlinear Control   the six things people actually do, in the order you
                         should try them

The honest framing, and it is worth stating before any of it: a robot is not
"nonlinear" in some abstract sense. It is nonlinear in six specific, nameable
places, and the whole practical art is knowing which one is biting you.
"""

from __future__ import annotations

import math

from PySide6.QtWidgets import QComboBox, QLabel

from ctrlcore.nonlinear import (
    Pendulum,
    computed_torque,
    energy_swingup,
    gain_scheduled_pd,
    gravity_comp_pd,
    large_angle_period,
    pd_controller,
    phase_field,
    run_stick_slip,
    separatrix,
    sliding_mode,
    trajectory,
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

SECTION = "Nonlinear"


# ==========================================================================
# PAGE -- what breaks
# ==========================================================================

class NonlinearSystemsPage(Page):
    TITLE = "Nonlinear Systems"
    SUBTITLE = ("Everything so far rested on superposition. Here is what it "
                "was buying you, where a robot violates it, and the behaviour "
                "you get instead.")
    SECTION = SECTION
    NOTES = "foundation"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>One property held the last nine pages together.</b><br><br>"
            "&nbsp;&nbsp;&nbsp;&nbsp;<b>Superposition</b> — double the input and "
            "the output doubles; add two inputs and the outputs add.<br><br>"
            "A transfer function exists only because of it. So does a pole, a "
            "Bode plot, a phase margin, a root locus and \"<i>the</i> step "
            "response\". Lose superposition and you lose <b>all of them at "
            "once</b> — not their accuracy, their <i>existence</i>.", "key"))

        l = Card("what you lose, precisely")
        l.add(body(
            "<table cellpadding='6'>"
            "<tr><td><b>Gone</b></td><td><b>Because</b></td></tr>"
            "<tr><td>Transfer function, poles, zeros</td>"
            "<td>Laplace transforms need linearity. There is nothing to "
            "factor.</td></tr>"
            "<tr><td>Bode plot, phase margin</td>"
            "<td>A sine in no longer gives a sine out — it gives a sine plus "
            "harmonics, so \"the gain at ω\" is not defined.</td></tr>"
            "<tr><td>\"The\" step response</td>"
            "<td>Response depends on <b>amplitude</b>. A 1° step and a 90° step "
            "are different experiments on the same robot.</td></tr>"
            "<tr><td>Global stability</td>"
            "<td>Stability becomes <b>local</b>: stable near here, and there is "
            "a boundary. Linear systems have no boundary.</td></tr>"
            "<tr><td>One equilibrium</td>"
            "<td>There can be several, with different characters, and the "
            "system chooses based on where it started.</td></tr>"
            "</table>"))
        self.add(l)

        n = Card("where a robot actually breaks it — the inventory")
        n.add(body(
            "<table cellpadding='6'>"
            "<tr><td><b>g(q) ~ sin q</b></td><td>gravity</td>"
            "<td>Torque needed depends on <b>posture</b>. Maximum when the link "
            "is horizontal, zero at both ends of the swing.</td></tr>"
            "<tr><td><b>C(q,q̇)q̇</b></td><td>Coriolis / centrifugal</td>"
            "<td><b>Quadratic in velocity.</b> Negligible when slow, dominant "
            "when fast — which is why a robot tuned at 10% speed misbehaves at "
            "full speed.</td></tr>"
            "<tr><td><b>M(q)</b></td><td>inertia matrix</td>"
            "<td>The <i>mass itself moves</i> as the arm folds. An extended arm "
            "and a tucked arm are different plants.</td></tr>"
            "<tr><td><b>stiction / Coulomb</b></td><td>friction</td>"
            "<td><b>Discontinuous at zero velocity.</b> Not merely nonlinear — "
            "not differentiable, so linearisation is undefined there.</td></tr>"
            "<tr><td><b>saturation</b></td><td>actuator limit</td>"
            "<td>The effective gain falls when you ask for too much. Loops "
            "change character under load.</td></tr>"
            "<tr><td><b>backlash, hysteresis</b></td><td>transmission</td>"
            "<td>Output depends on the <b>history</b>, not just the input. Not "
            "even a function of the current state.</td></tr>"
            "</table>"))
        n.add(body(
            "Note the practical hierarchy. Gravity is smooth and modellable — "
            "feedforward it. Coriolis is smooth and modellable — feedforward it "
            "too. <b>Friction and backlash are the hard ones</b>, because they "
            "are discontinuous and history-dependent, and they are also the "
            "ones a gearbox gives you most of.", dim=True))
        self.add(n)

        # ---- the pendulum ------------------------------------------------
        self.add(hline())
        self.add(title("The smallest complete example: two equilibria, one "
                       "system"))

        p = Card("same equation, opposite conclusions")
        p.add(math_label(r"J\ddot\theta + b\dot\theta + mgl\sin\theta = \tau",
                         17))
        p.add(body(
            "The <b>sin θ</b> is the entire nonlinearity, and it does something "
            "no linear term can: it gives the system <b>two equilibria</b> — "
            "hanging (θ = 0) and inverted (θ = π). Linearise about each — write "
            "θ = θ₀ + δ and keep the first term of sin — and the whole "
            "nonlinearity collapses into a single coefficient:"))
        p.add(math_label(r"J\,\ddot\delta + b\,\dot\delta "
                         r"+ \left(mgl\cos\theta_0\right)\delta = \tau", 17))
        p.add(body(
            "That bracket is the <b>stiffness</b> of the linearised system — the "
            "A<sub>21</sub> entry of the state matrix — and everything depends "
            "on its <b>sign</b>:"))
        p.add(body(
            "&nbsp;&nbsp;• <b>θ₀ = 0</b> (hanging): cos = +1, so the stiffness is "
            "<b>+mgl</b> — a genuine restoring spring → a stable complex pair. A "
            "damped oscillator.<br>"
            "&nbsp;&nbsp;• <b>θ₀ = π/2</b> (horizontal): cos = 0, so the "
            "stiffness is <b>zero</b> → a double integrator. Nothing restores "
            "it at all.<br>"
            "&nbsp;&nbsp;• <b>θ₀ = π</b> (inverted): cos = −1, so the stiffness "
            "is <b>−mgl</b> — a spring pushing the wrong way → <b>a real pole in "
            "the right half plane</b>. It falls."))
        p.add(body(
            "Three completely different linear systems, from one nonlinear "
            "equation, depending only on where you stood when you "
            "linearised. That is what \"linearisation is local\" means "
            "operationally, and it is why a controller tuned on the bench with "
            "the arm hanging can be actively wrong with the arm raised.",
            dim=True))
        self.add(p)

        # ---- interactive 1 ------------------------------------------------
        i = Card("slide the operating point and watch the poles cross over")
        i.add(body(
            "One pendulum. The only thing changing is <i>where you linearise</i>. "
            "Watch the pole pair walk out of the stable half plane as the "
            "operating point approaches upright.", dim=True))
        self.s_th0 = slider(0, 180, 0)           # degrees
        self.s_damp = slider(0, 100, 15)         # x0.01
        self.l_th0, self.l_damp = QLabel(), QLabel()
        i.add_layout(slider_row("operating point θ₀ (°)", self.s_th0,
                                self.l_th0))
        i.add_layout(slider_row("damping b (×0.01)", self.s_damp, self.l_damp))
        self.st_corner = Stat("−mgl·cos θ₀ / J", "--", theme.VIOLET)
        self.st_pol = Stat("worst pole", "--", theme.ACCENT)
        self.st_ver = Stat("locally", "--", theme.GOOD)
        self.st_dbl = Stat("doubling time", "--", theme.BAD)
        i.add_layout(stat_row(self.st_corner, self.st_pol, self.st_ver,
                              self.st_dbl))
        self.c1 = MplCanvas(width=7.4, height=3.0, ncols=2)
        i.add(self.c1)
        self.add(i)
        for s in (self.s_th0, self.s_damp):
            s.valueChanged.connect(self._redraw_lin)
        self._redraw_lin()

        # ---- phase portrait ------------------------------------------------
        self.add(hline())
        self.add(title("The right picture for a nonlinear system"))

        ph = Card("why a phase portrait, not a step response")
        ph.add(body(
            "A linear system has one behaviour, scaled. A nonlinear one has a "
            "different behaviour from every starting point, so no single "
            "response characterises it. The <b>phase plane</b> — θ against θ̇ — "
            "shows every initial condition at once, and the features that "
            "matter become <i>shapes</i>:<br><br>"
            "&nbsp;&nbsp;• <b>equilibria</b>: points where the arrows vanish. "
            "Centres (hanging) and saddles (inverted).<br>"
            "&nbsp;&nbsp;• <b>the separatrix</b>: the contour through the "
            "inverted equilibrium. Inside it the pendulum swings back and "
            "forth; outside it goes over the top and rotates. It is the "
            "<b>boundary of the basin of attraction</b>.<br>"
            "&nbsp;&nbsp;• <b>limit cycles</b>: closed loops that nearby "
            "trajectories spiral onto."))
        ph.add(callout(
            "<b>That boundary is the thing linear theory cannot express.</b> A "
            "stable linear system is stable from <i>every</i> initial condition — "
            "its basin is the whole state space, always. So when a linear "
            "analysis says \"stable\", it has said nothing about how big a push "
            "your robot can take.<br><br>"
            "For a real machine that question is the important one. \"Stable "
            "for deviations under 15° and disturbances under 20 N·m\" is an "
            "engineering statement. \"Stable\" on its own, for a nonlinear "
            "system, is not.", "key"))
        self.add(ph)

        i2 = Card("the phase plane, with a trajectory you choose")
        i2.add(body(
            "Grey arrows are the flow. The orange curve is the separatrix of "
            "the undamped pendulum. Start inside it and you swing; start "
            "outside and you go over the top.", dim=True))
        self.s_th_i = slider(-180, 180, 150)
        self.s_w_i = slider(-100, 100, 0)        # x0.1 rad/s
        self.s_b2 = slider(0, 100, 15)           # x0.01
        self.l_th_i, self.l_w_i, self.l_b2 = QLabel(), QLabel(), QLabel()
        i2.add_layout(slider_row("start θ (°)", self.s_th_i, self.l_th_i))
        i2.add_layout(slider_row("start θ̇ (×0.1)", self.s_w_i, self.l_w_i))
        i2.add_layout(slider_row("damping b (×0.01)", self.s_b2, self.l_b2))
        self.st_e0 = Stat("start energy", "--", theme.ACCENT)
        self.st_esep = Stat("energy to go over", "--", theme.WARN)
        self.st_fate = Stat("outcome", "--", theme.GOOD)
        self.st_per = Stat("period vs small-angle", "--", theme.VIOLET)
        i2.add_layout(stat_row(self.st_e0, self.st_esep, self.st_fate,
                               self.st_per))
        self.c2 = MplCanvas(width=7.4, height=3.2)
        i2.add(self.c2)
        self.add(i2)
        for s in (self.s_th_i, self.s_w_i, self.s_b2):
            s.valueChanged.connect(self._redraw_phase)
        self._redraw_phase()

        # ---- limit cycles ---------------------------------------------------
        self.add(hline())
        self.add(title("Limit cycles — the behaviour a linear system cannot "
                       "have"))

        lc = Card("stiction, and the two ways it ruins a position loop")
        lc.add(body(
            "A linear oscillation does one of three things: decay, grow, or sit "
            "exactly on the boundary. None of those is <b>amplitude-locked</b>. "
            "A limit cycle is a closed trajectory that nearby motions converge "
            "<i>onto</i> — self-sustaining, isolated, and independent of where "
            "you started. Only a nonlinearity can produce one, and in a robot "
            "the usual culprit is stiction."))
        lc.add(body(
            "<b>Without integral action</b> the joint sticks wherever the "
            "proportional torque first drops below breakaway and stays there — "
            "a permanent dead zone of width f<sub>static</sub>/K<sub>p</sub> "
            "around the setpoint. Not a limit cycle, and arguably worse, "
            "because nothing about it looks like a fault.<br><br>"
            "<b>With integral action</b> the error cannot be tolerated, so: the "
            "integrator climbs until it breaks the joint free → friction drops "
            "instantly from f<sub>static</sub> to f<sub>coulomb</sub> → the "
            "surplus torque makes it lurch and overshoot → it sticks on the "
            "other side → repeat. <b>Hunting</b>, forever."))
        lc.add(body(
            "<b>And you cannot tune it away.</b> Lower the gain and it hunts "
            "more slowly; raise it and it hunts harder. The real fixes are "
            "mechanical (better bearings, preload, lower ratio) or feedforward "
            "(a friction model, a dither signal) — which is the same conclusion "
            "the gearing pages reached from the other direction.", dim=True))
        self.add(lc)

        i3 = Card("watch it hunt")
        i3.add(body(
            "Set K<sub>i</sub> = 0 to see the dead zone; raise it to see the "
            "limit cycle. The shaded bands are the intervals when the joint is "
            "stuck.", dim=True))
        self.s_ki = slider(0, 120, 60)
        self.s_fs = slider(0, 120, 60)           # x0.1
        self.s_fc = slider(0, 120, 25)           # x0.1
        self.l_ki, self.l_fs, self.l_fc = QLabel(), QLabel(), QLabel()
        i3.add_layout(slider_row("K_i", self.s_ki, self.l_ki))
        i3.add_layout(slider_row("breakaway f_s (×0.1)", self.s_fs, self.l_fs))
        i3.add_layout(slider_row("sliding f_c (×0.1)", self.s_fc, self.l_fc))
        self.st_amp = Stat("hunt amplitude", "--", theme.BAD)
        self.st_stuck = Stat("time stuck", "--", theme.WARN)
        self.st_dead = Stat("dead zone f_s/K_p", "--", theme.VIOLET)
        self.st_final = Stat("final error", "--", theme.ACCENT)
        i3.add_layout(stat_row(self.st_amp, self.st_stuck, self.st_dead,
                               self.st_final))
        self.c3 = MplCanvas(width=7.4, height=3.2, nrows=2)
        i3.add(self.c3)
        self.add(i3)
        for s in (self.s_ki, self.s_fs, self.s_fc):
            s.valueChanged.connect(self._redraw_slip)
        self._redraw_slip()

        d = Card("saturation, and getting a number out of it anyway")
        d.add(body(
            "The <b>describing function</b> is the standard trick for putting a "
            "nonlinearity back into linear machinery: pretend it is a gain that "
            "depends on <b>amplitude</b>, then reuse Nyquist. For a saturation "
            "driven by a sine of amplitude A against a limit M:"))
        d.add(math_label(r"N(A) = \frac{2}{\pi}\left(\arcsin k "
                         r"+ k\sqrt{1-k^2}\right), \qquad k = M/A \leq 1", 16))
        d.add(body(
            "N(A) = 1 while you stay inside the limit and falls steadily "
            "afterwards — <b>the effective gain drops as the amplitude "
            "grows</b>. A = 2M gives N ≈ 0.61; A = 5M gives N ≈ 0.25.<br><br>"
            "Two consequences that bite in practice. First, a loop that is "
            "well-damped for small motions can be sluggish or hunt when driven "
            "hard, with no parameter having changed. Second — and this is the "
            "dangerous one — a <b>conditionally stable</b> loop (the "
            "Nyquist page) is unstable at <i>reduced</i> gain, and saturation "
            "reduces gain. Such a robot destabilises itself precisely when it "
            "is pushed hardest.", dim=True))
        self.add(d)

        self.add(callout(
            "<b>Carry forward.</b> Nonlinearity costs you every frequency-domain "
            "tool and replaces them with amplitude dependence, multiple "
            "equilibria, basins with boundaries, and limit cycles. The next "
            "page is the toolbox: six approaches, and the first two are just "
            "\"pretend it is linear, carefully\".", "good"))

        self.finish()

    # ------------------------------------------------------------------
    def _redraw_lin(self):
        th0 = math.radians(self.s_th0.value())
        b = self.s_damp.value() / 100.0
        self.l_th0.setText(f"{self.s_th0.value()}°")
        self.l_damp.setText(f"{b:.2f}")

        pend = Pendulum(m=1.0, l=0.5, b=b)
        A, _ = pend.linearise(th0)
        poles = pend.linear_poles(th0)
        worst = max(poles, key=lambda p: p.real)
        self.st_corner.set(f"{A[1,0]:+.1f}")
        self.st_pol.set(f"{worst.real:+.2f}")
        if worst.real < -1e-6:
            v, col = "stable", theme.GOOD
        elif worst.real > 1e-6:
            v, col = "UNSTABLE", theme.BAD
        else:
            v, col = "marginal", theme.WARN
        self.st_ver.set(v)
        self.st_ver.set_color(col)
        self.st_dbl.set("—" if worst.real <= 1e-6
                        else f"{math.log(2)/worst.real*1000:.0f} ms")

        c = self.c1
        c.clear()
        a1, a2 = c.axes
        # gravity torque curve, with the operating point marked
        ths = [i * math.pi / 90 for i in range(181)]
        a1.plot([math.degrees(t) for t in ths],
                [pend.gravity_torque(t) for t in ths], color=theme.WARN, lw=2.0,
                label="mgl·sin θ")
        a1.plot([math.degrees(t) for t in ths],
                [pend.m * pend.g * pend.l * t for t in ths],
                color=theme.TEXT_FAINT, lw=1.2, ls="--",
                label="the linear approximation at θ=0")
        a1.scatter([math.degrees(th0)], [pend.gravity_torque(th0)], s=70,
                   color=theme.ACCENT, zorder=6)
        a1.set_ylim(-1, pend.m * pend.g * pend.l * 3.4)
        a1.set_xlabel("θ (°)")
        a1.set_ylabel("gravity torque (N·m)")
        c.legend(a1, loc="upper left")
        _splane(a2, poles, lim=8.0)
        a2.set_title(f"linearised at θ₀ = {self.s_th0.value()}°", fontsize=9)
        c.refresh()

    def _redraw_phase(self):
        th0 = math.radians(self.s_th_i.value())
        w0 = self.s_w_i.value() / 10.0
        b = self.s_b2.value() / 100.0
        self.l_th_i.setText(f"{self.s_th_i.value()}°")
        self.l_w_i.setText(f"{w0:+.1f} rad/s")
        self.l_b2.setText(f"{b:.2f}")

        pend = Pendulum(m=1.0, l=0.5, b=b)
        e0 = pend.energy(th0, w0)
        e_sep = 2.0 * pend.m * pend.g * pend.l
        self.st_e0.set(f"{e0:.2f} J")
        self.st_esep.set(f"{e_sep:.2f} J")
        self.st_fate.set("goes over the top" if e0 > e_sep else "swings back")
        self.st_fate.set_color(theme.BAD if e0 > e_sep else theme.GOOD)
        amp = min(abs(th0), math.pi * 0.98)
        ratio = large_angle_period(pend, amp) / large_angle_period(pend, 1e-4)
        self.st_per.set(f"{ratio:.2f}×")

        ts, th, w, _ = trajectory(pend, th0, w0, duration=14.0, dt=4e-3)

        c = self.c2
        c.clear()
        ax = c.ax
        fld = phase_field(pend, th_range=(-math.pi, math.pi), n_th=17, n_w=11,
                          w_range=(-9, 9))
        ax.quiver([f[0] for f in fld], [f[1] for f in fld],
                  [f[2] for f in fld], [f[3] for f in fld],
                  color=theme.TEXT_FAINT, alpha=0.5, width=0.0022, scale=180)
        sths, up, dn = separatrix(pend)
        keep = [i for i, t in enumerate(sths) if -math.pi <= t <= math.pi]
        ax.plot([sths[i] for i in keep], [up[i] for i in keep],
                color=theme.WARN, lw=1.5, ls="--", label="separatrix")
        ax.plot([sths[i] for i in keep], [dn[i] for i in keep],
                color=theme.WARN, lw=1.5, ls="--")
        wrapped = [math.atan2(math.sin(x), math.cos(x)) for x in th]
        seg_t, seg_w = [], []
        for k in range(len(wrapped)):
            if seg_t and abs(wrapped[k] - seg_t[-1]) > math.pi:
                ax.plot(seg_t, seg_w, color=theme.ACCENT, lw=1.7)
                seg_t, seg_w = [], []
            seg_t.append(wrapped[k])
            seg_w.append(w[k])
        if seg_t:
            ax.plot(seg_t, seg_w, color=theme.ACCENT, lw=1.7,
                    label="your trajectory")
        ax.scatter([0], [0], s=70, color=theme.GOOD, zorder=6,
                   label="stable eq. (hanging)")
        ax.scatter([-math.pi, math.pi], [0, 0], s=70, marker="X",
                   color=theme.BAD, zorder=6, label="saddle (inverted)")
        ax.set_xlim(-math.pi, math.pi)
        ax.set_ylim(-9, 9)
        ax.set_xlabel("θ (rad, wrapped)")
        ax.set_ylabel("θ̇ (rad/s)")
        c.legend(loc="upper right")
        c.refresh()

    def _redraw_slip(self):
        ki = float(self.s_ki.value())
        fs = self.s_fs.value() / 10.0
        fc = min(self.s_fc.value() / 10.0, fs)
        self.l_ki.setText(f"{ki:.0f}")
        self.l_fs.setText(f"{fs:.1f} N·m")
        self.l_fc.setText(f"{fc:.1f} N·m")

        tr = run_stick_slip(kp=20.0, kd=1.0, ki=ki, f_static=fs, f_coulomb=fc,
                            duration=8.0, dt=1e-3)
        n = len(tr.theta)
        tail = tr.theta[int(n * 0.5):]
        amp = max(tail) - min(tail)
        self.st_amp.set(f"{math.degrees(amp):.2f}°")
        self.st_amp.set_color(theme.BAD if amp > 0.01 else theme.GOOD)
        self.st_stuck.set(f"{sum(tr.stuck)/n*100:.0f}%")
        self.st_dead.set(f"{math.degrees(fs/20.0):.1f}°")
        self.st_final.set(f"{math.degrees(abs(0.5 - tr.theta[-1])):.2f}°")

        c = self.c3
        c.clear()
        a1, a2 = c.axes
        a1.plot(tr.t, [math.degrees(v) for v in tr.theta], color=theme.ACCENT,
                lw=1.6, label="θ")
        a1.axhline(math.degrees(0.5), color=theme.TEXT_FAINT, lw=1.1, ls="--",
                   label="target")
        a1.fill_between(tr.t, 0, [math.degrees(0.7) * s for s in tr.stuck],
                        color=theme.BAD, alpha=0.08, step="mid")
        a1.set_ylabel("θ (°)")
        c.legend(a1, loc="lower right")
        a2.plot(tr.t, tr.tau, color=theme.BAD, lw=1.3, label="commanded τ")
        a2.axhline(fs, color=theme.WARN, lw=1.1, ls=":", label="breakaway")
        a2.axhline(-fs, color=theme.WARN, lw=1.1, ls=":")
        a2.set_xlabel("time (s)")
        a2.set_ylabel("τ (N·m)")
        c.legend(a2, loc="upper right")
        c.refresh()


# ==========================================================================
# PAGE -- nonlinear control
# ==========================================================================

class NonlinearControlPage(Page):
    TITLE = "Controlling a Nonlinear Robot"
    SUBTITLE = ("Six approaches, in the order you should try them — and the "
                "one that turns out to be the whole of manipulator control.")
    SECTION = SECTION
    NOTES = "design"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>The organising question is always the same:</b> how much of the "
            "nonlinearity do you <i>know</i>?<br><br>"
            "&nbsp;&nbsp;• Know almost none → high-gain PD, and accept the "
            "error.<br>"
            "&nbsp;&nbsp;• Know it locally → linearise, or schedule several "
            "linearisations.<br>"
            "&nbsp;&nbsp;• Know it well → cancel it exactly (computed "
            "torque).<br>"
            "&nbsp;&nbsp;• Know it only within bounds → sliding mode, which "
            "trades exactness for robustness.<br>"
            "&nbsp;&nbsp;• Know only its <i>energy</i> → passivity and energy "
            "shaping, which give the strongest guarantee of the lot.<br>"
            "&nbsp;&nbsp;• Know nothing but can try repeatedly → learn it. "
            "That is the second half of this tutor.", "key"))

        # ---- 0, 1, 2 -------------------------------------------------------
        a = Card("0 · High-gain PD — ignore it and pay the standing error")
        a.add(body(
            "It works, near the setpoint, if the gains dominate. And it fails "
            "in a completely predictable way: the spring must be stretched to "
            "hold the weight, so"))
        a.add(math_label(r"e_{ss} = \frac{mgl\sin\theta}{K_p}", 17))
        a.add(body(
            "— the same standoff argument as the impedance pages, with gravity "
            "in the role of the interaction force. And note it is "
            "<b>posture-dependent</b>: zero at the bottom, maximum horizontal. "
            "A robot that tracks beautifully in one part of the workspace and "
            "sags in another is not badly tuned; it is un-compensated.",
            dim=True))
        self.add(a)

        b = Card("1 · Linearise about an operating point")
        b.add(math_label(r"\delta\dot x = A\,\delta x + B\,\delta u, \qquad "
                         r"A = \left.\frac{\partial f}{\partial x}"
                         r"\right|_{x_0}", 17))
        b.add(body(
            "Take the Jacobian, get a linear system, and use every tool from "
            "the last two sections on it. This is what \"balance controller\" "
            "usually means: the linearisation about upright is valid for the "
            "few degrees a biped is ever allowed to deviate.<br><br>"
            "<b>Valid locally, and \"locally\" is not a formality</b> — the "
            "previous page showed the same pendulum linearising to a stable "
            "oscillator, a double integrator and an unstable pole depending on "
            "where you stood.", dim=True))
        self.add(b)

        c = Card("2 · Gain scheduling — many linearisations, interpolated")
        c.add(math_label(r"K_p(\theta) = J\omega_n^2 + mgl\cos\theta, \qquad "
                         r"K_d = 2\zeta\omega_n J", 17))
        c.add(body(
            "The linearised stiffness varies as cos θ, so a fixed PD is "
            "over-damped in one posture and under-damped in another. Schedule "
            "K<sub>p</sub> against posture and the <b>closed-loop poles stay "
            "put</b> across the whole range.<br><br>"
            "<b>This is what most industrial robots actually run</b>, and its "
            "limitation is the classic one: it assumes the scheduling variable "
            "moves <i>slowly</i> compared with the loop. Schedule on something "
            "fast and the interpolation becomes a dynamic you did not model — "
            "and gain-scheduled systems fail during fast transitions, not at "
            "the operating points you tested.", dim=True))
        self.add(c)

        # ---- 3 computed torque ---------------------------------------------
        self.add(hline())
        self.add(title("3 · Feedback linearisation — the one that runs the "
                       "world's manipulators"))

        d = Card("computed torque")
        d.add(body("Do not fight the nonlinearity. <b>Cancel it</b>, then "
                   "control what is left."))
        d.add(math_label(r"\tau = J\left(\ddot\theta_d + K_d\dot e + K_p e"
                         r"\right) + b\dot\theta + mgl\sin\theta", 17))
        d.add(body("Substitute that into the plant and every nonlinear term "
                   "cancels, leaving:"))
        d.add(math_label(r"\ddot e + K_d\dot e + K_p e = 0", 18))
        d.add(body(
            "<b>A linear, second-order error system with poles you chose</b> — "
            "and the same one everywhere in the workspace, at every speed. The "
            "multi-DOF version is the equation you have seen quoted on the "
            "torque-control page:"))
        d.add(math_label(r"\tau = M(q)\left(\ddot q_d + K_d\dot e + K_p e"
                         r"\right) + C(q,\dot q)\dot q + g(q)", 16))
        d.add(callout(
            "<b>The price, and it is not a footnote.</b> You cancelled the "
            "nonlinearity <i>using a model</i>. Every term you got wrong "
            "reappears as a disturbance, and unlike a plain PD there is no "
            "inherent margin absorbing it — the method's strength is "
            "exactness, so its weakness is exactness.<br><br>"
            "It also needs <b>M, C and g in real time</b>, which is why "
            "computed torque and the rigid-body dynamics libraries arrived "
            "together, and it needs <b>torque control at the joint</b>, which "
            "is why it needs the transparency the actuator pages spent so long "
            "on. Behind a 100:1 harmonic drive with 20 N·m of stiction you "
            "cannot deliver the torque you computed, and the cancellation is a "
            "fiction.", "warn"))
        self.add(d)

        # ---- 4 sliding mode ------------------------------------------------
        e = Card("4 · Sliding mode — robustness bought with a discontinuity")
        e.add(body("Define a surface that <i>is</i> the error dynamics you "
                   "want:"))
        e.add(math_label(r"s = \dot e + \lambda e \qquad\Longrightarrow\qquad "
                         r"s = 0 \;\Rightarrow\; e(t) = e(0)e^{-\lambda t}",
                         17))
        e.add(body(
            "Then drive s to zero with a term large enough to overwhelm any "
            "<b>bounded</b> model error:"))
        e.add(math_label(r"\tau = \hat\tau_{model} + J\lambda\dot e "
                         r"+ \eta\,\mathrm{sign}(s)", 17))
        e.add(body(
            "<b>The remarkable part:</b> once on the surface, the response is "
            "exactly first-order with time constant 1/λ <i>regardless of how "
            "wrong the model is</i>, as long as η exceeds the error bound. "
            "That is why sliding mode survives payload changes that break "
            "computed torque."))
        e.add(body(
            "<b>The cost is chattering.</b> sign(s) switches every sample, "
            "which excites unmodelled resonances, heats the motor and sounds "
            "terrible. The standard fix is a <b>boundary layer</b> — replace "
            "sign(s) with sat(s/φ) — trading a small tracking error for a "
            "continuous command. The widget below has that φ as a slider, "
            "because the trade is the design.", dim=True))
        self.add(e)

        # ---- interactive 1 --------------------------------------------------
        i = Card("the shoot-out: same pendulum, same wrong model")
        i.add(body(
            "Regulate a pendulum to <b>horizontal</b> — chosen because that is "
            "where gravity is largest, so the compensation actually matters. "
            "Then use <b>model error</b> to make the controller's idea of "
            "m, l and b wrong by up to ±40% and see which methods care.",
            dim=True))
        self.cmb = QComboBox()
        for lab, key in (("plain PD", "pd"),
                         ("PD + gravity compensation", "grav"),
                         ("computed torque", "ct"),
                         ("sliding mode", "sm"),
                         ("gain-scheduled PD", "gs")):
            self.cmb.addItem(lab, key)
        self.cmb.setCurrentIndex(2)
        self.cmb.currentIndexChanged.connect(self._redraw_cmp)
        i.add_layout(labelled("Controller", self.cmb, width=80))
        self.s_err = slider(-40, 40, -30)        # %
        self.s_kp = slider(5, 300, 60)
        self.s_phi = slider(0, 50, 5)            # x0.01 boundary layer
        self.l_err, self.l_kp, self.l_phi = QLabel(), QLabel(), QLabel()
        i.add_layout(slider_row("model error (%)", self.s_err, self.l_err))
        i.add_layout(slider_row("K_p", self.s_kp, self.l_kp))
        i.add_layout(slider_row("sliding boundary φ (×0.01)", self.s_phi,
                                self.l_phi))
        self.st_ess = Stat("steady error", "--", theme.BAD)
        self.st_pk = Stat("peak torque", "--", theme.WARN)
        self.st_chat = Stat("command chatter", "--", theme.VIOLET)
        self.st_set = Stat("settled by", "--", theme.GOOD)
        i.add_layout(stat_row(self.st_ess, self.st_pk, self.st_chat,
                              self.st_set))
        self.c1 = MplCanvas(width=7.4, height=3.4, nrows=2)
        i.add(self.c1)
        self.add(i)
        for s in (self.s_err, self.s_kp, self.s_phi):
            s.valueChanged.connect(self._redraw_cmp)
        self._redraw_cmp()

        self.add(callout(
            "<b>Run the comparison at −30% model error and read the steady "
            "error column.</b> Plain PD is the worst and does not care about "
            "the model because it never had one. Gravity compensation removes "
            "most of it. Computed torque is <i>perfect at 0% error and "
            "degrades in proportion</i>. Sliding mode barely moves — and if you "
            "set φ = 0 you will see the chatter number explode, which is the "
            "price it charges.<br><br>"
            "That table is the entire engineering choice, and note that none of "
            "the four is the answer. The answer is: how well do you know your "
            "robot, and how much chattering can your gearbox tolerate?", "good"))

        # ---- 5 Lyapunov and passivity ----------------------------------------
        self.add(hline())
        self.add(title("5 · Lyapunov and passivity — proving it without solving "
                       "it"))

        f = Card("the direct method")
        f.add(body(
            "There are no poles, so \"all poles in the left half plane\" is "
            "unavailable. Lyapunov's answer is to find a scalar function that "
            "behaves like <b>energy</b> — positive everywhere except at the "
            "equilibrium, and only ever decreasing:"))
        f.add(math_label(r"V(x) > 0, \qquad \dot V(x) \leq 0 "
                         r"\quad\Longrightarrow\quad \text{stable}", 17))
        f.add(body("For gravity-compensated PD on the pendulum, take the "
                   "obvious candidate:"))
        f.add(math_label(r"V = \frac{1}{2} J\dot\theta^2 "
                         r"+ \frac{1}{2} K_p(\theta-\theta_d)^2 "
                         r"\qquad\Longrightarrow\qquad "
                         r"\dot V = -(K_d + b)\,\dot\theta^2 \leq 0", 16))
        f.add(body(
            "<b>Read what that just did.</b> A stability proof for a nonlinear "
            "system — no linearisation, no poles, and without solving the "
            "differential equation. V is kinetic plus virtual spring energy, "
            "and V̇ says damping can only take energy out.<br><br>"
            "The catch is honest: nothing tells you how to <i>find</i> V. For "
            "mechanical systems the answer is nearly always \"try the energy\", "
            "and that works often enough to matter.", dim=True))
        self.add(f)

        g = Card("passivity — the guarantee that does not need a model of the "
                 "world")
        g.add(body(
            "A system is <b>passive</b> if it can never put out more energy "
            "than was put in. The theorem that follows is the strongest result "
            "in this whole tutor:"))
        g.add(title("A passive controller connected to a passive environment "
                    "is stable — whatever that environment turns out to be.",
                    15))
        g.add(body(
            "No model of the environment. No margin to compute. No assumption "
            "about what the robot is about to touch — and the world (walls, "
            "people, objects, floors) <i>is</i> passive, because none of it "
            "generates energy.<br><br>"
            "<b>This is the real reason impedance control is safe</b>, and it "
            "is a much stronger statement than anything gain or phase margin "
            "can give you. A virtual spring-damper with K, B &gt; 0 stores and "
            "dissipates energy; it never creates it. Which is also the precise "
            "reason admittance control lacks the same guarantee: it computes "
            "where to go and then <i>drives</i> there with a stiff loop, and "
            "that loop can inject energy — which is what the stiff-contact "
            "instability on the admittance page actually is, stated in "
            "energy terms."))
        g.add(body(
            "The same idea run forwards instead of backwards gives <b>energy "
            "shaping</b>: rather than commanding through the dynamics, feed "
            "them energy at the rate they will accept. The classic "
            "demonstration is inverting a pendulum with a motor that cannot "
            "lift it.", dim=True))
        self.add(g)

        # ---- interactive 2 ---------------------------------------------------
        i2 = Card("swing-up: invert it with a motor too weak to lift it")
        i2.add(body(
            "The torque limit is a <i>fraction</i> of mgl, so lifting it "
            "directly is impossible at any gain. The energy controller pumps "
            "τ·ω &gt; 0 until the pendulum has exactly the energy of the "
            "inverted equilibrium, then a local PD catches it. Watch the energy "
            "trace climb to the dashed line and stop.", dim=True))
        self.s_lim = slider(5, 120, 35)          # % of mgl
        self.s_ke = slider(2, 60, 15)            # x0.1
        self.l_lim, self.l_ke = QLabel(), QLabel()
        i2.add_layout(slider_row("torque limit (% of mgl)", self.s_lim,
                                 self.l_lim))
        i2.add_layout(slider_row("pump gain k_E (×0.1)", self.s_ke, self.l_ke))
        self.st_lim = Stat("τ limit", "--", theme.WARN)
        self.st_mgl = Stat("mgl (cannot lift)", "--", theme.BAD)
        self.st_swing = Stat("swings needed", "--", theme.VIOLET)
        self.st_up = Stat("inverted?", "--", theme.GOOD)
        i2.add_layout(stat_row(self.st_lim, self.st_mgl, self.st_swing,
                               self.st_up))
        self.c2 = MplCanvas(width=7.4, height=3.4, nrows=2)
        i2.add(self.c2)
        self.add(i2)
        for s in (self.s_lim, self.s_ke):
            s.valueChanged.connect(self._redraw_swing)
        self._redraw_swing()

        # ---- 6 the bridge -----------------------------------------------------
        self.add(hline())
        self.add(title("6 · When you do not have a model at all"))

        h = Card("adaptive, MPC, and the handover to the second half of this "
                 "tutor")
        h.add(body(
            "<b>Adaptive control.</b> Do not assume the parameters; "
            "<i>estimate them online</i> while controlling. For manipulators "
            "there is a beautiful result — the dynamics are <b>linear in the "
            "inertial parameters</b> — which makes the estimator well-posed and "
            "gives provable convergence. It needs persistent excitation: a "
            "robot standing still learns nothing.<br><br>"
            "<b>Model predictive control.</b> At every tick, optimise the input "
            "sequence over a finite horizon using the nonlinear model, apply "
            "the first input, throw the rest away, repeat. Handles constraints "
            "— torque limits, joint limits, the friction cone — <i>natively</i>, "
            "which none of the methods above do. The price is that you are "
            "solving an optimisation problem inside a real-time deadline, and "
            "the Real-Time page has opinions about that.<br><br>"
            "<b>Reinforcement learning.</b> Do not model, do not optimise "
            "online — <i>learn</i> the policy from experience, offline, and "
            "then evaluate a fixed function at run time. It gives up the "
            "guarantees every method on this page provides, and buys the "
            "ability to work when no usable model exists at all."))
        h.add(callout(
            "<b>Which is exactly where this half of the tutor hands over.</b> "
            "Look back at what the last twenty pages have been doing: define "
            "the dynamics, define what \"good\" means, find the input that "
            "achieves it, subject to what the actuator can deliver.<br><br>"
            "The RL half asks the same question with the model deleted. It "
            "trades the model for experience — which is why the Goal of Control "
            "page drew the identical loop for both, and why every constraint "
            "established here still applies afterwards. <b>A learned policy is "
            "still bounded by the bandwidth, the reflected inertia and the "
            "torque limit.</b> Learning changes where the policy comes from, "
            "not what physics allows it to do.", "key"))
        self.add(h)

        self.finish()

    # ------------------------------------------------------------------
    def _redraw_cmp(self):
        err = self.s_err.value() / 100.0
        kp = float(self.s_kp.value())
        phi = self.s_phi.value() / 100.0
        self.l_err.setText(f"{err*100:+.0f}%")
        self.l_kp.setText(f"{kp:.0f}")
        self.l_phi.setText(f"{phi:.2f}" if phi > 0 else "0 (pure sign)")

        pend = Pendulum(m=1.0, l=0.5, b=0.15)
        target = math.pi / 2
        kd = 2.0 * 0.9 * math.sqrt(max(kp, 1e-6) * pend.J)
        key = self.cmb.currentData()
        if key == "pd":
            law = pd_controller(kp, kd, theta_d=target)
        elif key == "grav":
            law = gravity_comp_pd(pend, kp, kd, theta_d=target,
                                  model_error=err)
        elif key == "ct":
            law = computed_torque(pend, kp, kd, model_error=err,
                                  traj_fn=lambda t: (target, 0.0, 0.0))
        elif key == "sm":
            law = sliding_mode(pend, lam=8.0, eta=10.0, boundary=phi,
                               theta_d=target, model_error=err)
        else:
            law = gain_scheduled_pd(pend, wn=math.sqrt(kp / pend.J), zeta=0.9,
                                    theta_d=target)

        ts, th, w, tau = trajectory(pend, 0.0, 0.0, duration=4.0, dt=2e-3,
                                    tau_fn=law, tau_limit=60.0)
        ess = abs(th[-1] - target)
        self.st_ess.set(f"{math.degrees(ess):.2f}°")
        self.st_ess.set_color(theme.GOOD if ess < math.radians(0.5)
                              else theme.BAD)
        self.st_pk.set(f"{max(abs(v) for v in tau):.1f} N·m")
        chat = sum(abs(b_ - a_) for a_, b_ in zip(tau, tau[1:])) / max(1, len(tau) - 1)
        self.st_chat.set(f"{chat:.2f}")
        self.st_chat.set_color(theme.BAD if chat > 1.0 else theme.GOOD)
        band = math.radians(1.0)
        settled = 0.0
        for t_, x_ in zip(ts, th):
            if abs(x_ - target) > band:
                settled = t_
        self.st_set.set(f"{settled:.2f} s" if settled < ts[-1] * 0.95
                        else "not settled")

        c = self.c1
        c.clear()
        a1, a2 = c.axes
        a1.plot(ts, [math.degrees(v) for v in th], color=theme.ACCENT, lw=2.0,
                label="θ")
        a1.axhline(math.degrees(target), color=theme.TEXT_FAINT, lw=1.2,
                   ls="--", label="target (horizontal)")
        a1.set_ylabel("θ (°)")
        c.legend(a1, loc="lower right")
        a2.plot(ts, tau, color=theme.BAD, lw=1.2)
        a2.axhline(pend.m * pend.g * pend.l, color=theme.WARN, lw=1.0, ls=":",
                   label="mgl")
        a2.set_xlabel("time (s)")
        a2.set_ylabel("τ (N·m)")
        c.legend(a2, loc="upper right")
        c.refresh()

    def _redraw_swing(self):
        frac = self.s_lim.value() / 100.0
        ke = self.s_ke.value() / 10.0
        pend = Pendulum(m=1.0, l=0.5, b=0.06)
        mgl = pend.m * pend.g * pend.l
        lim = frac * mgl
        self.l_lim.setText(f"{frac*100:.0f}%")
        self.l_ke.setText(f"{ke:.1f}")
        self.st_lim.set(f"{lim:.2f} N·m")
        self.st_mgl.set(f"{mgl:.2f} N·m")

        law = energy_swingup(pend, k_e=ke, tau_limit=lim, catch=0.5,
                             kp=45.0, kd=9.0)
        ts, th, w, tau = trajectory(pend, 0.05, 0.0, duration=18.0, dt=3e-3,
                                    tau_fn=law, tau_limit=60.0)
        wrapped = [math.atan2(math.sin(x), math.cos(x)) for x in th]
        up = abs(abs(wrapped[-1]) - math.pi) < 0.15
        self.st_up.set("yes" if up else "no")
        self.st_up.set_color(theme.GOOD if up else theme.BAD)
        swings = sum(1 for a_, b_ in zip(w, w[1:]) if a_ * b_ < 0)
        self.st_swing.set(f"{swings//2}" if up else "—")

        energies = [pend.energy(x, v) for x, v in zip(th, w)]
        e_top = 2 * mgl

        c = self.c2
        c.clear()
        a1, a2 = c.axes
        a1.plot(ts, [math.degrees(x) for x in wrapped], color=theme.ACCENT,
                lw=1.4, label="θ (wrapped)")
        a1.axhline(180, color=theme.GOOD, lw=1.1, ls="--", label="upright")
        a1.axhline(-180, color=theme.GOOD, lw=1.1, ls="--")
        a1.set_ylabel("θ (°)")
        c.legend(a1, loc="lower right")
        a2.plot(ts, energies, color=theme.VIOLET, lw=1.7, label="energy")
        a2.axhline(e_top, color=theme.WARN, lw=1.2, ls="--",
                   label="energy of the inverted equilibrium")
        a2.set_xlabel("time (s)")
        a2.set_ylabel("E (J)")
        c.legend(a2, loc="lower right")
        c.refresh()
