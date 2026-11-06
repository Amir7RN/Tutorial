#include <string>
#include <vector>
#include "alloc_count.hpp"
#include "check.hpp"
#include "scheduler.hpp"

static std::vector<std::string> g_order;
static int g_alive = 0;

struct Probe : Controller {
    const char* n;
    double lastDt = 0.0;
    explicit Probe(const char* name) : n(name) { ++g_alive; }
    ~Probe() override { --g_alive; }
    void update(double dt) override {
        lastDt = dt;
        if (g_order.size() < g_order.capacity()) g_order.push_back(n);   // never reallocates
    }
    const char* name() const override { return n; }
};

int main() {
    CHECK_THROWS("baseHz 0 is refused", Scheduler(0));
    Scheduler s(32000);
    auto cur = std::make_unique<Probe>("current");
    Probe* curView = cur.get();
    CHECK("add current at 32 kHz", s.add(std::move(cur), 32000));
    CHECK("add velocity at 8 kHz", s.add(std::make_unique<Probe>("velocity"), 8000));
    CHECK("add position at 1 kHz", s.add(std::make_unique<Probe>("position"), 1000));
    int aliveBefore = g_alive;
    CHECK("7 kHz does not divide 32 kHz: refused", !s.add(std::make_unique<Probe>("x"), 7000));
    CHECK("0 Hz refused", !s.add(std::make_unique<Probe>("x"), 0));
    CHECK("faster than the base clock refused", !s.add(std::make_unique<Probe>("x"), 64000));
    CHECK("null refused", !s.add(nullptr, 1000));
    CHECK_EQ("refused controllers were destroyed, not leaked", g_alive, aliveBefore);
    CHECK_EQ("three tasks", s.taskCount(), std::size_t(3));

    g_order.reserve(8);
    s.tick();
    bool order = g_order.size() == 3 && g_order[0] == "position" && g_order[1] == "velocity" &&
                 g_order[2] == "current";
    CHECK("tick 0 runs all three, slowest first", order);
    CHECK_NEAR("current loop told dt = 1/32000", curView->lastDt, 1.0 / 32000, 1e-15);

    long allocs = chk::totalAllocs();
    for (int k = 1; k < 32000; ++k) s.tick();
    CHECK_EQ("tick() never allocates", chk::totalAllocs() - allocs, 0L);
    CHECK_EQ("one second of ticks", s.ticks(), 32000L);
    if (s.taskCount() == 3) {
        CHECK_EQ("position ran 1000 times", s.runs(0), 1000L);
        CHECK_EQ("velocity ran 8000 times", s.runs(1), 8000L);
        CHECK_EQ("current ran 32000 times", s.runs(2), 32000L);
    }
    DONE();
}
