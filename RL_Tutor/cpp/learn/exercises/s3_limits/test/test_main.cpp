#include <cmath>
#include "check.hpp"
#include "limits.hpp"

int main() {
    CHECK_THROWS("constructor rejects lo > hi", Limits(1.0, -1.0));
    CHECK_THROWS("constructor rejects NaN", Limits(NAN, 1.0));
    CHECK_NOTHROW("lo == hi is a valid (single-point) range", Limits(2.0, 2.0));
    Limits L(-1.0, 2.0);
    CHECK_NEAR("clamp below", L.clamp(-5.0), -1.0, 0.0);
    CHECK_NEAR("clamp above", L.clamp(5.0), 2.0, 0.0);
    CHECK_NEAR("clamp inside is identity", L.clamp(0.5), 0.5, 0.0);
    CHECK("contains the edge", L.contains(2.0));
    CHECK("does not contain outside", !L.contains(2.0001));
    CHECK_THROWS("setRange rejects lo > hi", L.setRange(3.0, 1.0));
    CHECK("after a refused setRange, the old range is intact", L.lo() == -1.0 && L.hi() == 2.0);
    L.setRange(0.0, 10.0);
    CHECK("a valid setRange applies", L.lo() == 0.0 && L.hi() == 10.0);
    DONE();
}
