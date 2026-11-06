#include <cmath>
#include "check.hpp"
#include "config.hpp"
#include "motor.hpp"

static bool startsWith(const std::string& s, const std::string& p) { return s.rfind(p, 0) == 0; }

int main() {
    const std::string good =
        "# cascade\n"
        "\n"
        "position 1000  kp=63   limit=100\n"
        "velocity 8000  kp=0.25 ki=30   limit=5\n"
        "current  32000 kp=4.7  ki=9400 limit=24\n";
    Signals s;
    std::string err;
    auto sched = buildFromConfig(good, 32000, s, &err);
    CHECK("the good config builds", sched != nullptr);
    if (sched) {
        CHECK_EQ("three tasks", sched->taskCount(), std::size_t(3));
        MotorPlant motor;
        s.posRef = 1.0;
        for (long k = 0; k < 16000; ++k) { sched->tick(); motor.step(s, 1.0 / 32000); }
        CHECK_NEAR("closed loop from config reaches 1 rad", s.pos, 1.0, 0.01);
    }
    struct Bad { const char* text; const char* prefix; const char* what; };
    const Bad bad[] = {
        {"position 1000 kp=63 limit=100\nvelocty 8000 kp=1 limit=5\n", "line 2: ", "unknown type"},
        {"position kp=63 limit=100\n", "line 1: ", "missing rate"},
        {"position 1000.5 kp=63 limit=100\n", "line 1: ", "non-integer rate"},
        {"# c\nposition 1000 kp=6x3 limit=100\n", "line 2: ", "bad number"},
        {"position 1000 ki=1 limit=100\n", "line 1: ", "key the type does not take"},
        {"position 1000 kp=63\n", "line 1: ", "missing limit"},
        {"current 7000 kp=1 limit=24\n", "line 1: ", "rate the scheduler refuses"},
        {"position 1000 kp=63 limit=100 fast\n", "line 1: ", "token without ="},
    };
    for (const Bad& b : bad) {
        Signals t;
        std::string e;
        auto r = buildFromConfig(b.text, 32000, t, &e);
        CHECK(std::string("rejects: ") + b.what, r == nullptr);
        CHECK(std::string("  and names the line (") + b.prefix + "...)", startsWith(e, b.prefix));
    }
    DONE();
}
