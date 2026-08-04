#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <queue>

using namespace std;

struct Node {
    int x, y;
    int distance;

    bool operator>(const Node& another) const{
        return distance > another.distance;
    }
};

int distance(const pair<int, int> A, const pair<int, int> goal){
    int dist_A = abs(goal.first - A.first) + abs(goal.second - A.second);
    return dist_A;
}


void Solve (pair<int, int>& goal, pair<int, int>& start, vector<vector<int>>& grid){

    int R = grid.size();
    int C = grid[0].size();
    vector<vector<pair<int, int>>>parent(R, vector<pair<int, int>>(C, {-1,-1}));
    priority_queue<Node, vector<Node>, greater<Node>> MinHeap;
    MinHeap.push({start.first,start.second, distance(start,goal)});
    int dx[] = {0,0,-1,1}; // left, right, up, down.
    int dy[] = {-1, 1 , 0, 0};

    //vector<vector<int>>dist(R, vector<int>(C, 1e9));
    //dist[start.first][start.second] = distance(start,goal);

    vector<vector<bool>> visited(R, vector<bool>(C, false));
    visited[start.first][start.second] = true;

    bool found = false;
    while(!MinHeap.empty()){
        Node current = MinHeap.top();
        MinHeap.pop();

        if (current.x == goal.first && current.y == goal.second){
            cout << "Goal has been reached!" << endl;
            break;
        }

        for (int i = 0; i < 4; i++){
            int nx = current.x + dx[i];
            int ny = current.y + dy[i];

            if (nx >=0 && nx < C && ny >=0 && ny <R && grid[nx][ny] == 0 && !visited[nx][ny]){
                    visited[nx][ny] = true;
                    parent[nx][ny] = {current.x, current.y};
                    MinHeap.push({nx, ny, distance({nx,ny},goal)});
                    
            }
        }
    }

    if (!found){
        cout << "the goal cannot be reached";
        return;
    }

    vector<pair<int, int>> path;

    for (pair<int, int> P = goal; P != make_pair(-1,-1); P = parent[P.first][P.second]){
        path.push_back(P);
    }

    reverse(path.begin(), path.end());

    for (const auto& p : path){
        cout << "(" << p.first << "," << p.second << ")";
        cout << endl;
    }
}


int main(){
    vector<vector<int>> grid = {
        {0 ,0, 1, 0},
        {0 , 1 , 0, 1},
        {0 , 0 ,0, 1},
        {1 ,1 ,0 , 0}
    };
    pair<int, int > start = {0,0};
    pair<int, int> goal = {3,3};

}