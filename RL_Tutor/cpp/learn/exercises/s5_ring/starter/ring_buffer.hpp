#pragma once
#include <array>
#include <cstddef>

// TODO 1: a function template: works for any T that has operator<.
//         The compiler writes one copy per T you use (int, double, std::string...).
template <class T>
const T& clampT(const T& x, const T& lo, const T& hi) {
    return x;
}

// TODO 2: a fixed-capacity ring buffer. No heap: the storage is a
// std::array<T, N> member, so its size is part of the TYPE and known at
// compile time. push() overwrites the OLDEST element when full.
// at(0) is the oldest element, at(size()-1) the newest.
template <class T, std::size_t N>
class RingBuffer {
    static_assert(N > 0, "a ring needs at least one slot");

public:
    void push(const T& x) {}
    std::size_t size() const { return 0; }
    static constexpr std::size_t capacity() { return N; }
    bool full() const { return false; }
    const T& at(std::size_t i) const { return buf_[0]; }
    const T& latest() const { return buf_[0]; }
    void clear() {}

private:
    std::array<T, N> buf_{};
    // TODO: what else must it remember? (where the next write goes; how many are stored)
};
