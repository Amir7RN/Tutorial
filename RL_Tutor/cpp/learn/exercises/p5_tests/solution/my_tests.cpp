#include <string>
#include <vector>
#include "check.hpp"
#include "scheduler.hpp"

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
    {
        Scheduler s(32000);
        CHECK("a 1 kHz task is accepted", s.add(std::make_unique<Probe>("p", nullptr), 1000));
        CHECK_EQ("and counted", s.taskCount(), std::size_t(1));
    }
    {
        Scheduler s(32000);
        CHECK("7 kHz does not divide 32 kHz", !s.add(std::make_unique<Probe>("x", nullptr), 7000));
    }
    {
        std::vector<std::string> log;
        Scheduler s(32000);
        s.add(std::make_unique<Probe>("fast", &log), 32000);
        s.add(std::make_unique<Probe>("slow", &log), 1000);
        s.tick();
        CHECK("first tick runs both", log.size() == 2);
        CHECK("slowest first", log.size() == 2 && log[0] == "slow" && log[1] == "fast");
    }
    {
        auto p = std::make_unique<Probe>("slow", nullptr);
        Probe* view = p.get();
        Scheduler s(32000);
        s.add(std::move(p), 1000);
        s.tick();
        CHECK_EQ("tick 0 runs a 1 kHz task", view->calls, 1L);
        CHECK_NEAR("a 1 kHz task gets dt = 1 ms", view->lastDt, 0.001, 1e-12);
    }
    return chk::failures() == 0 ? 0 : 1;
}
