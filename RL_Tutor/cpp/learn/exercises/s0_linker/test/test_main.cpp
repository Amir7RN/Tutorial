#include "check.hpp"
#include "helpers.hpp"

double sensorRead(double raw);
double motorCommand(double u);

int main() {
    CHECK_NEAR("sensor scales by 0.01", sensorRead(50), 0.5, 1e-12);
    CHECK_NEAR("sensor clamps to +1", sensorRead(500), 1.0, 0.0);
    CHECK_NEAR("motor clamps to 24 V", motorCommand(30), 24.0, 0.0);
    CHECK_EQ("one g_ticks shared by every file", g_ticks, 3);
    CHECK_NEAR("clamp is usable from a third file", clamp(-5, -1, 1), -1.0, 0.0);
    DONE();
}
