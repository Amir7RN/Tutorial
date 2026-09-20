"""
Pages 8-11: value functions.

  8   V(s)          -- the state-value function
  9   Q(s,a)        -- the action-value function
  10  V vs Q        -- the difference, which is the base of actor-critic
  11  Bellman       -- expectation and optimality equations, one-step backups
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from rlcore.dp import policy_evaluation, policy_iteration, value_iteration
from rlcore.frozen_lake import (
    ACTION_ARROWS,
    ACTION_NAMES,
    N_ACTIONS,
    N_STATES,
    build_model,
    cell_kind,
    deterministic_to_probs,
    is_terminal,
    merge_duplicates,
    q_from_V,
    q_table_from_V,
    V_from_Q,
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
from .base import EnvControls, Page


# ==========================================================================
# PAGE 7 -- State value function
# ==========================================================================

class StateValuePage(Page):
    TITLE = "V(s) — State Value"
    SUBTITLE = ("\"How good is it to BE here, if I keep following π?\" "
                "Forward-looking, always.")
    SECTION = "Value Functions"
    NOTES = "notes p.1 §2.6.2"

    def __init__(self, parent=None):
        super().__init__(parent)

        m = Card("definition")
        m.add(math_label(
            r"V^\pi(s) \;=\; \mathbb{E}_\pi\!\left[\, G_t \mid S_t = s \,\right]"
            r"\;=\; \mathbb{E}_\pi\!\left[\, \sum_{k=0}^{\infty} \gamma^k R_{t+k+1}"
            r" \mid S_t = s \,\right]", 15))
        m.add(body(
            "Three things to notice, all of which your notes flag:<br>"
            "&nbsp;&nbsp;<b>1.</b> It is an <b>expectation</b> — an average over "
            "the randomness in both the policy and the ice.<br>"
            "&nbsp;&nbsp;<b>2.</b> It is indexed by <b>π</b>. There is no such thing "
            "as \"the value of state 10\"; only its value <i>under a policy</i>.<br>"
            "&nbsp;&nbsp;<b>3.</b> It is <b>forward-looking</b>. It says nothing "
            "about how you got here or what you already collected."))
        self.add(m)

        self.add(callout(
            "<b>The single most common misreading.</b> V(s) is not \"reward "
            "gathered so far\". Your notes put it exactly right: value functions "
            "answer <i>\"how much reward will I get from here forward?\"</i>, never "
            "<i>\"how much did I get to get here?\"</i> If it took you 5 steps or "
            "50 steps to reach state 10, V(10) is identical. That is the Markov "
            "property in action — the past is already priced in to <i>where you "
            "are</i>.", "bad"))

        # ---- interactive --------------------------------------------------
        ctl = Card("compute V^π on the real lake")
        self.env = EnvControls(slip="classic", reward="shaped", gamma=0.99)
        self.env.changed.connect(self.recompute)

        self.pol = QComboBox()
        self.pol.addItems([
            "π = optimal (π*)",
            "π = always DOWN",
            "π = always RIGHT",
            "π = always LEFT (deliberately terrible)",
            "π = uniform random",
        ])
        self.pol.currentIndexChanged.connect(self.recompute)
        ctl.add_layout(labelled("Policy π", self.pol, 80))
        ctl.add(self.env)

        gcard = Card("V^π(s) — colour is the value, arrow is π")
        self.grid = GridView(cell=92)
        self.grid.value_fmt = "{:.3f}"
        gcard.add(self.grid)
        gcard.add_layout(legend(
            ("#1f7a4d", "high value"),
            ("#1d2733", "zero"),
            ("#7d1128", "negative value"),
        ))
        self.st_v0 = Stat("V(start)", "-", theme.GOOD)
        self.st_min = Stat("min V", "-", theme.BAD)
        self.st_max = Stat("max V", "-", theme.GOOD)
        gcard.add_layout(stat_row(self.st_v0, self.st_min, self.st_max))

        self.row(gcard, ctl, stretches=[0, 1])

        # ---- bar chart -----------------------------------------------------
        self.canvas = MplCanvas(width=10.5, height=3.0)
        self.add(self.canvas)

        # ---- code ----------------------------------------------------------
        cc = Card("how it is actually computed")
        cc.add(body(
            (
                "Iterative policy evaluation — solve the Bellman expectation equation by repeated application "
                "until the numbers stop moving. Full detail on page 67."
            ), dim=True))
        cp = CodePane(get_source(policy_evaluation))
        cp.sizeHintLine(24)
        cc.add(cp)
        self.add(cc)

        self.finish()
        self.recompute()

    def _policy(self):
        idx = self.pol.currentIndex()
        P = self.env.build()
        g = self.env.gamma_value()
        if idx == 0:
            pi, _, _ = policy_iteration(P, gamma=min(g, 0.9999), theta=1e-12)
            return pi, None
        if idx == 1:
            return [1] * N_STATES, None
        if idx == 2:
            return [2] * N_STATES, None
        if idx == 3:
            return [0] * N_STATES, None
        probs = [[1.0 / N_ACTIONS] * N_ACTIONS for _ in range(N_STATES)]
        return None, probs

    def recompute(self):
        P = self.env.build()
        g = min(self.env.gamma_value(), 0.9999)
        pi, probs = self._policy()

        if pi is not None:
            V = policy_evaluation(P, pi, g, 1e-12)
            self.grid.policy = pi
            self.grid.show_policy = True
        else:
            # stochastic policy: full Bellman expectation with pi(a|s)
            V = [0.0] * N_STATES
            for _ in range(20000):
                Vp = list(V)
                delta = 0.0
                for s in range(N_STATES):
                    v = sum(probs[s][a] * q_from_V(P, Vp, s, a, g)
                            for a in range(N_ACTIONS))
                    delta = max(delta, abs(v - V[s]))
                    V[s] = v
                if delta < 1e-12:
                    break
            self.grid.show_policy = False
            self.grid.policy = None

        self.grid.V = V
        self.grid.update()
        self.st_v0.set(f"{V[0]:+.4f}")
        self.st_min.set(f"{min(V):+.4f}")
        self.st_max.set(f"{max(V):+.4f}")

        self.canvas.clear()
        ax = self.canvas.ax
        cols = [theme.BAD if cell_kind(s) == "hole"
                else theme.GOOD if cell_kind(s) == "goal"
                else theme.ACCENT for s in range(N_STATES)]
        ax.bar(range(N_STATES), V, color=cols)
        ax.axhline(0, color=theme.BORDER, lw=1)
        ax.set_xticks(range(N_STATES))
        ax.set_xlabel("state s")
        ax.set_ylabel("V^π(s)")
        ax.set_title(f"V^π for {self.pol.currentText()}   (γ={g:.2f})")
        self.canvas.refresh()


# ==========================================================================
# PAGE 8 -- Action value function
# ==========================================================================

class ActionValuePage(Page):
    TITLE = "Q(s,a) — Action Value"
    SUBTITLE = ("\"How good is it to be here AND press this specific button?\" "
                "The function that makes model-free control possible.")
    SECTION = "Value Functions"
    NOTES = "notes p.1 §2.6.3"

    def __init__(self, parent=None):
        super().__init__(parent)

        m = Card("definition")
        m.add(math_label(
            r"Q^\pi(s,a) \;=\; \mathbb{E}_\pi\!\left[\, G_t \mid S_t=s,\; A_t=a \,\right]", 15))
        m.add(body(
            "Read it as a <b>forced first move</b>: take action a right now — even "
            "if π would never choose it — and only <i>afterwards</i> go back to "
            "following π forever.<br><br>"
            "Your notes phrase it perfectly: <i>\"I don't care what your policy "
            "usually does. If you move LEFT right now and THEN follow your policy "
            "forever after, how much reward will you get?\"</i>"))
        self.add(m)

        self.add(callout(
            "The forced first action does not only change one step — it changes "
            "<b>which states you visit for the rest of the episode</b>. Your notes "
            "call it the butterfly effect: the policy for the remaining 49 steps is "
            "the same rule-book, but you are now walking in the ditch instead of on "
            "the pavement, so the states and rewards are completely different.",
            "key"))

        # ---- Q grid --------------------------------------------------------
        ctl = Card("controls")
        self.env = EnvControls(slip="classic", reward="shaped", gamma=0.99)
        self.env.changed.connect(self.recompute)
        ctl.add(self.env)
        self.chk_v = QCheckBox("also show V(s) = max_a Q(s,a) as the cell number")
        self.chk_v.setChecked(False)
        self.chk_v.toggled.connect(self.recompute)
        ctl.add(self.chk_v)
        ctl.add(body(
            "Each square is split into four triangles — one per action, placed where "
            "that action points. The gold outline marks argmax<sub>a</sub> Q(s,a), "
            "i.e. the greedy action. Seeing all four numbers at once is the point: "
            "V(s) would show you only the winner.", dim=True))

        gcard = Card("Q*(s,a)")
        self.grid = GridView(cell=118)
        self.grid.show_q = True
        self.grid.show_values = False
        self.grid.show_policy = False
        self.grid.show_indices = True
        gcard.add(self.grid)
        self.row(gcard, ctl, stretches=[0, 1])

        # ---- table ----------------------------------------------------------
        tcard = Card("the Q-table — click a square above")
        self.grid.clickable = True
        self.grid.selected = 10
        self.grid.cellClicked.connect(lambda s: self.refresh_table())
        self.tbl = QTableWidget(N_ACTIONS, 4)
        self.tbl.setHorizontalHeaderLabels(
            ["action", "Q(s,a)", "one-step lookahead", "greedy?"])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl.setMinimumHeight(190)
        self.tbl.setWordWrap(False)
        self.tbl.setColumnWidth(0, 130)
        self.tbl.setColumnWidth(1, 110)
        self.tbl.setColumnWidth(2, 520)
        tcard.add(self.tbl)
        self.tinfo = body("")
        tcard.add(self.tinfo)
        self.add(tcard)

        self.add(callout(
            "<b>Why Q and not V?</b> This is the \"VERY IMPORTANT\" box in your "
            "notes.<br><br>"
            "With V(s) alone, choosing an action means computing<br>"
            "&nbsp;&nbsp;<code>argmax_a Σ_s' P(s'|s,a)[r + γV(s')]</code><br>"
            "— and that needs <b>P</b>, the model. Without the map you know state 4 "
            "is valuable but not which button gets you there.<br><br>"
            "With Q(s,a) the choice is just <code>argmax_a Q(s,a)</code>. No "
            "transition probabilities anywhere. That one substitution is what makes "
            "Monte Carlo control, SARSA and Q-learning possible at all.", "good"))

        cc = Card("turning V into Q — the one-step lookahead")
        cc.add(math_label(
            r"Q^\pi(s,a) = \sum_{s'} P(s'\mid s,a)\left[\, r + \gamma V^\pi(s') \,\right]", 14))
        cp = CodePane(get_source(q_from_V))
        cp.sizeHintLine(15)
        cc.add(cp)
        self.add(cc)

        self.finish()
        self.recompute()

    def recompute(self):
        P = self.env.build()
        g = min(self.env.gamma_value(), 0.9999)
        pi, V, _ = value_iteration(P, gamma=g, theta=1e-12)
        self.Q = q_table_from_V(P, V, g)
        self.V = V
        self.grid.Q = self.Q
        self.grid.V = V
        self.grid.show_values = self.chk_v.isChecked()
        self.grid.update()
        self.refresh_table()

    def refresh_table(self):
        s = self.grid.selected if self.grid.selected is not None else 10
        P = self.env.build()
        g = min(self.env.gamma_value(), 0.9999)
        best = max(range(N_ACTIONS), key=lambda a: self.Q[s][a])
        for a in range(N_ACTIONS):
            it = QTableWidgetItem(f"{a} · {ACTION_NAMES[a]} {ACTION_ARROWS[a]}")
            self.tbl.setItem(a, 0, it)
            qv = QTableWidgetItem(f"{self.Q[s][a]:+.5f}")
            qv.setForeground(QColor(theme.GOOD if a == best else theme.TEXT))
            f = qv.font(); f.setBold(a == best); qv.setFont(f)
            self.tbl.setItem(a, 1, qv)
            parts = " + ".join(
                f"{t.prob:.2f}·({t.reward:+.2f}{'' if t.done else f' + {g:.2f}·{self.V[t.next_state]:+.3f}'})"
                for t in merge_duplicates(P[s][a]))
            pi = QTableWidgetItem(parts)
            pi.setToolTip(parts)
            self.tbl.setItem(a, 2, pi)
            self.tbl.setItem(a, 3, QTableWidgetItem("← greedy" if a == best else ""))
        self.tinfo.setText(
            f"state <b>{s}</b> ({cell_kind(s)}) &nbsp;·&nbsp; "
            f"V*(s) = max<sub>a</sub> Q*(s,a) = <b>{max(self.Q[s]):+.5f}</b>"
            + ("  &nbsp;·&nbsp; <span style='color:%s'>terminal — all actions "
               "self-loop with reward 0</span>" % theme.WARN if is_terminal(s) else ""))


# ==========================================================================
# PAGE 9 -- V vs Q
# ==========================================================================

class VvsQPage(Page):
    TITLE = "V vs Q — the Difference"
    SUBTITLE = ("They feel like the same thing. They are not. This difference is "
                "the base of every actor-critic method.")
    SECTION = "Value Functions"
    NOTES = "notes p.1 · p.7"

    def __init__(self, parent=None):
        super().__init__(parent)

        two = QHBoxLayout(); two.setSpacing(14)
        cv = Card("V(s) — the weather forecast")
        cv.add(math_label(r"V^\pi(s) = \mathbb{E}_\pi[G_t \mid S_t=s]", 14))
        cv.add(body(
            "\"You are in state 10. Your policy usually goes DOWN 80% of the time "
            "and RIGHT 20%. Averaging over that, expect 0.75.\"<br><br>"
            "<b>Assumes you behave normally.</b> One number per state: 16 numbers."))
        two.addWidget(cv)

        cq = Card("Q(s,a) — the what-if")
        cq.add(math_label(r"Q^\pi(s,a) = \mathbb{E}_\pi[G_t \mid S_t=s, A_t=a]", 14))
        cq.add(body(
            "\"Forget what you usually do. Move LEFT <i>right now</i>, then behave "
            "normally forever after. What then?\"<br><br>"
            "<b>Overrides the first action.</b> One number per state-action pair: "
            "16 × 4 = 64 numbers."))
        two.addWidget(cq)
        self.add_layout(two)

        # ---- the two identities --------------------------------------------
        idc = Card("the two identities that connect them")
        idc.add(body("<b>Q from V</b> — one-step lookahead. Needs the model P:", dim=True))
        idc.add(math_label(
            r"Q^\pi(s,a) = \sum_{s'} P(s'\mid s,a)\left[\, r + \gamma V^\pi(s')\,\right]", 14))
        idc.add(body("<b>V from Q</b> — average under the policy. Needs no model:", dim=True))
        idc.add(math_label(
            r"V^\pi(s) = \sum_a \pi(a\mid s)\, Q^\pi(s,a)", 14))
        idc.add(body(
            (
                "The asymmetry is the whole story. Going <b>Q → V</b> is free. Going <b>V → Q</b> costs you a "
                "model. That is why Q is useful for model-free action selection. Policy-gradient methods can "
                "instead learn a policy using sampled returns and a V baseline."
            ), dim=True))
        idc.add(callout(
            "Special case worth memorising: for a <b>deterministic</b> policy, "
            "π(a|s) is one-hot, so V<sup>π</sup>(s) = Q<sup>π</sup>(s, π(s)) exactly. "
            "And for the <b>optimal</b> policy, V*(s) = max<sub>a</sub> Q*(s,a).",
            "key"))
        self.add(idc)

        # ---- live verification ----------------------------------------------
        ver = Card("verify it numerically, right now")
        self.env = EnvControls(slip="classic", reward="shaped", gamma=0.99)
        self.env.changed.connect(self.recompute)
        self.polbox = QComboBox()
        self.polbox.addItems(["π = optimal", "π = always DOWN", "π = always RIGHT",
                              "π = uniform random (stochastic!)"])
        self.polbox.currentIndexChanged.connect(self.recompute)

        left = QVBoxLayout()
        left.addLayout(labelled("Policy π", self.polbox, 70))
        left.addWidget(self.env)
        left.addStretch(1)

        self.tbl = QTableWidget(N_STATES, 7)
        self.tbl.setHorizontalHeaderLabels(
            ["s", "V^π(s)", "Q(s,←)", "Q(s,↓)", "Q(s,→)", "Q(s,↑)",
             "Σ π(a|s)Q(s,a)"])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl.setMinimumHeight(430)
        for c in range(7):
            self.tbl.setColumnWidth(c, 95)
        self.tbl.setColumnWidth(0, 40)

        r = QHBoxLayout(); r.setSpacing(14)
        r.addLayout(left, 1)
        r.addWidget(self.tbl, 2)
        ver.add_layout(r)
        self.resid = body("")
        ver.add(self.resid)
        self.add(ver)

        # ---- side by side grids ----------------------------------------------
        sbs = Card("same policy, drawn both ways")
        row = QHBoxLayout(); row.setSpacing(18)
        c1 = QVBoxLayout()
        l1 = QLabel("V^π(s) — 16 numbers, one per square")
        l1.setStyleSheet(f"color:{theme.TEXT_DIM}; font-size:11px; background:transparent;")
        self.gv = GridView(cell=80)
        self.gv.value_fmt = "{:.3f}"
        c1.addWidget(l1); c1.addWidget(self.gv); c1.addStretch(1)
        c2 = QVBoxLayout()
        l2 = QLabel("Q^π(s,a) — 64 numbers, four per square")
        l2.setStyleSheet(f"color:{theme.TEXT_DIM}; font-size:11px; background:transparent;")
        self.gq = GridView(cell=110)
        self.gq.show_q = True
        self.gq.show_values = False
        self.gq.show_policy = False
        c2.addWidget(l2); c2.addWidget(self.gq); c2.addStretch(1)
        row.addLayout(c1); row.addLayout(c2); row.addStretch(1)
        sbs.add_layout(row)
        self.add(sbs)

        self.add(callout(
            (
                "<b>How actor-critic uses these scores.</b> A critic may estimate V(s) or Q(s,a), depending on "
                "the algorithm; it need not learn both. PPO commonly uses V to form advantage estimates for a "
                "stochastic actor. DDPG uses Q and its action derivative to train a deterministic actor. Both "
                "values predict future return, not reward already collected."
            ),
            "good"))

        self.finish()
        self.recompute()

    def recompute(self):
        P = self.env.build()
        g = min(self.env.gamma_value(), 0.9999)
        idx = self.polbox.currentIndex()

        if idx == 0:
            pi, _, _ = policy_iteration(P, gamma=g, theta=1e-12)
            probs = deterministic_to_probs(pi)
        elif idx == 1:
            pi = [1] * N_STATES; probs = deterministic_to_probs(pi)
        elif idx == 2:
            pi = [2] * N_STATES; probs = deterministic_to_probs(pi)
        else:
            pi = None
            probs = [[1.0 / N_ACTIONS] * N_ACTIONS for _ in range(N_STATES)]

        # evaluate V^pi under the (possibly stochastic) policy
        V = [0.0] * N_STATES
        for _ in range(20000):
            Vp = list(V)
            delta = 0.0
            for s in range(N_STATES):
                v = sum(probs[s][a] * q_from_V(P, Vp, s, a, g) for a in range(N_ACTIONS))
                delta = max(delta, abs(v - V[s]))
                V[s] = v
            if delta < 1e-13:
                break

        Q = q_table_from_V(P, V, g)
        V_rebuilt = V_from_Q(Q, probs)

        worst = 0.0
        for s in range(N_STATES):
            self.tbl.setItem(s, 0, QTableWidgetItem(str(s)))
            vi = QTableWidgetItem(f"{V[s]:+.5f}")
            vi.setForeground(QColor(theme.ACCENT))
            self.tbl.setItem(s, 1, vi)
            best = max(range(N_ACTIONS), key=lambda a: Q[s][a])
            for a in range(N_ACTIONS):
                qi = QTableWidgetItem(f"{Q[s][a]:+.5f}")
                if a == best:
                    qi.setForeground(QColor(theme.GOOD))
                self.tbl.setItem(s, 2 + a, qi)
            ri = QTableWidgetItem(f"{V_rebuilt[s]:+.5f}")
            ri.setForeground(QColor(theme.VIOLET))
            self.tbl.setItem(s, 6, ri)
            worst = max(worst, abs(V_rebuilt[s] - V[s]))

        self.resid.setText(
            f"Largest disagreement between column 2 (V computed directly) and "
            f"column 7 (V rebuilt from Q): <b style='color:{theme.GOOD}'>"
            f"{worst:.2e}</b> — that is floating-point dust. The identity "
            f"V<sup>π</sup>(s) = Σ<sub>a</sub> π(a|s)·Q<sup>π</sup>(s,a) holds "
            f"exactly, including for the stochastic policy.")

        self.gv.V = V
        self.gv.policy = pi
        self.gv.show_policy = pi is not None
        self.gv.update()
        self.gq.Q = Q
        self.gq.update()


# ==========================================================================
# PAGE 10 -- Bellman
# ==========================================================================

class BackupDiagram(QWidget):
    """The classic one-step backup tree: state -> actions -> successor states."""

    def __init__(self, mode="expectation", parent=None):
        super().__init__(parent)
        self.mode = mode
        self.setMinimumHeight(230)
        self.setStyleSheet("background: transparent;")

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        top = 34
        mid = h * 0.45
        bot = h - 46
        cx = w / 2

        # root state
        p.setBrush(QColor(theme.ACCENT))
        p.setPen(QPen(QColor(theme.ACCENT), 2))
        p.drawEllipse(int(cx - 9), int(top - 9), 18, 18)
        p.setPen(QColor(theme.TEXT))
        p.setFont(QFont("Consolas", 11, QFont.Bold))
        p.drawText(int(cx - 60), int(top - 30), 120, 20, Qt.AlignCenter, "s")

        n_a = 3
        axs = [cx + (i - (n_a - 1) / 2) * (w * 0.26) for i in range(n_a)]

        for i, ax in enumerate(axs):
            chosen = (i == 1)
            col = theme.GOOD if (self.mode == "optimality" and chosen) else \
                  theme.TEXT_FAINT if self.mode == "optimality" else theme.VIOLET
            p.setPen(QPen(QColor(col), 2.2 if chosen or self.mode == "expectation" else 1.2))
            p.drawLine(int(cx), int(top + 9), int(ax), int(mid - 7))
            p.setBrush(QColor(col)); p.setPen(QPen(QColor(col), 2))
            p.drawEllipse(int(ax - 6), int(mid - 6), 12, 12)

            # successors
            for j in range(2):
                sx = ax + (j - 0.5) * (w * 0.10)
                p.setPen(QPen(QColor(theme.CYAN),
                              2.0 if (self.mode == "expectation" or chosen) else 1.0))
                p.drawLine(int(ax), int(mid + 6), int(sx), int(bot - 8))
                p.setBrush(QColor(theme.CYAN)); p.setPen(QPen(QColor(theme.CYAN), 2))
                p.drawEllipse(int(sx - 7), int(bot - 7), 14, 14)

        p.setPen(QColor(theme.TEXT_DIM))
        p.setFont(QFont("Segoe UI", 9))
        if self.mode == "expectation":
            l1 = "π(a|s):  AVERAGE over all actions the policy might take"
        else:
            l1 = "max over a:  take only the BEST action, ignore the rest"
        p.drawText(0, int(mid - 34), w, 18, Qt.AlignCenter, l1)
        p.drawText(0, int(bot + 14), w, 18, Qt.AlignCenter,
                   "P(s'|s,a):  average over where the ice actually puts you "
                   "(always an average — you never control this)")
        p.end()


class BellmanPage(Page):
    TITLE = "The Bellman Equations"
    SUBTITLE = ("The recursion that makes all of this computable: value now = "
                "reward now + discounted value next.")
    SECTION = "Value Functions"
    NOTES = "notes p.1 · p.5"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "Bellman's insight in one sentence: <b>you do not need the whole "
            "future, only the next step plus the value of where you land.</b> "
            "An infinite sum collapses into a recursion over 16 numbers.", "key"))

        # ---- expectation ----------------------------------------------------
        ex = Card("Bellman EXPECTATION — evaluates a given π")
        ex.add(math_label(
            r"V^\pi(s) = \sum_a \pi(a\mid s) \sum_{s'} P(s'\mid s,a)"
            r"\left[\, r + \gamma V^\pi(s') \,\right]", 15))
        ex.add(math_label(
            r"Q^\pi(s,a) = \sum_{s'} P(s'\mid s,a)"
            r"\left[\, r + \gamma \sum_{a'} \pi(a'\mid s')\, Q^\pi(s',a') \,\right]", 14))
        ex.add(BackupDiagram("expectation"))
        ex.add(body(
            "Two averages stacked: first over what π might do, then over what the "
            "ice does. <b>No max anywhere</b> — you are scoring a fixed policy, not "
            "improving it. This equation is what policy evaluation solves.", dim=True))

        op = Card("Bellman OPTIMALITY — defines π*")
        op.add(math_label(
            r"V^*(s) = \max_a \sum_{s'} P(s'\mid s,a)"
            r"\left[\, r + \gamma V^*(s') \,\right]", 15))
        op.add(math_label(
            r"Q^*(s,a) = \sum_{s'} P(s'\mid s,a)"
            r"\left[\, r + \gamma \max_{a'} Q^*(s',a') \,\right]", 14))
        op.add(BackupDiagram("optimality"))
        op.add(body(
            "The outer average over π has become a <b>max</b>. You still cannot max "
            "over s' — the ice is not yours to choose. This equation is what value "
            "iteration solves.", dim=True))

        self.row(ex, op, stretches=[1, 1])

        self.add(callout(
            "Look at where the <b>max</b> sits in the two Q equations. In "
            "Q*(s,a) it is <i>inside</i> the sum, applied to the <b>next</b> state. "
            "That placement is exactly what lets Q-learning drop the model: replace "
            "<code>Σ_s' P(s'|s,a)</code> with one sampled transition and you have "
            "the Q-learning update, unchanged otherwise.", "good"))

        # ---- live one-state backup ------------------------------------------
        live = Card("watch one backup happen")
        live.add(body(
            "Pick a state. This shows the Bellman right-hand side computed term by "
            "term from the converged V*, and checks it equals V*(s).", dim=True))

        self.env = EnvControls(slip="classic", reward="shaped", gamma=0.99)
        self.env.changed.connect(self.recompute)

        self.grid = GridView(cell=78)
        self.grid.clickable = True
        self.grid.selected = 9
        self.grid.value_fmt = "{:.3f}"
        self.grid.cellClicked.connect(lambda s: self.refresh())

        self.detail = QLabel()
        self.detail.setWordWrap(True)
        self.detail.setTextFormat(Qt.RichText)
        self.detail.setAlignment(Qt.AlignTop)
        self.detail.setStyleSheet(
            f"background:{theme.BG_INPUT}; border:1px solid {theme.BORDER};"
            f"border-radius:8px; padding:12px; font-family:Consolas; font-size:12px;")
        self.detail.setMinimumHeight(290)

        rr = QHBoxLayout(); rr.setSpacing(14)
        c1 = QVBoxLayout(); c1.addWidget(self.grid); c1.addWidget(self.env); c1.addStretch(1)
        rr.addLayout(c1)
        rr.addWidget(self.detail, 1)
        live.add_layout(rr)
        self.add(live)

        self.add(callout(
            (
                "<b>This page is the summary. The next four are the lesson.</b><br><br>All four equations at "
                "once is the right <i>map</i> and the wrong place to learn from — the four look interchangeable "
                "here, and they are not. Pages 63–66 take one equation each and grind it down to arithmetic you "
                "can watch happen, with the numbers off this lake:<br><br>&nbsp;&nbsp;<b>63 · V<sup>π</sup></b> "
                "— two dice, both averaged. Drag π(a|s) and watch V move.<br>&nbsp;&nbsp;<b>64 · "
                "Q<sup>π</sup></b> — the first button is forced, so the π-average slides one step "
                "later.<br>&nbsp;&nbsp;<b>65 · V*</b> — the average over π becomes a choice. Swap the max for "
                "min and watch the lake turn hostile.<br>&nbsp;&nbsp;<b>66 · Q*</b> — same shove as page 64, "
                "with max instead of average. This is the one that turns into Q-learning.<br><br>The single "
                "sentence they are all built on: <b>the Q equations are the V equations with the action-choice "
                "delayed by one step</b>, because Q's first action is handed to you and the choosing cannot "
                "happen until the next square."
            ), "key", "GO DEEPER — ONE PAGE PER EQUATION"))

        self.add(callout(
            (
                "The Bellman operator is a <b>γ-contraction</b>. Applying it repeatedly from <i>any</i> starting"
                " V bounds the worst-case error contraction by a factor γ per synchronous sweep when γ < 1, so "
                "it converges to a unique fixed point. That is the theorem underneath both algorithms on the "
                "next pages — and the reason the initial V = 0 does not matter."
            ), "key"))

        self.finish()
        self.recompute()

    def recompute(self):
        P = self.env.build()
        g = min(self.env.gamma_value(), 0.9999)
        pi, V, sweeps = value_iteration(P, gamma=g, theta=1e-14)
        self.P, self.g, self.V, self.pi = P, g, V, pi
        self.grid.V = V
        self.grid.policy = pi
        self.grid.update()
        self.refresh()

    def refresh(self):
        s = self.grid.selected if self.grid.selected is not None else 9
        P, g, V = self.P, self.g, self.V

        if is_terminal(s):
            self.detail.setText(
                f"<b>State {s}</b> is <b>terminal</b> ({cell_kind(s)}).<br><br>"
                f"Terminal states are absorbing: every action self-loops with "
                f"reward 0. The Bellman equation degenerates to<br>"
                f"&nbsp;&nbsp;V({s}) = 0 + γ·V({s})<br>"
                f"whose only solution for γ &lt; 1 is <b>V({s}) = 0</b>.<br><br>"
                f"This is why <code>q_from_V</code> writes "
                f"<code>0.0 if t.done else V[t.next_state]</code> — a terminal "
                f"successor contributes its immediate reward and nothing more.")
            return

        lines = [f"<b style='color:{theme.ACCENT}'>State {s}</b> "
                 f"&nbsp;γ = {g:.3f}<br>",
                 f"<span style='color:{theme.TEXT_DIM}'>"
                 f"Q(s,a) = Σ<sub>s'</sub> P(s'|s,a)·[ r + γ·V(s') ]</span><br>"]

        qs = []
        for a in range(N_ACTIONS):
            terms = []
            total = 0.0
            for t in merge_duplicates(P[s][a]):
                boot = 0.0 if t.done else V[t.next_state]
                contrib = t.prob * (t.reward + g * boot)
                total += contrib
                terms.append(
                    f"&nbsp;&nbsp;{t.prob:.4f} × ({t.reward:+.2f} + {g:.2f}×"
                    f"{boot:+.4f}) = {contrib:+.5f}"
                    f"<span style='color:{theme.TEXT_FAINT}'>"
                    f"&nbsp;&nbsp;→ s'={t.next_state}"
                    f"{' (terminal)' if t.done else ''}</span>")
            qs.append(total)
            lines.append(
                f"<br><b>a = {a} · {ACTION_NAMES[a]} {ACTION_ARROWS[a]}</b><br>"
                + "<br>".join(terms)
                + f"<br>&nbsp;&nbsp;<b>Q(s,{a}) = {total:+.6f}</b>")

        best = max(range(N_ACTIONS), key=lambda a: qs[a])
        lines.append(
            f"<br><br><span style='color:{theme.GOOD}'>"
            f"max<sub>a</sub> Q(s,a) = Q(s,{best}) = <b>{qs[best]:+.6f}</b></span>"
            f"<br>stored V*({s}) = <b>{V[s]:+.6f}</b>"
            f"<br>residual = <b style='color:{theme.GOOD}'>"
            f"{abs(qs[best] - V[s]):.2e}</b> &nbsp;→ the Bellman optimality "
            f"equation holds at this state.")
        self.detail.setText("".join(lines))
