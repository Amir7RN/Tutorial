"""
The Multi-Armed Bandit -- exploration vs exploitation, with everything else
stripped away.

A bandit is an MDP with exactly ONE state. That single simplification kills:
    - transitions      (you never move)
    - discounting      (no future to discount)
    - credit assignment (the reward arrives immediately)

What survives is the one hard question: you have k slot machines with unknown
payout distributions, and every pull spent finding out about a bad machine is a
pull not spent on the good one. When do you stop learning and start earning?

The two strategies from your notes are implemented below.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field


@dataclass
class Bandit:
    """
    k arms. Arm i pays a Gaussian reward with mean q_true[i] and unit variance.
    This is the Sutton & Barto 10-armed testbed.
    """
    k: int = 10
    seed: int | None = 0
    q_true: list[float] = field(default_factory=list)

    def __post_init__(self):
        self.rng = random.Random(self.seed)
        if not self.q_true:
            self.q_true = [self.rng.gauss(0.0, 1.0) for _ in range(self.k)]
        self.best_arm = max(range(self.k), key=lambda a: self.q_true[a])
        self.best_value = self.q_true[self.best_arm]

    def pull(self, a: int) -> float:
        return self.rng.gauss(self.q_true[a], 1.0)


# --------------------------------------------------------------------------
# Strategy 1: epsilon-greedy
# --------------------------------------------------------------------------

def epsilon_greedy_run(bandit: Bandit, steps=1000, eps=0.1, seed=1,
                       optimistic_init=0.0):
    """
        A_t = random arm                with probability eps
            = argmax_a Q_t(a)           with probability 1 - eps

    Q_t(a) is the sample mean of the rewards seen from arm a so far, kept
    incrementally:   Q <- Q + (R - Q) / N

    The flaw: eps-greedy explores UNIFORMLY. When it decides to explore it is
    just as happy to re-test an arm it already knows is terrible as one it is
    genuinely unsure about. That waste is what UCB fixes.

    `optimistic_init` > 0 seeds every Q high, so early disappointment alone
    drives exploration -- a cheap trick that often beats eps outright.
    """
    rng = random.Random(seed)
    Q = [optimistic_init] * bandit.k
    N = [0] * bandit.k

    rewards, optimal, regret = [], [], []
    cum_regret = 0.0

    for t in range(1, steps + 1):
        if rng.random() < eps:
            a = rng.randrange(bandit.k)
        else:
            best = max(Q)
            a = rng.choice([i for i in range(bandit.k) if Q[i] >= best - 1e-12])

        r = bandit.pull(a)
        N[a] += 1
        Q[a] += (r - Q[a]) / N[a]

        cum_regret += bandit.best_value - bandit.q_true[a]
        rewards.append(r)
        optimal.append(1 if a == bandit.best_arm else 0)
        regret.append(cum_regret)

    return {"Q": Q, "N": N, "rewards": rewards,
            "optimal": optimal, "regret": regret}


# --------------------------------------------------------------------------
# Strategy 2: Upper Confidence Bound
# --------------------------------------------------------------------------

def ucb_run(bandit: Bandit, steps=1000, c=2.0, seed=1):
    r"""
    "Optimism in the face of uncertainty" -- straight from your handwritten note:

        A_t = argmax_a [ Q_t(a) + c * sqrt( ln(t) / N_t(a) ) ]
                        \______/   \______________________/
                        what I     how UNSURE I am about it
                        believe

    Read the bonus term:
        N_t(a) small  -> bonus large -> "I barely know this arm, go look"
        N_t(a) large  -> bonus small -> "I have measured this to death"
        ln(t) growing -> every bonus creeps up over time, so a long-neglected
                         arm eventually gets re-checked. Slowly (log), because
                         the world is not changing.

    Unlike eps-greedy, UCB is DETERMINISTIC. It never rolls a die -- it explores
    the arm with the highest plausible upside, which is a targeted question
    rather than a random one.

    Any arm with N=0 has an infinite bonus, so the first k pulls always sweep
    every arm once. That is built in, not a special case.
    """
    Q = [0.0] * bandit.k
    N = [0] * bandit.k

    rewards, optimal, regret, bonuses = [], [], [], []
    cum_regret = 0.0

    for t in range(1, steps + 1):
        # untried arms first -- their bonus is mathematically infinite
        untried = [i for i in range(bandit.k) if N[i] == 0]
        if untried:
            a = untried[0]
            bonus_row = [float("inf") if N[i] == 0 else
                         c * math.sqrt(math.log(t) / N[i]) for i in range(bandit.k)]
        else:
            bonus_row = [c * math.sqrt(math.log(t) / N[i]) for i in range(bandit.k)]
            scores = [Q[i] + bonus_row[i] for i in range(bandit.k)]
            best = max(scores)
            a = scores.index(best)

        r = bandit.pull(a)
        N[a] += 1
        Q[a] += (r - Q[a]) / N[a]

        cum_regret += bandit.best_value - bandit.q_true[a]
        rewards.append(r)
        optimal.append(1 if a == bandit.best_arm else 0)
        regret.append(cum_regret)
        bonuses.append(bonus_row)

    return {"Q": Q, "N": N, "rewards": rewards, "optimal": optimal,
            "regret": regret, "bonuses": bonuses}


# --------------------------------------------------------------------------
# Averaged comparison -- one run tells you nothing
# --------------------------------------------------------------------------

def compare(steps=1000, runs=200, eps_list=(0.0, 0.01, 0.1), ucb_c=2.0, k=10):
    """
    Average over many independent bandits. A single run is dominated by luck;
    the classic textbook curves only appear after ~200 runs.

    Returns {label: {"reward": [...], "optimal_pct": [...]}}.
    """
    out = {}
    for eps in eps_list:
        rew = [0.0] * steps
        opt = [0.0] * steps
        for run in range(runs):
            b = Bandit(k=k, seed=1000 + run)
            res = epsilon_greedy_run(b, steps=steps, eps=eps, seed=5000 + run)
            for t in range(steps):
                rew[t] += res["rewards"][t]
                opt[t] += res["optimal"][t]
        label = "greedy (eps=0)" if eps == 0 else f"eps-greedy ({eps})"
        out[label] = {"reward": [x / runs for x in rew],
                      "optimal_pct": [100.0 * x / runs for x in opt]}

    rew = [0.0] * steps
    opt = [0.0] * steps
    for run in range(runs):
        b = Bandit(k=k, seed=1000 + run)
        res = ucb_run(b, steps=steps, c=ucb_c, seed=5000 + run)
        for t in range(steps):
            rew[t] += res["rewards"][t]
            opt[t] += res["optimal"][t]
    out[f"UCB (c={ucb_c})"] = {"reward": [x / runs for x in rew],
                               "optimal_pct": [100.0 * x / runs for x in opt]}
    return out
