# Tutorial

Robotics study repository: an interactive **Control & RL Tutor** desktop app, plus
the C++ algorithm implementations and source PDFs it was built from.

The main thing here is **[`RL_Tutor/`](RL_Tutor/)** — a 53-page interactive
workbench covering real-time control, actuator dynamics, impedance control,
proprioception and reinforcement learning. Every algorithm is live and steppable, every formula is
rendered, and every code panel is pulled from the real source at runtime so
nothing on screen can drift out of sync with what actually ran.

---

## Run it on another machine

**You need [Python 3.10 or newer](https://www.python.org/downloads/) and
[Git](https://git-scm.com/downloads). Nothing else.**

On Windows, when the Python installer asks, **tick "Add python.exe to PATH"**.

### 1. Clone

```bash
git clone https://github.com/Amir7RN/Tutorial.git
cd Tutorial/RL_Tutor
```

### 2. Launch

**Windows** — double-click `run.bat` in `RL_Tutor/`.
Or from a terminal:

```powershell
.\run.bat
```

**macOS / Linux**

```bash
chmod +x run.sh
./run.sh
```

That's it. The first launch creates a private virtual environment in
`RL_Tutor/.venv/` and installs PySide6, numpy and matplotlib **into it** — your
system Python is never touched, so this cannot disturb anything you already have.
It takes a minute or two and needs internet.

Every launch after that is instant and works offline.

### If you'd rather manage the environment yourself

```bash
cd Tutorial/RL_Tutor
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
python -m app.main
```

### Using it

`Ctrl+←` / `Ctrl+→` move between pages. The sidebar jumps anywhere directly.

Start at page 1 and read in order — the tutor is written concrete-before-abstract,
and no page shows a number whose origin has not already been built up.

### Verify the install

```bash
python tests/test_ctrl.py     # physics: actuators, impedance, muscle model
python tests/test_core.py     # RL: Bellman, DP, Monte Carlo
python tests/smoke_gui.py     # builds all 53 pages headless, screenshots to _shots/
```

All three should exit clean.

### Troubleshooting

| Problem | Fix |
|---|---|
| `'git' is not recognized` | Install Git, reopen the terminal |
| `Python 3.10 or newer was not found` | Install Python and tick **Add python.exe to PATH**, then reopen the terminal. Or `winget install Python.Python.3.12` |
| `run.bat` flashes and closes | Run it from a terminal instead so you can read the error |
| Dependency install fails | Check your internet connection, then delete `RL_Tutor/.venv/` and run again |
| Window opens but text is blank boxes | A font problem — the app asks for Segoe UI / Inter; install one, or edit the font family in `app/theme.py` |

To uninstall completely: delete the folder.

### Sending it to somebody without Git

Run `RL_Tutor/pack.ps1` (right-click → *Run with PowerShell*). It writes a clean
`RL_Tutor.zip` of about **490 KB**, leaving out `.venv/` and caches. The recipient
unzips it anywhere and double-clicks `run.bat`. They need only Python 3.10+.

---

## What's in the tutor

**Part I — Control & Dynamics (pages 1–24)**

| Pages | Section | Covers |
|---|---|---|
| 1 | Real-Time | Hard vs firm vs soft real-time; sampling rate vs Nyquist vs actual bandwidth; aliasing; transport delay; FreeRTOS scheduling, priority inversion and the rate-monotonic bound |
| 2–6 | Actuators | Effective inertia derived for direct drive, series elastic and parallel elastic; the three compared on torque, speed, inertia and bandwidth; the N² reflected-inertia square law and three ways out of it |
| 7–14 | Control Paradigms | The goal of control from scratch, then position, PID-in-practice, torque/current, impedance and admittance — when, why, and what each costs — ending with the impedance spectrum that unifies them |
| 15–17 | Robot Design | Actuator choice per robot type, the square-cube law, 1X Neo as a case study |
| 18–20 | Proprioception | Biological sensing, mechanical transparency as the prerequisite, software-defined active compliance |
| 21–22 | Force Feedback | What positive force feedback actually is, the Hill-model maths, and the test for whether you have really built one |
| 23–24 | Bio → Robot | Translating human actuation, sensing, skin and bone into design requirements |

**Part II — Reinforcement Learning (pages 25–53)** — Frozen Lake end to end:
the MDP, value functions, all four Bellman equations one page each, dynamic
programming, Monte Carlo, and the surrounding ideas.

Full page-by-page table, the maths, the conventions and what the tests check:
**[`RL_Tutor/README.md`](RL_Tutor/README.md)**.

---

## Everything else in this repo

### C++ algorithm implementations

| File | What it is |
|---|---|
| `Astar.cpp`, `AStarModified.cpp`, `WeightedAtar.cpp` | A* search and variants |
| `Dijkstra.cpp`, `Greedy_bfs.cpp` | Shortest path and greedy best-first |
| `RRT.cpp`, `MotionPlanning.cpp` | Sampling-based motion planning |
| `FSM.cpp` | Finite state machine |
| `LSTM_Cpp.cpp`, `GRU.cpp`, `GP_Model.cpp` | Recurrent nets and a Gaussian process, from scratch |
| `RL-FrozenLake_ValIter.cpp`, `RL-FrozenLake_Prob.cpp`, `RL-FrozenLake_MontoCarlo.cpp` | Frozen Lake in C++ |
| `LSTM_PRedict.py` | LSTM prediction in Python |

The three Frozen Lake C++ files are dissected on **page 52 (Code Lab)** of the
tutor, which walks through two real bugs in `RL-FrozenLake_Prob.cpp` and one in
`RL-FrozenLake_MontoCarlo.cpp`.

Compile any of them with:

```bash
g++ -O2 -std=c++17 Astar.cpp -o Astar
./Astar
```

### Source material

| File | Used for |
|---|---|
| `Impedance_Material.pdf` | Handwritten notes behind tutor pages 2–24 |
| `ImpedanceControl.pdf` | Best, Rouse & Gregg — the decoupled impedance controller, page 14 |
| `RL.pdf` | Reinforcement learning notes behind pages 25–53 |
| `HumanoidMotionPlanner.pdf` | Motion planning reference |
