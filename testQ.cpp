#include <cmath>
#include <vector>
#include <array>
#include <set>
#include <random>
#include <iostream>
#include <algorithm>

using namespace std;

// ============================================================
// ENVIRONMENT
// Same 4x4 FrozenLake as your value/policy-iteration file.
// Action encoding kept identical to that file: 0=up,1=down,2=left,3=right
// ============================================================

struct StepResult {
    int    next_state;
    double reward;
    bool   done;
};

class Environment {
public:
    static constexpr int GRID_SIZE = 4;
    static constexpr int N_STATES  = GRID_SIZE * GRID_SIZE;
    static constexpr int N_ACTIONS = 4;

    Environment() : rng(random_device{}()) {}

    int reset() { return 0; }

    // 80% chance you actually move the way you intended.
    // 10% chance you slip to the action "one step clockwise" of it.
    // 10% chance you slip to the action "one step counter-clockwise" of it.
    // This is the SAME transition model your Environment() table builder used
    // (Landing = {a+1, a, a+3} with probs 0.1, 0.8, 0.1) -- just sampled
    // instead of enumerated, because the agent no longer gets to see the
    // full probability table.
    int slip(int action) {
        double roll = uniform01(rng);
        if (roll < 0.8)       return action;
        if (roll < 0.9)       return (action + 1) % N_ACTIONS;
        return (action + 3) % N_ACTIONS;
    }

    StepResult step(int state, int action) {
        int actual = slip(action);

        int row = state / GRID_SIZE;
        int col = state % GRID_SIZE;

        switch (actual) {
            case 0: row = max(0, row - 1); break;             // up
            case 1: row = min(GRID_SIZE - 1, row + 1); break;  // down
            case 2: col = max(0, col - 1); break;              // left
            case 3: col = min(GRID_SIZE - 1, col + 1); break;  // right
        }

        int next_state = row * GRID_SIZE + col;

        if (next_state == GOAL)      return {next_state, R_GOAL, true};
        if (HOLES.count(next_state)) return {next_state, R_HOLE, true};
        return {next_state, R_STEP, false};
    }

private:
    static constexpr double R_GOAL = 1.0;
    static constexpr double R_HOLE = -1.0;
    static constexpr double R_STEP = -0.04;
    static constexpr int    GOAL   = 15;
    const set<int> HOLES = {5, 7, 12, 13};   // same holes as your table-based file

    mt19937 rng;
    uniform_real_distribution<double> uniform01{0.0, 1.0};
};

// ============================================================
// EXPERIENCE + REPLAY BUFFER
// (state, action, reward, next_state, done) -- the standard tuple
// you already know from DDPG. Same idea here, just feeding a Q-table
// instead of a neural net.
// ============================================================

struct Experience {
    int    state;
    int    action;
    double reward;
    int    next_state;
    bool   done;
};

class ReplayBuffer {
public:
    explicit ReplayBuffer(size_t capacity) : capacity(capacity), rng(random_device{}()) {}

    void add(const Experience& e) {
        if (buffer.size() < capacity) buffer.push_back(e);
        else                          buffer[pos] = e;
        pos = (pos + 1) % capacity;
    }

    vector<Experience> sample(size_t batch_size) {
        vector<Experience> batch;
        batch.reserve(batch_size);
        uniform_int_distribution<size_t> pick(0, buffer.size() - 1);
        for (size_t i = 0; i < batch_size; ++i) batch.push_back(buffer[pick(rng)]);
        return batch;
    }

    size_t size() const { return buffer.size(); }

private:
    vector<Experience> buffer;
    size_t capacity;
    size_t pos = 0;
    mt19937 rng;
};

// ============================================================
// EPSILON-GREEDY ACTION SELECTION
// ============================================================

using QTable = vector<array<double, Environment::N_ACTIONS>>;

int select_action(int state, const QTable& Q, double epsilon, mt19937& rng) {
    uniform_real_distribution<double> coin(0.0, 1.0);
    if (coin(rng) < epsilon) {
        uniform_int_distribution<int> random_action(0, Environment::N_ACTIONS - 1);
        return random_action(rng);
    }
    int best = 0;
    for (int a = 1; a < Environment::N_ACTIONS; ++a)
        if (Q[state][a] > Q[state][best]) best = a;
    return best;
}

// ============================================================
// MAIN Q-LEARNING LOOP
//
// The update below IS the model-free, sample-based version of the
// Bellman OPTIMALITY equation for Q, exactly the thing you and I
// worked through conceptually:
//
//   Q(s,a)  <-  Q(s,a)  +  alpha * [ r + gamma * max_a' Q(s',a')  -  Q(s,a) ]
//
// Compare to Value_Iteration()'s line:
//   Q += tr.Probability * (tr.Reward + gamma * V_prev[tr.next_state]);
//
// Value_Iteration needed the FULL probability table (tr.Probability,
// looped over every possible landing spot) because it has the model.
// Here there is no probability loop at all -- one real experience
// gives you one (s,a,r,s') sample, and repeating this over many
// episodes lets the average of many samples stand in for the
// probability-weighted sum the model-based version computed exactly.
// ============================================================

int main() {
    constexpr int    N_EPISODES     = 10000;
    constexpr int    N_STEPS        = 200;
    constexpr double GAMMA          = 0.99;
    constexpr double ALPHA          = 0.1;     // learning rate
    constexpr double EPSILON_START  = 1.0;
    constexpr double EPSILON_MIN    = 0.1;
    constexpr double EPSILON_DECAY  = 0.9995;
    constexpr size_t BUFFER_CAPACITY = 5000;
    constexpr size_t BATCH_SIZE      = 1;      // 1 = plain online Q-learning.
                                                // Raise this later once you
                                                // want to see batched updates.

    Environment env;
    ReplayBuffer buffer(BUFFER_CAPACITY);
    QTable Q(Environment::N_STATES, {0.0, 0.0, 0.0, 0.0});

    mt19937 rng(random_device{}());
    double epsilon = EPSILON_START;

    for (int ep = 0; ep < N_EPISODES; ++ep) {
        int state = env.reset();

        for (int t = 0; t < N_STEPS; ++t) {
            int action = select_action(state, Q, epsilon, rng);
            StepResult res = env.step(state, action);

            buffer.add({state, action, res.reward, res.next_state, res.done});

            if (buffer.size() >= BATCH_SIZE) {
                auto batch = buffer.sample(BATCH_SIZE);
                for (const auto& e : batch) {
                    double best_next = *max_element(Q[e.next_state].begin(), Q[e.next_state].end());
                    double target    = e.reward + (e.done ? 0.0 : GAMMA * best_next);
                    Q[e.state][e.action] += ALPHA * (target - Q[e.state][e.action]);
                }
            }

            state = res.next_state;
            if (res.done) break;
        }

        epsilon = max(EPSILON_MIN, epsilon * EPSILON_DECAY);
    }

    // Extract the greedy policy: argmax_a Q(s,a) at every state.
    // This is the exact same argmax step policy_improvement() did --
    // just reading it off a learned Q-table instead of a computed one.
    vector<int> policy(Environment::N_STATES);
    for (int s = 0; s < Environment::N_STATES; ++s) {
        int best = 0;
        for (int a = 1; a < Environment::N_ACTIONS; ++a)
            if (Q[s][a] > Q[s][best]) best = a;
        policy[s] = best;
    }

    cout << "Learned policy (0=up,1=down,2=left,3=right):\n";
    for (int s = 0; s < Environment::N_STATES; ++s) {
        cout << policy[s] << " ";
        if (s % Environment::GRID_SIZE == Environment::GRID_SIZE - 1) cout << "\n";
    }

    return 0;
}