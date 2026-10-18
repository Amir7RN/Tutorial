#include <iostream>
#include <algorithm>
#include <map>
#include <set>
#include <algorithm>
#include <functional>
#include <queue>
#include <vector>
#include <utility>

using namespace std;

using cell = pair<int, int>;

struct Node {
    int x,y;
    int dist;

    bool operator> (const Node& other) const {
        return this->dist > other.dist;
    }
};

void solve(set<cell>& blocked, cell start, cell goal){

    if (blocked.count(start) || blocked.count(goal)){
        return;
    }

    map<cell, int> dist;
    map<cell, cell> parent;

    priority_queue<Node, vector<Node> , greater<Node>> minHeap;

    int dx[] = {0 , 0, -1, 1}; //right, left, up, down
    int dy[] = {-1, 1, 0, 0};

    dist[start] = 0;
    minHeap.push({start.first, start.second, 0});

    while(!minHeap.empty()){
        Node current = minHeap.top();
        minHeap.pop();

        cell current_cell = {current.x, current.y};
        if(current.dist > dist[current_cell]) continue;

        if(current_cell == goal) {
            cout << "Goal is reached" << endl;
            break;
        }

        for (int i = 0; i < 4; ++i) {
            int nx = current.x + dx[i];
            int ny = current.y + dy[i];

            cell next = {nx, ny};

            if (blocked.count(next)) continue;

            int newdist = current.dist + 1;

            auto it = dist.find(next);

            if (it == dist.end() || newdist < it->second){
                dist[next] = newdist;
                parent[next] = current_cell;
                minHeap.push({nx, ny, newdist});
            }
        }
    }
    cout << "Goal cannot be reached";

    vector<cell> path;
    for (cell p = goal; ; parent[p]){
        path.push_back(p);
        if (p == start) break;
    }

    reverse(path.begin(), path.end());

    for (const auto& p : path){
        cout << "(" << p.first << "," << p.second << ")" ;
    }
    return;
}
