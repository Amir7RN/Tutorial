"""
Pages 73-78: deep RL for continuous control, ending at a real deployment.

  73  Tables Run Out       why a Q-table cannot survive continuous states, and
                           why DQN cannot survive continuous ACTIONS
  74  Actor-Critic         the critic evaluates, the actor moves; deterministic
                           mu(s) versus stochastic pi(a|s)
  75  DDPG                 four networks and three equations, one at a time
  76  Still an MDP?        the Markov property does not care how you chose the
                           action -- and what separates DDPG from TD3/SAC/PPO
  77  Case Study           tuning a robotic knee prosthesis: one gait cycle is
                           one timestep
  78  Shipping It          the 1 kHz controller and the 20 Hz learner, and the
                           shared memory between them

The through-line of this block is a single sentence, and it is the same
sentence as the controller-design block, transposed:

    You cannot enumerate a continuous action, so you have to train something
    to hand you the best one.

Everything below -- function approximation, the actor, the deterministic
policy gradient, the target networks -- is a consequence of that.
"""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QPushButton

from rlcore.deeprl import (
    ALGO_TABLE,
    ContextualReach,
    DDPG,
    DDPGConfig,
    GaitTuneEnv,
    MLP,
    ReplayBuffer,
    rollout_gait,
    train_gait,
    train_reach,
)
from .. import theme
from ..widgets import (
    BlockDiagram,
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
from .motors import slider, slider_row

SECTION = "Deep RL & Continuous Control"


def _table(headers, rows, col0=150, colw=250, height=None):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QTableWidget, QTableWidgetItem
    t = QTableWidget(len(rows), len(headers))
    t.setHorizontalHeaderLabels(headers)
    for r, cells in enumerate(rows):
        for c, v in enumerate(cells):
            it = QTableWidgetItem(v)
            it.setFlags(Qt.ItemIsEnabled)
            t.setItem(r, c, it)
    t.verticalHeader().setVisible(False)
    t.setWordWrap(True)
    t.resizeRowsToContents()
    t.setColumnWidth(0, col0)
    for c in range(1, len(headers)):
        t.setColumnWidth(c, colw)
    t.setMinimumHeight(height or (44 + 64 * len(rows)))
    return t


# ==========================================================================
# PAGE -- tables run out
# ==========================================================================

class FunctionApproxPage(Page):
    TITLE = "Tables Run Out"
    SUBTITLE = ("A Q-table needs a cell per state-action pair. Count the cells "
                "for a real robot and the whole tabular half of this tutor "
                "stops applying.")
    SECTION = SECTION
    NOTES = "deep RL"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>Everything up to here assumed you could write the answer "
            "down.</b> Frozen Lake has 16 states and 4 actions, so Q is a "
            "16×4 array and \"learning\" means filling in 64 numbers. That is "
            "not a simplification of real RL — it is a different regime. The "
            "moment either axis goes continuous, the table stops existing and "
            "three things have to be replaced at once: how Q is stored, how it "
            "is updated, and how the best action is found.", "key"))

        # ---- the count -------------------------------------------------
        cnt = Card("count the cells, then stop arguing about it")
        cnt.add(body(
            "Discretising is the obvious first idea and it is worth doing the "
            "arithmetic before adopting it. Take the prosthesis problem from "
            "the case study two pages on: <b>five continuous state variables</b> "
            "(four joint-angle landmark errors and a phase lag) and <b>two "
            "continuous actions</b> (increments to two impedance weights)."))
        cnt.add(math_label(r"\text{cells} \;=\; B_s^{\,d_s} \times B_a^{\,d_a}",
                           17))
        cnt.add(body(
            "At a coarse 20 bins per state dimension and 9 per action, that is "
            "20⁵ × 9² = <b>259 million cells</b>. Every one of them needs to be "
            "visited several times before its average means anything, and a "
            "gait cycle takes about a second. The visit budget alone is "
            "measured in <b>centuries of walking</b>.<br><br>"
            "And the fatal part is not the size. It is that the table "
            "<b>generalises nothing</b>. Cell (12, 7, 3, 9, 4) learns nothing "
            "from its neighbour (12, 7, 3, 9, 5), even though the two describe "
            "gait cycles a human could not tell apart. A table is a lookup "
            "structure; it has no notion that nearby states are similar."))
        self.s_bins = slider(3, 40, 20)
        self.s_dims = slider(1, 8, 5)
        self.s_abins = slider(2, 20, 9)
        self.l_bins, self.l_dims, self.l_abins = QLabel(), QLabel(), QLabel()
        cnt.add_layout(slider_row("bins per state dim", self.s_bins,
                                  self.l_bins))
        cnt.add_layout(slider_row("state dimensions", self.s_dims, self.l_dims))
        cnt.add_layout(slider_row("bins per action dim", self.s_abins,
                                  self.l_abins))
        self.st_cells = Stat("cells in the table", "--", theme.BAD)
        self.st_visits = Stat("visits needed (10 each)", "--", theme.WARN)
        self.st_years = Stat("at 1 s per gait cycle", "--", theme.BAD)
        self.st_net = Stat("a small network instead", "--", theme.GOOD)
        cnt.add_layout(stat_row(self.st_cells, self.st_visits, self.st_years,
                                self.st_net))
        self.cA = MplCanvas(width=7.6, height=2.7, ncols=2)
        cnt.add(self.cA)
        self.tA = body("", dim=True)
        cnt.add(self.tA)
        self.add(cnt)
        for s in (self.s_bins, self.s_dims, self.s_abins):
            s.valueChanged.connect(self._redraw_count)
        self._redraw_count()

        # ---- function approximation ------------------------------------
        fa = Card("so store a function instead of a table")
        fa.add(body(
            "Replace the array Q[s][a] with a parameterised function "
            "Q(s, a; w) — a network with a few thousand weights that takes the "
            "state and the action as <i>numbers</i> and returns a value. Three "
            "things change, and only one of them is the obvious one:"))
        fa.add(body(
            "&nbsp;&nbsp;• <b>Storage</b> goes from 259 million floats to "
            "about 5000. That is the obvious one, and the least "
            "important.<br>"
            "&nbsp;&nbsp;• <b>Generalisation</b> arrives for free. A smooth "
            "function that fits the visited states necessarily says something "
            "about the ones in between. <b>This is the real reason for "
            "networks in RL</b> — not compression, interpolation.<br>"
            "&nbsp;&nbsp;• <b>The update stops being an assignment.</b> In DP "
            "you wrote V(s) ← max Q(s,a); you cannot assign to a network. You "
            "can only take a gradient step, which turns the Bellman equation "
            "into a <b>regression problem</b>: build a target y, and minimise "
            "(Q(s,a;w) − y)². The Adam page's last paragraph was this "
            "sentence in advance."))
        fa.add(callout(
            "<b>And the price: none of the tabular theorems survive.</b> "
            "Tabular Q-learning converges to Q* with probability 1, given "
            "enough visits. Put a function approximator in and you have the "
            "<i>deadly triad</i> — function approximation, bootstrapping (the "
            "target contains your own estimate) and off-policy data — for "
            "which there is <b>no convergence guarantee at all</b>, and there "
            "are known simple counterexamples that diverge. Every stabiliser "
            "in DQN and DDPG (replay buffers, target networks, small learning "
            "rates, gradient clipping) is engineering against that fact. This "
            "is what the Convergence page meant by \"tabular convergence is a "
            "theorem, deep-RL convergence is a hope\".", "warn"))
        self.add(fa)

        # ---- the argmax wall -------------------------------------------
        self.add(hline())
        self.add(title("The wall DQN hits, and the hole DDPG was invented to "
                       "fill"))

        aw = Card("max over actions is free in a table and impossible off it")
        aw.add(body(
            "Look at where the action enters every value-based method:"))
        aw.add(math_label(r"y \;=\; r + \gamma \max_{a'} Q(s', a'), "
                          r"\qquad \pi(s) = \arg\max_a Q(s,a)", 17))
        aw.add(body(
            "In Frozen Lake, <b>max</b> and <b>argmax</b> mean \"look at four "
            "numbers and take the biggest\". DQN keeps that structure exactly: "
            "the network outputs one value per action, so the max is still a "
            "scan over a fixed list — which is why DQN plays Atari, where "
            "there are 18 buttons, and does not drive a joint, where there are "
            "not.<br><br>"
            "For a continuous action, that max is <b>an optimisation problem "
            "in its own right</b>, and you would have to solve it twice per "
            "sample: once to build the target, and once every time the "
            "controller wants to act. In a 1 kHz loop that is not a cost "
            "problem, it is an impossibility."))
        aw.add(callout(
            "<b>DDPG's whole idea, in one line: train a second network to "
            "output the argmax.</b><br><br>"
            "Instead of searching for max<sub>a</sub> Q(s,a) at runtime, keep "
            "a network μ(s) whose job is to <i>already be</i> at the maximum, "
            "and train it by pushing it uphill on the critic's own surface. "
            "That is the actor. The max never gets computed — it gets "
            "<b>amortised into weights</b>, and evaluating it becomes one "
            "forward pass with a bounded, deterministic execution time. Which, "
            "for anyone who read page 1, is the only kind of computation you "
            "are allowed to put in a control loop.", "key"))
        aw.add(body(
            "Read that against the four algorithm families you already know: "
            "DP needs the model; MC needs episodes to end; TD needs a max over "
            "actions; and DDPG needs none of the three. What it needs instead "
            "is a critic that is differentiable with respect to the action — "
            "and that is a property you get for free the moment Q is a "
            "network rather than a table.", dim=True))
        self.add(aw)

        self.add(callout(
            "<b>Carry forward.</b> Continuous states kill the table and force "
            "function approximation, which costs you every convergence "
            "theorem. Continuous actions kill the argmax and force an actor. "
            "The next two pages build that actor and the critic that trains "
            "it.", "good"))
        self.finish()

    # ------------------------------------------------------------------
    def _redraw_count(self):
        b = self.s_bins.value()
        d = self.s_dims.value()
        ba = self.s_abins.value()
        self.l_bins.setText(f"{b}")
        self.l_dims.setText(f"{d}")
        self.l_abins.setText(f"{ba}")

        cells = (b ** d) * (ba ** 2)
        visits = cells * 10
        years = visits / (3600.0 * 24 * 365)
        self.st_cells.set(f"{cells:.3g}")
        self.st_visits.set(f"{visits:.3g}")
        self.st_years.set("< 1 day" if years < 1 / 365 else f"{years:.3g} yr")
        self.st_years.set_color(theme.GOOD if years < 0.05 else theme.BAD)
        self.st_net.set("~5 000 weights")

        if years < 0.05:
            self.tA.setText(
                f"<b>At this resolution a table is still viable</b> — "
                f"{cells:.3g} cells is a few days of data. Notice how few "
                "dimensions that took. Drag the state dimensions up one at a "
                "time and watch the exponent do its work: this is the curse of "
                "dimensionality, and it is not a slogan, it is the shape of "
                "b<sup>d</sup>.")
        else:
            self.tA.setText(
                f"<b>{cells:.3g} cells, {years:.3g} years of walking to fill "
                f"them ten deep.</b> And the table would still generalise "
                f"nothing: every one of those cells has to be visited on its "
                f"own merits. A network with a few thousand weights fits the "
                f"same function because it is <i>smooth</i> — the samples you "
                "did collect constrain the ones you did not.")

        c = self.cA
        c.clear()
        a1, a2 = c.axes
        ds = list(range(1, 9))
        a1.semilogy(ds, [(b ** k) * (ba ** 2) for k in ds], color=theme.BAD,
                    lw=2.2, marker="o", ms=3, label="table cells")
        a1.axhline(5000, color=theme.GOOD, lw=1.4, ls="--",
                   label="network weights")
        a1.scatter([d], [cells], s=55, color=theme.ACCENT, zorder=5)
        a1.set_xlabel("state dimensions")
        a1.set_ylabel("numbers to store")
        a1.set_title("b^d, and a flat line", fontsize=9)
        c.legend(a1, loc="upper left")

        # a table's staircase versus the true curve, on one 1-D slice
        xs = np.linspace(-1.0, 1.0, 400)
        true = -np.abs(xs - 0.35) + 0.5 * np.sin(3.0 * xs)
        edges = np.linspace(-1.0, 1.0, max(2, b) + 1)
        centres = 0.5 * (edges[:-1] + edges[1:])
        vals = -np.abs(centres - 0.35) + 0.5 * np.sin(3.0 * centres)
        idx = np.clip(np.digitize(xs, edges) - 1, 0, len(vals) - 1)
        a2.plot(xs, true, color=theme.GOOD, lw=2.0, label="true Q(s, a fixed)")
        a2.step(xs, vals[idx], where="mid", color=theme.WARN, lw=1.6,
                label=f"table, {b} bins")
        a2.set_xlabel("one continuous state variable")
        a2.set_ylabel("value")
        a2.set_title("a table is a staircase", fontsize=9)
        c.legend(a2, loc="lower right")
        c.refresh()


# ==========================================================================
# PAGE -- actor-critic
# ==========================================================================

class ActorCriticPage(Page):
    TITLE = "Actor-Critic"
    SUBTITLE = ("One network says how good things are; the other says what to "
                "do about it. And the choice that splits the whole family: is "
                "the actor a distribution, or a number?")
    SECTION = SECTION
    NOTES = "deep RL"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>This is generalised policy iteration again, with both halves "
            "replaced by networks.</b> Policy evaluation becomes the "
            "<b>critic</b>: a network trained to predict value. Policy "
            "improvement becomes the <b>actor</b>: a network trained to output "
            "actions the critic scores highly. The two chase each other "
            "exactly as they did in the DP pages — evaluate, improve, "
            "evaluate the improved thing — except that neither step is exact "
            "any more, so neither ever finishes.", "key"))

        wv = Card("why the actor cannot just read V(s)")
        wv.add(body(
            "The Model-Based page made this point tabularly and it is worth "
            "restating in network form, because it is the reason the critic "
            "usually learns Q and not V.<br><br>"
            "V(s) tells the agent <b>it is in a bad state</b>. It does not "
            "tell it which way is out. To convert V into an action you need "
            "to look at V(s') for every reachable s' and weight by "
            "P(s'|s,a) — and P is exactly the thing a model-free agent does "
            "not have.<br><br>"
            "Q(s,a) sidesteps that entirely: it attaches the value to the "
            "<b>button</b> rather than to the destination, so choosing needs "
            "no model. That is why DDPG's critic is Q(s,a) and why its actor "
            "can be trained by differentiating <i>through</i> the critic with "
            "respect to a."))
        wv.add(math_label(r"V^\pi(s) \;=\; \sum_a \pi(a|s)\, Q^\pi(s,a)"
                          r"\qquad\text{---}\qquad "
                          r"V \text{ is the policy-weighted average of } Q", 16))
        wv.add(body(
            "Read that both ways. Left to right, V is a summary of Q and "
            "throws away exactly the information the actor needs. Right to "
            "left, if you only have V you cannot recover Q without the "
            "transition probabilities. PPO gets away with a V-critic because "
            "it uses V only to compute an <i>advantage</i> for actions it "
            "already sampled — it never needs to ask \"what would this other "
            "action have been worth?\", which is the question DDPG's actor "
            "asks on every single update.", dim=True))
        self.add(wv)

        # ---- deterministic vs stochastic ---------------------------------
        self.add(hline())
        self.add(title("Deterministic μ(s) versus stochastic π(a|s) — the "
                       "split that names the algorithms"))

        ds = Card("the actor outputs a number, or the actor outputs a "
                  "distribution")
        ds.add(body(
            "<b>Stochastic actor.</b> The network outputs the parameters of a "
            "distribution over actions — for a continuous action, typically a "
            "mean and a standard deviation — and the action is <b>sampled</b> "
            "from it. Written π(a|s). Exploration is built in: the policy is "
            "random, so it tries things. Two consequences follow. It is "
            "naturally <b>on-policy</b> (the data was generated by the "
            "distribution you are about to update, and once you update it the "
            "data is stale), and its gradient must be estimated by the "
            "likelihood-ratio trick, which is noisy."))
        ds.add(math_label(r"\pi_\theta(a|s) = \mathcal{N}\!\big(\mu_\theta(s),\,"
                          r"\sigma_\theta(s)\big) \qquad a \sim \pi_\theta(a|s)",
                          16))
        ds.add(body(
            "<b>Deterministic actor.</b> The network outputs <b>the action "
            "itself</b>. Written μ(s) = a. Given the same state it returns the "
            "same 15.5 N·m forever. There is no sampling and no distribution, "
            "so exploration is not automatic — it has to be <b>added from "
            "outside</b>, usually as Gaussian noise on the output during "
            "training only. In exchange the gradient is not estimated, it is "
            "<b>computed</b>: you differentiate the critic with respect to the "
            "action and push."))
        ds.add(math_label(r"a = \mu_\theta(s) \qquad "
                          r"a_{\text{explore}} = \mu_\theta(s) + "
                          r"\mathcal{N}(0, \sigma)", 16))
        ds.add(callout(
            "<b>Why continuous control tends to pick the deterministic one.</b> "
            "A joint torque is one number. Representing a whole probability "
            "density over torques, sampling from it, and then estimating a "
            "gradient through the sampling operation is a great deal of "
            "machinery to arrive at a number you were going to send to a "
            "current loop anyway. The deterministic policy gradient computes "
            "the same improvement direction analytically and with far lower "
            "variance — which, on a robot where every sample costs a real "
            "stride, is the difference between a method you can run on a "
            "person and one you cannot.<br><br>"
            "The cost is real and it is exploration. A deterministic policy "
            "will happily converge to a mediocre action and never discover a "
            "better one, because it never tries anything else. <b>Everything "
            "that is hard about tuning DDPG is downstream of that one "
            "sentence.</b>", "key"))
        self.add(ds)

        ie = Card("see the difference: a distribution versus a spike plus "
                  "noise")
        ie.add(body(
            "Both actors below have the same <i>mean</i> action. What differs "
            "is where the randomness lives and whether it survives "
            "deployment.<br><br>"
            "<b>Left:</b> the stochastic actor's π(a|s) — the spread is a "
            "learned output of the network, it is part of the policy, and it "
            "is what gets differentiated. <b>Right:</b> the deterministic "
            "actor — a spike at μ(s), with an exploration distribution bolted "
            "on beside it that exists only during training. Set the "
            "exploration noise to zero and watch the right-hand policy stop "
            "exploring completely while the left-hand one carries on, which is "
            "the entire practical difference between the two families.",
            dim=True))
        self.s_mu = slider(-80, 80, 30)          # x0.01
        self.s_sig_pi = slider(1, 80, 30)        # x0.01, learned spread
        self.s_sig_n = slider(0, 80, 20)         # x0.01, injected noise
        self.l_mu, self.l_sig_pi, self.l_sig_n = QLabel(), QLabel(), QLabel()
        ie.add_layout(slider_row("mean action μ(s)", self.s_mu, self.l_mu))
        ie.add_layout(slider_row("π's learned σ", self.s_sig_pi,
                                 self.l_sig_pi))
        ie.add_layout(slider_row("injected noise σ", self.s_sig_n,
                                 self.l_sig_n))
        self.st_ent = Stat("π entropy", "--", theme.VIOLET)
        self.st_expl = Stat("μ explores?", "--", theme.WARN)
        self.st_dep = Stat("at deployment", "--", theme.GOOD)
        ie.add_layout(stat_row(self.st_ent, self.st_expl, self.st_dep))
        self.cB = MplCanvas(width=7.6, height=2.7, ncols=2)
        ie.add(self.cB)
        self.tB = body("", dim=True)
        ie.add(self.tB)
        self.add(ie)
        for s in (self.s_mu, self.s_sig_pi, self.s_sig_n):
            s.valueChanged.connect(self._redraw_dist)
        self._redraw_dist()

        fam = Card("who is in which family")
        fam.add(_table(
            ["Algorithm", "Actor", "Critic learns", "Data"],
            [(r[0], r[1], r[3], r[4]) for r in ALGO_TABLE],
            col0=110, colw=200, height=300))
        fam.add(body(
            "Note the pattern in the last column. <b>Deterministic actor and "
            "Q-critic go together with off-policy replay</b>; stochastic actor "
            "and V-critic go together with on-policy batches. That is not a "
            "coincidence — a Q-critic can score an action nobody is currently "
            "taking, which is precisely what makes replaying an old "
            "transition legitimate.", dim=True))
        self.add(fam)

        self.add(callout(
            "<b>Carry forward.</b> Critic answers \"how good\"; actor answers "
            "\"what to do\". A deterministic actor gives you an analytic "
            "gradient and off-policy replay, and takes away your exploration. "
            "The next page assembles exactly that into DDPG.", "good"))
        self.finish()

    # ------------------------------------------------------------------
    def _redraw_dist(self):
        mu = self.s_mu.value() / 100.0
        sig = max(1e-3, self.s_sig_pi.value() / 100.0)
        sn = self.s_sig_n.value() / 100.0
        self.l_mu.setText(f"{mu:+.2f}")
        self.l_sig_pi.setText(f"{sig:.2f}")
        self.l_sig_n.setText(f"{sn:.2f}")

        ent = 0.5 * math.log(2 * math.pi * math.e * sig * sig)
        self.st_ent.set(f"{ent:+.2f} nats")
        self.st_expl.set("no" if sn <= 1e-6 else f"only via σ={sn:.2f}")
        self.st_expl.set_color(theme.BAD if sn <= 1e-6 else theme.WARN)
        self.st_dep.set("π still random  /  μ exact")

        if sn <= 1e-6:
            self.tB.setText(
                "<b>Noise at zero: the deterministic actor has stopped "
                "exploring entirely.</b> It is a single spike, and it will "
                "return that same action for this state for the rest of "
                "training no matter how bad it is. The stochastic policy on "
                "the left is still sampling, because its randomness is part "
                "of the policy rather than bolted onto it. This is the failure "
                "mode you get when DDPG's noise schedule decays too fast: "
                "learning simply stops, quietly, with no error anywhere.")
        else:
            self.tB.setText(
                f"<b>Both are exploring, for structurally different "
                f"reasons.</b> π's spread (σ = {sig:.2f}) is a network output "
                f"— it is learned, it appears in the gradient, and SAC even "
                f"pays it a bonus to stay wide. μ's spread (σ = {sn:.2f}) is a "
                f"random number added after the network, invisible to the "
                f"gradient, and switched off the moment you deploy. At "
                f"deployment the deterministic controller emits exactly "
                f"μ(s) = {mu:+.2f} every time, which is what a joint controller "
                "should do and what a sampled policy cannot promise.")

        c = self.cB
        c.clear()
        a1, a2 = c.axes
        xs = np.linspace(-1.2, 1.2, 400)

        def gauss(x, m, s):
            return np.exp(-0.5 * ((x - m) / s) ** 2) / (s * math.sqrt(2 * math.pi))

        a1.plot(xs, gauss(xs, mu, sig), color=theme.VIOLET, lw=2.2)
        a1.fill_between(xs, gauss(xs, mu, sig), color=theme.VIOLET, alpha=0.18)
        a1.axvline(mu, color=theme.TEXT_FAINT, lw=1.1, ls="--")
        a1.set_xlabel("action")
        a1.set_ylabel("π(a|s)")
        a1.set_title("stochastic: the policy IS the spread", fontsize=9)

        top = float(gauss(xs, mu, max(sig, 1e-3)).max())
        if sn > 1e-6:
            noise = gauss(xs, mu, sn)
            top = max(top, float(noise.max()))
        a2.vlines([mu], 0, top, color=theme.GOOD, lw=3.0, label="μ(s)")
        if sn > 1e-6:
            a2.plot(xs, noise, color=theme.WARN, lw=1.8, ls="--",
                    label="+ exploration noise")
            a2.fill_between(xs, noise, color=theme.WARN, alpha=0.12)
        a2.set_xlabel("action")
        a2.set_ylabel("density")
        a2.set_ylim(0, top * 1.45)
        a2.set_title("deterministic: a number, plus a crutch", fontsize=9)
        c.legend(a2, loc="upper right")
        c.refresh()


# ==========================================================================
# PAGE -- DDPG itself
# ==========================================================================

class DDPGPage(Page):
    TITLE = "DDPG, One Piece at a Time"
    SUBTITLE = ("Four networks, three equations, and one honest admission: "
                "there is no ground truth anywhere, so we manufacture one.")
    SECTION = SECTION
    NOTES = "deep RL"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>Deep Deterministic Policy Gradient</b> is Q-learning with the "
            "argmax replaced by a network, plus the two stabilisers DQN "
            "introduced. Every one of its four networks exists for a reason "
            "you can state in one sentence, and if you can state all four you "
            "understand the algorithm.", "key"))

        four = Card("the four networks, and why each one exists")
        self.d_ddpg = BlockDiagram(width=7.6, height=2.6, ylim=(0, 2.6))
        four.add(self.d_ddpg)
        four.add(_table(
            ["Network", "Signature", "Exists because"],
            [("actor  μ", "s → a",
              "the argmax over a continuous action cannot be computed at "
              "runtime, so it is amortised into weights"),
             ("critic  Q", "(s, a) → value",
              "the actor needs a differentiable surface to climb; a table "
              "cannot be differentiated with respect to a"),
             ("target actor  μ′", "s′ → a′",
              "to ask 'what would we do next?' with a policy that is NOT "
              "moving while we fit to it"),
             ("target critic  Q′", "(s′, a′) → value",
              "the critic is regressed onto a target built from itself; "
              "freezing a slow copy stops the pair running away together")],
            col0=130, colw=330, height=270))
        self.add(four)

        # ---- the three equations ---------------------------------------
        eq = Card("the three equations, in the order the code runs them")
        eq.add(body("<b>1 · Manufacture a target.</b> This is the step that "
                    "answers \"where is the ground truth?\"."))
        eq.add(math_label(r"y \;=\; r \;+\; \gamma\,(1-d)\;"
                          r"Q'\big(s',\, \mu'(s')\big)", 18))
        eq.add(callout(
            "<b>There is no label anywhere in reinforcement learning.</b> In "
            "supervised learning a human wrote \"cat\" next to the picture. "
            "Here nobody knows what Q(s,a) should be — that is the whole "
            "problem. So we build a stand-in out of one real number and one "
            "guess:<br><br>"
            "&nbsp;&nbsp;• <b>r</b> — the reward that <i>actually happened</i>. "
            "This is the only fact in the equation, and it is why the method "
            "works at all: every target is anchored to at least one real "
            "measurement.<br>"
            "&nbsp;&nbsp;• <b>γQ′(s′, μ′(s′))</b> — the target networks' "
            "current opinion about everything after that. A guess.<br><br>"
            "We then treat y as though it were handed down, and regress the "
            "critic onto it. Each update the guess is one real reward less "
            "wrong than it was, and that slow leaking of real rewards backward "
            "through time <b>is</b> the learning. It is the Bellman equation "
            "from page 54, enforced by gradient descent instead of by "
            "assignment.", "key"))
        eq.add(body("<b>2 · Fit the critic.</b> Ordinary least squares, once "
                    "y exists."))
        eq.add(math_label(r"L(w) \;=\; \frac{1}{N}\sum_i "
                          r"\big(Q(s_i,a_i;w) - y_i\big)^2", 17))
        eq.add(body("<b>3 · Push the actor uphill.</b> This is the one that is "
                    "specific to DDPG, and it is a chain rule across two "
                    "networks."))
        eq.add(math_label(r"\nabla_\theta J \;=\; \mathbb{E}\Big[\;"
                          r"\underbrace{\nabla_a Q(s,a)\big|_{a=\mu(s)}}"
                          r"_{\text{from the critic}}\;\cdot\;"
                          r"\underbrace{\nabla_\theta \mu(s)}"
                          r"_{\text{from the actor}}\;\Big]", 17))
        eq.add(body(
            "Read the two factors. The <b>critic</b> is asked a question it is "
            "uniquely able to answer: <i>at the action we are currently "
            "taking, which direction in action-space increases value?</i> That "
            "is ∂Q/∂a, and getting it costs one backward pass through the "
            "critic — not to its weights, but all the way through to its "
            "<b>input</b>. The <b>actor</b> then answers: <i>how do I change "
            "my weights to move the output that way?</i> Multiply, and you "
            "have a weight update that provably increases Q.<br><br>"
            "It is gradient <b>ascent</b>, which is why the implementation "
            "negates the term before handing it to a descent optimiser. And "
            "notice what never happens: no action is ever enumerated, "
            "compared, or maximised over. The actor is dragged toward the "
            "maximum a small step at a time, forever.", dim=True))
        eq.add(body(
            "In the code, that entire paragraph is four lines — and the third "
            "one, the slice, is the whole trick:"))
        pane = CodePane(
            "a_pi = self.actor.forward(s) * c.a_max\n"
            "q_pi = self.critic.forward(np.concatenate([s, a_pi], axis=1))\n"
            "dx   = self.critic.backward(np.ones((c.batch, 1)) / c.batch)\n"
            "dq_da = dx[:, c.dim_s:]          # <- gradient w.r.t. the ACTION\n"
            "self.actor.backward(-dq_da * c.a_max)   # minus = ascent\n"
            "self.actor.adam(c.lr_actor)")
        pane.sizeHintLine(7)
        pane.mark(3, "#6b4e13")
        eq.add(pane)
        eq.add(body("<b>4 · Let the targets drift after the live networks.</b> "
                    "Not a copy every N steps — a continuous crawl.", dim=True))
        eq.add(math_label(r"\theta' \leftarrow \tau\,\theta + (1-\tau)\,\theta'"
                          r"\qquad \tau \approx 0.001 - 0.01", 17))
        eq.add(body(
            "τ = 0.01 means the target is roughly a 100-step moving average of "
            "the live network. Small τ is stable and slow; large τ is fast and "
            "risks the divergence the targets were introduced to prevent. "
            "τ = 1 removes the target networks entirely, which is the ablation "
            "in the second experiment below.", dim=True))
        self.add(eq)

        rb = Card("the replay buffer, and why 'off-policy' is the load-bearing "
                  "word")
        rb.add(body(
            "A transition (s, a, r, s′) is a <b>fact about the environment</b>: "
            "from there, that action paid that much and led here. That fact "
            "does not expire when the policy changes. So DDPG stores every "
            "transition it has ever seen and trains on uniform samples from "
            "the whole history.<br><br>"
            "Two separate benefits, and people usually only name the "
            "first:<br>"
            "&nbsp;&nbsp;• <b>Decorrelation.</b> Consecutive steps look almost "
            "identical, and a gradient method fed correlated samples is "
            "effectively taking one very large step in one direction. "
            "Uniform sampling from a big buffer breaks that.<br>"
            "&nbsp;&nbsp;• <b>Sample reuse.</b> Each real interaction is used "
            "hundreds of times. On a robot where a sample is a stride taken by "
            "an actual person, this is not an optimisation — it is the "
            "difference between a feasible experiment and an impossible one. "
            "PPO, being on-policy, throws its batch away after one update; "
            "that is why it is the algorithm of simulators."))
        rb.add(callout(
            "<b>And this is exactly what the deterministic actor bought "
            "you.</b> Replay is only legitimate because the critic is Q(s,a) — "
            "it can score an action that the current policy would never "
            "choose, so a transition generated by an old policy is still a "
            "valid training point. A V-critic cannot do that, which is why the "
            "stochastic/V-critic family is stuck on-policy. The three choices "
            "— deterministic actor, Q-critic, replay buffer — are one "
            "decision wearing three hats.", "key"))
        self.add(rb)

        # ---- interactive 1: the microscope ------------------------------
        self.add(hline())
        self.add(title("Watch the critic learn a surface, and the actor climb "
                       "it"))

        mi = Card("a task whose true Q is known, so the critic can be graded")
        mi.add(body(
            "One step per episode. The state is a scalar context s ∈ [−1,1], "
            "the action is a scalar a ∈ [−1,1], and the reward is "
            "−(a − g(s))² with g(s) = 0.8·sin(πs/2). Because the episode ends "
            "immediately, γ drops out and the <b>true action-value function is "
            "known exactly</b>: Q*(s,a) = −(a − g(s))².<br><br>"
            "That is the point of this toy. Everywhere else in deep RL you are "
            "guessing whether the critic learned anything real. Here you can "
            "plot the learned surface on top of the true one and the actor's "
            "output on top of the true argmax, and simply look.<br><br>"
            "<b>Three things to do:</b><br>"
            "&nbsp;&nbsp;<b>1.</b> Train, then sweep the context slider. The "
            "critic's parabola should slide left and right and the green "
            "actor marker should sit on its peak at every context — the actor "
            "has learned <i>the argmax as a function of the state</i>, which "
            "is the thing DQN could not do.<br>"
            "&nbsp;&nbsp;<b>2.</b> Drop the exploration noise to near zero and "
            "retrain. The critic ends up accurate <i>only in a narrow band "
            "around wherever the actor happened to start</i>, because nothing "
            "ever sampled the rest — and outside that band it is confidently "
            "wrong. That is the deterministic actor's failure mode, made "
            "visible.<br>"
            "&nbsp;&nbsp;<b>3.</b> Turn the target networks off and retrain. "
            "Watch the critic loss.", dim=True))
        hb = QHBoxLayout()
        hb.setSpacing(8)
        self.btn_train = QPushButton("Train  (≈3 s)")
        self.btn_train.setObjectName("Primary")
        self.chk_targets = QCheckBox("use target networks")
        self.chk_targets.setChecked(True)
        hb.addWidget(self.btn_train)
        hb.addWidget(self.chk_targets)
        hb.addStretch(1)
        mi.add_layout(hb)
        self.s_noise = slider(0, 60, 30)         # x0.01
        self.s_eps = slider(300, 2500, 1200)
        self.l_noise, self.l_eps = QLabel(), QLabel()
        mi.add_layout(slider_row("exploration σ (×0.01)", self.s_noise,
                                 self.l_noise))
        mi.add_layout(slider_row("training episodes", self.s_eps, self.l_eps))
        self.s_ctx = slider(-100, 100, 40)       # x0.01, the context to inspect
        self.l_ctx = QLabel()
        mi.add_layout(slider_row("inspect context s", self.s_ctx, self.l_ctx))
        self.st_err = Stat("|μ(s) − argmax|", "--", theme.ACCENT)
        self.st_rew = Stat("mean reward, last 100", "--", theme.GOOD)
        self.st_loss = Stat("final critic loss", "--", theme.WARN)
        self.st_par = Stat("weights", "--", theme.VIOLET)
        mi.add_layout(stat_row(self.st_err, self.st_rew, self.st_loss,
                               self.st_par))
        self.cC = MplCanvas(width=7.6, height=2.9, ncols=3)
        mi.add(self.cC)
        self.tC = body("Press <b>Train</b>.", dim=True)
        mi.add(self.tC)
        self.add(mi)
        self.agent = None
        self.log = None
        self.btn_train.clicked.connect(self._train)
        self.s_ctx.valueChanged.connect(self._redraw_scope)
        for s in (self.s_noise, self.s_eps):
            s.valueChanged.connect(self._labels)
        self._labels()
        self._redraw_scope()

        self.add(callout(
            "<b>What the middle panel is really showing.</b> The critic was "
            "never told the formula −(a−g(s))². It only ever saw scattered "
            "(s, a, r) triples and was fitted to targets built out of its own "
            "predictions. The parabola is <i>inferred</i>, and the actor never "
            "saw the reward function at all — it only ever followed ∂Q/∂a "
            "uphill on whatever surface the critic currently believed in. Two "
            "networks, each solving a problem it can solve, neither of them "
            "solving the actual task.", "good"))

        self._draw_diagram()
        self.finish()

    def on_show(self):
        # train on first view rather than at construction: every page in the
        # tutor is built at startup, and three seconds of gradient descent
        # per page is three seconds nobody asked for
        if self.agent is None:
            self._train()

    # ------------------------------------------------------------------
    def _draw_diagram(self):
        d = self.d_ddpg
        d.band(0.15, 3.95, 1.32, 2.52, "LIVE — updated every step",
               theme.ACCENT)
        d.band(0.15, 3.95, 0.14, 1.18, "TARGETS — soft-updated, τ ≈ 0.01",
               theme.VIOLET)
        d.block(1.05, 2.00, "actor  μ(s)", colour=theme.GOOD, w=1.5,
                sub="s → a, deterministic")
        d.block(2.95, 2.00, "critic  Q(s,a)", colour=theme.ACCENT, w=1.5,
                sub="fit to y")
        d.block(1.05, 0.68, "target actor  μ′", colour=theme.VIOLET, w=1.5,
                sub="a′ = μ′(s′)")
        d.block(2.95, 0.68, "target critic  Q′", colour=theme.VIOLET, w=1.5,
                sub="Q′(s′, a′)")
        d.arrow(1.80, 2.00, 2.20, 2.00, "a")
        d.arrow(1.80, 0.68, 2.20, 0.68, "a′")
        # the actor's gradient comes back OUT of the critic, w.r.t. the action
        d.arrow(2.20, 1.62, 1.82, 1.62, colour=theme.WARN)
        d.note(2.02, 1.46, "∂Q/∂a", colour=theme.WARN, fontsize=7.2)
        # the target flows UP into the critic's loss, not down
        d.arrow(3.62, 0.95, 3.62, 1.74, colour=theme.WARN, dashed=True)
        d.note(3.72, 1.35, "y = r + γQ′", colour=theme.WARN, fontsize=7.4,
               ha="left")
        d.block(5.75, 2.00, "replay buffer", colour=theme.CYAN, w=1.7,
                sub="(s, a, r, s′, d) × 20 000")
        d.block(7.35, 2.00, "robot", colour=theme.TEXT_FAINT, w=1.0,
                sub="one stride")
        d.arrow(6.85, 1.66, 6.62, 1.66, colour=theme.GOOD)
        d.note(6.74, 1.48, "transitions", colour=theme.GOOD, fontsize=7.0)
        d.arrow(4.88, 2.00, 4.02, 2.00, colour=theme.CYAN)
        d.note(4.45, 2.18, "batch", colour=theme.CYAN, fontsize=7.0)
        d.note(6.10, 0.85, "off-policy: a transition is a fact about the world,",
               colour=theme.CYAN, fontsize=7.0)
        d.note(6.10, 0.62, "so it stays usable after the policy changes",
               colour=theme.CYAN, fontsize=7.0)
        d.done()

    def _labels(self):
        self.l_noise.setText(f"{self.s_noise.value()/100.0:.2f}")
        self.l_eps.setText(f"{self.s_eps.value()}")

    # ------------------------------------------------------------------
    def _train(self):
        self.btn_train.setEnabled(False)
        self.btn_train.setText("training…")
        self.btn_train.repaint()
        try:
            self.agent, self.log = train_reach(
                episodes=int(self.s_eps.value()),
                noise=self.s_noise.value() / 100.0,
                use_targets=self.chk_targets.isChecked(),
                seed=3)
        finally:
            self.btn_train.setEnabled(True)
            self.btn_train.setText("Train  (≈3 s)")
        self._redraw_scope()

    def _redraw_scope(self):
        ctx = self.s_ctx.value() / 100.0
        self.l_ctx.setText(f"{ctx:+.2f}")
        c = self.cC
        c.clear()
        a_q, a_mu, a_l = c.axes
        acts = np.linspace(-1.0, 1.0, 200)
        true_q = np.array([ContextualReach.true_q([ctx], a) for a in acts])
        a_q.plot(acts, true_q, color=theme.TEXT_FAINT, lw=1.6, ls="--",
                 label="true Q*(s,·)")

        if self.agent is None:
            a_q.set_xlabel("action a")
            a_q.set_ylabel("Q")
            c.legend(a_q, loc="lower center")
            c.refresh()
            return

        ag = self.agent
        s_col = np.full((len(acts), 1), ctx)
        learned = ag.critic.forward(
            np.concatenate([s_col, acts.reshape(-1, 1)], axis=1)).ravel()
        mu = float(ag.act_greedy([ctx])[0])
        best = ContextualReach.best_action([ctx])
        a_q.plot(acts, learned, color=theme.ACCENT, lw=2.2,
                 label="learned Q(s,·)")
        a_q.axvline(mu, color=theme.GOOD, lw=1.6, label="μ(s)")
        a_q.axvline(best, color=theme.WARN, lw=1.2, ls=":", label="true argmax")
        a_q.set_xlabel("action a")
        a_q.set_ylabel("Q")
        a_q.set_title(f"the critic's surface at s = {ctx:+.2f}", fontsize=9)
        c.legend(a_q, loc="lower center")

        ss = np.linspace(-1.0, 1.0, 120)
        a_mu.plot(ss, [ContextualReach.best_action([x]) for x in ss],
                  color=theme.WARN, lw=1.6, ls="--", label="true argmax g(s)")
        a_mu.plot(ss, [float(ag.act_greedy([x])[0]) for x in ss],
                  color=theme.GOOD, lw=2.2, label="actor μ(s)")
        a_mu.scatter([ctx], [mu], s=45, color=theme.ACCENT, zorder=5)
        a_mu.set_xlabel("context s")
        a_mu.set_ylabel("action")
        a_mu.set_title("the actor IS the argmax", fontsize=9)
        c.legend(a_mu, loc="upper left")

        log = self.log
        if log.critic_loss:
            k = max(1, len(log.critic_loss) // 120)
            xs = list(range(0, len(log.critic_loss), k))
            a_l.semilogy(xs, [max(1e-12, log.critic_loss[i]) for i in xs],
                         color=theme.WARN, lw=1.5, label="critic loss")
        a_l.set_xlabel("training step")
        a_l.set_ylabel("MSE (log)")
        a_l.set_title("critic loss", fontsize=9)
        c.legend(a_l, loc="upper right")
        c.refresh()

        err = abs(mu - best)
        self.st_err.set(f"{err:.3f}")
        self.st_err.set_color(theme.GOOD if err < 0.08 else theme.BAD)
        self.st_rew.set(f"{float(np.mean(log.returns[-100:])):.4f}")
        self.st_loss.set(f"{log.critic_loss[-1]:.2e}" if log.critic_loss
                         else "--")
        self.st_par.set(f"{ag.actor.n_params() + ag.critic.n_params()}")

        if not self.chk_targets.isChecked():
            self.tC.setText(
                "<b>Target networks off (τ = 1).</b> The target is now built "
                "from the same weights that are being updated, so every "
                "gradient step moves the thing being aimed at. On a task this "
                "small and with γ = 0 it often survives — γ = 0 means the "
                "target is just r, with no bootstrapping to run away. Turn γ "
                "up on a real problem and this is where the critic loss climbs "
                "instead of falling and the Q values drift off to values no "
                "reward could ever justify. That failure has a name — the "
                "deadly triad — and the target networks are the cheapest known "
                "patch for it.")
        elif self.s_noise.value() <= 5:
            self.tC.setText(
                "<b>Almost no exploration.</b> Look at the middle panel: the "
                "actor tracks the true argmax only where it happened to "
                "wander, and elsewhere it is flat or wrong. A deterministic "
                "policy generates its own training data, so if it never tries "
                "an action it never learns that action was better — and there "
                "is no error message, no divergence, nothing to debug. It just "
                "converges confidently to the wrong answer. This is the single "
                "most common way DDPG fails in practice.")
        else:
            self.tC.setText(
                f"<b>Trained.</b> The critic's parabola (blue) sits on the "
                f"true one (dashed) and the actor (green line, middle panel) "
                f"tracks g(s) to within {err:.3f} at the inspected context. "
                f"Neither network was told the reward function. The critic "
                f"inferred the surface from scattered samples and its own "
                f"bootstrapped targets; the actor never saw a reward at all "
                f"and only ever followed ∂Q/∂a uphill. Sweep the context "
                "slider and watch the parabola slide — that sliding is what "
                "\"the argmax as a function of state\" looks like.")


# ==========================================================================
# PAGE -- is it still an MDP, and what makes it DDPG
# ==========================================================================

class MDPandFamilyPage(Page):
    TITLE = "Still an MDP? And What Makes It DDPG"
    SUBTITLE = ("The Markov property does not care how you picked the action. "
                "And the one feature that separates DDPG from TD3, SAC and "
                "PPO.")
    SECTION = SECTION
    NOTES = "deep RL"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>The MDP is the stage; DDPG is one actor standing on it.</b> "
            "The MDP defines what exists — states, actions, transitions, "
            "rewards, discount. An algorithm is a strategy for choosing "
            "actions <i>within</i> those rules. Asking \"is DDPG still an "
            "MDP?\" is a category error in the same way as asking whether a "
            "chess player is still chess. The useful question is whether your "
            "<b>problem</b> satisfies the Markov property, and that is a "
            "question about your state vector, not about your optimiser.",
            "key"))

        mk = Card("what \"Markov\" actually requires — one line, and it does "
                  "not mention the policy")
        mk.add(math_label(r"P\big(s_{t+1} \mid s_t, a_t\big) \;=\; "
                          r"P\big(s_{t+1} \mid s_t, a_t, s_{t-1}, a_{t-1}, "
                          r"\dots, s_0\big)", 16))
        mk.add(body(
            "In words: <b>the future depends on the present only</b>. Given "
            "where you are and what you do, the history adds nothing. Read "
            "the formula again and notice what is absent — there is no π "
            "anywhere in it. The Markov property is a property of the "
            "<b>environment</b>. It does not care whether a<sub>t</sub> came "
            "from a dice roll, an ε-greedy table, a stochastic Gaussian "
            "policy, or a deterministic neural network. Once a<sub>t</sub> is "
            "chosen, the environment's response is governed by the same "
            "transition kernel either way."))
        mk.add(body(
            "Two corollaries that are worth having ready, because they are the "
            "usual confusions:<br><br>"
            "&nbsp;&nbsp;• <b>A deterministic policy inside a stochastic "
            "environment is still an MDP.</b> You may deterministically decide "
            "to move Right; the slippery ice may still throw you sideways. "
            "μ(s) removes randomness from the <i>choice</i>, not from the "
            "<i>consequence</i>. DDPG on a real robot is exactly this "
            "case.<br>"
            "&nbsp;&nbsp;• <b>DDPG is built on the Bellman equation</b>, which "
            "is derived from the Markov property. Its target "
            "y = r + γQ′(s′, μ′(s′)) is a Bellman backup. So far from "
            "escaping the MDP framework, DDPG depends on it more directly than "
            "Monte Carlo does — MC only needs episodes to end, whereas any "
            "bootstrapping method needs the value of s′ to summarise the "
            "future, which is a Markov assumption in the strict sense."))
        mk.add(callout(
            "<b>Where DDPG does differ, and it is one word: instead of "
            "averaging over actions, it maximises over one.</b> A stochastic "
            "method's Bellman backup averages Q(s′,a′) over π(a′|s′). DDPG "
            "assumes there is a single best action and evaluates Q(s′, μ′(s′)) "
            "at that point alone. That is a modelling assumption about the "
            "problem — it is right when the value surface has one peak per "
            "state and wrong when a task genuinely has several equally good "
            "answers, which is where a stochastic policy earns its keep.",
            "key"))
        self.add(mk)

        # ---- model-based vs model-free, corrected ------------------------
        self.add(hline())
        self.add(title("The three-way classification, tightened"))

        cl = Card("known model, learned model, no model")
        cl.add(body(
            "The usual informal split is \"do we know the dynamics?\", and it "
            "is nearly right. Here it is stated so that the boundaries fall "
            "where they actually fall:"))
        cl.add(_table(
            ["Case", "What you have", "What you use", "Is it RL?"],
            [("1. Model known exactly",
              "P(s′|s,a) and r(s,a) in closed form",
              "Dynamic programming, optimal control, MPC, A*, trajectory "
              "optimisation. Pure computation — no interaction required.",
              "DP is; MPC and A* are not. Nothing here needs to learn."),
             ("2. Model unknown → learn one",
              "a simulator or a robot, and the intention to build P̂",
              "Model-based RL: fit a dynamics model from data, then plan or "
              "generate imagined rollouts against it. PILCO, MBPO, Dreamer, "
              "AlphaZero's learned value/dynamics.",
              "Yes. Very sample-efficient, and only as good as P̂."),
             ("3. Model unknown → skip it",
              "a simulator or a robot, and nothing else",
              "Model-free RL: learn Q or π directly from experience. "
              "Q-learning, DQN, DDPG, TD3, SAC, PPO.",
              "Yes. Sample-hungry, but nothing can be wrong about a model you "
              "never built.")],
            col0=170, colw=270, height=290))
        cl.add(body(
            "<b>Two refinements on the informal version.</b> First, \"if we "
            "know the dynamics RL is useless\" is too strong — a known model "
            "makes <i>planning</i> available, and planning is usually better, "
            "but a stochastic model with a huge branching factor can still be "
            "easier to attack by sampling than by exhaustive search. Say "
            "\"unnecessary\" rather than \"useless\". Second, the "
            "model-based/model-free line is about <b>whether you fit "
            "P(s′|s,a)</b>, not about whether a network appears. DDPG has two "
            "networks and neither predicts a next state, so it is model-free "
            "— it goes straight for the value.", dim=True))
        cl.add(callout(
            "<b>And MPC is the instructive non-example.</b> It has a model, it "
            "optimises over a horizon, it re-plans every step — everything "
            "that looks like model-based RL — but the model is <b>handed to "
            "it</b> and nothing is learned from experience. Bolt a learned "
            "dynamics model onto MPC and you have model-based RL; that hybrid "
            "is one of the most practical things in robotics right now, and it "
            "is exactly the \"combine classical methods with learning-based "
            "solutions\" line that shows up in robotics job descriptions.",
            "good"))
        self.add(cl)

        # ---- what makes it DDPG -----------------------------------------
        self.add(hline())
        self.add(title("What makes an algorithm DDPG rather than TD3, SAC or "
                       "PPO"))

        fm = Card("all of them have an actor and a critic — that is not the "
                  "distinguishing feature")
        fm.add(body(
            "\"It has an actor and a critic\" narrows nothing: so do TD3, SAC, "
            "PPO and A2C. Four independent switches decide which one you have "
            "built, and DDPG is one specific setting of all four."))
        fm.add(_table(
            ["Algorithm", "Actor", "Critics", "Estimates", "Data",
             "The defining feature"],
            [tuple(r) for r in ALGO_TABLE],
            col0=90, colw=150, height=330))
        fm.add(callout(
            "<b>You have built DDPG if, and only if, all four of these are "
            "true:</b><br><br>"
            "&nbsp;&nbsp;<b>1.</b> The actor is <b>deterministic</b> — it "
            "outputs the action itself, not a distribution, so exploration has "
            "to be injected as noise from outside.<br>"
            "&nbsp;&nbsp;<b>2.</b> There is <b>exactly one critic</b>, "
            "learning <b>Q(s,a)</b>, and the actor is trained by "
            "backpropagating ∂Q/∂a into it.<br>"
            "&nbsp;&nbsp;<b>3.</b> Learning is <b>off-policy from a replay "
            "buffer</b>.<br>"
            "&nbsp;&nbsp;<b>4.</b> There are <b>target networks</b>, updated "
            "by a soft Polyak crawl rather than a periodic hard copy.<br><br>"
            "Add a second critic and take the minimum, delay the actor "
            "updates, and smooth the target action with noise — you have "
            "<b>TD3</b>, and you have built it because DDPG's single critic "
            "systematically overestimates Q (the maximisation picks up the "
            "critic's own positive errors). Make the actor stochastic, add two "
            "critics and pay the policy an entropy bonus — <b>SAC</b>. Make "
            "the actor stochastic, learn V instead of Q, throw the data away "
            "each batch and clip how far the policy may move — <b>PPO</b>.",
            "key"))
        fm.add(body(
            "<b>A note on the honest ordering for a robotics problem.</b> TD3 "
            "is strictly an upgrade to DDPG and costs one extra network; if "
            "you are starting fresh today there is little reason to choose "
            "DDPG over TD3. The reason DDPG is still the right thing to "
            "understand first is that <b>TD3 and SAC are both described as "
            "patches to it</b> — you cannot follow either paper without it — "
            "and that its four components map one-to-one onto the four "
            "questions any continuous-control method has to answer.", dim=True))
        self.add(fm)

        pick = Card("pick a problem, get the algorithm — and the reason")
        pick.add(body(
            "The choice is nearly always forced by the problem rather than by "
            "preference. Select a situation and read why.", dim=True))
        self.cmb = QComboBox()
        for lab in ("continuous action, real hardware, few samples",
                    "continuous action, fast simulator, unlimited samples",
                    "discrete action, many samples",
                    "continuous action, several equally good solutions",
                    "continuous action, single critic overestimates"):
            self.cmb.addItem(lab)
        self.cmb.currentIndexChanged.connect(self._pick)
        pick.add_layout(labelled("Situation", self.cmb, width=70))
        self.pick_out = body("")
        pick.add(self.pick_out)
        self.add(pick)
        self._pick()

        self.finish()

    def _pick(self):
        i = self.cmb.currentIndex()
        msgs = [
            "<b>DDPG or TD3.</b> Continuous actions rule out DQN, and "
            "\"few samples\" rules out every on-policy method — PPO discards "
            "its batch after each update, so it needs orders of magnitude "
            "more real interactions than a replay-based method. Off-policy "
            "replay is not a nicety here; it is the only way the experiment "
            "fits inside a session with a human subject. Prefer TD3 if you "
            "can afford the second critic.",
            "<b>PPO.</b> With a cheap simulator, sample efficiency stops "
            "mattering and robustness starts to. PPO's clipped update is far "
            "less sensitive to hyperparameters than DDPG's, it parallelises "
            "trivially across environments, and its stochastic policy explores "
            "without a noise schedule to tune. This is why almost every "
            "sim-trained locomotion result you read used PPO.",
            "<b>DQN and its descendants.</b> If the actions can be "
            "enumerated, max<sub>a</sub>Q is a scan and you do not need an "
            "actor at all. Adding one would be strictly more machinery for "
            "strictly less: an actor is an approximation of an argmax you "
            "could have computed exactly.",
            "<b>SAC.</b> A deterministic actor commits to a single action per "
            "state, which is exactly wrong when the value surface has several "
            "peaks of similar height — it will pick one arbitrarily and lose "
            "the others. SAC's entropy bonus explicitly rewards keeping "
            "probability mass on all of the good options, so the policy stays "
            "multi-modal instead of collapsing.",
            "<b>TD3.</b> This is the exact failure TD3 was written for. A "
            "single critic's errors are not symmetric in effect: the actor "
            "climbs toward wherever Q is highest, so it actively seeks out the "
            "critic's positive errors and the bias compounds. Taking "
            "min(Q₁, Q₂) of two independently initialised critics is a cheap, "
            "deliberately pessimistic estimate that removes most of it.",
        ]
        self.pick_out.setText(msgs[i])


# ==========================================================================
# PAGE -- the case study
# ==========================================================================

class KneeRLPage(Page):
    TITLE = "Case Study: Tuning a Knee Prosthesis"
    SUBTITLE = ("One gait cycle is one timestep. The action is not a torque "
                "and not an angle — it is a change to the impedance itself.")
    SECTION = SECTION
    NOTES = "deep RL · impedance"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>This page joins the two halves of the tutor.</b> The left half "
            "built impedance control: a stiffness, a damping and an "
            "equilibrium angle that together decide what a joint feels like. "
            "The right half built reinforcement learning. Put them together "
            "and you get the problem this page is about — <b>the impedance "
            "parameters are the action</b>, and the reward is how closely the "
            "resulting gait matches a reference.<br><br>"
            "The numbers below are a small stand-in with a known optimum, not "
            "anyone's subject data. The <i>structure</i> is what transfers.",
            "key"))

        # ---- the setup ---------------------------------------------------
        st = Card("the controller underneath: continuous impedance, not a "
                  "state machine")
        st.add(body(
            "The conventional prosthesis controller is a <b>finite state "
            "machine</b>: split the gait cycle into four or five phases, and "
            "give each phase its own constant (K, B, θ<sub>eq</sub>) tuned "
            "offline. It works, and it has two well-known costs — the "
            "parameters jump discontinuously at phase boundaries, and there "
            "are 12-15 of them to tune per person by hand.<br><br>"
            "The alternative is <b>continuous impedance control</b>: let each "
            "of K, B and θ<sub>eq</sub> be a smooth function of gait phase, "
            "and represent each of those functions by its first two principal "
            "components extracted from a large dataset of normal walking."))
        st.add(math_label(
            r"K(\phi) = \bar K(\phi) + w_1^K \, \mathrm{PC}_1^K(\phi) "
            r"+ w_2^K \, \mathrm{PC}_2^K(\phi)", 16))
        st.add(body(
            "Same for B(φ) and θ<sub>eq</sub>(φ). Two things follow, and both "
            "matter for the RL problem:<br><br>"
            "&nbsp;&nbsp;• <b>The parameter count collapses.</b> A whole "
            "continuous stiffness trajectory is now <b>two numbers</b>. Convex "
            "optimisation over the dataset fixes the mean curves and the "
            "principal components once; the weights are what remains per "
            "person.<br>"
            "&nbsp;&nbsp;• <b>The search space becomes learnable.</b> A "
            "2-dimensional action is something a policy can explore in a few "
            "hundred strides. A 15-dimensional one is not."))
        st.add(callout(
            "<b>And note what is being commanded, because it is the whole "
            "reason this is an impedance page and not a position-control "
            "page.</b> The controller never commands the knee angle. It "
            "commands a <b>stiffness profile</b>, and the resulting torque is "
            "whatever that stiffness produces against the actual displacement. "
            "The reference angle appears only in the <b>reward</b>. So the "
            "device stays compliant — it yields when the ground or the user "
            "pushes — while still being driven toward a target trajectory by "
            "learning. Trying to get both from a position controller is what "
            "the impedance pages spent their length explaining you cannot do.",
            "key"))
        self.add(st)

        # ---- the MDP -----------------------------------------------------
        self.add(hline())
        self.add(title("The same problem, written as a 5-tuple"))

        mdp = Card("(S, A, P, R, γ) — filled in")
        mdp.add(_table(
            ["Element", "In this problem", "The non-obvious part"],
            [("timestep t", "one complete gait cycle (~1 s)",
              "Not a control tick. The state cannot be computed until the "
              "cycle finishes, because it is defined from the whole curve. "
              "The 1 kHz impedance loop runs underneath, untouched."),
             ("state  s ∈ ℝ⁵",
              "four knee-angle landmark errors (heel strike, peak stance "
              "flexion, peak stance extension, peak swing flexion) plus the "
              "phase lag from a cross-correlation against the reference",
              "Five numbers summarising a whole trajectory. The choice is a "
              "modelling decision, and a good one: it is low-dimensional, "
              "clinically interpretable, and directly comparable to the "
              "reference."),
             ("action  a ∈ ℝ²",
              "increments Δw₁, Δw₂ added to the base PC weights of the "
              "stiffness profile",
              "Increments, not absolute values — so the policy learns a "
              "correction rule rather than a lookup, and stays bounded near "
              "whatever the convex-optimisation baseline chose."),
             ("transition  P",
              "the person plus the device: weights → torque → gait → landmarks",
              "Never written down, never estimated. This is what makes the "
              "method model-free."),
             ("reward  R",
              "−Σ αᵢ|sᵢ| − effort regularisation − safety penalty",
              "The α weights encode clinical priority; swing flexion carries "
              "the largest because it is what subjects notice."),
             ("discount  γ",
              "≈0.95 over gait cycles",
              "A horizon of roughly 20 strides — long enough that the policy "
              "will accept one bad cycle to reach a better weight setting.")],
            col0=110, colw=290, height=420))
        self.add(mdp)

        rw = Card("the reward, term by term")
        rw.add(math_label(
            r"r \;=\; -\!\!\sum_{i=1}^{5}\alpha_i \,\big|s_i\big| "
            r"\;-\; \lambda \lVert a \rVert_1 \;-\; "
            r"\beta\,\mathbb{1}\big[\text{unsafe}\big]", 17))
        rw.add(body(
            "&nbsp;&nbsp;• <b>Tracking</b> — the weighted sum of the five "
            "landmark errors. α = (0.1, 0.1, 0.1, 0.4, 0.3): three landmarks "
            "at low weight, <b>peak swing flexion at 0.4</b> because it "
            "dominates how the gait looks and feels, and the phase lag at 0.3 "
            "because a correctly shaped but mistimed knee is still wrong.<br>"
            "&nbsp;&nbsp;• <b>Effort</b> — λ‖a‖₁ penalises large weight "
            "changes, which keeps the policy from thrashing the impedance "
            "between strides. This is the same regularisation term as in any "
            "optimal control cost, and it does the same job.<br>"
            "&nbsp;&nbsp;• <b>Safety</b> — a hard penalty if peak flexion "
            "exceeds ~70° or the knee hyperextends past −10°. A cliff rather "
            "than a slope, because these are limits, not preferences."))
        rw.add(callout(
            "<b>The honest caveat about the state, and it is worth being able "
            "to say it out loud.</b> The five landmark errors are a "
            "<i>function of</i> the true underlying state — the current weight "
            "vector — plus stride-to-stride variability. That makes this a "
            "<b>partially observable</b> problem in the strict sense: the "
            "agent observes a noisy summary, not the state. In practice it is "
            "treated as an MDP because the observation is an almost invertible "
            "function of what matters, and because the noise is small relative "
            "to the signal being corrected. That is a defensible engineering "
            "approximation, not an oversight — and knowing which one it is is "
            "the difference between using the framework and reciting it.",
            "warn"))
        self.add(rw)

        why = Card("why DDPG and not something else, for this problem "
                   "specifically")
        why.add(body(
            "&nbsp;&nbsp;• <b>Not DQN.</b> The action is two real numbers. "
            "Discretising them reintroduces the table problem from three pages "
            "back, and coarse bins mean the policy cannot make a fine "
            "correction.<br>"
            "&nbsp;&nbsp;• <b>Not PPO.</b> The sample budget is a person "
            "walking. A few hundred gait cycles is a long session; a few "
            "hundred thousand is not a study, it is a fantasy. On-policy "
            "methods discard each batch, so the replay buffer is not a "
            "convenience here, it is the feasibility condition.<br>"
            "&nbsp;&nbsp;• <b>Deterministic output is what a controller "
            "wants.</b> At deployment the device should apply the same "
            "correction for the same observed gait, every stride. A sampled "
            "policy would introduce stride-to-stride variation that the "
            "patient can feel and that no clinician would sign off on.<br>"
            "&nbsp;&nbsp;• <b>The critic is the whole point.</b> Nobody can "
            "write down how a weight change will propagate to peak swing "
            "flexion three strides later — the coupling is nonlinear and "
            "subject-specific. Q(s,a) learns that mapping from data, and "
            "∂Q/∂a is precisely \"which way should I move the weights\", which "
            "is the question a human tuner is trying to answer by hand.",
            dim=True))
        why.add(body(
            "<b>The one honest upgrade:</b> TD3, for the overestimation reason "
            "from the previous page. On a task where the actor is climbing a "
            "single critic that was fitted from a few thousand transitions, "
            "the optimism bias is real. Two critics and a minimum is cheap "
            "insurance."))
        self.add(why)

        # ---- interactive -------------------------------------------------
        self.add(hline())
        self.add(title("Run it"))

        run = Card("a toy with the same shape, trained end to end")
        run.add(body(
            "The environment underneath is a stand-in: a fixed, <b>non-"
            "diagonal</b> coupling from the two weights to the five landmark "
            "errors, with a hidden optimum at (0, 0), plus stride-to-stride "
            "noise. Non-diagonal matters — turning one weight moves several "
            "landmarks at once, which is exactly what makes hand tuning hard "
            "and what the critic has to work out.<br><br>"
            "<b>Left:</b> the learning curve, in mean reward per gait cycle. "
            "<b>Middle:</b> the weight trajectory of one greedy episode "
            "starting from a deliberately bad (1.0, −1.0), drawn on the true "
            "reward landscape the agent never sees. <b>Right:</b> the five "
            "landmark errors at the start and end of that episode.<br><br>"
            "<b>Things to try:</b> drop the training sessions to 15 and watch "
            "the policy get most of the way and stop — partial credit is the "
            "normal outcome of a short session. Raise the stride noise and "
            "watch the final errors floor out: <b>no policy can correct "
            "variability that is not caused by the weights</b>, and mistaking "
            "that floor for a tuning failure is a classic way to waste a "
            "study.", dim=True))
        hb = QHBoxLayout()
        hb.setSpacing(8)
        self.btn_g = QPushButton("Train  (≈7 s)")
        self.btn_g.setObjectName("Primary")
        hb.addWidget(self.btn_g)
        hb.addStretch(1)
        run.add_layout(hb)
        self.s_sess = slider(10, 80, 50)
        self.s_gnoise = slider(0, 150, 35)       # x0.01 deg
        self.s_expl = slider(5, 80, 35)          # x0.01
        self.l_sess, self.l_gnoise, self.l_expl = QLabel(), QLabel(), QLabel()
        run.add_layout(slider_row("training sessions", self.s_sess,
                                  self.l_sess))
        run.add_layout(slider_row("stride noise (×0.01°)", self.s_gnoise,
                                  self.l_gnoise))
        run.add_layout(slider_row("exploration σ (×0.01)", self.s_expl,
                                  self.l_expl))
        self.st_r0 = Stat("reward, first session", "--", theme.BAD)
        self.st_r1 = Stat("reward, last session", "--", theme.GOOD)
        self.st_w = Stat("final weights", "--", theme.ACCENT)
        self.st_e = Stat("mean |landmark error|", "--", theme.WARN)
        self.st_strides = Stat("real strides used", "--", theme.VIOLET)
        run.add_layout(stat_row(self.st_r0, self.st_r1, self.st_w, self.st_e,
                                self.st_strides))
        self.cD = MplCanvas(width=7.6, height=2.9, ncols=3)
        run.add(self.cD)
        self.tD = body("Press <b>Train</b>.", dim=True)
        run.add(self.tD)
        self.add(run)
        self.g_agent = None
        self.btn_g.clicked.connect(self._train_gait)
        for s in (self.s_sess, self.s_gnoise, self.s_expl):
            s.valueChanged.connect(self._glabels)
        self._glabels()

        self.add(callout(
            "<b>What this does and does not demonstrate.</b> It demonstrates "
            "that a deterministic actor-critic can find a two-dimensional "
            "impedance parameterisation from a reward built out of gait "
            "landmarks, in a few thousand strides, without any model of the "
            "coupling. It does not demonstrate anything about a person: real "
            "subjects adapt <i>while you tune</i>, which makes the environment "
            "non-stationary and is the single hardest thing about this problem "
            "that no toy reproduces.", "warn"))

        self.finish()

    def on_show(self):
        if self.g_agent is None:
            self._train_gait()

    def _glabels(self):
        self.l_sess.setText(f"{self.s_sess.value()}")
        self.l_gnoise.setText(f"{self.s_gnoise.value()/100.0:.2f}°")
        self.l_expl.setText(f"{self.s_expl.value()/100.0:.2f}")

    def _train_gait(self):
        self.btn_g.setEnabled(False)
        self.btn_g.setText("training…")
        self.btn_g.repaint()
        sess = int(self.s_sess.value())
        try:
            ag, env, log = train_gait(episodes=sess,
                                      noise=self.s_expl.value() / 100.0,
                                      seed=1)
            env.noise = self.s_gnoise.value() / 100.0
        finally:
            self.btn_g.setEnabled(True)
            self.btn_g.setText("Train  (≈7 s)")
        self.g_agent = ag
        ws, rs, feats = rollout_gait(ag, env, w0=(1.0, -1.0), n=40)

        self.st_r0.set(f"{log.returns[0]:.2f}")
        self.st_r1.set(f"{log.returns[-1]:.2f}")
        self.st_w.set(f"({ws[-1][0]:+.2f}, {ws[-1][1]:+.2f})")
        err = float(np.mean(np.abs(feats[-1])))
        self.st_e.set(f"{err:.2f}°")
        self.st_e.set_color(theme.GOOD if err < 1.0 else theme.WARN)
        self.st_strides.set(f"{sess * env.n_cycles}")

        self.tD.setText(
            f"<b>{sess} sessions × {env.n_cycles} cycles = "
            f"{sess*env.n_cycles} strides.</b> Mean reward per cycle went from "
            f"{log.returns[0]:.2f} to {log.returns[-1]:.2f}, and the greedy "
            f"policy walked the weights from (+1.00, −1.00) to "
            f"({ws[-1][0]:+.2f}, {ws[-1][1]:+.2f}) — the hidden optimum is "
            f"(0, 0), which the agent was never told and could only find "
            f"through the reward. Mean landmark error at the end: {err:.2f}°, "
            f"against a stride-noise floor of "
            f"{self.s_gnoise.value()/100.0:.2f}°. Look at the middle panel: "
            "the path is not a straight line to the optimum, because the "
            "coupling is not diagonal — correcting swing flexion drags stance "
            "extension with it, and the critic had to learn that trade before "
            "the actor could exploit it.")

        c = self.cD
        c.clear()
        a_l, a_w, a_f = c.axes
        a_l.plot(log.returns, color=theme.GOOD, lw=2.0)
        a_l.axhline(0.0, color=theme.TEXT_FAINT, lw=1.0, ls="--",
                    label="perfect (0 error, 0 effort)")
        a_l.set_xlabel("training session")
        a_l.set_ylabel("mean reward / gait cycle")
        a_l.set_title("learning curve", fontsize=9)
        c.legend(a_l, loc="lower right")

        gx = np.linspace(-1.6, 1.6, 70)
        gy = np.linspace(-1.6, 1.6, 70)
        GX, GY = np.meshgrid(gx, gy)
        Z = np.zeros_like(GX)
        al = np.array(env.alphas)
        for i in range(GX.shape[0]):
            for j in range(GX.shape[1]):
                f = env._features(np.array([GX[i, j], GY[i, j]]))
                Z[i, j] = -float(np.sum(al * np.abs(f)))
        a_w.contourf(GX, GY, Z, levels=18, cmap="viridis", alpha=0.75)
        a_w.plot(ws[:, 0], ws[:, 1], color=theme.PINK, lw=2.0, marker="o",
                 ms=2.5, label="greedy episode")
        a_w.scatter([0.0], [0.0], marker="*", s=110, color="white", zorder=6,
                    label="hidden optimum")
        a_w.set_xlabel("PC1 weight  w₁")
        a_w.set_ylabel("PC2 weight  w₂")
        a_w.set_title("the landscape it never saw", fontsize=9)
        c.legend(a_w, loc="upper right")

        names = ["strike", "st.flex", "st.ext", "sw.flex", "lag"]
        xpos = np.arange(5)
        a_f.bar(xpos - 0.18, np.abs(feats[0]), width=0.34, color=theme.BAD,
                alpha=0.85, label="start")
        a_f.bar(xpos + 0.18, np.abs(feats[-1]), width=0.34, color=theme.GOOD,
                alpha=0.85, label="after")
        a_f.set_xticks(xpos)
        a_f.set_xticklabels(names, fontsize=7.5, rotation=20)
        a_f.set_ylabel("|error|  (deg, % cycle)")
        a_f.set_title("landmark errors", fontsize=9)
        c.legend(a_f, loc="upper right")
        c.refresh()


# ==========================================================================
# PAGE -- shipping it
# ==========================================================================

class DeployRLPage(Page):
    TITLE = "Shipping It: Fast Loop, Slow Learner"
    SUBTITLE = ("A gradient step has no bound on how long it takes. A control "
                "loop is nothing but bounds. They cannot share a task.")
    SECTION = SECTION
    NOTES = "deep RL · real-time"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>Page 1's argument, arriving as an architecture.</b> The "
            "impedance loop must run at 1 kHz with a hard deadline. Training "
            "involves batch sampling, matrix multiplies, an optimiser, and "
            "memory traffic whose duration depends on cache state — a "
            "distribution with a long tail and no worst-case bound you would "
            "want to defend. <b>Put the trainer inside the control task and "
            "the first slow batch is a missed deadline</b>, which on a "
            "prosthesis is a stumble. So they go in two tasks at two rates, "
            "and everything interesting is in how they talk.", "key"))

        two = Card("two tasks, two clocks")
        self.d_rt = BlockDiagram(width=7.6, height=2.8, ylim=(0, 2.8))
        two.add(self.d_rt)
        two.add(_table(
            ["", "RT_Control", "RL_Trainer"],
            [("Rate", "1 kHz, hard deadline", "20 Hz, soft — a late batch is "
              "nothing"),
             ("Priority", "highest", "below every control task"),
             ("Does", "read encoder, evaluate μ(s) if a cycle ended, compute "
              "impedance torque, write current",
              "sample the buffer, run the gradient steps, publish new actor "
              "weights"),
             ("May allocate?", "never — no malloc, no resize, no logging to "
              "disk", "yes, it is not on the critical path"),
             ("May block?", "never — no lock it can wait on",
              "yes, briefly, on its own side only"),
             ("Owns", "a pointer into shared memory",
              "the shared memory itself")],
            col0=110, colw=290, height=310))
        self.add(two)

        sm = Card("the shared memory, and who is allowed to touch what")
        sm.add(body(
            "One structure, one owner, two writers with <b>disjoint</b> write "
            "sets. That last clause is the whole design: if no two "
            "participants write the same field, the exchange needs no lock, "
            "and the fast side can never be blocked by the slow one."))
        sm.add(CodePane(
            "struct SharedMemory {\n"
            "    TransferData transferQueue[300];  // ring buffer of (s,a,r,s')\n"
            "    long  writeIdx;                   // WRITTEN by RT_Control\n"
            "    long  readIdx;                    // WRITTEN by RL_Trainer\n"
            "    bool  newWeightsAvailable;        // set by Trainer, cleared by RT\n"
            "    double actorWeightsFlat[70000];   // WRITTEN by RL_Trainer\n"
            "};"))
        sm.add(body(
            "<b>Upstream — experience, fast → slow.</b> When a gait cycle "
            "completes, RT_Control writes one transition at "
            "<code>writeIdx</code> and advances it. It is the only writer of "
            "<code>writeIdx</code>. RL_Trainer reads from "
            "<code>readIdx</code> up to whatever <code>writeIdx</code> "
            "currently says and advances <code>readIdx</code>, which only it "
            "writes. A single-producer single-consumer ring, which is the one "
            "concurrent structure that is genuinely safe without a lock, "
            "provided the two indices are written atomically.<br><br>"
            "<b>Downstream — weights, slow → fast.</b> The trainer writes the "
            "new actor weights, then sets <code>newWeightsAvailable</code>. "
            "The order matters and is not negotiable: <b>publish the data, "
            "then raise the flag</b>. Raise the flag first and the controller "
            "may copy a half-written network. RT_Control checks the flag once "
            "per tick, and only if it is set does it copy the array into its "
            "own local copy and clear the flag."))
        sm.add(callout(
            "<b>Only the actor crosses the boundary, and that is worth "
            "noticing.</b> The critic, the target networks and the replay "
            "buffer all stay on the slow side and never appear in the control "
            "loop. At runtime the controller's entire share of this algorithm "
            "is <b>one forward pass through a small MLP</b> — a fixed number "
            "of multiply-accumulates, no branches, no allocation, and "
            "therefore a bounded execution time you can actually measure and "
            "put in a budget. Everything that made DDPG expensive was training "
            "machinery, and none of it ships.", "key"))
        sm.add(body(
            "<b>Three safety rules that are not optional on hardware.</b><br>"
            "&nbsp;&nbsp;<b>1.</b> Clamp the action in the <i>controller</i>, "
            "not in the policy. The network's tanh output is a soft bound and "
            "a bug can defeat it; the impedance limits are what stands between "
            "a bad weight update and a person.<br>"
            "&nbsp;&nbsp;<b>2.</b> Rate-limit weight changes between strides. "
            "A policy that is still learning will occasionally emit a large "
            "correction, and a large stiffness step mid-gait is felt as a "
            "kick.<br>"
            "&nbsp;&nbsp;<b>3.</b> Keep the last known-good weights. If the "
            "trainer crashes, hangs or publishes something that fails a "
            "sanity check, the controller keeps running on what it had. It "
            "must never wait for the learner, and it must never stop because "
            "the learner stopped.", dim=True))
        self.add(sm)

        # ---- interactive: what happens if you merge them ------------------
        mix = Card("what actually happens if you put the trainer in the fast "
                   "task")
        mix.add(body(
            "The controller's own work is short and nearly constant. A "
            "gradient step is neither — its duration has a mean and a tail. "
            "Below, the control task's budget is 1/f<sub>s</sub>, and the "
            "trainer is dropped into it every N ticks.<br><br>"
            "<b>Left:</b> per-tick execution time against the deadline. "
            "<b>Right:</b> the fraction of ticks that overrun. Raise the loop "
            "rate or the training cost and watch the overruns appear — and "
            "notice that they appear <i>periodically</i>, which is the worst "
            "possible signature: the loop looks fine on a scope for hundreds "
            "of cycles and then misses, so the bug is intermittent and shows "
            "up on hardware rather than on the bench.", dim=True))
        self.s_fs = slider(100, 4000, 1000)
        self.s_tcost = slider(1, 300, 120)       # x0.01 ms per gradient step
        self.s_every = slider(1, 200, 50)        # train every N ticks
        self.l_fs, self.l_tcost, self.l_every = QLabel(), QLabel(), QLabel()
        mix.add_layout(slider_row("loop rate f_s (Hz)", self.s_fs, self.l_fs))
        mix.add_layout(slider_row("train cost (×0.01 ms)", self.s_tcost,
                                  self.l_tcost))
        mix.add_layout(slider_row("train every N ticks", self.s_every,
                                  self.l_every))
        self.st_budget = Stat("budget per tick", "--", theme.ACCENT)
        self.st_ctrl = Stat("control work", "--", theme.GOOD)
        self.st_worst = Stat("worst tick", "--", theme.BAD)
        self.st_over = Stat("overruns", "--", theme.WARN)
        self.st_split = Stat("if split in two tasks", "--", theme.GOOD)
        mix.add_layout(stat_row(self.st_budget, self.st_ctrl, self.st_worst,
                                self.st_over, self.st_split))
        self.cE = MplCanvas(width=7.6, height=2.8, ncols=2)
        mix.add(self.cE)
        self.tE = body("", dim=True)
        mix.add(self.tE)
        self.add(mix)
        for s in (self.s_fs, self.s_tcost, self.s_every):
            s.valueChanged.connect(self._redraw_rt)
        self._redraw_rt()

        self.add(callout(
            "<b>Where this whole tutor ends up.</b> Page 1 said your loop rate "
            "is not your bandwidth and that deadlines are the real currency. "
            "The controller pages said a compliant joint is a design choice "
            "with a number attached. The RL pages said you can learn that "
            "number from experience instead of guessing it. This page is the "
            "point where all three become one piece of software: a bounded, "
            "boring, deterministic controller in the fast task, and everything "
            "clever demoted to a lower priority where it is allowed to be "
            "slow.", "good"))

        self._draw_rt_diagram()
        self.finish()

    # ------------------------------------------------------------------
    def _draw_rt_diagram(self):
        d = self.d_rt
        d.band(0.15, 3.55, 1.45, 2.70, "FAST TASK — 1 kHz, hard deadline",
               theme.GOOD)
        d.band(4.45, 7.85, 1.45, 2.70, "SLOW TASK — 20 Hz, soft",
               theme.VIOLET)
        d.block(1.10, 2.10, "RT_Control", colour=theme.GOOD, w=1.6,
                sub="impedance + μ(s) forward pass")
        d.block(2.85, 2.10, "joint", colour=theme.TEXT_FAINT, w=1.0,
                sub="1 kHz")
        d.arrow(1.90, 2.10, 2.35, 2.10, "τ")
        d.feedback(3.35, 2.10, 1.10, 1.78, "θ, θ̇", drop=0.42)
        d.block(6.20, 2.10, "RL_Trainer", colour=theme.VIOLET, w=1.7,
                sub="critic + targets + buffer")
        d.block(4.00, 0.72, "SharedMemory", colour=theme.CYAN, w=2.1,
                sub="owned by RL_Trainer")
        d.note(4.00, 0.30, "ring buffer  ·  writeIdx (fast)  ·  readIdx (slow)"
                           "  ·  flag  ·  actorWeightsFlat",
               colour=theme.CYAN, fontsize=6.8)
        d.arrow(1.55, 1.62, 3.20, 0.98, colour=theme.GOOD)
        d.note(2.72, 1.30, "push (s,a,r,s′)", colour=theme.GOOD, fontsize=7.0,
               ha="left")
        d.arrow(3.15, 0.62, 1.15, 1.55, colour=theme.WARN, dashed=True)
        d.note(1.90, 0.80, "copy weights if flag", colour=theme.WARN,
               fontsize=7.0)
        d.arrow(5.00, 0.98, 5.80, 1.58, colour=theme.VIOLET)
        d.note(4.90, 1.42, "sample batch", colour=theme.VIOLET, fontsize=7.0,
               ha="right")
        d.arrow(6.55, 1.58, 5.05, 0.66, colour=theme.WARN, dashed=True)
        d.note(6.05, 1.36, "weights, then flag", colour=theme.WARN,
               fontsize=7.0, ha="left")
        d.done()

    def _redraw_rt(self):
        fs = float(self.s_fs.value())
        cost = self.s_tcost.value() / 100.0        # ms per gradient step
        every = int(self.s_every.value())
        self.l_fs.setText(f"{fs:.0f} Hz")
        self.l_tcost.setText(f"{cost:.2f} ms")
        self.l_every.setText(f"{every}")

        budget = 1000.0 / fs                       # ms
        ctrl = 0.08 + 0.02                         # impedance + one forward pass
        n = 2000
        rng = np.random.default_rng(7)
        # control work is nearly constant; the trainer has a long tail
        ticks = ctrl + rng.normal(0.0, 0.006, size=n)
        hits = np.arange(n) % every == 0
        tail = cost * (1.0 + np.abs(rng.normal(0.0, 0.45, size=n)))
        ticks = ticks + hits * tail
        worst = float(ticks.max())
        over = float(np.mean(ticks > budget))

        self.st_budget.set(f"{budget:.2f} ms")
        self.st_ctrl.set(f"{ctrl:.2f} ms")
        self.st_worst.set(f"{worst:.2f} ms")
        self.st_worst.set_color(theme.BAD if worst > budget else theme.GOOD)
        self.st_over.set(f"{over*100:.1f} %")
        self.st_over.set_color(theme.GOOD if over == 0 else theme.BAD)
        self.st_split.set(f"{ctrl/budget*100:.0f} % of budget")

        if over == 0:
            self.tE.setText(
                f"<b>Fits — at this rate and this training cost.</b> Worst "
                f"tick {worst:.2f} ms against a {budget:.2f} ms budget. Now "
                f"raise the loop rate, or the training cost, or make training "
                f"more frequent. The margin disappears quickly, and it "
                f"disappears on the tail rather than the mean — which means "
                f"your average timing measurement will keep looking healthy "
                "right up until it does not. Split the two tasks and the "
                f"control side is a flat {ctrl/budget*100:.0f}% of budget "
                "regardless of what the learner is doing.")
        else:
            self.tE.setText(
                f"<b>{over*100:.1f}% of ticks overrun.</b> Worst case "
                f"{worst:.2f} ms against a {budget:.2f} ms deadline — the "
                f"control work is only {ctrl:.2f} ms of that, so the joint is "
                f"being starved by an optimiser. On a prosthesis a missed tick "
                f"is a torque held one cycle too long. And notice the "
                f"periodicity in the left panel: the overruns land every "
                f"{every} ticks, so the loop looks perfect between them. Move "
                f"the trainer to a lower-priority task and the control side "
                f"drops to a flat {ctrl/budget*100:.0f}% of budget, "
                "permanently.")

        c = self.cE
        c.clear()
        a1, a2 = c.axes
        a1.plot(ticks[:200], color=theme.ACCENT, lw=1.0)
        a1.axhline(budget, color=theme.BAD, lw=1.6, ls="--", label="deadline")
        a1.axhline(ctrl, color=theme.GOOD, lw=1.4, ls=":",
                   label="control work alone")
        a1.set_xlabel("tick")
        a1.set_ylabel("execution time (ms)")
        a1.set_title("one task doing both jobs", fontsize=9)
        c.legend(a1, loc="upper right")

        rates = np.linspace(100, 4000, 120)
        fracs = []
        for f in rates:
            b = 1000.0 / f
            fracs.append(float(np.mean(ticks > b)) * 100.0)
        a2.plot(rates, fracs, color=theme.BAD, lw=2.0)
        a2.scatter([fs], [over * 100], s=45, color=theme.ACCENT, zorder=5,
                   label="you are here")
        a2.axhline(0.0, color=theme.GOOD, lw=1.4, ls="--",
                   label="split tasks: always 0")
        a2.set_xlabel("loop rate (Hz)")
        a2.set_ylabel("ticks overrunning (%)")
        a2.set_title("merged: overruns vs rate", fontsize=9)
        c.legend(a2, loc="upper left")
        c.refresh()
