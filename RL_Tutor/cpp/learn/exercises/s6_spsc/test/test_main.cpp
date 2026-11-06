#include <chrono>
#include <thread>
#include "check.hpp"
#include "spsc.hpp"

int main() {
    SpscQueue<int, 4> q;
    int v = -1;
    CHECK("empty queue: pop fails", !q.pop(v));
    CHECK("push 1", q.push(1));
    CHECK("push 2", q.push(2));
    CHECK("push 3", q.push(3));
    CHECK("usable capacity is N-1: 4th push fails", !q.push(4));
    CHECK("FIFO: pops 1 first", q.pop(v) && v == 1);
    CHECK("then there is room again", q.push(4));
    CHECK("FIFO across the wrap", q.pop(v) && v == 2 && q.pop(v) && v == 3 && q.pop(v) && v == 4);
    CHECK("empty again", !q.pop(v));

    // two threads, 200000 values, in order, nothing lost
    const int total = 200000;
    SpscQueue<int, 64> big;
    bool gaveUp = false;
    auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(4);
    std::thread producer([&] {
        for (int i = 0; i < total; ++i)
            while (!big.push(i)) {
                if (std::chrono::steady_clock::now() > deadline) { gaveUp = true; return; }
            }
    });
    int expect = 0;
    bool inOrder = true;
    while (expect < total && std::chrono::steady_clock::now() < deadline) {
        int x;
        if (big.pop(x)) {
            if (x != expect) inOrder = false;
            ++expect;
        }
    }
    producer.join();
    CHECK("producer never stuck (queue drains)", !gaveUp);
    CHECK_EQ("consumer received every value", expect, total);
    CHECK("in order, across threads", inOrder);
    DONE();
}
