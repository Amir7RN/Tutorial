"""
Pages 12-16: Dynamic Programming / path planning on a known model.

  12  Policy Evaluation   -- solve V^pi for a fixed pi
  13  Policy Improvement  -- go greedy w.r.t. V
  14  Policy Iteration    -- alternate the two
  15  Value Iteration     -- fuse them into one line, watch the ripple
  16  PI vs VI            -- the code diff, side by side
"""

from __future__ import annotations

from ..widgets.cpp_source import get_example

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from rlcore.dp import (
    policy_evaluation,
    policy_evaluation_steps,
    policy_improvement,
    policy_iteration,
    policy_iteration_steps,
    value_iteration,
    value_iteration_steps,
)
from rlcore.frozen_lake import (
    ACTION_ARROWS,
    ACTION_NAMES,
    N_ACTIONS,
    N_STATES,
    build_model,
    cell_kind,
    is_terminal,
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
    legend,
    math_label,
    stat_row,
)
from .base import EnvControls, Page, Transport


# ==========================================================================
# Shared: an animated DP runner panel
# ==========================================================================

class DPRunner(Card):
    """Grid + transport + stats, driven by a snapshot generator."""

    def __init__(self, heading, cell=94, parent=None):
        super().__init__(heading, parent)
        self.grid = GridView(cell=cell)
        self.grid.value_fmt = "{:.3f}"
        self.add(self.grid)
        self.transport = Transport(interval=420)
        self.add(self.transport)

        self.st_sweep = Stat("sweep", "0", theme.ACCENT)
        self.st_delta = Stat("max change Δ", "-", theme.WARN)
        self.st_v0 = Stat("V(start)", "-", theme.GOOD)
        self.add_layout(stat_row(self.st_sweep, self.st_delta, self.st_v0))

        self.note = QLabel("Press Play.")
        self.note.setWordWrap(True)
        self.note.setStyleSheet(
            f"color:{theme.TEXT_DIM}; background:{theme.BG_INPUT};"
            f"border:1px solid {theme.BORDER}; border-radius:8px; padding:9px;"
            f"font-family:Consolas; font-size:11px;")
        self.note.setMinimumHeight(56)
        self.add(self.note)

        self.gen = None
        self._done = False

    def load(self, generator):
        self.gen = generator
        self._done = False
        self.transport.pause()

    def apply(self, snap):
        self.grid.V = snap.V
        self.grid.policy = snap.policy
        self.grid.highlight = set(snap.changed_states)
        self.grid.update()
        self.st_sweep.set(str(snap.sweep if snap.sweep else snap.outer_iter))
        self.st_delta.set("-" if snap.delta == float("inf") else f"{snap.delta:.3e}")
        self.st_v0.set(f"{snap.V[0]:+.5f}")
        self.note.setText(snap.note)
        if snap.converged:
            self.st_delta.set_color(theme.GOOD)
        else:
            self.st_delta.set_color(theme.WARN)

    def step(self):
        if self.gen is None or self._done:
            self.transport.pause()
            return None
        try:
            snap = next(self.gen)
        except StopIteration:
            self._done = True
            self.transport.pause()
            self.note.setText(self.note.text() + "\n\nCONVERGED — generator exhausted.")
            return None
        self.apply(snap)
        if snap.converged:
            self._done = True
            self.transport.pause()
        return snap


# ==========================================================================
# PAGE 11 -- Policy Evaluation
# ==========================================================================

class PolicyEvalPage(Page):
    TITLE = "Policy Evaluation"
    SUBTITLE = ("\"How good is THIS plan?\" Solve the Bellman expectation equation "
                "for a fixed π — no improving allowed.")
    SECTION = "Dynamic Prog."
    NOTES = "notes p.4 · p.6"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(math_label(
            r"V_{k+1}(s) \;\leftarrow\; \sum_{s'} P\big(s' \mid s, \pi(s)\big)"
            r"\left[\, r + \gamma\, V_k(s') \,\right]", 15))

        self.add(callout(
            "<b>You are forced to follow π.</b> If π(s) = LEFT you compute the "
            "physics of going LEFT, even when LEFT walks you into a hole. There is "
            "no max, no argmax, no choice. This is the honest-scoring half of the "
            "algorithm — and it must be honest, or the improvement half has nothing "
            "trustworthy to work from.", "key"))

        ctl = Card("controls")
        self.env = EnvControls(slip="classic", reward="shaped", gamma=0.99)
        self.env.changed.connect(self.reset)
        self.pol = QComboBox()
        self.pol.addItems([
            "π = always LEFT (awful)",
            "π = always DOWN",
            "π = always RIGHT",
            "π = go DOWN then RIGHT (hand-written)",
            "π = optimal π*",
        ])
        self.pol.currentIndexChanged.connect(self.reset)
        ctl.add_layout(labelled("Policy π", self.pol, 70))
        ctl.add(self.env)
        ctl.add(body(
            "Watch the numbers spread out from the goal. Each sweep, every state "
            "pulls the value of wherever π sends it. The gold outlines mark states "
            "that changed on this sweep.", dim=True))
        ctl.add_stretch()

        self.runner = DPRunner("iterative policy evaluation")
        self.runner.transport.step.connect(self.step)
        self.runner.transport.reset.connect(self.reset)

        self.row(self.runner, ctl, stretches=[0, 1])

        self.canvas = MplCanvas(width=10.5, height=2.9, ncols=2)
        self.add(self.canvas)

        cc = Card("the code")
        cp = CodePane(get_source(policy_evaluation))
        cp.sizeHintLine(26)
        self.cp = cp
        cc.add(cp)
        cc.add(body(
            (
                "Line to stare at: <code>v_new = q_from_V(P, V_prev, s, <b>pi[s]</b>, gamma)</code>. The action "
                "is <b>dictated</b> by π. On page 70 that one token becomes <code>max over a</code> and the "
                "algorithm turns into value iteration."
            ), dim=True))
        self.add(cc)

        self.add(callout(
            "<b>Jacobi vs Gauss-Seidel.</b> This implementation reads from "
            "<code>V_prev</code>, so every state updates from the <i>previous</i> "
            "sweep — that is Jacobi. If you read <code>V</code> in place instead, "
            "later states in the same sweep see the already-updated earlier ones "
            "(Gauss-Seidel), which usually converges in fewer sweeps. Both are "
            "correct and reach the same fixed point; only the path differs.", "warn"))

        self.finish()
        self.reset()

    def _pi(self):
        idx = self.pol.currentIndex()
        if idx == 0:
            return [0] * N_STATES
        if idx == 1:
            return [1] * N_STATES
        if idx == 2:
            return [2] * N_STATES
        if idx == 3:
            pi = []
            for s in range(N_STATES):
                r, c = divmod(s, 4)
                pi.append(1 if r < 3 else 2)
            return pi
        P = self.env.build()
        pi, _, _ = policy_iteration(P, gamma=min(self.env.gamma_value(), .9999),
                                    theta=1e-12)
        return pi

    def reset(self):
        P = self.env.build()
        g = min(self.env.gamma_value(), 0.9999)
        self.pi = self._pi()
        self.history = []
        self.runner.load(policy_evaluation_steps(P, self.pi, g, 1e-11, 2000))
        self.runner.grid.policy = self.pi
        self.runner.grid.V = [0.0] * N_STATES
        self.runner.grid.highlight = set()
        self.runner.grid.update()
        self.runner.st_sweep.set("0")
        self.runner.st_delta.set("-")
        self.runner.st_v0.set("+0.00000")
        self.runner.note.setText(
            "V = 0 everywhere. Press Play and watch the values propagate backwards "
            "from the goal.")
        self.cp.mark([], theme.ACCENT_DIM)
        self.draw()

    def step(self):
        snap = self.runner.step()
        if snap is None:
            return
        self.history.append((snap.sweep, snap.delta, list(snap.V)))
        self.draw()

    def draw(self):
        self.canvas.clear()
        a0, a1 = self.canvas.axes
        if self.history:
            xs = [h[0] for h in self.history]
            ds = [h[1] for h in self.history]
            a0.semilogy(xs, ds, color=theme.WARN, lw=2, marker="o", ms=3)
            a0.set_title("convergence: max |V_new − V_old| per sweep")
            a0.set_xlabel("sweep"); a0.set_ylabel("Δ  (log scale)")

            V = self.history[-1][2]
            cols = [theme.BAD if cell_kind(s) == "hole"
                    else theme.GOOD if cell_kind(s) == "goal"
                    else theme.ACCENT for s in range(N_STATES)]
            a1.bar(range(N_STATES), V, color=cols)
            a1.axhline(0, color=theme.BORDER, lw=1)
            a1.set_title(f"V^π after sweep {self.history[-1][0]}")
            a1.set_xlabel("state s"); a1.set_ylabel("V^π(s)")
        else:
            a0.set_title("convergence (press Play)")
            a1.set_title("V^π")
        self.canvas.refresh()

    def on_hide(self):
        self.runner.transport.pause()


# ==========================================================================
# PAGE 12 -- Policy Improvement
# ==========================================================================

class PolicyImprovePage(Page):
    TITLE = "Policy Improvement"
    SUBTITLE = "\"Given those scores, what SHOULD I do?\" One greedy pass. Here the max appears."
    SECTION = "Dynamic Prog."
    NOTES = "notes p.4 · p.6"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(math_label(
            r"\pi'(s) \;=\; \arg\max_a \sum_{s'} P(s'\mid s,a)"
            r"\left[\, r + \gamma\, V^\pi(s') \,\right] \;=\; \arg\max_a Q^\pi(s,a)", 15))

        self.add(callout(
            "<b>The policy improvement theorem.</b> If you build π' greedily from "
            "V<sup>π</sup>, then V<sup>π'</sup>(s) ≥ V<sup>π</sup>(s) for every "
            "state s. Never worse. Anywhere. And if π' = π, then π was already "
            "optimal. That guarantee is what makes the whole alternating scheme "
            "terminate.", "key"))

        ctl = Card("controls")
        self.env = EnvControls(slip="classic", reward="shaped", gamma=0.99)
        self.env.changed.connect(self.recompute)
        self.pol = QComboBox()
        self.pol.addItems(["start from π = always LEFT",
                           "start from π = always DOWN",
                           "start from π = always UP"])
        self.pol.currentIndexChanged.connect(self.recompute)
        ctl.add_layout(labelled("Old π", self.pol, 60))
        ctl.add(self.env)
        self.st_changed = Stat("states that changed", "-", theme.WARN)
        self.st_gain = Stat("V(start) before → after", "-", theme.GOOD)
        self.st_stable = Stat("policy stable?", "-", theme.ACCENT)
        ctl.add_layout(stat_row(self.st_changed))
        ctl.add_layout(stat_row(self.st_gain, self.st_stable))
        ctl.add_stretch()

        gr = Card("before → after")
        row = QHBoxLayout(); row.setSpacing(16)
        c1 = QVBoxLayout()
        l1 = QLabel("π (old) with its honest V^π")
        l1.setStyleSheet(f"color:{theme.TEXT_DIM}; font-size:11px; background:transparent;")
        self.g_old = GridView(cell=82); self.g_old.value_fmt = "{:.3f}"
        c1.addWidget(l1); c1.addWidget(self.g_old); c1.addStretch(1)
        c2 = QVBoxLayout()
        l2 = QLabel("π' = greedy(V^π) — gold = this state changed its mind")
        l2.setStyleSheet(f"color:{theme.TEXT_DIM}; font-size:11px; background:transparent;")
        self.g_new = GridView(cell=82); self.g_new.value_fmt = "{:.3f}"
        c2.addWidget(l2); c2.addWidget(self.g_new); c2.addStretch(1)
        row.addLayout(c1); row.addLayout(c2); row.addStretch(1)
        gr.add_layout(row)
        self.add(gr)
        self.add(ctl)

        # ---- per state detail -----------------------------------------------
        tb = Card("the argmax, state by state")
        self.tbl = QTableWidget(N_STATES, 7)
        self.tbl.setHorizontalHeaderLabels(
            ["s", "Q(s,←)", "Q(s,↓)", "Q(s,→)", "Q(s,↑)", "old π", "new π'"])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl.setMinimumHeight(430)
        self.tbl.setColumnWidth(0, 40)
        tb.add(self.tbl)
        self.add(tb)

        cc = Card("the code")
        cp = CodePane(get_source(policy_improvement))
        cp.sizeHintLine(22)
        cc.add(cp)
        self.add(cc)

        self.add(callout(
            "<b>Compare Q-values, not action indices.</b> Frozen Lake has masses of "
            "exact ties — two actions with identical Q. If you test "
            "<code>best_a != pi_old[s]</code> the policy will keep \"changing\" "
            "between equally good options and policy iteration <b>never "
            "terminates</b>. That is why the code tests "
            "<code>Q[s][best_a] - Q[s][pi_old[s]] &gt; 1e-12</code> instead. "
            "Your C++ <code>RL-FrozenLake_Prob.cpp</code> has this bug.", "bad"))

        self.finish()
        self.recompute()

    def recompute(self):
        P = self.env.build()
        g = min(self.env.gamma_value(), 0.9999)
        base = [0, 1, 3][self.pol.currentIndex()]
        pi_old = [base] * N_STATES

        V_old = policy_evaluation(P, pi_old, g, 1e-12)
        pi_new, stable, Q = policy_improvement(P, V_old, pi_old, g)
        V_new = policy_evaluation(P, pi_new, g, 1e-12)

        changed = [s for s in range(N_STATES)
                   if pi_new[s] != pi_old[s] and not is_terminal(s)]

        self.g_old.V, self.g_old.policy = V_old, pi_old
        self.g_old.update()
        self.g_new.V, self.g_new.policy = V_new, pi_new
        self.g_new.highlight = set(changed)
        self.g_new.update()

        self.st_changed.set(str(len(changed)))
        self.st_gain.set(f"{V_old[0]:+.4f} → {V_new[0]:+.4f}")
        self.st_stable.set("yes — π was optimal" if stable else "no")
        self.st_stable.set_color(theme.GOOD if stable else theme.WARN)

        for s in range(N_STATES):
            self.tbl.setItem(s, 0, QTableWidgetItem(str(s)))
            best = max(range(N_ACTIONS), key=lambda a: Q[s][a])
            for a in range(N_ACTIONS):
                it = QTableWidgetItem(f"{Q[s][a]:+.4f}")
                if a == best:
                    it.setForeground(QColor(theme.GOOD))
                    f = it.font(); f.setBold(True); it.setFont(f)
                self.tbl.setItem(s, 1 + a, it)
            self.tbl.setItem(s, 5, QTableWidgetItem(
                f"{ACTION_NAMES[pi_old[s]]} {ACTION_ARROWS[pi_old[s]]}"))
            ni = QTableWidgetItem(f"{ACTION_NAMES[pi_new[s]]} {ACTION_ARROWS[pi_new[s]]}")
            if s in changed:
                ni.setForeground(QColor(theme.WARN))
                f = ni.font(); f.setBold(True); ni.setFont(f)
            self.tbl.setItem(s, 6, ni)


# ==========================================================================
# PAGE 13 -- Policy Iteration
# ==========================================================================

class PolicyIterationPage(Page):
    TITLE = "Policy Iteration"
    SUBTITLE = "Evaluate → improve → evaluate → improve … until the policy stops moving."
    SECTION = "Dynamic Prog."
    NOTES = "notes p.3 · p.4"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>The cycle-of-trust paradox</b>, straight from your page-4 notes:<br>"
            "&nbsp;&nbsp;a. Evaluation scores state B as bad — <i>because the old "
            "dumb policy keeps walking into a wall there</i>.<br>"
            "&nbsp;&nbsp;b. Improvement fixes state B.<br>"
            "&nbsp;&nbsp;c. But state A made its decision assuming B was bad. Now "
            "that B is good, A wants to change its mind and move <i>towards</i> B."
            "<br><br>So you must re-evaluate to propagate the news — which opens up "
            "new improvements. Hence the loop.", "good"))

        ctl = Card("controls")
        self.env = EnvControls(slip="classic", reward="shaped", gamma=0.99)
        self.env.changed.connect(self.reset)
        ctl.add(self.env)
        self.st_round = Stat("PI round", "0", theme.VIOLET)
        self.st_phase = Stat("phase", "-", theme.ACCENT)
        self.st_evals = Stat("evaluation sweeps so far", "0", theme.CYAN)
        ctl.add_layout(stat_row(self.st_round, self.st_phase))
        ctl.add_layout(stat_row(self.st_evals))
        ctl.add(body(
            "Blue frames = an EVALUATE sweep (V changing, π frozen).<br>"
            "Gold frames = an IMPROVE pass (π changing, V frozen).<br><br>"
            "Notice the asymmetry: evaluation takes many sweeps, improvement takes "
            "exactly one. Almost all the compute goes into scoring a policy you are "
            "about to throw away — which is precisely the inefficiency value "
            "iteration removes.", dim=True))
        ctl.add_stretch()

        self.runner = DPRunner("policy iteration")
        self.runner.transport.step.connect(self.step)
        self.runner.transport.reset.connect(self.reset)
        self.row(self.runner, ctl, stretches=[0, 1])

        self.canvas = MplCanvas(width=10.5, height=2.9)
        self.add(self.canvas)

        cc = Card("the code")
        cp = CodePane(get_source(policy_iteration))
        cp.sizeHintLine(20)
        cc.add(cp)
        cc.add(body(
            (
                "Only ~8 real lines, because all the work is delegated to the two functions from pages 67 and "
                "68. Termination is <code>stable</code>, not a sweep count: policy iteration is guaranteed to "
                "finish in a <b>finite</b> number of rounds, because there are finitely many policies and each "
                "round strictly improves until it can't."
            ), dim=True))
        self.add(cc)

        self.finish()
        self.reset()

    def reset(self):
        P = self.env.build()
        g = min(self.env.gamma_value(), 0.9999)
        self.runner.load(policy_iteration_steps(P, g, 1e-11, 60, 2000))
        self.runner.grid.V = [0.0] * N_STATES
        self.runner.grid.policy = [0] * N_STATES
        self.runner.grid.highlight = set()
        self.runner.grid.update()
        self.eval_sweeps = 0
        self.rounds = []
        self.st_round.set("0"); self.st_phase.set("-"); self.st_evals.set("0")
        self.runner.note.setText("Round 0: π = all LEFT, V = 0. Press Play.")
        self.draw()

    def step(self):
        snap = self.runner.step()
        if snap is None:
            return
        if snap.kind == "evaluation":
            self.eval_sweeps += 1
            self.st_phase.set("EVALUATE")
            self.st_phase.set_color(theme.ACCENT)
        elif snap.kind == "improvement":
            self.st_phase.set("IMPROVE")
            self.st_phase.set_color(theme.WARN)
            self.rounds.append((snap.outer_iter, snap.V[0], len(snap.changed_states)))
            self.draw()
        self.st_round.set(str(snap.outer_iter))
        self.st_evals.set(str(self.eval_sweeps))

    def draw(self):
        self.canvas.clear()
        ax = self.canvas.ax
        if self.rounds:
            xs = [r[0] for r in self.rounds]
            v0 = [r[1] for r in self.rounds]
            ch = [r[2] for r in self.rounds]
            ax.plot(xs, v0, color=theme.GOOD, lw=2, marker="o", ms=5,
                    label="V(start) after each improvement")
            ax2 = ax.twinx()
            ax2.bar(xs, ch, alpha=0.35, color=theme.WARN,
                    label="states whose action changed")
            ax2.set_ylabel("states changed", color=theme.WARN, fontsize=9)
            ax2.tick_params(colors=theme.TEXT_DIM, labelsize=8)
            ax2.grid(False)
            ax.set_xlabel("policy-iteration round")
            ax.set_ylabel("V(start)")
            ax.set_title("monotone improvement — V(start) never goes down")
            self.canvas.legend(loc="lower right")
        else:
            ax.set_title("press Play")
        self.canvas.refresh()

    def on_hide(self):
        self.runner.transport.pause()


# ==========================================================================
# PAGE 14 -- Value Iteration
# ==========================================================================

class ValueIterationPage(Page):
    TITLE = "Value Iteration"
    SUBTITLE = ("One line instead of two phases. Watch the value \"ripple\" spread "
                "backwards from the goal.")
    SECTION = "Dynamic Prog."
    NOTES = "notes p.3 · p.4"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(math_label(
            r"V_{k+1}(s) \;\leftarrow\; \max_a \sum_{s'} P(s'\mid s,a)"
            r"\left[\, r + \gamma\, V_k(s') \,\right]", 15))

        self.add(callout(
            "<b>Reverse broadcasting</b>, exactly as your notes describe it: the "
            "goal yells \"I have money!\". On sweep 1 only its neighbours hear it. "
            "On sweep 2 the states two steps away find out. On sweep N the start "
            "node finally learns which way to go.<br><br>"
            "The physical world never changes during this — only <b>information</b> "
            "travels. That is why we loop.", "key"))

        ctl = Card("controls")
        self.env = EnvControls(slip="classic", reward="shaped", gamma=0.99)
        self.env.changed.connect(self.reset)
        ctl.add(self.env)
        ctl.add(body(
            "Gold outlines = states whose value changed this sweep. Watch the front "
            "expand outward from the goal, one ring per sweep, then stop.", dim=True))
        self.st_touched = Stat("states changed this sweep", "-", theme.WARN)
        self.st_total = Stat("total sweeps", "0", theme.CYAN)
        ctl.add_layout(stat_row(self.st_touched, self.st_total))
        ctl.add_stretch()

        self.runner = DPRunner("value iteration")
        self.runner.transport.step.connect(self.step)
        self.runner.transport.reset.connect(self.reset)
        self.row(self.runner, ctl, stretches=[0, 1])

        self.canvas = MplCanvas(width=10.5, height=2.9, ncols=2)
        self.add(self.canvas)

        cc = Card("the code")
        cp = CodePane(get_source(value_iteration))
        cp.sizeHintLine(30)
        cc.add(cp)
        cc.add(body(
            "Two structural differences from policy evaluation:<br>"
            "&nbsp;&nbsp;<b>1.</b> Compute all four action values, then use "
            "<code>q[argmax(q)]</code> instead of the value for <code>pi[s]</code>.<br>"
            "&nbsp;&nbsp;<b>2.</b> There is no policy inside the loop at all. It is "
            "<b>extracted once at the end</b>, from the converged values.", dim=True))
        self.add(cc)

        self.add(callout(
            "Value iteration is <b>Bellman optimality applied as an assignment</b>. "
            "It never bothers to make V correct for any particular policy — it goes "
            "straight for V*. That is why it needs no separate improvement step and "
            "no inner convergence loop. The price: unlike policy iteration it has no "
            "finite-round guarantee, only asymptotic convergence, so you stop on "
            "<code>Δ &lt; θ</code>.", "warn"))

        self.finish()
        self.reset()

    def reset(self):
        P = self.env.build()
        g = min(self.env.gamma_value(), 0.9999)
        self.runner.load(value_iteration_steps(P, g, 1e-11, 2000))
        self.runner.grid.V = [0.0] * N_STATES
        self.runner.grid.policy = [0] * N_STATES
        self.runner.grid.highlight = set()
        self.runner.grid.update()
        self.history = []
        self.st_touched.set("-"); self.st_total.set("0")
        self.runner.note.setText(
            "Sweep 0: V = 0 everywhere. Only transitions that actually touch the "
            "goal carry any reward yet. Press Play.")
        self.draw()

    def step(self):
        snap = self.runner.step()
        if snap is None:
            return
        self.history.append((snap.sweep, snap.delta, list(snap.V),
                             len(snap.changed_states)))
        self.st_touched.set(str(len(snap.changed_states)))
        self.st_total.set(str(snap.sweep))
        self.draw()

    def draw(self):
        self.canvas.clear()
        a0, a1 = self.canvas.axes
        if self.history:
            xs = [h[0] for h in self.history]
            a0.semilogy(xs, [max(h[1], 1e-16) for h in self.history],
                        color=theme.WARN, lw=2, marker="o", ms=3)
            a0.set_title("Δ per sweep — a straight line on a log axis means\n"
                         "geometric convergence at rate γ")
            a0.set_xlabel("sweep"); a0.set_ylabel("max |ΔV|  (log)")

            for s in [0, 4, 8, 9, 10, 13, 14]:
                a1.plot(xs, [h[2][s] for h in self.history], lw=1.6,
                        label=f"V({s})")
            a1.set_title("value of individual states over sweeps")
            a1.set_xlabel("sweep"); a1.set_ylabel("V(s)")
            self.canvas.legend(a1, ncol=2, loc="lower right")
        else:
            a0.set_title("press Play"); a1.set_title("")
        self.canvas.refresh()

    def on_hide(self):
        self.runner.transport.pause()


# ==========================================================================
# PAGE 15 -- PI vs VI, the code diff
# ==========================================================================

class CompareDPPage(Page):
    TITLE = "Policy vs Value Iteration"
    SUBTITLE = ("The same algorithm, one token apart. This page is the answer to "
                "\"how does a different chunk of code become a different algorithm?\"")
    SECTION = "Dynamic Prog."
    NOTES = "notes p.3 · p.4"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "Everything else — the sweeps, the θ test, the arrows, the "
            "<code>q_from_V</code> helper — is <b>identical</b>. Only the inner "
            "update line differs.", "key"))

        diff = Card("the one line that changes everything")
        row = QHBoxLayout(); row.setSpacing(16)

        c1 = QVBoxLayout()
        l1 = QLabel("POLICY EVALUATION  (inside policy iteration)")
        l1.setStyleSheet(f"color:{theme.ACCENT}; font-size:11px; font-weight:700;"
                         f"background:transparent;")
        cp1 = CodePane(
            get_example("evaluation_sweep"))
        cp1.sizeHintLine(6)
        cp1.mark_matching("q_from_V", theme.ACCENT_DIM)
        c1.addWidget(l1); c1.addWidget(cp1)
        l1b = QLabel("→ solves the Bellman EXPECTATION equation → V^π")
        l1b.setStyleSheet(f"color:{theme.TEXT_DIM}; font-size:11px; background:transparent;")
        c1.addWidget(l1b)

        c2 = QVBoxLayout()
        l2 = QLabel("VALUE ITERATION")
        l2.setStyleSheet(f"color:{theme.GOOD}; font-size:11px; font-weight:700;"
                         f"background:transparent;")
        cp2 = CodePane(
            get_example("optimality_sweep"))
        cp2.sizeHintLine(7)
        cp2.mark_matching("argmax(q)", "#1f7a4d")
        c2.addWidget(l2); c2.addWidget(cp2)
        l2b = QLabel("→ solves the Bellman OPTIMALITY equation → V*")
        l2b.setStyleSheet(f"color:{theme.TEXT_DIM}; font-size:11px; background:transparent;")
        c2.addWidget(l2b)

        row.addLayout(c1); row.addLayout(c2)
        diff.add_layout(row)
        self.add(diff)

        # ---- table -----------------------------------------------------------
        t = Card("structural comparison")
        tbl = QTableWidget(9, 3)
        tbl.setHorizontalHeaderLabels(["", "Policy Iteration", "Value Iteration"])
        tbl.verticalHeader().setVisible(False)
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        tbl.setColumnWidth(0, 190); tbl.setColumnWidth(1, 330)
        rows = [
            ("Inner update", "V(s) ← Q(s, π(s))", "V(s) ← max_a Q(s,a)"),
            ("Phases", "two, alternating and explicit", "one, fused"),
            ("Policy during the loop", "stored and used every sweep",
             "not stored at all — extracted once at the end"),
            ("Equation solved", "Bellman expectation, then greedy",
             "Bellman optimality, directly"),
            ("Inner loop", "evaluation runs to convergence each round",
             "none — one sweep per iteration"),
            ("Cost per iteration", "high (a full evaluation)", "low (one sweep)"),
            ("Iterations needed", "few (often 3–6 rounds)", "many (tens of sweeps)"),
            ("Termination", "policy stable — FINITE, guaranteed",
             "Δ < θ — asymptotic"),
            ("Best when", "actions are expensive to evaluate; you want a policy fast",
             "states are many; you want simple code"),
        ]
        for i, (a, b, c) in enumerate(rows):
            it = QTableWidgetItem(a)
            it.setForeground(QColor(theme.TEXT_DIM))
            f = it.font(); f.setBold(True); it.setFont(f)
            tbl.setItem(i, 0, it)
            tbl.setItem(i, 1, QTableWidgetItem(b))
            tbl.setItem(i, 2, QTableWidgetItem(c))
        tbl.resizeRowsToContents()
        tbl.setMinimumHeight(330)
        t.add(tbl)
        self.add(t)

        # ---- live race ---------------------------------------------------------
        race = Card("race them on identical settings")
        self.env = EnvControls(slip="classic", reward="shaped", gamma=0.99)
        self.env.changed.connect(self.race)
        race.add(self.env)

        rr = QHBoxLayout(); rr.setSpacing(16)
        cA = QVBoxLayout()
        la = QLabel("Policy Iteration result")
        la.setStyleSheet(f"color:{theme.ACCENT}; font-size:11px; font-weight:700;"
                         f"background:transparent;")
        self.gA = GridView(cell=80); self.gA.value_fmt = "{:.3f}"
        self.stA1 = Stat("rounds", "-", theme.ACCENT)
        self.stA2 = Stat("V(start)", "-", theme.GOOD)
        cA.addWidget(la); cA.addWidget(self.gA)
        cA.addLayout(stat_row(self.stA1, self.stA2)); cA.addStretch(1)

        cB = QVBoxLayout()
        lb = QLabel("Value Iteration result")
        lb.setStyleSheet(f"color:{theme.GOOD}; font-size:11px; font-weight:700;"
                         f"background:transparent;")
        self.gB = GridView(cell=80); self.gB.value_fmt = "{:.3f}"
        self.stB1 = Stat("sweeps", "-", theme.GOOD)
        self.stB2 = Stat("V(start)", "-", theme.GOOD)
        cB.addWidget(lb); cB.addWidget(self.gB)
        cB.addLayout(stat_row(self.stB1, self.stB2)); cB.addStretch(1)

        rr.addLayout(cA); rr.addLayout(cB); rr.addStretch(1)
        race.add_layout(rr)
        self.verdict = body("")
        race.add(self.verdict)
        self.add(race)

        self.add(callout(
            "The two grids should be numerically identical (to ~1e-9), even though "
            "one took 4 rounds and the other 30-odd sweeps. <b>Different route, "
            "same fixed point.</b> If the arrows differ anywhere, it is a tie — two "
            "actions with exactly equal Q — not a disagreement.", "good"))

        gpi = Card("both are special cases of one idea: GPI")
        gpi.add(body(
            (
                "<b>Generalised Policy Iteration</b> is the umbrella. Any algorithm that "
                "alternates<br>&nbsp;&nbsp;• making V more consistent with π (evaluation), and<br>&nbsp;&nbsp;• "
                "making π more greedy w.r.t. V (improvement)<br>is doing GPI, regardless of how completely it "
                "does either step.<br><br><b>Policy iteration</b> = run evaluation all the way to convergence "
                "before improving.<br><b>Value iteration</b> = do exactly one sweep of evaluation, then improve."
                " (The max <i>is</i> the improvement, folded in.)<br><b>Monte Carlo control</b> = evaluate with "
                "sampled returns, improve ε-greedily — same skeleton, page 74.<br><b>Actor-critic / DDPG</b> = "
                "the critic evaluates, the actor improves, both a little bit at every single time "
                "step.<br><br>Your notes call it \"a balance between critics and performers\". The two processes "
                "fight each other — each invalidating the other's work — and that fight is what converges."
            )))
        self.add(gpi)

        self.finish()
        self.race()

    def race(self):
        P = self.env.build()
        g = min(self.env.gamma_value(), 0.9999)

        import time
        t0 = time.perf_counter()
        piA, VA, rounds = policy_iteration(P, gamma=g, theta=1e-12)
        tA = time.perf_counter() - t0

        t0 = time.perf_counter()
        piB, VB, sweeps = value_iteration(P, gamma=g, theta=1e-12)
        tB = time.perf_counter() - t0

        self.gA.V, self.gA.policy = VA, piA; self.gA.update()
        self.gB.V, self.gB.policy = VB, piB; self.gB.update()
        self.stA1.set(str(rounds)); self.stA2.set(f"{VA[0]:+.5f}")
        self.stB1.set(str(sweeps)); self.stB2.set(f"{VB[0]:+.5f}")

        maxdiff = max(abs(a - b) for a, b in zip(VA, VB))
        differing = [s for s in range(N_STATES)
                     if piA[s] != piB[s] and not is_terminal(s)]

        # are the differing states genuine ties?
        QA = q_table_from_V(P, VA, g)
        ties = all(abs(QA[s][piA[s]] - QA[s][piB[s]]) < 1e-9 for s in differing)

        self.verdict.setText(
            f"largest |V_PI − V_VI| = <b style='color:{theme.GOOD}'>{maxdiff:.2e}</b> "
            f"&nbsp;·&nbsp; PI took <b>{rounds}</b> rounds ({tA*1000:.1f} ms), "
            f"VI took <b>{sweeps}</b> sweeps ({tB*1000:.1f} ms)"
            f"&nbsp;·&nbsp; arrows differ at <b>{len(differing)}</b> state(s)"
            + (f" — all of them exact ties in Q, so both are optimal."
               if differing and ties else
               " — a genuine disagreement, which would be a bug."
               if differing else "."))

