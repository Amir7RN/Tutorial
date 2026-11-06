// v3: the cascade comes from a config string. Try breaking a line and
// reading the error; try retuning without touching any class.
#include <cstdio>
#include "config.hpp"
#include "motor.hpp"

int main() {
    const char* cfg =
        "# joint 1 cascade\n"
        "position 1000  kp=63   limit=100\n"
        "velocity 8000  kp=0.25 ki=30   limit=5\n"
        "current  32000 kp=4.7  ki=9400 limit=24\n";
    Signals s;
    std::string err;
    auto sched = buildFromConfig(cfg, 32000, s, &err);
    if (!sched) { std::printf("config error: %s\n", err.c_str()); return 1; }
    MotorPlant motor;
    s.posRef = 1.0;
    for (long k = 0; k < 16000; ++k) {
        sched->tick();
        motor.step(s, 1.0 / 32000);
        if (k % 1600 == 0) std::printf("t=%5.3f  pos=%7.4f\n", k / 32000.0, s.pos);
    }
    return 0;
}
