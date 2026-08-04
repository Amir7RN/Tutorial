#include <iostream>
#include <algorithm>
#include <cmath>
#include <queue>

using namespace std;
using Point = pair<int, int>;


double get_h_cost(const Point& a, const Point& b){
    return (abs(a.first-b.first) + abs(a.second-b.second));
}

struct Node{
    int x, y;
    bool haspackage;
    double g_cost;
    double h_cost;
    bool operator> (const Node& another) const{
        return (g_cost + h_cost) > (another.g_cost + another.h_cost);
    }
};
struct parnetinfo{
        int x, y;
        bool pack;
    };

void Solve(vector<vector<int>>& grid, Point start, Point goal, Point package, int battery_limit){
    int R = grid.size();
    int C = grid[0].size();

    int dx[] = {0,0,-1,1}; //left, right, up, down
    int dy[] = {-1,1,0,0};
    priority_queue<Node, vector<Node>, greater<Node>> pq;
    pq.push({start.first,start.second,false, 0, (get_h_cost(start, goal)+ get_h_cost(start, package))});
    vector<vector<vector<double>>> dist(R, vector<vector<double>>(C, vector<double>(2,1e9)));
    dist[start.first][start.second][0] = 0;


    
    vector<vector<vector<parnetinfo>>> parent(R, vector<vector<parnetinfo>>(C, vector<parnetinfo>(2 , {-1,-1,false})));

    Node finalNode = {-1,-1,false, 0,0};
    bool found = false;
    
    while(!pq.empty()){

        Node curr = pq.top();
        pq.pop();

        if (curr.haspackage && curr.x == goal.first && curr.y == goal.second){
            finalNode = curr;
            found = true;
            break;
        }

        if (curr.g_cost > dist[curr.x][curr.y][curr.haspackage]){
            continue;
        }

        for (int i = 0 ; i < 4; i++){
            int nx = curr.x + dx[i];
            int ny = curr.y + dy[i];

            if (nx >= 0 && ny >=0 && nx < R && ny < C){
                double moveCost = grid[nx][ny];
                double new_g = curr.g_cost + moveCost;

                if (new_g > battery_limit){
                    continue;
                }

                bool nexthaspackage = curr.haspackage;
                if (nx == package.first && ny == package.second){
                    nexthaspackage = true;
                }

                if (new_g < dist[nx][ny][nexthaspackage]){
                    dist[nx][ny][nexthaspackage] = new_g;
                    parent[nx][ny][nexthaspackage] = {curr.x, curr.y, curr.haspackage};

                    double next_h;
                    if (!nexthaspackage){
                        next_h = (get_h_cost(make_pair(nx,ny), goal)+ get_h_cost(make_pair(nx,ny), package));
                    }else{
                        next_h = (get_h_cost(make_pair(nx,ny), goal));
                    }
                    pq.push({nx,ny,nexthaspackage,new_g,next_h});
                }
            }
        }
    }

    if (found) {
        cout << "Path found! Battery used: " << finalNode.g_cost << endl;
        vector<parnetinfo> path;
        for (parnetinfo P = {goal.first, goal.second, true} ; P.x != -1; P = parent[P.x][P.y][P.pack]){
            path.push_back(P);
        }
        reverse(path.begin(), path.end());

        for (const auto& P : path){
            cout << "(" << P.x << "," << P.y << ", " << P.pack << ")";
            cout << endl;
        }
    } else {
        cout << "Could not complete mission within battery limit." << endl;
    }

    




}


int main(){

    vector<vector<int>> grid = {
    {1, 1, 1, 1},
    {1, 5, 5, 1}, // 5 represents heavy cargo/mud
    {1, 1, 1, 1}
    };

    Point start = {0,0};
    Point package = {2,0};
    Point goal = {2,3};
    int battery_limit = 20;

    Solve(grid, start,goal,package,battery_limit);

    return 0;
}