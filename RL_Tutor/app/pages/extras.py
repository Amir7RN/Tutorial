"""
Pages 20-23.

  19  Exploration vs Exploitation -- multi-armed bandits, eps-greedy vs UCB
  20  Model-Based vs Model-Free   -- the central divide, side by side
  21  Hyperparameters             -- gamma, alpha, epsilon, theta
  22  Convergence                 -- what it does and does not mean
  23  Code Lab                    -- browse rlcore, and notes on your C++ files
  24  Adam & Backprop             -- the optimiser page from notes p.8
"""

from __future__ import annotations

from ..widgets.cpp_source import get_example

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from rlcore.bandit import Bandit, compare, epsilon_greedy_run, ucb_run
from rlcore.dp import (
    evaluate_policy_empirically,
    policy_evaluation,
    policy_iteration,
    q_value_iteration,
    value_iteration,
)
from rlcore.frozen_lake import (
    N_ACTIONS,
    N_STATES,
    FrozenLake,
    build_model,
    is_terminal,
)
from rlcore.mc import mc_control
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
# PAGE 19 -- Bandits
# ==========================================================================

class BanditPage(Page):
    TITLE = "Exploration vs Exploitation"
    SUBTITLE = ("The multi-armed bandit: an MDP with one state, so nothing is left "
                "but the exploration dilemma. ε-greedy vs UCB.")
    SECTION = "Beyond"
    NOTES = "notes p.1 §2.5"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "A bandit is an MDP with <b>exactly one state</b>. That kills "
            "transitions, discounting and credit assignment, and leaves only the "
            "hard part: every pull spent learning about a bad arm is a pull not "
            "spent earning on the good one.<br><br>"
            "Your notes' restaurant framing is exact: order your favourite dish "
            "again (exploit), or try the new one (explore)?", "key"))

        two = QHBoxLayout(); two.setSpacing(14)
        c1 = Card("ε-greedy")
        c1.add(math_label(
            r"A_t = \begin{cases} \text{random} \\ \arg\max_a Q_t(a) \end{cases}", 13))
        c1.add(body(
            "With probability ε, pull a uniformly random arm. Otherwise pull the "
            "current best.<br><br>"
            "<b>The flaw:</b> exploration is <b>undirected</b>. When ε-greedy "
            "decides to explore it is just as happy to re-test an arm it already "
            "knows is terrible as one it is genuinely uncertain about. It never "
            "stops wasting ε of its pulls, forever."))
        two.addWidget(c1)

        c2 = Card("UCB — optimism under uncertainty")
        c2.add(math_label(
            r"A_t = \arg\max_a \left[\, Q_t(a) + c\sqrt{\frac{\ln t}{N_t(a)}} \,\right]", 14))
        c2.add(body(
            "Exactly the formula in your handwritten note. Read the two terms:<br>"
            "&nbsp;&nbsp;<b>Q<sub>t</sub>(a)</b> — what I believe.<br>"
            "&nbsp;&nbsp;<b>c·√(ln t / N<sub>t</sub>(a))</b> — how <i>unsure</i> I am.<br><br>"
            "Few pulls → big bonus → \"go look at this one\". Many pulls → tiny "
            "bonus. The ln t on top means every neglected arm slowly becomes "
            "interesting again.<br><br>"
            "<b>UCB is deterministic</b> — it never rolls a die. It explores the arm "
            "with the highest <i>plausible</i> value, which is a targeted question "
            "rather than a random one."))
        two.addWidget(c2)
        self.add_layout(two)

        # ---- single run ------------------------------------------------------
        run = Card("one bandit, watched closely")
        hb = QHBoxLayout(); hb.setSpacing(8)
        self.k = QSpinBox(); self.k.setRange(2, 20); self.k.setValue(10)
        self.steps = QSpinBox(); self.steps.setRange(100, 20000); self.steps.setValue(1500)
        self.steps.setSingleStep(500)
        self.eps = QDoubleSpinBox(); self.eps.setRange(0.0, 1.0); self.eps.setValue(0.1)
        self.eps.setSingleStep(0.02); self.eps.setDecimals(3)
        self.c = QDoubleSpinBox(); self.c.setRange(0.0, 6.0); self.c.setValue(2.0)
        self.c.setSingleStep(0.25)
        self.btn = QPushButton("Run"); self.btn.setObjectName("Primary")
        for w, t in ((self.k, "arms"), (self.steps, "steps"),
                     (self.eps, "ε"), (self.c, "UCB c")):
            hb.addWidget(QLabel(t)); hb.addWidget(w)
        hb.addWidget(self.btn); hb.addStretch(1)
        run.add_layout(hb)
        self.canvas = MplCanvas(width=10.6, height=3.4, ncols=2)
        run.add(self.canvas)
        self.st_eg = Stat("ε-greedy regret", "-", theme.WARN)
        self.st_ucb = Stat("UCB regret", "-", theme.GOOD)
        self.st_gr = Stat("pure greedy regret", "-", theme.BAD)
        run.add_layout(stat_row(self.st_gr, self.st_eg, self.st_ucb))
        self.btn.clicked.connect(self.run_once)
        self.add(run)

        # ---- averaged --------------------------------------------------------
        avg = Card("averaged over many bandits — the textbook curves")
        avg.add(body(
            "A <b>single</b> run proves nothing: pure greedy sometimes locks onto "
            "the best arm immediately and looks unbeatable. Only after averaging "
            "over many independent bandits does the real ordering appear. This is "
            "why Sutton & Barto always plot 2000-run averages.", dim=True))
        hb2 = QHBoxLayout(); hb2.setSpacing(8)
        self.runs = QSpinBox(); self.runs.setRange(10, 500); self.runs.setValue(120)
        self.btn2 = QPushButton("Run averaged comparison")
        self.btn2.setObjectName("Primary")
        hb2.addWidget(QLabel("independent runs")); hb2.addWidget(self.runs)
        hb2.addWidget(self.btn2); hb2.addStretch(1)
        avg.add_layout(hb2)
        self.canvas2 = MplCanvas(width=10.6, height=3.4, ncols=2)
        avg.add(self.canvas2)
        self.btn2.clicked.connect(self.run_avg)
        self.add(avg)

        self.add(callout(
            "Back on Frozen Lake, this is the ε in ε-greedy MC control. The bandit "
            "strips away everything else so you can see that ε does one job: it "
            "buys information at the cost of reward. Decay it and you stop paying "
            "once you have bought enough.", "good"))

        cc = Card("the code")
        tabs = QTabWidget()
        t1 = CodePane(get_source(epsilon_greedy_run)); t1.sizeHintLine(30)
        t2 = CodePane(get_source(ucb_run)); t2.sizeHintLine(38)
        tabs.addTab(t1, "ε-greedy")
        tabs.addTab(t2, "UCB")
        tabs.setMinimumHeight(430)
        cc.add(tabs)
        self.add(cc)

        self.finish()
        self.run_once()

    def run_once(self):
        import random
        seed = random.randrange(10**6)
        k, n = self.k.value(), self.steps.value()
        b1 = Bandit(k=k, seed=seed)
        b2 = Bandit(k=k, seed=seed)
        b3 = Bandit(k=k, seed=seed)
        rg = epsilon_greedy_run(b1, steps=n, eps=0.0, seed=seed + 1)
        re = epsilon_greedy_run(b2, steps=n, eps=self.eps.value(), seed=seed + 1)
        ru = ucb_run(b3, steps=n, c=self.c.value(), seed=seed + 1)

        self.canvas.clear()
        a0, a1 = self.canvas.axes
        a0.plot(rg["regret"], color=theme.BAD, lw=1.6, label="greedy (ε=0)")
        a0.plot(re["regret"], color=theme.WARN, lw=1.6,
                label=f"ε-greedy ({self.eps.value():.2f})")
        a0.plot(ru["regret"], color=theme.GOOD, lw=1.6, label=f"UCB (c={self.c.value():.2f})")
        a0.set_xlabel("pull"); a0.set_ylabel("cumulative regret")
        a0.set_title("regret — lower is better\n(reward you gave up vs always picking the best arm)")
        self.canvas.legend(a0, loc="upper left")

        x = range(k)
        w = 0.27
        a1.bar([i - w for i in x], b1.q_true, w, color=theme.TEXT_DIM, label="true q*(a)")
        a1.bar([i for i in x], ru["Q"], w, color=theme.GOOD, label="UCB's estimate")
        a1.bar([i + w for i in x], re["Q"], w, color=theme.WARN, label="ε-greedy's estimate")
        a1.set_xticks(list(x)); a1.set_xlabel("arm")
        a1.set_title(f"value estimates   (best arm = {b1.best_arm})")
        self.canvas.legend(a1, loc="best")
        self.canvas.refresh()

        self.st_gr.set(f"{rg['regret'][-1]:.1f}")
        self.st_eg.set(f"{re['regret'][-1]:.1f}")
        self.st_ucb.set(f"{ru['regret'][-1]:.1f}")

    def run_avg(self):
        self.btn2.setEnabled(False)
        self.btn2.setText("running…")
        try:
            res = compare(steps=800, runs=self.runs.value(),
                          eps_list=(0.0, 0.01, 0.1), ucb_c=self.c.value(),
                          k=self.k.value())
            self.canvas2.clear()
            a0, a1 = self.canvas2.axes
            cols = {"greedy (eps=0)": theme.BAD, "eps-greedy (0.01)": theme.CYAN,
                    "eps-greedy (0.1)": theme.WARN}
            for label, d in res.items():
                col = cols.get(label, theme.GOOD)
                a0.plot(d["reward"], color=col, lw=1.4, label=label)
                a1.plot(d["optimal_pct"], color=col, lw=1.4, label=label)
            a0.set_xlabel("pull"); a0.set_ylabel("average reward")
            a0.set_title(f"average reward over {self.runs.value()} bandits")
            a1.set_xlabel("pull"); a1.set_ylabel("% optimal action")
            a1.set_title("how often the best arm is chosen")
            a1.set_ylim(0, 100)
            self.canvas2.legend(a0, loc="lower right")
            self.canvas2.refresh()
        finally:
            self.btn2.setEnabled(True)
            self.btn2.setText("Run averaged comparison")


# ==========================================================================
# PAGE 20 -- Model-based vs model-free
# ==========================================================================

class ModelPage(Page):
    TITLE = "Model-Based vs Model-Free"
    SUBTITLE = ("The central divide of this whole subject, shown as a single "
                "difference in function signatures.")
    SECTION = "Beyond"
    NOTES = "notes p.4 · p.5"

    def __init__(self, parent=None):
        super().__init__(parent)

        sig = Card("the difference, in two lines")
        row = QHBoxLayout(); row.setSpacing(16)
        c1 = QVBoxLayout()
        l1 = QLabel("MODEL-BASED  (planning)")
        l1.setStyleSheet(f"color:{theme.GOOD}; font-weight:700; font-size:11px;"
                         f"background:transparent;")
        p1 = CodePane(get_example("model_based_interface"))
        p1.sizeHintLine(6); p1.mark(1, "#1f7a4d")
        c1.addWidget(l1); c1.addWidget(p1)
        c2 = QVBoxLayout()
        l2 = QLabel("MODEL-FREE  (learning)")
        l2.setStyleSheet(f"color:{theme.WARN}; font-weight:700; font-size:11px;"
                         f"background:transparent;")
        p2 = CodePane(get_example("model_free_interface"))
        p2.sizeHintLine(6); p2.mark(1, "#6b4e13")
        c2.addWidget(l2); c2.addWidget(p2)
        row.addLayout(c1); row.addLayout(c2)
        sig.add_layout(row)
        self.add(sig)

        self.add(callout(
            "<b>The missing-map problem</b> from your notes. In DP we knew exactly "
            "how the wind blows, so we could pick an action by looking at V(s') of "
            "all neighbours and weighting by P.<br><br>"
            "In model-free RL we are blind. We know state 4 is valuable, but "
            "<b>we do not know which button takes us there</b>. Hence Q(s,a): "
            "learn the value of the <i>button</i>, not the destination.", "key"))

        # ---- table -----------------------------------------------------------
        t = Card("side by side")
        tbl = QTableWidget(11, 3)
        tbl.setHorizontalHeaderLabels(["", "Model-based (DP)", "Model-free (MC / TD)"])
        tbl.verticalHeader().setVisible(False)
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        tbl.setColumnWidth(0, 175); tbl.setColumnWidth(1, 330)
        rows = [
            ("Needs", "P(s'|s,a) and r for every pair", "a simulator, or the real robot"),
            ("Interacts?", "never — pure computation", "constantly — that is the only data source"),
            ("Learns V or Q?", "V is enough (P supplies the action)", "must be Q (no P to pick actions with)"),
            ("Exploration", "not a concept — sweeps all states", "essential; ε-greedy or similar"),
            ("Cost on this grid", "~30 sweeps, milliseconds", "tens of thousands of episodes"),
            ("Accuracy", "exact to machine precision", "sampling noise, O(1/√N)"),
            ("Scales to", "small discrete state spaces", "anything you can simulate"),
            ("Real robot?", "no — you never have P", "yes — this is what actually ships"),
            ("Bootstraps?", "yes — uses V(s') estimates", "MC: no.  TD/Q-learning: yes"),
            ("Update timing", "per sweep over all states", "MC: end of episode.  TD: every step"),
            ("Examples", "policy iteration, value iteration",
             "MC control, SARSA, Q-learning, DQN, DDPG"),
        ]
        for i, (a, b, c) in enumerate(rows):
            it = QTableWidgetItem(a)
            it.setForeground(QColor(theme.TEXT_DIM))
            f = it.font(); f.setBold(True); it.setFont(f)
            tbl.setItem(i, 0, it)
            ib = QTableWidgetItem(b); ib.setForeground(QColor(theme.GOOD))
            tbl.setItem(i, 1, ib)
            ic = QTableWidgetItem(c); ic.setForeground(QColor(theme.WARN))
            tbl.setItem(i, 2, ic)
        tbl.resizeRowsToContents()
        tbl.setMinimumHeight(400)
        t.add(tbl)
        self.add(t)

        # ---- head to head ------------------------------------------------------
        h2h = Card("head to head on the same lake")
        self.env = EnvControls(slip="classic", reward="shaped", gamma=0.99)
        h2h.add(self.env)
        hb = QHBoxLayout(); hb.setSpacing(8)
        self.mc_eps = QSpinBox(); self.mc_eps.setRange(1000, 300000); self.mc_eps.setValue(40000)
        self.mc_eps.setSingleStep(10000)
        self.btn = QPushButton("Run both"); self.btn.setObjectName("Primary")
        hb.addWidget(QLabel("MC episodes:")); hb.addWidget(self.mc_eps)
        hb.addWidget(self.btn); hb.addStretch(1)
        h2h.add_layout(hb)

        row = QHBoxLayout(); row.setSpacing(16)
        cA = QVBoxLayout()
        la = QLabel("Value Iteration (saw P)")
        la.setStyleSheet(f"color:{theme.GOOD}; font-size:11px; font-weight:700;"
                         f"background:transparent;")
        self.gA = GridView(cell=80); self.gA.value_fmt = "{:.3f}"
        self.sA1 = Stat("wall time", "-", theme.GOOD)
        self.sA2 = Stat("success rate", "-", theme.GOOD)
        cA.addWidget(la); cA.addWidget(self.gA)
        cA.addLayout(stat_row(self.sA1, self.sA2)); cA.addStretch(1)
        cB = QVBoxLayout()
        lb = QLabel("MC Control (never saw P)")
        lb.setStyleSheet(f"color:{theme.WARN}; font-size:11px; font-weight:700;"
                         f"background:transparent;")
        self.gB = GridView(cell=80); self.gB.value_fmt = "{:.3f}"
        self.sB1 = Stat("wall time", "-", theme.WARN)
        self.sB2 = Stat("success rate", "-", theme.WARN)
        cB.addWidget(lb); cB.addWidget(self.gB)
        cB.addLayout(stat_row(self.sB1, self.sB2)); cB.addStretch(1)
        row.addLayout(cA); row.addLayout(cB); row.addStretch(1)
        h2h.add_layout(row)
        self.verdict = body("Press <b>Run both</b>.")
        h2h.add(self.verdict)
        self.btn.clicked.connect(self.run_both)
        self.add(h2h)

        self.add(callout(
            (
                "Value iteration wins on speed and accuracy by a mile — because this lake supplies an exact "
                "small model. A robot may instead use approximate dynamics, a learned model or direct "
                "experience. Model-based and model-free methods both transfer; their tradeoffs include model "
                "error, computation and sample cost."
            ), "good"))

        self.finish()

    def run_both(self):
        import time
        self.btn.setEnabled(False); self.btn.setText("running…")
        try:
            P = self.env.build()
            g = min(self.env.gamma_value(), 0.9999)

            t0 = time.perf_counter()
            pi_vi, V_vi, sweeps = value_iteration(P, gamma=g, theta=1e-12)
            tA = time.perf_counter() - t0

            env = FrozenLake(slip=self.env.slip_key(), reward=self.env.reward_key(),
                             seed=1)
            t0 = time.perf_counter()
            Q, pi_mc, stats = mc_control(env, gamma=g, episodes=self.mc_eps.value(),
                                         eps_start=1.0, eps_min=0.05,
                                         eps_decay=0.9997, alpha_start=0.3,
                                         alpha_min=0.3, alpha_decay=1.0, seed=1)
            tB = time.perf_counter() - t0

            V_mc = policy_evaluation(P, pi_mc, g, 1e-12)
            self.gA.V, self.gA.policy = V_vi, pi_vi; self.gA.update()
            self.gB.V, self.gB.policy = V_mc, pi_mc
            self.gB.highlight = {s for s in range(N_STATES)
                                 if not is_terminal(s) and pi_mc[s] != pi_vi[s]}
            self.gB.update()

            e1 = FrozenLake(slip=self.env.slip_key(), reward=self.env.reward_key(), seed=7)
            srA, _, _ = evaluate_policy_empirically(e1, pi_vi, episodes=5000)
            e2 = FrozenLake(slip=self.env.slip_key(), reward=self.env.reward_key(), seed=7)
            srB, _, _ = evaluate_policy_empirically(e2, pi_mc, episodes=5000)

            self.sA1.set(f"{tA*1000:.0f} ms"); self.sA2.set(f"{srA:.1%}")
            self.sB1.set(f"{tB:.2f} s"); self.sB2.set(f"{srB:.1%}")

            self.verdict.setText(
                f"VI converged in <b>{sweeps}</b> sweeps ({tA*1000:.0f} ms) and is "
                f"exact. MC used <b>{self.mc_eps.value():,}</b> episodes "
                f"({tB:.1f} s) and disagrees with π* at "
                f"<b>{len(self.gB.highlight)}</b> state(s) — "
                f"V(start): {V_vi[0]:+.4f} vs {V_mc[0]:+.4f}. "
                f"MC is roughly <b>{tB/max(tA,1e-9):.0f}×</b> slower here, and it "
                f"still does not have the model.")
        finally:
            self.btn.setEnabled(True); self.btn.setText("Run both")


# ==========================================================================
# PAGE 21 -- Hyperparameters
# ==========================================================================

class HyperPage(Page):
    TITLE = "Hyperparameters"
    SUBTITLE = "γ, α, ε, θ — what each one actually does, and how each fails."
    SECTION = "Beyond"
    NOTES = "notes p.6 §2.6"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(body(
            "Hyperparameters are set <b>before</b> training and are not learned. "
            "Q-values are learned; these four are your job."))

        t = Card("the four that matter here")
        tbl = QTableWidget(4, 4)
        tbl.setHorizontalHeaderLabels(["", "does", "too low", "too high"])
        tbl.verticalHeader().setVisible(False)
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        tbl.setColumnWidth(0, 155); tbl.setColumnWidth(1, 300); tbl.setColumnWidth(2, 270)
        rows = [
            ("γ  discount",
             "How much the future counts. Sets the effective horizon 1/(1−γ).",
             "Myopic. On a sparse-reward lake V(start) underflows to ~0 and the "
             "policy becomes arbitrary.",
             "Far-sighted but slow to converge; VI needs many more sweeps and the "
             "numbers get delicate."),
            ("α  step size",
             "How far each update moves Q toward the observed return.",
             "Learning crawls; needs far more episodes.",
             "Q oscillates and can diverge — each new return overwrites everything "
             "learned before."),
            ("ε  exploration",
             "Probability of taking a random action instead of the greedy one.",
             "Locks onto the first mediocre policy it finds and never discovers "
             "better ones.",
             "Keeps throwing itself into holes; the learned policy is never "
             "actually executed."),
            ("θ  DP threshold",
             "Stop sweeping when max|ΔV| < θ. Purely a stopping rule.",
             "Wastes sweeps chasing floating-point dust.",
             "Stops early; the value 'ripple' has not reached the far states yet, "
             "so the extracted policy is wrong there."),
        ]
        for i, (a, b, c, d) in enumerate(rows):
            it = QTableWidgetItem(a)
            it.setForeground(QColor(theme.ACCENT))
            f = it.font(); f.setBold(True); it.setFont(f)
            tbl.setItem(i, 0, it)
            tbl.setItem(i, 1, QTableWidgetItem(b))
            ic = QTableWidgetItem(c); ic.setForeground(QColor(theme.CYAN))
            tbl.setItem(i, 2, ic)
            idd = QTableWidgetItem(d); idd.setForeground(QColor(theme.BAD))
            tbl.setItem(i, 3, idd)
        tbl.resizeRowsToContents()
        tbl.setMinimumHeight(310)
        t.add(tbl)
        self.add(t)

        # ---- theta sweep -------------------------------------------------------
        th = Card("θ, demonstrated — stop too early and the policy is wrong")
        th.add(body(
            "Value iteration run to a range of θ. The bar shows how many states end "
            "up with a different action than the fully-converged π*. This is the "
            "value ripple caught mid-flight.", dim=True))
        self.env = EnvControls(slip="classic", reward="shaped", gamma=0.99)
        self.env.changed.connect(self.sweep_theta)
        th.add(self.env)
        self.canvas = MplCanvas(width=10.6, height=3.2, ncols=2)
        th.add(self.canvas)
        self.add(th)

        # ---- gamma sweep --------------------------------------------------------
        gs = Card("γ, demonstrated — the real cost of far-sightedness")
        gs.add(body(
            "Same lake, γ swept. Left: how many sweeps VI needs. Right: the "
            "empirical success rate of the resulting policy over 3000 episodes.",
            dim=True))
        self.canvas2 = MplCanvas(width=10.6, height=3.2, ncols=2)
        gs.add(self.canvas2)
        self.btn_g = QPushButton("Run γ sweep (takes a few seconds)")
        self.btn_g.setObjectName("Primary")
        self.btn_g.clicked.connect(self.sweep_gamma)
        gs.add(self.btn_g)
        self.add(gs)

        self.add(callout(
            "Notice on the right-hand plot that success rate is <b>flat</b> over a "
            "wide band of γ. The optimal policy on this grid is fairly robust — γ "
            "mostly changes the <i>numbers</i>, not the <i>arrows</i>, until it gets "
            "small enough that the goal's influence cannot reach the start at all. "
            "Then it collapses.", "key"))

        self.finish()
        self.sweep_theta()

    def sweep_theta(self):
        P = self.env.build()
        g = min(self.env.gamma_value(), 0.9999)
        pi_star, V_star, sweeps_star = value_iteration(P, gamma=g, theta=1e-14)

        thetas = [1e-1, 1e-2, 1e-3, 1e-4, 1e-6, 1e-8, 1e-10, 1e-12]
        wrong, sweeps = [], []
        for th in thetas:
            pi, V, sw = value_iteration(P, gamma=g, theta=th)
            wrong.append(sum(1 for s in range(N_STATES)
                             if not is_terminal(s) and pi[s] != pi_star[s]))
            sweeps.append(sw)

        self.canvas.clear()
        a0, a1 = self.canvas.axes
        xs = list(range(len(thetas)))
        labels = [f"1e{int(round(__import__('math').log10(t)))}" for t in thetas]
        a0.bar(xs, wrong, color=[theme.BAD if w else theme.GOOD for w in wrong])
        a0.set_xticks(xs); a0.set_xticklabels(labels)
        a0.set_xlabel("θ"); a0.set_ylabel("states with the wrong action")
        a0.set_title("stop too early → wrong policy")
        a1.plot(xs, sweeps, color=theme.ACCENT, lw=2, marker="o")
        a1.set_xticks(xs); a1.set_xticklabels(labels)
        a1.set_xlabel("θ"); a1.set_ylabel("sweeps to stop")
        a1.set_title(f"cost of a tighter θ   (θ=1e-14 needs {sweeps_star})")
        self.canvas.refresh()

    def sweep_gamma(self):
        self.btn_g.setEnabled(False); self.btn_g.setText("running…")
        try:
            gammas = [0.30, 0.50, 0.70, 0.80, 0.90, 0.95, 0.98, 0.99, 0.995, 0.999]
            sweeps, srs, v0s = [], [], []
            for gg in gammas:
                P = self.env.build()
                pi, V, sw = value_iteration(P, gamma=gg, theta=1e-12)
                sweeps.append(sw); v0s.append(V[0])
                e = FrozenLake(slip=self.env.slip_key(),
                               reward=self.env.reward_key(), seed=5)
                sr, _, _ = evaluate_policy_empirically(e, pi, episodes=3000)
                srs.append(sr * 100)

            self.canvas2.clear()
            a0, a1 = self.canvas2.axes
            a0.plot(gammas, sweeps, color=theme.ACCENT, lw=2, marker="o")
            a0.set_xlabel("γ"); a0.set_ylabel("VI sweeps to converge")
            a0.set_title("higher γ costs more sweeps (roughly 1/(1−γ))")
            a1.plot(gammas, srs, color=theme.GOOD, lw=2, marker="o",
                    label="success rate %")
            a1.set_xlabel("γ"); a1.set_ylabel("success rate %")
            a1.set_title("quality of the resulting policy")
            a1.set_ylim(0, 100)
            self.canvas2.refresh()
        finally:
            self.btn_g.setEnabled(True)
            self.btn_g.setText("Run γ sweep (takes a few seconds)")


# ==========================================================================
# PAGE 22 -- Convergence
# ==========================================================================

class ConvergencePage(Page):
    TITLE = "What \"Convergence\" Means"
    SUBTITLE = ("Tabular convergence is a theorem. Deep-RL convergence is a "
                "judgement call. Do not confuse them.")
    SECTION = "Beyond"
    NOTES = "notes p.11"

    def __init__(self, parent=None):
        super().__init__(parent)

        two = QHBoxLayout(); two.setSpacing(14)
        c1 = Card("tabular DP — convergence is provable")
        c1.add(body(
            "The Bellman operator is a <b>γ-contraction</b> in the max norm:"))
        c1.add(math_label(
            r"\|T V_1 - T V_2\|_\infty \;\le\; \gamma\, \|V_1 - V_2\|_\infty", 14))
        c1.add(body(
            (
                "By Banach's fixed-point theorem this guarantees:<br>&nbsp;&nbsp;• a <b>unique</b> fixed point "
                "V*,<br>&nbsp;&nbsp;• convergence to it from <b>any</b> starting V,<br>&nbsp;&nbsp;• worst-case "
                "error contracting by at most a factor γ per synchronous sweep (γ < 1).<br><br>So <code>Δ &lt; "
                "θ</code> is not a heuristic — it bounds the true error by θγ/(1−γ). Policy iteration is even "
                "stronger: it terminates in a <b>finite</b> number of rounds."
            )))
        two.addWidget(c1)

        c2 = Card("deep / continuous RL — practical convergence only")
        c2.add(body(
            "Your notes state it flatly: <i>in continuous control RL, strict "
            "mathematical convergence almost never happens.</i> Function "
            "approximation breaks the contraction, and the data distribution shifts "
            "as the policy changes.<br><br>"
            "<b>Critic \"converged\"</b> means: TD error stops decreasing on average, "
            "Bellman residual stabilises, Q-values do not drift or explode, loss "
            "plateaus — <i>not necessarily near zero</i>.<br><br>"
            "<b>Actor \"converged\"</b> means: policy output stops changing "
            "meaningfully, gradient norms hover near zero. You never observe ∇J = 0 "
            "directly; you infer it from behaviour."))
        two.addWidget(c2)
        self.add_layout(two)

        self.add(callout(
            (
                "<b>Actor converged + critic converged ≠ system converged.</b><br>&nbsp;&nbsp;1. Actor stable, "
                "critic poor → policy stuck somewhere suboptimal.<br>&nbsp;&nbsp;2. Critic stable, actor "
                "oscillating → learning-rate or exploration problem.<br>&nbsp;&nbsp;3. Both change little, task "
                "performance bad → inspect reward design, coverage, model capacity and optimisation; any of them"
                " may be responsible.<br><br><b>Practical acceptance</b> requires a policy that changes little "
                "and satisfactory task performance. That is not a proof of mathematical convergence or "
                "closed-loop stability."
            ), "key"))

        self.add(callout(
            "For control work, convergence is <b>task-defined</b>, not "
            "algorithm-defined. Declare it when:<br>"
            "&nbsp;&nbsp;• tracking error (e.g. knee-angle RMSE) is below threshold "
            "for K consecutive episodes, with low variance;<br>"
            "&nbsp;&nbsp;• torques and impedances stay inside safe bounds;<br>"
            "&nbsp;&nbsp;• performance holds across different speeds and "
            "perturbations.<br><br>"
            "<b>NOT</b> when critic loss is zero, actor gradient is exactly zero, or "
            "the Bellman equation is perfectly satisfied. Those are theoretical "
            "ideals, not control-relevant goals.", "good"))

        self.add(callout(
            "Language check from your notes: in RL you <b>maximise return</b> — you "
            "do not \"minimise reward\". If your reward is defined as a negative "
            "cost then minimising cost is equivalent, but stay consistent in how "
            "you say it.", "warn"))

        # ---- live contraction demo -----------------------------------------------
        d = Card("watch the contraction, from three different starting points")
        d.add(body(
            "Value iteration started from V=0, from V=+5 everywhere, and from random "
            "values. All three land on the identical V*, and the error decays as a "
            "straight line on a log axis — that slope <i>is</i> γ.", dim=True))
        self.env = EnvControls(slip="classic", reward="shaped", gamma=0.99)
        self.env.changed.connect(self.demo)
        d.add(self.env)
        self.canvas = MplCanvas(width=10.6, height=3.3, ncols=2)
        d.add(self.canvas)
        self.verdict = body("")
        d.add(self.verdict)
        self.add(d)

        self.finish()
        self.demo()

    def demo(self):
        import math
        import random
        from rlcore.frozen_lake import q_from_V

        P = self.env.build()
        g = min(self.env.gamma_value(), 0.9999)
        _, V_star, _ = value_iteration(P, gamma=g, theta=1e-15)

        rng = random.Random(0)
        starts = {
            "V₀ = 0": [0.0] * N_STATES,
            "V₀ = +5": [5.0] * N_STATES,
            "V₀ random": [rng.uniform(-3, 3) for _ in range(N_STATES)],
        }
        cols = {"V₀ = 0": theme.ACCENT, "V₀ = +5": theme.WARN,
                "V₀ random": theme.VIOLET}

        self.canvas.clear()
        a0, a1 = self.canvas.axes
        finals = {}
        for name, V0 in starts.items():
            V = list(V0)
            errs = [max(abs(v - vs) for v, vs in zip(V, V_star))]
            for _ in range(90):
                Vp = list(V)
                for s in range(N_STATES):
                    V[s] = max(q_from_V(P, Vp, s, a, g) for a in range(N_ACTIONS))
                errs.append(max(abs(v - vs) for v, vs in zip(V, V_star)))
            finals[name] = V
            a0.semilogy(range(len(errs)), [max(e, 1e-17) for e in errs],
                        color=cols[name], lw=1.8, label=name)

        ref = [max(errs[0] * (g ** k), 1e-17) for k in range(len(errs))]
        a0.semilogy(range(len(ref)), ref, color=theme.TEXT_FAINT, lw=1.2, ls="--",
                    label=f"γ^k reference (γ={g:.2f})")
        a0.set_xlabel("sweep"); a0.set_ylabel("‖V − V*‖∞  (log)")
        a0.set_title("γ-contraction: any start, same destination")
        self.canvas.legend(a0)

        w = 0.27
        idx = list(range(N_STATES))
        a1.bar([i - w for i in idx], V_star, w, color=theme.GOOD, label="V* (exact)")
        for j, (name, V) in enumerate(finals.items()):
            if j == 0:
                a1.bar([i + w * j for i in idx], V, w, color=cols[name], label=name)
        a1.set_xticks(idx); a1.set_xlabel("state"); a1.set_ylabel("V")
        a1.set_title("all starts land on the same V*")
        self.canvas.legend(a1)
        self.canvas.refresh()

        worst = max(max(abs(v - vs) for v, vs in zip(V, V_star))
                    for V in finals.values())
        self.verdict.setText(
            f"After 90 sweeps, the worst disagreement between any starting point "
            f"and V* is <b style='color:{theme.GOOD}'>{worst:.2e}</b>. The initial "
            f"guess is genuinely irrelevant — that is what \"unique fixed point\" "
            f"buys you.")
