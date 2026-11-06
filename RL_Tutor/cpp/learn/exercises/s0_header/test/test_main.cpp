#include "check.hpp"
#include "pid.hpp"
#include "uses_pid.hpp"   // pid.hpp arrives a second time through here

int main() {
    Pid p(2.0, 1.0, 0.1, 0.001);
    CHECK_NEAR("first update has no derivative kick", p.update(1.0), 2.0 + 0.001, 1e-12);
    CHECK_NEAR("second update: P + I + D", runOnce(p, 0.5),
               2.0 * 0.5 + 1.0 * 0.0015 + 0.1 * (0.5 - 1.0) / 0.001, 1e-9);
    CHECK_NEAR("integral accumulates e*dt", p.integral(), 0.0015, 1e-12);
    p.reset();
    CHECK_NEAR("reset clears the integral", p.integral(), 0.0, 0.0);
    CHECK_NEAR("reset re-arms the no-kick rule", p.update(1.0), 2.001, 1e-12);
    const Pid& view = p;
    CHECK_NEAR("integral() is callable on a const Pid", view.integral(), 0.001, 1e-12);
    DONE();
}
