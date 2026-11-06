// main.cpp -- your playground. "Run main" builds pid.cpp + this file.
// (When you press "Check", the tutor links its own test main instead of this one.)
#include <cstdio>
#include "pid.hpp"

int main() {
    Pid pid(2.0, 1.0, 0.1, 0.001);
    for (int k = 0; k < 5; ++k)
        std::printf("u[%d] = %.4f\n", k, pid.update(1.0));
    return 0;
}
