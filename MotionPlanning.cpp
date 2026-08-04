#include <iostream>
#include <vector>
#include <queue>
#include <cmath>
#include <algorithm>
#include <random>
#include <unordered_set>

using namespace std;
struct Transition{
        double r;
        double prob;
        int ns;
        bool done;
    };

    using model = vector<vector<vector<Transition>>>;
    using Policy = vector<int>;
    using Point = pair<int, int>;
class MotionPlanning{
private:
    
public:

    MotionPlanning(){};
    model build_environment(){

        int S = 16;
        int A = 4; // up 0, down 1, left 2, right 3
        
        model env(S, vector<vector<Transition>>(A));

        int goal = 15;
        unordered_set<int> holes = {5,7,11,12};

        auto get_next = [&](int s, int move){

            int row = s / 4;
            int col = s % 4;

            if (move == 0) row = min(0,row-1);
            else if (move == 1) row = max(3, row+1);
            else if (move == 2) col = min(0, col-1);
            else if (move == 3) col = max(3, col+1);

            return row * 4 + col;

        };

        for (int s = 0 ; s < S; s++){
            for (int a = 0; a < A; a++){

                if (s == goal || holes.count(s)){
                    env[s][a].push_back({0.0, 1.0, s, true});
                    continue;
                }


                struct Chance{
                    double p;
                    int move;
                };
                vector<Chance> chances = {
                    {0.1, (a+1)%4},
                    {0.8, a},
                    {0.1, (a+3)%4}
                };

                for (auto ch : chances){
                    double r = -0.4;
                    bool done = false;
                    int next = get_next(s, ch.move);

                    if (next == goal){
                        r = 1;
                        done = true;
                    }else if (holes.count(next)){
                        r = -1;
                        done = true;
                    }

                    env[s][a].push_back({r,ch.p,next,done});
                }
            }
        }
        return env;
    }

    vector<double> policy_evaluation(model& env, Policy& pi, double gamma = 0.99, double theta = 1e-100){

        int S = env.size();

        vector<double> V(S,0.0);
        vector<double> V_prev(S, 0.0);

        while(true){

            for (int s = 0 ; s <S; s++){
                V[s] = 0;
                int a = pi[s];
                auto transit = env[s][a];

                for (const auto& tr : transit){
                    V[s] += tr.prob * (tr.r + gamma * V_prev[tr.ns]); 
                }
            }

            double max_diff = 0.0;

            for (int s = 0; s <S ; s++){
                max_diff = max(max_diff, abs(V[s] - V_prev[s]));
            }

            V_prev = V;

            if (max_diff < theta){
                break;
            }
        }

        return V;

    }

    bool policy_improvement(model& env, Policy& pi, vector<double>& V, double gamma = 0.99){
        int S = env.size();
        int A = env[0].size();

        bool policy_stable = true;

        for (int s = 0 ; s < S; s++){
            int old_a = pi[s];
            int best_q_value = -1e9;
            int best_action = -1;

            for (int a = 0 ; a < A; a++){
                double q_value = 0;
                auto transit = env[s][a];
                for (const auto& tr : transit){
                    q_value += tr.prob * (tr.r + gamma * V[tr.ns]);
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

    Policy policy_iteration(model& env, double gamma = 0.99, double theta = 1e-200){
        int S = env.size();
        Policy pi(S,0);
        int epoch = 0;

        while (true)
        {
            epoch++;
            vector<double> V = policy_evaluation(env, pi);
            bool is_stable = policy_improvement(env, pi, V);     
            if (is_stable){
                break;
            }
        }
        return pi;
        
    }

    Policy value_iteration(model& env, double gamma = 0.99, double theta = 1e-100){

        int S = env.size();
        int A = env[0].size();

        vector<double> V_prev(S,0);
        vector<double> V(S,0);

        Policy pi(S);

        while (true)
        {
            double max_diff = 0.0;
            for (int s = 0; s <S ; s++){
                double best_value_s = -1e9;
                for (int a = 0; a < A; a++){
                    double q_value = 0.0;
                    auto transit = env[s][a];
                    for (const auto& tr: transit){

                        q_value += tr.prob * (tr.r + gamma * V_prev[tr.ns]);
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

        for (int s = 0; s <S ; s++){
                double best_value_q = -1e9;
                int best_action = -1;
                for (int a = 0; a < A; a++){
                    double q_value = 0.0;
                    auto transit = env[s][a];
                    for (const auto& tr: transit){

                        q_value += tr.prob * (tr.r + gamma * V_prev[tr.ns]);
                    }
                    if (q_value > best_value_q){
                        best_value_q = q_value;
                        best_action = a;
                    }
                }
                pi[s] = best_action;
        
            }
        return pi;

    }

    void print_policy(const Policy& pi) {
        // Define the grid layout for visualization
        int rows = 4;
        int cols = 4;
        int goal = 15;
        unordered_set<int> holes = {5, 7, 11, 12};

        // Symbols for actions: 0:Up, 1:Down, 2:Left, 3:Right
        string arrows[] = {" ^ ", " v ", " < ", " > "};

        cout << "---------------------" << endl;
        for (int r = 0; r < rows; ++r) {
            cout << "|";
            for (int c = 0; c < cols; ++c) {
                int s = r * 4 + c;
                
                if (s == goal) {
                    cout << " G  |"; // Goal
                } else if (holes.count(s)) {
                    cout << " HO |"; // Hole
                } else {
                    cout << arrows[pi[s]] << "|";
                }
            }
            cout << endl;
            cout << "---------------------" << endl;
        }
    }

    struct Node{
        int x, y;
        double h_cost;
        double g_cost;
        bool operator> (const Node& another) const{
            return (h_cost + g_cost) > (another.g_cost + another.h_cost);
        }
    };

    double get_h_cost(const Point& a, const Point& b ){
        return (abs(a.first-b.first) + abs(a.second - b.second));
    }

    void solve_A_star(vector<vector<int>>& grid, Point start, Point goal){

        int R = grid.size();
        int C = grid[0].size();

        vector<vector<double>> dist(R, vector<double>(C, 1e9));
        priority_queue<Node, vector<Node>, greater<Node>> MinHeap;

        double h_start = get_h_cost(start,goal);
        MinHeap.push({start.first,start.second,0,h_start});
        dist[start.first][start.second] = 0;
        vector<vector<Point>> parent(R, vector<Point>(C, make_pair(-1,-1)));

        int dx[] = {0,0,-1,1}; // left, right, up, down
        int dy[] = {-1,1,0,0};

        int count = 0;
        while(!MinHeap.empty()){
            count++;
            Node curr = MinHeap.top();
            MinHeap.pop();

            if (curr.x == goal.first && curr.y == goal.second){
                cout << "goal has been achieved" << endl;
                break;
            }

            if (dist[curr.x][curr.y] < (curr.g_cost)){
                    continue;
                }

            for (int i = 0 ; i < 4; i++){
                int nx = curr.x + dx[i];
                int ny = curr.y + dy[i];

                if (nx >=0 && nx<R && ny >=0 && ny<C && grid[nx][ny] ==0 ){
                    double new_h = get_h_cost(make_pair(nx,ny), goal);
                    double new_g = curr.g_cost + 1;

                    if ((new_h+new_g) < dist[nx][ny]){
                        dist[nx][ny] = new_g;
                        MinHeap.push({nx, ny, new_g,new_h});
                        parent[nx][ny] = make_pair(curr.x,curr.y);
                    }
                }
            }
        }

        if (dist[goal.first][goal.second] == 1e9){
            cout << "goal cannot be achieved" << endl;
            return;
        }

        vector<Point> path;
        for (Point P = goal; P != make_pair(-1,-1) ; P = parent[P.first][P.second]){
            path.push_back(P);
        }
        reverse(path.begin(), path.end());

        for (const auto& P : path){
            cout << "(" << P.first << "," << P.second << ")" ;
            cout << endl;
        }

    }


    struct Node1{
        int x, y;
        double h_cost;
        bool operator> (const Node1& another) const{
            return h_cost > another.h_cost;
        }
    };


    void solve_BFS(vector<vector<int>>& grid, Point start, Point goal){

        int R = grid.size();
        int C = grid[0].size();

        priority_queue<Node1, vector<Node1>, greater<Node1>> MinHeap1;
        vector<vector<bool>> tab(R, vector<bool>(C, false));
        vector<vector<Point>> parent(R, vector<Point>(C, make_pair(-1,-1)));

        double h_start = get_h_cost(start,goal);
        MinHeap1.push({start.first,start.second,h_start});
        tab[start.first][start.second] = true;

        int dx[] = {0,0,-1,1}; // left, right, up, down
        int dy[] = {-1,1,0,0};

        int count = 0;
        bool found = false;
        while(!MinHeap1.empty()){
            count++;
            Node1 curr = MinHeap1.top();
            MinHeap1.pop();

            if (curr.x == goal.first && curr.y == goal.second){
                cout << "goal has been achieved" << endl;
                found = true;
                break;
            }

            for (int i = 0 ; i < 4; i++){
                int nx = curr.x + dx[i];
                int ny = curr.y + dy[i];

                if (nx >=0 && nx<C && ny >=0 && ny<R && grid[nx][ny] ==0 && !tab[nx][ny]){
                    tab[nx][ny] = true;
                    double new_h = get_h_cost(make_pair(nx,ny), goal);
                    MinHeap1.push({nx, ny, new_h});
                    parent[nx][ny] = make_pair(curr.x,curr.y);
                }
            }
        }

        if (!found){
            cout << "goal cannot be achieved" << endl;
            return;
        }

        vector<Point> path;
        for (Point P = goal; P != make_pair(-1,-1) ; P = parent[P.first][P.second]){
            path.push_back(P);
        }
        reverse(path.begin(), path.end());

        for (const auto& P : path){
            cout << "(" << P.first << "," << P.second << ")" ;
            cout << endl;
        }

    }
};

int main() {
    MotionPlanning mo;
    // 1. Setup the Environment
    cout << "Building Environment..." << endl;
    
    model env = mo.build_environment();

    // 2. Run Policy Iteration
    cout << "\nRunning Policy Iteration..." << endl;
    Policy pi_pi = mo.policy_iteration(env);
    
    cout << "Policy Iteration Result:" << endl;
    mo.print_policy(pi_pi);

    // 3. Run Value Iteration
    cout << "\nRunning Value Iteration..." << endl;
    Policy pi_vi = mo.value_iteration(env);
    
    cout << "Value Iteration Result:" << endl;
    mo.print_policy(pi_vi);

    return 0;
}