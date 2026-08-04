"""
Correctness checks for rlcore. Run with:   python tests/test_core.py

These are not decorative. Several of them encode facts that are easy to get
wrong and that the whole tutor depends on being right.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rlcore import *          # noqa
from rlcore.frozen_lake import _DELTA  # noqa

FAILS = []


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}   {detail}")
        FAILS.append(name)


def approx(a, b, tol=1e-6):
    return abs(a - b) <= tol


print("\n[1] Model structure")
for slip in SLIP_MODELS:
    for rew in REWARD_SCHEMES:
        P = build_model(slip=slip, reward=rew)
        # every P[s][a] must be a probability distribution
        bad = [(s, a) for s in range(N_STATES) for a in range(N_ACTIONS)
               if not approx(sum(t.prob for t in P[s][a]), 1.0)]
        check(f"P[s][a] sums to 1  ({slip}/{rew})", not bad, str(bad[:3]))

P = build_model("gym", "gym")
check("terminal states absorb",
      all(len(P[s][a]) == 1 and P[s][a][0].next_state == s and P[s][a][0].done
          for s in list(HOLES) + [GOAL] for a in range(N_ACTIONS)))
check("start state is 0 and non-terminal", not is_terminal(START) and START == 0)


print("\n[2] Geometry / action encoding")
check("LEFT from 0 clips to 0", move(0, LEFT) == 0)
check("UP from 0 clips to 0", move(0, UP) == 0)
check("RIGHT from 0 -> 1", move(0, RIGHT) == 1)
check("DOWN from 0 -> 4", move(0, DOWN) == 4)
check("RIGHT from 3 clips to 3", move(3, RIGHT) == 3)
check("RIGHT from 14 -> GOAL(15)", move(14, RIGHT) == GOAL)
check("DOWN from 14 clips (already bottom row)", move(14, DOWN) == 14)
check("DOWN from 11 -> GOAL(15)", move(11, DOWN) == GOAL)
check("(a+1)%4 and (a-1)%4 are perpendicular to a",
      all(_DELTA[a][0] * _DELTA[(a + 1) % 4][0] +
          _DELTA[a][1] * _DELTA[(a + 1) % 4][1] == 0 for a in range(4)))
check("(a+2)%4 is the reverse of a",
      all(_DELTA[a][0] == -_DELTA[(a + 2) % 4][0] and
          _DELTA[a][1] == -_DELTA[(a + 2) % 4][1] for a in range(4)))


print("\n[3] Deterministic env == shortest path")
Pd = build_model("deterministic", "gym")
pi, V, sweeps = value_iteration(Pd, gamma=1.0, theta=1e-12)
# With gamma=1, no step cost and a reachable goal, V(s)=1 for every state that
# can reach the goal without entering a hole.
check("deterministic V(start) == 1.0", approx(V[START], 1.0), f"V0={V[START]}")
check("holes have V == 0", all(approx(V[h], 0.0) for h in HOLES))
check("goal has V == 0 (absorbing, no further reward)", approx(V[GOAL], 0.0))


print("\n[4] Policy iteration == value iteration (same fixed point)")
for slip in ("gym", "classic", "deterministic"):
    for rew in ("gym", "shaped"):
        Pm = build_model(slip, rew)
        pi_pi, V_pi, rounds = policy_iteration(Pm, gamma=0.99, theta=1e-12)
        pi_vi, V_vi, sw = value_iteration(Pm, gamma=0.99, theta=1e-12)
        same_V = all(approx(a, b, 1e-6) for a, b in zip(V_pi, V_vi))
        # policies can differ on ties; the VALUES must not
        check(f"V_PI == V_VI  ({slip}/{rew})", same_V)
        # and both policies must achieve the same value
        Vp = policy_evaluation(Pm, pi_pi, 0.99, 1e-12)
        Vv = policy_evaluation(Pm, pi_vi, 0.99, 1e-12)
        check(f"both policies score equally  ({slip}/{rew})",
              all(approx(a, b, 1e-6) for a, b in zip(Vp, Vv)))


print("\n[5] Q-value iteration agrees with value iteration")
Pm = build_model("gym", "gym")
pi_q, Q, _ = q_value_iteration(Pm, gamma=0.99, theta=1e-12)
pi_v, V, _ = value_iteration(Pm, gamma=0.99, theta=1e-12)
check("max_a Q*(s,a) == V*(s)",
      all(approx(max(Q[s]), V[s], 1e-6) for s in range(N_STATES)))


print("\n[6] Bellman consistency of the DP solution")
Pm = build_model("classic", "shaped")
pi, V, _ = value_iteration(Pm, gamma=0.99, theta=1e-14)
resid = max(abs(V[s] - max(q_from_V(Pm, V, s, a, 0.99) for a in range(N_ACTIONS)))
            for s in range(N_STATES))
check("Bellman optimality residual ~ 0", resid < 1e-8, f"residual={resid:.2e}")

Vpi = policy_evaluation(Pm, pi, 0.99, 1e-14)
resid2 = max(abs(Vpi[s] - q_from_V(Pm, Vpi, s, pi[s], 0.99)) for s in range(N_STATES))
check("Bellman expectation residual ~ 0", resid2 < 1e-8, f"residual={resid2:.2e}")


print("\n[7] V from Q identity  (V^pi(s) = sum_a pi(a|s) Q^pi(s,a))")
Pm = build_model("classic", "shaped")
pi, V, _ = policy_iteration(Pm, gamma=0.99, theta=1e-12)
Vpi = policy_evaluation(Pm, pi, 0.99, 1e-12)
Qpi = q_table_from_V(Pm, Vpi, 0.99)
probs = deterministic_to_probs(pi)
V_reconstructed = V_from_Q(Qpi, probs)
check("V reconstructed from Q matches",
      all(approx(a, b, 1e-8) for a, b in zip(Vpi, V_reconstructed)))


print("\n[8] Discount factor behaves")
Pm = build_model("deterministic", "gym")
_, V_lo, _ = value_iteration(Pm, gamma=0.5, theta=1e-14)
_, V_hi, _ = value_iteration(Pm, gamma=0.99, theta=1e-14)
check("low gamma discounts the distant goal harder", V_lo[START] < V_hi[START],
      f"{V_lo[START]:.4f} vs {V_hi[START]:.4f}")
# Start (0,0) to goal (3,3) is 6 moves on the deterministic map. The +1 arrives
# ON the 6th transition, i.e. at t=6, so G_0 = gamma^5 * 1 -- discounted FIVE
# times, not six. Off-by-one here is the classic discounting mistake.
check("V(start) == gamma^5 exactly (6 moves, reward on the 6th)",
      approx(V_lo[START], 0.5 ** 5, 1e-9), f"{V_lo[START]} vs {0.5**5}")


print("\n[9] Simulator matches the model empirically")
import collections
env = FrozenLake(slip="classic", reward="shaped", seed=7)
counts = collections.Counter()
N = 60000
s0, a0 = 9, RIGHT
for _ in range(N):
    env.reset()
    env.state, env.done = s0, False
    nxt, r, d = env.step(a0)
    counts[nxt] += 1
model = {t.next_state: 0.0 for t in P[s0][a0]}
Pc = build_model("classic", "shaped")
for t in Pc[s0][a0]:
    model[t.next_state] = model.get(t.next_state, 0.0) + t.prob
ok = all(abs(counts[ns] / N - p) < 0.01 for ns, p in model.items())
check("sampled transition frequencies match P[s][a]", ok,
      f"model={ {k: round(v,3) for k,v in model.items()} } "
      f"empirical={ {k: round(v/N,3) for k,v in counts.items()} }")


print("\n[10] Monte Carlo prediction converges to the DP answer")
Pm = build_model("classic", "shaped")
pi_star, V_star, _ = policy_iteration(Pm, gamma=0.99, theta=1e-12)
env = FrozenLake(slip="classic", reward="shaped", seed=11)
V_mc, counts_mc = mc_prediction(env, lambda s: pi_star[s],
                                gamma=0.99, episodes=40000, first_visit=True)
# only compare states the policy actually visits often
tested = [s for s in range(N_STATES) if counts_mc[s] > 400 and not is_terminal(s)]
errs = [abs(V_mc[s] - V_star[s]) for s in tested]
check("FVMC ~= DP on well-visited states", tested and max(errs) < 0.08,
      f"n={len(tested)} max_err={max(errs) if errs else 'n/a':.4f}")

V_ev, counts_ev = mc_prediction(env, lambda s: pi_star[s],
                                gamma=0.99, episodes=40000, first_visit=False)
tested2 = [s for s in range(N_STATES) if counts_ev[s] > 400 and not is_terminal(s)]
errs2 = [abs(V_ev[s] - V_star[s]) for s in tested2]
check("EVMC ~= DP on well-visited states", tested2 and max(errs2) < 0.10,
      f"max_err={max(errs2) if errs2 else 'n/a':.4f}")
check("EVMC collects more samples than FVMC", sum(counts_ev) > sum(counts_mc),
      f"{sum(counts_ev)} vs {sum(counts_mc)}")


print("\n[11] MC control actually learns")
env = FrozenLake(slip="classic", reward="shaped", seed=3)
Q, pi_mc, stats = mc_control(env, gamma=0.99, episodes=30000, seed=3)
Pm = build_model("classic", "shaped")
V_learned = policy_evaluation(Pm, pi_mc, 0.99, 1e-12)
pi_star, V_star, _ = policy_iteration(Pm, gamma=0.99, theta=1e-12)
gap = V_star[START] - V_learned[START]
check("MC-control policy is near-optimal from the start state", gap < 0.15,
      f"V*={V_star[START]:.4f} V_learned={V_learned[START]:.4f} gap={gap:.4f}")
check("MC-control policy beats the all-LEFT baseline",
      V_learned[START] > policy_evaluation(Pm, [LEFT]*N_STATES, 0.99, 1e-12)[START])


print("\n[12] Bandits")
b = Bandit(k=10, seed=0)
r_ucb_single = ucb_run(b, steps=2000, c=2.0, seed=1)
check("UCB pulls every arm at least once", all(n > 0 for n in r_ucb_single["N"]))

# A SINGLE run proves nothing -- pure greedy sometimes happens to lock onto the
# best arm immediately and then looks unbeatable. The textbook ordering only
# appears once you average over many independent bandits. Averaging here is not
# padding; it is the whole reason Sutton & Barto plot 2000-run averages.
RUNS = 120
tot = {"greedy": 0.0, "eps": 0.0, "ucb": 0.0}
opt_end = {"greedy": 0, "eps": 0, "ucb": 0}
for run in range(RUNS):
    bb = Bandit(k=10, seed=200 + run)
    g = epsilon_greedy_run(Bandit(k=10, seed=200 + run), steps=1000, eps=0.0, seed=run)
    e = epsilon_greedy_run(Bandit(k=10, seed=200 + run), steps=1000, eps=0.1, seed=run)
    u = ucb_run(Bandit(k=10, seed=200 + run), steps=1000, c=2.0, seed=run)
    tot["greedy"] += g["regret"][-1]
    tot["eps"] += e["regret"][-1]
    tot["ucb"] += u["regret"][-1]
    opt_end["greedy"] += sum(g["optimal"][-100:])
    opt_end["eps"] += sum(e["optimal"][-100:])
    opt_end["ucb"] += sum(u["optimal"][-100:])

check("averaged: eps-greedy beats pure greedy on regret",
      tot["eps"] < tot["greedy"],
      f"eps={tot['eps']/RUNS:.1f} greedy={tot['greedy']/RUNS:.1f}")
check("averaged: UCB beats eps-greedy on regret",
      tot["ucb"] < tot["eps"],
      f"ucb={tot['ucb']/RUNS:.1f} eps={tot['eps']/RUNS:.1f}")
check("averaged: UCB picks the optimal arm most often at the end",
      opt_end["ucb"] > opt_end["eps"] > opt_end["greedy"],
      f"ucb={opt_end['ucb']} eps={opt_end['eps']} greedy={opt_end['greedy']}")


print("\n[13] MC toys")
d = dice_convergence(20000, seed=0)
check("dice mean -> 3.5", abs(d[-1] - 3.5) < 0.05, f"{d[-1]:.4f}")
p = estimate_pi(50000, seed=0)
check("dart throw -> pi", abs(p[-1] - 3.14159265) < 0.03, f"{p[-1]:.4f}")


print("\n[14] Animated generators agree with their plain twins")
Pm = build_model("gym", "gym")
last = None
for snap in value_iteration_steps(Pm, gamma=0.99, theta=1e-10):
    last = snap
pi_v, V_v, _ = value_iteration(Pm, gamma=0.99, theta=1e-10)
check("value_iteration_steps ends where value_iteration does",
      all(approx(a, b, 1e-8) for a, b in zip(last.V, V_v)))
check("value_iteration_steps reports convergence", last.converged)

last_pi = None
for snap in policy_iteration_steps(Pm, gamma=0.99, theta=1e-10):
    last_pi = snap
pi_p, V_p, _ = policy_iteration(Pm, gamma=0.99, theta=1e-10)
check("policy_iteration_steps converges", last_pi.converged)
Va = policy_evaluation(Pm, last_pi.policy, 0.99, 1e-12)
Vb = policy_evaluation(Pm, pi_p, 0.99, 1e-12)
check("policy_iteration_steps finds an equally good policy",
      all(approx(a, b, 1e-8) for a, b in zip(Va, Vb)))


print("\n[15] Known-good reference numbers (Gymnasium FrozenLake-v1)")
# The canonical result everybody quotes for slippery FrozenLake-v1, gamma=0.99:
# optimal success rate is a bit above 70%, and V(start) sits near 0.54.
Pg = build_model("gym", "gym")
pi_g, V_g, _ = value_iteration(Pg, gamma=0.99, theta=1e-14)
check("V*(start) in the documented range for FL-v1",
      0.50 < V_g[START] < 0.58, f"V(start)={V_g[START]:.4f}")
env = FrozenLake(slip="gym", reward="gym", seed=99)
sr, mr, ml = evaluate_policy_empirically(env, pi_g, episodes=20000)
check("empirical success rate of pi* in 0.68..0.82", 0.68 < sr < 0.82,
      f"success={sr:.3f} mean_return={mr:.3f} mean_len={ml:.1f}")


print("\n[16] The four Bellman equations, as pages 12-15 present them")
Pm = build_model("classic", "shaped")
g = 0.99

# -- expectation: iterative sweeps, exact linear solve and Q-average must agree
for name, probs in (
        ("uniform pi", [[1.0 / N_ACTIONS] * N_ACTIONS for _ in range(N_STATES)]),
        ("always DOWN", deterministic_to_probs([1] * N_STATES)),
        ("mixed pi", [[0.1, 0.6, 0.2, 0.1] for _ in range(N_STATES)])):
    it = policy_evaluation_stochastic(Pm, probs, g, 1e-14, 20000)
    ex = policy_evaluation_exact(Pm, probs, g)
    check(f"sweeps == matrix solve  ({name})",
          all(approx(a, b, 1e-9) for a, b in zip(it, ex)),
          f"worst={max(abs(a - b) for a, b in zip(it, ex)):.2e}")
    # V^pi(s) = sum_a pi(a|s) Q^pi(s,a)  -- page 12's equation, read backwards
    Qp = q_table_from_V(Pm, ex, g)
    check(f"V^pi == sum_a pi(a|s) Q^pi  ({name})",
          all(approx(ex[s], sum(probs[s][a] * Qp[s][a] for a in range(N_ACTIONS)),
                     1e-9) for s in range(N_STATES)))
    # page 13 form A (inner pi-sum spelled out) == form B (using V^pi(s'))
    worst = 0.0
    for s in range(N_STATES):
        for a in range(N_ACTIONS):
            formA = 0.0
            for t in Pm[s][a]:
                inner = 0.0 if t.done else sum(
                    probs[t.next_state][a2] * Qp[t.next_state][a2]
                    for a2 in range(N_ACTIONS))
                formA += t.prob * (t.reward + g * inner)
            worst = max(worst, abs(formA - Qp[s][a]))
    check(f"Q^pi form A == form B  ({name})", worst < 1e-9, f"worst={worst:.2e}")

# -- the operator knob: max is value iteration, mean is uniform-random evaluation
Vmax, hmax = value_iteration_operator(Pm, g, "max", 1e-14, 20000)
_, Vvi, _ = value_iteration(Pm, gamma=g, theta=1e-14)
check("value_iteration_operator('max') == value_iteration",
      all(approx(a, b, 1e-10) for a, b in zip(Vmax, Vvi)))
Vavg, _ = value_iteration_operator(Pm, g, "mean", 1e-14, 20000)
uni = [[1.0 / N_ACTIONS] * N_ACTIONS for _ in range(N_STATES)]
check("value_iteration_operator('mean') == evaluating uniform-random pi",
      all(approx(a, b, 1e-8) for a, b in zip(Vavg, policy_evaluation_exact(Pm, uni, g))))
Vmin, _ = value_iteration_operator(Pm, g, "min", 1e-14, 20000)
check("min <= mean <= max at every state",
      all(Vmin[s] <= Vavg[s] + 1e-9 and Vavg[s] <= Vmax[s] + 1e-9
          for s in range(N_STATES)))
check("history[0] is all zeros and history[-1] is the answer",
      all(v == 0.0 for v in hmax[0])
      and all(approx(a, b, 1e-12) for a, b in zip(hmax[-1], Vmax)))

# -- optimality: Q* bridges back to V* on every state, and both iterations agree
Qstar, qhist = q_value_iteration_history(Pm, g, 1e-14, 20000)
check("max_a' Q*(s',a') == V*(s')  (the page-15 bridge)",
      all(approx(max(Qstar[s]), Vmax[s], 1e-9) for s in range(N_STATES)),
      f"worst={max(abs(max(Qstar[s]) - Vmax[s]) for s in range(N_STATES)):.2e}")
worst = 0.0
for s in range(N_STATES):
    for a in range(N_ACTIONS):
        rhs = 0.0
        for t in Pm[s][a]:
            boot = 0.0 if t.done else max(Qstar[t.next_state])
            rhs += t.prob * (t.reward + g * boot)
        worst = max(worst, abs(rhs - Qstar[s][a]))
check("Bellman optimality residual for Q* ~ 0", worst < 1e-9, f"worst={worst:.2e}")
check("q_value_iteration_history agrees with q_value_iteration",
      all(approx(a, b, 1e-12)
          for ra, rb in zip(qhist[-1], Qstar) for a, b in zip(ra, rb)))

# -- the contraction is real: error never shrinks slower than gamma per sweep
errs = [max(abs(hmax[k][s] - Vmax[s]) for s in range(N_STATES))
        for k in range(len(hmax))]
check("error is monotone non-increasing, and never slower than gamma^k",
      all(errs[k + 1] <= errs[k] * g + 1e-12 for k in range(len(errs) - 1)
          if errs[k] > 1e-13))


print("\n" + "=" * 62)
if FAILS:
    print(f"{len(FAILS)} FAILURE(S): " + ", ".join(FAILS))
    sys.exit(1)
print("ALL CHECKS PASSED")
