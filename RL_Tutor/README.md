# Control & RL Tutor

An interactive, animated workbench for the fundamentals of **robot control,
actuator dynamics and reinforcement learning** — built from `Impedance_Material.pdf`
(pages 1–6, 9, 10), the Best/Rouse/Gregg impedance-control paper
(`ImpedanceControl.pdf`), and `RL.pdf` (pages 1, 3, 4, 5, 6, 7, 8, 11).

64 pages, every algorithm live and steppable, every formula rendered, every code
panel pulled from the real source with `inspect.getsource` so nothing on screen
can drift out of sync with what actually ran.

The tutor is in two halves and is written to be read **in order**:

1. **Control & dynamics (pages 1–35)** — what the world physically feels when it
   touches the robot, and how a controller can shape that. Starts from real-time
   constraints and `J_eff = J_m + J_L`, and ends at the biomechanics that
   motivate the whole design.
2. **Reinforcement learning (pages 36–64)** — how a policy is found for a machine
   whose dynamics you now understand. Page 36 is a game you play with the arrow
   keys, and every symbol introduced later refers back to something you have
   already felt.

**Page 1 is real-time control**, on purpose. Every later page makes a claim about
how fast something can respond, and every one of those claims is bounded by
sampling, delay and scheduling. The single most useful thing on it: your loop
rate is *not* your bandwidth — a 1 kHz loop buys you roughly 50–100 Hz of
control authority, and the mechanics may cap you lower still.

The join between the two halves is not decorative. An RL agent never learns a
control law in the abstract; it learns one for a specific plant with a specific
effective inertia, bandwidth and safety envelope. The first half is that plant.

## Run it

Starting from a fresh machine:

```bash
git clone https://github.com/Amir7RN/Tutorial.git
cd Tutorial/RL_Tutor
```

Then:

**Windows** — double-click `run.bat`.
**macOS / Linux** — `chmod +x run.sh` once, then `./run.sh`.

You need **Python 3.10 or newer** installed. Nothing else. (On Windows, tick
**"Add python.exe to PATH"** in the installer.)

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

`Ctrl+←` / `Ctrl+→` move between pages. The sidebar groups the 64 pages into
collapsible sections — click a section header to expand it — and `Ctrl+F` focuses
the filter box.

### Sending it to somebody else

Run `pack.ps1` (right-click → *Run with PowerShell*). It writes a clean
`RL_Tutor.zip` next to the folder — about **490 KB**.

It deliberately leaves out `.venv/` (a built one is ~770 MB of installed
packages, and it would not work on their machine anyway), plus `__pycache__/`
and any screenshot folders.

The recipient unzips it anywhere and double-clicks `run.bat` (or `./run.sh`).
They do **not** need this repo, your Python installation, the source PDFs, or
any prior setup — only **Python 3.10+**.

## Layout

```
RL_Tutor/
  run.bat                  launcher
  ctrlcore/                THE PHYSICS -- pure Python, zero Qt
    actuators.py             J_eff for DD/SEA/PEA, the three SEA frequencies,
                             gearing, square-cube scaling
    impedance.py             position / torque / impedance / admittance control
    neuro.py                 Hill muscle model, positive force feedback
    linear.py                poles, step response, Bode, margins, Nyquist,
                             Routh, root locus, compensators, pole placement,
                             observers
    nonlinear.py             the pendulum, phase portraits, limit cycles, and
                             the six nonlinear control approaches
    realtime.py              sampling, aliasing, jitter, scheduling, and a PID
                             with anti-windup and a filtered derivative
  rlcore/                  THE RL ALGORITHMS -- pure Python, zero Qt
    frozen_lake.py           environment: build_model() and FrozenLake()
    dp.py                    policy eval/improve, policy iteration, value iteration
    mc.py                    MC prediction (FVMC/EVMC), MC control
    bandit.py                epsilon-greedy vs UCB
  app/                     THE GUI
    main.py                  window + sidebar
    theme.py                 palette and stylesheet
    widgets/                 grid painter, code pane, math renderer, plots
    widgets/diagram.py       BlockDiagram -- the control block diagrams
    pages/                   the 64 pages
      realtime.py              page  1:     real-time control
      linsys.py                pages 2-6:   first/second order, stability,
                                            Bode, Nyquist
      ctrldesign.py            pages 7-10:  root locus, lead/lag, state
                                            feedback, observers
      nonlin.py                pages 11-12: nonlinear systems and control
      motors.py                pages 13-17: actuator mechanics
      paradigms.py             pages 18-25: the control paradigms
      pid.py                   page  20:    PID in practice
      design.py                pages 26-28: drivetrain choice, scaling, 1X Neo
      proprio.py               pages 29-31: proprioception
      forcefb.py               pages 32-33: positive force feedback
      biodesign.py             pages 34-35: bio -> robot translation
      intro.py                 pages 36-40: the RL opening sequence
      bellman.py               pages 47-50: one page per Bellman equation
  tests/
    test_ctrl.py             correctness checks for ctrlcore
    test_linear.py           correctness checks for linear.py / nonlinear.py
    test_core.py             correctness checks for rlcore
    smoke_gui.py             builds every page headless and screenshots it
```

Neither `ctrlcore/` nor `rlcore/` imports anything from `app/`. Both are usable
standalone:

```python
from ctrlcore import j_eff_sea, sea_bandwidth_hz, two_controller_demo

# an SEA hides the rotor at impact frequencies and not at low ones
print(j_eff_sea(0.04, 0.06, 300, omega=0.0))    # 0.10  = Jm + JL
print(j_eff_sea(0.04, 0.06, 300, omega=1e5))    # 0.06  = JL alone
print(sea_bandwidth_hz(300, 0.06))              # ~11 Hz

# two controllers, same tau_ff, very different K and B -> identical nominal torque
_, _, tau_a, tau_b, _, _ = two_controller_demo(160, 9.6, 45, 2.7, perturb_deg=0)
print(max(abs(a - b) for a, b in zip(tau_a, tau_b)))   # 0.0
```

```python
from rlcore import *

P = build_model(slip="classic", reward="shaped")
pi, V, sweeps = value_iteration(P, gamma=0.99)
print(sweeps, round(V[0], 4), [ACTION_ARROWS[a] for a in pi[:4]])
```

## Part I — Control & Dynamics (pages 1–35)

The order is **theory, then mechanics, then control, then biology**. The linear
systems block comes early only to supply vocabulary: "bandwidth", "damping" and
"phase margin" are load-bearing words from the actuator pages onwards, and none
of them means anything until you have watched a pole move. After that the order
is **mechanics before control**, because you cannot argue about impedance
control until you know what the environment actually feels when it touches the
robot, and that number is fixed by hardware long before any software runs.

| # | Page | Source |
|---|------|--------|
| | **Real-Time** — the constraint everything else is bounded by | |
| 1 | Real-Time Control *(hard vs soft, Nyquist, aliasing, jitter, FreeRTOS scheduling)* | — |
| | **Systems & Stability** — what "pole", "damping" and "margin" mean | |
| 2 | First-Order Systems *(one pole, one time constant, and the 90° phase ceiling that makes it unconditionally safe)* | — |
| 3 | Second-Order Systems *(ω_n and ζ — and the fact that your impedance K and B **are** ω_n and ζ)* | — |
| 4 | Stability & How to Check It *(LHP, marginal as its own category, Routh–Hurwitz)* | — |
| 5 | Bode Plots, Gain & Phase Margin *(how far from the edge, and PM ≈ 100ζ)* | — |
| 6 | The Nyquist Plot *(the −1 point, Z = N + P, and the vector margin that does not lie)* | — |
| | **Controller Design** — moving the poles on purpose | |
| 7 | Making It Stable *(root locus; D adds a zero and that is why it damps; the inverted pendulum needs both K_p > mgl and K_d > 0)* | — |
| 8 | Lead, Lag & Notch *(designed, not tuned — and why a notch betrays you in service)* | — |
| 9 | State Feedback & Pole Placement *(controllability as a mechanical verdict; Ackermann; LQR)* | — |
| 10 | Observers & Observability *(Luenberger, duality, separation; the disturbance observer behind "sensorless" collision detection)* | — |
| | **Nonlinear** — what all of the above was assuming | |
| 11 | Nonlinear Systems *(the six places a robot breaks superposition; phase portraits, basins, limit cycles from stiction)* | — |
| 12 | Controlling a Nonlinear Robot *(gain scheduling, computed torque, sliding mode, Lyapunov, passivity — then the handover to RL)* | — |
| | **Actuators** — what the world actually feels | |
| 13 | Effective Inertia *(direct drive, and what J_eff means for design, motor spec and control)* | material p.1–3 |
| 14 | Series Elastic Actuators *(the spring between, and the **three** frequencies people conflate)* | material p.2 |
| 15 | Parallel Elastic Actuators *(the spring alongside; what negative J_eff really means)* | material p.3 |
| 16 | DD vs SEA vs PEA *(torque, speed, inertia, bandwidth — and which is "better", per band)* | material p.2–3 |
| 17 | Gearing & Reflected Inertia *(the N² square law, and three ways out of it)* | material p.1 |
| | **Control Paradigms** — four answers to one question | |
| 18 | The Goal of Control *(the agent–environment loop, shared with the RL half)* | — |
| 19 | Position Control *(command where; accept whatever force that takes)* | — |
| 20 | PID in Practice *(anti-windup, derivative filtering, and what jitter breaks)* | real-time |
| 21 | Torque & Current Control *(the cascade: every paradigm is current control underneath)* | — |
| 22 | Impedance Control *(motion in → force out; θ_eq vs θ_d; PD vs impedance)* | material p.1 · Hogan 1984 |
| 23 | Admittance Control *(force in → motion out; the shape of the response)* | material p.1 |
| 24 | Impedance vs Admittance *(the decision, and the hardware that forces it)* | material p.1 |
| 25 | The Impedance Spectrum *(they were all one controller all along)* | ImpedanceControl.pdf |
| | **Robot Design** | |
| 26 | Which Actuator, Which Robot *(humanoid vs biped vs quadruped)* | material p.4 |
| 27 | Scaling Up: The Square-Cube Law *(m∝L³, τ∝L², J∝L⁵)* | material p.4 |
| 28 | Case Study: 1X Neo *(tendon-driven proprioceptive QDD)* | material p.5 |
| | **Proprioception** | |
| 29 | Proprioception in Biology *(spindles, GTOs, and the timescales)* | material p.6 |
| 30 | Robotic Proprioception *(transparency is the prerequisite, not the goal)* | material p.6 |
| 31 | Active Proprioceptive Compliance *(software-defined compliance, three layers)* | material p.6 |
| | **Force Feedback** | |
| 32 | Positive Force Feedback *(why "positive" is not a mistake)* | material p.9 |
| 33 | Closing the Force Loop *(the maths, live, and the honesty test)* | material p.9 |
| | **Bio → Robot** | |
| 34 | Actuation & Sensing *(muscles and receptors as design requirements)* | material p.10 |
| 35 | Skin & Bone *(the structures that shape force before control runs)* | material p.10 |

### What the interactive pages actually let you do

- **Pages 2–3** put the pole map next to the step response, so changing ζ and
  watching the poles ride the ω_n circle is one gesture. Page 3's second widget
  is the same thing in J, K, B, and shows the standard impedance-tuning mistake
  directly: double K alone and ζ **falls** by √2, so the joint rings more.
- **Page 5** builds a loop out of a real joint plus gain, derivative, a
  mechanical resonance and loop delay, and shows Bode magnitude, phase and the
  closed-loop step together. Turn the delay up and the magnitude curve does not
  move at all while the phase margin drains away — page 1's "delay is pure
  loss", drawn.
- **Page 7** sweeps the loop gain along the root locus with the closed-loop
  step beside it, then lets you balance an inverted pendulum: with K_d = 0 and
  K_p > mgl it oscillates about upright forever, exactly as the algebra says.
- **Page 8** tunes a notch onto an 18 Hz resonance, and then has a **resonance
  drift** slider. Move the resonance 15% and the gain margin you just bought
  disappears — which is the argument against notches, run rather than asserted.
- **Page 10** feeds the same noisy, quantised encoder signal to a finite
  difference and to an observer. Sweep the observer bandwidth from 10 to 400 and
  you watch it trade model-trust for sensor-trust; that trade *is* the Kalman
  filter. Its second widget recovers an unmeasured external torque from position
  alone.
- **Page 11** draws the pendulum phase plane with the separatrix marked, so the
  basin of attraction is a visible boundary rather than a caveat. Its stiction
  widget shows both failures: K_i = 0 gives a permanent dead zone, K_i > 0 gives
  a limit cycle no gain will remove.
- **Page 12** runs plain PD, gravity compensation, computed torque, sliding mode
  and gain scheduling against the *same* wrong model. Computed torque is exact
  at 0% model error and degrades in proportion; sliding mode barely moves, and
  charges you chatter for it. The last widget inverts a pendulum with 35% of the
  torque needed to lift it, by shaping energy instead of commanding through it.
- **Pages 13–16** sweep effective inertia against interaction frequency ω. The
  whole SEA argument is one plot: `J_eff → J_m + J_L` when you push slowly and
  `→ J_L` at impact, so the rotor is *mechanically hidden* during exactly the
  events that would hurt someone. The PEA plot goes **negative** at low ω, which
  is gravity compensation drawn as a curve.
- **Page 17** turns the gear ratio and shows `J_m · N²` on a log axis next to what
  a merely-linear penalty would look like. At 100:1 the human feels the rotor
  10,000× heavier than it is.
- **Pages 19–23** run the same 6 N·m human push through four different
  controllers on the same joint, so the trade is visible rather than asserted.
  Page 23's **stiction slider** demonstrates the bypass: crank gearbox friction
  right up and the admittance response barely changes, because the force sensor
  sits *outside* the transmission.
- **Page 25** is the sharpest one. Two impedance controllers with the same
  feedforward torque but very different stiffness produce **bit-identical** torque
  under nominal kinematics — drag the perturbation slider off zero and they
  separate immediately. That is Property 3 of Best/Rouse/Gregg, and its
  consequence is that *tuning K and B by watching nominal walking is
  uninformative*, because those parameters have no effect there.
- **Page 28** lets you raise the gear ratio and drop transmission efficiency, and
  plots what the controller *believes* the joint torque is against what the joint
  actually delivers. The widening gap is a robot losing its sense of touch.
- **Page 31** runs one gait cycle of an ankle plantarflexor with the reflex loop
  closed. Raise `k_f` and the push-off peak grows out of an unchanging EMG
  command. Then **switch the phase gate off** and watch the same gain become a
  runaway — which is the point: positive force feedback is safe because it is
  phase-gated and time-limited, not because the loop gain is small.

### The through-line

Five sentences carry the whole first half:

1. **Your loop rate is not your bandwidth.** 1 kHz sampling → 500 Hz Nyquist →
   ~50–100 Hz of usable control authority, and that only if delay does not cap
   you lower. Order of who wins, worst first: mechanics → delay → sample rate →
   CPU speed. People optimise that list backwards.
2. **Sensing bandwidth ≠ actuation bandwidth.** An SEA spring is an excellent,
   fast torque sensor *and* a hard limit on how fast you can change joint torque.
   You can know instantly and still be unable to act.
3. **Effective inertia is a function of frequency, not a constant.** That single
   fact is what separates DD, SEA and PEA, and it is why "how heavy is the robot"
   is not a well-posed question until you say how fast you are pushing it.
4. **Proprioception is not about what variables you know; it is about where the
   information comes from.** External forces must propagate back to the actuator.
   A 100:1 harmonic drive breaks that, and no sampling rate repairs it.
5. **Position, impedance and torque control are one controller with one knob.**
   `‖Z‖ = |K| + |B|` slides you from prioritising nominal torques to prioritising
   nominal positions. Almost every published "impedance controller" is somewhere
   in the middle of that line.

## Part II — Reinforcement Learning (pages 36–64)

The order is deliberately **concrete before abstract**. You walk the lake by
hand before anything is given a symbol, and no page shows a number whose origin
has not already been built up.

| # | Page | Notes page |
|---|------|-----------|
| | **Start Here** — the environment, then the vocabulary | |
| 36 | What is Reinforcement Learning? *(you play it, by hand)* | p.1, p.6 |
| 37 | The Frozen Lake *(the board and its geometry)* | p.1 |
| 38 | Stochastic Transitions *(the slippery ice, with real probabilities)* | p.1 |
| 39 | Rewards *(what the lake pays you; sparse vs shaped)* | p.1, p.6 §2.2.5 |
| 40 | Return & the Discount Factor *(a list of rewards → one number)* | p.1, p.6 |
| 41 | Policies *(the thing we are searching for)* | p.1, p.6 |
| 42 | The Markov Decision Process *(all five pieces, formally named)* | p.1 |
| | **Value Functions** — how good is a square? | |
| 43 | V(s) — State Value | p.1 §2.6.2 |
| 44 | Q(s,a) — Action Value | p.1 §2.6.3 |
| 45 | V vs Q — the Difference | p.1, p.7 |
| 46 | The Bellman Equations *(all four at once — the map)* | p.1, p.5 |
| 47 | Bellman ① V<sup>π</sup> *(expectation — drag π(a\|s) and watch V move)* | p.1, p.5 |
| 48 | Bellman ② Q<sup>π</sup> *(the π-average, delayed one step)* | p.1, p.5 |
| 49 | Bellman ③ V\* *(optimality — swap max for min and see)* | p.1, p.5 |
| 50 | Bellman ④ Q\* *(the max, delayed one step → Q-learning)* | p.1, p.5 |
| | **Dynamic Programming** — solve it, knowing the ice | |
| 51 | Policy Evaluation | p.4, p.6 |
| 52 | Policy Improvement | p.4, p.6 |
| 53 | Policy Iteration | p.3, p.4 |
| 54 | Value Iteration | p.3, p.4 |
| 55 | Policy vs Value Iteration | p.3, p.4 |
| | **Monte Carlo** — learn it, *not* knowing the ice | |
| 56 | Monte Carlo = Averaging | p.5 |
| 57 | MC Prediction (FVMC/EVMC) | p.5 §4.2–4.3 |
| 58 | MC Control (GPI) | p.5 §4.4 |
| | **Beyond** | |
| 59 | Exploration vs Exploitation | p.1 §2.5 |
| 60 | Model-Based vs Model-Free | p.4, p.5 |
| 61 | Hyperparameters | p.6 §2.6 |
| 62 | What "Convergence" Means | p.11 |
| 63 | Code Lab | — |
| 64 | Adam, Backprop & BatchNorm | p.8 |

Pages 47–50 exist because page 46 is a summary, and a summary is the wrong place
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

### Control

| symbol | meaning |
|--------|---------|
| `J_m` | motor (rotor) inertia |
| `J_L` | limb / load inertia |
| `k` | spring stiffness |
| `ω` | frequency of the interaction — a property of what is happening, not of the robot |
| `K, B` | virtual stiffness and damping of an impedance controller |
| `τ_ff` | feedforward torque — what the controller outputs while tracking perfectly |
| `θ_d` | desired trajectory — where you actually want the joint |
| `θ_eq` | equilibrium angle — a *control input*, generally **not** where you want the joint |
| `‖Z‖` | impedance magnitude, `\|K\| + \|B\|` |

### Reinforcement learning

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
python tests/test_ctrl.py     # all must pass
python tests/test_linear.py   # all must pass
python tests/test_core.py     # all must pass
python tests/smoke_gui.py     # builds all 64 pages, screenshots to _shots/
```

`test_ctrl.py` checks, among other things:

- direct-drive `J_eff` is `J_m + J_L` and is **frequency independent**
- SEA `J_eff → J_m + J_L` as ω→0 and **collapses onto `J_L`** as ω→∞ — the rotor
  really is hidden at impact
- the SEA antiresonance sits exactly at `√(k/J_m)` and blows up approaching it
- bandwidth is `(1/2π)√(k/J_L)`, rises with stiffness, falls with load, and lands
  in the 10–20 Hz band for plausible humanoid numbers
- PEA `J_eff` goes **negative** at low ω and passes through exactly zero at
  `√(k/(J_m+J_L))`
- some angle always exists at which a tuned PEA spring lets the motor supply
  **zero** torque
- reflected inertia is `J_m·N²`, and 100:1 gives exactly 10,000×
- scaling: mass ∝ L³, torque ∝ L², inertia ∝ L⁵, and torque-per-kg **falls** as
  the robot grows
- `θ_eq ↔ τ_ff` round-trips exactly between the two parameterisations
- **Property 3 / Corollary 3.1**: two controllers with the same `τ_ff` but very
  different `K` and `B` produce identical torque under nominal kinematics, and
  diverge off-nominal
- `‖Z‖ = 0` never returns to its target; a stiffer controller deviates less and
  pushes harder — the compliance/accuracy trade, as an assertion
- **the admittance bypass**: 25 N·m of gearbox stiction changes the response by
  <25%, because the force sensor is outside the transmission
- Hill force-length peaks at optimal length and is symmetric; force-velocity is
  1.0 at zero velocity, collapses when shortening fast, and saturates at the 1.8
  eccentric plateau
- closing the force loop amplifies force **without changing the EMG command**,
  and the phase gate is what keeps a high-gain loop bounded
- the **three SEA frequencies are three different numbers**: the antiresonance
  `√(k/J_m)`, the system resonance `√(k(J_m+J_L)/(J_m J_L))` which sits above it
  and where `J_eff = 0`, and the motor-side bandwidth `(1/2π)√(k/J_L)` which is
  none of the above
- spring deflection **vanishes as ω²** at low frequency (it deflects, but barely)
  and exceeds the load's own motion above the antiresonance
- motor→load transmissibility is ≈1 well below `f_n` and rolls off above it
- at impact, **a PEA presents `J_m + J_L` and an SEA presents `J_L`** — the one
  difference that matters, asserted directly
- Nyquist is `f_s/2`, but usable bandwidth is `f_s/15`, and **delay imposes a
  separate ceiling that more sampling cannot buy back**
- 950 Hz sampled at 1 kHz folds to exactly 50 Hz
- the rate-monotonic bound falls monotonically toward `ln 2`
- **10% timing jitter produces ~9% derivative error** — the D term takes the
  damage, and P/I do not
- **windup**: with a blocked joint and a saturated actuator, an unprotected
  integrator grows >2× larger than a clamped one, and that stored area becomes
  real overshoot the moment the joint is released
- an **unfiltered derivative chatters >2× more** than a filtered one under
  encoder noise

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

Covered in detail on page 63 (Code Lab). Summary:

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
