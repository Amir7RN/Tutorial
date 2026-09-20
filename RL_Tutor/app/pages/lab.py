"""
Pages 24-25.

  23  Code Lab  -- browse every rlcore function; notes on the C++ files in
                   this folder, including three real bugs
  24  Adam      -- the optimiser page from notes p.8
"""

from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .. import theme
from ..widgets import (
    Card,
    CodePane,
    MplCanvas,
    Stat,
    body,
    callout,
    get_source,
    labelled,
    math_label,
    stat_row,
)
from .base import Page


# ==========================================================================
# PAGE 23 -- Code Lab
# ==========================================================================

class CodeLabPage(Page):
    TITLE = "Code Lab"
    SUBTITLE = ("Every algorithm in this tutor, browsable. Edit the files under "
                "rlcore/ and the whole app changes with them.")
    SECTION = "Beyond"
    NOTES = "rlcore/"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "Nothing on any page re-implements an algorithm. Every grid, chart and "
            "number you have seen came from these functions, pulled live with "
            "<code>inspect.getsource</code>. Change a line here, relaunch, and the "
            "animations change. That is the point of keeping <code>rlcore/</code> "
            "free of any Qt import.", "key"))

        # ---- browser --------------------------------------------------------
        br = Card("browse rlcore")
        from rlcore import bandit, deeprl, dp, frozen_lake, mc

        self._registry = {}

        def reg(group, name, obj):
            self._registry[f"{group}  ·  {name}"] = obj

        reg("frozen_lake", "build_model  (the MDP table)", frozen_lake.build_model)
        reg("frozen_lake", "FrozenLake.step  (the simulator)", frozen_lake.FrozenLake.step)
        reg("frozen_lake", "SlipModel.as_pairs", frozen_lake.SlipModel.as_pairs)
        reg("frozen_lake", "move  (grid geometry + wall clipping)", frozen_lake.move)
        reg("frozen_lake", "q_from_V  (one-step lookahead)", frozen_lake.q_from_V)
        reg("frozen_lake", "V_from_Q", frozen_lake.V_from_Q)
        reg("frozen_lake", "run_episode", frozen_lake.run_episode)

        reg("dp", "policy_evaluation", dp.policy_evaluation)
        reg("dp", "policy_improvement", dp.policy_improvement)
        reg("dp", "policy_iteration", dp.policy_iteration)
        reg("dp", "value_iteration", dp.value_iteration)
        reg("dp", "q_value_iteration  (bridge to Q-learning)", dp.q_value_iteration)
        reg("dp", "evaluate_policy_empirically", dp.evaluate_policy_empirically)

        reg("mc", "mc_prediction  (FVMC / EVMC)", mc.mc_prediction)
        reg("mc", "mc_control  (GPI, model-free)", mc.mc_control)
        reg("mc", "epsilon_greedy", mc.epsilon_greedy)
        reg("mc", "estimate_pi", mc.estimate_pi)
        reg("mc", "dice_convergence", mc.dice_convergence)

        reg("bandit", "epsilon_greedy_run", bandit.epsilon_greedy_run)
        reg("bandit", "ucb_run", bandit.ucb_run)
        reg("bandit", "compare", bandit.compare)

        reg("deeprl", "Dense.backward  (where dQ/da comes from)",
            deeprl.Dense.backward)
        reg("deeprl", "Dense.adam", deeprl.Dense.adam)
        reg("deeprl", "ReplayBuffer  (why it is off-policy)",
            deeprl.ReplayBuffer)
        reg("deeprl", "DDPG  (the four networks)", deeprl.DDPG)
        reg("deeprl", "DDPG.train_step  (the three equations)",
            deeprl.DDPG.train_step)
        reg("deeprl", "DDPG.act  (deterministic, plus noise)", deeprl.DDPG.act)
        reg("deeprl", "ContextualReach  (true Q known)", deeprl.ContextualReach)
        reg("deeprl", "GaitTuneEnv  (one step = one gait cycle)",
            deeprl.GaitTuneEnv)
        reg("deeprl", "train_gait", deeprl.train_gait)

        self.picker = QListWidget()
        for k in self._registry:
            self.picker.addItem(k)
        self.picker.setMinimumWidth(300)
        self.picker.currentTextChanged.connect(self.show_source)

        self.pane = CodePane("")
        self.pane.setMinimumHeight(560)

        sp = QSplitter(Qt.Horizontal)
        w1 = QWidget(); l1 = QVBoxLayout(w1); l1.setContentsMargins(0, 0, 0, 0)
        l1.addWidget(self.picker)
        sp.addWidget(w1)
        sp.addWidget(self.pane)
        sp.setStretchFactor(0, 0)
        sp.setStretchFactor(1, 1)
        sp.setSizes([300, 900])
        br.add(sp)
        self.add(br)
        self.picker.setCurrentRow(0)

        # ---- how to run ------------------------------------------------------
        howto = Card("use it outside the GUI")
        howto.add(body("Everything is importable. From the project root:", dim=True))
        howto.add(CodePane(
            ">>> from rlcore import *\n"
            ">>>\n"
            ">>> # --- model-based ---------------------------------------\n"
            ">>> P = build_model(slip='classic', reward='shaped')\n"
            ">>> pi, V, sweeps = value_iteration(P, gamma=0.99)\n"
            ">>> print(sweeps, round(V[0], 4))\n"
            ">>> print([ACTION_ARROWS[a] for a in pi[:4]])\n"
            ">>>\n"
            ">>> # --- model-free ----------------------------------------\n"
            ">>> env = FrozenLake(slip='classic', reward='shaped', seed=0)\n"
            ">>> Q, pi_mc, stats = mc_control(env, episodes=30000)\n"
            ">>> print(stats['success_rate'])\n"
            ">>>\n"
            ">>> # --- do they agree? ------------------------------------\n"
            ">>> V_mc = policy_evaluation(P, pi_mc, 0.99)\n"
            ">>> print(round(V[0], 4), round(V_mc[0], 4))\n"
            ">>>\n"
            ">>> # --- run the correctness suite -------------------------\n"
            ">>> # python tests/test_core.py"))
        self.add(howto)

        # ---- exercises -------------------------------------------------------
        ex = Card("things to try — in rough order of difficulty")
        tbl = QTableWidget(9, 2)
        tbl.setHorizontalHeaderLabels(["change", "what to look for"])
        tbl.verticalHeader().setVisible(False)
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.setColumnWidth(0, 400)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        rows = [
            ("In dp.py, change value_iteration's `max(...)` to `min(...)`",
             "You now solve for the WORST policy. The arrows point at holes. "
             "Proof that the max is the only thing making it 'optimal'."),
            ("In policy_evaluation, read `V` instead of `V_prev`",
             (
                 "Gauss-Seidel instead of Jacobi. Same answer, fewer sweeps. Watch the sweep count on page 67 "
                 "drop."
             )),
            ("In frozen_lake.py, add a 4th slip preset with intended=0.5",
             "It appears in every dropdown on every page automatically — the "
             "pages read SLIP_MODELS, they do not hard-code it."),
            ("Set REWARD_SCHEMES['gym'].hole to -1.0",
             "Value iteration barely changes; MC control gets dramatically faster. "
             "That difference IS reward shaping."),
            ("In mc.py, delete the `first_idx` forward pass and use a "
             "backward-filled set",
             "You silently get LAST-visit MC. The estimates still look plausible, "
             "which is exactly why this bug survives in real code."),
            ("In mc_control, remove the random tie-break from epsilon_greedy",
             "Q starts all-zero, so max() always returns action 0. Three quarters "
             "of the grid never gets explored."),
            ("In policy_improvement, test `best_a != pi_old[s]` instead of "
             "comparing Q-values",
             "Policy iteration hangs forever on tie states. This is the bug in "
             "your RL-FrozenLake_Prob.cpp."),
            ("Write `sarsa(env, ...)` next to mc_control",
             "Same skeleton, but update inside the step loop with "
             "Q(s,a) += α[r + γQ(s',a') − Q(s,a)]. No waiting for the episode."),
            ("Write `q_learning(env, ...)`",
             "Change SARSA's Q(s',a') to max_a' Q(s',a'). That single token is the "
             "on-policy / off-policy divide."),
        ]
        for i, (a, b) in enumerate(rows):
            it = QTableWidgetItem(a)
            it.setForeground(QColor(theme.ACCENT))
            tbl.setItem(i, 0, it)
            tbl.setItem(i, 1, QTableWidgetItem(b))
        tbl.resizeRowsToContents()
        tbl.setMinimumHeight(430)
        ex.add(tbl)
        self.add(ex)

        # ---- C++ notes ---------------------------------------------------------
        cpp = Card("notes on the C++ files in this folder")
        cpp.add(body(
            "These implementations sit alongside the PDF. They are broadly right, "
            "and comparing them against <code>rlcore/</code> is a good exercise. "
            "Three genuine bugs are worth knowing about:", dim=True))

        cpp.add(callout(
            "<b>RL-FrozenLake_Prob.cpp — <code>get_next_state</code> is broken.</b> "
            "Every branch has <code>min</code> and <code>max</code> the wrong way "
            "round:<br>"
            "&nbsp;• <code>move 0 (up): row = min(0, row+1)</code> — row+1 ≥ 1, so "
            "this is <b>always 0</b>. UP teleports to the top row from anywhere. "
            "Should be <code>max(0, row-1)</code>.<br>"
            "&nbsp;• <code>move 2 (down): row = max(3, row+1)</code> — <b>always "
            "3</b>. DOWN teleports to the bottom row. Should be "
            "<code>min(3, row+1)</code>.<br>"
            "&nbsp;• <code>move 1 (left): col = min(0, col-1)</code> — gives "
            "<b>−1</b> when col is 0, which indexes off the row. Should be "
            "<code>max(0, col-1)</code>.<br>"
            "&nbsp;• <code>move 3 (right): row = max(3, col+1)</code> — assigns to "
            "<b>row</b> using <b>col</b>. Should be "
            "<code>col = min(3, col+1)</code>.<br><br>"
            "Concretely, from state 9: UP gives 1 (should be 5) and RIGHT gives 13 "
            "(should be 10). The DP algorithm wrapped around this is fine — it is "
            "solving the wrong world.", "bad"))

        cpp.add(callout(
            "<b>RL-FrozenLake_Prob.cpp — <code>policy_improvement</code> takes "
            "<code>Policy pi</code> by value.</b><br>"
            "The improved policy is written into a local copy and thrown away when "
            "the function returns. <code>policy_iteration</code> therefore evaluates "
            "the same all-zero policy forever. Needs <code>Policy&amp; pi</code>.<br>"
            "It also compares <code>old_a != best_action</code> rather than the "
            "Q-values, which would loop forever on ties even after the reference "
            "is fixed.", "bad"))

        cpp.add(callout(
            "<b>RL-FrozenLake_MontoCarlo.cpp — wrong distribution type.</b><br>"
            "<code>uniform_int_distribution&lt;&gt; dist(0.0, 1.0);</code> then "
            "<code>if (dist(rng) &lt; epsilon)</code>. An <i>int</i> distribution "
            "over {0,1} returns only 0 or 1, so with epsilon &lt; 1 this explores "
            "roughly 50% of the time regardless of ε, and ε decay does nothing. "
            "Should be <code>uniform_real_distribution&lt;double&gt;</code>.<br>"
            "Separately, <code>(action + 1) % GRID_SIZE</code> uses GRID_SIZE where "
            "N_ACTIONS is meant. It works here only because both happen to be 4.",
            "warn"))

        cpp.add(callout(
            "<b>RL-FrozenLake_ValIter.cpp is correct.</b> Jacobi value iteration, "
            "proper terminal handling, sensible policy extraction. Its "
            "<code>theta = 1e-100</code> is below double precision so it stops when "
            "the values stop changing bit-for-bit rather than at the threshold — "
            "harmless here, just slower than it needs to be.", "good"))

        cpp.add(body(
            "Also note the three files use <b>three different action encodings</b> "
            "(<code>down,left,up,right</code> / <code>up,left,down,right</code> / "
            "<code>left,down,right,up</code>). Their printed policies are therefore "
            "not comparable with each other. <code>rlcore</code> uses the Gymnasium "
            "convention <code>0=LEFT 1=DOWN 2=RIGHT 3=UP</code> everywhere, which is "
            "also what the arrows on every page mean."))
        self.add(cpp)

        self.finish()

    def show_source(self, key):
        obj = self._registry.get(key)
        if obj is None:
            return
        self.pane.set_code(get_source(obj))


# ==========================================================================
# PAGE 24 -- Adam
# ==========================================================================

class AdamPage(Page):
    TITLE = "Adam, Backprop & BatchNorm"
    SUBTITLE = ("From notes p.8. Not needed for tabular RL — needed the moment a "
                "neural network replaces the table.")
    SECTION = "Beyond"
    NOTES = "notes p.8"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            (
                "The preceding lake algorithms are <b>tabular</b>: 16 states fit in an array, so there is "
                "nothing to optimise — you just assign the right number to the right slot.<br><br>Adam only "
                "becomes relevant when the state space is too big to enumerate and V or Q becomes a neural "
                "network. Then the Bellman equation stops being an assignment and becomes a <b>loss to "
                "minimise</b>."
            ), "key"))

        # ---- adam ------------------------------------------------------------
        a = Card("Adam — adaptive moment estimation")
        a.add(body(
            "Your notes' hiker analogy: plain gradient descent feels the slope and "
            "takes one step downhill, zig-zagging on rough terrain. Adam is a heavy "
            "ball that keeps momentum through small bumps and adapts its friction to "
            "how rough the ground is.", dim=True))
        a.add(math_label(r"m_t = \beta_1 m_{t-1} + (1-\beta_1)\, g_t", 14))
        a.add(body("<b>m — momentum.</b> A moving average of the gradient "
                   "<i>direction</i>. β₁ = 0.9 means \"keep 90% of the old "
                   "direction, add 10% of the new one\". If the gradient zig-zags "
                   "left-right-left-right, m averages to roughly straight.", dim=True))
        a.add(math_label(r"v_t = \beta_2 v_{t-1} + (1-\beta_2)\, g_t^2", 14))
        a.add(body((
                       "<b>v — second raw moment.</b> A moving average of the <i>squared</i> gradient, so it measures "
                       "magnitude regardless of sign — how steep and volatile the terrain has been. β₂ = 0.999 keeps a "
                       "very long history."
                   ), dim=True))
        a.add(math_label(r"\hat{m}_t = \frac{m_t}{1-\beta_1^t}, \qquad "
                         r"\hat{v}_t = \frac{v_t}{1-\beta_2^t}", 14))
        a.add(body("<b>Bias correction.</b> m and v start at 0, so the first few "
                   "updates would be tiny (0.9 × 0 is still 0). Dividing by "
                   "(1 − βᵗ) inflates them back up early on, then fades to a no-op "
                   "as t grows.", dim=True))
        a.add(math_label(r"\theta_t = \theta_{t-1} - \frac{\alpha\, \hat{m}_t}"
                         r"{\sqrt{\hat{v}_t} + \epsilon}", 15))
        a.add(body("<b>The adaptive step.</b> Dividing by √v̂ is the whole trick: "
                   "steep, volatile terrain (v high) → divide by a big number → "
                   "small careful steps. Flat, stable terrain (v low) → divide by a "
                   "small number → speed up. ε = 1e-8 only prevents division by "
                   "zero.", dim=True))
        self.add(a)

        demo = Card("see it — three optimisers on the same bumpy valley")
        demo.add(body(
            "A narrow ravine: steep across, nearly flat along. The classic case "
            "where plain SGD zig-zags across the walls and barely advances.", dim=True))
        hb = QHBoxLayout(); hb.setSpacing(8)
        self.btn = QPushButton("Run"); self.btn.setObjectName("Primary")
        hb.addWidget(self.btn); hb.addStretch(1)
        demo.add_layout(hb)
        self.canvas = MplCanvas(width=10.6, height=3.6, ncols=2)
        demo.add(self.canvas)
        self.btn.clicked.connect(self.run_demo)
        self.add(demo)

        # ---- forward / backward ------------------------------------------------
        fb = Card("forward vs backward pass — the cheat sheet")
        row = QHBoxLayout(); row.setSpacing(16)
        f = Card("A · forward pass (predict)")
        f.add(body(
            "<b>Direction:</b> input → hidden → output.<br><br>"
            "Per layer:<br>"
            "&nbsp;1. receive input from the previous layer<br>"
            "&nbsp;2. <b>cache a copy of that input</b> — you need it later<br>"
            "&nbsp;3. Z = (input × W) + b<br>"
            "&nbsp;4. apply the activation (ReLU / tanh)<br>"
            "&nbsp;5. pass the result on"))
        row.addWidget(f)
        b = Card("B · backward pass (learn)")
        b.add(body(
            "<b>Direction:</b> output → hidden → input.<br><br>"
            "Per layer:<br>"
            "&nbsp;1. receive the error signal from the layer ahead<br>"
            "&nbsp;2. multiply by the activation derivative — <i>only let error "
            "through where the neuron was active</i><br>"
            "&nbsp;3. grad_W = error × cached input <span "
            "style='color:%s'>(this is why you cached it)</span><br>"
            "&nbsp;4. grad_b = error<br>"
            "&nbsp;5. delta_out = error × W → pass to the previous layer" % theme.WARN))
        row.addWidget(b)
        fb.add_layout(row)
        fb.add(body(
            (
                "<b>C · optimisation step (Adam).</b> Takes grad_W from B and actually changes the weights: "
                "check momentum (\"which way were we heading?\"), check the second moment (the recent "
                "squared-gradient scale), then W_new = W_old − smart_gradient."
            ), dim=True))
        self.add(fb)

        # ---- batchnorm ----------------------------------------------------------
        bn = Card("batch normalisation — and why your version drops half of it")
        bn.add(body(
            "<b>The problem.</b> A deep network is a game of telephone: as the "
            "signal passes through layers it can grow too large (numerical "
            "blow-up), shrink to nothing (vanishing), or drift off-centre. The "
            "technical name is <i>internal covariate shift</i>.<br><br>"
            "<b>Standard BN.</b> At each layer, force the batch to mean 0 and "
            "variance 1, then apply two <i>learnable</i> parameters — scale γ and "
            "shift β — so the network can undo the normalisation if it turns out to "
            "need to."))
        bn.add(math_label(
            r"\hat{x} = \frac{x - \mu_{\mathcal{B}}}"
            r"{\sqrt{\sigma^2_{\mathcal{B}} + \epsilon}}, \qquad y = \gamma \hat{x} + \beta", 14))
        bn.add(callout(
            "Your implementation keeps only the <b>second half</b> — the learnable "
            "γ and β — and skips computing batch mean and variance. That is a "
            "defensible choice for your case:<br>"
            "&nbsp;• <b>batch size 4</b> — mean/variance over 4 samples is so noisy "
            "it does more harm than good;<br>"
            "&nbsp;• <b>real-time constraint</b> — standard BN needs running "
            "statistics maintained for inference, which is extra state and extra "
            "latency;<br>"
            "&nbsp;• what remains is a <b>learnable volume knob</b>: a dedicated "
            "place for the network to say \"layer 1's output is too quiet, multiply "
            "by 2 before layer 2\".", "good"))
        self.add(bn)

        self.add(callout(
            (
                "<b>Where this reconnects to RL.</b> On page 70 the DP target was an assignment: <code>V(s) ← "
                "max_a Q(s,a)</code>. With a network you cannot assign — you can only nudge weights. So the same"
                " equation becomes a regression:<br>&nbsp;&nbsp;target y = r + γ·max<sub>a'</sub> Q(s', "
                "a')<br>&nbsp;&nbsp;loss = MSE(y, Q(s,a))<br>&nbsp;&nbsp;Adam minimises that loss.<br><br>The "
                "Bellman equation did not change. Only the way we <i>enforce</i> it did — and that is the entire"
                " step from value iteration to DQN and DDPG."
            ),
            "key"))

        self.finish()
        self.run_demo()

    def run_demo(self):
        import math

        # A narrow ravine: steep in x, shallow in y.
        def grad(x, y):
            return 20.0 * x, 1.0 * y

        def loss(x, y):
            return 10.0 * x * x + 0.5 * y * y

        start = (-1.0, -1.6)
        steps = 90

        def sgd(lr=0.04):
            x, y = start
            path = [(x, y)]
            for _ in range(steps):
                gx, gy = grad(x, y)
                x -= lr * gx; y -= lr * gy
                path.append((x, y))
            return path

        def momentum(lr=0.04, beta=0.9):
            x, y = start
            mx = my = 0.0
            path = [(x, y)]
            for _ in range(steps):
                gx, gy = grad(x, y)
                mx = beta * mx + (1 - beta) * gx
                my = beta * my + (1 - beta) * gy
                x -= lr * mx; y -= lr * my
                path.append((x, y))
            return path

        def adam(lr=0.12, b1=0.9, b2=0.999, eps=1e-8):
            x, y = start
            mx = my = vx = vy = 0.0
            path = [(x, y)]
            for t in range(1, steps + 1):
                gx, gy = grad(x, y)
                mx = b1 * mx + (1 - b1) * gx
                my = b1 * my + (1 - b1) * gy
                vx = b2 * vx + (1 - b2) * gx * gx
                vy = b2 * vy + (1 - b2) * gy * gy
                mhx, mhy = mx / (1 - b1 ** t), my / (1 - b1 ** t)
                vhx, vhy = vx / (1 - b2 ** t), vy / (1 - b2 ** t)
                x -= lr * mhx / (math.sqrt(vhx) + eps)
                y -= lr * mhy / (math.sqrt(vhy) + eps)
                path.append((x, y))
            return path

        paths = {"plain SGD": (sgd(), theme.BAD),
                 "momentum": (momentum(), theme.WARN),
                 "Adam": (adam(), theme.GOOD)}

        self.canvas.clear()
        a0, a1 = self.canvas.axes

        import numpy as np
        xs = np.linspace(-1.3, 1.3, 220)
        ys = np.linspace(-1.9, 1.9, 220)
        X, Y = np.meshgrid(xs, ys)
        Z = 10 * X ** 2 + 0.5 * Y ** 2
        a0.contour(X, Y, Z, levels=18, colors=theme.BORDER, linewidths=0.6)
        for name, (path, col) in paths.items():
            a0.plot([p[0] for p in path], [p[1] for p in path],
                    color=col, lw=1.7, marker="o", ms=2, label=name)
        a0.plot(0, 0, marker="*", ms=14, color=theme.TEXT)
        a0.set_xlabel("x  (steep direction)"); a0.set_ylabel("y  (flat direction)")
        a0.set_title("the ravine — SGD zig-zags, Adam drives straight down")
        self.canvas.legend(a0, loc="upper right")

        for name, (path, col) in paths.items():
            a1.semilogy([max(loss(x, y), 1e-18) for x, y in path],
                        color=col, lw=1.8, label=name)
        a1.set_xlabel("step"); a1.set_ylabel("loss  (log)")
        a1.set_title("loss over time")
        self.canvas.legend(a1)
        self.canvas.refresh()
