"""
The opening sequence -- written for somebody who has never seen RL.

  1  What is Reinforcement Learning?  -- YOU play the lake, by hand
  4  Rewards                          -- what the environment pays you
  5  Return & the Discount Factor     -- turning a list of rewards into ONE number

Design rule for this whole file: nothing appears on screen that has not been
built up first. No value functions, no policies, no Bellman -- those come later,
once the reader has actually felt the environment.
"""

from __future__ import annotations

import random

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from rlcore.frozen_lake import (
    ACTION_ARROWS,
    ACTION_NAMES,
    DOWN,
    GOAL,
    HOLES,
    LEFT,
    N_ACTIONS,
    N_STATES,
    REWARD_SCHEMES,
    RIGHT,
    SLIP_MODELS,
    UP,
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
from .base import Page, Transport


# ==========================================================================
# The agent <-> environment loop diagram
# ==========================================================================

class LoopDiagram(QWidget):
    """The canonical RL loop, with the active arm lit up."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(190)
        self.phase = 0        # 0 = action leaving agent, 1 = reward+state returning
        self.action_txt = "-"
        self.state_txt = "-"
        self.reward_txt = "-"
        self.setStyleSheet("background: transparent;")

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        bw, bh = min(190, w * 0.30), 62
        y = h * 0.5 - bh / 2

        ax, ex = w * 0.06, w * 0.94 - bw

        def box(x, label, colour):
            p.setBrush(QColor(theme.BG_RAISED))
            p.setPen(QPen(QColor(colour), 2))
            p.drawRoundedRect(x, y, bw, bh, 9, 9)
            p.setPen(QColor(theme.TEXT))
            p.setFont(QFont("Segoe UI", 12, QFont.Bold))
            p.drawText(int(x), int(y), int(bw), int(bh), Qt.AlignCenter, label)

        box(ax, "AGENT\n(you, for now)", theme.ACCENT)
        box(ex, "ENVIRONMENT\n(the lake)", theme.CYAN)

        top_y = y - 34
        bot_y = y + bh + 34

        act_col = theme.ACCENT if self.phase == 0 else theme.BORDER
        p.setPen(QPen(QColor(act_col), 2.4))
        p.setBrush(Qt.NoBrush)
        p.drawLine(int(ax + bw / 2), int(y), int(ax + bw / 2), int(top_y))
        p.drawLine(int(ax + bw / 2), int(top_y), int(ex + bw / 2), int(top_y))
        p.drawLine(int(ex + bw / 2), int(top_y), int(ex + bw / 2), int(y))
        self._head(p, ex + bw / 2, y, act_col, up=False)
        p.setPen(QColor(act_col if self.phase == 0 else theme.TEXT_FAINT))
        p.setFont(QFont("Consolas", 11, QFont.Bold))
        p.drawText(int(w * 0.28), int(top_y - 22), int(w * 0.44), 20,
                   Qt.AlignCenter, f"action  a = {self.action_txt}")

        ret_col = theme.GOOD if self.phase == 1 else theme.BORDER
        p.setPen(QPen(QColor(ret_col), 2.4))
        p.drawLine(int(ex + bw / 2), int(y + bh), int(ex + bw / 2), int(bot_y))
        p.drawLine(int(ex + bw / 2), int(bot_y), int(ax + bw / 2), int(bot_y))
        p.drawLine(int(ax + bw / 2), int(bot_y), int(ax + bw / 2), int(y + bh))
        self._head(p, ax + bw / 2, y + bh, ret_col, up=True)
        p.setPen(QColor(ret_col if self.phase == 1 else theme.TEXT_FAINT))
        p.setFont(QFont("Consolas", 11, QFont.Bold))
        p.drawText(int(w * 0.20), int(bot_y + 6), int(w * 0.60), 20,
                   Qt.AlignCenter,
                   f"reward r = {self.reward_txt}   next state s' = {self.state_txt}")
        p.end()

    def _head(self, p, x, y, colour, up):
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QPolygonF
        d = -1 if up else 1
        p.setBrush(QColor(colour))
        p.setPen(Qt.NoPen)
        p.drawPolygon(QPolygonF([
            QPointF(x, y),
            QPointF(x - 6, y - 11 * d),
            QPointF(x + 6, y - 11 * d),
        ]))


# ==========================================================================
# PAGE 1 -- What is Reinforcement Learning?
# ==========================================================================

class WhatIsRLPage(Page):
    TITLE = "What is Reinforcement Learning?"
    SUBTITLE = ("Play the lake yourself, one keypress at a time. Everything else "
                "in this app is about replacing you with an algorithm.")
    SECTION = "Start Here"
    NOTES = "notes p.1 · p.6"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>The setup.</b> An <b>agent</b> sits in an <b>environment</b>. Each "
            "turn it picks an <b>action</b>; the environment answers with a "
            "<b>reward</b> (a single number) and a <b>new situation</b>. That is "
            "the whole interface.<br><br>"
            "<b>What makes it hard.</b> Nobody ever tells the agent the right "
            "answer. There is no labelled dataset. The only feedback is a number, "
            "and it usually arrives <i>long after</i> the move that earned it. The "
            "agent has to work out which of its past actions deserve the credit.",
            "key"))

        d = Card("the loop")
        self.diagram = LoopDiagram()
        d.add(self.diagram)
        d.add(body(
            "Read it clockwise, starting top-left. Right now <b>you</b> are the "
            "agent. By page 19 an algorithm will be, and it will play better than "
            "you.", dim=True))
        self.add(d)

        # ---- manual play ----------------------------------------------------
        play = Card("your turn — walk from the top-left corner to the goal")
        self.grid = GridView(cell=86)
        self.grid.show_values = False
        self.grid.show_policy = False
        self.grid.show_agent = True
        self.grid.agent_state = 0
        play.add(self.grid)

        # D-pad
        pad = QGridLayout()
        pad.setSpacing(5)
        self.btns = {}
        for a, (r, c) in {UP: (0, 1), LEFT: (1, 0), DOWN: (1, 1), RIGHT: (1, 2)}.items():
            b = QPushButton(f"{ACTION_ARROWS[a]}\n{ACTION_NAMES[a]}")
            b.setFixedSize(74, 50)
            b.clicked.connect(lambda _=False, act=a: self.do_step(act))
            pad.addWidget(b, r, c)
            self.btns[a] = b
        padw = QWidget(); padw.setStyleSheet("background:transparent;")
        padw.setLayout(pad)

        side = QVBoxLayout()
        side.addWidget(padw)
        self.btn_random = QPushButton("Random action")
        self.btn_random.clicked.connect(lambda: self.do_step(None))
        self.btn_reset = QPushButton("New episode")
        self.btn_reset.setObjectName("Primary")
        self.btn_reset.clicked.connect(self.do_reset)
        side.addWidget(self.btn_random)
        side.addWidget(self.btn_reset)
        side.addStretch(1)

        padrow = QHBoxLayout(); padrow.setSpacing(16)
        padrow.addLayout(side)
        stats = QVBoxLayout()
        self.st_t = Stat("time step t", "0")
        self.st_s = Stat("state s", "0", theme.ACCENT)
        self.st_r = Stat("last reward", "—", theme.GOOD)
        self.st_G = Stat("rewards so far", "0.00", theme.WARN)
        stats.addLayout(stat_row(self.st_t, self.st_s))
        stats.addLayout(stat_row(self.st_r, self.st_G))
        stats.addStretch(1)
        padrow.addLayout(stats, 1)
        play.add_layout(padrow)

        self.ice = QCheckBox("Turn on the slippery ice  (leave this OFF for your first few tries)")
        self.ice.toggled.connect(self.on_ice)
        play.add(self.ice)
        self.status = body("Press an arrow. The ice is currently OFF, so you go exactly where you point.")
        play.add(self.status)

        logc = Card("what actually happened, step by step")
        self.log = QTableWidget(0, 7)
        self.log.setHorizontalHeaderLabels(
            ["t", "state s", "you pressed", "ice did", "result", "reward r", "next s'"])
        self.log.verticalHeader().setVisible(False)
        self.log.setEditTriggers(QTableWidget.NoEditTriggers)
        self.log.setMinimumHeight(300)
        for c, w in enumerate([34, 60, 96, 96, 230, 80]):
            self.log.setColumnWidth(c, w)
        self.log.horizontalHeader().setStretchLastSection(True)
        logc.add(self.log)
        self.log_note = body("")
        logc.add(self.log_note)

        self.row(play, logc, stretches=[0, 1])

        # ---- the two surprises ------------------------------------------------
        self.add(callout(
            "<b>Surprise 1: there is no \"stay\" action — but you will stay anyway.</b><br>"
            "The action space is exactly four moves: LEFT, DOWN, RIGHT, UP. If you "
            "press a direction that would take you off the board, the move is still "
            "legal — you simply <b>bump the wall and stay put</b>, and the turn is "
            "spent. From the top-left corner, both LEFT and UP do nothing at all.<br><br>"
            "That is why the agent can look frozen while the step counter keeps "
            "climbing. Watch the <b>result</b> column say <i>bumped wall</i>.",
            "warn"))

        self.add(callout(
            "<b>Surprise 2: once the ice is on, the action you press is not the "
            "action that happens.</b><br>"
            "Tick the checkbox above and keep playing. The <b>ice did</b> column "
            "will start disagreeing with <b>you pressed</b>. Press RIGHT and the "
            "lake may slide you UP or DOWN instead — never backwards, but sideways "
            "often.<br><br>"
            "So a single move can fail in <i>two different ways at once</i>: the ice "
            "sends you sideways, and then that sideways move bumps a wall. From "
            "state 0 pressing UP, you stay put <b>2 times out of 3</b> — once "
            "because UP hits the top wall, once because slipping LEFT hits the side "
            "wall. Only the 1-in-3 slip to the RIGHT actually moves you.<br><br>"
            "Page 3 pins this down with exact probabilities. For now, just feel it.",
            "bad"))

        # ---- why this is hard --------------------------------------------------
        hard = Card("why you cannot just plan a route")
        hard.add(body(
            "With the ice off, this is an ordinary maze — A* or Dijkstra solves it "
            "and you are done. You wrote both in C++ already.<br><br>"
            "With the ice on, everything changes:<br>"
            "&nbsp;&nbsp;<b>1.</b> A fixed sequence of moves is worthless. By move "
            "three you are not where the plan assumed.<br>"
            "&nbsp;&nbsp;<b>2.</b> You need a rule for <i>every square</i>, not a "
            "route — because you cannot predict which square you will end up on. "
            "That rule is called a <b>policy</b> (page 6).<br>"
            "&nbsp;&nbsp;<b>3.</b> The best move stops being the obvious one. "
            "Hugging a wall can be <i>better</i> than the direct path, because a "
            "wall cannot slide you into a hole. You will watch the algorithm "
            "discover that on page 19."))
        self.add(hard)

        vocab = Card("the five words, grounded in what you just did")
        tbl = QTableWidget(7, 3)
        tbl.setHorizontalHeaderLabels(["term", "on this lake", "symbol"])
        tbl.verticalHeader().setVisible(False)
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.setColumnWidth(0, 140); tbl.setColumnWidth(1, 600)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        rows = [
            ("Agent", "You, pressing buttons. Later: the algorithm.", "—"),
            ("Environment", "The lake — its walls, its ice, its holes, its goal.", "—"),
            ("State", "Which of the 16 squares you are standing on.", "s"),
            ("Action", "One of the four moves you can press.", "a"),
            ("Reward", "The number the lake hands back after each move.", "r"),
            ("Episode", "One attempt, from the start until you reach the goal "
                        "or fall in a hole.", "—"),
            ("Policy", "A rule saying which action to take in each square. "
                       "Right now, your instinct.", "π"),
        ]
        for i, (a, b, c) in enumerate(rows):
            it = QTableWidgetItem(a)
            it.setForeground(QColor(theme.ACCENT))
            f = it.font(); f.setBold(True); it.setFont(f)
            tbl.setItem(i, 0, it)
            tbl.setItem(i, 1, QTableWidgetItem(b))
            im = QTableWidgetItem(c)
            im.setForeground(QColor(theme.VIOLET))
            tbl.setItem(i, 2, im)
        tbl.resizeRowsToContents()
        tbl.setMinimumHeight(250)
        vocab.add(tbl)
        self.add(vocab)

        nxt = Card("where this is going")
        nxt.add(body(
            "<b>Pages 2–4</b> take the environment apart: the board, the ice, the "
            "rewards.<br>"
            "<b>Page 5</b> turns a whole episode's worth of rewards into a single "
            "score.<br>"
            "<b>Pages 6–7</b> name the thing we are searching for (a policy) and "
            "write the rules down formally (an MDP).<br>"
            "<b>Pages 8–11</b> build the tool that measures how good a square is.<br>"
            "<b>Pages 12–16</b> compute the perfect policy — assuming we know the "
            "ice.<br>"
            "<b>Pages 17–19</b> throw that assumption away and <i>learn</i> it "
            "instead, which is what a real robot has to do."))
        self.add(nxt)

        self.finish()
        self.do_reset()

    # ------------------------------------------------------------------
    def on_ice(self, on):
        self.status.setText(
            "Ice is <b>ON</b>. Your button is now only a <i>request</i> — check the "
            "<b>ice did</b> column." if on else
            "Ice is <b>OFF</b>. You go exactly where you point.")
        self.do_reset()

    def do_reset(self):
        slip = "gym" if self.ice.isChecked() else "deterministic"
        self.env = FrozenLake(slip=slip, reward="shaped", seed=None)
        self.s = self.env.reset()
        self.t = 0
        self.total_r = 0.0
        self.grid.agent_state = self.s
        self.grid.trajectory = [self.s]
        self.grid.update()
        self.log.setRowCount(0)
        self.diagram.phase = 0
        self.diagram.action_txt = "—"
        self.diagram.reward_txt = "—"
        self.diagram.state_txt = "0"
        self.diagram.update()
        self.st_t.set("0"); self.st_s.set("0")
        self.st_r.set("—"); self.st_G.set("0.00")
        for b in self.btns.values():
            b.setEnabled(True)
        self.btn_random.setEnabled(True)
        self.log_note.setText(
            "Reward here is <b>−0.04 per step</b> (time costs you), "
            "<b>+1</b> for the goal, <b>−1</b> for a hole.")

    def do_step(self, action=None):
        """`action=None` means "pick at random" -- used by the Random button."""
        if self.env.done:
            return
        a = random.randrange(N_ACTIONS) if action is None else action
        s_before = self.s
        nxt, r, done = self.env.step(a)
        actual = self.env.last_actual
        bumped = self.env.last_bumped

        self.t += 1
        self.total_r += r
        self.s = nxt

        # ---- log row ---------------------------------------------------
        row = self.log.rowCount()
        self.log.insertRow(row)
        self.log.setItem(row, 0, QTableWidgetItem(str(self.t - 1)))
        self.log.setItem(row, 1, QTableWidgetItem(str(s_before)))

        ci = QTableWidgetItem(f"{ACTION_NAMES[a]} {ACTION_ARROWS[a]}")
        ci.setForeground(QColor(theme.ACCENT))
        self.log.setItem(row, 2, ci)

        slipped = actual != a
        ai = QTableWidgetItem(f"{ACTION_NAMES[actual]} {ACTION_ARROWS[actual]}")
        ai.setForeground(QColor(theme.BAD if slipped else theme.TEXT_DIM))
        if slipped:
            f = ai.font(); f.setBold(True); ai.setFont(f)
        self.log.setItem(row, 3, ai)

        if bumped:
            what, col = "bumped wall — stayed put", theme.WARN
        elif nxt == GOAL:
            what, col = "REACHED THE GOAL", theme.GOOD
        elif nxt in HOLES:
            what, col = "fell in a HOLE", theme.BAD
        else:
            what, col = f"moved to {nxt}", theme.TEXT_DIM
        if slipped:
            what = "SLIPPED · " + what
        wi = QTableWidgetItem(what)
        wi.setForeground(QColor(col))
        self.log.setItem(row, 4, wi)

        ri = QTableWidgetItem(f"{r:+.2f}")
        ri.setForeground(QColor(theme.GOOD if r > 0 else theme.BAD if r < -0.5
                                else theme.TEXT_DIM))
        self.log.setItem(row, 5, ri)
        self.log.setItem(row, 6, QTableWidgetItem(str(nxt)))
        self.log.scrollToBottom()

        # ---- everything else -------------------------------------------
        self.diagram.phase = 1
        self.diagram.action_txt = f"{a} ({ACTION_NAMES[a]})"
        self.diagram.reward_txt = f"{r:+.2f}"
        self.diagram.state_txt = str(nxt)
        self.diagram.update()

        self.grid.agent_state = nxt
        self.grid.trajectory.append(nxt)
        self.grid.update()

        self.st_t.set(str(self.t)); self.st_s.set(str(nxt))
        self.st_r.set(f"{r:+.2f}"); self.st_G.set(f"{self.total_r:+.2f}")

        if done:
            for b in self.btns.values():
                b.setEnabled(False)
            self.btn_random.setEnabled(False)
            self.log_note.setText(
                f"<b style='color:{theme.GOOD}'>Episode over — you reached the goal "
                f"in {self.t} steps.</b> Total reward {self.total_r:+.2f}."
                if nxt == GOAL else
                f"<b style='color:{theme.BAD}'>Episode over — you fell in a hole "
                f"after {self.t} steps.</b> Total reward {self.total_r:+.2f}.")
        elif bumped:
            self.log_note.setText(
                f"You pressed <b>{ACTION_NAMES[a]}</b>"
                + (f" but the ice executed <b>{ACTION_NAMES[actual]}</b>, which "
                   if slipped else ", which ")
                + "ran into a wall — so you stayed on square "
                f"{nxt} and lost a turn.")
        elif slipped:
            self.log_note.setText(
                f"You pressed <b>{ACTION_NAMES[a]}</b>, but the ice executed "
                f"<b style='color:{theme.BAD}'>{ACTION_NAMES[actual]}</b>. "
                f"You ended up on square {nxt}.")
        else:
            self.log_note.setText(
                f"Moved <b>{ACTION_NAMES[a]}</b> to square {nxt}.")


# ==========================================================================
# PAGE 4 -- Rewards
# ==========================================================================

class RewardPage(Page):
    TITLE = "Rewards"
    SUBTITLE = ("The one number the environment gives you. Where it comes from, "
                "and why designing it is the hardest part of applied RL.")
    SECTION = "Start Here"
    NOTES = "notes p.1 · p.6 §2.2.5"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "After every single move, the environment hands back one number: "
            "<b>r</b>. That is the agent's <i>entire</i> supervision signal. No "
            "labels, no gradient, no \"the correct action was DOWN\" — just a "
            "scalar.<br><br>"
            "Notation matters here: the reward for the action you take at time t "
            "is written <b>R<sub>t+1</sub></b>, not R<sub>t</sub>. It arrives "
            "<i>after</i> the action, so it belongs to the next tick of the clock. "
            "That indexing trips up everybody once.", "key"))

        # ---- the schemes ------------------------------------------------------
        sc = Card("the two reward schemes used in this app")
        tbl = QTableWidget(3, 4)
        tbl.setHorizontalHeaderLabels(["event", "Gymnasium (sparse)", "Shaped (your C++ files)", "meaning"])
        tbl.verticalHeader().setVisible(False)
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        tbl.setColumnWidth(0, 190); tbl.setColumnWidth(1, 190); tbl.setColumnWidth(2, 210)
        rows = [
            ("reach the goal", "+1.00", "+1.00", "the thing you actually want"),
            ("fall in a hole", "0.00", "−1.00", "shaped version makes holes genuinely frightening"),
            ("any ordinary step", "0.00", "−0.04", "shaped version makes dawdling cost you — creates urgency"),
        ]
        for i, (a, b, c, d) in enumerate(rows):
            it = QTableWidgetItem(a)
            it.setForeground(QColor(theme.TEXT_DIM))
            f = it.font(); f.setBold(True); it.setFont(f)
            tbl.setItem(i, 0, it)
            for j, v in enumerate((b, c)):
                vi = QTableWidgetItem(v)
                vi.setForeground(QColor(theme.GOOD if v.startswith("+")
                                        else theme.BAD if v.startswith("−")
                                        else theme.TEXT_FAINT))
                tbl.setItem(i, 1 + j, vi)
            tbl.setItem(i, 3, QTableWidgetItem(d))
        tbl.resizeRowsToContents()
        tbl.setMinimumHeight(150)
        sc.add(tbl)
        sc.add(body(
            "Same lake, same physics, same holes. Only the payout table differs — "
            "and it changes everything about how <i>learnable</i> the problem is.",
            dim=True))
        self.add(sc)

        # ---- live episode ------------------------------------------------------
        live = Card("watch rewards arrive, one move at a time")
        self.grid = GridView(cell=80)
        self.grid.show_values = False
        self.grid.show_policy = False
        self.grid.show_agent = True
        live.add(self.grid)
        self.transport = Transport(interval=450)
        self.transport.step.connect(self.step)
        self.transport.reset.connect(self.reset_ep)
        live.add(self.transport)

        ctl = Card("settings")
        self.scheme = QComboBox()
        for k, r in REWARD_SCHEMES.items():
            self.scheme.addItem(r.name, k)
        self.scheme.setCurrentIndex(1)
        self.scheme.currentIndexChanged.connect(self.reset_ep)
        ctl.add_layout(labelled("Reward scheme", self.scheme, 110))
        self.slipbox = QComboBox()
        for k, m in SLIP_MODELS.items():
            self.slipbox.addItem(m.name, k)
        self.slipbox.setCurrentIndex(2)
        self.slipbox.currentIndexChanged.connect(self.reset_ep)
        ctl.add_layout(labelled("Ice", self.slipbox, 110))
        self.st_t = Stat("step", "0", theme.ACCENT)
        self.st_r = Stat("reward this step", "—", theme.GOOD)
        self.st_sum = Stat("running total Σr", "0.00", theme.WARN)
        ctl.add_layout(stat_row(self.st_t, self.st_r))
        ctl.add_layout(stat_row(self.st_sum))
        ctl.add(body(
            "A random policy is walking. Watch the <b>running total</b>: with the "
            "shaped scheme it drifts steadily downward at −0.04 a step, so a long "
            "wander is punished even if it eventually succeeds. With the sparse "
            "scheme it sits at exactly 0.00 until the very last move.", dim=True))
        self.ep_note = body("")
        ctl.add(self.ep_note)
        ctl.add_stretch()

        self.row(live, ctl, stretches=[0, 1])

        self.canvas = MplCanvas(width=10.5, height=2.7, ncols=2)
        self.add(self.canvas)

        # ---- the sparse problem -------------------------------------------------
        sp = Card("the sparse-reward problem — run this, it is the point of the page")
        sp.add(body(
            "Play 2000 episodes under a purely random policy and histogram the "
            "total reward of each. Compare the two schemes.", dim=True))
        hb = QHBoxLayout(); hb.setSpacing(8)
        self.btn_hist = QPushButton("Run 2000 random episodes under both schemes")
        self.btn_hist.setObjectName("Primary")
        self.btn_hist.clicked.connect(self.run_hist)
        hb.addWidget(self.btn_hist); hb.addStretch(1)
        sp.add_layout(hb)
        self.canvas2 = MplCanvas(width=10.5, height=3.0, ncols=2)
        sp.add(self.canvas2)
        self.hist_note = body("")
        sp.add(self.hist_note)
        self.add(sp)

        self.add(callout(
            "Under the sparse scheme, the overwhelming majority of random episodes "
            "score <b>exactly 0.00</b>. Every one of those is a lesson containing "
            "<b>no information whatsoever</b> — the agent cannot tell a near-miss "
            "from a disaster, because both paid the same. Learning cannot begin "
            "until a random walk blunders into the goal by luck.<br><br>"
            "The shaped scheme spreads the scores out. Now \"fell in a hole "
            "quickly\" (−1.1) and \"wandered a long time\" (−0.6) and \"reached the "
            "goal efficiently\" (+0.8) are all <i>different numbers</i>, so there is "
            "something to climb.<br><br>"
            "This is <b>reward shaping</b>, and it is where most real RL projects "
            "actually succeed or fail. Nothing about the lake changed.", "bad"))

        self.add(callout(
            "<b>Reward is not what the agent maximises.</b> Your notes are emphatic "
            "about this and it is worth stating flatly: the agent maximises the "
            "<b>return</b> — the total discounted reward over a whole episode — not "
            "the reward of the next step.<br><br>"
            "A greedy step-by-step reward chaser would never accept −0.04 now to "
            "earn +1 later. Turning this list of rewards into one number worth "
            "maximising is exactly what the next page does.", "key"))

        self.finish()
        self.reset_ep()

    # ------------------------------------------------------------------
    def reset_ep(self):
        self.transport.pause()
        self.env = FrozenLake(slip=self.slipbox.currentData(),
                              reward=self.scheme.currentData(), seed=None)
        self.s = self.env.reset()
        self.t = 0
        self.total = 0.0
        self.rewards = []
        self.grid.agent_state = self.s
        self.grid.trajectory = [self.s]
        self.grid.update()
        self.st_t.set("0"); self.st_r.set("—"); self.st_sum.set("0.00")
        self.ep_note.setText("Press Play.")
        self.draw()

    def step(self):
        if self.env.done:
            self.transport.pause()
            self.reset_ep()
            return
        a = random.randrange(N_ACTIONS)
        nxt, r, done = self.env.step(a)
        self.t += 1
        self.total += r
        self.rewards.append(r)
        self.s = nxt
        self.grid.agent_state = nxt
        self.grid.trajectory.append(nxt)
        self.grid.update()
        self.st_t.set(str(self.t))
        self.st_r.set(f"{r:+.2f}")
        self.st_sum.set(f"{self.total:+.2f}")
        if done:
            self.ep_note.setText(
                f"<b style='color:{theme.GOOD}'>Goal.</b> Total reward "
                f"{self.total:+.2f} over {self.t} steps."
                if nxt == GOAL else
                f"<b style='color:{theme.BAD}'>Hole.</b> Total reward "
                f"{self.total:+.2f} over {self.t} steps.")
        self.draw()

    def draw(self):
        self.canvas.clear()
        a0, a1 = self.canvas.axes
        if self.rewards:
            xs = range(1, len(self.rewards) + 1)
            cols = [theme.GOOD if r > 0 else theme.BAD if r < -0.5 else theme.TEXT_FAINT
                    for r in self.rewards]
            a0.bar(xs, self.rewards, color=cols)
            a0.axhline(0, color=theme.BORDER, lw=1)
            a0.set_xlabel("time step t"); a0.set_ylabel("reward $R_{t+1}$")
            a0.set_title("reward received at each step")
            run = []
            acc = 0.0
            for r in self.rewards:
                acc += r
                run.append(acc)
            a1.plot(list(xs), run, color=theme.WARN, lw=2, marker="o", ms=3)
            a1.axhline(0, color=theme.BORDER, lw=1)
            a1.set_xlabel("time step t"); a1.set_ylabel("Σ reward so far")
            a1.set_title("running total (undiscounted)")
        else:
            a0.set_title("reward per step — press Play")
            a1.set_title("running total")
        self.canvas.refresh()

    def run_hist(self):
        self.btn_hist.setEnabled(False); self.btn_hist.setText("running…")
        try:
            out = {}
            for key in ("gym", "shaped"):
                env = FrozenLake(slip="gym", reward=key, seed=3)
                totals = []
                for _ in range(2000):
                    s = env.reset()
                    tot = 0.0
                    for _ in range(200):
                        _, r, done = env.step(random.randrange(N_ACTIONS))
                        tot += r
                        if done:
                            break
                    totals.append(tot)
                out[key] = totals

            self.canvas2.clear()
            a0, a1 = self.canvas2.axes
            a0.hist(out["gym"], bins=30, color=theme.BAD)
            a0.set_title("Gymnasium (sparse) — almost every episode scores 0.00")
            a0.set_xlabel("total reward of the episode"); a0.set_ylabel("episodes")
            a1.hist(out["shaped"], bins=40, color=theme.GOOD)
            a1.set_title("Shaped — scores spread out, so there is a gradient")
            a1.set_xlabel("total reward of the episode"); a1.set_ylabel("episodes")
            self.canvas2.refresh()

            zeros = sum(1 for v in out["gym"] if abs(v) < 1e-9)
            distinct = len({round(v, 2) for v in out["shaped"]})
            self.hist_note.setText(
                f"Sparse scheme: <b style='color:{theme.BAD}'>{zeros}/2000</b> "
                f"({zeros/20:.1f}%) episodes returned exactly 0.00 — completely "
                f"uninformative. Shaped scheme: "
                f"<b style='color:{theme.GOOD}'>{distinct}</b> distinct outcome "
                f"values to learn from.")
        finally:
            self.btn_hist.setEnabled(True)
            self.btn_hist.setText("Run 2000 random episodes under both schemes")

    def on_hide(self):
        self.transport.pause()


# ==========================================================================
# PAGE 5 -- Return and the discount factor
# ==========================================================================

class ReturnPage(Page):
    TITLE = "Return & the Discount Factor"
    SUBTITLE = ("Turning a whole episode's rewards into ONE number. Built up term "
                "by term, from a real episode you can regenerate.")
    SECTION = "Start Here"
    NOTES = "notes p.1 · p.6"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>The problem.</b> Page 4 left you with a <i>list</i> of rewards: "
            "−0.04, −0.04, −0.04, +1. You cannot maximise a list. You need a single "
            "score for the whole episode, so that two different ways of playing can "
            "be compared.<br><br>"
            "The obvious answer — add them up — nearly works. The fix it needs is "
            "the discount factor.", "key"))

        # ---- step 1: the naive sum ---------------------------------------------
        s1 = Card("step 1 — just add the rewards up")
        s1.add(math_label(r"G_t \;=\; R_{t+1} + R_{t+2} + R_{t+3} + \cdots + R_{T}", 15))
        s1.add(body(
            "This is called the <b>return</b>, written G. It works fine for a task "
            "that always ends. But it breaks in two ways:<br><br>"
            "&nbsp;&nbsp;<b>1. It can be infinite.</b> For a task with no end — "
            "balancing a pole, walking forever — the sum diverges. Every policy "
            "scores ∞, so no policy is better than any other. There is nothing to "
            "optimise.<br>"
            "&nbsp;&nbsp;<b>2. It has no sense of time.</b> +1 in three steps and "
            "+1 in three hundred steps score identically. But a reward far in the "
            "future is <i>less certain</i> — the episode may end, your model of the "
            "world may be wrong. It should be worth less."))
        self.add(s1)

        # ---- step 2: discounting -------------------------------------------------
        s2 = Card("step 2 — shrink each reward by how far away it is")
        s2.add(body(
            "Multiply the reward k steps in the future by γ<sup>k</sup>, where "
            "γ (gamma) is a number between 0 and 1. Since γ<sup>k</sup> gets "
            "smaller as k grows, distant rewards count for less:", dim=True))
        s2.add(math_label(
            r"G_t \;=\; R_{t+1} + \gamma R_{t+2} + \gamma^2 R_{t+3} + \cdots"
            r"\;=\; \sum_{k=0}^{\infty} \gamma^{k} R_{t+k+1}", 16))
        s2.add(body(
            "Both problems are now fixed. The sum is guaranteed finite (bounded by "
            "r<sub>max</sub>/(1−γ)), and sooner is genuinely worth more than later.",
            dim=True))
        s2.add(body(
            "<b>Sanity check on the indices:</b> the first reward R<sub>t+1</sub> "
            "is multiplied by γ<sup>0</sup> = 1, i.e. not discounted at all. It "
            "already happened. Only the <i>future</i> gets shrunk.", dim=True))
        self.add(s2)

        # ---- step 3: worked example ----------------------------------------------
        s3 = Card("step 3 — a real episode, computed term by term")
        s3.add(body(
            "Below is an actual episode played on the lake. Every column is one "
            "step of the arithmetic. Change γ with the slider and watch each term "
            "change; the bottom row is the final answer.", dim=True))

        hb = QHBoxLayout(); hb.setSpacing(8)
        self.btn_new = QPushButton("Play a new episode")
        self.btn_new.setObjectName("Primary")
        self.btn_new.clicked.connect(self.new_episode)
        self.polbox = QComboBox()
        self.polbox.addItems(["a decent hand-written policy", "a random walk"])
        self.polbox.currentIndexChanged.connect(self.new_episode)
        hb.addWidget(self.btn_new)
        hb.addWidget(QLabel("played by:")); hb.addWidget(self.polbox)
        hb.addStretch(1)
        s3.add_layout(hb)

        self.gs = QSlider(Qt.Horizontal); self.gs.setRange(0, 100); self.gs.setValue(90)
        self.gl = QLabel("0.90")
        self.gl.setStyleSheet(f"color:{theme.ACCENT}; font-family:Consolas;"
                              f"font-weight:700; background:transparent;"
                              f"min-width:40px;")
        gw = QWidget(); gw.setStyleSheet("background:transparent;")
        gwl = QHBoxLayout(gw); gwl.setContentsMargins(0, 0, 0, 0); gwl.setSpacing(8)
        gwl.addWidget(self.gs, 1); gwl.addWidget(self.gl)
        s3.add_layout(labelled("Discount γ", gw, 90))
        self.gs.valueChanged.connect(self.redraw)

        self.tbl = QTableWidget(0, 7)
        self.tbl.setHorizontalHeaderLabels([
            "t", "state s_t", "action a_t", "reward R_{t+1}",
            "γ^t", "γ^t · R_{t+1}", "G_t  (return from here on)"])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl.setMinimumHeight(330)
        for c, w in enumerate([36, 74, 92, 116, 90, 120, 200]):
            self.tbl.setColumnWidth(c, w)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        s3.add(self.tbl)

        self.total_lbl = body("")
        s3.add(self.total_lbl)

        self.st_G = Stat("G₀ — score of this episode", "—", theme.WARN)
        self.st_len = Stat("episode length", "—", theme.ACCENT)
        self.st_hz = Stat("effective horizon 1/(1−γ)", "—", theme.CYAN)
        s3.add_layout(stat_row(self.st_G, self.st_len, self.st_hz))
        self.add(s3)

        self.canvas = MplCanvas(width=10.5, height=3.0, ncols=2)
        self.add(self.canvas)

        # ---- step 4: the backward recursion -------------------------------------
        s4 = Card("step 4 — the trick for computing every G_t at once")
        s4.add(body(
            "Look at the last column of the table. G<sub>t</sub> is the return "
            "measured <i>from step t onward</i>, so there is one for every step, "
            "not just for the start.<br><br>"
            "Computing each one from scratch would be O(T²). But notice:", dim=True))
        s4.add(math_label(r"G_t \;=\; R_{t+1} + \gamma\, G_{t+1}", 16))
        s4.add(body(
            "Each return is just the next reward plus the discounted <i>next</i> "
            "return. So walk the episode <b>backwards</b> from the end, carrying one "
            "running number:", dim=True))
        s4.add(CodePane(
            "G = 0.0\n"
            "for t in range(len(trajectory) - 1, -1, -1):   # backwards!\n"
            "    state, action, reward = trajectory[t]\n"
            "    G = gamma * G + reward      # G is now exactly G_t\n"
            "    ..."))
        s4.add(callout(
            "Memorise those three lines. They appear <b>unchanged</b> in every "
            "Monte Carlo function on pages 17–19 — it is how the algorithm turns a "
            "played episode into something learnable. And the equation "
            "G<sub>t</sub> = R<sub>t+1</sub> + γG<sub>t+1</sub> is the seed of the "
            "Bellman equation on page 11, which is the same idea applied to "
            "<i>averages</i> instead of a single episode.", "key"))
        self.add(s4)

        # ---- step 5: what gamma does ---------------------------------------------
        s5 = Card("step 5 — what γ actually buys you")
        s5.add(body(
            "Two episodes, same lake, same reward scheme. One reaches the goal in "
            "6 steps; the other takes a scenic 18-step route to the same place. "
            "Undiscounted, both look similar. Discounted, they do not.", dim=True))
        self.canvas2 = MplCanvas(width=10.5, height=3.0, ncols=2)
        s5.add(self.canvas2)
        self.cmp_note = body("")
        s5.add(self.cmp_note)
        self.add(s5)

        self.add(callout(
            "<b>γ → 0</b> — the agent is myopic. Only the very next reward counts; "
            "it will never accept a small cost now for a big payoff later.<br>"
            "<b>γ → 1</b> — the agent is far-sighted, but training converges more "
            "slowly and the numbers get delicate.<br>"
            "<b>Typical: 0.95 – 0.99.</b> The quantity worth thinking in is the "
            "<b>effective horizon 1/(1−γ)</b>: at γ = 0.99 the agent effectively "
            "cares about the next ~100 steps. If your task needs 500 steps of "
            "foresight, γ = 0.99 is too small — not a tuning nuisance, a modelling "
            "error.", "warn"))

        self.finish()
        self.new_episode()

    # ------------------------------------------------------------------
    def new_episode(self):
        """Play one episode and remember it. Deterministic ice, so the
        trajectory is readable and the arithmetic is easy to follow."""
        env = FrozenLake(slip="deterministic" if self.polbox.currentIndex() == 0
                         else "gym",
                         reward="shaped", seed=None)
        if self.polbox.currentIndex() == 0:
            # hand-written: go DOWN until the bottom row, then RIGHT
            def pol(s):
                r, c = divmod(s, 4)
                return DOWN if r < 3 else RIGHT
        else:
            def pol(s):
                return random.randrange(N_ACTIONS)

        for _attempt in range(400):
            traj = []
            s = env.reset()
            for _ in range(60):
                a = pol(s)
                nxt, r, done = env.step(a)
                traj.append((s, a, r))
                s = nxt
                if done:
                    break
            # prefer a readable episode; random walks can be enormous
            if 3 <= len(traj) <= 22:
                break
        self.traj = traj
        self.redraw()

    def redraw(self):
        g = self.gs.value() / 100.0
        self.gl.setText(f"{g:.2f}")
        traj = self.traj

        # backward recursion -> G_t for every t
        Gs = [0.0] * len(traj)
        G = 0.0
        for t in range(len(traj) - 1, -1, -1):
            G = g * G + traj[t][2]
            Gs[t] = G

        self.tbl.setRowCount(len(traj))
        contribs = []
        for t, (s, a, r) in enumerate(traj):
            w = g ** t
            contribs.append(w * r)
            self.tbl.setItem(t, 0, QTableWidgetItem(str(t)))
            self.tbl.setItem(t, 1, QTableWidgetItem(str(s)))
            self.tbl.setItem(t, 2, QTableWidgetItem(
                f"{ACTION_NAMES[a]} {ACTION_ARROWS[a]}"))
            ri = QTableWidgetItem(f"{r:+.2f}")
            ri.setForeground(QColor(theme.GOOD if r > 0
                                    else theme.BAD if r < -0.5 else theme.TEXT_DIM))
            self.tbl.setItem(t, 3, ri)
            wi = QTableWidgetItem(f"{w:.4f}")
            wi.setForeground(QColor(theme.CYAN))
            self.tbl.setItem(t, 4, wi)
            ci = QTableWidgetItem(f"{w * r:+.4f}")
            ci.setForeground(QColor(theme.VIOLET))
            self.tbl.setItem(t, 5, ci)
            gi = QTableWidgetItem(f"{Gs[t]:+.4f}")
            gi.setForeground(QColor(theme.WARN))
            f = gi.font(); f.setBold(t == 0); gi.setFont(f)
            self.tbl.setItem(t, 6, gi)

        G0 = sum(contribs)
        terms = "  ".join(
            f"{'+' if c >= 0 else '−'} {abs(c):.4f}" for c in contribs[:8])
        if len(contribs) > 8:
            terms += "  …"
        self.total_lbl.setText(
            f"<b>G₀ = column 6 added up</b> &nbsp;=&nbsp; {terms} &nbsp;=&nbsp; "
            f"<b style='color:{theme.WARN}'>{G0:+.4f}</b><br>"
            f"<span style='color:{theme.TEXT_FAINT}'>The last column computes the "
            f"same thing backwards and agrees at t=0: {Gs[0]:+.4f} "
            f"(difference {abs(G0 - Gs[0]):.1e}).</span>")

        self.st_G.set(f"{G0:+.4f}")
        self.st_len.set(f"{len(traj)} steps")
        self.st_hz.set("∞" if g >= 1.0 else f"{1/(1-g):.1f} steps")

        # ---- plots -----------------------------------------------------
        self.canvas.clear()
        a0, a1 = self.canvas.axes
        ks = list(range(len(traj)))
        a0.plot(ks, [g ** k for k in ks], color=theme.ACCENT, lw=2, marker="o", ms=4)
        a0.set_ylim(-0.05, 1.05)
        a0.set_xlabel("steps into the future  k"); a0.set_ylabel("γ^k")
        a0.set_title(f"how much a reward k steps away is worth   (γ={g:.2f})")

        cols = [theme.GOOD if c > 0 else theme.BAD if c < -0.02 else theme.TEXT_FAINT
                for c in contribs]
        a1.bar(ks, contribs, color=cols)
        a1.axhline(0, color=theme.BORDER, lw=1)
        a1.set_xlabel("time step t"); a1.set_ylabel("γ^t · R")
        a1.set_title(f"what each step contributed   →   G₀ = {G0:+.4f}")
        self.canvas.refresh()

        # ---- fast vs slow comparison ------------------------------------
        fast = [-0.04] * 5 + [1.0]
        slow = [-0.04] * 17 + [1.0]
        Gf = sum((g ** k) * r for k, r in enumerate(fast))
        Gsl = sum((g ** k) * r for k, r in enumerate(slow))
        undf, undsl = sum(fast), sum(slow)

        self.canvas2.clear()
        b0, b1 = self.canvas2.axes
        b0.bar(range(len(fast)), [(g ** k) * r for k, r in enumerate(fast)],
               color=theme.GOOD)
        b0.axhline(0, color=theme.BORDER, lw=1)
        b0.set_title(f"6-step route   →   G = {Gf:+.4f}")
        b0.set_xlabel("step"); b0.set_ylabel("γ^t · R")
        b1.bar(range(len(slow)), [(g ** k) * r for k, r in enumerate(slow)],
               color=theme.WARN)
        b1.axhline(0, color=theme.BORDER, lw=1)
        b1.set_title(f"18-step route   →   G = {Gsl:+.4f}")
        b1.set_xlabel("step"); b1.set_ylabel("γ^t · R")
        self.canvas2.refresh()

        self.cmp_note.setText(
            f"Undiscounted the gap is only {undf:+.2f} vs {undsl:+.2f} "
            f"(<b>{undf - undsl:+.2f}</b>). Discounted at γ={g:.2f} it is "
            f"{Gf:+.4f} vs {Gsl:+.4f} "
            f"(<b style='color:{theme.WARN}'>{Gf - Gsl:+.4f}</b>). "
            + ("Set γ to 1.00 and the two collapse to the step-cost difference "
               "alone — with no step cost they would be identical, and the agent "
               "would have no reason to hurry."
               if g >= 0.999 else
               "Discounting is what makes the +1 at the end of the long route "
               "worth measurably less."))
