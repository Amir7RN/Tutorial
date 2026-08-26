"""
rlcore -- the algorithms, with no GUI attached.

Everything in here is plain Python + the standard library. You can import it
from a notebook, a script, or the REPL and it behaves identically to what the
tutor draws on screen. The GUI never re-implements an algorithm; it only calls
these functions and paints the results.

Quick tour:

    frozen_lake.py   the environment, in BOTH forms:
                     build_model(...)  -> P[s][a], the table DP is allowed to read
                     FrozenLake(...)   -> .reset()/.step(), all MC ever sees

    dp.py            model-BASED: policy evaluation, policy improvement,
                     policy iteration, value iteration, Q-value iteration

    mc.py            model-FREE: first/every-visit MC prediction, MC control
                     with epsilon-greedy GPI

    bandit.py        the one-state MDP: epsilon-greedy vs UCB

    deeprl.py        continuous actions: an MLP with a hand-written backward
                     pass, a replay buffer, and DDPG. The one module that
                     needs numpy -- see its docstring for why.

Try it:

    >>> from rlcore import build_model, value_iteration, ACTION_ARROWS
    >>> P = build_model(slip="classic", reward="shaped")
    >>> pi, V, sweeps = value_iteration(P, gamma=0.99)
    >>> print(sweeps, [ACTION_ARROWS[a] for a in pi[:4]])
"""

from .frozen_lake import (  # noqa: F401
    ACTION_ARROWS,
    ACTION_NAMES,
    DOWN,
    GOAL,
    GRID,
    HOLES,
    LEFT,
    N_ACTIONS,
    N_STATES,
    REWARD_SCHEMES,
    RIGHT,
    SLIP_MODELS,
    START,
    UP,
    FrozenLake,
    RewardScheme,
    SlipModel,
    Transition,
    build_model,
    cell_kind,
    deterministic_to_probs,
    epsilon_greedy_probs,
    greedy_policy_from_V,
    is_terminal,
    merge_duplicates,
    move,
    q_from_V,
    q_table_from_V,
    run_episode,
    to_rc,
    to_s,
    V_from_Q,
)

from .dp import (  # noqa: F401
    Snapshot,
    evaluate_policy_empirically,
    policy_evaluation,
    policy_evaluation_exact,
    policy_evaluation_history,
    policy_evaluation_steps,
    policy_evaluation_stochastic,
    policy_improvement,
    policy_iteration,
    policy_iteration_steps,
    q_value_iteration,
    q_value_iteration_history,
    value_iteration,
    value_iteration_operator,
    value_iteration_steps,
)

from .mc import (  # noqa: F401
    MCSnapshot,
    dice_convergence,
    epsilon_greedy,
    estimate_pi,
    mc_control,
    mc_control_steps,
    mc_prediction,
    mc_prediction_steps,
)

from .bandit import (  # noqa: F401
    Bandit,
    compare,
    epsilon_greedy_run,
    ucb_run,
)

from .deeprl import (  # noqa: F401
    ALGO_TABLE,
    ContextualReach,
    DDPG,
    DDPGConfig,
    Dense,
    GaitTuneEnv,
    MLP,
    ReplayBuffer,
    TrainLog,
    rollout_gait,
    train_gait,
    train_reach,
)

__all__ = [n for n in dir() if not n.startswith("_")]
