"""
Page 1: real-time control -- the page that has to come first.

Everything later assumes "the loop runs every tick". This page is about what
that sentence actually costs, and it exists to kill one specific and very
common misunderstanding:

    "our controller runs at 1000 Hz, so we can control things at 1000 Hz"

No. 1 kHz is how often you LOOK. The rate at which you can ACT is 10-20x
lower, and the rate at which the MECHANICS will let you act may be lower
still. Three different numbers, and the smallest one wins.
"""

from __future__ import annotations

import math

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem

from ctrlcore.realtime import (
    TaskProfile,
    alias_frequency,
    delay_limited_bandwidth,
    delay_phase_lag_deg,
    nyquist,
    practical_bandwidth,
    rate_monotonic_bound,
    run_aliasing,
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

SECTION = "Real-Time"


def _tbl(headers, rows, widths, height=None):
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
    t.horizontalHeader().setStretchLastSection(True)
    t.setMinimumHeight(height or (44 + 60 * len(rows)))
    return t


class RealTimePage(Page):
    TITLE = "Real-Time Control"
    SUBTITLE = ("Your loop rate is not your bandwidth. Three numbers people "
                "collapse into one, and the failures that follow.")
    SECTION = SECTION
    NOTES = "foundation"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>What \"real-time\" means — and does not mean.</b><br><br>"
            "Real-time does <b>not</b> mean fast. It means <b>predictable</b>. A "
            "system that always answers in 8 ms is real-time; a system that "
            "usually answers in 0.2 ms but occasionally takes 40 ms is not, and "
            "is far more dangerous, because you will design around the 0.2 ms and "
            "be destroyed by the 40 ms.<br><br>"
            "The quantity that matters is not the average. It is the "
            "<b>worst case</b>.", "key"))

        # ---- hard / firm / soft ---------------------------------------------
        h = Card("hard, firm, soft")
        h.add(_tbl(
            ["Class", "A missed deadline means", "Examples"],
            [("Hard real-time",
              "System failure. The late answer is not merely late — it is "
              "wrong, and may be actively harmful.",
              "Motor commutation, current loop, joint torque loop, airbag "
              "firing, a biped's balance controller mid-step"),
             ("Firm real-time",
              "The late result is useless and is discarded, but the system "
              "survives.",
              "A vision frame that arrives after the grasp decision was "
              "needed; drop it and use the next one"),
             ("Soft real-time",
              "Quality degrades in proportion to lateness. Still useful.",
              "Teleop video, logging, UI, path re-planning, battery telemetry")],
            [150, 320, 330]))
        h.add(body(
            "A humanoid has all three running at once, and they must not share "
            "a priority level. The classic failure is putting the balance "
            "controller and the network stack in the same thread.", dim=True))
        self.add(h)

        # ---- the three numbers ----------------------------------------------
        self.add(hline())
        self.add(title("The three numbers — this answers \"we sample at 1 kHz, "
                       "so what?\""))

        n = Card("sampling rate ≠ Nyquist ≠ bandwidth")
        n.add(body(
            "<b>f<sub>s</sub> — sampling rate.</b> How often you look. Set by "
            "your timer interrupt. 1 kHz is typical for a joint loop, 10–20 kHz "
            "for a current loop.<br><br>"
            "<b>f<sub>nyq</sub> = f<sub>s</sub>/2 — the Nyquist frequency.</b> "
            "The highest frequency the samples can even <i>represent</i>. This "
            "is a statement about <b>reconstructing a signal</b>, not about "
            "closing a loop.<br><br>"
            "<b>f<sub>bw</sub> — closed-loop bandwidth.</b> How fast you can "
            "actually <b>act</b>: the frequency at which your closed-loop "
            "response has fallen by 3 dB. Realistically "
            "<b>f<sub>s</sub>/10 to f<sub>s</sub>/20</b>."))
        n.add(body(
            "So a 1 kHz loop gives Nyquist at 500 Hz and a usable control "
            "bandwidth around <b>50–100 Hz</b>. The gap is not waste — it is "
            "paid out in phase:", dim=True))
        n.add(body(
            "&nbsp;&nbsp;• <b>zero-order hold</b> — the command is held constant "
            "between ticks, worth an average delay of T/2<br>"
            "&nbsp;&nbsp;• <b>computation delay</b> — read sensors, compute, "
            "write: up to another full T<br>"
            "&nbsp;&nbsp;• <b>phase margin</b> — you must keep 40–60° in hand or "
            "the loop rings and then oscillates"))
        self.add(n)

        i = Card("watch the phase get eaten")
        i.add(body(
            "A pure delay costs phase linearly with frequency: "
            "∠ = −360·f·T<sub>d</sub> degrees. It buys you nothing and takes "
            "your stability margin. This is why \"just add a bigger buffer\" is "
            "never a fix.", dim=True))
        self.s_fs = slider(100, 20000, 1000)
        self.s_delay = slider(0, 20, 2)
        self.l_fs, self.l_delay = QLabel(), QLabel()
        i.add_layout(slider_row("sample rate f_s (Hz)", self.s_fs, self.l_fs))
        i.add_layout(slider_row("loop delay (×0.5 ms)", self.s_delay, self.l_delay))

        self.st_nyq = Stat("Nyquist", "--", theme.WARN)
        self.st_bw = Stat("usable bandwidth", "--", theme.GOOD)
        self.st_phase = Stat("phase lost at f_bw", "--", theme.BAD)
        self.st_budget = Stat("time per tick", "--", theme.ACCENT)
        i.add_layout(stat_row(self.st_nyq, self.st_bw, self.st_phase,
                              self.st_budget))
        self.canvas = MplCanvas(width=7.4, height=2.9)
        i.add(self.canvas)
        self.add(i)
        self.s_fs.valueChanged.connect(self._redraw_phase)
        self.s_delay.valueChanged.connect(self._redraw_phase)
        self._redraw_phase()

        self.add(callout(
            "<b>And there is a fourth number that beats all three.</b> The "
            "mechanics. If you have a series elastic actuator whose spring-load "
            "resonance sits at 12 Hz, then your control bandwidth is 12 Hz no "
            "matter how fast the CPU is. Sampling faster cannot make a spring "
            "stiffer.<br><br>"
            "Order of who wins, worst first: <b>mechanics → delay → sample rate "
            "→ CPU speed</b>. People optimise that list backwards.", "warn"))

        # ---- aliasing --------------------------------------------------------
        self.add(hline())
        self.add(title("Aliasing: the failure you cannot debug in software"))

        a = Card("what folding actually looks like")
        a.add(math_label(r"f_{alias} = \left| f_{signal} - f_s \cdot "
                         r"\mathrm{round}(f_{signal}/f_s) \right|", 16))
        a.add(body(
            "Content above Nyquist does not disappear when you sample. It "
            "<b>folds back down</b> and reappears as a lower frequency that is "
            "mathematically indistinguishable from a real signal."))
        a.add(body(
            "<b>The concrete disaster:</b> a gearbox tooth-mesh vibration at 950 "
            "Hz, sampled at 1 kHz, appears as a <b>50 Hz</b> oscillation. Your "
            "controller sees a 50 Hz disturbance that is not there, fights it, "
            "and injects a real 50 Hz oscillation into the robot.<br><br>"
            "<b>No digital filter can fix this.</b> The information was "
            "destroyed at the ADC. The only cure is an <b>analog anti-alias "
            "filter before the converter</b>, with its corner below "
            "f<sub>s</sub>/2.", dim=True))
        self.add(a)

        i2 = Card("fold a signal yourself")
        self.s_sig = slider(10, 3000, 950)
        self.s_rate = slider(100, 4000, 1000)
        self.l_sig, self.l_rate = QLabel(), QLabel()
        i2.add_layout(slider_row("true signal (Hz)", self.s_sig, self.l_sig))
        i2.add_layout(slider_row("sample rate (Hz)", self.s_rate, self.l_rate))
        self.st_alias = Stat("appears as", "--", theme.BAD)
        self.st_safe = Stat("below Nyquist?", "--", theme.GOOD)
        i2.add_layout(stat_row(self.st_alias, self.st_safe))
        self.canvas2 = MplCanvas(width=7.4, height=2.7)
        i2.add(self.canvas2)
        self.add(i2)
        self.s_sig.valueChanged.connect(self._redraw_alias)
        self.s_rate.valueChanged.connect(self._redraw_alias)
        self._redraw_alias()

        # ---- reconstruction vs "it looks wrong" -------------------------------
        r = Card("\"2× is not enough, 3× still looks wrong, 4× is fine\" — "
                 "what is going on")
        r.add(body(
            "Run the widget above with the true signal at <b>1000 Hz</b> and walk "
            "the sample rate up. Four regimes, and only the first one is actually "
            "aliasing:"))
        r.add(body(
            "&nbsp;&nbsp;• <b>f<sub>s</sub> = 1500 Hz (1.5×).</b> Below Nyquist. "
            "The 1 kHz signal folds to |1000 − 1500| = <b>500 Hz</b> and is "
            "<i>gone</i>. Information destroyed at the ADC. Nothing recovers "
            "it.<br>"
            "&nbsp;&nbsp;• <b>f<sub>s</sub> = 2000 Hz (exactly 2×).</b> The bound "
            "is <b>strict</b>: the theorem says f<sub>s</sub> &gt; 2f, not ≥. At "
            "exactly 2× you get two samples per cycle at one fixed pair of phases. "
            "Land them on the zero crossings and every sample reads zero — the "
            "sine has vanished entirely. Land them elsewhere and you recover the "
            "frequency but the <i>wrong amplitude</i>. Exactly-2× is the failure "
            "case, not the success case.<br>"
            "&nbsp;&nbsp;• <b>f<sub>s</sub> = 3913 Hz (3.913×).</b> Comfortably "
            "above Nyquist. The stat correctly reports 1000 Hz and \"below "
            "Nyquist: yes\". <b>Nothing is folded and nothing is lost</b> — yet "
            "the red trace looks like a wobbling, amplitude-modulated mess that "
            "clearly is not your sine.<br>"
            "&nbsp;&nbsp;• <b>f<sub>s</sub> = 4000 Hz (exactly 4×).</b> Suddenly "
            "clean and stable."))
        r.add(body(
            "The 3913 → 4000 jump is the one that feels like magic, and it is "
            "not. <b>Nothing changed about the information content.</b> Both rates "
            "capture the 1 kHz sine perfectly. What changed is how the samples "
            "<i>look when you draw straight lines between them</i>.", dim=True))
        r.add(title("Two different claims that get collapsed into one", 15))
        r.add(body(
            "<b>1 · What Nyquist actually promises.</b> If f<sub>s</sub> &gt; 2f, "
            "the samples contain <i>enough information</i> to reconstruct the "
            "original signal <b>exactly</b>. That is a statement about "
            "information, not about appearance. And the reconstruction it promises "
            "is a specific one — the ideal low-pass, i.e. <b>sinc "
            "interpolation</b>:"))
        r.add(math_label(r"x(t) = \sum_{n=-\infty}^{\infty} x[n]\;"
                         r"\mathrm{sinc}\!\left(\frac{t - nT_s}{T_s}\right)", 16))
        r.add(body(
            "Every reconstructed point is a weighted sum over <b>all</b> the "
            "samples, not just the two nearest. Run that on the 3913 Hz samples "
            "and the exact 1 kHz sine comes back."))
        r.add(body(
            "<b>2 · What the plot draws.</b> Straight lines between adjacent "
            "samples. Linear interpolation is a crude, badly-shaped low-pass "
            "filter, and it only <i>looks</i> like a sine when you have roughly "
            "<b>10+ samples per cycle</b>. At 3.9 samples per cycle it cannot, "
            "however much information is present."))
        r.add(body(
            "<b>So why does 4× look clean and 3.913× not?</b> The ratio "
            "f<sub>s</sub>/f<sub>sig</sub> is what decides the picture. At exactly "
            "<b>4.000</b>, every cycle is sampled at the same four phases (0°, "
            "90°, 180°, 270°). The polyline is therefore exactly periodic with the "
            "signal, with constant peak height — it reads as a clean waveform "
            "(albeit a triangular-looking one, which is still not the sine).<br><br>"
            "At <b>3.913</b>, each sample advances the phase by 360°×1000/3913 = "
            "<b>92.0°</b>, so the sampling phase <i>creeps</i>. Some cycles get "
            "sampled near the peaks, others near the zero crossings, and the "
            "polyline's apparent amplitude breathes at the beat rate between the "
            "sample grid and the signal. That envelope is a <b>drawing artifact</b> "
            "— a beat between two rates — not a folded frequency. The closer the "
            "ratio sits to 2, the fewer distinct phases you visit and the uglier "
            "it gets, which is why the classic \"picture of aliasing\" in "
            "textbooks is often not aliasing at all.", dim=True))
        self.add(r)

        self.add(callout(
            "<b>Three jobs, three different numbers — this is the whole "
            "resolution.</b><br><br>"
            "&nbsp;&nbsp;• <b>To not lose the information:</b> f<sub>s</sub> "
            "&gt; 2·f, strictly, with an analog anti-alias filter. This is "
            "Nyquist, and it is the <i>only</i> thing Nyquist claims.<br>"
            "&nbsp;&nbsp;• <b>To make the waveform look right</b> when you connect "
            "the dots (a plot, a scope, a naive numerical derivative): "
            "<b>≥10 samples per cycle</b>.<br>"
            "&nbsp;&nbsp;• <b>To control at that frequency:</b> "
            "<b>10–20× f</b>, because you must additionally pay ZOH delay, "
            "compute delay and phase margin.<br><br>"
            "\"2× is not enough\" is true for jobs two and three and false for "
            "job one. Nobody says which job they mean, which is exactly why this "
            "is confusing.", "key"))

        # ---- scheduling -------------------------------------------------------
        self.add(hline())
        self.add(title("Scheduling: FreeRTOS and friends"))

        s = Card("the task model")
        s.add(body(
            "A control loop is a <b>periodic task</b> with three numbers: a "
            "period T, a worst-case execution time (WCET), and a deadline "
            "(usually = T). It is schedulable only if WCET < deadline, "
            "<i>always</i>, not on average."))
        s.add(math_label(r"U = \sum_i \frac{C_i}{T_i} \;\le\; "
                         r"n\left(2^{1/n} - 1\right)", 16))
        s.add(body(
            "That is the <b>Liu &amp; Layland bound</b> for rate-monotonic "
            "scheduling — fixed priorities, shortest period gets highest "
            "priority, which is exactly what FreeRTOS gives you. Stay under it "
            "and every deadline is <b>provably</b> met. Go over and you may "
            "still be fine, but you have swapped a proof for a hope.<br><br>"
            "n=1 → 100%, n=2 → 82.8%, n=3 → 78.0%, n→∞ → <b>69.3%</b> (ln 2). "
            "Yes: with many tasks you must leave nearly a third of the CPU idle "
            "to keep the guarantee.", dim=True))
        self.add(s)

        i3 = Card("budget a real loop")
        self.s_period = slider(1, 20, 10)
        self.s_wcet = slider(1, 200, 35)
        self.s_ntask = slider(1, 12, 4)
        self.l_period, self.l_wcet, self.l_ntask = QLabel(), QLabel(), QLabel()
        i3.add_layout(slider_row("period (×0.1 ms)", self.s_period, self.l_period))
        i3.add_layout(slider_row("WCET (×0.01 ms)", self.s_wcet, self.l_wcet))
        i3.add_layout(slider_row("number of tasks", self.s_ntask, self.l_ntask))
        self.st_util = Stat("utilisation", "--", theme.ACCENT)
        self.st_bound = Stat("RM bound", "--", theme.WARN)
        self.st_verdict = Stat("guaranteed?", "--", theme.GOOD)
        i3.add_layout(stat_row(self.st_util, self.st_bound, self.st_verdict))
        self.canvas3 = MplCanvas(width=7.4, height=2.3)
        i3.add(self.canvas3)
        self.add(i3)
        for w in (self.s_period, self.s_wcet, self.s_ntask):
            w.valueChanged.connect(self._redraw_sched)
        self._redraw_sched()

        f = Card("FreeRTOS specifics worth knowing")
        f.add(body(
            "<b>Preemptive fixed-priority scheduling.</b> The highest-priority "
            "ready task runs. Your torque loop must be the highest priority "
            "thing in the system, above comms, above logging, above everything."))
        f.add(body(
            "<b>Priority inversion — the failure that killed Mars Pathfinder.</b> "
            "A low-priority task takes a mutex. A high-priority task blocks on "
            "that mutex. A medium-priority task then preempts the low-priority "
            "one, which now cannot run, cannot release the mutex, and so the "
            "high-priority task is blocked by a task with <i>lower</i> priority "
            "than itself. Fix: <b>priority inheritance</b> — FreeRTOS mutexes "
            "(<code>xSemaphoreCreateMutex</code>) do this; binary semaphores "
            "(<code>xSemaphoreCreateBinary</code>) do <b>not</b>. Use the right "
            "one."))
        f.add(body(
            "<b>Tick rate ≠ loop rate.</b> <code>configTICK_RATE_HZ</code> is "
            "usually 1000, and <code>vTaskDelayUntil</code> can only resolve to "
            "a tick. For a hard loop, drive it from a <b>hardware timer "
            "interrupt</b> or an ADC end-of-conversion, not from the scheduler "
            "tick."))
        f.add(body(
            "<b>Do not do these inside the loop:</b> dynamic allocation "
            "(<code>malloc</code>/<code>new</code> — unbounded time and "
            "fragmentation), <code>printf</code> (can block for milliseconds), "
            "unbounded <code>while</code> loops, blocking I/O, or anything "
            "whose execution time depends on data.", dim=True))
        f.add(body(
            "<b>Measure, do not assume.</b> Toggle a GPIO high on loop entry and "
            "low on exit, and put a scope on it. The pulse width is your "
            "execution time and the gap is your real jitter. This one trick "
            "finds more real-time bugs than any amount of reasoning.", dim=True))
        self.add(f)

        rt = Card("what runs where, on a real humanoid")
        rt.add(_tbl(
            ["Loop", "Typical rate", "Where it runs", "Class"],
            [("Current / commutation (FOC)", "10–40 kHz",
              "Motor-driver MCU or FPGA", "hard"),
             ("Joint torque / impedance", "1–4 kHz", "Joint MCU, FreeRTOS or bare "
              "metal", "hard"),
             ("Whole-body control / balance", "200 Hz – 1 kHz",
              "Onboard PC, Linux with PREEMPT_RT", "hard"),
             ("Footstep / trajectory planning", "10–100 Hz", "Onboard PC, normal "
              "priority", "firm"),
             ("Perception, RL policy inference", "10–60 Hz", "GPU / accelerator",
              "firm"),
             ("Behaviour, speech, logging, UI", "1–10 Hz", "Anywhere", "soft")],
            [230, 130, 230, 90], height=430))
        rt.add(body(
            "Note the hierarchy: fast, simple and hard at the bottom; slow, "
            "clever and soft at the top. If your RL policy stalls for 200 ms, "
            "the joint loops keep the robot standing. That layering is a "
            "<b>safety architecture</b>, not an implementation detail — and it "
            "is the same layering biology uses (0 ms passive stiffness, 30–50 ms "
            "reflex, ~200 ms voluntary).", dim=True))
        self.add(rt)

        self.add(callout(
            "<b>Carry these forward.</b><br><br>"
            "1. <b>Predictable beats fast.</b> Worst case is the only case that "
            "counts.<br>"
            "2. <b>Sampling rate is a ceiling, not a capability.</b> Divide by "
            "10–20 to get real bandwidth.<br>"
            "3. <b>Delay is pure loss.</b> It costs phase margin and returns "
            "nothing.<br>"
            "4. <b>Anti-alias in analog.</b> Software cannot un-fold a folded "
            "signal.<br>"
            "5. <b>Mechanics usually wins.</b> A 12 Hz spring caps you at 12 Hz "
            "regardless of CPU.<br><br>"
            "Every actuator page that follows is really a statement about which "
            "of these five limits binds first.", "good"))

        self.finish()

    # ------------------------------------------------------------------
    def _redraw_phase(self):
        fs = float(self.s_fs.value())
        delay = self.s_delay.value() * 0.0005
        self.l_fs.setText(f"{fs:.0f} Hz")
        self.l_delay.setText(f"{delay * 1000:.1f} ms")

        nyq = nyquist(fs)
        total_delay = delay + 1.5 / fs          # loop delay + ZOH/compute
        # Honest answer: whichever ceiling binds first.
        bw_sample = practical_bandwidth(fs)
        bw_delay = delay_limited_bandwidth(total_delay)
        bw = min(bw_sample, bw_delay)
        self.st_nyq.set(f"{nyq:.0f} Hz")
        self.st_bw.set(f"{bw:.0f} Hz")
        self.st_bw.set_color(theme.BAD if bw_delay < bw_sample else theme.GOOD)
        self.st_phase.set(f"{delay_phase_lag_deg(total_delay, bw):.0f}°")
        self.st_budget.set(f"{1000.0 / fs:.2f} ms")

        c = self.canvas
        c.clear()
        freqs = [10 ** (x / 30.0) for x in range(0, 105)]
        c.ax.semilogx(freqs, [delay_phase_lag_deg(total_delay, f) for f in freqs],
                      color=theme.BAD, lw=2.3, label="phase lost to delay")
        c.ax.axhline(-60, color=theme.WARN, lw=1.2, ls="--",
                     label="−60°: margin getting thin")
        c.ax.axhline(-180, color=theme.TEXT_FAINT, lw=1.2, ls=":",
                     label="−180°: this is where it oscillates")
        binds = "delay" if bw_delay < bw_sample else "sampling"
        c.ax.axvline(bw, color=theme.GOOD, lw=1.4)
        c.ax.text(bw, -20, f"  usable bandwidth\n  ({binds} is the limit)",
                  color=theme.GOOD, fontsize=7.5)
        if bw_sample != bw:
            c.ax.axvline(bw_sample, color=theme.TEXT_FAINT, lw=1.0, ls="-.")
            c.ax.text(bw_sample, -95, " what f_s alone\n would allow",
                      color=theme.TEXT_FAINT, fontsize=7)
        c.ax.axvline(nyq, color=theme.WARN, lw=1.1, ls="--")
        c.ax.text(nyq, -150, " Nyquist", color=theme.WARN, fontsize=7.5)
        c.ax.set_xlabel("frequency (Hz)")
        c.ax.set_ylabel("phase (deg)")
        c.ax.set_ylim(-220, 10)
        c.legend(loc="lower left")
        c.refresh()

    # ------------------------------------------------------------------
    def _redraw_alias(self):
        f_sig = float(self.s_sig.value())
        f_s = float(self.s_rate.value())
        self.l_sig.setText(f"{f_sig:.0f} Hz")
        self.l_rate.setText(f"{f_s:.0f} Hz")

        dur = max(4.0 / f_s, 0.006)
        td, yd, ts, ys, f_al = run_aliasing(f_sig, f_s, duration=dur * 6)
        safe = f_sig < f_s / 2
        self.st_alias.set(f"{f_al:.0f} Hz")
        self.st_alias.set_color(theme.GOOD if safe else theme.BAD)
        self.st_safe.set("yes" if safe else "NO — folded")
        self.st_safe.set_color(theme.GOOD if safe else theme.BAD)

        c = self.canvas2
        c.clear()
        c.ax.plot([t * 1000 for t in td], yd, color=theme.TEXT_FAINT, lw=1.0,
                  label=f"true signal, {f_sig:.0f} Hz")
        c.ax.plot([t * 1000 for t in ts], ys, color=theme.BAD, lw=1.8,
                  marker="o", ms=3.5,
                  label=f"what the controller sees, {f_al:.0f} Hz")
        c.ax.set_xlabel("time (ms)")
        c.ax.set_ylabel("amplitude")
        c.ax.set_ylim(-1.4, 1.4)
        c.legend(loc="upper right")
        c.refresh()

    # ------------------------------------------------------------------
    def _redraw_sched(self):
        period = self.s_period.value() * 0.1
        wcet = self.s_wcet.value() * 0.01
        n = self.s_ntask.value()
        self.l_period.setText(f"{period:.1f} ms")
        self.l_wcet.setText(f"{wcet:.2f} ms")
        self.l_ntask.setText(f"{n}")

        task = TaskProfile(period_ms=period, wcet_ms=wcet)
        u = task.utilisation * n
        bound = rate_monotonic_bound(n)
        ok = u <= bound and task.schedulable
        self.st_util.set(f"{u * 100:.0f}%")
        self.st_bound.set(f"{bound * 100:.0f}%")
        self.st_verdict.set("provably" if ok else ("maybe" if u < 1.0 else "NO"))
        self.st_verdict.set_color(theme.GOOD if ok else
                                  (theme.WARN if u < 1.0 else theme.BAD))

        c = self.canvas3
        c.clear()
        ns = list(range(1, 13))
        c.ax.plot(ns, [rate_monotonic_bound(k) * 100 for k in ns],
                  color=theme.WARN, lw=2.2, label="rate-monotonic bound")
        c.ax.axhline(math.log(2) * 100, color=theme.TEXT_FAINT, lw=1.1, ls=":",
                     label="ln 2 = 69.3% asymptote")
        c.ax.scatter([n], [u * 100], s=60,
                     color=theme.GOOD if ok else theme.BAD, zorder=5,
                     label="your system")
        c.ax.set_xlabel("number of periodic tasks")
        c.ax.set_ylabel("CPU utilisation (%)")
        c.ax.set_ylim(0, 120)
        c.legend(loc="upper right")
        c.refresh()
