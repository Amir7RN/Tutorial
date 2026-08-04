# RL Tutor

An interactive, animated workbench for the reinforcement-learning fundamentals in
`RL.pdf` (pages 1, 3, 4, 5, 6, 7, 8, 11), built around the Frozen Lake environment.

29 pages, every algorithm live and steppable, every formula rendered, every code
panel pulled from the real source with `inspect.getsource` so nothing on screen
can drift out of sync with what actually ran.

Written to be read **in order** by someone who has not done RL before: page 1 is
a game you play with the arrow keys, and every symbol introduced later refers
back to something you have already felt.

## Run it

**Windows** — double-click `run.bat`.
**macOS / Linux** — `chmod +x run.sh` once, then `./run.sh`.

You need **Python 3.10 or newer** installed. Nothing else.

The first run builds a private virtual environment in `.venv/` and installs
PySide6, numpy and matplotlib **into it** — your system Python is never touched,
so this cannot disturb anything you already have. That takes a minute or two and
needs internet. Every run after that is instant and works offline.

To uninstall completely: delete the folder.

If you'd rather manage the environment yourself:

```
pip install -r requirements.txt
python -m app.main
```

`Ctrl+←` / `Ctrl+→` move between pages.

### Sending it to somebody else

Run `pack.ps1` (right-click → *Run with PowerShell*). It writes a clean
`RL_Tutor.zip` next to the folder — about **120 KB**.

It deliberately leaves out `.venv/` (a built one is ~770 MB of installed
packages, and it would not work on their machine anyway), plus `__pycache__/`
and any screenshot folders.

The recipient unzips it anywhere and double-clicks `run.bat` (or `./run.sh`).
They do **not** need this repo, your Python installation, `RL.pdf`, or any prior
setup — only **Python 3.10+**.

## Layout

```
RL_Tutor/
  run.bat                  launcher
  rlcore/                  THE ALGORITHMS -- pure Python, zero Qt
    frozen_lake.py           environment: build_model() and FrozenLake()
    dp.py                    policy eval/improve, policy iteration, value iteration
    mc.py                    MC prediction (FVMC/EVMC), MC control
    bandit.py                epsilon-greedy vs UCB
  app/                     THE GUI
    main.py                  window + sidebar
    theme.py                 palette and stylesheet
    widgets/                 grid painter, code pane, math renderer, plots
    pages/                   the 29 pages (intro.py holds the opening sequence)
      bellman.py               pages 12-15: one page per Bellman equation
  tests/
    test_core.py             correctness checks -- run this first
    smoke_gui.py             builds every page headless and screenshots it
```

`rlcore/` imports nothing from `app/`. You can use it standalone:

```python
from rlcore import *

P = build_model(slip="classic", reward="shaped")
pi, V, sweeps = value_iteration(P, gamma=0.99)
print(sweeps, round(V[0], 4), [ACTION_ARROWS[a] for a in pi[:4]])

env = FrozenLake(slip="classic", reward="shaped", seed=0)
Q, pi_mc, stats = mc_control(env, episodes=30000)
print(stats["success_rate"])
```

## The pages

The order is deliberately **concrete before abstract**. You walk the lake by
hand before anything is given a symbol, and no page shows a number whose origin
has not already been built up.

| # | Page | Notes page |
|---|------|-----------|
| | **Start Here** — the environment, then the vocabulary | |
| 1 | What is Reinforcement Learning? *(you play it, by hand)* | p.1, p.6 |
| 2 | The Frozen Lake *(the board and its geometry)* | p.1 |
| 3 | Stochastic Transitions *(the slippery ice, with real probabilities)* | p.1 |
| 4 | Rewards *(what the lake pays you; sparse vs shaped)* | p.1, p.6 §2.2.5 |
| 5 | Return & the Discount Factor *(a list of rewards → one number)* | p.1, p.6 |
| 6 | Policies *(the thing we are searching for)* | p.1, p.6 |
| 7 | The Markov Decision Process *(all five pieces, formally named)* | p.1 |
| | **Value Functions** — how good is a square? | |
| 8 | V(s) — State Value | p.1 §2.6.2 |
| 9 | Q(s,a) — Action Value | p.1 §2.6.3 |
| 10 | V vs Q — the Difference | p.1, p.7 |
| 11 | The Bellman Equations *(all four at once — the map)* | p.1, p.5 |
| 12 | Bellman ① V<sup>π</sup> *(expectation — drag π(a\|s) and watch V move)* | p.1, p.5 |
| 13 | Bellman ② Q<sup>π</sup> *(the π-average, delayed one step)* | p.1, p.5 |
| 14 | Bellman ③ V\* *(optimality — swap max for min and see)* | p.1, p.5 |
| 15 | Bellman ④ Q\* *(the max, delayed one step → Q-learning)* | p.1, p.5 |
| | **Dynamic Programming** — solve it, knowing the ice | |
| 16 | Policy Evaluation | p.4, p.6 |
| 17 | Policy Improvement | p.4, p.6 |
| 18 | Policy Iteration | p.3, p.4 |
| 19 | Value Iteration | p.3, p.4 |
| 20 | Policy vs Value Iteration | p.3, p.4 |
| | **Monte Carlo** — learn it, *not* knowing the ice | |
| 21 | Monte Carlo = Averaging | p.5 |
| 22 | MC Prediction (FVMC/EVMC) | p.5 §4.2–4.3 |
| 23 | MC Control (GPI) | p.5 §4.4 |
| | **Beyond** | |
| 24 | Exploration vs Exploitation | p.1 §2.5 |
| 25 | Model-Based vs Model-Free | p.4, p.5 |
| 26 | Hyperparameters | p.6 §2.6 |
| 27 | What "Convergence" Means | p.11 |
| 28 | Code Lab | — |
| 29 | Adam, Backprop & BatchNorm | p.8 |

Pages 12–15 exist because page 11 is a summary, and a summary is the wrong place
to learn four equations that look interchangeable side by side. Each of the four
gets its own page with the arithmetic written out branch by branch off the real
lake, an interactive backup tree, and the plots that make the operator visible.
They are all built on one sentence: **the Q equations are the V equations with
the action-choice delayed by one step**, because Q's first action is handed to
you and the choosing cannot happen until the next square.

Page numbers are **not** written in the page files. `app/pages/__init__.py`
stamps `NUM` onto each class from its position in `PAGE_CLASSES`, so reordering
that one list renumbers the headers and the sidebar together.

## Conventions

Everything uses the **Gymnasium FrozenLake-v1** convention, so results are
comparable with published numbers:

- Actions: `0=LEFT 1=DOWN 2=RIGHT 3=UP`
- State index: `s = row * 4 + col`
- Map: start 0, holes {5, 7, 11, 12}, goal 15
- Walking into a wall is legal — you stay put
- Terminal states absorb with reward 0, so `V(terminal) = 0`

Two knobs are exposed everywhere, because the choice changes the answer:

**Slip model** — probability the commanded action actually executes:
| key | intended | perpendicular | source |
|-----|----------|---------------|--------|
| `gym` | 1/3 | 1/3, 1/3 | official `is_slippery=True`; the 0.33/0.66 split in your notes |
| `classic` | 0.8 | 0.1, 0.1 | Russell & Norvig; the setting in your C++ files |
| `deterministic` | 1.0 | 0, 0 | `is_slippery=False` |

**Reward scheme**:
| key | goal | hole | step |
|-----|------|------|------|
| `gym` | +1 | 0 | 0 |
| `shaped` | +1 | −1 | −0.04 |

## Verification

```
python tests/test_core.py     # all must pass
python tests/smoke_gui.py     # builds all 29 pages, screenshots to _shots/
```

`test_core.py` checks, among other things:

- every `P[s][a]` is a valid probability distribution, for all 6 slip×reward combos
- `(a±1)%4` really are perpendicular to `a`, and `(a+2)%4` is its reverse
- policy iteration and value iteration reach the **same** V (they may pick
  different actions only where Q ties exactly)
- `max_a Q*(s,a) == V*(s)`
- Bellman optimality and expectation residuals are ~1e-14
- `V^π(s) == Σ_a π(a|s) Q^π(s,a)`, including for a stochastic π
- iterative policy evaluation == the exact linear solve `(I − γP_π)V = r_π`, for
  three different policies
- `Q^π` computed with the inner π-sum spelled out == computed from `V^π(s')`
- `value_iteration_operator` with `max` == value iteration, with `mean` ==
  evaluating uniform-random π, and `min ≤ mean ≤ max` at every state
- the value-iteration error is monotone and never shrinks slower than γ per sweep
- `V(start) == γ⁵` on the deterministic map (6 moves, reward on the 6th)
- sampled transition frequencies match `P[s][a]` to <1%
- FVMC and EVMC both converge to the DP answer
- MC control gets within 0.15 of optimal `V(start)`
- **against published reference values**: `V*(start) ≈ 0.54` and empirical
  success rate ≈ 74% for slippery FrozenLake-v1 at γ=0.99

## Notes on the C++ files in the parent folder

Covered in detail on page 28 (Code Lab). Summary:

- `RL-FrozenLake_ValIter.cpp` — **correct**. (`theta = 1e-100` is below double
  precision, so it stops on bit-equality rather than the threshold. Harmless.)
- `RL-FrozenLake_Prob.cpp` — **two real bugs**.
  (a) `get_next_state` has every `min`/`max` inverted: `row = min(0, row+1)` is
  always 0, `row = max(3, row+1)` is always 3, `col = min(0, col-1)` goes to −1
  at the left edge, and the RIGHT branch assigns to `row` using `col`. From
  state 9, UP returns 1 (should be 5) and RIGHT returns 13 (should be 10).
  (b) `policy_improvement` takes `Policy pi` **by value**, so the improved
  policy is written to a copy and discarded — `policy_iteration` re-evaluates
  the same all-zero policy forever. It also compares action indices rather than
  Q-values, which would loop forever on ties even once the reference is fixed.
- `RL-FrozenLake_MontoCarlo.cpp` — **one real bug**: `uniform_int_distribution`
  where `uniform_real_distribution` is meant, so ε-greedy explores ~50% of the
  time regardless of ε and the decay does nothing.

The three files also use three *different* action encodings, so their printed
policies are not comparable with each other.
