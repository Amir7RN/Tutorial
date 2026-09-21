"""Animated physical explanations for the opening lessons (no plot widgets).

Sampling examples use exact uniform-time phase arithmetic. Mechanical frequency
comparisons explicitly use illustrative first-order CLOSED-LOOP models, not an
unvalidated simulation of a particular DD, SEA or PEA actuator.
"""
import math
import cmath

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPen

from .. import theme


def notch_response(frequency, centre=18, zero_damping=.015, pole_damping=.15):
    """Exact N(jω), using frequency ratio so Hz and rad/s factors cancel."""
    r = frequency / centre
    return (1-r*r+2j*zero_damping*r)/(1-r*r+2j*pole_damping*r)


def sampled_value(frequency, rate, index, sine=False):
    angle = 2 * math.pi * frequency * index / rate
    return math.sin(angle) if sine else math.cos(angle)


def signed_alias(frequency, rate):
    return (frequency + rate / 2) % rate - rate / 2


def response_gain_phase(frequency, bandwidth):
    """H(jf) = 1/(1 + j f/f_bw), unity DC gain."""
    ratio = frequency / bandwidth
    return 1 / math.sqrt(1 + ratio * ratio), -math.atan(ratio)


def step_response(t, zeta=0.3, wn=3.0):
    """Unit step of wn²/(s² + 2*zeta*wn*s + wn²)."""
    if zeta < 1:
        wd = wn * math.sqrt(1-zeta*zeta)
        return 1-math.exp(-zeta*wn*t)*(math.cos(wd*t)+zeta*wn/wd*math.sin(wd*t))
    if zeta == 1:
        return 1-math.exp(-wn*t)*(1+wn*t)
    r1 = -wn*(zeta-math.sqrt(zeta*zeta-1))
    r2 = -wn*(zeta+math.sqrt(zeta*zeta-1))
    return 1+(r2*math.exp(r1*t)-r1*math.exp(r2*t))/(r1-r2)


class FoundationScenes:
    """Drawing mixin; uses LessonCanvas's text, box, dot, line and arrow."""

    def dial(self, cx, cy, angle, label, color=theme.CYAN, radius=59):
        self.p.setPen(QPen(QColor(theme.BORDER), 2))
        self.p.setBrush(Qt.NoBrush)
        self.p.drawEllipse(QPointF(cx, cy), radius, radius)
        self.arrow(cx, cy, cx+radius*.9*math.cos(angle), cy-radius*.9*math.sin(angle), color, False)
        self.text(cx-125, cy-radius-39, 250, 33, label, color, 11)

    def draw_tick_cycle(self):
        rate, f = self.d.get("rate", 1000), self.d.get("f", 20)
        count = rate/f
        phase = self.progress*2*math.pi
        self.dial(230, 111, phase, f"One {f:g} Hz motion cycle", theme.WARN, 65)
        for i in range(int(count)):
            a = 2*math.pi*i/count
            self.dot(230+77*math.cos(a), 111-77*math.sin(a), 2,
                     theme.CYAN if i <= self.progress*count else theme.BORDER)
        done = min(int(count), int(self.progress*count))
        self.box(425, 26, 400, 67, f"Controller: {rate:g} updates / second\nOne tick every {1000/rate:g} ms", True)
        self.box(425, 107, 400, 72, f"Motion period: {1000/f:g} ms\n{done} of {count:g} updates inside ONE cycle", True, theme.WARN)
        self.note("Gold = motion phase · cyan marks = measure → compute → update ticks · playback slowed down")

    def draw_tick_work(self):
        fraction = self.progress
        lengths = (.18, .35, .12, .35)
        names = ("Read sensor", "Compute torque", "Write command", "Hold command")
        start = 0
        for label, length in zip(names, lengths):
            self.box(50+800*start, 64, 800*length-5, 72, label, start <= fraction < start+length)
            start += length
        self.line(50, 161, 850, 161)
        self.dot(50+800*fraction, 161, 8, theme.WARN)
        self.text(20, 164, 100, 29, "0 ms", size=10)
        self.text(780, 164, 100, 29, "1 ms", size=10)
        self.text(50, 8, 800, 37, "One control tick, magnified — phase durations are illustrative", theme.TEXT_DIM)
        self.note("The new command is held until the next update. The physical joint keeps moving between ticks.")

    def draw_alias_wheel(self):
        f, fs = self.d.get("f", 950), self.d.get("rate", 1000)
        time = self.progress * .01
        n = int(time*fs)
        apparent = signed_alias(f, fs)
        self.dial(170, 107, 2*math.pi*f*time, f"True phase: {f:g} Hz", theme.WARN)
        self.dial(455, 107, 2*math.pi*f*n/fs, "Last camera snapshot", theme.CYAN)
        self.dial(735, 107, 2*math.pi*apparent*time, f"Apparent phase: {apparent:g} Hz", theme.VIOLET)
        flash = time*fs-n < .16
        self.box(365, 170, 180, 29, f"FLASH #{n}" if flash else f"Holding sample #{n}", flash)
        self.text(50, 165, 245, 35, f"Advance per tick: {360*f/fs:g}°", theme.WARN, 11)
        self.text(610, 165, 245, 35, f"Equivalent step: {360*apparent/fs:g}°", theme.VIOLET, 11)
        self.note("At each flash the phases coincide modulo 360°. Between flashes, the sampler sees nothing.")

    def draw_sample_identity(self):
        f, other, fs = self.d.get("f", 950), self.d.get("other", 50), self.d.get("rate", 1000)
        sine = self.d.get("sine", False)
        shown = min(8, int(self.progress*8)+1)
        self.text(10, 4, 880, 31, "Two continuous motions → the same recorded numbers at these sample times", theme.TEXT_DIM, 12)
        for row, freq in enumerate((f, other)):
            y = 68+64*row
            self.text(10, y, 170, 44, f"{'sin' if sine else 'cos'} · {freq:g} Hz", theme.WARN if row == 0 else theme.VIOLET, 12)
            for i in range(8):
                x = 190+85*i
                value = sampled_value(freq, fs, i, sine)
                if abs(value) < 1e-9:
                    value = 0
                self.box(x, y, 76, 42, f"{value:+.2f}" if i < shown else "…", i < shown,
                         theme.CYAN if row == 0 else theme.VIOLET)
                if row == 0:
                    self.text(x, 39, 76, 27, f"{1000*i/fs:g} ms", theme.TEXT_DIM, 10)
        self.note(self.d.get("note", "The sampler records values, not the number of turns taken between samples."))

    def draw_tracking(self):
        f = self.d.get("f", 20)
        bands = self.d.get("bands", (100, 20, 50))
        labels = self.d.get("labels", ("DD example", "SEA example", "PEA example"))
        angle = 2*math.pi*self.progress
        for i, (band, label) in enumerate(zip(bands, labels)):
            gain, lag = response_gain_phase(f, band)
            y = 43+57*i
            self.text(8, y-21, 210, 49, f"{label}\nf_bw = {band:g} Hz", theme.TEXT, 11)
            self.line(245, y, 560, y, theme.BORDER, 3)
            desired = 402+145*math.sin(angle)
            actual = 402+145*gain*math.sin(angle+lag)
            self.dot(desired, y-7, 7, theme.WARN)
            self.dot(actual, y+8, 9, theme.CYAN)
            self.line(desired, y-7, actual, y+8, theme.TEXT_DIM, 1)
            self.text(595, y-23, 285, 48, f"Amplitude {gain*100:.1f}%\nLag {abs(math.degrees(lag)):.1f}°", theme.CYAN, 11)
        prefix = f"All loops update at {self.d.get('rate', 1000):g} Hz. " if len(bands) > 1 else "Continuous first-order response. "
        self.note(f"{prefix}Demand: {f:g} Hz. Gold = requested; cyan = actual.")

    def draw_delay_clock(self):
        f, delay_ms = self.d.get("f", 50), self.d.get("delay", 2)
        lag = 2*math.pi*f*delay_ms/1000
        angle = 2*math.pi*self.progress
        self.dial(235, 106, angle, "What is happening NOW", theme.WARN)
        self.dial(655, 106, angle-lag, f"What a {delay_ms:g} ms-old signal says", theme.CYAN)
        self.text(355, 72, 190, 78, f"{math.degrees(lag):g}°\nof phase lost", theme.BAD, 17)
        self.note(f"{f:g} Hz → period {1000/f:g} ms; {delay_ms:g} ms delay occupies {100*f*delay_ms/1000:g}% of one cycle.")

    def draw_filter_gate(self):
        before = self.d.get("before", True)
        names = ("Sensor", "Analog filter", "ADC", "Controller") if before else ("Sensor", "ADC", "Digital filter", "Controller")
        for i, label in enumerate(names):
            x = 35+220*i
            self.box(x, 68, 175, 75, label, True)
            if i < 3:
                self.arrow(x+180, 105, x+212, 105)
        self.text(20, 7, 860, 42, "Filter BEFORE the first sampling step" if before else "After folding, a real 50 Hz signal and an alias share the same data", theme.TEXT_DIM)
        x = 35+830*self.progress
        self.dot(x, 158, 6, theme.CYAN)
        alpha = .12 if before and x > 300 else 1
        self.dot(x, 181, 9*alpha, theme.BAD)
        self.text(40, 145, 180, 32, "wanted slow motion", theme.CYAN, 10)
        self.text(525, 168, 320, 29, "attenuated before aliasing" if before else "aliased component survives", theme.BAD, 10)
        self.note("Schematic attenuation: a practical anti-alias filter needs enough rejection in the unwanted frequency band.")

    def draw_deadline(self):
        duration = self.d.get("duration", .65)
        x0, unit = 130, 450
        self.text(20, 2, 860, 42, "One job is released every millisecond; it must finish before the next deadline.", theme.TEXT_DIM)
        self.line(x0, 138, 840, 138)
        self.line(x0+unit, 52, x0+unit, 179, theme.BAD, 3)
        self.text(x0+unit-95, 174, 190, 28, "deadline: 1 ms", theme.BAD, 11)
        width = unit*duration*self.progress
        self.box(x0, 75, max(2, width), 59, "" if width < 110 else "control job", True,
                 theme.BAD if duration > 1 else theme.CYAN)
        self.text(70, 170, 150, 28, "release: 0 ms", size=11)
        self.note(f"Execution time = {duration:g} ms → {'MISSED deadline' if duration > 1 else f'{1-duration:.2f} ms spare before the next tick'}.")

    def draw_notch_signal(self):
        f = self.d['f']
        response = notch_response(f)
        gain, phase = abs(response), cmath.phase(response)
        self.text(25, 5, 260, 30, f'Input component: {f:g} Hz', theme.WARN, 13)
        self.text(615, 5, 260, 30, f'Output: {100*gain:.1f}% amplitude', theme.CYAN, 13)
        self.box(330, 65, 240, 95, 'NOTCH\ncentre fixed at 18 Hz\nζ_z = 0.015; ζ_p = 0.15', True)
        self.arrow(285, 110, 322, 110, theme.WARN)
        self.arrow(578, 110, 615, 110, theme.CYAN)
        # Shared amplitude and time scales. A moving waveform, not a plot control.
        for left, amplitude, offset, color in ((30, 1, 0, theme.WARN), (620, gain, phase, theme.CYAN)):
            self.line(left, 112, left+250, 112, theme.TEXT_FAINT, 1)
            previous = None
            for i in range(126):
                angle = 2*math.pi*f*(i/125*.125-self.progress*.25)+offset
                point = (left+2*i, 112-48*amplitude*math.sin(angle))
                if previous is not None:
                    self.line(*previous, *point, color, 2)
                previous = point
            self.dot(*previous, 5, color)
        self.text(30, 168, 840, 28, f'Filter gain = {gain:.3f}  ({20*math.log10(gain):.1f} dB) · same vertical scale on both sides', theme.TEXT_DIM, 11)
        self.note('Steady sinusoidal response of the filter only; playback slowed. Plant motion is not shown.')

    def draw_tank(self):
        mode = self.d.get("mode", "fill")
        tau = self.d.get("tau", 1)
        t = self.progress*self.d.get("duration", 4)
        level = math.exp(-t/tau) if mode == "drain" else min(.95, .22*t) if mode == "integrate" else 1-math.exp(-t/tau)
        self.line(270, 35, 270, 183, theme.TEXT_DIM, 4)
        self.line(270, 183, 465, 183, theme.TEXT_DIM, 4)
        self.line(465, 183, 465, 35, theme.TEXT_DIM, 4)
        self.p.fillRect(QRectF(275, 179-135*level, 185, 135*level), QColor(theme.ACCENT_DIM))
        if mode != "drain":
            self.arrow(365, 4, 365, 41, theme.CYAN)
        if mode != "integrate":
            self.arrow(470, 169, 535, 169, theme.WARN)
        self.text(575, 45, 275, 135, f"Time {t:.2f} s\nLevel {100*level:.1f}%\n" + ("No drain → accumulation" if mode == "integrate" else f"Time constant τ = {tau:g} s"), theme.CYAN, 15)
        self.note(self.d.get("equation", "More stored level → more outflow → slower net rise."))

    def draw_spiral(self):
        sigma, omega = self.d.get("sigma", -.45), self.d.get("omega", 3)
        t = self.progress*3
        for k in range(100):
            tt = t*k/99
            r = 60*math.exp(sigma*tt)
            if r < 95:
                self.dot(295+r*math.cos(omega*tt), 111-r*math.sin(omega*tt), 1.5, theme.ACCENT_DIM)
        r = min(94, 60*math.exp(sigma*t))
        self.arrow(295, 111, 295+r*math.cos(omega*t), 111-r*math.sin(omega*t), theme.CYAN, False)
        self.text(450, 38, 390, 120, f"s = {sigma:g} + j{omega:g}\nSize: e^({sigma:g} t)\nRotation: {omega:g} rad/s", theme.CYAN, 16)
        self.note("Real part sets growth / decay; imaginary part sets rotation. The real signal is a projection.")

    def draw_mass(self):
        mode = self.d.get("mode", "free")
        t = self.progress*self.d.get("duration", 4)
        zeta = self.d.get("zeta", .3)
        wn = self.d.get("wn", 3)
        if mode == "step":
            displacement = step_response(t, zeta, wn)
            x = 350+115*displacement
            self.line(465, 48, 465, 193, theme.WARN)
            self.text(414, 6, 110, 35, "target", theme.WARN, 11)
        else:
            x0, v0 = self.d.get("x0", .7), self.d.get("v0", 0)
            wd = wn*math.sqrt(1-zeta*zeta)
            displacement = math.exp(-zeta*wn*t)*(x0*math.cos(wd*t)+(v0+zeta*wn*x0)/wd*math.sin(wd*t))
            x = 400+115*displacement
        self.line(145, 61, 145, 165, theme.TEXT_DIM, 6)
        self.spring(147, 112, x-30)
        self.box(x-30, 82, 60, 60, self.d.get("body_label", "m"), True)
        self.line(150, 159, 590, 159, theme.TEXT_DIM)
        self.text(610, 38, 260, 145, f"t = {t:.2f} s\nnormalized response = {displacement:.2f}\nζ = {zeta:.3g}\nωn = {wn:.3g} rad/s", theme.CYAN, 14)
        self.note(self.d.get("equation", "Spring stores energy; mass carries momentum; damping dissipates energy."))

    def draw_cancellation(self):
        value = math.exp(-2*self.progress*2)
        self.box(30, 75, 180, 75, "Input e^(−2t)", True)
        self.arrow(215, 110, 300, 57)
        self.arrow(215, 110, 300, 166, theme.VIOLET)
        self.box(307, 25, 250, 64, f"P path: +2x\n{2*value:+.3f}", True)
        self.box(307, 134, 250, 64, f"D path: dx/dt\n{-2*value:+.3f}", True, theme.VIOLET)
        self.arrow(566, 56, 668, 109)
        self.arrow(566, 166, 668, 109, theme.VIOLET)
        self.box(680, 75, 185, 75, "Sum = 0", True, theme.GOOD)
        self.note("Ideal PD example: C(s) = s + 2 has a zero at s = −2. Two nonzero paths cancel.")

    def draw_feedback_phase(self):
        degrees = self.d.get("degrees", 135)
        angle = 2*math.pi*self.progress
        self.dial(225, 112, angle, "Injected perturbation", theme.WARN)
        self.dial(675, 112, angle-math.radians(degrees)+math.pi, "After loop + subtraction", theme.CYAN)
        self.text(340, 49, 220, 116, f"|L| = 1\nLoop lag {degrees:g}°\nPM = {180-degrees:g}°", theme.CYAN, 16)
        self.note("At −180° and unit gain, the loop's phase reversal plus feedback subtraction returns the same signal.")
