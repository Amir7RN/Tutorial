"""
Dynamic Programming on a KNOWN model:  Policy Evaluation, Policy Improvement,
Policy Iteration, Value Iteration.

The defining assumption of this whole file, and the one thing that separates it
from mc.py, is on the very first line of every function signature:

        def something(P, ...)

We are handed `P`. We already know the physics. We are not learning, we are
SOLVING. Your notes call this "Planning, Not Learning" -- there is no episode,
no exploration, no trial and error. It is a system of equations on a grid.

--------------------------------------------------------------------------
THE ONE-LINE DIFFERENCE BETWEEN THE TWO BIG ALGORITHMS
--------------------------------------------------------------------------

    Policy Evaluation inner update      V(s) <- Q(s, pi(s))          <- FOLLOW
    Value Iteration inner update        V(s) <- max_a Q(s, a)        <- BEST

That is genuinely it. `pi(s)` versus `max_a`. Everything else -- the sweeps,
the theta test, the arrows -- is identical scaffolding. Page 20 of the tutor
puts these two lines side by side.

--------------------------------------------------------------------------
WHY EVERY FUNCTION HAS A `_steps` TWIN
--------------------------------------------------------------------------
The plain function returns the answer. The `_steps` generator yields a snapshot
after every sweep so the GUI can animate the value "ripple" spreading outward
from the goal. Same maths, same loop -- one just narrates.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .frozen_lake import (
    N_ACTIONS,
    N_STATES,
    q_from_V,
    q_table_from_V,
)

# --------------------------------------------------------------------------
# Snapshot type used by every animated variant
# --------------------------------------------------------------------------

@dataclass
class Snapshot:
    """One frame of an algorithm's execution, for the GUI to draw."""
    kind: str                      # "evaluation" | "improvement" | "value_iteration"
    sweep: int                     # which sweep produced this frame
    V: list[float]
    policy: list[int]
    delta: float                   # max |V_new - V_old| over this sweep
    note: str = ""
    changed_states: list[int] = field(default_factory=list)
    outer_iter: int = 0            # policy-iteration round, when relevant
    converged: bool = False


# ==========================================================================
# 1. POLICY EVALUATION  -- "how good is THIS plan?"
# ==========================================================================

def policy_evaluation(P, pi, gamma=0.99, theta=1e-10, max_sweeps=10_000):
    """
    Solve the Bellman EXPECTATION equation for a fixed deterministic policy pi.

        V^pi(s) = sum_{s'} P(s' | s, pi(s)) * [ r + gamma * V^pi(s') ]

    Notice there is NO max here. We are not asking what the agent SHOULD do; we
    are forced to follow pi even when pi is stupid. That is the entire point of
    the evaluation half -- get an honest score for the current plan.

    Returns the converged V.
    """
    V = [0.0] * N_STATES

    for _ in range(max_sweeps):
        delta = 0.0
        # Jacobi-style: read from the previous sweep so all states update
        # "simultaneously". (Gauss-Seidel -- reading V in place -- also
        # converges, usually faster. Both are correct.)
        V_prev = list(V)
        for s in range(N_STATES):
            v_new = q_from_V(P, V_prev, s, pi[s], gamma)
            delta = max(delta, abs(v_new - V[s]))
            V[s] = v_new
        if delta < theta:
            break
    return V


def policy_evaluation_stochastic(P, probs, gamma=0.99, theta=1e-12,
                                 max_sweeps=5000):
    """
    The Bellman EXPECTATION equation for V, written out in full for a policy that
    is allowed to be STOCHASTIC -- probs[s][a] is pi(a|s).

        V^pi(s) = sum_a pi(a|s) sum_s' P(s'|s,a) [ r + gamma * V^pi(s') ]
                  \\_____________/ \\____________________________________/
                   the AGENT's die            the ICE's die
                   (averaged, because          (averaged, because you
                    that is what pi does)       never control the ice)

    policy_evaluation() above is exactly this function with a one-hot pi, which is
    why it can index `pi[s]` instead of summing: multiplying by a one-hot vector
    and picking the single non-zero entry are the same operation.

    Two averages, no max. The max only appears in the OPTIMALITY equations.
    """
    V = [0.0] * N_STATES

    for _ in range(max_sweeps):
        V_prev = list(V)
        delta = 0.0
        for s in range(N_STATES):
            v_new = sum(probs[s][a] * q_from_V(P, V_prev, s, a, gamma)
                        for a in range(N_ACTIONS))
            delta = max(delta, abs(v_new - V[s]))
            V[s] = v_new
        if delta < theta:
            break
    return V


def policy_evaluation_history(P, probs, gamma=0.99, theta=1e-12, max_sweeps=200):
    """
    Same sweeps as policy_evaluation_stochastic, but keep every intermediate V.

    Returns a list `hist` with hist[0] = all zeros and hist[k] = V after sweep k,
    so the GUI can scrub through the sweeps and plot how fast the error dies.
    """
    V = [0.0] * N_STATES
    hist = [list(V)]

    for _ in range(max_sweeps):
        V_prev = list(V)
        delta = 0.0
        for s in range(N_STATES):
            V[s] = sum(probs[s][a] * q_from_V(P, V_prev, s, a, gamma)
                       for a in range(N_ACTIONS))
            delta = max(delta, abs(V[s] - V_prev[s]))
        hist.append(list(V))
        if delta < theta:
            break
    return hist


def policy_evaluation_exact(P, probs, gamma=0.99):
    """
    Solve the SAME equation in one shot, with linear algebra instead of sweeps.

    The Bellman EXPECTATION equation is LINEAR in V -- every V(s') appears
    multiplied by a constant and added, never inside a max. So it is nothing more
    exotic than 16 simultaneous equations in 16 unknowns:

        V = r_pi + gamma * P_pi V        ->        (I - gamma P_pi) V = r_pi

    where  r_pi[s]      = sum_a pi(a|s) sum_s' P(s'|s,a) r
           P_pi[s][s']  = sum_a pi(a|s) P(s'|s,a)        (dropping terminal s')

    This is worth knowing for two reasons. It is exact -- no theta, no sweeps, no
    convergence question at all. And it is the thing you CANNOT do to the
    optimality equation: `max` is not a linear operator, so V* has no matrix
    inverse to solve for and iteration is the only way in.
    """
    import numpy as np

    A = np.eye(N_STATES)            # this will become (I - gamma * P_pi)
    b = np.zeros(N_STATES)          # this will become r_pi

    for s in range(N_STATES):
        for a in range(N_ACTIONS):
            pa = probs[s][a]
            if pa == 0.0:
                continue
            for t in P[s][a]:
                b[s] += pa * t.prob * t.reward
                # A terminal successor contributes no future, so it contributes
                # nothing to the matrix -- same `if t.done` as in q_from_V.
                if not t.done:
                    A[s][t.next_state] -= pa * gamma * t.prob

    return list(np.linalg.solve(A, b))


def policy_evaluation_steps(P, pi, gamma=0.99, theta=1e-10, max_sweeps=2000):
    """Animated twin of policy_evaluation -- yields a Snapshot per sweep."""
    V = [0.0] * N_STATES
    yield Snapshot("evaluation", 0, list(V), list(pi), float("inf"),
                   "Start: V(s) = 0 everywhere. We know nothing yet.")

    for sweep in range(1, max_sweeps + 1):
        V_prev = list(V)
        delta = 0.0
        changed = []
        for s in range(N_STATES):
            v_new = q_from_V(P, V_prev, s, pi[s], gamma)
            if abs(v_new - V[s]) > 1e-12:
                changed.append(s)
            delta = max(delta, abs(v_new - V[s]))
            V[s] = v_new

        done = delta < theta
        yield Snapshot(
            "evaluation", sweep, list(V), list(pi), delta,
            f"Sweep {sweep}: every state pulled the value of wherever pi sends it. "
            f"max change = {delta:.2e}",
            changed, converged=done,
        )
        if done:
            return


# ==========================================================================
# 2. POLICY IMPROVEMENT  -- "given those scores, what SHOULD I do?"
# ==========================================================================

def policy_improvement(P, V, pi_old, gamma=0.99):
    """
        pi'(s) = argmax_a  sum_{s'} P(s'|s,a) [ r + gamma * V(s') ]

    This is where the `max` finally shows up. We keep V frozen and ask, for each
    square, "which of my four buttons has the best one-step lookahead?"

    Returns (pi_new, stable, q_table). `stable` True means nothing changed --
    that is the termination test for policy iteration.
    """
    Q = q_table_from_V(P, V, gamma)
    pi_new = []
    stable = True
    for s in range(N_STATES):
        best_a = max(range(N_ACTIONS), key=lambda a: Q[s][a])
        pi_new.append(best_a)
        # Compare Q-values, not action indices: ties are common on this grid and
        # flipping between two EQUALLY good actions is not a real change. Testing
        # `best_a != pi_old[s]` directly makes policy iteration loop forever.
        if Q[s][best_a] - Q[s][pi_old[s]] > 1e-12:
            stable = False
    return pi_new, stable, Q


# ==========================================================================
# 3. POLICY ITERATION  -- evaluate, improve, repeat
# ==========================================================================

def policy_iteration(P, gamma=0.99, theta=1e-10, max_rounds=200):
    """
    Alternate the two functions above until the policy stops moving.

        pi_0 -> V_0 -> pi_1 -> V_1 -> ... -> pi*   (finite, guaranteed)

    Terminates in a FINITE number of rounds because there are only 4^16 policies
    and each round is a strict improvement until it isn't.

    Returns (pi, V, rounds).
    """
    pi = [0] * N_STATES
    V = [0.0] * N_STATES
    for rnd in range(1, max_rounds + 1):
        V = policy_evaluation(P, pi, gamma, theta)
        pi, stable, _ = policy_improvement(P, V, pi, gamma)
        if stable:
            return pi, V, rnd
    return pi, V, max_rounds


def policy_iteration_steps(P, gamma=0.99, theta=1e-10, max_rounds=60,
                           eval_sweeps=2000):
    """
    Animated twin. Yields evaluation frames AND improvement frames so you can
    watch the two phases hand off to each other -- the "cycle of trust" from
    your page-4 notes.
    """
    pi = [0] * N_STATES
    V = [0.0] * N_STATES

    yield Snapshot("start", 0, list(V), list(pi), float("inf"),
                   "Round 0: arbitrary policy (all LEFT), V = 0. "
                   "Deliberately a terrible plan.", outer_iter=0)

    for rnd in range(1, max_rounds + 1):
        # ---- Phase A: evaluation (inner loop, runs to convergence) ----------
        for snap in policy_evaluation_steps(P, pi, gamma, theta, eval_sweeps):
            if snap.sweep == 0:
                continue
            snap.outer_iter = rnd
            snap.note = f"Round {rnd} / EVALUATE -- {snap.note}"
            yield snap

        V = policy_evaluation(P, pi, gamma, theta)

        # ---- Phase B: improvement (a single greedy pass) ---------------------
        pi_new, stable, _ = policy_improvement(P, V, pi, gamma)
        changed = [s for s in range(N_STATES) if pi_new[s] != pi[s]]
        pi = pi_new

        yield Snapshot(
            "improvement", 0, list(V), list(pi), 0.0,
            f"Round {rnd} / IMPROVE -- went greedy w.r.t. V. "
            + ("Policy is STABLE. This is pi*." if stable
               else f"{len(changed)} state(s) changed their mind -> must re-evaluate."),
            changed, outer_iter=rnd, converged=stable,
        )
        if stable:
            return


# ==========================================================================
# 4. VALUE ITERATION  -- fuse the two phases into one line
# ==========================================================================

def value_iteration(P, gamma=0.99, theta=1e-10, max_sweeps=10_000):
    """
    Solve the Bellman OPTIMALITY equation directly.

        V*(s) = max_a  sum_{s'} P(s'|s,a) [ r + gamma * V*(s') ]

    Compare with policy_evaluation(): the ONLY change is `pi[s]` becoming
    `max over a`. We never store an explicit policy while iterating -- the policy
    is extracted once at the end, from the converged values.

    Your notes call this "reverse broadcasting": the goal shouts "I have money",
    its neighbours hear it on sweep 1, their neighbours on sweep 2, and the news
    ripples backwards across the grid until the start square knows the way.

    Returns (pi, V, sweeps).
    """
    V = [0.0] * N_STATES

    for sweep in range(1, max_sweeps + 1):
        V_prev = list(V)
        delta = 0.0
        for s in range(N_STATES):
            v_new = max(q_from_V(P, V_prev, s, a, gamma) for a in range(N_ACTIONS))
            delta = max(delta, abs(v_new - V[s]))
            V[s] = v_new
        if delta < theta:
            break

    # Policy extraction: one greedy pass, done exactly once, at the end.
    Q = q_table_from_V(P, V, gamma)
    pi = [max(range(N_ACTIONS), key=lambda a: Q[s][a]) for s in range(N_STATES)]
    return pi, V, sweep


def value_iteration_steps(P, gamma=0.99, theta=1e-10, max_sweeps=2000):
    """Animated twin -- this is the one that shows the ripple beautifully."""
    V = [0.0] * N_STATES
    pi = [0] * N_STATES

    yield Snapshot("value_iteration", 0, list(V), list(pi), float("inf"),
                   "Sweep 0: V = 0. Only the goal transition carries any reward yet.")

    for sweep in range(1, max_sweeps + 1):
        V_prev = list(V)
        delta = 0.0
        changed = []
        for s in range(N_STATES):
            v_new = max(q_from_V(P, V_prev, s, a, gamma) for a in range(N_ACTIONS))
            if abs(v_new - V[s]) > 1e-9:
                changed.append(s)
            delta = max(delta, abs(v_new - V[s]))
            V[s] = v_new

        Q = q_table_from_V(P, V, gamma)
        pi = [max(range(N_ACTIONS), key=lambda a: Q[s][a]) for s in range(N_STATES)]

        done = delta < theta
        yield Snapshot(
            "value_iteration", sweep, list(V), list(pi), delta,
            f"Sweep {sweep}: {len(changed)} state(s) heard the news. "
            f"max change = {delta:.2e}",
            changed, converged=done,
        )
        if done:
            return


def value_iteration_operator(P, gamma=0.99, op="max", theta=1e-12,
                             max_sweeps=400):
    """
    Value iteration with the OUTER operator left as a knob. Nothing else changes.

        op = "max"    V(s) <- max_a Q(s,a)    the Bellman OPTIMALITY equation
        op = "mean"   V(s) <- avg_a Q(s,a)    = expectation under uniform-random pi
        op = "min"    V(s) <- min_a Q(s,a)    an adversary chooses your action

    All three converge (all three are gamma-contractions), all three are perfectly
    well-defined value functions, and only "max" answers the question RL asks. The
    knob exists to make one point unmissable: the `max` in the optimality equation
    is not decoration and it is not an average -- it is a CHOICE, and swapping it
    for any other operator quietly changes the question being asked.

    The INNER sum over s' is not a knob, because the ice is not yours to choose.

    Returns (V, history) with history[0] = zeros and history[k] = V after sweep k.
    """
    reduce = {"max": max, "min": min,
              "mean": lambda xs: sum(xs) / len(xs)}[op]

    V = [0.0] * N_STATES
    history = [list(V)]

    for _ in range(max_sweeps):
        V_prev = list(V)
        delta = 0.0
        for s in range(N_STATES):
            V[s] = reduce([q_from_V(P, V_prev, s, a, gamma)
                           for a in range(N_ACTIONS)])
            delta = max(delta, abs(V[s] - V_prev[s]))
        history.append(list(V))
        if delta < theta:
            break
    return V, history


# ==========================================================================
# 5. Q-VALUE ITERATION -- the same fixed point, stored as Q instead of V
# ==========================================================================

def q_value_iteration(P, gamma=0.99, theta=1e-10, max_sweeps=10_000):
    """
    The bridge from DP to Q-learning.

        Q*(s,a) = sum_{s'} P(s'|s,a) [ r + gamma * max_{a'} Q*(s', a') ]

    Same fixed point as value_iteration, stored per (state, action) instead of
    per state. Note where the `max` moved: INSIDE the sum, applied to the NEXT
    state. That relocation is precisely what lets Q-learning drop the model --
    replace `sum_{s'} P(...)` with "one sampled transition" and you have the
    Q-learning update.
    """
    Q = [[0.0] * N_ACTIONS for _ in range(N_STATES)]

    for sweep in range(1, max_sweeps + 1):
        Q_prev = [row[:] for row in Q]
        delta = 0.0
        for s in range(N_STATES):
            for a in range(N_ACTIONS):
                total = 0.0
                for t in P[s][a]:
                    boot = 0.0 if t.done else max(Q_prev[t.next_state])
                    total += t.prob * (t.reward + gamma * boot)
                delta = max(delta, abs(total - Q[s][a]))
                Q[s][a] = total
        if delta < theta:
            break

    pi = [max(range(N_ACTIONS), key=lambda a: Q[s][a]) for s in range(N_STATES)]
    return pi, Q, sweep


def q_value_iteration_history(P, gamma=0.99, theta=1e-12, max_sweeps=400):
    """
    Q-value iteration, keeping every sweep so the two convergence curves (this one
    and value_iteration_operator's) can be drawn on the same axes.

    Returns (Q, history) with history[0] = all zeros and history[k] = Q after
    sweep k. Note that history[k] is 64 numbers per frame where the V version is
    16 -- that 4x is the entire price of storing Q instead of V.
    """
    Q = [[0.0] * N_ACTIONS for _ in range(N_STATES)]
    history = [[row[:] for row in Q]]

    for _ in range(max_sweeps):
        Q_prev = [row[:] for row in Q]
        delta = 0.0
        for s in range(N_STATES):
            for a in range(N_ACTIONS):
                total = 0.0
                for t in P[s][a]:
                    # The max sits HERE -- one step downstream, inside the sum.
                    boot = 0.0 if t.done else max(Q_prev[t.next_state])
                    total += t.prob * (t.reward + gamma * boot)
                delta = max(delta, abs(total - Q[s][a]))
                Q[s][a] = total
        history.append([row[:] for row in Q])
        if delta < theta:
            break
    return Q, history


# ==========================================================================
# Evaluation helper -- score a policy by actually playing it
# ==========================================================================

def evaluate_policy_empirically(env, pi, episodes=2000, max_steps=200):
    """
    Sanity check: the DP answer is only useful if it survives contact with the
    simulator. Returns (success_rate, mean_return, mean_length).

    Takes a live `FrozenLake` and reuses it, so the RNG stream keeps advancing
    across episodes instead of restarting from the same seed every time.
    """
    wins = 0
    total_return = 0.0
    total_len = 0
    from .frozen_lake import GOAL

    for _ in range(episodes):
        s = env.reset()
        G = 0.0
        steps = 0
        for _ in range(max_steps):
            s, r, done = env.step(pi[s])
            G += r
            steps += 1
            if done:
                if s == GOAL:
                    wins += 1
                break
        total_return += G
        total_len += steps

    return wins / episodes, total_return / episodes, total_len / episodes
