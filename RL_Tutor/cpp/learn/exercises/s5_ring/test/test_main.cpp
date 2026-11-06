#include <string>
#include "alloc_count.hpp"
#include "check.hpp"
#include "ring_buffer.hpp"

struct Sample {
    double t, q;
};

int main() {
    CHECK_EQ("clampT<int>", clampT(7, 0, 5), 5);
    CHECK_NEAR("clampT<double>", clampT(-0.5, 0.0, 1.0), 0.0, 0.0);
    CHECK_EQ("clampT<std::string> (uses operator<)",
             clampT(std::string("zeta"), std::string("alpha"), std::string("beta")), std::string("beta"));

    RingBuffer<double, 3> r;
    CHECK_EQ("starts empty", r.size(), std::size_t(0));
    r.push(1); r.push(2);
    CHECK_EQ("two stored", r.size(), std::size_t(2));
    CHECK_NEAR("oldest", r.at(0), 1.0, 0.0);
    r.push(3); r.push(4); r.push(5);
    CHECK("full", r.full());
    CHECK_EQ("never more than N", r.size(), std::size_t(3));
    CHECK_NEAR("oldest after wrap is 3", r.at(0), 3.0, 0.0);
    CHECK_NEAR("newest is 5", r.at(2), 5.0, 0.0);
    CHECK_NEAR("latest() is 5", r.latest(), 5.0, 0.0);
    r.clear();
    CHECK_EQ("clear empties", r.size(), std::size_t(0));

    RingBuffer<Sample, 4> s;
    long before = chk::totalAllocs();
    for (int k = 0; k < 1000; ++k) s.push({k * 0.001, k * 1.0});
    CHECK_EQ("1000 pushes, zero heap allocations", chk::totalAllocs() - before, 0L);
    CHECK_NEAR("works for a struct too", s.latest().q, 999.0, 0.0);
    CHECK("the storage is inside the object", sizeof(s) >= 4 * sizeof(Sample));
    DONE();
}
