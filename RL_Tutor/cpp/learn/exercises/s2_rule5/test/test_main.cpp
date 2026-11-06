#include <type_traits>
#include <vector>
#include "alloc_count.hpp"
#include "check.hpp"
#include "trajectory.hpp"

int main() {
    CHECK("move constructor is noexcept (so std::vector will use it)",
          std::is_nothrow_move_constructible_v<Trajectory>);
    long base = chk::liveAllocs();
    bool shared = false;
    {
        Trajectory a(4);
        a[0] = 1.0; a[3] = 4.0;

        long before = chk::liveAllocs();
        Trajectory b(a);
        CHECK_EQ("copy allocates its own buffer", chk::liveAllocs() - before, 1L);
        CHECK("copy does not share the pointer", b.data() != a.data());
        shared = shared || b.data() == a.data();
        if (b.data() != a.data()) {
            CHECK_NEAR("copy has the same numbers", b[3], 4.0, 0.0);
            b[0] = 9.0;
            CHECK_NEAR("changing the copy leaves the original", a[0], 1.0, 0.0);
        }

        Trajectory c(2);
        c = a;
        CHECK("copy assignment gives a separate buffer", c.data() != a.data());
        shared = shared || c.data() == a.data();
        if (c.data() != a.data()) {
            CHECK_EQ("copy assignment copies the size", c.size(), std::size_t(4));
            c = c;
            CHECK_NEAR("self-assignment (c = c) keeps the data", c[3], 4.0, 0.0);
        }

        const double* buf = a.data();
        long total = chk::totalAllocs();
        Trajectory d(std::move(a));
        CHECK_EQ("move allocates nothing", chk::totalAllocs() - total, 0L);
        CHECK("move steals the buffer", d.data() == buf);
        CHECK("moved-from is empty (null data)", a.data() == nullptr);
        CHECK_EQ("moved-from has size 0", a.size(), std::size_t(0));

        Trajectory e(3);
        e = std::move(d);
        CHECK("move assignment steals", e.data() == buf);
        CHECK("and empties the source", d.data() == nullptr);
        if (shared) {   // avoid a double delete[] crashing the test before it reports
            std::cout << "FAIL buffers are still shared -- fix the copy members first" << std::endl;
            std::cout.flush();
            std::_Exit(0);
        }
    }
    CHECK_EQ("no leaks, no double frees", chk::liveAllocs() - base, 0L);
    DONE();
}
