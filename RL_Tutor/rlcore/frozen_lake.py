"""
Frozen Lake environment -- the single source of truth for every page in the tutor.

Two things live here, and it is important you keep them separate in your head:

  1. THE MODEL  P[s][a] -> [(prob, next_state, reward, done), ...]
     This is the MDP's transition function written down as a table.
     Dynamic Programming (policy iteration / value iteration) READS this table.
     A real robot never has it.

  2. THE SIMULATOR  env.step(a) -> (next_state, reward, done)
     This SAMPLES from the same distribution, one transition at a time.
     Monte Carlo / TD / Q-learning use only this. They are "model-free".

Both are built from the same `slip` numbers, so any disagreement between a DP
answer and an MC answer is a property of the algorithm, never of the physics.

Grid layout (4x4), state index s = row * 4 + col:

     0  1  2  3        S  F  F  F
     4  5  6  7        F  H  F  H
     8  9 10 11        F  F  F  H
    12 13 14 15        H  F  F  G

    S = start (state 0)   H = hole {5, 7, 11, 12}   G = goal (state 15)

ACTION ENCODING (Gymnasium convention -- used everywhere in this project):

    0 = LEFT    1 = DOWN    2 = RIGHT    3 = UP

Why this order matters: it puts the two PERPENDICULAR actions at (a+1) % 4 and
(a-1) % 4. That single fact is what makes the slip model a one-liner.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

GRID = 4
N_STATES = GRID * GRID
N_ACTIONS = 4

LEFT, DOWN, RIGHT, UP = 0, 1, 2, 3
ACTION_NAMES = ["LEFT", "DOWN", "RIGHT", "UP"]
ACTION_ARROWS = ["←", "↓", "→", "↑"]  # < v > ^

HOLES = frozenset({5, 7, 11, 12})
GOAL = 15
START = 0

# (drow, dcol) for each action index
_DELTA = {
    LEFT:  (0, -1),
    DOWN:  (+1, 0),
    RIGHT: (0, +1),
    UP:    (-1, 0),
}


# --------------------------------------------------------------------------
# Reward + slip presets
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class RewardScheme:
    """How the environment pays the agent."""
    name: str
    goal: float
    hole: float
    step: float
    blurb: str


REWARD_SCHEMES = {
    # The official OpenAI / Gymnasium FrozenLake-v1 reward. Extremely sparse:
    # the agent sees a single +1 at the very end, and nothing else, ever.
    "gym": RewardScheme(
        name="Gymnasium (sparse)",
        goal=1.0, hole=0.0, step=0.0,
        blurb="+1 at the goal, 0 everywhere else. This is the real FrozenLake-v1. "
              "Sparse reward: the agent gets ZERO feedback until it stumbles into "
              "the goal by luck. Hard for Monte Carlo, trivial for DP.",
    ),
    # The Russell & Norvig 'grid world' style reward, and the one used in the
    # C++ files in this folder (RL-FrozenLake_ValIter.cpp etc).
    "shaped": RewardScheme(
        name="Shaped (your C++ files)",
        goal=1.0, hole=-1.0, step=-0.04,
        blurb="+1 goal, -1 hole, -0.04 per step. The step cost creates urgency "
              "(dawdling is punished) and the hole penalty creates real fear. "
              "Much friendlier gradient for model-free learning.",
    ),
}


@dataclass(frozen=True)
class SlipModel:
    """
    Probability of what ACTUALLY happens when the agent COMMANDS action `a`.

        intended    -> the action the agent asked for
        perp_cw     -> (a + 1) % 4   (90 deg one way)
        perp_ccw    -> (a - 1) % 4   (90 deg the other way)

    The reverse action never happens -- you cannot slip backwards.
    Must sum to 1.0.
    """
    name: str
    intended: float
    perp_cw: float
    perp_ccw: float
    blurb: str

    def as_pairs(self, a: int) -> list[tuple[float, int]]:
        """-> [(probability, actual_action), ...], dropping zero-probability moves."""
        pairs = [
            (self.intended, a),
            (self.perp_cw, (a + 1) % N_ACTIONS),
            (self.perp_ccw, (a - 1) % N_ACTIONS),
        ]
        return [(p, m) for (p, m) in pairs if p > 0.0]


SLIP_MODELS = {
    "gym": SlipModel(
        name="Gymnasium slippery (1/3, 1/3, 1/3)",
        intended=1.0 / 3.0, perp_cw=1.0 / 3.0, perp_ccw=1.0 / 3.0,
        blurb="The official is_slippery=True setting. Your command is obeyed only "
              "1/3 of the time -- you are as likely to go sideways as forward. "
              "This is the 0.33 / 0.66 split described in your notes.",
    ),
    "classic": SlipModel(
        name="Classic slippery (0.8, 0.1, 0.1)",
        intended=0.8, perp_cw=0.1, perp_ccw=0.1,
        blurb="The Russell & Norvig setting used in your C++ files. Mostly obeys "
              "you, occasionally slips 90 degrees. Optimal policies here look far "
              "more 'sensible' than under the 1/3 model.",
    ),
    "deterministic": SlipModel(
        name="Deterministic (no ice)",
        intended=1.0, perp_cw=0.0, perp_ccw=0.0,
        blurb="is_slippery=False. The MDP collapses to an ordinary shortest-path "
              "problem -- this is where RL and A*/Dijkstra give the same answer.",
    ),
}


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------

def to_rc(s: int) -> tuple[int, int]:
    """state index -> (row, col)"""
    return divmod(s, GRID)


def to_s(row: int, col: int) -> int:
    """(row, col) -> state index"""
    return row * GRID + col


def move(s: int, action: int) -> int:
    """
    Apply one action on the grid, CLIPPED at the walls.

    Walking into a wall is legal and costs you a turn -- you simply stay put.
    That is why `min`/`max` appear here and not an exception.
    """
    row, col = to_rc(s)
    drow, dcol = _DELTA[action]
    row = max(0, min(GRID - 1, row + drow))
    col = max(0, min(GRID - 1, col + dcol))
    return to_s(row, col)


def is_terminal(s: int) -> bool:
    return s == GOAL or s in HOLES


def cell_kind(s: int) -> str:
    if s == GOAL:
        return "goal"
    if s in HOLES:
        return "hole"
    if s == START:
        return "start"
    return "frozen"


# --------------------------------------------------------------------------
# 1. THE MODEL  -- what Dynamic Programming is allowed to look at
# --------------------------------------------------------------------------

@dataclass
class Transition:
    """One branch of P(s', r | s, a)."""
    prob: float
    next_state: int
    reward: float
    done: bool

    def as_tuple(self):
        return (self.prob, self.next_state, self.reward, self.done)


def build_model(slip: str = "gym", reward: str = "gym") -> list[list[list[Transition]]]:
    """
    Build P[s][a] -> list of Transition.

    THIS IS THE HEART OF THE WHOLE PROJECT. Read it slowly.

    For every state s and every commanded action a, we enumerate every possible
    outcome together with its probability. Nothing here is sampled -- this is the
    exact distribution. Value iteration and policy iteration consume exactly this.

    Terminal states (holes + goal) get an absorbing self-loop with reward 0. Once
    you are in them, the episode is over and no further reward is possible, which
    is the code-level statement of "V(terminal) = 0".
    """
    sm = SLIP_MODELS[slip]
    rs = REWARD_SCHEMES[reward]

    P: list[list[list[Transition]]] = [
        [[] for _ in range(N_ACTIONS)] for _ in range(N_STATES)
    ]

    for s in range(N_STATES):
        for a in range(N_ACTIONS):

            # --- absorbing states: the game is already over -------------------
            if is_terminal(s):
                P[s][a].append(Transition(1.0, s, 0.0, True))
                continue

            # --- the slip: one command, several possible real moves -----------
            for prob, actual in sm.as_pairs(a):
                nxt = move(s, actual)

                if nxt == GOAL:
                    r, done = rs.goal, True
                elif nxt in HOLES:
                    r, done = rs.hole, True
                else:
                    r, done = rs.step, False

                P[s][a].append(Transition(prob, nxt, r, done))

    return P


def merge_duplicates(branches: list[Transition]) -> list[Transition]:
    """
    Two different slips can land on the SAME square (very common in corners,
    where clipping collapses two moves into one). For display it is clearer to
    add their probabilities together. The maths is identical either way.
    """
    acc: dict[tuple[int, float, bool], float] = {}
    for t in branches:
        key = (t.next_state, t.reward, t.done)
        acc[key] = acc.get(key, 0.0) + t.prob
    out = [Transition(p, ns, r, d) for (ns, r, d), p in acc.items()]
    out.sort(key=lambda t: -t.prob)
    return out


# --------------------------------------------------------------------------
# 2. THE SIMULATOR -- all a model-free agent ever gets to touch
# --------------------------------------------------------------------------

@dataclass
class FrozenLake:
    """
    Sampling interface. Deliberately gives you NO access to `P`.

    This is the whole model-free / model-based divide expressed as an API:
    Monte Carlo can call reset()/step() as often as it likes, but it can never
    ask "what were the odds?" -- it has to find that out by getting wet.
    """
    slip: str = "gym"
    reward: str = "gym"
    seed: int | None = None
    state: int = START
    done: bool = True
    rng: random.Random = field(default_factory=random.Random, repr=False)

    #: what the ice ACTUALLY executed on the last step(). The agent is not
    #: supposed to learn from this -- it exists so the tutor can show you the
    #: difference between what you commanded and what happened.
    last_actual: int | None = None
    last_bumped: bool = False

    def __post_init__(self):
        self.rng = random.Random(self.seed)
        self._sm = SLIP_MODELS[self.slip]
        self._rs = REWARD_SCHEMES[self.reward]

    def reset(self) -> int:
        self.state = START
        self.done = False
        return self.state

    def sample_actual_action(self, a: int) -> int:
        """Roll the ice. Returns the action that ACTUALLY gets executed."""
        roll = self.rng.random()
        cum = 0.0
        for prob, actual in self._sm.as_pairs(a):
            cum += prob
            if roll < cum:
                return actual
        return a  # float dust guard

    def step(self, a: int) -> tuple[int, float, bool]:
        """One interaction. Returns (next_state, reward, done)."""
        if self.done:
            raise RuntimeError("episode is over -- call reset() first")

        actual = self.sample_actual_action(a)
        nxt = move(self.state, actual)

        # bookkeeping for the tutor's step log (not used by any algorithm)
        self.last_actual = actual
        self.last_bumped = (nxt == self.state)

        if nxt == GOAL:
            r, done = self._rs.goal, True
        elif nxt in HOLES:
            r, done = self._rs.hole, True
        else:
            r, done = self._rs.step, False

        self.state = nxt
        self.done = done
        return nxt, r, done


# --------------------------------------------------------------------------
# Rollout helper (shared by the Monte Carlo pages)
# --------------------------------------------------------------------------

def run_episode(env: FrozenLake, policy_fn, max_steps: int = 200):
    """
    Play one full episode. `policy_fn(state) -> action`.

    Returns a list of (state, action, reward) -- exactly the "trajectory" from
    your notes:  tau = (s0, a0, r1, s1, a1, r2, ...)
    """
    traj = []
    s = env.reset()
    for _ in range(max_steps):
        a = policy_fn(s)
        nxt, r, done = env.step(a)
        traj.append((s, a, r))
        s = nxt
        if done:
            break
    return traj


# --------------------------------------------------------------------------
# Small utilities the GUI leans on
# --------------------------------------------------------------------------

def greedy_policy_from_V(P, V, gamma: float) -> list[int]:
    """pi(s) = argmax_a  sum_s' P(s'|s,a) [ r + gamma * V(s') ]"""
    pi = [0] * N_STATES
    for s in range(N_STATES):
        best_a, best_q = 0, float("-inf")
        for a in range(N_ACTIONS):
            q = q_from_V(P, V, s, a, gamma)
            if q > best_q:
                best_q, best_a = q, a
        pi[s] = best_a
    return pi


def q_from_V(P, V, s: int, a: int, gamma: float) -> float:
    """
    One-step lookahead -- turns a state-value into an action-value.

        Q(s,a) = sum_{s'} P(s'|s,a) * [ r + gamma * V(s') ]

    Note the `0.0 if t.done else V[...]`: a terminal successor contributes only
    its immediate reward, because there is no future left to discount.
    """
    total = 0.0
    for t in P[s][a]:
        bootstrap = 0.0 if t.done else V[t.next_state]
        total += t.prob * (t.reward + gamma * bootstrap)
    return total


def q_table_from_V(P, V, gamma: float) -> list[list[float]]:
    return [[q_from_V(P, V, s, a, gamma) for a in range(N_ACTIONS)]
            for s in range(N_STATES)]


def V_from_Q(Q, policy_probs) -> list[float]:
    """
    V^pi(s) = sum_a pi(a|s) * Q^pi(s,a)

    Straight out of your page-1 notes: "The State Value V is just the weighted
    average of all your Action Values Q."
    """
    return [sum(policy_probs[s][a] * Q[s][a] for a in range(N_ACTIONS))
            for s in range(N_STATES)]


def deterministic_to_probs(pi: list[int]) -> list[list[float]]:
    """pi(s) = a   ->   pi(a|s) as a one-hot row."""
    probs = [[0.0] * N_ACTIONS for _ in range(N_STATES)]
    for s, a in enumerate(pi):
        probs[s][a] = 1.0
    return probs


def epsilon_greedy_probs(Q, eps: float) -> list[list[float]]:
    """pi(a|s) = 1 - eps + eps/|A|  for the greedy action, eps/|A| otherwise."""
    probs = []
    for s in range(N_STATES):
        best = max(range(N_ACTIONS), key=lambda a: Q[s][a])
        row = [eps / N_ACTIONS] * N_ACTIONS
        row[best] += 1.0 - eps
        probs.append(row)
    return probs
