#include<iostream>
#include<vector>
#include<algorithm>
#include<cmath>
#include<queue>

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
    vector<vector<Cell>> parent(R, vector<Cell>(C, make_pair(-1,-1)));
    priority_queue<Node, vector<Node>, greater<Node>> minHeap;

    minHeap.push({start.first,start.second,distance(start,Goal)});

    int dx[] = {0,0,-1,1};
    int dy[] = {-1,1,0,0};

    vector<vector<bool>> visited(R, vector<bool>(C,false));
    visited[start.first][start.second] = true;
    bool found = false;
    while(!minHeap.empty()){

        Node current = minHeap.top();
        minHeap.pop();

        if (visited[current.x][current.y]) continue;
        visited[current.x][current.y] = true;

        if (current.x == Goal.first && current.y == Goal.second){
            cout<< "Goal is reached" << endl;
            found = true;
            break;

        } 

        for (int a = 0; a < 4; ++a){
            int nx = current.x + dx[a];
            int ny = current.y + dy[a];

            if (nx >=0 && nx < R && ny >= 0 && ny < C && !visited[nx][ny] && grid[nx][ny] ==0){
                parent[nx][ny] = make_pair(current.x, current.y);
                minHeap.push({nx, ny, distance({nx,ny}, Goal)});
            }
        }
    }

    if (!found) {
        cout << "Goal cannot be reached" << endl;
        return;
    }

    vector<Cell> path;

    for (Cell p = Goal; p.first !=-1; p = parent[p.first][p.second]){
        path.push_back(p);
    }

    reverse(path.begin(), path.end());

    for (const auto& p : path){
        cout << "(" << p.first << "," << p.second << ")";
        cout << endl;
    }

}