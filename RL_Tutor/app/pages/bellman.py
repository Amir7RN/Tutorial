"""
Pages 12-15: the four Bellman equations, one page each.

Page 11 shows all four at once, which is the right summary and the wrong place to
learn them. These four pages take one equation each and grind it down to
arithmetic you can watch happen.

  12  V^pi   Bellman EXPECTATION for the state value
  13  Q^pi   Bellman EXPECTATION for the action value
  14  V*     Bellman OPTIMALITY  for the state value
  15  Q*     Bellman OPTIMALITY  for the action value

--------------------------------------------------------------------------
THE ONE MENTAL MODEL ALL FOUR PAGES REUSE
--------------------------------------------------------------------------

There are exactly TWO dice between "I am standing here" and "I have landed
somewhere with money in my pocket":

    die 1   WHICH BUTTON gets pressed      the agent rolls it     pi(a|s)
    die 2   WHERE THE ICE PUTS YOU         the world rolls it     P(s'|s,a)

Die 2 is always averaged. You never get to choose where the ice throws you, so
`max` can never appear on the s' sum. Not in any of the four equations. Ever.

Die 1 is the only thing that differs between the four:

                    | choice happens NOW        | choice already made NOW
    ----------------+---------------------------+--------------------------
    follow pi       | V^pi   average now        | Q^pi   average one step later
    act optimally   | V*     max now            | Q*     max one step later

Read the right-hand column twice. The Q equations are the V equations with the
action-choice DELAYED BY ONE STEP -- because Q's first action is handed to you,
so the choosing cannot show up until the next state. That single sentence is what
makes Q*(s,a) stop looking arbitrary.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from rlcore.dp import (
    policy_evaluation_exact,
    policy_evaluation_history,
    policy_evaluation_stochastic,
    q_value_iteration_history,
    value_iteration,
    value_iteration_operator,
)
from rlcore.frozen_lake import (
    ACTION_ARROWS,
    ACTION_NAMES,
    N_ACTIONS,
    N_STATES,
    cell_kind,
    deterministic_to_probs,
    is_terminal,
    merge_duplicates,
    q_from_V,
    q_table_from_V,
)
from .. import theme
from ..widgets import (
    Card,
    CodePane,
    GridView,
    MplCanvas,
    Stat,
    body,
    callout,
    get_source,
    labelled,
    math_label,
    stat_row,
)
from .base import EnvControls, Page

# how many merged branches / children the backup tree is willing to draw
MAX_BRANCH = 3


# ==========================================================================
# Shared: the 2x2 map, so you always know which of the four you are looking at
# ==========================================================================

_MAP_CELLS = {
    "exp_v": ("V<sup>π</sup>(s)", "average over π <b>now</b>"),
    "exp_q": ("Q<sup>π</sup>(s,a)", "average over π <b>one step later</b>"),
    "opt_v": ("V<sup>*</sup>(s)", "<b>max</b> now"),
    "opt_q": ("Q<sup>*</sup>(s,a)", "<b>max</b> one step later"),
}


def bellman_map(active: str) -> Card:
    """A 2x2 orientation table with the current page's cell lit up."""
    def cell(key):
        name, what = _MAP_CELLS[key]
        on = (key == active)
        bg = "rgba(76,154,255,0.16)" if on else "transparent"
        col = theme.ACCENT if on else theme.TEXT_DIM
        return (f"<td style='background:{bg}; padding:7px 11px; "
                f"border:1px solid {theme.BORDER};'>"
                f"<span style='color:{col}; font-size:14px; font-weight:700'>"
                f"{name}</span><br>"
                f"<span style='color:{theme.TEXT_FAINT}; font-size:11px'>"
                f"{what}</span></td>")

    c = Card("where you are — the four equations are one 2×2 grid")
    c.add(body(
        "<table cellspacing='0' cellpadding='0'>"
        "<tr>"
        f"<td style='padding:6px 11px; color:{theme.TEXT_FAINT}; font-size:11px'></td>"
        f"<td style='padding:6px 11px; color:{theme.TEXT_FAINT}; font-size:11px'>"
        "anchored at a <b>square</b> — you have<br>not pressed anything yet</td>"
        f"<td style='padding:6px 11px; color:{theme.TEXT_FAINT}; font-size:11px'>"
        "anchored at a <b>square + button</b> —<br>the first press is already forced</td>"
        "</tr><tr>"
        f"<td style='padding:6px 11px; color:{theme.TEXT_DIM}; font-size:11px'>"
        "<b>EXPECTATION</b><br>score the policy you have</td>"
        + cell("exp_v") + cell("exp_q") +
        "</tr><tr>"
        f"<td style='padding:6px 11px; color:{theme.TEXT_DIM}; font-size:11px'>"
        "<b>OPTIMALITY</b><br>define the best policy</td>"
        + cell("opt_v") + cell("opt_q") +
        "</tr></table>"))
    c.add(body(
        "Left column: the choice is <b>still ahead of you</b>, so the equation "
        "handles it immediately. Right column: the choice is <b>behind you</b>, so "
        "the equation cannot touch it until the next square — which is why every Q "
        "equation has its π-average or its max sitting <i>inside</i> the sum over "
        "s', one step downstream.", dim=True))
    return c


# ==========================================================================
# Shared: the backup tree, painted with real numbers off the real lake
# ==========================================================================

class BackupTree(QWidget):
    """
    The one-step backup, drawn with the actual numbers for one state.

      mode     top node   first layer down        second layer down
      -----    ---------  ----------------------  ------------------------
      exp_v    s          π(a|s)  → averaged      P(s'|s,a) → averaged
      opt_v    s          max_a   → best one wins P(s'|s,a) → averaged
      exp_q    (s,a)      P(s'|s,a) → averaged    π(a'|s')  → averaged
      opt_q    (s,a)      P(s'|s,a) → averaged    max_a'    → best one wins

    Look at the layer ORDER, not just the operators. The V modes choose on the
    first layer; the Q modes choose on the second. Same two dice, opposite order.
    """

    def __init__(self, mode: str, parent=None, height=300):
        super().__init__(parent)
        self.mode = mode
        self.setMinimumHeight(height)
        self.setStyleSheet("background: transparent;")

        self.P = None
        self.V: list[float] | None = None
        self.Q: list[list[float]] | None = None
        self.probs: list[list[float]] | None = None
        self.gamma = 0.99
        self.s = 9
        self.a = 1

    def set_data(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)
        self.update()

    # -- painting helpers ------------------------------------------------
    def _dot(self, p, x, y, r, colour, filled=True):
        p.setPen(QPen(QColor(colour), 2))
        p.setBrush(QColor(colour) if filled else Qt.NoBrush)
        p.drawEllipse(int(x - r), int(y - r), int(2 * r), int(2 * r))

    def _txt(self, p, x, y, text, colour, size=8, bold=False, w=110,
             family="Consolas"):
        p.setPen(QColor(colour))
        f = QFont(family, size)
        f.setBold(bold)
        p.setFont(f)
        p.drawText(int(x - w / 2), int(y - 8), int(w), 17, Qt.AlignCenter, text)

    def _branches(self, s, a):
        return merge_duplicates(self.P[s][a])[:MAX_BRANCH]

    def _bracket(self, t):
        """The value of [ r + γ·V(s') ] on one branch."""
        boot = 0.0 if t.done else self.V[t.next_state]
        return t.reward + self.gamma * boot

    # ------------------------------------------------------------------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self.P is None or self.V is None:
            return
        if is_terminal(self.s):
            self._txt(p, self.width() / 2, self.height() / 2,
                      f"state {self.s} is terminal — the tree has no branches",
                      theme.WARN, 10, True, w=self.width(), family="Segoe UI")
            return
        if self.mode in ("exp_v", "opt_v"):
            self._paint_v(p)
        else:
            self._paint_q(p)
        p.end()

    # ---- V modes: choose on the FIRST layer ----------------------------
    def _paint_v(self, p):
        w, h = self.width(), self.height()
        y_root, y_act, y_leaf = 62, h * 0.50, h - 66
        cx = w / 2
        opt = (self.mode == "opt_v")
        qrow = [q_from_V(self.P, self.V, self.s, a, self.gamma)
                for a in range(N_ACTIONS)]
        best = max(range(N_ACTIONS), key=lambda a: qrow[a])

        cap = ("MAX over a — one action is kept, three are thrown away"
               if opt else
               "Σ over a weighted by π(a|s) — every action contributes")
        self._txt(p, cx, 14, "layer 1 (your die):  " + cap,
                  theme.GOOD if opt else theme.VIOLET, 9, True, w=w,
                  family="Segoe UI")

        self._txt(p, cx, y_root - 24, f"s = {self.s}", theme.TEXT, 11, True)
        self._dot(p, cx, y_root, 9, theme.ACCENT)

        for a in range(N_ACTIONS):
            ax = w * (0.155 + a * 0.23)
            hot = (not opt) or (a == best)
            col = (theme.GOOD if (opt and a == best)
                   else theme.TEXT_FAINT if opt else theme.VIOLET)

            p.setPen(QPen(QColor(col), 2.6 if hot else 1.0))
            p.drawLine(int(cx), int(y_root + 9), int(ax), int(y_act - 26))
            lab = (("WINNER" if a == best else "not taken") if opt
                   else f"π={self.probs[self.s][a]:.2f}")
            self._txt(p, cx + (ax - cx) * 0.46, y_root + (y_act - y_root) * 0.46,
                      lab, col if hot else theme.TEXT_FAINT, 8, hot, w=86)

            # name and Q on ONE line above the node, so the fan below stays clear
            self._txt(p, ax, y_act - 22,
                      f"{ACTION_ARROWS[a]} {ACTION_NAMES[a]}   Q={qrow[a]:+.3f}",
                      theme.TEXT if hot else theme.TEXT_FAINT, 9, hot, w=210,
                      family="Segoe UI")
            self._dot(p, ax, y_act, 7, col, filled=hot)

            br = self._branches(self.s, a)
            n = len(br)
            for j, t in enumerate(br):
                sx = ax + (j - (n - 1) / 2) * w * 0.064
                cyan = QColor(theme.CYAN)
                cyan.setAlphaF(0.35 + 0.65 * min(1.0, t.prob) if hot else 0.18)
                p.setPen(QPen(cyan, 1.2 + 3.2 * min(1.0, t.prob)))
                p.drawLine(int(ax), int(y_act + 7), int(sx), int(y_leaf - 9))
                self._txt(p, ax + (sx - ax) * 0.55 + 14,
                          y_act + (y_leaf - y_act) * 0.55, f"{t.prob:.2f}",
                          theme.CYAN if hot else theme.TEXT_FAINT, 7, w=44)
                self._dot(p, sx, y_leaf, 9, theme.CYAN if hot else theme.BORDER)
                self._txt(p, sx, y_leaf, str(t.next_state),
                          theme.BG if hot else theme.TEXT_FAINT, 7, True)
                self._txt(p, sx, y_leaf + 20, f"{self._bracket(t):+.3f}",
                          theme.TEXT_DIM if hot else theme.TEXT_FAINT, 7)

        self._txt(p, cx, h - 14,
                  "layer 2 (the ice's die):  Σ over s' weighted by P(s'|s,a) — "
                  "never a max.   leaf number = [ r + γ·V(s') ]",
                  theme.CYAN, 9, True, w=w, family="Segoe UI")

    # ---- Q modes: choose on the SECOND layer ---------------------------
    def _paint_q(self, p):
        w, h = self.width(), self.height()
        y_root, y_succ, y_leaf = 62, h * 0.46, h - 84
        cx = w / 2
        opt = (self.mode == "opt_q")

        self._txt(p, cx, 14,
                  "layer 1 (the ice's die):  Σ over s' weighted by P(s'|s,a) — "
                  "your action is already spent, so nothing is chosen here",
                  theme.CYAN, 9, True, w=w, family="Segoe UI")

        self._txt(p, cx, y_root - 26,
                  f"s = {self.s},  a = {ACTION_ARROWS[self.a]} "
                  f"{ACTION_NAMES[self.a]}  (already forced)",
                  theme.TEXT, 11, True, w=360, family="Segoe UI")
        self._dot(p, cx, y_root, 9, theme.ACCENT)

        br = self._branches(self.s, self.a)
        n = len(br)
        for j, t in enumerate(br):
            sx = cx + (j - (n - 1) / 2) * w * 0.30
            cyan = QColor(theme.CYAN)
            cyan.setAlphaF(0.4 + 0.6 * min(1.0, t.prob))
            p.setPen(QPen(cyan, 1.4 + 3.4 * min(1.0, t.prob)))
            p.drawLine(int(cx), int(y_root + 9), int(sx), int(y_succ - 10))
            self._txt(p, cx + (sx - cx) * 0.5, y_root + (y_succ - y_root) * 0.5,
                      f"P={t.prob:.2f}", theme.CYAN, 8, True, w=70)
            self._dot(p, sx, y_succ, 10, theme.CYAN)
            self._txt(p, sx, y_succ, str(t.next_state), theme.BG, 8, True)
            # reward to the SIDE of the node -- the action fan owns the space below
            self._txt(p, sx + 56, y_succ, f"r={t.reward:+.2f}", theme.TEXT_DIM, 8,
                      w=76)

            if t.done:
                self._txt(p, sx, y_leaf, "terminal — no future,",
                          theme.WARN, 8, True, w=170, family="Segoe UI")
                self._txt(p, sx, y_leaf + 16, "the branch stops at r",
                          theme.WARN, 8, False, w=170, family="Segoe UI")
                continue

            ns = t.next_state
            qrow = self.Q[ns]
            best = max(range(N_ACTIONS), key=lambda a2: qrow[a2])
            for a2 in range(N_ACTIONS):
                lx = sx + (a2 - 1.5) * w * 0.058
                hot = (not opt) or (a2 == best)
                col = (theme.GOOD if (opt and a2 == best)
                       else theme.TEXT_FAINT if opt else theme.VIOLET)
                p.setPen(QPen(QColor(col), 2.2 if hot else 0.9))
                p.drawLine(int(sx), int(y_succ + 10), int(lx), int(y_leaf - 7))
                self._dot(p, lx, y_leaf, 6, col, filled=hot)
                self._txt(p, lx, y_leaf - 18,
                          (f"π={self.probs[ns][a2]:.2f}" if not opt
                           else ("max" if a2 == best else "")),
                          col, 7, hot, w=56)
                self._txt(p, lx, y_leaf + 18, ACTION_ARROWS[a2],
                          theme.TEXT if hot else theme.TEXT_FAINT, 9, hot,
                          family="Segoe UI")
                self._txt(p, lx, y_leaf + 33, f"{qrow[a2]:+.2f}",
                          theme.TEXT_DIM if hot else theme.TEXT_FAINT, 7)

        cap = ("MAX over a' — the choice comes back at the NEXT square"
               if opt else
               "Σ over a' weighted by π(a'|s') — the π-average, one step late")
        self._txt(p, cx, h - 14, "layer 2 (your die, delayed):  " + cap,
                  theme.GOOD if opt else theme.VIOLET, 9, True, w=w,
                  family="Segoe UI")


# ==========================================================================
# Shared: four sliders that edit pi(a|s) at ONE square
# ==========================================================================

class PolicyMixer(Card):
    """
    Edit π(a|s) at the selected square and watch V^π move.

    The point of letting you drag these: V^π is a property OF A POLICY. There is
    no "value of square 9" — only "value of square 9 if you behave like this".
    """

    changed = Signal()
    preset = Signal(str)

    def __init__(self, parent=None):
        super().__init__("π(a|s) at the selected square — drag these", parent)
        self.sliders: list[QSlider] = []
        self.labels: list[QLabel] = []

        grid = QGridLayout()
        grid.setSpacing(6)
        grid.setColumnStretch(1, 1)
        for a in range(N_ACTIONS):
            nm = QLabel(f"{ACTION_ARROWS[a]} {ACTION_NAMES[a]}")
            nm.setStyleSheet(f"color:{theme.TEXT_DIM}; background:transparent;")
            nm.setFixedWidth(78)
            sl = QSlider(Qt.Horizontal)
            sl.setRange(0, 100)
            sl.setValue(25)
            sl.valueChanged.connect(self._emit)
            vl = QLabel("0.25")
            vl.setStyleSheet(
                f"color:{theme.VIOLET}; font-family:Consolas; font-weight:700;"
                f"background:transparent; min-width:40px;")
            grid.addWidget(nm, a, 0)
            grid.addWidget(sl, a, 1)
            grid.addWidget(vl, a, 2)
            self.sliders.append(sl)
            self.labels.append(vl)
        self.add_layout(grid)

        btns = QHBoxLayout()
        btns.setSpacing(6)
        for key, text in (("uniform", "uniform"), ("greedy", "greedy (one-hot)"),
                          ("base", "match base π")):
            b = QPushButton(text)
            b.clicked.connect(lambda _=False, k=key: self.preset.emit(k))
            btns.addWidget(b)
        btns.addStretch(1)
        self.add_layout(btns)

        self.add(body(
            "The sliders are renormalised to sum to 1 — they are probabilities, "
            "not weights. Everything else on the page keeps the <i>base</i> policy; "
            "only this one square is overridden.", dim=True))

    def row(self) -> list[float]:
        raw = [s.value() for s in self.sliders]
        tot = sum(raw)
        if tot == 0:
            return [1.0 / N_ACTIONS] * N_ACTIONS
        return [v / tot for v in raw]

    def set_row(self, row: list[float]):
        for a, sl in enumerate(self.sliders):
            sl.blockSignals(True)
            sl.setValue(int(round(row[a] * 100)))
            sl.blockSignals(False)
        self._refresh_labels()

    def _refresh_labels(self):
        for a, v in enumerate(self.row()):
            self.labels[a].setText(f"{v:.2f}")

    def _emit(self):
        self._refresh_labels()
        self.changed.emit()


# ==========================================================================
# Shared: base-policy picker used by both expectation pages
# ==========================================================================

def base_probs(P, gamma, which: int) -> list[list[float]]:
    """probs[s][a] for the four base policies offered in the combo boxes."""
    if which == 0:                                   # optimal
        pi, _, _ = value_iteration(P, gamma=gamma, theta=1e-12)
        return deterministic_to_probs(pi)
    if which == 1:                                   # uniform random
        return [[1.0 / N_ACTIONS] * N_ACTIONS for _ in range(N_STATES)]
    if which == 2:                                   # always DOWN
        return deterministic_to_probs([1] * N_STATES)
    return deterministic_to_probs([2] * N_STATES)     # always RIGHT


BASE_LABELS = ["base π = optimal (π*)", "base π = uniform random",
               "base π = always DOWN", "base π = always RIGHT"]


def detail_box(min_height=270) -> QLabel:
    """The monospace arithmetic panel used on all four pages."""
    lb = QLabel()
    lb.setWordWrap(True)
    lb.setTextFormat(Qt.RichText)
    lb.setAlignment(Qt.AlignTop)
    lb.setTextInteractionFlags(Qt.TextSelectableByMouse)
    lb.setStyleSheet(
        f"background:{theme.BG_INPUT}; border:1px solid {theme.BORDER};"
        f"border-radius:8px; padding:12px; font-family:Consolas; font-size:12px;")
    lb.setMinimumHeight(min_height)
    return lb


def observed_rate(errs) -> float | None:
    """
    The per-sweep shrink factor actually achieved, as a geometric mean.

    Worth surfacing, because γ^k is only the WORST-CASE bound. On a 4x4 lake with
    absorbing holes and a goal, most chains of states end after a handful of hops,
    so the real error dies far faster than γ^k -- at γ=0.99 you typically see
    ~0.6/sweep, not 0.99/sweep. Printing both stops the plot from looking like it
    disagrees with the theorem.
    """
    good = [e for e in errs if e > 1e-13]
    if len(good) < 3:
        return None
    return (good[-1] / good[0]) ** (1.0 / (len(good) - 1))


def waterfall(ax, labels, contribs, total, title, colour=theme.CYAN):
    """
    Contribution waterfall: each branch's p·[r+γV] stacked onto a running total,
    with the final bar being the answer. Makes "a sum of signed pieces" visible in
    a way a table of numbers does not.
    """
    run = 0.0
    for i, (lb, c) in enumerate(zip(labels, contribs)):
        col = theme.GOOD if c >= 0 else theme.BAD
        ax.bar(i, c, bottom=run, color=col, alpha=0.85, width=0.62)
        ax.plot([i - 0.31, i + 0.31], [run + c, run + c], color=theme.TEXT_FAINT,
                lw=0.8)
        if i:
            ax.plot([i - 1 + 0.31, i - 0.31], [run, run],
                    color=theme.TEXT_FAINT, lw=0.7, ls=":")
        run += c
    ax.bar(len(contribs), total, color=colour, alpha=0.95, width=0.62)
    ax.axhline(0, color=theme.BORDER, lw=1)
    ax.set_xticks(range(len(labels) + 1))
    ax.set_xticklabels(list(labels) + ["TOTAL"], fontsize=7, rotation=0)
    ax.set_title(title)


# ==========================================================================
# PAGE 12 -- Bellman expectation for V
# ==========================================================================

class BellmanExpVPage(Page):
    TITLE = "Bellman ① — V^π (expectation)"
    SUBTITLE = ("Two dice, both averaged. \"How good is this square if I keep "
                "behaving exactly the way I behave?\"")
    SECTION = "Value Functions"
    NOTES = "notes p.1 · p.5"

    def __init__(self, parent=None):
        super().__init__(parent)

        # ---- the words first, the symbols second ---------------------------
        self.add(callout(
            "<b>Say it out loud, no symbols.</b><br><br>"
            "You are standing on square <b>s</b> and you have <b>not pressed "
            "anything yet</b>. Two things are still random.<br><br>"
            "<b>1. Which button you press.</b> Your policy is a habit, not a law: "
            "it presses ↓ some fraction of the time, → some fraction, and so on. "
            "That fraction is π(a|s).<br>"
            "<b>2. Where the ice dumps you</b> once you have pressed. That is "
            "P(s'|s,a), and it is not yours.<br><br>"
            "So: <b>walk every combination of the two.</b> For each button you "
            "might press, and for each square the ice might slide you onto, that "
            "branch pays you <b>the reward on that landing, plus γ times the number "
            "already written on the square you land on</b>. Weight the branch by "
            "how likely it is — how often you press that button, times how often "
            "the ice does that. Add up every branch. That total is V<sup>π</sup>(s).",
            "key", "READ IT IN PLAIN ENGLISH"))

        self.add(bellman_map("exp_v"))

        # ---- the formula, term by term --------------------------------------
        f = Card("the same sentence, in symbols")
        f.add(math_label(
            r"V^\pi(s) \;=\; \sum_a \pi(a\mid s) \;\sum_{s'} P(s'\mid s,a)"
            r"\left[\, r \;+\; \gamma\, V^\pi(s') \,\right]", 16))
        f.add(body(
            f"<span style='color:{theme.VIOLET}'>Σ<sub>a</sub> π(a|s)</span> is your "
            f"die &nbsp;·&nbsp; "
            f"<span style='color:{theme.CYAN}'>Σ<sub>s'</sub> P(s'|s,a)</span> is the "
            f"ice's die &nbsp;·&nbsp; both are averages, neither is a choice."))
        f.add(body(
            "<table cellspacing='0' cellpadding='5'>"
            f"<tr><td style='color:{theme.ACCENT}; font-family:Consolas'>Σ<sub>a</sub></td>"
            "<td>for every button you <i>might</i> press</td></tr>"
            f"<tr><td style='color:{theme.ACCENT}; font-family:Consolas'>π(a|s)</td>"
            "<td>how often you actually press it — <b>your</b> die</td></tr>"
            f"<tr><td style='color:{theme.ACCENT}; font-family:Consolas'>Σ<sub>s'</sub></td>"
            "<td>for every square the ice might dump you on</td></tr>"
            f"<tr><td style='color:{theme.ACCENT}; font-family:Consolas'>P(s'|s,a)</td>"
            "<td>how likely that particular landing is — <b>the world's</b> die</td></tr>"
            f"<tr><td style='color:{theme.ACCENT}; font-family:Consolas'>r</td>"
            "<td>cash paid <i>on that specific landing</i>. A hole branch pays −1, "
            "a plain-ice branch pays −0.04. It is <b>per branch</b>, not per state</td></tr>"
            f"<tr><td style='color:{theme.ACCENT}; font-family:Consolas'>γ·V<sup>π</sup>(s')</td>"
            "<td>everything that happens after, already crushed into one number "
            "by the previous sweep</td></tr>"
            "</table>"))
        self.add(f)

        self.add(callout(
            "<b>The bracket is a SUM, not a product.</b> Every branch contributes<br>"
            "&nbsp;&nbsp;<code>p × ( r + γ·V(s') )</code><br>"
            "and never <code>p × r × γ × V(s')</code>. The reward is <i>added</i> to "
            "the discounted future, because you collect it <i>and then</i> continue — "
            "you do not collect it <i>times</i> continuing. Only the probability "
            "multiplies, because it is a weight.", "bad"))

        self.add(callout(
            "<b>Same idea with no lake in it.</b> Your morning commute. Some days "
            "you take the bus, some days you walk — that is π. Traffic is different "
            "every day whatever you chose — that is P. \"How long does my commute "
            "take?\" is not answerable for one day; it is an <b>average over your "
            "own habits and over the traffic</b>. Change your habits and the answer "
            "changes, even though the roads did not. That is why V is written "
            "V<sup>π</sup> and never just V.", "good", "INTUITIVE EXAMPLE"))

        # ---- the tree -------------------------------------------------------
        t = Card("the backup tree, with this lake's real numbers")
        self.tree = BackupTree("exp_v", height=340)
        t.add(self.tree)
        self.add(t)

        # ---- interactive ----------------------------------------------------
        ctl = Card("controls")
        self.env = EnvControls(slip="classic", reward="shaped", gamma=0.99,
                              heading="environment")
        self.env.changed.connect(self.recompute)
        self.basebox = QComboBox()
        self.basebox.addItems(BASE_LABELS)
        self.basebox.currentIndexChanged.connect(self._base_changed)
        ctl.add_layout(labelled("Base π", self.basebox, 54))
        ctl.add(self.env)

        self.mixer = PolicyMixer()
        self.mixer.changed.connect(self.recompute)
        self.mixer.preset.connect(self._preset)

        gcard = Card("V^π(s) — click a square to inspect it")
        self.grid = GridView(cell=86)
        self.grid.clickable = True
        self.grid.selected = 9
        self.grid.value_fmt = "{:.3f}"
        self.grid.show_policy = False
        self.grid.cellClicked.connect(self._state_changed)
        gcard.add(self.grid)
        self.st_v = Stat("V^π(s) here", "-", theme.ACCENT)
        self.st_best = Stat("max_a Q^π(s,a)", "-", theme.GOOD)
        self.st_worst = Stat("min_a Q^π(s,a)", "-", theme.BAD)
        gcard.add_layout(stat_row(self.st_v, self.st_best, self.st_worst))

        self.row(gcard, ctl, self.mixer, stretches=[0, 1, 1])

        d = Card("every branch of both dice, added up")
        self.detail = detail_box(330)
        d.add(self.detail)
        self.add(d)

        # ---- plots -----------------------------------------------------------
        pc = Card("V^π is trapped between the worst and the best Q")
        self.canvas = MplCanvas(width=11.0, height=3.5, ncols=2)
        pc.add(self.canvas)
        pc.add(body(
            "<b>Left:</b> the four Q<sup>π</sup>(s,a) as bars, bar opacity = "
            "π(a|s), dashed line = V<sup>π</sup>(s). The dashed line is literally "
            "the weighted average of the bars — drag a slider and watch it slide "
            "between them.<br>"
            "<b>Right:</b> hand a fraction <i>p</i> of your probability to the "
            "best-looking action and keep the rest on your habit. V<sup>π</sup>(s) "
            "climbs towards the green line, which is V*(s) — and never crosses it. "
            "It only <i>touches</i> the line if the action you are feeding is the "
            "genuinely optimal one and the rest of the lake is already playing "
            "optimally too; otherwise it levels off short. Either way, no "
            "reshuffling of an average can beat being allowed to choose, and that "
            "gap is exactly what the <b>max</b> in the optimality equation buys "
            "you.<br>"
            "The curve is nearly straight but not quite: V<sup>π</sup>(s) is a "
            "weighted average of Q values that <i>themselves</i> depend on what you "
            "do at s, because paths can loop back here. That faint bend is the loop.",
            dim=True))
        self.add(pc)

        cc = Card("two ways to solve the same equation")
        self.canvas2 = MplCanvas(width=11.0, height=2.9)
        cc.add(self.canvas2)
        self.st_iter = Stat("iterative V(s), 4000 sweeps", "-", theme.ACCENT)
        self.st_exact = Stat("exact V(s)", "-", theme.VIOLET)
        self.st_gap = Stat("disagreement", "-", theme.GOOD)
        cc.add_layout(stat_row(self.st_iter, self.st_exact, self.st_gap))
        self.gap_note = body("")
        cc.add(self.gap_note)
        cc.add(callout(
            "<b>The expectation equation is LINEAR.</b> Every V(s') appears "
            "multiplied by a constant and added — nothing is inside a max. So this "
            "is 16 simultaneous equations in 16 unknowns and you can just "
            "<i>solve</i> it: <code>(I − γP<sub>π</sub>)V = r<sub>π</sub></code>. "
            "The sweeps are one way; the matrix inverse is the other, and they agree "
            "to floating-point dust.<br><br>"
            "This is precisely what you <b>cannot</b> do to the optimality equation "
            "two pages from now. <code>max</code> is not linear, so there is no "
            "matrix to invert and iteration stops being a convenience and becomes "
            "the only road in.", "key"))
        cp = CodePane(get_source(policy_evaluation_stochastic))
        cp.sizeHintLine(26)
        cc.add(cp)
        cp2 = CodePane(get_source(policy_evaluation_exact))
        cp2.sizeHintLine(30)
        cc.add(cp2)
        self.add(cc)

        self.finish()
        self._base_changed()

    # ------------------------------------------------------------------
    #: base policy table, rebuilt whenever the combo box or the env changes
    _base: list[list[float]] | None = None

    def _current_probs(self):
        """Base policy everywhere, mixer row at the selected square."""
        probs = [row[:] for row in self._base]
        probs[self.grid.selected] = self.mixer.row()
        return probs

    def _base_changed(self):
        P = self.env.build()
        g = min(self.env.gamma_value(), 0.9999)
        self._base = base_probs(P, g, self.basebox.currentIndex())
        self.mixer.set_row(self._base[self.grid.selected])
        self.recompute()

    def _state_changed(self, _s):
        self.mixer.set_row(self._base[self.grid.selected])
        self.recompute()

    def _preset(self, key):
        if key == "uniform":
            self.mixer.set_row([0.25] * 4)
        elif key == "base":
            self.mixer.set_row(self._base[self.grid.selected])
        else:
            s = self.grid.selected
            P = self.env.build()
            g = min(self.env.gamma_value(), 0.9999)
            V = policy_evaluation_exact(P, self._current_probs(), g)
            qs = [q_from_V(P, V, s, a, g) for a in range(N_ACTIONS)]
            row = [0.0] * N_ACTIONS
            row[max(range(N_ACTIONS), key=lambda a: qs[a])] = 1.0
            self.mixer.set_row(row)
        self.recompute()

    # ------------------------------------------------------------------
    def recompute(self):
        P = self.env.build()
        g = min(self.env.gamma_value(), 0.9999)
        probs = self._current_probs()
        # base policy may be stale after a slip/reward change
        if self._base is None:
            self._base = base_probs(P, g, self.basebox.currentIndex())

        V = policy_evaluation_exact(P, probs, g)
        Q = q_table_from_V(P, V, g)
        self.P, self.g, self.probs, self.V, self.Q = P, g, probs, V, Q

        self.grid.V = V
        self.grid.update()
        self.tree.set_data(P=P, V=V, Q=Q, probs=probs, gamma=g,
                           s=self.grid.selected)

        s = self.grid.selected
        self.st_v.set(f"{V[s]:+.4f}")
        self.st_best.set(f"{max(Q[s]):+.4f}")
        self.st_worst.set(f"{min(Q[s]):+.4f}")

        self._refresh_detail()
        self._refresh_plots()

    # ------------------------------------------------------------------
    def _refresh_detail(self):
        s, P, g, V, Q, probs = (self.grid.selected, self.P, self.g, self.V,
                                self.Q, self.probs)
        if is_terminal(s):
            self.detail.setText(
                f"<b>State {s} is terminal</b> ({cell_kind(s)}).<br><br>"
                f"Every action self-loops with reward 0, so the equation collapses "
                f"to V({s}) = 0 + γ·V({s}), whose only solution for γ &lt; 1 is "
                f"<b>V({s}) = 0</b>. Nothing to average — the episode is over.")
            return

        out = [f"<b style='color:{theme.ACCENT}'>State {s}</b> "
               f"&nbsp;γ={g:.3f}&nbsp;·&nbsp;"
               f"<span style='color:{theme.TEXT_DIM}'>"
               f"V<sup>π</sup>(s) = Σ<sub>a</sub> π(a|s)·[ Σ<sub>s'</sub> "
               f"P(s'|s,a)·( r + γ·V<sup>π</sup>(s') ) ]</span><br>"]
        total = 0.0
        for a in range(N_ACTIONS):
            pa = probs[s][a]
            inner = []
            qa = 0.0
            for t in merge_duplicates(P[s][a]):
                boot = 0.0 if t.done else V[t.next_state]
                c = t.prob * (t.reward + g * boot)
                qa += c
                inner.append(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;{t.prob:.4f} × ({t.reward:+.2f} + "
                    f"{g:.2f}×{boot:+.4f}) = {c:+.5f}"
                    f"<span style='color:{theme.TEXT_FAINT}'>&nbsp;&nbsp;→ s'="
                    f"{t.next_state}{' (terminal)' if t.done else ''}</span>")
            contrib = pa * qa
            total += contrib
            dead = (pa == 0.0)
            col = theme.TEXT_FAINT if dead else theme.TEXT
            out.append(
                f"<br><b style='color:{col}'>a={a} · {ACTION_NAMES[a]} "
                f"{ACTION_ARROWS[a]} &nbsp;&nbsp;π(a|s)={pa:.3f}</b>"
                + ("<span style='color:%s'> — never pressed, contributes "
                   "nothing</span>" % theme.TEXT_FAINT if dead else "")
                + "<br>" + "<br>".join(inner)
                + f"<br>&nbsp;&nbsp;Q<sup>π</sup>(s,{a}) = <b>{qa:+.6f}</b>"
                + f"&nbsp;&nbsp;→ weighted: {pa:.3f} × {qa:+.6f} = "
                  f"<b style='color:{theme.VIOLET}'>{contrib:+.6f}</b>")

        out.append(
            f"<br><br><span style='color:{theme.VIOLET}'>Σ over all four actions "
            f"= <b>{total:+.6f}</b></span>"
            f"<br>V<sup>π</sup>({s}) from the exact linear solve = "
            f"<b>{V[s]:+.6f}</b>"
            f"<br>residual = <b style='color:{theme.GOOD}'>"
            f"{abs(total - V[s]):.2e}</b> → the Bellman expectation equation holds "
            f"at this square.")
        self.detail.setText("".join(out))

    # ------------------------------------------------------------------
    def _refresh_plots(self):
        s, P, g, probs, V, Q = (self.grid.selected, self.P, self.g, self.probs,
                                self.V, self.Q)
        self.canvas.clear()
        a1, a2 = self.canvas.axes

        # -- left: the Q bars and the pi-weighted average -------------------
        pi_row = probs[s]
        for a in range(N_ACTIONS):
            a1.bar(a, Q[s][a], color=theme.VIOLET,
                   alpha=0.22 + 0.78 * pi_row[a], width=0.66)
            a1.text(a, Q[s][a], f" π={pi_row[a]:.2f}", ha="center",
                    va="bottom" if Q[s][a] >= 0 else "top",
                    fontsize=7, color=theme.TEXT_DIM)
        a1.axhline(V[s], color=theme.ACCENT, ls="--", lw=1.6,
                   label=f"V^π(s) = {V[s]:+.3f}")
        a1.axhline(max(Q[s]), color=theme.GOOD, lw=0.9, ls=":",
                   label=f"max_a Q = {max(Q[s]):+.3f}")
        a1.set_xticks(range(N_ACTIONS))
        a1.set_xticklabels([f"{ACTION_ARROWS[a]}\n{ACTION_NAMES[a]}"
                            for a in range(N_ACTIONS)], fontsize=8)
        a1.set_ylabel("Q^π(s,a)")
        a1.set_title(f"state {s}: V^π is the π-weighted average of these bars")
        self.canvas.legend(a1, loc="best")

        # -- right: hand probability to the best action ---------------------
        if not is_terminal(s):
            best = max(range(N_ACTIONS), key=lambda a: Q[s][a])
            rest = [pi_row[a] if a != best else 0.0 for a in range(N_ACTIONS)]
            tot = sum(rest)
            if tot == 0:
                rest = [0.0 if a == best else 1.0 / 3.0 for a in range(N_ACTIONS)]
                tot = 1.0
            ps = [i / 24.0 for i in range(25)]
            ys = []
            for pmass in ps:
                trial = [row[:] for row in probs]
                r = [(1.0 - pmass) * rest[a] / tot for a in range(N_ACTIONS)]
                r[best] += pmass
                trial[s] = r
                ys.append(policy_evaluation_exact(P, trial, g)[s])
            a2.plot(ps, ys, color=theme.ACCENT, lw=1.8,
                    label="V^π(s) as mass moves to the best action")
            _, Vstar, _ = value_iteration(P, gamma=g, theta=1e-12)
            a2.axhline(Vstar[s], color=theme.GOOD, ls="--", lw=1.4,
                       label=f"V*(s) = {Vstar[s]:+.3f}  (the ceiling)")
            a2.scatter([pi_row[best]], [V[s]], color=theme.VIOLET, zorder=5,
                       s=42, label="where your sliders are now")
            a2.set_xlabel(f"probability handed to {ACTION_ARROWS[best]} "
                          f"{ACTION_NAMES[best]}")
            a2.set_ylabel("V^π(s)")
            a2.set_title("averaging can approach the ceiling, never beat it")
            self.canvas.legend(a2, loc="best")
        self.canvas.refresh()

        # -- convergence: sweeps vs the exact answer ------------------------
        self.canvas2.clear()
        ax = self.canvas2.ax
        hist = policy_evaluation_history(P, probs, g, theta=1e-13, max_sweeps=140)
        errs = [max(abs(hist[k][i] - V[i]) for i in range(N_STATES))
                for k in range(len(hist))]
        errs = [max(e, 1e-17) for e in errs]
        rate = observed_rate(errs)
        ax.semilogy(range(len(errs)), errs, color=theme.ACCENT, lw=1.7,
                    label="‖V_k − V^π‖∞  (iterative sweeps)"
                          + (f" — {rate:.3f}/sweep" if rate else ""))
        e0 = errs[0] if errs[0] > 0 else 1.0
        ax.semilogy(range(len(errs)), [e0 * (g ** k) for k in range(len(errs))],
                    color=theme.WARN, ls="--", lw=1.2,
                    label=f"γ^k — the worst-case bound only (γ={g:.2f})")
        ax.axhline(1e-15, color=theme.VIOLET, lw=1.0, ls=":",
                   label="exact solve — no sweeps at all")
        ax.set_xlabel("sweep k")
        ax.set_ylabel("worst-state error")
        ax.set_title("geometric decay — usually much faster than the γ^k bound")
        self.canvas2.legend(ax, loc="best")
        self.canvas2.refresh()

        it = policy_evaluation_stochastic(P, probs, g, theta=1e-13,
                                         max_sweeps=4000)
        gap = max(abs(it[i] - V[i]) for i in range(N_STATES))
        self.st_iter.set(f"{it[s]:+.6f}")
        self.st_exact.set(f"{V[s]:+.6f}")
        self.st_gap.set(f"{gap:.1e}")
        self.st_gap.set_color(theme.GOOD if gap < 1e-6 else theme.BAD)
        if gap < 1e-6:
            self.gap_note.setText(
                f"Both roads arrive: the sweeps got within "
                f"<b style='color:{theme.GOOD}'>{gap:.1e}</b> of the exact answer, "
                f"which is floating-point dust. Sweeping needs roughly "
                f"log(ε)/log(γ) passes to get there; the matrix solve needs none.")
        else:
            self.gap_note.setText(
                f"<b style='color:{theme.BAD}'>Look at that gap: {gap:.2e}.</b> "
                f"The exact solve is still exact — the <i>iteration</i> has not "
                f"finished. It needs about log(ε)/log(γ) sweeps, and at γ={g:.4f} "
                f"that is tens of thousands, so 4000 is nowhere near enough. It is "
                f"worst for a policy that never reaches a hole or the goal (try "
                f"base π = always RIGHT, γ = 1.00): with no terminal state to anchor "
                f"it, V settles at the bare loop value r/(1−γ) and the sweeps crawl "
                f"there one γ-step at a time. This is the practical reason to know "
                f"the linear form exists.")


# ==========================================================================
# PAGE 13 -- Bellman expectation for Q
# ==========================================================================

class BellmanExpQPage(Page):
    TITLE = "Bellman ② — Q^π (expectation)"
    SUBTITLE = ("The first button is already pressed, so the π-average cannot "
                "happen now — it happens one square later.")
    SECTION = "Value Functions"
    NOTES = "notes p.1 · p.5"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>Say it out loud, no symbols.</b><br><br>"
            "Same square <b>s</b>, but this time somebody has already grabbed your "
            "hand and pressed <b>a</b>. Your die is <b>spent</b>. Only the ice is "
            "left to roll.<br><br>"
            "So the first thing that happens is <i>not</i> a choice: it is the ice, "
            "sliding you onto s' with probability P(s'|s,a), paying you r on the "
            "way.<br><br>"
            "Now you are standing on s' with <b>nothing forced</b> — and from here "
            "on you go back to your usual habit π. Which means the question "
            "\"which button?\" has come back, and it gets averaged with π(a'|s') "
            "just like on the previous page. <b>The π-average did not disappear. "
            "It moved one step later.</b>",
            "key", "READ IT IN PLAIN ENGLISH"))

        self.add(bellman_map("exp_q"))

        f = Card("the same sentence, in symbols — and why there are two forms")
        f.add(body("<b>Form A — spelled out.</b> The delayed π-average is visible:",
                   dim=True))
        f.add(math_label(
            r"Q^\pi(s,a) \;=\; \sum_{s'} P(s'\mid s,a)\left[\, r \;+\; \gamma "
            r"\sum_{a'} \pi(a'\mid s')\, Q^\pi(s',a') \,\right]", 15))
        f.add(body(
            f"The <span style='color:{theme.VIOLET}'>Σ<sub>a'</sub> π(a'|s')</span> "
            f"is the choice, arriving one step later than it did on page 12."))
        f.add(body("<b>Form B — collapsed.</b> That inner sum has a name:",
                   dim=True))
        f.add(math_label(
            r"V^\pi(s') \;=\; \sum_{a'} \pi(a'\mid s')\, Q^\pi(s',a')"
            r" \qquad \Longrightarrow \qquad "
            r"Q^\pi(s,a) \;=\; \sum_{s'} P(s'\mid s,a)"
            r"\left[\, r + \gamma\, V^\pi(s') \,\right]", 14))
        f.add(body(
            "Form B is what the code computes (<code>q_from_V</code>), because by "
            "then V<sup>π</sup> is already sitting in an array. Form A is what you "
            "need in your head, because it is the only one that shows <b>where the "
            "choice went</b>. They are the same equation — the panel below checks "
            "that numerically, branch by branch.", dim=True))
        self.add(f)

        self.add(callout(
            "<b>Same idea with no lake in it.</b> Back to the commute. "
            "Q<sup>π</sup>(s, walk) is: \"<i>today</i> I walk — I am not asking "
            "whether that is my habit, somebody has decided it — and from tomorrow "
            "onwards I go back to being my usual coin-flipping self.\" The forced "
            "first choice is what makes Q<sup>π</sup> answerable for an action you "
            "would <b>never normally take</b>. That is the whole reason Q exists: it "
            "can price options you do not currently use, which is the only way to "
            "ever discover a better habit.", "good", "INTUITIVE EXAMPLE"))

        t = Card("the backup tree — notice the choice layer is now SECOND")
        self.tree = BackupTree("exp_q", height=380)
        t.add(self.tree)
        self.add(t)

        # ---- controls ---------------------------------------------------
        ctl = Card("controls")
        self.env = EnvControls(slip="classic", reward="shaped", gamma=0.99)
        self.env.changed.connect(self.recompute)
        self.basebox = QComboBox()
        self.basebox.addItems(BASE_LABELS)
        self.basebox.setCurrentIndex(1)
        self.basebox.currentIndexChanged.connect(self._base_changed)
        self.actbox = QComboBox()
        self.actbox.addItems([f"a = {a} · {ACTION_NAMES[a]} {ACTION_ARROWS[a]}"
                              for a in range(N_ACTIONS)])
        self.actbox.setCurrentIndex(1)
        self.actbox.currentIndexChanged.connect(self.recompute)
        ctl.add_layout(labelled("Base π", self.basebox, 74))
        ctl.add_layout(labelled("Forced a", self.actbox, 74))
        ctl.add(self.env)

        self.mixer = PolicyMixer()
        self.mixer.changed.connect(self.recompute)
        self.mixer.preset.connect(self._preset)

        gcard = Card("Q^π(s,a) — click a square, pick the forced action")
        self.grid = GridView(cell=104)
        self.grid.show_q = True
        self.grid.show_values = False
        self.grid.show_policy = False
        self.grid.clickable = True
        self.grid.selected = 9
        self.grid.cellClicked.connect(self._state_changed)
        gcard.add(self.grid)
        self.st_q = Stat("Q^π(s,a)", "-", theme.VIOLET)
        self.st_v = Stat("V^π(s) = Σπ·Q", "-", theme.ACCENT)
        self.st_res = Stat("form A vs form B", "-", theme.GOOD)
        gcard.add_layout(stat_row(self.st_q, self.st_v, self.st_res))

        self.row(gcard, ctl, self.mixer, stretches=[0, 1, 1])

        d = Card("branch by branch — with the delayed π-average expanded")
        self.detail = detail_box(360)
        d.add(self.detail)
        self.add(d)

        pc = Card("plots")
        self.canvas = MplCanvas(width=11.0, height=3.5, ncols=2)
        pc.add(self.canvas)
        pc.add(body(
            "<b>Left — the waterfall.</b> Each landing the ice can give you adds "
            "(or subtracts) its p·(r + γV<sup>π</sup>(s')) onto a running total, and "
            "the last bar is Q<sup>π</sup>(s,a). This is the picture of \"a sum of "
            "signed pieces\", which is what the Σ actually is.<br>"
            "<b>Right — γ decides which action wins.</b> The four "
            "Q<sup>π</sup>(s,a) as γ moves from 0 to 0.99. At γ=0 nothing but the "
            "immediate reward matters and the ranking is pure short-termism; as γ "
            "rises, actions that head somewhere useful overtake actions that merely "
            "avoid a step cost. <b>Where the lines cross, the greedy action "
            "changes.</b> That is γ changing the problem, not the solver.", dim=True))
        self.add(pc)

        self.add(callout(
            "<b>This equation is the one SARSA samples.</b> Replace "
            "<code>Σ<sub>s'</sub>P(s'|s,a)</code> with a single observed "
            "transition, and <code>Σ<sub>a'</sub>π(a'|s')Q(s',a')</code> with the "
            "single action your policy actually chose next, and Form A becomes<br>"
            "&nbsp;&nbsp;<code>Q(s,a) ← Q(s,a) + α[ r + γQ(s',a') − Q(s,a) ]</code>"
            "<br>which is SARSA, exactly. The <b>a'</b> being drawn from π — not "
            "maximised — is what makes SARSA <i>on-policy</i>. One page from now the "
            "same slot holds a max, and that is Q-learning.", "key"))

        cc = Card("the code that computes form B")
        cp = CodePane(get_source(q_from_V))
        cp.sizeHintLine(16)
        cc.add(cp)
        self.add(cc)

        self.finish()
        self._base_changed()

    # ------------------------------------------------------------------
    _base: list[list[float]] | None = None

    def _current_probs(self):
        probs = [row[:] for row in self._base]
        probs[self.grid.selected] = self.mixer.row()
        return probs

    def _base_changed(self):
        P = self.env.build()
        g = min(self.env.gamma_value(), 0.9999)
        self._base = base_probs(P, g, self.basebox.currentIndex())
        self.mixer.set_row(self._base[self.grid.selected])
        self.recompute()

    def _state_changed(self, _s):
        self.mixer.set_row(self._base[self.grid.selected])
        self.recompute()

    def _preset(self, key):
        if key == "uniform":
            self.mixer.set_row([0.25] * 4)
        elif key == "base":
            self.mixer.set_row(self._base[self.grid.selected])
        else:
            s = self.grid.selected
            qs = self.Q[s]
            row = [0.0] * N_ACTIONS
            row[max(range(N_ACTIONS), key=lambda a: qs[a])] = 1.0
            self.mixer.set_row(row)
        self.recompute()

    # ------------------------------------------------------------------
    def recompute(self):
        P = self.env.build()
        g = min(self.env.gamma_value(), 0.9999)
        if getattr(self, "_base", None) is None:
            self._base = base_probs(P, g, self.basebox.currentIndex())
        probs = self._current_probs()
        V = policy_evaluation_exact(P, probs, g)
        Q = q_table_from_V(P, V, g)
        self.P, self.g, self.probs, self.V, self.Q = P, g, probs, V, Q

        self.grid.Q = Q
        self.grid.V = V
        self.grid.update()
        s, a = self.grid.selected, self.actbox.currentIndex()
        self.tree.set_data(P=P, V=V, Q=Q, probs=probs, gamma=g, s=s, a=a)

        # form A: expand the inner sum. form B: use V^pi(s'). Must match.
        formA = 0.0
        for t in P[s][a]:
            inner = 0.0 if t.done else sum(
                probs[t.next_state][a2] * Q[t.next_state][a2]
                for a2 in range(N_ACTIONS))
            formA += t.prob * (t.reward + g * inner)
        self.st_q.set(f"{Q[s][a]:+.5f}")
        self.st_v.set(f"{V[s]:+.5f}")
        self.st_res.set(f"{abs(formA - Q[s][a]):.1e}")

        self._refresh_detail(formA)
        self._refresh_plots()

    # ------------------------------------------------------------------
    def _refresh_detail(self, formA):
        s, a, P, g, V, Q, probs = (self.grid.selected, self.actbox.currentIndex(),
                                   self.P, self.g, self.V, self.Q, self.probs)
        if is_terminal(s):
            self.detail.setText(
                f"<b>State {s} is terminal</b> ({cell_kind(s)}). Every action "
                f"self-loops with reward 0, so Q<sup>π</sup>({s},a) = 0 for all four "
                f"actions. There is no first move to force.")
            return

        out = [f"<b style='color:{theme.ACCENT}'>Q<sup>π</sup>({s}, "
               f"{ACTION_NAMES[a]} {ACTION_ARROWS[a]})</b> &nbsp;γ={g:.3f}<br>"
               f"<span style='color:{theme.TEXT_DIM}'>the forced action is spent — "
               f"layer 1 is pure ice, and the π-average shows up at each s'"
               f"</span><br>"]
        total = 0.0
        for t in merge_duplicates(P[s][a]):
            ns = t.next_state
            if t.done:
                c = t.prob * t.reward
                total += c
                out.append(
                    f"<br><b>s' = {ns}</b> &nbsp;P={t.prob:.4f} &nbsp;r="
                    f"{t.reward:+.2f} &nbsp;<span style='color:{theme.WARN}'>"
                    f"TERMINAL</span><br>"
                    f"&nbsp;&nbsp;no future to average → contributes "
                    f"{t.prob:.4f} × {t.reward:+.2f} = <b>{c:+.6f}</b>")
                continue

            inner_terms = []
            inner = 0.0
            for a2 in range(N_ACTIONS):
                pa = probs[ns][a2]
                inner += pa * Q[ns][a2]
                inner_terms.append(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;π({ACTION_ARROWS[a2]}|{ns})="
                    f"{pa:.3f} × Q<sup>π</sup>({ns},{ACTION_ARROWS[a2]})="
                    f"{Q[ns][a2]:+.4f} → {pa * Q[ns][a2]:+.5f}")
            c = t.prob * (t.reward + g * inner)
            total += c
            out.append(
                f"<br><b>s' = {ns}</b> &nbsp;P={t.prob:.4f} &nbsp;r={t.reward:+.2f}"
                f"<br><span style='color:{theme.TEXT_DIM}'>&nbsp;&nbsp;the delayed "
                f"π-average at s'={ns}:</span><br>"
                + "<br>".join(inner_terms)
                + f"<br>&nbsp;&nbsp;Σ = <b style='color:{theme.VIOLET}'>"
                  f"{inner:+.6f}</b> = V<sup>π</sup>({ns}) = {V[ns]:+.6f} "
                  f"<span style='color:{theme.GOOD}'>✓ same number</span>"
                + f"<br>&nbsp;&nbsp;branch = {t.prob:.4f} × ({t.reward:+.2f} + "
                  f"{g:.2f}×{inner:+.5f}) = <b>{c:+.6f}</b>")

        out.append(
            f"<br><br><b>form A total (inner π-sum spelled out) = {formA:+.6f}</b>"
            f"<br><b>form B total (using V<sup>π</sup>(s')) = {Q[s][a]:+.6f}</b>"
            f"<br>residual = <b style='color:{theme.GOOD}'>"
            f"{abs(formA - Q[s][a]):.2e}</b> → the two forms are one equation."
            f"<br><br><span style='color:{theme.TEXT_DIM}'>and across the four "
            f"actions: Σ<sub>a</sub> π(a|{s})·Q<sup>π</sup>({s},a) = "
            f"{sum(probs[s][x] * Q[s][x] for x in range(N_ACTIONS)):+.6f} = "
            f"V<sup>π</sup>({s}) = {V[s]:+.6f} — which is the previous page's "
            f"equation, read backwards.</span>")
        self.detail.setText("".join(out))

    # ------------------------------------------------------------------
    def _refresh_plots(self):
        s, a, P, g, V, Q, probs = (self.grid.selected, self.actbox.currentIndex(),
                                   self.P, self.g, self.V, self.Q, self.probs)
        self.canvas.clear()
        ax1, ax2 = self.canvas.axes

        if not is_terminal(s):
            labels, contribs = [], []
            for t in merge_duplicates(P[s][a]):
                boot = 0.0 if t.done else V[t.next_state]
                contribs.append(t.prob * (t.reward + g * boot))
                labels.append(f"s'={t.next_state}\np={t.prob:.2f}")
            waterfall(ax1, labels, contribs, Q[s][a],
                      f"Q^π({s},{ACTION_ARROWS[a]}) = sum of these branches",
                      theme.VIOLET)
            ax1.set_ylabel("running total")

            # gamma sweep -- exact solve is cheap enough to do 30 times
            gs = [i / 30.0 * 0.99 for i in range(31)]
            series = [[] for _ in range(N_ACTIONS)]
            for gg in gs:
                Vg = policy_evaluation_exact(P, probs, gg)
                for a2 in range(N_ACTIONS):
                    series[a2].append(q_from_V(P, Vg, s, a2, gg))
            cols = [theme.BAD, theme.ACCENT, theme.GOOD, theme.WARN]
            for a2 in range(N_ACTIONS):
                ax2.plot(gs, series[a2], color=cols[a2],
                         lw=2.2 if a2 == a else 1.3,
                         label=f"{ACTION_ARROWS[a2]} {ACTION_NAMES[a2]}")
            ax2.axvline(g, color=theme.TEXT_FAINT, ls="--", lw=1.0)
            ax2.set_xlabel("γ")
            ax2.set_ylabel(f"Q^π({s},a)")
            ax2.set_title("which action looks best depends on γ")
            self.canvas.legend(ax2, loc="best")
        self.canvas.refresh()


# ==========================================================================
# PAGE 14 -- Bellman optimality for V
# ==========================================================================

class BellmanOptVPage(Page):
    TITLE = "Bellman ③ — V* (optimality)"
    SUBTITLE = ("Your die stops being random: you choose. The ice's die never "
                "does. That asymmetry IS the equation.")
    SECTION = "Value Functions"
    NOTES = "notes p.1 · p.5"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>Your own words, checked line by line.</b><br><br>"
            "You wrote: <i>\"for any action get the probability of getting to a new "
            "state, and for that probable situation compute prob × reward × γV of "
            "that new state, and sum over all probable situations — so we take an "
            "action and it can lead us to different states with different "
            "probability, take those new states' values and weight by the "
            "probability; then for all possible actions take the highest value as "
            "the state value, and the best action is the best move.\"</i><br><br>"
            "<b>The shape of that is exactly right</b> — probability-weighted "
            "average <i>inside</i>, highest-wins <i>outside</i>, and the winner is "
            "π*(s). Two fixes and it is word-perfect:<br><br>"
            "<b>Fix 1 — it is a sum, not a product.</b> Each branch is "
            "<code>p × ( r + γ·V(s') )</code>. The reward is <b>added</b> to the "
            "discounted future, not multiplied by it. <code>p × r × γ × V</code> "
            "would say \"getting paid and continuing\" are multiplicative, and "
            "would also make every branch worthless the moment one reward is 0.<br>"
            "<b>Fix 2 — r belongs to the branch, not the action.</b> Sliding into a "
            "hole pays −1 on <i>that branch only</i>; the sibling branch of the same "
            "action pays −0.04. The reward lives inside the s' sum, which is why it "
            "sits inside the bracket.", "key", "YOUR INTUITION, VERIFIED"))

        self.add(bellman_map("opt_v"))

        f = Card("the same sentence, in symbols")
        f.add(math_label(
            r"V^*(s) \;=\; \max_a \;\sum_{s'} P(s'\mid s,a)"
            r"\left[\, r \;+\; \gamma\, V^*(s') \,\right]", 16))
        f.add(math_label(
            r"\pi^*(s) \;=\; \mathrm{argmax}_a \;\sum_{s'} P(s'\mid s,a)"
            r"\left[\, r \;+\; \gamma\, V^*(s') \,\right]", 13))
        f.add(body(
            f"<span style='color:{theme.GOOD}'>max<sub>a</sub></span> — you choose, "
            f"and the winner's name is π*(s) &nbsp;·&nbsp; "
            f"<span style='color:{theme.CYAN}'>Σ<sub>s'</sub> P(s'|s,a)</span> — the "
            f"ice still rolls, so this half stays an average. Same bracket in both "
            f"lines: one returns the number, the other returns the button."))
        f.add(body(
            "Compare it with page 12 and only <b>one</b> thing moved:<br>"
            "&nbsp;&nbsp;<code>Σ<sub>a</sub> π(a|s) · (…)</code> &nbsp;→&nbsp; "
            "<code>max<sub>a</sub> (…)</code><br><br>"
            "That is the entire difference between \"how good is the policy I have\" "
            "and \"how good is the best policy that exists\". The inner "
            "<code>Σ<sub>s'</sub></code> is untouched, and it must be: you cannot "
            "<code>max</code> over where the ice throws you. If you could, the "
            "equation would be describing a game where you also control the weather."))
        f.add(body(
            "<b>And note what V*(s') is doing inside the bracket.</b> It is not "
            "\"the value if I follow some policy from s'\" — it is already the "
            "<i>optimal</i> value from s', so it already contains every future max. "
            "You only ever write one max per equation because the rest are baked "
            "into the number you are reading.", dim=True))
        self.add(f)

        self.add(callout(
            "<b>Same idea with no lake in it.</b> Driving to work in traffic. At "
            "each junction <b>you</b> pick the turn — no coin flip, you simply take "
            "the best one. But once you have turned, traffic does what it likes, so "
            "the same turn sometimes takes 4 minutes and sometimes 12. So the score "
            "of a turn is the <i>average</i> over traffic, and the score of the "
            "junction is the <i>best</i> of those averages. Best-of-averages — never "
            "best-of-best, because you cannot promise yourself the green lights.",
            "good", "INTUITIVE EXAMPLE"))

        t = Card("the backup tree — three branches get thrown away")
        self.tree = BackupTree("opt_v", height=340)
        t.add(self.tree)
        self.add(t)

        # ---- interactive 1: swap the operator ------------------------------
        ctl = Card("controls")
        self.env = EnvControls(slip="classic", reward="shaped", gamma=0.99)
        self.env.changed.connect(self.recompute)
        ctl.add(self.env)

        opc = Card("swap the outer operator — same code, three questions")
        self.ops = QButtonGroup(self)
        oplay = QVBoxLayout()
        for i, (key, txt) in enumerate((
                ("max", "max<sub>a</sub> — <b>you</b> choose  →  this is V*"),
                ("mean", "avg<sub>a</sub> — a coin chooses  →  V under uniform π"),
                ("min", "min<sub>a</sub> — an <b>enemy</b> chooses your button"))):
            rb = QRadioButton()
            rb.setChecked(i == 0)
            lbl = QLabel(txt)
            lbl.setStyleSheet(f"color:{theme.TEXT}; background:transparent;")
            r = QHBoxLayout()
            r.setSpacing(6)
            r.addWidget(rb)
            r.addWidget(lbl, 1)
            w = QWidget()
            w.setStyleSheet("background:transparent;")
            w.setLayout(r)
            oplay.addWidget(w)
            self.ops.addButton(rb, i)
            rb.setProperty("opkey", key)
        self.ops.idToggled.connect(lambda *_: self.recompute())
        opc.add_layout(oplay)
        opc.add(body(
            "The inner Σ<sub>s'</sub> is identical in all three. Only the outer "
            "reduction changes — and with it, the entire meaning. If \"max\" felt "
            "like a formality, watch what \"min\" does to the arrows.", dim=True))

        gcard = Card("V(s) under the chosen operator — click a square")
        self.grid = GridView(cell=86)
        self.grid.clickable = True
        self.grid.selected = 9
        self.grid.value_fmt = "{:.3f}"
        self.grid.cellClicked.connect(lambda _s: self._refresh_detail())
        gcard.add(self.grid)
        self.st_start = Stat("V(start)", "-", theme.ACCENT)
        self.st_here = Stat("V(s) here", "-", theme.GOOD)
        self.st_sweeps = Stat("sweeps", "-", theme.WARN)
        gcard.add_layout(stat_row(self.st_start, self.st_here, self.st_sweeps))

        self.row(gcard, opc, ctl, stretches=[0, 1, 1])

        d = Card("the four candidates and the winner")
        self.detail = detail_box(320)
        d.add(self.detail)
        self.add(d)

        # ---- interactive 2: scrub the sweeps -------------------------------
        sc = Card("scrub the sweeps — watch the news ripple back from the goal")
        self.sweep = QSlider(Qt.Horizontal)
        self.sweep.setRange(0, 1)
        self.sweep.valueChanged.connect(self._refresh_sweep)
        self.sweep_lbl = QLabel("sweep 0")
        self.sweep_lbl.setStyleSheet(
            f"color:{theme.ACCENT}; font-family:Consolas; font-weight:700;"
            f"background:transparent; min-width:90px;")
        srow = QHBoxLayout()
        srow.addWidget(self.sweep, 1)
        srow.addWidget(self.sweep_lbl)
        self.gridk = GridView(cell=78)
        self.gridk.value_fmt = "{:.3f}"
        self.gridk.show_policy = True
        krow = QHBoxLayout()
        krow.setSpacing(14)
        kleft = QVBoxLayout()
        kleft.addWidget(self.gridk)
        kleft.addLayout(srow)
        kleft.addStretch(1)
        krow.addLayout(kleft)
        self.canvas2 = MplCanvas(width=7.6, height=3.4)
        krow.addWidget(self.canvas2, 1)
        sc.add_layout(krow)
        sc.add(body(
            "Sweep 0 is all zeros — the agent knows nothing. On sweep 1 only the "
            "squares that can <i>touch</i> a rewarding transition change. On sweep 2 "
            "their neighbours hear about it. The gold outlines mark the squares that "
            "moved this sweep. The plot on the right is the same story as a number: "
            "the worst-state distance to V*, dying geometrically — that is the "
            "<b>γ-contraction</b>, and it is why starting from V=0 does not "
            "matter.<br><br>"
            "<b>Read the two lines carefully, because the theorem is a bound, not a "
            "prediction.</b> γ<sup>k</sup> is the <i>guaranteed ceiling</i> on the "
            "error: it says the error can never shrink <i>slower</i> than that. On "
            "this lake it shrinks a great deal faster — around 0.6 per sweep at "
            "γ=0.99 — because holes and the goal are absorbing, so most chains of "
            "states run out after a few hops and there is simply nothing left to "
            "propagate. The legend prints the rate actually observed next to the "
            "bound. Where γ<sup>k</sup> becomes the honest answer is a long loop with "
            "no terminal state in it, which is exactly the case that made the "
            "iterative solver on page 12 fall behind the matrix solve.", dim=True))
        self.add(sc)

        pc = Card("max is a choice, not an average")
        self.canvas = MplCanvas(width=11.0, height=3.3, ncols=2)
        pc.add(self.canvas)
        pc.add(body(
            "<b>Left:</b> the four one-step lookaheads at the selected square. The "
            "green bar wins and becomes V*(s); the other three are simply discarded. "
            "The dashed violet line is what an <i>average</i> would have given you — "
            "the gap is the value of being allowed to choose.<br>"
            "<b>Right:</b> V(s) for all 16 squares under the three operators. "
            "max ≥ avg ≥ min everywhere, by construction. Notice that the min curve "
            "is not \"the max curve, worse\" — under an adversary the whole "
            "<i>shape</i> of the problem changes.", dim=True))
        self.add(pc)

        cc = Card("the code — one operator, three questions")
        cp = CodePane(get_source(value_iteration_operator))
        cp.sizeHintLine(30)
        cc.add(cp)
        cc.add(callout(
            "In real value iteration nobody stores a policy while sweeping. The "
            "policy is implicit: at every sweep the algorithm is evaluating "
            "\"whatever is greedy w.r.t. my current V\", and <code>max<sub>a</sub></code> "
            "IS <code>Σ<sub>a</sub>π(a|s)</code> when π is greedy — a one-hot vector "
            "dotted with Q is the biggest entry of Q. The arrows are written down "
            "once, at the end, for a robot to read.", "key"))
        self.add(cc)

        self.finish()
        self.recompute()

    # ------------------------------------------------------------------
    #: first solve positions the sweep scrubber; later ones leave it alone
    _first_solve = True

    def _op(self):
        btn = self.ops.checkedButton()
        return btn.property("opkey") if btn else "max"

    def recompute(self):
        P = self.env.build()
        g = min(self.env.gamma_value(), 0.9999)
        op = self._op()
        V, hist = value_iteration_operator(P, gamma=g, op=op, theta=1e-11,
                                           max_sweeps=4000)
        pi = [max(range(N_ACTIONS), key=lambda a: q_from_V(P, V, s, a, g))
              if op == "max" else
              min(range(N_ACTIONS), key=lambda a: q_from_V(P, V, s, a, g))
              for s in range(N_STATES)]

        self.P, self.g, self.V, self.hist, self.pi = P, g, V, hist, pi
        self.grid.V = V
        self.grid.policy = pi
        self.grid.show_policy = (op != "mean")
        self.grid.update()

        self.st_start.set(f"{V[0]:+.4f}")
        self.st_sweeps.set(str(len(hist) - 1))
        self.tree.set_data(P=P, V=V, Q=q_table_from_V(P, V, g),
                           probs=[[0.25] * 4] * N_STATES, gamma=g,
                           s=self.grid.selected)

        self.sweep.blockSignals(True)
        self.sweep.setRange(0, len(hist) - 1)
        if self._first_solve:
            # open on a partly-rippled board -- sweep 0 is all zeros and shows
            # nothing, which is a dull thing to land on
            self.sweep.setValue(min(3, len(hist) - 1))
            self._first_solve = False
        else:
            self.sweep.setValue(min(self.sweep.value(), len(hist) - 1))
        self.sweep.blockSignals(False)

        self._refresh_detail()
        self._refresh_sweep()
        self._refresh_plots()

    # ------------------------------------------------------------------
    def _refresh_detail(self):
        s, P, g, V = self.grid.selected, self.P, self.g, self.V
        self.st_here.set(f"{V[s]:+.4f}")
        self.tree.set_data(s=s)
        if is_terminal(s):
            self.detail.setText(
                f"<b>State {s} is terminal</b> ({cell_kind(s)}). Absorbing, reward "
                f"0, so V({s}) = 0 + γ·V({s}) → <b>V({s}) = 0</b>. There is nothing "
                f"to maximise over: all four actions are the same self-loop.")
            self._refresh_plots()
            return

        op = self._op()
        out = [f"<b style='color:{theme.ACCENT}'>State {s}</b> &nbsp;γ={g:.3f}"
               f"&nbsp;·&nbsp;operator = <b>{op}</b><br>"
               f"<span style='color:{theme.TEXT_DIM}'>each candidate is "
               f"Σ<sub>s'</sub> P(s'|s,a)·( r + γ·V(s') ) — the ice averaged, "
               f"nothing chosen yet</span><br>"]
        qs = []
        for a in range(N_ACTIONS):
            terms, tot = [], 0.0
            for t in merge_duplicates(P[s][a]):
                boot = 0.0 if t.done else V[t.next_state]
                c = t.prob * (t.reward + g * boot)
                tot += c
                terms.append(
                    f"&nbsp;&nbsp;{t.prob:.4f} × ({t.reward:+.2f} + {g:.2f}×"
                    f"{boot:+.4f}) = {c:+.5f}"
                    f"<span style='color:{theme.TEXT_FAINT}'>&nbsp;&nbsp;→ s'="
                    f"{t.next_state}{' (terminal)' if t.done else ''}</span>")
            qs.append(tot)
            out.append(f"<br><b>a={a} · {ACTION_NAMES[a]} {ACTION_ARROWS[a]}</b>"
                       f"<br>" + "<br>".join(terms)
                       + f"<br>&nbsp;&nbsp;candidate = <b>{tot:+.6f}</b>")

        win = (max(range(N_ACTIONS), key=lambda a: qs[a]) if op != "min"
               else min(range(N_ACTIONS), key=lambda a: qs[a]))
        chosen = {"max": max(qs), "min": min(qs),
                  "mean": sum(qs) / len(qs)}[op]
        out.append(
            f"<br><br><span style='color:{theme.GOOD}'>{op}<sub>a</sub> = "
            f"<b>{chosen:+.6f}</b>"
            + (f" &nbsp;→ from a={win} ({ACTION_NAMES[win]} "
               f"{ACTION_ARROWS[win]}), so π({s}) = {ACTION_ARROWS[win]}"
               if op != "mean" else " &nbsp;(no action is chosen — it is an average)")
            + f"</span><br>stored V({s}) = <b>{V[s]:+.6f}</b>"
            f"<br>residual = <b style='color:{theme.GOOD}'>"
            f"{abs(chosen - V[s]):.2e}</b> → the equation holds here."
            f"<br><br><span style='color:{theme.TEXT_DIM}'>the three discarded "
            f"candidates were "
            + ", ".join(f"{qs[a]:+.4f}" for a in range(N_ACTIONS) if a != win)
            + " — thrown away, not averaged in. That is what makes this equation "
              "non-linear and un-invertible.</span>")
        self.detail.setText("".join(out))

    # ------------------------------------------------------------------
    def _refresh_sweep(self):
        k = self.sweep.value()
        hist = self.hist
        k = min(k, len(hist) - 1)
        Vk = hist[k]
        prev = hist[k - 1] if k > 0 else [0.0] * N_STATES
        self.gridk.V = Vk
        self.gridk.policy = [max(range(N_ACTIONS),
                                 key=lambda a: q_from_V(self.P, Vk, s, a, self.g))
                             for s in range(N_STATES)]
        self.gridk.highlight = {s for s in range(N_STATES)
                                if abs(Vk[s] - prev[s]) > 1e-9}
        self.gridk.update()
        err = max(abs(Vk[s] - self.V[s]) for s in range(N_STATES))
        self.sweep_lbl.setText(f"sweep {k}\nerr {err:.1e}")

    # ------------------------------------------------------------------
    def _refresh_plots(self):
        P, g, V, hist = self.P, self.g, self.V, self.hist
        s = self.grid.selected

        # ---- convergence -------------------------------------------------
        self.canvas2.clear()
        ax = self.canvas2.ax
        errs = [max(max(abs(hist[k][i] - V[i]) for i in range(N_STATES)), 1e-17)
                for k in range(len(hist))]
        rate = observed_rate(errs)
        ax.semilogy(range(len(errs)), errs, color=theme.GOOD, lw=1.8,
                    label="‖V_k − V*‖∞"
                          + (f" — observed {rate:.3f}/sweep" if rate else ""))
        e0 = errs[0] if errs[0] > 0 else 1.0
        ax.semilogy(range(len(errs)), [e0 * (g ** k) for k in range(len(errs))],
                    color=theme.WARN, ls="--", lw=1.2,
                    label=f"γ^k — guaranteed ceiling only (γ={g:.2f})")
        ax.axvline(self.sweep.value(), color=theme.ACCENT, lw=1.2, ls=":",
                   label="the sweep you are looking at")
        ax.set_xlabel("sweep k")
        ax.set_ylabel("worst-state error")
        ax.set_title("γ-contraction — the error dies geometrically, "
                     "faster than γ^k here")
        self.canvas2.legend(ax, loc="best")
        self.canvas2.refresh()

        # ---- candidates + operator comparison ----------------------------
        self.canvas.clear()
        ax1, ax2 = self.canvas.axes
        qs = [q_from_V(P, V, s, a, g) for a in range(N_ACTIONS)]
        best = max(range(N_ACTIONS), key=lambda a: qs[a])
        for a in range(N_ACTIONS):
            ax1.bar(a, qs[a], width=0.66,
                    color=theme.GOOD if a == best else theme.BORDER,
                    alpha=0.95 if a == best else 0.8)
        ax1.axhline(sum(qs) / len(qs), color=theme.VIOLET, ls="--", lw=1.4,
                    label=f"avg = {sum(qs) / len(qs):+.3f}  (what π-averaging gives)")
        ax1.axhline(max(qs), color=theme.GOOD, ls=":", lw=1.2,
                    label=f"max = {max(qs):+.3f}  → V*(s)")
        ax1.set_xticks(range(N_ACTIONS))
        ax1.set_xticklabels([f"{ACTION_ARROWS[a]}\n{ACTION_NAMES[a]}"
                             for a in range(N_ACTIONS)], fontsize=8)
        ax1.set_title(f"state {s}: one candidate survives, three are discarded")
        self.canvas.legend(ax1, loc="best")

        for op, col in (("max", theme.GOOD), ("mean", theme.VIOLET),
                        ("min", theme.BAD)):
            Vo, _ = value_iteration_operator(P, gamma=g, op=op, theta=1e-8,
                                             max_sweeps=900)
            ax2.plot(range(N_STATES), Vo, color=col, lw=1.6, marker="o",
                     markersize=3, label=f"{op}")
        ax2.set_xticks(range(N_STATES))
        ax2.set_xlabel("state s")
        ax2.set_ylabel("V(s)")
        ax2.set_title("same inner sum, three outer operators")
        self.canvas.legend(ax2, loc="best")
        self.canvas.refresh()


# ==========================================================================
# PAGE 15 -- Bellman optimality for Q
# ==========================================================================

class BellmanOptQPage(Page):
    TITLE = "Bellman ④ — Q* (optimality)"
    SUBTITLE = ("The one you found hardest. It is page 14's equation with the max "
                "pushed one square downstream — and that shove is why Q-learning "
                "exists.")
    SECTION = "Value Functions"
    NOTES = "notes p.1 · p.5"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>Say it out loud, no symbols.</b><br><br>"
            "You are on <b>s</b> and the first button <b>a</b> has been forced on "
            "you. So there is nothing to maximise <i>right now</i> — the choice has "
            "already been made for you, possibly stupidly.<br><br>"
            "The ice rolls: with probability P(s'|s,a) you land on s' and get paid "
            "r. Average over that, because you never control it.<br><br>"
            "Now the interesting bit. You are standing on s' and <b>nobody is "
            "forcing you any more</b>. You are free, and Q* is the promise that from "
            "here on you play perfectly. Perfect play at s' means taking the best "
            "button there: <b>max<sub>a'</sub> Q*(s',a')</b>.<br><br>"
            "So the max <b>is</b> still there — it just could not fire on this "
            "square, because this square's action was spoken for. It fires one step "
            "later. <b>Exactly the same relocation you saw on page 13</b>, where the "
            "π-average slid one step later for the same reason. Same trick, "
            "different operator.", "key", "READ IT IN PLAIN ENGLISH"))

        self.add(bellman_map("opt_q"))

        f = Card("the same sentence, in symbols — and the one-substitution table")
        f.add(math_label(
            r"Q^*(s,a) \;=\; \sum_{s'} P(s'\mid s,a)"
            r"\left[\, r \;+\; \gamma \max_{a'} Q^*(s',a') \,\right]", 16))
        f.add(body(
            f"<span style='color:{theme.CYAN}'>Σ<sub>s'</sub> P(s'|s,a)</span> — the "
            f"ice, and nothing else, because your action is already spent "
            f"&nbsp;·&nbsp; <span style='color:{theme.GOOD}'>max<sub>a'</sub></span> "
            f"— the choice, one step later, at the square you land on."))
        f.add(body(
            "Every one of the four equations is the same skeleton with one slot "
            "filled differently. This is the whole page in one table:"
            "<table cellspacing='0' cellpadding='6'>"
            f"<tr style='color:{theme.TEXT_FAINT}; font-size:11px'>"
            "<td>equation</td><td>layer 1 (now)</td><td>layer 2 (next square)</td></tr>"
            f"<tr><td style='color:{theme.ACCENT}'>V<sup>π</sup>(s)</td>"
            "<td><b>Σ<sub>a</sub> π(a|s)</b></td><td>Σ<sub>s'</sub> P → V<sup>π</sup>(s')</td></tr>"
            f"<tr><td style='color:{theme.ACCENT}'>V*(s)</td>"
            "<td><b>max<sub>a</sub></b></td><td>Σ<sub>s'</sub> P → V*(s')</td></tr>"
            f"<tr><td style='color:{theme.VIOLET}'>Q<sup>π</sup>(s,a)</td>"
            "<td>Σ<sub>s'</sub> P (nothing chosen)</td>"
            "<td><b>Σ<sub>a'</sub> π(a'|s')</b> Q<sup>π</sup>(s',a')</td></tr>"
            f"<tr><td style='color:{theme.VIOLET}'>Q*(s,a)</td>"
            "<td>Σ<sub>s'</sub> P (nothing chosen)</td>"
            "<td><b>max<sub>a'</sub></b> Q*(s',a')</td></tr>"
            "</table>"
            "Read the last two rows. Q<sup>π</sup> → Q* is <b>one substitution</b>: "
            "<code>Σ<sub>a'</sub>π(a'|s')</code> becomes <code>max<sub>a'</sub></code>. "
            "That is also, exactly and literally, SARSA → Q-learning."))
        self.add(f)

        self.add(callout(
            "<b>Same idea with no lake in it.</b> You are at the junction and your "
            "passenger has already yanked the wheel left — that turn is happening "
            "whether you like it or not. Q*(here, left) is: \"fine. Given that left "
            "is happening, and given that traffic will do whatever it does, and "
            "given that from the <b>next</b> junction onward I drive perfectly — how "
            "long does my trip take?\" You are not allowed to be smart now. You are "
            "promised to be smart from the next junction on. That promise is the "
            "<code>max<sub>a'</sub></code>.", "good", "INTUITIVE EXAMPLE"))

        t = Card("the backup tree — the max fires at the SECOND layer")
        self.tree = BackupTree("opt_q", height=390)
        t.add(self.tree)
        self.add(t)

        # ---- interactive --------------------------------------------------
        ctl = Card("controls")
        self.env = EnvControls(slip="classic", reward="shaped", gamma=0.99)
        self.env.changed.connect(self.recompute)
        self.actbox = QComboBox()
        self.actbox.addItems([f"a = {a} · {ACTION_NAMES[a]} {ACTION_ARROWS[a]}"
                              for a in range(N_ACTIONS)])
        self.actbox.setCurrentIndex(1)
        self.actbox.currentIndexChanged.connect(self._refresh)
        ctl.add_layout(labelled("Forced a", self.actbox, 74))
        ctl.add(self.env)
        ctl.add(body(
            "Pick a deliberately bad forced action — ← at square 9, say — and watch "
            "Q*(s,a) stay <i>respectable</i>. That is the promise of future perfect "
            "play carrying a stupid first move. Q* is never \"the value of a bad "
            "plan\"; it is \"the value of one bad step, then flawless play\".",
            dim=True))

        gcard = Card("Q*(s,a) — click a square")
        self.grid = GridView(cell=104)
        self.grid.show_q = True
        self.grid.show_values = False
        self.grid.show_policy = False
        self.grid.clickable = True
        self.grid.selected = 9
        self.grid.cellClicked.connect(lambda _s: self._refresh())
        gcard.add(self.grid)
        self.st_q = Stat("Q*(s,a)", "-", theme.VIOLET)
        self.st_v = Stat("V*(s) = max_a Q*", "-", theme.GOOD)
        self.st_res = Stat("Bellman residual", "-", theme.ACCENT)
        gcard.add_layout(stat_row(self.st_q, self.st_v, self.st_res))

        self.row(gcard, ctl, stretches=[0, 1])

        d = Card("branch by branch — with the inner max exposed")
        self.detail = detail_box(370)
        d.add(self.detail)
        self.add(d)

        pc = Card("plots")
        self.canvas = MplCanvas(width=11.0, height=3.5, ncols=2)
        pc.add(self.canvas)
        pc.add(body(
            "<b>Left — the inner max, per landing.</b> One cluster of four bars for "
            "each square the ice can put you on. Inside each cluster exactly one bar "
            "is bright: that is the <code>max<sub>a'</sub>Q*(s',a')</code> this "
            "branch will use. Three per cluster are discarded. Then those winners — "
            "and only those — get averaged by P.<br>"
            "<b>Right — the waterfall</b> that assembles Q*(s,a) from "
            "p·(r + γ·max<sub>a'</sub>Q*) branch by branch.", dim=True))
        self.add(pc)

        # ---- the two ways to store the same fixed point --------------------
        bc = Card("V-iteration vs Q-iteration — same answer, 4× the memory")
        self.tbl = QTableWidget(N_STATES, 4)
        self.tbl.setHorizontalHeaderLabels(
            ["s", "V*(s)  from value iteration", "max_a Q*(s,a)  from Q-iteration",
             "difference"])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl.setMinimumHeight(390)
        self.tbl.setColumnWidth(0, 40)
        self.tbl.setColumnWidth(1, 210)
        self.tbl.setColumnWidth(2, 230)
        self.canvas2 = MplCanvas(width=7.0, height=3.9)
        brow = QHBoxLayout()
        brow.setSpacing(14)
        brow.addWidget(self.tbl, 1)
        bcol = QVBoxLayout()
        bcol.addWidget(self.canvas2)
        self.st_vsw = Stat("V-iteration sweeps", "-", theme.GOOD)
        self.st_qsw = Stat("Q-iteration sweeps", "-", theme.VIOLET)
        self.st_mem = Stat("numbers stored", "-", theme.WARN)
        bcol.addLayout(stat_row(self.st_vsw, self.st_qsw, self.st_mem))
        brow.addLayout(bcol, 1)
        bc.add_layout(brow)
        bc.add(body(
            "Both iterations are the same γ-contraction on the same fixed point, so "
            "they land in the same place in about the same number of sweeps. The "
            "difference is not speed and not accuracy — it is <b>16 numbers versus "
            "64</b>, and what those 64 numbers let you do without a model.", dim=True))
        self.add(bc)

        cc = Card("the code, and the one line that becomes Q-learning")
        cp = CodePane(get_source(q_value_iteration_history))
        cp.sizeHintLine(30)
        cc.add(cp)
        cc.add(callout(
            "<b>Why the max's position is the whole point.</b> Look at what the "
            "inner max needs: <code>max(Q_prev[t.next_state])</code> — one row of "
            "the Q-table, for the state you landed in. It does <b>not</b> need "
            "P.<br><br>"
            "So delete the <code>for t in P[s][a]</code> loop, and instead let the "
            "environment hand you one sampled <code>(s', r)</code>. What is left "
            "is<br>"
            "&nbsp;&nbsp;<code>Q(s,a) ← Q(s,a) + α[ r + γ·max<sub>a'</sub>Q(s',a') "
            "− Q(s,a) ]</code><br>"
            "which is Q-learning, and it never once mentions a transition "
            "probability. Compare with page 13's version, where that slot holds "
            "<code>Q(s',a')</code> for the a' your policy actually took — SARSA. "
            "<b>max vs sampled-a' is the entire off-policy / on-policy divide.</b>",
            "good"))
        cc.add(callout(
            "And the bridge back to page 14, which the table above checks on every "
            "row: <code>max<sub>a'</sub>Q*(s',a') = V*(s')</code>. Substitute that "
            "into Q* and you get the plain one-step lookahead "
            "<code>Q*(s,a) = Σ<sub>s'</sub>P·[r + γV*(s')]</code>. The two "
            "optimality equations are not two facts. They are one fact, written from "
            "two anchor points.", "key"))
        self.add(cc)

        self.finish()
        self.recompute()

    # ------------------------------------------------------------------
    def recompute(self):
        P = self.env.build()
        g = min(self.env.gamma_value(), 0.9999)
        Vstar, vhist = value_iteration_operator(P, gamma=g, op="max",
                                                theta=1e-11, max_sweeps=4000)
        Qstar, qhist = q_value_iteration_history(P, gamma=g, theta=1e-11,
                                                 max_sweeps=4000)
        self.P, self.g, self.V, self.Q = P, g, Vstar, Qstar
        self.vhist, self.qhist = vhist, qhist

        self.grid.Q = Qstar
        self.grid.V = Vstar
        self.grid.update()

        self.st_vsw.set(str(len(vhist) - 1))
        self.st_qsw.set(str(len(qhist) - 1))
        self.st_mem.set(f"{N_STATES} vs {N_STATES * N_ACTIONS}")

        worst = 0.0
        for s in range(N_STATES):
            mq = max(Qstar[s])
            self.tbl.setItem(s, 0, QTableWidgetItem(str(s)))
            i1 = QTableWidgetItem(f"{Vstar[s]:+.8f}")
            i1.setForeground(QColor(theme.GOOD))
            self.tbl.setItem(s, 1, i1)
            i2 = QTableWidgetItem(f"{mq:+.8f}")
            i2.setForeground(QColor(theme.VIOLET))
            self.tbl.setItem(s, 2, i2)
            self.tbl.setItem(s, 3, QTableWidgetItem(f"{abs(mq - Vstar[s]):.2e}"))
            worst = max(worst, abs(mq - Vstar[s]))
        self._worst = worst

        self._refresh()
        self._refresh_convergence()

    # ------------------------------------------------------------------
    def _refresh(self):
        s, a = self.grid.selected, self.actbox.currentIndex()
        P, g, V, Q = self.P, self.g, self.V, self.Q
        self.tree.set_data(P=P, V=V, Q=Q, probs=[[0.25] * 4] * N_STATES,
                           gamma=g, s=s, a=a)
        self.st_q.set(f"{Q[s][a]:+.5f}")
        self.st_v.set(f"{max(Q[s]):+.5f}")

        if is_terminal(s):
            self.st_res.set("0.0e+00")
            self.detail.setText(
                f"<b>State {s} is terminal</b> ({cell_kind(s)}). Q*({s},a) = 0 for "
                f"every a: the self-loop pays 0 and there is no next square to be "
                f"clever on. Both the outer sum and the inner max are trivial.")
            self.canvas.clear()
            self.canvas.refresh()
            return

        out = [f"<b style='color:{theme.ACCENT}'>Q*({s}, {ACTION_NAMES[a]} "
               f"{ACTION_ARROWS[a]})</b> &nbsp;γ={g:.3f}<br>"
               f"<span style='color:{theme.TEXT_DIM}'>Q*(s,a) = Σ<sub>s'</sub> "
               f"P(s'|s,a)·[ r + γ·max<sub>a'</sub> Q*(s',a') ] &nbsp;— no max on "
               f"this square, one max per landing</span><br>"]
        total = 0.0
        for t in merge_duplicates(P[s][a]):
            ns = t.next_state
            if t.done:
                c = t.prob * t.reward
                total += c
                out.append(
                    f"<br><b>s' = {ns}</b> &nbsp;P={t.prob:.4f} &nbsp;r="
                    f"{t.reward:+.2f} &nbsp;<span style='color:{theme.WARN}'>"
                    f"TERMINAL</span><br>&nbsp;&nbsp;the episode ends, so there is "
                    f"no a' to be optimal about → {t.prob:.4f} × {t.reward:+.2f} = "
                    f"<b>{c:+.6f}</b>")
                continue
            best2 = max(range(N_ACTIONS), key=lambda x: Q[ns][x])
            rows = []
            for a2 in range(N_ACTIONS):
                win = (a2 == best2)
                rows.append(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;"
                    f"<span style='color:{theme.GOOD if win else theme.TEXT_FAINT}'>"
                    f"Q*({ns},{ACTION_ARROWS[a2]}) = {Q[ns][a2]:+.5f}"
                    f"{'  ← max, this one is used' if win else '   (discarded)'}"
                    f"</span>")
            mx = Q[ns][best2]
            c = t.prob * (t.reward + g * mx)
            total += c
            out.append(
                f"<br><b>s' = {ns}</b> &nbsp;P={t.prob:.4f} &nbsp;r={t.reward:+.2f}"
                f"<br><span style='color:{theme.TEXT_DIM}'>&nbsp;&nbsp;you are free "
                f"again on {ns} — so take the best button there:</span><br>"
                + "<br>".join(rows)
                + f"<br>&nbsp;&nbsp;max<sub>a'</sub> Q*({ns},a') = "
                  f"<b style='color:{theme.GOOD}'>{mx:+.6f}</b> = V*({ns}) = "
                  f"{V[ns]:+.6f} <span style='color:{theme.GOOD}'>✓</span>"
                + f"<br>&nbsp;&nbsp;branch = {t.prob:.4f} × ({t.reward:+.2f} + "
                  f"{g:.2f}×{mx:+.6f}) = <b>{c:+.6f}</b>")

        res = abs(total - Q[s][a])
        self.st_res.set(f"{res:.1e}")
        out.append(
            f"<br><br><b>Σ over landings = {total:+.6f}</b>"
            f"<br>stored Q*({s},{ACTION_ARROWS[a]}) = <b>{Q[s][a]:+.6f}</b>"
            f"<br>residual = <b style='color:{theme.GOOD}'>{res:.2e}</b><br><br>"
            f"<span style='color:{theme.TEXT_DIM}'>and on this square: "
            f"max<sub>a</sub> Q*({s},a) = {max(Q[s]):+.6f} = V*({s}) = "
            f"{V[s]:+.6f}. The max you did <b>not</b> get to use here is the one "
            f"the previous page's equation uses. Worst mismatch over all 16 "
            f"squares: {getattr(self, '_worst', 0.0):.2e}.</span>")
        self.detail.setText("".join(out))
        self._refresh_plots()

    # ------------------------------------------------------------------
    def _refresh_plots(self):
        s, a = self.grid.selected, self.actbox.currentIndex()
        P, g, Q = self.P, self.g, self.Q
        self.canvas.clear()
        ax1, ax2 = self.canvas.axes

        br = merge_duplicates(P[s][a])
        # ---- left: the inner max, one cluster per landing ----------------
        xt, xl = [], []
        x = 0
        for t in br:
            ns = t.next_state
            if t.done:
                ax1.bar(x + 1.5, 0.0, width=0.7, color=theme.WARN, alpha=0.6)
                ax1.text(x + 1.5, 0.0, "terminal\nno max", ha="center",
                         va="bottom", fontsize=7, color=theme.WARN)
            else:
                best2 = max(range(N_ACTIONS), key=lambda k: Q[ns][k])
                for a2 in range(N_ACTIONS):
                    ax1.bar(x + a2, Q[ns][a2], width=0.78,
                            color=theme.GOOD if a2 == best2 else theme.BORDER,
                            alpha=0.95 if a2 == best2 else 0.75)
            xt.append(x + 1.5)
            xl.append(f"s'={ns}\np={t.prob:.2f}")
            x += 5
        ax1.axhline(0, color=theme.BORDER, lw=1)
        ax1.set_xticks(xt)
        ax1.set_xticklabels(xl, fontsize=8)
        ax1.set_ylabel("Q*(s', a')")
        ax1.set_title("one max per landing — green survives, grey is discarded")

        # ---- right: waterfall -------------------------------------------
        labels, contribs = [], []
        for t in br:
            boot = 0.0 if t.done else max(Q[t.next_state])
            contribs.append(t.prob * (t.reward + g * boot))
            labels.append(f"s'={t.next_state}\np={t.prob:.2f}")
        waterfall(ax2, labels, contribs, Q[s][a],
                  f"Q*({s},{ACTION_ARROWS[a]}) — the winners, averaged by P",
                  theme.VIOLET)
        ax2.set_ylabel("running total")
        self.canvas.refresh()

    # ------------------------------------------------------------------
    def _refresh_convergence(self):
        self.canvas2.clear()
        ax = self.canvas2.ax
        V, Q, g = self.V, self.Q, self.g
        ve = [max(max(abs(self.vhist[k][i] - V[i]) for i in range(N_STATES)), 1e-17)
              for k in range(len(self.vhist))]
        qe = [max(max(abs(self.qhist[k][i][j] - Q[i][j])
                      for i in range(N_STATES) for j in range(N_ACTIONS)), 1e-17)
              for k in range(len(self.qhist))]
        rv, rq = observed_rate(ve), observed_rate(qe)
        ax.semilogy(range(len(ve)), ve, color=theme.GOOD, lw=1.8,
                    label="value iteration  ‖V_k − V*‖∞"
                          + (f"  ({rv:.3f}/sweep)" if rv else ""))
        ax.semilogy(range(len(qe)), qe, color=theme.VIOLET, lw=1.5, ls="--",
                    label="Q-value iteration  ‖Q_k − Q*‖∞"
                          + (f"  ({rq:.3f}/sweep)" if rq else ""))
        ax.semilogy(range(len(ve)), [ve[0] * (g ** k) for k in range(len(ve))],
                    color=theme.WARN, ls=":", lw=1.1,
                    label=f"γ^k bound (γ={g:.2f})")
        ax.set_xlabel("sweep k")
        ax.set_ylabel("worst error")
        ax.set_title("same contraction, same fixed point")
        self.canvas2.legend(ax, loc="best")
        self.canvas2.refresh()
