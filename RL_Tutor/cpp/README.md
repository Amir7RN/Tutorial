# C++ code cards

Every GUI code card and Code Lab implementation uses C++17. These are teaching
counterparts; the GUI and its live simulations still run in Python. A C++ compiler
is only needed to run these examples separately, not to launch the GUI.

Build and run the console example from the project directory:

```sh
g++ -std=c++17 -O2 cpp/demo.cpp -o cpp/demo.exe
./cpp/demo.exe
```

The headers use only the C++ standard library:

- `tutor.hpp`: control laws, FrozenLake, dynamic programming and Monte Carlo.
- `learning.hpp`: bandits, dense layers, Adam, replay, DDPG and environments.
- `examples.hpp`: short examples used in explanatory cards.

Include `cpp/examples.hpp` to use everything in the `tutor` namespace. Method
cards show an excerpt; their class members and shared helper types are in these
headers. The pre-existing shared-memory deployment excerpt still needs the
robot application's `TransferData` type and platform integration.

The examples retain the teaching calculations but use C++ containers and return
structs/maps where appropriate. Some GUI-only histories and logging are omitted.
Random samples are not identical across languages even with the same seed.
`train_gait` accepts an existing agent and environment so the setup is explicit.
Editing these files changes the displayed examples, not the Python simulations.

`BEGIN`/`END` comments identify the regions loaded into the GUI. Keep their keys
stable when editing. Run `python -m unittest discover -s tests -p test_cpp_examples.py`
to check card coverage and compile/run the numerical checks (requires g++).
