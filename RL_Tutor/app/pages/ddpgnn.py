"""
The three pages that sit between "DDPG, one piece at a time" and the case
study -- all three answering questions that the four-networks summary raises
and does not settle.

    The Gradient Handoff    what dQ/da actually IS (a vector, one number per
                            action dimension per sample), what it is NOT (a
                            target for the actor's output), and what the
                            actor does with it
    Inside the Critic       two inputs of completely different kinds arriving
                            at one network; early concat versus the paper's
                            late fusion, and what the merge point does to the
                            gradient the actor depends on
    One Rulebook            the structures every value-based agent shares --
                            Experience, StepResult, Env, ReplayBuffer, act()
                            -- what genuinely is identical from tabular
                            Q-learning to DDPG, and the exact points where
                            PPO refuses to fit the same mould

The first of these is the page to send someone to when they say "so we pass
the sensitivity to the actor" and cannot say what that sentence means
mechanically. It is the single most misread step in the algorithm.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton

from rlcore.deeprl import ContextualReach, ReplayBuffer, train_reach
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
from .deeprl import _table as _deeprl_table
from .motors import slider, slider_row

SECTION = "Deep RL & Continuous Control"


def _table(headers, rows, col0=150, colw=250, height=None):
    """
    The deep-RL page table, resized to fit its contents.

    `_table` in deeprl.py guesses a height from the row count, which is fine
    for short cells and cuts long ones off behind a scrollbar. These pages
    have several tables whose whole point is that every row is visible at
    once, so the height is measured after the column widths are set rather
    than estimated before. `height` is accepted and ignored, so call sites
    read the same as everywhere else in the tutor.
    """
    t = _deeprl_table(headers, rows, col0=col0, colw=colw, height=height)
    t.resizeRowsToContents()
    h = (t.horizontalHeader().height()
         + sum(t.rowHeight(r) for r in range(t.rowCount())) + 8)
    t.setMinimumHeight(h)
    t.setMaximumHeight(h)
    return t


def _code(src: str) -> CodePane:
    """A CodePane sized to its own contents, so no pane leaves a dead gap."""
    pane = CodePane(src)
    pane.sizeHintLine(len(src.strip().splitlines()) + 1)
    return pane



# ==========================================================================
# PAGE -- the gradient handoff
# ==========================================================================

class GradientHandoffPage(Page):
    TITLE = "The Gradient Handoff"
    SUBTITLE = ("∂Q/∂a is not a target for the actor's output. It is the SEED "
                "of the actor's backward pass — and that distinction is the "
                "whole update.")
    SECTION = SECTION
    NOTES = "deep RL"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>One sentence, and everything on this page is an unpacking of "
            "it:</b> the critic hands the actor a number that says <i>if your "
            "output were a hair larger, the value would change by this "
            "much, in this direction</i> — and the actor then runs its own "
            "ordinary backward pass with that number in the slot where a "
            "prediction error would normally sit.", "key"))

        # ---- what the object is -----------------------------------------
        wi = Card("first: what kind of object the sensitivity is")
        wi.add(body(
            "It is easy to picture ∂Q/∂a as \"one number at the end of a long "
            "multiplication\", and for a one-dimensional action, evaluated at "
            "one state, that is exactly right. The general shape is worth "
            "stating precisely because the code slices it:"))
        wi.add(math_label(r"\left.\nabla_a Q(s,a)\right|_{a=\mu(s)} "
                          r"\;\in\; \mathbb{R}^{N \times d_a}", 17))
        wi.add(body(
            "&nbsp;&nbsp;• <b>One number per action dimension.</b> A knee "
            "with two impedance weights gets two numbers: \"raise the "
            "stiffness weight → Q goes up 0.4 per unit; raise the damping "
            "weight → Q goes down 1.2 per unit\". They are independent "
            "answers to independent questions.<br>"
            "&nbsp;&nbsp;• <b>One row per sample in the batch.</b> The "
            "question is asked separately at each of the 64 states in the "
            "minibatch, because the best direction in one state has nothing "
            "to do with the best direction in another.<br>"
            "&nbsp;&nbsp;• <b>Evaluated at a = μ(s), not anywhere else.</b> "
            "It is the slope of the critic's surface <i>at the point the "
            "actor currently stands</i>. Move the actor and the number "
            "changes; that is why the update is one small step and then a "
            "re-measurement, forever."))
        wi.add(body(
            "And each of those numbers is itself the multiply-along-a-path, "
            "sum-across-paths quantity from the backprop page: every route "
            "from the action input, through both hidden layers of the critic, "
            "to the single output, multiplied out and added up. There are "
            "64 × 64 = 4 096 such routes in the tutor's critic. Backprop "
            "computes the sum without listing them.", dim=True))
        self.add(wi)

        # ---- what it is NOT ----------------------------------------------
        no = Card("second, and this is the common misreading: it is not a "
                  "target")
        no.add(body(
            "The wrong picture — and it is a natural one, because it is how "
            "every supervised network works — goes: the critic produces a "
            "number, we hand it to the actor, and the actor is trained so "
            "that its output <i>becomes</i> that number. It is not that. "
            "Nothing anywhere is trying to make μ(s) equal ∂Q/∂a. The two "
            "quantities are not even in the same units: one is a torque, the "
            "other is value-per-torque."))
        no.add(_table(
            ["", "Supervised regression", "The actor's update"],
            [("What arrives from outside", "a target t — a value the output "
              "should equal", "a slope ∂Q/∂a — a direction the output should "
              "move"),
             ("The seed of the backward pass", "2(y − t)/N — computed FROM "
              "the target", "−∂Q/∂a — the arriving quantity IS the seed, "
              "already"),
             ("What it means to succeed", "y ends up equal to t",
              "y ends up somewhere nobody named, where the slope is zero"),
             ("Where the truth came from", "a human wrote it down",
              "nowhere. There is no correct action anywhere in the problem — "
              "that is what makes it RL"),
             ("If the outside signal is wrong", "the fit is wrong in a "
              "measurable way", "the actor confidently walks the wrong way "
              "and nothing contradicts it")],
            col0=190, colw=250, height=290))
        no.add(callout(
            "<b>Why there cannot be a target action, ever.</b> A target would "
            "have to come from somebody who knows the right torque for this "
            "state. Nobody does — if such a table existed you would deploy it "
            "and skip the learning entirely. The only thing available in the "
            "whole system is an <i>opinion about actions that were tried</i>, "
            "which is the critic. An opinion supports a comparison, and a "
            "comparison in the limit of a small change is a derivative. So "
            "the derivative is not a convenient choice of signal; it is the "
            "<b>only</b> signal the problem admits.", "key"))
        self.add(no)

        # ---- the mechanics ------------------------------------------------
        self.add(hline())
        self.add(title("The mechanics: where the number is inserted, and what "
                       "happens after"))

        me = Card("five lines, in order, with the shapes")
        me.add(_table(
            ["Step", "Code", "Shape", "What is happening"],
            [("1", "a_pi = actor.forward(s) * a_max", "64 × d_a",
              "the actor proposes an action for each state in the batch. "
              "This forward pass caches every x and z inside the ACTOR — "
              "that cache is what makes step 5 possible."),
             ("2", "q = critic.forward([s, a_pi])", "64 × 1",
              "the critic grades those proposals. Caches inside the CRITIC "
              "this time."),
             ("3", "dx = critic.backward(ones/N)", "64 × (d_s + d_a)",
              "seed the critic's backward pass with ∂J/∂Q = 1/N and run it "
              "all the way to the critic's INPUT. Weight gradients get "
              "filled in on the way and are never used — the critic's "
              "optimiser is not called on this pass, which is what "
              "'the critic is frozen here' means concretely."),
             ("4", "dq_da = dx[:, dim_s:]", "64 × d_a",
              "throw away the state half of that input gradient and keep the "
              "action half. ∂Q/∂s is a perfectly real number and is of no "
              "use to anybody: the actor cannot change the state it was "
              "given."),
             ("5", "actor.backward(-dq_da * a_max)", "→ every actor weight",
              "hand that array to the actor as the blame at its OUTPUT layer. "
              "From here it is the ordinary backward pass of page 83: "
              "multiply by tanh's slope, spread back through each weight, "
              "sum at every node.")],
            col0=45, colw=250, height=390))
        me.add(body("The real source, from <code>rlcore/deeprl.py</code>:"))
        pane = CodePane(
            "a_pi = self.actor.forward(s) * c.a_max\n"
            "q_pi = self.critic.forward(np.concatenate([s, a_pi], axis=1))\n"
            "dx   = self.critic.backward(np.ones((c.batch, 1)) / c.batch)\n"
            "dq_da = dx[:, c.dim_s:]                 # the action half only\n"
            "self.actor.backward(-dq_da * c.a_max)   # minus = ascent\n"
            "self.actor.adam(c.lr_actor)             # only NOW does anything move")
        pane.sizeHintLine(7)
        pane.mark([3, 4], "#6b4e13")
        me.add(pane)
        me.add(body(
            "<b>Three details in those six lines that are easy to read past.</b> "
            "The <b>minus sign</b>: Adam descends, and we want to ascend on "
            "Q, so the seed is negated once and everything downstream is "
            "ordinary. The <b>× a_max</b>: the network's tanh output was "
            "scaled up to physical units before the critic saw it, so the "
            "chain rule owes that same factor on the way back — a units "
            "conversion, nothing deeper. And the <b>adam call on the last "
            "line only</b>: backward() computes, adam() moves. Between them "
            "the critic's own gradients are sitting in memory, complete and "
            "deliberately ignored.", dim=True))
        self.add(me)

        # ---- sign and magnitude ------------------------------------------
        sm = Card("what the sign does, what the magnitude does, and what Adam "
                  "does to the magnitude")
        sm.add(body(
            "<b>Sign is direction.</b> ∂Q/∂a > 0 means \"a larger action "
            "scores better here\", so the actor's weights are nudged so that "
            "next time μ(s) comes out a little larger for this state. "
            "Negative, and they are nudged the other way. That is the whole "
            "of the directional content, and it is enough — hill climbing has "
            "never needed more.<br><br>"
            "<b>Magnitude is confidence, or steepness.</b> ∂Q/∂a = +100 says "
            "the critic believes value is changing violently with the action "
            "right here; +0.1 says the surface is nearly flat and it barely "
            "matters. A raw gradient step scales with that, so big slopes "
            "would produce big weight changes."))
        sm.add(callout(
            "<b>Except that DDPG does not take raw gradient steps, and this "
            "changes the answer.</b> Adam divides every parameter's gradient "
            "by a running estimate of that same gradient's typical size. A "
            "sensitivity that is consistently ±100 and one that is "
            "consistently ±0.1 therefore produce steps of a very similar "
            "size — roughly the learning rate, in both cases. What survives "
            "the normalisation is the <b>sign and the relative pattern "
            "across weights</b>, plus any <i>sudden change</i> in magnitude, "
            "which the running average has not caught up with yet.<br><br>"
            "So the honest version of \"a big sensitivity means a big weight "
            "change\" is: it is true for one plain SGD step, and mostly false "
            "under Adam, which is one of the reasons Adam is what makes deep "
            "RL trainable at all. The critic's absolute scale drifts "
            "constantly as rewards leak backwards; an optimiser that cared "
            "about it would be permanently re-tuning itself.", "warn"))
        sm.add(body(
            "The magnitude does still matter in one place, and it is the "
            "dangerous one: a critic with a genuinely enormous local slope "
            "usually has it because the critic is <b>wrong</b> there — a "
            "region of action space nothing has ever visited, where the "
            "network extrapolates freely. The actor will happily follow that "
            "slope, arrive somewhere no data exists, and the critic's opinion "
            "there is fiction. That failure has a name in the offline-RL "
            "literature (extrapolation error) and its cheap mitigations are "
            "the ones already on the DDPG page: keep exploring so the visited "
            "region stays wide, weight-decay the critic so its slopes stay "
            "moderate, clip the gradient.", dim=True))
        self.add(sm)

        # ---- interactive: measure it -------------------------------------
        self.add(hline())
        self.add(title("Measure it: the sensitivity on a critic that was "
                       "actually trained"))

        iv = Card("read the slope off the surface, then check it by nudging")
        iv.add(body(
            "The same one-step task as the DDPG page — action a ∈ [−1,1], "
            "true Q*(s,a) = −(a − g(s))², so the surface is a parabola whose "
            "peak moves with the context. Pick a context and an action, and "
            "the panel below reports the sensitivity three ways: what "
            "backprop through the critic says, what a brute-force ± nudge of "
            "the trained critic says, and what the <i>true</i> Q would say. "
            "The first two agree to rounding always. The third agrees only "
            "where the critic has learned, which is the interesting part.",
            dim=True))
        hb = QHBoxLayout()
        hb.setSpacing(8)
        self.btn_train = QPushButton("Train the critic  (≈3 s)")
        self.btn_train.setObjectName("Primary")
        hb.addWidget(self.btn_train)
        hb.addStretch(1)
        iv.add_layout(hb)
        self.s_ctx = slider(-100, 100, 40)
        self.s_act = slider(-100, 100, -50)
        self.l_ctx, self.l_act = QLabel(), QLabel()
        iv.add_layout(slider_row("context s", self.s_ctx, self.l_ctx))
        iv.add_layout(slider_row("action a (where the actor stands)",
                                 self.s_act, self.l_act))
        self.st_bp = Stat("∂Q/∂a, backprop", "--", theme.ACCENT)
        self.st_fd = Stat("∂Q/∂a, by nudging", "--", theme.CYAN)
        self.st_true = Stat("∂Q*/∂a, the truth", "--", theme.WARN)
        self.st_move = Stat("actor is told to", "--", theme.GOOD)
        iv.add_layout(stat_row(self.st_bp, self.st_fd, self.st_true,
                               self.st_move))
        self.cG = MplCanvas(width=7.6, height=2.9, ncols=2)
        iv.add(self.cG)
        self.tG = body("Press <b>Train</b>.", dim=True)
        iv.add(self.tG)
        self.add(iv)
        self.agent = None
        self.btn_train.clicked.connect(self._train)
        for s in (self.s_ctx, self.s_act):
            s.valueChanged.connect(self._redraw)
        self._redraw()

        # ---- the dark room -----------------------------------------------
        dr = Card("the picture to keep")
        dr.add(body(
            "The actor is standing on a hillside in the dark. It cannot see "
            "the landscape, there is no map, and nobody will tell it where "
            "the summit is — nobody knows. What it can do is feel the slope "
            "under its feet, take one step in the uphill direction, and feel "
            "again. The critic is the ground. ∂Q/∂a is the slope felt through "
            "the boots.<br><br>"
            "Two things that picture gets right which a \"target\" picture "
            "gets wrong. First, the walker never learns the destination, only "
            "the next step — which is why training is a million small updates "
            "and not one solve. Second, <b>the ground is being rebuilt while "
            "the walker walks on it</b>: the critic is fitted to new targets "
            "every step, so a slope felt at step 10 000 is a slope on a "
            "different hill than the one at step 100. The two processes have "
            "to be kept at compatible speeds, which is precisely why the "
            "critic's learning rate is typically twice the actor's, and why "
            "TD3 goes further and updates the actor only every other step."))
        self.add(dr)

        self.add(callout(
            "<b>Carry forward.</b> ∂Q/∂a: one number per action dimension "
            "per sample, measured at the actor's current output, computed by "
            "the same backward pass that trains any network, sliced out of "
            "the critic's input gradient, negated, and used as the seed — not "
            "the target — of the actor's own backward pass. The next page "
            "opens the critic up and asks where in it the action should "
            "enter, which turns out to be a question about this exact "
            "gradient.", "good"))
        self.finish()

    # ------------------------------------------------------------------
    def on_show(self):
        if self.agent is None:
            self._train()

    def _train(self):
        self.btn_train.setEnabled(False)
        self.btn_train.setText("training…")
        self.btn_train.repaint()
        try:
            self.agent, _ = train_reach(episodes=1200, noise=0.3,
                                        use_targets=True, seed=3)
        finally:
            self.btn_train.setEnabled(True)
            self.btn_train.setText("Train the critic  (≈3 s)")
        self._redraw()

    def _redraw(self):
        ctx = self.s_ctx.value() / 100.0
        act = self.s_act.value() / 100.0
        self.l_ctx.setText(f"{ctx:+.2f}")
        self.l_act.setText(f"{act:+.2f}")

        c = self.cG
        c.clear()
        a1, a2 = c.axes
        acts = np.linspace(-1, 1, 300)
        true_q = np.array([ContextualReach.true_q([ctx], a) for a in acts])
        true_d = -2.0 * (act - ContextualReach.best_action([ctx]))

        a1.plot(acts, true_q, color=theme.TEXT_FAINT, lw=1.5, ls="--",
                label="true Q*")
        if self.agent is None:
            a1.set_xlabel("action a")
            c.legend(a1, loc="lower center")
            c.refresh()
            return

        ag = self.agent
        s_col = np.full((len(acts), 1), ctx)
        learned = ag.critic.forward(
            np.concatenate([s_col, acts.reshape(-1, 1)], axis=1)).ravel()

        # backprop: seed the critic's output with 1, read the action slice
        x = np.array([[ctx, act]])
        ag.critic.forward(x)
        dx = ag.critic.backward(np.ones((1, 1)))
        g_bp = float(dx[0, 1])
        # brute force, for the same reason the backprop page does it
        h = 1e-5
        qp = float(ag.critic.forward(np.array([[ctx, act + h]]))[0, 0])
        qm = float(ag.critic.forward(np.array([[ctx, act - h]]))[0, 0])
        g_fd = (qp - qm) / (2 * h)
        q_here = float(ag.critic.forward(x)[0, 0])

        self.st_bp.set(f"{g_bp:+.3f}")
        self.st_fd.set(f"{g_fd:+.3f}")
        self.st_true.set(f"{true_d:+.3f}")
        self.st_move.set("raise a" if g_bp > 0 else "lower a")
        self.st_move.set_color(theme.GOOD if g_bp * true_d > 0 else theme.BAD)

        a1.plot(acts, learned, color=theme.ACCENT, lw=2.2, label="learned Q")
        a1.scatter([act], [q_here], s=55, color=theme.GOOD, zorder=6)
        seg = np.linspace(act - 0.28, act + 0.28, 20)
        a1.plot(seg, q_here + g_bp * (seg - act), color=theme.WARN, lw=2.2,
                label="the slope handed to the actor")
        a1.axvline(ContextualReach.best_action([ctx]), color=theme.TEXT_FAINT,
                   lw=1.0, ls=":")
        a1.set_xlabel("action a")
        a1.set_ylabel("Q")
        a1.set_title(f"the critic at s = {ctx:+.2f}", fontsize=9)
        c.legend(a1, loc="lower center")

        grads = []
        for a in acts:
            ag.critic.forward(np.array([[ctx, a]]))
            grads.append(float(ag.critic.backward(np.ones((1, 1)))[0, 1]))
        a2.plot(acts, grads, color=theme.WARN, lw=2.2, label="learned ∂Q/∂a")
        a2.plot(acts, [-2.0 * (a - ContextualReach.best_action([ctx]))
                       for a in acts], color=theme.TEXT_FAINT, lw=1.4,
                ls="--", label="true ∂Q*/∂a")
        a2.axhline(0, color=theme.BORDER, lw=1.0)
        a2.scatter([act], [g_bp], s=55, color=theme.GOOD, zorder=6)
        a2.set_xlabel("action a")
        a2.set_ylabel("∂Q/∂a")
        a2.set_title("the sensitivity, across the whole action range",
                     fontsize=9)
        c.legend(a2, loc="upper right")
        c.refresh()

        agree = abs(g_bp - g_fd)
        self.tG.setText(
            f"<b>Backprop says {g_bp:+.3f}; nudging the critic by ±1e−5 says "
            f"{g_fd:+.3f}. They differ by {agree:.1e}</b> — floating point, "
            "nothing else. That is worth doing once in your life: the "
            "backward pass is not a different kind of object from the "
            "derivative, it is the derivative, computed cheaply.<br><br>"
            f"The truth here is {true_d:+.3f}, and the critic says "
            f"{g_bp:+.3f}. Where the two agree in <b>sign</b>, the actor gets "
            "pushed the right way — and note that the sign is all it needs; "
            "the critic can be badly wrong about the magnitude and the policy "
            "still improves. Where the signs disagree, the actor is being "
            "confidently walked downhill, and nothing in the algorithm can "
            "tell. Drag the action out to the edges, where the trained critic "
            "saw the fewest samples, and watch the right-hand curves come "
            "apart.")


# ==========================================================================
# PAGE -- inside the critic
# ==========================================================================

class CriticArchPage(Page):
    TITLE = "Inside the Critic: Two Inputs, One Number"
    SUBTITLE = ("A state and an action are not the same kind of thing. Where "
                "in the network they are allowed to meet is a real design "
                "decision, and it is a decision about ∂Q/∂a.")
    SECTION = SECTION
    NOTES = "deep RL"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>The critic is the only network in DDPG with two inputs of "
            "different kinds</b>, and they are unequal in every way that "
            "matters: the state may be 5 numbers or 500, the action is "
            "usually 1 to 8; the state is given, the action is chosen; and "
            "only one of the two needs a gradient taken with respect to it. "
            "Two standard architectures answer this differently.", "key"))

        # ---- the two architectures --------------------------------------
        d1 = Card("A · early fusion — concatenate at the input")
        self.d_early = BlockDiagram(width=7.6, height=2.3, ylim=(0, 2.3))
        d1.add(self.d_early)
        d1.add(body(
            "Glue s and a into one vector of length d<sub>s</sub> + "
            "d<sub>a</sub> and feed it to an ordinary MLP. <b>This is what "
            "this tutor's code does</b>, and you can see it in every "
            "<code>np.concatenate([s, a], axis=1)</code> in the training "
            "step.<br><br>"
            "&nbsp;&nbsp;• <b>For:</b> it is one network with nothing special "
            "in it. The action can interact with the state from the very "
            "first layer, which matters when the value genuinely depends on "
            "the combination — and it always does; that is what Q means. The "
            "input gradient comes back as one array and the action part is "
            "one slice.<br>"
            "&nbsp;&nbsp;• <b>Against:</b> when d<sub>s</sub> ≫ "
            "d<sub>a</sub> — 60 state numbers against 2 action numbers — the "
            "action arrives as 3% of the input vector and can be drowned. "
            "The first layer's weights on the action columns have to grow "
            "large to compete, and large weights on the exact path the "
            "actor's gradient travels down is not a comfortable place to be."))
        self.add(d1)

        d2 = Card("B · late fusion — the action joins at the second hidden "
                  "layer")
        self.d_late = BlockDiagram(width=7.6, height=2.3, ylim=(0, 2.3))
        d2.add(self.d_late)
        d2.add(body(
            "Run the state alone through one hidden layer first, then "
            "concatenate the action onto that layer's <i>output</i> and carry "
            "on. <b>This is the original DDPG paper's critic</b>, and it is "
            "still the common choice when the state is large or structured "
            "(images, many joints, a history buffer).<br><br>"
            "&nbsp;&nbsp;• <b>For:</b> the state gets processed into features "
            "before the action has to be compared against it, so the action "
            "meets a compact, meaningful representation rather than raw "
            "sensor numbers. When the state path is a convolutional stack, "
            "this is the only sane arrangement — you would not convolve over "
            "a torque.<br>"
            "&nbsp;&nbsp;• <b>For, and this one is underrated:</b> the "
            "action's path to the output is <b>shorter</b>. Fewer layers "
            "between the action input and Q means fewer weight-times-slope "
            "factors in ∂Q/∂a, so the actor's signal is less attenuated and "
            "less distorted.<br>"
            "&nbsp;&nbsp;• <b>Against:</b> the state features are computed "
            "without knowing the action, so the first layer cannot form "
            "anything that depends on the two jointly. And it is a custom "
            "network — no longer a plain <code>MLP([...])</code> call."))
        self.add(d2)

        cmp_ = Card("choosing, on the numbers rather than the fashion")
        cmp_.add(_table(
            ["Situation", "Pick", "Because"],
            [("d_s and d_a comparable (5 and 2, as in the case study)",
              "early fusion",
              "the action is a fifth of the input — it cannot be drowned, and "
              "you get to keep a plain MLP with no custom code"),
             ("d_s ≫ d_a  (a 100-number state, a 2-number action)",
              "late fusion",
              "the action would otherwise be 2% of the input vector and the "
              "first layer would have to learn to amplify it"),
             ("state is an image or a sequence", "late fusion, always",
              "the state path is a conv net or an RNN and the action has no "
              "business inside it"),
             ("you need the crispest possible ∂Q/∂a",
              "late fusion, or even inject the action at the LAST hidden "
              "layer",
              "shorter path, fewer slope factors, less attenuation. The limit "
              "of this idea is Q(s,a) = f(φ(s), a) with f small and almost "
              "linear in a"),
             ("you are debugging and want fewer moving parts", "early fusion",
              "one network, one slice, nothing to get wrong")],
            col0=200, colw=230, height=330))
        self.add(cmp_)

        # ---- the gradient path -------------------------------------------
        self.add(hline())
        self.add(title("What the merge point does to the actor's signal"))

        gp = Card("count the factors between the action input and Q")
        gp.add(body(
            "Every layer the action's signal passes through contributes one "
            "weight matrix and one activation slope to the product, and "
            "sums over that layer's width. More layers means a more "
            "expressive dependence on the action, and also a more attenuated "
            "and more easily-saturated gradient coming back. Slide the merge "
            "point and read the trade directly."))
        self.s_merge = slider(0, 3, 0)
        self.s_ds = slider(2, 120, 5)
        self.s_da = slider(1, 8, 2)
        self.l_merge, self.l_ds, self.l_da = QLabel(), QLabel(), QLabel()
        gp.add_layout(slider_row("action enters after N layers", self.s_merge,
                                 self.l_merge))
        gp.add_layout(slider_row("state dimension d_s", self.s_ds, self.l_ds))
        gp.add_layout(slider_row("action dimension d_a", self.s_da, self.l_da))
        self.st_hops = Stat("layers on the action path", "--", theme.ACCENT)
        self.st_share = Stat("action's share of layer 1", "--", theme.WARN)
        self.st_paths = Stat("distinct paths a → Q", "--", theme.VIOLET)
        self.st_att = Stat("typical attenuation", "--", theme.CYAN)
        gp.add_layout(stat_row(self.st_hops, self.st_share, self.st_paths,
                               self.st_att))
        self.cM = MplCanvas(width=7.6, height=2.6, ncols=2)
        gp.add(self.cM)
        self.tM = body("", dim=True)
        gp.add(self.tM)
        self.add(gp)
        for s in (self.s_merge, self.s_ds, self.s_da):
            s.valueChanged.connect(self._redraw_merge)
        self._redraw_merge()

        gp2 = Card("three rules for the critic that all come from ∂Q/∂a")
        gp2.add(body(
            "The critic is not just a regressor. It is a regressor whose "
            "<b>input derivative is a product</b>, and that changes three "
            "choices you would otherwise make freely:<br><br>"
            "&nbsp;&nbsp;<b>1 · Keep the action's units sane.</b> The actor "
            "outputs tanh ∈ [−1,1] and the code multiplies by a_max. Feed "
            "the critic the <i>scaled</i> action and its first-layer weights "
            "on those columns must be ~1/a_max to compete with the state "
            "columns; feed it the normalised action and they need not be. "
            "Either works — but the a_max factor must then appear in the "
            "gradient handed back, which is exactly the "
            "<code>* c.a_max</code> on the actor's backward call.<br>"
            "&nbsp;&nbsp;<b>2 · No dropout, and no batch norm, on the action "
            "path.</b> Both make Q(s,a) depend on something other than (s,a) "
            "— a random mask, or the other 63 samples — so ∂Q/∂a stops being "
            "a statement about this state's action. Page 78 has the four "
            "reasons; this is the sharpest of them.<br>"
            "&nbsp;&nbsp;<b>3 · Prefer smooth activations near the action "
            "input if the actor is struggling.</b> ReLU's derivative is a "
            "step function, so ∂Q/∂a is <b>piecewise constant</b> in a: the "
            "actor is being handed a slope that does not change as it moves, "
            "until suddenly it does. tanh gives a slope that varies "
            "continuously, which is a gentler thing to hill-climb on. This is "
            "one honest reason the tutor's small networks are tanh "
            "throughout, beyond their size."))
        self.add(gp2)

        # ---- what the code builds ----------------------------------------
        cd = Card("what the code actually constructs")
        cd.add(_code(
            "self.actor    = MLP([dim_s, h, h, dim_a], out_act=\"tanh\")\n"
            "self.critic   = MLP([dim_s + dim_a, h, h, 1], out_act=\"linear\")\n"
            "self.actor_t  = MLP([dim_s, h, h, dim_a], out_act=\"tanh\")\n"
            "self.critic_t = MLP([dim_s + dim_a, h, h, 1], out_act=\"linear\")\n"
            "self.actor_t.copy_from(self.actor, tau=1.0)    # start identical\n"
            "self.critic_t.copy_from(self.critic, tau=1.0)"))
        cd.add(body(
            "Four lines, and every asymmetry between the actor and the critic "
            "is visible in them: the critic's input is wider by "
            "d<sub>a</sub> (early fusion), its output is <b>1</b> and "
            "<b>linear</b> (a value has no bound), the actor's output is "
            "d<sub>a</sub> and <b>tanh</b> (an action does), and the targets "
            "are constructed identically and then immediately copied so that "
            "training starts from agreement rather than from two random "
            "opinions.", dim=True))
        self.add(cd)

        self.add(callout(
            "<b>Carry forward.</b> Early fusion when the action is a "
            "reasonable fraction of the input; late fusion when the state "
            "dwarfs it or needs its own processing. The merge point sets how "
            "many weight-and-slope factors sit between the action and the "
            "value, and that product is the actor's entire training signal — "
            "so the critic's architecture is, in the end, a decision about "
            "how clearly the actor can hear.", "good"))

        self._draw_diagrams()
        self.finish()

    # ------------------------------------------------------------------
    def _draw_diagrams(self):
        d = self.d_early
        d.block(0.75, 1.55, "state s", colour=theme.CYAN, w=1.1,
                sub="d_s numbers")
        d.block(0.75, 0.60, "action a", colour=theme.GOOD, w=1.1,
                sub="d_a numbers")
        d.block(2.30, 1.10, "concat", colour=theme.TEXT_FAINT, w=1.0,
                sub="d_s + d_a")
        d.arrow(1.30, 1.55, 1.80, 1.20)
        d.arrow(1.30, 0.60, 1.80, 1.00)
        d.block(3.85, 1.10, "hidden 1", colour=theme.ACCENT, w=1.2,
                sub="64, tanh")
        d.block(5.40, 1.10, "hidden 2", colour=theme.ACCENT, w=1.2,
                sub="64, tanh")
        d.block(6.95, 1.10, "Q(s,a)", colour=theme.VIOLET, w=1.1,
                sub="1, linear")
        d.arrow(2.80, 1.10, 3.25, 1.10)
        d.arrow(4.45, 1.10, 4.80, 1.10)
        d.arrow(6.00, 1.10, 6.40, 1.10)
        d.arrow(6.40, 0.42, 1.30, 0.42, colour=theme.WARN)
        d.note(3.9, 0.24, "∂Q/∂a comes back through THREE weight matrices",
               colour=theme.WARN, fontsize=7.2)
        d.done()

        d = self.d_late
        d.block(0.75, 1.65, "state s", colour=theme.CYAN, w=1.1,
                sub="d_s numbers")
        d.block(2.30, 1.65, "state path", colour=theme.ACCENT, w=1.3,
                sub="64, tanh (or conv)")
        d.arrow(1.30, 1.65, 1.65, 1.65)
        d.block(0.75, 0.62, "action a", colour=theme.GOOD, w=1.1,
                sub="d_a numbers")
        d.block(3.95, 1.15, "concat", colour=theme.TEXT_FAINT, w=1.0,
                sub="64 + d_a")
        d.arrow(2.95, 1.65, 3.45, 1.28)
        d.arrow(1.30, 0.62, 3.45, 1.02, colour=theme.GOOD)
        d.block(5.45, 1.15, "hidden 2", colour=theme.ACCENT, w=1.2,
                sub="64, tanh")
        d.block(6.95, 1.15, "Q(s,a)", colour=theme.VIOLET, w=1.1,
                sub="1, linear")
        d.arrow(4.45, 1.15, 4.85, 1.15)
        d.arrow(6.05, 1.15, 6.40, 1.15)
        d.arrow(6.40, 0.30, 1.30, 0.30, colour=theme.WARN)
        d.note(3.9, 0.12, "∂Q/∂a comes back through TWO — a shorter, cleaner "
                          "path", colour=theme.WARN, fontsize=7.2)
        d.done()

    def _redraw_merge(self):
        m = self.s_merge.value()          # layers of state-only processing
        ds = self.s_ds.value()
        da = self.s_da.value()
        self.l_merge.setText(f"{m}")
        self.l_ds.setText(f"{ds}")
        self.l_da.setText(f"{da}")

        h = 64
        hops = 3 - m                       # weight matrices on the action path
        share = da / (ds + da) if m == 0 else da / (h + da)
        paths = h ** max(0, hops - 1)
        # a representative attenuation: one tanh slope per hop, |sigma'| ~ 0.6
        att = 0.6 ** max(0, hops - 1)

        self.st_hops.set(f"{hops}")
        self.st_share.set(f"{100*share:.1f}%")
        self.st_share.set_color(theme.BAD if share < 0.03 else theme.GOOD)
        self.st_paths.set(f"{paths:,}")
        self.st_att.set(f"×{att:.2f}")
        self.st_att.set_color(theme.GOOD if att > 0.5 else theme.WARN)

        c = self.cM
        c.clear()
        a1, a2 = c.axes
        ms = [0, 1, 2, 3]
        a1.bar([f"after {k}" for k in ms],
               [ds if k == 0 else h for k in ms], color=theme.ACCENT,
               label="other inputs at the merge")
        a1.bar([f"after {k}" for k in ms], [da] * 4,
               bottom=[ds if k == 0 else h for k in ms], color=theme.GOOD,
               label="the action")
        a1.set_ylabel("width of the merged vector")
        a1.set_title("how much of the merge is the action", fontsize=9)
        c.legend(a1, loc="upper left")

        a2.plot(ms, [0.6 ** max(0, (3 - k) - 1) for k in ms],
                color=theme.WARN, lw=2.2, marker="o", ms=4,
                label="surviving fraction of ∂Q/∂a")
        a2.axvline(m, color=theme.ACCENT, lw=1.2, ls="--")
        a2.set_ylim(0, 1.05)
        a2.set_xlabel("layers of state-only processing before the merge")
        a2.set_title("later merge = shorter gradient path", fontsize=9)
        c.legend(a2, loc="lower right")
        c.refresh()

        if m == 0 and share < 0.05:
            self.tM.setText(
                f"<b>Early fusion with d_s = {ds} and d_a = {da}: the action "
                f"is {100*share:.1f}% of the input vector.</b> The critic can "
                "still learn this — nothing is broken — but the first layer "
                "must devote unusually large weights to a handful of columns "
                "in order to hear the action at all, and those large weights "
                "sit on the exact path the actor's gradient comes back down. "
                "This is the regime where the paper's late fusion earns its "
                "extra code.")
        elif m == 3:
            self.tM.setText(
                "<b>Merging after three layers means the action is "
                "concatenated straight onto the output stage</b> — Q becomes "
                "nearly linear in a, so ∂Q/∂a is nearly constant and the "
                "actor gets a beautifully clean, un-attenuated signal. The "
                "price is that the critic can barely represent a curved "
                "dependence on the action, and a Q with no curvature in a has "
                "no interior maximum to climb toward: the actor will simply "
                "run to the ±a_max bound. This end of the slider is a real "
                "failure mode, not just a trade-off.")
        else:
            self.tM.setText(
                f"<b>{hops} weight matrices between the action input and Q, "
                f"about {paths:,} distinct paths, roughly ×{att:.2f} of the "
                "signal surviving the slope factors.</b> This is the shape "
                "the DDPG paper chose and it is a reasonable default: enough "
                "depth after the merge to represent a curved Q(·, a), few "
                "enough hops that the actor's gradient is not mush.")


# ==========================================================================
# PAGE -- one rulebook
# ==========================================================================

class AgentSkeletonPage(Page):
    TITLE = "One Rulebook: Experience, Buffer, act()"
    SUBTITLE = ("Every agent in this tutor is the same five objects. What "
                "changes between Q-learning, DQN and DDPG is smaller than it "
                "looks — and PPO is where the mould actually breaks.")
    SECTION = SECTION
    NOTES = "deep RL"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add(callout(
            "<b>Yes — the scaffolding is genuinely shared, and it is worth "
            "trusting that instinct.</b> A transition record, a step result, "
            "an environment with reset/step, a store of past experience and a "
            "function that turns a state into an action: those five appear in "
            "tabular Q-learning, in DQN, in DDPG, in SAC. The algorithm is "
            "what fills them in. But two of the five are not as universal as "
            "they look, and PPO is the counter-example that shows exactly "
            "which two.", "key"))

        # ---- the five objects --------------------------------------------
        fv = Card("the five objects, and how much of each is really shared")
        fv.add(_table(
            ["Object", "Tabular Q-learning", "DQN", "DDPG", "PPO"],
            [("Transition\n(s, a, r, s′, done)",
              "identical", "identical",
              "identical — a and s are float vectors instead of ints",
              "NOT identical: needs log π(a|s) and V(s) recorded AT "
              "COLLECTION TIME as well"),
             ("StepResult\n(s′, r, done, info)",
              "identical", "identical", "identical",
              "identical — this one really is universal"),
             ("Env\n.reset() / .step(a)",
              "identical", "identical",
              "identical; action space is a box, not a set",
              "identical"),
             ("Experience store",
              "usually NONE — update online, discard",
              "replay buffer, uniform sample of 32–256",
              "replay buffer, uniform sample of 64–256",
              "rollout buffer: fixed length, ORDERED, used for a few epochs, "
              "then cleared"),
             ("act(s)",
              "argmax over a row of the table, ε-greedy",
              "argmax over the network's output head, ε-greedy",
              "μ(s) + Gaussian noise — no argmax anywhere",
              "sample from π(a|s), and record the log-probability of what was "
              "sampled")],
            col0=130, colw=200, height=430))
        fv.add(body(
            "Read the rows: three of the five are shared essentially "
            "verbatim across all four algorithms. The two that are not — the "
            "experience store and act() — are the two that encode the "
            "algorithm's actual commitments.", dim=True))
        self.add(fv)

        # ---- the buffer ---------------------------------------------------
        self.add(hline())
        self.add(title("The buffer: same class, three different contracts"))

        bf = Card("what 'add' and 'sample' mean in each case")
        bf.add(body(
            "The mechanics of a ring buffer — write at an index, wrap when "
            "full, overwrite the oldest — are identical everywhere the "
            "structure appears, and that is the tutor's implementation:"))
        bf.add(_code(get_source(ReplayBuffer.push)))
        bf.add(body(
            "What differs is the <b>contract</b> around it:"))
        bf.add(_table(
            ["", "Tabular Q-learning", "DQN / DDPG", "PPO"],
            [("How many samples per update", "one — the transition that just "
              "happened", "a uniform random minibatch of 64–256",
              "the entire rollout, cut into minibatches, several passes"),
             ("Are old samples valid?",
              "the question does not arise — nothing is stored",
              "YES. A transition is a fact about the world and does not "
              "expire when the policy changes",
              "NO. The gradient is weighted by how likely the CURRENT policy "
              "is to have taken that action, and once the policy has moved "
              "far enough the correction blows up"),
             ("Lifetime", "one step", "hundreds of thousands of steps; "
              "capacity ~1e5–1e6", "one iteration, then cleared — typically "
              "2048 steps"),
             ("Order matters?", "n/a", "no — order is deliberately destroyed, "
              "that is the point of sampling uniformly",
              "YES. Advantages are computed by walking the trajectory "
              "backwards (GAE), so the rollout must stay in sequence"),
             ("Why", "online TD update", "decorrelate and reuse",
              "on-policy estimation requires data from the policy being "
              "updated")],
            col0=170, colw=215, height=380))
        bf.add(callout(
            "<b>So \"PPO has a buffer too\" is true and misleading.</b> It "
            "has a <i>rollout</i> buffer, which is a different data structure "
            "with different fields, a different access pattern (ordered, not "
            "random), and a lifetime of one iteration rather than the whole "
            "run. If you tried to reuse a replay buffer for PPO you would get "
            "silently wrong advantages, because the values stored alongside "
            "each transition were produced by a policy that no longer "
            "exists.<br><br>"
            "The one-line version: <b>a replay buffer stores facts about the "
            "environment; a rollout buffer stores facts about a policy.</b> "
            "Facts about the environment keep. Facts about a policy expire "
            "the moment you update it.", "key"))
        self.add(bf)

        # ---- act() --------------------------------------------------------
        self.add(hline())
        self.add(title("act(): the function whose body names the algorithm"))

        ac = Card("four bodies, side by side")
        ac.add(_code(
            "# tabular Q-learning -- a lookup and a comparison\n"
            "def act(self, s):\n"
            "    if rng.random() < self.eps:\n"
            "        return rng.integers(self.n_actions)\n"
            "    return int(np.argmax(self.Q[s]))          # argmax over a ROW\n"
            "\n"
            "# DQN -- the row became a forward pass, nothing else changed\n"
            "def act(self, s):\n"
            "    if rng.random() < self.eps:\n"
            "        return rng.integers(self.n_actions)\n"
            "    return int(np.argmax(self.net.forward(s)))  # argmax over OUTPUTS\n"
            "\n"
            "# DDPG -- no argmax exists; the network IS the argmax\n"
            "def act(self, s, noise):\n"
            "    a = self.actor.forward(s) * self.a_max\n"
            "    return np.clip(a + rng.normal(0, noise), -a_max, a_max)\n"
            "\n"
            "# PPO -- sample, and REMEMBER how likely the sample was\n"
            "def act(self, s):\n"
            "    mu, sigma = self.policy.forward(s)\n"
            "    a = mu + sigma * rng.normal(size=mu.shape)\n"
            "    return a, log_prob(a, mu, sigma), self.value.forward(s)"))
        ac.add(body(
            "<b>Four things to notice, in order of how much they matter.</b>"
            "<br><br>"
            "&nbsp;&nbsp;<b>1.</b> The first two are the same function. DQN "
            "did not change the decision rule at all — it changed how the row "
            "of Q values is produced. That is why DQN is \"Q-learning with a "
            "network\" and nothing more.<br>"
            "&nbsp;&nbsp;<b>2.</b> DDPG's body contains no argmax and no "
            "comparison. The maximisation was moved into training and baked "
            "into weights; at runtime it is one forward pass with a bounded "
            "execution time, which is the only reason it can live in a "
            "control loop.<br>"
            "&nbsp;&nbsp;<b>3.</b> Exploration is in a different place in "
            "each. ε-greedy sometimes ignores the policy entirely; Gaussian "
            "noise perturbs a policy that has no randomness of its own; PPO's "
            "policy <i>is</i> the randomness, so there is nothing to add.<br>"
            "&nbsp;&nbsp;<b>4.</b> PPO's act() <b>returns three things</b>, "
            "and that is the structural break. Its update needs the "
            "probability the old policy assigned to the action it took, and "
            "that number cannot be recovered later — the old policy is gone. "
            "So it is recorded at collection time and carried in the "
            "transition. This single requirement is what makes PPO on-policy "
            "and what makes its buffer disposable."))
        self.add(ac)

        # ---- the training loop --------------------------------------------
        tl = Card("and the loop around all of it")
        tl.add(_code(
            "s = env.reset()\n"
            "for t in range(total_steps):\n"
            "    a = agent.act(s)                     # <- differs per algorithm\n"
            "    s2, r, done, info = env.step(a)      # <- identical everywhere\n"
            "    agent.store(s, a, r, s2, done)       # <- differs per algorithm\n"
            "    agent.train_step()                   # <- differs per algorithm\n"
            "    s = s2 if not done else env.reset()"))
        tl.add(body(
            "Seven lines, and they are the same seven for every model-free "
            "method in this tutor. Tabular Q-learning fills in store() as a "
            "no-op and train_step() as one arithmetic update; DQN and DDPG "
            "fill in store() as a buffer push and train_step() as a "
            "minibatch; PPO fills in train_step() as \"do nothing for 2 047 "
            "steps, then do 10 epochs of work and clear everything\". The "
            "skeleton does not care.", dim=True))
        tl.add(callout(
            "<b>The one field in that loop people get wrong, and it is worth "
            "a paragraph.</b> <code>done</code> is doing two different jobs "
            "and most environments conflate them:<br><br>"
            "&nbsp;&nbsp;• <b>Termination</b> — the episode genuinely ended. "
            "The agent fell over; there is no future; the value of s′ really "
            "is zero, and the target must be y = r with no bootstrap "
            "term.<br>"
            "&nbsp;&nbsp;• <b>Truncation</b> — you stopped it, at a 1 000-step "
            "time limit. The world would have carried on and s′ has a "
            "perfectly real value; cutting the bootstrap here teaches the "
            "critic that every state 1 000 steps in is worthless.<br><br>"
            "In the target y = r + γ(1−d)Q′(s′,a′), <b>d must be the "
            "termination flag only</b>. Modern APIs return them separately "
            "(<code>terminated</code>, <code>truncated</code>) precisely "
            "because this bug is so common and so quiet — nothing crashes, "
            "the agent just becomes mysteriously short-sighted.", "warn"))
        self.add(tl)

        # ---- interactive comparison ---------------------------------------
        self.add(hline())
        self.add(title("Pick two and see exactly what differs"))

        pk = Card("the diff, field by field")
        row = QHBoxLayout()
        row.setSpacing(10)
        self.cmb_a = QComboBox()
        self.cmb_b = QComboBox()
        for c in ("Tabular Q-learning", "DQN", "DDPG", "PPO"):
            self.cmb_a.addItem(c)
            self.cmb_b.addItem(c)
        self.cmb_a.setCurrentIndex(0)
        self.cmb_b.setCurrentIndex(2)
        pk.add_layout(labelled("Compare", self.cmb_a, width=70))
        pk.add_layout(labelled("with", self.cmb_b, width=70))
        self.diff_out = body("")
        pk.add(self.diff_out)
        self.add(pk)
        self.cmb_a.currentIndexChanged.connect(self._diff)
        self.cmb_b.currentIndexChanged.connect(self._diff)
        self._diff()

        self.add(callout(
            "<b>Carry forward.</b> The transition record, the step result and "
            "the environment interface are genuinely universal — build them "
            "once. The experience store and act() are where the algorithm "
            "lives: <b>store facts about the world and sample them randomly "
            "forever</b> (off-policy: Q-learning, DQN, DDPG, TD3, SAC), or "
            "<b>store facts about the current policy and throw them away when "
            "it moves</b> (on-policy: PPO, A2C, TRPO). Every other difference "
            "you have read about follows from that one.", "good"))
        self.finish()

    # ------------------------------------------------------------------
    def _diff(self):
        a = self.cmb_a.currentText()
        b = self.cmb_b.currentText()
        if a == b:
            self.diff_out.setText(
                "<b>Same algorithm on both sides.</b> Pick two different "
                "ones — the interesting pairs are Q-learning vs DDPG (how "
                "little changes) and DDPG vs PPO (how much).")
            return

        facts = {
            "Tabular Q-learning": dict(
                store="nothing — the update happens on the spot and the "
                      "transition is discarded",
                act="argmax over a row of a table, with ε-greedy on top",
                data="on-policy behaviour, off-policy target (it learns about "
                     "the greedy policy while behaving ε-greedily)",
                fn="none — Q is a literal array",
                spec="converges to Q* with probability 1, which no other "
                     "column here can claim"),
            "DQN": dict(
                store="replay buffer, uniform minibatch",
                act="argmax over the network's action-head outputs, ε-greedy",
                data="off-policy",
                fn="one network, s → one value per discrete action",
                spec="discrete actions only; the argmax is a scan over a "
                     "fixed list"),
            "DDPG": dict(
                store="replay buffer, uniform minibatch",
                act="μ(s) + Gaussian noise; no comparison of any kind",
                data="off-policy",
                fn="two networks plus two frozen copies; critic is Q(s,a)",
                spec="continuous actions; the argmax is amortised into the "
                     "actor's weights"),
            "PPO": dict(
                store="rollout buffer: ordered, fixed length, cleared every "
                      "iteration",
                act="sample from π(a|s) AND record log π(a|s) and V(s)",
                data="on-policy — old data is invalid the moment the policy "
                     "moves",
                fn="policy network (mean and spread) plus a V critic",
                spec="a clipped ratio that refuses to let the policy move far "
                     "in one update"),
        }
        fa, fb = facts[a], facts[b]
        rows = [("What it stores", "store"), ("How it acts", "act"),
                ("Data regime", "data"), ("Function approximation", "fn"),
                ("Its defining feature", "spec")]
        html = [f"<b>{a}</b> versus <b>{b}</b><br><br>"]
        same = []
        for label, key in rows:
            if fa[key] == fb[key]:
                same.append(label)
                continue
            html.append(
                f"<b>{label}</b><br>"
                f"&nbsp;&nbsp;• {a}: {fa[key]}<br>"
                f"&nbsp;&nbsp;• {b}: {fb[key]}<br><br>")
        html.append(
            "<b>Identical in both:</b> the transition record's core fields "
            "(s, a, r, s′, done), the StepResult, the environment interface, "
            "and the seven-line training loop"
            + (", plus " + ", ".join(same).lower() if same else "")
            + ".")
        self.diff_out.setText("".join(html))
