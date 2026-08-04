#include <cmath>
#include <algorithm>
#include <vector>
#include <queue>
#include <iostream>

using namespace std;

typedef pair<int, int> Point;

struct Node{
    int x, y;
    int st_dist;
    int goal_dist;
    bool operator> (const Node& another) const {
        return (st_dist+goal_dist) > (another.st_dist+another.goal_dist);
    }
};

int g_cost(const Point& a, const Point& goal){
    return (abs(a.first - goal.first) + abs(a.second - goal.second));
}

void solve (vector<vector<int>>& grid, Point& start, Point& goal){

    int R = grid.size();
    int C = grid[0].size();

    vector<vector<int>> dist_tab(R, vector<int>(C, 1e9));
    priority_queue<Node, vector<Node>, greater<Node>> MinHeap;
    vector<vector<Point>> parent(R, vector<Point>(C, {-1,-1}));

    dist_tab[start.first][start.second] = 0;
    MinHeap.push({start.first,start.second,0,g_cost(start,goal)});


    int dx[] = {0,0,-1,1};
    int dy[] = {-1, 1, 0, 0};

    int count = 0;
    while(!MinHeap.empty()){
        count++;
        Node curr = MinHeap.top();
        MinHeap.pop();

        if (curr.x == goal.first && curr.y == goal.second){
            cout << "done " << endl;
            break;
        }

        if (curr.st_dist > dist_tab[curr.x][curr.y]) continue;

        for (int i = 0 ; i< 4; i++){
            int nx = curr.x + dx[i];
            int ny = curr.y + dy[i];

            if (nx >= 0 && nx < R && ny >=0 && ny < C && grid[nx][ny] == 0){
                int newdist = curr.st_dist + 1;

                if (newdist < dist_tab[nx][ny]){
                    dist_tab[nx][ny] = newdist;
                    parent[nx][ny] = make_pair(curr.x,curr.y);
                    MinHeap.push({nx,ny, newdist, g_cost({nx,ny}, goal)});

                }
            }
        }
    }

    if (dist_tab[goal.first][goal.second] == 1e9){
        cout << "Goal cannot be reached" << endl;
        return;
    }

    vector<Point> path;
    for (Point p = goal; p != make_pair(-1,-1); p = parent[p.first][p.second]){
        path.push_back(p);
    }
    reverse(path.begin(), path.end());

    cout << "shortest path is : " << path.size() << endl;
    cout << "number of nodes investigated : " << count << endl;

    for (const auto& p : path){
        cout << " (" << p.first << "," << p.second << ")";
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

    solve(grid, start, goal);

}