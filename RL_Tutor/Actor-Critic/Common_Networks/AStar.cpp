#include <iostream>
#include <vector>
#include <algorithm>
#include <cstdint>
#include <map>
#include <set>
#include <cmath>
#include <queue>

using namespace std;

struct Node
{
    int x, y;
    int dist_start;
    int dist_goal;
};
using Cell = pair<int, int>;
int distance(const Cell& A, const Cell& B){
    return abs(A.first - B.first) + abs(A.second - B.second);
}




void Solve(set<Cell>& blocked, Cell start, Cell Goal){
    // left, right, up , down
    int dx[] = {0,0,1,-1};
    int dy[] = {-1,1,0,0};

    map<Cell, Cell> parent;
    map<Cell, int> dist_start;
    map<Cell, int> dist_goal;


    // dist is summation of distance to goal and from start
    auto comparison = [](const Node& A, const Node& B) {
        return (A.dist_goal + A.dist_start) > (B.dist_goal + B.dist_start);
    };

    //push the higher priority to the top
    priority_queue<Node, vector<Node>, decltype(comparison)> minHeap(comparison);

    dist_start[start] = 0 ;
    dist_goal[start] = distance(start, Goal);
    minHeap.push({start.first, start.second, dist_start[start], dist_goal[start]});

    bool found = false;

    while (!minHeap.empty()){
        Node current = minHeap.top();
        minHeap.pop();

        Cell curr_cell = {current.x, current.y};
        if (blocked.count(curr_cell)) continue;

        if (current.dist_start > dist_start[curr_cell]) continue;

        if (current.x == Goal.first && current.y == Goal.second){
            cout << "Goal is reached" << endl;
            found = true;
            break;
        }

        for (int a = 0; a < 4; ++a){
            int nx = current.x + dx[a];
            int ny = current.y + dy[a];
            Cell neighbor = {nx, ny};

            int newDist_start = dist_start[curr_cell] + 1;
            int newDist_goal = distance({nx, ny}, Goal);

            if (!blocked.count({nx, ny}) && (dist_start.find(neighbor) == dist_start.end() || newDist_start < dist_start[neighbor])){
                minHeap.push({nx, ny, newDist_start, newDist_goal });
                parent[neighbor] = curr_cell;
                dist_start[neighbor] = newDist_start;
                dist_goal[neighbor] = newDist_goal;

            }
        } 
    }
    if (found){
        vector<Cell> path;

        for (Cell p = Goal; ; p = parent[p]){
            path.push_back(p);
            if (p == start) break;
        }
        reverse(path.begin(), path.end());
    }else{
        cout<< "Goal is not reached"<<endl;
    }
}
