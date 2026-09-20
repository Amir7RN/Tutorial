"""Quiet, automatically playing concept movies, independent of the page's labs.

All geometry is painted in logical coordinates. No plotting backend or simulation
is run on the animation timer; off-page and scrolled-out movies suspend it.
"""
from __future__ import annotations

import math
import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QAbstractScrollArea, QComboBox, QHBoxLayout, QLabel, QPushButton, QWidget

from .. import theme
from .common import Card, body


class LessonCanvas(QWidget):
    def __init__(self, story, parent=None):
        super().__init__(parent)
        self.story = story
        self.stage = 0
        self.progress = 0.0
        self.setMinimumHeight(246)
        self.setAccessibleName(story.title)
        self.setAccessibleDescription("Animated illustration. The explanation is also written below the image.")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(theme.BG_INPUT))
        scale = min(self.width() / 900, self.height() / 246)
        p.translate((self.width() - 900 * scale) / 2, (self.height() - 246 * scale) / 2)
        p.scale(scale, scale)
        self.p = p
        self.d = self.story.steps[self.stage].data
        getattr(self, "draw_" + self.d.get("scene", self.story.scene))()
        p.end()

    def text(self, x, y, w, h, text, color=theme.TEXT, size=12):
        self.p.setPen(QColor(color))
        self.p.setFont(QFont("Segoe UI", size))
        self.p.drawText(QRectF(x, y, w, h), Qt.AlignCenter | Qt.TextWordWrap, str(text))

    def line(self, x1, y1, x2, y2, color=theme.TEXT_DIM, width=2):
        self.p.setPen(QPen(QColor(color), width))
        self.p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def dot(self, x, y, radius=7, color=theme.CYAN):
        self.p.setPen(Qt.NoPen)
        self.p.setBrush(QColor(color))
        self.p.drawEllipse(QPointF(x, y), radius, radius)

    def box(self, x, y, w, h, label, active=False, color=theme.CYAN):
        self.p.setPen(QPen(QColor(color if active else theme.BORDER), 2))
        self.p.setBrush(QColor(theme.BG_RAISED))
        self.p.drawRoundedRect(QRectF(x, y, w, h), 10, 10)
        self.text(x+6, y+4, w-12, h-8, label, color if active else theme.TEXT_DIM)

    def arrow(self, x1, y1, x2, y2, color=theme.CYAN, moving=True):
        self.line(x1, y1, x2, y2, color)
        a = math.atan2(y2-y1, x2-x1)
        for sign in (-1, 1):
            self.line(x2, y2, x2-9*math.cos(a+sign*.45), y2-9*math.sin(a+sign*.45), color)
        if moving:
            t = self.progress
            self.dot(x1+(x2-x1)*t, y1+(y2-y1)*t, 6, theme.WARN)

    def spring(self, x1, y, x2, color=theme.CYAN):
        pts = [QPointF(x1, y)]
        for i in range(1, 16):
            pts.append(QPointF(x1+(x2-x1)*i/16, y+(8 if i % 2 else -8)))
        pts.append(QPointF(x2, y))
        self.p.setPen(QPen(QColor(color), 2))
        self.p.setBrush(Qt.NoBrush)
        self.p.drawPolyline(QPolygonF(pts))

    def note(self, text):
        self.text(30, 206, 840, 35, text, theme.CYAN, 12)

    def draw_flow(self):
        nodes = self.d.get("nodes", self.story.nodes)
        count = len(nodes)
        width = min(170, 730/count)
        gap = (840-count*width)/max(1, count-1)
        active = self.d.get("active", self.stage % count)
        for i, node in enumerate(nodes):
            x = 30+i*(width+gap)
            self.box(x, 72, width, 78, node, i == active)
            if i == active:
                # The active operation progresses even at the end of a chain.
                self.line(x+12, 143, x+12+(width-24)*self.progress, 143, theme.WARN, 3)
            if i < count-1:
                self.arrow(x+width+4, 111, x+width+gap-4, 111,
                           theme.CYAN if i == active else theme.BORDER, i == active)
        if self.d.get("feedback"):
            self.line(840, 159, 840, 187, theme.VIOLET)
            self.arrow(840, 187, 65, 187, theme.VIOLET)
            self.line(65, 187, 65, 157, theme.VIOLET)
        self.text(25, 8, 850, 40, self.d.get("top", "Follow the moving signal"), theme.TEXT_DIM)
        self.note(self.d.get("equation", ""))

    def draw_joint(self):
        """Two joints make direction, damping, stiffness and estimation visible."""
        t = self.progress * 4
        mode = self.d.get("mode", "damped")
        for i, x in enumerate((235, 660)):
            if mode == "unstable":
                a = min(1.25, .08*math.exp(.7*t)) if i == 0 else .48*math.exp(-t)*math.cos(3*t)
            elif mode == "state":
                a = .45*math.cos(1.4*t) + (-1 if i == 0 else 1)*.28*math.sin(1.4*t)
            elif mode == "observer":
                a = .48*math.sin(1.8*t) + (0 if i == 0 else .7*math.exp(-1.3*t))
            elif mode == "force":
                a = min(.9, .18*t*t) if i == 0 else .48*(1-math.exp(-t))
            elif mode == "nonlinear":
                a = (.2 if i == 0 else 1.2)*math.cos((1.8 if i == 0 else 1.62)*t)
            else:
                damping = self.d.get("damping", .6) if i else self.d.get("left_damping", .05)
                a = .65*math.exp(-damping*t)*math.cos(3*t)
            upright = self.d.get("upright", False)
            y = 175 if upright else 66
            end = (x+105*math.sin(a), y+(-1 if upright else 1)*105*math.cos(a))
            self.line(x, y, x, y+(-108 if upright else 108), theme.BORDER)
            self.line(x-40, y, x+40, y, theme.TEXT_DIM, 5)
            self.line(x, y, *end, theme.CYAN if i else theme.WARN, 9)
            self.dot(x, y, 10, theme.TEXT)
            self.dot(*end, 15, theme.CYAN if i else theme.WARN)
            self.text(x-180, 6, 360, 45, self.d.get("labels", ("Before correction", "With feedback"))[i])
        self.note(self.d.get("equation", ""))

    def draw_actuator(self):
        mode = self.d.get("mode", "sea")
        t = self.progress * 2*math.pi
        fast = self.d.get("fast", False)
        displacement = 28*math.sin(t*(3 if fast else 1))
        motor = displacement*(.08 if fast and mode == "sea" else .85 if mode == "sea" else 1)
        mx, lx = 240+motor, 640+displacement
        self.box(mx-70, 72, 140, 75, "Motor / rotor", True)
        self.box(lx-65, 72, 130, 75, "Load / joint", True, theme.WARN)
        if mode == "sea":
            self.spring(mx+70, 110, lx-65)
            self.text(350, 38, 200, 32, "spring IN SERIES")
        else:
            self.line(mx+70, 110, lx-65, 110, theme.TEXT, 6)
            self.text(355, 72, 200, 28, "rigid force path", theme.TEXT_DIM, 10)
            if mode == "pea":
                self.line(100, 176, 100, 204, theme.TEXT_DIM, 5)
                self.spring(100, 183, lx, theme.GOOD)
                self.line(lx, 183, lx, 149, theme.GOOD)
                self.text(310, 153, 250, 26, "spring IN PARALLEL", theme.GOOD, 10)
        self.arrow(817, 110, lx+70, 110, theme.WARN)
        self.text(725, 40, 155, 45, "Fast impact" if fast else "Slow external push", theme.WARN)
        self.note(self.d.get("equation", ""))

    def draw_gears(self):
        ratio = self.d.get("ratio", 4)
        for cx, r, angle, label in [(295, 36, -self.progress*2*math.pi*ratio, "motor"),
                                     (435, 92, self.progress*2*math.pi, "joint")]:
            self.p.setPen(QPen(QColor(theme.CYAN), 3))
            self.p.setBrush(QColor(theme.BG_RAISED))
            self.p.drawEllipse(QPointF(cx, 110), r, r)
            for k in range(12):
                a = angle + k*math.pi/6
                self.line(cx+(r-8)*math.cos(a), 110+(r-8)*math.sin(a),
                          cx+(r+5)*math.cos(a), 110+(r+5)*math.sin(a), theme.CYAN, 4)
            self.line(cx, 110, cx+(r-10)*math.cos(angle), 110+(r-10)*math.sin(angle), theme.WARN, 3)
            self.text(cx-r, 0, 2*r, 25, label, size=10)
        self.text(570, 35, 285, 130, f"Ratio N = {ratio}:1\nMotor speed: ×{ratio}\nReflected rotor inertia: ×{ratio**2}", theme.WARN, 14)
        self.note("Speed markers are schematic; J reflected = N² J motor.")

    def draw_robot(self):
        biped = self.d.get("biped", False)
        q = math.sin(self.progress*2*math.pi)
        if biped:
            self.line(80, 190, 530, 190, theme.TEXT_DIM, 4)
            self.dot(285, 55, 14)
            self.line(285, 55, 285, 85, theme.CYAN, 8)
            for i, side in enumerate((-1, 1)):
                knee = (285+side*35+q*15, 130)
                foot = (285+side*70+q*25, 183-12*max(0, side*q))
                self.line(285, 85, *knee, theme.CYAN, 9)
                self.line(*knee, *foot, theme.CYAN, 9)
                self.line(foot[0]-12, foot[1], foot[0]+28, foot[1], theme.TEXT, 6)
                for point in [(285, 85), knee, foot]:
                    self.dot(*point, 8, theme.WARN)
            if self.d.get("impact"):
                self.arrow(400, 225-30*self.progress, 400, 175, theme.WARN)
        else:
            pts = [(160, 183), (235, 100), (350+q*35, 90+q*25), (440+q*40, 125+q*25)]
            self.line(110, 193, 205, 193, theme.TEXT_DIM, 6)
            for a, b in zip(pts, pts[1:]):
                self.line(*a, *b, theme.CYAN, 10)
            for pt in pts:
                self.dot(*pt, 10, theme.WARN)
            if self.d.get("contact"):
                self.line(485, 65, 485, 192, theme.VIOLET, 9)
                self.arrow(560, 138, 485, 138, theme.VIOLET)
            if self.d.get("mass"):
                self.box(pts[-1][0]-20, pts[-1][1], 48, 40, "m", True, theme.WARN)
        labels = self.d.get("labels", ("", "", ""))
        for i, label in enumerate(labels):
            self.box(600, 18+i*59, 255, 47, label, i == self.stage % len(labels))
        self.note(self.d.get("equation", ""))

    def draw_scaling(self):
        target = self.d.get("scale", 1)
        start = max(1, target-.5)
        scale = start+(target-start)*self.progress
        for x, s in ((225, 1), (470, scale)):
            h = 62*s
            self.box(x-30*s, 184-h, 60*s, h, f"L ×{s:.2f}", True)
            angle = self.progress*2*math.pi
            self.dot(x+40*s*math.cos(angle), 184-h/2+40*s*math.sin(angle), 5, theme.WARN)
        self.text(635, 24, 230, 150,
                  f"Geometric scaling\nMass: ×{scale**3:.2f}\nRotational inertia: ×{scale**5:.2f}", theme.WARN, 14)
        self.note("Same density and shape: mass ∝ L³; inertia ∝ mass × L² = L⁵.")

    def draw_skin(self):
        compress = .5+.5*math.sin(self.progress*2*math.pi-math.pi/2)
        for i, (label, color) in enumerate((("soft outer layer", theme.CYAN), ("damping", theme.VIOLET), ("sensing", theme.GOOD))):
            self.box(130, 75+i*35+compress*(18-i*6), 340, 32-compress*5, label, True, color)
        self.dot(300, 48+compress*38, 24, theme.WARN)
        self.arrow(300, 7, 300, 34+compress*24, theme.WARN)
        self.box(610, 65, 220, 85, self.d.get("label", "Force spreads\nbefore control reacts"), True)
        self.arrow(482, 148, 600, 107)
        self.note(self.d.get("equation", "Mechanics acts first; sensing and control follow."))

    def draw_lake(self):
        route = self.d.get("route", (0, 4, 8, 9, 13, 14, 15))
        t = self.progress*(len(route)-1)
        k = min(int(t), len(route)-2)
        blend = t-k
        for s in range(16):
            x, y = 170+(s%4)*44, 18+(s//4)*44
            kind = "H" if s in (5, 7, 11, 12) else "G" if s == 15 else "S" if s == 0 else str(s)
            self.box(x, y, 40, 40, kind, s in route[:k+1], theme.GOOD if s == 15 else theme.BAD if kind == "H" else theme.CYAN)
        a, b = route[k:k+2]
        self.dot(190+44*((a%4)*(1-blend)+(b%4)*blend), 38+44*((a//4)*(1-blend)+(b//4)*blend), 9, theme.WARN)
        self.text(420, 24, 410, 50, self.d.get("label", "One sampled episode"), theme.CYAN, 17)
        self.text(420, 88, 410, 100, self.d.get("detail", "Choose an action → move → receive reward"))
        self.note(self.d.get("equation", "H = hole · G = goal · gold dot = agent"))

    def draw_backup(self):
        vals = self.d.get("values", (.2, .6, .4))
        probs = self.d.get("weights", (1/3, 1/3, 1/3))
        mode = self.d.get("reduce", "mean")
        result = max(vals) if mode == "max" else sum(v*p for v, p in zip(vals, probs))
        self.box(50, 83, 175, 66, self.d.get("root", "Backup"), True)
        for i, v in enumerate(vals):
            y = 12+i*63
            participates = v == max(vals) if mode == "max" else probs[i] > 0
            active = self.progress >= i/len(vals) and participates
            self.box(418, y, 145, 49, f"{self.d.get('branch', 'value')} {i+1}: {v:g}", active,
                     theme.GOOD if mode == "max" and v == max(vals) else theme.CYAN)
            self.arrow(412, y+24, 230, 115, theme.CYAN if active else theme.BORDER, active)
            weight = "chosen" if mode == "max" and v == max(vals) else "" if mode == "max" else f"× {probs[i]:.2f}"
            self.text(270, y, 125, 30, weight, theme.WARN, 11)
        self.text(600, 40, 250, 120, f"{'MAX' if mode == 'max' else 'WEIGHTED SUM'}\n{result:.3f}", theme.GOOD, 18)
        self.note(self.d.get("equation", "Average chance outcomes. Choose only between actions."))

    def draw_sweep(self):
        """Actual synchronous VI on the deterministic lake, gamma = .9."""
        from .lesson_stories import deterministic_sweeps
        sweep = self.d.get("sweep", self.stage+1)
        values = deterministic_sweeps()[sweep]
        prev = deterministic_sweeps()[max(0, sweep-1)]
        for s in range(16):
            v = prev[s]+(values[s]-prev[s])*self.progress
            x, y = 165+(s%4)*50, 12+(s//4)*46
            label = "H" if s in (5, 7, 11, 12) else "G" if s == 15 else f"{v:.2f}"
            self.box(x, y, 47, 42, label, v > 0, theme.GOOD)
        self.text(425, 24, 420, 125, f"Sweep {sweep}\nReward reaches one more predecessor\nV(goal) stays 0; entering it pays +1.", theme.CYAN, 14)
        self.note("Fixed example: deterministic lake, γ = 0.9, V₀ = 0. Values animate between completed sweeps.")

    def draw_return(self):
        rewards = self.d.get("rewards", (0, 0, 0, 1))
        gamma = self.d.get("gamma", .9)
        n = len(rewards)
        upto = min(n, int(self.progress*n)+1)
        for i, reward in enumerate(rewards):
            x = 75+i*185
            active = i < upto
            self.box(x, 45, 150, 60, f"r{i+1} = {reward:g}", active)
            self.text(x, 118, 150, 58, f"× {gamma:g}^{i}\n= {reward*gamma**i:.3f}", theme.CYAN if active else theme.TEXT_FAINT)
            if i < n-1:
                self.text(x+154, 120, 25, 35, "+")
        total = sum(r*gamma**i for i, r in enumerate(rewards[:upto]))
        self.note(f"γ = {gamma:g}     Running discounted return = {total:.3f}     (first reward has exponent 0)")

    def draw_samples(self):
        samples = self.d.get("samples", (1, 6, 2, 5, 3, 4))
        n = min(len(samples), int(self.progress*len(samples))+1)
        for i, value in enumerate(samples):
            x = 70+i*min(105, 670/len(samples))
            self.box(x, 60, 75, 65, str(value) if i < n else "…", i < n)
            if i == n-1:
                self.arrow(x+37, 135, 450, 185, theme.WARN)
        avg = sum(samples[:n])/n
        self.text(80, 5, 750, 38, self.d.get("label", "Observed samples, one at a time"), theme.TEXT_DIM)
        self.note(f"{n} samples     total = {sum(samples[:n]):g}     running mean = {avg:.3f}")

    def draw_network(self):
        layers = self.d.get("layers", (3, 4, 3, 2))
        reverse = self.d.get("reverse", False)
        active = min(len(layers)-2, int(self.progress*(len(layers)-1)))
        fraction = (self.progress*(len(layers)-1)) % 1
        if reverse:
            active = len(layers)-2-active
            fraction = 1-fraction
        points = [[(130+i*205, 48+j*135/max(1,n-1)) for j in range(n)] for i,n in enumerate(layers)]
        dropout = self.d.get("dropout", False)
        for i in range(len(layers)-1):
            for j, a in enumerate(points[i]):
                for k, b in enumerate(points[i+1]):
                    if dropout and ((i == 1 and j%2) or (i+1 == 1 and k%2)):
                        continue
                    self.line(*a, *b, theme.VIOLET if reverse and i == active else theme.CYAN if i == active else theme.BORDER, 1.5)
                    if i == active:
                        self.dot(a[0]+fraction*(b[0]-a[0]), a[1]+fraction*(b[1]-a[1]), 3, theme.WARN)
        for i, layer in enumerate(points):
            for j, pt in enumerate(layer):
                self.dot(*pt, 13, theme.BORDER if dropout and i == 1 and j%2 else theme.VIOLET if reverse else theme.CYAN)
        labels = self.d.get("labels", ("input", "hidden", "hidden", "output"))
        for i, label in enumerate(labels):
            self.text(65+i*205, 4, 130, 30, label, theme.TEXT_DIM, 11)
        self.note(self.d.get("equation", "Multiply along each path; add contributions where paths meet."))

    def draw_neuron(self):
        inputs, weights, bias = (2, -1, .5), (.3, -.4, .2), .1
        completed = min(3, int(self.progress*4))
        total = bias + sum(inputs[i]*weights[i] for i in range(completed))
        for i, (x, w) in enumerate(zip(inputs, weights)):
            y = 12+61*i
            self.box(40, y, 145, 46, f"x{i+1} = {x:g}", i < completed)
            self.text(195, y, 160, 42, f"× {w:g} = {x*w:g}", theme.WARN)
            self.arrow(350, y+23, 445, 106, theme.CYAN if i < completed else theme.BORDER, i < completed)
        self.box(450, 64, 175, 80, f"Sum + bias {bias}\nz = {total:.2f}", True)
        self.arrow(635, 104, 705, 104)
        self.box(715, 64, 160, 80, f"tanh(z)\na = {math.tanh(total):.3f}", True)
        self.note("2×0.3 + (−1)×(−0.4) + 0.5×0.2 + 0.1 = 1.2; tanh(1.2) ≈ 0.834")

    def draw_activation(self):
        z = self.d.get("z", 0)
        relu = self.d.get("relu", False)
        name = "ReLU" if relu else "tanh"
        activation = (lambda v: max(0, v)) if relu else math.tanh
        slope = (1.0 if z > 0 else 0.0) if relu else 1-math.tanh(z)**2
        delta = .1*math.sin(self.progress*2*math.pi)
        change = activation(z+delta)-activation(z)
        self.box(40, 65, 210, 80, f"Input z = {z:g}\nsmall change: {delta:+.3f}", True)
        self.arrow(260, 106, 345, 106)
        self.box(355, 65, 180, 80, f"{name}\nlocal slope: {slope:.3f}", True)
        self.arrow(545, 106, 630, 106, theme.BORDER if slope == 0 else theme.CYAN, slope > 0)
        self.box(640, 65, 215, 80, f"Output: {activation(z+delta):.3f}\nchange: {change:+.4f}", slope > 0)
        self.text(45, 9, 810, 35, "Watch how much of a small input change reaches the output", theme.TEXT_DIM)
        self.note(f"Backward sensitivity is multiplied by {slope:.3f} at this operating point.")

    def draw_phase(self):
        z, pole = self.d.get("z", 1), self.d.get("pole", 9)
        omega = math.sqrt(z*pole)
        h = (pole/z)*(complex(z, omega)/complex(pole, omega))
        phase = math.atan2(h.imag, h.real)
        for cx, offset, label, color in ((230, 0, "Input", theme.WARN),
                                         (590, phase, "Output", theme.CYAN)):
            self.p.setPen(QPen(QColor(theme.BORDER), 2))
            self.p.setBrush(Qt.NoBrush)
            self.p.drawEllipse(QPointF(cx, 106), 72, 72)
            a = self.progress*2*math.pi + offset
            self.arrow(cx, 106, cx+68*math.cos(a), 106-68*math.sin(a), color, False)
            self.text(cx-100, 0, 200, 30, label, color)
        self.text(335, 65, 150, 90, f"{'LEAD' if phase > 0 else 'LAG'}\n{math.degrees(phase):+.1f}°", theme.CYAN, 17)
        self.note(f"C(s) = ({pole:g}/{z:g})(s+{z:g})/(s+{pole:g}); ω = {omega:g} rad/s; gain = {abs(h):.2f}")

    def draw_buffer(self):
        n = 8
        index = min(15, int(self.progress*16))
        for i in range(n):
            a = i*2*math.pi/n-math.pi/2
            x,y = 275+95*math.cos(a), 112+73*math.sin(a)
            self.box(x-30, y-18, 60, 36, str(i), i == index%n)
        self.text(204, 83, 143, 52, "replay\nwrite → wrap", theme.CYAN)
        self.box(540, 50, 280, 80, self.d.get("label", "Sample a mixed batch"), True)
        self.arrow(400, 100, 528, 90, theme.WARN)
        self.note(self.d.get("equation", "New experience replaces the oldest once the ring is full."))

    def draw_clocks(self):
        for row, (label, count, color) in enumerate((("Control · 1 kHz", 40, theme.CYAN), ("Learner · 20 Hz", 1, theme.VIOLET))):
            y = 50+row*92
            self.text(15, y-10, 195, 50, label, color)
            for k in range(count):
                x = 235+k*14
                self.box(x, y, 9 if count > 1 else 140, 30, "" if count > 1 else "batch update", True, color)
            self.dot(235+560*self.progress, y+45, 5, theme.WARN)
        self.note(self.d.get("equation", "Illustrative 40 ms window: the fast loop never waits for training."))


class LessonAnimation(Card):
    """A movie with readable held captions and explicit playback controls."""
    SECONDS_PER_STEP = 6.0

    def __init__(self, story, parent=None):
        super().__init__("Watch the idea · " + story.title, parent)
        self.story = story
        self.playing = True
        self.position = 0.0
        self.rate = 1.0
        self._scroll = None
        self._last = time.monotonic()
        self._shown_stage = -1
        self.add(body("A fixed, illustrative animation • plays automatically • separate from the controls below", dim=True))
        self.canvas = self.add(LessonCanvas(story))
        self.step_label = self.add(QLabel())
        self.step_label.setWordWrap(True)
        self.step_label.setStyleSheet(f"color:{theme.CYAN}; font-weight:700; background:transparent;")
        self.caption = self.add(body(""))
        self.caption.setMinimumHeight(46)
        row = QHBoxLayout()
        self.play_button = QPushButton("Pause animation")
        self.play_button.clicked.connect(self.toggle)
        row.addWidget(self.play_button)
        for label, callback in (("Replay", self.replay), ("Previous scene", lambda: self.step(-1)), ("Next scene", lambda: self.step(1))):
            button = QPushButton(label)
            button.clicked.connect(callback)
            row.addWidget(button)
        speed = QComboBox()
        speed.setAccessibleName("Animation playback speed")
        for label, value in (("½ speed", .5), ("Normal speed", 1.0), ("1½ speed", 1.5)):
            speed.addItem(label, value)
        speed.setCurrentIndex(1)
        speed.currentIndexChanged.connect(lambda: setattr(self, "rate", speed.currentData()))
        row.addWidget(speed)
        row.addStretch()
        self.add_layout(row)
        self.timer = QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self.tick)
        self.render_position()

    def render_position(self):
        count = len(self.story.steps)
        phase = self.position / self.SECONDS_PER_STEP
        stage = min(count-1, int(phase) % count)
        self.canvas.stage = stage
        # Hold the completed image for the last second, so it can be read.
        self.canvas.progress = min(.999999, (phase % 1)*1.2)
        if stage != self._shown_stage:
            self._shown_stage = stage
            step = self.story.steps[stage]
            self.step_label.setText(f"{stage+1} / {count} · {step.title}")
            self.caption.setText(step.caption)
            self.canvas.setAccessibleDescription(step.caption)
        self.canvas.update()

    def tick(self):
        now = time.monotonic()
        self.position = (self.position + min(.15, now-self._last)*self.rate) % (self.SECONDS_PER_STEP*len(self.story.steps))
        self._last = now
        self.render_position()

    def toggle(self):
        self.playing = not self.playing
        self.play_button.setText("Pause animation" if self.playing else "Play animation")
        self.update_visibility()

    def replay(self):
        self.position = 0
        self.playing = True
        self.play_button.setText("Pause animation")
        self.render_position()
        self.update_visibility()

    def step(self, direction):
        self.playing = False
        self.play_button.setText("Play animation")
        index = (self.canvas.stage+direction) % len(self.story.steps)
        self.position = index*self.SECONDS_PER_STEP
        self.render_position()
        self.update_visibility()

    def showEvent(self, event):
        super().showEvent(event)
        if self._scroll is None:
            parent = self.parentWidget()
            while parent is not None:
                if isinstance(parent, QAbstractScrollArea):
                    self._scroll = parent
                    parent.verticalScrollBar().valueChanged.connect(self.update_visibility)
                    break
                parent = parent.parentWidget()
        QTimer.singleShot(0, self.update_visibility)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self.update_visibility)

    def update_visibility(self, *_):
        visible = self.isVisible()
        if visible and self._scroll is not None:
            viewport = self._scroll.viewport()
            top = self.canvas.mapTo(viewport, self.canvas.rect().topLeft())
            visible = viewport.rect().intersects(self.canvas.rect().translated(top))
        if visible and self.playing:
            if not self.timer.isActive():
                self._last = time.monotonic()
                self.timer.start()
        else:
            self.timer.stop()
