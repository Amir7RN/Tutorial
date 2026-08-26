"""
deeprl.py -- DDPG written out from scratch, so that nothing about it is a
library call you have to take on faith.

Everything else in rlcore/ is plain Python and stdlib. This file is the one
exception: it uses numpy, because a from-scratch MLP in Python lists would be
slow enough to make the pages unusable. Nothing else changes -- there is no
autograd, no framework, no hidden optimiser. Forward pass, backward pass and
Adam are all written below, in about a hundred lines, and every gradient in
DDPG is derived by hand.

The pieces, in the order the DDPG page uses them:

    Dense, MLP        a two-layer network with tanh hidden units. `backward`
                      returns the gradient with respect to its INPUT as well
                      as filling in the weight gradients -- that return value
                      is not decoration, it is exactly how dQ/da reaches the
                      actor.

    Adam              the optimiser from the Adam page, per-parameter.

    ReplayBuffer      a ring buffer of (s, a, r, s', done). Off-policy
                      learning lives or dies on this: it is what lets a
                      transition collected under an old policy still be
                      useful, and what breaks the correlation between
                      consecutive samples.

    DDPG              four networks -- actor, critic, and a slow-moving copy
                      of each -- plus the three equations that define the
                      algorithm:

                        y  = r + gamma (1-done) Q'(s', mu'(s'))     the target
                        L  = mean (Q(s,a) - y)^2                    critic loss
                        grad_theta J = dQ/da * dmu/dtheta           actor update

    ContextualReach   a one-step continuous task whose true Q(s,a) is known
                      in closed form, so the learned critic can be plotted
                      against the truth. This is the page's microscope.

    GaitTuneEnv       a multi-step stand-in for the knee-prosthesis tuning
                      loop: one step is one gait cycle, the state is how far
                      four gait landmarks and the phase lag sit from a
                      reference, and the action nudges two impedance weights.
                      It is a TOY with a known optimum, not anyone's plant.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np


# ==========================================================================
# A network, with the backward pass written out
# ==========================================================================

class Dense:
    """
    One fully connected layer: y = act(x @ W + b).

    Holds its own gradients (gW, gb) and its own Adam state, because at this
    size a per-layer optimiser is simpler to read than a global parameter
    vector and costs nothing.
    """

    def __init__(self, n_in: int, n_out: int, act: str = "tanh", rng=None,
                 scale: float | None = None):
        rng = rng or np.random.default_rng(0)
        # He/Xavier-ish: keep the pre-activation variance near 1 so tanh does
        # not saturate on the first forward pass
        s = scale if scale is not None else math.sqrt(1.0 / n_in)
        self.W = rng.uniform(-s, s, size=(n_in, n_out))
        self.b = np.zeros(n_out)
        self.act = act
        self.gW = np.zeros_like(self.W)
        self.gb = np.zeros_like(self.b)
        # Adam moments
        self._mW = np.zeros_like(self.W)
        self._vW = np.zeros_like(self.W)
        self._mb = np.zeros_like(self.b)
        self._vb = np.zeros_like(self.b)
        self._t = 0
        self._x = None
        self._z = None

    def forward(self, x: np.ndarray) -> np.ndarray:
        self._x = x                      # cached: the backward pass needs it
        self._z = x @ self.W + self.b
        if self.act == "tanh":
            return np.tanh(self._z)
        if self.act == "relu":
            return np.maximum(self._z, 0.0)
        return self._z                   # linear

    def backward(self, dout: np.ndarray) -> np.ndarray:
        """
        Given dL/d(output), fill gW and gb and return dL/d(input).

        The returned value is what lets one network's gradient flow into
        another one's -- in DDPG, out of the critic and into the actor.
        """
        if self.act == "tanh":
            dz = dout * (1.0 - np.tanh(self._z) ** 2)
        elif self.act == "relu":
            dz = dout * (self._z > 0.0)
        else:
            dz = dout
        n = max(1, self._x.shape[0])
        self.gW = self._x.T @ dz / n
        self.gb = dz.mean(axis=0)
        return dz @ self.W.T

    def adam(self, lr: float, b1=0.9, b2=0.999, eps=1e-8):
        """The optimiser from the Adam page, applied to this layer."""
        self._t += 1
        for p, g, m, v in ((self.W, self.gW, self._mW, self._vW),
                           (self.b, self.gb, self._mb, self._vb)):
            m *= b1
            m += (1 - b1) * g
            v *= b2
            v += (1 - b2) * g * g
            mhat = m / (1 - b1 ** self._t)
            vhat = v / (1 - b2 ** self._t)
            p -= lr * mhat / (np.sqrt(vhat) + eps)

    def copy_from(self, other: "Dense", tau: float = 1.0):
        """Polyak / soft update:  theta' <- tau theta + (1-tau) theta'."""
        self.W += tau * (other.W - self.W)
        self.b += tau * (other.b - self.b)


class MLP:
    """A stack of Dense layers. Two hidden layers is plenty at this scale."""

    def __init__(self, sizes: list[int], out_act: str = "linear", rng=None,
                 hidden_act: str = "tanh"):
        self.layers: list[Dense] = []
        for i in range(len(sizes) - 1):
            last = i == len(sizes) - 2
            self.layers.append(Dense(sizes[i], sizes[i + 1],
                                     act=out_act if last else hidden_act,
                                     rng=rng,
                                     scale=3e-3 if last else None))

    def forward(self, x: np.ndarray) -> np.ndarray:
        for l in self.layers:
            x = l.forward(x)
        return x

    def backward(self, dout: np.ndarray) -> np.ndarray:
        for l in reversed(self.layers):
            dout = l.backward(dout)
        return dout                      # dL/d(network input)

    def adam(self, lr: float):
        for l in self.layers:
            l.adam(lr)

    def copy_from(self, other: "MLP", tau: float = 1.0):
        for a, b in zip(self.layers, other.layers):
            a.copy_from(b, tau)

    def n_params(self) -> int:
        return sum(l.W.size + l.b.size for l in self.layers)


# ==========================================================================
# Replay buffer -- what makes the method OFF-policy
# ==========================================================================

class ReplayBuffer:
    """
    A ring buffer of transitions.

    Two jobs, and they are separate:

      1. DECORRELATION. Consecutive steps of one gait cycle look almost
         identical. Training on them in order is training on the same sample
         many times; sampling uniformly from a large buffer breaks that.

      2. REUSE. A transition is a fact about the environment -- "from here,
         that action gave this reward and led there". That fact does not stop
         being true when the policy changes, so it can be replayed for the
         rest of training. This is precisely what "off-policy" buys, and it
         is why DDPG needs orders of magnitude fewer real robot steps than an
         on-policy method like PPO.
    """

    def __init__(self, capacity: int, dim_s: int, dim_a: int):
        self.cap = capacity
        self.s = np.zeros((capacity, dim_s))
        self.a = np.zeros((capacity, dim_a))
        self.r = np.zeros((capacity, 1))
        self.s2 = np.zeros((capacity, dim_s))
        self.d = np.zeros((capacity, 1))
        self.idx = 0
        self.full = False

    def __len__(self) -> int:
        return self.cap if self.full else self.idx

    def push(self, s, a, r, s2, done):
        i = self.idx
        self.s[i], self.a[i], self.r[i] = s, a, r
        self.s2[i], self.d[i] = s2, float(done)
        self.idx += 1
        if self.idx >= self.cap:
            self.idx, self.full = 0, True

    def sample(self, n: int, rng):
        j = rng.integers(0, len(self), size=n)
        return self.s[j], self.a[j], self.r[j], self.s2[j], self.d[j]


# ==========================================================================
# DDPG
# ==========================================================================

@dataclass
class DDPGConfig:
    dim_s: int
    dim_a: int
    a_max: float = 1.0
    hidden: int = 64
    gamma: float = 0.95
    tau: float = 0.01            # soft-update rate for BOTH targets
    lr_actor: float = 1e-3
    lr_critic: float = 2e-3
    batch: int = 64
    capacity: int = 20000
    noise: float = 0.2           # exploration sigma, in action units
    seed: int = 0


class DDPG:
    """
    Deep Deterministic Policy Gradient.

    Four networks. Two of them do the learning and two of them exist only to
    hold still:

        actor   mu(s)      -> a          deterministic: one action, no
                                          distribution, no sampling
        critic  Q(s, a)    -> scalar     the thing that tells the actor which
                                          way is uphill
        actor'  mu'(s)     the target actor: a lagged copy, used only to ask
                            "what would we do in s'?"
        critic' Q'(s, a)   the target critic: a lagged copy, used only to
                            score that hypothetical next action

    The targets exist because of a circularity. The critic is trained to
    match r + gamma Q(s', mu(s')), which is built out of the critic itself.
    Regressing a network onto its own output moves the target every time you
    move the prediction, and the pair can run away together. Freezing a slow
    copy to build the target restores something to aim at.
    """

    def __init__(self, cfg: DDPGConfig):
        self.cfg = cfg
        rng = np.random.default_rng(cfg.seed)
        self.rng = rng
        h = cfg.hidden
        self.actor = MLP([cfg.dim_s, h, h, cfg.dim_a], out_act="tanh", rng=rng)
        self.critic = MLP([cfg.dim_s + cfg.dim_a, h, h, 1], out_act="linear",
                          rng=rng)
        self.actor_t = MLP([cfg.dim_s, h, h, cfg.dim_a], out_act="tanh", rng=rng)
        self.critic_t = MLP([cfg.dim_s + cfg.dim_a, h, h, 1], out_act="linear",
                            rng=rng)
        self.actor_t.copy_from(self.actor, tau=1.0)     # start identical
        self.critic_t.copy_from(self.critic, tau=1.0)
        self.buf = ReplayBuffer(cfg.capacity, cfg.dim_s, cfg.dim_a)
        self.critic_losses: list[float] = []
        self.q_mean: list[float] = []

    # -- acting --------------------------------------------------------
    def act(self, s, noise: float | None = None) -> np.ndarray:
        """
        mu(s), plus exploration noise.

        A deterministic policy explores nothing on its own -- given the same
        state it returns the same action forever. So the noise is not a
        detail of the implementation, it is the ONLY source of exploration
        the algorithm has. Set it to zero and DDPG stops learning anything it
        does not already know.
        """
        a = self.actor.forward(np.atleast_2d(s))[0] * self.cfg.a_max
        sig = self.cfg.noise if noise is None else noise
        if sig > 0:
            a = a + self.rng.normal(0.0, sig * self.cfg.a_max, size=a.shape)
        return np.clip(a, -self.cfg.a_max, self.cfg.a_max)

    def act_greedy(self, s) -> np.ndarray:
        return self.actor.forward(np.atleast_2d(s))[0] * self.cfg.a_max

    def q(self, s, a) -> np.ndarray:
        """Q(s,a) for arrays of states and actions, batched."""
        s = np.atleast_2d(s)
        a = np.atleast_2d(a)
        return self.critic.forward(np.concatenate([s, a], axis=1))

    # -- learning ------------------------------------------------------
    def train_step(self):
        """
        One gradient step on each network, in the order that matters:
        critic first (the actor needs a critic worth listening to), then the
        actor, then the two soft updates.
        """
        c = self.cfg
        if len(self.buf) < max(c.batch, 200):
            return
        s, a, r, s2, d = self.buf.sample(c.batch, self.rng)

        # ---- 1. the manufactured target -----------------------------
        # There is no label anywhere in RL. y is built out of ONE real
        # number -- the reward that actually happened -- plus the target
        # networks' guess about everything after it.
        a2 = self.actor_t.forward(s2) * c.a_max
        q2 = self.critic_t.forward(np.concatenate([s2, a2], axis=1))
        y = r + c.gamma * (1.0 - d) * q2

        # ---- 2. critic: plain regression onto y ---------------------
        q = self.critic.forward(np.concatenate([s, a], axis=1))
        err = q - y
        self.critic.backward(2.0 * err / c.batch)
        self.critic.adam(c.lr_critic)
        self.critic_losses.append(float(np.mean(err ** 2)))

        # ---- 3. actor: climb the critic -----------------------------
        # a_pi = mu(s); we want to move theta so that Q(s, mu(s)) goes UP.
        # The chain rule splits that into two factors that live in two
        # different networks:
        #     dJ/dtheta = dQ/da  (from the critic, at a = mu(s))
        #                 * dmu/dtheta  (from the actor)
        # so we run the critic backward to its INPUT, slice off the action
        # part, negate it (ascent, not descent) and hand it to the actor.
        a_pi = self.actor.forward(s) * c.a_max
        q_pi = self.critic.forward(np.concatenate([s, a_pi], axis=1))
        dx = self.critic.backward(np.ones((c.batch, 1)) / c.batch)
        dq_da = dx[:, c.dim_s:]                    # <- the only slice that matters
        self.actor.backward(-dq_da * c.a_max)
        self.actor.adam(c.lr_actor)
        self.q_mean.append(float(np.mean(q_pi)))

        # ---- 4. let the targets drift after them --------------------
        self.actor_t.copy_from(self.actor, c.tau)
        self.critic_t.copy_from(self.critic, c.tau)


# ==========================================================================
# Environment 1 -- one step, and the true Q is known
# ==========================================================================

class ContextualReach:
    """
    The smallest environment in which DDPG is not overkill.

    One step per episode. The state is a scalar context s in [-1, 1]; the
    action is a scalar a in [-1, 1]; the reward is

        r = -(a - g(s))^2,      g(s) = 0.8 sin(pi s / 2)

    Because the episode ends immediately, gamma never enters and the true
    action-value function is available in closed form:

        Q*(s, a) = -(a - g(s))^2

    That is the point of this toy. Everywhere else in deep RL you are
    guessing whether the critic learned anything real; here you can plot the
    critic's surface directly on top of the true one, and you can plot the
    actor's output on top of the true argmax.
    """

    dim_s, dim_a, a_max = 1, 1, 1.0

    def __init__(self, seed: int = 0):
        self.rng = np.random.default_rng(seed)
        self.s = np.zeros(1)

    @staticmethod
    def best_action(s) -> float:
        return 0.8 * math.sin(math.pi * float(np.ravel(s)[0]) / 2.0)

    @classmethod
    def true_q(cls, s, a) -> float:
        return -(float(a) - cls.best_action(s)) ** 2

    def reset(self):
        self.s = self.rng.uniform(-1.0, 1.0, size=1)
        return self.s.copy()

    def step(self, a):
        r = self.true_q(self.s, float(np.ravel(a)[0]))
        return self.s.copy(), r, True


# ==========================================================================
# Environment 2 -- one step is one gait cycle
# ==========================================================================

@dataclass
class GaitTuneEnv:
    """
    A deliberately small stand-in for the knee-prosthesis tuning loop.

    THIS IS A TOY. It is not anyone's prosthesis and not anyone's subject
    data. It exists so the RL machinery on the case-study page runs on
    something with the same SHAPE as the real problem:

        one step        = one completed gait cycle. Nothing can be evaluated
                          until the cycle finishes, because the state is
                          computed from the whole cycle.

        state (5)       = how far four knee-angle landmarks sit from the
                          reference, plus the phase lag from a
                          cross-correlation of the two curves:
                            0  heel strike angle error        (deg)
                            1  peak stance flexion error      (deg)
                            2  peak stance extension error    (deg)
                            3  peak swing flexion error       (deg)
                            4  phase lag                      (% of cycle)

        action (2)      = increments to the PC1 and PC2 weights of the
                          stiffness profile. The controller adds them to a
                          base set of weights; it never commands an angle.

        reward          = -(sum of weighted absolute errors) - penalties.
                          The swing-flexion term carries the largest weight
                          because that is the landmark subjects notice.

    The hidden truth the agent never sees: there is one weight pair `w_star`
    at which every landmark error is zero, and the map from weights to
    landmark errors is a fixed, mildly nonlinear coupling matrix. The agent
    has no access to it, which is the entire point -- this is model-free.
    """

    seed: int = 0
    n_cycles: int = 40           # episode length, in gait cycles
    step_scale: float = 0.15     # how much one action moves the weights
    noise: float = 0.35          # stride-to-stride variability, in degrees
    dim_s: int = field(default=5, init=False)
    dim_a: int = field(default=2, init=False)
    a_max: float = field(default=1.0, init=False)

    # weights of the reward terms, in the paper's notation
    alphas: tuple = (0.1, 0.1, 0.1, 0.4, 0.3)
    reg: float = 0.05            # penalise large weight changes (effort)
    flex_limit: float = 70.0     # degrees; beyond this, penalty
    ext_limit: float = -10.0     # degrees; beyond this, penalty
    pen: float = 5.0

    def __post_init__(self):
        self.rng = np.random.default_rng(self.seed)
        # the coupling from (w1, w2) to the five landmark errors -- fixed,
        # unknown to the agent, and deliberately NOT diagonal: turning one
        # weight moves several landmarks at once, which is what makes hand
        # tuning hard and what the critic has to figure out
        self.M = np.array([[2.5, -0.6],
                           [6.0, 1.5],
                           [-3.2, 2.4],
                           [8.5, -4.0],
                           [1.2, 3.0]])
        self.w_star = np.array([0.0, 0.0])
        self.w = np.zeros(2)
        self.t = 0

    # -- the hidden plant ----------------------------------------------
    def _features(self, w) -> np.ndarray:
        d = w - self.w_star
        lin = self.M @ d
        # a mild saturation, so that far-off weights do not produce absurd
        # landmark errors and the problem stays nonlinear
        return 12.0 * np.tanh(lin / 12.0)

    def reset(self, w0=None):
        self.w = (np.array(w0, dtype=float) if w0 is not None
                  else self.rng.uniform(-1.2, 1.2, size=2))
        self.t = 0
        return self._observe()

    def _observe(self) -> np.ndarray:
        f = self._features(self.w)
        return f + self.rng.normal(0.0, self.noise, size=5)

    # -- the reward, spelled out ---------------------------------------
    def reward(self, s: np.ndarray, a: np.ndarray) -> tuple[float, bool]:
        terms = [al * abs(float(x)) for al, x in zip(self.alphas, s)]
        r = -sum(terms)
        r -= self.reg * float(np.sum(np.abs(a)))
        # safety: the reference peak swing flexion is ~60 deg, so s[3] is an
        # error about that; convert back to an angle before checking limits
        peak = 60.0 + float(s[3])
        strike = 0.0 + float(s[0])
        unsafe = peak > self.flex_limit or strike < self.ext_limit
        if unsafe:
            r -= self.pen
        return r, unsafe

    def step(self, a):
        a = np.clip(np.ravel(a), -1.0, 1.0)
        self.w = np.clip(self.w + self.step_scale * a, -3.0, 3.0)
        s2 = self._observe()
        r, unsafe = self.reward(s2, a)
        self.t += 1
        done = self.t >= self.n_cycles
        return s2, r, done, unsafe

    # -- what a hand-tuner would achieve, for comparison ---------------
    def best_possible_reward(self) -> float:
        """Reward at the optimum, ignoring stride noise: 0 error, 0 action."""
        return 0.0


# ==========================================================================
# Training loops
# ==========================================================================

@dataclass
class TrainLog:
    returns: list[float] = field(default_factory=list)
    critic_loss: list[float] = field(default_factory=list)
    q_mean: list[float] = field(default_factory=list)
    noise: list[float] = field(default_factory=list)


def train_reach(episodes: int = 1500, seed: int = 0, noise: float = 0.3,
                gamma: float = 0.0, tau: float = 0.01,
                use_targets: bool = True, hidden: int = 48
                ) -> tuple[DDPG, TrainLog]:
    """
    Train on ContextualReach. One step per episode, so `episodes` is also the
    number of environment steps and the number of gradient steps.

    `use_targets=False` rewires the target networks to be exact copies of the
    live ones on every step (tau = 1), which is the ablation the DDPG page
    uses to show what the slow copies are actually for.
    """
    env = ContextualReach(seed=seed)
    cfg = DDPGConfig(dim_s=1, dim_a=1, gamma=gamma, tau=1.0 if not use_targets
                     else tau, noise=noise, hidden=hidden, seed=seed,
                     lr_actor=1e-3, lr_critic=3e-3, batch=64, capacity=10000)
    ag = DDPG(cfg)
    log = TrainLog()
    for ep in range(episodes):
        s = env.reset()
        sig = noise * max(0.05, 1.0 - ep / (0.8 * episodes))
        a = ag.act(s, noise=sig)
        s2, r, done = env.step(a)
        ag.buf.push(s, a, r, s2, done)
        ag.train_step()
        log.returns.append(r)
        log.noise.append(sig)
        if ag.critic_losses:
            log.critic_loss.append(ag.critic_losses[-1])
            log.q_mean.append(ag.q_mean[-1])
    return ag, log


def train_gait(episodes: int = 60, seed: int = 0, noise: float = 0.35,
               gamma: float = 0.95, updates_per_step: int = 1,
               n_cycles: int = 40) -> tuple[DDPG, GaitTuneEnv, TrainLog]:
    """
    Train on GaitTuneEnv. `episodes` here are training sessions and each one
    is `n_cycles` gait cycles, so the total number of real strides is
    episodes * n_cycles -- the number that decides whether a method is
    deployable on a person.
    """
    env = GaitTuneEnv(seed=seed, n_cycles=n_cycles)
    cfg = DDPGConfig(dim_s=5, dim_a=2, gamma=gamma, tau=0.02, noise=noise,
                     hidden=64, seed=seed, lr_actor=5e-4, lr_critic=2e-3,
                     batch=64, capacity=20000)
    ag = DDPG(cfg)
    log = TrainLog()
    for ep in range(episodes):
        s = env.reset()
        sig = noise * max(0.05, 1.0 - ep / (0.8 * episodes))
        total = 0.0
        for _ in range(n_cycles):
            a = ag.act(s, noise=sig)
            s2, r, done, _unsafe = env.step(a)
            ag.buf.push(s, a, r, s2, done)
            for _ in range(updates_per_step):
                ag.train_step()
            total += r
            s = s2
            if done:
                break
        log.returns.append(total / n_cycles)     # mean reward per gait cycle
        log.noise.append(sig)
        if ag.critic_losses:
            log.critic_loss.append(ag.critic_losses[-1])
            log.q_mean.append(ag.q_mean[-1])
    return ag, env, log


def rollout_gait(ag: DDPG, env: GaitTuneEnv, w0=(1.0, -1.0), n: int = 40):
    """One greedy episode, for plotting what the trained policy does."""
    s = env.reset(w0=w0)
    ws, rs, feats = [env.w.copy()], [], [s.copy()]
    for _ in range(n):
        a = ag.act_greedy(s)
        s, r, done, _u = env.step(a)
        ws.append(env.w.copy())
        rs.append(r)
        feats.append(s.copy())
        if done:
            break
    return np.array(ws), np.array(rs), np.array(feats)


# ==========================================================================
# The comparison table on the "what makes it DDPG" page, as data
# ==========================================================================

ALGO_TABLE = [
    # name, policy type, n critics, what the critic estimates, on/off policy,
    # the one feature that defines it
    ("DDPG", "deterministic  mu(s)", "1", "Q(s,a)", "off-policy",
     "A deterministic actor trained by pushing action through dQ/da. Needs "
     "added noise to explore at all."),
    ("TD3", "deterministic  mu(s)", "2", "Q(s,a)", "off-policy",
     "DDPG plus three fixes: take min(Q1,Q2) to stop the critic being "
     "optimistic, update the actor less often than the critic, and smooth "
     "the target action with noise."),
    ("SAC", "stochastic  pi(a|s)", "2", "Q(s,a)", "off-policy",
     "Maximises reward PLUS policy entropy, so exploration is part of the "
     "objective rather than injected noise."),
    ("PPO", "stochastic  pi(a|s)", "1", "V(s)", "on-policy",
     "Clips how far the new policy may move from the old one per update. "
     "Throws its data away after each batch."),
    ("A2C/A3C", "stochastic  pi(a|s)", "1", "V(s)", "on-policy",
     "The plain actor-critic: advantage = r + gamma V(s') - V(s), no trust "
     "region, no replay."),
    ("DQN", "implicit  argmax_a Q", "1", "Q(s,a)", "off-policy",
     "No actor at all. Works only when you can enumerate the actions to take "
     "the max -- which is exactly why continuous control needs DDPG."),
]
