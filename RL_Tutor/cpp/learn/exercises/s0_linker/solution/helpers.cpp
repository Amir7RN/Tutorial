#include "helpers.hpp"

double clamp(double x, double lo, double hi) {
    return x < lo ? lo : (x > hi ? hi : x);
}

int g_ticks = 0;
