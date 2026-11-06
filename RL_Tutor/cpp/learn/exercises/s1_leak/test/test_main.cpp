#include <cmath>
#include "alloc_count.hpp"
#include "check.hpp"
#include "window.hpp"

int main() {
    const double d[6] = {1, 2, 3, 4, 5, 6};
    const double bad[3] = {1, NAN, 3};
    long base = chk::liveAllocs();
    CHECK_NEAR("mean of the last 3", recentMean(d, 6, 3), 5.0, 1e-12);
    CHECK_EQ("normal path: no leak", chk::liveAllocs() - base, 0L);
    CHECK_NEAR("window larger than data -> 0", recentMean(d, 6, 9), 0.0, 0.0);
    CHECK_EQ("early-return path: no leak", chk::liveAllocs() - base, 0L);
    CHECK_NEAR("NaN in the window -> 0", recentMean(bad, 3, 3), 0.0, 0.0);
    CHECK_EQ("NaN path: no leak", chk::liveAllocs() - base, 0L);
    CHECK_NEAR("window 0 -> 0", recentMean(d, 6, 0), 0.0, 0.0);
    CHECK_EQ("window-0 path: no leak", chk::liveAllocs() - base, 0L);
    DONE();
}
