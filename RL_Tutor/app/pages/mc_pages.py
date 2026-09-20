"""
Pages 17-19: Monte Carlo -- learning without a model.

  17  MC is just averaging  -- dice, darts, and the law of large numbers
  18  MC Prediction         -- FVMC vs EVMC, converging to the DP answer
  19  MC Control            -- GPI with sampled returns and epsilon-greedy
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
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
    FrozenLake,
    build_model,
    cell_kind,
    is_terminal,
)
from rlcore.mc import (
    dice_convergence,
    epsilon_greedy,
    estimate_pi,
    mc_control,
    mc_control_steps,
    mc_prediction,
    mc_prediction_steps,
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
# PAGE 16 -- MC is just averaging
# ==========================================================================

class MCIntroPage(Page):
    TITLE = "Monte Carlo = Averaging"
    SUBTITLE = ("Before any RL: the whole method is 'sample a lot, take the mean'. "
                "Both warm-ups from your notes, live.")
    SECTION = "Monte Carlo"
    NOTES = "notes p.5"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "V<sup>π</sup>(s) is <b>defined</b> as an expectation: "
            "V<sup>π</sup>(s) = E<sub>π</sub>[G<sub>t</sub> | S<sub>t</sub>=s].<br><br>"
            "Dynamic programming computes that expectation <i>exactly</i>, by "
            "summing over P. Monte Carlo estimates it the way you'd estimate any "
            "average: <b>play many episodes and take the mean of the returns you "
            "actually saw</b>. No model. No bootstrapping. No Bellman equation.",
            "key"))

        # ---- dice -----------------------------------------------------------
        d = Card("warm-up 1 — the six-sided die")
        d.add(body(
            "E[die] = (1+2+3+4+5+6)/6 = <b>3.5</b>. You can compute that exactly "
            "(that is DP). Or you can roll it and average (that is MC). Watch the "
            "running mean crawl in.", dim=True))
        hb = QHBoxLayout(); hb.setSpacing(8)
        self.dice_n = QSpinBox(); self.dice_n.setRange(10, 200000); self.dice_n.setValue(3000)
        self.dice_n.setSingleStep(500)
        self.btn_dice = QPushButton("Roll"); self.btn_dice.setObjectName("Primary")
        hb.addWidget(QLabel("rolls:")); hb.addWidget(self.dice_n)
        hb.addWidget(self.btn_dice); hb.addStretch(1)
        d.add_layout(hb)
        self.dice_canvas = MplCanvas(width=10.4, height=2.7)
        d.add(self.dice_canvas)
        self.st_dice = Stat("estimate after N rolls", "-", theme.WARN)
        self.st_dice_err = Stat("|error|", "-", theme.BAD)
        d.add_layout(stat_row(self.st_dice, self.st_dice_err))
        self.btn_dice.clicked.connect(self.roll_dice)
        self.add(d)

        # ---- pi -------------------------------------------------------------
        pcard = Card("warm-up 2 — estimating π by throwing darts")
        pcard.add(body(
            "Throw random points into the unit square; count how many land inside "
            "the quarter circle x²+y² ≤ 1. The ratio of areas is π/4, so "
            "π ≈ 4·(inside/total). Same machinery, different question.", dim=True))
        hb2 = QHBoxLayout(); hb2.setSpacing(8)
        self.pi_n = QSpinBox(); self.pi_n.setRange(10, 500000); self.pi_n.setValue(5000)
        self.pi_n.setSingleStep(1000)
        self.btn_pi = QPushButton("Throw"); self.btn_pi.setObjectName("Primary")
        hb2.addWidget(QLabel("darts:")); hb2.addWidget(self.pi_n)
        hb2.addWidget(self.btn_pi); hb2.addStretch(1)
        pcard.add_layout(hb2)
        self.pi_canvas = MplCanvas(width=10.4, height=3.2, ncols=2)
        pcard.add(self.pi_canvas)
        self.st_pi = Stat("estimate of π", "-", theme.WARN)
        self.st_pi_err = Stat("|error|", "-", theme.BAD)
        pcard.add_layout(stat_row(self.st_pi, self.st_pi_err))
        self.btn_pi.clicked.connect(self.throw_darts)
        self.add(pcard)

        self.add(callout(
            "<b>The convergence rate is O(1/√N)</b>, and you can see it: the error "
            "envelope narrows, but slowly. 100× more samples buys only 10× more "
            "accuracy.<br><br>"
            "That single fact explains the entire cost difference in this tutor: "
            "value iteration nails V* in ~30 sweeps; Monte Carlo needs tens of "
            "thousands of episodes for a rougher answer. DP <i>computes</i> the "
            "expectation; MC has to <i>measure</i> it.", "warn"))

        cc = Card("the code")
        cp = CodePane(get_source(estimate_pi))
        cp.sizeHintLine(20)
        cc.add(cp)
        self.add(cc)

        self.finish()
        self.roll_dice()
        self.throw_darts()

    def roll_dice(self):
        n = self.dice_n.value()
        import random
        run = dice_convergence(n, seed=random.randrange(10**6))
        self.dice_canvas.clear()
        ax = self.dice_canvas.ax
        ax.plot(range(1, n + 1), run, color=theme.ACCENT, lw=1.2)
        ax.axhline(3.5, color=theme.GOOD, lw=1.6, ls="--", label="true E = 3.5")
        ax.set_xscale("log")
        ax.set_xlabel("rolls (log scale)"); ax.set_ylabel("running mean")
        ax.set_title("the estimate converges — but the wobble decays slowly")
        ax.set_ylim(2.6, 4.4)
        self.dice_canvas.legend()
        self.dice_canvas.refresh()
        self.st_dice.set(f"{run[-1]:.4f}")
        self.st_dice_err.set(f"{abs(run[-1] - 3.5):.4f}")

    def throw_darts(self):
        import math
        import random
        n = self.pi_n.value()
        seed = random.randrange(10**6)
        run = estimate_pi(n, seed=seed)

        rng = random.Random(seed)
        show = min(n, 3000)
        xin, yin, xout, yout = [], [], [], []
        for _ in range(show):
            x, y = rng.random(), rng.random()
            if x * x + y * y <= 1.0:
                xin.append(x); yin.append(y)
            else:
                xout.append(x); yout.append(y)

        self.pi_canvas.clear()
        a0, a1 = self.pi_canvas.axes
        a0.scatter(xin, yin, s=2, color=theme.GOOD, label="inside")
        a0.scatter(xout, yout, s=2, color=theme.BAD, label="outside")
        th = [i / 200 * math.pi / 2 for i in range(201)]
        a0.plot([math.cos(t) for t in th], [math.sin(t) for t in th],
                color=theme.TEXT, lw=1.4)
        a0.set_aspect("equal"); a0.set_xlim(0, 1); a0.set_ylim(0, 1)
        a0.set_title(f"first {show:,} darts")
        self.pi_canvas.legend(a0, loc="lower left")

        a1.plot(range(1, n + 1), run, color=theme.ACCENT, lw=1.2)
        a1.axhline(math.pi, color=theme.GOOD, lw=1.6, ls="--", label="π")
        a1.set_xscale("log"); a1.set_ylim(2.6, 3.7)
        a1.set_xlabel("darts (log scale)"); a1.set_ylabel("4 · inside / total")
        a1.set_title("running estimate")
        self.pi_canvas.legend(a1)
        self.pi_canvas.refresh()

        self.st_pi.set(f"{run[-1]:.5f}")
        self.st_pi_err.set(f"{abs(run[-1] - math.pi):.5f}")


# ==========================================================================
# PAGE 17 -- MC prediction
# ==========================================================================

class MCPredictionPage(Page):
    TITLE = "MC Prediction (FVMC / EVMC)"
    SUBTITLE = ("The prediction problem: estimate V^π without a model. First-visit "
                "vs every-visit, converging onto the DP answer.")
    SECTION = "Monte Carlo"
    NOTES = "notes p.5 §4.2–4.3"

    def __init__(self, parent=None):
        super().__init__(parent)

        m = Card("the algorithm")
        m.add(body("For each episode generated under π, walk the trajectory "
                   "<b>backwards</b> accumulating the return:", dim=True))
        m.add(math_label(r"G \;\leftarrow\; \gamma\, G + R_{t+1}"
                         r"\qquad\text{(after this line, } G = G_t\text{)}", 14))
        m.add(body("then fold that return into a running mean for the state:", dim=True))
        m.add(math_label(
            r"N(s) \mathrel{+}= 1, \qquad "
            r"V(s) \mathrel{+}= \frac{G - V(s)}{N(s)}", 14))
        m.add(callout(
            "The backward walk is not a style choice. Computing every G<sub>t</sub> "
            "forwards is O(T²); backwards it is O(T), because G<sub>t</sub> = "
            "γ·G<sub>t+1</sub> + R<sub>t+1</sub> reuses the work you just did.",
            "key"))
        self.add(m)

        two = QHBoxLayout(); two.setSpacing(14)
        fv = Card("First-Visit MC (FVMC)")
        fv.add(body(
            "Within one episode, only the <b>first</b> time you land on s "
            "contributes a return to s's average. Later re-visits in that same "
            "episode are skipped.<br><br>"
            "<b>Unbiased</b> — each sampled return is an independent draw from "
            "G<sub>t</sub>|S<sub>t</sub>=s. The textbook default."))
        two.addWidget(fv)
        ev = Card("Every-Visit MC (EVMC)")
        ev.add(body(
            "<b>Every</b> landing contributes, so one episode can feed the same "
            "state several returns.<br><br>"
            "<b>Biased</b> for finite samples (the returns within an episode are "
            "correlated), but <b>consistent</b> — the bias vanishes as N → ∞ — and "
            "it extracts more data per episode, so it is often better early on."))
        two.addWidget(ev)
        self.add_layout(two)

        self.add(callout(
            "The implementation trap: you <b>cannot</b> detect first-visit with a "
            "set filled while walking backwards. A backward set tells you the state "
            "appears <i>later</i>, which keeps the LAST visit, not the first. This "
            "code does a forward pass to record each state's first index, then walks "
            "backwards. Get this wrong and FVMC silently becomes 'last-visit MC'.",
            "bad"))

        # ---- runner ------------------------------------------------------------
        ctl = Card("controls")
        self.env = EnvControls(slip="classic", reward="shaped", gamma=0.99)
        self.env.changed.connect(self.reset)
        self.mode = QComboBox(); self.mode.addItems(["First-visit (FVMC)",
                                                     "Every-visit (EVMC)"])
        self.mode.currentIndexChanged.connect(self.reset)
        self.polbox = QComboBox()
        self.polbox.addItems(["π = optimal π*", "π = always DOWN", "π = uniform random"])
        self.polbox.currentIndexChanged.connect(self.reset)
        self.n_ep = QSpinBox(); self.n_ep.setRange(100, 500000); self.n_ep.setValue(30000)
        self.n_ep.setSingleStep(5000)
        ctl.add_layout(labelled("Variant", self.mode, 70))
        ctl.add_layout(labelled("Policy π", self.polbox, 70))
        ctl.add_layout(labelled("Episodes", self.n_ep, 70))
        ctl.add(self.env)
        self.st_ep = Stat("episodes", "0", theme.ACCENT)
        self.st_err = Stat("max |V_MC − V_DP|", "-", theme.WARN)
        self.st_ret = Stat("returns averaged", "0", theme.CYAN)
        ctl.add_layout(stat_row(self.st_ep, self.st_ret))
        ctl.add_layout(stat_row(self.st_err))
        ctl.add_stretch()

        gr = Card("MC estimate vs the exact DP answer")
        row = QHBoxLayout(); row.setSpacing(16)
        c1 = QVBoxLayout()
        l1 = QLabel("V_MC — learned by averaging returns")
        l1.setStyleSheet(f"color:{theme.WARN}; font-size:11px; font-weight:700;"
                         f"background:transparent;")
        self.g_mc = GridView(cell=80); self.g_mc.value_fmt = "{:.3f}"
        self.g_mc.show_policy = False
        c1.addWidget(l1); c1.addWidget(self.g_mc); c1.addStretch(1)
        c2 = QVBoxLayout()
        l2 = QLabel("V_DP — computed exactly from the model (ground truth)")
        l2.setStyleSheet(f"color:{theme.GOOD}; font-size:11px; font-weight:700;"
                         f"background:transparent;")
        self.g_dp = GridView(cell=80); self.g_dp.value_fmt = "{:.3f}"
        self.g_dp.show_policy = False
        c2.addWidget(l2); c2.addWidget(self.g_dp); c2.addStretch(1)
        row.addLayout(c1); row.addLayout(c2); row.addStretch(1)
        gr.add_layout(row)
        self.transport = Transport(interval=60)
        gr.add(self.transport)
        self.transport.step.connect(self.step)
        self.transport.reset.connect(self.reset)
        self.note = body("")
        gr.add(self.note)

        self.row(gr, ctl, stretches=[0, 1])

        self.canvas = MplCanvas(width=10.5, height=3.0, ncols=2)
        self.add(self.canvas)

        cc = Card("the code")
        cp = CodePane(get_source(mc_prediction))
        cp.sizeHintLine(46)
        cc.add(cp)
        cc.add(body(
            (
                "Compare the signature with <code>policy_evaluation(P, pi, ...)</code> on page 67. There it was "
                "<b>P</b>, the model. Here it is <b>env</b>, a simulator. That swap <i>is</i> the model-free / "
                "model-based divide."
            ),
            dim=True))
        self.add(cc)

        self.finish()
        self.reset()

    def _pi(self):
        idx = self.polbox.currentIndex()
        P = self.env.build()
        g = min(self.env.gamma_value(), 0.9999)
        if idx == 0:
            pi, _, _ = policy_iteration(P, gamma=g, theta=1e-12)
            return pi
        if idx == 1:
            return [1] * N_STATES
        return None   # uniform random

    def reset(self):
        self.transport.pause()
        P = self.env.build()
        g = min(self.env.gamma_value(), 0.9999)
        self.pi = self._pi()

        if self.pi is not None:
            self.V_dp = policy_evaluation(P, self.pi, g, 1e-12)
            policy_fn = lambda s: self.pi[s]
        else:
            from rlcore.frozen_lake import q_from_V
            V = [0.0] * N_STATES
            for _ in range(20000):
                Vp = list(V); delta = 0.0
                for s in range(N_STATES):
                    v = sum(q_from_V(P, Vp, s, a, g) for a in range(N_ACTIONS)) / N_ACTIONS
                    delta = max(delta, abs(v - V[s])); V[s] = v
                if delta < 1e-13:
                    break
            self.V_dp = V
            import random
            policy_fn = lambda s: random.randrange(N_ACTIONS)

        self.g_dp.V = self.V_dp
        self.g_dp.policy = self.pi
        self.g_dp.show_policy = self.pi is not None
        self.g_dp.update()

        env = FrozenLake(slip=self.env.slip_key(), reward=self.env.reward_key(),
                         seed=None)
        self.gen = mc_prediction_steps(
            env, policy_fn, gamma=g, episodes=self.n_ep.value(),
            first_visit=(self.mode.currentIndex() == 0), report_every=200)
        self.hist = []
        self.g_mc.V = [0.0] * N_STATES
        self.g_mc.policy = self.pi
        self.g_mc.show_policy = self.pi is not None
        self.g_mc.update()
        self.st_ep.set("0"); self.st_err.set("-"); self.st_ret.set("0")
        self.note.setText("Press Play. Each frame runs 200 episodes.")
        self.draw()

    def step(self):
        try:
            snap = next(self.gen)
        except StopIteration:
            self.transport.pause()
            self.note.setText("Finished all episodes.")
            return
        self.g_mc.V = snap.V
        self.g_mc.update()
        tested = [s for s in range(N_STATES)
                  if snap.visits[s] > 30 and not is_terminal(s)]
        err = max((abs(snap.V[s] - self.V_dp[s]) for s in tested), default=0.0)
        self.hist.append((snap.episode, err, snap.success_rate))
        self.st_ep.set(f"{snap.episode:,}")
        self.st_ret.set(f"{sum(snap.visits):,}")
        self.st_err.set(f"{err:.4f}")
        self.st_err.set_color(theme.GOOD if err < 0.05 else theme.WARN)
        self.note.setText(
            f"{snap.note}   ·   states with >30 visits: {len(tested)}/14   ·   "
            f"episode success rate {snap.success_rate:.1%}")
        self.draw()

    def draw(self):
        self.canvas.clear()
        a0, a1 = self.canvas.axes
        if self.hist:
            xs = [h[0] for h in self.hist]
            a0.plot(xs, [h[1] for h in self.hist], color=theme.WARN, lw=1.7)
            a0.set_xlabel("episodes"); a0.set_ylabel("max |V_MC − V_DP|")
            a0.set_title("MC estimate closing on the exact answer")
            a0.set_ylim(bottom=0)
        else:
            a0.set_title("press Play")

        V_mc = self.g_mc.V or [0.0] * N_STATES
        w = 0.38
        idx = list(range(N_STATES))
        a1.bar([i - w/2 for i in idx], self.V_dp, w, color=theme.GOOD, label="V_DP (exact)")
        a1.bar([i + w/2 for i in idx], V_mc, w, color=theme.WARN, label="V_MC (sampled)")
        a1.axhline(0, color=theme.BORDER, lw=1)
        a1.set_xticks(idx); a1.set_xlabel("state s"); a1.set_ylabel("V^π(s)")
        a1.set_title("per-state comparison")
        self.canvas.legend(a1)
        self.canvas.refresh()

    def on_hide(self):
        self.transport.pause()


# ==========================================================================
# PAGE 18 -- MC control
# ==========================================================================

class MCControlPage(Page):
    TITLE = "MC Control (GPI)"
    SUBTITLE = ("The control problem: no model, no policy given. Learn Q by "
                "sampling, act ε-greedily, repeat.")
    SECTION = "Monte Carlo"
    NOTES = "notes p.5 §4.4"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>Why Q(s,a) and not V(s)?</b> Because acting greedily on V requires "
            "<code>argmax_a Σ_s' P(s'|s,a)[r + γV(s')]</code> — and we do not have "
            "P. Learning Q directly makes the greedy step <code>argmax_a Q(s,a)</code>, "
            "with no transition probabilities anywhere. Your notes: <i>\"we must "
            "shift from judging States to judging Buttons.\"</i>", "good"))

        m = Card("the update")
        m.add(math_label(
            r"Q(S_t, A_t) \;\leftarrow\; Q(S_t, A_t) + \alpha\left[\, G_t - Q(S_t, A_t) \,\right]", 15))
        m.add(body(
            "A constant α (rather than a true running mean 1/N) deliberately "
            "<b>forgets</b> old returns. That matters here: the policy is changing "
            "underneath you, so returns collected 5000 episodes ago were generated "
            "by a different — worse — policy and deserve less weight.", dim=True))
        m.add(body(
            "<b>Where is the improvement step?</b> There isn't a separate one. The "
            "policy <i>is</i> ε-greedy(Q), so the moment Q changes, π changes with "
            "it. Evaluation and improvement are fused — this is GPI at its most "
            "compressed.", dim=True))
        self.add(m)

        # ---- runner --------------------------------------------------------
        ctl = Card("hyperparameters")
        self.env = EnvControls(slip="classic", reward="shaped", gamma=0.99)
        self.env.changed.connect(self.reset)

        self.n_ep = QSpinBox(); self.n_ep.setRange(1000, 500000); self.n_ep.setValue(60000)
        self.n_ep.setSingleStep(10000)
        self.eps0 = QDoubleSpinBox(); self.eps0.setRange(0.0, 1.0); self.eps0.setValue(1.0)
        self.eps0.setSingleStep(0.05); self.eps0.setDecimals(2)
        self.epsmin = QDoubleSpinBox(); self.epsmin.setRange(0.0, 1.0); self.epsmin.setValue(0.05)
        self.epsmin.setSingleStep(0.01); self.epsmin.setDecimals(3)
        self.epsdec = QDoubleSpinBox(); self.epsdec.setRange(0.9, 1.0); self.epsdec.setValue(0.9997)
        self.epsdec.setDecimals(5); self.epsdec.setSingleStep(0.0001)
        self.alpha0 = QDoubleSpinBox(); self.alpha0.setRange(0.001, 1.0); self.alpha0.setValue(0.3)
        self.alpha0.setSingleStep(0.05); self.alpha0.setDecimals(3)
        self.fv = QCheckBox("first-visit (unchecked = every-visit)")
        self.fv.setChecked(True)
        for w in (self.n_ep, self.eps0, self.epsmin, self.epsdec, self.alpha0):
            w.valueChanged.connect(self.reset)
        self.fv.toggled.connect(self.reset)

        ctl.add_layout(labelled("Episodes", self.n_ep, 96))
        ctl.add_layout(labelled("ε start", self.eps0, 96))
        ctl.add_layout(labelled("ε min", self.epsmin, 96))
        ctl.add_layout(labelled("ε decay", self.epsdec, 96))
        ctl.add_layout(labelled("α (step size)", self.alpha0, 96))
        ctl.add(self.fv)
        ctl.add(self.env)

        self.st_ep = Stat("episode", "0", theme.ACCENT)
        self.st_eps = Stat("ε now", "-", theme.VIOLET)
        self.st_sr = Stat("recent success", "-", theme.GOOD)
        self.st_match = Stat("actions matching π*", "-", theme.CYAN)
        ctl.add_layout(stat_row(self.st_ep, self.st_eps))
        ctl.add_layout(stat_row(self.st_sr, self.st_match))
        ctl.add_stretch()

        gr = Card("learned Q vs the optimal policy")
        row = QHBoxLayout(); row.setSpacing(16)
        c1 = QVBoxLayout()
        l1 = QLabel("Q learned by Monte Carlo (no model was used)")
        l1.setStyleSheet(f"color:{theme.WARN}; font-size:11px; font-weight:700;"
                         f"background:transparent;")
        self.g_q = GridView(cell=104)
        self.g_q.show_q = True; self.g_q.show_values = False; self.g_q.show_policy = False
        c1.addWidget(l1); c1.addWidget(self.g_q); c1.addStretch(1)
        c2 = QVBoxLayout()
        l2 = QLabel("π* from value iteration — gold = MC disagrees here")
        l2.setStyleSheet(f"color:{theme.GOOD}; font-size:11px; font-weight:700;"
                         f"background:transparent;")
        self.g_star = GridView(cell=84); self.g_star.value_fmt = "{:.3f}"
        c2.addWidget(l2); c2.addWidget(self.g_star); c2.addStretch(1)
        row.addLayout(c1); row.addLayout(c2); row.addStretch(1)
        gr.add_layout(row)
        self.transport = Transport(interval=50)
        gr.add(self.transport)
        self.transport.step.connect(self.step)
        self.transport.reset.connect(self.reset)
        self.note = body("")
        gr.add(self.note)

        self.row(gr, ctl, stretches=[0, 1])

        self.canvas = MplCanvas(width=10.5, height=3.0, ncols=2)
        self.add(self.canvas)

        self.add(callout(
            "<b>Try this.</b> Set the reward scheme to <i>Gymnasium (sparse)</i> and "
            "watch learning stall — with +1 only at the goal, almost every early "
            "episode returns G = 0 and there is nothing to learn from until a random "
            "walk stumbles into the goal. Then switch back to <i>shaped</i>: the "
            "−0.04 step cost and −1 hole penalty give a gradient from episode one. "
            "This is reward shaping, and it is the difference between hours and "
            "seconds.", "warn"))

        self.add(callout(
            "<b>The known limitation of MC</b>, and the reason TD exists: you must "
            "wait for the <b>entire episode to finish</b> before you can update "
            "anything, because G<sub>t</sub> is not known until the terminal state. "
            "For a continuing task — no terminal state ever — Monte Carlo simply "
            "does not apply. TD learning fixes this by bootstrapping off the next "
            "state's estimate after a single step.", "key"))

        cc = Card("the code")
        cp = CodePane(get_source(mc_control))
        cp.sizeHintLine(58)
        cc.add(cp)
        self.add(cc)

        cc2 = Card("ε-greedy action selection")
        cp2 = CodePane(get_source(epsilon_greedy))
        cp2.sizeHintLine(16)
        cc2.add(cp2)
        cc2.add(body(
            "The random tie-break matters more than it looks. Q starts all-zero, so "
            "without it <code>max</code> would always return action 0 and three "
            "quarters of the grid would never be tried.", dim=True))
        self.add(cc2)

        self.finish()
        self.reset()

    def reset(self):
        self.transport.pause()
        P = self.env.build()
        g = min(self.env.gamma_value(), 0.9999)
        self.pi_star, self.V_star, _ = value_iteration(P, gamma=g, theta=1e-12)
        self.g_star.V = self.V_star
        self.g_star.policy = self.pi_star
        self.g_star.highlight = set()
        self.g_star.update()
        self.Q_star = None

        env = FrozenLake(slip=self.env.slip_key(), reward=self.env.reward_key(),
                         seed=None)
        self.gen = mc_control_steps(
            env, gamma=g, episodes=self.n_ep.value(),
            eps_start=self.eps0.value(), eps_min=self.epsmin.value(),
            eps_decay=self.epsdec.value(),
            alpha_start=self.alpha0.value(), alpha_min=self.alpha0.value(),
            alpha_decay=1.0,
            first_visit=self.fv.isChecked(), seed=None, report_every=250)
        self.hist = []
        self.g_q.Q = [[0.0] * N_ACTIONS for _ in range(N_STATES)]
        self.g_q.update()
        self.st_ep.set("0"); self.st_eps.set("-")
        self.st_sr.set("-"); self.st_match.set("-")
        self.note.setText("Press Play. Each frame runs 250 episodes.")
        self.draw()

    def step(self):
        try:
            snap = next(self.gen)
        except StopIteration:
            self.transport.pause()
            self.note.setText("Finished all episodes.")
            return
        self.g_q.Q = snap.Q
        self.g_q.update()

        P = self.env.build()
        g = min(self.env.gamma_value(), 0.9999)
        disagree = [s for s in range(N_STATES)
                    if not is_terminal(s) and snap.policy[s] != self.pi_star[s]]
        self.g_star.highlight = set(disagree)
        self.g_star.update()

        n_nonterm = sum(1 for s in range(N_STATES) if not is_terminal(s))
        match = n_nonterm - len(disagree)
        V_learned = policy_evaluation(P, snap.policy, g, 1e-12)

        self.hist.append((snap.episode, snap.success_rate, snap.epsilon,
                          V_learned[0], match))
        self.st_ep.set(f"{snap.episode:,}")
        self.st_eps.set(f"{snap.epsilon:.3f}")
        self.st_sr.set(f"{snap.success_rate:.1%}")
        self.st_match.set(f"{match}/{n_nonterm}")
        self.st_match.set_color(theme.GOOD if match >= n_nonterm - 1 else theme.WARN)
        self.note.setText(
            f"{snap.note}   ·   V(start) under the LEARNED policy = "
            f"{V_learned[0]:+.4f}   vs   optimal {self.V_star[0]:+.4f}")
        self.draw()

    def draw(self):
        self.canvas.clear()
        a0, a1 = self.canvas.axes
        if self.hist:
            xs = [h[0] for h in self.hist]
            a0.plot(xs, [h[1] * 100 for h in self.hist], color=theme.GOOD, lw=1.7,
                    label="success rate (last 200 eps)")
            a0.set_ylabel("success %", color=theme.GOOD)
            ax2 = a0.twinx()
            ax2.plot(xs, [h[2] for h in self.hist], color=theme.VIOLET, lw=1.4, ls="--")
            ax2.set_ylabel("ε", color=theme.VIOLET, fontsize=9)
            ax2.tick_params(colors=theme.TEXT_DIM, labelsize=8)
            ax2.grid(False)
            a0.set_xlabel("episode")
            a0.set_title("learning curve — success rises as ε decays")

            a1.plot(xs, [h[3] for h in self.hist], color=theme.WARN, lw=1.7,
                    label="V(start) of learned π")
            a1.axhline(self.V_star[0], color=theme.GOOD, ls="--", lw=1.5,
                       label="V*(start) — the ceiling")
            a1.set_xlabel("episode"); a1.set_ylabel("V(start)")
            a1.set_title("how close the learned policy is to optimal")
            self.canvas.legend(a1, loc="lower right")
        else:
            a0.set_title("press Play"); a1.set_title("")
        self.canvas.refresh()

    def on_hide(self):
        self.transport.pause()
