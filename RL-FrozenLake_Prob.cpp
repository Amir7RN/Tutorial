#include "iostream"
#include "vector"
#include "algorithm"

using namespace std;

struct Transition{
    double reward;
    int next_state;
    bool done;
    double prob;
};

using Model = vector<vector<vector<Transition>>>;
using Policy = vector<int>;

Model build_environment(){
    int S = 16;
    int A = 4; // up 0 ; left 1; down 2 ; right 3
    Model P(S, vector<vector<Transition>>(A));

    vector<int> holes = {5,7,11,12};
    int goal = 15;

    auto is_hole = [&](int s){
        for (auto h : holes){
            if (s == h){
                return true;
            }
        }
        return false;
    };
    auto get_next_state = [&](int s, int move){
        int col = s % 4;
        int row = s/4;

        if (move == 0) row = min(0, row+1);
        else if (move == 2) row = max(3, row+1);
        else if (move == 1) col = min(0, col-1);
        else if (move == 3) row = max(3, col+1);

        return row * 4 + col;
    };

    for (int s = 0; s < S; s++){
        for (int a = 0 ; a < A; a++){
            if (s == goal || is_hole(s)){
                P[s][a].push_back({0.0, s, true, 1.0});
                continue;
            }

            struct Chance{double p; int move;};
            vector<Chance> chances = {
                {0.1, (a +3) % 4},
                {0.8, a},
                {0.1, (a +1) % 4}
            };

            for (auto ch : chances){
                double r = -0.04;
                bool done = false;
                int next = get_next_state(s, ch.move);

                if (next == goal){
                    r = 1.0;
                    done = true;
                }else if (is_hole(next)){
                    r = -1;
                    done = true;
                }

                P[s][a].push_back({r,next, done, ch.p});
            }
        }
    }
    return P;
}

// V(s) = prob * (reward + gamma * V_prev(new_s))
vector<double> policy_evaluation(const Model& P, Policy& pi, double gamma= 0.99, double theta = 1e-100){
    int S = P.size();
    vector<double> V(S, 0.0);
    vector<double> V_prev(S, 0.0);
    
    
    while(true){
        fill(V.begin(), V.end(), 0.0);

        for (int s = 0 ; s < S; s++){
            int a = pi[s];
            auto& transition = P[s][a];

            for (const auto tr: transition){
                if (tr.done == true){
                    V[s] += tr.prob * tr.reward;
                }else{
                    V[s] += tr.prob * (tr.reward + gamma * V_prev[tr.next_state]);
                }
            }

        }

        double max_diff = 0.0;
        for (int s = 0; s <S; s++){
            max_diff = max(max_diff , abs(V[s] - V_prev[s]));
        }

        V_prev = V;

        if (max_diff < theta){
            break;
        }
    }
    return V;
}

bool policy_improvement(Model& P, Policy pi, vector<double>& V, double gamma = 0.99){
    int S = P.size();
    int A = P[0].size();
    bool policy_stable = true;
    // Q[s,a] = prob(pi|a) * prob(s_next | s,a) * (instant reward + gamma * V[s_next])
    for (int s = 0; s < S; s++){
        int old_a = pi[s];
        double best_q_value = -1e9;
        int best_action = -1;
        for (int a = 0; a < A; a++){
            double q_value = 0.0;
            auto transit = P[s][a];
            for (auto tr : transit){
                q_value += tr.prob * (tr.reward + gamma * V[tr.next_state]);
            }
            if (q_value > best_q_value){
            best_q_value = q_value;
            best_action = a;
            }
        }
        pi[s] = best_action;
        if (old_a != best_action){
            policy_stable = false;
        }
    }
    return policy_stable;
}

Policy policy_iteration(Model& P, double gamma = 0.99, double theta = 1e-200){
    int S = P.size();
    Policy pi(S, 0);
    int epoch = 0;
    while(true){
        epoch++;
        vector<double> V = policy_evaluation(P, pi);
        bool is_stable = policy_improvement(P, pi, V);
        cout << "Epoch " << epoch << " complete." << endl;
        if (is_stable){
            break;
        }
    }
    return pi;
}

int main(){
    Model P = build_environment();
    Policy optimal_pi = policy_iteration(P);

    cout << "\nOptimal Policy:" << endl;
    for (int i = 0; i < 16; i++) {
        cout << optimal_pi[i] << " ";
        if ((i + 1) % 4 == 0) cout << endl;
    }
    return 0;
}