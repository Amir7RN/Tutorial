#include <iostream>
#include <vector>
#include <queue>
#include <climits>
#include <map>
#include <algorithm>

using namespace std;

struct Node{
    int x, y;
    int dist;
    bool operator> (const Node& other) const {
        return dist > other.dist;
    }
};

void Solve(vector<vector<int>>& grid, pair<int, int >& start, pair<int, int>& goal){

    int R = grid.size();
    int C = grid[0].size();

    vector<vector<int>> dist(R, vector<int>(C, 1e9));
    priority_queue<Node, vector<Node>, greater<Node>> MinHeap;
    int dx[] = {0, 0, -1, 1}; // left, right, up, down
    int dy[] = {-1, 1, 0, 0};

    MinHeap.push({start.first, start.second, 0});
    dist[start.first][start.second] = 0;

    vector<vector<pair<int, int>>> parent(R, vector<pair<int, int>>(C, {-1,-1}));
    int count = 0;
    while(!MinHeap.empty()){
        count++;
        Node current = MinHeap.top();
        MinHeap.pop();

        if (current.x == goal.first && current.y == goal.second){
            cout << "Goal is reached ! " << endl;
            break;
        }

        if (current.dist > dist[current.x][current.y]) continue;

        for(int i = 0; i < 4; i++){
            
            int nx = current.x + dx[i];
            int ny = current.y + dy[i];
            
            if (nx >= 0 && nx < R && ny >=0 && ny< C && grid[nx][ny] == 0){
                int newdist = dist[current.x][current.y] + 1;

                if (newdist < dist[nx][ny]){
                    dist[nx][ny] = newdist;
                    parent[nx][ny] = {current.x,current.y};
                    MinHeap.push({nx, ny, newdist});
                }
            }
        }
    }

    if (dist[goal.first][goal.second] == 1e9){
        cout << "the gaol cannot be reached";
        return;
    }

    vector<pair<int , int>> path;

    for (pair<int , int> p = goal; p.first != -1; p = parent[p.first][p.second]){
        path.push_back(p);
    }

    reverse(path.begin(), path.end());

    cout << "shortest path is : " << path.size() << endl;
    cout << "number of nodes investigated : " << count << endl;

    for (const auto& p : path){
        cout << "(" << p.first << "," << p.second << ")";
        cout << endl;
    }
}


int main(){

    vector<vector<int>> grid = {
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    {0, 1, 1, 1, 1, 1, 1, 1, 1, 1}, // Wall with gap at (5,0)
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0}
};
    pair<int, int > start = {0,0};
    pair<int, int> goal = {9,9};


    Solve(grid, start,goal);

    return 0;
}