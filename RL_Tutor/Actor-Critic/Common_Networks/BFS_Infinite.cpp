#include<iostream>
#include<vector>
#include<algorithm>
#include<cmath>
#include<queue>
#include<map>
#include<set>

using namespace std;

using Cell = pair<int, int>;

struct Node {
    int x,y;
    int dist;

    bool operator> (const Node& other) const{
        return this->dist > other.dist;
    }
};

int distance(const Cell A, const Cell Goal){
    return (abs(Goal.first - A.first) + abs(Goal.second - A.second));
}

void Solve(Cell& start, Cell& Goal, vector<vector<int>>& grid){
    int R = grid.size();
    int C = grid[0].size();
    map<Cell, Cell> parent;
    priority_queue<Node, vector<Node>, greater<Node>> minHeap;

    minHeap.push({start.first,start.second,distance(start,Goal)});

    int dx[] = {0,0,-1,1};
    int dy[] = {-1,1,0,0};

    set<Cell> Visited;

    bool found = false;
    while(!minHeap.empty()){

        Node current = minHeap.top();
        minHeap.pop();

        if (Visited.count({current.x,current.y})) continue;
        Visited.insert({current.x,current.y});

        if (current.x == Goal.first && current.y == Goal.second){
            cout<< "Goal is reached" << endl;
            found = true;
            break;

        } 

        for (int a = 0; a < 4; ++a){
            int nx = current.x + dx[a];
            int ny = current.y + dy[a];

            if (nx >=0 && nx < R && ny >= 0 && ny < C && !Visited.count({nx,ny}) && grid[nx][ny] ==0){
                Cell neighbor = {nx, ny};
                if (parent.find(neighbor) == parent.end() && neighbor != start){
                    parent[neighbor] = make_pair(current.x, current.y);
                }
                
                minHeap.push({nx, ny, distance(neighbor, Goal)});
            }
        }
    }

    if (!found) {
        cout << "Goal cannot be reached" << endl;
        return;
    }

    vector<Cell> path;

    for (Cell p = Goal; ; p = parent[p]){
        path.push_back(p);
        if (p == start) break;
    }

    reverse(path.begin(), path.end());

    for (const auto& p : path){
        cout << "(" << p.first << "," << p.second << ")";
        cout << endl;
    }

}