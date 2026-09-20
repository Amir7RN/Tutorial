"""
Pages 2-3: the environment itself.

  2  The Frozen Lake        -- the board, the rules, the geometry
  3  Stochastic Transitions -- the slip model, sampled vs exact
"""

from __future__ import annotations

import collections

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from rlcore.frozen_lake import (
    ACTION_ARROWS,
    ACTION_NAMES,
    GOAL,
    HOLES,
    N_ACTIONS,
    N_STATES,
    REWARD_SCHEMES,
    SLIP_MODELS,
    FrozenLake,
    build_model,
    cell_kind,
    merge_duplicates,
    move,
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
    legend,
    math_label,
    stat_row,
)
from .base import EnvControls, Page, Transport


# ==========================================================================
# PAGE 5 -- The Frozen Lake
# ==========================================================================

class FrozenLakePage(Page):
    TITLE = "The Frozen Lake"
    SUBTITLE = ("The environment every other page uses. 16 states, 4 actions, "
                "4 holes, 1 goal — and ice that does not do what you tell it.")
    SECTION = "Start Here"
    NOTES = "notes p.1"

    def __init__(self, parent=None):
        super().__init__(parent)

        board = Card("the board")
        g = GridView(cell=88)
        g.show_values = False
        g.show_policy = False
        g.show_indices = True
        board.add(g)
        board.add_layout(legend(
            (theme.C_START, "start · state 0"),
            ("#3d1620", "holes · 5, 7, 11, 12"),
            ("#14361f", "goal · state 15"),
            (theme.C_FROZEN, "frozen · safe"),
        ))

        rules = Card("the rules")
        rules.add(body(
            "<b>States.</b> 16, indexed <code>s = row·4 + col</code>. The agent "
            "always knows exactly which square it is on — this is a "
            "<i>fully observed</i> environment, so observation = state.<br><br>"
            "<b>Actions.</b> 4: <code>0=LEFT 1=DOWN 2=RIGHT 3=UP</code>. Walking "
            "into a wall is legal — you stay put and lose the turn.<br><br>"
            "<b>Termination.</b> Reaching a hole or the goal ends the episode. "
            "Both are <i>absorbing</i>: in the model they loop to themselves with "
            "reward 0 forever, which is the code-level way of saying "
            "V(terminal) = 0.<br><br>"
            "<b>The twist.</b> The ice is slippery. The action you command is not "
            "necessarily the action that executes. That single fact is what makes "
            "this an interesting MDP rather than a maze."))
        rules.add(callout(
            (
                "Why this environment and not a maze? Because the stochasticity is <b>not noise you can average "
                "away</b> — it changes the optimal policy itself. On slippery ice the best move is often to hug "
                "a wall, deliberately bumping into it, because a wall cannot slip you into a hole. You will see "
                "π* do exactly that on page 70."
            ),
            "key"))

        self.row(board, rules, stretches=[0, 1])

        # ---- geometry explorer -------------------------------------------
        geo = Card("where does each action take you? (ice off, for now)")
        geo.add(body(
            "Click any square. The four arrows show where each action lands you "
            "with the ice switched OFF — pure geometry, no randomness yet. Look for "
            "the loops: those are the wall bumps, where the action is legal but you "
            "do not move.", dim=True))

        self.geo_grid = GridView(cell=84)
        self.geo_grid.show_values = False
        self.geo_grid.show_policy = False
        self.geo_grid.clickable = True
        self.geo_grid.selected = 0
        self.geo_grid.cellClicked.connect(lambda s: self.refresh_geo())

        self.geo_tbl = QTableWidget(N_ACTIONS, 4)
        self.geo_tbl.setHorizontalHeaderLabels(
            ["action", "lands on", "cell", "what happens"])
        self.geo_tbl.verticalHeader().setVisible(False)
        self.geo_tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.geo_tbl.setMinimumHeight(170)
        self.geo_tbl.setColumnWidth(0, 130)
        self.geo_tbl.setColumnWidth(1, 90)
        self.geo_tbl.setColumnWidth(2, 90)
        self.geo_tbl.horizontalHeader().setStretchLastSection(True)

        grow = QHBoxLayout(); grow.setSpacing(16)
        gc = QVBoxLayout(); gc.addWidget(self.geo_grid); gc.addStretch(1)
        gc2 = QVBoxLayout()
        gc2.addWidget(self.geo_tbl)
        self.geo_note = body("")
        gc2.addWidget(self.geo_note)
        gc2.addStretch(1)
        grow.addLayout(gc); grow.addLayout(gc2, 1)
        geo.add_layout(grow)
        self.add(geo)

        self.add(callout(
            (
                "Try the four corners. On square 0, <b>two</b> of the four actions do nothing at all — LEFT and "
                "UP both walk into a wall. On square 3 it is RIGHT and UP.<br><br>That is the honest explanation"
                " for the \"agent won't move\" behaviour on page 52. There is no <i>stay</i> action; there is a "
                "<i>failed move</i>, and it costs you a turn exactly like any other."
            ), "warn"))

        # ---- the two interfaces --------------------------------------------
        api = Card("one environment, two interfaces — this is the whole book")
        api.add(body(
            "Everything in this tutor divides on which of these two you are allowed "
            "to touch:", dim=True))
        two = QHBoxLayout(); two.setSpacing(14)

        c1 = Card("build_model()  →  P[s][a]")
        c1.add(body(
            (
                "The full transition table. Gives you every outcome <i>and its probability</i>, without "
                "moving.<br><br><b>Used by:</b> policy evaluation, policy iteration, value "
                "iteration.<br><b>Called:</b> model-based / planning.<br><b>Reality check:</b> a robot may have "
                "an approximate or learned model, but rarely an exact small transition table."
            )))
        two.addWidget(c1)

        c2 = Card("FrozenLake()  →  .reset() / .step()")
        c2.add(body(
            "A simulator. You pick an action, it returns ONE sampled outcome. "
            "You are never told the odds.<br><br>"
            "<b>Used by:</b> Monte Carlo prediction, MC control, TD, Q-learning.<br>"
            "<b>Called:</b> model-free / learning.<br>"
            "<b>Reality check:</b> this is what you actually get."))
        two.addWidget(c2)
        api.add_layout(two)
        api.add(body(
            "Do not worry about the algorithm names yet — the point is only that "
            "there are two doors into the same lake, and which one you are allowed "
            "through decides everything that follows.", dim=True))
        self.add(api)

        self.finish()
        self.refresh_geo()

    # ------------------------------------------------------------------
    def refresh_geo(self):
        """Deterministic geometry: where each action leads, and which ones bump."""
        s = self.geo_grid.selected if self.geo_grid.selected is not None else 0
        overlay = []
        bumps = 0
        for a in range(N_ACTIONS):
            nxt = move(s, a)
            bumped = (nxt == s)
            if bumped:
                bumps += 1
            self.geo_tbl.setItem(a, 0, QTableWidgetItem(
                f"{a} · {ACTION_NAMES[a]} {ACTION_ARROWS[a]}"))
            ni = QTableWidgetItem(str(nxt))
            self.geo_tbl.setItem(a, 1, ni)
            self.geo_tbl.setItem(a, 2, QTableWidgetItem(cell_kind(nxt)))
            if bumped:
                what, col = "wall — you stay on this square", theme.WARN
            elif nxt == GOAL:
                what, col = "the GOAL", theme.GOOD
            elif nxt in HOLES:
                what, col = "a HOLE — episode over", theme.BAD
            else:
                what, col = "moves normally", theme.TEXT_DIM
            wi = QTableWidgetItem(what)
            wi.setForeground(QColor(col))
            self.geo_tbl.setItem(a, 3, wi)
            overlay.append((s, nxt, 1.0))

        self.geo_grid.arrow_overlay = overlay
        self.geo_grid.overlay_text = {}
        self.geo_grid.update()

        kind = cell_kind(s)
        if kind in ("hole", "goal"):
            self.geo_note.setText(
                f"Square {s} is <b>terminal</b> ({kind}). The episode ends the "
                f"moment you arrive, so no action from here means anything — in the "
                f"model it just loops to itself forever with reward 0.")
        else:
            self.geo_note.setText(
                f"Square {s}: <b>{bumps}</b> of the 4 actions bump a wall and leave "
                f"you where you are." if bumps else
                f"Square {s} is in the interior — all 4 actions move you.")


# ==========================================================================
# PAGE 6 -- Stochastic transitions
# ==========================================================================

class TransitionsPage(Page):
    TITLE = "Stochastic Transitions"
    SUBTITLE = ("The slip model in detail: what P(s'|s,a) actually contains, and "
                "proof that sampling really does converge to it.")
    SECTION = "Start Here"
    NOTES = "notes p.1"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(math_label(
            r"P(s' \mid s,a) \;=\; \Pr\{S_{t+1}=s' \mid S_t=s,\, A_t=a\},"
            r"\qquad \sum_{s'} P(s' \mid s,a) = 1", 15))

        self.add(callout(
            "The slip rule: the commanded action executes with probability "
            "<code>p</code>; otherwise the agent goes 90° to one side or the other. "
            "<b>It never reverses.</b><br><br>"
            "In code this is a one-liner because of the action encoding: the two "
            "perpendicular actions are exactly <code>(a+1)%4</code> and "
            "<code>(a-1)%4</code>, and the reverse is <code>(a+2)%4</code>. Pick a "
            "different action order and this stops working.", "key"))

        # ---- explorer -----------------------------------------------------
        exp = Card("transition explorer")
        exp.add(body("Click a square, choose an action. Arrow thickness = probability.",
                     dim=True))

        self.grid = GridView(cell=84)
        self.grid.show_values = False
        self.grid.show_policy = False
        self.grid.clickable = True
        self.grid.selected = 6

        self.act = QComboBox()
        for i, n in enumerate(ACTION_NAMES):
            self.act.addItem(f"{i} · {n}  {ACTION_ARROWS[i]}", i)
        self.act.setCurrentIndex(1)

        self.slip = QComboBox()
        for k, m in SLIP_MODELS.items():
            self.slip.addItem(m.name, k)

        ctl = QVBoxLayout()
        ctl.addLayout(labelled("Action", self.act, 70))
        ctl.addLayout(labelled("Slip model", self.slip, 70))
        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(
            ["probability", "actual move", "lands on", "cell", "reward"])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl.setMinimumHeight(150)
        ctl.addWidget(self.tbl)
        self.note = body("")
        ctl.addWidget(self.note)
        ctl.addStretch(1)

        r = QHBoxLayout(); r.setSpacing(16)
        gcol = QVBoxLayout(); gcol.addWidget(self.grid); gcol.addStretch(1)
        r.addLayout(gcol); r.addLayout(ctl, 1)
        exp.add_layout(r)

        self.grid.cellClicked.connect(lambda s: self.refresh())
        self.act.currentIndexChanged.connect(self.refresh)
        self.slip.currentIndexChanged.connect(self.refresh)
        self.add(exp)

        # ---- law of large numbers ------------------------------------------
        lln = Card("sampled vs exact — does the simulator really match the model?")
        lln.add(body(
            "The model says the probabilities are exactly these. The simulator only "
            "ever gives you one draw at a time. Roll it a few thousand times and "
            "the histogram should converge onto the model bars. This is the "
            "assumption every model-free method silently depends on.", dim=True))

        hb = QHBoxLayout(); hb.setSpacing(8)
        self.n_samples = QSpinBox()
        self.n_samples.setRange(10, 200000)
        self.n_samples.setValue(2000)
        self.n_samples.setSingleStep(500)
        self.btn_sample = QPushButton("Sample")
        self.btn_sample.setObjectName("Primary")
        self.btn_more = QPushButton("+ Sample again (accumulate)")
        self.btn_clear = QPushButton("Clear")
        hb.addWidget(QLabel("draws:"))
        hb.addWidget(self.n_samples)
        hb.addWidget(self.btn_sample)
        hb.addWidget(self.btn_more)
        hb.addWidget(self.btn_clear)
        hb.addStretch(1)
        lln.add_layout(hb)

        self.canvas = MplCanvas(width=9.4, height=3.0)
        lln.add(self.canvas)
        self.st_n = Stat("total draws", "0", theme.ACCENT)
        self.st_err = Stat("max |empirical − model|", "-", theme.WARN)
        lln.add_layout(stat_row(self.st_n, self.st_err))

        self.btn_sample.clicked.connect(lambda: self.sample(reset=True))
        self.btn_more.clicked.connect(lambda: self.sample(reset=False))
        self.btn_clear.clicked.connect(self.clear_samples)
        self.add(lln)

        self.add(callout(
            "Notice the error shrinks like 1/√N, not 1/N. Ten times more samples "
            "buys about three times more accuracy. That slow rate is exactly why "
            "Monte Carlo needs tens of thousands of episodes where value iteration "
            "needs about thirty sweeps — DP computes the expectation, MC has to "
            "measure it.", "warn"))

        # ---- code ---------------------------------------------------------
        cc = Card("the slip, in code")
        cc.add(body("Model side — enumerate every branch with its probability:", dim=True))
        from rlcore.frozen_lake import SlipModel
        cp1 = CodePane(get_source(SlipModel.as_pairs))
        cp1.sizeHintLine(6)
        cc.add(cp1)
        cc.add(body("Simulator side — draw exactly one branch:", dim=True))
        cp2 = CodePane(get_source(FrozenLake.sample_actual_action))
        cp2.sizeHintLine(10)
        cc.add(cp2)
        cc.add(body(
            "Same numbers, two uses. <code>as_pairs</code> hands the whole "
            "distribution to DP; <code>sample_actual_action</code> hands one "
            "realisation to the agent. Everything else in RL follows from which "
            "one you are allowed to call.", dim=True))
        self.add(cc)

        self._counts = collections.Counter()
        self._total = 0
        self.finish()
        self.refresh()

    # ------------------------------------------------------------------
    def refresh(self):
        slip = self.slip.currentData()
        P = build_model(slip, "shaped")
        s = self.grid.selected if self.grid.selected is not None else 6
        a = self.act.currentData()
        sm = SLIP_MODELS[slip]

        raw = P[s][a]
        merged = merge_duplicates(raw)

        # table shows the RAW branches (one row per possible actual move)
        pairs = sm.as_pairs(a)
        self.tbl.setRowCount(len(pairs))
        for i, (prob, actual) in enumerate(pairs):
            nxt = move(s, actual) if not (s in HOLES or s == GOAL) else s
            it = QTableWidgetItem(f"{prob:.4f}")
            it.setForeground(QColor(theme.CYAN))
            f = it.font(); f.setBold(True); it.setFont(f)
            self.tbl.setItem(i, 0, it)
            tag = " (commanded)" if actual == a else " (slip)"
            self.tbl.setItem(i, 1, QTableWidgetItem(
                f"{ACTION_NAMES[actual]} {ACTION_ARROWS[actual]}{tag}"))
            self.tbl.setItem(i, 2, QTableWidgetItem(str(nxt)))
            self.tbl.setItem(i, 3, QTableWidgetItem(cell_kind(nxt)))
            rr = next((t.reward for t in raw if t.next_state == nxt), 0.0)
            self.tbl.setItem(i, 4, QTableWidgetItem(f"{rr:+.2f}"))

        self.grid.arrow_overlay = [(s, t.next_state, t.prob) for t in merged]
        self.grid.overlay_text = {t.next_state: f"{t.prob:.2f}" for t in merged}
        self.grid.update()

        collapsed = len(pairs) - len(merged)
        extra = ""
        if collapsed > 0:
            extra = (f"<br><span style='color:{theme.WARN}'>{collapsed} branch(es) "
                     f"collapsed: a wall clipped two different moves onto the same "
                     f"square, so their probabilities add.</span>")
        self.note.setText(
            f"Σ P = <b>{sum(t.prob for t in merged):.6f}</b>&nbsp;&nbsp;·&nbsp;&nbsp;"
            f"{len(merged)} distinct destination(s) from {len(pairs)} branch(es).{extra}")
        self.clear_samples()

    def clear_samples(self):
        self._counts = collections.Counter()
        self._total = 0
        self.st_n.set("0")
        self.st_err.set("-")
        self.draw_hist()

    def sample(self, reset=True):
        if reset:
            self._counts = collections.Counter()
            self._total = 0
        slip = self.slip.currentData()
        s = self.grid.selected if self.grid.selected is not None else 6
        a = self.act.currentData()
        n = self.n_samples.value()

        env = FrozenLake(slip=slip, reward="shaped", seed=None)
        for _ in range(n):
            env.reset()
            env.state, env.done = s, False
            try:
                nxt, r, d = env.step(a)
            except RuntimeError:
                break
            self._counts[nxt] += 1
        self._total += n
        self.st_n.set(f"{self._total:,}")
        self.draw_hist()

    def draw_hist(self):
        slip = self.slip.currentData()
        P = build_model(slip, "shaped")
        s = self.grid.selected if self.grid.selected is not None else 6
        a = self.act.currentData()
        merged = merge_duplicates(P[s][a])
        dests = sorted({t.next_state for t in merged})
        model = {d: sum(t.prob for t in merged if t.next_state == d) for d in dests}

        self.canvas.clear()
        ax = self.canvas.ax
        x = range(len(dests))
        w = 0.38
        mvals = [model[d] for d in dests]
        evals = [self._counts[d] / self._total if self._total else 0.0 for d in dests]
        ax.bar([i - w / 2 for i in x], mvals, w, label="model  P(s'|s,a)",
               color=theme.ACCENT)
        ax.bar([i + w / 2 for i in x], evals, w, label="empirical (sampled)",
               color=theme.WARN)
        ax.set_xticks(list(x))
        ax.set_xticklabels([f"s'={d}\n{cell_kind(d)}" for d in dests])
        ax.set_ylabel("probability")
        ax.set_ylim(0, max(1.0, max(mvals + evals + [0.1]) * 1.25))
        ax.set_title(f"from s={s}, action {ACTION_NAMES[a]} {ACTION_ARROWS[a]}"
                     f"   ·   {self._total:,} draws")
        self.canvas.legend()
        self.canvas.refresh()

        if self._total:
            err = max(abs(model[d] - self._counts[d] / self._total) for d in dests)
            self.st_err.set(f"{err:.4f}")
            self.st_err.set_color(theme.GOOD if err < 0.02 else theme.WARN)
