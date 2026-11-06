#include <atomic>
#include <chrono>
#include <thread>
#include "check.hpp"
#include "latest_value.hpp"

struct State {
    long a = 0, b = 0, c = 0;   // invariant the writer keeps: b == 2a, c == 3a
};

int main() {
    LatestValue<State> lv;
    State out;
    CHECK("nothing written yet: read returns false", !lv.read(out));
    lv.write({1, 2, 3});
    CHECK("after a write: read returns true", lv.read(out));
    CHECK_EQ("and gives the value", out.a, 1L);
    CHECK("reading again without a write: false", !lv.read(out));
    CHECK_EQ("but still gives the last value", out.a, 1L);
    lv.write({2, 4, 6});
    lv.write({3, 6, 9});
    CHECK("two writes, one read: true", lv.read(out));
    CHECK_EQ("the reader gets the LATEST, not a queue", out.a, 3L);

    LatestValue<State> shared;
    const long total = 300000;
    std::atomic<bool> done{false};
    std::thread writer([&] {
        for (long i = 1; i <= total; ++i) shared.write({i, 2 * i, 3 * i});
        done = true;
    });
    bool torn = false, backwards = false;
    long last = 0, reads = 0;
    auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(4);
    while (std::chrono::steady_clock::now() < deadline) {
        State v;
        bool fresh = shared.read(v);
        if (fresh) ++reads;
        if (v.b != 2 * v.a || v.c != 3 * v.a) torn = true;
        if (v.a < last) backwards = true;
        last = v.a;
        if (done && !fresh && last == total) break;
    }
    writer.join();
    CHECK("never a torn read across threads", !torn);
    CHECK("never goes backwards in time", !backwards);
    CHECK_EQ("ends on the final value", last, total);
    CHECK("the reader saw new values while the writer ran", reads > 1);
    DONE();
}
