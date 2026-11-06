#include <type_traits>
#include "alloc_count.hpp"
#include "check.hpp"
#include "sample_buffer.hpp"

int main() {
    CHECK("copying is forbidden (deleted copy constructor)",
          !std::is_copy_constructible_v<SampleBuffer>);
    long base = chk::liveAllocs();
    {
        SampleBuffer b(8);
        CHECK_EQ("constructor allocates exactly one block", chk::liveAllocs() - base, 1L);
        CHECK_EQ("size() is 8", b.size(), std::size_t(8));
        if (chk::liveAllocs() - base == 1) {   // only touch memory that exists
            bool zero = true;
            for (std::size_t i = 0; i < b.size(); ++i) zero = zero && b[i] == 0.0;
            CHECK("starts zeroed", zero);
            b[3] = 2.5;
            CHECK_NEAR("write then read back", b[3], 2.5, 0.0);
        }
    }
    CHECK_EQ("the closing brace frees it (destructor ran)", chk::liveAllocs() - base, 0L);
    for (int k = 0; k < 1000; ++k) { SampleBuffer tmp(64); (void)tmp; }
    CHECK_EQ("1000 buffers later, still nothing leaked", chk::liveAllocs() - base, 0L);
    DONE();
}
