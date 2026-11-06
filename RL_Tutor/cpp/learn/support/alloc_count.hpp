// alloc_count.hpp -- counts every heap allocation the program makes.
// Include it in exactly ONE .cpp (the test main): it replaces the global
// operator new/delete, which is legal C++ and is how leak checkers start.
//   long before = chk::liveAllocs();  ...  CHECK_EQ("no leak", chk::liveAllocs() - before, 0L);
#pragma once
#include <cstdlib>
#include <new>

namespace chk {
inline long& liveRef() { static long n = 0; return n; }
inline long& totalRef() { static long n = 0; return n; }
inline long liveAllocs() { return liveRef(); }     // allocations not yet freed
inline long totalAllocs() { return totalRef(); }   // allocations ever made
}  // namespace chk

void* operator new(std::size_t n) {
    void* p = std::malloc(n ? n : 1);
    if (!p) throw std::bad_alloc();
    ++chk::liveRef(); ++chk::totalRef();
    return p;
}
void* operator new[](std::size_t n) { return operator new(n); }
void operator delete(void* p) noexcept { if (p) { --chk::liveRef(); std::free(p); } }
void operator delete[](void* p) noexcept { operator delete(p); }
void operator delete(void* p, std::size_t) noexcept { operator delete(p); }
void operator delete[](void* p, std::size_t) noexcept { operator delete(p); }
