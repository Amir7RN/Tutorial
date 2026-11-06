// Project v5: YOU write the tests.
//
// The grader compiles this file five times against scheduler.hpp: once
// correct, and once with each of four hidden bugs (see the hints on the page).
// Your tests must PASS on the correct scheduler and FAIL (exit code != 0) on
// every broken one. That is what a test suite is for: catching the change
// that someone will make next month.
//
// check.hpp gives you CHECK, CHECK_EQ, CHECK_NEAR, CHECK_THROWS.
// End main with:   return chk::failures() == 0 ? 0 : 1;
#include <string>
#include <vector>
#include "check.hpp"
#include "scheduler.hpp"

// A controller that records what happened to it -- the usual testing trick.
struct Probe : Controller {
    std::string n;
    std::vector<std::string>* log;
    double lastDt = 0.0;
    long calls = 0;
    Probe(std::string name, std::vector<std::string>* l) : n(std::move(name)), log(l) {}
    void update(double dt) override {
        lastDt = dt;
        ++calls;
        if (log) log->push_back(n);
    }
    const char* name() const override { return n.c_str(); }
};

int main() {
    // One test to start you off: adding a valid task works.
    {
        Scheduler s(32000);
        CHECK("a 1 kHz task is accepted", s.add(std::make_unique<Probe>("p", nullptr), 1000));
        CHECK_EQ("and counted", s.taskCount(), std::size_t(1));
    }

    // TODO: test that a rate which does not divide the base rate is refused
    // TODO: test the order tasks run in within one tick (use the log)
    // TODO: test that the very first tick() runs every task
    // TODO: test the dt a slow task is given

    return chk::failures() == 0 ? 0 : 1;
}
