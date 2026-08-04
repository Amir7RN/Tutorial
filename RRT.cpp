#include<iostream>
#include <cmath>
#include <vector>
#include <queue>
#include <algorithm>
#include <random>
#include <memory>

using namespace std;


struct RRTNode {
    double x_,y_;
    RRTNode* parent;

    RRTNode(double x, double y): x_(x), y_(y), parent(nullptr) {}
};

double get_dist(double x1, double y1, double x2, double y2){
    return sqrt(pow(x1-x2,2) + pow(y1-y2,2));
}

struct Obstacle {
    double x, y, radius;
};

bool isCollisionFree(double x1, double y1, double x2, double y2, const vector<Obstacle>& obstacles) {
    // We check points along the line segment from (x1,y1) to (x2,y2)
    int checks = 10; 
    for (int i = 0; i <= checks; i++) {
        double t = (double)i / checks;
        double currX = x1 + t * (x2 - x1);
        double currY = y1 + t * (y2 - y1);

        for (auto& obs : obstacles) {
            if (get_dist(currX, currY, obs.x, obs.y) < obs.radius) {
                return false; // Hits a circle!
            }
        }
    }
    return true;
}

void solveRRT(pair<double, double> start, pair<double, double> goal){
    double stepsize = 0.5;
    double getthreshold = 0.5;
    int maxIteration = 5000;

    random_device rd;
    mt19937 gen(rd());
    uniform_real_distribution<> dis(0.0, 10.0);

    vector<unique_ptr<RRTNode>> tree;
    tree.push_back(make_unique<RRTNode>(start.first, start.second));
    RRTNode* lastNode = nullptr;

    for (int i = 0; i < maxIteration; i++){
        double randX, randY;
        if (dis(gen) < 1.0){
            randX = goal.first;
            randY = goal.second;
        }else{
            randX = dis(gen);
            randY = dis(gen);
        }

        RRTNode* nearest = tree[0];
        double min_dist = get_dist(nearest->x, nearest->y, randX, randY);
        for (auto node& : tree){
            double d = get_dist(node->x_, node->y_, randX, randY);
            if (d < min_dist){
                min_dist = d;
                nearest = node;
            }
        }

        double theta = atan2(randY-nearest->y, randX-nearest->x);
        double newX = nearest->x + stepSize * cos(theta);
        double newY = nearest->y + stepSize * sin(theta);

        if (isCollisionFree(nearest->x, nearest->y, newX, newY)){
            auto newNode = make_unique<RRTNode>(newX, newY);
            newNode->parent = nearest;
            tree.push_back(move(newNode));


            if (get_dist(newX, newY, goal.first, goal.second) < goalThreshold){
                lastNode = tree.back().get();
                cout << "Goal Found in " << i << " iterations!" << endl;
                break;
            }
        }
    }

    if (lastNode){
        vector<pair<double, double>> path;
        for (RRTNode* curr = lastNode; curr!= nullptr; curr= curr->parent){
            path.push_back({curr->x, curr->y});
        }
        reverse(path.begin(), path.end());

        for (auto p : path) cout << "(" << p.first << ", " << p.second << ") -> ";
        cout << "GOAL" << endl;
    } else {
        cout << "Path not found." << endl;
    }
    //for (auto node : tree) delete node;
}

int main() {
    solveRRT({0.0, 0.0}, {9.0, 9.0});
    return 0;
}