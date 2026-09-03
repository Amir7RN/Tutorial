"""
Neural network fundamentals -- the six pages the deep-RL block stands on.

    73  What a Neuron Computes   weight = gain, bias = offset, activation =
                                 saturation; and why stacking linear layers
                                 buys nothing at all
    74  Activations and Slopes   every activation with its DERIVATIVE beside
                                 it, because the derivative is the thing
                                 backprop actually multiplies by
    75  Forward Propagation      the signal travelling through weights and
                                 neurons, animated, with the two cached
                                 quantities the backward pass will need
    76  Backpropagation          multiply along each path, SUM across paths;
                                 seeded by the loss, checked against finite
                                 differences
    77  Losses, Softmax, Argmax  what a loss is for, why softmax pairs with
                                 cross-entropy, why argmax has no gradient
                                 and what RL does instead
    78  Regularisation & Norm.   L2, dropout, batch norm, layer norm, init,
                                 clipping -- and which of them are actively
                                 dangerous inside an RL loop

Why these pages sit HERE, between Adam and "Tables Run Out": everything
before this point in the RL half is a table, and a table has no gradient. The
moment the table dies, a network takes its place, and from then on every
sentence in the tutor -- "the critic is fitted to y", "the actor follows
dQ/da uphill" -- is a sentence about weights, slopes and a chain rule. This
block is that vocabulary, built on the SAME numpy MLP that the DDPG pages
actually train, so nothing here is a parallel toy.
"""

from __future__ import annotations

import math

import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QPushButton

from rlcore.deeprl import Dense, MLP
from .. import theme
from ..widgets import (
    Card,
    CodePane,
    MplCanvas,
    Stat,
    body,
    callout,
    get_source,
    hline,
    labelled,
    math_label,
    stat_row,
    title,
)
from .base import Page
from .deeprl import _table as _deeprl_table
from .motors import slider, slider_row

SECTION = "Neural Networks"


def _table(headers, rows, col0=150, colw=250, height=None):
    """
    The deep-RL page table, resized to fit its contents.

    `_table` in deeprl.py guesses a height from the row count, which is fine
    for short cells and cuts long ones off behind a scrollbar. These pages
    have several tables whose whole point is that every row is visible at
    once, so the height is measured after the column widths are set rather
    than estimated before. `height` is accepted and ignored, so call sites
    read the same as everywhere else in the tutor.
    """
    t = _deeprl_table(headers, rows, col0=col0, colw=colw, height=height)
    t.resizeRowsToContents()
    h = (t.horizontalHeader().height()
         + sum(t.rowHeight(r) for r in range(t.rowCount())) + 8)
    t.setMinimumHeight(h)
    t.setMaximumHeight(h)
    return t


def _code(src: str) -> CodePane:
    """A CodePane sized to its own contents, so no pane leaves a dead gap."""
    pane = CodePane(src)
    pane.sizeHintLine(len(src.strip().splitlines()) + 1)
    return pane



# ==========================================================================
# Shared drawing helper -- a small network as nodes and edges
# ==========================================================================

def _blend(c0: str, c1: str, t: float):
    """Linear blend between two hex colours, t in [0, 1]."""
    from matplotlib.colors import to_rgb
    a, b = np.array(to_rgb(c0)), np.array(to_rgb(c1))
    t = float(np.clip(t, 0.0, 1.0))
    return tuple(a + (b - a) * t)


def _val_color(v: float, span: float = 1.0):
    """Positive activations glow green, negative red, zero is the panel."""
    t = min(1.0, abs(v) / max(1e-9, span))
    return _blend(theme.BG_RAISED, theme.GOOD if v >= 0 else theme.BAD,
                  0.25 + 0.75 * t)


class NetCanvas(MplCanvas):
    """
    A fully connected network drawn as nodes and edges, with a travelling
    signal.

    One artist for all the edges (a LineCollection) rather than one line per
    edge -- at 12 frames a second the difference between the two is the
    difference between an animation and a slideshow.
    """

    def __init__(self, sizes, parent=None, width=7.6, height=3.1,
                 labels=None):
        super().__init__(parent, width=width, height=height)
        self.sizes = list(sizes)
        self.labels = labels or []
        self.ax.axis("off")
        self.ax.grid(False)
        self.fig.subplots_adjust(left=0.01, right=0.99, top=0.94, bottom=0.02)
        self._pos = []
        xs = np.linspace(0.75, 7.25, len(self.sizes))
        for x, n in zip(xs, self.sizes):
            ys = np.linspace(0.0, 1.0, n + 2)[1:-1] * 2.05 + 0.20
            self._pos.append([(float(x), float(y)) for y in ys])

    # ------------------------------------------------------------------
    def render(self, Ws, acts=None, wave=None, back=False, node_span=1.0,
               edge_note=None, title_text=None):
        """
        Ws        list of weight matrices, one per layer gap
        acts      list of 1-D arrays, one per layer of nodes (may be None)
        wave      float in [0, len(Ws)] -- where the travelling signal is
        back      True draws the wave right-to-left and colours it amber
        """
        ax = self.ax
        ax.clear()
        ax.axis("off")
        ax.grid(False)
        ax.set_xlim(0, 8)
        ax.set_ylim(0, 2.5)

        n_gap = len(Ws)
        k_act = None if wave is None else int(min(n_gap - 1e-9, max(0.0, wave)))
        frac = 0.0 if wave is None else float(wave) - (k_act or 0)

        segs, cols, lws = [], [], []
        for k, W in enumerate(Ws):
            wmax = max(1e-9, float(np.abs(W).max()))
            if wave is None:
                bright = 1.0
            elif k < (k_act or 0):
                bright = 1.0 if not back else 0.35
            elif k == k_act:
                bright = 1.0
            else:
                bright = 0.35 if not back else 1.0
            for i, (x0, y0) in enumerate(self._pos[k]):
                for j, (x1, y1) in enumerate(self._pos[k + 1]):
                    w = float(W[i, j])
                    mag = abs(w) / wmax
                    segs.append([(x0, y0), (x1, y1)])
                    base = theme.GOOD if w >= 0 else theme.BAD
                    cols.append((*_blend(theme.BG_RAISED, base,
                                         0.35 + 0.65 * mag),
                                 (0.20 + 0.72 * mag) * bright))
                    lws.append(0.5 + 2.1 * mag)
        ax.add_collection(LineCollection(segs, colors=cols, linewidths=lws,
                                         zorder=1))

        # the travelling signal: a dot per edge of the layer being computed
        if wave is not None and k_act is not None:
            f = 1.0 - frac if back else frac
            xs, ys = [], []
            for (x0, y0) in self._pos[k_act]:
                for (x1, y1) in self._pos[k_act + 1]:
                    xs.append(x0 + (x1 - x0) * f)
                    ys.append(y0 + (y1 - y0) * f)
            ax.scatter(xs, ys, s=26,
                       color=theme.WARN if back else theme.CYAN,
                       zorder=6, edgecolors="none")

        # nodes
        for k, layer in enumerate(self._pos):
            for i, (x, y) in enumerate(layer):
                v = 0.0
                if acts is not None and k < len(acts) and acts[k] is not None:
                    v = float(np.ravel(acts[k])[i])
                fc = _val_color(v, node_span)
                ax.add_patch(Circle((x, y), 0.155, facecolor=fc,
                                    edgecolor=theme.BORDER, lw=1.1, zorder=5))
                if acts is not None and k < len(acts) and acts[k] is not None:
                    ax.text(x, y, f"{v:+.2f}", ha="center", va="center",
                            fontsize=6.2, color=theme.TEXT, zorder=7)

        for k, lab in enumerate(self.labels[:len(self._pos)]):
            ax.text(self._pos[k][0][0], 2.42, lab, ha="center", va="center",
                    fontsize=7.4, color=theme.TEXT_DIM)
        if edge_note:
            ax.text(4.0, 0.03, edge_note, ha="center", va="bottom",
                    fontsize=7.0, color=theme.TEXT_FAINT)
        if title_text:
            ax.set_title(title_text, fontsize=9)
        self.refresh(layout=False)


# ==========================================================================
# PAGE -- what a neuron computes
# ==========================================================================

class NeuronPage(Page):
    TITLE = "What a Neuron Computes"
    SUBTITLE = ("A weight is a gain, a bias is an offset, an activation is a "
                "saturation. You have already tuned all three on a real "
                "actuator — this page only renames them.")
    SECTION = SECTION
    NOTES = "neural nets"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>One neuron is one line of arithmetic.</b> Take the inputs, "
            "multiply each by its own number, add them up, add one more "
            "number, and squash the result through a fixed curve. That is "
            "the whole of it — there is nothing else inside. Everything "
            "impressive a network does comes from stacking that operation, "
            "not from any single unit being clever.", "key"))

        # ---- the unit --------------------------------------------------
        u = Card("the unit, with every symbol named")
        u.add(math_label(r"z \;=\; w_1x_1 + w_2x_2 + w_3x_3 + b "
                         r"\;=\; \mathbf{w}\cdot\mathbf{x} + b, "
                         r"\qquad y \;=\; \sigma(z)", 17))
        u.add(body(
            "&nbsp;&nbsp;• <b>x</b> — what the neuron is looking at. In a "
            "critic, part of it is a joint angle and part of it is a "
            "torque.<br>"
            "&nbsp;&nbsp;• <b>w</b> — one <b>gain</b> per input. Its sign says "
            "\"more of this input pushes me up / down\"; its size says how "
            "hard. This is the same object as a proportional gain, and it is "
            "learned rather than dialled in.<br>"
            "&nbsp;&nbsp;• <b>b</b> — the <b>offset</b>. It decides where the "
            "neuron's threshold sits: with b = −2 the unit stays quiet until "
            "the weighted sum climbs past 2.<br>"
            "&nbsp;&nbsp;• <b>z</b> — the <b>pre-activation</b>. Worth its own "
            "name because the backward pass needs it, not y.<br>"
            "&nbsp;&nbsp;• <b>σ</b> — the <b>activation</b>. A fixed, "
            "hand-chosen curve with no parameters. The next page is entirely "
            "about which one and why."))
        u.add(body(
            "Drag anything below. The bars show each input's contribution "
            "w<sub>i</sub>x<sub>i</sub> — that decomposition is literally all "
            "the neuron did before the squash.", dim=True))

        self.n_x = [slider(-200, 200, v) for v in (120, -60, 80)]
        self.n_w = [slider(-200, 200, v) for v in (90, 140, -70)]
        self.n_b = slider(-200, 200, -30)
        self.n_lbl = [QLabel() for _ in range(7)]
        for i in range(3):
            u.add_layout(slider_row(f"input x{i+1}", self.n_x[i],
                                    self.n_lbl[i]))
        for i in range(3):
            u.add_layout(slider_row(f"weight w{i+1}", self.n_w[i],
                                    self.n_lbl[3 + i]))
        u.add_layout(slider_row("bias b", self.n_b, self.n_lbl[6]))
        self.n_act = QComboBox()
        for k in ("tanh", "relu", "sigmoid", "linear"):
            self.n_act.addItem(k)
        u.add_layout(labelled("Activation", self.n_act, width=90))
        self.st_z = Stat("pre-activation z", "--", theme.ACCENT)
        self.st_y = Stat("output y", "--", theme.GOOD)
        self.st_sl = Stat("local slope σ′(z)", "--", theme.WARN)
        u.add_layout(stat_row(self.st_z, self.st_y, self.st_sl))
        self.cN = MplCanvas(width=7.6, height=2.7, ncols=2)
        u.add(self.cN)
        self.tN = body("", dim=True)
        u.add(self.tN)
        self.add(u)
        for s in self.n_x + self.n_w + [self.n_b]:
            s.valueChanged.connect(self._redraw_unit)
        self.n_act.currentIndexChanged.connect(self._redraw_unit)
        self._redraw_unit()

        u2 = Card("the same picture, in control language")
        u2.add(_table(
            ["Neural net", "Control", "What it does"],
            [("weight  w", "gain  K",
              "scales one input. Learned by gradient descent instead of "
              "chosen from a root locus."),
             ("bias  b", "offset / setpoint bias",
              "shifts the operating point. Without it every neuron would be "
              "forced through the origin."),
             ("activation  σ", "saturation / limiter",
              "a fixed nonlinearity. tanh is a soft limiter; ReLU is a "
              "half-wave rectifier."),
             ("layer", "a bank of parallel gain blocks",
              "same inputs, different gains, computed in one matrix "
              "multiply."),
             ("depth", "cascaded blocks",
              "each layer's outputs are the next one's inputs — but with a "
              "limiter in between, which is the entire point.")],
            col0=130, colw=290, height=240))
        self.add(u2)

        # ---- a layer is a matrix ---------------------------------------
        self.add(hline())
        self.add(title("A layer is one matrix multiply; depth is composition"))

        ly = Card("stack the neurons side by side and the sum becomes a "
                  "product")
        ly.add(body(
            "Put n neurons side by side, all looking at the same input "
            "vector. Each has its own weight vector, so the whole layer's "
            "weights are a <b>matrix</b> — one column per neuron — and the "
            "layer's output is one matrix product plus one vector:"))
        ly.add(math_label(r"\mathbf{z} = \mathbf{x}W + \mathbf{b}, \qquad "
                          r"\mathbf{y} = \sigma(\mathbf{z}), \qquad "
                          r"W \in \mathbb{R}^{n_{in} \times n_{out}}", 17))
        ly.add(body(
            "This is the shape convention the tutor's own code uses, and it "
            "is worth reading once: <b>x is a row</b>, so a batch of 64 "
            "samples is a 64×n<sub>in</sub> array and one matrix multiply "
            "processes all 64 at once. Nothing about the maths changes; the "
            "batch dimension just rides along in front. Every gradient "
            "formula on the backprop page has the same shape for a batch of "
            "1 and a batch of 256."))
        ly.add(_code(get_source(Dense.forward)))
        ly.add(body(
            "That is the real forward pass out of <code>rlcore/deeprl.py</code> "
            "— the one the DDPG pages run. <code>self._x</code> and "
            "<code>self._z</code> are cached on the way through because the "
            "backward pass cannot be computed without them; page 76 spends a "
            "card on exactly why those two and nothing else.", dim=True))
        self.add(ly)

        # ---- why a nonlinearity ----------------------------------------
        nl = Card("without an activation, depth is a lie")
        nl.add(body(
            "Delete the activation and ask what a two-layer network computes:"))
        nl.add(math_label(r"\mathbf{y} = (\mathbf{x}W_1 + \mathbf{b}_1)W_2 "
                          r"+ \mathbf{b}_2 = \mathbf{x}\underbrace{W_1W_2}"
                          r"_{\textstyle W_{\!*}} + "
                          r"\underbrace{\mathbf{b}_1W_2 + \mathbf{b}_2}"
                          r"_{\textstyle \mathbf{b}_{\!*}}", 17))
        nl.add(body(
            "<b>A single layer with weights W<sub>*</sub> and bias "
            "b<sub>*</sub> computes exactly the same function.</b> Fifty "
            "linear layers collapse to one. Depth without a nonlinearity buys "
            "you a slower way to multiply two matrices and nothing else — "
            "the model can only ever draw straight lines, which for a critic "
            "means it could never represent a curved Q surface, and for an "
            "actor means μ(s) could only ever be a linear state feedback. "
            "Which, note, is precisely the <b>u = −Kx</b> of the state "
            "feedback page. A linear network <i>is</i> a gain matrix; the "
            "activation is the only thing that lets it be more."))
        nl.add(body(
            "The other direction is the useful one: with a nonlinearity you "
            "can build a curve out of shifted, scaled copies of one shape. "
            "Three tanh units, three sliders, and the sum of them below — "
            "that is a one-hidden-layer network approximating a function, "
            "which is the whole content of the universal-approximation "
            "result, minus the epsilons.", dim=True))
        self.a_amp = [slider(-150, 150, v) for v in (110, -90, 70)]
        self.a_shift = [slider(-200, 200, v) for v in (-90, 10, 110)]
        self.a_lbl = [QLabel() for _ in range(6)]
        for i in range(3):
            nl.add_layout(slider_row(f"unit {i+1} output weight",
                                     self.a_amp[i], self.a_lbl[i]))
        for i in range(3):
            nl.add_layout(slider_row(f"unit {i+1} bias (where it bends)",
                                     self.a_shift[i], self.a_lbl[3 + i]))
        self.cA = MplCanvas(width=7.6, height=2.6, ncols=2)
        nl.add(self.cA)
        nl.add(body(
            "<b>Left:</b> the three tanh units on their own. <b>Right:</b> "
            "their weighted sum, which is what the output neuron sees. Set "
            "every output weight the same and you get one big smooth step; "
            "spread the biases out and the sum grows a bend per unit. Widen "
            "the layer and you can bend it anywhere.", dim=True))
        self.add(nl)
        for s in self.a_amp + self.a_shift:
            s.valueChanged.connect(self._redraw_approx)
        self._redraw_approx()

        # ---- the two networks this tutor actually trains ----------------
        self.add(hline())
        self.add(title("The two networks the DDPG pages actually build"))

        sz = Card("count the parameters, once, so the numbers stop being "
                  "abstract")
        sz.add(_table(
            ["Network", "Shape", "Weights + biases", "Output activation"],
            [("actor  μ(s)", "5 → 64 → 64 → 2",
              "5·64+64 + 64·64+64 + 64·2+2  =  4 674",
              "tanh — the action is bounded, and the bound is a hardware "
              "fact, not a preference"),
             ("critic  Q(s,a)", "7 → 64 → 64 → 1",
              "7·64+64 + 64·64+64 + 64·1+1  =  4 737",
              "linear — a value is a sum of discounted rewards and has no "
              "reason to be in [−1, 1]"),
             ("both targets", "identical copies",
              "another 9 411, updated by a crawl, never by a gradient",
              "same as their live twins")],
            col0=120, colw=250, height=210))
        sz.add(body(
            "Under ten thousand numbers, total. Hold that against the 259 "
            "million cells the table needed for the same problem two pages "
            "on — and remember that the reason the network wins is not the "
            "storage, it is that those 4 737 numbers describe a <b>smooth "
            "function</b>, so a sample collected at one gait cycle says "
            "something about every gait cycle near it.", dim=True))
        self.add(sz)

        self.add(callout(
            "<b>Carry forward.</b> Neuron = weighted sum + offset + fixed "
            "squash. Layer = matrix multiply. Depth is only worth having "
            "because of the squash between the layers. The next page is about "
            "that squash, and specifically about its <b>slope</b>, because "
            "the slope is the only part of it that backpropagation ever "
            "touches.", "good"))
        self.finish()

    # ------------------------------------------------------------------
    @staticmethod
    def _apply(kind, z):
        if kind == "tanh":
            return np.tanh(z), 1.0 - np.tanh(z) ** 2
        if kind == "relu":
            return np.maximum(z, 0.0), (z > 0).astype(float)
        if kind == "sigmoid":
            s = 1.0 / (1.0 + np.exp(-z))
            return s, s * (1 - s)
        return z, np.ones_like(z)

    def _redraw_unit(self):
        xs = [s.value() / 100.0 for s in self.n_x]
        ws = [s.value() / 100.0 for s in self.n_w]
        b = self.n_b.value() / 100.0
        for i in range(3):
            self.n_lbl[i].setText(f"{xs[i]:+.2f}")
            self.n_lbl[3 + i].setText(f"{ws[i]:+.2f}")
        self.n_lbl[6].setText(f"{b:+.2f}")

        kind = self.n_act.currentText()
        parts = [w * x for w, x in zip(ws, xs)]
        z = sum(parts) + b
        y, sl = self._apply(kind, np.array([z]))
        y, sl = float(y[0]), float(sl[0])
        self.st_z.set(f"{z:+.3f}")
        self.st_y.set(f"{y:+.3f}")
        self.st_sl.set(f"{sl:.3f}")
        self.st_sl.set_color(theme.BAD if sl < 0.05 else theme.WARN)

        if sl < 0.05:
            self.tN.setText(
                f"<b>Slope {sl:.3f} — this neuron is effectively "
                f"disconnected.</b> Whatever blame arrives here on the "
                "backward pass gets multiplied by that number and all but "
                "vanishes, so none of its weights will move. For tanh and "
                "sigmoid this is <i>saturation</i> (|z| too large); for ReLU "
                "it is a <i>dead unit</i> (z below zero). Either way the fix "
                "is the same: keep z near the middle, which is what "
                "initialisation and normalisation on page 85 are for.")
        else:
            self.tN.setText(
                f"<b>z = {z:+.3f} → y = {y:+.3f}, local slope {sl:.3f}.</b> "
                "The bars are the three products w<sub>i</sub>x<sub>i</sub>; "
                "the bias shifts the whole stack. Notice that a large weight "
                "on a small input and a small weight on a large input are "
                "indistinguishable to the neuron — only the product reaches "
                "it. That is why input scaling matters, and why the state "
                "vector fed to a critic is normalised before it is fed.")

        c = self.cN
        c.clear()
        a1, a2 = c.axes
        cols = [theme.GOOD if p >= 0 else theme.BAD for p in parts] + [
            theme.ACCENT]
        a1.bar(["w₁x₁", "w₂x₂", "w₃x₃", "b"], parts + [b], color=cols)
        a1.axhline(0, color=theme.BORDER, lw=1.0)
        a1.scatter([3.6], [z], s=0)
        a1.set_title(f"contributions, summing to z = {z:+.2f}", fontsize=9)
        a1.set_ylabel("contribution")

        zs = np.linspace(-4, 4, 400)
        ys, _ = self._apply(kind, zs)
        a2.plot(zs, ys, color=theme.ACCENT, lw=2.0)
        a2.axvline(z, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a2.scatter([z], [y], s=55, color=theme.GOOD, zorder=5)
        if abs(z) < 4:
            a2.plot(zs, y + sl * (zs - z), color=theme.WARN, lw=1.1, ls=":")
        a2.set_ylim(min(-1.4, float(ys.min()) - 0.3),
                    max(1.4, float(ys.max()) + 0.3))
        a2.set_xlabel("z")
        a2.set_ylabel("y")
        a2.set_title(f"{kind}, and its slope here (dotted)", fontsize=9)
        c.refresh()

    def _redraw_approx(self):
        amps = [s.value() / 100.0 for s in self.a_amp]
        shifts = [s.value() / 100.0 for s in self.a_shift]
        for i in range(3):
            self.a_lbl[i].setText(f"{amps[i]:+.2f}")
            self.a_lbl[3 + i].setText(f"{shifts[i]:+.2f}")
        xs = np.linspace(-3, 3, 400)
        units = [np.tanh(2.2 * (xs - sh)) for sh in shifts]
        total = sum(a * u for a, u in zip(amps, units))

        c = self.cA
        c.clear()
        a1, a2 = c.axes
        for i, (u, col) in enumerate(zip(units, (theme.ACCENT, theme.VIOLET,
                                                 theme.CYAN))):
            a1.plot(xs, u, color=col, lw=1.7, label=f"tanh unit {i+1}")
        a1.set_title("three hidden units", fontsize=9)
        a1.set_xlabel("x")
        c.legend(a1, loc="upper left")
        a2.plot(xs, total, color=theme.GOOD, lw=2.4)
        a2.axhline(0, color=theme.BORDER, lw=1.0)
        a2.set_title("their weighted sum — the network's output", fontsize=9)
        a2.set_xlabel("x")
        c.refresh()


# ==========================================================================
# PAGE -- activations and their derivatives
# ==========================================================================

_ACTS = ("sigmoid", "tanh", "relu", "leaky relu", "linear")


def _act_pair(kind, z):
    """Return (value, derivative) for a whole array."""
    z = np.asarray(z, dtype=float)
    if kind == "sigmoid":
        s = 1.0 / (1.0 + np.exp(-z))
        return s, s * (1 - s)
    if kind == "tanh":
        t = np.tanh(z)
        return t, 1.0 - t ** 2
    if kind == "relu":
        return np.maximum(z, 0.0), (z > 0).astype(float)
    if kind == "leaky relu":
        return np.where(z > 0, z, 0.01 * z), np.where(z > 0, 1.0, 0.01)
    return z, np.ones_like(z)


class ActivationPage(Page):
    TITLE = "Activations and Their Slopes"
    SUBTITLE = ("Backprop never uses the activation. It uses the "
                "activation's DERIVATIVE — so the curve you should be looking "
                "at is the one underneath.")
    SECTION = SECTION
    NOTES = "neural nets"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>Pick an activation by its derivative, not by its shape.</b> "
            "The forward pass evaluates σ(z) once. The backward pass "
            "multiplies by σ′(z) at every layer it passes through, so a "
            "derivative that is usually small makes a deep network untrainable "
            "and a derivative that is exactly zero makes a unit permanently "
            "dead. Every choice below is a statement about that multiplier.",
            "key"))

        # ---- the gallery -----------------------------------------------
        g = Card("every activation with its derivative directly beneath it")
        self.cG = MplCanvas(width=7.8, height=3.6, nrows=2, ncols=5)
        g.add(self.cG)
        g.add(body(
            "<b>Top row: σ(z). Bottom row: σ′(z), on a shared 0–1.1 axis.</b> "
            "Read the bottom row across and the whole design space is "
            "visible in one look — sigmoid never exceeds 0.25 anywhere, tanh "
            "reaches 1 but only in a narrow band around zero, and ReLU is "
            "either exactly 1 or exactly 0 with nothing in between.",
            dim=True))
        self.add(g)
        self._draw_gallery()

        t = Card("what each one is actually for")
        t.add(_table(
            ["Activation", "Range", "Derivative", "Use it when", "Watch out"],
            [("sigmoid  1/(1+e⁻ᶻ)", "(0, 1)",
              "σ(1−σ), max 0.25 at z = 0",
              "you need a probability or a gate in [0,1] — a single binary "
              "output, an LSTM gate.",
              "Hidden layers: almost never. Max slope 0.25 means ten layers "
              "multiply to 10⁻⁶. Also not zero-centred, so all gradients into "
              "a weight row share a sign."),
             ("tanh  (eᶻ−e⁻ᶻ)/(eᶻ+e⁻ᶻ)", "(−1, 1)",
              "1 − tanh²(z), max 1 at z = 0",
              "bounded outputs, and small networks. It is sigmoid rescaled "
              "to be zero-centred and four times steeper.",
              "Still saturates: past |z| ≈ 3 the slope is under 0.01 and the "
              "unit stops learning. Keep z small with sane init."),
             ("ReLU  max(0, z)", "[0, ∞)",
              "1 if z > 0, else 0",
              "the default for hidden layers in anything deep. One "
              "comparison, no exponential, and no saturation on the positive "
              "side.",
              "Dead units: a unit pushed to z < 0 for every sample has "
              "gradient exactly 0 forever and can never come back. Usually a "
              "learning rate that was too large."),
             ("leaky ReLU", "(−∞, ∞)",
              "1 if z > 0, else 0.01",
              "ReLU, but you have seen units die. The 0.01 is a rescue rope.",
              "One more hyperparameter for a usually-small gain."),
             ("linear (none)", "(−∞, ∞)", "1 everywhere",
              "the OUTPUT layer of any regression — including every critic "
              "in this tutor, because Q is a sum of discounted rewards.",
              "Never in a hidden layer: the whole stack collapses to one "
              "matrix.")],
            col0=140, colw=210, height=430))
        self.add(t)

        # ---- vanishing gradients ---------------------------------------
        self.add(hline())
        self.add(title("Why the slope decides how deep you can go"))

        v = Card("multiply the slopes together and watch what survives")
        v.add(body(
            "Page 83 derives this properly, but the headline is short enough "
            "to state now: the blame signal reaching layer 1 of an L-layer "
            "network has been multiplied by <b>one activation slope per "
            "layer</b> on the way down. Slopes below 1 compound into nothing; "
            "slopes above 1 compound into an overflow."))
        v.add(math_label(r"\frac{\partial L}{\partial z^{(1)}} \;\propto\; "
                         r"\prod_{k=1}^{L}\; \sigma'\!\left(z^{(k)}\right)"
                         r"\cdot W^{(k)}", 17))
        self.s_depth = slider(1, 30, 12)
        self.s_zmag = slider(0, 400, 100)
        self.l_depth, self.l_zmag = QLabel(), QLabel()
        v.add_layout(slider_row("layers", self.s_depth, self.l_depth))
        v.add_layout(slider_row("typical |z| per unit", self.s_zmag,
                                self.l_zmag))
        self.st_sig = Stat("sigmoid, at layer 1", "--", theme.BAD)
        self.st_tanh = Stat("tanh, at layer 1", "--", theme.WARN)
        self.st_relu = Stat("ReLU, at layer 1", "--", theme.GOOD)
        v.add_layout(stat_row(self.st_sig, self.st_tanh, self.st_relu))
        self.cV = MplCanvas(width=7.6, height=2.6)
        v.add(self.cV)
        self.tV = body("", dim=True)
        v.add(self.tV)
        self.add(v)
        for s in (self.s_depth, self.s_zmag):
            s.valueChanged.connect(self._redraw_vanish)
        self._redraw_vanish()

        v.add(callout(
            "<b>This is why the tutor's own networks are two hidden layers "
            "of tanh and not twenty.</b> At depth 2, tanh's saturation costs "
            "you a factor of a few and nobody notices. At depth 20 it costs "
            "you everything, and the field's answers to that — ReLU, "
            "normalisation layers, residual connections — are all answers to "
            "this one product. A control-sized problem with a five-number "
            "state does not need the depth, so it does not need the "
            "machinery.", "good"))

        # ---- softmax vs argmax -----------------------------------------
        self.add(hline())
        self.add(title("Softmax and argmax: the same ranking, and only one of "
                       "them has a gradient"))

        sm = Card("softmax turns scores into probabilities; argmax throws the "
                  "rest away")
        sm.add(math_label(r"\mathrm{softmax}(z)_i = "
                          r"\frac{e^{z_i/T}}{\sum_j e^{z_j/T}}, "
                          r"\qquad \arg\max_i z_i", 17))
        sm.add(body(
            "Both take a vector of scores and say which is biggest. The "
            "difference is everything that happens to the losers:<br><br>"
            "&nbsp;&nbsp;• <b>softmax</b> returns a full distribution — "
            "positive, summing to 1, and <b>smooth</b>. Nudge any score a "
            "little and every probability moves a little. It therefore has a "
            "derivative everywhere, and can sit inside a network being "
            "trained.<br>"
            "&nbsp;&nbsp;• <b>argmax</b> returns an index. Nudge a score a "
            "little and the answer either does not change at all (gradient "
            "<b>zero</b>) or jumps to a different index (gradient "
            "<b>undefined</b>). It is a <i>decision</i>, not a layer. You use "
            "it at the end, after training, and you never differentiate "
            "through it.<br><br>"
            "The temperature T interpolates between them: T → 0 makes softmax "
            "a one-hot argmax, T → ∞ makes it uniform. That is a useful knob "
            "and it is also the reason the two are so often confused."))
        self.z_log = [slider(-300, 300, v) for v in (120, 40, -60, 190)]
        self.z_lbl = [QLabel() for _ in range(4)]
        for i in range(4):
            sm.add_layout(slider_row(f"score z{i+1}", self.z_log[i],
                                     self.z_lbl[i]))
        self.s_temp = slider(5, 300, 100)
        self.l_temp = QLabel()
        sm.add_layout(slider_row("temperature T (×0.01)", self.s_temp,
                                 self.l_temp))
        self.cS = MplCanvas(width=7.6, height=2.6, ncols=2)
        sm.add(self.cS)
        self.tS = body("", dim=True)
        sm.add(self.tS)
        self.add(sm)
        for s in self.z_log + [self.s_temp]:
            s.valueChanged.connect(self._redraw_softmax)
        self._redraw_softmax()

        sm2 = Card("and this is exactly where the RL half of the tutor sits")
        sm2.add(body(
            "Read the three algorithms you know against those two "
            "operations:<br><br>"
            "&nbsp;&nbsp;• <b>Tabular Q-learning</b> uses argmax and does not "
            "care that it has no gradient — nothing is being "
            "differentiated.<br>"
            "&nbsp;&nbsp;• <b>DQN</b> uses argmax over a fixed list of "
            "outputs. Still no gradient needed through it: the max only picks "
            "which output the regression loss applies to.<br>"
            "&nbsp;&nbsp;• <b>A stochastic policy over discrete actions</b> "
            "(PPO on a discrete task) uses <b>softmax</b>, precisely because "
            "the policy must be differentiable with respect to its own "
            "parameters.<br>"
            "&nbsp;&nbsp;• <b>DDPG</b> uses <b>neither</b>. There is no list "
            "to softmax over and no list to argmax over — the action is a "
            "real number. The actor's output activation is <b>tanh</b>, and "
            "the argmax is replaced by a network trained to already be at it. "
            "That substitution is the subject of the whole deep-RL block."))
        self.add(sm2)

        self.add(callout(
            "<b>Carry forward.</b> Hidden layers: ReLU by default, tanh when "
            "the network is small. Output layer: <b>linear for a value, tanh "
            "for a bounded action, softmax for a distribution over a discrete "
            "set, sigmoid for one probability.</b> The tutor's critic and "
            "actor are one example of each of the first two, and the reason "
            "is the physical range of the quantity, not a preference.",
            "good"))
        self.finish()

    # ------------------------------------------------------------------
    def _draw_gallery(self):
        c = self.cG
        c.clear()
        zs = np.linspace(-5, 5, 400)
        cols = (theme.VIOLET, theme.ACCENT, theme.GOOD, theme.CYAN,
                theme.TEXT_FAINT)
        for i, (kind, col) in enumerate(zip(_ACTS, cols)):
            y, d = _act_pair(kind, zs)
            top, bot = c.axes[i], c.axes[5 + i]
            top.plot(zs, y, color=col, lw=2.0)
            top.axhline(0, color=theme.BORDER, lw=0.8)
            top.axvline(0, color=theme.BORDER, lw=0.8)
            top.set_ylim(-1.6, 1.9)
            top.set_title(kind, fontsize=8.5)
            top.tick_params(labelsize=6)
            bot.plot(zs, d, color=theme.WARN, lw=2.0)
            bot.fill_between(zs, d, color=theme.WARN, alpha=0.14)
            bot.set_ylim(-0.05, 1.15)
            bot.tick_params(labelsize=6)
            bot.set_xlabel("z", fontsize=7)
            if i == 0:
                top.set_ylabel("σ(z)", fontsize=8)
                bot.set_ylabel("σ′(z)", fontsize=8)
        c.refresh()

    def _redraw_vanish(self):
        L = self.s_depth.value()
        zm = self.s_zmag.value() / 100.0
        self.l_depth.setText(f"{L}")
        self.l_zmag.setText(f"{zm:.2f}")

        slopes = {k: float(_act_pair(k, np.array([zm]))[1][0])
                  for k in ("sigmoid", "tanh", "relu")}
        ks = list(range(1, L + 1))
        c = self.cV
        c.clear()
        a = c.ax
        for k, col in (("sigmoid", theme.BAD), ("tanh", theme.WARN),
                       ("relu", theme.GOOD)):
            s = max(1e-12, slopes[k])
            a.semilogy(ks, [s ** n for n in ks], color=col, lw=2.0,
                       marker="o", ms=2.6, label=f"{k}  (σ′ = {slopes[k]:.3f})")
        a.axhline(1e-7, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a.text(1, 1.3e-7, "below here nothing moves in float32",
               fontsize=7, color=theme.TEXT_FAINT)
        a.set_xlabel("layers the blame must travel through")
        a.set_ylabel("surviving fraction (log)")
        a.set_title("the product of the slopes, layer by layer", fontsize=9)
        c.legend(a, loc="lower left")
        c.refresh()

        for st, k in ((self.st_sig, "sigmoid"), (self.st_tanh, "tanh"),
                      (self.st_relu, "relu")):
            v = max(1e-300, slopes[k]) ** L
            st.set(f"{v:.2e}")
            st.set_color(theme.GOOD if v > 1e-3 else
                         (theme.WARN if v > 1e-7 else theme.BAD))

        if slopes["relu"] == 0.0:
            self.tV.setText(
                "<b>|z| here is on the negative side for ReLU, so its slope "
                "is exactly zero</b> — which is the dead-unit failure, not a "
                "vanishing one. There is no small number to compound; the "
                "path is simply cut. Note the difference from saturation: a "
                "saturated tanh recovers if z drifts back toward zero, a dead "
                "ReLU has no gradient with which to drift.")
        else:
            self.tV.setText(
                f"<b>At |z| = {zm:.2f} and {L} layers</b>, sigmoid delivers "
                f"{slopes['sigmoid']**L:.1e} of the blame to the first layer, "
                f"tanh {slopes['tanh']**L:.1e}, ReLU "
                f"{slopes['relu']**L:.1e}. Push |z| up and watch tanh join "
                "sigmoid in the basement — saturation is a function of where "
                "the pre-activations sit, which is a function of "
                "initialisation and input scaling, which is why page 78 "
                "treats those as load-bearing rather than cosmetic.")

    def _redraw_softmax(self):
        z = np.array([s.value() / 100.0 for s in self.z_log])
        T = max(0.05, self.s_temp.value() / 100.0)
        for i in range(4):
            self.z_lbl[i].setText(f"{z[i]:+.2f}")
        self.l_temp.setText(f"{T:.2f}")

        e = np.exp((z - z.max()) / T)
        p = e / e.sum()
        one_hot = np.zeros(4)
        one_hot[int(np.argmax(z))] = 1.0

        c = self.cS
        c.clear()
        a1, a2 = c.axes
        names = ["a₁", "a₂", "a₃", "a₄"]
        a1.bar(names, p, color=theme.ACCENT)
        a1.set_ylim(0, 1.05)
        a1.set_title(f"softmax at T = {T:.2f} — smooth, differentiable",
                     fontsize=9)
        a1.set_ylabel("probability")
        a2.bar(names, one_hot, color=theme.WARN)
        a2.set_ylim(0, 1.05)
        a2.set_title("argmax — a decision, gradient 0 or undefined",
                     fontsize=9)
        c.refresh()

        gap = float(np.sort(z)[-1] - np.sort(z)[-2])
        self.tS.setText(
            f"<b>Top probability {p.max():.3f}, and the gap between the best "
            f"two scores is {gap:.2f}.</b> Drag the temperature down toward "
            "0.05 and the left bar chart converges on the right one — softmax "
            "<i>becomes</i> argmax in the limit, which is why it is called "
            "\"soft\". Drag it up and the distribution flattens toward "
            "uniform, which is exactly how an entropy bonus keeps SAC "
            "exploring. Meanwhile the right-hand chart does not move at all "
            "until one score overtakes another, at which point it jumps: no "
            "useful derivative anywhere, which is the entire reason a "
            "continuous-action method cannot be built on it.")


# ==========================================================================
# PAGE -- forward propagation
# ==========================================================================

class ForwardPropPage(Page):
    TITLE = "Forward Propagation"
    SUBTITLE = ("The signal entering on the left, getting multiplied by every "
                "weight it crosses, and arriving as one number on the right.")
    SECTION = SECTION
    NOTES = "neural nets"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>A forward pass is a fixed number of multiply-adds in a fixed "
            "order.</b> No search, no branching, no iteration to "
            "convergence — which is exactly why a network is allowed inside a "
            "control loop and a solver is not. The actor's forward pass is "
            "the entire runtime cost of a trained DDPG controller: about 4 500 "
            "multiply-adds, the same 4 500 every cycle, whatever the state.",
            "key"))

        # ---- the animation ---------------------------------------------
        an = Card("watch one input vector cross the network")
        an.add(body(
            "Three inputs, two hidden layers of four tanh units, two linear "
            "outputs — the shape of an actor. <b>Green edges are positive "
            "weights, red are negative, and thickness is magnitude.</b> The "
            "cyan dots are the signal: they leave every node of one layer, "
            "travel along every edge simultaneously, and arrive together, at "
            "which point the receiving node sums what reached it, adds its "
            "bias, squashes, and lights up with its own value.<br><br>"
            "The thing to watch for is the <b>fan-out</b>. Every node sends "
            "its value down <i>every</i> edge leaving it — not one path, four. "
            "That branching is invisible in the formula y = σ(xW + b) and it "
            "is the single fact that makes the backward pass on the next page "
            "a sum rather than a product."))
        hb = QHBoxLayout()
        hb.setSpacing(8)
        self.btn_play = QPushButton("Play")
        self.btn_play.setObjectName("Primary")
        self.btn_step = QPushButton("Step one layer")
        self.btn_new = QPushButton("New input")
        hb.addWidget(self.btn_play)
        hb.addWidget(self.btn_step)
        hb.addWidget(self.btn_new)
        hb.addStretch(1)
        an.add_layout(hb)
        self.net = NetCanvas([3, 4, 4, 2], width=7.8, height=3.2,
                             labels=["input  x", "hidden 1  tanh",
                                     "hidden 2  tanh", "output  linear"])
        an.add(self.net)
        self.st_layer = Stat("computing", "--", theme.CYAN)
        self.st_mac = Stat("multiply-adds so far", "--", theme.ACCENT)
        self.st_out = Stat("output", "--", theme.GOOD)
        an.add_layout(stat_row(self.st_layer, self.st_mac, self.st_out))
        self.tF = body("", dim=True)
        an.add(self.tF)
        self.add(an)

        rng = np.random.default_rng(11)
        self._mlp = MLP([3, 4, 4, 2], out_act="linear", rng=rng)
        # the output layer is deliberately tiny at init (3e-3) so that a fresh
        # actor starts near zero; widen it here so the numbers on screen are
        # readable rather than four leading zeros
        self._mlp.layers[-1].W = rng.uniform(-1.0, 1.0,
                                             size=self._mlp.layers[-1].W.shape)
        self._x = rng.uniform(-1, 1, size=(1, 3))
        self._wave = 0.0
        self._acts = []
        self._recompute()

        self._timer = QTimer(self)
        self._timer.setInterval(70)
        self._timer.timeout.connect(self._tick)
        self.btn_play.clicked.connect(self._toggle)
        self.btn_step.clicked.connect(self._step_layer)
        self.btn_new.clicked.connect(self._new_input)
        self._render()

        # ---- the arithmetic --------------------------------------------
        self.add(hline())
        self.add(title("The same three lines, written out"))

        ar = Card("layer by layer, with the shapes")
        ar.add(math_label(r"\mathbf{a}^{(0)} = \mathbf{x} \qquad "
                          r"\mathbf{z}^{(k)} = \mathbf{a}^{(k-1)}W^{(k)} + "
                          r"\mathbf{b}^{(k)} \qquad "
                          r"\mathbf{a}^{(k)} = \sigma_k\!\left("
                          r"\mathbf{z}^{(k)}\right)", 17))
        ar.add(_table(
            ["Step", "Shapes", "Cost", "What it means"],
            [("z⁽¹⁾ = xW⁽¹⁾ + b⁽¹⁾", "(1×3)(3×4) + (4) → 1×4", "12 mults",
              "each hidden unit forms its own weighted sum of all three "
              "inputs"),
             ("a⁽¹⁾ = tanh(z⁽¹⁾)", "1×4 → 1×4", "4 tanh",
              "element-wise. No mixing happens here — the squash never looks "
              "at its neighbours"),
             ("z⁽²⁾ = a⁽¹⁾W⁽²⁾ + b⁽²⁾", "(1×4)(4×4) → 1×4", "16 mults",
              "the second layer mixes the first layer's FEATURES, not the "
              "raw inputs"),
             ("a⁽²⁾ = tanh(z⁽²⁾)", "1×4 → 1×4", "4 tanh", "same again"),
             ("y = a⁽²⁾W⁽³⁾ + b⁽³⁾", "(1×4)(4×2) → 1×2", "8 mults",
              "linear output: no squash, because the answer has no natural "
              "bound")],
            col0=170, colw=200, height=290))
        ar.add(body(
            "<b>Batching changes exactly one thing.</b> Make x a 64×3 array "
            "and every line above is unchanged — the same W, the same b "
            "broadcast across rows, and 64 independent forward passes come "
            "out of one matrix multiply. Nothing about sample i affects "
            "sample j. (That statement is true for every layer in this tutor "
            "and false for exactly one layer type in existence, batch norm, "
            "which is why page 85 treats it as a special case rather than as "
            "one more layer.)", dim=True))
        self.add(ar)

        # ---- what gets cached ------------------------------------------
        cc = Card("the two things the forward pass has to remember")
        cc.add(_code(get_source(Dense.forward)))
        cc.add(body(
            "Two assignments in that function are not about computing the "
            "output at all:<br><br>"
            "&nbsp;&nbsp;• <b><code>self._x = x</code></b> — the layer's "
            "input. The weight gradient is going to be "
            "<code>x<sup>T</sup> · dz</code>, so the input <i>is</i> half of "
            "every weight update. \"How much this weight is to blame\" is "
            "\"how much blame arrived\" times \"how big the thing it was "
            "multiplying was\".<br>"
            "&nbsp;&nbsp;• <b><code>self._z = x @ W + b</code></b> — the "
            "pre-activation. The backward pass needs σ′(z), <i>not</i> σ(z), "
            "and z is the cheapest thing to keep that recovers it.<br><br>"
            "This is why training a network costs more memory than running "
            "one. An inference-only forward pass can overwrite its buffers "
            "as it goes; a training forward pass must keep one cached "
            "activation per layer per sample until the backward pass has "
            "consumed it. On a robot that difference decides whether the "
            "learner can share a machine with the controller — which is "
            "exactly the argument on the deployment page."))
        self.add(cc)

        rt = Card("why this shape of computation is allowed in a control loop")
        rt.add(body(
            "Page 1 asked for one property from anything running at 1 kHz: a "
            "<b>bounded, repeatable execution time</b>. A forward pass has "
            "it, and almost nothing else in optimisation does.<br><br>"
            "&nbsp;&nbsp;• <b>No data-dependent branching.</b> The same "
            "multiply-adds run for every state. ReLU is a comparison, not a "
            "branch that changes the work done.<br>"
            "&nbsp;&nbsp;• <b>No iteration to a tolerance.</b> Compare with "
            "solving max<sub>a</sub> Q(s,a) numerically at runtime, which "
            "takes however many iterations it takes — that is the wall the "
            "next block calls the argmax problem.<br>"
            "&nbsp;&nbsp;• <b>No allocation</b>, if the buffers are "
            "preallocated. Which they must be: a garbage collector inside a "
            "1 kHz loop is a jitter source, and jitter is phase margin.<br><br>"
            "Worst-case timing for the tutor's actor: ~4 500 multiply-adds "
            "and 128 tanh calls. On any modern CPU that is single-digit "
            "microseconds, deterministic — comfortably inside a 1 ms budget "
            "with three orders of magnitude to spare."))
        self.add(rt)

        self.add(callout(
            "<b>Carry forward.</b> Forward is: multiply, add the bias, "
            "squash, hand on. It fans out at every node, it caches x and z on "
            "the way, and it ends with one number for a critic or one action "
            "vector for an actor. The next page runs the identical graph "
            "backwards.", "good"))
        self.finish()

    # ------------------------------------------------------------------
    def on_show(self):
        self._timer.start()

    def on_hide(self):
        self._timer.stop()
        self.btn_play.setText("Play")

    def _toggle(self):
        if self._timer.isActive():
            self._timer.stop()
            self.btn_play.setText("Play")
        else:
            self._timer.start()
            self.btn_play.setText("Pause")

    def _step_layer(self):
        self._timer.stop()
        self.btn_play.setText("Play")
        self._wave = float((int(self._wave) + 1) % 3)
        self._render()

    def _new_input(self):
        self._x = np.random.default_rng().uniform(-1, 1, size=(1, 3))
        self._recompute()
        self._wave = 0.0
        self._render()

    def _recompute(self):
        a = self._x
        self._acts = [a.ravel().copy()]
        for l in self._mlp.layers:
            a = l.forward(a)
            self._acts.append(a.ravel().copy())

    def _tick(self):
        self._wave = (self._wave + 0.09) % 3.0
        self._render()

    def _render(self):
        Ws = [l.W for l in self._mlp.layers]
        k = int(self._wave)
        shown = [self._acts[i] if i <= k else None
                 for i in range(len(self._acts))]
        self.net.render(Ws, acts=shown, wave=self._wave, node_span=1.0,
                        edge_note="green = positive weight, red = negative, "
                                  "thickness = |w|")
        self.st_layer.set(["x → h1", "h1 → h2", "h2 → y"][k])
        self.st_mac.set(["0", "12", "28"][k])
        y = self._acts[-1]
        self.st_out.set(f"{y[0]:+.2f}, {y[1]:+.2f}")
        self.tF.setText(
            f"<b>Layer {k+1} of 3 in flight.</b> Every node in the sending "
            
            f"separate edges at once, and every node in the receiving layer "
            f"is collecting {self.net.sizes[k]} arrivals. Count the dots: "
            f"{self.net.sizes[k] * self.net.sizes[k+1]} of them, one per "
            "weight in this layer's matrix.")


# ==========================================================================
# PAGE -- backpropagation
# ==========================================================================

class BackpropPage(Page):
    TITLE = "Backpropagation"
    SUBTITLE = ("Multiply along each path; SUM across all the paths. The loss "
                "seeds it, the activation slopes shape it, and it comes out "
                "as one number per weight.")
    SECTION = SECTION
    NOTES = "neural nets"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>Backprop answers one question, for every weight at once: if "
            "this weight were a hair larger, would the loss go up or down, and "
            "by how much?</b> That is a partial derivative, and there are as "
            "many of them as there are weights. Computing them one at a time "
            "by nudging would cost one forward pass per weight; backprop gets "
            "all of them for the price of roughly two.", "key"))

        # ---- the seed --------------------------------------------------
        sd = Card("it starts at the loss, and the loss is ONE number")
        sd.add(body(
            "Nothing can be differentiated until there is a single scalar to "
            "differentiate. A network that outputs two numbers has no "
            "gradient until you say what you wanted from them — that is what "
            "a loss is for, and it is the only job it has."))
        sd.add(math_label(r"L = \frac{1}{N}\sum_i (y_i - t_i)^2 "
                          r"\qquad\Longrightarrow\qquad "
                          r"\frac{\partial L}{\partial y_i} = "
                          r"\frac{2(y_i - t_i)}{N}", 17))
        sd.add(body(
            "That right-hand expression is the <b>seed</b>: the blame handed "
            "to the output layer before any propagating happens. Everything "
            "afterwards is mechanical. Change the loss and only the seed "
            "changes — the machinery below it is identical, which is why the "
            "same <code>backward()</code> serves a critic being regressed "
            "onto a target and an actor being pushed uphill on a critic. The "
            "second of those has no target at all and still works, because "
            "all the actor's update ever needed was <i>a seed</i>."))
        self.add(sd)

        # ---- multiple paths --------------------------------------------
        self.add(hline())
        self.add(title("The rule, stated completely: multiply along a path, "
                       "sum across paths"))

        mp = Card("one input does not have one route to the output — it has "
                  "all of them")
        mp.add(body(
            "The tempting mental model is a chain: input → neuron → neuron → "
            "output, multiply the three sensitivities together, done. That is "
            "right only for a network one neuron wide. In a real layer, an "
            "input fans out to <b>every</b> unit of the next layer, each of "
            "those fans out to every unit of the layer after, and the number "
            "of distinct routes multiplies."))
        mp.add(math_label(r"\frac{\partial y}{\partial x_i} \;=\; "
                          r"\sum_{\mathrm{paths}\; p \,:\, x_i \to y} \;\;"
                          r"\prod_{\mathrm{edges}\; e \in p} "
                          r"\left(w_e \cdot \sigma'(z_e)\right)", 17))
        mp.add(body(
            "&nbsp;&nbsp;• <b>Along one path: multiply.</b> Each hop "
            "contributes the weight it crossed and the slope of the unit it "
            "landed on. That is the chain rule, applied literally.<br>"
            "&nbsp;&nbsp;• <b>Across paths: add.</b> A small change in "
            "x<sub>i</sub> arrives at the output by every route "
            "simultaneously, and the effects superpose. Some paths push up "
            "and some push down; what survives is the sum, and it can be "
            "small because there are no paths or because the paths cancel — "
            "two very different situations that look identical from the "
            "outside.<br><br>"
            "In a 2→3→3→1 network there are 3 × 3 = <b>nine</b> paths from "
            "each input to the output. Below, every one of them is listed "
            "with its own product, the nine are summed, and the sum is "
            "checked against a brute-force numerical derivative — nudge the "
            "input by ±h, re-run the network, divide. If the path picture is "
            "right, those two numbers agree to five decimal places."))
        self.s_in = QComboBox()
        self.s_in.addItem("x₁")
        self.s_in.addItem("x₂")
        self.s_in.currentIndexChanged.connect(self._redraw_paths)
        self.s_xv = [slider(-150, 150, 60), slider(-150, 150, -40)]
        self.l_xv = [QLabel(), QLabel()]
        mp.add_layout(labelled("Differentiate w.r.t.", self.s_in, width=140))
        for i in range(2):
            self.s_xv[i].valueChanged.connect(self._redraw_paths)
            mp.add_layout(slider_row(f"input x{i+1}", self.s_xv[i],
                                     self.l_xv[i]))
        self.st_sum = Stat("sum of the 9 paths", "--", theme.ACCENT)
        self.st_fd = Stat("finite difference", "--", theme.GOOD)
        self.st_diff = Stat("disagreement", "--", theme.WARN)
        mp.add_layout(stat_row(self.st_sum, self.st_fd, self.st_diff))
        self.pathnet = NetCanvas([2, 3, 3, 1], width=7.8, height=2.9,
                                 labels=["input", "hidden 1", "hidden 2",
                                         "output y"])
        mp.add(self.pathnet)
        self.path_table_holder = Card("every path, and what it contributes")
        mp.add(self.path_table_holder)
        self.tP = body("", dim=True)
        mp.add(self.tP)
        self.add(mp)

        rng = np.random.default_rng(5)
        self._pnet = MLP([2, 3, 3, 1], out_act="linear", rng=rng)
        self._pnet.layers[-1].W = rng.uniform(-1.0, 1.0,
                                              size=self._pnet.layers[-1].W.shape)
        self._ptable = None
        self._redraw_paths()

        mp2 = Card("why nobody enumerates paths in practice")
        mp2.add(body(
            "The path formula is the <b>definition</b>, and it is the right "
            "picture to hold. It is a terrible algorithm: the number of paths "
            "in an L-layer network of width n is n<sup>L−1</sup>, so a "
            "64-wide, 3-layer network already has 4 096 paths per input-output "
            "pair and a 10-layer one has 10<sup>18</sup>.<br><br>"
            "Backpropagation computes the identical sum in <b>linear</b> time "
            "by refusing to expand it. Instead of following paths, it carries "
            "one blame number per <i>node</i>, layer by layer, and every node "
            "adds up the blame arriving from all its children before passing "
            "anything on. The additions that the path formula does at the "
            "end, backprop does early and shares — the same trick as dynamic "
            "programming on the DP pages, and for the same reason: "
            "overlapping subproblems."))
        self.add(mp2)

        # ---- the animation ---------------------------------------------
        self.add(hline())
        self.add(title("The same graph, run backwards"))

        an = Card("blame flowing right to left")
        an.add(body(
            "Same network as the forward page. Now the amber dots start at "
            "the output holding the seed ∂L/∂y, and every edge they cross "
            "multiplies them by that edge's weight; every node they land on "
            "multiplies by its own σ′(z) and <b>sums</b> whatever arrived "
            "from the right. When the wave has passed a layer, that layer's "
            "weight gradients are known: gradient of a weight = blame at its "
            "output end × value at its input end."))
        hb = QHBoxLayout()
        hb.setSpacing(8)
        self.btn_bplay = QPushButton("Play")
        self.btn_bplay.setObjectName("Primary")
        self.chk_fwd = QCheckBox("show the forward pass first")
        self.chk_fwd.setChecked(True)
        hb.addWidget(self.btn_bplay)
        hb.addWidget(self.chk_fwd)
        hb.addStretch(1)
        an.add_layout(hb)
        self.bnet = NetCanvas([3, 4, 4, 2], width=7.8, height=3.2,
                              labels=["input  x", "hidden 1", "hidden 2",
                                      "output  y"])
        an.add(self.bnet)
        self.st_dir = Stat("direction", "--", theme.WARN)
        self.st_known = Stat("gradients known", "--", theme.GOOD)
        an.add_layout(stat_row(self.st_dir, self.st_known))
        an.add(body(
            "Note what the backward wave does <b>not</b> do: it never changes "
            "a weight. It only computes numbers. The weights move afterwards, "
            "all at once, when the optimiser is called — which is why the "
            "gradient is a snapshot of the surface at the point you were "
            "standing, and why taking too big a step with it is the classic "
            "way to diverge.", dim=True))
        self.add(an)

        rng2 = np.random.default_rng(11)
        self._bmlp = MLP([3, 4, 4, 2], out_act="linear", rng=rng2)
        self._bmlp.layers[-1].W = rng2.uniform(
            -1.0, 1.0, size=self._bmlp.layers[-1].W.shape)
        self._bx = rng2.uniform(-1, 1, size=(1, 3))
        a = self._bx
        self._bacts = [a.ravel().copy()]
        for l in self._bmlp.layers:
            a = l.forward(a)
            self._bacts.append(a.ravel().copy())
        self._bphase = 3.0
        self._btimer = QTimer(self)
        self._btimer.setInterval(70)
        self._btimer.timeout.connect(self._btick)
        self.btn_bplay.clicked.connect(self._btoggle)
        self._brender()

        # ---- per-layer rules -------------------------------------------
        self.add(hline())
        self.add(title("The three lines that do all of it"))

        rl = Card("one layer's backward pass, and what each line is")
        rl.add(math_label(r"\delta = \frac{\partial L}{\partial z} = "
                          r"\frac{\partial L}{\partial a}\odot\sigma'(z), "
                          r"\quad \frac{\partial L}{\partial W} = "
                          r"x^{\!\top}\delta, \quad "
                          r"\frac{\partial L}{\partial b} = \delta, \quad "
                          r"\frac{\partial L}{\partial x} = \delta W^{\!\top}",
                          16))
        rl.add(_code(get_source(Dense.backward)))
        rl.add(_table(
            ["Line", "Formula", "What it is"],
            [("dz = dout * σ′(z)", "δ = ∂L/∂a ⊙ σ′(z)",
              "push the blame through the squash. Element-wise: no mixing. "
              "This is the ONLY place the activation appears in the backward "
              "pass, and it appears as its derivative."),
             ("self.gW = x.T @ dz / n", "∂L/∂W = xᵀδ / N",
              "blame × input. A weight that multiplied a large input is more "
              "responsible for the error than one that multiplied a small "
              "one. This is the entire content of \"blame × the value that "
              "fed it\", averaged over the batch."),
             ("self.gb = dz.mean(0)", "∂L/∂b = δ",
              "the bias multiplies a constant 1, so its gradient is the "
              "blame itself, averaged over the batch."),
             ("return dz @ W.T", "∂L/∂x = δWᵀ",
              "the blame handed to the PREVIOUS layer. Each input's share is "
              "the sum, over every unit it fed, of that unit's blame times "
              "the weight between them — the 'sum across paths', done one "
              "layer at a time.")],
            col0=170, colw=250, height=330))
        rl.add(callout(
            "<b>That return value is the load-bearing line of the whole "
            "tutor.</b> <code>return dz @ W.T</code> is the gradient with "
            "respect to the layer's <i>input</i>, not its weights. Chain it "
            "through every layer of a network and you get the gradient with "
            "respect to the network's input — which, when the network is a "
            "critic and part of its input is the action, is ∂Q/∂a. "
            "The actor's entire training signal is one slice of that array. "
            "No autograd, no special case: it falls out of the same three "
            "lines that train any layer of anything.", "key"))
        self.add(rl)

        # ---- the step ---------------------------------------------------
        st = Card("and then, separately, the step")
        st.add(body(
            "Backprop produces gradients. It does not update anything. The "
            "update is one more line and it is where the learning rate "
            "lives:"))
        st.add(math_label(r"w \;\leftarrow\; w \;-\; \eta\,"
                          r"\frac{\partial L}{\partial w}", 17))
        st.add(body(
            "Minus, because the gradient points <b>uphill</b> on the loss and "
            "we want down. Flip the sign of the seed and the identical "
            "machinery climbs instead of descends — which is exactly the "
            "trick the actor update uses, and the whole reason "
            "<code>-dq_da</code> has a minus in front of it.<br><br>"
            "In this tutor η is not applied raw: the Adam page's optimiser "
            "divides each gradient by a running estimate of its own "
            "magnitude, so a gradient of 100 and a gradient of 0.1 produce "
            "steps of a comparable size. That has a consequence people find "
            "surprising, and it matters on the DDPG pages: with Adam, the "
            "<b>sign and relative pattern</b> of the gradient across weights "
            "carries most of the information, and its absolute scale carries "
            "much less than you would expect.", dim=True))
        self.add(st)

        self.add(callout(
            "<b>Carry forward.</b> Seed at the loss, multiply along each "
            "path, sum across paths, and stop at whatever you wanted the "
            "derivative of. Stop at the weights and you have a training "
            "signal for this network; carry on to the <b>input</b> and you "
            "have a training signal for whatever produced that input. The "
            "second one is DDPG.", "good"))
        self.finish()

    # ------------------------------------------------------------------
    def on_show(self):
        self._btimer.start()

    def on_hide(self):
        self._btimer.stop()
        self.btn_bplay.setText("Play")

    def _btoggle(self):
        if self._btimer.isActive():
            self._btimer.stop()
            self.btn_bplay.setText("Play")
        else:
            self._btimer.start()
            self.btn_bplay.setText("Pause")

    def _btick(self):
        span = 6.0 if self.chk_fwd.isChecked() else 3.0
        self._bphase = (self._bphase + 0.09) % span
        self._brender()

    def _brender(self):
        Ws = [l.W for l in self._bmlp.layers]
        fwd_first = self.chk_fwd.isChecked()
        p = self._bphase
        if fwd_first and p < 3.0:
            k = int(p)
            shown = [self._bacts[i] if i <= k else None
                     for i in range(len(self._bacts))]
            self.bnet.render(Ws, acts=shown, wave=p, back=False,
                             edge_note="forward: values moving right")
            self.st_dir.set("forward")
            self.st_dir.set_color(theme.CYAN)
            self.st_known.set("none yet")
        else:
            q = p - 3.0 if fwd_first else p
            wave = 3.0 - q
            self.bnet.render(Ws, acts=self._bacts, wave=min(2.999, wave),
                             back=True,
                             edge_note="backward: blame moving left, "
                                       "summed at every node")
            self.st_dir.set("backward")
            self.st_dir.set_color(theme.WARN)
            done = 3 - int(min(2.999, wave))
            self.st_known.set(f"{done} of 3 layers")

    # ------------------------------------------------------------------
    def _redraw_paths(self):
        x = np.array([[self.s_xv[0].value() / 100.0,
                       self.s_xv[1].value() / 100.0]])
        for i in range(2):
            self.l_xv[i].setText(f"{x[0, i]:+.2f}")
        i_in = self.s_in.currentIndex()
        net = self._pnet

        y = net.forward(x)
        L0, L1, L2 = net.layers
        s1 = 1.0 - np.tanh(L0._z) ** 2          # slopes of hidden layer 1
        s2 = 1.0 - np.tanh(L1._z) ** 2          # slopes of hidden layer 2

        rows, total = [], 0.0
        for j in range(3):
            for k in range(3):
                prod = (float(L0.W[i_in, j]) * float(s1[0, j])
                        * float(L1.W[j, k]) * float(s2[0, k])
                        * float(L2.W[k, 0]))
                total += prod
                rows.append((
                    f"x{i_in+1} → h1[{j+1}] → h2[{k+1}] → y",
                    f"{L0.W[i_in, j]:+.3f} × {s1[0, j]:.3f}",
                    f"{L1.W[j, k]:+.3f} × {s2[0, k]:.3f}",
                    f"{L2.W[k, 0]:+.3f}",
                    f"{prod:+.5f}"))

        h = 1e-5
        xp, xm = x.copy(), x.copy()
        xp[0, i_in] += h
        xm[0, i_in] -= h
        fd = float((net.forward(xp) - net.forward(xm))[0, 0] / (2 * h))
        net.forward(x)                      # restore the caches we just clobbered

        self.st_sum.set(f"{total:+.5f}")
        self.st_fd.set(f"{fd:+.5f}")
        self.st_diff.set(f"{abs(total - fd):.2e}")
        self.st_diff.set_color(theme.GOOD if abs(total - fd) < 1e-6
                               else theme.BAD)

        if self._ptable is not None:
            self._ptable.setParent(None)
        self._ptable = _table(
            ["Path", "edge 1: w × σ′", "edge 2: w × σ′", "edge 3: w",
             "product"],
            rows, col0=190, colw=150, height=390)
        self.path_table_holder.add(self._ptable)

        pos = [r for r in rows if float(r[4]) > 0]
        neg = [r for r in rows if float(r[4]) < 0]
        biggest = max(rows, key=lambda r: abs(float(r[4])))
        self.tP.setText(
            f"<b>Nine paths, {len(pos)} pushing the output up and "
            f"{len(neg)} pushing it down, summing to {total:+.5f}.</b> The "
            f"brute-force numerical derivative says {fd:+.5f} — they agree to "
            f"{abs(total-fd):.0e}, which is finite-difference rounding and "
            "nothing else. The largest single path contributes "
            f"{biggest[4]}, which is "
            f"{100*abs(float(biggest[4]))/max(1e-12, sum(abs(float(r[4])) for r in rows)):.0f}% "
            "of the total absolute traffic: no single route dominates, and "
            "picking any one of them as \"the\" chain would give the wrong "
            "answer. Drag an input until a hidden unit saturates and watch "
            "the paths through it collapse to near zero — that is a vanishing "
            "gradient happening in front of you, one path at a time.")

        # the picture, with the fan-out made visible
        acts = [x.ravel(), np.tanh(L0._z).ravel(), np.tanh(L1._z).ravel(),
                y.ravel()]
        self.pathnet.render([L0.W, L1.W, L2.W], acts=acts,
                            edge_note=f"every route from x{i_in+1} to y is a "
                                      f"separate term in the sum")


# ==========================================================================
# PAGE -- losses, softmax, argmax
# ==========================================================================

class LossPage(Page):
    TITLE = "Losses, and What They Do to the Gradient"
    SUBTITLE = ("A loss is not a score card. It is the thing whose slope you "
                "will be riding for the next million steps — so its shape "
                "matters more than its value.")
    SECTION = SECTION
    NOTES = "neural nets"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>You never optimise the loss. You optimise along its "
            "derivative.</b> Two losses that rank every model identically can "
            "still train completely differently, because what reaches the "
            "weights is dL/dy, not L. Every choice on this page is a choice "
            "about that derivative: how big it is when you are badly wrong, "
            "and how fast it dies as you get close.", "key"))

        # ---- the three regression losses --------------------------------
        r = Card("the three you will actually use, with their gradients under "
                 "them")
        r.add(body(
            "Drag the prediction and watch the bottom row. The loss curves "
            "are almost interchangeable; the gradient curves are not."))
        self.s_pred = slider(-300, 300, 150)
        self.s_delta = slider(10, 300, 100)
        self.l_pred, self.l_delta = QLabel(), QLabel()
        r.add_layout(slider_row("prediction y (target = 0)", self.s_pred,
                                self.l_pred))
        r.add_layout(slider_row("Huber δ", self.s_delta, self.l_delta))
        self.st_mse = Stat("MSE gradient", "--", theme.ACCENT)
        self.st_mae = Stat("MAE gradient", "--", theme.VIOLET)
        self.st_hub = Stat("Huber gradient", "--", theme.GOOD)
        r.add_layout(stat_row(self.st_mse, self.st_mae, self.st_hub))
        self.cL = MplCanvas(width=7.6, height=2.8, ncols=2)
        r.add(self.cL)
        self.tL = body("", dim=True)
        r.add(self.tL)
        self.add(r)
        for s in (self.s_pred, self.s_delta):
            s.valueChanged.connect(self._redraw_loss)
        self._redraw_loss()

        r2 = Card("choosing between them")
        r2.add(_table(
            ["Loss", "Formula", "Gradient", "Behaviour"],
            [("MSE  (L2)", "(y − t)²", "2(y − t) — grows with the error",
              "The default for regression, and what every critic in this "
              "tutor uses. Smooth everywhere, and its minimiser is the MEAN "
              "of the targets, which is exactly what a value function is "
              "defined to be. Its weakness is its strength: one outlier "
              "target moves the fit a long way."),
             ("MAE  (L1)", "|y − t|", "±1 — constant, whatever the error",
              "Ignores how wrong you are, only which side. Its minimiser is "
              "the MEDIAN. Robust to outliers, but the constant gradient "
              "never shrinks near the optimum, so it rattles instead of "
              "settling."),
             ("Huber", "L2 near zero, L1 far out",
              "clipped at ±δ",
              "MSE's smooth settling with MAE's tolerance for outliers. This "
              "is the standard choice for a DQN/DDPG critic on a hard "
              "problem, because a single bad bootstrapped target — and there "
              "WILL be some, the targets are manufactured — cannot then "
              "produce one enormous step.")],
            col0=110, colw=290, height=300))
        self.add(r2)

        # ---- classification --------------------------------------------
        self.add(hline())
        self.add(title("Cross-entropy, and why it is glued to softmax"))

        ce = Card("the pairing is not a convention — it is what makes the "
                  "gradient clean")
        ce.add(math_label(r"L = -\sum_i t_i \log p_i, \qquad "
                          r"p = \mathrm{softmax}(z) \qquad\Longrightarrow"
                          r"\qquad \frac{\partial L}{\partial z} = p - t", 17))
        ce.add(body(
            "<b>Read the right-hand side: the seed is literally "
            "\"predicted minus wanted\".</b> No σ′ factor, no saturation "
            "term, nothing that can go to zero while the answer is still "
            "wrong. Softmax's own derivative and the log in cross-entropy "
            "cancel exactly, and that cancellation is the reason the pair is "
            "always used together.<br><br>"
            "Try the other combination and the failure is instructive. "
            "Softmax followed by <b>MSE</b> gives a gradient with a factor of "
            "p(1−p) in it. A network that is confidently, catastrophically "
            "wrong has p ≈ 0 for the right class — so that factor is ≈ 0, so "
            "the gradient is ≈ 0, so it never corrects. <b>The more wrong it "
            "is, the less it learns.</b> Same model, same data, same "
            "optimiser; the pairing of loss to output activation is the "
            "entire difference."))
        ce.add(_table(
            ["Output activation", "Paired loss", "Seed ∂L/∂z", "Where it "
             "shows up"],
            [("softmax", "cross-entropy", "p − t (clean)",
              "any discrete distribution — a PPO policy over discrete "
              "actions, a classifier"),
             ("sigmoid", "binary cross-entropy", "p − t (clean, same reason)",
              "one independent probability, e.g. a terminal-state predictor"),
             ("linear", "MSE / Huber", "2(y − t)",
              "every critic in this tutor, and any regression"),
             ("tanh", "— (usually no loss here at all)", "n/a",
              "a bounded ACTOR output. There is no target to compare it to; "
              "its gradient arrives from a critic instead")],
            col0=140, colw=230, height=250))
        self.add(ce)

        # ---- RL's twist --------------------------------------------------
        self.add(hline())
        self.add(title("What all of that becomes in reinforcement learning"))

        rl = Card("one network has a loss; the other one does not, really")
        rl.add(body(
            "This is the point where supervised intuition has to be bent, and "
            "it is worth being blunt about how far.<br><br>"
            "<b>The critic has an honest loss</b>, but a dishonest target. "
            "L = mean(Q(s,a) − y)² is textbook MSE regression. What is not "
            "textbook is that y was manufactured — y = r + γQ′(s′, μ′(s′)) "
            "contains the network's own opinion. In supervised learning a "
            "human wrote the label; here the label is partly a guess that "
            "improves as training goes on. One real reward per target is the "
            "only fact in it, and the whole method is a mechanism for leaking "
            "those real rewards backwards through time."))
        rl.add(math_label(r"L_{\mathrm{critic}}(w) = \frac{1}{N}\sum_i"
                          r"\Big(Q(s_i,a_i;w) - \underbrace{\big[r_i + "
                          r"\gamma(1-d_i)Q'(s'_i,\mu'(s'_i))\big]}"
                          r"_{\textstyle y_i,\ \mathrm{held\ fixed}}\Big)^2",
                          16))
        rl.add(body(
            "<b>The actor has no loss at all</b>, in the sense this page has "
            "been using the word. There is no target action, no error, "
            "nothing to be close to — nobody knows what the right action is, "
            "which is the entire reason the problem is reinforcement learning "
            "and not supervised learning. What the code writes as a loss is "
            "just <b>−Q(s, μ(s))</b>: a scalar we would like to be small, "
            "whose gradient is the only thing anybody wants from it."))
        rl.add(math_label(r"J(\theta) = \mathbb{E}\big[Q(s,\mu_\theta(s))"
                          r"\big] \qquad \text{maximise} \qquad "
                          r"L_{\mathrm{actor}} = -J(\theta)", 17))
        rl.add(callout(
            "<b>So \"minimise the loss\" and \"climb the critic\" are the "
            "same instruction with a minus sign between them.</b> The seed "
            "handed to the backward pass is ∂(−Q)/∂Q = −1, spread over the "
            "batch. It flows through the critic to the critic's input, where "
            "the action lives, and continues into the actor. The critic's "
            "weight gradients get computed on the way and thrown away — the "
            "critic's optimiser is not called on that pass. Everything the "
            "actor learns is that single number, re-multiplied by weights and "
            "slopes on its way home.", "key"))
        rl.add(body(
            "Two consequences worth carrying into the DDPG pages. First, the "
            "actor's update is <b>only as good as the critic</b> — a wrong "
            "critic gives a confident wrong direction, and there is no "
            "external signal to contradict it. Second, the actor's \"loss\" "
            "value printed in a training log is <b>meaningless as a progress "
            "measure</b>: it is −Q, which drifts as the critic's whole "
            "surface shifts, and it can fall while the policy gets worse. "
            "Watch the returns, not the actor loss.", dim=True))
        self.add(rl)

        self.add(callout(
            "<b>Carry forward.</b> The loss's job is to produce a seed. "
            "Regression → 2(y−t). Classification with softmax → p−t. Actor → "
            "−1, routed through a critic. Three seeds, one identical backward "
            "pass under all of them.", "good"))
        self.finish()

    # ------------------------------------------------------------------
    def _redraw_loss(self):
        e = self.s_pred.value() / 100.0
        d = self.s_delta.value() / 100.0
        self.l_pred.setText(f"{e:+.2f}")
        self.l_delta.setText(f"{d:.2f}")

        es = np.linspace(-3, 3, 400)
        mse = es ** 2
        mae = np.abs(es)
        hub = np.where(np.abs(es) <= d, 0.5 * es ** 2,
                       d * (np.abs(es) - 0.5 * d))
        g_mse = 2 * es
        g_mae = np.sign(es)
        g_hub = np.clip(es, -d, d)

        self.st_mse.set(f"{2*e:+.2f}")
        self.st_mae.set(f"{np.sign(e):+.2f}")
        self.st_hub.set(f"{np.clip(e, -d, d):+.2f}")

        c = self.cL
        c.clear()
        a1, a2 = c.axes
        for ys, col, lab in ((mse, theme.ACCENT, "MSE"),
                             (mae, theme.VIOLET, "MAE"),
                             (hub, theme.GOOD, f"Huber δ={d:.2f}")):
            a1.plot(es, ys, color=col, lw=2.0, label=lab)
        a1.axvline(e, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a1.set_xlabel("error  y − t")
        a1.set_ylabel("loss")
        a1.set_title("the losses", fontsize=9)
        c.legend(a1, loc="upper center")
        for ys, col, lab in ((g_mse, theme.ACCENT, "2(y−t)"),
                             (g_mae, theme.VIOLET, "sign"),
                             (g_hub, theme.GOOD, "clipped")):
            a2.plot(es, ys, color=col, lw=2.0, label=lab)
        a2.axvline(e, color=theme.TEXT_FAINT, lw=1.0, ls="--")
        a2.axhline(0, color=theme.BORDER, lw=0.9)
        a2.set_xlabel("error  y − t")
        a2.set_ylabel("dL/dy — what reaches the weights")
        a2.set_title("the gradients — this is the row that matters",
                     fontsize=9)
        c.legend(a2, loc="upper left")
        c.refresh()

        if abs(e) > d:
            self.tL.setText(
                f"<b>Error {e:+.2f} is outside the Huber elbow (δ = {d:.2f}), "
                f"so Huber has clipped its gradient to {np.clip(e,-d,d):+.2f} "
                f"while MSE is handing over {2*e:+.2f}.</b> That factor of "
                f"{abs(2*e)/max(1e-9, abs(np.clip(e,-d,d))):.1f} is the "
                "difference between one bad bootstrapped target nudging the "
                "critic and one bad target throwing it across the room. On a "
                "problem where targets are manufactured from the network's "
                "own guesses, the clipped version is often the only one that "
                "survives.")
        else:
            self.tL.setText(
                f"<b>Inside the elbow, Huber IS MSE</b> — the two gradient "
                f"curves coincide, both at {2*e:+.2f}/2. Note that MSE's "
                "gradient shrinks to zero as the error does, which is what "
                "lets the fit settle, whereas MAE's stays at ±1 all the way "
                "in and keeps kicking. That difference is why MSE is the "
                "default and MAE almost never is.")


# ==========================================================================
# PAGE -- regularisation, normalisation, initialisation
# ==========================================================================

class RegularisationPage(Page):
    TITLE = "Regularisation, Normalisation, Initialisation"
    SUBTITLE = ("The four things done to a network that are not the network: "
                "keep it from memorising, keep its numbers centred, start it "
                "somewhere sane, and stop one bad step from ruining it.")
    SECTION = SECTION
    NOTES = "neural nets"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>These are not decorations, and two of them are actively "
            "dangerous in RL.</b> Batch normalisation and dropout were both "
            "designed for a setting reinforcement learning does not have: a "
            "fixed dataset, i.i.d. batches, and a clean train/eval split. "
            "Inside a learner whose data distribution moves because the "
            "policy moved, both need care, and one of them is usually "
            "replaced outright. This page says which and why.", "key"))

        # ---- overfitting -------------------------------------------------
        of = Card("what regularisation is for: fitting the noise")
        of.add(body(
            "Twelve noisy samples from a smooth curve. Raise the model's "
            "capacity and the training error goes to zero — by threading "
            "through every sample, including the noise in it. The test error "
            "goes the other way. This is the whole phenomenon, and every "
            "technique below is a way of buying capacity without buying "
            "this."))
        self.s_cap = slider(1, 12, 9)
        self.s_lam = slider(0, 400, 0)
        self.s_n = slider(6, 40, 12)
        self.l_cap, self.l_lam, self.l_n = QLabel(), QLabel(), QLabel()
        of.add_layout(slider_row("capacity (poly degree)", self.s_cap,
                                 self.l_cap))
        of.add_layout(slider_row("L2 strength λ (×0.001)", self.s_lam,
                                 self.l_lam))
        of.add_layout(slider_row("training samples", self.s_n, self.l_n))
        self.st_tr = Stat("train error", "--", theme.GOOD)
        self.st_te = Stat("test error", "--", theme.BAD)
        self.st_w = Stat("largest coefficient", "--", theme.WARN)
        of.add_layout(stat_row(self.st_tr, self.st_te, self.st_w))
        self.cO = MplCanvas(width=7.6, height=2.8, ncols=2)
        of.add(self.cO)
        self.tO = body("", dim=True)
        of.add(self.tO)
        self.add(of)
        for s in (self.s_cap, self.s_lam, self.s_n):
            s.valueChanged.connect(self._redraw_overfit)
        self._redraw_overfit()

        # ---- the toolkit -------------------------------------------------
        tk = Card("the four regularisers, and the honest verdict on each "
                  "inside an RL loop")
        tk.add(_table(
            ["Technique", "What it does", "In supervised learning",
             "In an RL learner"],
            [("L2 / weight decay",
              "adds λ‖w‖² to the loss, so every weight gets pulled toward "
              "zero unless the data pays for it. Gradient picks up +2λw.",
              "The default. Cheap, one hyperparameter, never hurts much.",
              "Fine and commonly used, small (1e−4 or less). It also keeps "
              "the critic's surface from developing the enormous local slopes "
              "that make the actor's step wild."),
             ("Dropout",
              "randomly zeroes a fraction of units each forward pass during "
              "training, so no unit can rely on any other. At eval time "
              "everything is on and the outputs are rescaled.",
              "Very effective on large over-parameterised nets.",
              "Rare, and usually a mistake in the critic. It makes Q(s,a) "
              "NOISY, and the actor's gradient is a derivative of that "
              "noisy surface — you are asking for a direction from a function "
              "that changes every time you evaluate it."),
             ("Early stopping",
              "watch a held-out error and stop when it turns up.",
              "Standard practice.",
              "There is no held-out set and no 'converged' — the data "
              "distribution moves with the policy. Replaced by checkpointing "
              "on evaluated RETURN, which is a different measurement "
              "entirely."),
             ("Small networks",
              "the crudest regulariser: not enough capacity to memorise.",
              "Usually the wrong trade.",
              "Usually the right one here. Two hidden layers of 64–256 is "
              "the standard continuous-control critic, and going bigger "
              "reliably makes DDPG less stable rather than more capable.")],
            col0=125, colw=230, height=470))
        self.add(tk)

        # ---- normalisation ------------------------------------------------
        self.add(hline())
        self.add(title("Normalisation: three different things with confusingly "
                       "similar names"))

        nm = Card("input scaling, batch norm, layer norm")
        nm.add(body(
            "<b>1 · Input scaling</b> — done once, outside the network, and "
            "the one that is never optional. A state vector whose first "
            "component is a joint angle in radians (±0.5) and whose second is "
            "a stiffness in N·m/rad (±300) presents the first layer with "
            "wildly mismatched scales: the big component dominates every "
            "z, saturates the units, and the small one is invisible. Divide "
            "each component by its own typical magnitude and the problem "
            "disappears. The gait environment on the case-study page does "
            "exactly this before anything reaches a network."))
        nm.add(math_label(r"\hat{x}_j = \frac{x_j - \mu_j}{\sigma_j} "
                          r"\qquad\text{per input dimension, fixed}", 16))
        nm.add(body(
            "<b>2 · Batch normalisation</b> — a <i>layer</i>, inside the "
            "network, that normalises each feature using the mean and "
            "variance <b>of the current batch</b>, then applies a learned "
            "scale and shift so the network can undo it if it wants to:"))
        nm.add(math_label(r"\mathrm{BN}(z_j) = \gamma_j\,"
                          r"\frac{z_j - \mu_j^{\mathrm{batch}}}"
                          r"{\sqrt{\left(\sigma_j^{\mathrm{batch}}\right)^2 "
                          r"+ \epsilon}} + \beta_j", 16))
        nm.add(body(
            "It keeps every layer's inputs centred no matter how the layers "
            "beneath it drift, which allows much larger learning rates and "
            "much deeper networks. Two properties are usually glossed over "
            "and both bite in RL:<br><br>"
            "&nbsp;&nbsp;• <b>The output for sample i depends on the other "
            "samples in the batch.</b> This is the one place the "
            "\"samples don't interact\" rule from the forward-prop page is "
            "false.<br>"
            "&nbsp;&nbsp;• <b>It behaves differently at training time and at "
            "run time.</b> At run time there is no batch, so it uses a running "
            "average collected during training."))
        nm.add(callout(
            "<b>Why batch norm and DDPG fight.</b> Four separate reasons, and "
            "they compound:<br><br>"
            "&nbsp;&nbsp;<b>1.</b> The controller calls the actor with a "
            "<b>batch of one</b>, at 1 kHz, while the learner trains it with "
            "batches of 64. The statistics are different, so the deployed "
            "policy is not the policy that was trained.<br>"
            "&nbsp;&nbsp;<b>2.</b> The <b>target networks</b> are copies. A "
            "copy has to include the running statistics too, and those crawl "
            "at a different rate than the weights do — a subtle, silent "
            "mismatch in the very quantity the algorithm needs to hold "
            "still.<br>"
            "&nbsp;&nbsp;<b>3.</b> The replay buffer is <b>off-policy</b>: a "
            "batch drawn from it mixes transitions from policies months "
            "apart, so the batch statistics do not describe any single "
            "distribution.<br>"
            "&nbsp;&nbsp;<b>4.</b> The actor's gradient is ∂Q/∂a. With batch "
            "norm in the critic, Q for one sample depends on the other 63 "
            "actions in the batch, so that derivative is no longer a clean "
            "statement about this state.<br><br>"
            "<b>The fix the field settled on is layer normalisation</b> — "
            "same idea, but the mean and variance are taken across the "
            "features of a <i>single sample</i>. No batch dependence, no "
            "train/run difference, no running statistics to copy. TD3 and SAC "
            "implementations use it routinely; the original DDPG paper used "
            "batch norm and it is one of the things later work quietly "
            "dropped.", "warn"))
        nm.add(body(
            "<b>3 · Layer normalisation</b>, for completeness: normalise "
            "z over the units of one layer for one sample, then the same "
            "learned γ and β. Everything else about it is identical to batch "
            "norm and none of the four problems above apply.", dim=True))
        self.add(nm)

        # ---- initialisation ------------------------------------------------
        self.add(hline())
        self.add(title("Initialisation, and the one line of it that is "
                       "RL-specific"))

        ini = Card("where the weights start decides whether they can move at "
                   "all")
        ini.add(_code(get_source(Dense.__init__)))
        ini.add(body(
            "<b>scale = √(1/n_in)</b> is the whole idea. A unit with 64 "
            "inputs sums 64 products; if the weights were drawn from a fixed "
            "range regardless of fan-in, that sum would grow with the width "
            "of the previous layer, z would land far out on the tanh, σ′(z) "
            "would be ~0, and the layer would be born saturated and unable to "
            "learn. Scaling the draw by 1/√n<sub>in</sub> keeps the variance "
            "of z near 1 whatever the width. (Xavier/Glorot for tanh, He for "
            "ReLU — same argument, factor of 2 apart because ReLU discards "
            "half its input.)"))
        ini.add(callout(
            "<b>And the deliberately tiny final layer — scale = 3e−3 — is a "
            "reinforcement-learning trick, not a general one.</b> It makes "
            "the network's <i>output</i> start near zero, and that means two "
            "specific things here:<br><br>"
            "&nbsp;&nbsp;• The <b>actor</b> starts by commanding almost zero "
            "action. On a robot that is the only acceptable behaviour on "
            "step one, and it also starts tanh in its steep middle rather "
            "than pinned at ±1, where its slope would be ~0 and the actor "
            "could never move.<br>"
            "&nbsp;&nbsp;• The <b>critic</b> starts by predicting Q ≈ 0 "
            "everywhere, which is a flat, honest \"I know nothing\" rather "
            "than a random landscape of confident peaks and troughs for the "
            "actor to run off toward before any reward has been seen.<br><br>"
            "It is three characters in a constructor and it is in the DDPG "
            "paper for a reason.", "good"))
        ini.add(body(
            "<b>Gradient clipping</b> is the last item and it belongs with "
            "these: rescale the whole gradient vector if its norm exceeds "
            "some bound, so a single freak target cannot produce a single "
            "enormous step. It does not change the direction, only the "
            "length. In a method whose targets are manufactured from its own "
            "predictions, occasional freak targets are not a possibility, "
            "they are a certainty.", dim=True))
        self.add(ini)

        self.add(callout(
            "<b>Carry forward, and this is the end of the fundamentals "
            "block.</b> You now have: a neuron, a layer, a forward pass, a "
            "backward pass that multiplies along paths and sums across them, "
            "a loss that seeds it, and the housekeeping that keeps the "
            "numbers in range. Everything from here on is those pieces "
            "arranged into agents — starting with why the table has to go.",
            "good"))
        self.finish()

    # ------------------------------------------------------------------
    def _redraw_overfit(self):
        deg = self.s_cap.value()
        lam = self.s_lam.value() / 1000.0
        n = self.s_n.value()
        self.l_cap.setText(f"{deg}")
        self.l_lam.setText(f"{lam:.3f}")
        self.l_n.setText(f"{n}")

        rng = np.random.default_rng(3)
        xs = np.linspace(-1, 1, n)
        truth = lambda x: np.sin(2.4 * x) * 0.8
        ys = truth(xs) + rng.normal(0, 0.16, size=n)
        xt = np.linspace(-1, 1, 200)
        yt = truth(xt)

        # ridge regression on a polynomial basis -- the smallest honest model
        # in which capacity and L2 are both one number
        A = np.vander(xs, deg + 1, increasing=True)
        reg = lam * np.eye(deg + 1)
        reg[0, 0] = 0.0                      # never penalise the constant
        coef = np.linalg.solve(A.T @ A + reg, A.T @ ys)
        fit_tr = np.vander(xs, deg + 1, increasing=True) @ coef
        fit_te = np.vander(xt, deg + 1, increasing=True) @ coef

        e_tr = float(np.mean((fit_tr - ys) ** 2))
        e_te = float(np.mean((fit_te - yt) ** 2))
        self.st_tr.set(f"{e_tr:.4f}")
        self.st_te.set(f"{e_te:.4f}")
        self.st_te.set_color(theme.GOOD if e_te < 0.02 else theme.BAD)
        self.st_w.set(f"{np.abs(coef).max():.1f}")
        self.st_w.set_color(theme.BAD if np.abs(coef).max() > 50
                            else theme.WARN)

        c = self.cO
        c.clear()
        a1, a2 = c.axes
        a1.plot(xt, yt, color=theme.TEXT_FAINT, lw=1.6, ls="--",
                label="the truth")
        a1.scatter(xs, ys, s=26, color=theme.WARN, zorder=5,
                   label="noisy samples")
        a1.plot(xt, fit_te, color=theme.ACCENT, lw=2.2, label="the fit")
        a1.set_ylim(-1.8, 1.8)
        a1.set_title(f"degree {deg}, λ = {lam:.3f}", fontsize=9)
        c.legend(a1, loc="lower right")

        degs = list(range(1, 13))
        tr, te = [], []
        for dd in degs:
            Ad = np.vander(xs, dd + 1, increasing=True)
            rg = lam * np.eye(dd + 1)
            rg[0, 0] = 0.0
            cf = np.linalg.solve(Ad.T @ Ad + rg, Ad.T @ ys)
            tr.append(float(np.mean((Ad @ cf - ys) ** 2)))
            te.append(float(np.mean(
                (np.vander(xt, dd + 1, increasing=True) @ cf - yt) ** 2)))
        a2.semilogy(degs, tr, color=theme.GOOD, lw=2.0, marker="o", ms=3,
                    label="train")
        a2.semilogy(degs, te, color=theme.BAD, lw=2.0, marker="o", ms=3,
                    label="test")
        a2.axvline(deg, color=theme.ACCENT, lw=1.2, ls="--")
        a2.set_xlabel("capacity")
        a2.set_ylabel("error (log)")
        a2.set_title("the two curves that never agree", fontsize=9)
        c.legend(a2, loc="upper center")
        c.refresh()

        if e_te > 4 * e_tr and lam < 1e-6:
            self.tO.setText(
                f"<b>Train {e_tr:.4f}, test {e_te:.4f} — a factor of "
                f"{e_te/max(1e-9,e_tr):.0f}.</b> The fit passes through the "
                "samples and does something absurd between them, and the "
                "largest coefficient has grown to "
                f"{np.abs(coef).max():.0f}: that is what memorisation looks "
                "like numerically, and it is why penalising the SIZE of the "
                "weights works as a cure. Push λ up a little and watch both "
                "the wiggles and the coefficient collapse — the model keeps "
                "its capacity and stops being allowed to use it.")
        elif lam > 0.05:
            self.tO.setText(
                f"<b>λ = {lam:.3f} is now doing more harm than good.</b> "
                "Train and test error are both rising: the penalty is "
                "overwhelming the data, and the fit is being dragged toward a "
                "flat line regardless of what the samples say. That is "
                "underfitting, and it is the failure at the other end. λ is "
                "not 'more is safer'.")
        else:
            self.tO.setText(
                f"<b>Train {e_tr:.4f}, test {e_te:.4f}.</b> Add samples and "
                "watch the gap close on its own — more data is the "
                "regulariser that costs no bias, and it is exactly what a "
                "replay buffer is quietly providing when it lets one real "
                "transition be reused hundreds of times.")
