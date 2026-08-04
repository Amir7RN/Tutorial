"""
Monte Carlo methods -- learning WITHOUT the model.

Look at the signatures in this file and compare them with dp.py:

        dp.py     def value_iteration(P, gamma, ...)      <- gets the map
        mc.py     def mc_prediction(env, policy, ...)     <- gets a simulator

That swap, `P` for `env`, is the entire model-free / model-based divide. From
here on the agent can only find out what the ice does by walking on it.

--------------------------------------------------------------------------
THE CORE MC IDEA
--------------------------------------------------------------------------
V^pi(s) is DEFINED as an expectation:  V^pi(s) = E_pi [ G_t | S_t = s ].

DP computes that expectation exactly, by summing over P.
MC estimates it the way you'd estimate anything else: play a lot of episodes,
average the returns you actually saw. Law of large numbers does the rest.

No bootstrapping. No Bellman equation. Just averaging.

--------------------------------------------------------------------------
THE BACKWARD RETURN LOOP  (the trick worth memorising)
--------------------------------------------------------------------------
Computing G_t = R_{t+1} + gamma*R_{t+2} + gamma^2*R_{t+3} + ... naively for every
t is O(T^2). Walking the trajectory BACKWARDS makes it O(T):

        G = 0
        for t = T-1 down to 0:
            G = gamma * G + R_{t+1}       <- G is now exactly G_t

Every function below uses that loop. It is the same three lines each time.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .frozen_lake import (
    N_ACTIONS,
    N_STATES,
    FrozenLake,
    GOAL,
)


@dataclass
class MCSnapshot:
    """One frame of Monte Carlo learning."""
    episode: int
    V: list[float] | None = None
    Q: list[list[float]] | None = None
    policy: list[int] = field(default_factory=list)
    visits: list[int] = field(default_factory=list)
    epsilon: float = 0.0
    alpha: float = 0.0
    last_trajectory: list[tuple[int, int, float]] = field(default_factory=list)
    last_return: float = 0.0
    success_rate: float = 0.0
    note: str = ""


# ==========================================================================
# 1. MC PREDICTION -- "how good is this policy?" (the PREDICTION problem)
# ==========================================================================

def mc_prediction(env: FrozenLake, policy_fn, gamma=0.99, episodes=5000,
                  first_visit=True, max_steps=200):
    """
    Estimate V^pi by averaging observed returns.

    first_visit=True  -> FVMC: within one episode, only the FIRST time you land
                         on s contributes a return to s's average.
                         Unbiased. The textbook default.

    first_visit=False -> EVMC: EVERY landing contributes, so a single episode can
                         feed the same state several correlated returns.
                         Biased for finite samples, but consistent, and usually
                         lower variance early on.

    Returns (V, counts).
    """
    V = [0.0] * N_STATES
    counts = [0] * N_STATES

    for _ in range(episodes):
        # --- generate one full episode under pi --------------------------
        traj = []
        s = env.reset()
        for _ in range(max_steps):
            a = policy_fn(s)
            nxt, r, done = env.step(a)
            traj.append((s, a, r))
            s = nxt
            if done:
                break

        # --- index of the FIRST time each state appears -------------------
        # Careful: you cannot build this with a set while walking backwards.
        # A backward-filled set tells you a state appears LATER, which would
        # make you keep the last visit, not the first. So do a forward pass.
        first_idx = {}
        for t, (st, _, _) in enumerate(traj):
            first_idx.setdefault(st, t)

        # --- walk it backwards, accumulating the return -------------------
        G = 0.0
        for t in range(len(traj) - 1, -1, -1):
            st, at, rt = traj[t]
            G = gamma * G + rt          # G is now exactly G_t

            # THE ONE LINE THAT SEPARATES FVMC FROM EVMC:
            if first_visit and first_idx[st] != t:
                continue

            # incremental sample mean:  mean <- mean + (x - mean)/n
            counts[st] += 1
            V[st] += (G - V[st]) / counts[st]

    return V, counts


def mc_prediction_steps(env: FrozenLake, policy_fn, gamma=0.99, episodes=5000,
                        first_visit=True, max_steps=200, report_every=25):
    """Animated twin -- yields an MCSnapshot every `report_every` episodes."""
    V = [0.0] * N_STATES
    counts = [0] * N_STATES
    wins = 0

    for ep in range(1, episodes + 1):
        traj = []
        s = env.reset()
        for _ in range(max_steps):
            a = policy_fn(s)
            nxt, r, done = env.step(a)
            traj.append((s, a, r))
            s = nxt
            if done:
                if s == GOAL:
                    wins += 1
                break

        first_idx = {}
        for t, (st, _, _) in enumerate(traj):
            first_idx.setdefault(st, t)

        G = 0.0
        for t in range(len(traj) - 1, -1, -1):
            st, at, rt = traj[t]
            G = gamma * G + rt
            if first_visit and first_idx[st] != t:
                continue
            counts[st] += 1
            V[st] += (G - V[st]) / counts[st]
        ep_return = G  # after the full backward pass, G == G_0

        if ep % report_every == 0 or ep == episodes:
            yield MCSnapshot(
                episode=ep, V=list(V), visits=list(counts),
                last_trajectory=traj, last_return=ep_return,
                success_rate=wins / ep,
                note=("FVMC" if first_visit else "EVMC")
                     + f": {ep} episodes, {sum(counts)} returns averaged in.",
            )


# ==========================================================================
# 2. MC CONTROL -- "find me a GOOD policy" (the CONTROL problem)
# ==========================================================================

def epsilon_greedy(Q, s, eps, rng: random.Random) -> int:
    """
    With probability eps: explore (uniform random action).
    Otherwise:            exploit (argmax_a Q[s][a], ties broken at random).

    Random tie-breaking matters more than it looks. Q starts all-zero, so
    without it every state would deterministically pick action 0 forever and
    three quarters of the grid would never be explored.
    """
    if rng.random() < eps:
        return rng.randrange(N_ACTIONS)
    best = max(Q[s])
    ties = [a for a in range(N_ACTIONS) if Q[s][a] >= best - 1e-12]
    return rng.choice(ties)


def mc_control(env: FrozenLake, gamma=0.99, episodes=20000,
               eps_start=1.0, eps_min=0.05, eps_decay=0.9995,
               alpha_start=0.5, alpha_min=0.01, alpha_decay=0.9995,
               first_visit=True, max_steps=200, seed=0):
    """
    Generalised Policy Iteration without a model (on-policy, every/first visit).

    Why Q and not V?  <-- this is the "VERY IMPORTANT" box in your page-4 notes.
    With V alone you know a square is good but not which BUTTON gets you there,
    because that requires knowing P. Learning Q(s,a) sidesteps the model entirely:
    acting greedily is just `argmax_a Q[s][a]`, no transition probabilities needed.

    The GPI loop, one episode at a time:
        EVALUATE   -- play an episode with eps-greedy(Q), nudge Q toward the
                      returns actually observed
        IMPROVE    -- the policy IS eps-greedy(Q), so improving Q improves pi
                      for free. There is no separate improvement step.

    Constant-alpha update (rather than a true running mean):
        Q(s,a) <- Q(s,a) + alpha * ( G - Q(s,a) )
    A fixed alpha forgets old returns, which is what you want while the policy
    is still changing underneath you.

    Returns (Q, pi, stats).
    """
    rng = random.Random(seed)
    Q = [[0.0] * N_ACTIONS for _ in range(N_STATES)]
    counts = [[0] * N_ACTIONS for _ in range(N_STATES)]

    eps, alpha = eps_start, alpha_start
    wins = 0
    history = []

    for ep in range(1, episodes + 1):
        traj = []
        s = env.reset()
        for _ in range(max_steps):
            a = epsilon_greedy(Q, s, eps, rng)
            nxt, r, done = env.step(a)
            traj.append((s, a, r))
            s = nxt
            if done:
                if s == GOAL:
                    wins += 1
                break

        # first visit is now per (state, ACTION) pair, not per state
        first_idx = {}
        for t, (st, at, _) in enumerate(traj):
            first_idx.setdefault((st, at), t)

        G = 0.0
        for t in range(len(traj) - 1, -1, -1):
            st, at, rt = traj[t]
            G = gamma * G + rt
            if first_visit and first_idx[(st, at)] != t:
                continue
            counts[st][at] += 1
            Q[st][at] += alpha * (G - Q[st][at])

        eps = max(eps_min, eps * eps_decay)
        alpha = max(alpha_min, alpha * alpha_decay)
        if ep % 100 == 0:
            history.append((ep, wins / ep, eps, alpha))

    pi = [max(range(N_ACTIONS), key=lambda a: Q[s][a]) for s in range(N_STATES)]
    stats = {"success_rate": wins / episodes, "history": history,
             "counts": counts, "epsilon": eps, "alpha": alpha}
    return Q, pi, stats


def mc_control_steps(env: FrozenLake, gamma=0.99, episodes=20000,
                     eps_start=1.0, eps_min=0.05, eps_decay=0.9995,
                     alpha_start=0.5, alpha_min=0.01, alpha_decay=0.9995,
                     first_visit=True, max_steps=200, seed=0,
                     report_every=100):
    """Animated twin of mc_control."""
    rng = random.Random(seed)
    Q = [[0.0] * N_ACTIONS for _ in range(N_STATES)]
    counts = [[0] * N_ACTIONS for _ in range(N_STATES)]
    eps, alpha = eps_start, alpha_start
    wins = 0
    recent = []

    for ep in range(1, episodes + 1):
        traj = []
        s = env.reset()
        for _ in range(max_steps):
            a = epsilon_greedy(Q, s, eps, rng)
            nxt, r, done = env.step(a)
            traj.append((s, a, r))
            s = nxt
            if done:
                if s == GOAL:
                    wins += 1
                    recent.append(1)
                else:
                    recent.append(0)
                break
        else:
            recent.append(0)
        if len(recent) > 200:
            recent.pop(0)

        first_idx = {}
        for t, (st, at, _) in enumerate(traj):
            first_idx.setdefault((st, at), t)

        G = 0.0
        for t in range(len(traj) - 1, -1, -1):
            st, at, rt = traj[t]
            G = gamma * G + rt
            if first_visit and first_idx[(st, at)] != t:
                continue
            counts[st][at] += 1
            Q[st][at] += alpha * (G - Q[st][at])

        eps = max(eps_min, eps * eps_decay)
        alpha = max(alpha_min, alpha * alpha_decay)

        if ep % report_every == 0 or ep == episodes:
            pi = [max(range(N_ACTIONS), key=lambda a: Q[s][a])
                  for s in range(N_STATES)]
            yield MCSnapshot(
                episode=ep, Q=[row[:] for row in Q], policy=pi,
                visits=[sum(r) for r in counts],
                epsilon=eps, alpha=alpha,
                last_trajectory=traj, last_return=G,
                success_rate=sum(recent) / max(1, len(recent)),
                note=f"episode {ep}  eps={eps:.3f}  alpha={alpha:.3f}  "
                     f"recent success={sum(recent) / max(1, len(recent)):.1%}",
            )


# ==========================================================================
# 3. Teaching toys from the notes -- MC really is just averaging
# ==========================================================================

def dice_convergence(n=5000, seed=0):
    """
    A fair d6 has expectation 3.5. Roll it n times and watch the running mean
    crawl to 3.5. This is Monte Carlo with the RL stripped away -- and it is
    exactly the argument that makes mc_prediction correct.
    """
    rng = random.Random(seed)
    running, total = [], 0
    for i in range(1, n + 1):
        total += rng.randint(1, 6)
        running.append(total / i)
    return running


def estimate_pi(n=5000, seed=0):
    """
    The other example from your notes: throw darts at the unit square, count how
    many land inside the quarter circle x^2 + y^2 <= 1, multiply by 4.

    Same machinery as mc_prediction: sample, average, converge. Convergence is
    O(1/sqrt(n)) -- 100x more samples buys 10x more accuracy. That slow rate is
    exactly why MC needs thousands of episodes where DP needs ~30 sweeps.
    """
    rng = random.Random(seed)
    inside = 0
    running = []
    for i in range(1, n + 1):
        x, y = rng.random(), rng.random()
        if x * x + y * y <= 1.0:
            inside += 1
        running.append(4.0 * inside / i)
    return running
