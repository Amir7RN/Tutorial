#include <iostream>
#include <vector>
#include <array>
#include <cstdint>
#include <set>
#include <random>
#include <algorithm>

using namespace std;

struct Experience{
    int state;
    int action;
    double reward;
    int next_state;
    bool done;
};

struct StepResult{
    int next_state;
    double reward;
    bool done;
};

class Environment{
private:

    static constexpr int GOAL = 15;
    const set<int> HOLES{5,7,12,13} ;
    static constexpr double R_HOLES = -1.0;
    static constexpr double R_GOAL = 1.0;
    static constexpr double R_STEP = -0.04;
    mt19937 rng;
    uniform_real_distribution<double> uniform01{0.0,1.0};

public:
    static constexpr int GRID_SIZE = 4;
    static constexpr int N_State = GRID_SIZE * GRID_SIZE;
    static constexpr int N_Action = GRID_SIZE;

    Environment() : rng(random_device{}()) {};

    int reset() {return 0;}

    int slip(int action){
        double roll = uniform01(rng);

        if(roll < 0.8) return action;
        if(roll < 0.9) return (action + 1) % N_Action;
        else { return (action + 3) %N_Action;}

    }

    StepResult step(int state, int action){
        int actual = slip(action);

        int row = state / 4;
        int col = state % 4;

        switch(actual){
            case 0: row = max(0, row - 1); break;             // up
            case 1: row = min(GRID_SIZE - 1, row + 1); break;  // down
            case 2: col = max(0, col - 1); break;              // left
            case 3: col = min(GRID_SIZE - 1, col + 1); break;  // right 
        }
        int next_state = row * 4 + col;

        if (next_state == GOAL) return {next_state, actual, true};
        if (HOLES.count(next_state)) return {next_state, actual, true};
        return {next_state, actual, false};
    }
};


class ReplayBuffer {
public:

    ReplayBuffer(size_t capacity) : capacity(capacity), rng(random_device{}()) {};

    void add(const Experience& e){
        if(buffer.size() < capacity) buffer.push_back(e);
        else buffer[pos] = e;
        pos = (pos + 1) % capacity;
    }

    vector<Experience> Sample (size_t batch_size){
        vector<Experience> batch;
        batch.reserve(batch_size);
        uniform_int_distribution<size_t> pick(0,buffer.size() - 1);
        for (size_t i = 0; i < batch_size; ++i){
            batch.push_back(buffer[pick(rng)]);
        }
        return batch;
    }

    size_t size() const {return buffer.size();}


private:
    vector<Experience> buffer;
    mt19937 rng;
    size_t capacity;
    size_t pos = 0;
};

using QTable = vector<array<double, Environment::N_Action>>;


int select_Action(int state, const QTable& Q, double epsilon, mt19937& rng){
    uniform_real_distribution<double> uniform02(0.0,1.0);
    if (uniform02(rng) < epsilon){
        uniform_int_distribution<int> random_action(0,Environment::N_Action-1);
        return random_action(rng);
    }
    int best = 0;
    for (int a = 1 ; a < Environment::N_Action; a++){
        if(Q[state][a] > Q[state][best]) best = a;
    }

    return best;
}

int main(){
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
    QTable Q(Environment::N_State, {0.0,0.0,0.0,0.0});
    
    mt19937 rng(random_device{}());
    double epsilon = EPSILON_START;

    for (int ep = 0; ep < N_EPISODES; ep++){
        int state = env.reset();

        for (int t = 0; t < N_STEPS; t++){
            int action = select_Action(state, Q, epsilon,rng);
            StepResult res = env.step(state, action);

            buffer.add({state,action, res.reward, res.done, res.next_state});

            if (buffer.size() >= BATCH_SIZE){
                auto batch = buffer.Sample(BATCH_SIZE);
                for (const auto& e : batch){
                    double best_next = *max_element(Q[e.next_state].begin, Q[e.next_state].end());
                    double target = e.reward + (e.done ? 0.0 : GAMMA * best_next);
                    Q[e.state][e.action] += ALPHA * (target - Q[e.state][e.action]);
                }
            }
            state = res.next_state;
            if (res.done) break;
        }
        epsilon = max(EPSILON_MIN, EPSILON_DECAY * epsilon);
    }

    vector<int> policy(Environment::N_STATES);
    for (int s = 0; s < Environment::N_STATES; ++s) {
        int best = 0;
        for (int a = 1; a < Environment::N_ACTIONS; ++a)
            if (Q[s][a] > Q[s][best]) best = a;
        policy[s] = best;
    }

}