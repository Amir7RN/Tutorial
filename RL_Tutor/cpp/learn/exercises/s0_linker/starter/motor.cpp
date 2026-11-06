#include "helpers.hpp"

double motorCommand(double u) {
    ++g_ticks;
    return clamp(u, -24.0, 24.0);
}
