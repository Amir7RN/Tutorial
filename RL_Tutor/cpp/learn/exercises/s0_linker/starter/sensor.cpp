#include "helpers.hpp"

double sensorRead(double raw) {
    ++g_ticks;
    return clamp(raw * 0.01, -1.0, 1.0);
}
