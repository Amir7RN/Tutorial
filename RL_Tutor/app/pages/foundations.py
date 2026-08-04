"""
Pages 6-7: naming what the reader has already felt.

  6  Policies  -- pi(s) and pi(a|s): the thing we are actually searching for
  7  The MDP   -- the formal 5-tuple, assembled from parts already seen

Both of these come AFTER the environment pages on purpose. By the time the
reader gets here they have already walked the lake, watched it slip, and
collected rewards. Nothing below introduces a new mechanism -- it only gives
names and symbols to mechanisms already experienced.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from rlcore.frozen_lake import (
    ACTION_ARROWS,
    ACTION_NAMES,
    N_ACTIONS,
    N_STATES,
    build_model,
    cell_kind,
    is_terminal,
    merge_duplicates,
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


# ==========================================================================
# PAGE 6 -- Policies
# ==========================================================================

class PolicyPage(Page):
    TITLE = "Policies"
    SUBTITLE = ("The thing we are actually searching for. Not a route — a rule for "
                "every square.")
    SECTION = "Start Here"
    NOTES = "notes p.1 · p.6"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>Why not just a list of moves?</b> On page 1 you saw that the ice "
            "breaks any fixed plan — after three moves you are not where the plan "
            "assumed. So a solution cannot be a <i>route</i>. It has to be a rule "
            "that answers \"what do I do <b>here</b>?\" for <b>every</b> square, "
            "because you might end up on any of them.<br><br>"
            "That rule is a <b>policy</b>, written π. It is the agent's brain, and "
            "it is the only thing we are ever trying to find.", "key"))

        d = Card("two kinds of policy")
        g = QGridLayout(); g.setSpacing(12)
        g.setColumnStretch(0, 1); g.setColumnStretch(1, 1)

        det = Card("deterministic")
        det.add(math_label(r"\pi(s) = a", 17))
        det.add(body(
            "A lookup table: state in, one action out. \"On square 9, go DOWN.\" "
            "No randomness in the choice.<br><br>"
            "<b>Good for:</b> continuous control where you need one exact number — "
            "a joint torque for your exoskeleton. Also cheaper: computing one value "
            "beats computing a distribution over every possible torque.<br>"
            "<b>Catch:</b> it never explores on its own. It will repeat the same "
            "mistake forever, so DDPG/TD3 have to inject external noise.<br>"
            "<b>Algorithms:</b> DPG, DDPG, TD3."))
        g.addWidget(det, 0, 0)

        sto = Card("stochastic")
        sto.add(math_label(r"\pi(a \mid s) = \Pr\{A_t = a \mid S_t = s\}", 15))
        sto.add(body(
            "A probability distribution over actions. \"On square 9: DOWN 70%, "
            "RIGHT 20%, LEFT 10%.\" The agent <i>samples</i>.<br><br>"
            "<b>Good for:</b> discrete action spaces (this lake), high uncertainty, "
            "partial observability, and anywhere you want exploration built in "
            "rather than bolted on.<br>"
            "<b>Catch:</b> more machinery, noisier gradients.<br>"
            "<b>Algorithms:</b> A2C/A3C, PPO, SAC."))
        g.addWidget(sto, 0, 1)
        d.add_layout(g)
        self.add(d)

        self.add(callout(
            "Every deterministic policy is a stochastic one with all its "
            "probability on a single action. The reverse is not true. That is why "
            "the maths is always written π(a|s) — one notation covering both.",
            "key"))

        # --- reading a policy off the grid ---------------------------------
        rd = Card("what a policy looks like on the lake")
        rd.add(body(
            "Every arrow below is one line of the rule book. That whole picture — "
            "16 arrows — <b>is</b> π. Pick a preset and see.", dim=True))
        self.polbox = QComboBox()
        self.polbox.addItems([
            "π = always DOWN  (a very simple rule)",
            "π = always RIGHT",
            "π = DOWN until the bottom row, then RIGHT  (hand-written)",
            "π = the optimal policy  (computed on page 19 — a preview)",
        ])
        self.polbox.currentIndexChanged.connect(self.show_policy)
        rd.add_layout(labelled("Policy π", self.polbox, 70))
        self.grid = GridView(cell=84)
        self.grid.show_values = False
        rd.add(self.grid)
        self.pol_note = body("")
        rd.add(self.pol_note)
        self.add(rd)

        # --- epsilon-greedy --------------------------------------------------
        eg = Card("ε-greedy: the bridge between the two kinds")
        eg.add(body(
            "This is how nearly every algorithm in this app actually behaves. Take "
            "a deterministic rule, then with probability ε ignore it and act at "
            "random instead. Drag ε from 0 (fully deterministic) to 1 (fully "
            "random).", dim=True))
        self.eps = QSlider(Qt.Horizontal); self.eps.setRange(0, 100); self.eps.setValue(20)
        self.eps_lbl = QLabel("0.20")
        self.eps_lbl.setStyleSheet(f"color:{theme.ACCENT}; font-family:Consolas;"
                                   f"font-weight:700; background:transparent;"
                                   f"min-width:40px;")
        ww = QWidget(); ww.setStyleSheet("background:transparent;")
        wl = QHBoxLayout(ww); wl.setContentsMargins(0, 0, 0, 0); wl.setSpacing(8)
        wl.addWidget(self.eps, 1); wl.addWidget(self.eps_lbl)
        eg.add_layout(labelled("ε", ww, 40))

        eg.add(math_label(
            r"\pi(a\mid s) = 1-\varepsilon+\frac{\varepsilon}{|A|}"
            r"\quad \mathrm{for\ the\ chosen\ action}", 14))
        eg.add(math_label(
            r"\pi(a\mid s) = \frac{\varepsilon}{|A|}"
            r"\quad \mathrm{for\ each\ of\ the\ other\ three}", 14))
        eg.add(body(
            "Read the first formula slowly. With probability 1−ε you take the "
            "chosen action outright. But even when you \"explore\", the random draw "
            "might land on it anyway — that is the extra ε/|A|. So the greedy "
            "action's true probability is a little higher than 1−ε.", dim=True))

        self.canvas = MplCanvas(width=9.6, height=2.7)
        eg.add(self.canvas)
        self.st_greedy = Stat("P(chosen action)", "-", theme.GOOD)
        self.st_other = Stat("P(each other action)", "-", theme.TEXT_DIM)
        self.st_explore = Stat("P(acting at random)", "-", theme.WARN)
        eg.add_layout(stat_row(self.st_greedy, self.st_other, self.st_explore))
        self.eps.valueChanged.connect(self.redraw)
        self.add(eg)

        self.add(callout(
            "ε is the exploration knob, and it must <b>decay</b>. Early on the agent "
            "knows nothing, so ε ≈ 1 is right. Later it should cash in, so ε → 0.05. "
            "A fixed ε means the agent keeps hurling itself into holes forever — you "
            "will watch exactly that happen on page 23.", "warn"))

        gp = Card("greedy · ε-greedy · optimal — three words people mix up")
        gp.add(body(
            "<b>Greedy</b> — always take the action your <i>current</i> numbers say "
            "is best. If those numbers are wrong, greedy is confidently wrong.<br><br>"
            "<b>ε-greedy</b> — greedy, plus a fixed chance of exploring. Cannot be "
            "optimal by construction, since it deliberately wastes ε of its "
            "moves.<br><br>"
            "<b>Optimal (π*)</b> — the policy with the highest expected return from "
            "every state. It <i>is</i> greedy, but with respect to the <b>correct</b> "
            "numbers. Your notes put it exactly: <i>a greedy policy may or may not "
            "be optimal, but an optimal policy must be greedy with respect to the "
            "optimal value function.</i><br><br>"
            "Pages 8–11 build those correct numbers. Pages 12–16 compute them."))
        self.add(gp)

        self.finish()
        self.show_policy()
        self.redraw()

    def show_policy(self):
        idx = self.polbox.currentIndex()
        if idx == 0:
            pi = [1] * N_STATES
            note = ("A legal policy, and a bad one. From the bottom row DOWN just "
                    "bumps the wall forever — the episode times out.")
        elif idx == 1:
            pi = [2] * N_STATES
            note = ("Also legal, also bad. Runs along the top row into the right "
                    "wall and stays there.")
        elif idx == 2:
            pi = []
            for s in range(N_STATES):
                r, c = divmod(s, 4)
                pi.append(1 if r < 3 else 2)
            note = ("Sensible-looking, and it does reach the goal on dry ground. On "
                    "slippery ice it walks straight past holes 5 and 12 and often "
                    "falls in.")
        else:
            from rlcore.dp import value_iteration
            P = build_model("classic", "shaped")
            pi, V, _ = value_iteration(P, gamma=0.99, theta=1e-12)
            note = ("The best possible rule book for this ice. Look at square 0: it "
                    "points UP, into a wall. That is not a mistake — bumping the top "
                    "wall is <i>safer</i> than risking a slip toward hole 5. You "
                    "will compute this yourself on page 19.")
        self.grid.policy = pi
        self.grid.update()
        self.pol_note.setText(note)

    def redraw(self):
        e = self.eps.value() / 100.0
        self.eps_lbl.setText(f"{e:.2f}")
        n = N_ACTIONS
        greedy = 1 - e + e / n
        other = e / n
        probs = [other] * n
        probs[2] = greedy      # pretend RIGHT is the chosen action

        self.canvas.clear()
        ax = self.canvas.ax
        cols = [theme.GOOD if i == 2 else theme.ACCENT_DIM for i in range(n)]
        bars = ax.bar([f"{ACTION_NAMES[i]}\n{ACTION_ARROWS[i]}" for i in range(n)],
                      probs, color=cols)
        for b, v in zip(bars, probs):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.3f}",
                    ha="center", color=theme.TEXT, fontsize=9, fontweight="bold")
        ax.set_ylim(0, 1.12)
        ax.set_ylabel("π(a|s)")
        ax.set_title(f"ε = {e:.2f}   (the rule book says RIGHT here)")
        self.canvas.refresh()

        self.st_greedy.set(f"{greedy:.3f}")
        self.st_other.set(f"{other:.3f}")
        self.st_explore.set(f"{e:.3f}")


# ==========================================================================
# PAGE 7 -- The MDP
# ==========================================================================

class MDPPage(Page):
    TITLE = "The Markov Decision Process"
    SUBTITLE = ("Nothing new here — just the formal name for the five things you "
                "have already been using.")
    SECTION = "Start Here"
    NOTES = "notes p.1"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "You have now met every ingredient separately: squares (page 2), the "
            "slippery transitions (page 3), the payouts (page 4), the discount "
            "(page 5) and the rule book (page 6).<br><br>"
            "Bundle those five together and the result has a name: a <b>Markov "
            "Decision Process</b>. From here on, papers will hand you the 5-tuple "
            "and expect you to know what each letter means.", "key"))

        tup = Card("the 5-tuple  (S, A, P, R, γ)")
        g = QGridLayout(); g.setSpacing(11); g.setColumnStretch(1, 1)
        items = [
            (r"s \in S",
             "<b>State space.</b> The 16 squares. <i>Page 2.</i>"),
            (r"a \in A",
             "<b>Action space.</b> {LEFT, DOWN, RIGHT, UP}. <i>Page 2.</i>"),
            (r"P(s' \mid s,a) = \Pr\{S_{t+1}=s' \mid S_t=s,\, A_t=a\}",
             "<b>Transition function.</b> The ice. Must satisfy "
             "Σ<sub>s'</sub> P(s'|s,a) = 1 for every (s,a). <i>Page 3 — this is "
             "the table you were clicking through.</i>"),
            (r"r(s,a,s') = \mathbb{E}[R_{t+1} \mid S_t=s, A_t=a, S_{t+1}=s']",
             "<b>Reward function.</b> The payout for that transition. "
             "<i>Page 4.</i>"),
            (r"\gamma \in [0,1]",
             "<b>Discount factor.</b> How much the future counts. <i>Page 5.</i>"),
        ]
        for i, (latex, desc) in enumerate(items):
            g.addWidget(math_label(latex, 13), i, 0, Qt.AlignLeft | Qt.AlignVCenter)
            g.addWidget(body(desc), i, 1)
        tup.add_layout(g)
        self.add(tup)

        self.add(callout(
            "<b>The Markov property</b> — the M in MDP, and the reason this is "
            "tractable at all.<br><br>"
            "P(s<sub>t+1</sub> | s<sub>t</sub>, a<sub>t</sub>): the next state "
            "depends <b>only</b> on the current state and action, never on the route "
            "that got you there. Your notes write it as <i>s' depends on (s, a), "
            "NOT on history</i>.<br><br>"
            "Concretely: if you are standing on square 9, it makes no difference "
            "whether you arrived in 3 moves or 30. The square is all the "
            "information there is. That is what lets us store one number per square "
            "instead of one number per possible history.", "key"))

        self.add(callout(
            "<b>The MDP is not a learning algorithm.</b> It is the rule-book — it "
            "only describes how the world transitions. Value iteration, Monte Carlo "
            "and DDPG are different <i>players</i> of the same game.<br><br>"
            "The MDP also does not care <i>how</i> you picked your action. Dice "
            "roll, lookup table, neural network — still an MDP, because the "
            "property is about the environment's response, not the agent's "
            "reasoning.", "good"))

        # --- 1D warm-up ---------------------------------------------------
        w = Card("the smallest possible MDP — three squares")
        w.add(body(
            "Strip the lake down to one dimension: <b>H</b>(ole) ← <b>S</b>(tart) → "
            "<b>G</b>(oal). H and G are absorbing — once there, you loop forever. "
            "Drag the slider to turn the deterministic version into a stochastic "
            "one and watch a second arrow appear.", dim=True))
        self.p_slider = QSlider(Qt.Horizontal); self.p_slider.setRange(50, 100)
        self.p_slider.setValue(100)
        self.p_lbl = QLabel("1.00")
        self.p_lbl.setStyleSheet(f"color:{theme.ACCENT}; font-family:Consolas;"
                                 f"font-weight:700; background:transparent;"
                                 f"min-width:40px;")
        ww = QWidget(); ww.setStyleSheet("background:transparent;")
        wl = QHBoxLayout(ww); wl.setContentsMargins(0, 0, 0, 0); wl.setSpacing(8)
        wl.addWidget(self.p_slider, 1); wl.addWidget(self.p_lbl)
        w.add_layout(labelled("P(intended)", ww, 100))
        self.oned = _OneDMDP()
        w.add(self.oned)
        self.p_slider.valueChanged.connect(self._oned_changed)
        self.add(w)

        # --- the full 5-tuple on the real lake ------------------------------
        tt = Card("the same 5-tuple, on the real 4×4 lake")
        tt.add(body(
            "Click a square, pick an action. This is <code>P</code> and "
            "<code>r</code> for that pair — the exact numbers value iteration will "
            "consume on page 19. You saw this table on page 3; here it is labelled "
            "with its formal names.", dim=True))

        self.env_ctl = EnvControls(show_gamma=False, slip="gym", reward="gym")
        self.env_ctl.changed.connect(self.refresh_table)

        self.grid = GridView(cell=66)
        self.grid.show_values = False
        self.grid.show_policy = False
        self.grid.clickable = True
        self.grid.selected = 10
        self.grid.cellClicked.connect(lambda s: self.refresh_table())

        self.act = QComboBox()
        for i, n in enumerate(ACTION_NAMES):
            self.act.addItem(f"{i} · {n} {ACTION_ARROWS[i]}", i)
        self.act.setCurrentIndex(2)
        self.act.currentIndexChanged.connect(self.refresh_table)

        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(
            ["P(s'|s,a)", "next s'", "cell", "reward r", "terminal?"])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl.setMinimumHeight(170)

        lay = QHBoxLayout(); lay.setSpacing(14)
        col1 = QVBoxLayout(); col1.addWidget(self.grid); col1.addStretch(1)
        col2 = QVBoxLayout()
        col2.addLayout(labelled("Action", self.act, 60))
        col2.addWidget(self.tbl)
        self.sum_lbl = body("")
        col2.addWidget(self.sum_lbl)
        lay.addLayout(col1); lay.addLayout(col2, 1)
        tt.add_layout(lay)
        tt.add(self.env_ctl)
        self.add(tt)

        cc = Card("the whole MDP, in one function")
        cc.add(body(
            "Every letter of the 5-tuple appears in these ~40 lines. There is no "
            "hidden machinery anywhere in this app.", dim=True))
        cp = CodePane(get_source(build_model))
        cp.sizeHintLine(34)
        cc.add(cp)
        self.add(cc)

        self.finish()
        self._oned_changed()
        self.refresh_table()

    def _oned_changed(self):
        p = self.p_slider.value() / 100.0
        self.p_lbl.setText(f"{p:.2f}")
        self.oned.p = p
        self.oned.update()

    def refresh_table(self):
        P = self.env_ctl.build()
        s = self.grid.selected if self.grid.selected is not None else 10
        a = self.act.currentData()
        branches = merge_duplicates(P[s][a])

        self.tbl.setRowCount(len(branches))
        overlay = []
        for i, t in enumerate(branches):
            it = QTableWidgetItem(f"{t.prob:.4f}")
            it.setForeground(QColor(theme.CYAN))
            f = it.font(); f.setBold(True); it.setFont(f)
            self.tbl.setItem(i, 0, it)
            self.tbl.setItem(i, 1, QTableWidgetItem(str(t.next_state)))
            self.tbl.setItem(i, 2, QTableWidgetItem(cell_kind(t.next_state)))
            ri = QTableWidgetItem(f"{t.reward:+.2f}")
            ri.setForeground(QColor(theme.GOOD if t.reward > 0
                                    else theme.BAD if t.reward < 0
                                    else theme.TEXT_DIM))
            self.tbl.setItem(i, 3, ri)
            self.tbl.setItem(i, 4, QTableWidgetItem("yes" if t.done else "no"))
            overlay.append((s, t.next_state, t.prob))

        self.grid.arrow_overlay = overlay
        self.grid.overlay_text = {t.next_state: f"{t.prob:.2f}" for t in branches}
        self.grid.update()

        total = sum(t.prob for t in branches)
        term = ("  ·  <span style='color:%s'>this square is an absorbing terminal "
                "state</span>" % theme.WARN) if is_terminal(s) else ""
        self.sum_lbl.setText(
            f"Σ<sub>s'</sub> P(s'|s={s}, a={a}) = <b>{total:.6f}</b> "
            f"— must be exactly 1, or it is not a probability distribution{term}")


class _OneDMDP(QWidget):
    """H <- S -> G, painted."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        self.p = 1.0
        self.setStyleSheet("background: transparent;")

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        bw, bh = 92, 60
        gap = max(60, (w - 3 * bw - 80) / 2)
        x0 = (w - (3 * bw + 2 * gap)) / 2
        y = h * 0.5 - bh / 2 + 8

        labels = [("H", theme.BAD, "hole · absorbing"),
                  ("S", theme.ACCENT, "start"),
                  ("G", theme.GOOD, "goal · absorbing")]
        xs = []
        for i, (lab, col, sub) in enumerate(labels):
            x = x0 + i * (bw + gap)
            xs.append(x)
            p.setBrush(QColor(theme.BG_RAISED))
            p.setPen(QPen(QColor(col), 2))
            p.drawRoundedRect(x, y, bw, bh, 8, 8)
            p.setPen(QColor(col))
            p.setFont(QFont("Segoe UI", 17, QFont.Bold))
            p.drawText(int(x), int(y + 4), bw, 30, Qt.AlignCenter, lab)
            p.setPen(QColor(theme.TEXT_FAINT))
            p.setFont(QFont("Segoe UI", 8))
            p.drawText(int(x) - 14, int(y + 34), bw + 28, 26,
                       Qt.AlignHCenter | Qt.AlignTop, sub)

        mid = xs[1]
        q = 1.0 - self.p

        self._arc(p, mid + bw, y + bh * 0.32, xs[2], y + bh * 0.32,
                  theme.GOOD, f"{self.p:.2f}", above=True)
        if q > 1e-9:
            self._arc(p, mid, y + bh * 0.7, xs[0] + bw, y + bh * 0.7,
                      theme.BAD, f"{q:.2f}", above=False)

        p.setPen(QColor(theme.TEXT_DIM))
        p.setFont(QFont("Segoe UI", 9))
        txt = ("Action = RIGHT.  Deterministic — it always works."
               if q < 1e-9 else
               f"Action = RIGHT.  Reaches the goal with probability {self.p:.2f}, "
               f"slips into the hole with {q:.2f}.")
        p.drawText(0, h - 22, w, 20, Qt.AlignCenter, txt)
        p.end()

    def _arc(self, p, x1, y1, x2, y2, colour, label, above):
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QPainterPath, QPolygonF
        path = QPainterPath()
        path.moveTo(x1, y1)
        cy = y1 - 38 if above else y1 + 38
        path.quadTo((x1 + x2) / 2, cy, x2, y2)
        p.setPen(QPen(QColor(colour), 2.2))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)
        d = 1 if x2 > x1 else -1
        p.setBrush(QColor(colour)); p.setPen(Qt.NoPen)
        p.drawPolygon(QPolygonF([QPointF(x2, y2),
                                 QPointF(x2 - 9 * d, y2 - 5),
                                 QPointF(x2 - 9 * d, y2 + 5)]))
        p.setPen(QColor(colour))
        p.setFont(QFont("Consolas", 10, QFont.Bold))
        p.drawText(int(min(x1, x2)), int(cy - 14 if above else cy - 2),
                   int(abs(x2 - x1)), 20, Qt.AlignCenter, label)
