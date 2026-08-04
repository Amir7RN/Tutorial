#include "algorithm"
#include "vector"
#include "iostream"

using namespace std;

struct Transition {
    double reward;
    double prob;
    int next_state;
    bool done;
};

using Model = vector<vector<vector<Transition>>>;
using Policy = vector<int>;
Model build_env(){
    int S = 16;
    int A = 4; // down 0, left 1, up 2, right 3
    Model P(S, vector<vector<Transition>>(A));

    auto get_new_state = [&](int s, int move){
        int row = s / 4;
        int col = s % 4;

        if (move == 0) row = min(3, row+1);
        else if (move == 1) col = max(col-1, 0);
        else if (move == 2) row = max(0, row-1);
        else if (move == 3) col = min(3, col+1);

        return row*4 + col;
    };

    int goal = 15;
    vector<int> holes = {5,7,11,12};

    auto is_hole = [&](int s){
        for (auto& h : holes){
            if (h == s){
                return true;
            }
        }
        return false;
    };

    for (int s = 0; s < S; s++){
        for (int a = 0; a < A; a++){
            if (s == goal || is_hole(s)){
                P[s][a].push_back({0.0, 1.0, s, true});
                continue;
            }

            struct Chance {double p; int move;};
            vector<Chance> chances = {
                {0.8, a},
                {0.1, (a+1) %4},
                {0.1, (a+3) %4}
            };
            for (const auto& ch : chances){
                double r = -0.04;
                bool done = false;
                int next = get_new_state(s, ch.move);
                if (next == goal){
                    r = 1.0;
                    done = true;
                }else if (is_hole(next)){
                    r = -1.0;
                    done = true;
                }
                P[s][a].push_back({r, ch.p, next, done});
            }
        }
    }
    return P;
}

Policy value_iteration(Model& P, double gamma = 0.99, double theta = 1e-100){
    int S = P.size();
    vector<double> V(S, 0.0);
    vector<double> V_prev(S, 0.0);
    int A = P[0].size();
    Policy pi(S);
    while(true){
        double max_diff = 0.0;
        for (int s = 0; s< S; s++){
            double best_value_s = -1e9;

            for (int a = 0; a < A; a++){
                auto transition = P[s][a];
                double q_value = 0.0;
                // Q(s,a) = P(s_next |s,a) * (reward + gamma * (V[s_next]))
                for (const auto& tr : transition){
                    if (tr.done){
                        q_value += tr.prob * (tr.reward);
                    }else{
                        q_value += tr.prob * (tr.reward + gamma * V_prev[tr.next_state]);
                    }
                }
                if (q_value > best_value_s){
                    best_value_s = q_value;
                }
            }
            V[s] = best_value_s;
            max_diff = max(max_diff, abs(V[s]-V_prev[s]));
        }
        V_prev = V;
        if (max_diff < theta){
            break;
        }
    }

    for (int s = 0; s< S; s++){
        int best_action = -1;
        double best_q = -1e9;
        for (int a = 0; a < A; a++){
                auto transition = P[s][a];
                double q_value = 0.0;
                // Q(s,a) = P(s_next |s,a) * (reward + gamma * (V[s_next]))
                for (const auto& tr : transition){
                    if (tr.done){
                        q_value += tr.prob * (tr.reward);
                    }else{
                        q_value += tr.prob * (tr.reward + gamma * V_prev[tr.next_state]);
                    }
                }
                if (q_value > best_q){
                    best_q = q_value;
                    best_action = a;
                }
            }
            pi[s] = best_action;
        }
        return pi;
}