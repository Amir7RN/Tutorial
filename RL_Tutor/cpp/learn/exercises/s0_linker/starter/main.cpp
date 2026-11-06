#include <cstdio>
#include "helpers.hpp"

double sensorRead(double raw);   // declared here, defined in sensor.cpp
double motorCommand(double u);   // declared here, defined in motor.cpp

int main() {
    std::printf("sensor %.2f  motor %.2f  ticks %d\n", sensorRead(42), motorCommand(30), g_ticks);
    return 0;
}
