#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

class Interval {
public:
    int start, end;
    Interval(int start, int end){
        this->start = start;
        this->end = end;
    };
    bool operator<(const Interval& another) const{
            return start < another.start;
    }
};

class Solution{
public:
    bool canAttendMeetings(vector<Interval>& intervals){
        sort(intervals.begin(), intervals.end(), [](const Interval& a, const Interval& b){
            return a.start < b.start;
        });
        int start = intervals[0].start;
        int end = intervals[0].end;
        int EndPrev = end;
        for(int i = 1; i < intervals.size(); i++){
            if (intervals[i].start >= EndPrev){
                continue;
            }else{
                return false;
            }
        }
        return true;
    }
};