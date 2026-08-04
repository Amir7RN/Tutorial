#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <cmath>
#include <map>
#include <iomanip>
#include <set>

using namespace std;

const int N_EPISODES = 10000;
const double GAMMA = 0.99;
const int MAX_STEPS = 200;

const double EPSILON_START = 1.0;
const double EPSILON_MIN = 0.1;
const double EPSILON_DECAY = 0.9995;

const double ALPHA_START = 0.5;
const double ALPHA_MIN = 0.01;
const double ALPHA_DECAY = 0.9995;

const int GRID_SIZE = 4;
const int N_STATES = GRID_SIZE * GRID_SIZE;
const int N_ACTIONS = 4; // up, down, left, right

const double REWARD_GOAL = 1.0;
const double REWARD_STEP = -0.04;
const double REWARD_HOLE = -1.0;

struct StepResult {
    int next_state;
    double reward;
    bool done;
};

struct Experience {
    int state;
    int action;
    double reward;
};

class FrozenLakeEnv {
    int goal_state = 15;
    set<int> hole_states = {5, 7, 11, 12};
    mt19937 rng;
public:
    FrozenLakeEnv(){
        random_device rd;
        rng.seed(rd());
    }

    pair <int, int> to_coord(int s){
        return {s/GRID_SIZE, s % GRID_SIZE};
    }

    int to_state(int r, int c){
        return r*GRID_SIZE + c;
    }

    StepResult step(int state, int action){
        uniform_real_distribution<> dist(0.0, 1.0);
        double roll = dist(rng);
        int actual_move;

        if (roll < 0.8){
            actual_move = action;
        }else if (roll < 0.9){
            actual_move = (action + 1) % GRID_SIZE;
        }else{
            actual_move = (action + GRID_SIZE - 1) % GRID_SIZE;
        }

        pair<int, int>coords = to_coord(state);
        int row = coords.first;
        int col = coords.second;

        if (actual_move == 0) col = max(0, col - 1);      // Left
        else if (actual_move == 1) row = min(GRID_SIZE - 1, row + 1); // Down
        else if (actual_move == 2) col = min(GRID_SIZE - 1, col + 1); // Right
        else if (actual_move == 3) row = max(0, row - 1);      // Up

        int next_s = to_state(row, col);

        if (next_s == goal_state) return {next_s, REWARD_GOAL, true};
        if (hole_states.count(next_s)) return {next_s, REWARD_HOLE, true};

        return {next_s, REWARD_STEP, false};
    }

    int reset() {return 0;}
};

int select_Action(int state, const vector<vector<double>>& Q, double epsilon, mt19937& rng){
    uniform_int_distribution<> dist(0.0, 1.0);

    if (dist(rng) < epsilon){
        uniform_int_distribution<> action_dist(0.0, N_ACTIONS-1);
        return action_dist(rng);
    }

    int best_a = 0;
    double max_val = -1e9;

    vector<int> ties;
    for (int a = 0 ; a < N_ACTIONS; a++){
        if (Q[state][a] > max_val){
            max_val = Q[state][a];
            ties.clear();
            ties.push_back(a);
        }else if (abs(Q[state][a] - max_val) < 1e-5){
            ties.push_back(a);
        }
    }

    uniform_int_distribution<> tie_dist(0.0, ties.size()-1);
    return ties[tie_dist(rng)];

}

int main(){
    FrozenLakeEnv env;
    mt19937 rng(random_device{}());

    vector<vector<double>> Q(N_STATES, vector<double>(N_ACTIONS, 0.0));

    double epsilon = EPSILON_START;
    double alpha = ALPHA_START;

    cout << "Starting Monte Carlo Training..." << endl;

    for (int episode = 0; episode < N_EPISODES; episode++){
        vector<Experience> trajectory;
        int state = env.reset();
        bool done = false;

        for (int t = 0 ; t < MAX_STEPS; t++){
            int action = select_Action(state, Q, epsilon, rng);
            StepResult res = env.step(state, action);

            trajectory.push_back({state, action, res.reward});

            if (res.done) break;
            state =res.next_state;
        }
        
        double G = 0.0;

        for (int i = trajectory.size()-1 ; i >=0; i--){
            Experience& exp = trajectory[i];
            G = GAMMA * G + exp.reward;

            bool appears_before = false;
            for (int j =0; j <i; j++){
                if(trajectory[j].state == exp.state && trajectory[j].action == exp.action){
                    appears_before = true;
                    break;
                }
            }

            if (!appears_before){
                Q[exp.state][exp.action] += alpha * (G - Q[exp.state][exp.action]);
            }
        }
        if (epsilon > EPSILON_MIN) epsilon *= EPSILON_DECAY;
        if (alpha > ALPHA_MIN) alpha *= ALPHA_DECAY;

        if (episode % 1000 == 0){
            cout << "Episode: " << episode << " | Epsilon: " << epsilon << endl;
        }
    }

    // --- PRINT RESULTS ---
    cout << "\nTraining Complete. Final Policy:\n" << endl;
    
    // Symbols: Left, Down, Right, Up
    string symbols[4] = {"<", "v", ">", "^"};
    cout << "-----------------" << endl;
    for (int r = 0; r < GRID_SIZE; r++) {
        cout << "| ";
        for (int c = 0; c < GRID_SIZE; c++) {
            int s = r * GRID_SIZE + c;
            
            if (s == 15) { cout << "GOAL"; }
            else if (s == 5 || s == 7 || s == 11 || s == 12) { cout << "HOLE"; }
            else {
                // Find best action
                int best_a = 0;
                double max_q = -1e9;
                for(int a=0; a<4; a++) {
                    if(Q[s][a] > max_q) {
                        max_q = Q[s][a];
                        best_a = a;
                    }
                }
                cout << " " << symbols[best_a] << "  ";
            }
            cout << " | ";
        }
        cout << "\n-----------------" << endl;
    }

    return 0;
}