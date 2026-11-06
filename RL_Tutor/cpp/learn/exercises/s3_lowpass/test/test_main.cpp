#include <cmath>
#include "check.hpp"
#include "lowpass.hpp"

int main() {
    const double pi = 3.14159265358979323846;
    CHECK_THROWS("rejects cutoff 0", LowPass(0.0, 0.001));
    CHECK_THROWS("rejects negative dt", LowPass(10.0, -0.001));
    CHECK_THROWS("rejects NaN cutoff", LowPass(NAN, 0.001));
    LowPass f(10.0, 0.001);
    const double a = 0.001 / (0.001 + 1.0 / (2 * pi * 10.0));
    CHECK_NEAR("alpha from fc and dt", f.alpha(), a, 1e-12);
    CHECK_NEAR("first step from 0 toward 1", f.update(1.0), a, 1e-12);
    for (int k = 0; k < 2000; ++k) f.update(1.0);
    CHECK_NEAR("converges to the input", f.value(), 1.0, 1e-6);
    f.reset(-2.0);
    CHECK_NEAR("reset sets the output", f.value(), -2.0, 0.0);
    const LowPass& view = f;
    CHECK_NEAR("value() works on a const filter", view.value(), -2.0, 0.0);
    CHECK("object holds no more than it needs (<= 3 doubles)", sizeof(LowPass) <= 3 * sizeof(double));
    DONE();
}
