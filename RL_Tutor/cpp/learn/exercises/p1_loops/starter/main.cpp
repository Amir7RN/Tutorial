// v0: a hand-written cascade. 32 kHz base tick: current every tick,
// velocity every 4th (8 kHz), position every 32nd (1 kHz).
// The divide-by-counter logic below is what v2's Scheduler will own.
#include <cstdio>
#include "loops.hpp"
#include "motor.hpp"

int main() {
    Signals s;
    MotorPlant motor;
    PositionLoop pos(s, 63.0, 100.0);
    VelocityLoop vel(s, 0.25, 30.0, 5.0);
    CurrentLoop cur(s, 4.7, 9400.0, 24.0);

    const int base = 32000;
    const double dt = 1.0 / base;
    s.posRef = 1.0;
    for (long k = 0; k < base / 2; ++k) {           // half a second
        if (k % 32 == 0) pos.update(32 * dt);
        if (k % 4 == 0) vel.update(4 * dt);
        cur.update(dt);
        motor.step(s, dt);
        if (k % 1600 == 0)
            std::printf("t=%5.3f s  pos=%7.4f  vel=%8.3f  cur=%6.3f  V=%6.2f\n",
                        k * dt, s.pos, s.vel, s.cur, s.voltage);
    }
    return 0;
}
