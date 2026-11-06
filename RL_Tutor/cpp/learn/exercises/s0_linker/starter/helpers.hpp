#pragma once
// helpers.hpp is included by sensor.cpp AND motor.cpp (and by the test).
// #pragma once stops a double include inside ONE .cpp file. It does nothing
// across two .cpp files: each one is compiled alone and gets its own copy.
//
// The program compiles, then the LINKER fails with
//     multiple definition of `clamp(double, double, double)'
//     multiple definition of `g_ticks'
// because each object file now contains its own clamp and its own g_ticks.
//
// TODO: keep ONE definition of each in the whole program. Two standard fixes:
//   a) declare here, define once in helpers.cpp:
//        double clamp(double x, double lo, double hi);   // declaration only
//        extern int g_ticks;                             // "exists elsewhere"
//   b) C++17: mark both `inline` here (the linker then merges the copies).
// Try (a): it is what you will see in most codebases.

double clamp(double x, double lo, double hi) {
    return x < lo ? lo : (x > hi ? hi : x);
}

int g_ticks = 0;   // how many times any module has run
