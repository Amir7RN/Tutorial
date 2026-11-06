#include <cmath>
#include "check.hpp"
#include "loops.hpp"
#include "motor.hpp"

int main() {
    Pi pi{2.0, 10.0, 1.0};
    CHECK_NEAR("PI: kp*e + ki*integral", pi.step(0.1, 0.01), 2.0 * 0.1 + 10.0 * 0.001, 1e-12);
    Pi sat{2.0, 10.0, 1.0};
    CHECK_NEAR("PI output is clamped", sat.step(5.0, 0.01), 1.0, 0.0);
    for (int k = 0; k < 1000; ++k) sat.step(5.0, 0.01);
    CHECK("anti-windup: ki*integral never exceeds the limit", 10.0 * sat.integral <= 1.0 + 1e-12);
    CHECK("after a long saturation, a reversed error un-saturates fast", sat.step(-5.0, 0.01) < 0.0);

    Signals s;
    s.velRef = 2.0; s.vel = 1.0;
    VelocityLoop vel(s, 0.25, 30.0, 5.0);
    vel.update(0.001);
    CHECK_NEAR("VelocityLoop writes curRef", s.curRef, 0.25 * 1.0 + 30.0 * 0.001, 1e-12);
    s.curRef = 1.0; s.cur = 0.5;
    CurrentLoop cur(s, 4.7, 9400.0, 24.0);
    cur.update(1.0 / 32000);
    CHECK_NEAR("CurrentLoop writes voltage", s.voltage, 4.7 * 0.5 + 9400.0 * 0.5 / 32000, 1e-9);

    // the whole cascade, by hand, against the simulated motor
    Signals j;
    MotorPlant motor;
    PositionLoop p(j, 63.0, 100.0);
    VelocityLoop v(j, 0.25, 30.0, 5.0);
    CurrentLoop c(j, 4.7, 9400.0, 24.0);
    const double dt = 1.0 / 32000;
    j.posRef = 1.0;
    double peakV = 0.0;
    for (long k = 0; k < 16000; ++k) {
        if (k % 32 == 0) p.update(32 * dt);
        if (k % 4 == 0) v.update(4 * dt);
        c.update(dt);
        motor.step(j, dt);
        peakV = std::max(peakV, std::fabs(j.voltage));
    }
    CHECK_NEAR("cascade reaches 1 rad in 0.5 s", j.pos, 1.0, 0.01);
    CHECK("and settles (velocity near 0)", std::fabs(j.vel) < 0.5);
    CHECK("voltage stayed within the 24 V supply", peakV <= 24.0 + 1e-9);
    DONE();
}
