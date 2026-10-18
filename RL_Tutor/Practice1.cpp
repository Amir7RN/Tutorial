#include <vector>
#include <iostream>
#include <unordered_set>
#include <algorithm>

using namespace std;

struct Transition {
    bool done;
    int next_state;
    double probability;
    double reward;
};

struct Chance{
    double prob;
    int move;
};

using actionCell = vector<Transition>;
using stateCell = vector<actionCell>;
using TransitionTable = vector<stateCell>;

TransitionTable Environment(){
    int S = 16;
    int A = 4;
    int grid_size = 4;
    TransitionTable P(S, stateCell(A, actionCell()));

    int goal = 15;
    unordered_set holes = {5,7,11,12};

    auto next_state = [grid_size](int state, int action){
        int row = state / grid_size;
        int col = state % grid_size;
        // up 0, right 1, down 2, left 3
        switch (action){
            case 0:
                row = max(row-1,0);
                break;
            case 1:
                col = min(col + 1, 3);
                break;
            case 2:
                row = min(3, row +1);
                break;
            case 3:
                col = max(0, col -1);
                break;
        }

        return row * grid_size + col;
    };

    auto is_hole = [&holes](int state){
        return holes.count(state);
    };

    for (int s = 0; s < S; ++s){
        for (int a = 0; a < A; ++a){

            if (s == goal || is_hole(s)){
                P[s][a].push_back({true,s,1,0});
                continue;
            }


            vector<Chance> chances = {
                {0.1, (a + 1) % grid_size },
                {0.8, a},
                {0.1 , (a+3) % grid_size}
            };

            for (const auto& ch : chances){
                int ns = next_state(s, ch.move);
                double reward = -0.04;
                bool done = false;
                if (ns == goal) {
                    reward = 1;
                    done = true;
                }
                if (is_hole(ns)) {
                    reward = -1;
                    done = true;
                }
                P[s][a].push_back({done, ns, ch.prob, reward});
            }

        }
    }
    return P;
}

using policy = vector<int>;

policy value_iteration(const TransitionTable& env, double gamma = 0.99, double epsilon = 0.001){
    int S = env.size();
    int A = env[0].size();

    vector<double> V(S , 0), V_prev(S , 0);

    policy pi(S,0);

    while(true){

        double max_diff = 0.0;
        for (int s =0; s < S; ++s){
            double Q_best = -1e9;
            int best_action  = 0;
            for (int a = 0; a < A; ++a){

                double q = 0;

                auto transition = env[s][a];
                for (const auto& tr : transition){
                    q += tr.probability  * (tr.reward + gamma * V_prev[tr.next_state]); 
                }

                if (q > Q_best){
                    Q_best = q;
                    best_action = a;
                }
            }

            pi[s] = best_action;
            V[s] = Q_best;
            max_diff = max(max_diff, abs(V[s] - V_prev[s]));
  
        }
        
        V_prev = V;
        if (max_diff < epsilon){
            break;
        }
    }

    return pi;
}

vector <double> policy_evaluation(const TransitionTable& env, double gamma = 0.99, double epsilon = 0.001, policy& pi){
    int S = env.size();
    int A = env[0].size();
    
    vector<double> V(S, 0.0), V_prev(S, 0.0);

    while(true){
        double max_diff = 0.0;
        for (int s =0; s < S; s++){
            int action = pi[s];
            auto transition = env[s][action];
            double q = 0.0;
            for (const auto& tr : transition){
                    q += tr.probability  * (tr.reward + gamma * V_prev[tr.next_state]); 
                }

            max_diff = max(max_diff, abs(q- V_prev[s]));
            V[s] = q;

        }
        V_prev = V;
        if (max_diff< epsilon) break;

    }

    return V;
}

bool policy_improvement(const TransitionTable& env, vector<double>& V, policy& pi, double gamma = 0.99){

    int S = env.size();
    int A = env[0].size();
    bool policy_stable = true;
    
    for (int s = 0; s < S; s++){
        int old_action = pi[s];
        double best_q = -1e9;
        int best_action = 0;
        for (int a = 0 ; a < A; a++){

            auto transition = env[s][a];
            double q = 0.0;
            for (const auto& tr : transition){
                    q += tr.probability  * (tr.reward + gamma * V[tr.next_state]); 
            }
            
            if (q > best_q){
                best_q = q;
                best_action = a;

            }
        }
        pi[s] = best_action;

        if (old_action != best_action) policy_stable = false;
    }
    return policy_stable;
}

policy policy_iteration(const TransitionTable& env, double gamma = 0.99, double epsilon = 0.001){
    int S = env.size();

    policy pi(S,0);

    while(true){

        vector<double> V = policy_evaluation(env, gamma, epsilon, pi);
        bool stable = policy_improvement(env, V, pi, gamma);

        if (stable) break;
    }
    return pi;
}


int main(){
    TransitionTable env = Environment();
    policy pi_vi = value_iteration(env);
    policy pi_pi = policy_iteration(env);

    cout << "Value Iteration and Policy Iteration successfully executed!" << endl;



    return 0;
}